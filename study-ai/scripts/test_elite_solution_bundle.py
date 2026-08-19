from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def run() -> int:
    client = TestClient(app)
    failures = []
    user_id = "elite-solution-test"

    patterns = client.get("/app-ai/elite/patterns")
    patterns_body = patterns.json()
    ok = patterns.status_code == 200 and len(patterns_body) >= 12
    print(("PASS" if ok else "FAIL"), "elite pattern library")
    if not ok:
        print(patterns.status_code, patterns_body)
        failures.append("patterns")

    math_solution = client.post(
        "/app-ai/elite/solution",
        json={
            "user_id": user_id,
            "problem_text": "이차함수 y=x^2-4x+1의 최솟값을 구하시오",
            "subject": "math",
            "elapsed_seconds": 90,
        },
    )
    math_body = math_solution.json()
    ok = (
        math_solution.status_code == 200
        and math_body["verified_answer"] == "-3"
        and math_body["selected_patterns"][0]["id"] == "math_quadratic_extreme"
        and "x=-b/(2a)" in math_body["top_student_solution"]
        and math_body["data_readiness_percent"] >= 75
    )
    print(("PASS" if ok else "FAIL"), "elite math solution")
    if not ok:
        print(math_solution.status_code, math_body)
        failures.append("math-solution")

    science_solution = client.post(
        "/app-ai/elite/solution",
        json={
            "user_id": user_id,
            "problem_text": "저항 4Ω에 전류 3A가 흐를 때 전압과 전력을 각각 구하시오",
            "subject": "science",
        },
    )
    science_body = science_solution.json()
    ok = (
        science_solution.status_code == 200
        and science_body["verified_answer"] == "12V, 36W"
        and science_body["selected_patterns"][0]["id"] == "science_circuit_combo"
        and science_body["time_target_seconds"] <= 24
    )
    print(("PASS" if ok else "FAIL"), "elite science solution")
    if not ok:
        print(science_solution.status_code, science_body)
        failures.append("science-solution")

    sample = client.post(
        "/app-ai/elite/sample",
        json={
            "user_id": user_id,
            "problem_text": "이차함수 y=x^2-4x+1의 최솟값을 구하시오",
            "subject": "math",
            "solution_text": "x=-b/(2a)=2만 보고 y=-3",
            "verified_answer": "-3",
            "source_level": "top_1_percent",
            "elapsed_seconds": 14,
            "tags": ["math_quadratic_extreme", "vertex", "exam_shortcut"],
        },
    )
    sample_body = sample.json()
    ok = sample.status_code == 200 and sample_body["saved"] is True
    print(("PASS" if ok else "FAIL"), "elite sample save")
    if not ok:
        print(sample.status_code, sample_body)
        failures.append("sample")

    sample_list = client.get(f"/app-ai/elite/samples/{user_id}")
    list_body = sample_list.json()
    ok = sample_list.status_code == 200 and len(list_body) >= 1
    print(("PASS" if ok else "FAIL"), "elite sample list")
    if not ok:
        print(sample_list.status_code, list_body)
        failures.append("sample-list")

    stats = client.get("/app-ai/elite/stats")
    stats_body = stats.json()
    ok = stats.status_code == 200 and stats_body["readiness_percent"] >= 75 and stats_body["total_samples"] >= 1
    print(("PASS" if ok else "FAIL"), "elite stats")
    if not ok:
        print(stats.status_code, stats_body)
        failures.append("stats")

    production = client.post(
        "/app-ai/production/action",
        json={
            "action": "elite_solution",
            "user_id": user_id,
            "plan": "premium",
            "subject": "math",
            "problem_text": "이차함수 y=x^2-4x+1의 최솟값을 구하시오",
        },
    )
    production_body = production.json()
    ok = (
        production.status_code == 200
        and production_body["allowed"] is True
        and production_body["result"]["verified_answer"] == "-3"
    )
    print(("PASS" if ok else "FAIL"), "production elite action")
    if not ok:
        print(production.status_code, production_body)
        failures.append("production")

    roadmap = client.get("/app-ai/roadmap/status")
    roadmap_body = roadmap.json()
    elite = next(item for item in roadmap_body["features"] if item["id"] == 8)
    ok = roadmap.status_code == 200 and elite["completion_percent"] >= 75 and elite["production_action"] == "elite_patterns"
    print(("PASS" if ok else "FAIL"), "roadmap elite progress")
    if not ok:
        print(roadmap.status_code, elite)
        failures.append("roadmap")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
