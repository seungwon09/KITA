from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.models.schemas import (
    AdminSmokeTestResponse,
    AchievementResponse,
    AnswerCheckRequest,
    AnswerCheckResponse,
    AppAiBatchRequest,
    AppAiBatchResponse,
    AppAiCapabilities,
    AppHomeResponse,
    AppAiRequest,
    AppAiResponse,
    AppSessionResponse,
    AttemptHistoryItem,
    ConceptSummary,
    DiagnosticStartRequest,
    DiagnosticStartResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    ElitePattern,
    EliteSolutionRequest,
    EliteSolutionResponse,
    EliteStatsResponse,
    EliteTrainingDataItem,
    EliteTrainingDataRequest,
    EliteTrainingDataResponse,
    ErrorTaxonomyResponse,
    FlashcardResponse,
    FormulaNote,
    FeatureGateRequest,
    FeatureGateResponse,
    FeedbackRequest,
    FeedbackResponse,
    BookmarkItem,
    BookmarkListResponse,
    BookmarkRequest,
    LearningStyleProfile,
    LeaderboardResponse,
    MasteryMapResponse,
    MistakeNotebookResponse,
    MobileAnalyzeRequest,
    MobileAnalyzeResponse,
    MobileAppBootstrapResponse,
    MobileFeatureConfig,
    MobileNextCall,
    MobileOcrAnalyzeResponse,
    MockExamStartRequest,
    MockExamStartResponse,
    MockExamSubmitRequest,
    MockExamSubmitResponse,
    PlanCatalog,
    NotificationPlanResponse,
    ProblemSet,
    PersonalizedTrainingQueueResponse,
    ProductionActionRequest,
    ProductionActionResponse,
    ProductionFeatureRegistryResponse,
    ProductionStatusResponse,
    LearningRoute,
    MentalAnalysis,
    OcrResponse,
    OcrCorrectionItem,
    OcrCorrectionRequest,
    OcrCorrectionResponse,
    OcrCorrectionStatsResponse,
    ProblemRecognitionRequest,
    ProblemRecognitionResponse,
    ProblemSolveRequest,
    QualityCheckRequest,
    QualityCheckResponse,
    ReviewBundle,
    ReviewScheduleResponse,
    RoadmapStatusResponse,
    SolveResponse,
    StudentInsight,
    StudentProgress,
    StudentPersonalizationResponse,
    StudyRecommendation,
    SpeedOptimization,
    StudySessionResponse,
    StudentDataExport,
    StudentProfileRequest,
    StudentProfileResponse,
    StudentReportResponse,
    SolutionVariantsRequest,
    SolutionVariantsResponse,
    TutorHintRequest,
    TutorHintResponse,
    UsageSnapshot,
    WeaknessDeepDiveResponse,
    WeeklyPlanResponse,
)
from app.repositories.student_repo import StudentRepository
from app.services.app_ai import AppAiService
from app.services.learning_intelligence import LearningIntelligenceService
from app.services.elite_solutions import EliteSolutionService
from app.services.ocr import OcrService
from app.services.problem_ai import ProblemAiService
from app.services.problem_generator import ProblemGeneratorService
from app.services.problem_recognition import ProblemRecognitionService
from app.services.production_app import ProductionAppService
from app.services.roadmap import RoadmapService
from app.services.study_guide import StudyGuideService

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
problem_ai = ProblemAiService()
ocr = OcrService()
problem_recognition = ProblemRecognitionService(ocr)
roadmap = RoadmapService()
student_repo = StudentRepository()
study_guide = StudyGuideService(student_repo)
problem_generator = ProblemGeneratorService(student_repo)
app_ai = AppAiService(problem_ai, student_repo, study_guide, problem_generator)
learning_intelligence = LearningIntelligenceService(student_repo, problem_ai, problem_generator)
elite_solutions = EliteSolutionService(problem_recognition)
production_app = ProductionAppService(
    problem_ai,
    app_ai,
    student_repo,
    study_guide,
    problem_generator,
    learning_intelligence,
    problem_recognition,
    elite_solutions,
)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def mobile_config() -> MobileFeatureConfig:
    return MobileFeatureConfig(
        api_version="2026-05-mvp",
        base_url_hint="http://127.0.0.1:8002",
        default_plan="pro",
        supported_subjects=["math", "science", "auto"],
        client_timeout_seconds=60,
        image_upload_field="image",
        endpoints={
            "bootstrap": "GET /app-ai/mobile/bootstrap/{user_id}?plan=pro",
            "analyze_text": "POST /app-ai/mobile/analyze",
            "analyze_image": "POST /app-ai/mobile/ocr-analyze",
            "recognize_problem": "POST /app-ai/problem/recognize",
            "quality_check": "POST /app-ai/quality/check",
            "ocr_correction": "POST /app-ai/ocr/correction",
            "elite_patterns": "GET /app-ai/elite/patterns",
            "elite_solution": "POST /app-ai/elite/solution",
            "elite_sample": "POST /app-ai/elite/sample",
            "roadmap_status": "GET /app-ai/roadmap/status",
            "home": "GET /app-ai/home/{user_id}?plan=pro",
            "training_queue": "GET /app-ai/training-queue/{user_id}?subject=mixed&count=8",
        },
        required_request_fields=["user_id", "problem_text", "subject", "plan"],
        response_tabs=["answer", "fast_solution", "basic_solution", "analysis", "next_training"],
        cors_origins=settings.cors_origins,
    )


def mobile_next_calls(user_id: str) -> list[MobileNextCall]:
    safe_user = user_id or "student-1"
    return [
        MobileNextCall(
            label="앱 홈 새로고침",
            method="GET",
            path=f"/app-ai/home/{safe_user}?plan=pro",
            when_to_call="앱 첫 화면 진입 또는 풀이 후",
        ),
        MobileNextCall(
            label="맞춤 훈련큐",
            method="GET",
            path=f"/app-ai/training-queue/{safe_user}?subject=mixed&count=8",
            when_to_call="학생이 다음 문제 버튼을 눌렀을 때",
        ),
        MobileNextCall(
            label="약점 심층",
            method="GET",
            path=f"/app-ai/weakness-deep-dive/{safe_user}",
            when_to_call="약점 카드 상세 화면 진입 시",
        ),
    ]


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "model": settings.local_llm_model,
        "mock_llm": settings.use_mock_llm,
    }


@app.post("/ocr", response_model=OcrResponse)
async def extract_problem_text(image: UploadFile = File(...)) -> OcrResponse:
    image_bytes = await image.read()
    return await ocr.extract_text(image_bytes)


@app.post("/app-ai/problem/recognize", response_model=ProblemRecognitionResponse)
async def recognize_problem(request: ProblemRecognitionRequest) -> ProblemRecognitionResponse:
    return problem_recognition.recognize(request)


@app.post("/app-ai/quality/check", response_model=QualityCheckResponse)
async def check_solution_quality(request: QualityCheckRequest) -> QualityCheckResponse:
    return problem_recognition.quality_check(request)


@app.post("/app-ai/ocr/correction", response_model=OcrCorrectionResponse)
async def save_ocr_correction(correction: OcrCorrectionRequest) -> OcrCorrectionResponse:
    return student_repo.save_ocr_correction(correction)


@app.get("/app-ai/ocr/corrections/{user_id}", response_model=list[OcrCorrectionItem])
async def list_ocr_corrections(user_id: str, limit: int = 50) -> list[OcrCorrectionItem]:
    return student_repo.list_ocr_corrections(user_id=user_id, limit=max(1, min(limit, 100)))


@app.get("/app-ai/ocr/stats", response_model=OcrCorrectionStatsResponse)
async def get_ocr_correction_stats() -> OcrCorrectionStatsResponse:
    return student_repo.ocr_correction_stats()


@app.post("/solve", response_model=SolveResponse)
async def solve_problem(request: ProblemSolveRequest) -> SolveResponse:
    return await problem_ai.solve(request)


@app.post("/app-ai/analyze", response_model=AppAiResponse)
async def analyze_for_app(request: AppAiRequest) -> AppAiResponse:
    return await app_ai.analyze(request)


@app.get("/app-ai/health")
async def app_ai_health() -> dict[str, str | list[str]]:
    return {
        "status": "ok",
        "api_version": "2026-05-mvp",
        "main_endpoint": "POST /app-ai/analyze",
        "plans": ["free", "basic", "pro", "premium"],
    }


@app.get("/app-ai/capabilities", response_model=AppAiCapabilities)
async def get_app_ai_capabilities() -> AppAiCapabilities:
    return app_ai.capabilities()


@app.get("/app-ai/production/status", response_model=ProductionStatusResponse)
async def get_production_status() -> ProductionStatusResponse:
    return production_app.status()


@app.get("/app-ai/production/registry", response_model=ProductionFeatureRegistryResponse)
async def get_production_registry() -> ProductionFeatureRegistryResponse:
    return production_app.registry()


@app.get("/app-ai/roadmap/status", response_model=RoadmapStatusResponse)
async def get_roadmap_status() -> RoadmapStatusResponse:
    return roadmap.status()


@app.get("/app-ai/elite/patterns", response_model=list[ElitePattern])
async def get_elite_patterns(subject: str = "mixed") -> list[ElitePattern]:
    return elite_solutions.patterns(subject)


@app.post("/app-ai/elite/solution", response_model=EliteSolutionResponse)
async def create_elite_solution(request: EliteSolutionRequest) -> EliteSolutionResponse:
    return elite_solutions.solve(request)


@app.post("/app-ai/elite/sample", response_model=EliteTrainingDataResponse)
async def save_elite_training_sample(sample: EliteTrainingDataRequest) -> EliteTrainingDataResponse:
    candidates = elite_solutions.pattern_candidates(sample.problem_text, sample.subject)
    return student_repo.save_elite_solution_sample(sample, pattern_candidates=candidates)


@app.get("/app-ai/elite/samples/{user_id}", response_model=list[EliteTrainingDataItem])
async def list_elite_training_samples(user_id: str, limit: int = 50) -> list[EliteTrainingDataItem]:
    return student_repo.list_elite_solution_samples(user_id=user_id, limit=max(1, min(limit, 100)))


@app.get("/app-ai/elite/stats", response_model=EliteStatsResponse)
async def get_elite_training_stats() -> EliteStatsResponse:
    return student_repo.elite_solution_stats()


@app.post("/app-ai/production/action", response_model=ProductionActionResponse)
async def run_production_action(request: ProductionActionRequest) -> ProductionActionResponse:
    return await production_app.run_action(request)


@app.get("/app-ai/mobile/config", response_model=MobileFeatureConfig)
async def get_mobile_config() -> MobileFeatureConfig:
    return mobile_config()


@app.get("/app-ai/mobile/bootstrap/{user_id}", response_model=MobileAppBootstrapResponse)
async def get_mobile_bootstrap(
    user_id: str,
    plan: str = "pro",
) -> MobileAppBootstrapResponse:
    return MobileAppBootstrapResponse(
        config=mobile_config(),
        session=app_ai.app_session(user_id=user_id, plan=plan),
        personalization=learning_intelligence.personalization_dashboard(user_id),
        training_queue=learning_intelligence.personalized_training_queue(user_id, subject="mixed", count=8),
        next_calls=mobile_next_calls(user_id),
    )


@app.post("/app-ai/mobile/analyze", response_model=MobileAnalyzeResponse)
async def mobile_analyze_problem(request: MobileAnalyzeRequest) -> MobileAnalyzeResponse:
    analyze = await app_ai.analyze(request)
    home = app_ai.app_home(request.user_id, request.plan) if request.include_home else None
    personalization = (
        learning_intelligence.personalization_dashboard(request.user_id)
        if request.include_personalization
        else None
    )
    training_queue = (
        learning_intelligence.personalized_training_queue(request.user_id, subject="mixed", count=8)
        if request.include_training_queue
        else None
    )
    return MobileAnalyzeResponse(
        config=mobile_config(),
        analyze=analyze,
        home=home,
        personalization=personalization,
        training_queue=training_queue,
        next_client_actions=[
            "verified_answer를 상단 정답 영역에 표시",
            "plan에 따라 fast_solution/basic_solution 탭 잠금 처리",
            "training_queue.items를 다음 문제 리스트로 표시",
            "풀이 후 feedback 또는 bookmark를 저장",
        ],
        raw_debug={"request_id": analyze.request_id, "engine": analyze.solve.engine},
    )


@app.post("/app-ai/mobile/ocr-analyze", response_model=MobileOcrAnalyzeResponse)
async def mobile_ocr_analyze(
    image: UploadFile = File(...),
    user_id: str = Form("student-1"),
    subject: str = Form("auto"),
    plan: str = Form("pro"),
    student_level: str = Form("intermediate"),
    elapsed_seconds: int = Form(0),
    was_correct: bool = Form(True),
    auto_solve: bool = Form(True),
) -> MobileOcrAnalyzeResponse:
    image_bytes = await image.read()
    ocr_result = await ocr.extract_text(image_bytes)
    detected_subject = subject if subject in {"math", "science"} else ocr_result.detected_subject
    if detected_subject == "unknown":
        detected_subject = None
    analyze = None
    warning = None
    if ocr_result.needs_review:
        warning = "사진 인식 결과를 한 번 확인해 주세요. 특히 등호, 부호, 숫자, 단위를 확인하면 풀이 정확도가 올라갑니다."
    if auto_solve and ocr_result.extracted_text.strip():
        analyze = await app_ai.analyze(
            AppAiRequest(
                user_id=user_id,
                problem_text=ocr_result.extracted_text,
                subject=detected_subject,
                plan=plan,
                student_level=student_level,
                elapsed_seconds=elapsed_seconds,
                was_correct=was_correct,
                include_practice=True,
            )
        )
    return MobileOcrAnalyzeResponse(
        config=mobile_config(),
        ocr=ocr_result,
        analyze=analyze,
        warning=warning,
    )


@app.get("/app-ai/plans", response_model=PlanCatalog)
async def get_plan_catalog() -> PlanCatalog:
    return app_ai.plan_catalog()


@app.post("/app-ai/gate", response_model=FeatureGateResponse)
async def check_feature_gate(request: FeatureGateRequest) -> FeatureGateResponse:
    return app_ai.feature_gate(request)


@app.get("/app-ai/session/{user_id}", response_model=AppSessionResponse)
async def get_app_session(user_id: str, plan: str = "free") -> AppSessionResponse:
    return app_ai.app_session(user_id=user_id, plan=plan)


@app.post("/app-ai/batch-analyze", response_model=AppAiBatchResponse)
async def batch_analyze_for_app(request: AppAiBatchRequest) -> AppAiBatchResponse:
    return await app_ai.batch_analyze(request)


@app.get("/app-ai/home/{user_id}", response_model=AppHomeResponse)
async def get_app_home(user_id: str, plan: str = "free") -> AppHomeResponse:
    return app_ai.app_home(user_id=user_id, plan=plan)


@app.get("/app-ai/usage/{user_id}", response_model=UsageSnapshot)
async def get_app_usage(user_id: str, plan: str = "free") -> UsageSnapshot:
    return app_ai.usage_snapshot(user_id=user_id, plan=plan)


@app.get("/app-ai/learning-style/{user_id}", response_model=LearningStyleProfile)
async def get_learning_style(user_id: str) -> LearningStyleProfile:
    return app_ai.learning_style(user_id=user_id)


@app.get("/app-ai/mental/{user_id}", response_model=MentalAnalysis)
async def get_mental_analysis(user_id: str) -> MentalAnalysis:
    return app_ai.mental_analysis(user_id=user_id)


@app.get("/app-ai/speed/{user_id}", response_model=SpeedOptimization)
async def get_speed_optimization(user_id: str) -> SpeedOptimization:
    return app_ai.speed_optimization(user_id=user_id)


@app.get("/app-ai/study-session/{user_id}", response_model=StudySessionResponse)
async def get_study_session(
    user_id: str,
    plan: str = "free",
    subject: str = "math",
) -> StudySessionResponse:
    return app_ai.study_session(user_id=user_id, plan=plan, subject=subject)


@app.get("/app-ai/review-schedule/{user_id}", response_model=ReviewScheduleResponse)
async def get_review_schedule(user_id: str) -> ReviewScheduleResponse:
    return app_ai.review_schedule(user_id=user_id)


@app.post("/app-ai/feedback", response_model=FeedbackResponse)
async def save_app_feedback(feedback: FeedbackRequest) -> FeedbackResponse:
    return app_ai.save_feedback(feedback)


@app.get("/app-ai/export/{user_id}", response_model=StudentDataExport)
async def export_student_data(user_id: str) -> StudentDataExport:
    return app_ai.export_student_data(user_id)


@app.get("/admin/smoke-test", response_model=AdminSmokeTestResponse)
async def admin_smoke_test() -> AdminSmokeTestResponse:
    return app_ai.admin_smoke_test()


@app.get("/app-ai/profile/{user_id}", response_model=StudentProfileResponse)
async def get_student_profile(user_id: str) -> StudentProfileResponse:
    return app_ai.get_profile(user_id)


@app.post("/app-ai/profile", response_model=StudentProfileResponse)
async def save_student_profile(profile: StudentProfileRequest) -> StudentProfileResponse:
    return app_ai.save_profile(profile)


@app.post("/app-ai/bookmark", response_model=BookmarkItem)
async def save_bookmark(bookmark: BookmarkRequest) -> BookmarkItem:
    return app_ai.save_bookmark(bookmark)


@app.get("/app-ai/bookmarks/{user_id}", response_model=BookmarkListResponse)
async def list_bookmarks(user_id: str) -> BookmarkListResponse:
    return app_ai.list_bookmarks(user_id)


@app.get("/app-ai/report/{user_id}", response_model=StudentReportResponse)
async def get_student_report(user_id: str) -> StudentReportResponse:
    return app_ai.student_report(user_id)


@app.get("/app-ai/achievements/{user_id}", response_model=AchievementResponse)
async def get_achievements(user_id: str) -> AchievementResponse:
    return app_ai.achievements(user_id)


@app.get("/app-ai/leaderboard/{user_id}", response_model=LeaderboardResponse)
async def get_leaderboard(user_id: str) -> LeaderboardResponse:
    return app_ai.leaderboard(user_id)


@app.get("/app-ai/notifications/{user_id}", response_model=NotificationPlanResponse)
async def get_notification_plan(user_id: str) -> NotificationPlanResponse:
    return app_ai.notification_plan(user_id)


@app.get("/app-ai/mastery/{user_id}", response_model=MasteryMapResponse)
async def get_mastery_map(user_id: str) -> MasteryMapResponse:
    return learning_intelligence.mastery_map(user_id)


@app.get("/app-ai/personalization/{user_id}", response_model=StudentPersonalizationResponse)
async def get_personalization_dashboard(user_id: str) -> StudentPersonalizationResponse:
    return learning_intelligence.personalization_dashboard(user_id)


@app.get("/app-ai/training-queue/{user_id}", response_model=PersonalizedTrainingQueueResponse)
async def get_personalized_training_queue(
    user_id: str,
    subject: str = "mixed",
    count: int = 8,
) -> PersonalizedTrainingQueueResponse:
    return learning_intelligence.personalized_training_queue(
        user_id=user_id,
        subject=subject,
        count=max(1, min(count, 12)),
    )


@app.get("/app-ai/weakness-deep-dive/{user_id}", response_model=WeaknessDeepDiveResponse)
async def get_weakness_deep_dive(
    user_id: str,
    target: str | None = None,
) -> WeaknessDeepDiveResponse:
    return learning_intelligence.weakness_deep_dive(user_id=user_id, target=target)


@app.post("/app-ai/diagnostic/start", response_model=DiagnosticStartResponse)
async def start_diagnostic(request: DiagnosticStartRequest) -> DiagnosticStartResponse:
    return learning_intelligence.start_diagnostic(request)


@app.post("/app-ai/diagnostic/submit", response_model=DiagnosticSubmitResponse)
async def submit_diagnostic(request: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
    return learning_intelligence.submit_diagnostic(request)


@app.post("/app-ai/solution-variants", response_model=SolutionVariantsResponse)
async def get_solution_variants(request: SolutionVariantsRequest) -> SolutionVariantsResponse:
    return await learning_intelligence.solution_variants(request)


@app.post("/app-ai/tutor-hint", response_model=TutorHintResponse)
async def get_tutor_hint(request: TutorHintRequest) -> TutorHintResponse:
    return await learning_intelligence.tutor_hint(request)


@app.get("/app-ai/error-taxonomy/{user_id}", response_model=ErrorTaxonomyResponse)
async def get_error_taxonomy(user_id: str) -> ErrorTaxonomyResponse:
    return learning_intelligence.error_taxonomy(user_id)


@app.get("/app-ai/weekly-plan/{user_id}", response_model=WeeklyPlanResponse)
async def get_weekly_plan(user_id: str) -> WeeklyPlanResponse:
    return learning_intelligence.weekly_plan(user_id)


@app.post("/app-ai/answer-check", response_model=AnswerCheckResponse)
async def check_answer(request: AnswerCheckRequest) -> AnswerCheckResponse:
    return learning_intelligence.answer_check(request)


@app.post("/app-ai/mock-exam/start", response_model=MockExamStartResponse)
async def start_mock_exam(request: MockExamStartRequest) -> MockExamStartResponse:
    return learning_intelligence.start_mock_exam(request)


@app.post("/app-ai/mock-exam/submit", response_model=MockExamSubmitResponse)
async def submit_mock_exam(request: MockExamSubmitRequest) -> MockExamSubmitResponse:
    return learning_intelligence.submit_mock_exam(request)


@app.get("/app-ai/flashcards/{user_id}", response_model=FlashcardResponse)
async def get_flashcards(user_id: str, subject: str = "mixed") -> FlashcardResponse:
    return learning_intelligence.flashcards(user_id=user_id, subject=subject)


@app.get("/app-ai/mistake-notebook/{user_id}", response_model=MistakeNotebookResponse)
async def get_mistake_notebook(user_id: str) -> MistakeNotebookResponse:
    return learning_intelligence.mistake_notebook(user_id)


@app.get("/students/{user_id}/insight", response_model=StudentInsight)
async def get_student_insight(user_id: str) -> StudentInsight:
    return student_repo.get_insight(user_id)


@app.get("/students/{user_id}/attempts", response_model=list[AttemptHistoryItem])
async def list_student_attempts(user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
    return student_repo.list_attempts(user_id, limit=limit)


@app.get("/students/{user_id}/attempts/wrong", response_model=list[AttemptHistoryItem])
async def list_wrong_attempts(user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
    return student_repo.list_wrong_attempts(user_id, limit=limit)


@app.get("/students/{user_id}/attempts/slow", response_model=list[AttemptHistoryItem])
async def list_slow_attempts(user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
    return student_repo.list_slow_attempts(user_id, limit=limit)


@app.get("/students/{user_id}/progress", response_model=StudentProgress)
async def get_student_progress(user_id: str) -> StudentProgress:
    return student_repo.get_progress(user_id)


@app.get("/students/{user_id}/recommendation", response_model=StudyRecommendation)
async def get_study_recommendation(user_id: str) -> StudyRecommendation:
    return student_repo.get_recommendation(user_id)


@app.get("/students/{user_id}/review", response_model=ReviewBundle)
async def get_review_bundle(user_id: str) -> ReviewBundle:
    return student_repo.get_review_bundle(user_id)


@app.get("/study/concepts", response_model=ConceptSummary)
async def get_concept_summary(subject: str = "math", unit: str | None = None) -> ConceptSummary:
    return study_guide.concept_summary(subject=subject, unit=unit)


@app.get("/study/formulas", response_model=FormulaNote)
async def get_formula_note(subject: str = "math") -> FormulaNote:
    return study_guide.formula_note(subject=subject)


@app.get("/students/{user_id}/learning-route", response_model=LearningRoute)
async def get_learning_route(user_id: str) -> LearningRoute:
    return study_guide.learning_route(user_id)


@app.get("/practice/generate", response_model=ProblemSet)
async def generate_practice_set(
    subject: str = "math",
    difficulty: str = "same",
    count: int = 5,
    unit: str | None = None,
) -> ProblemSet:
    return problem_generator.generate_set(
        subject=subject,
        difficulty=difficulty,
        count=count,
        unit=unit,
    )


@app.get("/students/{user_id}/expected-problems", response_model=ProblemSet)
async def get_expected_problems(user_id: str, subject: str = "math") -> ProblemSet:
    return problem_generator.expected_set(user_id=user_id, subject=subject)


@app.get("/students/{user_id}/adaptive-problems", response_model=ProblemSet)
async def get_adaptive_problems(user_id: str, subject: str = "math") -> ProblemSet:
    return problem_generator.adaptive_set(user_id=user_id, subject=subject)


@app.get("/students/{user_id}/targeted-practice", response_model=ProblemSet)
async def get_targeted_practice(
    user_id: str,
    subject: str = "mixed",
    count: int = 8,
) -> ProblemSet:
    return problem_generator.targeted_set(
        user_id=user_id,
        subject=subject,
        count=max(1, min(count, 12)),
    )
