# HealthGuard AI

GenAI-based preventive health risk copilot. It collects patient symptoms, lifestyle, diet, occupation, location, and climate information, then generates a safe personalized health awareness report.

HealthGuard AI is not a doctor and does not provide diagnosis, prescriptions, dosage changes, or emergency treatment decisions. It provides educational risk awareness, preventive guidance, and doctor-consultation suggestions.

## Current MVP

- FastAPI backend
- Static web UI served at `/`
- SQLite-backed demo persistence
- Role-based registration and login for patient, doctor, dietician, admin, and compliance users
- Six-digit email confirmation gate before dashboard access
- Expiring signed session tokens, logout revocation, failed-login lockout, and password reset
- Google SSO support; Facebook and Instagram are disabled until production OAuth apps are configured
- Consent-gated health data processing
- Red-flag triage
- Lifestyle, diet, climate, and occupation risk scoring
- Safe health Q&A with medication-prescribing refusal
- Personalized report JSON saved for history/review
- Branded PDF report download with chart bars, RAG references, doctor guidance, review metadata, and version history
- Report versioning/history for generated reports and doctor-review updates
- Document upload placeholder with lab-report disclaimer
- Persistent RAG pipeline with document chunking, stored embeddings, optional PostgreSQL pgvector retrieval, source citations, and per-patient isolation
- Doctor review demo workflow
- Admin knowledge upload and audit-log APIs
- Compliance status, consent records, privacy export, and confirmed health-data deletion controls
- Living implementation tracker in [docs/TRACK.md](docs/TRACK.md)

## Run Locally

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

- App: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## Test

```bash
pytest
```

## Key API Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/password-reset/request`
- `POST /api/auth/password-reset/confirm`
- `GET /api/auth/verify-email`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-confirmation`
- `GET /api/auth/sso/{provider}/start`
- `GET /api/auth/sso/{provider}/callback`
- `GET /api/health`
- `GET /api/health/compliance`
- `POST /api/patients/profile`
- `POST /api/symptoms/triage`
- `POST /api/assessments/submit`
- `POST /api/reports/generate`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/versions`
- `GET /api/reports/{report_id}/download`
- `GET /api/privacy/export`
- `POST /api/privacy/delete-health-data`
- `POST /api/chat/health-question`
- `POST /api/documents/upload`
- `POST /api/admin/knowledge`
- `GET /api/admin/knowledge`
- `GET /api/admin/audit-logs`
- `GET /api/doctor/reports/pending`
- `POST /api/doctor/reports/{report_id}/review`

## Demo Data

For local development, PostgreSQL is preferred. Set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql://postgres:your-password@localhost:5432/healthguard_ai
```

Create the `healthguard_ai` database in your local PostgreSQL first, then restart the app. If `DATABASE_URL` is empty, the app falls back to SQLite for tests/demo use.

For production-quality RAG similarity search on PostgreSQL, enable pgvector in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

When pgvector is available, HealthGuard stores chunk vectors in `rag_chunks.embedding_vector` and ranks with vector cosine distance. Without pgvector, the app keeps using the portable JSON-vector cosine fallback for local demos/tests.

Check the active database:

- `GET /api/health/db`

Role-guarded demo APIs use the `X-Demo-Token` header returned by register/login. The browser app stores that signed, expiring token in local storage for the current session.

The home/dashboard features are hidden until registration or login succeeds. Protected feature APIs also reject requests without a valid demo session token.

Registration sends a 6-digit confirmation code before login is allowed. To send real email, copy `.env.example` to `.env` and set SMTP values:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail-address@gmail.com
SMTP_PASSWORD=your-16-character-google-app-password
SMTP_FROM=your-gmail-address@gmail.com
```

For Gmail, enable 2-Step Verification and create an App Password. Use the App Password as `SMTP_PASSWORD`, not your normal Gmail password.

Production-auth settings:

```bash
HEALTHGUARD_JWT_SECRET=use-a-long-random-secret
AUTH_SESSION_MINUTES=480
AUTH_MAX_FAILED_LOGINS=5
AUTH_LOCKOUT_MINUTES=15
AUTH_PASSWORD_RESET_MINUTES=30
```

Google SSO requires a Google OAuth client configured with the callback URL shown in `.env.example`:

```bash
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/api/auth/sso/google/callback
```

Facebook and Instagram SSO buttons/endpoints are intentionally disabled until real production OAuth apps, provider review, and callback secrets are configured.

## LLM Provider

HealthGuard AI can use Gemini, Hugging Face Inference Providers, or OpenAI for live report and chat enhancement.

Gemini example:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=25
```

Hugging Face example:

```bash
LLM_PROVIDER=huggingface
HF_TOKEN=your-hugging-face-token
HUGGINGFACE_MODEL=openai/gpt-oss-120b:cerebras
HUGGINGFACE_BASE_URL=https://router.huggingface.co/v1
HUGGINGFACE_MAX_TOKENS=900
LLM_TIMEOUT_SECONDS=25
```

Restart the app after changing `.env`, then check:

```bash
GET /api/health/llm
```

Report generation is fail-closed: if the selected live LLM provider is missing credentials or fails, no report is created or saved. Chat can still fall back to the guarded educational answer.

## RAG Pipeline

HealthGuard AI indexes uploaded patient documents and approved internal knowledge into local database-backed RAG tables:

- `rag_documents` stores document metadata and ownership.
- `rag_chunks` stores chunk text, citation labels, metadata, JSON embeddings, and pgvector embeddings when PostgreSQL has the `vector` extension.
- Patient uploads are indexed under that patient's user ID.
- Approved admin knowledge is indexed globally.
- Retrieval uses pgvector cosine distance when available, with JSON-vector cosine similarity as the local fallback.
- Report and chat generation retrieve the top semantic chunks before calling Gemini.

This gives the demo a complete local RAG pipeline without a separate embedding API, while allowing PostgreSQL + pgvector to act as the production vector store.

## Tracking Rule

Every meaningful project update should be recorded in [docs/TRACK.md](docs/TRACK.md), including what changed, what was verified, and which requirement gaps remain.
