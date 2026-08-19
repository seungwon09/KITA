from __future__ import annotations

import re

from app.models.schemas import ProblemRecognitionRequest, ProblemRecognitionResponse, QualityCheckRequest, QualityCheckResponse
from app.services.math_solver import MathSolver
from app.services.ocr import OcrService
from app.services.science_solver import ScienceSolver


class ProblemRecognitionService:
    def __init__(self, ocr: OcrService | None = None) -> None:
        self.ocr = ocr or OcrService()
        self.math_solver = MathSolver()
        self.science_solver = ScienceSolver()

    def recognize(self, request: ProblemRecognitionRequest) -> ProblemRecognitionResponse:
        normalized = self.ocr.recognize_text(request.problem_text, base_confidence=0.9)
        subject = request.subject if request.subject in {"math", "science"} else normalized.detected_subject
        if subject == "unknown":
            subject = self._subject_from_text(normalized.extracted_text)
        unit, problem_type = self._fallback_unit(normalized.extracted_text, subject)
        if normalized.detected_unit not in {None, "미분류"}:
            unit = normalized.detected_unit
        if normalized.problem_type not in {None, "일반 문제"}:
            problem_type = normalized.problem_type
        solved = self._solve(normalized.extracted_text, subject)
        known_values = self._known_values(normalized.extracted_text)
        warnings = list(normalized.warnings)
        if subject == "unknown":
            warnings.append("과목 판별이 불확실합니다.")
        if not solved:
            warnings.append("규칙 풀이 범위를 벗어나 로컬 AI 보완이 필요합니다.")
        confidence = normalized.confidence + (0.08 if solved else 0) + (0.04 if known_values else 0)
        confidence = round(max(0.0, min(1.0, confidence - max(0, len(warnings) - 1) * 0.03)), 3)
        return ProblemRecognitionResponse(
            original_text=request.problem_text,
            normalized_text=normalized.extracted_text,
            detected_subject=subject,
            detected_unit=unit,
            problem_type=problem_type,
            formula_candidates=normalized.formula_candidates,
            numbers=normalized.numbers,
            known_values=known_values,
            required_values=self._required_values(normalized.extracted_text),
            strategy_tags=self._strategy_tags(normalized.extracted_text, subject, solved is not None),
            solvable_by_rules=solved is not None,
            verified_answer=solved[3] if solved else None,
            confidence=confidence,
            warnings=list(dict.fromkeys(warnings)),
            next_action="규칙 풀이 결과를 바로 표시합니다." if solved else "로컬 AI 답변을 함께 생성하고 사용자 확인을 받습니다.",
        )

    def quality_check(self, request: QualityCheckRequest) -> QualityCheckResponse:
        recognition = self.recognize(
            ProblemRecognitionRequest(
                user_id=request.user_id,
                problem_text=request.problem_text,
                subject=request.subject,
                source="quality_check",
            )
        )
        solved = self._solve(recognition.normalized_text, recognition.detected_subject)
        verified = solved[3] if solved else None
        expected_match = self._answer_match(request.expected_answer, verified) if request.expected_answer else None
        student_match = self._answer_match(request.student_answer, verified or request.expected_answer) if request.student_answer else None
        flags: list[str] = []
        if not solved:
            flags.append("규칙 검산 불가")
        if recognition.confidence < 0.72:
            flags.append("문제 인식 신뢰도 낮음")
        if expected_match is False:
            flags.append("제공 정답과 검산 결과 불일치")
        if student_match is False:
            flags.append("학생 답안 불일치")
        if request.elapsed_seconds is not None and request.elapsed_seconds >= 180:
            flags.append("풀이 시간 초과")
        preview = {}
        if solved:
            preview = {"basic_solution": solved[0][:600], "fast_solution": solved[1][:400], "similar_problem": solved[2]}
        return QualityCheckResponse(
            recognition=recognition,
            solver_engine="rules" if solved else "local_llm_needed",
            verified_answer=verified,
            expected_answer_match=expected_match,
            student_answer_match=student_match,
            confidence=max(0.0, round(recognition.confidence - len(flags) * 0.04, 3)),
            risk_flags=flags,
            recommended_action="풀이와 검산 결과를 바로 표시합니다." if not flags else "표시 전 인식 결과와 답안을 한 번 확인해 주세요.",
            solution_preview=preview,
        )

    def _solve(self, text: str, subject: str) -> tuple[str, str, str, str | None] | None:
        if subject == "science":
            return self.science_solver.solve(text) or self.math_solver.solve(text)
        return self.math_solver.solve(text) or self.science_solver.solve(text)

    def _subject_from_text(self, text: str) -> str:
        science = ["질량", "가속도", "힘", "전압", "전류", "전력", "저항", "속력", "파동", "몰", "kg", "m/s"]
        math = ["함수", "방정식", "최솟값", "최댓값", "확률", "평균", "x^2", "f(x)"]
        if sum(word in text for word in science) > sum(word in text for word in math):
            return "science"
        return "math" if any(word in text for word in math) or "x" in text else "unknown"

    def _fallback_unit(self, text: str, subject: str) -> tuple[str, str]:
        if subject == "math":
            if "x^2" in text or "이차" in text:
                return "이차함수/이차방정식", "이차식 분석"
            if "확률" in text or "평균" in text:
                return "확률과 통계", "계산형"
            return "수학", "일반 수학 문제"
        if subject == "science":
            if any(word in text for word in ["전압", "전류", "저항", "전력"]):
                return "물리/전기", "공식 적용형"
            if any(word in text for word in ["몰", "몰농도"]):
                return "화학/몰과 농도", "공식 적용형"
            return "물리", "공식 적용형"
        return "미분류", "일반 문제"

    def _known_values(self, text: str) -> list[dict[str, str]]:
        units = r"(kg|g/mol|g/cm\^3|cm\^3|cm\^2|m/s\^2|m/s|m\^2|mol|mL|Pa|Hz|N|V|A|W|J|Ω|L|g|m|s)"
        values = [
            {"value": match.group(1), "unit": match.group(2), "label": self._nearest_label(text, match.start())}
            for match in re.finditer(rf"(-?\d+(?:\.\d+)?)\s*{units}", text)
        ]
        for match in re.finditer(r"([a-zA-Z])\s*=\s*(-?\d+(?:\.\d+)?)", text):
            values.append({"value": match.group(2), "unit": "", "label": match.group(1)})
        return values[:12]

    def _nearest_label(self, text: str, index: int) -> str:
        window = text[max(0, index - 16) : index + 16]
        for label in ["질량", "가속도", "힘", "전압", "전류", "전력", "저항", "거리", "시간", "속력", "밀도", "부피", "몰수", "몰질량"]:
            if label in window:
                return label
        return "값"

    def _required_values(self, text: str) -> list[str]:
        for value in ["최솟값", "최댓값", "힘", "질량", "가속도", "전력", "전압", "전류", "저항", "속력", "거리", "시간", "밀도", "부피", "몰수", "주기", "운동량", "충격량", "전기에너지", "농도"]:
            if value in text and any(word in text for word in ["구하", "계산", "얼마"]):
                return [value]
        return ["x"] if "=" in text and "x" in text else []

    def _strategy_tags(self, text: str, subject: str, solvable: bool) -> list[str]:
        tags = ["조건 분리", "구할 값 확인"]
        if subject == "math" and "x^2" in text:
            tags.append("꼭짓점 또는 근의 공식")
        if subject == "science":
            tags.extend(["공식 먼저 선택", "단위 확인"])
        tags.append("규칙 풀이 가능" if solvable else "로컬 AI 보완 필요")
        return tags

    def _answer_match(self, left: str | None, right: str | None) -> bool | None:
        if not left or not right:
            return None
        replacements = {"²": "^2", "³": "^3", "㎨": "m/s^2", "㎡": "m^2", "㎥": "m^3", "㎤": "cm^3"}
        l_norm, r_norm = left.lower(), right.lower()
        for source, target in replacements.items():
            l_norm = l_norm.replace(source, target)
            r_norm = r_norm.replace(source, target)
        l_norm = re.sub(r"\s+", "", l_norm).replace("입니다", "")
        r_norm = re.sub(r"\s+", "", r_norm).replace("입니다", "")
        return l_norm == r_norm or l_norm in r_norm or r_norm in l_norm
