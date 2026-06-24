from backend.app.schemas.health import AssessmentRequest, RiskSummary


class RiskService:
    def score(self, request: AssessmentRequest, red_flag_count: int = 0) -> RiskSummary:
        profile = request.profile
        points = 0
        factors: list[str] = []

        if profile.age >= 60:
            points += 12
            factors.append("Age above 60")
        elif profile.age >= 40:
            points += 6
            factors.append("Age above 40")

        if profile.bmi:
            if profile.bmi >= 30:
                points += 14
                factors.append("BMI in obesity range")
            elif profile.bmi >= 25:
                points += 8
                factors.append("BMI in overweight range")
            elif profile.bmi < 18.5:
                points += 6
                factors.append("BMI below healthy range")

        if profile.sleep_hours is not None and profile.sleep_hours < 6:
            points += 8
            factors.append("Short sleep duration")

        exercise = (profile.exercise_frequency or "").lower()
        if any(term in exercise for term in ["none", "rare", "low", "0"]):
            points += 8
            factors.append("Low physical activity")

        occupation = (profile.occupation or "").lower()
        if any(term in occupation for term in ["software", "desk", "driver", "office"]):
            points += 7
            factors.append("Sedentary occupation")
        if any(term in occupation for term in ["construction", "factory", "outdoor"]):
            points += 7
            factors.append("Physical or environmental occupational exposure")

        diet_text = " ".join([profile.diet_style or "", *profile.food_habits]).lower()
        diet_terms = {
            "sugar": "High sugar intake",
            "salt": "High salt intake",
            "processed": "Processed food intake",
            "late": "Late-night eating",
            "caffeine": "Excess caffeine",
            "low water": "Low water intake",
            "low protein": "Low protein or low vegetable intake",
            "low vegetables": "Low protein or low vegetable intake",
        }
        for term, label in diet_terms.items():
            if term in diet_text:
                points += 5
                factors.append(label)

        smoking = (profile.smoking_status or "").lower()
        if "current" in smoking:
            points += 12
            factors.append("Current smoking")
        elif "former" in smoking or "passive" in smoking:
            points += 5
            factors.append("Smoking exposure history")

        alcohol = (profile.alcohol_status or "").lower()
        if "frequent" in alcohol:
            points += 8
            factors.append("Frequent alcohol intake")
        elif "occasional" in alcohol:
            points += 3
            factors.append("Alcohol intake")

        if profile.existing_conditions:
            condition_text = " ".join(profile.existing_conditions).lower()
            condition_weights = {
                "diabetes": 10,
                "bp": 8,
                "blood pressure": 8,
                "hypertension": 8,
                "heart": 12,
                "kidney": 12,
                "asthma": 7,
                "thyroid": 5,
            }
            matched = sum(weight for term, weight in condition_weights.items() if term in condition_text)
            points += min(22, matched or 5 * len(profile.existing_conditions))
            factors.append("Existing medical conditions")
        if profile.family_history:
            family_text = " ".join(profile.family_history).lower()
            inherited_markers = ["diabetes", "heart", "stroke", "cancer", "bp", "hypertension"]
            points += min(14, 6 if any(term in family_text for term in inherited_markers) else 4 * len(profile.family_history))
            factors.append("Family medical history")

        for symptom in request.symptoms:
            if symptom.severity:
                points += min(12, symptom.severity)
                if symptom.severity >= 7:
                    factors.append(f"Severe symptom: {symptom.name}")
            if symptom.duration_days and symptom.duration_days >= 3:
                points += 5
                factors.append(f"Persistent symptom: {symptom.name}")

        if red_flag_count:
            points = max(points, 76)
            factors.append("Emergency red-flag symptom")

        score = min(100, points)
        if score >= 76:
            level = "Urgent"
        elif score >= 51:
            level = "High"
        elif score >= 21:
            level = "Moderate"
        else:
            level = "Low"

        if not factors:
            factors.append("No major risk factors detected from provided information")

        return RiskSummary(overall_risk_level=level, risk_score=score, key_risk_factors=list(dict.fromkeys(factors)))
