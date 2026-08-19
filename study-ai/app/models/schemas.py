from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StudentLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class SolveMode(str, Enum):
    basic = "basic"
    fast = "fast"
    compare = "compare"
    tutor = "tutor"


class ProblemSolveRequest(BaseModel):
    user_id: str | None = None
    problem_text: str = Field(..., min_length=1)
    subject: str | None = "math"
    student_level: StudentLevel = StudentLevel.intermediate
    mode: SolveMode = SolveMode.compare
    user_solution: str | None = None
    elapsed_seconds: int | None = None
    was_correct: bool | None = None


class ProblemAnalysis(BaseModel):
    subject: str
    unit: str
    problem_type: str
    difficulty: str
    intent: str
    is_killer: bool


class SolveResponse(BaseModel):
    analysis: ProblemAnalysis
    basic_solution: str
    fast_solution: str
    wrong_answer_reasons: list[str]
    similar_problem: str
    tutor_hint: str
    recommended_next_action: str
    verified_answer: str | None = None
    quality_warnings: list[str] = []
    engine: str = "local_llm"
    expected_speed: str = "slow"


class AttemptRecord(BaseModel):
    user_id: str
    problem_text: str
    subject: str
    unit: str
    problem_type: str
    difficulty: str
    elapsed_seconds: int | None = None
    was_correct: bool | None = None


class AttemptHistoryItem(AttemptRecord):
    id: int
    created_at: str


class StudentInsight(BaseModel):
    user_id: str
    total_attempts: int
    weak_units: list[str]
    slow_types: list[str]
    repeated_mistakes: list[str]
    next_recommendation: str


class StudentProgress(BaseModel):
    user_id: str
    total_attempts: int
    correct_attempts: int
    wrong_attempts: int
    accuracy_percent: float
    average_elapsed_seconds: float | None = None
    recent_average_elapsed_seconds: float | None = None
    trend_message: str


class StudyRecommendation(BaseModel):
    user_id: str
    priority: str
    today_plan: list[str]
    review_targets: list[str]
    recommended_problem_types: list[str]
    recommended_problems: list[str]
    message: str


class ReviewBundle(BaseModel):
    user_id: str
    wrong_items: list[AttemptHistoryItem]
    slow_items: list[AttemptHistoryItem]
    today_review: list[str]
    retry_problems: list[str]
    message: str


class ConceptSummary(BaseModel):
    subject: str
    unit: str
    one_line: str
    core_points: list[str]
    exam_patterns: list[str]
    common_mistakes: list[str]
    quick_check: str


class FormulaNote(BaseModel):
    subject: str
    formulas: list[dict[str, str]]
    must_memorize: list[str]
    use_when: list[str]


class LearningRoute(BaseModel):
    user_id: str
    priority: str
    route: list[str]
    daily_mission: list[str]
    next_unlock: str
    message: str


class GeneratedProblem(BaseModel):
    problem: str
    subject: str
    unit: str
    difficulty: str
    target_skill: str
    expected_answer: str


class ProblemSet(BaseModel):
    subject: str
    difficulty: str
    problems: list[GeneratedProblem]
    message: str


class FeatureAccess(BaseModel):
    plan: str
    allowed_features: list[str]
    locked_features: list[str]
    daily_limit: int
    used_today: int = 0
    remaining_today: int = 0
    response_depth: str


class UserSolutionEvaluation(BaseModel):
    score: int
    verdict: str
    strengths: list[str]
    missing_steps: list[str]
    mistake_candidates: list[str]
    faster_rewrite: str
    next_action: str


class MistakeReport(BaseModel):
    risk_level: str
    detected_mistakes: list[str]
    likely_causes: list[str]
    fix_drill: list[str]


class ExamStrategy(BaseModel):
    elapsed_seconds: int | None
    time_limit_seconds: int
    speed_judgement: str
    recommended_order: list[str]
    skip_rule: str
    pressure_tip: str


class AppAiCard(BaseModel):
    title: str
    body: str
    action: str


class AppAiRequest(BaseModel):
    user_id: str = "student-1"
    problem_text: str = Field(..., min_length=1)
    subject: str | None = "math"
    plan: str = "free"
    student_level: StudentLevel = StudentLevel.intermediate
    user_solution: str | None = None
    elapsed_seconds: int | None = None
    was_correct: bool | None = None
    time_limit_seconds: int = 90
    include_practice: bool = True


class AppAiResponse(BaseModel):
    api_version: str
    request_id: str
    feature_access: FeatureAccess
    solve: SolveResponse
    evaluation: UserSolutionEvaluation
    mistake_report: MistakeReport
    exam_strategy: ExamStrategy
    insight: StudentInsight
    recommendation: StudyRecommendation
    learning_route: LearningRoute
    practice_set: ProblemSet | None = None
    ui_cards: list[AppAiCard]


class BatchProblemInput(BaseModel):
    problem_text: str = Field(..., min_length=1)
    subject: str | None = "math"
    user_solution: str | None = None
    elapsed_seconds: int | None = None
    was_correct: bool | None = None


class AppAiBatchRequest(BaseModel):
    user_id: str = "student-1"
    plan: str = "free"
    student_level: StudentLevel = StudentLevel.intermediate
    time_limit_seconds: int = 90
    items: list[BatchProblemInput]


class AppAiBatchResponse(BaseModel):
    api_version: str
    user_id: str
    total: int
    results: list[AppAiResponse]
    summary_cards: list[AppAiCard]


class AppAiCapabilities(BaseModel):
    api_version: str
    primary_endpoint: str
    endpoints: list[dict[str, str]]
    plans: dict[str, list[str]]
    recommended_app_flow: list[str]


class UsageSnapshot(BaseModel):
    user_id: str
    plan: str
    used_today: int
    daily_limit: int
    remaining_today: int
    reset_at: str


class PlanInfo(BaseModel):
    plan: str
    price_label: str
    daily_limit: int
    features: list[str]
    locked_features: list[str]
    recommended_for: str


class PlanCatalog(BaseModel):
    default_plan: str
    plans: list[PlanInfo]


class FeatureGateRequest(BaseModel):
    user_id: str = "student-1"
    plan: str = "free"
    feature: str = "fast_solution"


class FeatureGateResponse(BaseModel):
    allowed: bool
    feature: str
    plan: str
    reason: str
    upgrade_to: str | None = None
    usage: UsageSnapshot | None = None


class StudySessionResponse(BaseModel):
    user_id: str
    title: str
    estimated_minutes: int
    warmup: list[str]
    main_problems: list[GeneratedProblem]
    review: list[str]
    finish_rule: str


class ReviewScheduleResponse(BaseModel):
    user_id: str
    today: list[str]
    tomorrow: list[str]
    later: list[str]
    message: str


class AdminSmokeTestResponse(BaseModel):
    ok: bool
    checks: list[dict[str, str]]


class StudentDataExport(BaseModel):
    user_id: str
    attempts: list[AttemptHistoryItem]
    wrong_items: list[AttemptHistoryItem]
    slow_items: list[AttemptHistoryItem]
    progress: StudentProgress
    insight: StudentInsight
    review: ReviewBundle
    recommendation: StudyRecommendation


class LearningStyleProfile(BaseModel):
    user_id: str
    primary_style: str
    confidence: float
    evidence: list[str]
    best_study_method: list[str]
    avoid: list[str]


class MentalAnalysis(BaseModel):
    user_id: str
    pressure_risk: str
    signals: list[str]
    intervention: list[str]
    exam_day_tip: str


class SpeedOptimization(BaseModel):
    user_id: str
    average_seconds: float | None
    target_seconds: int
    bottlenecks: list[str]
    drills: list[str]
    message: str


class AppHomeResponse(BaseModel):
    user_id: str
    usage: UsageSnapshot
    progress: StudentProgress
    insight: StudentInsight
    recommendation: StudyRecommendation
    learning_style: LearningStyleProfile
    mental_analysis: MentalAnalysis
    speed_optimization: SpeedOptimization
    quick_actions: list[str]
    dashboard_cards: list[AppAiCard]


class AppSessionResponse(BaseModel):
    user_id: str
    plan: str
    api_version: str
    home: AppHomeResponse
    capabilities: AppAiCapabilities
    feature_flags: dict[str, bool]
    startup_actions: list[str]


class FeedbackRequest(BaseModel):
    user_id: str = "student-1"
    request_id: str | None = None
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
    problem_text: str | None = None
    was_helpful: bool = True


class FeedbackResponse(BaseModel):
    saved: bool
    message: str


class StudentProfileRequest(BaseModel):
    user_id: str = "student-1"
    nickname: str = "학생"
    grade: str = "미설정"
    target_exam: str = "내신/수능"
    target_score: str = "점수 상승"
    preferred_subjects: list[str] = ["math", "science"]
    goal_message: str = "시험 점수 올리기"


class StudentProfileResponse(StudentProfileRequest):
    saved: bool = True
    message: str = "프로필이 저장되었습니다."


class BookmarkRequest(BaseModel):
    user_id: str = "student-1"
    problem_text: str = Field(..., min_length=1)
    subject: str = "math"
    note: str | None = None


class BookmarkItem(BookmarkRequest):
    id: int
    created_at: str


class BookmarkListResponse(BaseModel):
    user_id: str
    bookmarks: list[BookmarkItem]


class Achievement(BaseModel):
    key: str
    title: str
    description: str
    unlocked: bool
    progress: str


class AchievementResponse(BaseModel):
    user_id: str
    achievements: list[Achievement]
    next_badge: str


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    score: int
    label: str


class LeaderboardResponse(BaseModel):
    user_id: str
    my_rank: int
    entries: list[LeaderboardEntry]
    message: str


class NotificationPlanResponse(BaseModel):
    user_id: str
    push_messages: list[str]
    quiet_hours: str
    best_send_times: list[str]
    message: str


class StudentReportResponse(BaseModel):
    user_id: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    next_7_days: list[str]
    parent_message: str
    teacher_message: str


class MasteryUnit(BaseModel):
    unit: str
    total_attempts: int
    accuracy_percent: float
    average_seconds: float | None
    mastery_score: int
    level: str
    next_action: str


class MasteryMapResponse(BaseModel):
    user_id: str
    units: list[MasteryUnit]
    strongest_unit: str
    weakest_unit: str
    message: str


class DiagnosticQuestion(BaseModel):
    question_id: str
    problem: str
    subject: str
    unit: str
    difficulty: str
    target_skill: str
    expected_answer: str


class DiagnosticStartRequest(BaseModel):
    subject: str = "mixed"
    count: int = Field(default=8, ge=2, le=12)
    difficulty: str = "same"


class DiagnosticStartResponse(BaseModel):
    diagnostic_id: str
    questions: list[DiagnosticQuestion]
    time_limit_minutes: int
    instructions: list[str]


class DiagnosticAnswerInput(BaseModel):
    question_id: str
    problem: str
    subject: str
    unit: str
    target_skill: str
    expected_answer: str
    student_answer: str
    elapsed_seconds: int | None = None


class DiagnosticSubmitRequest(BaseModel):
    user_id: str = "student-1"
    diagnostic_id: str
    answers: list[DiagnosticAnswerInput]


class DiagnosticResultItem(BaseModel):
    question_id: str
    correct: bool
    expected_answer: str
    student_answer: str
    unit: str
    target_skill: str
    feedback: str


class DiagnosticSubmitResponse(BaseModel):
    user_id: str
    diagnostic_id: str
    score_percent: float
    placement: str
    weak_units: list[str]
    strong_units: list[str]
    results: list[DiagnosticResultItem]
    recommended_start: str


class SolutionVariantsRequest(BaseModel):
    problem_text: str = Field(..., min_length=1)
    subject: str | None = "math"
    student_level: StudentLevel = StudentLevel.intermediate


class SolutionVariantsResponse(BaseModel):
    problem_text: str
    verified_answer: str | None
    beginner_solution: str
    standard_solution: str
    fast_solution: str
    exam_solution: str
    top_student_solution: str


class TutorHintRequest(BaseModel):
    problem_text: str = Field(..., min_length=1)
    subject: str | None = "math"
    step: int = Field(default=1, ge=1, le=4)
    reveal_answer: bool = False


class TutorHintResponse(BaseModel):
    step: int
    hint: str
    next_prompt: str
    reveal_answer: str | None = None


class ErrorTaxonomyItem(BaseModel):
    category: str
    severity: str
    count: int
    evidence: list[str]
    fix: list[str]


class ErrorTaxonomyResponse(BaseModel):
    user_id: str
    items: list[ErrorTaxonomyItem]
    priority_fix: str


class WeeklyPlanDay(BaseModel):
    day: int
    focus: str
    tasks: list[str]
    success_rule: str


class WeeklyPlanResponse(BaseModel):
    user_id: str
    title: str
    days: list[WeeklyPlanDay]
    expected_outcome: str


class AnswerCheckRequest(BaseModel):
    problem_text: str | None = None
    expected_answer: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)
    subject: str | None = "math"


class AnswerCheckResponse(BaseModel):
    correct: bool
    partial_credit: int
    normalized_expected: str
    normalized_student: str
    matched_parts: list[str]
    missing_parts: list[str]
    feedback: str


class MockExamStartRequest(BaseModel):
    subject: str = "mixed"
    count: int = Field(default=10, ge=3, le=20)
    difficulty: str = "exam"
    time_limit_minutes: int = Field(default=20, ge=5, le=120)


class MockExamStartResponse(BaseModel):
    exam_id: str
    questions: list[DiagnosticQuestion]
    time_limit_minutes: int
    per_question_seconds: int
    recommended_strategy: list[str]


class MockExamAnswerInput(DiagnosticAnswerInput):
    marked_for_review: bool = False


class MockExamSubmitRequest(BaseModel):
    user_id: str = "student-1"
    exam_id: str
    time_limit_minutes: int = 20
    answers: list[MockExamAnswerInput]


class MockExamSubmitResponse(BaseModel):
    user_id: str
    exam_id: str
    score_percent: float
    correct_count: int
    total_count: int
    predicted_grade: str
    pacing_report: str
    skip_candidates: list[str]
    results: list[DiagnosticResultItem]
    next_training: list[str]


class FlashcardItem(BaseModel):
    front: str
    back: str
    subject: str
    unit: str
    tag: str


class FlashcardResponse(BaseModel):
    user_id: str
    cards: list[FlashcardItem]
    message: str


class MistakeNotebookGroup(BaseModel):
    title: str
    count: int
    problems: list[str]
    root_cause: str
    retry_plan: list[str]


class MistakeNotebookResponse(BaseModel):
    user_id: str
    groups: list[MistakeNotebookGroup]
    priority: str


class SkillProfile(BaseModel):
    subject: str
    unit: str
    problem_type: str
    attempts: int
    correct_attempts: int
    wrong_attempts: int
    accuracy_percent: float
    average_seconds: float | None = None
    recent_average_seconds: float | None = None
    speed_level: str
    mastery_score: int
    weakness_score: int
    label: str
    evidence: list[str]
    next_action: str


class StudentPersonalizationResponse(BaseModel):
    user_id: str
    learner_stage: str
    total_attempts: int
    overall_accuracy_percent: float
    average_seconds: float | None = None
    strongest_skills: list[str]
    weakest_skills: list[str]
    risk_flags: list[str]
    skill_profiles: list[SkillProfile]
    today_focus: str
    next_best_actions: list[str]
    routing_rules: list[str]


class TrainingQueueItem(BaseModel):
    problem: str
    subject: str
    unit: str
    difficulty: str
    mode: str
    target_seconds: int
    reason: str
    expected_benefit: str


class PersonalizedTrainingQueueResponse(BaseModel):
    user_id: str
    queue_title: str
    estimated_minutes: int
    items: list[TrainingQueueItem]
    finish_rule: str


class WeaknessDeepDiveResponse(BaseModel):
    user_id: str
    target: str
    root_causes: list[str]
    evidence: list[str]
    drills: list[str]
    success_metric: str
    escalation_rule: str


class MobileFeatureConfig(BaseModel):
    api_version: str
    base_url_hint: str
    default_plan: str
    supported_subjects: list[str]
    client_timeout_seconds: int
    image_upload_field: str
    endpoints: dict[str, str]
    required_request_fields: list[str]
    response_tabs: list[str]
    cors_origins: list[str]


class MobileNextCall(BaseModel):
    label: str
    method: str
    path: str
    when_to_call: str


class MobileAppBootstrapResponse(BaseModel):
    config: MobileFeatureConfig
    session: AppSessionResponse
    personalization: StudentPersonalizationResponse
    training_queue: PersonalizedTrainingQueueResponse
    next_calls: list[MobileNextCall]


class MobileAnalyzeRequest(AppAiRequest):
    include_home: bool = True
    include_personalization: bool = True
    include_training_queue: bool = True


class MobileAnalyzeResponse(BaseModel):
    config: MobileFeatureConfig
    analyze: AppAiResponse
    home: AppHomeResponse | None = None
    personalization: StudentPersonalizationResponse | None = None
    training_queue: PersonalizedTrainingQueueResponse | None = None
    next_client_actions: list[str]
    raw_debug: dict[str, Any] = {}


class MobileOcrAnalyzeResponse(BaseModel):
    config: MobileFeatureConfig
    ocr: OcrResponse
    analyze: AppAiResponse | None = None
    warning: str | None = None


class OcrResponse(BaseModel):
    extracted_text: str
    confidence: float
    raw_text: str | None = None
    normalized_text: str | None = None
    detected_subject: str = "unknown"
    detected_unit: str | None = None
    problem_type: str | None = None
    formula_candidates: list[str] = []
    numbers: list[str] = []
    corrections: list[str] = []
    warnings: list[str] = []
    needs_review: bool = False
    engine: str = "easyocr"
    preprocessing_steps: list[str] = []
    image_quality: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []


class ProblemRecognitionRequest(BaseModel):
    user_id: str | None = None
    problem_text: str = Field(..., min_length=1)
    subject: str = "auto"
    source: str = "typed"


class ProblemRecognitionResponse(BaseModel):
    original_text: str
    normalized_text: str
    detected_subject: str
    detected_unit: str
    problem_type: str
    formula_candidates: list[str]
    numbers: list[str]
    known_values: list[dict[str, str]]
    required_values: list[str]
    strategy_tags: list[str]
    solvable_by_rules: bool
    verified_answer: str | None = None
    confidence: float
    warnings: list[str]
    next_action: str


class QualityCheckRequest(BaseModel):
    user_id: str | None = None
    problem_text: str = Field(..., min_length=1)
    subject: str = "auto"
    expected_answer: str | None = None
    student_answer: str | None = None
    elapsed_seconds: int | None = None


class QualityCheckResponse(BaseModel):
    recognition: ProblemRecognitionResponse
    solver_engine: str
    verified_answer: str | None = None
    expected_answer_match: bool | None = None
    student_answer_match: bool | None = None
    confidence: float
    risk_flags: list[str]
    recommended_action: str
    solution_preview: dict[str, str]


class OcrCorrectionRequest(BaseModel):
    user_id: str = "student-1"
    raw_text: str | None = None
    extracted_text: str = Field(..., min_length=1)
    corrected_text: str = Field(..., min_length=1)
    detected_subject: str = "unknown"
    confidence: float | None = None
    source: str = "app"


class OcrCorrectionItem(OcrCorrectionRequest):
    id: int
    created_at: str


class OcrCorrectionResponse(BaseModel):
    saved: bool
    item: OcrCorrectionItem
    improvement_targets: list[str]
    message: str


class OcrCorrectionStatsResponse(BaseModel):
    total_corrections: int
    by_subject: dict[str, int]
    common_replacements: list[dict[str, str | int]]
    next_training_actions: list[str]


class RoadmapFeatureStatus(BaseModel):
    id: int
    name: str
    status: str
    completion_percent: int
    backend_endpoint: str | None = None
    production_action: str | None = None
    needs_ui: bool = False
    needs_more_data: bool = False
    note: str


class RoadmapStatusResponse(BaseModel):
    total_features: int
    ready_count: int
    partial_count: int
    backend_average_percent: int
    app_integration_ready: bool
    features: list[RoadmapFeatureStatus]
    next_backend_priorities: list[str]
    next_ui_priorities: list[str]


class ElitePattern(BaseModel):
    id: str
    subject: str
    unit: str
    problem_type: str
    trigger_keywords: list[str]
    shortcut: str
    exam_use: str
    calculation_reduction: str
    common_traps: list[str]
    time_target_seconds: int
    difficulty_band: str
    requires_verified_answer: bool = True


class EliteSolutionRequest(BaseModel):
    user_id: str = "student-1"
    problem_text: str = Field(..., min_length=1)
    subject: str = "auto"
    student_level: str = "advanced"
    elapsed_seconds: int | None = None
    mode: str = "exam"
    include_drills: bool = True


class EliteSolutionResponse(BaseModel):
    recognition: ProblemRecognitionResponse
    verified_answer: str | None = None
    selected_patterns: list[ElitePattern]
    top_student_solution: str
    exam_shortcut: str
    calculation_reduction: str
    traps: list[str]
    time_target_seconds: int
    confidence: float
    recommended_drills: list[str]
    data_readiness_percent: int
    next_action: str


class EliteTrainingDataRequest(BaseModel):
    user_id: str = "student-1"
    problem_text: str = Field(..., min_length=1)
    subject: str = "math"
    solution_text: str = Field(..., min_length=1)
    verified_answer: str | None = None
    source_level: str = "top_1_percent"
    elapsed_seconds: int | None = None
    tags: list[str] = []


class EliteTrainingDataItem(EliteTrainingDataRequest):
    id: int
    created_at: str


class EliteTrainingDataResponse(BaseModel):
    saved: bool
    item: EliteTrainingDataItem
    pattern_candidates: list[str]
    message: str


class EliteStatsResponse(BaseModel):
    total_samples: int
    by_subject: dict[str, int]
    by_source_level: dict[str, int]
    top_tags: list[dict[str, str | int]]
    readiness_percent: int
    next_training_actions: list[str]


class ProductionFeatureItem(BaseModel):
    action: str
    label: str
    category: str
    method: str
    endpoint: str
    required_plan: str
    required_feature: str
    ui_target: str
    description: str


class ProductionFeatureRegistryResponse(BaseModel):
    api_version: str
    recommended_base_url: str
    features: list[ProductionFeatureItem]
    default_flow: list[str]


class ProductionActionRequest(BaseModel):
    action: str
    user_id: str = "student-1"
    plan: str = "pro"
    subject: str = "math"
    problem_text: str | None = None
    user_solution: str | None = None
    elapsed_seconds: int | None = None
    was_correct: bool | None = None
    time_limit_seconds: int = 90
    count: int = 8
    target: str | None = None
    payload: dict[str, Any] = {}


class ProductionActionResponse(BaseModel):
    action: str
    allowed: bool
    plan: str
    ui_target: str
    result: dict[str, Any]
    next_actions: list[str]
    warnings: list[str] = []


class ProductionStatusResponse(BaseModel):
    ok: bool
    api_version: str
    server: str
    model: str
    mock_llm: bool
    database_ready: bool
    feature_count: int
    checks: list[dict[str, str]]
