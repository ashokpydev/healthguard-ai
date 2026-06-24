# HealthGuard AI Track Doc

This document is the running implementation record for HealthGuard AI. Update it for every meaningful change so future work stays traceable.

## Current Branch

- `version-1.0`

## Source Requirement

- `HealthGuard AI Requirement Document.pdf`
- Extracted on 2026-06-23.

## Update Log

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
