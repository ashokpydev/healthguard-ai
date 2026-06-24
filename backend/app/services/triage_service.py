from backend.app.core.config import get_settings
from backend.app.schemas.health import SymptomInput, TriageResult


RED_FLAG_TERMS = {
    "chest pain": "Chest pain",
    "shortness of breath": "Severe breathing difficulty",
    "breathing difficulty": "Severe breathing difficulty",
    "stroke": "Stroke-like symptoms",
    "face drooping": "Stroke-like symptoms",
    "unconscious": "Unconsciousness",
    "severe bleeding": "Severe bleeding",
    "suicidal": "Suicidal thoughts",
    "severe dehydration": "Severe dehydration",
    "anaphylaxis": "Severe allergic reaction",
    "severe allergic": "Severe allergic reaction",
    "pregnancy bleeding": "Pregnancy complications",
}


class TriageService:
    def analyze(self, symptoms: list[SymptomInput], free_text: str | None = None) -> TriageResult:
        combined_parts = [free_text or ""]
        combined_parts.extend(f"{item.name} {item.notes or ''}" for item in symptoms)
        combined = " ".join(combined_parts).lower()

        red_flags = sorted({label for term, label in RED_FLAG_TERMS.items() if term in combined})
        follow_ups: list[str] = []
        if not symptoms and not free_text:
            follow_ups.append("What symptom or concern would you like to discuss?")
        if combined and not red_flags:
            if "fever" in combined:
                follow_ups.extend(
                    [
                        "How many days have you had fever?",
                        "Do you have breathing difficulty, chest pain, confusion, or dehydration?",
                    ]
                )
            if any(word in combined for word in ["weak", "weakness", "tired"]):
                follow_ups.extend(
                    [
                        "How long have you felt weak?",
                        "Do you have fever, weight loss, dizziness, or reduced food intake?",
                    ]
                )

        message = get_settings().emergency_message if red_flags else None
        return TriageResult(
            emergency_warning=bool(red_flags),
            red_flags=red_flags,
            message=message,
            follow_up_questions=list(dict.fromkeys(follow_ups)),
        )
