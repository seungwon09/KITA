from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    failures = []
    user_id = "backend-completion-test"

    recognition = client.post(
        "/app-ai/problem/recognize",
        json={
            "user_id": user_id,
            "problem_text": "이 차 함수 y = X² - 4X + 1 의 최소값을 구하시오",
            "subject": "auto",
            "source": "test",
        },
    )
    body = recognition.json()
    ok = (
        recognition.status_code == 200
        and body["detected_subject"] == "math"
        and body["solvable_by_rules"] is True
        and body["verified_answer"] == "-3"
        and "y=x^2-4x+1" in body["normalized_text"]
    )
    print(("PASS" if ok else "FAIL"), "problem recognition")
    if not ok:
        print(recognition.status_code, body)
        failures.append("recognition")

    quality = client.post(
        "/app-ai/quality/check",
        json={
            "user_id": user_id,
            "problem_text": "전력 60W, 전압 12V일 때 전류를 구하시오",
            "subject": "science",
            "expected_answer": "5A",
            "student_answer": "5A",
            "elapsed_seconds": 45,
        },
    )
    quality_body = quality.json()
    ok = (
        quality.status_code == 200
        and quality_body["verified_answer"] == "5A"
        and quality_body["student_answer_match"] is True
        and quality_body["solver_engine"] == "rules"
    )
    print(("PASS" if ok else "FAIL"), "quality check")
    if not ok:
        print(quality.status_code, quality_body)
        failures.append("quality")

    correction = client.post(
        "/app-ai/ocr/correction",
        json={
            "user_id": user_id,
            "raw_text": "y=XA2 4X+1",
            "extracted_text": "y=XA2 4X+1",
            "corrected_text": "y=x^2-4x+1",
            "detected_subject": "math",
            "confidence": 0.71,
            "source": "test",
        },
    )
    correction_body = correction.json()
    ok = correction.status_code == 200 and correction_body["saved"] is True
    print(("PASS" if ok else "FAIL"), "ocr correction save")
    if not ok:
        print(correction.status_code, correction_body)
        failures.append("correction")

    correction_list = client.get(f"/app-ai/ocr/corrections/{user_id}")
    list_body = correction_list.json()
    ok = correction_list.status_code == 200 and len(list_body) >= 1
    print(("PASS" if ok else "FAIL"), "ocr correction list")
    if not ok:
        print(correction_list.status_code, list_body)
        failures.append("correction-list")

    stats = client.get("/app-ai/ocr/stats")
    stats_body = stats.json()
    ok = stats.status_code == 200 and stats_body["total_corrections"] >= 1
    print(("PASS" if ok else "FAIL"), "ocr correction stats")
    if not ok:
        print(stats.status_code, stats_body)
        failures.append("stats")

    production = client.post(
        "/app-ai/production/action",
        json={
            "action": "quality_check",
            "user_id": user_id,
            "plan": "basic",
            "subject": "science",
            "problem_text": "질량 2kg, 가속도 3m/s^2일 때 힘을 구하시오",
            "payload": {"expected_answer": "6N", "student_answer": "6N"},
        },
    )
    production_body = production.json()
    ok = (
        production.status_code == 200
        and production_body["allowed"] is True
        and production_body["result"]["verified_answer"] == "6N"
    )
    print(("PASS" if ok else "FAIL"), "production quality action")
    if not ok:
        print(production.status_code, production_body)
        failures.append("production-quality")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
