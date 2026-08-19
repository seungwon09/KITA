from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.math_solver import MathSolver
from app.services.science_solver import ScienceSolver
from app.main import app


def run() -> int:
    math = MathSolver()
    science = ScienceSolver()
    cases = [
        (math, "이차함수 y=2x^2-8x+1의 최솟값을 구하시오", "-7"),
        (math, "이차함수 y=-x^2+4x+1의 최댓값을 구하시오", "5"),
        (math, "이차함수 y=x^2-4x+1의 축의 방정식을 구하시오", "x=2"),
        (math, "2x^2-8x+6=0을 풀어라", "x=1 또는 x=3"),
        (math, "x^2+2x+5=0을 풀어라", "실근 없음"),
        (math, "3x+2=2x+7을 풀어라", "x=5"),
        (math, "f(x)=x^2-4x+1일 때 f(3)을 구하시오", "-2"),
        (science, "질량 2kg, 가속도 3m/s^2일 때 힘을 구하시오", "6N"),
        (science, "힘 12N, 질량 4kg일 때 가속도를 구하시오", "3m/s^2"),
        (science, "전압 12V, 전류 3A일 때 전력을 구하시오", "36W"),
        (science, "전력 60W, 전압 12V일 때 전류를 구하시오", "5A"),
        (science, "전압 12V, 전류 3A일 때 저항을 구하시오", "4Ω"),
        (science, "거리 100m, 시간 20초일 때 속력을 구하시오", "5m/s"),
        (science, "밀도 2g/cm^3, 부피 5cm^3일 때 질량을 구하시오", "10g"),
        (science, "일 30J, 힘 10N일 때 이동거리를 구하시오", "3m"),
    ]

    failures = []
    for solver, problem, expected in cases:
        result = solver.solve(problem)
        combined = "" if result is None else "\n".join(str(item) for item in result if item is not None)
        if expected in combined:
            print(f"PASS {expected} :: {problem}")
        else:
            print(f"FAIL {expected} :: {problem}")
            print(combined)
            failures.append(problem)

    try:
        from fastapi.testclient import TestClient

        client = TestClient(app)
        api_cases = [
            (
                {
                    "user_id": "accuracy-test",
                    "problem_text": "이차함수 y=2x^2-8x+1의 최솟값을 구하시오",
                    "subject": "math",
                    "student_level": "intermediate",
                    "mode": "compare",
                    "elapsed_seconds": 90,
                    "was_correct": True,
                },
                "-7",
            ),
            (
                {
                    "user_id": "accuracy-test",
                    "problem_text": "전력 60W, 전압 12V일 때 전류를 구하시오",
                    "subject": "science",
                    "student_level": "intermediate",
                    "mode": "compare",
                    "elapsed_seconds": 45,
                    "was_correct": True,
                },
                "5A",
            ),
        ]
        for payload, expected in api_cases:
            response = client.post("/solve", json=payload)
            body = response.json()
            combined = "\n".join(str(value) for value in body.values())
            if response.status_code == 200 and expected in combined:
                print(f"PASS API {expected} :: {payload['problem_text']}")
            else:
                print(f"FAIL API {expected} :: {payload['problem_text']}")
                print(response.status_code, body)
                failures.append(payload["problem_text"])
    except Exception as exc:
        print(f"FAIL API smoke :: {exc}")
        failures.append("api-smoke")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
