from __future__ import annotations

import re
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "HealthGuard_AI_Interview_Preparation_Guide.pdf"
PAGE_W = 595.28
PAGE_H = 841.89
MARGIN = 48
TOP = PAGE_H - 64
BOTTOM = 56
BLUE = "0.06 0.17 0.36"
TEAL = "0.07 0.39 0.40"
GRAY = "0.25 0.29 0.36"


def pdf_escape(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class SimplePDF:
    def __init__(self):
        self.pages: list[str] = []
        self.ops: list[str] = []
        self.y = TOP
        self.page_no = 0
        self.new_page()

    def new_page(self):
        if self.ops:
            self.pages.append("\n".join(self.ops))
        self.page_no += 1
        self.ops = []
        self.y = TOP
        self.rect(0, PAGE_H - 38, PAGE_W, 38, BLUE, fill=True)
        self.text("HealthGuard AI - Senior Software Engineer / GenAI Interview Guide", MARGIN, PAGE_H - 24, 9, "F2", "1 1 1")
        self.text("Healthcare GenAI | RAG | Voice Assistant | Patient Safety Chatbot", MARGIN, 28, 8, "F1", GRAY)
        self.text(f"Page {self.page_no}", PAGE_W - MARGIN - 45, 28, 8, "F1", GRAY)

    def finish_page(self):
        if self.ops:
            self.pages.append("\n".join(self.ops))
            self.ops = []

    def ensure(self, amount: float):
        if self.y - amount < BOTTOM:
            self.new_page()

    def text(self, value: str, x: float, y: float, size: float, font: str = "F1", color: str = "0 0 0"):
        self.ops.append(f"BT {color} rg /{font} {size} Tf {x:.2f} {y:.2f} Td ({pdf_escape(value)}) Tj ET")

    def rect(self, x: float, y: float, w: float, h: float, color: str, fill: bool = False):
        op = "f" if fill else "S"
        self.ops.append(f"{color} rg {color} RG {x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "0.82 0.85 0.88"):
        self.ops.append(f"{color} RG 0.6 w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def paragraph(self, text: str, size: float = 9.5, font: str = "F1", color: str = "0.07 0.09 0.13", indent: float = 0, gap: float = 5):
        usable = PAGE_W - 2 * MARGIN - indent
        chars = max(40, int(usable / (size * 0.50)))
        lines = []
        for para in text.split("\n"):
            if not para.strip():
                lines.append("")
            else:
                lines.extend(textwrap.wrap(para.strip(), width=chars, break_long_words=False))
        self.ensure((len(lines) + 1) * (size + 3))
        for line in lines:
            if line:
                self.text(line, MARGIN + indent, self.y, size, font, color)
            self.y -= size + 3
        self.y -= gap

    def heading(self, number: int, title: str):
        self.ensure(48)
        self.y -= 4
        self.text(f"{number}. {title}", MARGIN, self.y, 16, "F2", BLUE)
        self.y -= 8
        self.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 14

    def subheading(self, title: str):
        self.ensure(24)
        self.text(title, MARGIN, self.y, 11.5, "F2", TEAL)
        self.y -= 17

    def bullets(self, items: list[str]):
        for item in items:
            self.ensure(18)
            self.text("-", MARGIN + 4, self.y, 9.5, "F2", TEAL)
            self.paragraph(item, 9.2, indent=16, gap=0)
        self.y -= 3

    def code(self, text: str):
        lines = text.strip("\n").splitlines()
        self.ensure((len(lines) + 1) * 10)
        self.rect(MARGIN - 4, self.y - len(lines) * 10 - 8, PAGE_W - 2 * MARGIN + 8, len(lines) * 10 + 12, "0.95 0.97 0.99", fill=True)
        for line in lines:
            self.text(line[:105], MARGIN, self.y - 10, 7.6, "F3", "0.05 0.07 0.10")
            self.y -= 10
        self.y -= 12

    def table_text(self, headers: list[str], rows: list[list[str]], widths: list[int]):
        self.ensure(32)
        fmt = " | ".join("{:<" + str(w) + "}" for w in widths)
        self.text(fmt.format(*[h[:w] for h, w in zip(headers, widths)]), MARGIN, self.y, 7.5, "F3", "1 1 1")
        self.rect(MARGIN - 4, self.y - 3, PAGE_W - 2 * MARGIN + 8, 13, BLUE, fill=True)
        self.y -= 16
        for row in rows:
            values = [re.sub(r"\s+", " ", cell)[:w] for cell, w in zip(row, widths)]
            self.ensure(14)
            self.text(fmt.format(*values), MARGIN, self.y, 7.2, "F3", "0.06 0.09 0.16")
            self.y -= 11
        self.y -= 8

    def save(self, path: Path):
        self.finish_page()
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{i * 2 + 6} 0 R" for i in range(len(self.pages)))
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode())
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
        for i, content in enumerate(self.pages):
            content_obj = len(objects) + 2
            page = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {content_obj} 0 R >>"
            objects.append(page.encode())
            stream = content.encode("latin-1", errors="replace")
            objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        path.parent.mkdir(parents=True, exist_ok=True)
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        path.write_bytes(out)


def add_section(pdf: SimplePDF, n: int, title: str, paras: list[str], bullets: list[str] | None = None):
    pdf.heading(n, title)
    for para in paras:
        pdf.paragraph(para)
    if bullets:
        pdf.bullets(bullets)


def qa_pairs() -> list[tuple[str, str]]:
    seeds = [
        ("Why RAG?", "RAG grounds answers in uploaded documents and approved knowledge without training private patient data into the model."),
        ("Why not only LLM?", "LLMs can hallucinate. HealthGuard uses deterministic safety rules, NLP intent extraction, RAG context, and tests."),
        ("How do you avoid hallucination?", "Use scoped retrieval, citations, safe base answers, refusal rules, and prompt regression tests."),
        ("How do embeddings work?", "Chunks become numeric vectors. Similar vectors represent semantically related content."),
        ("What vector DB did you use?", "The demo supports local embedding JSON and is ready for pgvector or Qdrant."),
        ("How does chunking work?", "Documents are split into overlapping chunks with metadata for precise retrieval."),
        ("How do you handle latest records?", "Fetch latest chat rows DESC, limit them, then reverse to chronological order."),
        ("How do you isolate user data?", "Every chat, report, and RAG query filters by user_id and conversation_id or ownership."),
        ("How do you handle voice input?", "Continuous speech recognition captures interim text and sends the final transcript to lightweight chat mode."),
        ("Why async?", "Async improves throughput for I/O waits such as LLM, DB, SMTP, and vector search."),
        ("Async vs threading vs multiprocessing?", "Async handles waiting I/O, threads handle blocking I/O, and multiprocessing handles CPU-heavy parsing/OCR."),
        ("How do decorators work?", "Decorators wrap functions to add behavior such as auth checks, logging, caching, or rate limits."),
        ("How do you handle 5000 Excel uploads?", "Save files, create jobs, process with Redis/Celery workers, use read_only mode, batch inserts, and progress tracking."),
        ("What metrics do you monitor?", "Latency, P95, errors, token usage, cost, LLM latency, vector latency, RAG hit rate, queue length, and feedback."),
        ("How do you test RAG?", "Use known documents, expected chunks, citation checks, isolation tests, and prompt regressions."),
        ("Prompt engineering vs fine-tuning?", "Prompting changes instructions; fine-tuning trains behavior. RAG supplies dynamic knowledge."),
        ("How CI/CD works for GenAI?", "Run unit tests, integration tests, RAG evals, prompt regressions, security scans, Docker build, deploy, and rollback."),
        ("How do you secure PHI?", "Use auth, RBAC, owner filters, masked logs, secret management, HTTPS, and audit logs."),
        ("How do you handle LLM failure?", "Fail closed for reports and use rules-based fallback for safe chat when possible."),
        ("What is fail-closed behavior?", "Stop a risky operation instead of saving or returning incomplete unsafe output."),
        ("How do you reduce cost?", "Short prompts, smaller classifiers, top_k tuning, caching, token limits, and avoiding unnecessary LLM calls."),
        ("How do you improve performance?", "Batch embeddings, cache metadata, tune chunks, use workers, stream responses, and reduce tokens."),
        ("Why FastAPI?", "It provides typed APIs, validation, OpenAPI docs, async readiness, and clean Python service structure."),
        ("Why Pydantic?", "It validates data contracts and prevents malformed health data from entering service logic."),
        ("Why layered architecture?", "It separates routes, schemas, services, storage, RAG, LLM, and security for testability."),
        ("What is the NLP layer?", "It extracts intent, symptoms, duration, severity, age, medicines, allergies, conditions, and missing fields."),
        ("What intents are detected?", "Symptom guidance, medicine question, lab report question, diet question, emergency symptom, and info request."),
        ("How are red flags detected?", "Rules detect chest pain, breathing trouble, bleeding, confusion, fainting, and severe weakness."),
        ("Why no repeated disclaimer?", "Repeated disclaimers hurt UX; safety appears when risk requires it and static guidance covers general limits."),
        ("How do you refuse medication?", "The bot says it cannot recommend medication/dosage and asks for context or clinician review."),
        ("How do you handle dosage questions?", "Dosage is refused because it needs clinician judgment and patient-specific context."),
        ("What is user-specific memory?", "Recent messages from the current user_id and conversation_id only."),
        ("How was the memory bug fixed?", "Current user message is saved first, latest rows are fetched DESC, and rows are reversed before prompt use."),
        ("How do you prevent old chats mixing?", "Backend filters by conversation_id and frontend stores active conversation keys per user."),
        ("Can doctors see patient chats?", "Not by default. Doctor workflow focuses on reviewable reports, not private chat memory."),
        ("What documents can users upload?", "Lab reports, prescriptions, discharge summaries, scan notes, doctor notes, vitals, and allergy records."),
        ("What documents should not be uploaded?", "IDs, bank files, resumes, unrelated photos, or non-health files."),
        ("How do you validate uploads?", "Size/type checks, malware pattern scan, extraction checks, and audit logging."),
        ("How are documents indexed?", "Extract text, clean, chunk, embed, store metadata, and link chunks to user_id."),
        ("What is metadata filtering?", "Filtering retrieval by user_id, source type, document ID, category, and ownership."),
        ("Why citations?", "They make answers auditable and reduce unsupported claims."),
        ("How choose chunk size?", "Balance semantic completeness, retrieval precision, and token cost."),
        ("What is overlap?", "Shared text between chunks to preserve context at boundaries."),
        ("What is reranking?", "A second ranking step to reorder retrieved chunks by final relevance."),
        ("How handle poor retrieval?", "Ask clarification, lower confidence, avoid pretending context exists, and cite only real sources."),
        ("What does a report include?", "Risk summary, precautions, diet, wellness plan, doctor questions, reminders, and sources."),
        ("Why mandatory fields?", "Reports require enough structured data to avoid unsafe generic output."),
        ("Why consent validation?", "Health data processing must be explicit and auditable."),
        ("What is triage?", "Rule-based urgent symptom and risk detection before LLM/report generation."),
        ("What is risk scoring?", "Deterministic scoring across symptoms, lifestyle, conditions, sleep, diet, and red flags."),
    ]
    extra_answers = {
        "PDF generation": "The report/PDF layer formats structured report data into a doctor-ready document with sections, sources, review metadata, and page numbers.",
        "doctor review": "Doctors review submitted reports, add status, notes, priority, signature, and follow-up guidance without bypassing patient ownership controls.",
        "admin knowledge": "Admins upload trusted knowledge with category and citation metadata so RAG can retrieve approved context.",
        "compliance role": "Compliance users inspect audit logs, privacy controls, security status, and operational evidence.",
        "email verification": "Registration creates an OTP; the account stays restricted until the email is verified.",
        "Google SSO": "The app has provider start/callback scaffolding so production identity can integrate without changing business flows.",
        "backend route protection": "Every protected API validates the token, role, and ownership. Frontend hiding is never trusted.",
        "sessions": "Sessions or tokens identify verified users and are checked on each protected request.",
        "CSRF": "Cookie-authenticated writes should require a CSRF token so other sites cannot submit actions as the user.",
        "secret management": "Local .env is for demo only. Production should use a cloud secret manager or vault.",
        "SPF": "SPF authorizes which mail servers can send email for the domain.",
        "DKIM": "DKIM signs email so receivers can verify it came from an authorized domain sender.",
        "DMARC": "DMARC tells receivers what to do when SPF or DKIM fails and improves email trust.",
        "no personal Gmail": "Production should use a domain no-reply sender with SPF, DKIM, DMARC, auditability, and deliverability.",
        "PHI masking": "Logs should avoid raw health text and store IDs, hashes, event types, and limited metadata.",
        "audit logging": "Important actions such as login, upload, report generation, review, and deletion are recorded.",
        "privacy export": "Users can export their stored reports, chats, consents, and related health data.",
        "delete health data": "A confirmation flow deletes user-owned reports, chats, documents, and profiles.",
        "voice silence detection": "A timer resets when speech arrives and auto-stops after five seconds of silence.",
        "interim transcripts": "Interim results make speech capture feel live and prevent losing partial phrases.",
        "manual stop": "Manual Stop lets the user finish immediately without waiting for silence detection.",
        "voice assessment separation": "Voice questions go to lightweight chatbot mode unless the user explicitly starts assessment/report generation.",
        "voice follow-ups": "The bot asks one short question at a time and limits follow-ups to a few useful details.",
        "voice summary": "After enough details, the bot summarizes symptoms and gives precautions, diet, hydration, rest, and doctor-prep notes.",
        "safe wording": "The assistant uses calm wording such as consult a clinician or seek urgent care for specific red flags.",
        "allergy extraction": "The NLP layer scans allergy/allergic phrases and stores mentioned allergy context.",
        "age extraction": "The NLP layer detects phrases such as age is, I am, or I'm followed by a number.",
        "severity extraction": "Severity can be mild/moderate/severe, a 1-10 score, or a high temperature value.",
        "duration extraction": "Duration is extracted from phrases like for two days, since yesterday, today, or for 3 hours.",
        "medicine extraction": "Medicine intent is detected from medicine, medication, tablet, antibiotic, can I take, and similar wording.",
        "condition extraction": "Conditions such as diabetes, BP, asthma, thyroid, cholesterol, kidney, and heart disease are recognized.",
        "follow-up selection": "Missing required fields for the detected intent decide the next single follow-up question.",
        "default answer style": "The chatbot defaults to 1-3 short lines and avoids long paragraphs unless requested.",
        "streaming responses": "Streaming sends token-like chunks so users see progress before the final answer is complete.",
        "rate limiting": "Rate limits protect APIs from abuse and accidental repeated requests.",
        "upload scanning": "Uploads are checked for size, type, suspicious content, and extraction viability before indexing.",
        "unsupported browser voice": "The UI shows a clear message and allows manual transcript typing.",
        "ASR failure": "The backend returns a safe generic transcription error without leaking provider internals.",
        "local vector store": "The demo can store embeddings as JSON locally for simple semantic retrieval.",
        "pgvector": "pgvector is useful when PostgreSQL is already the primary database and vector search should stay nearby.",
        "Qdrant": "Qdrant is suitable for a dedicated scalable vector service with payload filtering and fast retrieval.",
        "prompt output tests": "Prompt regression tests assert style, refusal language, shortness, stages, and no unsafe content.",
        "RAG evaluation": "RAG evals check that known queries retrieve expected chunks and cite correct sources.",
        "backups": "Production needs database, object storage, vector index, and audit log backups with restore drills.",
        "rollback": "Rollback returns the system to a known-good deployment if smoke tests or metrics fail.",
        "model upgrades": "Model upgrades require prompt regression, safety, RAG, and cost/latency tests before release.",
        "token optimization": "Keep prompts short, retrieve only relevant chunks, limit memory, and choose compact output.",
        "small classifier model": "A smaller model or rules can classify intent cheaply before calling a larger model.",
        "large final model": "A larger model is reserved for final synthesis when context and safety checks justify it.",
        "hallucination rate": "Track unsupported claims and improve prompts/retrieval when the rate rises.",
        "citation coverage": "Measure how often RAG answers include usable citations and source references.",
        "P95 latency": "P95 shows the user experience for slower requests and guides performance tuning.",
        "queue length": "Queue length reveals whether background workers are keeping up with uploads and embeddings.",
        "one-line explanation": "HealthGuard AI is a safe healthcare GenAI workspace combining FastAPI, RAG, voice, NLP, memory, and RBAC.",
        "production hardening": "Harden with PostgreSQL, Redis/Celery, pgvector/Qdrant, HTTPS, secrets, monitoring, backups, and security review.",
    }
    for topic, answer in extra_answers.items():
        seeds.append((f"How do you handle {topic}?", answer))
    return seeds[:100]


def build():
    pdf = SimplePDF()
    pdf.y -= 90
    pdf.text("HealthGuard AI", 165, pdf.y, 28, "F2", BLUE)
    pdf.y -= 28
    pdf.text("Complete Senior Software Engineer / GenAI Developer Interview Preparation Guide", 82, pdf.y, 12, "F1", GRAY)
    pdf.y -= 50
    pdf.table_text(
        ["Item", "Details"],
        [
            ["Project Type", "Healthcare GenAI / RAG / Voice Assistant / Patient Safety Chatbot"],
            ["Goal", "Safe, short, user-friendly guidance without diagnosis, prescriptions, or dosage advice"],
            ["Capabilities", "Assessment, chatbot, voice input, document upload, RAG, reports, doctor review, admin knowledge"],
            ["Interview Focus", "Architecture, safety, RAG, memory isolation, NLP, voice, testing, deployment"],
        ],
        [18, 72],
    )
    pdf.paragraph("This PDF is written for practical interview preparation. It explains the implemented project, design decisions, backend and frontend flows, GenAI architecture, production readiness, and cross-question answers.", 10)
    pdf.new_page()

    add_section(pdf, 1, "Project Overview", [
        "HealthGuard AI is a healthcare assistant workspace for patients, doctors, admins, and compliance users. It allows patients to enter health details, ask health questions, use voice input, upload medical documents, generate educational reports, and prepare for doctor review.",
        "The business problem is fragmented patient information and unclear symptom communication. The application organizes inputs and provides safe, short guidance while avoiding diagnosis, prescription, and dosage advice.",
    ], ["Patient: assessment, chatbot, voice, upload, reports.", "Doctor/Dietician: review reports and add notes.", "Admin: manage trusted knowledge and citations.", "Compliance: audit and privacy controls."])

    pdf.heading(2, "Complete Tech Stack")
    pdf.table_text(["Layer", "Technology", "Why"], [
        ["Frontend", "HTML/CSS/JavaScript, React-ready", "Responsive dashboard, chatbot, voice UI, mobile nav"],
        ["Backend", "Python FastAPI", "Typed APIs, service layer, async-ready"],
        ["LLM", "Gemini/OpenAI-ready abstraction", "Provider swap, JSON contract, fail-closed"],
        ["RAG", "Extraction, chunks, embeddings", "Grounded answers from documents"],
        ["Database", "SQLite fallback / PostgreSQL-ready", "Demo plus production persistence"],
        ["Vector DB", "Local vectors / pgvector / Qdrant-ready", "Semantic search with user metadata"],
        ["Auth", "Email OTP, sessions, SSO path", "Verified users and RBAC"],
        ["Email", "SMTP no-reply", "Verification and password reset"],
        ["PDF", "Built-in generator / ReportLab-ready", "Reports and interview docs"],
        ["Voice", "Web Speech API / ASR fallback", "Natural voice questions"],
        ["Monitoring", "Health endpoints, audit logs", "Operational readiness"],
        ["CI/CD", "GitHub Actions/Jenkins-ready", "Tests, build, deploy, rollback"],
    ], [14, 27, 46])

    pdf.heading(3, "Complete Project Structure")
    pdf.code("""
healthguard-ai/
  backend/app/api/           FastAPI routes
  backend/app/schemas/       Pydantic contracts
  backend/app/services/      Auth, chat, NLP, RAG, LLM, report, PDF, speech, storage
  backend/app/db/            SQLite/PostgreSQL schema and connections
  backend/tests/             Safety, auth, RAG, memory, upload, report tests
  frontend/index.html        Dashboard, chatbot, voice, forms, reports
  frontend/app.js            API calls, memory keys, voice capture, UI behavior
  frontend/styles.css        Responsive healthcare UI and chatbot drawer
  docs/                      Documentation
  scripts/                   Utility and PDF generation scripts
  output/pdf/                Generated artifacts
  infra/                     Docker/deployment-ready assets
""")
    pdf.paragraph("The architecture is layered so routes stay thin, schemas validate data, services own business logic, and storage/RAG/LLM integrations are isolated and testable.")

    add_section(pdf, 4, "System Architecture", ["The browser talks to FastAPI. FastAPI enforces auth/RBAC, routes work to services, stores data in the database, retrieves RAG context, calls the LLM abstraction when needed, and generates PDFs or audit logs."], [])
    pdf.code("""
Browser UI -> FastAPI Routes -> Auth/RBAC -> Services
  -> Chat + NLP + Safety -> RAG Retrieval -> LLM/Rules -> Chat Memory
  -> Assessment -> Report Engine -> PDF
  -> Upload -> Extract -> Chunk -> Embed -> Vector Store
  -> SMTP -> Audit Logs -> Health Checks
""")
    add_section(pdf, 5, "Backend Architecture", ["Routes handle HTTP, consent, auth, and orchestration. Services implement domain logic. Storage owns database queries. RAG and LLM layers isolate external systems. This separation improves testing and production maintainability."], ["API routes", "Pydantic schemas", "Services layer", "Database/repository layer", "RAG layer", "LLM provider layer", "Security and monitoring layers"])
    add_section(pdf, 6, "Frontend Architecture", ["The frontend includes login/register, email verification, dashboard, chatbot, voice assistant, assessment form, document upload, reports, doctor review, admin knowledge upload, and mobile responsive navigation."], ["Textbox clears after Send", "Loading states", "Mobile hamburger menu", "Floating chatbot", "Voice states: Listening, Processing, Responding"])
    add_section(pdf, 7, "Authentication and Authorization Flow", ["Users register, verify email OTP, log in, and access role-specific dashboards. Backend route protection is mandatory because frontend hiding is only UX."], ["Patient, doctor, admin, compliance roles", "Session/JWT-ready handling", "Google SSO path", "User data isolation"])
    add_section(pdf, 8, "Chatbot Functionality", ["The chatbot gives short 1-3 line answers, avoids repeated disclaimers, shows urgent safety only for red flags, stores user-specific memory, and scopes history by user_id and conversation_id."], ["Stores user message immediately", "Fetches latest 5-10 messages", "Uses active conversation only", "Does not mix users or old conversations", "Current message is always included"])
    pdf.code("""
Memory flow:
1. Save current user message
2. Fetch latest messages for user_id + conversation_id ORDER BY id DESC LIMIT 10
3. Reverse rows into chronological order
4. Build prompt with recent memory + current question + RAG context
5. Save assistant response
""")
    add_section(pdf, 9, "Voice Assistant Functionality", ["Voice input is lightweight chatbot mode. It uses continuous listening, interim transcripts, a manual Stop button, and 5-second silence detection. It sends only the final transcript to the chat API."], ["Does not generate full reports", "Asks 3-4 human-style follow-ups", "Summarizes responses", "Gives precautions, diet, hydration, rest, and doctor-visit preparation", "Escalates red flags calmly"])
    add_section(pdf, 10, "NLP Layer / Intent Understanding", ["The NLP layer runs before final response generation. It detects intent, symptoms, duration, severity, age, location, medicines, allergies, conditions, red flags, missing fields, and next action."], ["Intent examples: symptom_guidance, medicine_question, lab_report_question, diet_question, emergency_symptom, general_health_question, better_suggestion_info_request", "Example answer: I need symptom, duration, severity, age, existing conditions, current medicines, allergies, recent reports, and red flags."])
    add_section(pdf, 11, "RAG Pipeline", ["File upload goes through validation, extraction, cleaning, chunking, embedding, vector storage, metadata storage, retrieval, reranking, prompt building, LLM/rules answer generation, citations, and user-specific isolation."], ["Chunk size controls context granularity", "Overlap preserves boundary context", "top_k controls retrieval cost", "Similarity threshold reduces irrelevant context"])
    add_section(pdf, 12, "RAG Data Sources", ["Uploadable sources include lab reports, discharge summaries, prescriptions, health reports, allergy records, diagnosis history, diet plans, BP/sugar logs, synthetic patient files, and legal public demo datasets such as Synthea/MIMIC demo."], ["Markdown is good for clean text hierarchy", "JSON is good for structured lab/vitals data"])
    add_section(pdf, 13, "Report Generation Flow", ["User completes assessment, mandatory fields and consent are validated, triage/risk scoring runs, RAG context is retrieved, a base safety report is built, Gemini may enhance it, and the result is saved and downloadable as PDF."], ["Fail-closed if LLM enhancement fails", "Audit log records generation", "Doctor-ready questions and reminders included"])
    add_section(pdf, 14, "Safety and Guardrails", ["HealthGuard does not diagnose, prescribe, or recommend dosage. Safety rules refuse medication changes, escalate red flags, use calm wording, and avoid scary language."], ["Prompt injection prevention", "PHI/privacy protection", "Static disclaimer strategy", "Doctor consultation guidance"])
    add_section(pdf, 15, "User Memory and Chat History Isolation", ["Memory is needed for follow-ups but must be scoped. The app uses user_id and conversation_id, never mixes users, and does not mix old conversations unless opened."], ["Latest memory bug fix: save current message first", "Query latest rows DESC", "Reverse before LLM prompt", "Frontend active conversation stored per user"])
    pdf.code("""
SELECT role, content, created_at
FROM chat_messages
WHERE user_id = :user_id AND conversation_id = :conversation_id
ORDER BY id DESC
LIMIT 10;
messages = list(reversed(messages))
""")

    pdf.heading(16, "Database Design")
    pdf.table_text(["Table", "Purpose"], [
        ["users", "identity, email, role, verification"], ["sessions", "active login records"],
        ["email_verifications", "OTP and reset tokens"], ["patient_profiles", "demographics and lifestyle"],
        ["assessments", "structured health inputs"], ["reports", "generated report JSON and status"],
        ["chat_conversations", "conversation owner and metadata"], ["chat_messages", "role, content, sources, flags"],
        ["rag_documents", "uploaded/admin documents"], ["rag_chunks", "chunk text and embeddings"],
        ["knowledge_documents", "admin trusted knowledge"], ["audit_logs", "compliance events"],
        ["doctor_reviews", "review notes, status, signature"],
    ], [24, 68])

    pdf.heading(17, "API Design")
    pdf.table_text(["Endpoint", "Purpose"], [
        ["POST /api/auth/register", "Create user"], ["POST /api/auth/login", "Login"],
        ["POST /api/auth/verify-email", "Verify OTP"], ["GET /api/auth/sso/{provider}/start", "Start SSO"],
        ["GET /api/auth/sso/{provider}/callback", "SSO callback"], ["POST /api/reports/generate", "Generate report"],
        ["GET /api/reports", "List reports"], ["GET /api/reports/{id}", "Read report"],
        ["GET /api/reports/{id}/download", "Download PDF"], ["POST /api/chat/health-question", "Chatbot"],
        ["POST /api/documents/upload", "Upload/index document"], ["GET /api/health/rag", "RAG health"],
        ["POST /api/admin/knowledge", "Add knowledge"], ["GET /api/admin/knowledge", "List knowledge"],
        ["GET /api/doctor/reports/pending", "Doctor queue"], ["POST /api/doctor/reports/{id}/review", "Doctor review"],
        ["GET /api/health", "App health"], ["GET /api/health/db", "DB health"], ["GET /api/health/llm", "LLM health"],
    ], [40, 52])

    add_section(pdf, 18, "LLM Integration", ["LLM provider abstraction supports Gemini and OpenAI-ready providers. The LLM enhances structured safe output; it is not the primary safety engine. JSON response contracts, retries, token limits, and fail-closed behavior reduce risk."], [])
    add_section(pdf, 19, "Prompt Engineering", ["Prompts define system behavior, RAG context usage, concise chatbot answers, voice follow-ups, safety refusal, and JSON output. Prompt engineering prevents hallucination by constraining context and style."], [])
    add_section(pdf, 20, "Fine-Tuning vs Prompt Engineering", ["Prompt engineering changes instructions. Fine-tuning trains behavior. RAG supplies dynamic knowledge. Fine-tune repeated classifiers such as intent/safety/lab extraction, but do not fine-tune private patient records."], [])
    add_section(pdf, 21, "Handling Large File Uploads", ["For 5000 Excel files, save the file, create a job, enqueue with Redis/Celery, parse in workers using openpyxl read_only mode, batch insert rows, create RAG chunks, track progress, retry failures, and isolate users."], [])
    add_section(pdf, 22, "Async, Multithreading, and Multiprocessing", ["Async uses an event loop for I/O waits. Threads help blocking I/O. Multiprocessing handles CPU-heavy OCR/PDF parsing. HealthGuard can use async for LLM/DB calls, background threads for SMTP, and workers for OCR/Excel parsing."], [])
    add_section(pdf, 23, "Performance Optimization", ["Use async FastAPI, background workers, Redis caching, batch embeddings, metadata filters, top_k tuning, reranking, chunk optimization, smaller models for classification, larger models for final answers, token limits, streaming, and rate limiting."], [])
    add_section(pdf, 24, "Monitoring and Observability", ["Track API latency, P95 latency, error rate, token usage, cost/request, LLM latency, vector DB latency, RAG hit rate, hallucination rate, citation coverage, user feedback, queue length, and failed jobs."], ["OpenTelemetry", "Prometheus", "Grafana", "CloudWatch/Azure Monitor", "ELK/Datadog"])
    add_section(pdf, 25, "CI/CD Pipeline", ["Pipeline: linting, unit tests, integration tests, RAG evaluation, prompt regression tests, security scan, Docker build, deploy to dev, deploy to staging, manual approval, production deployment, smoke tests, rollback."], [])
    add_section(pdf, 26, "Testing Strategy", ["Tests cover auth, role guards, patient isolation, chat memory, latest question memory, RAG retrieval, prompt output, voice assistant, upload, report generation, LLM fail-closed, API health, and privacy flows."], [])
    add_section(pdf, 27, "Security and Privacy", ["Use auth, RBAC, user-specific records, patient-specific RAG chunks, no cross-user chat history, no personal Gmail in production, no-reply email with SPF/DKIM/DMARC, .env security, secret management, audit logs, PHI masking, and HTTPS."], [])
    add_section(pdf, 28, "Deployment", ["Local runs with Uvicorn. Production should use Docker, PostgreSQL, Redis, object storage, reverse proxy/HTTPS, ngrok for demo only, environment variables, health endpoints, backups, monitoring, and hardened auth/email setup."], [])
    add_section(pdf, 29, "Scenarios Implemented", ["Registration/email verification, login/dashboard, patient assessment, voice questions, chatbot short answer and follow-up mode, fever/rash, medication refusal, document upload/RAG indexing, report PDF, doctor review, admin knowledge, mobile menu, chat memory bug fix, and 5000 Excel upload design."], [])

    pdf.heading(30, "Interview Explanation")
    pdf.subheading("30-second explanation")
    pdf.paragraph("HealthGuard AI is a healthcare GenAI workspace that lets patients ask safe health questions, use voice, upload reports, complete assessments, and generate doctor-ready educational reports. It uses FastAPI, RAG, NLP intent understanding, user-specific memory, RBAC, and safety guardrails.")
    pdf.subheading("2-minute explanation")
    pdf.paragraph("The system includes a responsive dashboard, chatbot, voice assistant, document upload, RAG indexing, and report generation. The backend validates auth and consent, stores chat memory by user and conversation, runs NLP and safety checks, retrieves RAG context, and uses an LLM abstraction only when useful.")
    pdf.subheading("5-minute architecture explanation")
    pdf.paragraph("Start with browser flows: auth, dashboard, assessment, chat, voice, upload, and reports. FastAPI routes enforce user and role checks. Services handle chat/NLP/safety/RAG/LLM/report/PDF/storage. Uploaded documents become user-scoped chunks. Reports use triage, risk scoring, RAG context, optional Gemini enhancement, fail-closed behavior, audit logs, and PDF generation.")
    pdf.subheading("Senior Engineer / GenAI role")
    pdf.paragraph("As a Senior Engineer, emphasize modular architecture, testing, memory isolation, RBAC, performance, and production hardening. As a GenAI Developer, emphasize RAG, prompts, NLP extraction, safety guardrails, model abstraction, and evaluation.")

    pdf.heading(31, "Cross Questions and Answers")
    for i, (q, a) in enumerate(qa_pairs(), 1):
        pdf.ensure(42)
        pdf.text(f"{i}. {q}", MARGIN, pdf.y, 9.4, "F2", BLUE)
        pdf.y -= 13
        pdf.paragraph(a, 9.0, gap=5)

    add_section(pdf, 32, "Final Summary", ["HealthGuard AI is strong because it combines healthcare safety, RAG, voice, NLP intent understanding, memory isolation, role-based access, document processing, report generation, doctor review, audit logging, and regression testing. It is demo-ready and has a clear roadmap for PostgreSQL, pgvector/Qdrant, Redis/Celery, object storage, HTTPS, SIEM, secret managers, and formal compliance controls."], ["Explain it confidently from user workflow to backend architecture.", "Emphasize that LLM is not the safety engine.", "Tie every design decision to safety, scalability, maintainability, or user trust."])

    pdf.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
