import os
import re

from backend.app.core.config import get_settings
from backend.app.schemas.health import ChatRequest, ChatResponse
from backend.app.services.chat_support_data import CHATBOT_PROMPT_VERSION, FAQ_KNOWLEDGE_BASE, SIMPLE_CHAT_ANSWERS, VOICE_INTENT_TRAINING_DATA
from backend.app.services.health_intent_service import HealthIntentService, HealthNLPAnalysis
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
        self.nlp = HealthIntentService()

    def answer(self, request: ChatRequest, user_id: int | None = None, chat_memory: list[dict] | None = None) -> ChatResponse:
        question = self._clean_question(request.question)
        triage = self.triage.analyze([], question)
        if request.voice_mode or request.source == "voice":
            return self._answer_voice_mode(request, question, triage, user_id, chat_memory or [])
        question_lower = question.lower()
        has_document_context = bool(re.search(r"\n\s*Uploaded document context:", request.question or "", flags=re.IGNORECASE))
        nlp = self.nlp.analyze(question, chat_memory or [], request.profile, has_document_context)
        product_answer = self._product_help_answer(question_lower)
        simple_answer = self._simple_answer(question_lower)
        memory_answer = self._memory_answer(question_lower, chat_memory or [])
        nlp_answer = self._nlp_answer(nlp)
        sources = [] if len(question.split()) <= 10 or product_answer or nlp_answer or simple_answer else self.knowledge.retrieve(question, user_id=user_id)
        trusted_context_answer = self._trusted_context_answer(sources)
        answer_source = "rules"
        unresolved = False

        if product_answer:
            answer = product_answer
            doctor_required = False
            answer_source = "faq"
        elif memory_answer:
            answer = memory_answer
            doctor_required = False
            answer_source = "memory"
        elif nlp.next_action == "urgent":
            answer = "Emergency medical care now for breathing trouble, chest pain, bleeding, confusion, or severe weakness."
            doctor_required = True
            answer_source = "urgent"
        elif nlp_answer:
            answer = nlp_answer
            doctor_required = nlp.intent in {"medicine_question", "symptom_guidance", "emergency_symptom"}
            answer_source = "nlp"
        elif self._is_medication_request(question_lower):
            answer = "I cannot recommend medication. Consult a clinician, especially with high fever."
            doctor_required = True
            answer_source = "nlp"
        elif self._has_fever_with_rash(question_lower):
            answer = "Fever with rash needs doctor review.\nUrgent care for breathing trouble, swelling, bleeding, severe weakness."
            doctor_required = True
            answer_source = "nlp"
        elif self._has_high_fever(question_lower):
            answer = "Fever 103 F is high. Consult a doctor soon.\nUrgent care if confusion, breathing trouble, severe weakness."
            doctor_required = True
            answer_source = "nlp"
        elif triage.emergency_warning:
            answer = "Emergency medical care now. Call local emergency services or go to ER."
            doctor_required = True
            answer_source = "urgent"
        elif simple_answer:
            answer = simple_answer
            doctor_required = False
            answer_source = "faq"
        elif len(question.split()) <= 4:
            answer = "Need more information: symptom, duration, severity, conditions, medicines?"
            doctor_required = False
            unresolved = True
            answer_source = "fallback"
        elif trusted_context_answer:
            answer = trusted_context_answer
            doctor_required = False
            answer_source = "rag"
        else:
            answer = self._contextual_short_answer(question_lower)
            doctor_required = True
            unresolved = answer.startswith("Need more information")
            answer_source = "fallback" if unresolved else "rules"

        if os.getenv("CHAT_LLM_ENABLED", "").lower() not in {"1", "true", "yes"}:
            llm_result = {"answer": answer, "generation_engine": "rules"}
        else:
            try:
                llm_result = self.llm.answer_chat(request, answer, sources)
                answer_source = "llm"
            except RuntimeError:
                llm_result = {"answer": answer, "generation_engine": "rules"}
        validation = self.safety.validate_text(llm_result["answer"])
        return ChatResponse(
            answer=self._trim_to_human_length(validation.sanitized_text),
            red_flags=triage.red_flags,
            doctor_consultation_required=doctor_required or bool(triage.red_flags),
            sources=sources,
            disclaimer=get_settings().safety_disclaimer,
            conversation_stage="asking_followup" if nlp.next_action == "ask_followup" and nlp_answer else "urgent" if nlp.next_action == "urgent" else "answered",
            answer_source=answer_source,
            prompt_version=CHATBOT_PROMPT_VERSION,
            generation_engine=llm_result.get("generation_engine", "rules"),
            rag_used=bool(sources),
            unresolved=unresolved,
        )

    def _answer_voice_mode(self, request: ChatRequest, question: str, triage, user_id: int | None, chat_memory: list[dict]) -> ChatResponse:
        question_lower = question.lower()
        red_flags = triage.red_flags
        nlp = self.nlp.analyze(question, chat_memory, request.profile, False)
        if triage.emergency_warning or self._has_voice_red_flags(question_lower):
            return ChatResponse(
                answer="Please seek urgent care now, especially for breathing trouble, confusion, bleeding, or severe weakness.",
                red_flags=red_flags or ["Possible urgent symptom mentioned"],
                doctor_consultation_required=True,
                sources=[],
                disclaimer=get_settings().safety_disclaimer,
                conversation_stage="urgent",
                answer_source="urgent",
                prompt_version=CHATBOT_PROMPT_VERSION,
                generation_engine="rules",
                rag_used=False,
            )
        nlp_answer = self._nlp_answer(nlp)
        if nlp.intent in {"better_suggestion_info_request", "medicine_question"} and nlp_answer:
            return ChatResponse(
                answer=self._trim_to_human_length(nlp_answer),
                red_flags=red_flags,
                doctor_consultation_required=nlp.intent == "medicine_question",
                sources=[],
                disclaimer=get_settings().safety_disclaimer,
                conversation_stage="asking_followup" if nlp.next_action == "ask_followup" else "answered",
                answer_source="nlp",
                prompt_version=CHATBOT_PROMPT_VERSION,
                generation_engine="rules",
                rag_used=False,
            )

        user_messages = [
            message.get("content", "").strip()
            for message in chat_memory
            if message.get("role") == "user" and message.get("content", "").strip()
        ]
        conversation_text = " ".join([*user_messages, question]).lower()
        intent = self._voice_intent(conversation_text)
        followup_count = self._voice_followup_count(chat_memory)
        next_question = self._next_voice_followup(intent, conversation_text, followup_count, question_lower)
        sources = [] if len(question.split()) <= 10 else self.knowledge.retrieve(question, user_id=user_id)

        if next_question and followup_count < 4:
            intro = "I cannot recommend medication directly. " if self._is_medication_request(question_lower) else "I'll help you understand what to do next. "
            answer = f"{intro}{next_question}"
            return ChatResponse(
                answer=self._trim_to_human_length(answer),
                red_flags=red_flags,
                doctor_consultation_required=False,
                sources=[],
                disclaimer=get_settings().safety_disclaimer,
                conversation_stage="asking_followup",
                answer_source="nlp",
                prompt_version=CHATBOT_PROMPT_VERSION,
                generation_engine="rules",
                rag_used=False,
            )

        answer = self._voice_summary_answer(intent, conversation_text)
        validation = self.safety.validate_text(answer)
        return ChatResponse(
            answer=validation.sanitized_text,
            red_flags=red_flags,
            doctor_consultation_required=True,
            sources=sources[:2],
            disclaimer=get_settings().safety_disclaimer,
            conversation_stage="summary_ready",
            answer_source="nlp" if not sources else "rag",
            prompt_version=CHATBOT_PROMPT_VERSION,
            generation_engine="rules",
            rag_used=bool(sources),
        )

    def _clean_question(self, question: str) -> str:
        return re.split(r"\n\s*Uploaded document context:", question or "", maxsplit=1, flags=re.IGNORECASE)[0].strip()

    def _simple_answer(self, question_lower: str) -> str | None:
        for keywords, answer in SIMPLE_CHAT_ANSWERS:
            if any(self._keyword_matches(question_lower, keyword) for keyword in keywords):
                return answer
        return None

    def _keyword_matches(self, question_lower: str, keyword: str) -> bool:
        return bool(re.search(rf"\b{re.escape(keyword)}\b", question_lower))

    def _product_help_answer(self, question_lower: str) -> str | None:
        matched = [
            item
            for item in FAQ_KNOWLEDGE_BASE
            if any(pattern in question_lower for pattern in item["patterns"])
        ]
        matched_ids = {item["id"] for item in matched}
        if {"uploadable_documents", "expected_chatbot_answers"}.issubset(matched_ids):
            return (
                "Upload lab reports, prescriptions, discharge summaries, scan notes, or doctor notes.\n"
                "Chatbot gives short health guidance, follow-up questions, document explanations, and doctor-visit prep."
            )
        if matched:
            return matched[0]["answer"]
        asks_docs = any(term in question_lower for term in ["what kind of docs", "what documents", "what can i upload", "upload"])
        asks_bot = any(term in question_lower for term in ["what kind of answer", "what answer", "chatbot", "bot answer", "expect"])
        if asks_docs and asks_bot:
            return (
                "Upload lab reports, prescriptions, discharge summaries, scan notes, or doctor notes.\n"
                "Chatbot gives short health guidance, follow-up questions, document explanations, and doctor-visit prep."
            )
        if asks_docs:
            return "Upload lab reports, prescriptions, discharge summaries, scan notes, or doctor notes. Avoid ID, bank, resume, or unrelated files."
        if asks_bot:
            return "Chatbot gives short health guidance, follow-up questions, document explanations, and doctor-visit prep."
        return None

    def _nlp_answer(self, analysis: HealthNLPAnalysis) -> str | None:
        if analysis.intent == "better_suggestion_info_request":
            return (
                "I need symptom, duration, severity, age, existing conditions, current medicines, allergies, recent reports, "
                "and red flags like breathing trouble, chest pain, bleeding, or severe weakness."
            )
        if analysis.next_action == "ask_followup":
            return self._nlp_followup_answer(analysis)
        if analysis.intent == "medicine_question":
            return "I cannot recommend medication directly. Consult a clinician if worse. Tell me age, symptom duration, conditions, and allergies?"
        if analysis.intent == "symptom_guidance" and analysis.enough_information:
            current_symptoms = set(analysis.current_symptoms)
            if analysis.asks_reason and current_symptoms.intersection({"loose motion", "diarrhea"}):
                return "Loose motions can happen from infection, unsafe food, intolerance, or stress. Drink fluids; see a doctor if blood, fever, or dehydration."
            if current_symptoms.intersection({"vomiting", "loose motion", "diarrhea"}):
                return "For vomiting or loose motions, sip ORS/water, eat light food, and avoid oily/spicy meals. Seek care if severe."
            symptom = ", ".join(analysis.symptoms[:2]) or "symptoms"
            if analysis.requested_diet_guidance and "fever" in set(analysis.symptoms):
                return "For fever, choose light food: rice, soup, curd, fruits, and fluids. Avoid oily, spicy food."
            if analysis.requested_diet_guidance and set(analysis.symptoms).intersection({"cough", "cold", "sore throat"}):
                return "For cough, choose warm fluids, soups, soft food, fruits, and water. Avoid cold drinks and oily food."
            return f"For {symptom}, track changes, rest, hydrate, and consult if symptoms worsen or persist."
        return None

    def _nlp_followup_answer(self, analysis: HealthNLPAnalysis) -> str:
        symptoms = set(analysis.symptoms)
        if analysis.intent == "medicine_question":
            return "I cannot recommend medication directly. Consult a clinician if worse. Tell me age, symptom duration, conditions, and allergies?"
        if "fever" in symptoms and "rash" in symptoms and analysis.duration:
            return "Is the rash spreading, itchy, painful, or blister-like?"
        if "fever" in symptoms and "duration" in analysis.missing_fields:
            return "How many days have you had fever, and what is your temperature?"
        if set(analysis.current_symptoms).intersection({"vomiting", "loose motion", "diarrhea"}):
            return "How long has this been happening, and can you keep fluids down?"
        if "cough" in symptoms and "duration" in analysis.missing_fields:
            return "How many days have you had the cough, and is it dry or with mucus?"
        if "stomach pain" in symptoms or "abdominal pain" in symptoms:
            return "Where is the pain located, and do you have vomiting, fever, or loose motions?"
        first_missing = analysis.missing_fields[0] if analysis.missing_fields else "details"
        prompts = {
            "symptom": "What is your main symptom?",
            "duration": "How long has this been happening?",
            "severity": "How severe is it: mild, moderate, severe, or 1-10?",
            "age": "What is your age?",
            "conditions": "Do you have any existing conditions like diabetes, BP, asthma, thyroid, or heart disease?",
            "allergies": "Do you have any medicine or food allergies?",
            "uploaded_document": "Please upload the report or share the key values you want explained.",
        }
        return prompts.get(first_missing, "Please share one more detail so I can guide you safely.")

    def _is_medication_request(self, question_lower: str) -> bool:
        medication_terms = [
            "which antibiotic",
            "what antibiotic",
            "medicine should i take",
            "tablet should i take",
            "medication for",
            "medicine for",
            "tablet for",
            "drug for",
            "what medicine",
            "which medicine",
            "can i take",
            "give me medicine",
            "give medicine",
            "need medicine",
            "suggest medicine",
            "recommend medicine",
        ]
        return any(term in question_lower for term in medication_terms)

    def _has_fever_with_rash(self, question_lower: str) -> bool:
        return "fever" in question_lower and any(term in question_lower for term in ["rash", "rashes", "spots"])

    def _has_high_fever(self, question_lower: str) -> bool:
        return bool(re.search(r"\b10[3-6](?:\.\d+)?\b", question_lower)) and any(term in question_lower for term in ["fever", "temperature", "temp"])

    def _has_voice_red_flags(self, question_lower: str) -> bool:
        negated_terms = [
            "no breathing trouble",
            "no shortness of breath",
            "no confusion",
            "no fainting",
            "no bleeding",
            "no severe weakness",
            "no chest pain",
            "without breathing trouble",
            "without bleeding",
        ]
        normalized = re.sub(r"\s+", " ", question_lower)
        for term in negated_terms:
            normalized = normalized.replace(term, "")
        red_flag_terms = [
            "breathing trouble",
            "shortness of breath",
            "can't breathe",
            "cannot breathe",
            "confusion",
            "fainting",
            "bleeding",
            "severe weakness",
            "chest pain",
            "swelling of face",
            "swelling of lips",
        ]
        return any(term in normalized for term in red_flag_terms)

    def _voice_intent(self, text: str) -> str:
        for intent, config in VOICE_INTENT_TRAINING_DATA.items():
            if intent == "general":
                continue
            keywords = config.get("keywords", ())
            requires_any = config.get("requires_any")
            if keywords and any(keyword in text for keyword in keywords):
                if requires_any and not any(keyword in text for keyword in requires_any):
                    continue
                return intent
        return "general"

    def _voice_followup_count(self, chat_memory: list[dict]) -> int:
        return sum(
            1
            for message in chat_memory
            if message.get("role") == "assistant"
            and "?" in message.get("content", "")
            and "Based on what you shared" not in message.get("content", "")
        )

    def _next_voice_followup(self, intent: str, text: str, followup_count: int, latest_question: str) -> str | None:
        if followup_count >= 4:
            return None
        if followup_count >= 2 and not self._is_medication_request(latest_question):
            return None
        intent_config = VOICE_INTENT_TRAINING_DATA.get(intent, VOICE_INTENT_TRAINING_DATA["general"])
        for item in intent_config["followups"]:
            if not self._slot_answered(text, item["markers"]):
                return item["question"]
        return None

    def _slot_answered(self, text: str, markers: tuple[str, ...]) -> bool:
        if any(marker in text for marker in markers):
            return True
        return bool(re.search(r"\b\d+\s*(day|days|week|weeks|hour|hours)\b", text))

    def _voice_summary_answer(self, intent: str, text: str) -> str:
        intent_config = VOICE_INTENT_TRAINING_DATA.get(intent, VOICE_INTENT_TRAINING_DATA["general"])
        concern = intent_config["concern"]
        summary = f"Based on what you shared: {concern}. A clinician can check the exact cause."
        guidance = intent_config["guidance"]
        urgent = "Urgent care for breathing trouble, confusion, bleeding, swelling, or severe weakness."
        return f"{summary}\n{guidance}\n{urgent}"

    def _memory_answer(self, question_lower: str, chat_memory: list[dict]) -> str | None:
        memory_terms = ["previous", "last question", "earlier", "before", "what did i ask", "my last"]
        if not any(term in question_lower for term in memory_terms):
            return None
        last_user_message = next(
            (
                message.get("content", "").strip()
                for message in reversed(chat_memory)
                if message.get("role") == "user"
                and message.get("content", "").strip()
                and message.get("content", "").strip().lower() != question_lower
            ),
            "",
        )
        if not last_user_message:
            return "I do not see an earlier question in this chat yet."
        return f"Your previous question was: {last_user_message[:120]}"

    def _trusted_context_answer(self, sources: list) -> str | None:
        if not sources:
            return None
        excerpt = getattr(sources[0], "excerpt", "") or ""
        first_sentence = re.split(r"(?<=[.!?])\s+", excerpt.strip(), maxsplit=1)[0].strip()
        if not first_sentence:
            return None
        cleaned = re.sub(r"\s+", " ", first_sentence)
        return f"Trusted guidance: {cleaned}"

    def _contextual_short_answer(self, question_lower: str) -> str:
        if any(word in question_lower for word in ["pain", "symptom", "cough", "cold", "fever", "dizzy"]):
            return "Track duration, severity, triggers. Consult if worsening."
        if any(word in question_lower for word in ["diet", "weight", "sugar", "salt"]):
            return "Use balanced meals, protein, vegetables, water. Limit sugar."
        if any(word in question_lower for word in ["stress", "sleep", "tired", "fatigue"]):
            return "Improve sleep, hydration, meals, movement. Seek care if persistent."
        return "Need more information: symptom, duration, severity, conditions, medicines?"

    def _trim_to_human_length(self, answer: str) -> str:
        lines = [line.strip() for line in answer.splitlines() if line.strip()][:3]
        compact = "\n".join(lines) if lines else answer.strip()
        words = compact.split()
        if len(words) <= 32:
            return compact
        return " ".join(words[:31]).rstrip(".,;") + "."
