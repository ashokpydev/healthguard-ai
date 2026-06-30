from __future__ import annotations

from pathlib import Path
from textwrap import wrap


PAGE_W = 842
PAGE_H = 595
OUT = Path("output/pdf/HealthGuard_AI_Project_Architecture.pdf")


class SimplePdf:
    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.current: list[str] = []

    def new_page(self, title: str, subtitle: str | None = None) -> None:
        if self.current:
            self.pages.append(self.current)
        self.current = [
            "0.96 0.98 1 rg 0 0 842 595 re f",
            "0.04 0.22 0.44 rg 0 542 842 53 re f",
            "0.10 0.72 0.70 rg 0 538 842 4 re f",
            "1 1 1 rg BT /F2 22 Tf 36 562 Td ({}) Tj ET".format(self.esc(title)),
        ]
        if subtitle:
            self.text(36, 546, subtitle, size=9, color=(0.91, 0.97, 1))

    def text(self, x: float, y: float, value: str, size: int = 10, bold: bool = False, color=(0.08, 0.12, 0.22)) -> None:
        r, g, b = color
        font = "F2" if bold else "F1"
        self.current.append(f"{r} {g} {b} rg BT /{font} {size} Tf {x} {y} Td ({self.esc(value)}) Tj ET")

    def paragraph(self, x: float, y: float, text: str, width: int = 90, size: int = 10, leading: int = 14) -> float:
        for line in wrap(text, width=width):
            self.text(x, y, line, size=size)
            y -= leading
        return y

    def bullet_list(self, x: float, y: float, items: list[str], width: int = 78, size: int = 9) -> float:
        for item in items:
            lines = wrap(item, width=width)
            if not lines:
                continue
            self.text(x, y, "- " + lines[0], size=size)
            y -= 12
            for extra in lines[1:]:
                self.text(x + 10, y, extra, size=size)
                y -= 12
            y -= 2
        return y

    def box(self, x: float, y: float, w: float, h: float, title: str, body: list[str], fill=(1, 1, 1), stroke=(0.60, 0.74, 0.88)) -> None:
        fr, fg, fb = fill
        sr, sg, sb = stroke
        self.current.append(f"{fr} {fg} {fb} rg {x} {y} {w} {h} re f")
        self.current.append(f"{sr} {sg} {sb} RG {x} {y} {w} {h} re S")
        self.text(x + 8, y + h - 18, title, size=10, bold=True, color=(0.03, 0.20, 0.42))
        ty = y + h - 34
        for line in body:
            for wrapped in wrap(line, width=max(18, int(w / 5.2))):
                self.text(x + 8, ty, wrapped, size=7, color=(0.16, 0.22, 0.32))
                ty -= 9

    def line(self, x1: float, y1: float, x2: float, y2: float, label: str | None = None) -> None:
        self.current.append(f"0.10 0.38 0.65 RG 1.2 w {x1} {y1} m {x2} {y2} l S")
        if label:
            self.text((x1 + x2) / 2 - 24, (y1 + y2) / 2 + 4, label, size=7, color=(0.08, 0.20, 0.34))

    def finish(self) -> bytes:
        if self.current:
            self.pages.append(self.current)
            self.current = []
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
        page_refs = []
        for index, page in enumerate(self.pages, start=1):
            footer = [
                "0.63 0.72 0.82 RG 36 30 770 1 re S",
                f"0.34 0.39 0.46 rg BT /F1 8 Tf 36 16 Td (HealthGuard AI architecture - page {index} of {len(self.pages)}) Tj ET",
            ]
            stream = "\n".join(page + footer).encode("latin-1", errors="replace")
            page_id = len(objects) + 1
            content_id = len(objects) + 2
            page_refs.append(f"{page_id} 0 R")
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>".encode(
                    "ascii"
                )
            )
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(self.pages)} >>".encode("ascii")
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
        return bytes(pdf)

    def esc(self, value: str) -> str:
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf() -> bytes:
    pdf = SimplePdf()

    pdf.new_page("HealthGuard AI Project Architecture", "Client-ready system architecture, data flow, security, RAG, LLM, and compliance overview")
    y = 500
    y = pdf.paragraph(
        42,
        y,
        "HealthGuard AI is a preventive health intelligence workspace. Patients complete guided assessments, upload optional health documents, use voice intake, and generate educational reports. Doctors and dieticians review patient reports with assignment, comments, signatures, status lifecycle, and patient notifications. Admin and compliance users manage knowledge and audit visibility.",
        width=112,
        size=11,
        leading=15,
    )
    pdf.box(44, 300, 180, 120, "Implemented Stack", ["FastAPI + Uvicorn", "HTML, CSS, JavaScript, Bootstrap", "PostgreSQL with SQLite fallback", "Gemini LLM, Hugging Face ASR", "RAG with pgvector-ready embeddings"], fill=(0.91, 0.97, 1))
    pdf.box(252, 300, 180, 120, "Core Capabilities", ["Verified auth and RBAC", "Assessment, risk, diet, activity", "Document extraction and RAG", "Doctor review workflow", "PDF reports and versioning"], fill=(0.94, 1, 0.97))
    pdf.box(460, 300, 180, 120, "Compliance Controls", ["Consent records", "Privacy export and deletion", "Encrypted PHI payloads", "Audit hash chain", "Security headers"], fill=(1, 0.96, 0.91))
    pdf.box(668, 300, 120, 120, "Current Status", ["Demo ready: about 85%", "Production: about 60%", "Healthcare compliance: about 60%"], fill=(0.98, 0.95, 1))
    pdf.text(42, 250, "Architecture Goals", size=14, bold=True)
    pdf.bullet_list(
        52,
        228,
        [
            "Keep patient data isolated by authenticated user at API and storage layers.",
            "Use deterministic safety and risk scoring before LLM enhancement.",
            "Retrieve only relevant global and user-owned RAG chunks for reports and chat.",
            "Fail closed when live LLM report generation is configured but unavailable.",
            "Maintain audit, consent, report versioning, and privacy controls for pilot compliance readiness.",
        ],
        width=120,
    )

    pdf.new_page("End-to-End Architecture Diagram", "Major deployable layers and information flow")
    boxes = {
        "Clients": (34, 400, 135, 92, ["Patient browser/mobile", "Doctor dashboard", "Admin/compliance"]),
        "FastAPI Gateway": (204, 400, 135, 92, ["Static UI", "API router", "Security headers"]),
        "Core Services": (374, 380, 170, 125, ["Auth/RBAC", "Assessment/risk", "Document/RAG", "Report/doctor", "Compliance/privacy"]),
        "Data Stores": (594, 400, 190, 92, ["PostgreSQL", "SQLite fallback", "RAG/pgvector", "Audit/consent"]),
        "External APIs": (594, 245, 190, 92, ["Gemini LLM", "Hugging Face ASR", "SMTP", "Google OAuth"]),
        "Outputs": (374, 220, 170, 92, ["Saved report", "Branded PDF", "Doctor notifications", "Privacy export"]),
    }
    colors = [(0.91, 0.97, 1), (0.94, 1, 0.97), (1, 0.96, 0.91), (0.98, 0.95, 1), (0.95, 0.98, 0.92), (0.93, 0.96, 1)]
    for (name, (x, yb, w, h, body)), fill in zip(boxes.items(), colors):
        pdf.box(x, yb, w, h, name, body, fill=fill)
    pdf.line(169, 446, 204, 446, "HTTPS")
    pdf.line(339, 446, 374, 446, "routes")
    pdf.line(544, 446, 594, 446, "read/write")
    pdf.line(544, 410, 594, 292, "API calls")
    pdf.line(459, 380, 459, 312, "produces")
    pdf.line(544, 266, 594, 292, "integrates")
    pdf.text(42, 162, "Key Flow", size=14, bold=True)
    pdf.bullet_list(
        52,
        140,
        [
            "User request enters the FastAPI router after authentication and email verification.",
            "Assessment service validates mandatory patient fields and consent.",
            "Document service scans uploads, extracts text, chunks content, stores embeddings, and indexes per user.",
            "Report service combines deterministic risk output, RAG citations, and Gemini LLM enhancement.",
            "Doctor workflow updates report lifecycle and version history; patient receives notifications.",
        ],
        width=124,
    )

    pdf.new_page("RAG and LLM Orchestration", "How uploaded files and knowledge are used safely")
    pdf.box(44, 392, 145, 82, "1. Upload", ["TXT, PDF, DOCX", "Security scan", "Size/type checks"], fill=(0.91, 0.97, 1))
    pdf.box(218, 392, 145, 82, "2. Extract", ["Text extraction", "Health-topic detection", "Safe suggestions"], fill=(0.94, 1, 0.97))
    pdf.box(392, 392, 145, 82, "3. Chunk", ["Sentence-aware chunks", "Overlap", "Citation labels"], fill=(1, 0.96, 0.91))
    pdf.box(566, 392, 145, 82, "4. Embed", ["Stored embeddings", "JSON fallback", "pgvector optional"], fill=(0.98, 0.95, 1))
    pdf.line(189, 433, 218, 433, "")
    pdf.line(363, 433, 392, 433, "")
    pdf.line(537, 433, 566, 433, "")
    pdf.box(110, 240, 170, 92, "5. Retrieve", ["Only global knowledge", "Plus logged-in user's chunks", "Cosine similarity ranking"], fill=(0.95, 0.98, 0.92))
    pdf.box(335, 240, 170, 92, "6. Prompt", ["Patient input", "Risk summary", "Top citations", "Safety requirements"], fill=(0.93, 0.96, 1))
    pdf.box(560, 240, 170, 92, "7. Generate", ["Gemini JSON output", "No diagnosis", "No prescription", "Fail closed for reports"], fill=(1, 0.94, 0.95))
    pdf.line(280, 286, 335, 286, "")
    pdf.line(505, 286, 560, 286, "")
    pdf.text(44, 170, "RAG Privacy Rule", size=14, bold=True)
    pdf.paragraph(44, 148, "Patient uploads are tied to rag_documents.user_id and rag_chunks.user_id. Report and chat retrieval loads global approved knowledge plus only the logged-in patient's document chunks. Other patients' uploaded files are never selected for that user's report context.", width=124, size=10)

    pdf.new_page("Security, Privacy, and Compliance Architecture", "Controls that lift pilot-readiness toward healthcare compliance")
    pdf.box(44, 390, 168, 105, "Access Control", ["Email verification gate", "Signed expiring sessions", "Logout revocation", "Role-based APIs", "Google SSO path"], fill=(0.91, 0.97, 1))
    pdf.box(238, 390, 168, 105, "Data Protection", ["Encrypted PHI payloads", "Patient-only reports", "Per-user RAG", "Privacy export", "Health-data deletion"], fill=(0.94, 1, 0.97))
    pdf.box(432, 390, 168, 105, "Auditability", ["Audit hash chain", "IP/user-agent metadata", "Consent records", "Report versions", "Doctor review history"], fill=(1, 0.96, 0.91))
    pdf.box(626, 390, 168, 105, "App Hardening", ["Security headers", "Upload scan", "Rate limits", "LLM fail-closed", "No prescribing"], fill=(0.98, 0.95, 1))
    pdf.text(44, 320, "Compliance Status", size=14, bold=True)
    pdf.bullet_list(
        54,
        296,
        [
            "Current healthcare compliance readiness is approximately 60% for a pilot or controlled demo.",
            "The system includes consent, audit, privacy export/delete, PHI encryption, and access isolation controls.",
            "It is not yet production HIPAA-ready without BAA, KMS-managed keys, SIEM, penetration testing, formal risk assessment, malware scanning, backup evidence, and incident response procedures.",
        ],
        width=124,
    )

    pdf.new_page("Pending Production Architecture Items", "What remains before production healthcare deployment")
    pdf.text(44, 500, "Highest Priority Pending Items", size=15, bold=True)
    pdf.bullet_list(
        54,
        474,
        [
            "Deploy over HTTPS with managed PostgreSQL, private database networking, secure cookies, and platform-level rate limiting.",
            "Move secrets and encryption keys to AWS Secrets Manager, GCP Secret Manager, or Vault with KMS-backed rotation.",
            "Use production pgvector and a stronger embedding model, with prompt/version audit trails and PHI minimization.",
            "Integrate real malware scanning, OCR for scanned files, lab table extraction, and confidence scoring.",
            "Add SIEM/monitoring, immutable audit storage, backup/restore evidence, disaster recovery, and incident response.",
            "Complete legal/compliance work: BAA, HIPAA risk assessment, policy docs, and penetration testing.",
        ],
        width=125,
    )
    pdf.text(44, 260, "Recommended Deployment Path", size=15, bold=True)
    pdf.box(54, 145, 180, 78, "Demo", ["Render or ngrok", "HTTPS URL", "Managed PostgreSQL optional"], fill=(0.91, 0.97, 1))
    pdf.box(270, 145, 180, 78, "Pilot", ["Google Cloud Run", "Cloud SQL", "Secret Manager", "Cloud Logging"], fill=(0.94, 1, 0.97))
    pdf.box(486, 145, 220, 78, "Production Healthcare", ["AWS or GCP with BAA", "KMS, WAF, SIEM", "Private network and compliance evidence"], fill=(1, 0.96, 0.91))
    pdf.line(234, 184, 270, 184, "")
    pdf.line(450, 184, 486, 184, "")

    return pdf.finish()


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build_pdf()
    OUT.write_bytes(payload)
    print(OUT)
    print(len(payload))


if __name__ == "__main__":
    main()
