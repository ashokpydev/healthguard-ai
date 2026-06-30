import html
import json
import os
import secrets
import time

from fastapi import APIRouter, Cookie, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from backend.app.schemas.health import (
    AssessmentRequest,
    ChatExportRequest,
    ChatFeedbackRequest,
    ChatRequest,
    DoctorAssignmentRequest,
    DoctorReviewRequest,
    EmailVerificationRequest,
    HealthProfile,
    KnowledgeUploadRequest,
    KnowledgeCategoryRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PrivacyDeleteRequest,
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
from backend.app.services.rag_service import RAGService
from backend.app.services.security_service import RateLimiter, UploadSecurityScanner, audit_metadata_from_request, rows_to_csv
from backend.app.services.speech_service import SpeechService
from backend.app.services.storage_service import StorageService
from backend.app.services.triage_service import TriageService

router = APIRouter()
rate_limiter = RateLimiter()


def client_key(request: Request, user: dict | None = None, suffix: str = "general") -> str:
    client = request.client.host if request.client else "unknown"
    return f"{suffix}:{user.get('id') if user else client}"


def check_rate(key: str, limit: int = 80, window_seconds: int = 60) -> None:
    try:
        rate_limiter.check(key, limit=limit, window_seconds=window_seconds)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


def set_secure_session_cookies(response: Response, token: str) -> None:
    csrf_token = secrets.token_urlsafe(24)
    max_age = int(os.getenv("AUTH_SESSION_MINUTES", "480")) * 60
    response.set_cookie("healthguard_session", token, httponly=True, samesite="strict", secure=False, max_age=max_age)
    response.set_cookie("healthguard_csrf", csrf_token, httponly=False, samesite="strict", secure=False, max_age=max_age)


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie("healthguard_session")
    response.delete_cookie("healthguard_csrf")


def enforce_csrf_if_cookie_auth(
    x_demo_token: str | None,
    healthguard_session: str | None,
    healthguard_csrf: str | None,
    x_csrf_token: str | None,
) -> None:
    cookie_auth_enabled = os.getenv("HEALTHGUARD_ENABLE_COOKIE_AUTH", "").lower() in {"1", "true", "yes"}
    if not cookie_auth_enabled:
        return
    if x_demo_token or not healthguard_session:
        return
    if not healthguard_csrf or not x_csrf_token or not secrets.compare_digest(healthguard_csrf, x_csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token is required for cookie-authenticated write actions.")


def require_user(x_demo_token: str | None = None, demo_token: str | None = None, healthguard_session: str | None = None) -> dict:
    cookie_auth_enabled = os.getenv("HEALTHGUARD_ENABLE_COOKIE_AUTH", "").lower() in {"1", "true", "yes"}
    token = x_demo_token or demo_token or (healthguard_session if cookie_auth_enabled else None)
    if not token:
        raise HTTPException(status_code=401, detail="Login is required for this action.")
    user = AuthService().me(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired demo session.")
    if not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Email confirmation is required before accessing the dashboard.")
    return user


def require_role(
    allowed_roles: set[str],
    x_demo_token: str | None = None,
    demo_token: str | None = None,
    healthguard_session: str | None = None,
) -> dict:
    user = require_user(x_demo_token, demo_token, healthguard_session)
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


@router.get("/health/speech")
def health_speech() -> dict:
    return SpeechService().status()


@router.get("/health/google-sso")
def health_google_sso() -> dict:
    return AuthService().google_sso_status()


@router.get("/health/rag")
def health_rag(x_demo_token: str | None = Header(default=None)) -> dict:
    user = AuthService().me(x_demo_token) if x_demo_token else None
    return RAGService().status(user_id=user["id"] if user and user["role"] == "patient" else None)


@router.get("/health/compliance")
def health_compliance(x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin", "compliance"}, x_demo_token)
    return {
        "status": "pilot-ready-controls",
        "estimated_healthcare_compliance_readiness": "about 60%",
        "implemented_controls": [
            "verified authentication gate",
            "role-based access control",
            "patient-owned report isolation",
            "consent records",
            "encrypted PHI payload storage",
            "audit hash chain with retention metadata",
            "upload security scan",
            "privacy export",
            "patient health-data deletion request",
            "security response headers",
            "RAG per-user document isolation",
            "LLM fail-closed report generation",
        ],
        "remaining_for_production_compliance": [
            "BAA with cloud provider and subprocessors",
            "KMS/Vault-managed encryption keys and rotation",
            "independent penetration test",
            "formal HIPAA risk assessment",
            "centralized SIEM monitoring and incident response plan",
            "malware scanner service integration",
            "backup/restore and disaster recovery evidence",
        ],
    }


@router.post("/auth/register")
def register(request: RegisterRequest, raw_request: Request) -> dict:
    check_rate(client_key(raw_request, suffix="auth.register"), limit=100, window_seconds=300)
    try:
        user = AuthService().register(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    StorageService().save_audit(
        "auth.register",
        request.email,
        f"created role {request.role}",
        metadata=audit_metadata_from_request(raw_request, extra={"role": request.role}),
    )
    return user


@router.post("/auth/login")
def login(request: LoginRequest, response: Response, raw_request: Request) -> dict:
    check_rate(client_key(raw_request, suffix="auth.login"), limit=60, window_seconds=300)
    try:
        user = AuthService().login(request)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    set_secure_session_cookies(response, user["demo_token"])
    StorageService().save_audit(
        "auth.login",
        request.email,
        "login success",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user),
    )
    return user


@router.post("/auth/logout")
def logout(response: Response, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    token = x_demo_token or healthguard_session
    if token:
        AuthService().logout(token)
    clear_session_cookies(response)
    return {"message": "Logged out."}


@router.post("/auth/password-reset/request")
def request_password_reset(request: PasswordResetRequest, raw_request: Request) -> dict:
    check_rate(client_key(raw_request, suffix="auth.password-reset"), limit=20, window_seconds=300)
    try:
        result = AuthService().request_password_reset(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    StorageService().save_audit("auth.password-reset.request", request.email, "password reset requested", metadata=audit_metadata_from_request(raw_request))
    return result


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(request: PasswordResetConfirmRequest, raw_request: Request) -> dict:
    check_rate(client_key(raw_request, suffix="auth.password-reset-confirm"), limit=30, window_seconds=300)
    try:
        result = AuthService().confirm_password_reset(request)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    StorageService().save_audit("auth.password-reset.confirm", request.email, "password reset confirmed", metadata=audit_metadata_from_request(raw_request))
    return result


@router.get("/auth/verify-email")
def verify_email_get(response: Response, raw_request: Request, code: str = Query(...), email: str | None = Query(default=None)) -> dict:
    user = AuthService().verify_email(code, email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")
    set_secure_session_cookies(response, user["demo_token"])
    StorageService().save_audit("auth.verify-email", user["email"], "email verified", user_id=user["id"], metadata=audit_metadata_from_request(raw_request, user))
    return user


@router.post("/auth/verify-email")
def verify_email_post(request: EmailVerificationRequest, response: Response, raw_request: Request) -> dict:
    user = AuthService().verify_email(request.code, request.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token.")
    set_secure_session_cookies(response, user["demo_token"])
    StorageService().save_audit("auth.verify-email", user["email"], "email verified", user_id=user["id"], metadata=audit_metadata_from_request(raw_request, user))
    return user


@router.post("/auth/resend-confirmation")
def resend_confirmation(request: ResendVerificationRequest, raw_request: Request) -> dict:
    check_rate(client_key(raw_request, suffix="auth.resend"), limit=60, window_seconds=300)
    try:
        result = AuthService().resend_verification(request.email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    StorageService().save_audit("auth.resend-confirmation", request.email, "verification email queued", metadata=audit_metadata_from_request(raw_request))
    return result


@router.get("/auth/me")
def me(x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    return require_user(x_demo_token, healthguard_session=healthguard_session)


@router.get("/auth/csrf-token")
def csrf_token(response: Response) -> dict:
    token = secrets.token_urlsafe(24)
    response.set_cookie("healthguard_csrf", token, httponly=False, samesite="strict", secure=False, max_age=60 * 60 * 8)
    return {"csrf_token": token}


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
def sso_callback(provider: str, response: Response, raw_request: Request, code: str | None = Query(default=None), state: str | None = Query(default=None)) -> dict:
    try:
        user = AuthService().sso_callback(provider, code, state)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        StorageService().save_audit(
            "voice.transcribe.failed",
            filename,
            str(exc)[:500],
            user_id=user["id"],
            metadata=audit_metadata_from_request(raw_request, user),
        )
        raise HTTPException(status_code=503, detail="Voice transcription is temporarily unavailable. Please type the transcript manually.") from exc
    set_secure_session_cookies(response, user["demo_token"])
    StorageService().save_audit("auth.sso-login", user["email"], f"{provider} login success", user_id=user["id"], metadata=audit_metadata_from_request(raw_request, user))
    payload = html.escape(json.dumps(user), quote=False)
    return HTMLResponse(
        f"""
        <!doctype html>
        <html>
          <head><title>HealthGuard AI SSO</title></head>
          <body>
            <p>Signing you in...</p>
            <script>
              localStorage.setItem("healthguardUser", {json.dumps(payload)});
              window.location.replace("/");
            </script>
          </body>
        </html>
        """
    )


@router.post("/patients/profile")
def create_profile(profile: HealthProfile, raw_request: Request, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None), healthguard_csrf: str | None = Cookie(default=None), x_csrf_token: str | None = Header(default=None)) -> dict:
    enforce_csrf_if_cookie_auth(x_demo_token, healthguard_session, healthguard_csrf, x_csrf_token)
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    item = StorageService().save_profile(profile, user["id"] if user["role"] == "patient" else None)
    StorageService().save_audit("patients.profile.create", profile.name or "anonymous", f"profile {item['id']} created", user_id=user["id"], metadata=audit_metadata_from_request(raw_request, user))
    return item


@router.post("/assessments/submit")
def submit_assessment(request: AssessmentRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    StorageService().record_consent(user, "assessments.submit", audit_metadata_from_request(raw_request, user))
    try:
        report = ReportService().generate(request, user_id=user["id"] if user["role"] == "patient" else None).model_dump()
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
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user),
    )
    return {**ids, "report": report}


@router.post("/reports/generate")
def generate_report(request: AssessmentRequest, raw_request: Request, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None), healthguard_csrf: str | None = Cookie(default=None), x_csrf_token: str | None = Header(default=None)):
    enforce_csrf_if_cookie_auth(x_demo_token, healthguard_session, healthguard_csrf, x_csrf_token)
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    check_rate(client_key(raw_request, user, "reports.generate"), limit=60, window_seconds=300)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    StorageService().record_consent(user, "reports.generate", audit_metadata_from_request(raw_request, user))
    try:
        report = ReportService().generate(request, user_id=user["id"] if user["role"] == "patient" else None).model_dump()
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
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user),
    )
    return {**ids, "report": report}


@router.get("/reports")
def list_reports(x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    return {"items": StorageService().list_reports(user, include_role_scope=False)}


@router.get("/reports/{report_id}")
def get_report(report_id: int, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    item = StorageService().get_report(report_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    return item


@router.get("/reports/{report_id}/versions")
def report_versions(report_id: int, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    item = StorageService().get_report(report_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"items": item.get("version_history", []), "current_version": item.get("current_version", 1)}


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    x_demo_token: str | None = Header(default=None),
    demo_token: str | None = Query(default=None),
    healthguard_session: str | None = Cookie(default=None),
):
    user = require_user(x_demo_token, demo_token, healthguard_session)
    item = StorageService().get_report(report_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    pdf = PdfService().build_report_pdf(item)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="healthguard-report-{report_id}.pdf"'},
    )


@router.get("/notifications")
def notifications(x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    return {"items": StorageService().list_notifications(user)}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    item = StorageService().mark_notification_read(notification_id, user)
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return item


@router.get("/privacy/export")
def privacy_export(raw_request: Request, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    export = StorageService().export_user_health_data(user)
    StorageService().save_audit(
        "privacy.export",
        user["email"],
        "user health data exported",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user),
    )
    return export


@router.post("/privacy/delete-health-data")
def privacy_delete_health_data(request: PrivacyDeleteRequest, raw_request: Request, x_demo_token: str | None = Header(default=None), healthguard_session: str | None = Cookie(default=None)) -> dict:
    user = require_user(x_demo_token, healthguard_session=healthguard_session)
    result = StorageService().delete_user_health_data(user, audit_metadata_from_request(raw_request, user))
    StorageService().save_audit(
        "privacy.delete-health-data",
        user["email"],
        f"deleted user-owned health data request {result['request_id']}",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"request_id": result["request_id"]}),
    )
    return result


def _answer_and_persist_chat(request: ChatRequest, user: dict, raw_request: Request) -> dict:
    started_at = time.perf_counter()
    storage = StorageService()
    conversation = storage.ensure_chat_conversation(
        user,
        conversation_id=request.conversation_id,
        report_id=request.report_id,
        title=request.question[:80],
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat conversation not found.")
    user_message = storage.save_chat_message(conversation["id"], user["id"], "user", request.question)
    chat_memory = storage.list_chat_messages(user, conversation["id"], limit=12)
    answer = ChatService().answer(request, user_id=user["id"] if user["role"] == "patient" else None, chat_memory=chat_memory)
    latency_ms = int((time.perf_counter() - started_at) * 1000)
    payload = answer.model_dump()
    assistant_message = storage.save_chat_message(
        conversation["id"],
        user["id"],
        "assistant",
        answer.answer,
        answer.red_flags,
        [source.model_dump() if hasattr(source, "model_dump") else dict(source) for source in answer.sources],
        answer.doctor_consultation_required,
        answer.prompt_version,
        answer.answer_source,
        answer.generation_engine,
        answer.rag_used,
    )
    payload.update(
        {
            "conversation_id": conversation["id"],
            "user_message_id": user_message["id"],
            "assistant_message_id": assistant_message["id"],
            "emergency_escalation": bool(answer.red_flags),
        }
    )
    StorageService().save_audit(
        "chat.health-question",
        request.question,
        answer.answer,
        answer.red_flags,
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"conversation_id": conversation["id"], "report_id": request.report_id}),
    )
    storage.save_chat_analytics(
        user,
        conversation["id"],
        request.question,
        answer.answer_source,
        answer.answer_source,
        answer.prompt_version,
        latency_ms,
        answer.rag_used,
        answer.unresolved,
    )
    return payload


@router.post("/chat/health-question")
def health_question(request: ChatRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    StorageService().record_consent(user, "chat.health-question", audit_metadata_from_request(raw_request, user))
    return _answer_and_persist_chat(request, user, raw_request)


@router.post("/chat/health-question/stream")
def health_question_stream(request: ChatRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    StorageService().record_consent(user, "chat.health-question.stream", audit_metadata_from_request(raw_request, user))
    payload = _answer_and_persist_chat(request, user, raw_request)

    def events():
        words = payload["answer"].split(" ")
        running: list[str] = []
        for word in words:
            running.append(word)
            yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'payload': payload})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/chat/conversations")
def chat_conversations(x_demo_token: str | None = Header(default=None), report_id: int | None = Query(default=None)) -> dict:
    user = require_user(x_demo_token)
    return {"items": StorageService().list_chat_conversations(user, report_id=report_id)}


@router.get("/chat/starter-questions")
def chat_starter_questions(x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    return {"items": StorageService().chat_starter_questions(user)}


@router.get("/chat/analytics")
def chat_analytics(x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    return StorageService().chat_analytics_summary(user)


@router.post("/chat/export")
def chat_export(request: ChatExportRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    conversation = StorageService().export_chat_conversation(user, request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat conversation not found.")
    lines = [f"HealthGuard AI Chat Conversation #{conversation['id']}", ""]
    for message in conversation.get("messages", []):
        label = "HealthGuard" if message["role"] == "assistant" else "User"
        lines.append(f"{label}: {message['content']}")
    export_text = "\n".join(lines)
    StorageService().save_audit(
        "chat.export",
        str(request.conversation_id),
        "chat conversation exported",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"conversation_id": request.conversation_id, "report_id": request.report_id}),
    )
    return {"conversation_id": conversation["id"], "report_id": request.report_id, "content": export_text}


@router.post("/chat/feedback")
def chat_feedback(request: ChatFeedbackRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_user(x_demo_token)
    item = StorageService().save_chat_feedback(user, request.message_id, request.rating, request.reason)
    if not item:
        raise HTTPException(status_code=404, detail="Chat message not found.")
    StorageService().save_audit(
        "chat.feedback",
        str(request.message_id),
        request.rating,
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"rating": request.rating}),
    )
    return item


@router.post("/symptoms/triage")
def triage(request: ChatRequest, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    if not request.consent_to_process_health_data:
        raise HTTPException(status_code=400, detail="Consent is required before processing health data.")
    StorageService().record_consent(user, "symptoms.triage", {})
    return TriageService().analyze([], request.question)


@router.post("/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...), raw_request: Request = None, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    check_rate(client_key(raw_request, user, "voice.transcribe"), limit=30, window_seconds=300)
    filename = audio.filename or "voice-input.webm"
    try:
        payload = await audio.read()
        result = SpeechService().transcribe(filename, audio.content_type, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        StorageService().save_audit(
            "voice.transcribe.failed",
            filename,
            str(exc)[:500],
            user_id=user["id"],
            metadata=audit_metadata_from_request(raw_request, user),
        )
        raise HTTPException(status_code=503, detail="Voice transcription is temporarily unavailable. Please type the transcript manually.") from exc
    StorageService().save_audit(
        "voice.transcribe",
        filename,
        f"transcribed {len(result['transcript'])} characters",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"provider": result["provider"], "model": result["model"]}),
    )
    return result


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), raw_request: Request = None, x_demo_token: str | None = Header(default=None)):
    user = require_user(x_demo_token)
    check_rate(client_key(raw_request, user, "documents.upload"), limit=40, window_seconds=300)
    filename = file.filename or "uploaded document"
    try:
        payload = await file.read()
        scan = UploadSecurityScanner().scan(filename, file.content_type, payload)
        if not scan.allowed:
            StorageService().save_audit(
                "documents.upload.blocked",
                filename,
                scan.details,
                user_id=user["id"],
                metadata=audit_metadata_from_request(raw_request, user, {"scan_status": scan.status, "sha256": scan.sha256}),
            )
            raise HTTPException(status_code=400, detail=f"Upload blocked by security scan: {scan.details}")
        result = DocumentService().process_upload(filename, file.content_type, payload)
        if result.tuned_context:
            indexed = RAGService().index_document(
                title=filename,
                content=result.tuned_context,
                source_type="patient_upload",
                user_id=user["id"] if user["role"] == "patient" else None,
                filename=filename,
            )
            result.rag_summary = f"{result.rag_summary} Indexed {indexed['chunk_count']} chunk(s) for semantic retrieval."
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    StorageService().save_audit(
        "documents.upload",
        filename,
        result.status,
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user, {"scan_status": scan.status, "sha256": scan.sha256}),
    )
    response = result.model_dump()
    response["security_scan"] = {"status": scan.status, "details": scan.details, "sha256": scan.sha256}
    return response


@router.get("/admin/audit-logs")
def audit_logs(
    x_demo_token: str | None = Header(default=None),
    action: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> dict:
    require_role({"admin", "compliance"}, x_demo_token)
    return {"items": StorageService().list_audit_logs(action=action, user_id=user_id, date_from=date_from, date_to=date_to)}


@router.get("/admin/audit-logs/export")
def audit_logs_export(
    x_demo_token: str | None = Header(default=None),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    action: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    require_role({"admin", "compliance"}, x_demo_token)
    rows = StorageService().list_audit_logs(action=action, user_id=user_id, date_from=date_from, date_to=date_to, limit=1000)
    if format == "csv":
        return Response(
            content=rows_to_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="healthguard-audit-export.csv"'},
        )
    return {"items": rows, "count": len(rows)}


@router.post("/admin/knowledge")
def upload_knowledge(request: KnowledgeUploadRequest, x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin"}, x_demo_token)
    item = StorageService().add_knowledge(request.title, request.content, request.source_type, request.category, request.citation)
    rag_source_type = f"{request.source_type}:{request.category}" if request.category else request.source_type
    RAGService().index_document(request.title, request.content, rag_source_type, user_id=None, filename=None)
    StorageService().save_audit("admin.knowledge.create", request.title, f"knowledge {item['id']} approved")
    return item


@router.get("/admin/knowledge")
def list_knowledge(x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin", "doctor", "dietician", "compliance"}, x_demo_token)
    return {"items": StorageService().list_knowledge()}


@router.post("/admin/knowledge/categories")
def create_knowledge_category(request: KnowledgeCategoryRequest, x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin"}, x_demo_token)
    item = StorageService().upsert_knowledge_category(request.name, request.description)
    StorageService().save_audit("admin.knowledge-category.upsert", request.name, "category saved")
    return item


@router.get("/admin/knowledge/categories")
def list_knowledge_categories(x_demo_token: str | None = Header(default=None)) -> dict:
    require_role({"admin", "doctor", "dietician", "compliance"}, x_demo_token)
    return {"items": StorageService().list_knowledge_categories()}


@router.get("/doctor/reports/pending")
def pending_reports(x_demo_token: str | None = Header(default=None), status: str = Query(default="pending"), priority: str | None = Query(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    return StorageService().list_doctor_queue(user, status=status, priority=priority)


@router.get("/doctor/reports/queue")
def doctor_report_queue(x_demo_token: str | None = Header(default=None), status: str = Query(default="pending"), priority: str | None = Query(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    return StorageService().list_doctor_queue(user, status=status, priority=priority)


@router.post("/doctor/reports/{report_id}/assign")
def assign_report(report_id: int, request: DoctorAssignmentRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    item = StorageService().assign_report(report_id, request.reviewer_id or user["id"], request.priority, user)
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    StorageService().save_audit(
        "doctor.report.assign",
        str(report_id),
        f"assigned to {request.reviewer_id or user['id']} priority {request.priority}",
        user_id=user["id"],
        metadata=audit_metadata_from_request(raw_request, user),
    )
    return item


@router.post("/doctor/reports/{report_id}/review")
def review_report(report_id: int, request: DoctorReviewRequest, raw_request: Request, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_role({"doctor", "dietician"}, x_demo_token)
    item = StorageService().review_report(
        report_id,
        request.status,
        request.comments,
        request.final_clinical_notes,
        user,
        request.clinician_signature,
        request.review_priority,
        request.escalation_reason,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    StorageService().save_audit("doctor.report.review", str(report_id), f"{request.status} by {user['email']}", user_id=user["id"], metadata=audit_metadata_from_request(raw_request, user))
    return item


@router.get("/doctor/reports/{report_id}/history")
def report_review_history(report_id: int, x_demo_token: str | None = Header(default=None)) -> dict:
    user = require_role({"doctor", "dietician", "admin", "compliance"}, x_demo_token)
    history = StorageService().report_review_history(report_id, user)
    if history is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"items": history}
