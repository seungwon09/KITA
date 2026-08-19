from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ocr import OcrService


def expect_contains(name: str, text: str, expected: list[str], subject: str, unit_part: str) -> bool:
    ocr = OcrService()
    result = ocr.recognize_text(text, base_confidence=0.78)
    missing = [item for item in expected if item not in result.extracted_text]
    ok = (
        not missing
        and result.detected_subject == subject
        and unit_part in (result.detected_unit or "")
        and result.confidence >= 0.72
    )
    if ok:
        print(f"PASS {name} -> {result.extracted_text}")
    else:
        print(
            f"FAIL {name}",
            {
                "text": result.extracted_text,
                "missing": missing,
                "subject": result.detected_subject,
                "unit": result.detected_unit,
                "confidence": result.confidence,
                "warnings": result.warnings,
            },
        )
    return ok


def run() -> int:
    cases = [
        (
            "quadratic_min",
            "이 차 함수 y = X² − 4X + 1 의 최소값을 구 하시오",
            ["이차함수", "y=x^2-4x+1", "최솟값", "구하시오"],
            "math",
            "이차",
        ),
        (
            "quadratic_equation",
            "2X2 - 8X + 6 = O 을 풀 어라",
            ["2x^2-8x+6=0"],
            "math",
            "이차",
        ),
        (
            "easyocr_xa2",
            "y = XA2 4X + 1 minimum value?",
            ["y=x^2-4x+1", "최솟값"],
            "math",
            "이차",
        ),
        (
            "force",
            "질 량 2kg, 가 속도 3m/s2 일 때 힘을 구 하시오",
            ["질량", "2kg", "가속도", "3m/s^2", "힘", "구하시오"],
            "science",
            "힘",
        ),
        (
            "electric_power",
            "전 압 12V 전 류 3A 일때 전 력 P = V I 를 구하시오",
            ["전압", "12V", "전류", "3A", "전력", "P=VI"],
            "science",
            "전기",
        ),
        (
            "density",
            "밀 도 2g/cm3 부 피 5cm3 일 때 질량을 구하시오",
            ["밀도", "2g/cm^3", "부피", "5cm^3", "질량"],
            "science",
            "밀도",
        ),
    ]
    failed = [
        name
        for name, text, expected, subject, unit_part in cases
        if not expect_contains(name, text, expected, subject, unit_part)
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
