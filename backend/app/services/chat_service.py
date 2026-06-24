from backend.app.core.config import get_settings
from backend.app.schemas.health import ChatRequest, ChatResponse
from backend.app.services.knowledge_service import KnowledgeService
from backend.app.services.llm_service import LLMService
from backend.app.services.safety_service import SafetyService
from backend.app.services.triage_service import TriageService


class ChatService:
    def __init__(self) -> None:
        self.knowledge = KnowledgeService()
        self.llm = LLMService()
        self.safety = SafetyService()
        self.triage = TriageService()

    def answer(self, request: ChatRequest) -> ChatResponse:
        triage = self.triage.analyze([], request.question)
        sources = self.knowledge.retrieve(request.question)
        question_lower = request.question.lower()

        if any(term in question_lower for term in ["which antibiotic", "what antibiotic", "medicine should i take", "tablet should i take"]):
            answer = self.safety.medication_awareness_answer()
            doctor_required = True
        elif triage.emergency_warning:
            answer = get_settings().emergency_message
            doctor_required = True
        elif len(request.question.split()) <= 4:
            answer = (
                "I need a little more information to give safe educational guidance. "
                "Please share duration, severity, associated symptoms, existing conditions, and current medications."
            )
            doctor_required = False
        else:
            answer = (
                "Based on the information provided, this should be treated as health-risk awareness rather than a diagnosis. "
                "Monitor symptoms, use sensible self-care such as rest and hydration when appropriate, and consult a qualified "
                "healthcare professional if symptoms persist, worsen, or concern you."
            )
            doctor_required = True

        try:
            llm_result = self.llm.answer_chat(request, answer, sources)
        except RuntimeError:
            llm_result = {"answer": answer, "generation_engine": "rules"}
        validation = self.safety.validate_text(llm_result["answer"])
        return ChatResponse(
            answer=validation.sanitized_text,
            red_flags=triage.red_flags,
            doctor_consultation_required=doctor_required or bool(triage.red_flags),
            sources=sources,
            disclaimer=get_settings().safety_disclaimer,
        )
