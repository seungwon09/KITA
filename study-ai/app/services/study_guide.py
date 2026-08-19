from app.models.schemas import ConceptSummary, FormulaNote, LearningRoute
from app.repositories.student_repo import StudentRepository


class StudyGuideService:
    def __init__(self, student_repo: StudentRepository) -> None:
        self.student_repo = student_repo

    def concept_summary(self, subject: str = "math", unit: str | None = None) -> ConceptSummary:
        subject = subject or "math"
        unit_key = self._normalize_unit(subject, unit)
        data = self._concept_data()[subject][unit_key]
        return ConceptSummary(
            subject=subject,
            unit=data["unit"],
            one_line=data["one_line"],
            core_points=data["core_points"],
            exam_patterns=data["exam_patterns"],
            common_mistakes=data["common_mistakes"],
            quick_check=data["quick_check"],
        )

    def formula_note(self, subject: str = "math") -> FormulaNote:
        subject = subject or "math"
        if subject == "science":
            formulas = [
                {"name": "힘", "formula": "F = ma", "tip": "질량과 가속도가 보이면 바로 곱한다."},
                {"name": "속력", "formula": "v = s / t", "tip": "거리, 시간, 속력 중 하나를 묻는 문제."},
                {"name": "밀도", "formula": "rho = m / V", "tip": "질량/부피 단위 확인이 핵심."},
                {"name": "전력", "formula": "P = VI", "tip": "전압과 전류가 같이 나오면 전력."},
                {"name": "몰수", "formula": "n = m / M", "tip": "질량과 몰 질량을 구분한다."},
                {"name": "운동 에너지", "formula": "Ek = 1/2 mv^2", "tip": "속도는 제곱된다."},
                {"name": "옴의 법칙", "formula": "V = IR", "tip": "전압, 전류, 저항 삼각관계."},
            ]
            return FormulaNote(
                subject="science",
                formulas=formulas,
                must_memorize=["F=ma", "v=s/t", "rho=m/V", "P=VI", "n=m/M", "V=IR"],
                use_when=["단위가 주어짐", "공식에 바로 대입 가능", "계산보다 조건 정리가 중요"],
            )

        formulas = [
            {"name": "일차방정식", "formula": "ax + b = c", "tip": "x항과 숫자를 양쪽으로 분리."},
            {"name": "이차방정식", "formula": "x = (-b +- sqrt(b^2-4ac)) / 2a", "tip": "인수분해가 안 되면 공식."},
            {"name": "이차함수 꼭짓점", "formula": "x = -b / 2a", "tip": "최댓값/최솟값은 꼭짓점부터 확인."},
            {"name": "평균", "formula": "평균 = 총합 / 개수", "tip": "총합으로 바꾸면 빨라진다."},
            {"name": "확률", "formula": "확률 = 원하는 경우 / 전체 경우", "tip": "전체 경우를 먼저 세기."},
            {"name": "거듭제곱", "formula": "a^m * a^n = a^(m+n)", "tip": "밑이 같은지 먼저 본다."},
        ]
        return FormulaNote(
            subject="math",
            formulas=formulas,
            must_memorize=["x=-b/2a", "근의 공식", "평균=총합/개수", "확률=부분/전체"],
            use_when=["최댓값/최솟값", "방정식 풀이", "경우의 수", "반복 계산 줄이기"],
        )

    def learning_route(self, user_id: str) -> LearningRoute:
        insight = self.student_repo.get_insight(user_id)
        progress = self.student_repo.get_progress(user_id)
        weak = insight.weak_units[0] if insight.weak_units else "기본 계산/공식"

        if progress.total_attempts == 0:
            priority = "기준 기록 만들기"
            route = ["쉬운 수학 3문제", "쉬운 과학 3문제", "풀이 시간 입력", "오답만 다시 풀기"]
            daily = ["수학 3문제", "과학 3문제", "각 문제 풀이 시간 기록"]
            next_unlock = "기록 10개가 쌓이면 약점 기반 루트로 전환"
            message = "지금은 AI가 학생 스타일을 알기 위한 데이터가 먼저 필요합니다."
        elif progress.accuracy_percent < 60:
            priority = "정확도 회복"
            route = [f"{weak} 개념 압축", "기본 풀이 5문제", "오답 이유 한 줄 저장", "같은 유형 재출제"]
            daily = [f"{weak} 기본 문제 5개", "틀린 문제만 다시 2개", "공식 노트 3개 암기"]
            next_unlock = "정답률 70% 이상이면 빠른 풀이 루트"
            message = "아직은 속도보다 정확도가 먼저입니다."
        elif progress.average_elapsed_seconds and progress.average_elapsed_seconds >= 150:
            priority = "속도 개선"
            route = [f"{weak} 빠른 풀이 패턴", "계산 줄이는 풀이 비교", "제한 시간 풀이", "느린 문제 재도전"]
            daily = ["빠른 풀이 5문제", "기본 풀이와 차이 1줄 비교", "90초 제한 풀이 3문제"]
            next_unlock = "평균 시간이 줄면 난이도 상승 루트"
            message = "정답은 가능하니 시험장에서 쓰는 짧은 풀이로 줄이는 단계입니다."
        else:
            priority = "난이도 상승"
            route = ["상위 유형 3문제", "빠른 풀이만 먼저 시도", "막히면 힌트 1개", "오답만 복습"]
            daily = ["한 단계 어려운 문제 3개", "실전 타이머 사용", "비슷한 문제 2개 생성"]
            next_unlock = "킬러/준킬러 유형 분석"
            message = "기본 흐름이 괜찮아서 난이도를 올려도 됩니다."

        return LearningRoute(
            user_id=user_id,
            priority=priority,
            route=route,
            daily_mission=daily,
            next_unlock=next_unlock,
            message=message,
        )

    def _normalize_unit(self, subject: str, unit: str | None) -> str:
        if subject == "science":
            if unit and ("화학" in unit or "몰" in unit or "질량" in unit):
                return "chemistry"
            return "physics"
        if unit and ("방정식" in unit):
            return "equation"
        return "function"

    def _concept_data(self) -> dict[str, dict[str, dict[str, object]]]:
        return {
            "math": {
                "function": {
                    "unit": "함수/이차함수",
                    "one_line": "이차함수는 꼭짓점만 찾으면 최댓값/최솟값 문제가 빨라집니다.",
                    "core_points": ["x=-b/2a로 꼭짓점 x좌표 확인", "완전제곱식으로 그래프 모양 파악", "a가 양수면 최솟값, 음수면 최댓값"],
                    "exam_patterns": ["최솟값/최댓값", "꼭짓점", "축의 방정식", "그래프 이동"],
                    "common_mistakes": ["-b/2a 부호 실수", "최솟값이 x값인지 y값인지 혼동", "완전제곱 상수항 계산 실수"],
                    "quick_check": "최솟값을 물으면 x좌표가 아니라 y값을 답해야 합니다.",
                },
                "equation": {
                    "unit": "방정식",
                    "one_line": "방정식은 양변에 같은 조작을 해서 미지수를 고립시키는 문제입니다.",
                    "core_points": ["x항과 숫자항 분리", "인수분해 가능 여부 먼저 확인", "근을 구한 뒤 원식에 대입 검산"],
                    "exam_patterns": ["일차방정식", "이차방정식", "연립방정식", "조건 방정식"],
                    "common_mistakes": ["이항 부호 실수", "근 하나 누락", "대입 검산 생략"],
                    "quick_check": "답을 구하면 원래 식에 넣어 맞는지 5초 검산하세요.",
                },
            },
            "science": {
                "physics": {
                    "unit": "물리",
                    "one_line": "물리는 단위와 공식을 매칭하면 대부분 빠르게 풀립니다.",
                    "core_points": ["주어진 값의 단위 확인", "묻는 값에 맞는 공식 선택", "대입 전 단위 변환"],
                    "exam_patterns": ["힘 F=ma", "속력 v=s/t", "전력 P=VI", "에너지 계산"],
                    "common_mistakes": ["단위 변환 누락", "곱셈/나눗셈 공식 혼동", "m/s와 km/h 혼동"],
                    "quick_check": "답 단위가 문제에서 묻는 물리량과 맞는지 확인하세요.",
                },
                "chemistry": {
                    "unit": "화학",
                    "one_line": "화학 계산은 몰수, 질량, 몰 질량 관계를 잡으면 빨라집니다.",
                    "core_points": ["n=m/M", "m=nM", "농도 M=n/V", "단위 L와 mL 구분"],
                    "exam_patterns": ["몰수 계산", "질량 계산", "몰 농도", "비례식"],
                    "common_mistakes": ["몰 질량과 질량 혼동", "mL를 L로 바꾸지 않음", "공식 위치 반대로 대입"],
                    "quick_check": "몰 농도 문제는 부피 단위가 L인지 먼저 보세요.",
                },
            },
        }
