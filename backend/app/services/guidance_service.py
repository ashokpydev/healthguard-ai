from backend.app.schemas.health import AssessmentRequest


class GuidanceService:
    def lifestyle_precautions(self, request: AssessmentRequest) -> list[str]:
        profile = request.profile
        occupation = (profile.occupation or "").lower()
        precautions: list[str] = []

        if any(term in occupation for term in ["software", "desk", "office"]):
            precautions.extend(
                [
                    "Take a 5-minute movement break every hour during desk work.",
                    "Use the 20-20-20 eye-rest rule when using screens.",
                    "Review chair, monitor, and keyboard ergonomics to reduce neck and back strain.",
                ]
            )
        if any(term in occupation for term in ["construction", "factory", "outdoor"]):
            precautions.extend(
                [
                    "Use appropriate protective equipment for dust, heat, and injury prevention.",
                    "Plan hydration and rest breaks during hot or physically demanding work.",
                ]
            )
        if profile.sleep_hours is not None and profile.sleep_hours < 6:
            precautions.append("Prioritize a consistent sleep schedule and discuss persistent poor sleep with a clinician.")
        if (profile.smoking_status or "").lower():
            precautions.append("Avoid tobacco exposure and discuss cessation support with a qualified clinician if relevant.")
        if "frequent" in (profile.alcohol_status or "").lower():
            precautions.append("Reduce alcohol intake and discuss liver, BP, sleep, and metabolic health screening with a clinician.")
        return precautions

    def diet_precautions(self, request: AssessmentRequest) -> list[str]:
        diet_text = " ".join([request.profile.diet_style or "", *request.profile.food_habits]).lower()
        precautions: list[str] = []
        if "sugar" in diet_text:
            precautions.append("Reduce sugary drinks and frequent sweets; choose whole foods when possible.")
        if "salt" in diet_text:
            precautions.append("Limit high-salt packaged foods and discuss blood pressure screening if relevant.")
        if "processed" in diet_text:
            precautions.append("Replace processed snacks with fiber-rich foods such as vegetables, pulses, fruit, or whole grains.")
        if "low water" in diet_text:
            precautions.append("Keep regular hydration reminders, especially in hot weather or during outdoor work.")
        if "low protein" in diet_text or "low vegetables" in diet_text:
            precautions.append("Add safe protein sources and vegetables according to personal tolerance and medical restrictions.")
        if "late" in diet_text:
            precautions.append("Avoid heavy late-night meals when possible, especially if sleep, acidity, or weight are concerns.")
        if not precautions:
            precautions.append("Aim for balanced meals with protein, fiber-rich carbohydrates, vegetables, and adequate water.")
        precautions.append("Consult a dietician for a personalized nutrition plan, especially with diabetes, BP, kidney, or heart concerns.")
        return precautions

    def climate_precautions(self, request: AssessmentRequest) -> list[str]:
        location_text = " ".join([request.profile.location or "", request.profile.climate or ""]).lower()
        precautions: list[str] = []
        if any(term in location_text for term in ["hot", "hyderabad", "heat"]):
            precautions.extend(
                [
                    "Maintain hydration and avoid intense outdoor activity during peak heat.",
                    "Watch for heat exhaustion signs such as dizziness, confusion, heavy sweating, or fainting.",
                ]
            )
        if any(term in location_text for term in ["pollution", "aqi", "smog"]):
            precautions.append("Avoid outdoor exercise during poor air-quality periods and seek care if breathing worsens.")
        if any(term in location_text for term in ["rain", "monsoon", "mosquito"]):
            precautions.append("Use mosquito protection and remove standing water during rainy seasons.")
        return precautions
