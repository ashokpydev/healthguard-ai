from __future__ import annotations

import re
from pathlib import Path

from generate_healthguard_interview_pdf_builtin import BLUE, GRAY, MARGIN, OUT as _OLD_OUT, SimplePDF


ROOT = Path(__file__).resolve().parents[1]
ATTACHMENT = Path.home() / ".codex" / "attachments" / "9e387e69-7f69-411f-8abb-581b7465f9df" / "pasted-text.txt"
OUT = ROOT / "output" / "pdf" / "GenAI_Team_Lead_Scenario_Answers_HealthGuard_AI.pdf"


def read_questions() -> list[tuple[int, str, str]]:
    text = ATTACHMENT.read_text(encoding="utf-8", errors="ignore")
    items: list[tuple[int, str, str]] = []
    section = "General"
    for raw in text.splitlines():
        line = raw.strip()
        section_match = re.match(r"##\s+\d+\.\s+(.+)", line)
        if section_match:
            section = section_match.group(1).strip()
            continue
        q_match = re.match(r"(\d+)\.\s+(.+)", line)
        if q_match and int(q_match.group(1)) <= 250:
            items.append((int(q_match.group(1)), section, q_match.group(2).strip()))
    return items


def base_answer(section: str) -> dict[str, str]:
    common = {
        "Project Understanding and Ownership": {
            "lead": "I start by converting the idea into a controlled delivery plan before code. For HealthGuard AI, that means clarifying users, risk boundaries, data sources, safety constraints, MVP scope, and success metrics.",
            "steps": "I run discovery workshops, identify patient/doctor/admin/compliance workflows, define what the AI may and may not answer, map regulatory/privacy risks, and produce architecture plus backlog.",
            "validation": "I validate with an MVP scope document, acceptance criteria, prototype flows, risk register, and sign-off from product, clinical, security, and delivery stakeholders.",
            "risk": "The main risk is building a chatbot that looks impressive but is unsafe, unmeasurable, or impossible to operate in production.",
        },
        "Requirement Analysis Scenarios": {
            "lead": "I convert vague GenAI requirements into measurable acceptance criteria. Terms like accurate, human-like, short, safe, or remembers must become testable behavior.",
            "steps": "I define intents, roles, inputs, outputs, response length, safety refusals, memory scope, upload rules, latency targets, evaluation datasets, and user journeys.",
            "validation": "Acceptance criteria should include examples, negative tests, latency limits, citation requirements, red-flag handling, privacy rules, and demo scenarios.",
            "risk": "If requirements stay subjective, teams argue about quality late in delivery and the client loses confidence.",
        },
        "Architecture Design Scenarios": {
            "lead": "I design the architecture around safety, data isolation, observability, and provider flexibility. The LLM is one component, not the whole system.",
            "steps": "Use browser UI, FastAPI APIs, auth/RBAC, service layer, NLP intent analyzer, RAG pipeline, vector store, LLM abstraction, audit logs, workers, and monitoring.",
            "validation": "I review the architecture against scale, security, privacy, failure modes, cost, latency, and maintainability.",
            "risk": "A weak architecture usually leaks data, mixes conversations, blocks API requests, or cannot survive LLM/provider failure.",
        },
        "RAG Pipeline Scenarios": {
            "lead": "For RAG, I focus on ingestion quality, metadata, retrieval quality, and answer grounding. Uploading a document is not enough; the retrieval pipeline must be measurable.",
            "steps": "Validate files, extract text, clean, chunk, embed, store chunks with metadata, retrieve by semantic and keyword search, rerank, build prompt, cite sources, and filter by user_id.",
            "validation": "I test retrieval with known questions, expected chunks, citation accuracy, faithfulness, context precision/recall, and user isolation.",
            "risk": "Poor chunking, missing metadata, or unfiltered retrieval creates wrong answers or cross-user data leakage.",
        },
        "LLM and Prompt Engineering Scenarios": {
            "lead": "Prompt engineering must be treated like versioned application logic. It needs requirements, tests, rollout, rollback, and monitoring.",
            "steps": "Create system, RAG, safety, voice, concise-answer, and JSON prompts. Keep prompts short, explicit, and backed by backend rules.",
            "validation": "Run prompt regression tests for style, safety, citations, hallucination, refusal, latency, and token cost before release.",
            "risk": "Prompt-only safety is fragile. Backend rules must block medication dosage, diagnosis, unsafe medical advice, and prompt injection.",
        },
        "Voice Assistant Scenarios": {
            "lead": "Voice must behave like a conversation, not a file upload or assessment form. The core UX is listening, waiting through short pauses, finalizing transcript, then asking short follow-ups.",
            "steps": "Use continuous recognition, interim results, 5-second silence detection, manual stop, transcript correction, voice_mode routing, and short conversational responses.",
            "validation": "Test pauses, noisy speech, wrong transcript, unsupported browser, manual stop, mobile layout, and red-flag escalation.",
            "risk": "If voice stops early or triggers report generation, users lose trust quickly.",
        },
        "Chat Memory Scenarios": {
            "lead": "Chat memory must be scoped and ordered. The latest active conversation should drive follow-up answers, while old memory is only supporting context.",
            "steps": "Save user message first, fetch latest messages by user_id and conversation_id, order DESC, limit 5-10, reverse to chronological order, then build the prompt.",
            "validation": "Test latest-message memory, long conversations, old conversation isolation, cross-user isolation, and assistant failure after user-message save.",
            "risk": "Bad memory logic causes the bot to answer the wrong question or leak data across users.",
        },
        "NLP / Intent Detection Scenarios": {
            "lead": "The NLP layer turns raw user text into structured intent and entities before answer generation. This prevents generic or unsafe replies.",
            "steps": "Extract intent, symptoms, duration, severity, age, medicines, allergies, conditions, red flags, missing fields, and next action.",
            "validation": "Use labeled examples, confusion matrix, entity-level accuracy, red-flag recall, spelling/voice-error tests, and production feedback loops.",
            "risk": "If intent detection is weak, the bot either over-asks, under-asks, or gives unsafe answers.",
        },
        "Safety and Guardrail Scenarios": {
            "lead": "Healthcare GenAI needs deterministic guardrails before LLM output. Safety is not optional and cannot be delegated only to prompts.",
            "steps": "Refuse diagnosis, prescription, dosage, and medication changes. Detect red flags, escalate emergencies, use calm language, log unsafe attempts, and add doctor review.",
            "validation": "Create safety acceptance tests for medication, dosage, red flags, diagnosis requests, report interpretation, and hallucinated medical advice.",
            "risk": "Unsafe medical output is a product, legal, and patient-safety risk.",
        },
        "Evaluation Metrics Scenarios": {
            "lead": "Evaluation must cover answer correctness, grounding, safety, latency, and user experience. Manual testing alone is not enough.",
            "steps": "Measure faithfulness, relevance, context precision/recall, citation accuracy, hallucination rate, red-flag detection, memory accuracy, and voice completion rate.",
            "validation": "Build gold datasets, run model A/B comparisons, monitor production feedback, and review failed cases weekly.",
            "risk": "Without metrics, the team cannot prove improvement or detect regressions.",
        },
        "Performance and Scalability Scenarios": {
            "lead": "I debug latency by breaking down time across frontend, API, retrieval, LLM, database, and workers. Then I optimize the bottleneck, not guesses.",
            "steps": "Use async I/O, streaming, caching, token reduction, smaller classifiers, batch embeddings, background workers, rate-limit handling, and queue monitoring.",
            "validation": "Track P50/P95/P99 latency, throughput, queue length, provider latency, retrieval latency, and cost per request.",
            "risk": "Large files, slow LLMs, and blocking API requests can make the product unusable under load.",
        },
        "Database and Data Design Scenarios": {
            "lead": "The data model must support ownership, auditability, versioning, retrieval, and deletion. For healthcare, isolation is as important as schema correctness.",
            "steps": "Design users, sessions, profiles, assessments, reports, conversations, messages, documents, chunks, embeddings, knowledge, reviews, and audit logs.",
            "validation": "Review foreign keys, indexes, user_id filters, migration strategy, backups, soft/hard delete policy, and restore drills.",
            "risk": "Weak data design creates privacy issues, slow queries, and painful migrations.",
        },
        "Security and Privacy Scenarios": {
            "lead": "Security starts with backend enforcement: authentication, RBAC, ownership filters, upload scanning, audit logs, secret management, and HTTPS.",
            "steps": "Protect APIs, secure env variables, isolate RAG chunks, mask PHI in logs, require consent, prevent prompt injection, and configure no-reply email properly.",
            "validation": "Run role tests, cross-user isolation tests, upload security tests, audit checks, and dependency/security scans.",
            "risk": "Frontend-only checks, leaked secrets, or unfiltered retrieval can expose patient data.",
        },
        "DevOps and Deployment Scenarios": {
            "lead": "A production GenAI deployment needs more than running Uvicorn. It needs containers, managed data services, secrets, monitoring, CI/CD, rollback, and prompt release control.",
            "steps": "Deploy frontend/backend separately, configure PostgreSQL, Redis, object storage, vector DB, HTTPS, API keys, migrations, smoke tests, and environment-specific config.",
            "validation": "Use staging, production, health checks, dashboards, logs, alerts, pipeline tests, and rollback rehearsals.",
            "risk": "Demo-style deployment fails under real traffic, security review, or provider outages.",
        },
        "Team Lead and Delivery Scenarios": {
            "lead": "As a team lead, I translate product goals into workstreams, risks, reviews, and measurable delivery. I do not let GenAI remain a black box.",
            "steps": "Split frontend, backend, AI/RAG, QA, DevOps tasks; run standups; review architecture; enforce tests; manage scope; and communicate risks early.",
            "validation": "Track progress through milestones, demos, acceptance criteria, risk burn-down, bug trends, and evaluation metrics.",
            "risk": "Without leadership discipline, teams over-focus on prompts and miss safety, data, testing, and production readiness.",
        },
        "Client Demo Scenarios": {
            "lead": "A client demo should tell a safe product story: problem, workflow, value, guardrails, evidence, and limitations.",
            "steps": "Demo login, assessment, chat, voice, document upload, RAG answer with citation, safety refusal, memory, doctor review, and admin knowledge.",
            "validation": "Prepare fallback data, offline examples, known demo prompts, LLM failure plan, release notes, and feedback capture.",
            "risk": "Live GenAI demos can fail; a lead prepares deterministic paths and explains limitations honestly.",
        },
        "Deep Validation Questions": {
            "lead": "For deep validation, I explain the real implementation flow, not generic AI theory. I connect user action to API, services, data, safety, retrieval, and monitoring.",
            "steps": "Walk through request lifecycle, storage, NLP, RAG, LLM, safety, response persistence, and tests.",
            "validation": "Use concrete examples from HealthGuard AI: fever, rash, medicine refusal, document upload, voice follow-up, and memory bug fix.",
            "risk": "If a candidate cannot explain edge cases, they probably did not own the implementation.",
        },
    }
    return common.get(section, common["Project Understanding and Ownership"])


def answer_question(num: int, section: str, question: str) -> list[str]:
    b = base_answer(section)
    q = question.lower()
    lines = [b["lead"]]
    if "what is the first" in q:
        lines.append("My first step is discovery: confirm business goal, target users, clinical safety boundaries, data availability, compliance needs, success metrics, and MVP timeline.")
    elif "vague" in q or "one line" in q or "what questions" in q:
        lines.append("I convert vague input into a requirement checklist: user roles, top use cases, data sources, answer boundaries, latency, safety, integrations, reporting, and acceptance criteria.")
    elif "hallucinat" in q:
        lines.append("I combine RAG grounding, citation rules, answer refusal when context is missing, deterministic safety filters, prompt regression tests, and monitoring of unsupported claims.")
    elif "remember" in q or "memory" in q or "latest" in q:
        lines.append("I require user_id and conversation_id scoping, saving the current user message before generation, latest-message retrieval, chronological prompt order, and tests for old-memory leakage.")
    elif "voice" in q:
        lines.append("For voice, I require continuous listening, interim transcript handling, manual stop, 5-second silence detection, final-transcript submission, and lightweight chat mode.")
    elif "medicine" in q or "dosage" in q or "prescription" in q:
        lines.append("Medication and dosage requests must be refused safely. The bot should ask for context and suggest clinician review, but it must not prescribe or adjust medicines.")
    elif "red-flag" in q or "chest pain" in q or "breathing" in q or "emergency" in q:
        lines.append("Red flags should trigger calm urgent-care guidance immediately, with no long diagnostic discussion.")
    elif "document" in q or "pdf" in q or "rag" in q or "chunk" in q or "embedding" in q:
        lines.append("For document/RAG scenarios, I focus on extraction quality, chunking, metadata, vector retrieval, reranking, citations, and strict user isolation.")
    elif "deploy" in q or "production" in q or "ci/cd" in q or "rollback" in q:
        lines.append("For delivery, I plan environments, Dockerization, secrets, migrations, observability, CI/CD, smoke tests, prompt versioning, and rollback.")
    elif "team" in q or "developer" in q or "mentor" in q or "standup" in q or "client" in q:
        lines.append("As team lead, I split ownership clearly, review architecture and PRs, track risks, mentor developers, and translate technical trade-offs for stakeholders.")
    else:
        lines.append(b["steps"])
    lines.append(f"Implementation approach: {b['steps']}")
    lines.append(f"Validation: {b['validation']}")
    lines.append(f"Risk/trade-off: {b['risk']}")
    return lines


def add_text_list(pdf: SimplePDF, items: list[str]):
    for item in items:
        pdf.ensure(26)
        pdf.text("-", MARGIN + 4, pdf.y, 8.8, "F2", "0.07 0.39 0.40")
        pdf.paragraph(item, 8.8, indent=16, gap=2)


def build_pdf():
    questions = read_questions()
    pdf = SimplePDF()
    pdf.y -= 85
    pdf.text("GenAI Team Lead Scenario Answers", 86, pdf.y, 24, "F2", BLUE)
    pdf.y -= 26
    pdf.text("Detailed Project Manager / Delivery Manager Interview Preparation", 92, pdf.y, 12, "F1", GRAY)
    pdf.y -= 40
    pdf.paragraph(
        "This document provides detailed answers for the complete scenario-based GenAI Team Lead question bank. Answers are framed around HealthGuard AI: a healthcare GenAI, RAG, voice assistant, patient-safety chatbot platform.",
        10.5,
    )
    pdf.paragraph(
        "Use these answers to demonstrate end-to-end ownership: requirement discovery, architecture, RAG, LLM safety, voice UX, memory isolation, evaluation, performance, database design, security, DevOps, leadership, demo handling, and production readiness.",
        10.5,
    )
    pdf.new_page()

    current_section = ""
    for num, section, question in questions:
        if section != current_section:
            current_section = section
            pdf.heading(int(re.match(r"(\d+)", str(num)).group(1)) if False else len({s for _, s, _ in questions[:questions.index((num, section, question)) + 1]}), section)
            pdf.paragraph(
                "Team-lead lens: answer with business clarity, technical depth, safety awareness, measurable acceptance criteria, and delivery ownership.",
                9.2,
            )
        pdf.ensure(82)
        pdf.text(f"Q{num}. {question}", MARGIN, pdf.y, 10.2, "F2", BLUE)
        pdf.y -= 15
        add_text_list(pdf, answer_question(num, section, question))
        pdf.y -= 4

    pdf.heading(18, "Strong Follow-Up Probe Answering Framework")
    add_text_list(
        pdf,
        [
            "Why this approach? Tie the choice to safety, scalability, user trust, delivery speed, and maintainability.",
            "Alternatives considered: mention simpler chatbot, pure LLM, RAG, fine-tuning, agents, and rule-based systems where relevant.",
            "What can go wrong? Discuss hallucination, wrong retrieval, data leakage, latency, cost, browser issues, and unclear requirements.",
            "How to test? Use unit tests, integration tests, RAG evals, prompt regressions, red-flag tests, memory tests, and user acceptance scenarios.",
            "How to monitor? Track latency, errors, cost, retrieval quality, hallucination rate, feedback, queue length, and safety events.",
            "How to explain to client? Use workflow diagrams, demos, limitations, phased delivery, and risk register language.",
            "How to scale and secure? Use workers, caching, vector DB, RBAC, owner filters, encryption, audit logs, and HTTPS.",
        ],
    )
    pdf.heading(19, "Scoring Rubric - How to Sound Like a Real Team Lead")
    pdf.table_text(
        ["Area", "Strong Answer", "Weak Answer"],
        [
            ["Architecture", "Explains full flow, failure modes, and integrations", "Only says use LLM API"],
            ["RAG", "Explains chunks, embeddings, metadata, retrieval, reranking", "Only says upload docs"],
            ["Safety", "Mentions no diagnosis, no dosage, red flags, tests", "Ignores medical risk"],
            ["Memory", "Uses user_id + conversation_id and latest-message ordering", "Mixes old chats"],
            ["Voice", "Handles silence, interim transcript, manual stop", "Only says use mic"],
            ["Evaluation", "Uses faithfulness, relevance, recall, safety metrics", "Manual testing only"],
            ["Security", "RBAC, PHI, audit, isolation, prompt injection", "Frontend checks only"],
            ["Delivery", "MVP, phases, risks, estimation, stakeholder alignment", "No planning approach"],
            ["Leadership", "Splits tasks, reviews, mentors, manages blockers", "Only individual coding"],
            ["Production", "Monitoring, CI/CD, rollback, secrets, health checks", "Demo-only thinking"],
        ],
        [15, 43, 34],
    )
    pdf.paragraph(
        "Best interview line: A strong GenAI Team Lead should not only know LLM, RAG, and prompts. They should know how to deliver a safe, scalable, secure, tested, monitored, production-ready AI system with a team.",
        10.0,
    )
    pdf.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build_pdf()
