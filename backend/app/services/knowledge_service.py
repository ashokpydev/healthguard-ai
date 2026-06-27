from backend.app.schemas.health import KnowledgeSource
from backend.app.services.rag_service import RAGService


APPROVED_KNOWLEDGE = [
    KnowledgeSource(
        title="Emergency red flags",
        excerpt="Chest pain, severe breathing difficulty, stroke-like symptoms, severe bleeding, unconsciousness, and suicidal thoughts require urgent medical care.",
    ),
    KnowledgeSource(
        title="Medication safety boundary",
        excerpt="Health education tools must not prescribe, start, stop, or change medication without qualified clinician review.",
    ),
    KnowledgeSource(
        title="Lifestyle prevention basics",
        excerpt="Regular movement, adequate sleep, balanced diet, hydration, and routine checkups can reduce common preventive health risks.",
    ),
    KnowledgeSource(
        title="Climate health precautions",
        excerpt="Heat, poor air quality, and seasonal mosquito exposure can increase risk for dehydration, breathing issues, and vector-borne illness.",
    ),
]


class KnowledgeService:
    def retrieve(self, query: str | None, user_id: int | None = None) -> list[KnowledgeSource]:
        rag = RAGService()
        rag.seed_global_knowledge(APPROVED_KNOWLEDGE)
        rag_sources = rag.retrieve(query, user_id=user_id)
        if rag_sources:
            return rag_sources
        if not query:
            return APPROVED_KNOWLEDGE[:3]
        query_lower = query.lower()
        matched = [
            source
            for source in APPROVED_KNOWLEDGE
            if any(word in (source.title + " " + source.excerpt).lower() for word in query_lower.split())
        ]
        return matched or APPROVED_KNOWLEDGE[:2]
