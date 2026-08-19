from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.math_solver import MathSolver
from app.services.ocr import OcrService
from app.services.science_solver import ScienceSolver


def run() -> int:
    failures: list[str] = []
    math = MathSolver()
    science = ScienceSolver()

    cases = [
        (math, "두 점 (1,2), (4,6) 사이의 거리를 구하시오", "5"),
        (math, "첫째항 3, 공차 2인 등차수열의 10번째 항까지의 합을 구하시오", "120"),
        (math, "첫째항 2, 공비 3인 등비수열의 4번째 항까지의 합을 구하시오", "80"),
        (math, "2x+3<11을 풀어라", "x<4"),
        (math, "-2x+4>10을 풀어라", "x<-3"),
        (science, "진동수 5Hz인 파동의 주기를 구하시오", "0.2s"),
        (science, "주기 0.25s인 파동의 진동수를 구하시오", "4Hz"),
        (science, "질량 3kg인 물체가 4m/s로 움직일 때 운동량을 구하시오", "12kg·m/s"),
        (science, "힘 6N이 3초 동안 작용할 때 충격량을 구하시오", "18N·s"),
        (science, "전력 60W인 기기를 2분 동안 사용할 때 전기에너지를 구하시오", "7200J"),
        (science, "용질 10g이 들어 있는 용액 200g의 질량 퍼센트 농도를 구하시오", "5%"),
    ]

    for solver, problem, expected in cases:
        result = solver.solve(problem)
        ok = result is not None and result[3] == expected
        print(("PASS" if ok else "FAIL"), expected, "::", problem)
        if not ok:
            print(result)
            failures.append(problem)

    normalized, _ = OcrService()._normalize_text("이 차 함수 y = X² - 4X + 1 의 최소값")
    ocr_ok = "이차함수" in normalized and "y=x^2-4x+1" in normalized.lower() and "최솟값" in normalized
    print(("PASS" if ocr_ok else "FAIL"), "ocr quadratic normalization")
    if not ocr_ok:
        print(normalized)
        failures.append("ocr")

    client = TestClient(app)
    api = client.post(
        "/solve",
        json={
            "user_id": "release-solver-test",
            "problem_text": "전력 60W인 기기를 2분 동안 사용할 때 전기에너지를 구하시오",
            "subject": "science",
        },
    )
    body = api.json()
    api_ok = api.status_code == 200 and body["verified_answer"] == "7200J" and body["engine"] == "rules"
    print(("PASS" if api_ok else "FAIL"), "API electrical energy")
    if not api_ok:
        print(api.status_code, body)
        failures.append("api")

    print(f"RESULT {len(cases) + 2 - len(failures)}/{len(cases) + 2}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
