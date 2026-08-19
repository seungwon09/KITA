import json
from pathlib import Path


class RagService:
    def __init__(self) -> None:
        data_path = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
        self.items = json.loads(data_path.read_text(encoding="utf-8"))

    def search(self, problem_text: str, limit: int = 3) -> list[dict]:
        scored = []
        for item in self.items:
            score = sum(1 for keyword in item["keywords"] if keyword in problem_text)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [item for _, item in scored[:limit]]
