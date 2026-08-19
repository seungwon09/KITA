from typing import Any

from app.core.config import settings
from app.models.schemas import (
    AnswerCheckRequest,
    AppAiRequest,
    EliteSolutionRequest,
    FeatureGateRequest,
    ProblemRecognitionRequest,
    ProblemSolveRequest,
    ProductionActionRequest,
    ProductionActionResponse,
    ProductionFeatureItem,
    ProductionFeatureRegistryResponse,
    ProductionStatusResponse,
    QualityCheckRequest,
)
from app.repositories.student_repo import StudentRepository
from app.services.app_ai import AppAiService
from app.services.elite_solutions import EliteSolutionService
from app.services.learning_intelligence import LearningIntelligenceService
from app.services.problem_ai import ProblemAiService
from app.services.problem_generator import ProblemGeneratorService
from app.services.problem_recognition import ProblemRecognitionService
from app.services.study_guide import StudyGuideService


class ProductionAppService:
    def __init__(
        self,
        problem_ai: ProblemAiService,
        app_ai: AppAiService,
        student_repo: StudentRepository,
        study_guide: StudyGuideService,
        problem_generator: ProblemGeneratorService,
        learning_intelligence: LearningIntelligenceService,
        problem_recognition: ProblemRecognitionService | None = None,
        elite_solutions: EliteSolutionService | None = None,
    ) -> None:
        self.problem_ai = problem_ai
        self.app_ai = app_ai
        self.student_repo = student_repo
        self.study_guide = study_guide
        self.problem_generator = problem_generator
        self.learning_intelligence = learning_intelligence
        self.problem_recognition = problem_recognition
        self.elite_solutions = elite_solutions

    def registry(self) -> ProductionFeatureRegistryResponse:
        features = self._features()
        return ProductionFeatureRegistryResponse(
            api_version="2026-05-complete",
            recommended_base_url="http://127.0.0.1:8002",
            features=features,
            default_flow=[
                "app_bootstrap",
                "mobile_analyze",
                "personalization",
                "training_queue",
                "weakness_deep_dive",
                "feedback",
            ],
        )

    def status(self) -> ProductionStatusResponse:
        checks = [
            {"name": "fastapi", "status": "ok", "detail": settings.app_name},
            {"name": "database", "status": "ok", "detail": str(self.student_repo.db_path)},
            {"name": "model", "status": "ok", "detail": settings.local_llm_model},
            {"name": "features", "status": "ok", "detail": str(len(self._features()))},
        ]
        return ProductionStatusResponse(
            ok=True,
            api_version="2026-05-complete",
            server="study-ai-local",
            model=settings.local_llm_model,
            mock_llm=settings.use_mock_llm,
            database_ready=self.student_repo.db_path.exists(),
            feature_count=len(self._features()),
            checks=checks,
        )

    async def run_action(self, request: ProductionActionRequest) -> ProductionActionResponse:
        feature = self._feature_by_action(request.action)
        if not feature:
            return ProductionActionResponse(
                action=request.action,
                allowed=False,
                plan=request.plan,
                ui_target="error",
                result={"message": "알 수 없는 action입니다.", "known_actions": [item.action for item in self._features()]},
                next_actions=["registry"],
                warnings=["unknown_action"],
            )

        gate = self.app_ai.feature_gate(
            FeatureGateRequest(
                user_id=request.user_id,
                plan=request.plan,
                feature=feature.required_feature,
            )
        )
        if not gate.allowed and feature.required_feature not in {"basic", "mobile_config"}:
            return ProductionActionResponse(
                action=request.action,
                allowed=False,
                plan=request.plan,
                ui_target=feature.ui_target,
                result=gate.model_dump(),
                next_actions=["plans", "feature_gate"],
                warnings=[gate.reason],
            )

        result = await self._dispatch(request)
        return ProductionActionResponse(
            action=request.action,
            allowed=True,
            plan=request.plan,
            ui_target=feature.ui_target,
            result=result,
            next_actions=self._next_actions_for(request.action),
            warnings=[],
        )

    async def _dispatch(self, request: ProductionActionRequest) -> dict[str, Any]:
        action = request.action
        subject = request.subject if request.subject in {"math", "science"} else "math"
        problem_text = request.problem_text or self._default_problem(subject)

        if action == "solve":
            return (
                await self.problem_ai.solve(
                    ProblemSolveRequest(
                        user_id=request.user_id,
                        problem_text=problem_text,
                        subject=subject,
                        user_solution=request.user_solution,
                        elapsed_seconds=request.elapsed_seconds,
                        was_correct=request.was_correct,
                    )
                )
            ).model_dump()

        if action in {"analyze", "mobile_analyze"}:
            return (
                await self.app_ai.analyze(
                    AppAiRequest(
                        user_id=request.user_id,
                        problem_text=problem_text,
                        subject=subject,
                        plan=request.plan,
                        user_solution=request.user_solution,
                        elapsed_seconds=request.elapsed_seconds,
                        was_correct=request.was_correct,
                        time_limit_seconds=request.time_limit_seconds,
                        include_practice=True,
                    )
                )
            ).model_dump()

        if action == "home":
            return self.app_ai.app_home(request.user_id, request.plan).model_dump()
        if action == "app_bootstrap":
            return self.app_ai.app_session(request.user_id, request.plan).model_dump()
        if action == "plans":
            return self.app_ai.plan_catalog().model_dump()
        if action == "feature_gate":
            feature = str(request.payload.get("feature", "fast_solution"))
            return self.app_ai.feature_gate(
                FeatureGateRequest(user_id=request.user_id, plan=request.plan, feature=feature)
            ).model_dump()
        if action == "problem_recognition":
            if not self.problem_recognition:
                return {"message": "problem recognition service not connected"}
            return self.problem_recognition.recognize(
                ProblemRecognitionRequest(
                    user_id=request.user_id,
                    problem_text=problem_text,
                    subject=request.subject,
                    source="production_action",
                )
            ).model_dump()
        if action == "quality_check":
            if not self.problem_recognition:
                return {"message": "quality check service not connected"}
            return self.problem_recognition.quality_check(
                QualityCheckRequest(
                    user_id=request.user_id,
                    problem_text=problem_text,
                    subject=request.subject,
                    expected_answer=str(request.payload.get("expected_answer", "")) or None,
                    student_answer=str(request.payload.get("student_answer", request.user_solution or "")) or None,
                    elapsed_seconds=request.elapsed_seconds,
                )
            ).model_dump()
        if action == "ocr_stats":
            return self.student_repo.ocr_correction_stats().model_dump()
        if action == "elite_patterns":
            if not self.elite_solutions:
                return {"message": "elite solution service not connected"}
            return {"patterns": [pattern.model_dump() for pattern in self.elite_solutions.patterns(request.subject)]}
        if action == "elite_solution":
            if not self.elite_solutions:
                return {"message": "elite solution service not connected"}
            return self.elite_solutions.solve(
                EliteSolutionRequest(
                    user_id=request.user_id,
                    problem_text=problem_text,
                    subject=request.subject,
                    elapsed_seconds=request.elapsed_seconds,
                    mode=str(request.payload.get("mode", "exam")),
                    include_drills=bool(request.payload.get("include_drills", True)),
                )
            ).model_dump()
        if action == "elite_stats":
            return self.student_repo.elite_solution_stats().model_dump()
        if action == "personalization":
            return self.learning_intelligence.personalization_dashboard(request.user_id).model_dump()
        if action == "training_queue":
            return self.learning_intelligence.personalized_training_queue(
                request.user_id,
                subject=request.subject,
                count=request.count,
            ).model_dump()
        if action == "weakness_deep_dive":
            return self.learning_intelligence.weakness_deep_dive(
                request.user_id,
                target=request.target,
            ).model_dump()
        if action == "targeted_practice":
            return self.problem_generator.targeted_set(
                request.user_id,
                subject=request.subject,
                count=request.count,
            ).model_dump()
        if action == "concept":
            unit = request.target or request.payload.get("unit")
            return self.study_guide.concept_summary(subject=subject, unit=unit).model_dump()
        if action == "formula":
            return self.study_guide.formula_note(subject=subject).model_dump()
        if action == "learning_route":
            return self.study_guide.learning_route(request.user_id).model_dump()
        if action == "progress":
            return self.student_repo.get_progress(request.user_id).model_dump()
        if action == "insight":
            return self.student_repo.get_insight(request.user_id).model_dump()
        if action == "review":
            return self.student_repo.get_review_bundle(request.user_id).model_dump()
        if action == "mastery":
            return self.learning_intelligence.mastery_map(request.user_id).model_dump()
        if action == "weekly_plan":
            return self.learning_intelligence.weekly_plan(request.user_id).model_dump()
        if action == "flashcards":
            return self.learning_intelligence.flashcards(request.user_id, subject=request.subject).model_dump()
        if action == "mistake_notebook":
            return self.learning_intelligence.mistake_notebook(request.user_id).model_dump()
        if action == "answer_check":
            return self.learning_intelligence.answer_check(
                AnswerCheckRequest(
                    problem_text=problem_text,
                    expected_answer=str(request.payload.get("expected_answer", "")) or "검산 답 없음",
                    student_answer=str(request.payload.get("student_answer", request.user_solution or "")),
                    subject=subject,
                )
            ).model_dump()
        if action == "diagnostic_start":
            from app.models.schemas import DiagnosticStartRequest

            return self.learning_intelligence.start_diagnostic(
                DiagnosticStartRequest(
                    subject=request.subject if request.subject in {"math", "science", "mixed"} else "mixed",
                    count=max(2, min(request.count, 12)),
                    difficulty=str(request.payload.get("difficulty", "same")),
                )
            ).model_dump()
        if action == "mock_exam_start":
            from app.models.schemas import MockExamStartRequest

            return self.learning_intelligence.start_mock_exam(
                MockExamStartRequest(
                    subject=request.subject if request.subject in {"math", "science", "mixed"} else "mixed",
                    count=max(3, min(request.count, 20)),
                    difficulty=str(request.payload.get("difficulty", "exam")),
                    time_limit_minutes=int(request.payload.get("time_limit_minutes", 20)),
                )
            ).model_dump()

        return {"message": "실행기는 준비되었지만 이 action은 아직 dispatch에 연결되지 않았습니다."}

    def _features(self) -> list[ProductionFeatureItem]:
        return [
            self._feature("app_bootstrap", "앱 시작", "app", "POST", "/app-ai/production/action", "free", "mobile_config", "appProfile", "앱 시작에 필요한 홈/권한/기능 정보를 가져옵니다."),
            self._feature("solve", "풀이", "solve", "POST", "/app-ai/production/action", "free", "basic", "solution", "기본 풀이와 검산 답을 가져옵니다."),
            self._feature("analyze", "통합 분석", "solve", "POST", "/app-ai/production/action", "basic", "mobile_bundle", "appAiResult", "풀이, 평가, 실수 감지, 추천을 한 번에 가져옵니다."),
            self._feature("mobile_analyze", "모바일 분석", "app", "POST", "/app-ai/production/action", "basic", "mobile_bundle", "appAiResult", "모바일 앱 버튼에 바로 연결할 통합 분석입니다."),
            self._feature("home", "앱 홈", "student", "POST", "/app-ai/production/action", "free", "basic", "appProfile", "홈 대시보드 데이터를 가져옵니다."),
            self._feature("personalization", "개인화", "student", "POST", "/app-ai/production/action", "pro", "personalization", "appProfile", "단원/유형별 숙련도와 약점을 가져옵니다."),
            self._feature("training_queue", "훈련 큐", "practice", "POST", "/app-ai/production/action", "pro", "training_queue", "practiceSet", "오늘 풀 맞춤 문제 큐를 가져옵니다."),
            self._feature("targeted_practice", "약점 문제", "practice", "POST", "/app-ai/production/action", "basic", "adaptive_practice", "practiceSet", "약점 기반 문제 세트를 가져옵니다."),
            self._feature("weakness_deep_dive", "약점 심층", "student", "POST", "/app-ai/production/action", "pro", "personalization", "appProfile", "약점 원인과 훈련법을 가져옵니다."),
            self._feature("concept", "개념 압축", "study", "POST", "/app-ai/production/action", "free", "basic", "studyGuide", "단원 개념 압축을 가져옵니다."),
            self._feature("formula", "공식 노트", "study", "POST", "/app-ai/production/action", "free", "basic", "studyGuide", "수학/과학 공식 노트를 가져옵니다."),
            self._feature("learning_route", "학습 루트", "study", "POST", "/app-ai/production/action", "pro", "learning_route", "studyGuide", "맞춤 학습 루트를 가져옵니다."),
            self._feature("progress", "성장 추적", "student", "POST", "/app-ai/production/action", "free", "basic", "progress", "성장 지표를 가져옵니다."),
            self._feature("insight", "약점 분석", "student", "POST", "/app-ai/production/action", "free", "basic", "insight", "약점 요약을 가져옵니다."),
            self._feature("review", "복습 묶음", "student", "POST", "/app-ai/production/action", "basic", "mistake_detection", "review", "오답/느린 문제 복습 묶음을 가져옵니다."),
            self._feature("mastery", "숙련도", "student", "POST", "/app-ai/production/action", "pro", "personalization", "appProfile", "단원 숙련도 지도를 가져옵니다."),
            self._feature("weekly_plan", "7일 계획", "study", "POST", "/app-ai/production/action", "pro", "learning_route", "appProfile", "7일 학습 계획을 가져옵니다."),
            self._feature("flashcards", "플래시카드", "study", "POST", "/app-ai/production/action", "basic", "mistake_detection", "appProfile", "공식/개념 플래시카드를 가져옵니다."),
            self._feature("mistake_notebook", "오답노트", "student", "POST", "/app-ai/production/action", "basic", "mistake_detection", "appProfile", "고급 오답노트를 가져옵니다."),
            self._feature("answer_check", "답안 채점", "solve", "POST", "/app-ai/production/action", "basic", "mistake_detection", "appProfile", "학생 답안을 채점합니다."),
            self._feature("diagnostic_start", "진단 시작", "exam", "POST", "/app-ai/production/action", "free", "basic", "appProfile", "진단 테스트를 시작합니다."),
            self._feature("mock_exam_start", "모의고사", "exam", "POST", "/app-ai/production/action", "pro", "exam_strategy", "appProfile", "실전 모의고사를 시작합니다."),
            self._feature("plans", "요금제", "app", "POST", "/app-ai/production/action", "free", "mobile_config", "appProfile", "요금제 표를 가져옵니다."),
            self._feature("feature_gate", "기능 잠금", "app", "POST", "/app-ai/production/action", "free", "mobile_config", "appProfile", "기능 사용 가능 여부를 확인합니다."),
            self._feature("problem_recognition", "문제 인식", "solve", "POST", "/app-ai/production/action", "free", "basic", "appAiResult", "문제 텍스트를 과목, 단원, 유형, 조건으로 구조화합니다."),
            self._feature("quality_check", "풀이 품질 검사", "solve", "POST", "/app-ai/production/action", "basic", "mistake_detection", "appAiResult", "검산 답, 학생 답안, 풀이 위험 신호를 확인합니다."),
            self._feature("ocr_stats", "OCR 교정 통계", "app", "POST", "/app-ai/production/action", "pro", "ocr_analyze", "appProfile", "OCR 교정 데이터와 개선 후보를 확인합니다."),
            self._feature("elite_patterns", "상위권 패턴", "solve", "POST", "/app-ai/production/action", "premium", "advanced_exam_strategy", "appAiResult", "상위권 풀이 패턴 라이브러리를 가져옵니다."),
            self._feature("elite_solution", "고급 풀이", "solve", "POST", "/app-ai/production/action", "premium", "advanced_exam_strategy", "solution", "문제에 맞는 상위권 압축 풀이와 시험장 풀이를 생성합니다."),
            self._feature("elite_stats", "상위권 데이터", "student", "POST", "/app-ai/production/action", "premium", "advanced_exam_strategy", "appProfile", "상위권 풀이 샘플 축적 상태를 확인합니다."),
        ]

    def _feature(
        self,
        action: str,
        label: str,
        category: str,
        method: str,
        endpoint: str,
        required_plan: str,
        required_feature: str,
        ui_target: str,
        description: str,
    ) -> ProductionFeatureItem:
        return ProductionFeatureItem(
            action=action,
            label=label,
            category=category,
            method=method,
            endpoint=endpoint,
            required_plan=required_plan,
            required_feature=required_feature,
            ui_target=ui_target,
            description=description,
        )

    def _feature_by_action(self, action: str) -> ProductionFeatureItem | None:
        return next((item for item in self._features() if item.action == action), None)

    def _next_actions_for(self, action: str) -> list[str]:
        if action in {"solve", "analyze", "mobile_analyze"}:
            return ["elite_solution", "personalization", "training_queue", "weakness_deep_dive"]
        if action in {"elite_solution", "elite_patterns"}:
            return ["quality_check", "training_queue", "elite_stats"]
        if action in {"personalization", "weakness_deep_dive"}:
            return ["training_queue", "targeted_practice", "weekly_plan"]
        if action in {"training_queue", "targeted_practice"}:
            return ["solve", "answer_check", "review"]
        return ["home", "training_queue"]

    def _default_problem(self, subject: str) -> str:
        if subject == "science":
            return "전력 60W, 전압 12V일 때 전류를 구하시오"
        return "이차함수 y=2x^2-8x+1의 최솟값을 구하시오"
