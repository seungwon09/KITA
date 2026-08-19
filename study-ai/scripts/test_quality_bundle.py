from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.services.ocr import OcrService


def run() -> int:
    failed = []
    client = TestClient(app)

    ocr = OcrService()
    normalized, corrections = ocr._normalize_text("이 차 함수 y = X² − 4X + 1 의 최소값")
    if "이차함수" in normalized and "x^2" in normalized.lower() and "최솟값" in normalized:
        print("PASS ocr normalization")
    else:
        print("FAIL ocr normalization", normalized, corrections)
        failed.append("ocr")

    targeted = client.get("/students/quality-bundle-test/targeted-practice?subject=mixed&count=8")
    body = targeted.json()
    if targeted.status_code == 200 and len(body["problems"]) >= 5:
        print("PASS targeted practice")
    else:
        print("FAIL targeted practice", targeted.status_code, body)
        failed.append("targeted")

    gate = client.post(
        "/app-ai/gate",
        json={
            "user_id": "quality-bundle-test",
            "plan": "free",
            "feature": "ocr_analyze",
        },
    )
    gate_body = gate.json()
    if gate.status_code == 200 and gate_body["allowed"] is False and gate_body["upgrade_to"]:
        print("PASS plan gate")
    else:
        print("FAIL plan gate", gate.status_code, gate_body)
        failed.append("gate")

    plans = client.get("/app-ai/plans")
    plan_body = plans.json()
    if plans.status_code == 200 and any("ocr_analyze" in plan["features"] for plan in plan_body["plans"]):
        print("PASS plan catalog")
    else:
        print("FAIL plan catalog", plans.status_code, plan_body)
        failed.append("plans")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
