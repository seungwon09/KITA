import re

from app.services.math_solver import MathSolver


class MathGuard:
    """Checks a few high-risk math answers before they are shown."""

    def __init__(self) -> None:
        self.solver = MathSolver()

    def verify(self, problem_text: str, solution_text: str) -> tuple[str | None, list[str]]:
        warnings: list[str] = []
        compact = solution_text.replace(" ", "")
        if "b/2a" in compact and "-b/(2a)" not in compact and "-b/2a" not in compact:
            warnings.append("이차함수 꼭짓점 공식은 b/2a가 아니라 -b/(2a)입니다.")
        solved = self.solver.solve(problem_text)
        verified_answer = solved[3] if solved else None
        if verified_answer and verified_answer not in solution_text:
            warnings.append(f"규칙 검산 결과 정답은 {verified_answer}입니다.")
        return verified_answer, warnings

    def corrected_note(self, verified_answer: str | None, warnings: list[str]) -> str:
        if not verified_answer or not warnings:
            return ""
        return f"\n\n[자동 검산]\n검산된 정답은 {verified_answer}입니다. 이 값을 기준으로 풀이를 확인하세요."

    def _extract_final_answer(self, text: str) -> str | None:
        matches = re.findall(r"(?:정답|답|최솟값|최댓값)[^\d-]*(-?\d+(?:\.\d+)?)", text)
        return matches[-1] if matches else None
