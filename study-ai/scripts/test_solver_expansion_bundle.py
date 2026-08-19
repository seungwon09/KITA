from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.math_solver import MathSolver
from app.services.science_solver import ScienceSolver


def run() -> int:
    failures = []
    math_cases = [
        ("직각삼각형의 두 변이 3, 4일 때 빗변의 길이를 구하시오", "5"),
        ("두 점 (1,2), (3,6)을 지나는 직선의 기울기를 구하시오", "2"),
        ("첫째항 3, 공차 2인 등차수열의 10번째 항을 구하시오", "21"),
        ("첫째항 2, 공비 3인 등비수열의 4번째 항을 구하시오", "54"),
        ("150의 20%를 구하시오", "30"),
    ]
    math_solver = MathSolver()
    for problem, expected in math_cases:
        result = math_solver.solve(problem)
        ok = result is not None and result[3] == expected
        print(("PASS" if ok else "FAIL"), expected, "::", problem)
        if not ok:
            print(result)
            failures.append(problem)

    science_cases = [
        ("저항 4Ω에 전류 3A가 흐를 때 전압과 전력을 각각 구하시오", "12V, 36W"),
        ("속도가 2m/s에서 10m/s로 4초 동안 변할 때 가속도를 구하시오", "2m/s^2"),
        ("비열 4.2J/g도, 질량 100g, 온도변화 5도일 때 열량을 구하시오", "2100J"),
        ("파장 2m, 진동수 3Hz인 파동의 속력을 구하시오", "6m/s"),
    ]
    science_solver = ScienceSolver()
    for problem, expected in science_cases:
        result = science_solver.solve(problem)
        ok = result is not None and result[3] == expected
        print(("PASS" if ok else "FAIL"), expected, "::", problem)
        if not ok:
            print(result)
            failures.append(problem)

    client = TestClient(app)
    api = client.post(
        "/solve",
        json={
            "user_id": "solver-expansion-test",
            "problem_text": "직각삼각형의 두 변이 3, 4일 때 빗변의 길이를 구하시오",
            "subject": "math",
            "elapsed_seconds": 25,
            "was_correct": True,
        },
    )
    api_body = api.json()
    ok = api.status_code == 200 and api_body["verified_answer"] == "5"
    print(("PASS" if ok else "FAIL"), "API pythagorean")
    if not ok:
        print(api.status_code, api_body)
        failures.append("api")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
