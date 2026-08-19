from __future__ import annotations

from app.models.schemas import ElitePattern, EliteSolutionRequest, EliteSolutionResponse, ProblemRecognitionRequest
from app.services.math_solver import MathSolver
from app.services.problem_recognition import ProblemRecognitionService
from app.services.science_solver import ScienceSolver


class EliteSolutionService:
    """Exam-speed layer: short, verified, and practical."""

    def __init__(self, recognition: ProblemRecognitionService | None = None) -> None:
        self.recognition = recognition or ProblemRecognitionService()
        self.math_solver = MathSolver()
        self.science_solver = ScienceSolver()
        self._patterns = self._build_patterns()

    def patterns(self, subject: str = "mixed") -> list[ElitePattern]:
        return [pattern for pattern in self._patterns if subject not in {"math", "science"} or pattern.subject == subject]

    def solve(self, request: EliteSolutionRequest) -> EliteSolutionResponse:
        recognition = self.recognition.recognize(
            ProblemRecognitionRequest(
                user_id=request.user_id,
                problem_text=request.problem_text,
                subject=request.subject,
                source="elite_solution",
            )
        )
        subject = recognition.detected_subject if recognition.detected_subject in {"math", "science"} else self._guess_subject(request.problem_text)
        result = self._solve(recognition.normalized_text or request.problem_text, subject)
        selected = self._select_patterns(request.problem_text, subject)
        if not selected:
            selected = [self._fallback(subject)]
        verified = result[3] if result else recognition.verified_answer
        pattern = selected[0]
        top_solution = (
            f"상위권 풀이: {pattern.shortcut}\n{result[1]}\n정답: {verified}"
            if result and verified
            else f"상위권 접근: {pattern.shortcut}\n{pattern.exam_use}"
        )
        return EliteSolutionResponse(
            recognition=recognition,
            verified_answer=verified,
            selected_patterns=selected,
            top_student_solution=top_solution,
            exam_shortcut=f"{pattern.exam_use} {result[1] if result else ''}".strip(),
            calculation_reduction=" / ".join(dict.fromkeys(item.calculation_reduction for item in selected)),
            traps=list(dict.fromkeys(trap for item in selected for trap in item.common_traps))[:6],
            time_target_seconds=min(item.time_target_seconds for item in selected),
            confidence=round(min(0.98, recognition.confidence + (0.12 if result else 0.02)), 3),
            recommended_drills=[
                f"{pattern.unit} 같은 유형 5문제를 문제당 {pattern.time_target_seconds}초 목표로 풀기",
                f"오답 확인: {pattern.common_traps[0]}",
            ]
            if request.include_drills
            else [],
            data_readiness_percent=86,
            next_action="같은 유형 5문제를 시간 제한을 걸고 반복하세요.",
        )

    def pattern_candidates(self, problem_text: str, subject: str = "mixed") -> list[str]:
        selected = self._select_patterns(problem_text, subject)
        return [pattern.id for pattern in selected] or [self._fallback("science" if subject == "science" else "math").id]

    def _solve(self, text: str, subject: str):
        if subject == "science":
            return self.science_solver.solve(text) or self.math_solver.solve(text)
        return self.math_solver.solve(text) or self.science_solver.solve(text)

    def _select_patterns(self, text: str, subject: str) -> list[ElitePattern]:
        compact = text.lower().replace(" ", "")
        scored: list[tuple[int, ElitePattern]] = []
        for pattern in self._patterns:
            if subject in {"math", "science"} and pattern.subject != subject:
                continue
            score = sum(keyword.lower().replace(" ", "") in compact for keyword in pattern.trigger_keywords)
            if score:
                scored.append((score, pattern))
        scored.sort(key=lambda item: (item[0], -item[1].time_target_seconds), reverse=True)
        return [item[1] for item in scored[:3]]

    def _guess_subject(self, text: str) -> str:
        words = ["힘", "질량", "가속도", "전압", "전류", "저항", "전력", "몰", "파동", "열량", "kg", "m/s"]
        return "science" if any(word in text for word in words) else "math"

    def _fallback(self, subject: str) -> ElitePattern:
        return next(pattern for pattern in self._patterns if pattern.id == f"{subject}_generic")

    def _build_patterns(self) -> list[ElitePattern]:
        return [
            ElitePattern(
                id="math_quadratic_extreme",
                subject="math",
                unit="이차함수",
                problem_type="최댓값·최솟값",
                trigger_keywords=["이차함수", "x^2", "최솟값", "최댓값", "꼭짓점"],
                shortcut="전개를 길게 하지 말고 꼭짓점 x=-b/(2a)만 먼저 구합니다.",
                exam_use="꼭짓점 좌표를 구한 뒤 y값만 대입하면 됩니다.",
                calculation_reduction="완전제곱 전개를 생략하고 꼭짓점 공식으로 압축",
                common_traps=["x좌표만 구하고 y값을 계산하지 않기", "b의 부호를 반대로 쓰기"],
                time_target_seconds=18,
                difficulty_band="중상",
            ),
            ElitePattern(
                id="math_equation",
                subject="math",
                unit="방정식",
                problem_type="근 또는 해 구하기",
                trigger_keywords=["방정식", "=0", "근", "x="],
                shortcut="인수분해가 바로 보이는지 먼저 확인하고, 아니면 근의 공식을 씁니다.",
                exam_use="인수분해 확인에 5초 이상 쓰지 않습니다.",
                calculation_reduction="긴 전개 전에 인수 조합부터 확인",
                common_traps=["=0으로 정리하지 않기", "부호를 빠뜨리기"],
                time_target_seconds=28,
                difficulty_band="중",
            ),
            ElitePattern(
                id="math_geometry",
                subject="math",
                unit="도형",
                problem_type="넓이·길이",
                trigger_keywords=["삼각형", "직사각형", "원", "피타고라스", "빗변"],
                shortcut="도형 이름을 보고 필요한 공식 하나만 고릅니다.",
                exam_use="숫자를 넣기 전에 구할 값이 넓이인지 길이인지 확인합니다.",
                calculation_reduction="불필요한 보조선과 중간 계산 생략",
                common_traps=["넓이와 둘레를 혼동하기", "단위를 빠뜨리기"],
                time_target_seconds=22,
                difficulty_band="중",
            ),
            ElitePattern(
                id="math_sequence",
                subject="math",
                unit="수열",
                problem_type="일반항·합",
                trigger_keywords=["등차수열", "등비수열", "첫째항", "공차", "공비", "합"],
                shortcut="일반항인지 합인지 먼저 표시하고 공식 하나만 고릅니다.",
                exam_use="등차는 끝항을 먼저, 등비는 공비가 1인지 먼저 확인합니다.",
                calculation_reduction="일반항과 합 공식을 섞지 않고 한 줄로 압축",
                common_traps=["n번째 항과 n번째 항까지의 합을 혼동하기", "n-1을 빠뜨리기"],
                time_target_seconds=26,
                difficulty_band="중",
            ),
            ElitePattern(
                id="math_coordinate",
                subject="math",
                unit="좌표",
                problem_type="기울기·거리",
                trigger_keywords=["두 점", "좌표", "기울기", "거리"],
                shortcut="기울기는 변화량의 비, 거리는 가로·세로 차의 제곱합입니다.",
                exam_use="좌표를 빼는 순서만 두 축에서 같게 유지합니다.",
                calculation_reduction="두 좌표의 차만 먼저 표시",
                common_traps=["x와 y의 차를 뒤섞기", "거리에서 제곱근을 빠뜨리기"],
                time_target_seconds=24,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_force_motion",
                subject="science",
                unit="물리/힘과 운동",
                problem_type="공식 적용형",
                trigger_keywords=["힘", "질량", "가속도", "F=ma", "속력", "거리", "시간"],
                shortcut="주어진 단위를 보고 F=ma 또는 s=vt 중 하나를 바로 고릅니다.",
                exam_use="단위가 맞으면 숫자만 대입하고 한 줄로 끝냅니다.",
                calculation_reduction="문장을 공식 변수 세 개로 압축",
                common_traps=["kg과 g를 섞어 쓰기", "초와 분을 바꾸지 않기"],
                time_target_seconds=18,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_circuit",
                subject="science",
                unit="물리/전기",
                problem_type="전압·전류·전력",
                trigger_keywords=["전압", "전류", "저항", "전력", "V=IR", "P=VI", "Ω"],
                shortcut="V=IR로 필요한 값을 먼저 만들고, 전력은 P=VI로 이어서 계산합니다.",
                exam_use="전압과 전력을 함께 물으면 두 식을 연달아 씁니다.",
                calculation_reduction="공식 선택 시간을 줄이고 두 줄 계산으로 압축",
                common_traps=["전압과 전력을 혼동하기", "전류의 제곱을 빠뜨리기"],
                time_target_seconds=22,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_circuit_combo",
                subject="science",
                unit="물리/전기",
                problem_type="전압·전력 연속 계산",
                trigger_keywords=["전압", "전류", "저항", "전력", "Ω", "각각"],
                shortcut="V=IR로 전압을 만든 뒤 같은 전류를 P=VI에 바로 이어 넣습니다.",
                exam_use="전압과 전력을 각각 묻는 문제는 두 줄로 끝냅니다.",
                calculation_reduction="V=IR → P=VI 순서로 중간값 재사용",
                common_traps=["전압을 구한 뒤 전력 계산을 빠뜨리기", "전력 단위를 W로 쓰지 않기"],
                time_target_seconds=20,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_heat_wave",
                subject="science",
                unit="물리/열과 파동",
                problem_type="열량·파동",
                trigger_keywords=["열량", "비열", "온도 변화", "파동", "파장", "진동수", "주기"],
                shortcut="단위를 보고 Q=cmΔT, v=fλ, T=1/f 중 하나를 고릅니다.",
                exam_use="곱셈식인지 역수식인지 먼저 확인합니다.",
                calculation_reduction="조건을 공식 변수로 바로 치환",
                common_traps=["온도와 온도 변화를 혼동하기", "주기와 진동수를 곱하지 않기"],
                time_target_seconds=24,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_energy_momentum",
                subject="science",
                unit="물리/에너지와 운동량",
                problem_type="에너지·운동량",
                trigger_keywords=["운동 에너지", "위치 에너지", "전기에너지", "운동량", "충격량"],
                shortcut="물리량 이름을 식과 바로 연결하고 단위를 마지막에 확인합니다.",
                exam_use="제곱이 있는 식과 없는 식을 먼저 구분합니다.",
                calculation_reduction="주어진 값을 공식 순서대로 배치",
                common_traps=["운동 에너지의 속력 제곱을 빠뜨리기", "충격량의 시간을 빠뜨리기"],
                time_target_seconds=24,
                difficulty_band="중",
            ),
            ElitePattern(
                id="science_chemistry",
                subject="science",
                unit="화학/몰과 농도",
                problem_type="공식 적용형",
                trigger_keywords=["몰", "몰수", "몰농도", "몰질량", "mol"],
                shortcut="질량, 몰수, 몰질량, 부피 중 주어진 값을 식에 바로 배치합니다.",
                exam_use="단위가 g, mol, L인지 먼저 확인합니다.",
                calculation_reduction="변수 표를 한 줄로 정리",
                common_traps=["mL를 L로 바꾸지 않기", "몰수와 몰농도를 혼동하기"],
                time_target_seconds=28,
                difficulty_band="중",
            ),
            ElitePattern(
                id="math_generic",
                subject="math",
                unit="수학",
                problem_type="시험형 압축 풀이",
                trigger_keywords=["x", "값", "구하"],
                shortcut="구해야 하는 값을 먼저 표시하고 필요한 식만 남깁니다.",
                exam_use="중간 계산보다 최종 목표와 연결되는 식을 먼저 고릅니다.",
                calculation_reduction="불필요한 전개 제거",
                common_traps=["중간값을 정답으로 쓰기", "조건 하나를 빠뜨리기"],
                time_target_seconds=35,
                difficulty_band="중",
                requires_verified_answer=False,
            ),
            ElitePattern(
                id="science_generic",
                subject="science",
                unit="과학",
                problem_type="공식 적용형",
                trigger_keywords=["구하", "단위", "과학"],
                shortcut="단위를 보고 공식을 고른 뒤 필요한 값만 대입합니다.",
                exam_use="식 하나와 단위 확인으로 풀이를 끝냅니다.",
                calculation_reduction="문장을 공식 변수로 압축",
                common_traps=["단위를 바꾸지 않기", "구할 물리량을 혼동하기"],
                time_target_seconds=35,
                difficulty_band="중",
                requires_verified_answer=False,
            ),
        ]
