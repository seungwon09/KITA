from app.models.schemas import RoadmapFeatureStatus, RoadmapStatusResponse


class RoadmapService:
    def status(self) -> RoadmapStatusResponse:
        features = self._features()
        ready = [item for item in features if item.status == "ready"]
        partial = [item for item in features if item.status == "partial"]
        average = round(sum(item.completion_percent for item in features) / len(features))
        return RoadmapStatusResponse(
            total_features=len(features),
            ready_count=len(ready),
            partial_count=len(partial),
            backend_average_percent=average,
            app_integration_ready=True,
            features=features,
            next_backend_priorities=[
                "사진 OCR 실제 교정 데이터 100개 이상 수집",
                "수학/과학 단원별 규칙 풀이 50유형까지 확장",
                "상위권 풀이 샘플을 유형별로 20개씩 축적",
            ],
            next_ui_priorities=[
                "사진 촬영 후 OCR 확인/수정 화면",
                "풀이 탭: 기본/빠른/비교/힌트",
                "오답노트와 맞춤 훈련큐 화면",
            ],
        )

    def _features(self) -> list[RoadmapFeatureStatus]:
        data = [
            (1, "기본 풀이", "ready", 92, "/solve", "solve", False, False, "수학·과학 빈출 규칙 풀이 확장, 검증 스위트와 로컬 모델 fallback 연결 완료"),
            (2, "빠른 풀이", "ready", 90, "/app-ai/elite/solution", "elite_solution", False, True, "대표 유형 빠른 풀이와 상위권 압축 풀이 패턴 확장 완료"),
            (3, "풀이 방식 비교", "partial", 75, "/app-ai/elite/solution", "elite_solution", True, True, "기본/빠른/상위권 풀이 비교용 데이터 제공, UI 탭 구성 필요"),
            (4, "문제 분석 AI", "ready", 90, "/app-ai/problem/recognize", "problem_recognition", False, False, "OCR 수식 정규화와 과목/단원/유형/조건 구조화 API 연결 완료"),
            (5, "학생 실력 분석", "ready", 76, "/app-ai/personalization/{user_id}", "personalization", False, True, "기록 기반 분석 가능, 데이터가 많을수록 향상"),
            (6, "시간 분석", "ready", 72, "/app-ai/speed/{user_id}", "progress", False, True, "평균/최근 시간과 병목 분석 가능"),
            (7, "사용자 풀이 평가", "ready", 74, "/app-ai/quality/check", "quality_check", False, True, "답안 검산/위험 신호 확인 가능"),
            (8, "상위권 데이터 학습", "ready", 86, "/app-ai/elite/patterns", "elite_patterns", False, True, "상위권 풀이 패턴 라이브러리 확장, 고급 풀이 API, 샘플 저장 구조 완료"),
            (9, "AI 티칭", "partial", 65, "/app-ai/tutor-hint", "solve", True, True, "힌트 API 있음, 단계형 대화 UI 필요"),
            (10, "AI 난이도 조절", "ready", 70, "/app-ai/training-queue/{user_id}", "training_queue", False, True, "기록 기반 난이도 조절 가능"),
            (11, "실전 시험 모드", "partial", 68, "/app-ai/mock-exam/start", "mock_exam_start", True, False, "모의고사 API 있음, 타이머 UI 필요"),
            (12, "AI 오답노트", "ready", 73, "/app-ai/mistake-notebook/{user_id}", "mistake_notebook", False, True, "오답 그룹/복습 계획 제공"),
            (13, "AI 문제 생성", "ready", 70, "/practice/generate", "targeted_practice", False, True, "대표 유형 생성 가능"),
            (14, "AI 예상 문제", "partial", 58, "/students/{user_id}/expected-problems", "targeted_practice", False, True, "출제 경향 데이터가 더 필요"),
            (15, "AI 학습 루트", "ready", 72, "/students/{user_id}/learning-route", "learning_route", False, True, "맞춤 루트 API 준비"),
            (16, "AI 멘탈 분석", "ready", 62, "/app-ai/mental/{user_id}", "home", False, True, "시간/오답 신호 기반"),
            (17, "AI 경쟁 시스템", "partial", 45, "/app-ai/leaderboard/{user_id}", "home", True, True, "랭킹 API는 있음, 실제 사용자 데이터 필요"),
            (18, "AI 압축 요약", "ready", 75, "/study/concepts", "concept", False, False, "개념/공식 요약 가능"),
            (19, "AI 기억 시스템", "ready", 78, "/app-ai/export/{user_id}", "personalization", False, True, "학생 기록 저장/추적 가능"),
            (20, "AI 학습 스타일 분석", "ready", 64, "/app-ai/learning-style/{user_id}", "home", False, True, "행동 데이터 기반 추정"),
            (21, "AI 속도 최적화", "ready", 70, "/app-ai/speed/{user_id}", "progress", False, True, "목표 시간/훈련 추천 가능"),
            (22, "AI 전략 추천", "ready", 76, "/app-ai/problem/recognize", "problem_recognition", False, True, "유형별 전략 태그 제공"),
            (23, "AI 시험 전략", "partial", 66, "/app-ai/mock-exam/start", "mock_exam_start", True, True, "문제 순서/스킵 전략 기본 제공"),
            (24, "AI 성장 추적", "ready", 72, "/students/{user_id}/progress", "progress", False, True, "정답률/시간 추이 제공"),
            (25, "AI 개념 압축", "ready", 75, "/study/concepts", "concept", False, False, "한 줄 개념/패턴/실수 제공"),
            (26, "AI 실수 감지", "ready", 72, "/app-ai/quality/check", "quality_check", False, True, "답안 불일치/시간 초과/검산 위험 신호 제공"),
            (27, "AI 복습 시스템", "ready", 70, "/app-ai/review-schedule/{user_id}", "review", False, True, "복습 일정/재출제 후보 제공"),
            (28, "AI 학습 추천", "ready", 76, "/students/{user_id}/recommendation", "home", False, True, "오늘 할 일/복습 대상 추천"),
            (29, "AI 질문 기능", "partial", 62, "/app-ai/mobile/analyze", "mobile_analyze", True, True, "답변 API 있음, 채팅 UI 필요"),
            (30, "점수 상승형 통합 목표", "partial", 68, "/app-ai/mobile/bootstrap/{user_id}", "app_bootstrap", True, True, "핵심 백엔드 연결됨, 실제 앱 UX/데이터 축적 필요"),
        ]
        return [
            RoadmapFeatureStatus(
                id=item[0],
                name=item[1],
                status=item[2],
                completion_percent=item[3],
                backend_endpoint=item[4],
                production_action=item[5],
                needs_ui=item[6],
                needs_more_data=item[7],
                note=item[8],
            )
            for item in data
        ]
