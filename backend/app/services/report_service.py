from backend.app.core.config import get_settings
from backend.app.schemas.health import AssessmentRequest, HealthReport, KnowledgeSource
from backend.app.services.guidance_service import GuidanceService
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.llm_service import LLMService
from backend.app.services.risk_service import RiskService
from backend.app.services.triage_service import TriageService


class ReportLLMError(RuntimeError):
    def __init__(self, message: str, provider: str, model: str, original_error: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error

    def as_detail(self) -> dict:
        detail = {
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
        }
        if self.original_error:
            detail["error"] = self.original_error
        return detail


class ReportService:
    def __init__(self) -> None:
        self.triage = TriageService()
        self.risk = RiskService()
        self.guidance = GuidanceService()
        self.knowledge = KnowledgeService()
        self.llm = LLMService()

    def generate(self, request: AssessmentRequest) -> HealthReport:
        triage = self.triage.analyze(request.symptoms, request.question)
        risk = self.risk.score(request, len(triage.red_flags))
        precautions = [
            *self.guidance.lifestyle_precautions(request),
            *self.guidance.diet_precautions(request),
            *self.guidance.climate_precautions(request),
        ]
        if triage.emergency_warning and triage.message:
            precautions.insert(0, triage.message)

        concerns = self._concerns(request, risk.key_risk_factors)
        sources = self.knowledge.retrieve(request.question)
        if request.document_context:
            sources.insert(
                0,
                KnowledgeSource(
                    title="Uploaded document context",
                    source_type="user_upload_rag_context",
                    excerpt=request.document_context[:500],
                ),
            )
            concerns.append("Uploaded document findings that may need clinician interpretation")
        report_payload = {
            "patient_summary": {
                "age": request.profile.age,
                "gender": request.profile.gender,
                "occupation": request.profile.occupation,
                "location": request.profile.location,
                "bmi": request.profile.bmi,
            },
            "risk_summary": risk,
            "possible_health_concerns_to_discuss_with_doctor": concerns,
            "precautions": list(dict.fromkeys(precautions)),
            "doctor_consultation_required": risk.overall_risk_level in {"Moderate", "High", "Urgent"} or bool(request.symptoms),
            "emergency_warning": triage.emergency_warning,
            "red_flags": triage.red_flags,
            "suggested_questions_to_ask_doctor": [
                "Which symptoms or risk factors need medical evaluation first?",
                "Do I need any screening tests based on my age, family history, or symptoms?",
                "What lifestyle changes are safest for my current health conditions?",
            ],
            "follow_up_reminders": triage.follow_up_questions or ["Track symptoms and seek medical advice if they worsen or persist."],
            "sources": sources,
            "disclaimer": get_settings().safety_disclaimer,
        }
        if not self.llm.configured():
            status = self.llm.status()
            missing = ", ".join(status.get("missing", [])) or "LLM API key"
            raise ReportLLMError(
                f"LLM is not configured. Missing required setting: {missing}. Report generation was stopped.",
                status.get("provider", "unknown"),
                status.get("model", "unknown"),
            )
        try:
            llm_result = self.llm.enhance_report(request, report_payload, sources)
        except RuntimeError as exc:
            status = self.llm.status()
            raise ReportLLMError(
                "LLM report generation failed. No report was created or saved.",
                status.get("provider", "unknown"),
                status.get("model", "unknown"),
                str(exc).splitlines()[0],
            ) from exc
        if llm_result.get("additional_precautions"):
            report_payload["precautions"] = list(dict.fromkeys([*report_payload["precautions"], *llm_result["additional_precautions"]]))
        if llm_result.get("doctor_questions"):
            report_payload["suggested_questions_to_ask_doctor"] = list(
                dict.fromkeys([*report_payload["suggested_questions_to_ask_doctor"], *llm_result["doctor_questions"]])
            )
        if llm_result.get("follow_up_reminders"):
            report_payload["follow_up_reminders"] = list(dict.fromkeys([*report_payload["follow_up_reminders"], *llm_result["follow_up_reminders"]]))
        if llm_result.get("concerns_to_discuss"):
            report_payload["possible_health_concerns_to_discuss_with_doctor"] = list(
                dict.fromkeys([*report_payload["possible_health_concerns_to_discuss_with_doctor"], *llm_result["concerns_to_discuss"]])
            )
        report_payload["llm_summary"] = llm_result.get("llm_summary")
        report_payload["generation_engine"] = llm_result.get("generation_engine", "rules")
        report_payload["llm_error"] = None
        return HealthReport(**report_payload)

    def _concerns(self, request: AssessmentRequest, factors: list[str]) -> list[str]:
        concerns: list[str] = []
        occupation = (request.profile.occupation or "").lower()
        if "software" in occupation or "desk" in occupation:
            concerns.extend(["Back/neck strain risk", "Eye strain risk", "Metabolic health risk from sedentary work"])
        if request.profile.bmi and request.profile.bmi >= 25:
            concerns.append("Metabolic health risk")
        if request.profile.sleep_hours is not None and request.profile.sleep_hours < 6:
            concerns.append("Sleep-related health risk")
        if request.profile.family_history:
            concerns.append("Family-history-related preventive screening needs")
        if any("Emergency" in factor for factor in factors):
            concerns.insert(0, "Emergency symptoms requiring immediate medical care")
        if not concerns:
            concerns.append("General preventive health risks to review during routine checkup")
        return list(dict.fromkeys(concerns))
