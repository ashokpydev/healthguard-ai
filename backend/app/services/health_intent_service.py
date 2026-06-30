from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.app.schemas.health import HealthProfile


@dataclass
class HealthNLPAnalysis:
    intent: str
    symptoms: list[str] = field(default_factory=list)
    current_symptoms: list[str] = field(default_factory=list)
    duration: str | None = None
    current_duration: str | None = None
    severity: str | None = None
    age: int | None = None
    location: str | None = None
    conditions: list[str] = field(default_factory=list)
    medicines: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    enough_information: bool = False
    next_action: str = "answer"
    has_document_context: bool = False
    requested_diet_guidance: bool = False
    asks_reason: bool = False


class HealthIntentService:
    symptoms = [
        "fever",
        "rash",
        "rashes",
        "cough",
        "cold",
        "headache",
        "stomach pain",
        "abdominal pain",
        "vomiting",
        "loose motion",
        "diarrhea",
        "chest pain",
        "dizziness",
        "weak",
        "weakness",
        "fatigue",
        "back pain",
        "sore throat",
    ]
    condition_terms = ["diabetes", "bp", "hypertension", "asthma", "thyroid", "cholesterol", "kidney", "heart"]
    medicine_terms = ["metformin", "insulin", "tablet", "medicine", "medication", "antibiotic", "paracetamol"]
    red_flag_terms = [
        ("breathing trouble", "breathing trouble"),
        ("shortness of breath", "breathing trouble"),
        ("chest pain", "chest pain"),
        ("bleeding", "bleeding"),
        ("confusion", "confusion"),
        ("fainting", "fainting"),
        ("severe weakness", "severe weakness"),
        ("swelling", "swelling"),
    ]

    def analyze(
        self,
        question: str,
        chat_memory: list[dict] | None = None,
        profile: HealthProfile | None = None,
        has_document_context: bool = False,
    ) -> HealthNLPAnalysis:
        current = self._normalize(question)
        memory_text = " ".join(
            message.get("content", "")
            for message in (chat_memory or [])
            if message.get("role") == "user" and message.get("content")
        )
        last_assistant_prompt = next(
            (
                message.get("content", "")
                for message in reversed(chat_memory or [])
                if message.get("role") == "assistant" and message.get("content")
            ),
            "",
        )
        combined = self._normalize(f"{memory_text} {question}")
        intent = self._intent(current, combined, has_document_context)
        current_symptoms = self._extract_symptoms(current)
        current_duration = self._extract_duration(current)
        current_bare_number = bool(re.fullmatch(r"\s*(?:[1-9]|10)\s*", current or ""))
        current_requests_diet = self._requested_diet_guidance(current)
        followup_continues_prior_diet = (
            not current_symptoms
            and (bool(current_duration) or current_bare_number)
            and self._requested_diet_guidance(memory_text)
        )
        symptoms = self._extract_symptoms(combined)
        analysis = HealthNLPAnalysis(
            intent=intent,
            symptoms=symptoms,
            current_symptoms=current_symptoms,
            duration=self._extract_duration(combined),
            current_duration=current_duration,
            severity=self._extract_severity(combined) or self._extract_contextual_severity(current, last_assistant_prompt),
            age=(self._extract_age(combined) or self._extract_contextual_age(current, last_assistant_prompt) or profile.age) if profile else (self._extract_age(combined) or self._extract_contextual_age(current, last_assistant_prompt)),
            location=profile.location if profile else self._extract_location(combined),
            conditions=self._extract_terms(combined, self.condition_terms),
            medicines=self._extract_terms(combined, self.medicine_terms),
            allergies=self._extract_allergies(combined),
            red_flags=self._extract_red_flags(combined),
            has_document_context=has_document_context,
            requested_diet_guidance=current_requests_diet or followup_continues_prior_diet,
            asks_reason=any(term in current for term in ["reason", "why", "cause", "causes"]),
        )
        analysis.missing_fields = self._missing_fields(analysis)
        analysis.enough_information = not analysis.missing_fields
        analysis.next_action = self._next_action(analysis)
        return analysis

    def _normalize(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
        typo_map = {
            "caugh": "cough",
            "cuf": "cough",
            "coff": "cough",
            "dite": "diet",
            "wamitings": "vomiting",
            "wamiting": "vomiting",
            "vomitings": "vomiting",
            "motions": "loose motion",
            "motion": "loose motion",
        }
        for typo, replacement in typo_map.items():
            normalized = re.sub(rf"\b{typo}\b", replacement, normalized)
        return normalized

    def _intent(self, current: str, combined: str, has_document_context: bool) -> str:
        if any(term in current for term in ["what details", "what information", "what kind of information", "better suggestion", "better suggestions", "details do you need"]):
            return "better_suggestion_info_request"
        if self._extract_red_flags(current):
            return "emergency_symptom"
        if any(term in current for term in ["can i take", "medicine", "medication", "tablet", "antibiotic"]):
            return "medicine_question"
        if has_document_context or any(term in current for term in ["lab report", "blood report", "uploaded", "document", "scan report"]):
            return "lab_report_question"
        diet_requested = self._requested_diet_guidance(current)
        if diet_requested and self._extract_symptoms(combined):
            return "symptom_guidance"
        if diet_requested:
            return "diet_question"
        if self._extract_symptoms(combined):
            return "symptom_guidance"
        return "general_health_question"

    def _extract_symptoms(self, text: str) -> list[str]:
        found: list[str] = []
        for symptom in self.symptoms:
            if re.search(rf"\b{re.escape(symptom)}\b", text):
                canonical = "rash" if symptom == "rashes" else "weakness" if symptom == "weak" else symptom
                if canonical not in found:
                    found.append(canonical)
        return found

    def _extract_duration(self, text: str) -> str | None:
        match = re.search(r"\b(?:for|since)?\s*(\d+\s*(?:day|days|week|weeks|hour|hours))\b", text)
        if match:
            return match.group(1)
        if "today" in text:
            return "today"
        if "yesterday" in text:
            return "yesterday"
        return None

    def _extract_severity(self, text: str) -> str | None:
        match = re.search(r"\b([1-9]|10)\s*/\s*10\b", text)
        if match:
            return f"{match.group(1)}/10"
        for word in ["mild", "moderate", "severe", "high"]:
            if re.search(rf"\b{word}\b", text):
                return word
        temp = re.search(r"\b10[0-6](?:\.\d+)?\b", text)
        return temp.group(0) if temp else None

    def _extract_contextual_severity(self, current: str, last_assistant_prompt: str) -> str | None:
        if not re.search(r"\b(?:severity|severe|1-10|1 to 10)\b", self._normalize(last_assistant_prompt)):
            return None
        match = re.fullmatch(r"\s*([1-9]|10)\s*", current or "")
        return f"{match.group(1)}/10" if match else None

    def _extract_contextual_age(self, current: str, last_assistant_prompt: str) -> int | None:
        if not re.search(r"\bage\b", self._normalize(last_assistant_prompt)):
            return None
        match = re.fullmatch(r"\s*(\d{1,3})\s*", current or "")
        if not match:
            return None
        age = int(match.group(1))
        return age if 0 <= age <= 125 else None

    def _requested_diet_guidance(self, text: str) -> bool:
        return any(term in text for term in ["diet", "dite", "food", "eat", "meal"])

    def _extract_age(self, text: str) -> int | None:
        match = re.search(r"\b(?:age is|age|i am|i'm)\s*(\d{1,3})\b", text)
        return int(match.group(1)) if match else None

    def _extract_location(self, text: str) -> str | None:
        match = re.search(r"\b(?:in|from|at)\s+([a-z ]{3,30})(?:$|[,.])", text)
        return match.group(1).strip() if match else None

    def _extract_terms(self, text: str, terms: list[str]) -> list[str]:
        return [term for term in terms if re.search(rf"\b{re.escape(term)}\b", text)]

    def _extract_allergies(self, text: str) -> list[str]:
        if not any(term in text for term in ["allergy", "allergic"]):
            return []
        match = re.search(r"\ballerg(?:y|ic)(?: to)?\s+([a-z, ]{3,60})", text)
        return [match.group(1).strip(" .,")] if match else ["allergy mentioned"]

    def _extract_red_flags(self, text: str) -> list[str]:
        normalized = text
        for phrase in ["no breathing trouble", "no shortness of breath", "no chest pain", "no bleeding", "no confusion", "no severe weakness"]:
            normalized = normalized.replace(phrase, "")
        found = []
        for phrase, label in self.red_flag_terms:
            if phrase in normalized and label not in found:
                found.append(label)
        return found

    def _missing_fields(self, analysis: HealthNLPAnalysis) -> list[str]:
        if analysis.intent == "better_suggestion_info_request":
            return []
        if analysis.intent == "medicine_question":
            required = ["symptom", "duration", "age", "conditions", "allergies"]
        elif analysis.intent == "symptom_guidance":
            required = ["duration"] if analysis.requested_diet_guidance else ["duration", "severity"]
            if not analysis.symptoms:
                required.insert(0, "symptom")
            if set(analysis.current_symptoms).intersection({"vomiting", "loose motion", "diarrhea"}) and not analysis.current_duration and not analysis.asks_reason:
                required = ["duration"]
            if set(analysis.current_symptoms).intersection({"vomiting", "loose motion", "diarrhea"}) and analysis.asks_reason:
                required = []
        elif analysis.intent == "lab_report_question":
            required = [] if analysis.has_document_context else ["uploaded_document"]
        elif analysis.intent == "diet_question":
            required = ["age", "conditions"]
        else:
            required = []
        values = {
            "symptom": analysis.symptoms,
            "duration": analysis.duration,
            "severity": analysis.severity,
            "age": analysis.age,
            "conditions": analysis.conditions,
            "medicines": analysis.medicines,
            "allergies": analysis.allergies,
            "uploaded_document": analysis.has_document_context,
        }
        return [field_name for field_name in required if not values.get(field_name)]

    def _next_action(self, analysis: HealthNLPAnalysis) -> str:
        if analysis.red_flags:
            return "urgent"
        if analysis.intent == "better_suggestion_info_request":
            return "answer"
        if analysis.missing_fields:
            return "ask_followup"
        return "answer"
