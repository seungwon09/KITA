import difflib
import os
import sqlite3
from datetime import date
from pathlib import Path

from app.models.schemas import (
    AttemptHistoryItem,
    AttemptRecord,
    BookmarkItem,
    BookmarkRequest,
    EliteStatsResponse,
    EliteTrainingDataItem,
    EliteTrainingDataRequest,
    EliteTrainingDataResponse,
    OcrCorrectionItem,
    OcrCorrectionRequest,
    OcrCorrectionResponse,
    OcrCorrectionStatsResponse,
    ReviewBundle,
    StudentProfileRequest,
    StudentProfileResponse,
    StudentInsight,
    StudentProgress,
    StudyRecommendation,
)


class StudentRepository:
    def __init__(self) -> None:
        db_path = Path(os.getenv("STUDY_AI_DB_PATH", Path(__file__).resolve().parents[2] / "study_ai.sqlite3"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    problem_text TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    problem_type TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    elapsed_seconds INTEGER,
                    was_correct INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    request_id TEXT,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    problem_text TEXT,
                    was_helpful INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS student_profiles (
                    user_id TEXT PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    target_exam TEXT NOT NULL,
                    target_score TEXT NOT NULL,
                    preferred_subjects TEXT NOT NULL,
                    goal_message TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    problem_text TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ocr_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    raw_text TEXT,
                    extracted_text TEXT NOT NULL,
                    corrected_text TEXT NOT NULL,
                    detected_subject TEXT NOT NULL,
                    confidence REAL,
                    source TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS elite_solution_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    problem_text TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    solution_text TEXT NOT NULL,
                    verified_answer TEXT,
                    source_level TEXT NOT NULL,
                    elapsed_seconds INTEGER,
                    tags TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_attempt(self, record: AttemptRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO attempts (
                    user_id, problem_text, subject, unit, problem_type,
                    difficulty, elapsed_seconds, was_correct
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.user_id,
                    record.problem_text,
                    record.subject,
                    record.unit,
                    record.problem_type,
                    record.difficulty,
                    record.elapsed_seconds,
                    None if record.was_correct is None else int(record.was_correct),
                ),
            )

    def record_usage(self, user_id: str, plan: str, event_type: str = "analyze") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO usage_events (user_id, plan, event_type, created_date)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, plan, event_type, date.today().isoformat()),
            )

    def get_usage_today(self, user_id: str, plan: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM usage_events
                WHERE user_id = ? AND plan = ? AND created_date = ?
                """,
                (user_id, plan, date.today().isoformat()),
            ).fetchone()
        return int(row[0]) if row else 0

    def save_feedback(
        self,
        user_id: str,
        request_id: str | None,
        rating: int,
        comment: str | None,
        problem_text: str | None,
        was_helpful: bool,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (
                    user_id, request_id, rating, comment, problem_text, was_helpful
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, request_id, rating, comment, problem_text, int(was_helpful)),
            )

    def save_profile(self, profile: StudentProfileRequest) -> StudentProfileResponse:
        preferred = ",".join(profile.preferred_subjects)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO student_profiles (
                    user_id, nickname, grade, target_exam, target_score,
                    preferred_subjects, goal_message, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    nickname = excluded.nickname,
                    grade = excluded.grade,
                    target_exam = excluded.target_exam,
                    target_score = excluded.target_score,
                    preferred_subjects = excluded.preferred_subjects,
                    goal_message = excluded.goal_message,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    profile.user_id,
                    profile.nickname,
                    profile.grade,
                    profile.target_exam,
                    profile.target_score,
                    preferred,
                    profile.goal_message,
                ),
            )
        return StudentProfileResponse(**profile.model_dump())

    def get_profile(self, user_id: str) -> StudentProfileResponse:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT user_id, nickname, grade, target_exam, target_score,
                       preferred_subjects, goal_message
                FROM student_profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if not row:
            return StudentProfileResponse(user_id=user_id, saved=False, message="기본 프로필입니다.")
        return StudentProfileResponse(
            user_id=row["user_id"],
            nickname=row["nickname"],
            grade=row["grade"],
            target_exam=row["target_exam"],
            target_score=row["target_score"],
            preferred_subjects=[
                item for item in row["preferred_subjects"].split(",") if item
            ],
            goal_message=row["goal_message"],
            saved=True,
            message="저장된 프로필입니다.",
        )

    def save_bookmark(self, bookmark: BookmarkRequest) -> BookmarkItem:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookmarks (user_id, problem_text, subject, note)
                VALUES (?, ?, ?, ?)
                """,
                (
                    bookmark.user_id,
                    bookmark.problem_text,
                    bookmark.subject,
                    bookmark.note,
                ),
            )
            bookmark_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT id, user_id, problem_text, subject, note, created_at
                FROM bookmarks
                WHERE id = ?
                """,
                (bookmark_id,),
            ).fetchone()
        return BookmarkItem(
            id=row[0],
            user_id=row[1],
            problem_text=row[2],
            subject=row[3],
            note=row[4],
            created_at=row[5],
        )

    def list_bookmarks(self, user_id: str, limit: int = 50) -> list[BookmarkItem]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, problem_text, subject, note, created_at
                FROM bookmarks
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            BookmarkItem(
                id=row["id"],
                user_id=row["user_id"],
                problem_text=row["problem_text"],
                subject=row["subject"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_ocr_correction(self, correction: OcrCorrectionRequest) -> OcrCorrectionResponse:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ocr_corrections (
                    user_id, raw_text, extracted_text, corrected_text,
                    detected_subject, confidence, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    correction.user_id,
                    correction.raw_text,
                    correction.extracted_text,
                    correction.corrected_text,
                    correction.detected_subject,
                    correction.confidence,
                    correction.source,
                ),
            )
            item_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT id, user_id, raw_text, extracted_text, corrected_text,
                       detected_subject, confidence, source, created_at
                FROM ocr_corrections
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()

        item = OcrCorrectionItem(
            id=row[0],
            user_id=row[1],
            raw_text=row[2],
            extracted_text=row[3],
            corrected_text=row[4],
            detected_subject=row[5],
            confidence=row[6],
            source=row[7],
            created_at=row[8],
        )
        return OcrCorrectionResponse(
            saved=True,
            item=item,
            improvement_targets=self._ocr_improvement_targets(
                correction.extracted_text,
                correction.corrected_text,
            ),
            message="OCR 교정 데이터가 저장되었습니다.",
        )

    def list_ocr_corrections(self, user_id: str, limit: int = 50) -> list[OcrCorrectionItem]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, raw_text, extracted_text, corrected_text,
                       detected_subject, confidence, source, created_at
                FROM ocr_corrections
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            OcrCorrectionItem(
                id=row["id"],
                user_id=row["user_id"],
                raw_text=row["raw_text"],
                extracted_text=row["extracted_text"],
                corrected_text=row["corrected_text"],
                detected_subject=row["detected_subject"],
                confidence=row["confidence"],
                source=row["source"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def ocr_correction_stats(self) -> OcrCorrectionStatsResponse:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT extracted_text, corrected_text, detected_subject
                FROM ocr_corrections
                ORDER BY id DESC
                LIMIT 500
                """
            ).fetchall()

        by_subject: dict[str, int] = {}
        replacements: dict[str, int] = {}
        for row in rows:
            subject = row["detected_subject"] or "unknown"
            by_subject[subject] = by_subject.get(subject, 0) + 1
            for target in self._ocr_improvement_targets(row["extracted_text"], row["corrected_text"]):
                replacements[target] = replacements.get(target, 0) + 1

        common = [
            {"pattern": key, "count": value}
            for key, value in sorted(replacements.items(), key=lambda item: item[1], reverse=True)[:10]
        ]
        return OcrCorrectionStatsResponse(
            total_corrections=len(rows),
            by_subject=by_subject,
            common_replacements=common,
            next_training_actions=[
                "교정 전/후 텍스트 쌍을 OCR 후처리 규칙 후보로 검토",
                "반복되는 수식 오류는 app/services/ocr.py 보정 규칙에 추가",
                "과목별 교정이 30개 이상 쌓이면 별도 테스트 케이스로 승격",
            ],
        )

    def save_elite_solution_sample(
        self,
        sample: EliteTrainingDataRequest,
        pattern_candidates: list[str] | None = None,
    ) -> EliteTrainingDataResponse:
        tags = ",".join(tag.strip() for tag in sample.tags if tag.strip())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO elite_solution_samples (
                    user_id, problem_text, subject, solution_text, verified_answer,
                    source_level, elapsed_seconds, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample.user_id,
                    sample.problem_text,
                    sample.subject,
                    sample.solution_text,
                    sample.verified_answer,
                    sample.source_level,
                    sample.elapsed_seconds,
                    tags,
                ),
            )
            item_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT id, user_id, problem_text, subject, solution_text, verified_answer,
                       source_level, elapsed_seconds, tags, created_at
                FROM elite_solution_samples
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()

        item = self._elite_item_from_row(row)
        candidates = pattern_candidates or self._elite_pattern_candidates(sample.problem_text, sample.subject, sample.tags)
        return EliteTrainingDataResponse(
            saved=True,
            item=item,
            pattern_candidates=candidates,
            message="상위권 풀이 샘플이 저장되었습니다.",
        )

    def list_elite_solution_samples(self, user_id: str, limit: int = 50) -> list[EliteTrainingDataItem]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, problem_text, subject, solution_text, verified_answer,
                       source_level, elapsed_seconds, tags, created_at
                FROM elite_solution_samples
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._elite_item_from_row(row) for row in rows]

    def elite_solution_stats(self) -> EliteStatsResponse:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT subject, source_level, tags
                FROM elite_solution_samples
                ORDER BY id DESC
                LIMIT 1000
                """
            ).fetchall()

        by_subject: dict[str, int] = {}
        by_source: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        for row in rows:
            subject = row["subject"] or "unknown"
            source = row["source_level"] or "unknown"
            by_subject[subject] = by_subject.get(subject, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1
            for tag in (row["tags"] or "").split(","):
                clean = tag.strip()
                if clean:
                    tag_counts[clean] = tag_counts.get(clean, 0) + 1

        readiness = min(88, 75 + len(rows) // 20)
        top_tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ]
        return EliteStatsResponse(
            total_samples=len(rows),
            by_subject=by_subject,
            by_source_level=by_source,
            top_tags=top_tags,
            readiness_percent=readiness,
            next_training_actions=[
                "상위권 풀이 샘플을 유형별로 20개씩 모으기",
                "각 샘플에 시간, 풀이 줄 수, 계산량 태그 붙이기",
                "오답률 높은 유형부터 빠른 풀이 패턴을 우선 보강하기",
            ],
        )

    def _elite_item_from_row(self, row) -> EliteTrainingDataItem:
        tags = [tag for tag in (row["tags"] if isinstance(row, sqlite3.Row) else row[8] or "").split(",") if tag]
        if isinstance(row, sqlite3.Row):
            return EliteTrainingDataItem(
                id=row["id"],
                user_id=row["user_id"],
                problem_text=row["problem_text"],
                subject=row["subject"],
                solution_text=row["solution_text"],
                verified_answer=row["verified_answer"],
                source_level=row["source_level"],
                elapsed_seconds=row["elapsed_seconds"],
                tags=tags,
                created_at=row["created_at"],
            )
        return EliteTrainingDataItem(
            id=row[0],
            user_id=row[1],
            problem_text=row[2],
            subject=row[3],
            solution_text=row[4],
            verified_answer=row[5],
            source_level=row[6],
            elapsed_seconds=row[7],
            tags=tags,
            created_at=row[9],
        )

    def _elite_pattern_candidates(self, text: str, subject: str, tags: list[str]) -> list[str]:
        haystack = f"{text} {' '.join(tags)}".lower()
        candidates: list[str] = []
        checks = [
            ("math_quadratic_extreme", ["이차함수", "최솟값", "최댓값", "x^2"]),
            ("math_quadratic_equation", ["이차방정식", "=0", "근"]),
            ("science_force", ["힘", "질량", "가속도", "f=ma"]),
            ("science_circuit_combo", ["전압", "전류", "저항", "전력"]),
            ("science_speed", ["속력", "거리", "시간"]),
        ]
        for name, words in checks:
            if any(word in haystack for word in words):
                candidates.append(name)
        if not candidates:
            candidates.append(f"{subject}_generic_shortcut" if subject in {"math", "science"} else "generic_exam_compression")
        return candidates

    def get_insight(self, user_id: str) -> StudentInsight:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT unit, problem_type, elapsed_seconds, was_correct
                FROM attempts
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 100
                """,
                (user_id,),
            ).fetchall()

        weak_units = self._top_values(
            row["unit"] for row in rows if row["was_correct"] == 0
        )
        slow_types = self._top_values(
            row["problem_type"]
            for row in rows
            if row["elapsed_seconds"] is not None and row["elapsed_seconds"] >= 180
        )
        repeated_mistakes = [
            f"{unit} 단원 반복 오답" for unit in weak_units[:3]
        ] or ["아직 반복 오답 데이터가 부족함"]

        next_recommendation = (
            f"{weak_units[0]} 단원 기본 개념과 빠른 풀이를 같이 복습"
            if weak_units
            else "문제 풀이 기록을 더 쌓아 약점 분석 시작"
        )

        return StudentInsight(
            user_id=user_id,
            total_attempts=len(rows),
            weak_units=weak_units,
            slow_types=slow_types,
            repeated_mistakes=repeated_mistakes,
            next_recommendation=next_recommendation,
        )

    def list_attempts(self, user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, problem_text, subject, unit, problem_type,
                       difficulty, elapsed_seconds, was_correct, created_at
                FROM attempts
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            AttemptHistoryItem(
                id=row["id"],
                user_id=row["user_id"],
                problem_text=row["problem_text"],
                subject=row["subject"],
                unit=row["unit"],
                problem_type=row["problem_type"],
                difficulty=row["difficulty"],
                elapsed_seconds=row["elapsed_seconds"],
                was_correct=None
                if row["was_correct"] is None
                else bool(row["was_correct"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_wrong_attempts(self, user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
        return self._list_attempts_by_filter(user_id, "was_correct = 0", limit)

    def list_slow_attempts(self, user_id: str, limit: int = 20) -> list[AttemptHistoryItem]:
        return self._list_attempts_by_filter(
            user_id,
            "elapsed_seconds IS NOT NULL AND elapsed_seconds >= 180",
            limit,
        )

    def get_review_bundle(self, user_id: str) -> ReviewBundle:
        wrong_items = self.list_wrong_attempts(user_id, limit=10)
        slow_items = self.list_slow_attempts(user_id, limit=10)
        insight = self.get_insight(user_id)

        targets = insight.weak_units[:2] + insight.slow_types[:2]
        today_review = targets or ["최근 푼 계산형 문제 3개", "과학 공식 적용형 문제 3개"]

        retry_source = wrong_items[:3] or slow_items[:3]
        retry_problems = [
            self._make_retry_problem(item.problem_text)
            for item in retry_source
        ] or [
            "이차함수 y=x^2-6x+5의 최솟값을 구하시오",
            "질량 3kg인 물체의 가속도가 4m/s^2일 때 힘을 구하시오",
        ]

        message = (
            "틀린 문제를 먼저 다시 풀고, 오래 걸린 문제는 빠른 풀이로 재도전하세요."
            if wrong_items or slow_items
            else "아직 오답/느린 문제 기록이 부족합니다. 몇 문제를 더 풀어 기준을 만드세요."
        )
        return ReviewBundle(
            user_id=user_id,
            wrong_items=wrong_items,
            slow_items=slow_items,
            today_review=today_review,
            retry_problems=retry_problems,
            message=message,
        )

    def get_progress(self, user_id: str) -> StudentProgress:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT elapsed_seconds, was_correct
                FROM attempts
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 100
                """,
                (user_id,),
            ).fetchall()

        total = len(rows)
        correct = sum(1 for row in rows if row["was_correct"] == 1)
        wrong = sum(1 for row in rows if row["was_correct"] == 0)
        graded = correct + wrong
        accuracy = round((correct / graded) * 100, 1) if graded else 0.0
        elapsed = [row["elapsed_seconds"] for row in rows if row["elapsed_seconds"] is not None]
        recent_elapsed = [
            row["elapsed_seconds"]
            for row in rows[:10]
            if row["elapsed_seconds"] is not None
        ]
        average_elapsed = round(sum(elapsed) / len(elapsed), 1) if elapsed else None
        recent_average = (
            round(sum(recent_elapsed) / len(recent_elapsed), 1)
            if recent_elapsed
            else None
        )

        if total == 0:
            trend = "아직 풀이 기록이 없습니다."
        elif recent_average is not None and average_elapsed is not None and recent_average < average_elapsed:
            trend = "최근 풀이 속도가 평균보다 빨라졌습니다."
        elif wrong > correct:
            trend = "오답 비율이 높아 기본 개념 복습이 필요합니다."
        else:
            trend = "기록이 쌓이고 있습니다. 같은 유형을 더 풀어 추세를 확인하세요."

        return StudentProgress(
            user_id=user_id,
            total_attempts=total,
            correct_attempts=correct,
            wrong_attempts=wrong,
            accuracy_percent=accuracy,
            average_elapsed_seconds=average_elapsed,
            recent_average_elapsed_seconds=recent_average,
            trend_message=trend,
        )

    def _list_attempts_by_filter(
        self, user_id: str, filter_sql: str, limit: int
    ) -> list[AttemptHistoryItem]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT id, user_id, problem_text, subject, unit, problem_type,
                       difficulty, elapsed_seconds, was_correct, created_at
                FROM attempts
                WHERE user_id = ? AND {filter_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            AttemptHistoryItem(
                id=row["id"],
                user_id=row["user_id"],
                problem_text=row["problem_text"],
                subject=row["subject"],
                unit=row["unit"],
                problem_type=row["problem_type"],
                difficulty=row["difficulty"],
                elapsed_seconds=row["elapsed_seconds"],
                was_correct=None
                if row["was_correct"] is None
                else bool(row["was_correct"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_recommendation(self, user_id: str) -> StudyRecommendation:
        insight = self.get_insight(user_id)
        progress = self.get_progress(user_id)
        preferred_subject = self._preferred_subject(user_id)

        review_targets = insight.weak_units[:3] or insight.slow_types[:3]
        if not review_targets:
            review_targets = ["기본 계산형 문제", "공식 적용형 문제"]

        if progress.total_attempts == 0:
            priority = "기록 만들기"
            today_plan = [
                "수학 계산형 3문제 풀기",
                "과학 공식 적용형 3문제 풀기",
                "풀이 시간을 입력해 기준 기록 만들기",
            ]
            message = "아직 기록이 없으니 먼저 기준 데이터를 만드는 것이 좋습니다."
        elif progress.accuracy_percent < 60:
            priority = "정확도 회복"
            today_plan = [
                f"{review_targets[0]} 기본 풀이 3문제",
                "틀린 문제의 오답 이유를 한 줄로 정리",
                "같은 유형의 비슷한 문제 2문제 재풀이",
            ]
            message = "정답률이 낮으니 빠른 풀이보다 기본 풀이 안정화가 먼저입니다."
        elif progress.average_elapsed_seconds and progress.average_elapsed_seconds >= 180:
            priority = "풀이 속도 개선"
            today_plan = [
                f"{review_targets[0]} 빠른 풀이 5문제",
                "풀이마다 계산을 줄일 수 있는 지점 표시",
                "같은 유형을 제한 시간 안에 다시 풀기",
            ]
            message = "정답은 가능하지만 시간이 오래 걸리는 패턴을 줄이는 단계입니다."
        else:
            priority = "난이도 상승"
            today_plan = [
                "현재 맞히는 유형보다 한 단계 어려운 문제 3문제",
                "빠른 풀이와 기본 풀이 비교",
                "실수한 문제만 오답노트에 저장",
            ]
            message = "기본 흐름이 잡히고 있으니 난이도를 조금 올려도 됩니다."

        recommended_types = insight.slow_types[:3] or ["일반 풀이형", "공식 적용형"]
        recommended_problems = self._recommended_problems(
            preferred_subject=preferred_subject,
            review_targets=review_targets,
            priority=priority,
        )
        return StudyRecommendation(
            user_id=user_id,
            priority=priority,
            today_plan=today_plan,
            review_targets=review_targets,
            recommended_problem_types=recommended_types,
            recommended_problems=recommended_problems,
            message=message,
        )

    def _ocr_improvement_targets(self, extracted: str, corrected: str) -> list[str]:
        matcher = difflib.SequenceMatcher(a=extracted or "", b=corrected or "")
        targets: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            before = (extracted or "")[i1:i2] or "∅"
            after = (corrected or "")[j1:j2] or "∅"
            targets.append(f"{before} -> {after}")
        return targets[:8] or ["문장 확인"]

    def _top_values(self, values) -> list[str]:
        counts: dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return [
            value
            for value, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        ][:5]

    def _preferred_subject(self, user_id: str) -> str:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT subject, COUNT(*) AS count
                FROM attempts
                WHERE user_id = ?
                GROUP BY subject
                ORDER BY count DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchall()
        return rows[0]["subject"] if rows else "mixed"

    def _recommended_problems(
        self, preferred_subject: str, review_targets: list[str], priority: str
    ) -> list[str]:
        math_set = [
            "이차함수 y=x^2-6x+5의 최솟값을 구하시오",
            "x^2-7x+12=0을 푸시오",
            "4x-5=19를 푸시오",
        ]
        science_set = [
            "질량 3kg인 물체의 가속도가 4m/s^2일 때 힘을 구하시오",
            "전압 9V, 전류 3A일 때 전력을 구하시오",
            "몰수 2mol, 몰 질량 18g/mol인 물질의 질량을 구하시오",
        ]

        if preferred_subject == "science" or any(target == "물리" for target in review_targets):
            problems = science_set
        elif preferred_subject == "math" or any("함수" in target for target in review_targets):
            problems = math_set
        else:
            problems = [math_set[0], science_set[0], math_set[1]]

        if priority == "정확도 회복":
            return problems[:2] + ["틀린 문제와 같은 유형으로 숫자만 바꾼 문제를 다시 푸시오"]
        return problems

    def _make_retry_problem(self, problem_text: str) -> str:
        import re

        numbers = re.findall(r"\d+", problem_text)
        if not numbers:
            return problem_text

        def bump(match: re.Match) -> str:
            return str(int(match.group(0)) + 1)

        return re.sub(r"\d+", bump, problem_text, count=2)
