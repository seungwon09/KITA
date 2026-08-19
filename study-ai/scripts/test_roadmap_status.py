from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    response = client.get("/app-ai/roadmap/status")
    body = response.json()
    ok = (
        response.status_code == 200
        and body["total_features"] == 30
        and body["ready_count"] >= 15
        and body["backend_average_percent"] >= 60
        and body["app_integration_ready"] is True
    )
    print(("PASS" if ok else "FAIL"), "roadmap status")
    if not ok:
        print(response.status_code, body)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
