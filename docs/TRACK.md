# HealthGuard AI Track Doc

This document is the running implementation record for HealthGuard AI. Update it for every meaningful change so future work stays traceable.

## Current Branch

- `version-1.0`

## Source Requirement

- `HealthGuard AI Requirement Document.pdf`
- Extracted on 2026-06-23.

## Update Log

### 2026-06-27 - User-specific saved reports view

Implemented:

- Updated `/api/reports` to return only reports owned by the logged-in account.
- Kept doctor/dietician patient queues separated under `/api/doctor/reports/pending`.
- Removed patient-facing Approve action from Saved reports.
- Added a Saved reports privacy note explaining that the list is account-specific.

Verified:

- Added regression coverage proving a doctor's regular Saved reports endpoint does not expose another patient's report.
- `python -m pytest` passed with 25 tests.
- `node --check frontend\app.js` passed.

### 2026-06-26 - Structured diet plan suggestions

Implemented:

- Added a dedicated `diet_plan` section to generated reports.
- Added practical meal-structure guidance: plate method, meal timing, protein, fiber, hydration, and foods to prefer/limit.
- Added condition-aware diet guidance for sugar/metabolic risk, BP/heart/lipid risk, kidney concerns, acidity/reflux, fever/weakness, and hot-weather hydration.
- Updated frontend report rendering and PDF downloads to include the diet plan.

Verified:

- `python -m pytest` passed with 25 tests.
- `node --check frontend\app.js` passed.

### 2026-06-26 - Improved wellness, activity, and doctor guidance

Implemented:

- Added structured report sections for feel-better precautions, physical activity plan, and which doctor/department to consult.
- Added rule-based wellness guidance for fever/infection symptoms, stress/sleep issues, metabolic risk, hydration, rest, and self-medication safety.
- Added problem-specific activity suggestions for desk-work strain, metabolic risk, stress/sleep, breathing concerns, fever/acute illness, and emergency red flags.
- Added department routing for General Physician/Internal Medicine, Cardiology, Endocrinology, Pulmonology, Orthopedics/Physiotherapy, Gastroenterology, Nephrology/Urology, Dermatology, Ophthalmology, Psychiatry/Psychology/Sleep Medicine, Gynecology, and Dentistry.
- Updated the report UI and PDF output to show these sections.

Verified:

- `python -m pytest` passed with 25 tests.
- `node --check frontend\app.js` passed.

### 2026-06-26 - One-time uploaded document context

Implemented:

- Fixed stale uploaded-file data reappearing from browser `localStorage`.
- Scoped uploaded document context by logged-in user instead of using one shared browser key.
- Cleared uploaded document context after a successful report generation because uploads are meant to support only the next report.
- Cleared user-specific uploaded document context on logout/session switch.

Verified:

- `node --check frontend\app.js` passed.

### 2026-06-26 - Doctor patient-problem monitor

Implemented:

- Added doctor-facing report metadata for patient problem summary, top risk factors, suggested doctor questions, and uploaded-document context.
- Updated patient folder cards so doctors can see the patient problem directly in the monitor view before opening the PDF.
- Added compact clinical styling for the patient problem area in doctor report folders.
- Added a local Chrome DevTools capture utility for doctor monitor screenshots.

Verified:

- `python -m pytest` passed with 25 tests.
- `node --check frontend\app.js` passed.
- `node --check scripts\capture_doctor_monitor_screenshot.mjs` passed.
- Captured doctor patient-problem screenshots in `outputs/doctor-patient-problem.png` and `outputs/doctor-patient-problem-focused.png`.

### 2026-06-26 - Uploaded-file relevant suggestions

Implemented:

- Enhanced document upload processing to extract structured health signals from patient files.
- Added detected topics for common labs, conditions, medication mentions, and emergency terms.
- Added safe relevant suggestions based on uploaded findings, including diabetes/glucose, lipid, thyroid, kidney, hemoglobin/anemia, vitamin D, and emergency-symptom review.
- Added doctor-question generation from uploaded file findings.
- Added medication-safety handling so uploaded medication mentions produce clinician-review guidance, not prescriptions or dose changes.
- Added safety alerts for emergency terms found in uploaded files.
- Added uploaded-file suggestions into `tuned_context` so RAG/chat/report generation receives the safer structured interpretation.
- Updated the frontend document panel to display extracted summary, safety alerts, detected topics, relevant suggestions, and doctor questions after upload.

Verified:

- Added regression coverage proving uploaded lab/condition content produces relevant suggestions and does not prescribe medication.
- `python -m pytest` passed with 25 tests.
- `node --check frontend\app.js` passed.
- Backend AST syntax check passed.

### 2026-06-26 - MIMIC-IV demo RAG ingestion

Implemented:

- Added `scripts/ingest_mimic_iv_demo_rag.py` to download MIMIC-IV Clinical Database Demo 2.2 files from PhysioNet.
- Added resilient streaming download with retries and `.part` cleanup support.
- Added curated default ingestion for useful clinical/demo tables, with optional `--all` mode for full official-file download.
- Added `--no-download` mode to index already-downloaded official files when the network is unreliable.
- Indexed MIMIC table summaries as global RAG knowledge using source type `mimic_iv_demo_approved_public_dataset`.
- Summaries include table purpose, row counts, columns, common admission categories, diagnosis concepts, procedure concepts, lab concepts, microbiology concepts, OMR data, README, and license text.
- Avoided indexing every raw patient event row as an individual vector; the RAG receives safe, bounded summaries for retrieval.
- Added `data/mimic-iv-demo/` to `.gitignore` so downloaded dataset artifacts stay local.

Verified:

- Downloaded and indexed 16 official MIMIC-IV demo files that completed successfully.
- Added 16 MIMIC RAG documents and 38 RAG chunks.
- RAG status now reports 20 total documents and 42 total chunks including existing internal guidance.
- Verified retrieval returns MIMIC admissions, lab, diagnosis, README, and license context for a clinical query.

### 2026-06-26 - First-login application tour

Implemented:

- Added a guided application tour modal for first successful login/email verification.
- Added per-user local storage tracking so the tour appears once per user.
- Added a dashboard `Tour` menu button so users can reopen the walkthrough anytime.
- Added six guided steps covering workspace purpose, assessment, voice intake, document upload, report generation, saved reports, and clinician workflow.
- Added section scrolling and visual highlighting for the active tour step.
- Added tour navigation controls: Previous, Next/Finish, Skip, close button, backdrop close, and Escape key close.
- Closed the tour safely on logout.

Verified:

- `node --check frontend\app.js` passed.
- `python -m pytest` passed with 24 tests.

### 2026-06-26 - Hugging Face LLM provider

Implemented:

- Added Hugging Face Inference Providers support as a live LLM provider.
- Added `LLM_PROVIDER=huggingface` / `LLM_PROVIDER=hf` routing in `LLMService`.
- Added `HF_TOKEN` and `HUGGINGFACE_API_KEY` credential support.
- Added `HUGGINGFACE_MODEL`, `HUGGINGFACE_BASE_URL`, and `HUGGINGFACE_MAX_TOKENS` configuration.
- Used the OpenAI-compatible Hugging Face chat-completions endpoint at `/chat/completions`.
- Preserved the existing JSON-schema response contract for report generation and chatbot answers.
- Added robust JSON extraction for Hugging Face `choices[].message.content` responses.
- Updated `.env.example` and README with Hugging Face configuration.
- Added Hugging Face ASR/Whisper speech transcription service for voice input.
- Added `/api/health/speech` to inspect speech transcription configuration.
- Added `/api/voice/transcribe` to receive recorded browser audio and return a transcript.
- Changed the voice UI to prefer local browser audio recording with `MediaRecorder`, then server-side Hugging Face transcription, avoiding browser speech-service network failures.
- Preserved the old browser SpeechRecognition path as a fallback when MediaRecorder is unavailable.
- After transcription, the UI automatically sends the transcript through the existing chat/RAG flow and reads the answer aloud.
- Added Hugging Face ASR retry handling for transient 429/5xx/network/model-loading failures.
- Added configurable ASR fallback models with `HUGGINGFACE_ASR_FALLBACK_MODELS`.
- Added `X-Wait-For-Model` on ASR requests to reduce cold-start failures.
- Added minimum audio-size validation and frontend minimum recording-duration guidance to avoid intermittent empty/too-short recordings.

Verified:

- Added a mocked Hugging Face provider regression test that validates endpoint, bearer token, model, JSON schema payload, and parsed output.
- Added a mocked Hugging Face ASR regression test for `/api/voice/transcribe`.
- `python -m pytest` passed with 24 tests.
- `node --check frontend\app.js` passed.
- Backend AST syntax check passed with `python -B`.

### 2026-06-25 - Voice assistant intake and read-aloud response

Implemented:

- Added a Voice menu item and dashboard voice assistant panel.
- Added microphone controls for start, stop, submit, read answer, and clear.
- Added browser speech-recognition support using the Web Speech API.
- Extracted common spoken patient details into the assessment form when fields are empty, including age, height, weight, sleep hours, location, climate, smoking, alcohol, diet pattern, symptom, severity, and duration.
- Sent the cleaned transcript through the existing authenticated chat endpoint, which uses safety checks and supporting knowledge/RAG retrieval.
- Included uploaded document context in the voice question when a patient has attached a document.
- Added browser text-to-speech playback for the generated answer.
- Added safe output escaping for voice transcript, answer, sources, and disclaimer rendering.
- Hardened microphone capture with explicit browser microphone permission preflight.
- Added clearer voice-recognition error messages for blocked permission, missing microphone, no speech, network/service blocks, and unsupported browsers.
- Added a typed-transcript fallback path so patients can still submit the voice text manually if browser speech capture is blocked.

Verified:

- `node --check frontend\app.js` passed.
- `python -m pytest` passed with 22 tests.

### 2026-06-25 - PDF, clinical workflow, audit, and security hardening

Implemented:

- Replaced the basic one-page PDF output with a branded, multi-section report export.
- Added PDF section formatting, footer pagination, risk-score chart text, evidence sources, disclaimer, and doctor-review metadata.
- Added clinician review workflow fields for assigned reviewer, priority, lifecycle status, clinician signature, escalation reason, and review history.
- Added doctor APIs for report assignment and review-history retrieval.
- Expanded doctor review updates to persist comments, clinical notes, signatures, priority, escalation reasons, timestamps, and lifecycle history.
- Added additive SQLite/PostgreSQL schema migration columns for clinical workflow and compliance metadata.
- Added PHI encryption at rest for stored patient profiles, assessments, and report JSON, with backward-compatible decryption on read.
- Added audit PII masking, user/IP/user-agent metadata, immutable marker, retention date, previous-hash chaining, and event hashes.
- Added filtered audit log retrieval and CSV/JSON audit export.
- Added upload security scanning for size limits, unsupported/executable file types, executable signatures, and the EICAR antivirus test signature.
- Added rate limiting for registration, login, confirmation resend, report generation, and document upload.
- Added secure session-cookie issuance plus a CSRF token endpoint; cookie-authenticated writes are guarded when cookie auth is explicitly enabled.

Verified:

- Added regression coverage for blocked upload scanning, audit hash/metadata/export behavior, PHI encryption at rest, doctor assignment, status lifecycle, signatures, escalation, review history, and PDF review metadata.
- `python -m pytest` passed with 22 tests.
- `node --check frontend\app.js` passed.
- Backend AST syntax check passed with `python -B`.

### 2026-06-25 - Figma architecture diagram

Implemented:

- Created an editable FigJam architecture diagram for HealthGuard AI.
- Diagram covers the web UI, FastAPI routes, auth/RBAC, report generation, document extraction, RAG retrieval, doctor review, admin/audit, PDF export, PostgreSQL/SQLite, RAG tables, reports/assessments, audit logs, Gemini, SMTP, Google OAuth, and optional future file-processing jobs.
- Added a more complete senior-level end-to-end architecture flow to the same FigJam file after review feedback.
- The detailed flow now covers user entry points, API layer, registration/email verification/SSO, session and role guards, patient intake validation, optional document upload, RAG extraction/chunking/embedding/retrieval, deterministic safety rules, Gemini prompt/response/failure path, report persistence, saved reports, PDF export, doctor review, admin knowledge, and compliance audit access.
- Added a corrected end-to-end architecture diagram after checking the FigJam readback and identifying missing/unclear connections.
- The corrected diagram explicitly connects SMTP confirmation, Google OAuth token exchange, verified session creation, dashboard unlock, mandatory intake validation, profile persistence, document upload to patient RAG chunks, admin knowledge to global RAG indexing, Gemini success/failure paths, report/audit persistence, saved reports, PDF download, doctor review updates, compliance audit view, and health-check dependencies.
- Removed old/duplicate FigJam diagrams and regenerated a single clean current architecture diagram.
- Replaced the board with a final full architecture diagram using `Complete ...` sections and removed remaining previous diagram sections.
- Removed all previous FigJam content and created a fresh end-to-end flow diagram from an empty board.
- The fresh diagram is organized into 11 numbered sections: users, frontend, FastAPI routes, authentication/authorization, patient intake, document/RAG ingestion, safety/report engine, retrieval/LLM, database persistence, external services, and outputs/operations.

Verified:

- Generated successfully in Figma/FigJam using the architecture diagram layout.
- Generated the detailed end-to-end flow successfully in Figma/FigJam.
- Verified the corrected FigJam diagram readback includes the key missing connection paths.
- Verified the FigJam board now contains only the `Current ...` architecture sections and active connectors for the final diagram.
- Verified the FigJam board now contains only the `Complete ...` architecture sections with active connector lines for the full architecture diagram.
- Verified the FigJam board was cleared first and now contains only the fresh numbered end-to-end flow with active connector lines.
- Figma link: `https://www.figma.com/board/s9W4ClPD6VDAPzDeK4RRgK`

### 2026-06-25 - Client architecture presentation

Implemented:

- Added `scripts/generate_client_presentation.py` to generate a reusable client-demo PowerPoint deck.
- Created `outputs/HealthGuard_AI_Client_Architecture_Demo.pptx` with 20 slides covering product overview, system architecture, backend layers, authentication, roles, assessment data, report generation, RAG, Gemini integration, database design, privacy, API surface, document extraction, testing, deployment, security, and roadmap.
- Embedded the HealthGuard AI logo and included editable architecture/flow diagrams using PowerPoint shapes and connector lines.

Verified:

- Generated PPTX successfully with 20 slides.
- Validated required PPTX package parts, slide XML parsing, and embedded logo presence.

### 2026-06-25 - Interview guide PDF export

Implemented:

- Created `docs/HealthGuard_AI_Interview_Guide.pdf` from `docs/INTERVIEW_GUIDE.md`.
- Exported the senior engineering interview guide as an 11-page PDF with headings, bullets, code blocks, and page footers.

Verified:

- Confirmed the file has a valid PDF header and EOF marker.
- Confirmed `pypdf` can read all 11 pages and extract first-page text.

### 2026-06-25 - Senior engineer interview documentation

Implemented:

- Added `docs/INTERVIEW_GUIDE.md` with senior software engineer interview explanations.
- Covered architecture, modules, authentication, roles, RAG, LLM, report generation, database design, privacy, testing, limitations, production improvements, and cross-question answers.

Verified:

- Documentation created in the project docs folder.

### 2026-06-25 - Wide dashboard space usage

Implemented:

- Expanded the authenticated dashboard shell from a narrow max width to a wider `1680px` workspace.
- Adjusted assessment/documents column sizing to use wide screens more effectively.
- Stretched the right-side documents and saved-reports stack so it fills vertical space beside the assessment form.
- Gave Saved reports a larger flexible panel area.

Verified:

- `node --check frontend\app.js` passed.
- `python -m pytest` passed with 20 tests.
- Confirmed the running stylesheet serves the wider shell and stretched grid rules.

### 2026-06-25 - Complete local RAG pipeline

Implemented:

- Added persistent RAG tables for documents and chunks.
- Added document chunking with overlap.
- Added deterministic local embedding generation.
- Added cosine similarity semantic retrieval and chunk ranking.
- Indexed uploaded patient documents into per-user RAG storage.
- Indexed approved internal knowledge as global RAG context.
- Connected report and chat generation to semantic RAG retrieval.
- Added `/api/health/rag` to report RAG status, vector store, embedding provider, and chunk counts.
- Preserved per-patient document isolation so one patient's uploaded context is not retrieved for another patient.

Verified:

- Added regression coverage proving uploaded documents are indexed, retrieved semantically, and isolated per patient.
- `python -m pytest` passed with 20 tests.
- Backend syntax check passed.
- `node --check frontend\app.js` passed.

### 2026-06-25 - Google SSO token endpoint connectivity check

Implemented:

- Added `/api/health/google-sso` to verify Google SSO configuration without exposing secrets.
- Health check reports client ID presence, client secret presence, redirect URI, and Google token endpoint reachability.
- Restarted the app with outbound network access so the callback can exchange OAuth codes with Google.

Verified:

- `python -m pytest` passed with 19 tests.
- Backend syntax check passed.
- `/api/health/google-sso` reports `configured: true` and `token_endpoint_reachable: true`.
- `/api/auth/sso/google/start` returns a Google authorization URL.

### 2026-06-24 - Google SSO configuration reload fix

Implemented:

- Added targeted SSO environment reload so Google client ID, secret, and redirect URI are read from `.env`.
- Avoided broad `.env` override so SMTP/test environment behavior remains intact.
- Restarted the app so the updated Google SSO configuration is active.

Verified:

- `python -m pytest` passed with 19 tests.
- Backend syntax check passed.
- `/api/auth/sso/google/start` now returns `configured: true` and a Google authorization URL.

### 2026-06-24 - Google SSO callback implementation

Implemented:

- Added real Google OAuth callback support when `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` are configured.
- Added Google token exchange and userinfo lookup using the configured OAuth credentials.
- Added local SSO user creation/update with verified email and demo session creation.
- Added callback handoff page that stores the demo session and redirects back to the app.
- Updated `.env.example` and local `.env` with explicit SSO client secret and redirect URI keys.
- Improved unconfigured Google SSO response to include the required callback URL.

Verified:

- `python -m pytest` passed with 19 tests.
- Backend syntax check passed.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001`.
- Confirmed Google SSO start reports missing `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` while credentials are blank.

### 2026-06-24 - Hide role tools for patients

Implemented:

- Marked Role tools navigation, hero shortcut, and role panel as role-only UI.
- Hid role-only UI for patient users after login.
- Kept Role tools visible for doctor, dietician, admin, and compliance users.
- Updated patient dashboard subtitle to focus on assessment, documents, and own saved reports.
- Added a guard so hidden role-only scroll targets cannot be activated.

Verified:

- `node --check frontend\app.js` passed.
- `python -m pytest` passed with 19 tests.
- Confirmed served HTML includes role-only markers.

### 2026-06-24 - Patient report privacy and doctor folders

Implemented:

- Bound newly generated patient reports to the logged-in patient user.
- Filtered Saved reports so patient users only see their own reports.
- Protected report detail and PDF download endpoints from cross-patient access.
- Kept doctor, dietician, admin, and compliance roles able to view review queues.
- Added doctor review grouping by patient folder through `patient_folders`.
- Updated the doctor role UI to render pending reports under separate patient folders.
- Added regression coverage for patient X not seeing or downloading patient Y's report.

Verified:

- `python -m pytest` passed with 19 tests.
- `node --check frontend\app.js` passed.
- Backend syntax check passed.
- Restarted the app on `http://127.0.0.1:8001`; health endpoint is OK.

### 2026-06-24 - Gemini transient overload retry cleanup

Implemented:

- Increased Gemini retry patience for transient 429/5xx/connection failures.
- Collapsed duplicate retry errors so failures show one clear message per model.
- Preserved primary `gemini-2.5-flash` with fallback to `gemini-2.5-flash-lite`.
- Updated local `.env` and `.env.example` retry settings.

Verified:

- Live full report-generation check succeeded after retry/fallback with generation engine `gemini:gemini-2.5-flash-lite`.
- `python -m pytest` passed with 18 tests.
- Backend syntax check passed.

Note:

- Final app restart with outbound network access was blocked by Codex usage-limit approval. Restart locally to load this change into the running browser app.

### 2026-06-24 - Gemini report reliability hardening

Implemented:

- Restarted the local app server with outbound network access so report generation can call Gemini.
- Added Gemini fallback models via `GEMINI_FALLBACK_MODELS`.
- Added short retry settings for transient Gemini 429/5xx/connection failures.
- Compacted the report enhancement prompt so full report generation is less likely to hit provider overload.
- Kept the hard-fail rule: if all Gemini attempts fail, no report is created or saved.

Verified:

- Live full report-generation check succeeded with generation engine `gemini:gemini-2.5-flash`.
- `python -m pytest` passed with 18 tests.
- `/api/health/llm` reports provider `gemini`, model `gemini-2.5-flash`, and `configured: true`.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-24 - Gemini generateContent endpoint fix

Implemented:

- Switched Gemini calls from the experimental interactions endpoint to the standard `models/{model}:generateContent` REST endpoint.
- Added Gemini response-schema conversion for the standard endpoint.
- Added parsing for standard Gemini `candidates[].content.parts[].text` responses.
- Preserved hard-fail report behavior: report generation still stops and returns HTTP 503 if Gemini fails.

Verified:

- Live Gemini smoke test succeeded with generation engine `gemini:gemini-2.5-flash`.
- `python -m pytest` passed with 18 tests.
- `node --check frontend\app.js` passed.
- `/api/health/llm` reports provider `gemini`, model `gemini-2.5-flash`, and `configured: true`.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-24 - Stop report generation on LLM failure

Implemented:

- Removed rules-based fallback for report generation when a configured LLM fails.
- Added `ReportLLMError` so failed Gemini report generation returns HTTP 503 with provider, model, and error details.
- Ensured failed LLM report generation does not save a report or assessment.
- Updated frontend API error formatting so the report section shows provider/model/error details clearly.
- Added regression coverage proving a configured LLM failure stops report generation.

Verified:

- `/api/health/llm` reports provider `gemini`, model `gemini-2.5-flash`, and `configured: true`.
- `python -m pytest` passed with 18 tests.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-24 - Gemini LLM provider migration

Implemented:

- Replaced the default OpenAI LLM provider with Gemini.
- Added Gemini REST integration for JSON report and chat enhancement.
- Updated `.env.example`, local `.env`, and README configuration to use `GEMINI_API_KEY` and `GEMINI_MODEL`.
- Updated the LLM environment loader path so workspace `.env` values override stale OS-level LLM variables.
- Switched the live model to `gemini-2.5-flash` after `gemini-3.5-flash` returned a temporary provider high-demand error.

Verified:

- `/api/health/llm` reports provider `gemini`, model `gemini-2.5-flash`, and `configured: true`.
- Live Gemini smoke test passed and returned generation engine `gemini:gemini-2.5-flash`.
- `python -m pytest` passed with 17 tests.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-24 - Saved reports pagination

Implemented:

- Added client-side pagination for Saved reports.
- Shows 5 saved reports per page with Previous and Next controls.
- Resets Saved reports to page 1 after login, refresh, report generation, or doctor review.
- Added disabled button styling for pagination controls.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running frontend script includes saved-report pagination controls.
- Confirmed the running stylesheet includes pagination and disabled button styles.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Report section anchored at page bottom

Implemented:

- Added a dedicated bottom-section class to the generated report panel.
- Styled the generated report as a full-width bottom panel after the workspace grid.
- Preserved the Saved reports section in its existing dashboard placement.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page serves `dashboard-bottom-section`.
- Confirmed the generated report panel appears after the workspace grid in the running HTML.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Generated report reveal and scroll fix

Implemented:

- Hid the generated report panel on initial page load so the bottom output area only appears when needed.
- Revealed the generated report panel after required assessment fields pass validation.
- Kept the Saved reports placement unchanged in the dashboard side-stack.
- Waited for saved-report refresh to finish before scrolling to the generated report output.
- Made Reports navigation reveal the generated report area when users explicitly open that section.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page serves the hidden `reports-panel` with the `Generated report` heading.
- Confirmed the running frontend script includes the reveal and `requestAnimationFrame` scroll behavior.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Generated report bottom placement

Implemented:

- Moved only the generated report output panel to the bottom of the page after the workspace section.
- Kept Saved reports in its existing side-stack placement.
- Added automatic smooth scroll to the generated report after successful report generation.
- Renamed the output header to Generated report for clearer placement.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page includes the bottom `generated-report-panel` at `http://127.0.0.1:8001`.
- Confirmed the running frontend script includes the post-generation scroll behavior.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Live LLM key check and quota fallback

Implemented:

- Verified the local `.env` contains an `OPENAI_API_KEY` without printing the secret.
- Restarted the app so the key is loaded.
- Added graceful fallback when a live LLM provider returns an error.
- Added `llm_error` to generated reports so quota/auth/provider errors are visible in the UI.
- Chat now falls back to the safe rule-based answer if the LLM provider errors.

Verified:

- `/api/health/llm` reports `configured: true`, provider `openai`, model `gpt-4.1-mini`.
- A live OpenAI smoke test reached OpenAI but failed with `429 insufficient_quota`.
- `python -m pytest` passed with 17 tests.
- `python -B -c "... ast.parse ..."` parsed 22 backend Python files successfully.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-24 - LLM integration wiring

Implemented:

- Added an OpenAI Responses API integration service using configured environment variables.
- Added `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and `LLM_TIMEOUT_SECONDS` configuration keys.
- Added `/api/health/llm` to show whether live LLM usage is configured.
- Connected report generation to LLM enhancement when an API key is present.
- Connected health chat responses to LLM enhancement when an API key is present.
- Added report fields for `llm_summary` and `generation_engine`.
- Updated the report UI to show AI summary and generation engine after report generation.
- Added test-mode coverage for LLM-enhanced report generation and LLM status.

Verified:

- `python -m pytest` passed with 17 tests.
- `python -B -c "... ast.parse ..."` parsed 22 backend Python files successfully.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001`.
- Confirmed `/api/health/llm` currently reports `configured: false` because `OPENAI_API_KEY` is not set.

### 2026-06-24 - Dashboard button functionality audit

Implemented:

- Converted decorative hero workflow labels into functional buttons.
- Converted workflow summary cards into clickable buttons.
- Wired Role workflows to Role tools, Self-service intake to Assessment, Report export to Reports, Patient Info First to Assessment, Upload Files to Documents, and Safety Alerts to Reports.
- Added hover/focus-visible states so interactive cards and hero controls are clear and accessible.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page contains functional `data-scroll-target` controls for hero actions and workflow cards at `http://127.0.0.1:8001`.
- Confirmed the running app serves the updated interactive-control CSS at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Workspace grid empty-space fix

Implemented:

- Fixed the remaining empty-space issue caused by CSS Grid auto-placement mixing tall assessment content with shorter supporting cards.
- Changed the main app shell into a vertical page stack.
- Added a dedicated `workspace-grid` wrapper to control only the assessment/supporting-card two-column area.
- Kept assessment and supporting panels aligned without browser-created row gaps.
- Added responsive behavior so `workspace-grid` stacks cleanly on smaller screens.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page includes the new `workspace-grid` structure at `http://127.0.0.1:8001`.
- Confirmed the running app serves the updated layout CSS at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Readable glass refinement and tighter spacing

Implemented:

- Replaced low-contrast white hero text with dark navy text on a light glass hero surface.
- Kept colorful highlight treatment through orange, cyan, and violet accents instead of relying on white text.
- Tightened spacing between workflow cards, panels, and form fields.
- Reduced panel padding and form gaps so tabular/form content is more compact and aligned.
- Preserved the bright screenshot-inspired background while improving readability and professional polish.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running app serves the updated readable-glass CSS at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Screenshot-matched bright glass dashboard

Implemented:

- Reworked the logged-in page toward the provided screenshot: glass top navigation, shield-plus brand mark, dark translucent hero card, bright wave-style background, and three workflow tiles under the hero.
- Replaced the logo image in the dashboard nav with a CSS shield/cross mark to match the screenshot style.
- Simplified the hero to show welcome text, workflow tags, a single primary Start assessment action, and a top-right Logout button.
- Added workflow cards for Patient Info First, Upload Files, and Safety Alerts.
- Added a screenshot-style background with blue, cyan, purple, pink, and orange wave layers.
- Added responsive handling so the new workflow cards stack on smaller screens.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page includes the new shield, hero tags, and workflow cards at `http://127.0.0.1:8001`.
- Confirmed the running app serves the screenshot-style CSS at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - BootstrapMade Clinic-inspired home adaptation

Implemented:

- Adapted the logged-in home hero toward a medical clinic template style with trust badges, large healthcare headline, stats, and clear workflow calls to action.
- Added clinic-style badges for verified access, educational safety checks, and doctor-ready reports.
- Added home hero stats for role workflows, self-service intake, and PDF export.
- Updated feature cards into numbered workflow cards for guided intake, document support, and safety review.
- Shifted the color system slightly toward a clinic-style blue/teal palette while retaining limited violet/pink accents.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page includes the new clinic badges, stats, and workflow cards at `http://127.0.0.1:8001`.
- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-24 - Bootstrap styling and brighter readable UI

Implemented:

- Added Bootstrap 5.3.3 CSS and JS bundle to the frontend.
- Applied Bootstrap navbar, nav-pills, and shadow utilities to the authenticated dashboard structure.
- Brightened the page background with stronger pink, blue, violet, cyan, and teal gradient mixing.
- Increased text contrast across labels, report text, menu items, form fields, and panel content.
- Made panels more visible with brighter white surfaces, stronger gradient borders, and deeper shadows.
- Improved input visibility with clearer borders and subtle inset depth.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running page includes Bootstrap assets and Bootstrap classes at `http://127.0.0.1:8001`.
- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-23 - Template-style hero upgrade

Implemented:

- Reworked the authenticated home area from a basic dashboard welcome card into a template-style hero section.
- Added large landing-page typography, stronger visual hierarchy, a role workflow headline, and polished quick action placement.
- Added three visual feature tiles for guided intake, document support, and safety-first review.
- Updated the hero gradient with pink, violet, blue, cyan, and teal accents inspired by modern Wix/Canva-style templates.
- Adjusted responsive behavior so the hero stacks cleanly on smaller screens.

Verified:

- `node --check frontend\app.js` passed.
- Confirmed the running app serves the updated hero markup and CSS at `http://127.0.0.1:8001`.

### 2026-06-23 - Canva-inspired multi-color dashboard style

Implemented:

- Added a dynamic multi-color page background inspired by pink, white, and blue gradient website templates.
- Introduced pink, violet, cyan, blue, and teal accents while preserving readable clinical panels.
- Added subtle animated background movement using broad gradient bands.
- Applied gradient borders to the dashboard menu and panels for a more polished modern look.
- Updated buttons, selected food chips, upload area, and status pills to match the new color system.

Verified:

- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- `node --check frontend\app.js` passed.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-23 - Attractive layered page background

Implemented:

- Replaced the flat dashboard background with a layered clinical blue/green page background.
- Added fixed background attachment so the visual treatment stays stable while scrolling.
- Made dashboard panels and the menu slightly translucent with blur so they integrate with the new background while keeping text readable.

Verified:

- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-23 - Dashboard whitespace and color balance cleanup

Implemented:

- Removed the large empty right-side space by grouping Documents, Report, Saved reports, and Role tools into a stacked right rail beside the assessment form.
- Adjusted dashboard column sizing so the long assessment form and supporting panels use the page width more efficiently.
- Refined the color mix toward navy and clinical blue, with teal used as a restrained accent.
- Reduced panel padding slightly and softened supporting panel backgrounds for a tighter professional layout.

Verified:

- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- `node --check frontend\app.js` passed.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-23 - Professional dashboard visual refresh

Implemented:

- Refined the authenticated dashboard color palette with a calmer clinical mix of navy, blue, white, and restrained teal.
- Reworked the top menu into a normal dashboard header instead of a sticky overlay.
- Improved home panel hierarchy with a professional gradient band, smaller logo, softer buttons, and better contrast.
- Reduced heavy shadows and tightened spacing across panels, forms, upload controls, and selected food chips.
- Improved input focus states and catalog styling for a cleaner product-grade form experience.

Verified:

- Confirmed the running app serves the updated stylesheet at `http://127.0.0.1:8001/static/styles.css`.
- Confirmed the app health endpoint is responding at `http://127.0.0.1:8001/api/health`.

### 2026-06-23 - Mandatory assessment fields and professional food catalog

Implemented:

- Removed system-entered/demo values from the patient assessment form.
- Made report generation require user-entered mandatory fields before any report request is sent.
- Added backend validation so incomplete assessment API calls are rejected before report generation.
- Replaced free-text diet notes with a professional food catalog: food group, food item, add-to-list, and removable selected food chips.
- Passed selected foods as a structured list to the backend for risk scoring and report generation.
- Kept uploaded document support as optional supporting context while removing user-facing technical wording.

Verified:

- `python -m pytest` passed with 16 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001`.
- Confirmed the served page includes the food catalog and no longer includes the old demo assessment values.

### 2026-06-23 - Functional report basis and patient-friendly home copy

Implemented:

- Removed technical RAG/LLM wording from the visible home/dashboard document upload experience.
- Expanded patient intake with gender, height, weight, climate, diet pattern, water intake, smoking, alcohol, symptom severity/duration, existing conditions, family history, medications, and allergies.
- Updated report payload generation so structured patient, diet, lifestyle, and symptom data is sent to the backend.
- Improved risk scoring to account for smoking, alcohol, specific existing-condition markers, family-history markers, diet pattern, hydration, and symptom severity/duration.
- Improved guidance generation for tobacco exposure, frequent alcohol, low protein/vegetable intake, and late-night eating.
- Added a regression test proving structured patient inputs drive report risk factors.

Verified:

- `python -m pytest` passed with 15 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001` and confirmed the live page includes the new fields without visible RAG/LLM wording.

### 2026-06-23 - Dashboard menu and optional document RAG upload

Implemented:

- Added a sticky logged-in workspace menu with Home, Assessment, Documents, Reports, and Role tools actions.
- Updated the home panel with quick action buttons for assessment, document upload, report history, and role tools.
- Added an optional document upload panel for TXT, Markdown, CSV, JSON, PDF, and DOCX files.
- Extracted uploaded document text, tuned it into bounded RAG context, and attached it to the next report when present.
- Added uploaded document context as a report source so clinicians can see user-provided context separately from approved internal guidance.
- Added a regression test for document upload feeding report RAG context.

Verified:

- `python -m pytest` passed with 14 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.
- `node --check frontend\app.js` passed.
- Restarted the app on `http://127.0.0.1:8001` and confirmed the served HTML/JS includes the new menu and upload features.

### 2026-06-23 - Pending registration retry fix

Implemented:

- Updated registration to remove an existing unverified pending account before retrying the same email.
- Preserved duplicate protection for already verified users.
- Cleared the local demo database so registration and login start fresh.
- Added a regression test for retrying registration with the same unverified email.

Verified:

- `python -m pytest` passed with 13 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.
- Confirmed local SQLite database has `users = 0` and `email_outbox = 0`.
- Restarted the app on `http://127.0.0.1:8001`.

### 2026-06-23 - Confirmation popup reliability

Implemented:

- Made the email confirmation modal force its visible display state when registration succeeds.
- Added a fallback "Open confirmation popup" action in the auth status message for pending verification.
- Guarded modal event handlers so missing or delayed DOM nodes do not break the auth page script.

Verified:

- `python -m pytest` passed with 12 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.
- Confirmed the running app serves the updated popup code at `http://127.0.0.1:8001/static/app.js`.

### 2026-06-23 - Professional auth template and confirmation modal

Implemented:

- Reduced the logo size and moved it to a corner brand position.
- Refreshed the auth page color palette and layout.
- Removed the always-visible email confirmation code block from the front page.
- Added a modal dialog for entering the 6-digit confirmation code.
- Opens the confirmation modal only after successful registration or resend.
- Added modal close/backdrop behavior.

Verified:

- `python -m pytest` passed with 12 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.

### 2026-06-23 - Application logo

Implemented:

- Added the provided HealthGuard AI logo image to `frontend/assets/healthguard-logo.png`.
- Used the logo in the authentication hero.
- Used the logo in the authenticated dashboard header.
- Added the logo as the browser favicon.

Verified:

- Logo asset exists and is served from the static frontend directory.
- `python -m pytest` passed with 12 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.

### 2026-06-23 - Registration requires successful email delivery

Implemented:

- Registration now sends the confirmation email before creating the user.
- If SMTP is not configured or email sending fails, registration returns an error and no user record is created.
- Resend confirmation now updates the verification code only after email sending succeeds.
- Added explicit SMTP test mode for automated tests.
- Added regression coverage proving no user is created when SMTP is unavailable.

Verified:

- `python -m pytest` passed with 12 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.

### 2026-06-23 - PostgreSQL local database support

Implemented:

- Added `DATABASE_URL` support for PostgreSQL.
- Added `psycopg[binary]` dependency.
- Refactored persistence adapter to use PostgreSQL when `DATABASE_URL` starts with `postgresql://` or `postgres://`.
- Preserved SQLite as fallback/test storage when `DATABASE_URL` is empty.
- Added PostgreSQL-compatible schema creation.
- Added `GET /api/health/db` to inspect the active database backend.
- Updated `.env.example` and README with local PostgreSQL configuration.

Verified:

- `python -m pytest` passed with 11 tests.
- `python -B -c "... ast.parse ..."` parsed 21 backend Python files successfully.

Notes:

- Local PostgreSQL is reachable on `localhost:5432`, but default `postgres/postgres` credentials failed. A valid local username, password, and database name are required to complete live configuration.

### 2026-06-23 - Six-digit email code and professional auth UI

Implemented:

- Registration now creates an unverified account and does not return a dashboard session.
- Added stronger email format/domain validation and blocked placeholder domains such as `example.com`.
- Replaced long confirmation tokens with 6-digit numeric email confirmation codes.
- Added local email outbox plus optional SMTP sending via environment variables.
- Added confirmation endpoints:
  - `GET /api/auth/verify-email`
  - `POST /api/auth/verify-email`
  - `POST /api/auth/resend-confirmation`
  - `GET /api/auth/dev/outbox` for local demo verification
- Login now rejects users until email confirmation succeeds.
- Protected dashboard/session access checks `email_verified`.
- Added SSO start scaffolds:
  - Google
  - Facebook
  - Instagram
- Added SSO callback scaffold with provider configuration message.
- Updated frontend:
  - professional split authentication layout
  - registration no longer opens the dashboard immediately
  - user must confirm the 6-digit code first
  - resend/load demo code controls
  - branded SSO buttons for Google, Facebook, and Instagram
- Added frontend API error formatting so invalid-email validation shows the HTTP status and field message, for example `Error 422: email: Enter a valid email address.`
- Added client-side registration email preflight so invalid email/domain values do not call `/auth/register`.
- Tightened backend email-domain validation for typo domains such as `gmail.con`.
- Added regression coverage proving invalid email domains do not create confirmation outbox records.
- Removed the user-facing "Load demo code" bypass so mailbox ownership can only be proven by entering the code received through real email delivery.
- Updated registration/resend messaging to distinguish real SMTP delivery from local development queueing.
- Added `.env` loading support for SMTP configuration.
- Added `.env.example` with Gmail SMTP/app-password guidance.
- Added `GET /api/auth/email/status` to verify whether SMTP settings are configured.

Verified:

- `python -m pytest` passed with 11 tests.
- `python -B -c "... ast.parse ..."` parsed 20 backend Python files successfully.

Notes:

- Real outbound email requires SMTP environment variables.
- Live SSO requires provider app credentials, secrets, and token exchange implementation.

### 2026-06-23 - Authentication gate fix

Implemented:

- Changed the browser flow so unauthenticated users see only the register/login screen.
- Added an authenticated home/dashboard section that appears only after registration or login succeeds.
- Added session restore through `GET /api/auth/me`.
- Added logout from the authenticated home page.
- Protected feature APIs behind a valid demo session token:
  - profile creation
  - assessment submission
  - report generation
  - report list/detail
  - PDF report download
  - health chat
  - symptom triage
  - document upload
- Updated PDF download links to include the demo session token for browser downloads.
- Added tests proving feature routes are blocked before login.

Verified:

- `python -m pytest` passed with 9 tests.
- `python -B -c "... ast.parse ..."` parsed 19 backend Python files successfully.

### 2026-06-23 - Role-based registration and login

Implemented:

- Expanded registration for multiple user types:
  - patient
  - doctor
  - dietician
  - admin
  - compliance officer
- Added role profile fields for organization, license/ID, and specialty.
- Added persistent demo sessions and `GET /api/auth/me`.
- Added role capabilities and landing-view metadata to register/login responses.
- Added role guards:
  - doctor/dietician can view and review pending reports
  - admin can upload approved knowledge
  - admin/compliance can view audit logs
  - patient users are blocked from privileged admin/doctor actions
- Added frontend registration/login forms with user-type selector.
- Added role-aware frontend tools for doctor/dietician review and admin/compliance actions.
- Added tests for role-based auth, `auth/me`, and blocked wrong-role access.

Verified:

- `python -m pytest` passed with 8 tests.
- `python -B -c "... ast.parse ..."` parsed 19 backend Python files successfully.

### 2026-06-23 - Demo workflow expansion

Implemented:

- Added SQLite-backed demo persistence with configurable `HEALTHGUARD_DB_PATH`.
- Added demo auth:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
- Persisted patient profiles, assessments, reports, admin knowledge records, doctor reviews, and audit logs.
- Added report history:
  - `GET /api/reports`
  - `GET /api/reports/{report_id}`
- Added downloadable generated PDF reports:
  - `GET /api/reports/{report_id}/download`
- Added admin knowledge APIs:
  - `POST /api/admin/knowledge`
  - `GET /api/admin/knowledge`
- Added doctor review APIs:
  - `GET /api/doctor/reports/pending`
  - `POST /api/doctor/reports/{report_id}/review`
- Upgraded frontend demo flow:
  - generate and save report
  - show report ID
  - download PDF
  - view saved report history
  - approve report through demo doctor-review action
- Expanded tests to cover auth, saved reports, PDF download, doctor review, admin knowledge, and audit logs.

Verified:

- `python -m pytest` passed with 7 tests.
- `python -B -c "... ast.parse ..."` parsed 19 backend Python files successfully.
- Demo server started on `127.0.0.1:8001`; `GET /api/health` returned `{"status":"ok","service":"HealthGuard AI"}`.

Notes:

- SQLite is intentionally configured to use the OS temp directory by default because the workspace is inside a OneDrive reparse/read-only path that caused SQLite disk I/O errors.
- Set `HEALTHGUARD_DB_PATH` for a fixed demo database location.
- Demo auth returns a non-secure `demo_token`; production auth still requires JWT/session hardening, password policy, and RBAC enforcement.

### 2026-06-23 - MVP foundation

Implemented:

- Created FastAPI backend scaffold.
- Added deterministic medical safety boundaries:
  - no final diagnosis
  - no medication prescribing
  - consent required before health-data processing
  - emergency red-flag detection
- Added health profile, symptom, chat, assessment, report, and document schemas.
- Added MVP services for triage, risk scoring, lifestyle guidance, diet guidance, climate guidance, knowledge retrieval, safety validation, and report generation.
- Added API endpoints:
  - `GET /api/health`
  - `POST /api/patients/profile`
  - `POST /api/symptoms/triage`
  - `POST /api/assessments/submit`
  - `POST /api/reports/generate`
  - `POST /api/chat/health-question`
  - `POST /api/documents/upload`
  - `GET /api/admin/audit-logs`
- Added static web UI served by FastAPI at `/`.
- Added acceptance tests for:
  - emergency symptom warning
  - lifestyle risk for software engineer
  - medication request refusal
  - missing-information follow-up
  - consent enforcement
- Added `Dockerfile`, `docker-compose.yml`, `.gitignore`, and pytest configuration.

Verified:

- `python -m pytest` passed with 5 tests.
- `python -c "from backend.app.main import app; print(app.title)"` imported the app successfully.
- `python -B -c "... ast.parse ..."` parsed 14 backend Python files successfully.
- Started the app with Uvicorn on `127.0.0.1:8001` because `8000` was already occupied; `GET /api/health` returned `{"status":"ok","service":"HealthGuard AI"}`.

Notes:

- RAG is represented by an approved internal guidance retrieval stub for MVP.
- Document OCR/lab parsing is a safe placeholder and queued for a later implementation slice.
- Production auth/RBAC, real RAG, polished PDF rendering, OCR/lab parsing, privacy controls, and deployment hardening are next major gaps.
- ReportLab is not installed in the current local environment, so PDF generation remains tracked rather than marked complete.
- `python -m compileall backend` was not used as a final check because this OneDrive-backed folder denied `.pyc` cache writes; AST parsing was used instead.

## Requirement Coverage

| Area | Status | Notes |
| --- | --- | --- |
| User login | Partial | Role-based demo register/login and session tokens implemented; secure production auth pending. |
| Patient profile | Partial | Schema, validation, and persistence implemented; user ownership/RBAC pending. |
| Symptom intake | Partial | Triage accepts text; structured history persistence pending. |
| Basic triage | Implemented | Deterministic red-flag rules. |
| Lifestyle risk analysis | Implemented | MVP scoring and precautions. |
| Diet risk analysis | Implemented | MVP scoring and precautions. |
| Climate-aware guidance | Partial | Location/climate text rules; weather/AQI API pending. |
| RAG health Q&A | Partial | Approved source stub; vector DB ingestion pending. |
| Medical disclaimer | Implemented | Included in chat/report responses. |
| AI-generated health report | Implemented | Deterministic MVP report response saved to SQLite. |
| PDF download | Implemented | Simple generated PDF download; polished renderer pending. |
| Admin knowledge upload | Partial | Role-guarded admin API stores approved knowledge text; ingestion/chunking pending. |
| Safety validator | Implemented | Text validation and medication refusal. |
| Audit logs | Partial | Role-guarded database-backed action logs implemented; PII masking/immutability pending. |
| Doctor review | Partial | Role-guarded pending list and review status/comments implemented; full clinical workflow pending. |
| Docker setup | Implemented | Basic app container and compose file added. |

## Next Recommended Updates

1. Add database models and SQLite/PostgreSQL persistence.
2. Add auth, user roles, and consent records.
3. Store assessments/reports and generate downloadable PDFs.
4. Add knowledge document upload, chunking, and vector retrieval.
5. Add doctor review APIs and UI.
6. Add Docker Compose and CI checks.
