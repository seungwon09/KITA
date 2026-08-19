from datetime import date, timedelta
from uuid import uuid4

from app.models.schemas import (
    AdminSmokeTestResponse,
    Achievement,
    AchievementResponse,
    AppAiCard,
    AppAiBatchRequest,
    AppAiBatchResponse,
    AppAiCapabilities,
    AppAiRequest,
    AppAiResponse,
    AppHomeResponse,
    AppSessionResponse,
    ExamStrategy,
    FeatureAccess,
    FeatureGateRequest,
    FeatureGateResponse,
    FeedbackRequest,
    FeedbackResponse,
    BookmarkItem,
    BookmarkListResponse,
    BookmarkRequest,
    LearningStyleProfile,
    LeaderboardEntry,
    LeaderboardResponse,
    MentalAnalysis,
    NotificationPlanResponse,
    MistakeReport,
    ProblemSet,
    ProblemSolveRequest,
    PlanCatalog,
    PlanInfo,
    ReviewScheduleResponse,
    SolveMode,
    SolveResponse,
    SpeedOptimization,
    StudySessionResponse,
    StudentDataExport,
    StudentProfileRequest,
    StudentProfileResponse,
    StudentReportResponse,
    UsageSnapshot,
    UserSolutionEvaluation,
)
from app.repositories.student_repo import StudentRepository
from app.services.problem_ai import ProblemAiService
from app.services.problem_generator import ProblemGeneratorService
from app.services.study_guide import StudyGuideService


class AppAiService:
    def __init__(
        self,
        problem_ai: ProblemAiService,
        student_repo: StudentRepository,
        study_guide: StudyGuideService,
        problem_generator: ProblemGeneratorService,
    ) -> None:
        self.problem_ai = problem_ai
        self.student_repo = student_repo
        self.study_guide = study_guide
        self.problem_generator = problem_generator

    async def analyze(self, request: AppAiRequest) -> AppAiResponse:
        plan = self._normalize_plan(request.plan)
        access = self._feature_access(plan)
        self._attach_usage(access, request.user_id, plan)
        if access.remaining_today <= 0:
            return self._usage_limited_response(request, access)
        self.student_repo.record_usage(request.user_id, plan, "analyze")
        self._attach_usage(access, request.user_id, plan)
        solve = await self.problem_ai.solve(
            ProblemSolveRequest(
                user_id=request.user_id,
                problem_text=request.problem_text,
                subject=request.subject,
                student_level=request.student_level,
                mode=SolveMode.compare,
                user_solution=request.user_solution,
                elapsed_seconds=request.elapsed_seconds,
                was_correct=request.was_correct,
            )
        )

        evaluation = self._evaluate_solution(request, solve, plan)
        mistake_report = self._mistake_report(request, solve)
        exam_strategy = self._exam_strategy(request, solve)
        insight = self.student_repo.get_insight(request.user_id)
        recommendation = self.student_repo.get_recommendation(request.user_id)
        learning_route = self.study_guide.learning_route(request.user_id)
        practice_set = self._practice_set(request, plan)
        self._apply_plan_locks(plan, solve, evaluation, practice_set)

        return AppAiResponse(
            api_version="2026-05-mvp",
            request_id=str(uuid4()),
            feature_access=access,
            solve=solve,
            evaluation=evaluation,
            mistake_report=mistake_report,
            exam_strategy=exam_strategy,
            insight=insight,
            recommendation=recommendation,
            learning_route=learning_route,
            practice_set=practice_set,
            ui_cards=self._ui_cards(solve, evaluation, mistake_report, exam_strategy, access),
        )

    def app_home(self, user_id: str, plan: str = "free") -> AppHomeResponse:
        plan = self._normalize_plan(plan)
        usage = self.usage_snapshot(user_id, plan)
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        recommendation = self.student_repo.get_recommendation(user_id)
        learning_style = self.learning_style(user_id)
        mental_analysis = self.mental_analysis(user_id)
        speed_optimization = self.speed_optimization(user_id)
        quick_actions = [
            "사진으로 문제 입력",
            "앱용 통합 분석",
            "오답만 다시 풀기",
            "난이도 자동 문제",
        ]
        dashboard_cards = [
            AppAiCard(title="오늘 사용량", body=f"{usage.used_today}/{usage.daily_limit}", action="show_usage"),
            AppAiCard(title="정답률", body=f"{progress.accuracy_percent}%", action="show_progress"),
            AppAiCard(title="학습 스타일", body=learning_style.primary_style, action="show_style"),
            AppAiCard(title="압박 위험", body=mental_analysis.pressure_risk, action="show_mental"),
            AppAiCard(title="속도 목표", body=f"{speed_optimization.target_seconds}초", action="show_speed"),
        ]
        return AppHomeResponse(
            user_id=user_id,
            usage=usage,
            progress=progress,
            insight=insight,
            recommendation=recommendation,
            learning_style=learning_style,
            mental_analysis=mental_analysis,
            speed_optimization=speed_optimization,
            quick_actions=quick_actions,
            dashboard_cards=dashboard_cards,
        )

    async def batch_analyze(self, request: AppAiBatchRequest) -> AppAiBatchResponse:
        results: list[AppAiResponse] = []
        for item in request.items[:10]:
            results.append(
                await self.analyze(
                    AppAiRequest(
                        user_id=request.user_id,
                        problem_text=item.problem_text,
                        subject=item.subject,
                        plan=request.plan,
                        student_level=request.student_level,
                        user_solution=item.user_solution,
                        elapsed_seconds=item.elapsed_seconds,
                        was_correct=item.was_correct,
                        time_limit_seconds=request.time_limit_seconds,
                        include_practice=False,
                    )
                )
            )

        wrong_count = sum(1 for result in results if result.mistake_report.risk_level == "높음")
        slow_count = sum(1 for result in results if result.exam_strategy.speed_judgement == "시간 초과")
        summary_cards = [
            AppAiCard(title="분석 수", body=str(len(results)), action="show_batch"),
            AppAiCard(title="위험 문제", body=str(wrong_count), action="show_mistakes"),
            AppAiCard(title="시간 초과", body=str(slow_count), action="show_speed"),
            AppAiCard(title="다음 행동", body="오답/느린 문제부터 복습", action="open_review"),
        ]
        return AppAiBatchResponse(
            api_version="2026-05-mvp",
            user_id=request.user_id,
            total=len(results),
            results=results,
            summary_cards=summary_cards,
        )

    def capabilities(self) -> AppAiCapabilities:
        return AppAiCapabilities(
            api_version="2026-05-mvp",
            primary_endpoint="POST /app-ai/analyze",
            endpoints=[
                {"method": "POST", "path": "/app-ai/analyze", "purpose": "문제 1개 통합 분석"},
                {"method": "POST", "path": "/app-ai/batch-analyze", "purpose": "문제 여러 개 한 번에 분석"},
                {"method": "GET", "path": "/app-ai/mobile/config", "purpose": "모바일 앱 연결 설정"},
                {"method": "GET", "path": "/app-ai/mobile/bootstrap/{user_id}", "purpose": "앱 시작 데이터 묶음"},
                {"method": "POST", "path": "/app-ai/mobile/analyze", "purpose": "모바일 앱용 문제 분석 묶음"},
                {"method": "POST", "path": "/app-ai/mobile/ocr-analyze", "purpose": "사진 OCR 후 바로 분석"},
                {"method": "GET", "path": "/app-ai/production/status", "purpose": "완성형 서버 상태"},
                {"method": "GET", "path": "/app-ai/production/registry", "purpose": "UI 버튼 연결용 기능 레지스트리"},
                {"method": "POST", "path": "/app-ai/production/action", "purpose": "UI action 하나로 기능 실행"},
                {"method": "GET", "path": "/app-ai/home/{user_id}", "purpose": "앱 첫 화면 데이터"},
                {"method": "GET", "path": "/app-ai/learning-style/{user_id}", "purpose": "학습 스타일"},
                {"method": "GET", "path": "/app-ai/mental/{user_id}", "purpose": "멘탈/시간 압박"},
                {"method": "GET", "path": "/app-ai/speed/{user_id}", "purpose": "속도 최적화"},
                {"method": "GET", "path": "/app-ai/personalization/{user_id}", "purpose": "학생 개인화 대시보드"},
                {"method": "GET", "path": "/app-ai/training-queue/{user_id}", "purpose": "오늘 맞춤 훈련 큐"},
                {"method": "GET", "path": "/app-ai/weakness-deep-dive/{user_id}", "purpose": "약점 원인 심층 분석"},
                {"method": "GET", "path": "/app-ai/export/{user_id}", "purpose": "학생 데이터 내보내기"},
                {"method": "POST", "path": "/app-ai/feedback", "purpose": "응답 품질 피드백 저장"},
            ],
            plans={
                "free": ["검산 답", "기본 풀이", "짧은 힌트"],
                "basic": ["기본 풀이", "빠른 풀이", "실수 감지"],
                "pro": ["통합 분석", "풀이 평가", "자동 난이도", "학습 루트"],
                "premium": ["전체 기능", "우선 응답", "고급 전략"],
            },
            recommended_app_flow=[
                "사진/OCR 또는 텍스트로 문제 입력",
                "앱에서는 POST /app-ai/mobile/analyze 또는 /app-ai/mobile/ocr-analyze 호출",
                "버튼 기반 UI는 /app-ai/production/registry로 action 목록을 받고 /app-ai/production/action 호출",
                "ui_cards를 상단 요약으로 표시",
                "solve/evaluation/mistake_report를 탭으로 표시",
                "practice_set으로 다음 문제 추천",
                "사용자 반응을 /app-ai/feedback에 저장",
            ],
        )

    def export_student_data(self, user_id: str) -> StudentDataExport:
        return StudentDataExport(
            user_id=user_id,
            attempts=self.student_repo.list_attempts(user_id, limit=100),
            wrong_items=self.student_repo.list_wrong_attempts(user_id, limit=100),
            slow_items=self.student_repo.list_slow_attempts(user_id, limit=100),
            progress=self.student_repo.get_progress(user_id),
            insight=self.student_repo.get_insight(user_id),
            review=self.student_repo.get_review_bundle(user_id),
            recommendation=self.student_repo.get_recommendation(user_id),
        )

    def plan_catalog(self) -> PlanCatalog:
        plan_names = ["free", "basic", "pro", "premium"]
        labels = {
            "free": "무료",
            "basic": "기본 유료",
            "pro": "추천",
            "premium": "최상위",
        }
        recommended = {
            "free": "맛보기와 단순 검산",
            "basic": "일반 학생의 기본 풀이/빠른 풀이",
            "pro": "앱 핵심 요금제, 풀이 평가와 맞춤 추천",
            "premium": "상위권/시험 집중 사용자",
        }
        plans = []
        for name in plan_names:
            access = self._feature_access(name)
            plans.append(
                PlanInfo(
                    plan=name,
                    price_label=labels[name],
                    daily_limit=access.daily_limit,
                    features=access.allowed_features,
                    locked_features=access.locked_features,
                    recommended_for=recommended[name],
                )
            )
        return PlanCatalog(default_plan="free", plans=plans)

    def feature_gate(self, request: FeatureGateRequest) -> FeatureGateResponse:
        plan = self._normalize_plan(request.plan)
        access = self._feature_access(plan)
        self._attach_usage(access, request.user_id, plan)
        feature = request.feature
        allowed_by_plan = (
            self._feature_allowed(feature, access)
            or feature.startswith("basic_")
        )
        allowed_by_usage = access.remaining_today > 0
        allowed = allowed_by_plan and allowed_by_usage

        if not allowed_by_usage:
            reason = "오늘 사용량을 모두 썼습니다."
            upgrade_to = "basic" if plan == "free" else "pro" if plan == "basic" else "premium"
        elif allowed_by_plan:
            reason = "사용 가능한 기능입니다."
            upgrade_to = None
        else:
            reason = f"{feature} 기능은 현재 요금제에서 잠겨 있습니다."
            upgrade_to = "basic" if plan == "free" else "pro" if plan == "basic" else "premium"

        return FeatureGateResponse(
            allowed=allowed,
            feature=feature,
            plan=plan,
            reason=reason,
            upgrade_to=upgrade_to,
            usage=self.usage_snapshot(request.user_id, plan),
        )

    def app_session(self, user_id: str, plan: str = "free") -> AppSessionResponse:
        plan = self._normalize_plan(plan)
        access = self._feature_access(plan)
        flags = {
            "can_use_fast_solution": self._feature_allowed("fast_solution", access),
            "can_use_solution_evaluation": self._feature_allowed("solution_evaluation", access),
            "can_use_adaptive_practice": self._feature_allowed("adaptive_practice", access),
            "can_use_exam_strategy": self._feature_allowed("exam_strategy", access),
            "can_use_learning_route": self._feature_allowed("learning_route", access),
            "can_use_ocr_analyze": self._feature_allowed("ocr_analyze", access),
            "can_use_training_queue": self._feature_allowed("training_queue", access),
        }
        return AppSessionResponse(
            user_id=user_id,
            plan=plan,
            api_version="2026-05-mvp",
            home=self.app_home(user_id, plan),
            capabilities=self.capabilities(),
            feature_flags=flags,
            startup_actions=[
                "앱 시작 시 /app-ai/session 호출",
                "feature_flags로 UI 버튼 잠금 처리",
                "home.dashboard_cards를 홈 화면에 표시",
                "문제 풀이 시 /app-ai/analyze 호출",
            ],
        )

    def study_session(self, user_id: str, plan: str = "free", subject: str = "math") -> StudySessionResponse:
        progress = self.student_repo.get_progress(user_id)
        review = self.student_repo.get_review_bundle(user_id)
        style = self.learning_style(user_id)
        difficulty = "easy" if progress.accuracy_percent < 60 else "same" if progress.average_elapsed_seconds and progress.average_elapsed_seconds >= 150 else "harder"
        problem_set = self.problem_generator.generate_set(subject=subject, difficulty=difficulty, count=5)
        return StudySessionResponse(
            user_id=user_id,
            title=f"{style.primary_style} 맞춤 {subject} 세션",
            estimated_minutes=25,
            warmup=[
                "공식/개념 2분 확인",
                "쉬운 문제 1개로 시작",
                "오늘 제한 시간 정하기",
            ],
            main_problems=problem_set.problems,
            review=review.today_review,
            finish_rule="5문제 중 4문제 이상 맞히고 평균 90초 이하면 다음 난이도로 이동",
        )

    def review_schedule(self, user_id: str) -> ReviewScheduleResponse:
        review = self.student_repo.get_review_bundle(user_id)
        today = review.retry_problems[:3]
        tomorrow = review.today_review[:3] or ["오늘 틀린 문제 다시 풀기"]
        later = [
            f"{(date.today() + timedelta(days=3)).isoformat()} 재복습",
            f"{(date.today() + timedelta(days=7)).isoformat()} 장기 복습",
        ]
        return ReviewScheduleResponse(
            user_id=user_id,
            today=today,
            tomorrow=tomorrow,
            later=later,
            message="망각 곡선용 MVP 일정입니다. 오답은 오늘, 내일, 3일 뒤, 7일 뒤 다시 봅니다.",
        )

    def admin_smoke_test(self) -> AdminSmokeTestResponse:
        checks = [
            {"name": "app_ai_service", "status": "ok", "detail": "service loaded"},
            {"name": "student_repository", "status": "ok", "detail": str(self.student_repo.db_path)},
            {"name": "plans", "status": "ok", "detail": ",".join(item.plan for item in self.plan_catalog().plans)},
            {"name": "capabilities", "status": "ok", "detail": self.capabilities().primary_endpoint},
        ]
        return AdminSmokeTestResponse(ok=True, checks=checks)

    def save_profile(self, profile: StudentProfileRequest) -> StudentProfileResponse:
        return self.student_repo.save_profile(profile)

    def get_profile(self, user_id: str) -> StudentProfileResponse:
        return self.student_repo.get_profile(user_id)

    def save_bookmark(self, bookmark: BookmarkRequest) -> BookmarkItem:
        return self.student_repo.save_bookmark(bookmark)

    def list_bookmarks(self, user_id: str) -> BookmarkListResponse:
        return BookmarkListResponse(
            user_id=user_id,
            bookmarks=self.student_repo.list_bookmarks(user_id),
        )

    def student_report(self, user_id: str) -> StudentReportResponse:
        profile = self.get_profile(user_id)
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        style = self.learning_style(user_id)
        speed = self.speed_optimization(user_id)
        strengths = [
            f"학습 스타일: {style.primary_style}",
            progress.trend_message,
        ]
        if progress.correct_attempts:
            strengths.append(f"맞힌 문제 {progress.correct_attempts}개 누적")
        weaknesses = insight.weak_units[:3] or insight.slow_types[:3] or ["아직 약점 데이터 부족"]
        next_7_days = [
            "1일차: 현재 약점 유형 3문제",
            "2일차: 오답 재풀이와 공식 노트",
            "3일차: 빠른 풀이 5문제",
            "4일차: 과학 공식 적용형 3문제",
            "5일차: 실전 타이머 세션",
            "6일차: 예상 문제 세트",
            "7일차: 주간 오답 정리",
        ]
        summary = (
            f"{profile.nickname}은 현재 {progress.total_attempts}개 풀이 기록이 있고 "
            f"정답률은 {progress.accuracy_percent}%입니다."
        )
        return StudentReportResponse(
            user_id=user_id,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            next_7_days=next_7_days,
            parent_message=f"{profile.nickname}은 {speed.message}",
            teacher_message=f"우선 지도 단원: {', '.join(weaknesses)}",
        )

    def achievements(self, user_id: str) -> AchievementResponse:
        progress = self.student_repo.get_progress(user_id)
        bookmarks = self.student_repo.list_bookmarks(user_id)
        usage = self.usage_snapshot(user_id, "pro")
        achievements = [
            Achievement(
                key="first_solve",
                title="첫 풀이",
                description="문제 풀이 기록 1개 달성",
                unlocked=progress.total_attempts >= 1,
                progress=f"{progress.total_attempts}/1",
            ),
            Achievement(
                key="ten_solves",
                title="풀이 루틴 시작",
                description="문제 풀이 기록 10개 달성",
                unlocked=progress.total_attempts >= 10,
                progress=f"{progress.total_attempts}/10",
            ),
            Achievement(
                key="accuracy_80",
                title="정확도 80%",
                description="정답률 80% 이상",
                unlocked=progress.accuracy_percent >= 80 and progress.total_attempts >= 5,
                progress=f"{progress.accuracy_percent}%/80%",
            ),
            Achievement(
                key="bookmarker",
                title="오답 저장 습관",
                description="북마크 3개 저장",
                unlocked=len(bookmarks) >= 3,
                progress=f"{len(bookmarks)}/3",
            ),
            Achievement(
                key="active_today",
                title="오늘도 학습",
                description="오늘 AI 분석 1회 이상",
                unlocked=usage.used_today >= 1,
                progress=f"{usage.used_today}/1",
            ),
        ]
        next_badge = next((item.title for item in achievements if not item.unlocked), "모든 MVP 배지 달성")
        return AchievementResponse(
            user_id=user_id,
            achievements=achievements,
            next_badge=next_badge,
        )

    def leaderboard(self, user_id: str) -> LeaderboardResponse:
        progress = self.student_repo.get_progress(user_id)
        my_score = int(progress.correct_attempts * 100 + progress.total_attempts * 10 - (progress.average_elapsed_seconds or 90))
        entries = [
            LeaderboardEntry(rank=1, user_id="top-1", score=max(my_score + 180, 500), label="상위권 빠른 풀이"),
            LeaderboardEntry(rank=2, user_id=user_id, score=max(my_score, 0), label="나"),
            LeaderboardEntry(rank=3, user_id="rival-1", score=max(my_score - 70, 120), label="비슷한 수준"),
            LeaderboardEntry(rank=4, user_id="rival-2", score=max(my_score - 130, 80), label="추격 대상"),
        ]
        entries = sorted(entries, key=lambda item: item.score, reverse=True)
        ranked = [
            LeaderboardEntry(rank=index + 1, user_id=item.user_id, score=item.score, label=item.label)
            for index, item in enumerate(entries)
        ]
        my_rank = next(item.rank for item in ranked if item.user_id == user_id)
        return LeaderboardResponse(
            user_id=user_id,
            my_rank=my_rank,
            entries=ranked,
            message="MVP용 랭킹입니다. 실제 서비스에서는 같은 학년/단원끼리 비교하면 됩니다.",
        )

    def notification_plan(self, user_id: str) -> NotificationPlanResponse:
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        target = insight.weak_units[0] if insight.weak_units else "오늘 추천 문제"
        if progress.total_attempts == 0:
            messages = [
                "오늘 첫 문제 3개만 풀고 기준 기록을 만들어보세요.",
                "수학 1문제, 과학 1문제로 시작해도 충분합니다.",
            ]
        else:
            messages = [
                f"{target} 복습할 시간입니다.",
                "어제 틀린 유형을 숫자만 바꿔 다시 풀어보세요.",
                "90초 타이머로 빠른 풀이를 한 번만 체크하세요.",
            ]
        return NotificationPlanResponse(
            user_id=user_id,
            push_messages=messages,
            quiet_hours="22:30-07:00",
            best_send_times=["07:30", "18:30", "21:00"],
            message="앱 푸시 알림 문구 MVP입니다.",
        )

    def usage_snapshot(self, user_id: str, plan: str = "free") -> UsageSnapshot:
        plan = self._normalize_plan(plan)
        access = self._feature_access(plan)
        used = self.student_repo.get_usage_today(user_id, plan)
        remaining = max(0, access.daily_limit - used)
        return UsageSnapshot(
            user_id=user_id,
            plan=plan,
            used_today=used,
            daily_limit=access.daily_limit,
            remaining_today=remaining,
            reset_at=(date.today() + timedelta(days=1)).isoformat(),
        )

    def learning_style(self, user_id: str) -> LearningStyleProfile:
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        attempts = self.student_repo.list_attempts(user_id, limit=30)
        slow_count = sum(1 for item in attempts if item.elapsed_seconds and item.elapsed_seconds >= 150)
        science_count = sum(1 for item in attempts if item.subject == "science")

        if progress.total_attempts == 0:
            style = "진단 전"
            confidence = 0.2
            evidence = ["풀이 기록 부족"]
            method = ["수학 3문제, 과학 3문제를 풀어 기준 데이터 만들기"]
            avoid = ["기록 없이 성향을 확정하지 않기"]
        elif progress.accuracy_percent < 60:
            style = "반복형"
            confidence = 0.72
            evidence = ["정답률이 낮아 반복 복습 효과가 큼", *insight.repeated_mistakes[:2]]
            method = ["같은 유형 숫자만 바꿔 3회 반복", "오답 이유를 한 줄로 저장", "다음 날 다시 풀기"]
            avoid = ["새 유형을 너무 빨리 늘리기"]
        elif slow_count >= 3:
            style = "단계형"
            confidence = 0.68
            evidence = ["시간이 오래 걸린 문제가 누적됨", *insight.slow_types[:2]]
            method = ["기본 풀이를 짧은 단계로 압축", "풀이 전 공식/전략 먼저 고르기", "90초 제한 훈련"]
            avoid = ["모든 풀이를 길게 쓰기"]
        elif science_count >= len(attempts) / 2 and attempts:
            style = "공식 매칭형"
            confidence = 0.65
            evidence = ["과학 공식 적용형 풀이 비중이 높음"]
            method = ["단위에서 공식을 먼저 고르기", "공식 노트 5개 반복", "대입 전 단위 체크"]
            avoid = ["공식 없이 문장만 읽으며 오래 고민하기"]
        else:
            style = "직관형"
            confidence = 0.61
            evidence = ["기본 흐름이 안정적", progress.trend_message]
            method = ["빠른 풀이 먼저 시도", "막히면 힌트 1개만 보기", "상위 유형으로 난이도 상승"]
            avoid = ["이미 아는 유형을 너무 오래 반복하기"]

        return LearningStyleProfile(
            user_id=user_id,
            primary_style=style,
            confidence=confidence,
            evidence=evidence,
            best_study_method=method,
            avoid=avoid,
        )

    def mental_analysis(self, user_id: str) -> MentalAnalysis:
        progress = self.student_repo.get_progress(user_id)
        slow_items = self.student_repo.list_slow_attempts(user_id, limit=10)
        wrong_items = self.student_repo.list_wrong_attempts(user_id, limit=10)
        signals: list[str] = []

        if slow_items:
            signals.append("시간 초과 문제가 반복됨")
        if wrong_items:
            signals.append("오답 누적")
        if progress.average_elapsed_seconds and progress.average_elapsed_seconds >= 180:
            signals.append("평균 풀이 시간이 긴 편")
        if not signals:
            signals.append("강한 압박 신호는 아직 없음")

        if len(slow_items) >= 3 and len(wrong_items) >= 3:
            risk = "높음"
            intervention = ["먼저 풀 문제와 버릴 문제를 구분", "제한 시간 지나면 표시 후 넘기기", "쉬운 문제 5개로 리듬 회복"]
        elif slow_items or wrong_items:
            risk = "중간"
            intervention = ["타이머 켜고 90초 컷 연습", "틀린 문제는 바로 다시 풀기", "풀이 전 공식/전략 한 줄 작성"]
        else:
            risk = "낮음"
            intervention = ["현재 루틴 유지", "난이도 한 단계 상승", "실전 모드로 속도 확인"]

        return MentalAnalysis(
            user_id=user_id,
            pressure_risk=risk,
            signals=signals,
            intervention=intervention,
            exam_day_tip="막히는 문제는 표시하고 넘긴 뒤, 맞힐 수 있는 문제에서 점수를 먼저 확보하세요.",
        )

    def speed_optimization(self, user_id: str) -> SpeedOptimization:
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        average = progress.average_elapsed_seconds
        target = 60 if average and average <= 120 else 90
        bottlenecks = insight.slow_types[:3] or insight.weak_units[:3] or ["기록 부족"]

        if average is None:
            message = "풀이 시간을 더 기록하면 목표 시간이 정확해집니다."
        elif average <= target:
            message = "현재 속도는 괜찮습니다. 난이도를 올려도 됩니다."
        else:
            message = f"평균 {average}초에서 목표 {target}초로 줄이는 훈련이 필요합니다."

        return SpeedOptimization(
            user_id=user_id,
            average_seconds=average,
            target_seconds=target,
            bottlenecks=bottlenecks,
            drills=[
                "문제 읽고 10초 안에 유형 말하기",
                "공식/전략 먼저 고르고 계산 시작",
                "같은 유형 3문제를 연속으로 제한 시간 안에 풀기",
                "풀이 후 줄일 수 있는 계산 한 줄 표시",
            ],
            message=message,
        )

    def save_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        self.student_repo.save_feedback(
            user_id=feedback.user_id,
            request_id=feedback.request_id,
            rating=feedback.rating,
            comment=feedback.comment,
            problem_text=feedback.problem_text,
            was_helpful=feedback.was_helpful,
        )
        return FeedbackResponse(saved=True, message="피드백이 저장되었습니다.")

    def _normalize_plan(self, plan: str) -> str:
        return plan if plan in {"free", "basic", "pro", "premium"} else "free"

    def _feature_access(self, plan: str) -> FeatureAccess:
        rules = {
            "free": (
                ["verified_answer", "basic_solution", "short_hint", "ocr_basic", "mobile_config"],
                [
                    "full_fast_solution",
                    "solution_evaluation",
                    "adaptive_practice",
                    "learning_route_detail",
                    "training_queue",
                    "ocr_analyze",
                    "premium_exam_mode",
                ],
                10,
                "short",
            ),
            "basic": (
                ["verified_answer", "basic_solution", "fast_solution", "mistake_detection", "ocr_analyze", "mobile_bundle"],
                ["adaptive_practice", "advanced_exam_strategy", "personalization_deep"],
                80,
                "normal",
            ),
            "pro": (
                [
                    "all_solve",
                    "solution_evaluation",
                    "adaptive_practice",
                    "exam_strategy",
                    "learning_route",
                    "training_queue",
                    "personalization",
                    "ocr_analyze",
                    "mobile_bundle",
                ],
                ["premium_priority"],
                500,
                "deep",
            ),
            "premium": (
                [
                    "all_solve",
                    "solution_evaluation",
                    "adaptive_practice",
                    "exam_strategy",
                    "learning_route",
                    "training_queue",
                    "personalization",
                    "ocr_analyze",
                    "mobile_bundle",
                    "priority",
                    "premium_exam_mode",
                    "advanced_exam_strategy",
                ],
                [],
                2000,
                "deep",
            ),
        }
        allowed, locked, daily_limit, depth = rules[plan]
        return FeatureAccess(
            plan=plan,
            allowed_features=allowed,
            locked_features=locked,
            daily_limit=daily_limit,
            remaining_today=daily_limit,
            response_depth=depth,
        )

    def _attach_usage(self, access: FeatureAccess, user_id: str, plan: str) -> None:
        used = self.student_repo.get_usage_today(user_id, plan)
        access.used_today = used
        access.remaining_today = max(0, access.daily_limit - used)

    def _feature_allowed(self, feature: str, access: FeatureAccess) -> bool:
        if "all_solve" in access.allowed_features and feature in {
            "fast_solution",
            "basic_solution",
            "verified_answer",
            "solution_evaluation",
            "exam_strategy",
        }:
            return True
        aliases = {
            "full_fast_solution": "fast_solution",
            "ocr": "ocr_analyze",
            "photo_solve": "ocr_analyze",
            "next_problem": "training_queue",
            "student_dashboard": "personalization",
        }
        normalized = aliases.get(feature, feature)
        return normalized in access.allowed_features

    def _usage_limited_response(
        self,
        request: AppAiRequest,
        access: FeatureAccess,
    ) -> AppAiResponse:
        from app.models.schemas import ProblemAnalysis

        solve = SolveResponse(
            analysis=ProblemAnalysis(
                subject=request.subject or "unknown",
                unit="사용량 제한",
                problem_type="요금제 제한",
                difficulty="제한",
                intent="오늘 사용량 초과",
                is_killer=False,
            ),
            basic_solution="오늘 사용량을 모두 사용했습니다. 내일 다시 사용하거나 상위 요금제로 올려야 합니다.",
            fast_solution="사용량 초과",
            wrong_answer_reasons=["사용량 제한"],
            similar_problem="사용량 제한 상태에서는 문제 생성이 잠깁니다.",
            tutor_hint="오늘 사용량이 초기화된 뒤 다시 시도하세요.",
            recommended_next_action="요금제 업그레이드 또는 내일 재시도",
            verified_answer=None,
            quality_warnings=["daily_limit_exceeded"],
            engine="locked",
            expected_speed="locked",
        )
        evaluation = UserSolutionEvaluation(
            score=0,
            verdict="사용량 초과",
            strengths=[],
            missing_steps=["요금제 사용량 확인"],
            mistake_candidates=["daily_limit_exceeded"],
            faster_rewrite="사용량 초과로 제공되지 않습니다.",
            next_action="요금제 화면으로 이동",
        )
        mistake_report = MistakeReport(
            risk_level="낮음",
            detected_mistakes=["사용량 제한"],
            likely_causes=["요금제 일일 제한 도달"],
            fix_drill=["내일 다시 시도", "상위 요금제 확인"],
        )
        exam_strategy = ExamStrategy(
            elapsed_seconds=request.elapsed_seconds,
            time_limit_seconds=request.time_limit_seconds,
            speed_judgement="사용량 초과",
            recommended_order=["요금제 확인"],
            skip_rule="사용량 초과 시 분석 호출 중단",
            pressure_tip="학습 기록은 유지됩니다.",
        )
        return AppAiResponse(
            api_version="2026-05-mvp",
            request_id=str(uuid4()),
            feature_access=access,
            solve=solve,
            evaluation=evaluation,
            mistake_report=mistake_report,
            exam_strategy=exam_strategy,
            insight=self.student_repo.get_insight(request.user_id),
            recommendation=self.student_repo.get_recommendation(request.user_id),
            learning_route=self.study_guide.learning_route(request.user_id),
            practice_set=None,
            ui_cards=[
                AppAiCard(title="사용량", body="오늘 한도 초과", action="show_plan"),
                AppAiCard(title="요금제", body=access.plan, action="upgrade"),
            ],
        )

    def _evaluate_solution(
        self, request: AppAiRequest, solve: SolveResponse, plan: str
    ) -> UserSolutionEvaluation:
        if not request.user_solution:
            return UserSolutionEvaluation(
                score=0,
                verdict="사용자 풀이 없음",
                strengths=[],
                missing_steps=["사용자 풀이를 올리면 과정 평가 가능"],
                mistake_candidates=["풀이 과정 데이터가 없음"],
                faster_rewrite=solve.fast_solution,
                next_action="학생 풀이 사진 또는 텍스트를 함께 보내세요.",
            )

        user_solution = request.user_solution.replace(" ", "")
        answer = (solve.verified_answer or "").replace(" ", "")
        has_answer = bool(answer and answer in user_solution)
        score = 90 if request.was_correct or has_answer else 55
        strengths = ["풀이 과정을 남김"]
        if "=" in request.user_solution:
            strengths.append("식을 세워 접근함")
        if has_answer:
            strengths.append("최종 답과 일치")

        missing_steps = []
        if not has_answer:
            missing_steps.append("최종 답 검산")
        if "따라서" not in request.user_solution and "답" not in request.user_solution:
            missing_steps.append("마지막 결론 문장")
        if len(request.user_solution) < 20:
            missing_steps.append("중간 과정 설명")

        verdict = "좋음" if score >= 80 else "보완 필요"
        next_action = (
            "같은 유형을 제한 시간 안에 한 번 더 푸세요."
            if score >= 80
            else "기본 풀이와 비교해서 빠진 조건을 표시하세요."
        )
        if plan == "free":
            verdict = "기본 평가"

        return UserSolutionEvaluation(
            score=score,
            verdict=verdict,
            strengths=strengths,
            missing_steps=missing_steps or ["큰 누락 없음"],
            mistake_candidates=solve.wrong_answer_reasons,
            faster_rewrite=solve.fast_solution,
            next_action=next_action,
        )

    def _mistake_report(self, request: AppAiRequest, solve: SolveResponse) -> MistakeReport:
        mistakes: list[str] = []
        if request.was_correct is False:
            mistakes.append("정답 불일치")
        if request.elapsed_seconds and request.elapsed_seconds > request.time_limit_seconds:
            mistakes.append("풀이 시간 초과")
        if solve.quality_warnings:
            mistakes.extend(solve.quality_warnings)
        if not mistakes:
            mistakes.append("큰 위험 신호 없음")

        risk = "높음" if request.was_correct is False else "중간" if request.elapsed_seconds and request.elapsed_seconds > request.time_limit_seconds else "낮음"
        return MistakeReport(
            risk_level=risk,
            detected_mistakes=mistakes,
            likely_causes=[
                "조건을 끝까지 반영하지 않음",
                "부호 또는 단위 실수",
                "검산 없이 답을 확정함",
            ],
            fix_drill=[
                "문제에서 구하는 값을 한 줄로 쓰기",
                "마지막 답을 원식이나 공식에 대입해 검산",
                "같은 유형 숫자 바꾼 문제 2개 재풀이",
            ],
        )

    def _exam_strategy(self, request: AppAiRequest, solve: SolveResponse) -> ExamStrategy:
        elapsed = request.elapsed_seconds
        limit = max(10, request.time_limit_seconds)
        if elapsed is None:
            judgement = "시간 데이터 없음"
        elif elapsed <= limit:
            judgement = "제한 시간 안에 풀이"
        else:
            judgement = "시간 초과"

        if solve.analysis.is_killer:
            order = ["조건 정리", "빠른 풀이 가능 여부 확인", "막히면 표시 후 다음 문제", "마지막에 재도전"]
            skip_rule = f"{limit}초 안에 핵심 식이 안 나오면 일단 넘기기"
        else:
            order = ["공식/유형 확인", "바로 대입", "검산", "다음 문제"]
            skip_rule = f"{limit // 2}초 안에 방향이 보이면 끝까지 풀기"

        return ExamStrategy(
            elapsed_seconds=elapsed,
            time_limit_seconds=limit,
            speed_judgement=judgement,
            recommended_order=order,
            skip_rule=skip_rule,
            pressure_tip="쉬운 문제에서 시간을 벌고, 오래 걸리는 문제는 표시 후 돌아오세요.",
        )

    def _practice_set(self, request: AppAiRequest, plan: str) -> ProblemSet | None:
        if not request.include_practice:
            return None
        if plan in {"free", "basic"}:
            return self.problem_generator.generate_set(
                subject=request.subject or "math",
                difficulty="same",
                count=2,
            )
        return self.problem_generator.adaptive_set(
            user_id=request.user_id,
            subject=request.subject or "math",
        )

    def _apply_plan_locks(
        self,
        plan: str,
        solve: SolveResponse,
        evaluation: UserSolutionEvaluation,
        practice_set: ProblemSet | None,
    ) -> None:
        if plan == "free":
            solve.fast_solution = "빠른 풀이 전체는 basic 이상에서 제공됩니다."
            evaluation.faster_rewrite = "풀이 평가와 빠른 수정안은 pro 이상에서 제공됩니다."
            if practice_set:
                practice_set.problems = practice_set.problems[:1]
        elif plan == "basic":
            evaluation.faster_rewrite = "상세 풀이 평가와 상위권식 수정안은 pro 이상에서 제공됩니다."

    def _ui_cards(
        self,
        solve: SolveResponse,
        evaluation: UserSolutionEvaluation,
        mistake_report: MistakeReport,
        exam_strategy: ExamStrategy,
        access: FeatureAccess,
    ) -> list[AppAiCard]:
        return [
            AppAiCard(
                title="정답",
                body=solve.verified_answer or "검산 답 없음",
                action="answer",
            ),
            AppAiCard(
                title="빠른 판단",
                body=f"{solve.analysis.unit} / {solve.analysis.problem_type} / {exam_strategy.speed_judgement}",
                action="show_strategy",
            ),
            AppAiCard(
                title="풀이 평가",
                body=f"{evaluation.verdict} · {evaluation.score}점",
                action="show_evaluation",
            ),
            AppAiCard(
                title="실수 위험",
                body=f"{mistake_report.risk_level} · {', '.join(mistake_report.detected_mistakes[:2])}",
                action="show_mistakes",
            ),
            AppAiCard(
                title="요금제",
                body=f"{access.plan} · {access.response_depth} 응답",
                action="show_plan",
            ),
        ]
