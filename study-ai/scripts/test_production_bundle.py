from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    user_id = "production-bundle-test"
    failures = []

    status = client.get("/app-ai/production/status")
    status_body = status.json()
    if status.status_code == 200 and status_body["ok"] and status_body["feature_count"] >= 20:
        print("PASS production status")
    else:
        print("FAIL production status", status.status_code, status_body)
        failures.append("status")

    registry = client.get("/app-ai/production/registry")
    registry_body = registry.json()
    actions = {item["action"] for item in registry_body.get("features", [])}
    required = {"solve", "mobile_analyze", "personalization", "training_queue", "targeted_practice", "plans"}
    if registry.status_code == 200 and required.issubset(actions):
        print("PASS production registry")
    else:
        print("FAIL production registry", registry.status_code, sorted(actions))
        failures.append("registry")

    action_cases = [
        (
            {
                "action": "solve",
                "user_id": user_id,
                "plan": "free",
                "subject": "math",
                "problem_text": "이차함수 y=2x^2-8x+1의 최솟값을 구하시오",
                "elapsed_seconds": 80,
                "was_correct": True,
            },
            "solution",
        ),
        (
            {
                "action": "mobile_analyze",
                "user_id": user_id,
                "plan": "basic",
                "subject": "science",
                "problem_text": "전력 60W, 전압 12V일 때 전류를 구하시오",
                "elapsed_seconds": 45,
                "was_correct": True,
            },
            "appAiResult",
        ),
        (
            {
                "action": "training_queue",
                "user_id": user_id,
                "plan": "pro",
                "subject": "mixed",
                "count": 6,
            },
            "practiceSet",
        ),
    ]
    for payload, target in action_cases:
        response = client.post("/app-ai/production/action", json=payload)
        body = response.json()
        ok = response.status_code == 200 and body["allowed"] is True and body["ui_target"] == target
        print(("PASS" if ok else "FAIL"), f"production action {payload['action']}")
        if not ok:
            print(response.status_code, body)
            failures.append(payload["action"])

    locked = client.post(
        "/app-ai/production/action",
        json={
            "action": "training_queue",
            "user_id": user_id,
            "plan": "free",
            "subject": "mixed",
        },
    )
    locked_body = locked.json()
    if locked.status_code == 200 and locked_body["allowed"] is False:
        print("PASS production action gate")
    else:
        print("FAIL production action gate", locked.status_code, locked_body)
        failures.append("gate")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
