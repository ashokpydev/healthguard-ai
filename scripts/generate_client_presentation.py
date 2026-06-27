from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


OUT = Path("outputs/HealthGuard_AI_Client_Architecture_Demo.pptx")
LOGO = Path("frontend/assets/healthguard-logo.png")
EMU = 9525
SLIDE_W = 12192000
SLIDE_H = 6858000

COLORS = {
    "navy": "0B2D5C",
    "blue": "2563EB",
    "cyan": "06B6D4",
    "teal": "0F766E",
    "green": "10B981",
    "orange": "F97316",
    "pink": "EC4899",
    "purple": "7C3AED",
    "slate": "334155",
    "muted": "64748B",
    "line": "CBD5E1",
    "card": "FFFFFF",
    "pale_blue": "E0F2FE",
    "pale_green": "DCFCE7",
    "pale_orange": "FFEDD5",
    "pale_purple": "EDE9FE",
}


def px(value: float) -> int:
    return int(round(value * EMU))


def rgb(color: str) -> str:
    return COLORS.get(color, color).replace("#", "").upper()


def safe(text: object) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    value = str(text)
    for old, new in replacements.items():
        value = value.replace(old, new)
    return escape(value, {'"': "&quot;"})


class Slide:
    def __init__(self, title: str | None = None, subtitle: str | None = None, section: str | None = None, dark: bool = False) -> None:
        self.items: list[str] = []
        self.rels: list[tuple[str, str]] = []
        self.next_id = 2
        self.bg_dark() if dark else self.bg_light()
        if title:
            self.add_header(title, subtitle, section)
        self.footer()

    def new_id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def solid_fill(self, color: str) -> str:
        return f'<a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>'

    def line_xml(self, color: str = "line", width: float = 1) -> str:
        if width <= 0 or color == "none":
            return "<a:ln><a:noFill/></a:ln>"
        return f'<a:ln w="{int(width * 12700)}"><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill></a:ln>'

    def bg_light(self) -> None:
        self.rect(0, 0, 1280, 720, "F7FBFF", "F7FBFF", 0, radius=False, name="background")
        self.rect(-150, 530, 860, 260, "DBEAFE", "DBEAFE", 0, name="blue-wave")
        self.rect(575, 470, 860, 320, "FED7AA", "FED7AA", 0, name="orange-wave")
        self.rect(925, -48, 460, 190, "CCFBF1", "CCFBF1", 0, name="cyan-wave")

    def bg_dark(self) -> None:
        self.rect(0, 0, 1280, 720, "0B2D5C", "0B2D5C", 0, radius=False, name="background")
        self.rect(-30, 420, 820, 320, "1D4ED8", "1D4ED8", 0, name="blue-band")
        self.rect(510, 430, 840, 330, "F97316", "F97316", 0, name="orange-band")
        self.rect(860, -70, 480, 240, "22D3EE", "22D3EE", 0, name="cyan-glow")

    def rect(self, x: float, y: float, w: float, h: float, fill: str = "card", line: str = "line", lw: float = 1, radius: bool = True, name: str = "shape") -> None:
        shape_id = self.new_id()
        geom = "roundRect" if radius else "rect"
        self.items.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{safe(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{px(x)}" y="{px(y)}"/><a:ext cx="{px(w)}" cy="{px(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{self.solid_fill(fill)}{self.line_xml(line, lw)}</p:spPr></p:sp>'
        )

    def text(self, x: float, y: float, w: float, h: float, text: str, size: float = 16, color: str = "slate", bold: bool = False, align: str = "l", fill: str = "none") -> None:
        shape_id = self.new_id()
        fill_xml = "<a:noFill/>" if fill == "none" else self.solid_fill(fill)
        paragraphs = []
        for line in str(text).split("\n"):
            paragraphs.append(
                f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="en-US" sz="{int(size * 100)}" b="{1 if bold else 0}">'
                f'<a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>{safe(line)}</a:t></a:r></a:p>'
            )
        self.items.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{px(x)}" y="{px(y)}"/><a:ext cx="{px(w)}" cy="{px(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill_xml}{self.line_xml("none", 0)}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" lIns="{px(2)}" tIns="{px(2)}" rIns="{px(2)}" bIns="{px(2)}"/><a:lstStyle/>{"".join(paragraphs)}</p:txBody></p:sp>'
        )

    def logo(self, x: float, y: float, size: float) -> None:
        if not LOGO.exists():
            return
        shape_id = self.new_id()
        rid = f"rId{len(self.rels) + 1}"
        self.rels.append((rid, "../media/healthguard-logo.png"))
        self.items.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{shape_id}" name="HealthGuard AI logo"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr><a:xfrm><a:off x="{px(x)}" y="{px(y)}"/><a:ext cx="{px(size)}" cy="{px(size)}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        )

    def add_header(self, title: str, subtitle: str | None, section: str | None) -> None:
        self.logo(50, 30, 46)
        self.text(106, 34, 410, 30, "HealthGuard AI", 20, "navy", True)
        self.text(108, 63, 370, 22, "Clinical safety workspace", 11, "slate")
        if section:
            self.text(54, 108, 240, 20, section.upper(), 11, "purple", True)
        self.text(54, 132, 850, 54, title, 30, "navy", True)
        if subtitle:
            self.text(56, 190, 880, 48, subtitle, 14, "slate")

    def footer(self) -> None:
        self.text(54, 682, 380, 18, "HealthGuard AI architecture demo", 8.5, "muted")
        self.text(1048, 682, 180, 18, "Generated: 2026-06-25", 8.5, "muted", align="r")

    def card(self, x: float, y: float, w: float, h: float, title: str, body: str | list[str] | None, accent: str = "blue", fill: str = "card") -> None:
        self.rect(x, y, w, h, fill, "line", 1, True, "card")
        self.rect(x, y, 8, h, accent, accent, 0, False, "accent")
        self.text(x + 24, y + 18, w - 40, 30, title, 17, "navy", True)
        if body:
            content = "\n".join(f"- {item}" for item in body) if isinstance(body, list) else body
            self.text(x + 24, y + 56, w - 40, h - 66, content, 12.5, "slate")

    def pill(self, x: float, y: float, w: float, h: float, text: str, fill: str, color: str) -> None:
        self.rect(x, y, w, h, fill, fill, 0, True, "pill")
        self.text(x + 8, y + 8, w - 16, h - 10, text, 11, color, True, align="c")

    def arrow(self, x1: float, y1: float, x2: float, y2: float, color: str = "blue") -> None:
        shape_id = self.new_id()
        left, top = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1) or 1, abs(y2 - y1) or 1
        flip_h = ' flipH="1"' if x2 < x1 else ""
        flip_v = ' flipV="1"' if y2 < y1 else ""
        self.items.append(
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="arrow"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            f'<p:spPr><a:xfrm{flip_h}{flip_v}><a:off x="{px(left)}" y="{px(top)}"/><a:ext cx="{px(w)}" cy="{px(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom><a:ln w="19050"><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill><a:tailEnd type="triangle"/></a:ln></p:spPr></p:cxnSp>'
        )

    def xml(self) -> str:
        tree = (
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            + "".join(self.items)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f"<p:cSld><p:spTree>{tree}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )


def build_slides() -> list[Slide]:
    slides: list[Slide] = []

    s = Slide(dark=True)
    s.logo(72, 54, 74)
    s.text(162, 58, 520, 42, "HealthGuard AI", 30, "card", True)
    s.text(166, 100, 500, 26, "Client Architecture & Professional Demo", 16, "E0F2FE")
    s.text(78, 214, 780, 118, "Safety-first preventive\nhealth intelligence platform", 42, "card", True)
    s.text(82, 350, 780, 70, "FastAPI | Gemini LLM | Local RAG | Role-based workflows | PostgreSQL-ready persistence", 18, "E0F2FE")
    s.card(880, 190, 310, 250, "Demo promise", ["Verified access before dashboard", "Patient-isolated reports and documents", "LLM-backed report generation with fail-closed behavior", "Editable architecture and implementation traceability"], "cyan", "E0F2FE")
    s.pill(82, 450, 180, 38, "Client demo deck", "pale_green", "teal")
    s.pill(276, 450, 200, 38, "Architecture included", "pale_orange", "orange")
    slides.append(s)

    s = Slide("Executive Overview", "What HealthGuard AI delivers for patients, doctors, admins, and compliance teams.", "Overview")
    cards = [
        ("Product goal", "Collect patient lifestyle, diet, symptoms, climate, occupation, and optional documents, then generate educational preventive health-risk reports.", "blue"),
        ("Safety posture", "Rules detect risk and red flags first; Gemini enhances language only after deterministic safety checks and RAG context.", "green"),
        ("Trust boundary", "Backend enforces sessions, email verification, role access, patient report ownership, and RAG document isolation.", "purple"),
        ("Demo readiness", "Includes auth, SSO path, report generation, document upload, RAG retrieval, saved reports, PDF download, and review workflow.", "orange"),
    ]
    for i, (title, body, color) in enumerate(cards):
        s.card(62 + i * 296, 250, 270, 180, title, body, color)
    s.text(92, 478, 1050, 110, "- Not a diagnosis or prescription system; output is educational and doctor-consultation oriented.\n- If LLM generation fails, report creation fails closed and no report is saved.\n- PostgreSQL is supported through DATABASE_URL; SQLite remains available for local fallback.", 15, "slate")
    slides.append(s)

    s = Slide("Capability Map", "End-to-end feature areas implemented in the current HealthGuard AI application.", "Scope")
    capabilities = [
        ("Access & Identity", ["Registration/login", "6-digit email confirmation", "Google SSO callback path", "Role-aware sessions"], "blue"),
        ("Patient Workspace", ["Guided assessment", "Optional document upload", "Generated report at page bottom", "Saved report pagination"], "teal"),
        ("AI & Safety", ["Triage rules", "Risk scoring", "Gemini enhancement", "Medication/prescription refusal"], "green"),
        ("RAG & Data", ["Document extraction", "Chunking with overlap", "Local embeddings", "Cosine retrieval + isolation"], "purple"),
        ("Clinical Review", ["Doctor queues", "Patient folders", "Review status/comments", "PDF download"], "orange"),
        ("Governance", ["Audit logs", "Admin knowledge upload", "Health checks", "Tracking documentation"], "pink"),
    ]
    for i, (title, body, color) in enumerate(capabilities):
        s.card(60 + (i % 3) * 400, 242 + (i // 3) * 185, 350, 145, title, body, color)
    slides.append(s)

    s = Slide("System Architecture", "Editable high-level architecture diagram showing runtime boundaries and integrations.", "Architecture")
    boxes = [
        (70, 265, 160, 70, "Browser UI\nHTML/CSS/JS", "blue"),
        (300, 265, 170, 70, "FastAPI\nAPI routes", "teal"),
        (540, 160, 180, 64, "Auth & RBAC\nEmail + SSO", "purple"),
        (540, 250, 180, 64, "Report Engine\nRules + Gemini", "green"),
        (540, 340, 180, 64, "Document/RAG\nChunk + retrieve", "orange"),
        (800, 160, 170, 64, "Database\nPostgreSQL/SQLite", "blue"),
        (800, 250, 170, 64, "Gemini API\nLLM output", "green"),
        (800, 340, 170, 64, "SMTP\nEmail code", "pink"),
        (1030, 250, 150, 64, "PDF Service\nDownload", "orange"),
    ]
    for x, y, w, h, title, color in boxes:
        s.card(x, y, w, h, title, None, color)
    for args in [(230, 300, 300, 300), (470, 300, 540, 192), (470, 300, 540, 282), (470, 300, 540, 372), (720, 192, 800, 192), (720, 282, 800, 282), (720, 372, 800, 372), (970, 282, 1030, 282)]:
        s.arrow(*args, "blue")
    s.text(74, 470, 1070, 60, "Key principle: the browser is a UX layer; identity, authorization, patient isolation, report creation, RAG retrieval, and persistence are enforced by backend routes and services.", 16, "navy", True)
    slides.append(s)

    s = Slide("Backend Layered Architecture", "How responsibilities are separated for maintainability and safer health workflows.", "Architecture")
    layers = [
        ("API Routes", "backend/app/api/routes.py - request validation, session checks, role guards, HTTP errors", "blue"),
        ("Schemas", "backend/app/schemas/health.py - Pydantic request/response models and mandatory field validation", "teal"),
        ("Domain Services", "backend/app/services/* - auth, triage, risk, guidance, report, LLM, RAG, documents, PDF, storage", "green"),
        ("Database Adapter", "backend/app/db/store.py - SQLite/PostgreSQL abstraction, schema creation, row helpers", "purple"),
        ("External Services", ".env configured - Gemini, SMTP, Google OAuth, public tunnel when needed", "orange"),
    ]
    for i, (title, body, color) in enumerate(layers):
        y = 210 + i * 78
        s.card(100, y, 1080, 58, title, body, color)
        if i < 4:
            s.arrow(640, y + 58, 640, y + 78, color)
    slides.append(s)

    s = Slide("Authentication & Registration Flow", "Verified identity is required before users can enter the dashboard or access features.", "Access")
    steps = [
        ("1 Register", "Validate email format, role, password, and profile fields", "blue"),
        ("2 Email delivery", "Create 6-digit code and send through SMTP; if SMTP fails, registration fails", "cyan"),
        ("3 Confirm code", "User submits code in popup; account becomes email_verified", "green"),
        ("4 Login / SSO", "Password login or Google OAuth maps to local user/session", "purple"),
        ("5 Dashboard access", "Session token unlocks role-specific UI and protected APIs", "orange"),
    ]
    for i, (title, body, color) in enumerate(steps):
        x = 58 + i * 238
        s.card(x, 250, 205, 150, title, body, color)
        if i < 4:
            s.arrow(x + 205, 325, x + 238, 325, "blue")
    s.text(78, 465, 1080, 90, "- Dashboard routes reject missing sessions; login rejects unverified email.\n- Google SSO validates Google userinfo and creates/updates the local verified user.\n- Facebook and Instagram buttons are scaffolded; production requires provider credentials/callbacks.", 15, "slate")
    slides.append(s)

    s = Slide("Role-Based Experience", "Each role gets only the features it needs; patient data is isolated at API/storage level.", "Access")
    roles = [
        ("Patient", ["Create own reports", "Upload own docs", "View/download own reports", "No role-tools tab"], "blue"),
        ("Doctor / Dietician", ["Pending review queue", "Patient folders", "Review status/comments", "Clinical notes"], "green"),
        ("Admin", ["Approved knowledge upload", "Knowledge listing", "System configuration visibility"], "purple"),
        ("Compliance", ["Audit-log visibility", "Governance review", "Activity traceability"], "orange"),
    ]
    for i, (title, body, color) in enumerate(roles):
        s.card(80 + i * 300, 240, 260, 250, title, body, color)
    s.text(100, 540, 1020, 44, "Security design: frontend hiding is only convenience; backend routes and storage queries enforce role and ownership rules.", 17, "navy", True)
    slides.append(s)

    s = Slide("Patient Assessment Data Collection", "The report is generated only after mandatory patient inputs and consent are provided.", "Data")
    assessment_cards = [
        ("Identity & profile", ["Age, gender", "Height, weight, BMI", "Location and climate", "Occupation"], "blue"),
        ("Lifestyle factors", ["Sleep hours", "Exercise level", "Water intake", "Smoking and alcohol", "Diet pattern + food catalog"], "teal"),
        ("Clinical context", ["Main symptom", "Severity and duration", "Existing conditions", "Family history", "Medications, allergies"], "green"),
        ("Optional context", ["Uploaded PDFs/DOCX/text", "Extracted document summary", "Patient-owned RAG chunks"], "purple"),
    ]
    for i, (title, body, color) in enumerate(assessment_cards):
        s.card(70 + i * 300, 235, 270 if i < 3 else 230, 260, title, body, color)
    s.text(84, 535, 1060, 44, "No default patient data is used for final reports. Mandatory fields must be entered by the user before report generation.", 16, "navy", True)
    slides.append(s)

    s = Slide("Report Generation Flow", "Rules, RAG, and Gemini work together; failure behavior is explicit and safe.", "AI Flow")
    flow = [
        ("Validate session\n+ consent", "blue"),
        ("Validate mandatory\nassessment fields", "cyan"),
        ("Triage red flags\n+ score risk", "green"),
        ("Retrieve RAG\ncontext", "purple"),
        ("Build base\nsafety report", "orange"),
        ("Gemini JSON\nenhancement", "pink"),
        ("Save report\n+ audit log", "teal"),
    ]
    for i, (title, color) in enumerate(flow):
        x = 50 + i * 172
        s.card(x, 260, 145, 105, title, None, color)
        if i < 6:
            s.arrow(x + 145, 312, x + 172, 312, color)
    s.text(86, 430, 1050, 105, "- Deterministic services own red flags, scoring, precautions, and doctor-consultation guidance.\n- Gemini enhances the report with educational summary, doctor questions, reminders, and extra safe precautions.\n- If Gemini is configured but fails, HTTP 503 is returned and no report is persisted.", 15, "slate")
    slides.append(s)

    s = Slide("RAG Pipeline Architecture", "Uploaded patient documents and admin knowledge become retrievable context for report/chat generation.", "RAG")
    steps = [
        ("Upload file", "PDF/DOCX/TXT/CSV/JSON bytes received", "blue"),
        ("Extract & tune", "Decode text, normalize whitespace, summarize, redact secret-like values", "teal"),
        ("Chunk", "140-word chunks with 30-word overlap", "green"),
        ("Embed", "128-dimension deterministic local hashing vectors", "purple"),
        ("Store", "rag_documents + rag_chunks embedding_json", "orange"),
        ("Retrieve", "Cosine similarity over global + user-owned chunks", "pink"),
        ("Prompt Gemini", "Send top ranked excerpts, not entire raw file", "cyan"),
    ]
    for i, (title, body, color) in enumerate(steps):
        x = 60 + (i % 4) * 300
        y = 230 + (i // 4) * 180
        s.card(x, y, 250, 130, title, body, color)
        if i < 6 and i % 4 != 3:
            s.arrow(x + 250, y + 65, x + 300, y + 65, "blue")
    s.arrow(960, 295, 60, 475, "blue")
    s.text(72, 612, 1050, 38, "Isolation rule: patient documents are stored with user_id; retrieval allows global knowledge plus only the current user's chunks.", 15, "navy", True)
    slides.append(s)

    s = Slide("Gemini LLM Integration", "LLM is used as an enhancement layer, not the primary safety engine.", "AI")
    s.card(84, 235, 300, 230, "Provider configuration", ["LLM_PROVIDER=gemini", "GEMINI_API_KEY required", "Primary: gemini-2.5-flash", "Fallback: gemini-2.5-flash-lite"], "blue")
    s.card(430, 235, 360, 230, "Prompt contract", ["Structured JSON response requested", "No diagnosis, prescription, or dosage changes", "Emergency escalation instruction", "Use RAG only as supporting context"], "green")
    s.card(836, 235, 320, 230, "Reliability behavior", ["Retries transient 429/5xx/network failures", "Fallback model attempts", "Detailed 503 error if all attempts fail", "No silent rules-only save on failure"], "orange")
    s.text(110, 520, 1000, 58, "Client message: AI output is bounded by deterministic safety logic and transparent failure handling.", 22, "navy", True, align="c")
    slides.append(s)

    s = Slide("Database Architecture", "Core persistence model for users, sessions, reports, RAG, knowledge, and audits.", "Data")
    entities = [
        ("users", "sessions\npatient_profiles\nrag_documents", 80, 240, "blue"),
        ("patient_profiles", "assessments\nreports", 370, 240, "teal"),
        ("reports", "doctor review\nPDF download", 650, 240, "green"),
        ("knowledge_documents", "global RAG seed", 930, 240, "purple"),
        ("rag_documents", "rag_chunks\nembedding_json", 250, 460, "orange"),
        ("audit_logs", "registration\nlogin\nreport\nupload\nreview", 650, 460, "pink"),
    ]
    for title, body, x, y, color in entities:
        s.card(x, y, 230, 130, title, body, color)
    for args in [(310, 275, 370, 275), (600, 275, 650, 275), (1045, 370, 365, 460), (195, 370, 250, 460), (765, 370, 765, 460)]:
        s.arrow(*args, "blue")
    s.text(84, 610, 1070, 34, "Database support: PostgreSQL through DATABASE_URL, SQLite fallback for local/demo. Production recommendation: PostgreSQL + Alembic + pgvector.", 14, "navy", True)
    slides.append(s)

    s = Slide("Patient Privacy & Data Isolation", "Patient X must never see Patient Y data; isolation is implemented in backend storage queries.", "Security")
    s.card(80, 250, 300, 210, "Report isolation", ["patient_profiles.user_id binds reports to owner", "Patient report list filters by logged-in user", "Download endpoint checks ownership", "Elevated roles use explicit review paths"], "blue")
    s.card(490, 250, 300, 210, "RAG isolation", ["rag_documents.user_id stores document owner", "Retrieval permits global + current user chunks", "Patient uploaded content is not shared across patients"], "purple")
    s.card(900, 250, 280, 210, "Role controls", ["require_user for protected APIs", "require_role for doctor/admin/compliance", "UI hiding is not trusted as security"], "green")
    s.text(120, 535, 1000, 44, "Trust boundary: authorization and privacy are enforced server-side before returning any report, document context, or review data.", 18, "navy", True, align="c")
    slides.append(s)

    s = Slide("API Surface", "Main endpoints used by the frontend and demo workflows.", "API")
    api_cols = [
        ("Auth", ["POST /api/auth/register", "POST /api/auth/login", "POST /api/auth/verify-email", "GET /api/auth/sso/{provider}/start", "GET /api/auth/sso/{provider}/callback"]),
        ("Reports", ["POST /api/reports/generate", "GET /api/reports", "GET /api/reports/{id}", "GET /api/reports/{id}/download", "POST /api/chat/health-question"]),
        ("Documents & RAG", ["POST /api/documents/upload", "GET /api/health/rag", "POST /api/admin/knowledge", "GET /api/admin/knowledge"]),
        ("Review & Health", ["GET /api/doctor/reports/pending", "POST /api/doctor/reports/{id}/review", "GET /api/health", "GET /api/health/db", "GET /api/health/llm"]),
    ]
    for i, (title, body) in enumerate(api_cols):
        s.card(60 + i * 300, 230, 270, 340, title, body, ["blue", "green", "purple", "orange"][i])
    slides.append(s)

    s = Slide("Client Demo Journey", "Recommended walkthrough path for demonstrating the product end to end.", "Demo")
    journey = [
        ("1 Secure access", "Register or login, verify email code, or use Google SSO when configured", "blue"),
        ("2 Intake", "Enter mandatory health, lifestyle, diet, and symptom details", "teal"),
        ("3 Optional documents", "Upload lab notes or reports; extracted text is indexed into patient-owned RAG", "purple"),
        ("4 Generate report", "Show LLM-backed generated report at bottom of page and saved reports separately", "green"),
        ("5 Review/download", "Doctor reviews pending reports; patient downloads own PDF", "orange"),
    ]
    for i, (title, body, color) in enumerate(journey):
        s.card(100, 210 + i * 82, 980, 58, title, body, color)
    slides.append(s)

    s = Slide("Document Extraction & Processing", "How uploaded files become safe, searchable report context.", "Documents")
    s.card(80, 230, 260, 230, "Supported today", ["Text-like files: txt, md, csv, json", "DOCX via document XML", "Basic text PDFs", "Upload is optional"], "blue")
    s.card(390, 230, 300, 230, "Processing steps", ["Extract raw text", "Normalize/tune for retrieval", "Summarize for UI", "Index into RAG chunks", "Use only top retrieved excerpts"], "green")
    s.card(750, 230, 360, 230, "Production upgrades", ["OCR for scanned PDFs/images", "Table extraction for labs", "Lab value normalization", "Extraction confidence scoring", "Manual review for low confidence"], "orange")
    s.text(110, 520, 1000, 42, "Important: current pipeline is suitable for demo/local use; production medical files need OCR, structured parsing, validation, and quality gates.", 16, "navy", True, align="c")
    slides.append(s)

    s = Slide("Testing & Verification Strategy", "Acceptance tests cover the behaviors most important for a health AI demo.", "Quality")
    s.card(78, 230, 330, 250, "Automated tests", ["Auth registration/login/email verification", "Mandatory assessment validation", "Report generation and LLM test mode", "Document upload and RAG retrieval", "Patient report/privacy isolation", "Doctor/admin role guards"], "blue")
    s.card(478, 230, 330, 250, "Manual verification", ["Health endpoints", "Google SSO connectivity checks", "SMTP error reporting", "Generated report placement", "Pagination and UI flows"], "green")
    s.card(878, 230, 300, 250, "Current status", ["20 acceptance tests passing", "Backend syntax checks used", "Frontend JS syntax checks used", "Living TRACK.md maintained"], "purple")
    s.text(92, 535, 1060, 36, "Testing focus: prove access control, isolation, and fail-closed behavior rather than only checking happy-path UI rendering.", 16, "navy", True)
    slides.append(s)

    s = Slide("Deployment & Configuration", "How the application runs locally and how it can be exposed for demo.", "Deployment")
    s.card(70, 230, 300, 230, "Local runtime", ["FastAPI app served by Uvicorn", "Static UI at /", "Default local port used: 8001", "API docs available through FastAPI"], "blue")
    s.card(405, 230, 310, 230, "Configuration", ["DATABASE_URL for PostgreSQL", "SMTP_HOST/PORT/USERNAME/PASSWORD", "GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI", "GEMINI_API_KEY + model settings"], "purple")
    s.card(750, 230, 360, 230, "Public demo URL", ["ngrok tunnel can expose local app", "Google redirect URI must match public domain", "Never print secrets in logs or slides", "Use HTTPS/reverse proxy for production"], "orange")
    s.text(96, 520, 1030, 46, "Production path: Dockerized FastAPI behind HTTPS, PostgreSQL, pgvector, secret manager, observability, rate limits, and background workers.", 16, "navy", True, align="c")
    slides.append(s)

    s = Slide("Security, Safety & Governance Controls", "Controls already included and controls recommended for production hardening.", "Governance")
    s.card(80, 230, 310, 250, "Implemented controls", ["Verified login before dashboard", "Role guards on protected APIs", "Patient report/document isolation", "No report saved when LLM fails", "Medication/prescription refusal", "Audit logs for key actions"], "green")
    s.card(475, 230, 310, 250, "Safety language", ["Not a diagnosis system", "No prescriptions or dosage changes", "Emergency symptoms escalated", "Doctor consultation encouraged", "Uploaded context treated as user-provided support"], "blue")
    s.card(870, 230, 310, 250, "Production hardening", ["PHI encryption at rest", "OIDC/JWT session hardening", "Virus scanning for uploads", "Rate limiting and abuse protection", "Central logs/metrics/traces"], "orange")
    slides.append(s)

    s = Slide("Roadmap & Client Demo Close", "What is demo-ready now and what should be upgraded for production launch.", "Roadmap")
    s.card(70, 230, 340, 255, "Demo-ready now", ["Authentication + email verification", "Role-based dashboard", "Gemini-backed reports", "Local RAG pipeline", "Saved reports + PDF", "Doctor review workflow"], "green")
    s.card(470, 230, 340, 255, "Next engineering milestones", ["PostgreSQL migrations with Alembic", "pgvector or dedicated vector DB", "Production embeddings", "OCR and lab parser", "Background jobs for file ingestion"], "blue")
    s.card(870, 230, 310, 255, "Client value", ["Preventive health awareness", "Safer AI guardrails", "Traceable reports", "Role-specific collaboration", "Clear production path"], "purple")
    s.text(110, 548, 1000, 58, "Closing message: HealthGuard AI is designed as a safety-first GenAI health assistant where deterministic rules, private RAG context, and Gemini work together under backend-enforced trust boundaries.", 18, "navy", True, align="c")
    slides.append(s)

    return slides


def write_deck(slides: list[Slide]) -> None:
    OUT.parent.mkdir(exist_ok=True)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        + "".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, len(slides) + 1))
        + "</Types>"
    )
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>'
    pres_rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    pres_rels.extend(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, len(slides) + 1))
    pres_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(pres_rels) + "</Relationships>"
    slide_ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, len(slides) + 1))
    presentation_xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{slide_ids}</p:sldIdLst><p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="screen4x3"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:defaultTextStyle></p:presentation>'
    master_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'
    master_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>'
    layout_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
    layout_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'
    theme_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="HealthGuard AI"><a:themeElements><a:clrScheme name="HealthGuard"><a:dk1><a:srgbClr val="0B2D5C"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="334155"/></a:dk2><a:lt2><a:srgbClr val="F8FAFC"/></a:lt2><a:accent1><a:srgbClr val="2563EB"/></a:accent1><a:accent2><a:srgbClr val="06B6D4"/></a:accent2><a:accent3><a:srgbClr val="10B981"/></a:accent3><a:accent4><a:srgbClr val="F97316"/></a:accent4><a:accent5><a:srgbClr val="7C3AED"/></a:accent5><a:accent6><a:srgbClr val="EC4899"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme><a:fontScheme name="Aptos"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle/></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'

    with ZipFile(OUT, "w", ZIP_DEFLATED) as deck:
        deck.writestr("[Content_Types].xml", content_types)
        deck.writestr("_rels/.rels", root_rels)
        deck.writestr("ppt/presentation.xml", presentation_xml)
        deck.writestr("ppt/_rels/presentation.xml.rels", pres_rels_xml)
        deck.writestr("ppt/slideMasters/slideMaster1.xml", master_xml)
        deck.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        deck.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml)
        deck.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        deck.writestr("ppt/theme/theme1.xml", theme_xml)
        if LOGO.exists():
            deck.write(LOGO, "ppt/media/healthguard-logo.png")
        for index, slide in enumerate(slides, start=1):
            deck.writestr(f"ppt/slides/slide{index}.xml", slide.xml())
            rels = "".join(
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>'
                for rid, target in slide.rels
            )
            deck.writestr(
                f"ppt/slides/_rels/slide{index}.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                + rels
                + "</Relationships>",
            )


if __name__ == "__main__":
    slides = build_slides()
    write_deck(slides)
    print(OUT.resolve())
    print(OUT.stat().st_size)
    print(len(slides))
