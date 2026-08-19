from app.models.schemas import AttemptRecord, ProblemAnalysis, ProblemSolveRequest, SolveResponse
from app.repositories.student_repo import StudentRepository
from app.services.llm import LocalLlmService
from app.services.math_guard import MathGuard
from app.services.math_solver import MathSolver
from app.services.rag import RagService
from app.services.science_solver import ScienceSolver


class ProblemAiService:
    """Routes common problems to deterministic solvers and uncommon ones to the local LLM."""

    def __init__(self) -> None:
        self.rag = RagService()
        self.llm = LocalLlmService()
        self.student_repo = StudentRepository()
        self.math_guard = MathGuard()
        self.math_solver = MathSolver()
        self.science_solver = ScienceSolver()

    async def solve(self, request: ProblemSolveRequest) -> SolveResponse:
        subject = self._subject(request.problem_text, request.subject)
        analysis = self._analyze_with_rules(request.problem_text, subject)
        deterministic = self._deterministic_solve(request.problem_text, subject)
        if deterministic:
            basic_solution, fast_solution, similar_problem, verified_answer = deterministic
            quality_warnings: list[str] = []
            engine, expected_speed = "rules", "instant"
        else:
            references = self.rag.search(request.problem_text)
            generated = await self.llm.generate(self._build_prompt(request, references))
            basic_solution = self._section(generated, "기본 풀이")
            fast_solution = self._section(generated, "빠른 풀이")
            similar_problem = self._section(generated, "비슷한 문제")
            verified_answer, quality_warnings = self.math_guard.verify(
                request.problem_text, f"{basic_solution}\n{fast_solution}"
            )
            note = self.math_guard.corrected_note(verified_answer, quality_warnings)
            if note:
                basic_solution += note
                fast_solution += note
            engine, expected_speed = "local_llm", "normal"

        if request.user_id:
            self.student_repo.save_attempt(
                AttemptRecord(
                    user_id=request.user_id,
                    problem_text=request.problem_text,
                    subject=analysis.subject,
                    unit=analysis.unit,
                    problem_type=analysis.problem_type,
                    difficulty=analysis.difficulty,
                    elapsed_seconds=request.elapsed_seconds,
                    was_correct=request.was_correct,
                )
            )
        return SolveResponse(
            analysis=analysis,
            basic_solution=basic_solution,
            fast_solution=fast_solution,
            wrong_answer_reasons=[
                "문제에서 요구한 값과 중간 계산값을 혼동했을 가능성",
                "부호, 단위 또는 대입 과정에서 실수했을 가능성",
            ],
            similar_problem=similar_problem or "같은 개념에서 숫자를 바꿔 다시 풀어 보세요.",
            tutor_hint="주어진 값, 구할 값, 사용할 공식 순서로 한 줄씩 적어 보세요.",
            recommended_next_action="기본 풀이와 빠른 풀이를 비교한 뒤, 짧은 풀이를 한 번 직접 다시 써 보세요.",
            verified_answer=verified_answer,
            quality_warnings=quality_warnings,
            engine=engine,
            expected_speed=expected_speed,
        )

    def _build_prompt(self, request: ProblemSolveRequest, references: list[dict]) -> str:
        reference_text = "\n".join(f"- {item['title']}: {item['strategy']}" for item in references)
        return f"""
당신은 수학과 과학을 가르치는 한국어 학습 AI입니다.
외부 API 없이 로컬 모델로만 동작합니다.
질문에 필요한 내용만 짧고 정확하게 답하세요.
수식은 읽기 쉬운 일반 텍스트로 적고, 정답을 마지막에 분명히 표시하세요.

과목: {request.subject}
학생 수준: {request.student_level}
문제: {request.problem_text}
학생 풀이: {request.user_solution or "없음"}

참고 전략:
{reference_text or "- 관련 규칙 풀이 없음"}

[기본 풀이]
단계별 풀이

[빠른 풀이]
시험장에서 쓸 가장 짧은 풀이

[오답 이유]
실수하기 쉬운 지점

[비슷한 문제]
숫자만 바꾼 연습 문제
""".strip()

    def _analyze_with_rules(self, text: str, subject: str) -> ProblemAnalysis:
        if subject == "science":
            if any(word in text for word in ["전압", "전류", "전력", "저항"]):
                unit = "물리/전기"
            elif any(word in text for word in ["몰", "몰농도", "화학"]):
                unit = "화학"
            else:
                unit = "물리"
            problem_type = "공식 적용형"
        else:
            if any(word in text for word in ["이차", "x^2", "최솟값", "최댓값"]):
                unit = "이차함수/이차방정식"
            elif any(word in text for word in ["확률", "평균"]):
                unit = "확률과 통계"
            else:
                unit = "수학"
            problem_type = "조건 분석형" if any(word in text for word in ["조건", "최솟값", "최댓값"]) else "일반 풀이형"
        hard = any(word in text for word in ["증명", "킬러", "최댓값", "최솟값"])
        return ProblemAnalysis(
            subject=subject,
            unit=unit,
            problem_type=problem_type,
            difficulty="상" if hard else "중",
            intent="문제 조건을 해석하고 가장 효율적인 풀이 전략을 선택하는 능력 평가",
            is_killer="킬러" in text,
        )

    def _subject(self, text: str, hint: str | None) -> str:
        if hint in {"math", "science"}:
            return hint
        science_words = ["힘", "가속도", "전압", "전류", "전력", "저항", "몰", "파동", "열량", "kg", "m/s"]
        return "science" if any(word in text for word in science_words) else "math"

    def _deterministic_solve(self, text: str, subject: str) -> tuple[str, str, str, str | None] | None:
        if subject == "science":
            return self.science_solver.solve(text) or self.math_solver.solve(text)
        return self.math_solver.solve(text) or self.science_solver.solve(text)

    def _section(self, text: str, title: str) -> str:
        marker = f"[{title}]"
        if marker not in text:
            return text.strip()
        after = text.split(marker, 1)[1].strip()
        positions = [after.find(f"[{next_title}]") for next_title in ["기본 풀이", "빠른 풀이", "오답 이유", "비슷한 문제"]]
        positions = [position for position in positions if position >= 0]
        return after[: min(positions)].strip() if positions else after
