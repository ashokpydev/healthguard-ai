from fastapi import APIRouter, File, Header, HTTPException, Query, Response, UploadFile

from backend.app.schemas.health import (
    AssessmentRequest,
    ChatRequest,
    DoctorReviewRequest,
    EmailVerificationRequest,
    HealthProfile,
    KnowledgeUploadRequest,
    LoginRequest,
    ResendVerificationRequest,
    RegisterRequest,
)
from backend.app.db.store import db_status
from backend.app.services.auth_service import AuthService
from backend.app.services.chat_service import ChatService
from backend.app.services.document_service import DocumentService
from backend.app.services.email_service import EmailService
from backend.app.services.llm_service import LLMService
from backend.app.services.pdf_service import PdfService
from backend.app.services.report_service import ReportLLMError, ReportService
from backend.app.services.storage_service import StorageService
from backend.app.services.triage_service import TriageService

router = APIRouter()


def require_user(x_demo_token: str | None = None, demo_token: str | None = None) -> dict:
    token = x_demo_token or demo_token
    if not token:
        raise HTTPException(status_code=401, detail="Login is required for this action.")
    user = AuthService().me(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired demo session.")
    if not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Email confirmation is required before accessing the dashboard.")
    return user


def require_role(allowed_roles: set[str], x_demo_token: str | None = None, demo_token: str | None = None) -> dict:
    user = require_user(x_demo_token, demo_token)
    if user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"This action requires one of these roles: {', '.join(sorted(allowed_roles))}.")
    return user


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "HealthGuard AI"}


@router.get("/health/db")
def health_db() -> dict:
    return db_status()


@router.get("/health/llm")
def health_llm() -> dict:
    return LLMService().status()


@router.post("/auth/register")
def register(request: RegisterRequest) -> dict:
    try:
        user = AuthService().register(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    StorageService().save_audit("auth.register", request.email, f"created role {request.role}")
    return user


@router.post("/auth/login")
def login(request: LoginRequest) -> dict:
    try:
        user = AuthService().login(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    StorageService().save_audit("auth.login", request.email, "login success")
    return user


@router.get("/auth/verify-email")
def verify_email_get(code: str = Query(...), email: str | None = Query(default=None)) -> dict:
    user = AuthService().verify_email(code, email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")
    StorageService().save_audit("auth.verify-email", user["email"], "email verified")
    return user


@router.post("/auth/verify-email")
def verify_email_post(request: EmailVerificationRequest) -> dict:
    user = AuthService().verify_email(request.code, request.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token.")
    StorageService().save_audit("auth.verify-email", user["email"], "email verified")
    return user


@router.post("/auth/resend-confirmation")
def resend_confirmation(request: ResendVerificationRequest) -> dict:
    try:
        result = AuthService().resend_verification(request.email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    StorageService().save_audit("auth.resend-confirmation", request.email, "verification email queued")
    return result


@router.get("/auth/me")
def me(x_demo_token: str | None = Header(default=None)) -> dict:
    return require_user(x_demo_token)


@router.get("/auth/dev/outbox")
def latest_dev_email(email: str = Query(...)) -> dict:
    item = EmailService().latest_for(email.lower())
    if not item:
        raise HTTPException(status_code=404, detail="No confirmation email found for this address.")
    return item


@router.get("/auth/email/status")
def email_status() -> dict:
    return EmailService().smtp_status()


@router.get("/auth/sso/{provider}/start")
def sso_start(provider: str, role: str = Query(default="patient")) -> dict:
    try:
        return AuthService().sso_start(provider, role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/auth/sso/{provider}/callback")
def sso_callback(provider: str, code: str | None = Query(default=None), state: str | None = Query(default=None)) -> dict:
    return {
        "provider": provider,
        "state": state,
        "code_received": bool(code),
        "message": "SSO callback is scaffolded. Configure provider secrets and token exchange to complete live SSO.",
    }


@router.post("/patients/profile")
def create_profile(profile: HealthProfile, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    item = StorageService().save_profile(profile, user["id"] if user["role"] == "patient" else None)
    StorageService().save_audit("patients.profile.create", profile.name or "anonymous", f"profile {item['id']} created")
    return item


@router.post("/assessments/submit")
def submit_assessment(request: AssessmentRequest, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    try:
        report = ReportService().generate(request).model_dump()
    except ReportLLMError as exc:
        raise HTTPException(status_code=503, detail=exc.as_detail()) from exc
    ids = StorageService().save_assessment_and_report(
        request,
        report,
        request.patient_id,
        user["id"] if user["role"] == "patient" else None,
    )
    StorageService().save_audit(
        "assessments.submit",
        request.question or "structured assessment",
        f"report {ids['report_id']} risk {report['risk_summary']['overall_risk_level']}",
        report["red_flags"],
    )
    return {**ids, "report": report}


@router.post("/reports/generate")
def generate_report(request: AssessmentRequest, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    try:
        report = ReportService().generate(request).model_dump()
    except ReportLLMError as exc:
        raise HTTPException(status_code=503, detail=exc.as_detail()) from exc
    ids = StorageService().save_assessment_and_report(
        request,
        report,
        request.patient_id,
        user["id"] if user["role"] == "patient" else None,
    )
    StorageService().save_audit(
        "reports.generate",
        request.question or "structured report",
        f"report {ids['report_id']} risk {report['risk_summary']['overall_risk_level']}",
        report["red_flags"],
    )
    return {**ids, "report": report}


@router.get("/reports")
def list_reports(x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    return {"items": StorageService().list_reports(user)}


@router.get("/reports/{report_id}")
def get_report(report_id: int, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    item = StorageService().get_report(report_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    return item


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    x_demo_token: str | None = Header(default=None),
    demo_token: str | None = Query(default=None),
):
    user = require_user(x_demo_token, demo_token)
    item = StorageService().get_report(report_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    pdf = PdfService().build_report_pdf(item)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="healthguard-report-{report_id}.pdf"'},
    )


@router.post("/chat/health-question")
def health_question(request: ChatRequest, x_demo_token: str | None = Header(default=None)):
    require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    answer = ChatService().answer(request)
    StorageService().save_audit("chat.health-question", request.question, answer.answer, answer.red_flags)
    return answer


@router.post("/symptoms/triage")
def triage(request: ChatRequest, x_demo_token: str | None = Header(default=None)):
    require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    return TriageService().analyze([], request.question)


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), x_demo_token: str | None = Header(default=None)):
    require_user(x_demo_token)
    filename = file.filename or "uploaded document"
    try:
        payload = await file.read()
        result = DocumentService().process_upload(filename, file.content_type, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    StorageService().save_audit("documents.upload", filename, result.status)
    return result


@router.get("/admin/audit-logs")
def audit_logs(x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin", "compliance"}, x_demo_token)
    return {"items": StorageService().list_audit_logs()}


@router.post("/admin/knowledge")
def upload_knowledge(request: KnowledgeUploadRequest, x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin"}, x_demo_token)
    item = StorageService().add_knowledge(request.title, request.content, request.source_type)
    StorageService().save_audit("admin.knowledge.create", request.title, f"knowledge {item['id']} approved")
    return item


@router.get("/admin/knowledge")
def list_knowledge(x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin", "doctor", "dietician", "compliance"}, x_demo_token)
    return {"items": StorageService().list_knowledge()}


@router.get("/doctor/reports/pending")
def pending_reports(x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    items = [item for item in StorageService().list_reports(user) if item["doctor_review_status"] == "pending"]
    folders = [
        {**folder, "reports": [item for item in folder["reports"] if item["doctor_review_status"] == "pending"]}
        for folder in StorageService().list_patient_report_folders(user)
        if folder["pending_count"]
    ]
    return {"items": items, "patient_folders": folders}


@router.post("/doctor/reports/{report_id}/review")
def review_report(report_id: int, request: DoctorReviewRequest, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    item = StorageService().review_report(
        report_id,
        request.status,
        request.comments,
        request.final_clinical_notes,
        user,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    StorageService().save_audit("doctor.report.review", str(report_id), f"{request.status} by {user['email']}")
    return item
