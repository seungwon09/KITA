from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    user_id = "personalization-test"
    attempts = [
        ("이차함수 y=2x^2-8x+1의 최솟값을 구하시오", "math", False, 210),
        ("이차함수 y=x^2-4x+1의 축의 방정식을 구하시오", "math", False, 190),
        ("전력 60W, 전압 12V일 때 전류를 구하시오", "science", True, 70),
        ("질량 2kg, 가속도 3m/s^2일 때 힘을 구하시오", "science", True, 55),
    ]

    for problem, subject, was_correct, elapsed in attempts:
        response = client.post(
            "/solve",
            json={
                "user_id": user_id,
                "problem_text": problem,
                "subject": subject,
                "student_level": "intermediate",
                "mode": "compare",
                "was_correct": was_correct,
                "elapsed_seconds": elapsed,
            },
        )
        if response.status_code != 200:
            print("FAIL solve", response.status_code, response.text)
            return 1

    checks = [
        (f"/app-ai/personalization/{user_id}", "skill_profiles"),
        (f"/app-ai/training-queue/{user_id}?subject=mixed&count=6", "items"),
        (f"/app-ai/weakness-deep-dive/{user_id}", "root_causes"),
    ]
    failed = False
    for path, key in checks:
        response = client.get(path)
        body = response.json()
        ok = response.status_code == 200 and key in body and body[key]
        print(("PASS" if ok else "FAIL"), path)
        if not ok:
            print(response.status_code, body)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
