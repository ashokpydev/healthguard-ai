from __future__ import annotations

import re
import zipfile
from html import unescape
from io import BytesIO

from pydantic import BaseModel, Field


class DocumentExplanation(BaseModel):
    filename: str
    status: str
    message: str
    extracted_text: str = ""
    tuned_context: str = ""
    rag_summary: str = ""
    detected_topics: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    doctor_questions: list[str] = Field(default_factory=list)
    safety_alerts: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    disclaimer: str


class DocumentService:
    max_bytes = 4 * 1024 * 1024
    max_context_chars = 2800

    def process_upload(self, filename: str, content_type: str | None, payload: bytes) -> DocumentExplanation:
        if not payload:
            raise ValueError("The uploaded document is empty.")
        if len(payload) > self.max_bytes:
            raise ValueError("Upload limit is 4 MB for demo document processing.")

        extracted = self._extract_text(filename, content_type, payload)
        insights = self._analyze_health_context(extracted)
        tuned = self._tune_for_rag(extracted, insights)
        summary = self._summarize(tuned)
        status = "processed_for_rag" if tuned else "received_needs_review"
        return DocumentExplanation(
            filename=filename,
            status=status,
            message=f"{filename} was processed and can be used as optional supporting context for the next report.",
            extracted_text=extracted[: self.max_context_chars],
            tuned_context=tuned,
            rag_summary=summary,
            detected_topics=insights["detected_topics"],
            suggested_actions=insights["suggested_actions"],
            doctor_questions=insights["doctor_questions"],
            safety_alerts=insights["safety_alerts"],
            sources=[filename] if tuned else [],
            disclaimer="Reference ranges may vary by lab. Please consult your doctor for interpretation.",
        )

    def _extract_text(self, filename: str, content_type: str | None, payload: bytes) -> str:
        name = filename.lower()
        if name.endswith(".docx"):
            return self._extract_docx(payload)
        if name.endswith(".pdf") or content_type == "application/pdf":
            return self._extract_pdf_text(payload)
        return self._decode_text(payload)

    def _decode_text(self, payload: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="ignore")

    def _extract_docx(self, payload: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(payload)) as docx:
                xml = docx.read("word/document.xml").decode("utf-8", errors="ignore")
        except (KeyError, zipfile.BadZipFile):
            return self._decode_text(payload)
        text = re.sub(r"<[^>]+>", " ", xml)
        return unescape(text)

    def _extract_pdf_text(self, payload: bytes) -> str:
        decoded = payload.decode("latin-1", errors="ignore")
        chunks = re.findall(r"\(([^()]{2,})\)\s*Tj", decoded)
        if not chunks:
            chunks = re.findall(r"\(([^()]{2,})\)", decoded)
        return " ".join(unescape(chunk.replace("\\)", ")").replace("\\(", "(")) for chunk in chunks)

    def _tune_for_rag(self, text: str, insights: dict | None = None) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = re.sub(r"(?i)(password|secret|token)\s*[:=]\s*\S+", r"\1: [redacted]", cleaned)
        if not cleaned:
            return ""
        insight_text = ""
        if insights:
            parts = []
            if insights.get("detected_topics"):
                parts.append("Detected health topics: " + "; ".join(insights["detected_topics"]))
            if insights.get("suggested_actions"):
                parts.append("Safe suggested actions: " + "; ".join(insights["suggested_actions"]))
            if insights.get("doctor_questions"):
                parts.append("Questions for doctor: " + "; ".join(insights["doctor_questions"]))
            if insights.get("safety_alerts"):
                parts.append("Safety alerts: " + "; ".join(insights["safety_alerts"]))
            if parts:
                insight_text = " ".join(parts) + " "
        return (insight_text + cleaned)[: self.max_context_chars]

    def _summarize(self, text: str) -> str:
        if not text:
            return "No readable text was extracted. The file was received for manual review."
        sentences = re.split(r"(?<=[.!?])\s+", text)
        summary = " ".join(sentence for sentence in sentences[:3] if sentence)
        return summary[:700] or text[:700]

    def _analyze_health_context(self, text: str) -> dict[str, list[str]]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        lower = normalized.lower()
        detected: list[str] = []
        suggestions: list[str] = []
        questions: list[str] = []
        alerts: list[str] = []

        emergency_terms = {
            "chest pain": "Chest pain mentioned in the uploaded file.",
            "shortness of breath": "Breathing difficulty mentioned in the uploaded file.",
            "stroke": "Stroke-related term mentioned in the uploaded file.",
            "unconscious": "Unconsciousness mentioned in the uploaded file.",
            "severe bleeding": "Severe bleeding mentioned in the uploaded file.",
        }
        for term, alert in emergency_terms.items():
            if term in lower:
                alerts.append(alert)
        if alerts:
            suggestions.append("Seek urgent medical care immediately if any emergency symptom is current, severe, or worsening.")

        lab_patterns = [
            ("HbA1c", r"(?i)\b(?:hba1c|a1c)\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 5.7, "high", "Discuss diabetes or prediabetes screening and glucose management with a clinician."),
            ("Glucose", r"(?i)\bglucose\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 140, "high", "Ask whether the glucose value was fasting/random and whether repeat testing is needed."),
            ("LDL cholesterol", r"(?i)\bldl\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 130, "high", "Review cardiovascular risk, diet, activity, and lipid follow-up with a clinician."),
            ("Triglycerides", r"(?i)\btriglycerides?\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 150, "high", "Discuss metabolic risk, diet pattern, alcohol intake, and lipid follow-up."),
            ("TSH", r"(?i)\btsh\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 4.5, "high", "Discuss thyroid follow-up and whether free T4 or repeat testing is needed."),
            ("Creatinine", r"(?i)\bcreatinine\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 1.3, "high", "Ask whether kidney function needs repeat testing or medication review."),
            ("Hemoglobin", r"(?i)\b(?:hemoglobin|hb)\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 12.0, "low", "Discuss anemia evaluation, nutrition, bleeding history, and follow-up testing."),
            ("Vitamin D", r"(?i)\bvitamin d\b[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", 20.0, "low", "Discuss vitamin D status, sunlight exposure, diet, and clinician-directed supplementation if appropriate."),
        ]
        for label, pattern, threshold, direction, suggestion in lab_patterns:
            for match in re.finditer(pattern, normalized):
                try:
                    value = float(match.group(1))
                except ValueError:
                    continue
                abnormal = value >= threshold if direction == "high" else value < threshold
                detected.append(f"{label}: {value:g}" + (" flagged for review" if abnormal else " mentioned"))
                if abnormal:
                    suggestions.append(suggestion)
                    questions.append(f"What does my {label} value of {value:g} mean with my age, symptoms, and medical history?")
                break

        condition_terms = {
            "diabetes": "Diabetes or blood-sugar history mentioned.",
            "hypertension": "High blood pressure history mentioned.",
            "blood pressure": "Blood pressure concern mentioned.",
            "thyroid": "Thyroid concern mentioned.",
            "asthma": "Asthma or breathing condition mentioned.",
            "kidney": "Kidney-related concern mentioned.",
            "cholesterol": "Cholesterol or lipid concern mentioned.",
            "anemia": "Anemia or low hemoglobin concern mentioned.",
        }
        for term, topic in condition_terms.items():
            if term in lower:
                detected.append(topic)

        medication_matches = sorted(set(re.findall(r"(?i)\b(?:tablet|tab|capsule|cap|inj|injection|medicine|medication|metformin|insulin|amlodipine|atorvastatin|thyroxine|antibiotic)\b[^.,;\n]{0,45}", normalized)))
        if medication_matches:
            detected.append("Medication names or medication instructions were mentioned in the uploaded file.")
            suggestions.append("Do not start, stop, or change any medicine from this app; review medication details with a qualified clinician.")
            questions.append("Are any current medicines, doses, or interactions relevant to these uploaded findings?")

        if detected and not suggestions:
            suggestions.append("Use the uploaded findings as discussion points with a qualified clinician; do not treat this as a diagnosis.")
        if detected and not questions:
            questions.append("Which uploaded findings need follow-up, repeat testing, or clinical examination?")
        if not detected and normalized:
            suggestions.append("The file was readable, but no common lab, condition, emergency, or medication signals were confidently detected.")
            questions.append("Can my clinician explain which parts of this uploaded document are clinically important?")

        suggestions.append("Continue routine self-care basics: hydration, sleep, balanced food, physical activity as tolerated, and timely clinical follow-up.")
        suggestions = self._unique(suggestions)[:8]
        questions = self._unique(questions)[:8]
        detected = self._unique(detected)[:12]
        alerts = self._unique(alerts)[:6]
        return {
            "detected_topics": detected,
            "suggested_actions": suggestions,
            "doctor_questions": questions,
            "safety_alerts": alerts,
        }

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))
