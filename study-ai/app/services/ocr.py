from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

from app.models.schemas import OcrResponse


class OcrService:
    """OCR with lightweight preprocessing and study-problem normalization."""

    async def extract_text(self, image_bytes: bytes) -> OcrResponse:
        variants, image_quality = self._build_image_variants(image_bytes)
        candidates: list[dict[str, Any]] = []
        engine_error: str | None = None
        for variant_name, variant_bytes in variants:
            try:
                candidate = self._read_tesseract(variant_bytes, variant_name)
            except Exception as exc:  # An image upload must not break the app flow.
                engine_error = str(exc)
                continue
            if candidate["raw_text"].strip():
                candidate["score"] = self._candidate_score(candidate["raw_text"], candidate["confidence"])
                candidates.append(candidate)
        if not candidates:
            return self._empty_response(engine_error, image_quality)
        candidates.sort(key=lambda item: item["score"], reverse=True)
        best = candidates[0]
        return self.recognize_text(
            best["raw_text"],
            base_confidence=best["confidence"],
            engine="tesseract",
            preprocessing_steps=[name for name, _ in variants],
            image_quality=image_quality,
            candidates=candidates[:4],
        )

    def recognize_text(
        self,
        raw_text: str,
        base_confidence: float = 0.82,
        engine: str = "text-normalizer",
        preprocessing_steps: list[str] | None = None,
        image_quality: dict[str, Any] | None = None,
        candidates: list[dict[str, Any]] | None = None,
    ) -> OcrResponse:
        normalized, corrections = self._normalize_text(raw_text)
        recognition = self._recognize_problem(normalized)
        warnings = self._ocr_warnings(normalized, base_confidence, recognition, image_quality or {})
        confidence = self._adjust_confidence(base_confidence, normalized, warnings, recognition)
        return OcrResponse(
            extracted_text=normalized,
            confidence=round(confidence, 3),
            raw_text=raw_text,
            normalized_text=normalized,
            detected_subject=recognition["subject"],
            detected_unit=recognition["unit"],
            problem_type=recognition["problem_type"],
            formula_candidates=recognition["formula_candidates"],
            numbers=recognition["numbers"],
            corrections=corrections,
            warnings=warnings,
            needs_review=self._needs_review(confidence, warnings, recognition),
            engine=engine,
            preprocessing_steps=preprocessing_steps or [],
            image_quality=image_quality or {},
            candidates=self._public_candidates(candidates or []),
        )

    def _read_tesseract(self, image_bytes: bytes, variant_name: str) -> dict[str, Any]:
        import pytesseract
        from PIL import Image
        from pytesseract import Output

        image = Image.open(io.BytesIO(image_bytes))
        configs = [
            ("psm6_block", "--oem 3 --psm 6 -c preserve_interword_spaces=1"),
            ("psm4_column", "--oem 3 --psm 4 -c preserve_interword_spaces=1"),
            ("psm11_sparse", "--oem 3 --psm 11 -c preserve_interword_spaces=1"),
            ("psm12_sparse_osd", "--oem 3 --psm 12 -c preserve_interword_spaces=1"),
        ]
        best: dict[str, Any] | None = None
        for config_name, config in configs:
            try:
                data = pytesseract.image_to_data(image, lang="kor+eng", config=config, output_type=Output.DICT)
            except pytesseract.TesseractError:
                data = pytesseract.image_to_data(image, lang="eng", config=config, output_type=Output.DICT)
            lines: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
            confidences: list[float] = []
            for index, token in enumerate(data.get("text", [])):
                value = str(token).strip()
                if not value:
                    continue
                try:
                    confidence = float(data["conf"][index])
                except (KeyError, TypeError, ValueError):
                    confidence = -1
                if confidence >= 0:
                    confidences.append(confidence / 100)
                key = (
                    int(data.get("block_num", [0])[index]),
                    int(data.get("par_num", [0])[index]),
                    int(data.get("line_num", [0])[index]),
                )
                left = int(data.get("left", [0])[index])
                lines.setdefault(key, []).append((left, value))
            raw_text = "\n".join(
                " ".join(value for _, value in sorted(tokens, key=lambda item: item[0]))
                for _, tokens in sorted(lines.items(), key=lambda item: item[0])
            )
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            candidate = {
                "engine": "tesseract",
                "variant": f"{variant_name}:{config_name}",
                "raw_text": raw_text,
                "confidence": round(confidence, 3),
                "line_count": len(lines),
            }
            candidate["score"] = self._candidate_score(candidate["raw_text"], candidate["confidence"])
            if best is None or candidate["score"] > best["score"]:
                best = candidate
        return best or {
            "engine": "tesseract",
            "variant": variant_name,
            "raw_text": "",
            "confidence": 0.0,
            "line_count": 0,
            "score": 0.0,
        }

    def _build_image_variants(self, image_bytes: bytes) -> tuple[list[tuple[str, bytes]], dict[str, Any]]:
        variants = [("original", image_bytes)]
        quality: dict[str, Any] = {"bytes": len(image_bytes)}
        try:
            from PIL import Image, ImageEnhance, ImageOps

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            gray = ImageOps.grayscale(image)
            auto = ImageOps.autocontrast(gray)
            quality.update({"width": image.width, "height": image.height})
            quality.update(self._image_features(auto))
            scale = 3 if max(image.width, image.height) < 1100 else 2 if max(image.width, image.height) < 2200 else 1
            upscaled = auto.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
            clean = ImageEnhance.Contrast(upscaled).enhance(1.8)
            clean = ImageEnhance.Sharpness(clean).enhance(1.6)
            high_contrast = ImageEnhance.Contrast(upscaled).enhance(2.6)
            inverted = ImageOps.invert(auto)
            threshold_soft = clean.point(lambda pixel: 255 if pixel > 145 else 0)
            threshold_hard = clean.point(lambda pixel: 255 if pixel > 185 else 0)
            graph_friendly = ImageEnhance.Sharpness(ImageEnhance.Contrast(auto).enhance(2.2)).enhance(2.0)
            variants.extend(
                [
                    ("gray_autocontrast", self._to_png_bytes(auto)),
                    ("upscale_contrast_sharp", self._to_png_bytes(clean)),
                    ("high_contrast", self._to_png_bytes(high_contrast)),
                    ("binary_threshold_soft", self._to_png_bytes(threshold_soft)),
                    ("binary_threshold_hard", self._to_png_bytes(threshold_hard)),
                    ("inverted", self._to_png_bytes(inverted)),
                    ("graph_line_sharp", self._to_png_bytes(graph_friendly)),
                ]
            )
        except Exception as exc:
            quality["preprocess_error"] = str(exc)
        return self._dedupe_variants(variants), quality

    def _image_features(self, gray_image: Any) -> dict[str, Any]:
        sample = gray_image.resize((160, 160))
        pixels = list(sample.getdata())
        mean = sum(pixels) / len(pixels)
        variance = sum((pixel - mean) ** 2 for pixel in pixels) / len(pixels)
        dark = [1 if pixel < 130 else 0 for pixel in pixels]
        row_ratios = [sum(dark[row * 160 : (row + 1) * 160]) / 160 for row in range(160)]
        col_ratios = [sum(dark[col::160]) / 160 for col in range(160)]
        horizontal = sum(1 for ratio in row_ratios if ratio > 0.62)
        vertical = sum(1 for ratio in col_ratios if ratio > 0.62)
        medium_lines = sum(1 for ratio in row_ratios + col_ratios if ratio > 0.35)
        ink_ratio = sum(dark) / len(dark)
        likely_graph = horizontal + vertical >= 2 or medium_lines >= 5
        likely_geometry = not likely_graph and 0.01 < ink_ratio < 0.22 and medium_lines >= 2
        return {
            "brightness": round(mean, 1),
            "contrast": round(variance**0.5, 1),
            "ink_ratio": round(ink_ratio, 3),
            "visual_features": {
                "horizontal_lines": horizontal,
                "vertical_lines": vertical,
                "medium_lines": medium_lines,
                "likely_graph": likely_graph,
                "likely_geometry": likely_geometry,
            },
        }

    def _to_png_bytes(self, image: Any) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _dedupe_variants(self, variants: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
        seen: set[int] = set()
        unique: list[tuple[str, bytes]] = []
        for name, data in variants:
            marker = hash(data)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append((name, data))
        return unique

    def _normalize_text(self, text: str) -> tuple[str, list[str]]:
        corrections: list[str] = []
        normalized = str(text or "")
        # Preserve exponent meaning before NFKC flattens superscript characters.
        for source, target in {
            "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4",
            "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
        }.items():
            normalized = normalized.replace(source, target)
        normalized = unicodedata.normalize("NFKC", normalized)
        before = normalized
        replacements = {
            "−": "-",
            "–": "-",
            "—": "-",
            "×": "*",
            "÷": "/",
            "㎡": "m^2",
            "㎥": "m^3",
            "㎤": "cm^3",
            "Ω": "Ω",
            "⁰": "^0",
            "¹": "^1",
            "²": "^2",
            "³": "^3",
            "⁴": "^4",
            "⁵": "^5",
            "⁶": "^6",
            "⁷": "^7",
            "⁸": "^8",
            "⁹": "^9",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)
        for source, target in {
            "이 차 함수": "이차함수",
            "구 하시오": "구하시오",
            "풀 어라": "풀어라",
            "질 량": "질량",
            "가 속도": "가속도",
            "전 압": "전압",
            "전 류": "전류",
            "전 력": "전력",
            "밀 도": "밀도",
            "부 피": "부피",
        }.items():
            normalized = normalized.replace(source, target)
        normalized = re.sub(r"\bminimum\s*value\??", "최솟값", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bmaximum\s*value\??", "최댓값", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bmax(?:imum)?\s*height\??", "최대높이", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bfind\s+(?:the\s+)?", "구하시오 ", normalized, flags=re.IGNORECASE)
        if normalized != before:
            corrections.append("수식 기호와 윗첨자를 정리했습니다.")
        before = normalized
        normalized = re.sub(r"\s*([=+\-*/^(),:])\s*", r"\1", normalized)
        normalized = re.sub(r"(?<=\d)\s+(?=[A-Za-z가-힣])", "", normalized)
        normalized = re.sub(r"(?<=[가-힣])\s+(?=\d)", " ", normalized)
        normalized = re.sub(r"이\s*차\s*함\s*수", "이차함수", normalized)
        normalized = normalized.replace("최소값", "최솟값").replace("최대값", "최댓값")
        normalized = normalized.replace("최대 높이", "최대높이")
        normalized = re.sub(r"(?<![A-Za-z])([xX])\s*[Aa]\s*2\b", r"\1^2", normalized)
        normalized = re.sub(r"(?<![A-Za-z])([xX])2(?=[+\-=)]|$|\s)", r"\1^2", normalized)
        normalized = re.sub(r"(?<![A-Za-z])([xyXY])\s*[∧^]\s*([0-9])", r"\1^\2", normalized)
        normalized = re.sub(r"([xy])\s*\^\s*(\d+)", r"\1^\2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"([xy])\^(\d)(?=\d*x)", r"\1^\2-", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"([xy])\^2(\d+(?:\.\d+)?)x", r"\1^2-\2x", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bf\s*\(\s*x\s*\)", "f(x)", normalized, flags=re.IGNORECASE)
        unit_end = r"(?=$|[^A-Za-z0-9])"
        normalized = re.sub(r"(?<![A-Za-z])m\s*/\s*s\s*\^?\s*2" + unit_end, "m/s^2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![A-Za-z])m\s*/\s*s2" + unit_end, "m/s^2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![A-Za-z])g\s*/\s*cm\s*\^?\s*3" + unit_end, "g/cm^3", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![A-Za-z])cm\s*\^?\s*3" + unit_end, "cm^3", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![A-Za-z])cm\s*\^?\s*2" + unit_end, "cm^2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![A-Za-z])m\s*\^?\s*2" + unit_end, "m^2", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bP\s*=\s*V\s*I\b", "P=VI", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bV\s*=\s*I\s*R\b", "V=IR", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bx\^2\s+(\d+(?:\.\d+)?)\s*x\b", r"x^2-\1x", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bX(?=\^|=|[+\-*/]|\d)", "x", normalized)
        normalized = re.sub(r"(?<=[\d^])X\b", "x", normalized)
        normalized = normalized.replace("X", "x")
        normalized = re.sub(r"(?<=[=+\-*/(^])O(?=\d|\b)", "0", normalized)
        normalized = re.sub(r"(?<=\d)O(?=\d|[+\-*/)]|$)", "0", normalized)
        normalized = re.sub(r"(?<=[=+\-*/(^])(?:I|l)(?=\d|\b)", "1", normalized)
        normalized = re.sub(r"(?<=\d)(?:I|l)(?=\d|[+\-*/)]|$)", "1", normalized)
        normalized = re.sub(r"(?<=\d)S(?=\d|[+\-*/)]|$)", "5", normalized)
        normalized = re.sub(r"(?<=\d)B(?=\d|[+\-*/)]|$)", "8", normalized)
        normalized = re.sub(r"\b([Ff])\s*[=:]\s*([Mm])\s*[Aa]\b", "F=ma", normalized)
        if "=" in normalized and "x" not in normalized.lower():
            normalized = re.sub(r"(?<=\d)%(?=[+\-=])", "x", normalized)
        normalized = self._repair_equation_lines(normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n\s+", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip(" .,")
        if normalized != before:
            corrections.append("OCR 문자와 수식 간격을 보정했습니다.")
        return normalized, corrections

    def _repair_equation_lines(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        repaired: list[str] = []
        for line in lines or [text]:
            line = re.sub(r"([+\-=])\s*([+\-=])+", r"\1", line)
            line = re.sub(r"(?<=\d)\*([xy])", r"\1", line, flags=re.IGNORECASE)
            line = re.sub(r"(?<=\d)\s+([xy])", r"\1", line, flags=re.IGNORECASE)
            repaired.append(line)
        return "\n".join(repaired)

    def _recognize_problem(self, text: str) -> dict[str, Any]:
        subject = self._detect_subject(text)
        unit, problem_type = "미분류", "일반 문제"
        if subject == "math":
            if "x^2" in text or "이차" in text:
                unit, problem_type = "이차함수/이차방정식", "최댓값·최솟값" if any(word in text for word in ["최댓값", "최솟값"]) else "이차식 분석"
            elif "연립" in text:
                unit, problem_type = "연립방정식", "방정식 계산"
            elif "확률" in text:
                unit, problem_type = "확률", "경우의 수·확률"
            elif "평균" in text:
                unit, problem_type = "통계", "평균 계산"
            else:
                unit, problem_type = "수학", "식 계산"
        elif subject == "science":
            if any(word in text for word in ["전압", "전류", "저항", "전력", "V=IR", "P=VI"]):
                unit = "물리/전기"
            elif any(word in text for word in ["힘", "가속도", "F=ma", "속력", "거리"]):
                unit = "물리/힘과 운동"
            elif any(word in text for word in ["던지", "수직방향", "최대높이", "중력가속도", "포물선"]):
                unit = "물리/역학"
            elif any(word in text for word in ["열량", "비열", "온도 변화"]):
                unit = "물리/열"
            elif any(word in text for word in ["파동", "파장", "진동수"]):
                unit = "물리/파동"
            elif any(word in text for word in ["밀도", "부피", "g/cm^3", "cm^3"]):
                unit = "화학/밀도"
            elif any(word in text for word in ["몰", "몰농도", "질량"]):
                unit = "화학/몰과 농도"
            else:
                unit = "과학"
            problem_type = "공식 적용형"
        return {
            "subject": subject,
            "unit": unit,
            "problem_type": problem_type,
            "formula_candidates": self._extract_formula_candidates(text),
            "numbers": re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", text),
        }

    def _detect_subject(self, text: str) -> str:
        science_words = ["질량", "가속도", "힘", "전압", "전류", "전력", "저항", "속력", "속도", "거리", "높이", "중력", "던지", "파동", "몰", "열량", "F=ma", "P=VI", "V=IR", "kg", "m/s", "N", "J"]
        math_words = ["함수", "방정식", "최솟값", "최댓값", "확률", "평균", "연립", "그래프", "좌표", "기울기", "x^2", "f(x)"]
        science_score = sum(word in text for word in science_words)
        math_score = sum(word in text for word in math_words)
        if science_score > math_score:
            return "science"
        if math_score > 0 or re.search(r"\b\d*x\^?2|\bx[+\-*/=]", text, re.IGNORECASE):
            return "math"
        return "unknown"

    def _extract_formula_candidates(self, text: str) -> list[str]:
        patterns = [
            r"y=[^가-힣\s,]+",
            r"f\(x\)=[^가-힣\s,]+",
            r"[FPVIRW]=[A-Za-z0-9*/^+\-()]+",
            r"-?\d*x\^2[+\-]\d*x[+\-]\d+",
            r"\d*x[+\-]\d+=\d+",
            r"v\^2=v_?0\^2[+\-]2a[sh]",
            r"h=v_?0t[+\-]\d+(?:\.\d+)?t\^2",
            r"\d+(?:\.\d+)?\s*(?:kg|N|V|A|W|Ω|m/s\^2|m/s|J|Pa|mol|g/mol|cm\^3|cm\^2|m\^2|L|mL)",
        ]
        formulas: list[str] = []
        for pattern in patterns:
            formulas.extend(match.group(0) for match in re.finditer(pattern, text, re.IGNORECASE))
        return list(dict.fromkeys(formulas))[:8]

    def _ocr_warnings(self, text: str, confidence: float, recognition: dict[str, Any], quality: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        if confidence < 0.55:
            warnings.append("OCR 신뢰도가 낮습니다.")
        if len(text) < 8:
            warnings.append("인식된 글자가 너무 적습니다.")
        if recognition["subject"] == "unknown":
            warnings.append("과목 자동 판별이 불확실합니다.")
        if quality.get("width", 9999) < 600 or quality.get("height", 9999) < 240:
            warnings.append("사진 해상도가 낮습니다.")
        if quality.get("contrast", 99) < 16:
            warnings.append("사진 대비가 낮습니다.")
        visual = quality.get("visual_features", {})
        if visual.get("likely_graph") and not recognition["formula_candidates"]:
            warnings.append("그래프/표처럼 보이지만 축 숫자 인식이 부족합니다.")
        if visual.get("likely_geometry") and len(recognition["numbers"]) < 2:
            warnings.append("도형처럼 보이지만 길이 숫자 인식이 부족합니다.")
        if not any(word in text for word in ["구하", "계산", "설명", "값", "얼마"]):
            warnings.append("질문 문장이 잘렸는지 확인해 주세요.")
        return warnings

    def _adjust_confidence(self, base: float, text: str, warnings: list[str], recognition: dict[str, Any]) -> float:
        confidence = base
        confidence += 0.05 if len(text) >= 15 else 0
        confidence += 0.08 if recognition["subject"] != "unknown" else 0
        confidence += 0.06 if recognition["unit"] != "미분류" else 0
        confidence += 0.06 if recognition["formula_candidates"] else 0
        confidence += 0.04 if recognition["numbers"] else 0
        confidence -= min(0.28, len(warnings) * 0.04)
        return max(0.0, min(1.0, confidence))

    def _candidate_score(self, raw_text: str, confidence: float) -> float:
        normalized, _ = self._normalize_text(raw_text)
        recognition = self._recognize_problem(normalized)
        score = confidence + min(0.16, len(normalized) / 500)
        score += 0.12 if recognition["subject"] != "unknown" else 0
        score += 0.08 if recognition["unit"] != "미분류" else 0
        score += 0.10 if recognition["formula_candidates"] else 0
        score += 0.05 if recognition["numbers"] else 0
        score += 0.05 if any(word in normalized for word in ["구하", "계산", "최솟값", "최댓값", "얼마"]) else 0
        score -= 0.10 if self._garbage_ratio(normalized) > 0.28 else 0
        return score

    def _garbage_ratio(self, text: str) -> float:
        if not text:
            return 1.0
        useful = sum(1 for ch in text if ch.isalnum() or ch.isspace() or ch in "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호구누두루무부수우주추쿠투푸후그느드르므브스으즈츠크트프흐기니디리미비시이지치키티피히+-=*/^().,?:%Ω")
        return 1 - useful / len(text)

    def _needs_review(self, confidence: float, warnings: list[str], recognition: dict[str, Any]) -> bool:
        return confidence < 0.72 or recognition["subject"] == "unknown" or len(warnings) >= 3

    def _public_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        public: list[dict[str, Any]] = []
        for candidate in candidates:
            normalized, _ = self._normalize_text(candidate.get("raw_text", ""))
            public.append(
                {
                    "variant": candidate.get("variant"),
                    "confidence": candidate.get("confidence", 0.0),
                    "score": round(float(candidate.get("score", 0.0)), 3),
                    "text": normalized[:240],
                }
            )
        return public

    def _empty_response(self, engine_error: str | None, quality: dict[str, Any]) -> OcrResponse:
        warnings = ["사진에서 글자를 찾지 못했습니다.", "밝기와 초점을 확인하고 문제 부분만 크게 찍어 주세요."]
        if engine_error:
            warnings.append(f"OCR 엔진 오류: {engine_error[:120]}")
        return OcrResponse(
            extracted_text="사진에서 문제를 읽지 못했습니다. 문제 부분만 밝고 선명하게 다시 찍어 주세요.",
            confidence=0.0,
            raw_text="",
            normalized_text="",
            detected_subject="unknown",
            detected_unit="미분류",
            problem_type="인식 실패",
            formula_candidates=[],
            numbers=[],
            corrections=[],
            warnings=warnings,
            needs_review=True,
            engine="tesseract",
            preprocessing_steps=[],
            image_quality=quality,
            candidates=[],
        )
