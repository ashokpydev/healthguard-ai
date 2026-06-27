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

    def diet_plan(self, request: AssessmentRequest) -> list[str]:
        profile = request.profile
        text = self._assessment_text(request)
        diet_text = " ".join([profile.diet_style or "", *profile.food_habits]).lower()
        plan = [
            "Daily plate method: fill half the plate with vegetables/salad, one quarter with protein, and one quarter with whole grains or millets if tolerated.",
            "Prefer regular meal timing: breakfast, lunch, evening snack if needed, and an early light dinner; avoid skipping meals followed by heavy late-night eating.",
            "Protein choices: dal, beans, curd, paneer/tofu, eggs, fish, or lean chicken based on preference, allergies, kidney advice, and cultural diet.",
            "Fiber choices: vegetables, leafy greens, whole fruit, pulses, oats, brown rice, chapati, millets, nuts, and seeds in sensible portions.",
            "Hydration: keep water available through the day; increase fluids in hot weather unless a clinician has restricted fluids.",
        ]
        if any(term in diet_text for term in ["sugar", "sweet", "processed", "late", "fried", "junk"]):
            plan.extend(
                [
                    "Limit sugary drinks, sweets, bakery foods, packaged snacks, deep-fried foods, and frequent fast food.",
                    "Replace late-night processed snacks with fruit, curd, nuts in small portions, sprouts, or a light home-cooked option.",
                ]
            )
        if any(term in text for term in ["diabetes", "sugar", "hba1c", "metabolic", "overweight", "obesity"]):
            plan.extend(
                [
                    "For sugar/metabolic risk: choose low-glycemic, high-fiber carbohydrates; pair carbs with protein and vegetables; avoid sweet beverages.",
                    "Keep carbohydrate portions consistent across meals and discuss glucose monitoring targets with a clinician or dietician.",
                ]
            )
        if any(term in text for term in ["bp", "blood pressure", "hypertension", "heart", "cholesterol"]):
            plan.extend(
                [
                    "For BP/heart/lipid risk: reduce high-salt packaged foods, pickles, chips, processed meats, and excess oil.",
                    "Prefer unsaturated fats in small amounts, nuts/seeds in moderation, and more vegetables, pulses, and whole grains.",
                ]
            )
        if any(term in text for term in ["kidney", "creatinine", "ckd"]):
            plan.append("For kidney concerns: do not start high-protein or mineral supplements without nephrology/dietician advice; potassium, salt, protein, and fluids may need personalization.")
        if any(term in text for term in ["acidity", "gastric", "reflux", "stomach"]):
            plan.append("For acidity/reflux: keep dinner light and early, reduce spicy/fried foods, caffeine, and lying down soon after meals.")
        if any(term in text for term in ["fever", "cold", "infection", "weakness"]):
            plan.append("During fever or acute weakness: use light, easy-to-digest meals, soups, fruits, oral fluids, and small frequent meals if appetite is low.")
        if any(term in text for term in ["low water", "hot", "heat", "hyderabad"]):
            plan.append("In hot weather: add hydration reminders and include water-rich foods such as cucumber, citrus fruits, curd/buttermilk if tolerated.")
        plan.append("For an exact calorie plan, disease-specific restrictions, pregnancy, kidney disease, diabetes medicines, or food allergies, consult a registered dietician or doctor.")
        return list(dict.fromkeys(plan))

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

    def wellness_recommendations(self, request: AssessmentRequest) -> list[str]:
        text = self._assessment_text(request)
        recommendations = [
            "Rest when symptoms are active, maintain hydration, and track temperature, pain, sleep, appetite, and symptom changes daily.",
            "Use slow breathing or 5-10 minutes of meditation to reduce stress response while waiting for clinical review.",
            "Avoid self-medication, antibiotics, or dose changes unless a qualified clinician has advised it.",
        ]
        if any(term in text for term in ["fever", "cold", "cough", "infection", "weakness", "headache"]):
            recommendations.extend(
                [
                    "Prioritize sleep, warm fluids if tolerated, light food, and avoid strenuous workouts until fever or weakness improves.",
                    "Seek medical care promptly if fever is high, persistent, associated with breathing difficulty, confusion, chest pain, severe headache, rash, dehydration, or worsening weakness.",
                ]
            )
        if any(term in text for term in ["stress", "anxiety", "tension", "poor sleep", "insomnia"]):
            recommendations.extend(
                [
                    "Practice a regular wind-down routine: reduce screens before sleep, keep a fixed sleep time, and try guided breathing or yoga nidra.",
                    "Discuss persistent anxiety, low mood, panic, or sleep disruption with a mental-health professional or physician.",
                ]
            )
        if any(term in text for term in ["sugar", "diabetes", "overweight", "cholesterol", "bp", "blood pressure"]):
            recommendations.append("Use regular meal timing, portion control, fiber-rich foods, and clinician-approved monitoring for sugar, BP, weight, or lipids.")
        return list(dict.fromkeys(recommendations))

    def physical_activity_plan(self, request: AssessmentRequest) -> list[str]:
        text = self._assessment_text(request)
        occupation = (request.profile.occupation or "").lower()
        plan: list[str] = []
        if any(term in text for term in ["chest pain", "severe breath", "faint", "stroke", "emergency"]):
            return [
                "Do not start exercise during red-flag symptoms such as chest pain, fainting, severe breathlessness, weakness on one side, or confusion; seek urgent medical care first."
            ]
        if any(term in occupation for term in ["software", "desk", "office"]) or any(term in text for term in ["back", "neck", "sedentary"]):
            plan.extend(
                [
                    "For desk-related back or neck strain: take 3-5 minute walking or mobility breaks every hour.",
                    "Try gentle neck range-of-motion, shoulder rolls, chest-opening stretches, and hip-flexor stretches; stop if pain, numbness, or dizziness increases.",
                    "Yoga options for stiffness: cat-cow, child's pose, gentle seated twist, and bridge pose if comfortable and pain-free.",
                ]
            )
        if any(term in text for term in ["overweight", "diabetes", "sugar", "cholesterol", "bp", "blood pressure", "metabolic"]):
            plan.extend(
                [
                    "For metabolic risk: aim for brisk walking or cycling most days, starting with 10-15 minutes and gradually moving toward 150 minutes per week if safe.",
                    "Add light strength training 2 days per week, such as sit-to-stand, wall push-ups, resistance bands, or supervised gym work.",
                ]
            )
        if any(term in text for term in ["stress", "anxiety", "poor sleep", "insomnia"]):
            plan.extend(
                [
                    "For stress or sleep issues: practice 10 minutes of meditation, diaphragmatic breathing, or alternate-nostril breathing daily.",
                    "Use gentle evening yoga such as legs-up-the-wall, supported forward fold, or yoga nidra instead of intense late-night exercise.",
                ]
            )
        if any(term in text for term in ["cough", "asthma", "breath", "wheezing", "pollution"]):
            plan.append("For breathing concerns: choose gentle indoor walking and breathing exercises only when comfortable; avoid outdoor activity in poor air quality and stop if breathlessness worsens.")
        if any(term in text for term in ["fever", "infection", "weakness"]):
            plan.append("For fever or acute illness: avoid strenuous exercise; use rest and short gentle walking only after fever and significant weakness improve.")
        if not plan:
            plan.extend(
                [
                    "Start with low-impact activity such as walking, cycling, swimming, or beginner yoga for 10-20 minutes most days if symptoms allow.",
                    "Warm up, hydrate, progress slowly, and stop activity if pain, dizziness, chest discomfort, or unusual breathlessness occurs.",
                ]
            )
        return list(dict.fromkeys(plan))

    def doctor_department_guidance(self, request: AssessmentRequest) -> list[str]:
        text = self._assessment_text(request)
        guidance: list[str] = []
        mappings = [
            (["chest pain", "heart", "palpitation", "high bp", "blood pressure"], "Heart/BP concern: consult Cardiology or Internal Medicine; go to emergency care for chest pain, fainting, severe breathlessness, or sweating with pain."),
            (["diabetes", "sugar", "hba1c", "thyroid", "obesity", "weight"], "Metabolic or hormone concern: consult Endocrinology or Internal Medicine."),
            (["cough", "asthma", "wheezing", "breath", "pollution"], "Breathing concern: consult Pulmonology or Internal Medicine; urgent care is needed for severe breathlessness or low oxygen symptoms."),
            (["software", "desk", "office", "back", "neck", "joint", "knee", "shoulder", "sprain"], "Desk-work, muscle, joint, back, or neck concern: consult Orthopedics, Physical Medicine/Rehabilitation, or a qualified Physiotherapist."),
            (["fever", "infection", "cold", "weakness", "headache"], "Fever/infection-type symptoms: consult a General Physician or Internal Medicine doctor first."),
            (["stomach", "acidity", "gastric", "vomit", "diarrhea", "liver"], "Digestive concern: consult Gastroenterology or a General Physician."),
            (["kidney", "urine", "creatinine", "uti"], "Kidney/urinary concern: consult Nephrology or Urology depending on the symptoms."),
            (["skin", "rash", "itching"], "Skin concern: consult Dermatology."),
            (["eye", "vision", "screen strain"], "Eye or vision concern: consult Ophthalmology; screen strain may also need ergonomics review."),
            (["stress", "anxiety", "depression", "sleep", "insomnia"], "Stress, anxiety, mood, or sleep concern: consult Psychiatry, Psychology/Counselling, or Sleep Medicine based on severity."),
            (["pregnancy", "period", "pcos", "gynec"], "Women's health concern: consult Gynecology."),
            (["tooth", "dental", "gum"], "Dental concern: consult Dentistry."),
        ]
        for terms, message in mappings:
            if any(term in text for term in terms):
                guidance.append(message)
        if not guidance:
            guidance.append("Start with a General Physician/Internal Medicine doctor, who can examine you and refer to a specialist if needed.")
        return list(dict.fromkeys(guidance))

    def _assessment_text(self, request: AssessmentRequest) -> str:
        profile = request.profile
        parts = [
            request.question or "",
            profile.occupation or "",
            profile.diet_style or "",
            profile.exercise_frequency or "",
            profile.smoking_status or "",
            profile.alcohol_status or "",
            " ".join(profile.food_habits),
            " ".join(profile.existing_conditions),
            " ".join(profile.family_history),
            " ".join(symptom.name for symptom in request.symptoms),
            " ".join(symptom.notes or "" for symptom in request.symptoms),
            request.document_context or "",
        ]
        return " ".join(parts).lower()
