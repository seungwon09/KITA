import re


class ScienceSolver:
    """Small, deterministic solver for common middle/high-school science formulas."""

    def solve(self, problem_text: str) -> tuple[str, str, str, str | None] | None:
        text = self._normalize(problem_text)
        solvers = [
            self.solve_combined_circuit,
            self.solve_acceleration_change,
            self.solve_heat_energy,
            self.solve_wave_speed,
            self.solve_wave_period,
            self.solve_kinetic_energy,
            self.solve_potential_energy,
            self.solve_momentum,
            self.solve_impulse,
            self.solve_electrical_energy,
            self.solve_power,
            self.solve_ohms_law,
            self.solve_work,
            self.solve_pressure,
            self.solve_force,
            self.solve_density,
            self.solve_molarity,
            self.solve_mass_from_moles,
            self.solve_moles,
            self.solve_mass_percent_concentration,
            self.solve_speed_distance_time,
        ]
        for solver in solvers:
            result = solver(text)
            if result:
                return result
        return None

    def solve_combined_circuit(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not ("전압" in text and "전력" in text):
            return None
        current = self._extract_number(text, ["A"])
        resistance = self._extract_number(text, ["Ω", "ohm"])
        if current is None or resistance is None:
            return None
        voltage = current * resistance
        power = voltage * current
        v, p = self._number_text(voltage), self._number_text(power)
        basic = (
            "옴의 법칙 V=IR로 전압을 먼저 구합니다.\n"
            f"V={self._number_text(current)}×{self._number_text(resistance)}={v}V\n"
            "그다음 P=VI를 사용합니다.\n"
            f"P={v}×{self._number_text(current)}={p}W\n"
            f"따라서 전압은 {v}V, 전력은 {p}W입니다."
        )
        return basic, f"V=IR={v}V, P=VI={p}W.", f"저항이 {self._number_text(resistance + 1)}Ω일 때 전압과 전력을 구해 보세요.", f"{v}V, {p}W"

    def solve_acceleration_change(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "가속도" not in text:
            return None
        speeds = [float(value) for value in re.findall(r"(-?\d+(?:\.\d+)?)\s*m/s(?!\^)", text)]
        seconds = self._extract_labeled_number(text, ["시간", "동안"], ["초", "s"])
        if len(speeds) < 2 or seconds in [None, 0]:
            return None
        acceleration = (speeds[1] - speeds[0]) / seconds
        answer = self._number_text(acceleration)
        basic = (
            "가속도는 속도 변화량을 걸린 시간으로 나눈 값입니다.\n"
            f"a=({self._number_text(speeds[1])}-{self._number_text(speeds[0])})/{self._number_text(seconds)}={answer}m/s²\n"
            f"따라서 가속도는 {answer}m/s²입니다."
        )
        return basic, f"a=Δv/t={answer}m/s².", "처음 속도와 나중 속도를 바꿔 같은 방식으로 풀어 보세요.", f"{answer}m/s^2"

    def solve_heat_energy(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["열량", "비열", "온도 변화"]):
            return None
        specific_heat = self._extract_labeled_number(text, ["비열"], ["J/g℃", "J/g°C", "J/g도", "J/g"])
        mass = self._extract_labeled_number(text, ["질량"], ["g", "kg"])
        delta_t = self._extract_labeled_number(text, ["온도 변화", "온도변화", "온도차"], ["℃", "°C", "도"])
        if specific_heat is None or mass is None or delta_t is None:
            return None
        if "kg" in text and re.search(r"질량[^\d]*\d+(?:\.\d+)?\s*kg", text):
            mass *= 1000
        heat = specific_heat * mass * delta_t
        answer = self._number_text(heat)
        basic = (
            "열량은 Q=cmΔT입니다.\n"
            f"Q={self._number_text(specific_heat)}×{self._number_text(mass)}×{self._number_text(delta_t)}={answer}J\n"
            f"따라서 필요한 열량은 {answer}J입니다."
        )
        return basic, f"Q=cmΔT에 바로 대입하면 {answer}J.", "질량이나 온도 변화량을 바꿔 다시 계산해 보세요.", f"{answer}J"

    def solve_wave_speed(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["파동", "파장", "진동수"]):
            return None
        wavelength = self._extract_labeled_number(text, ["파장"], ["m"])
        frequency = self._extract_labeled_number(text, ["진동수", "주파수"], ["Hz"])
        if wavelength is None or frequency is None:
            return None
        speed = wavelength * frequency
        answer = self._number_text(speed)
        basic = (
            "파동의 속력은 v=fλ입니다.\n"
            f"v={self._number_text(frequency)}×{self._number_text(wavelength)}={answer}m/s\n"
            f"따라서 속력은 {answer}m/s입니다."
        )
        return basic, f"v=fλ={answer}m/s.", "파장이나 진동수를 바꿔 같은 식으로 풀어 보세요.", f"{answer}m/s"

    def solve_wave_period(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "주기" not in text and "진동수" not in text and "주파수" not in text:
            return None
        frequency = self._extract_labeled_number(text, ["진동수", "주파수"], ["Hz"])
        period = self._extract_labeled_number(text, ["주기"], ["s", "초"])
        if period is None and frequency not in [None, 0]:
            answer = self._number_text(1 / frequency)
            return self._formula_result("주기", "T=1/f", f"1/{self._number_text(frequency)}", answer, "s")
        if frequency is None and period not in [None, 0]:
            answer = self._number_text(1 / period)
            return self._formula_result("진동수", "f=1/T", f"1/{self._number_text(period)}", answer, "Hz")
        return None

    def solve_kinetic_energy(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "운동 에너지" not in text and "운동에너지" not in text:
            return None
        mass = self._extract_number(text, ["kg"])
        speed = self._extract_number(text, ["m/s"])
        if mass is None or speed is None:
            return None
        energy = 0.5 * mass * speed**2
        answer = self._number_text(energy)
        basic = (
            "운동 에너지는 Eₖ=½mv²입니다.\n"
            f"Eₖ=½×{self._number_text(mass)}×{self._number_text(speed)}²={answer}J\n"
            f"따라서 운동 에너지는 {answer}J입니다."
        )
        return basic, f"Eₖ=½mv²={answer}J.", "질량이나 속력을 바꿔 운동 에너지를 다시 구해 보세요.", f"{answer}J"

    def solve_potential_energy(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "위치 에너지" not in text and "위치에너지" not in text:
            return None
        mass = self._extract_number(text, ["kg"])
        height = self._extract_labeled_number(text, ["높이"], ["m"])
        gravity = self._extract_labeled_number(text, ["중력 가속도", "g"], ["m/s^2"])
        if mass is None or height is None:
            return None
        gravity = gravity or 9.8
        energy = mass * gravity * height
        answer = self._number_text(energy)
        basic = (
            "위치 에너지는 Eₚ=mgh입니다.\n"
            f"Eₚ={self._number_text(mass)}×{self._number_text(gravity)}×{self._number_text(height)}={answer}J\n"
            f"따라서 위치 에너지는 {answer}J입니다."
        )
        return basic, f"Eₚ=mgh={answer}J.", "질량이나 높이를 바꿔 위치 에너지를 다시 구해 보세요.", f"{answer}J"

    def solve_momentum(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "운동량" not in text:
            return None
        mass = self._extract_number(text, ["kg"])
        speed = self._extract_number(text, ["m/s"])
        if mass is None or speed is None:
            return None
        answer = self._number_text(mass * speed)
        return self._formula_result("운동량", "p=mv", f"{self._number_text(mass)}×{self._number_text(speed)}", answer, "kg·m/s")

    def solve_impulse(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "충격량" not in text:
            return None
        force = self._extract_number(text, ["N"])
        seconds = self._extract_labeled_number(text, ["시간", "동안"], ["초", "s"])
        if force is None or seconds is None:
            return None
        answer = self._number_text(force * seconds)
        return self._formula_result("충격량", "I=FΔt", f"{self._number_text(force)}×{self._number_text(seconds)}", answer, "N·s")

    def solve_electrical_energy(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["전기에너지", "전기 에너지", "전력량"]):
            return None
        power = self._extract_number(text, ["W"])
        seconds = self._extract_labeled_number(text, ["시간", "동안"], ["시간", "분", "초", "s"])
        if power is None or seconds is None:
            return None
        answer = self._number_text(power * seconds)
        return self._formula_result("전기에너지", "E=Pt", f"{self._number_text(power)}×{self._number_text(seconds)}", answer, "J")

    def solve_ohms_law(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["옴", "전압", "전류", "저항", "V=IR"]):
            return None
        voltage = self._extract_number(text, ["V"])
        current = self._extract_number(text, ["A"])
        resistance = self._extract_number(text, ["Ω", "ohm"])
        if voltage is None and current is not None and resistance is not None:
            answer = self._number_text(current * resistance)
            return self._formula_result("전압", "V=IR", f"{self._number_text(current)}×{self._number_text(resistance)}", answer, "V")
        if current is None and voltage is not None and resistance not in [None, 0]:
            answer = self._number_text(voltage / resistance)
            return self._formula_result("전류", "I=V/R", f"{self._number_text(voltage)}/{self._number_text(resistance)}", answer, "A")
        if resistance is None and voltage is not None and current not in [None, 0]:
            answer = self._number_text(voltage / current)
            return self._formula_result("저항", "R=V/I", f"{self._number_text(voltage)}/{self._number_text(current)}", answer, "Ω")
        return None

    def solve_work(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["일", "W=Fs", "이동 거리"]):
            return None
        work = self._extract_number(text, ["J"])
        force = self._extract_number(text, ["N"])
        distance = self._extract_labeled_number(text, ["거리", "이동 거리"], ["m"])
        if distance is None:
            distance = self._extract_number(text, ["m"])
        if work is None and force is not None and distance is not None:
            answer = self._number_text(force * distance)
            return self._formula_result("일", "W=Fs", f"{self._number_text(force)}×{self._number_text(distance)}", answer, "J")
        if force is None and work is not None and distance not in [None, 0]:
            answer = self._number_text(work / distance)
            return self._formula_result("힘", "F=W/s", f"{self._number_text(work)}/{self._number_text(distance)}", answer, "N")
        if distance is None and work is not None and force not in [None, 0]:
            answer = self._number_text(work / force)
            return self._formula_result("거리", "s=W/F", f"{self._number_text(work)}/{self._number_text(force)}", answer, "m")
        return None

    def solve_pressure(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "압력" not in text and "P=F/A" not in text:
            return None
        pressure = self._extract_number(text, ["Pa"])
        force = self._extract_number(text, ["N"])
        area = self._extract_labeled_number(text, ["면적", "넓이"], ["m^2"])
        if pressure is None and force is not None and area not in [None, 0]:
            answer = self._number_text(force / area)
            return self._formula_result("압력", "P=F/A", f"{self._number_text(force)}/{self._number_text(area)}", answer, "Pa")
        if force is None and pressure is not None and area is not None:
            answer = self._number_text(pressure * area)
            return self._formula_result("힘", "F=PA", f"{self._number_text(pressure)}×{self._number_text(area)}", answer, "N")
        if area is None and pressure not in [None, 0] and force is not None:
            answer = self._number_text(force / pressure)
            return self._formula_result("면적", "A=F/P", f"{self._number_text(force)}/{self._number_text(pressure)}", answer, "m²")
        return None

    def solve_force(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["힘", "F=ma", "가속도"]):
            return None
        force = self._extract_number(text, ["N"])
        mass = self._extract_number(text, ["kg"])
        acceleration = self._extract_number(text, ["m/s^2"])
        if force is None and mass is not None and acceleration is not None:
            answer = self._number_text(mass * acceleration)
            return self._formula_result("힘", "F=ma", f"{self._number_text(mass)}×{self._number_text(acceleration)}", answer, "N")
        if mass is None and force is not None and acceleration not in [None, 0]:
            answer = self._number_text(force / acceleration)
            return self._formula_result("질량", "m=F/a", f"{self._number_text(force)}/{self._number_text(acceleration)}", answer, "kg")
        if acceleration is None and force is not None and mass not in [None, 0]:
            answer = self._number_text(force / mass)
            return self._formula_result("가속도", "a=F/m", f"{self._number_text(force)}/{self._number_text(mass)}", answer, "m/s^2", "m/s²")
        return None

    def solve_density(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["밀도", "부피"]):
            return None
        density = self._extract_number(text, ["g/cm^3"])
        mass = self._extract_labeled_number(text, ["질량"], ["g"])
        volume = self._extract_labeled_number(text, ["부피"], ["cm^3", "mL"])
        if density is None and mass is not None and volume not in [None, 0]:
            answer = self._number_text(mass / volume)
            return self._formula_result("밀도", "ρ=m/V", f"{self._number_text(mass)}/{self._number_text(volume)}", answer, "g/cm³")
        if mass is None and density is not None and volume is not None:
            answer = self._number_text(density * volume)
            return self._formula_result("질량", "m=ρV", f"{self._number_text(density)}×{self._number_text(volume)}", answer, "g")
        if volume is None and density not in [None, 0] and mass is not None:
            answer = self._number_text(mass / density)
            return self._formula_result("부피", "V=m/ρ", f"{self._number_text(mass)}/{self._number_text(density)}", answer, "cm³")
        return None

    def solve_power(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["전력", "P=VI"]):
            return None
        power = self._extract_number(text, ["W"])
        voltage = self._extract_number(text, ["V"])
        current = self._extract_number(text, ["A"])
        if power is None and voltage is not None and current is not None:
            answer = self._number_text(voltage * current)
            return self._formula_result("전력", "P=VI", f"{self._number_text(voltage)}×{self._number_text(current)}", answer, "W")
        if voltage is None and power is not None and current not in [None, 0]:
            answer = self._number_text(power / current)
            return self._formula_result("전압", "V=P/I", f"{self._number_text(power)}/{self._number_text(current)}", answer, "V")
        if current is None and power is not None and voltage not in [None, 0]:
            answer = self._number_text(power / voltage)
            return self._formula_result("전류", "I=P/V", f"{self._number_text(power)}/{self._number_text(voltage)}", answer, "A")
        return None

    def solve_molarity(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["몰농도", "몰 농도"]):
            return None
        moles = self._extract_labeled_number(text, ["몰수", "용질"], ["mol"])
        volume = self._extract_labeled_number(text, ["부피", "용액"], ["L"])
        if moles is None or volume in [None, 0]:
            return None
        answer = self._number_text(moles / volume)
        return self._formula_result("몰농도", "M=n/V", f"{self._number_text(moles)}/{self._number_text(volume)}", answer, "M")

    def solve_mass_from_moles(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "질량" not in text or "몰" not in text:
            return None
        moles = self._extract_labeled_number(text, ["몰수"], ["mol"])
        molar_mass = self._extract_labeled_number(text, ["몰 질량", "몰질량"], ["g/mol"])
        if moles is None or molar_mass is None:
            return None
        answer = self._number_text(moles * molar_mass)
        return self._formula_result("질량", "m=nM", f"{self._number_text(moles)}×{self._number_text(molar_mass)}", answer, "g")

    def solve_moles(self, text: str) -> tuple[str, str, str, str | None] | None:
        if "몰수" not in text and "몰 수" not in text:
            return None
        mass = self._extract_labeled_number(text, ["질량"], ["g"])
        molar_mass = self._extract_labeled_number(text, ["몰 질량", "몰질량"], ["g/mol"])
        if mass is None or molar_mass in [None, 0]:
            return None
        answer = self._number_text(mass / molar_mass)
        return self._formula_result("몰수", "n=m/M", f"{self._number_text(mass)}/{self._number_text(molar_mass)}", answer, "mol")

    def solve_mass_percent_concentration(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["질량 퍼센트 농도", "질량 백분율", "질량%농도"]):
            return None
        solute = self._extract_labeled_number(text, ["용질"], ["g"])
        solution = self._extract_labeled_number(text, ["용액"], ["g"])
        if solute is None or solution in [None, 0]:
            return None
        answer = self._number_text(solute / solution * 100)
        return self._formula_result("질량 퍼센트 농도", "농도=용질/용액×100", f"{self._number_text(solute)}/{self._number_text(solution)}×100", answer, "%")

    def solve_speed_distance_time(self, text: str) -> tuple[str, str, str, str | None] | None:
        if not any(word in text for word in ["속력", "속도", "거리", "시간"]):
            return None
        speed = self._extract_number(text, ["m/s"])
        distance = self._extract_labeled_number(text, ["거리", "이동 거리"], ["km", "m"])
        seconds = self._extract_labeled_number(text, ["시간", "동안"], ["시간", "분", "초", "s"])
        if speed is None and distance is not None and seconds not in [None, 0]:
            answer = self._number_text(distance / seconds)
            return self._formula_result("속력", "v=s/t", f"{self._number_text(distance)}/{self._number_text(seconds)}", answer, "m/s")
        if distance is None and speed is not None and seconds is not None:
            answer = self._number_text(speed * seconds)
            return self._formula_result("거리", "s=vt", f"{self._number_text(speed)}×{self._number_text(seconds)}", answer, "m")
        if seconds is None and speed not in [None, 0] and distance is not None:
            answer = self._number_text(distance / speed)
            return self._formula_result("시간", "t=s/v", f"{self._number_text(distance)}/{self._number_text(speed)}", answer, "s")
        return None

    def _formula_result(
        self, label: str, formula: str, calculation: str, answer: str, unit: str, display_unit: str | None = None
    ) -> tuple[str, str, str, str]:
        verified = f"{answer}{unit}"
        shown = f"{answer}{display_unit or unit}"
        basic = f"{label}을 구하는 식은 {formula}입니다.\n{formula.split('=')[0]}={calculation}={shown}\n따라서 {label}은 {shown}입니다."
        return basic, f"{formula}={shown}.", f"숫자를 바꿔 {formula}를 한 번 더 적용해 보세요.", verified

    def _extract_number(self, text: str, units: list[str]) -> float | None:
        for unit in units:
            match = re.search(rf"(-?\d+(?:\.\d+)?)\s*{self._unit_pattern(unit)}", text, re.IGNORECASE)
            if match:
                return self._convert_unit(float(match.group(1)), unit)
        return None

    def _extract_labeled_number(self, text: str, labels: list[str], units: list[str]) -> float | None:
        for label in labels:
            for unit in units:
                patterns = [
                    rf"{re.escape(label)}[^\d-]{{0,20}}(-?\d+(?:\.\d+)?)\s*{self._unit_pattern(unit)}",
                    rf"(-?\d+(?:\.\d+)?)\s*{self._unit_pattern(unit)}[^\n,.]{{0,16}}{re.escape(label)}",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return self._convert_unit(float(match.group(1)), unit)
        return None

    def _unit_pattern(self, unit: str) -> str:
        aliases = {
            "Ω": r"(?:Ω|Ω|옴)",
            "ohm": r"(?:ohm|옴)",
            "m/s^2": r"(?:m/s\^?2|m/s²)",
            "m^2": r"(?:m\^?2|m²)",
            "cm^3": r"(?:cm\^?3|cm³)",
            "g/cm^3": r"(?:g/cm\^?3|g/cm³)",
            "J/g℃": r"(?:J/g℃|J/g°C)",
            "J/g°C": r"(?:J/g°C|J/g℃)",
            "J/g도": r"(?:J/g도|J/g℃|J/g°C|J/g)",
            "°C": r"(?:°C|℃)",
            "℃": r"(?:℃|°C)",
            "도": r"(?:도|°C|℃)",
        }
        escaped = aliases.get(unit, re.escape(unit))
        if unit in {"m", "s", "g", "kg", "V", "A", "N", "W", "J", "Pa", "L"}:
            return rf"{escaped}(?![/A-Za-z0-9_^²³])"
        if unit == "m/s":
            return rf"{escaped}(?![\^²])"
        return escaped

    def _convert_unit(self, value: float, unit: str) -> float:
        if unit == "km":
            return value * 1000
        if unit == "분":
            return value * 60
        if unit == "시간":
            return value * 3600
        return value

    def _normalize(self, text: str) -> str:
        return (
            text.replace("×", "*")
            .replace("㎨", "m/s^2")
            .replace("㎡", "m^2")
            .replace("㎥", "m^3")
            .replace("㎤", "cm^3")
            .replace("Ω", "Ω")
            .strip()
        )

    def _number_text(self, value: float) -> str:
        number = float(value)
        if abs(number - round(number)) < 1e-10:
            return str(int(round(number)))
        return f"{number:.6f}".rstrip("0").rstrip(".")
