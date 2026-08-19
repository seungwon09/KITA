import re
from collections import defaultdict
from uuid import uuid4

from app.models.schemas import (
    AnswerCheckRequest,
    AnswerCheckResponse,
    AttemptRecord,
    DiagnosticAnswerInput,
    DiagnosticQuestion,
    DiagnosticResultItem,
    DiagnosticStartRequest,
    DiagnosticStartResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    ErrorTaxonomyItem,
    ErrorTaxonomyResponse,
    FlashcardItem,
    FlashcardResponse,
    MasteryMapResponse,
    MasteryUnit,
    MistakeNotebookGroup,
    MistakeNotebookResponse,
    MockExamStartRequest,
    MockExamStartResponse,
    MockExamSubmitRequest,
    MockExamSubmitResponse,
    PersonalizedTrainingQueueResponse,
    ProblemSolveRequest,
    SkillProfile,
    SolutionVariantsRequest,
    SolutionVariantsResponse,
    StudentPersonalizationResponse,
    TrainingQueueItem,
    TutorHintRequest,
    TutorHintResponse,
    WeaknessDeepDiveResponse,
    WeeklyPlanDay,
    WeeklyPlanResponse,
)
from app.repositories.student_repo import StudentRepository
from app.services.problem_ai import ProblemAiService
from app.services.problem_generator import ProblemGeneratorService


class LearningIntelligenceService:
    def __init__(
        self,
        student_repo: StudentRepository,
        problem_ai: ProblemAiService,
        problem_generator: ProblemGeneratorService,
    ) -> None:
        self.student_repo = student_repo
        self.problem_ai = problem_ai
        self.problem_generator = problem_generator

    def mastery_map(self, user_id: str) -> MasteryMapResponse:
        attempts = self.student_repo.list_attempts(user_id, limit=100)
        grouped: dict[str, list] = defaultdict(list)
        for item in attempts:
            grouped[item.unit].append(item)

        if not grouped:
            units = [
                MasteryUnit(
                    unit="함수/이차함수",
                    total_attempts=0,
                    accuracy_percent=0,
                    average_seconds=None,
                    mastery_score=0,
                    level="진단 전",
                    next_action="진단 테스트 또는 기본 문제 3개 풀이",
                ),
                MasteryUnit(
                    unit="물리",
                    total_attempts=0,
                    accuracy_percent=0,
                    average_seconds=None,
                    mastery_score=0,
                    level="진단 전",
                    next_action="공식 적용형 문제 3개 풀이",
                ),
            ]
        else:
            units = [self._mastery_for_unit(unit, rows) for unit, rows in grouped.items()]
            units.sort(key=lambda item: item.mastery_score)

        weakest = units[0].unit
        strongest = units[-1].unit
        return MasteryMapResponse(
            user_id=user_id,
            units=units,
            strongest_unit=strongest,
            weakest_unit=weakest,
            message=f"가장 먼저 올릴 단원은 {weakest}입니다.",
        )

    def personalization_dashboard(self, user_id: str) -> StudentPersonalizationResponse:
        profiles = self._skill_profiles(user_id)
        progress = self.student_repo.get_progress(user_id)

        strongest = [
            f"{item.unit} · {item.problem_type}"
            for item in sorted(profiles, key=lambda profile: profile.mastery_score, reverse=True)
            if item.mastery_score >= 70
        ][:3] or ["아직 강점 데이터 부족"]
        weakest = [
            f"{item.unit} · {item.problem_type}"
            for item in sorted(profiles, key=lambda profile: profile.weakness_score, reverse=True)
            if item.weakness_score >= 35
        ][:4] or ["약점 판단 전"]
        risk_flags = self._risk_flags(profiles, progress.total_attempts)
        learner_stage = self._learner_stage(progress.total_attempts, progress.accuracy_percent, progress.average_elapsed_seconds)
        top_focus = weakest[0]

        return StudentPersonalizationResponse(
            user_id=user_id,
            learner_stage=learner_stage,
            total_attempts=progress.total_attempts,
            overall_accuracy_percent=progress.accuracy_percent,
            average_seconds=progress.average_elapsed_seconds,
            strongest_skills=strongest,
            weakest_skills=weakest,
            risk_flags=risk_flags,
            skill_profiles=profiles,
            today_focus=top_focus,
            next_best_actions=self._next_best_actions(profiles, learner_stage),
            routing_rules=[
                "정답률 60% 미만 유형은 기본 풀이부터 보여줍니다.",
                "평균 150초 이상 유형은 빠른 풀이와 시간 단축 훈련으로 보냅니다.",
                "숙련도 75점 이상 유형은 한 단계 어려운 문제로 올립니다.",
                "오답과 시간 초과가 겹친 유형은 복습 큐 맨 앞으로 보냅니다.",
            ],
        )

    def personalized_training_queue(
        self,
        user_id: str,
        subject: str = "mixed",
        count: int = 8,
    ) -> PersonalizedTrainingQueueResponse:
        profiles = self._skill_profiles(user_id)
        if subject in {"math", "science"}:
            profiles = [profile for profile in profiles if profile.subject == subject] or profiles
        ranked = sorted(profiles, key=lambda profile: profile.weakness_score, reverse=True)
        if not ranked:
            ranked = self._starter_profiles()

        items: list[TrainingQueueItem] = []
        seen: set[str] = set()
        for profile in ranked:
            if len(items) >= count:
                break
            difficulty, mode, target_seconds = self._queue_strategy(profile)
            unit_key = self._generator_unit_key(profile)
            generated = self.problem_generator.generate_set(
                subject=profile.subject if profile.subject in {"math", "science"} else "math",
                difficulty=difficulty,
                count=3,
                unit=unit_key,
            )
            for problem in generated.problems:
                if problem.problem in seen:
                    continue
                seen.add(problem.problem)
                items.append(
                    TrainingQueueItem(
                        problem=problem.problem,
                        subject=problem.subject,
                        unit=problem.unit,
                        difficulty=problem.difficulty,
                        mode=mode,
                        target_seconds=target_seconds,
                        reason=f"{profile.unit} · {profile.problem_type} 약점 점수 {profile.weakness_score}",
                        expected_benefit=profile.next_action,
                    )
                )
                if len(items) >= count:
                    break

        return PersonalizedTrainingQueueResponse(
            user_id=user_id,
            queue_title="오늘 맞춤 훈련 큐",
            estimated_minutes=max(8, len(items) * 3),
            items=items,
            finish_rule="정답률 70% 이상 또는 시간 초과 2개 이하이면 다음 난이도로 이동",
        )

    def weakness_deep_dive(
        self,
        user_id: str,
        target: str | None = None,
    ) -> WeaknessDeepDiveResponse:
        profiles = self._skill_profiles(user_id)
        if target:
            matched = [
                profile for profile in profiles
                if target in profile.unit or target in profile.problem_type
            ]
        else:
            matched = []
        profile = (
            sorted(matched, key=lambda item: item.weakness_score, reverse=True)[0]
            if matched
            else sorted(profiles, key=lambda item: item.weakness_score, reverse=True)[0]
        )

        root_causes = []
        if profile.attempts < 3:
            root_causes.append("기록이 적어서 아직 안정적인 패턴이 아닙니다.")
        if profile.accuracy_percent < 60:
            root_causes.append("정답률이 낮아 개념 조건을 끝까지 반영하지 못했을 가능성이 큽니다.")
        if profile.average_seconds and profile.average_seconds >= 150:
            root_causes.append("풀이 방향 선택이 늦거나 계산량을 줄이는 전략이 부족합니다.")
        if profile.wrong_attempts >= 2 and profile.recent_average_seconds:
            root_causes.append("최근에도 같은 유형에서 오답/지연이 반복되고 있습니다.")
        if not root_causes:
            root_causes.append("큰 위험은 아니지만 상위 난이도 전환 전 검산 습관을 확인해야 합니다.")

        target_name = f"{profile.unit} · {profile.problem_type}"
        drills = [
            f"{target_name} 기본 풀이 2문제",
            f"{target_name} 숫자만 바꾼 재풀이 2문제",
            "빠른 풀이를 읽고 같은 문제를 제한 시간 안에 다시 풀기",
            "마지막 답을 원식/공식에 대입해 검산하기",
        ]
        return WeaknessDeepDiveResponse(
            user_id=user_id,
            target=target_name,
            root_causes=root_causes,
            evidence=profile.evidence,
            drills=drills,
            success_metric="다음 5문제에서 정답률 80% 이상, 평균 120초 이하",
            escalation_rule="성공하면 한 단계 어려운 문제, 실패하면 개념 압축과 힌트 모드로 복귀",
        )

    def start_diagnostic(self, request: DiagnosticStartRequest) -> DiagnosticStartResponse:
        subject = request.subject
        count = request.count
        questions: list[DiagnosticQuestion] = []

        if subject == "math":
            sets = [self.problem_generator.generate_set("math", request.difficulty, count)]
        elif subject == "science":
            sets = [self.problem_generator.generate_set("science", request.difficulty, count)]
        else:
            math_count = max(1, count // 2)
            science_count = max(1, count - math_count)
            sets = [
                self.problem_generator.generate_set("math", request.difficulty, math_count),
                self.problem_generator.generate_set("science", request.difficulty, science_count),
            ]

        index = 1
        for problem_set in sets:
            for problem in problem_set.problems:
                questions.append(
                    DiagnosticQuestion(
                        question_id=f"q{index}",
                        problem=problem.problem,
                        subject=problem.subject,
                        unit=problem.unit,
                        difficulty=problem.difficulty,
                        target_skill=problem.target_skill,
                        expected_answer=problem.expected_answer,
                    )
                )
                index += 1

        return DiagnosticStartResponse(
            diagnostic_id=str(uuid4()),
            questions=questions[:count],
            time_limit_minutes=max(10, count * 2),
            instructions=[
                "모르는 문제는 오래 붙잡지 말고 다음 문제로 넘기세요.",
                "답만 적어도 채점됩니다.",
                "진단 결과는 단원 숙련도와 주간 계획에 반영됩니다.",
            ],
        )

    def submit_diagnostic(self, request: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
        results: list[DiagnosticResultItem] = []
        unit_correct: dict[str, int] = defaultdict(int)
        unit_total: dict[str, int] = defaultdict(int)

        for answer in request.answers:
            correct = self._answer_matches(answer.student_answer, answer.expected_answer)
            unit_total[answer.unit] += 1
            if correct:
                unit_correct[answer.unit] += 1
            self.student_repo.save_attempt(
                AttemptRecord(
                    user_id=request.user_id,
                    problem_text=answer.problem,
                    subject=answer.subject,
                    unit=answer.unit,
                    problem_type=answer.target_skill,
                    difficulty="진단",
                    elapsed_seconds=answer.elapsed_seconds,
                    was_correct=correct,
                )
            )
            results.append(
                DiagnosticResultItem(
                    question_id=answer.question_id,
                    correct=correct,
                    expected_answer=answer.expected_answer,
                    student_answer=answer.student_answer,
                    unit=answer.unit,
                    target_skill=answer.target_skill,
                    feedback="정답" if correct else "답 또는 핵심 숫자가 다릅니다. 기본 풀이로 다시 확인하세요.",
                )
            )

        total = len(results)
        correct_count = sum(1 for item in results if item.correct)
        score = round((correct_count / total) * 100, 1) if total else 0.0
        placement = "advanced" if score >= 80 else "intermediate" if score >= 50 else "beginner"
        weak_units = [
            unit for unit, total_count in unit_total.items()
            if unit_correct[unit] / total_count < 0.7
        ] or ["약점 단원 없음"]
        strong_units = [
            unit for unit, total_count in unit_total.items()
            if unit_correct[unit] / total_count >= 0.8
        ] or ["강점 단원 데이터 부족"]
        recommended = (
            f"{weak_units[0]} 기본 개념부터 시작"
            if weak_units[0] != "약점 단원 없음"
            else "상위 난이도 문제로 이동"
        )
        return DiagnosticSubmitResponse(
            user_id=request.user_id,
            diagnostic_id=request.diagnostic_id,
            score_percent=score,
            placement=placement,
            weak_units=weak_units,
            strong_units=strong_units,
            results=results,
            recommended_start=recommended,
        )

    async def solution_variants(self, request: SolutionVariantsRequest) -> SolutionVariantsResponse:
        solve = await self.problem_ai.solve(
            ProblemSolveRequest(
                problem_text=request.problem_text,
                subject=request.subject,
                student_level=request.student_level,
            )
        )
        answer = solve.verified_answer or "검산 답 없음"
        beginner = (
            "초보 풀이:\n"
            "1. 문제에서 구하라는 값을 먼저 표시합니다.\n"
            "2. 주어진 숫자와 조건을 한 줄로 정리합니다.\n"
            f"3. 다음 풀이를 천천히 따라갑니다.\n{solve.basic_solution}"
        )
        exam = (
            "시험장 풀이:\n"
            f"{solve.fast_solution}\n"
            f"마지막에 답 {answer}만 빠르게 검산합니다."
        )
        top_student = (
            "상위권 풀이:\n"
            "유형을 먼저 판별하고, 계산량이 적은 공식/대입/그래프 접근을 고릅니다.\n"
            f"이 문제는 {solve.analysis.problem_type}이므로 핵심은 {solve.analysis.unit} 조건을 빠르게 잡는 것입니다.\n"
            f"결론: {answer}"
        )
        return SolutionVariantsResponse(
            problem_text=request.problem_text,
            verified_answer=solve.verified_answer,
            beginner_solution=beginner,
            standard_solution=solve.basic_solution,
            fast_solution=solve.fast_solution,
            exam_solution=exam,
            top_student_solution=top_student,
        )

    async def tutor_hint(self, request: TutorHintRequest) -> TutorHintResponse:
        solve = await self.problem_ai.solve(
            ProblemSolveRequest(problem_text=request.problem_text, subject=request.subject)
        )
        hints = [
            f"이 문제는 {solve.analysis.unit}의 {solve.analysis.problem_type}입니다. 먼저 구해야 하는 값을 한 줄로 쓰세요.",
            "주어진 숫자와 조건을 공식 또는 식에 맞게 나눠 적어보세요.",
            f"빠른 접근은 이겁니다: {solve.fast_solution.splitlines()[0] if solve.fast_solution else '핵심 조건부터 잡기'}",
            f"풀이 흐름: {solve.basic_solution}",
        ]
        step = min(max(request.step, 1), len(hints))
        reveal = solve.verified_answer if request.reveal_answer else None
        return TutorHintResponse(
            step=step,
            hint=hints[step - 1],
            next_prompt="다음 힌트를 보려면 step 값을 1 올리세요.",
            reveal_answer=reveal,
        )

    def error_taxonomy(self, user_id: str) -> ErrorTaxonomyResponse:
        wrong = self.student_repo.list_wrong_attempts(user_id, limit=50)
        slow = self.student_repo.list_slow_attempts(user_id, limit=50)
        items: list[ErrorTaxonomyItem] = []

        if wrong:
            by_unit = defaultdict(list)
            for item in wrong:
                by_unit[item.unit].append(item.problem_text)
            for unit, examples in by_unit.items():
                items.append(
                    ErrorTaxonomyItem(
                        category=f"{unit} 개념/조건 오류",
                        severity="높음" if len(examples) >= 3 else "중간",
                        count=len(examples),
                        evidence=examples[:3],
                        fix=["기본 개념 3분 복습", "같은 유형 숫자 바꿔 재풀이", "마지막 답 검산"],
                    )
                )

        if slow:
            items.append(
                ErrorTaxonomyItem(
                    category="시간 관리 오류",
                    severity="중간" if len(slow) < 3 else "높음",
                    count=len(slow),
                    evidence=[item.problem_text for item in slow[:3]],
                    fix=["90초 타이머", "빠른 풀이 먼저 읽기", "막히면 표시 후 넘기기"],
                )
            )

        if not items:
            items.append(
                ErrorTaxonomyItem(
                    category="데이터 부족",
                    severity="낮음",
                    count=0,
                    evidence=["오답/느린 문제 기록이 아직 부족합니다."],
                    fix=["진단 테스트 1회", "수학/과학 각 3문제 풀이"],
                )
            )

        items.sort(key=lambda item: {"높음": 0, "중간": 1, "낮음": 2}[item.severity])
        return ErrorTaxonomyResponse(
            user_id=user_id,
            items=items,
            priority_fix=items[0].fix[0],
        )

    def weekly_plan(self, user_id: str) -> WeeklyPlanResponse:
        mastery = self.mastery_map(user_id)
        weak = mastery.weakest_unit
        days = [
            WeeklyPlanDay(day=1, focus=f"{weak} 개념 회복", tasks=["개념 압축 읽기", "기본 문제 3개", "오답 이유 기록"], success_rule="3문제 중 2문제 이상 정답"),
            WeeklyPlanDay(day=2, focus="공식/전략 암기", tasks=["공식 노트 5개", "빠른 풀이 3개", "검산 훈련"], success_rule="평균 120초 이하"),
            WeeklyPlanDay(day=3, focus="오답 재출제", tasks=["오답 3개 재풀이", "숫자 바꾼 문제 2개", "북마크 정리"], success_rule="오답 재풀이 80% 이상"),
            WeeklyPlanDay(day=4, focus="실전 타이머", tasks=["90초 제한 5문제", "넘길 문제 표시", "느린 문제 저장"], success_rule="시간 초과 2개 이하"),
            WeeklyPlanDay(day=5, focus="난이도 상승", tasks=["한 단계 어려운 문제 3개", "풀이 방식 비교", "상위권 풀이 확인"], success_rule="3문제 중 2문제 접근 성공"),
            WeeklyPlanDay(day=6, focus="혼합 세트", tasks=["수학 3문제", "과학 3문제", "약점 단원 2문제"], success_rule="정답률 70% 이상"),
            WeeklyPlanDay(day=7, focus="주간 리포트", tasks=["학생 리포트 확인", "성취 배지 확인", "다음 주 목표 설정"], success_rule="다음 약점 1개 선택"),
        ]
        return WeeklyPlanResponse(
            user_id=user_id,
            title=f"{weak} 중심 7일 성장 계획",
            days=days,
            expected_outcome=f"{weak} 단원의 정확도와 속도를 동시에 올리는 것이 목표입니다.",
        )

    def answer_check(self, request: AnswerCheckRequest) -> AnswerCheckResponse:
        expected = self._normalize(request.expected_answer)
        student = self._normalize(request.student_answer)
        expected_numbers = re.findall(r"-?\d+(?:\.\d+)?", expected)
        student_numbers = re.findall(r"-?\d+(?:\.\d+)?", student)
        matched = [number for number in expected_numbers if number in student_numbers]
        missing = [number for number in expected_numbers if number not in student_numbers]
        correct = self._answer_matches(request.student_answer, request.expected_answer)

        if correct:
            credit = 100
            feedback = "정답입니다. 마지막 단위와 조건까지 맞는지 확인하세요."
        elif expected_numbers:
            credit = int((len(matched) / len(expected_numbers)) * 70)
            feedback = "일부 숫자는 맞지만 최종 답 또는 단위가 다릅니다."
        elif student == expected:
            credit = 100
            feedback = "정답입니다."
        else:
            credit = 30 if student and student in expected or expected in student else 0
            feedback = "정답과 다릅니다. 기본 풀이로 다시 확인하세요."

        return AnswerCheckResponse(
            correct=correct,
            partial_credit=credit,
            normalized_expected=expected,
            normalized_student=student,
            matched_parts=matched,
            missing_parts=missing,
            feedback=feedback,
        )

    def start_mock_exam(self, request: MockExamStartRequest) -> MockExamStartResponse:
        diagnostic = self.start_diagnostic(
            DiagnosticStartRequest(
                subject=request.subject,
                count=request.count,
                difficulty=request.difficulty,
            )
        )
        per_question = max(30, int((request.time_limit_minutes * 60) / len(diagnostic.questions)))
        return MockExamStartResponse(
            exam_id=str(uuid4()),
            questions=diagnostic.questions,
            time_limit_minutes=request.time_limit_minutes,
            per_question_seconds=per_question,
            recommended_strategy=[
                "처음 1분 안에 전체 문제 난이도를 훑기",
                f"문제당 {per_question}초 기준으로 넘길 문제 표시",
                "쉬운 공식형 문제부터 점수 확보",
                "마지막 20% 시간은 표시한 문제 재도전",
            ],
        )

    def submit_mock_exam(self, request: MockExamSubmitRequest) -> MockExamSubmitResponse:
        results: list[DiagnosticResultItem] = []
        skip_candidates: list[str] = []
        total_elapsed = 0

        for answer in request.answers:
            correct = self._answer_matches(answer.student_answer, answer.expected_answer)
            total_elapsed += answer.elapsed_seconds or 0
            if answer.marked_for_review or (answer.elapsed_seconds and answer.elapsed_seconds > 150):
                skip_candidates.append(answer.problem)
            self.student_repo.save_attempt(
                AttemptRecord(
                    user_id=request.user_id,
                    problem_text=answer.problem,
                    subject=answer.subject,
                    unit=answer.unit,
                    problem_type=answer.target_skill,
                    difficulty="모의고사",
                    elapsed_seconds=answer.elapsed_seconds,
                    was_correct=correct,
                )
            )
            results.append(
                DiagnosticResultItem(
                    question_id=answer.question_id,
                    correct=correct,
                    expected_answer=answer.expected_answer,
                    student_answer=answer.student_answer,
                    unit=answer.unit,
                    target_skill=answer.target_skill,
                    feedback="정답" if correct else "오답. 같은 유형을 복습 목록에 넣으세요.",
                )
            )

        total = len(results)
        correct_count = sum(1 for item in results if item.correct)
        score = round((correct_count / total) * 100, 1) if total else 0.0
        if score >= 90:
            grade = "상위권"
        elif score >= 75:
            grade = "안정권"
        elif score >= 55:
            grade = "보완 필요"
        else:
            grade = "기초 회복 필요"

        limit_seconds = request.time_limit_minutes * 60
        if total_elapsed == 0:
            pacing = "시간 기록이 없어 속도 평가는 보류합니다."
        elif total_elapsed <= limit_seconds:
            pacing = "제한 시간 안에 해결했습니다."
        else:
            pacing = f"제한 시간보다 {total_elapsed - limit_seconds}초 초과했습니다."

        next_training = [
            "틀린 문제만 기본 풀이로 다시 보기",
            "표시한 문제는 빠른 풀이로 재도전",
            "같은 단원 문제 3개를 제한 시간 안에 풀기",
        ]
        return MockExamSubmitResponse(
            user_id=request.user_id,
            exam_id=request.exam_id,
            score_percent=score,
            correct_count=correct_count,
            total_count=total,
            predicted_grade=grade,
            pacing_report=pacing,
            skip_candidates=skip_candidates,
            results=results,
            next_training=next_training,
        )

    def flashcards(self, user_id: str, subject: str = "mixed") -> FlashcardResponse:
        mastery = self.mastery_map(user_id)
        weak = mastery.weakest_unit
        cards = [
            FlashcardItem(front="이차함수 최솟값은 어디서 확인?", back="꼭짓점 x=-b/(2a)를 구한 뒤 y값을 계산한다.", subject="math", unit="함수/이차함수", tag="공식"),
            FlashcardItem(front="이차방정식 인수분해 핵심", back="합이 b, 곱이 c인 두 수를 찾는다.", subject="math", unit="방정식", tag="패턴"),
            FlashcardItem(front="힘 공식", back="F=ma. 질량과 가속도를 곱한다.", subject="science", unit="물리", tag="공식"),
            FlashcardItem(front="전력 공식", back="P=VI. 전압과 전류를 곱한다.", subject="science", unit="물리", tag="공식"),
            FlashcardItem(front="몰수 공식", back="n=m/M. 질량을 몰 질량으로 나눈다.", subject="science", unit="화학", tag="공식"),
            FlashcardItem(front="시험장에서 오래 걸리면?", back="표시하고 넘긴 뒤 마지막에 돌아온다.", subject="mixed", unit="시험 전략", tag="전략"),
        ]
        filtered = [
            card for card in cards
            if subject == "mixed" or card.subject == subject or card.subject == "mixed"
        ]
        prioritized = sorted(filtered, key=lambda card: 0 if card.unit in weak else 1)
        return FlashcardResponse(
            user_id=user_id,
            cards=prioritized,
            message=f"{weak} 약점을 우선으로 플래시카드를 정렬했습니다.",
        )

    def mistake_notebook(self, user_id: str) -> MistakeNotebookResponse:
        wrong = self.student_repo.list_wrong_attempts(user_id, limit=50)
        slow = self.student_repo.list_slow_attempts(user_id, limit=50)
        groups: list[MistakeNotebookGroup] = []

        by_unit: dict[str, list[str]] = defaultdict(list)
        for item in wrong:
            by_unit[item.unit].append(item.problem_text)
        for unit, problems in by_unit.items():
            groups.append(
                MistakeNotebookGroup(
                    title=f"{unit} 오답",
                    count=len(problems),
                    problems=problems[:5],
                    root_cause="개념 조건을 끝까지 반영하지 않았거나 계산 검산이 부족합니다.",
                    retry_plan=[
                        "기본 풀이 다시 읽기",
                        "숫자만 바꾼 문제 2개 풀기",
                        "정답을 원식/공식에 대입해 검산",
                    ],
                )
            )

        if slow:
            groups.append(
                MistakeNotebookGroup(
                    title="시간 초과 문제",
                    count=len(slow),
                    problems=[item.problem_text for item in slow[:5]],
                    root_cause="풀이 방향 선택 또는 계산량 관리가 늦습니다.",
                    retry_plan=[
                        "빠른 풀이만 먼저 읽기",
                        "90초 타이머로 재풀이",
                        "막히는 순간 표시 후 넘기는 연습",
                    ],
                )
            )

        if not groups:
            groups.append(
                MistakeNotebookGroup(
                    title="오답 데이터 부족",
                    count=0,
                    problems=["진단 테스트나 문제 풀이를 먼저 진행하세요."],
                    root_cause="아직 충분한 기록이 없습니다.",
                    retry_plan=["수학 3문제", "과학 3문제", "풀이 시간 기록"],
                )
            )

        groups.sort(key=lambda group: group.count, reverse=True)
        return MistakeNotebookResponse(
            user_id=user_id,
            groups=groups,
            priority=groups[0].title,
        )

    def _skill_profiles(self, user_id: str) -> list[SkillProfile]:
        attempts = self.student_repo.list_attempts(user_id, limit=200)
        grouped: dict[tuple[str, str, str], list] = defaultdict(list)
        for item in attempts:
            grouped[(item.subject, item.unit, item.problem_type)].append(item)

        if not grouped:
            return self._starter_profiles()

        profiles = [
            self._profile_for_group(subject, unit, problem_type, rows)
            for (subject, unit, problem_type), rows in grouped.items()
        ]
        profiles.sort(key=lambda item: item.weakness_score, reverse=True)
        return profiles

    def _starter_profiles(self) -> list[SkillProfile]:
        return [
            SkillProfile(
                subject="math",
                unit="함수/이차함수",
                problem_type="꼭짓점/최솟값",
                attempts=0,
                correct_attempts=0,
                wrong_attempts=0,
                accuracy_percent=0,
                average_seconds=None,
                recent_average_seconds=None,
                speed_level="진단 전",
                mastery_score=0,
                weakness_score=70,
                label="진단 필요",
                evidence=["아직 풀이 기록이 없습니다."],
                next_action="이차함수 기본 문제 3개로 기준 기록 만들기",
            ),
            SkillProfile(
                subject="science",
                unit="물리",
                problem_type="공식 적용형",
                attempts=0,
                correct_attempts=0,
                wrong_attempts=0,
                accuracy_percent=0,
                average_seconds=None,
                recent_average_seconds=None,
                speed_level="진단 전",
                mastery_score=0,
                weakness_score=65,
                label="진단 필요",
                evidence=["과학 공식 적용 기록이 아직 없습니다."],
                next_action="F=ma, P=VI 같은 기본 공식 문제 3개 풀이",
            ),
        ]

    def _profile_for_group(
        self,
        subject: str,
        unit: str,
        problem_type: str,
        rows: list,
    ) -> SkillProfile:
        attempts = len(rows)
        correct = sum(1 for row in rows if row.was_correct is True)
        wrong = sum(1 for row in rows if row.was_correct is False)
        graded = correct + wrong
        accuracy = round((correct / graded) * 100, 1) if graded else 0.0
        times = [row.elapsed_seconds for row in rows if row.elapsed_seconds is not None]
        recent_times = [
            row.elapsed_seconds
            for row in rows[:5]
            if row.elapsed_seconds is not None
        ]
        average = round(sum(times) / len(times), 1) if times else None
        recent_average = round(sum(recent_times) / len(recent_times), 1) if recent_times else None

        speed_score = self._speed_score(average)
        mastery = int(accuracy * 0.72 + speed_score * 0.28)
        if attempts < 3:
            mastery = min(mastery, 65)
        wrong_ratio = (wrong / graded) if graded else 0.4
        time_penalty = 0
        if average is not None:
            if average >= 220:
                time_penalty = 35
            elif average >= 150:
                time_penalty = 24
            elif average >= 100:
                time_penalty = 12
        data_penalty = 15 if attempts < 3 else 0
        weakness = min(100, int(wrong_ratio * 65 + time_penalty + data_penalty))
        speed_level = self._speed_level(average)
        label = self._profile_label(mastery, weakness)

        evidence = [
            f"풀이 {attempts}개",
            f"정답률 {accuracy}%",
            f"평균 시간 {average}초" if average is not None else "시간 기록 부족",
        ]
        if recent_average is not None and average is not None:
            delta = round(recent_average - average, 1)
            evidence.append(f"최근 평균 변화 {delta:+g}초")

        return SkillProfile(
            subject=subject,
            unit=unit,
            problem_type=problem_type,
            attempts=attempts,
            correct_attempts=correct,
            wrong_attempts=wrong,
            accuracy_percent=accuracy,
            average_seconds=average,
            recent_average_seconds=recent_average,
            speed_level=speed_level,
            mastery_score=mastery,
            weakness_score=weakness,
            label=label,
            evidence=evidence,
            next_action=self._profile_next_action(accuracy, average, attempts),
        )

    def _speed_score(self, average: float | None) -> int:
        if average is None:
            return 60
        if average <= 75:
            return 100
        if average <= 120:
            return 82
        if average <= 180:
            return 58
        return 35

    def _speed_level(self, average: float | None) -> str:
        if average is None:
            return "시간 데이터 부족"
        if average <= 75:
            return "빠름"
        if average <= 120:
            return "보통"
        if average <= 180:
            return "느림"
        return "매우 느림"

    def _profile_label(self, mastery: int, weakness: int) -> str:
        if weakness >= 70:
            return "최우선 보완"
        if mastery >= 85:
            return "강점"
        if mastery >= 70:
            return "안정"
        if mastery >= 45:
            return "불안정"
        return "기초 보강"

    def _profile_next_action(
        self,
        accuracy: float,
        average: float | None,
        attempts: int,
    ) -> str:
        if attempts < 3:
            return "기준 데이터 확보를 위해 같은 유형 3문제 풀이"
        if accuracy < 60:
            return "기본 풀이와 오답 재출제로 정확도 회복"
        if average is not None and average >= 150:
            return "빠른 풀이 비교와 90초 재풀이"
        if accuracy >= 80:
            return "한 단계 어려운 실전 문제로 상승"
        return "같은 난이도에서 검산 습관 고정"

    def _risk_flags(self, profiles: list[SkillProfile], total_attempts: int) -> list[str]:
        flags: list[str] = []
        if total_attempts < 5:
            flags.append("데이터 부족: 최소 5문제 이상 기록 필요")
        if any(profile.accuracy_percent < 50 and profile.attempts >= 3 for profile in profiles):
            flags.append("정확도 위험: 특정 유형 정답률 50% 미만")
        if any(profile.average_seconds and profile.average_seconds >= 180 for profile in profiles):
            flags.append("시간 위험: 평균 180초 이상 유형 존재")
        if any(profile.wrong_attempts >= 3 for profile in profiles):
            flags.append("반복 오답 위험: 같은 유형 오답 3회 이상")
        return flags or ["큰 위험 신호 없음"]

    def _learner_stage(
        self,
        total_attempts: int,
        accuracy: float,
        average_seconds: float | None,
    ) -> str:
        if total_attempts == 0:
            return "진단 전"
        if total_attempts < 5:
            return "기준 데이터 수집"
        if accuracy < 60:
            return "정확도 회복"
        if average_seconds is not None and average_seconds >= 150:
            return "속도 개선"
        if accuracy >= 80:
            return "난이도 상승"
        return "안정화"

    def _next_best_actions(self, profiles: list[SkillProfile], learner_stage: str) -> list[str]:
        first = profiles[0]
        actions = [first.next_action]
        if learner_stage == "정확도 회복":
            actions.extend(["힌트 모드로 기본 풀이 확인", "오답 원인을 한 줄로 저장"])
        elif learner_stage == "속도 개선":
            actions.extend(["빠른 풀이만 먼저 읽기", "90초 타이머로 같은 유형 재풀이"])
        elif learner_stage == "난이도 상승":
            actions.extend(["상위권 풀이 비교", "실전 모드에서 넘길 문제 판단 훈련"])
        else:
            actions.extend(["진단 테스트 1회", "수학/과학 각 3문제 기록"])
        return actions[:4]

    def _queue_strategy(self, profile: SkillProfile) -> tuple[str, str, int]:
        if profile.attempts < 3 or profile.accuracy_percent < 60:
            return "easy", "basic", 150
        if profile.average_seconds and profile.average_seconds >= 150:
            return "same", "fast", 90
        if profile.mastery_score >= 75:
            return "harder", "exam", 90
        return "same", "compare", 120

    def _generator_unit_key(self, profile: SkillProfile) -> str | None:
        if "함수" in profile.unit or "이차" in profile.problem_type:
            return "function"
        if "방정식" in profile.unit or "방정식" in profile.problem_type:
            return "equation"
        if "물리" in profile.unit:
            return "physics"
        if "화학" in profile.unit:
            return "chemistry"
        return None

    def _mastery_for_unit(self, unit: str, rows: list) -> MasteryUnit:
        total = len(rows)
        correct = sum(1 for row in rows if row.was_correct is True)
        graded = sum(1 for row in rows if row.was_correct is not None)
        accuracy = round((correct / graded) * 100, 1) if graded else 0.0
        times = [row.elapsed_seconds for row in rows if row.elapsed_seconds is not None]
        average = round(sum(times) / len(times), 1) if times else None
        speed_score = 70
        if average is not None:
            if average <= 90:
                speed_score = 100
            elif average <= 150:
                speed_score = 75
            elif average <= 220:
                speed_score = 50
            else:
                speed_score = 30
        score = int(accuracy * 0.75 + speed_score * 0.25)
        if total < 3:
            score = min(score, 65)
        if score >= 85:
            level = "강함"
            next_action = "상위 난이도와 실전 모드"
        elif score >= 70:
            level = "안정"
            next_action = "빠른 풀이로 시간 단축"
        elif score >= 40:
            level = "불안정"
            next_action = "기본 풀이와 오답 재출제"
        else:
            level = "약함"
            next_action = "개념 압축부터 다시 시작"
        return MasteryUnit(
            unit=unit,
            total_attempts=total,
            accuracy_percent=accuracy,
            average_seconds=average,
            mastery_score=score,
            level=level,
            next_action=next_action,
        )

    def _answer_matches(self, student: str, expected: str) -> bool:
        left = self._normalize(student)
        right = self._normalize(expected)
        if not left:
            return False
        if right and right in left:
            return True
        expected_numbers = re.findall(r"-?\d+(?:\.\d+)?", right)
        student_numbers = re.findall(r"-?\d+(?:\.\d+)?", left)
        if expected_numbers:
            return all(number in student_numbers for number in expected_numbers)
        return left == right

    def _normalize(self, text: str) -> str:
        return (
            text.lower()
            .replace(" ", "")
            .replace(",", "")
            .replace("또는", "")
            .replace("정답", "")
            .replace("답", "")
        )
