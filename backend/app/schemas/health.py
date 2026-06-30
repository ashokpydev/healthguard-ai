import re
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


RiskLevel = Literal["Low", "Moderate", "High", "Urgent"]


class SymptomInput(BaseModel):
    name: str
    duration_days: int | None = Field(default=None, ge=0)
    severity: int | None = Field(default=None, ge=1, le=10)
    frequency: str | None = None
    notes: str | None = None


class MedicationInput(BaseModel):
    medicine_name: str
    dosage_text: str | None = None
    prescribed_by: str | None = None
    notes: str | None = None


class HealthProfile(BaseModel):
    name: str | None = None
    age: int = Field(ge=0, le=125)
    gender: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    location: str | None = None
    climate: str | None = None
    occupation: str | None = None
    work_schedule: str | None = None
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    exercise_frequency: str | None = None
    diet_style: str | None = None
    food_habits: list[str] = Field(default_factory=list)
    smoking_status: str | None = None
    alcohol_status: str | None = None
    existing_conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    family_history: list[str] = Field(default_factory=list)
    current_medications: list[MedicationInput] = Field(default_factory=list)

    @computed_field
    @property
    def bmi(self) -> float | None:
        if not self.height_cm or not self.weight_kg:
            return None
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m * height_m), 1)


class AssessmentRequest(BaseModel):
    profile: HealthProfile
    symptoms: list[SymptomInput] = Field(default_factory=list)
    question: str | None = None
    document_context: str | None = None
    consent_to_process_health_data: bool = False
    patient_id: int | None = None

    @model_validator(mode="after")
    def mandatory_patient_fields(self) -> "AssessmentRequest":
        missing: list[str] = []
        required_profile_fields = [
            "age",
            "gender",
            "height_cm",
            "weight_kg",
            "location",
            "climate",
            "occupation",
            "sleep_hours",
            "exercise_frequency",
            "diet_style",
        ]
        for field_name in required_profile_fields:
            value = getattr(self.profile, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field_name)
        if not self.profile.food_habits:
            missing.append("food_habits")
        if not self.question or not self.question.strip():
            missing.append("question")
        if missing:
            raise ValueError(f"Complete mandatory assessment fields before generating a report: {', '.join(missing)}.")
        return self


class TriageResult(BaseModel):
    emergency_warning: bool
    red_flags: list[str]
    message: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list)


class RiskSummary(BaseModel):
    overall_risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    key_risk_factors: list[str]


class KnowledgeSource(BaseModel):
    title: str
    source_type: str = "approved_internal_guidance"
    excerpt: str
    citation: str | None = None
    document_id: int | None = None
    chunk_index: int | None = None
    similarity_score: float | None = None


class HealthReport(BaseModel):
    patient_summary: dict
    risk_summary: RiskSummary
    possible_health_concerns_to_discuss_with_doctor: list[str]
    precautions: list[str]
    diet_plan: list[str] = Field(default_factory=list)
    wellness_recommendations: list[str] = Field(default_factory=list)
    physical_activity_plan: list[str] = Field(default_factory=list)
    doctor_department_guidance: list[str] = Field(default_factory=list)
    doctor_consultation_required: bool
    emergency_warning: bool
    red_flags: list[str]
    suggested_questions_to_ask_doctor: list[str]
    follow_up_reminders: list[str]
    sources: list[KnowledgeSource]
    llm_summary: str | None = None
    generation_engine: str = "rules"
    llm_error: str | None = None
    disclaimer: str


class ChatRequest(BaseModel):
    question: str
    profile: HealthProfile | None = None
    consent_to_process_health_data: bool = False
    conversation_id: int | None = None
    report_id: int | None = None
    voice_mode: bool = False
    source: Literal["chat", "voice"] | None = None


class ChatResponse(BaseModel):
    answer: str
    red_flags: list[str]
    doctor_consultation_required: bool
    sources: list[KnowledgeSource]
    disclaimer: str
    conversation_stage: Literal["answered", "asking_followup", "summary_ready", "urgent"] = "answered"
    conversation_id: int | None = None
    user_message_id: int | None = None
    assistant_message_id: int | None = None
    emergency_escalation: bool = False
    answer_source: Literal["faq", "nlp", "memory", "rag", "rules", "llm", "fallback", "urgent"] = "rules"
    prompt_version: str | None = None
    generation_engine: str = "rules"
    rag_used: bool = False
    unresolved: bool = False


class ChatFeedbackRequest(BaseModel):
    message_id: int
    rating: Literal["helpful", "not_helpful", "unsafe"]
    reason: str | None = None


class ChatExportRequest(BaseModel):
    conversation_id: int
    report_id: int | None = None


class KnowledgeCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = None


class SafetyValidationResult(BaseModel):
    safe: bool
    blocked_reasons: list[str]
    sanitized_text: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)
    role: Literal["patient", "doctor", "admin", "dietician", "compliance"] = "patient"
    organization: str | None = None
    license_number: str | None = None
    specialty: str | None = None

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        email = value.strip().lower()
        pattern = r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"
        if not re.match(pattern, email, re.IGNORECASE):
            raise ValueError("Enter a valid email address.")
        local_part, full_domain = email.rsplit("@", 1)
        if local_part.startswith(".") or local_part.endswith(".") or ".." in local_part:
            raise ValueError("Enter a valid email address.")
        if ".." in full_domain or full_domain.startswith("-") or full_domain.endswith("-"):
            raise ValueError("Enter a valid email domain.")
        labels = full_domain.split(".")
        if any(not label or label.startswith("-") or label.endswith("-") for label in labels):
            raise ValueError("Enter a valid email domain.")
        blocked_domains = {"example", "invalid", "test"}
        blocked_full_domains = {
            "example.com",
            "test.com",
            "invalid.com",
            "gmail.con",
            "gamil.com",
            "gmial.com",
            "gmai.com",
            "gnail.com",
            "yahoo.con",
            "outlook.con",
            "hotmail.con",
        }
        allowed_tlds = {"ai", "app", "co", "com", "dev", "edu", "gov", "health", "in", "io", "me", "net", "org"}
        domain = full_domain.rsplit(".", 1)[0]
        tld = full_domain.rsplit(".", 1)[1]
        if domain in blocked_domains or full_domain in blocked_full_domains:
            raise ValueError("Use a real email domain for registration.")
        if len(tld) < 2 or tld.isdigit() or tld not in allowed_tlds:
            raise ValueError("Enter a valid email domain.")
        return email


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return RegisterRequest.valid_email(value)


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return RegisterRequest.valid_email(value)


class PasswordResetConfirmRequest(BaseModel):
    email: str
    token: str = Field(min_length=20, max_length=128)
    new_password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return RegisterRequest.valid_email(value)


class EmailVerificationRequest(BaseModel):
    email: str | None = None
    code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def valid_optional_email(cls, value: str | None) -> str | None:
        return RegisterRequest.valid_email(value) if value else value


class ResendVerificationRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return RegisterRequest.valid_email(value)


class AuthUser(BaseModel):
    id: int
    name: str
    email: str
    role: str
    role_profile: dict = Field(default_factory=dict)
    demo_token: str
    capabilities: list[str]
    landing_view: str


class KnowledgeUploadRequest(BaseModel):
    title: str
    content: str = Field(min_length=20)
    source_type: str = "admin_upload"
    category: str = "General"
    citation: str | None = None


class DoctorReviewRequest(BaseModel):
    status: Literal["submitted", "pending", "assigned", "in_review", "needs_patient_followup", "escalated", "reviewed", "approved", "rejected", "modified", "closed"]
    comments: str | None = None
    final_clinical_notes: str | None = None
    clinician_signature: str | None = None
    review_priority: Literal["routine", "priority", "urgent"] = "routine"
    escalation_reason: str | None = None


class DoctorAssignmentRequest(BaseModel):
    reviewer_id: int | None = None
    priority: Literal["routine", "priority", "urgent"] = "routine"


class PrivacyDeleteRequest(BaseModel):
    confirmation: Literal["DELETE"]
