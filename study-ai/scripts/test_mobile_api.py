from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    user_id = "mobile-api-test"
    failures = []

    config = client.get("/app-ai/mobile/config")
    if config.status_code == 200 and "analyze_text" in config.json()["endpoints"]:
        print("PASS mobile config")
    else:
        print("FAIL mobile config", config.status_code, config.text)
        failures.append("config")

    bootstrap = client.get(f"/app-ai/mobile/bootstrap/{user_id}?plan=pro")
    if bootstrap.status_code == 200 and bootstrap.json()["session"]["user_id"] == user_id:
        print("PASS mobile bootstrap")
    else:
        print("FAIL mobile bootstrap", bootstrap.status_code, bootstrap.text)
        failures.append("bootstrap")

    analyze = client.post(
        "/app-ai/mobile/analyze",
        json={
            "user_id": user_id,
            "problem_text": "전력 60W, 전압 12V일 때 전류를 구하시오",
            "subject": "science",
            "plan": "pro",
            "student_level": "intermediate",
            "elapsed_seconds": 45,
            "was_correct": True,
            "time_limit_seconds": 90,
            "include_practice": True,
            "include_home": True,
            "include_personalization": True,
            "include_training_queue": True,
        },
    )
    body = analyze.json()
    if analyze.status_code == 200 and body["analyze"]["solve"]["verified_answer"] == "5A":
        print("PASS mobile analyze")
    else:
        print("FAIL mobile analyze", analyze.status_code, body)
        failures.append("analyze")

    preflight = client.options(
        "/app-ai/mobile/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    if preflight.status_code in {200, 204} and "access-control-allow-origin" in preflight.headers:
        print("PASS cors preflight")
    else:
        print("FAIL cors preflight", preflight.status_code, dict(preflight.headers))
        failures.append("cors")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
