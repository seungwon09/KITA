from app.models.schemas import GeneratedProblem, ProblemSet
from app.repositories.student_repo import StudentRepository


class ProblemGeneratorService:
    def __init__(self, student_repo: StudentRepository) -> None:
        self.student_repo = student_repo

    def generate_set(
        self,
        subject: str = "math",
        difficulty: str = "same",
        count: int = 5,
        unit: str | None = None,
    ) -> ProblemSet:
        subject = subject if subject in {"math", "science"} else "math"
        level = self._normalize_difficulty(difficulty)
        pool = self._science_pool(level, unit) if subject == "science" else self._math_pool(level, unit)
        problems = self._take_unique(pool, count)
        return ProblemSet(
            subject=subject,
            difficulty=level,
            problems=problems,
            message=f"{subject} {level} 문제 {len(problems)}개를 만들었습니다.",
        )

    def expected_set(self, user_id: str, subject: str = "math") -> ProblemSet:
        insight = self.student_repo.get_insight(user_id)
        weak_text = " ".join(insight.weak_units + insight.slow_types)
        subject = self._choose_subject(subject, weak_text)
        unit = self._choose_unit(weak_text)
        result = self.generate_set(subject=subject, difficulty="harder", count=6, unit=unit)
        result.message = "현재 약점과 자주 나오는 유형 기준 예상 훈련 문제입니다."
        return result

    def adaptive_set(self, user_id: str, subject: str = "math") -> ProblemSet:
        progress = self.student_repo.get_progress(user_id)
        insight = self.student_repo.get_insight(user_id)
        weak_text = " ".join(insight.weak_units + insight.slow_types)
        unit = self._choose_unit(weak_text)
        if progress.total_attempts == 0:
            difficulty = "easy"
        elif progress.accuracy_percent < 60:
            difficulty = "easy"
        elif progress.average_elapsed_seconds and progress.average_elapsed_seconds >= 150:
            difficulty = "same"
        else:
            difficulty = "harder"

        result = self.generate_set(subject=subject, difficulty=difficulty, count=6, unit=unit)
        result.message = f"학생 기록을 보고 난이도 {difficulty}, 단원 {unit or '혼합'}으로 조절했습니다."
        return result

    def targeted_set(
        self,
        user_id: str,
        subject: str = "mixed",
        count: int = 8,
    ) -> ProblemSet:
        insight = self.student_repo.get_insight(user_id)
        progress = self.student_repo.get_progress(user_id)
        weak_text = " ".join(insight.weak_units + insight.slow_types)
        chosen_subject = self._choose_subject(subject, weak_text)
        unit = self._choose_unit(weak_text)
        difficulty = "easy" if progress.accuracy_percent < 60 else "same"
        if progress.total_attempts >= 5 and progress.accuracy_percent >= 80:
            difficulty = "harder"
        result = self.generate_set(
            subject=chosen_subject,
            difficulty=difficulty,
            count=count,
            unit=unit,
        )
        result.message = f"약점 {unit or '혼합'} 중심 맞춤 훈련 문제입니다."
        return result

    def _normalize_difficulty(self, difficulty: str) -> str:
        if difficulty in {"easy", "same", "harder", "exam"}:
            return difficulty
        return "same"

    def _choose_subject(self, requested: str, weak_text: str) -> str:
        if requested in {"math", "science"}:
            return requested
        if any(word in weak_text for word in ["물리", "화학", "공식"]):
            return "science"
        return "math"

    def _choose_unit(self, weak_text: str) -> str | None:
        if "함수" in weak_text or "이차" in weak_text or "미분" in weak_text:
            return "function"
        if "방정식" in weak_text:
            return "equation"
        if "확률" in weak_text:
            return "probability"
        if "통계" in weak_text or "평균" in weak_text:
            return "statistics"
        if "물리" in weak_text or "힘" in weak_text or "전력" in weak_text:
            return "physics"
        if "화학" in weak_text or "몰" in weak_text:
            return "chemistry"
        return None

    def _take_unique(self, pool: list[GeneratedProblem], count: int) -> list[GeneratedProblem]:
        limit = max(1, min(count, 20))
        seen: set[str] = set()
        selected: list[GeneratedProblem] = []
        for problem in pool:
            if problem.problem in seen:
                continue
            seen.add(problem.problem)
            selected.append(problem)
            if len(selected) >= limit:
                break
        return selected

    def _math_pool(self, difficulty: str, unit: str | None) -> list[GeneratedProblem]:
        function = [
            GeneratedProblem(problem="이차함수 y=x^2-6x+5의 최솟값을 구하시오", subject="math", unit="함수/이차함수", difficulty=difficulty, target_skill="꼭짓점", expected_answer="-4"),
            GeneratedProblem(problem="이차함수 y=2x^2-8x+1의 최솟값을 구하시오", subject="math", unit="함수/이차함수", difficulty=difficulty, target_skill="계수 있는 꼭짓점", expected_answer="-7"),
            GeneratedProblem(problem="이차함수 y=-x^2+4x+1의 최댓값을 구하시오", subject="math", unit="함수/이차함수", difficulty=difficulty, target_skill="최댓값", expected_answer="5"),
            GeneratedProblem(problem="y=x^2+2x-3의 축의 방정식을 구하시오", subject="math", unit="함수/이차함수", difficulty=difficulty, target_skill="축", expected_answer="x=-1"),
            GeneratedProblem(problem="f(x)=x^2-4x+1일 때 f(3)을 구하시오", subject="math", unit="함수/이차함수", difficulty=difficulty, target_skill="함숫값", expected_answer="-2"),
        ]
        equation = [
            GeneratedProblem(problem="x^2-7x+12=0을 푸시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="인수분해", expected_answer="x=3 또는 x=4"),
            GeneratedProblem(problem="2x^2-8x+6=0을 푸시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="근의 공식", expected_answer="x=1 또는 x=3"),
            GeneratedProblem(problem="x^2+2x+5=0의 실근이 있는지 판단하시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="판별식", expected_answer="실근 없음"),
            GeneratedProblem(problem="5x-7=18을 푸시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="일차방정식", expected_answer="x=5"),
            GeneratedProblem(problem="3x+2=2x+7을 푸시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="양변 일차방정식", expected_answer="x=5"),
            GeneratedProblem(problem="x+y=9, x-y=3일 때 x,y를 구하시오", subject="math", unit="방정식", difficulty=difficulty, target_skill="연립방정식", expected_answer="x=6, y=3"),
        ]
        probability = [
            GeneratedProblem(problem="주사위 한 개를 던질 때 짝수가 나올 확률을 구하시오", subject="math", unit="확률", difficulty=difficulty, target_skill="기본 확률", expected_answer="1/2"),
            GeneratedProblem(problem="전체 12개 중 원하는 경우가 3개일 때 확률을 구하시오", subject="math", unit="확률", difficulty=difficulty, target_skill="경우의 수 비율", expected_answer="0.25"),
        ]
        statistics = [
            GeneratedProblem(problem="2, 4, 6, 8, 10의 평균을 구하시오", subject="math", unit="통계", difficulty=difficulty, target_skill="평균", expected_answer="6"),
            GeneratedProblem(problem="70, 80, 90의 평균을 구하시오", subject="math", unit="통계", difficulty=difficulty, target_skill="평균", expected_answer="80"),
        ]
        mixed = function + equation + probability + statistics
        if difficulty == "easy":
            mixed = [function[0], function[3], equation[3], equation[4], statistics[0], probability[0]] + mixed
        if difficulty == "harder":
            mixed.insert(0, GeneratedProblem(problem="이차함수 y=x^2-8x+10의 최솟값과 그때의 x값을 구하시오", subject="math", unit="함수/이차함수", difficulty="harder", target_skill="최솟값+좌표", expected_answer="x=4, 최솟값 -6"))
            mixed.insert(1, GeneratedProblem(problem="이차함수 y=3x^2-12x+8의 최솟값을 구하시오", subject="math", unit="함수/이차함수", difficulty="harder", target_skill="계수 있는 최솟값", expected_answer="-4"))
        if difficulty == "exam":
            mixed.insert(0, GeneratedProblem(problem="이차함수 y=x^2-2ax+3의 최솟값이 -1일 때 a의 양수 값을 구하시오", subject="math", unit="함수/이차함수", difficulty="exam", target_skill="조건 해석", expected_answer="a=2"))
            mixed.insert(1, GeneratedProblem(problem="3x+2=2x+7을 30초 안에 푸시오", subject="math", unit="방정식", difficulty="exam", target_skill="실전 시간 단축", expected_answer="x=5"))
        if unit == "function":
            return function + mixed
        if unit == "equation":
            return equation + mixed
        if unit == "probability":
            return probability + mixed
        if unit == "statistics":
            return statistics + mixed
        return mixed

    def _science_pool(self, difficulty: str, unit: str | None) -> list[GeneratedProblem]:
        physics = [
            GeneratedProblem(problem="질량 4kg인 물체의 가속도가 5m/s^2일 때 힘을 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="F=ma", expected_answer="20N"),
            GeneratedProblem(problem="힘 12N, 질량 4kg일 때 가속도를 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="F=ma 역산", expected_answer="3m/s^2"),
            GeneratedProblem(problem="전압 10V, 전류 3A일 때 전력을 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="P=VI", expected_answer="30W"),
            GeneratedProblem(problem="전력 60W, 전압 12V일 때 전류를 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="P=VI 역산", expected_answer="5A"),
            GeneratedProblem(problem="전압 12V, 전류 3A일 때 저항을 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="옴의 법칙", expected_answer="4Ω"),
            GeneratedProblem(problem="거리 120m를 20초 동안 이동했을 때 속력을 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="v=s/t", expected_answer="6m/s"),
            GeneratedProblem(problem="일 30J, 힘 10N일 때 이동거리를 구하시오", subject="science", unit="물리", difficulty=difficulty, target_skill="W=Fs 역산", expected_answer="3m"),
        ]
        chemistry = [
            GeneratedProblem(problem="몰수 2mol, 몰 질량 18g/mol인 물질의 질량을 구하시오", subject="science", unit="화학", difficulty=difficulty, target_skill="m=nM", expected_answer="36g"),
            GeneratedProblem(problem="질량 40g, 몰 질량 20g/mol인 물질의 몰수를 구하시오", subject="science", unit="화학", difficulty=difficulty, target_skill="n=m/M", expected_answer="2mol"),
            GeneratedProblem(problem="몰수 3mol이 2L에 녹아 있을 때 몰농도를 구하시오", subject="science", unit="화학", difficulty=difficulty, target_skill="M=n/V", expected_answer="1.5M"),
            GeneratedProblem(problem="밀도 2g/cm^3, 부피 5cm^3일 때 질량을 구하시오", subject="science", unit="화학", difficulty=difficulty, target_skill="밀도 역산", expected_answer="10g"),
        ]
        mixed = physics + chemistry
        if difficulty == "easy":
            mixed = [physics[0], physics[2], physics[5], chemistry[0], chemistry[1]] + mixed
        if difficulty == "harder":
            mixed.insert(0, GeneratedProblem(problem="질량 2kg인 물체가 10m/s로 움직일 때 운동 에너지를 구하시오", subject="science", unit="물리", difficulty="harder", target_skill="Ek=1/2mv^2", expected_answer="100J"))
            mixed.insert(1, GeneratedProblem(problem="압력 20Pa, 면적 3m^2일 때 힘을 구하시오", subject="science", unit="물리", difficulty="harder", target_skill="P=F/A 역산", expected_answer="60N"))
        if difficulty == "exam":
            mixed.insert(0, GeneratedProblem(problem="저항 4Ω에 전류 3A가 흐를 때 전압과 전력을 각각 구하시오", subject="science", unit="물리", difficulty="exam", target_skill="V=IR, P=VI", expected_answer="12V, 36W"))
            mixed.insert(1, GeneratedProblem(problem="몰수와 몰 질량 조건을 보고 질량을 20초 안에 구하시오: n=3mol, M=18g/mol", subject="science", unit="화학", difficulty="exam", target_skill="공식 빠른 매칭", expected_answer="54g"))
        if unit == "physics":
            return physics + mixed
        if unit == "chemistry":
            return chemistry + mixed
        return mixed
