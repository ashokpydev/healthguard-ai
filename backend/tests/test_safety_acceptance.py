import os
import tempfile
import uuid
import json
from pathlib import Path

import pytest

os.environ["HEALTHGUARD_DB_PATH"] = str(Path(tempfile.gettempdir()) / "healthguard-ai-tests" / "test-healthguard.db")
os.environ["SMTP_TEST_MODE"] = "1"
os.environ["LLM_TEST_MODE"] = "1"

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.store import connect
from backend.app.schemas.health import AssessmentRequest, HealthProfile
from backend.app.services.llm_service import LLMService
from backend.app.services.report_service import ReportLLMError, ReportService


client = TestClient(app)


def register_user(role: str) -> dict:
    email = f"{role}-{uuid.uuid4().hex}@gmail.com"
    response = client.post(
        "/api/auth/register",
        json={
            "name": f"Demo {role.title()}",
            "email": email,
            "password": "secret123",
            "role": role,
            "organization": "HealthGuard Demo",
            "license_number": f"{role.upper()}-001",
        },
    )
    assert response.status_code == 200
    registered = response.json()
    outbox = client.get("/api/auth/dev/outbox", params={"email": registered["email"]})
    assert outbox.status_code == 200
    code = outbox.json()["token"]
    assert code.isdigit()
    assert len(code) == 6
    verified = client.post("/api/auth/verify-email", json={"email": registered["email"], "code": code})
    assert verified.status_code == 200
    return verified.json()


def profile(**overrides):
    base = {
        "age": 35,
        "gender": "male",
        "height_cm": 170,
        "weight_kg": 80,
        "location": "Hyderabad",
        "climate": "hot weather",
        "occupation": "Software Engineer",
        "sleep_hours": 5,
        "exercise_frequency": "none",
        "diet_style": "processed food, high sugar, low water",
        "food_habits": ["late-night eating"],
    }
    base.update(overrides)
    return base


def test_emergency_symptom_gets_immediate_warning():
    patient = register_user("patient")
    response = client.post(
        "/api/chat/health-question",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={"question": "Chest pain and shortness of breath.", "consent_to_process_health_data": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["red_flags"]
    assert body["doctor_consultation_required"] is True
    assert "emergency medical care" in body["answer"].lower()


def test_lifestyle_report_for_software_engineer():
    patient = register_user("patient")
    response = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": profile(),
            "symptoms": [],
            "question": "I sit for 10 hours daily and sleep poorly.",
            "consent_to_process_health_data": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    report = body["report"]
    assert body["report_id"] > 0
    assert report["risk_summary"]["overall_risk_level"] in {"Moderate", "High"}
    assert any("Sedentary" in item for item in report["risk_summary"]["key_risk_factors"])
    assert any("movement break" in item for item in report["precautions"])
    assert any("plate method" in item.lower() for item in report["diet_plan"])
    assert any("sugar" in item.lower() or "processed" in item.lower() for item in report["diet_plan"])
    assert any("meditation" in item.lower() or "breathing" in item.lower() for item in report["wellness_recommendations"])
    assert any("cat-cow" in item.lower() or "walking" in item.lower() for item in report["physical_activity_plan"])
    assert any("Orthopedics" in item or "General Physician" in item for item in report["doctor_department_guidance"])
    assert report["doctor_consultation_required"] is True
    assert report["generation_engine"] == "test-llm"
    assert report["llm_summary"]


def test_llm_status_reports_test_mode():
    response = client.get("/api/health/llm")
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["test_mode"] is True


def test_huggingface_provider_uses_chat_completions_json(monkeypatch):
    monkeypatch.delenv("LLM_TEST_MODE", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "huggingface")
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    monkeypatch.setenv("HUGGINGFACE_MODEL", "demo/model:provider")

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "demo/model:provider",
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "llm_summary": "HF summary",
                                        "additional_precautions": [],
                                        "doctor_questions": [],
                                        "follow_up_reminders": [],
                                        "concerns_to_discuss": [],
                                    }
                                )
                            }
                        }
                    ],
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    service = LLMService()
    service.provider = "huggingface"
    service.model = "demo/model:provider"
    service.active_model = service.model
    service._api_key_value = lambda: "hf_test_token"
    result = service.enhance_report(
        AssessmentRequest(
            profile=HealthProfile(**profile()),
            symptoms=[],
            question="I feel tired.",
            consent_to_process_health_data=True,
        ),
        {
            "risk_summary": type(
                "Risk",
                (),
                {"overall_risk_level": "Moderate", "risk_score": 46, "key_risk_factors": ["Short sleep duration"]},
            )(),
            "possible_health_concerns_to_discuss_with_doctor": [],
            "precautions": [],
            "emergency_warning": False,
            "red_flags": [],
        },
        [],
    )

    assert captured["url"] == "https://router.huggingface.co/v1/chat/completions"
    assert captured["authorization"] == "Bearer hf_test_token"
    assert captured["payload"]["model"] == "demo/model:provider"
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert result["generation_engine"] == "huggingface:demo/model:provider"
    assert result["llm_summary"] == "HF summary"

    monkeypatch.setenv("LLM_TEST_MODE", "1")


def test_voice_transcription_uses_huggingface_asr(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_voice_test")
    monkeypatch.setenv("HUGGINGFACE_ASR_MODEL", "openai/whisper-large-v3-turbo")
    monkeypatch.setattr("backend.app.services.speech_service.SpeechService._token", lambda self: "hf_voice_test")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"text": "I have headache for two days and sleep poorly."}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers["Authorization"]
        captured["content_type"] = request.headers["Content-type"]
        captured["payload"] = request.data
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    patient = register_user("patient")
    response = client.post(
        "/api/voice/transcribe",
        headers={"X-Demo-Token": patient["demo_token"]},
        files={"audio": ("voice-input.webm", b"demo-audio-bytes" * 120, "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json()["transcript"] == "I have headache for two days and sleep poorly."
    assert captured["url"].endswith("/openai/whisper-large-v3-turbo")
    assert captured["authorization"] == "Bearer hf_voice_test"
    assert captured["content_type"] == "audio/webm"
    assert captured["payload"] == b"demo-audio-bytes" * 120


def test_report_generation_stops_when_configured_llm_fails():
    class FailingLLM:
        def configured(self):
            return True

        def status(self):
            return {"provider": "gemini", "model": "test-fail", "missing": []}

        def enhance_report(self, request, base_report, sources):
            raise RuntimeError("simulated Gemini connection failed")

    service = ReportService()
    service.llm = FailingLLM()
    request = AssessmentRequest(
        profile=HealthProfile(**profile()),
        symptoms=[],
        question="I feel tired and sleep poorly.",
        consent_to_process_health_data=True,
    )

    with pytest.raises(ReportLLMError) as exc:
        service.generate(request)

    detail = exc.value.as_detail()
    assert detail["provider"] == "gemini"
    assert detail["model"] == "test-fail"
    assert "No report was created or saved" in detail["message"]
    assert "simulated Gemini connection failed" in detail["error"]


def test_optional_document_upload_feeds_report_rag_context():
    patient = register_user("patient")
    upload = client.post(
        "/api/documents/upload",
        headers={"X-Demo-Token": patient["demo_token"]},
        files={"file": ("labs.txt", b"HbA1c 6.1. Vitamin D low. LDL borderline high.", "text/plain")},
    )
    assert upload.status_code == 200
    uploaded = upload.json()
    assert uploaded["status"] == "processed_for_rag"
    assert "HbA1c" in uploaded["tuned_context"]

    response = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": profile(),
            "symptoms": [],
            "question": "Review my uploaded lab context.",
            "document_context": uploaded["tuned_context"],
            "consent_to_process_health_data": True,
        },
    )
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["sources"][0]["source_type"] == "user_upload_rag_context"
    assert "Uploaded document findings that may need clinician interpretation" in report[
        "possible_health_concerns_to_discuss_with_doctor"
    ]


def test_uploaded_file_generates_relevant_safe_suggestions_without_prescribing():
    patient = register_user("patient")
    upload = client.post(
        "/api/documents/upload",
        headers={"X-Demo-Token": patient["demo_token"]},
        files={
            "file": (
                "health-condition.txt",
                (
                    b"Patient history: diabetes and high cholesterol. "
                    b"HbA1c 6.8, LDL 162, Vitamin D 14. "
                    b"Current medication: Metformin tablet. "
                    b"No chest pain today."
                ),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 200
    data = upload.json()
    assert any("HbA1c" in item for item in data["detected_topics"])
    assert any("LDL" in item or "cholesterol" in item.lower() for item in data["detected_topics"])
    assert any("diabetes" in item.lower() for item in data["suggested_actions"])
    assert any("cardiovascular" in item.lower() or "lipid" in item.lower() for item in data["suggested_actions"])
    assert any("do not start, stop, or change" in item.lower() for item in data["suggested_actions"])
    assert not any("take metformin" in item.lower() for item in data["suggested_actions"])
    assert "Safe suggested actions" in data["tuned_context"]


def test_uploaded_documents_are_indexed_for_user_isolated_semantic_rag():
    patient_a = register_user("patient")
    patient_b = register_user("patient")
    upload = client.post(
        "/api/documents/upload",
        headers={"X-Demo-Token": patient_a["demo_token"]},
        files={
            "file": (
                "thyroid-note.txt",
                b"TSH is elevated. Thyroid follow up was advised. Fatigue may need endocrine review.",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 200
    assert "Indexed" in upload.json()["rag_summary"]

    own_status = client.get("/api/health/rag", headers={"X-Demo-Token": patient_a["demo_token"]})
    assert own_status.status_code == 200
    assert own_status.json()["user_documents"] >= 1
    assert own_status.json()["user_chunks"] >= 1

    own_report = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient_a["demo_token"]},
        json={
            "profile": profile(),
            "symptoms": [{"name": "fatigue", "duration_days": 10, "severity": 4}],
            "question": "Does my thyroid follow up note matter for fatigue?",
            "consent_to_process_health_data": True,
        },
    )
    assert own_report.status_code == 200
    own_sources = own_report.json()["report"]["sources"]
    assert any(source["source_type"] == "patient_document_rag" and "Thyroid" in source["excerpt"] for source in own_sources)

    other_report = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient_b["demo_token"]},
        json={
            "profile": profile(),
            "symptoms": [{"name": "fatigue", "duration_days": 10, "severity": 4}],
            "question": "Does my thyroid follow up note matter for fatigue?",
            "consent_to_process_health_data": True,
        },
    )
    assert other_report.status_code == 200
    other_sources = other_report.json()["report"]["sources"]
    assert not any(source["source_type"] == "patient_document_rag" and "Thyroid" in source["excerpt"] for source in other_sources)


def test_structured_patient_inputs_drive_risk_factors():
    patient = register_user("patient")
    response = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": {
                "age": 48,
                "gender": "male",
                "height_cm": 170,
                "weight_kg": 92,
                "location": "Hyderabad",
                "climate": "hot weather",
                "occupation": "Office manager",
                "sleep_hours": 5,
                "exercise_frequency": "rare",
                "diet_style": "processed food, high salt packaged food, low water",
                "food_habits": ["late-night eating"],
                "smoking_status": "current smoker",
                "alcohol_status": "frequent alcohol",
                "existing_conditions": ["BP"],
                "family_history": ["diabetes"],
            },
            "symptoms": [{"name": "headache", "duration_days": 4, "severity": 7}],
            "question": "I feel tired and have headaches.",
            "consent_to_process_health_data": True,
        },
    )
    assert response.status_code == 200
    factors = response.json()["report"]["risk_summary"]["key_risk_factors"]
    assert "Current smoking" in factors
    assert "Frequent alcohol intake" in factors
    assert "Existing medical conditions" in factors
    assert "Severe symptom: headache" in factors


def test_medication_request_is_not_prescribed():
    patient = register_user("patient")
    response = client.post(
        "/api/chat/health-question",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={"question": "I have fever. Which antibiotic should I take?", "consent_to_process_health_data": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert "cannot recommend" in body["answer"].lower()
    assert "consult" in body["answer"].lower()


def test_missing_information_asks_follow_up():
    patient = register_user("patient")
    response = client.post(
        "/api/chat/health-question",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={"question": "I feel weak.", "consent_to_process_health_data": True},
    )

    assert response.status_code == 200
    assert "more information" in response.json()["answer"].lower()


def test_health_data_requires_consent():
    patient = register_user("patient")
    response = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": profile(),
            "symptoms": [],
            "question": "I want a preventive health report.",
            "consent_to_process_health_data": False,
        },
    )

    assert response.status_code == 400
    assert "Consent is required" in response.json()["detail"]


def test_report_requires_mandatory_patient_fields():
    patient = register_user("patient")
    response = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": {"age": 35, "location": "Hyderabad"},
            "symptoms": [],
            "question": "",
            "consent_to_process_health_data": True,
        },
    )
    assert response.status_code == 422
    assert "Complete mandatory assessment fields" in str(response.json()["detail"])


def test_register_login_report_download_and_doctor_review():
    patient = register_user("patient")
    doctor = register_user("doctor")

    login = client.post("/api/auth/login", json={"email": patient["email"], "password": "secret123"})
    assert login.status_code == 200
    assert login.json()["role"] == "patient"
    assert "generate_report" in login.json()["capabilities"]

    me = client.get("/api/auth/me", headers={"X-Demo-Token": login.json()["demo_token"]})
    assert me.status_code == 200
    assert me.json()["landing_view"] == "assessment"

    generated = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": profile(name="Demo Patient"),
            "symptoms": [{"name": "back pain", "duration_days": 5, "severity": 5}],
            "question": "Back pain after long desk work.",
            "consent_to_process_health_data": True,
        },
    )
    assert generated.status_code == 200
    report_id = generated.json()["report_id"]

    pdf = client.get(f"/api/reports/{report_id}/download")
    assert pdf.status_code == 401

    pdf = client.get(f"/api/reports/{report_id}/download?demo_token={patient['demo_token']}")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    review = client.post(
        f"/api/doctor/reports/{report_id}/review",
        headers={"X-Demo-Token": doctor["demo_token"]},
        json={"status": "approved", "comments": "Looks safe for demo.", "final_clinical_notes": "Routine follow-up."},
    )
    assert review.status_code == 200
    assert review.json()["doctor_review_status"] == "approved"


def test_patient_reports_are_private_and_doctor_gets_patient_folders():
    patient_x = register_user("patient")
    patient_y = register_user("patient")
    doctor = register_user("doctor")

    generated = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient_x["demo_token"]},
        json={
            "profile": profile(name="Patient X", location="Hyderabad"),
            "symptoms": [{"name": "fatigue", "duration_days": 3, "severity": 4}],
            "question": "Patient X feels tired after desk work.",
            "consent_to_process_health_data": True,
        },
    )
    assert generated.status_code == 200
    report_id = generated.json()["report_id"]

    own_reports = client.get("/api/reports", headers={"X-Demo-Token": patient_x["demo_token"]})
    assert own_reports.status_code == 200
    assert any(item["id"] == report_id for item in own_reports.json()["items"])

    other_reports = client.get("/api/reports", headers={"X-Demo-Token": patient_y["demo_token"]})
    assert other_reports.status_code == 200
    assert all(item["id"] != report_id for item in other_reports.json()["items"])

    doctor_own_reports = client.get("/api/reports", headers={"X-Demo-Token": doctor["demo_token"]})
    assert doctor_own_reports.status_code == 200
    assert all(item["id"] != report_id for item in doctor_own_reports.json()["items"])

    other_download = client.get(f"/api/reports/{report_id}/download?demo_token={patient_y['demo_token']}")
    assert other_download.status_code == 404

    folders = client.get("/api/doctor/reports/pending", headers={"X-Demo-Token": doctor["demo_token"]})
    assert folders.status_code == 200
    assert any(
        report["id"] == report_id
        for folder in folders.json()["patient_folders"]
        for report in folder["reports"]
    )


def test_admin_knowledge_and_audit_logs():
    admin = register_user("admin")
    compliance = register_user("compliance")
    knowledge = client.post(
        "/api/admin/knowledge",
        headers={"X-Demo-Token": admin["demo_token"]},
        json={
            "title": "Demo hydration guidance",
            "content": "During hot weather, patients should maintain hydration and seek care for severe dehydration symptoms.",
        },
    )
    assert knowledge.status_code == 200
    assert knowledge.json()["status"] == "approved"

    logs = client.get("/api/admin/audit-logs", headers={"X-Demo-Token": compliance["demo_token"]})
    assert logs.status_code == 200
    assert isinstance(logs.json()["items"], list)


def test_role_guards_block_wrong_user_type():
    patient = register_user("patient")
    blocked = client.get("/api/admin/audit-logs", headers={"X-Demo-Token": patient["demo_token"]})
    assert blocked.status_code == 403

    anonymous = client.get("/api/doctor/reports/pending")
    assert anonymous.status_code == 401


def test_feature_routes_require_login_before_home_access():
    response = client.post(
        "/api/reports/generate",
        json={
            "profile": profile(),
            "symptoms": [],
            "question": "I sit for 10 hours daily.",
            "consent_to_process_health_data": True,
        },
    )
    assert response.status_code == 401
    assert "Login is required" in response.json()["detail"]


def test_registration_requires_valid_real_email_and_confirmation_before_login():
    invalid = client.post(
        "/api/auth/register",
        json={"name": "Bad Email", "email": "bad-email", "password": "secret123", "role": "patient"},
    )
    assert invalid.status_code == 422
    assert "valid email" in str(invalid.json()["detail"]).lower()

    blocked_domain = client.post(
        "/api/auth/register",
        json={"name": "Example Email", "email": "blocked@example.com", "password": "secret123", "role": "patient"},
    )
    assert blocked_domain.status_code == 422

    typo_domain = client.post(
        "/api/auth/register",
        json={"name": "Typo Email", "email": "blocked@gmail.con", "password": "secret123", "role": "patient"},
    )
    assert typo_domain.status_code == 422
    typo_outbox = client.get("/api/auth/dev/outbox", params={"email": "blocked@gmail.con"})
    assert typo_outbox.status_code == 404

    email = f"pending-{uuid.uuid4().hex}@gmail.com"
    pending = client.post(
        "/api/auth/register",
        json={"name": "Pending Patient", "email": email, "password": "secret123", "role": "patient"},
    )
    assert pending.status_code == 200
    assert pending.json()["email_verified"] is False
    assert "demo_token" not in pending.json()

    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 403
    assert "confirm your email" in login.json()["detail"].lower()

    outbox = client.get("/api/auth/dev/outbox", params={"email": email})
    assert outbox.status_code == 200
    code = outbox.json()["token"]
    assert code.isdigit()
    assert len(code) == 6
    verified = client.post("/api/auth/verify-email", json={"email": email, "code": code})
    assert verified.status_code == 200
    assert verified.json()["email_verified"] is True
    assert verified.json()["demo_token"]


def test_registration_does_not_create_user_when_smtp_unavailable(monkeypatch):
    monkeypatch.delenv("SMTP_TEST_MODE", raising=False)
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"]:
        monkeypatch.setenv(key, "")

    email = f"nosmtp-{uuid.uuid4().hex}@gmail.com"
    response = client.post(
        "/api/auth/register",
        json={"name": "No SMTP", "email": email, "password": "secret123", "role": "patient"},
    )
    assert response.status_code == 503

    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 401

    monkeypatch.setenv("SMTP_TEST_MODE", "1")


def test_unverified_registration_can_be_retried_with_same_email():
    email = f"retry-{uuid.uuid4().hex}@gmail.com"
    first = client.post(
        "/api/auth/register",
        json={"name": "First Pending", "email": email, "password": "secret123", "role": "patient"},
    )
    assert first.status_code == 200

    retry = client.post(
        "/api/auth/register",
        json={"name": "Retry Pending", "email": email, "password": "changed123", "role": "patient"},
    )
    assert retry.status_code == 200
    assert retry.json()["email"] == email

    login = client.post("/api/auth/login", json={"email": email, "password": "changed123"})
    assert login.status_code == 403


def test_sso_start_scaffold_for_supported_providers():
    google = client.get("/api/auth/sso/google/start")
    assert google.status_code == 200
    assert google.json()["provider"] == "google"

    facebook = client.get("/api/auth/sso/facebook/start")
    assert facebook.status_code == 200
    assert facebook.json()["provider"] == "facebook"

    instagram = client.get("/api/auth/sso/instagram/start")
    assert instagram.status_code == 200
    assert instagram.json()["provider"] == "instagram"

    unsupported = client.get("/api/auth/sso/twitter/start")
    assert unsupported.status_code == 400


def test_security_scan_blocks_malicious_upload_and_audit_masks_pii():
    patient = register_user("patient")
    blocked = client.post(
        "/api/documents/upload",
        headers={"X-Demo-Token": patient["demo_token"]},
        files={"file": ("eicar.txt", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!", "text/plain")},
    )
    assert blocked.status_code == 400
    assert "Upload blocked by security scan" in blocked.json()["detail"]

    compliance = register_user("compliance")
    logs = client.get(
        "/api/admin/audit-logs",
        headers={"X-Demo-Token": compliance["demo_token"]},
        params={"action": "documents.upload.blocked"},
    )
    assert logs.status_code == 200
    item = logs.json()["items"][0]
    assert item["event_hash"]
    assert item["immutable"] == 1
    assert "sha256" in item["metadata_json"]

    export = client.get(
        "/api/admin/audit-logs/export",
        headers={"X-Demo-Token": compliance["demo_token"]},
        params={"format": "csv", "action": "documents.upload.blocked"},
    )
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")


def test_doctor_assignment_lifecycle_signature_history_and_pdf_metadata():
    patient = register_user("patient")
    doctor = register_user("doctor")
    generated = client.post(
        "/api/reports/generate",
        headers={"X-Demo-Token": patient["demo_token"]},
        json={
            "profile": profile(name="Lifecycle Patient"),
            "symptoms": [{"name": "fatigue", "duration_days": 5, "severity": 5}],
            "question": "I feel tired and sleep poorly.",
            "consent_to_process_health_data": True,
        },
    )
    assert generated.status_code == 200
    report_id = generated.json()["report_id"]

    with connect() as conn:
        raw = conn.execute("SELECT report_json FROM reports WHERE id = ?", (report_id,)).fetchone()["report_json"]
    assert raw.startswith("enc:v1:")

    assigned = client.post(
        f"/api/doctor/reports/{report_id}/assign",
        headers={"X-Demo-Token": doctor["demo_token"]},
        json={"priority": "priority"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_reviewer_id"] == doctor["id"]
    assert assigned.json()["doctor_review_status"] == "assigned"

    reviewed = client.post(
        f"/api/doctor/reports/{report_id}/review",
        headers={"X-Demo-Token": doctor["demo_token"]},
        json={
            "status": "escalated",
            "comments": "Needs clinician follow-up.",
            "final_clinical_notes": "Schedule review.",
            "clinician_signature": "Dr Demo",
            "review_priority": "urgent",
            "escalation_reason": "Persistent symptoms with elevated risk score.",
        },
    )
    assert reviewed.status_code == 200
    body = reviewed.json()
    assert body["doctor_review_status"] == "escalated"
    assert body["clinician_signature"] == "Dr Demo"
    assert body["review_priority"] == "urgent"
    assert len(body["review_history"]) >= 2

    history = client.get(f"/api/doctor/reports/{report_id}/history", headers={"X-Demo-Token": doctor["demo_token"]})
    assert history.status_code == 200
    assert history.json()["items"][-1]["to_status"] == "escalated"

    pdf = client.get(f"/api/reports/{report_id}/download?demo_token={patient['demo_token']}")
    assert pdf.status_code == 200
    assert b"DOCTOR REVIEW METADATA" in pdf.content
    assert b"Dr Demo" in pdf.content
