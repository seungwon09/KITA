# Study AI App API

앱에서는 우선 모바일용 API를 붙이면 됩니다.

## Endpoint

추천:

- 앱 시작: `GET /app-ai/mobile/bootstrap/{user_id}?plan=pro`
- 텍스트 문제: `POST /app-ai/mobile/analyze`
- 사진 문제: `POST /app-ai/mobile/ocr-analyze`
- 버튼형 UI 완성 연결: `GET /app-ai/production/registry` 후 `POST /app-ai/production/action`

기존 단일 분석 API:

`POST /app-ai/analyze`

## Request

```json
{
  "user_id": "student-1",
  "problem_text": "이차함수 y=x^2-4x+1의 최솟값을 구하시오",
  "subject": "math",
  "plan": "pro",
  "student_level": "intermediate",
  "user_solution": "x=2일 때 y=-3",
  "elapsed_seconds": 80,
  "was_correct": true,
  "time_limit_seconds": 90,
  "include_practice": true
}
```

## Response 핵심 필드

- `solve`: 기본 풀이, 빠른 풀이, 검산 답
- `evaluation`: 학생 풀이 평가
- `mistake_report`: 실수 감지
- `exam_strategy`: 시험장에서의 시간 전략
- `insight`: 학생 약점
- `recommendation`: 오늘 학습 추천
- `learning_route`: 맞춤 학습 루트
- `practice_set`: 추가 훈련 문제
- `feature_access`: 요금제별 허용/잠금 기능
- `ui_cards`: 앱 화면에 바로 뿌릴 수 있는 카드형 요약

## 요금제 값

- `free`
- `basic`
- `pro`
- `premium`

## 추가 앱용 API

- `GET /app-ai/mobile/config`
- `GET /app-ai/mobile/bootstrap/{user_id}?plan=pro`
- `POST /app-ai/mobile/analyze`
- `POST /app-ai/mobile/ocr-analyze`
- `GET /app-ai/production/status`
- `GET /app-ai/production/registry`
- `POST /app-ai/production/action`
- `GET /app-ai/home/{user_id}?plan=pro`
- `POST /app-ai/batch-analyze`
- `GET /app-ai/capabilities`
- `GET /app-ai/plans`
- `POST /app-ai/gate`
- `GET /app-ai/session/{user_id}?plan=pro`
- `GET /app-ai/usage/{user_id}?plan=pro`
- `GET /app-ai/learning-style/{user_id}`
- `GET /app-ai/mental/{user_id}`
- `GET /app-ai/speed/{user_id}`
- `GET /app-ai/study-session/{user_id}?plan=pro&subject=math`
- `GET /app-ai/review-schedule/{user_id}`
- `GET /app-ai/export/{user_id}`
- `POST /app-ai/feedback`
- `GET /admin/smoke-test`
- `GET /app-ai/profile/{user_id}`
- `POST /app-ai/profile`
- `POST /app-ai/bookmark`
- `GET /app-ai/bookmarks/{user_id}`
- `GET /app-ai/report/{user_id}`
- `GET /app-ai/achievements/{user_id}`
- `GET /app-ai/leaderboard/{user_id}`
- `GET /app-ai/notifications/{user_id}`
- `GET /app-ai/mastery/{user_id}`
- `GET /app-ai/personalization/{user_id}`
- `GET /app-ai/training-queue/{user_id}?subject=mixed&count=8`
- `GET /app-ai/weakness-deep-dive/{user_id}`
- `GET /students/{user_id}/targeted-practice?subject=mixed&count=8`
- `POST /app-ai/diagnostic/start`
- `POST /app-ai/diagnostic/submit`
- `POST /app-ai/solution-variants`
- `POST /app-ai/tutor-hint`
- `GET /app-ai/error-taxonomy/{user_id}`
- `GET /app-ai/weekly-plan/{user_id}`
- `POST /app-ai/answer-check`
- `POST /app-ai/mock-exam/start`
- `POST /app-ai/mock-exam/submit`
- `GET /app-ai/flashcards/{user_id}?subject=mixed`
- `GET /app-ai/mistake-notebook/{user_id}`

`/app-ai/home/{user_id}`는 앱 첫 화면에 필요한 사용량, 성장 추적, 추천, 학습 스타일, 멘탈, 속도 진단을 한 번에 줍니다.
`/app-ai/session/{user_id}`는 앱 시작 시 UI 잠금 상태와 홈 데이터를 같이 줍니다.
`/app-ai/personalization/{user_id}`는 단원/유형별 숙련도와 약점 점수를 줍니다.
`/app-ai/training-queue/{user_id}`는 오늘 바로 풀 문제 큐를 줍니다.
`/students/{user_id}/targeted-practice`는 약점 기반 문제 세트를 바로 줍니다.

## 모바일 앱 텍스트 분석

```json
{
  "user_id": "student-1",
  "problem_text": "전력 60W, 전압 12V일 때 전류를 구하시오",
  "subject": "science",
  "plan": "pro",
  "student_level": "intermediate",
  "user_solution": null,
  "elapsed_seconds": 45,
  "was_correct": true,
  "time_limit_seconds": 90,
  "include_practice": true,
  "include_home": true,
  "include_personalization": true,
  "include_training_queue": true
}
```

응답은 `analyze`, `home`, `personalization`, `training_queue`를 한 번에 줍니다.

## 모바일 앱 사진 분석

`multipart/form-data`

- `image`: 문제 사진 파일
- `user_id`: `student-1`
- `subject`: `auto`, `math`, `science`
- `plan`: `pro`
- `auto_solve`: `true`

예제 클라이언트 파일:

`client_examples/study_ai_client.js`

사진/OCR 응답 핵심 필드:

- `ocr.extracted_text`: 앱 입력창에 넣을 최종 보정 텍스트
- `ocr.raw_text`: OCR 원본
- `ocr.detected_subject`: `math`, `science`, `unknown`
- `ocr.corrections`: 자동 보정 내용
- `ocr.warnings`: 사용자가 확인해야 할 부분
- `ocr.needs_review`: 앱에서 확인 UI를 띄울지 여부

## 요금제/기능 제한

앱 시작 시 `GET /app-ai/session/{user_id}?plan=pro` 또는 `GET /app-ai/mobile/bootstrap/{user_id}?plan=pro`를 호출하세요.

UI 잠금은 `feature_flags`와 `feature_access.locked_features`를 기준으로 처리하면 됩니다.

주요 기능 키:

- `fast_solution`
- `solution_evaluation`
- `adaptive_practice`
- `training_queue`
- `personalization`
- `ocr_analyze`
- `mobile_bundle`

개별 기능 확인은 `POST /app-ai/gate`를 쓰면 됩니다.

## 완성형 UI 연결 방식

UI 버튼을 직접 여러 API에 연결하지 않고, 아래 흐름으로 붙이면 됩니다.

1. 앱 시작 시 `GET /app-ai/production/registry`
2. 응답의 `features`를 보고 버튼을 만듭니다.
3. 버튼 클릭 시 `POST /app-ai/production/action`에 `action`만 바꿔서 보냅니다.
4. 응답의 `ui_target`에 따라 화면 영역을 업데이트합니다.

예:

```json
{
  "action": "training_queue",
  "user_id": "student-1",
  "plan": "pro",
  "subject": "mixed",
  "count": 8
}
```

주요 action:

- `solve`
- `mobile_analyze`
- `personalization`
- `training_queue`
- `targeted_practice`
- `weakness_deep_dive`
- `concept`
- `formula`
- `learning_route`
- `progress`
- `review`
- `mastery`
- `weekly_plan`
- `flashcards`
- `mistake_notebook`
- `diagnostic_start`
- `mock_exam_start`
- `plans`

## Batch Analyze

```json
{
  "user_id": "student-1",
  "plan": "pro",
  "student_level": "intermediate",
  "time_limit_seconds": 90,
  "items": [
    {
      "problem_text": "x^2-5x+6=0을 푸시오",
      "subject": "math",
      "elapsed_seconds": 80,
      "was_correct": true
    }
  ]
}
```
