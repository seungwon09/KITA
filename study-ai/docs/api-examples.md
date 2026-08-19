# API 예시

## 문제 풀이

```http
POST /solve
Content-Type: application/json
```

```json
{
  "user_id": "student-1",
  "problem_text": "함수 조건을 만족할 때 최댓값을 구하시오",
  "subject": "math",
  "student_level": "intermediate",
  "mode": "compare",
  "elapsed_seconds": 220,
  "was_correct": false
}
```

## 학생 약점 분석

```http
GET /students/student-1/insight
```
