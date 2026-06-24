# HealthGuard AI

GenAI-based preventive health risk copilot. It collects patient symptoms, lifestyle, diet, occupation, location, and climate information, then generates a safe personalized health awareness report.

HealthGuard AI is not a doctor and does not provide diagnosis, prescriptions, dosage changes, or emergency treatment decisions. It provides educational risk awareness, preventive guidance, and doctor-consultation suggestions.

## Current MVP

- FastAPI backend
- Static web UI served at `/`
- SQLite-backed demo persistence
- Role-based registration and login for patient, doctor, dietician, admin, and compliance users
- Six-digit email confirmation gate before dashboard access
- SSO start scaffolds for Google, Facebook, and Instagram
- Consent-gated health data processing
- Red-flag triage
- Lifestyle, diet, climate, and occupation risk scoring
- Safe health Q&A with medication-prescribing refusal
- Personalized report JSON saved for history/review
- PDF report download endpoint
- Document upload placeholder with lab-report disclaimer
- Doctor review demo workflow
- Admin knowledge upload and audit-log APIs
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
- `GET /api/auth/me`
- `GET /api/auth/verify-email`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-confirmation`
- `GET /api/auth/sso/{provider}/start`
- `GET /api/auth/sso/{provider}/callback`
- `GET /api/health`
- `POST /api/patients/profile`
- `POST /api/symptoms/triage`
- `POST /api/assessments/submit`
- `POST /api/reports/generate`
- `GET /api/reports`
- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/download`
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

Check the active database:

- `GET /api/health/db`

Role-guarded demo APIs use the `X-Demo-Token` header returned by register/login. The browser app stores that token in local storage for the current demo session.

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

SSO endpoints are scaffolded for Google, Facebook, and Instagram. Live SSO requires provider app credentials such as `GOOGLE_CLIENT_ID`, `FACEBOOK_CLIENT_ID`, or `INSTAGRAM_CLIENT_ID` plus the matching provider secrets and callback configuration.

## Gemini LLM

HealthGuard AI uses Gemini for live report and chat enhancement. Add a Gemini API key to `.env`:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT_SECONDS=25
```

Restart the app after changing `.env`, then check:

```bash
GET /api/health/llm
```

If `GEMINI_API_KEY` is empty, the app safely falls back to rule-based report generation.

## Tracking Rule

Every meaningful project update should be recorded in [docs/TRACK.md](docs/TRACK.md), including what changed, what was verified, and which requirement gaps remain.
