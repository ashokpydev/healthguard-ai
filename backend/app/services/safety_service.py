import re

from backend.app.schemas.health import SafetyValidationResult


UNSAFE_PATTERNS = {
    r"\byou have\b": "diagnosis certainty",
    r"\byou will definitely\b": "certainty claim",
    r"\btake\s+\w+": "possible medication instruction",
    r"\bstop\s+(your\s+)?medication\b": "medication change instruction",
    r"\bignore\s+(your\s+)?doctor\b": "contradicts doctor advice",
    r"\bantibiotic should i take\b": "medication request",
}


class SafetyService:
    def validate_text(self, text: str) -> SafetyValidationResult:
        reasons = [label for pattern, label in UNSAFE_PATTERNS.items() if re.search(pattern, text, re.IGNORECASE)]
        sanitized = text
        if reasons:
            sanitized = (
                "I cannot provide a diagnosis or prescribe medication. "
                "Based on the information shared, please discuss symptoms and treatment options with a qualified healthcare professional."
            )
        return SafetyValidationResult(safe=not reasons, blocked_reasons=reasons, sanitized_text=sanitized)

    def medication_awareness_answer(self) -> str:
        return (
            "I cannot recommend an antibiotic or any new medicine. Antibiotics are only appropriate for specific infections "
            "and should be chosen by a qualified clinician. Please consult a doctor, and seek urgent care if symptoms are severe "
            "or include breathing difficulty, chest pain, confusion, dehydration, or very high fever."
        )
