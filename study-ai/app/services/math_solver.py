import math
import re


class MathSolver:
    """Fast deterministic solver for common middle/high-school math patterns."""

    NUMBER = r"-?\d+(?:\.\d+)?"
    QUADRATIC_EXPR = r"[+-]?(?:\d+(?:\.\d+)?)?\*?x\^2(?:[+-](?:\d+(?:\.\d+)?)?\*?x)?(?:[+-]\d+(?:\.\d+)?)?"

    def solve(self, problem_text: str) -> tuple[str, str, str, str | None] | None:
        text = self._normalize(problem_text)
        for solver in [
            self.solve_circle,
            self.solve_triangle_area,
            self.solve_rectangle,
            self.solve_pythagorean,
            self.solve_distance_between_points,
            self.solve_slope_between_points,
            self.solve_arithmetic_sequence_sum,
            self.solve_arithmetic_sequence,
            self.solve_geometric_sequence_sum,
            self.solve_geometric_sequence,
            self.solve_percentage,
            self.solve_simultaneous_equations,
            self.solve_function_value,
            self.solve_quadratic_extreme,
            self.solve_quadratic_axis,
            self.solve_quadratic_equation,
            self.solve_linear_inequality,
            self.solve_linear_equation,
            self.solve_proportion,
            self.solve_average,
            self.solve_probability_basic,
            self.solve_exponent,
        ]:
            result = solver(text)
            if result:
                return result
        return None

    def solve_circle(self, text: str):
        if "원" not in text and "circle" not in text.lower():
            return None
        radius = self._labeled_number(text, ["반지름", "radius", "r"])
        if radius is None:
            return None
        area = math.pi * radius**2
        circumference = 2 * math.pi * radius
        area_text, circumference_text = self._number_text(area), self._number_text(circumference)
        basic = (
            f"원의 넓이는 πr^2, 둘레는 2πr입니다.\n"
            f"r={self._number_text(radius)}이므로 넓이={self._number_text(radius)}^2π={self._number_text(radius**2)}π≈{area_text}입니다.\n"
            f"둘레=2π×{self._number_text(radius)}={self._number_text(2 * radius)}π≈{circumference_text}입니다."
        )
        fast = f"r={self._number_text(radius)}를 바로 대입하면 넓이={self._number_text(radius**2)}π, 둘레={self._number_text(2 * radius)}π입니다."
        similar = f"반지름이 {self._number_text(radius + 1)}인 원의 넓이와 둘레를 구하시오."
        return basic, fast, similar, f"넓이 {self._number_text(radius**2)}π, 둘레 {self._number_text(2 * radius)}π"

    def solve_triangle_area(self, text: str):
        if "삼각형" not in text or "넓이" not in text:
            return None
        base = self._labeled_number(text, ["밑변", "base"])
        height = self._labeled_number(text, ["높이", "height"])
        if base is None or height is None:
            return None
        area = base * height / 2
        answer = self._number_text(area)
        basic = f"삼각형의 넓이는 밑변×높이÷2입니다.\n{self._number_text(base)}×{self._number_text(height)}÷2={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"밑변×높이÷2={answer}."
        similar = f"밑변 {self._number_text(base + 1)}, 높이 {self._number_text(height + 2)}인 삼각형의 넓이를 구하시오."
        return basic, fast, similar, answer

    def solve_rectangle(self, text: str):
        if not any(word in text for word in ["직사각형", "사각형", "rectangle"]):
            return None
        width = self._labeled_number(text, ["가로", "width"])
        height = self._labeled_number(text, ["세로", "높이", "height"])
        if width is None or height is None:
            return None
        if "둘레" in text:
            value = 2 * (width + height)
            formula = "둘레=2×(가로+세로)"
        else:
            value = width * height
            formula = "넓이=가로×세로"
        answer = self._number_text(value)
        basic = f"직사각형의 {formula}입니다.\n{formula.replace('가로', self._number_text(width)).replace('세로', self._number_text(height))}={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"{formula}={answer}."
        similar = f"가로 {self._number_text(width + 1)}, 세로 {self._number_text(height + 1)}인 직사각형의 {'둘레' if '둘레' in text else '넓이'}를 구하시오."
        return basic, fast, similar, answer

    def solve_pythagorean(self, text: str):
        if not any(word in text for word in ["직각삼각형", "피타고라스", "빗변"]):
            return None
        nums = [float(num) for num in re.findall(self.NUMBER, text)]
        if len(nums) < 2:
            return None
        a, b = nums[:2]
        c = math.sqrt(a * a + b * b)
        answer = self._number_text(c)
        basic = f"직각삼각형에서 빗변 c는 c^2=a^2+b^2입니다.\nc^2={self._number_text(a)}^2+{self._number_text(b)}^2={self._number_text(a*a+b*b)}이므로 c={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"a^2+b^2만 계산하면 c={answer}입니다."
        similar = f"두 직각변이 {self._number_text(a + 1)}, {self._number_text(b + 1)}인 직각삼각형의 빗변을 구하시오."
        return basic, fast, similar, answer

    def solve_slope_between_points(self, text: str):
        if "기울기" not in text:
            return None
        points = re.findall(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)", text)
        if len(points) < 2:
            return None
        x1, y1 = map(float, points[0])
        x2, y2 = map(float, points[1])
        if abs(x2 - x1) < 1e-12:
            return None
        slope = (y2 - y1) / (x2 - x1)
        answer = self._number_text(slope)
        basic = f"기울기는 (y값의 변화량)/(x값의 변화량)입니다.\n({self._number_text(y2)}-{self._number_text(y1)})/({self._number_text(x2)}-{self._number_text(x1)})={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"Δy/Δx={self._number_text(y2-y1)}/{self._number_text(x2-x1)}={answer}."
        similar = f"두 점 ({self._number_text(x1 + 1)},{self._number_text(y1 + 1)}), ({self._number_text(x2 + 1)},{self._number_text(y2 + 2)})를 지나는 직선의 기울기를 구하시오."
        return basic, fast, similar, answer

    def solve_distance_between_points(self, text: str):
        if "거리" not in text or "점" not in text:
            return None
        points = re.findall(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)", text)
        if len(points) < 2:
            return None
        x1, y1 = map(float, points[0])
        x2, y2 = map(float, points[1])
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        answer = self._number_text(distance)
        basic = f"두 점 사이의 거리는 √((x₂-x₁)²+(y₂-y₁)²)입니다.\n√(({self._number_text(x2)}-{self._number_text(x1)})²+({self._number_text(y2)}-{self._number_text(y1)})²)={answer}입니다."
        fast = f"가로 차와 세로 차를 제곱해 더하면 거리={answer}."
        similar = f"두 점 ({self._number_text(x1 + 1)},{self._number_text(y1)}), ({self._number_text(x2 + 1)},{self._number_text(y2 + 1)}) 사이의 거리를 구하시오."
        return basic, fast, similar, answer

    def solve_arithmetic_sequence_sum(self, text: str):
        if "등차수열" not in text or "합" not in text:
            return None
        first = self._labeled_number(text, ["첫째항", "첫 항", "a1"])
        diff = self._labeled_number(text, ["공차"])
        n = self._nth(text)
        if first is None or diff is None or n is None:
            return None
        last = first + (n - 1) * diff
        value = n * (first + last) / 2
        answer = self._number_text(value)
        basic = f"등차수열의 합은 Sₙ=n(a₁+aₙ)/2입니다.\naₙ={self._number_text(first)}+({n}-1)×{self._number_text(diff)}={self._number_text(last)}\nSₙ={n}×({self._number_text(first)}+{self._number_text(last)})/2={answer}입니다."
        fast = f"끝항 {self._number_text(last)}만 구한 뒤 평균×개수={answer}."
        similar = f"첫째항 {self._number_text(first + 1)}, 공차 {self._number_text(diff)}인 등차수열의 {n}번째 항까지의 합을 구하시오."
        return basic, fast, similar, answer

    def solve_arithmetic_sequence(self, text: str):
        if "등차수열" not in text:
            return None
        first = self._labeled_number(text, ["첫째항", "첫 항", "a1"])
        diff = self._labeled_number(text, ["공차"])
        n = self._nth(text)
        if first is None or diff is None or n is None:
            return None
        value = first + (n - 1) * diff
        answer = self._number_text(value)
        basic = f"등차수열의 n번째 항은 a_n=a_1+(n-1)d입니다.\na_{n}={self._number_text(first)}+({n}-1)×{self._number_text(diff)}={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"첫째항에 공차를 {n-1}번 더하면 {answer}입니다."
        similar = f"첫째항이 {self._number_text(first + 1)}, 공차가 {self._number_text(diff)}인 등차수열의 {n + 1}번째 항을 구하시오."
        return basic, fast, similar, answer

    def solve_geometric_sequence(self, text: str):
        if "등비수열" not in text:
            return None
        first = self._labeled_number(text, ["첫째항", "첫 항", "a1"])
        ratio = self._labeled_number(text, ["공비"])
        n = self._nth(text)
        if first is None or ratio is None or n is None:
            return None
        value = first * ratio ** (n - 1)
        answer = self._number_text(value)
        basic = f"등비수열의 n번째 항은 a_n=a_1×r^(n-1)입니다.\na_{n}={self._number_text(first)}×{self._number_text(ratio)}^({n}-1)={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"첫째항에 공비를 {n-1}번 곱하면 {answer}입니다."
        similar = f"첫째항이 {self._number_text(first)}, 공비가 {self._number_text(ratio + 1)}인 등비수열의 {n}번째 항을 구하시오."
        return basic, fast, similar, answer

    def solve_geometric_sequence_sum(self, text: str):
        if "등비수열" not in text or "합" not in text:
            return None
        first = self._labeled_number(text, ["첫째항", "첫 항", "a1"])
        ratio = self._labeled_number(text, ["공비"])
        n = self._nth(text)
        if first is None or ratio is None or n is None:
            return None
        value = first * n if abs(ratio - 1) < 1e-12 else first * (ratio**n - 1) / (ratio - 1)
        answer = self._number_text(value)
        basic = f"등비수열의 합은 Sₙ=a₁(rⁿ-1)/(r-1)입니다.\nSₙ={self._number_text(first)}×({self._number_text(ratio)}^{n}-1)/({self._number_text(ratio)}-1)={answer}입니다."
        fast = f"등비수열 합 공식에 바로 대입하면 {answer}."
        similar = f"첫째항 {self._number_text(first)}, 공비 {self._number_text(ratio + 1)}인 등비수열의 {n}번째 항까지의 합을 구하시오."
        return basic, fast, similar, answer

    def solve_percentage(self, text: str):
        match = re.search(r"(\d+(?:\.\d+)?)\s*%.*?(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?).*?(\d+(?:\.\d+)?)\s*%", text)
        if "%" not in text or not match:
            return None
        nums = [float(num) for num in re.findall(r"\d+(?:\.\d+)?", text)]
        percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if len(nums) < 2 or not percent_match:
            return None
        percent = float(percent_match.group(1))
        base = next((num for num in nums if abs(num - percent) > 1e-12), None)
        if base is None:
            return None
        value = base * percent / 100
        answer = self._number_text(value)
        basic = f"{self._number_text(base)}의 {self._number_text(percent)}%는 {self._number_text(base)}×{self._number_text(percent)}/100입니다.\n계산하면 {answer}입니다."
        fast = f"{self._number_text(percent)}%={self._number_text(percent / 100)}이므로 바로 곱하면 {answer}."
        similar = f"{self._number_text(base + 50)}의 {self._number_text(percent)}%를 구하시오."
        return basic, fast, similar, answer

    def solve_function_value(self, text: str):
        compact = self._compact(text)
        expr_match = re.search(r"f\(x\)=([+\-\d.*x^]+)", compact)
        target_matches = re.findall(r"f\((-?\d+(?:\.\d+)?)\)", compact)
        if not expr_match or not target_matches:
            return None
        coeffs = self._parse_polynomial(expr_match.group(1))
        if not coeffs:
            return None
        a, b, c = coeffs
        x = float(target_matches[-1])
        value = a * x**2 + b * x + c
        answer = self._number_text(value)
        expression = self._format_polynomial(a, b, c)
        basic = f"f(x)={expression}에 x={self._number_text(x)}를 대입합니다.\nf({self._number_text(x)})={answer}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"x={self._number_text(x)}를 바로 대입하면 {answer}."
        similar = f"f(x)={expression}일 때 f({self._number_text(x + 1)})를 구하시오."
        return basic, fast, similar, answer

    def solve_quadratic_extreme(self, text: str):
        wants_min = any(word in text for word in ["최솟값", "최소값", "minimum"])
        wants_max = any(word in text for word in ["최댓값", "최대값", "maximum"])
        if not wants_min and not wants_max:
            return None
        expr = self._extract_quadratic_expression(self._compact(text))
        coeffs = self._parse_polynomial(expr) if expr else None
        if not coeffs or abs(coeffs[0]) < 1e-12:
            return None
        a, b, c = coeffs
        x_vertex = -b / (2 * a)
        y_vertex = a * x_vertex**2 + b * x_vertex + c
        if (wants_min and a < 0) or (wants_max and a > 0):
            answer = "없음"
            basic = f"y={self._format_polynomial(a, b, c)}의 그래프 방향을 확인하면 요구한 극값은 전체 실수 범위에서 존재하지 않습니다.\n따라서 정답은 {answer}입니다."
            return basic, "그래프가 열리는 방향만 확인하면 됩니다.", "y=x^2-4x+1의 최솟값을 구하시오.", answer
        answer = self._number_text(y_vertex)
        kind = "최솟값" if wants_min else "최댓값"
        basic = f"y={self._format_polynomial(a, b, c)}에서 꼭짓점의 x좌표는 -b/(2a)={self._number_text(x_vertex)}입니다.\nx={self._number_text(x_vertex)}를 대입하면 y={answer}입니다.\n따라서 {kind}은 {answer}입니다."
        fast = f"꼭짓점만 보면 x=-b/(2a)={self._number_text(x_vertex)}, y={answer}. 답은 {answer}."
        similar = f"y={self._format_polynomial(a, b - 2, c + 3)}의 {kind}을 구하시오."
        return basic, fast, similar, answer

    def solve_quadratic_axis(self, text: str):
        if "축" not in text:
            return None
        expr = self._extract_quadratic_expression(self._compact(text))
        coeffs = self._parse_polynomial(expr) if expr else None
        if not coeffs or abs(coeffs[0]) < 1e-12:
            return None
        a, b, c = coeffs
        axis = -b / (2 * a)
        answer = f"x={self._number_text(axis)}"
        basic = f"이차함수 y={self._format_polynomial(a, b, c)}의 축은 꼭짓점의 x좌표입니다.\nx=-b/(2a)={self._number_text(axis)}입니다.\n따라서 정답은 {answer}입니다."
        fast = f"축은 x=-b/(2a), 즉 {answer}."
        similar = f"y={self._format_polynomial(a, b + 2, c)}의 축의 방정식을 구하시오."
        return basic, fast, similar, answer

    def solve_quadratic_equation(self, text: str):
        compact = self._compact(text)
        if "x^2" not in compact or "=" not in compact:
            return None
        match = re.search(rf"({self.QUADRATIC_EXPR})=0", compact)
        if not match:
            return None
        coeffs = self._parse_polynomial(match.group(1))
        if not coeffs or abs(coeffs[0]) < 1e-12:
            return None
        a, b, c = coeffs
        discriminant = b**2 - 4 * a * c
        expression = self._format_polynomial(a, b, c)
        if discriminant < 0:
            answer = "실근 없음"
            basic = f"{expression}=0의 판별식 D=b^2-4ac={self._number_text(discriminant)}입니다.\nD<0이므로 실근이 없습니다."
            return basic, "판별식이 음수이므로 실근 없음.", f"{expression}-1=0을 풀어보시오.", answer
        sqrt_d = math.sqrt(discriminant)
        roots = sorted([(-b - sqrt_d) / (2 * a), (-b + sqrt_d) / (2 * a)])
        answer = f"x={self._number_text(roots[0])}" if abs(roots[0] - roots[1]) < 1e-12 else f"x={self._number_text(roots[0])} 또는 x={self._number_text(roots[1])}"
        basic = f"{expression}=0에서 D={self._number_text(discriminant)}입니다.\n근의 공식 x=(-b±√D)/(2a)를 적용하면 {answer}입니다."
        fast = f"근의 공식 또는 인수분해로 {answer}."
        similar = f"{self._format_polynomial(a, b - 1, c)}=0을 풀어보시오."
        return basic, fast, similar, answer

    def solve_linear_inequality(self, text: str):
        compact = self._compact(text)
        if "x^2" in compact:
            return None
        match = re.search(r"([+\-\d.*x]+)(<=|>=|<|>)([+\-\d.*x]+)", compact)
        if not match:
            return None
        left, operator, right = match.groups()
        left_coeffs, right_coeffs = self._parse_polynomial(left), self._parse_polynomial(right)
        if not left_coeffs or not right_coeffs:
            return None
        coefficient = left_coeffs[1] - right_coeffs[1]
        constant = right_coeffs[2] - left_coeffs[2]
        if abs(coefficient) < 1e-12:
            return None
        if coefficient < 0:
            operator = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[operator]
        boundary = constant / coefficient
        answer = f"x{operator}{self._number_text(boundary)}"
        basic = f"x항과 상수항을 정리하면 {self._number_text(coefficient)}x{match.group(2)}{self._number_text(constant)}입니다.\n계수가 음수이면 부등호 방향을 바꿉니다.\n따라서 {answer}입니다."
        fast = f"이항 후 계수의 부호만 확인하면 {answer}."
        similar = f"{self._format_linear(left_coeffs[1] + 1, left_coeffs[2])}{match.group(2)}{self._format_linear(right_coeffs[1], right_coeffs[2] + 2)}를 풀어보시오."
        return basic, fast, similar, answer

    def solve_linear_equation(self, text: str):
        compact = self._compact(text)
        if "x^2" in compact:
            return None
        equation = self._extract_equation(compact)
        if not equation:
            return None
        left, right = equation
        left_coeffs, right_coeffs = self._parse_polynomial(left), self._parse_polynomial(right)
        if not left_coeffs or not right_coeffs:
            return None
        a = left_coeffs[1] - right_coeffs[1]
        b = right_coeffs[2] - left_coeffs[2]
        if abs(a) < 1e-12:
            return None
        x = b / a
        answer = f"x={self._number_text(x)}"
        basic = f"x항은 왼쪽, 상수항은 오른쪽으로 모읍니다.\n{self._number_text(a)}x={self._number_text(b)}이므로 {answer}입니다."
        fast = f"정리하면 {self._number_text(a)}x={self._number_text(b)}, {answer}."
        similar = f"{self._format_linear(left_coeffs[1] + 1, left_coeffs[2])}={self._format_linear(right_coeffs[1], right_coeffs[2] + 2)}를 풀어보시오."
        return basic, fast, similar, answer

    def solve_simultaneous_equations(self, text: str):
        compact = self._compact(text)
        match = re.search(r"([+-]?\d*)x([+-]\d*)y=([+-]?\d+).*?([+-]?\d*)x([+-]\d*)y=([+-]?\d+)", compact)
        if not match:
            return None
        a1, b1, c1, a2, b2, c2 = match.groups()
        a1, b1, c1, a2, b2, c2 = self._coef(a1), self._coef(b1), int(c1), self._coef(a2), self._coef(b2), int(c2)
        det = a1 * b2 - a2 * b1
        if det == 0:
            return None
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        answer = f"x={self._number_text(x)}, y={self._number_text(y)}"
        basic = f"연립방정식을 소거법으로 정리합니다.\n계산하면 {answer}입니다."
        fast = f"소거법으로 바로 계산하면 {answer}."
        similar = "2x+3y=13, x-y=1을 풀어보시오."
        return basic, fast, similar, answer

    def solve_proportion(self, text: str):
        match = re.search(r"(\d+):(\d+)=x:(\d+)", self._compact(text))
        if not match:
            return None
        a, b, c = map(int, match.groups())
        if b == 0:
            return None
        x = a * c / b
        answer = f"x={self._number_text(x)}"
        basic = f"{a}:{b}=x:{c}에서 대각선끼리 곱하면 {b}x={a}×{c}입니다.\n따라서 {answer}입니다."
        fast = f"x={a}×{c}/{b}={self._number_text(x)}."
        similar = f"{a + 1}:{b}=x:{c + 2}에서 x를 구하시오."
        return basic, fast, similar, answer

    def solve_average(self, text: str):
        if "평균" not in text:
            return None
        nums = [float(num) for num in re.findall(self.NUMBER, text)]
        if len(nums) < 2:
            return None
        avg = sum(nums) / len(nums)
        answer = self._number_text(avg)
        basic = f"평균은 자료의 합을 개수로 나눈 값입니다.\n합={self._number_text(sum(nums))}, 개수={len(nums)}이므로 평균={answer}입니다."
        fast = f"합÷개수={answer}."
        similar = f"{', '.join(self._number_text(n + 1) for n in nums)}의 평균을 구하시오."
        return basic, fast, similar, answer

    def solve_probability_basic(self, text: str):
        if "확률" not in text:
            return None
        match = re.search(r"(?:전체\s*)?(\d+)\s*개\s*(?:중|에서)\s*(?:유리한\s*)?(\d+)\s*개", text)
        if not match:
            return None
        total, favorable = map(int, match.groups())
        if total == 0:
            return None
        probability = favorable / total
        answer = self._number_text(probability)
        basic = f"확률은 유리한 경우의 수/전체 경우의 수입니다.\n{favorable}/{total}={answer}입니다."
        fast = f"확률={favorable}/{total}={answer}."
        similar = f"전체 {total + 2}개 중 유리한 경우가 {favorable + 1}개일 때 확률을 구하시오."
        return basic, fast, similar, answer

    def solve_exponent(self, text: str):
        match = re.search(r"(\d+)\^(\d+)", self._compact(text))
        if not match or "x^" in self._compact(text):
            return None
        base, exp = map(int, match.groups())
        value = base**exp
        basic = f"{base}^{exp}은 {base}를 {exp}번 곱한 값입니다.\n따라서 {base}^{exp}={value}입니다."
        return basic, f"{base}^{exp}={value}.", f"{base + 1}^{exp}을 계산하시오.", str(value)

    def _normalize(self, text: str) -> str:
        return (
            str(text or "")
            .replace("²", "^2")
            .replace("³", "^3")
            .replace("−", "-")
            .replace("–", "-")
            .replace("×", "*")
            .replace("÷", "/")
            .replace("＝", "=")
        )

    def _compact(self, text: str) -> str:
        return re.sub(r"\s+", "", self._normalize(text)).lower()

    def _labeled_number(self, text: str, labels: list[str]) -> float | None:
        for label in labels:
            patterns = [
                rf"{re.escape(label)}\s*(?:=|이|가|은|는|:)?\s*(-?\d+(?:\.\d+)?)",
                rf"(-?\d+(?:\.\d+)?)\s*(?:cm|mm|m)?\s*(?:인|의)?\s*{re.escape(label)}",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return float(match.group(1))
        return None

    def _nth(self, text: str) -> int | None:
        match = re.search(r"(\d+)\s*(?:번째|번\s*째|항)", text)
        return int(match.group(1)) if match else None

    def _extract_quadratic_expression(self, compact: str) -> str | None:
        match = re.search(rf"(?:y=|f\(x\)=)({self.QUADRATIC_EXPR})", compact)
        if match:
            return match.group(1)
        match = re.search(rf"({self.QUADRATIC_EXPR})", compact)
        return match.group(1) if match else None

    def _extract_equation(self, compact: str) -> tuple[str, str] | None:
        match = re.search(r"([+\-\d.*x^]+)=([+\-\d.*x^]+)", compact)
        return (match.group(1), match.group(2)) if match else None

    def _parse_polynomial(self, expr: str | None) -> tuple[float, float, float] | None:
        if not expr:
            return None
        expr = expr.replace("*", "")
        normalized = expr.replace("-", "+-")
        if normalized.startswith("+-"):
            normalized = normalized[1:]
        terms = [term for term in normalized.split("+") if term]
        a = b = c = 0.0
        try:
            for term in terms:
                if term.endswith("x^2"):
                    a += self._coef_float(term[:-3])
                elif term.endswith("x"):
                    b += self._coef_float(term[:-1])
                else:
                    c += float(term)
        except ValueError:
            return None
        return a, b, c

    def _coef_float(self, text: str) -> float:
        if text in ["", "+"]:
            return 1.0
        if text == "-":
            return -1.0
        return float(text)

    def _coef(self, text: str) -> int:
        if text in ["", "+"]:
            return 1
        if text == "-":
            return -1
        return int(text)

    def _format_polynomial(self, a: float, b: float, c: float) -> str:
        return "".join(filter(None, [self._format_term(a, "x^2", True), self._format_term(b, "x"), self._format_term(c, "")])) or "0"

    def _format_linear(self, a: float, b: float) -> str:
        return "".join(filter(None, [self._format_term(a, "x", True), self._format_term(b, "")])) or "0"

    def _format_term(self, value: float, suffix: str, leading: bool = False) -> str:
        if abs(value) < 1e-12:
            return ""
        number = "" if suffix and abs(abs(value) - 1) < 1e-12 else self._number_text(abs(value))
        if leading:
            return f"-{number}{suffix}" if value < 0 else f"{number}{suffix}"
        return f"{'-' if value < 0 else '+'}{number}{suffix}"

    def _number_text(self, value: float) -> str:
        value = float(value)
        if abs(value - round(value)) < 1e-10:
            return str(int(round(value)))
        return f"{value:.4f}".rstrip("0").rstrip(".")
