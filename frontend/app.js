const form = document.querySelector("#assessment-form");
const registerForm = document.querySelector("#register-form");
const loginForm = document.querySelector("#login-form");
const logoutButton = document.querySelector("#logout");
const homeLogoutButton = document.querySelector("#home-logout");
const authStatus = document.querySelector("#auth-status");
const verifyEmailButton = document.querySelector("#verify-email");
const loadConfirmationEmailButton = document.querySelector("#load-confirmation-email");
const resendConfirmationButton = document.querySelector("#resend-confirmation");
const verificationModal = document.querySelector("#verification-modal");
const closeVerificationModalButton = document.querySelector("#close-verification-modal");
const verificationCopy = document.querySelector("#verification-copy");
const homeTitle = document.querySelector("#home-title");
const homeSubtitle = document.querySelector("#home-subtitle");
const reportsPanel = document.querySelector("#reports-panel");
const report = document.querySelector("#report");
const riskPill = document.querySelector("#risk-pill");
const historyPanel = document.querySelector("#history");
const refreshHistory = document.querySelector("#refresh-history");
const loadRoleData = document.querySelector("#load-role-data");
const roleOutput = document.querySelector("#role-output");
const roleToolsTitle = document.querySelector("#role-tools-title");
const knowledgeForm = document.querySelector("#knowledge-form");
const documentForm = document.querySelector("#document-form");
const documentFile = document.querySelector("#document-file");
const documentStatus = document.querySelector("#document-status");
const clearDocumentContextButton = document.querySelector("#clear-document-context");
const foodGroupSelect = document.querySelector("#food-group");
const foodItemSelect = document.querySelector("#food-item");
const addFoodButton = document.querySelector("#add-food");
const selectedFoodsPanel = document.querySelector("#selected-foods");
let lastReportId = null;
let savedReports = [];
let savedReportsPage = 1;
const savedReportsPageSize = 5;
let currentUser = JSON.parse(localStorage.getItem("healthguardUser") || "null");
let pendingVerificationEmail = localStorage.getItem("healthguardPendingEmail") || "";
let uploadedDocumentContext = JSON.parse(localStorage.getItem("healthguardDocumentContext") || "null");
let selectedFoods = [];

const foodCatalog = {
  grains: ["rice", "chapati", "millets", "oats", "brown rice", "white bread", "noodles"],
  protein: ["dal", "beans", "chickpeas", "eggs", "chicken", "fish", "paneer", "tofu", "nuts"],
  vegetables: ["leafy greens", "carrot", "beans", "cucumber", "tomato", "mixed vegetables"],
  fruits: ["apple", "banana", "orange", "papaya", "berries", "seasonal fruit"],
  dairy: ["milk", "curd", "buttermilk", "cheese", "soy milk"],
  snacks: ["chips", "biscuits", "sweets", "fried snacks", "fast food", "packaged snacks"],
  drinks: ["water", "tea", "coffee", "sugary drinks", "fruit juice", "energy drinks"]
};

function csvValues(selector) {
  return document
    .querySelector(selector)
    .value.split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function populateFoodItems() {
  const items = foodCatalog[foodGroupSelect.value] || [];
  foodItemSelect.innerHTML = [
    `<option value="" selected>Select food item</option>`,
    ...items.map((item) => `<option>${item}</option>`)
  ].join("");
}

function renderSelectedFoods() {
  if (!selectedFoodsPanel) {
    return;
  }
  if (!selectedFoods.length) {
    selectedFoodsPanel.textContent = "No food items selected.";
    return;
  }
  selectedFoodsPanel.innerHTML = selectedFoods
    .map(
      (food, index) => `<span class="selected-chip">${food}<button type="button" aria-label="Remove ${food}" data-remove-food="${index}">x</button></span>`
    )
    .join("");
}

function addSelectedFood() {
  const food = foodItemSelect.value;
  if (!food || selectedFoods.includes(food)) {
    return;
  }
  selectedFoods.push(food);
  renderSelectedFoods();
}

function validateAssessmentForm() {
  if (!form.reportValidity()) {
    report.textContent = "Please complete all required fields before generating the report.";
    riskPill.textContent = "Required";
    riskPill.className = "pill urgent";
    return false;
  }
  if (!selectedFoods.length) {
    selectedFoodsPanel.textContent = "Select at least one food item from the catalog.";
    report.textContent = "Please select at least one food item before generating the report.";
    riskPill.textContent = "Required";
    riskPill.className = "pill urgent";
    return false;
  }
  return true;
}

document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((field) => {
  field.dataset.placeholder = field.placeholder;
  field.addEventListener("focus", () => {
    field.placeholder = "";
  });
  field.addEventListener("blur", () => {
    if (!field.value) {
      field.placeholder = field.dataset.placeholder || "";
    }
  });
});

document.querySelectorAll(".auth-shell input[value]").forEach((field) => {
  field.dataset.defaultValue = field.defaultValue;
  field.dataset.userEdited = "false";
  field.addEventListener("focus", () => {
    if (field.dataset.userEdited === "false" && field.value === field.dataset.defaultValue) {
      field.value = "";
    }
  });
  field.addEventListener("input", () => {
    field.dataset.userEdited = "true";
  });
});

function clearAuthForm(formElement) {
  formElement.querySelectorAll("input").forEach((field) => {
    field.value = "";
    field.dataset.userEdited = "false";
  });
}

function authHeaders() {
  return currentUser?.demo_token ? { "X-Demo-Token": currentUser.demo_token } : {};
}

function formatApiError(response, data, fallback) {
  let message = fallback;
  if (typeof data?.detail === "string") {
    message = data.detail;
  } else if (data?.detail && typeof data.detail === "object" && !Array.isArray(data.detail)) {
    const parts = [data.detail.message, data.detail.provider ? `Provider: ${data.detail.provider}` : "", data.detail.model ? `Model: ${data.detail.model}` : "", data.detail.error ? `Details: ${data.detail.error}` : ""].filter(Boolean);
    message = parts.join(" | ");
  } else if (Array.isArray(data?.detail) && data.detail.length) {
    message = data.detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
        return `${field}: ${item.msg}`;
      })
      .join("; ");
  } else if (data?.message) {
    message = data.message;
  }
  return `Error ${response.status}: ${message}`;
}

function validateEmailForRegistration(email) {
  const normalized = email.trim().toLowerCase();
  const pattern = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;
  if (!pattern.test(normalized)) {
    return "Error 422: email: Enter a valid email address.";
  }
  const [localPart, fullDomain] = normalized.split("@");
  const labels = fullDomain.split(".");
  const domain = fullDomain.slice(0, fullDomain.lastIndexOf("."));
  const tld = fullDomain.slice(fullDomain.lastIndexOf(".") + 1);
  const blockedNames = new Set(["example", "invalid", "test"]);
  const blockedDomains = new Set([
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
    "hotmail.con"
  ]);
  const allowedTlds = new Set(["ai", "app", "co", "com", "dev", "edu", "gov", "health", "in", "io", "me", "net", "org"]);
  if (localPart.startsWith(".") || localPart.endsWith(".") || localPart.includes("..")) {
    return "Error 422: email: Enter a valid email address.";
  }
  if (
    fullDomain.includes("..") ||
    labels.some((label) => !label || label.startsWith("-") || label.endsWith("-")) ||
    blockedNames.has(domain) ||
    blockedDomains.has(fullDomain) ||
    !allowedTlds.has(tld)
  ) {
    return "Error 422: email: Enter a valid email domain.";
  }
  return "";
}

function clearPendingVerification() {
  pendingVerificationEmail = "";
  localStorage.removeItem("healthguardPendingEmail");
  const codeField = document.querySelector("#verification-code");
  if (codeField) {
    codeField.value = "";
  }
}

function openVerificationModal(email) {
  pendingVerificationEmail = email;
  localStorage.setItem("healthguardPendingEmail", pendingVerificationEmail);
  if (!verificationModal || !verificationCopy) {
    authStatus.innerHTML = `Confirmation code sent to ${email}. <button class="inline-action" type="button" data-open-verification>Open confirmation popup</button>`;
    return;
  }
  verificationCopy.textContent = `We sent a 6-digit confirmation code to ${email}.`;
  verificationModal.classList.add("open");
  verificationModal.style.display = "grid";
  verificationModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#verification-code").focus(), 0);
}

function closeVerificationModal() {
  if (!verificationModal) {
    return;
  }
  verificationModal.classList.remove("open");
  verificationModal.style.display = "";
  verificationModal.setAttribute("aria-hidden", "true");
}

function setCurrentUser(user) {
  currentUser = user;
  if (user) {
    localStorage.setItem("healthguardUser", JSON.stringify(user));
  } else {
    localStorage.removeItem("healthguardUser");
  }
  renderAuthState();
}

function renderAuthState() {
  if (!currentUser) {
    document.body.classList.remove("is-authenticated");
    authStatus.innerHTML = pendingVerificationEmail
      ? `Confirmation required for ${pendingVerificationEmail}. <button class="inline-action" type="button" data-open-verification>Open confirmation popup</button>`
      : "Register with a valid email, confirm the 6-digit code, then enter the dashboard.";
    roleToolsTitle.textContent = "Role actions";
    knowledgeForm.classList.remove("visible");
    return;
  }
  document.body.classList.add("is-authenticated");
  authStatus.textContent = `${currentUser.name} is logged in as ${currentUser.role}.`;
  homeTitle.textContent = `Welcome, ${currentUser.name}`;
  homeSubtitle.textContent = `Signed in as ${currentUser.role}. Follow the guided workflow to create safer preventive reports, review saved outputs, and use role-specific tools.`;
  roleToolsTitle.textContent = `${currentUser.role} actions`;
  knowledgeForm.classList.toggle("visible", currentUser.role === "admin");
  loadHistory({ resetPage: true });
}

function list(items) {
  return `<ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function section(title, content) {
  return `<div class="report-section"><h3>${title}</h3>${content}</div>`;
}

function renderDocumentStatus() {
  if (!documentStatus) {
    return;
  }
  if (!uploadedDocumentContext?.tuned_context) {
    documentStatus.textContent = "No document is attached. You can generate a report without uploading files.";
    return;
  }
  documentStatus.innerHTML = [
    section("Attached document", `<p><strong>${uploadedDocumentContext.filename}</strong> is ready to support the next report.</p>`),
    section("Extracted summary", `<p>${uploadedDocumentContext.rag_summary}</p>`),
    section("Processing note", `<p>${uploadedDocumentContext.disclaimer}</p>`)
  ].join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateAssessmentForm()) {
    return;
  }
  if (reportsPanel) {
    reportsPanel.hidden = false;
  }
  report.textContent = "Generating safe report...";
  riskPill.textContent = "Working";
  riskPill.className = "pill";

  const payload = {
    consent_to_process_health_data: document.querySelector("#consent").checked,
    question: document.querySelector("#question").value,
    document_context: uploadedDocumentContext?.tuned_context || null,
    profile: {
      age: Number(document.querySelector("#age").value),
      gender: document.querySelector("#gender").value || null,
      location: document.querySelector("#location").value,
      climate: document.querySelector("#climate").value,
      occupation: document.querySelector("#occupation").value,
      sleep_hours: Number(document.querySelector("#sleep").value),
      exercise_frequency: document.querySelector("#exercise").value,
      diet_style: [
        document.querySelector("#diet-pattern").value,
        document.querySelector("#water-intake").value,
        selectedFoods.join(", ")
      ].filter(Boolean).join(", "),
      food_habits: selectedFoods,
      smoking_status: document.querySelector("#smoking").value || null,
      alcohol_status: document.querySelector("#alcohol").value || null,
      existing_conditions: csvValues("#conditions"),
      allergies: csvValues("#allergies"),
      family_history: csvValues("#family-history"),
      current_medications: csvValues("#medications").map((medicine) => ({ medicine_name: medicine })),
      height_cm: Number(document.querySelector("#height").value) || null,
      weight_kg: Number(document.querySelector("#weight").value) || null
    },
    symptoms: document.querySelector("#symptom-name").value
      ? [
          {
            name: document.querySelector("#symptom-name").value,
            severity: Number(document.querySelector("#symptom-severity").value) || null,
            duration_days: Number(document.querySelector("#symptom-duration").value) || null,
            notes: document.querySelector("#question").value
          }
        ]
      : []
  };

  const response = await fetch("/api/reports/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (!response.ok) {
    riskPill.textContent = `Error ${response.status}`;
    report.textContent = formatApiError(response, data, "Unable to generate report.");
    requestAnimationFrame(() => reportsPanel?.scrollIntoView({ behavior: "smooth", block: "start" }));
    return;
  }

  const generated = data.report;
  lastReportId = data.report_id;
  riskPill.textContent = `${generated.risk_summary.overall_risk_level} ${generated.risk_summary.risk_score}`;
  riskPill.className = generated.emergency_warning ? "pill urgent" : "pill";
  report.innerHTML = [
    section("Saved report", `<p>Report #${data.report_id} is saved for doctor review.</p>`),
    generated.emergency_warning ? section("Emergency warning", `<p>${generated.precautions[0]}</p>`) : "",
    section("Risk factors", list(generated.risk_summary.key_risk_factors)),
    section("Concerns to discuss with a doctor", list(generated.possible_health_concerns_to_discuss_with_doctor)),
    section("Precautions", list(generated.precautions)),
    generated.llm_summary ? section("AI summary", `<p>${generated.llm_summary}</p>`) : "",
    section("Generation engine", `<p>${generated.generation_engine || "rules"}</p>`),
    generated.llm_error ? section("LLM status", `<p>${generated.llm_error}</p>`) : "",
    section("Questions for doctor", list(generated.suggested_questions_to_ask_doctor)),
    section(
      "Actions",
      `<div class="actions">
        <a class="button-link" href="/api/reports/${data.report_id}/download?demo_token=${encodeURIComponent(currentUser.demo_token)}">Download PDF</a>
        <button class="secondary" type="button" onclick="approveReport(${data.report_id})">Doctor approve</button>
      </div>`
    ),
    uploadedDocumentContext?.tuned_context
      ? section("Uploaded document details", `<p>${uploadedDocumentContext.rag_summary}</p>`)
      : "",
    section("Disclaimer", `<p>${generated.disclaimer}</p>`)
  ].join("");
  await loadHistory({ resetPage: true });
  requestAnimationFrame(() => reportsPanel?.scrollIntoView({ behavior: "smooth", block: "start" }));
});

async function uploadDocument(event) {
  event.preventDefault();
  if (!currentUser) {
    documentStatus.textContent = "Login first to upload documents.";
    return;
  }
  if (!documentFile.files.length) {
    documentStatus.textContent = "Choose a document before uploading.";
    return;
  }
  documentStatus.textContent = "Reading the document and preparing the useful details...";
  const body = new FormData();
  body.append("file", documentFile.files[0]);
  const response = await fetch("/api/documents/upload", {
    method: "POST",
    headers: authHeaders(),
    body
  });
  const data = await response.json();
  if (!response.ok) {
    documentStatus.textContent = formatApiError(response, data, "Document upload failed.");
    return;
  }
  uploadedDocumentContext = data;
  localStorage.setItem("healthguardDocumentContext", JSON.stringify(uploadedDocumentContext));
  renderDocumentStatus();
}

function clearDocumentContext() {
  uploadedDocumentContext = null;
  localStorage.removeItem("healthguardDocumentContext");
  if (documentFile) {
    documentFile.value = "";
  }
  renderDocumentStatus();
}

async function loadHistory(options = {}) {
  const shouldResetPage = Boolean(options.resetPage);
  if (!currentUser) {
    savedReports = [];
    savedReportsPage = 1;
    historyPanel.textContent = "Login to view saved reports.";
    return;
  }
  const response = await fetch("/api/reports", { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    savedReports = [];
    historyPanel.textContent = formatApiError(response, data, "Unable to load reports.");
    return;
  }
  if (!data.items.length) {
    savedReports = [];
    savedReportsPage = 1;
    historyPanel.textContent = "No saved reports yet.";
    return;
  }
  savedReports = data.items;
  if (shouldResetPage) {
    savedReportsPage = 1;
  }
  savedReportsPage = Math.min(savedReportsPage, Math.ceil(savedReports.length / savedReportsPageSize)) || 1;
  renderSavedReports();
}

function renderSavedReports() {
  if (!savedReports.length) {
    historyPanel.textContent = "No saved reports yet.";
    return;
  }
  const totalPages = Math.ceil(savedReports.length / savedReportsPageSize);
  const pageStart = (savedReportsPage - 1) * savedReportsPageSize;
  const pageItems = savedReports.slice(pageStart, pageStart + savedReportsPageSize);
  const reportList = pageItems
    .map(
      (item) => `<div class="history-item">
        <div>
          <strong>#${item.id}</strong> ${item.patient_summary.location || "Unknown location"} -
          ${item.patient_summary.occupation || "Unknown occupation"} -
          ${item.risk_level} ${item.risk_score}
          <br />
          Review: ${item.doctor_review_status}
        </div>
        <div class="actions">
          <a class="button-link" href="/api/reports/${item.id}/download?demo_token=${encodeURIComponent(currentUser.demo_token)}">PDF</a>
          <button class="secondary" type="button" onclick="approveReport(${item.id})">Approve</button>
        </div>
      </div>`
    )
    .join("");
  const pager =
    totalPages > 1
      ? `<div class="history-pagination" aria-label="Saved reports pagination">
          <button class="secondary" type="button" data-history-page="prev" ${savedReportsPage === 1 ? "disabled" : ""}>Previous</button>
          <span>Page ${savedReportsPage} of ${totalPages}</span>
          <button class="secondary" type="button" data-history-page="next" ${savedReportsPage === totalPages ? "disabled" : ""}>Next</button>
        </div>`
      : "";
  historyPanel.innerHTML = `${reportList}${pager}`;
}

function renderPatientReportFolders(folders = []) {
  if (!folders.length) {
    return section("Patient folders", "<p>No pending patient reports.</p>");
  }
  return folders
    .map((folder) => {
      const summary = folder.patient_summary || {};
      const title = [
        `Patient #${folder.patient_id}`,
        summary.location || "Unknown location",
        summary.occupation || "Unknown occupation"
      ].join(" - ");
      const reports = folder.reports
        .map(
          (item) => `<div class="history-item">
            <div>
              <strong>#${item.id}</strong> ${item.risk_level} ${item.risk_score}
              <br />
              Review: ${item.doctor_review_status}
            </div>
            <div class="actions">
              <a class="button-link" href="/api/reports/${item.id}/download?demo_token=${encodeURIComponent(currentUser.demo_token)}">PDF</a>
              <button class="secondary" type="button" onclick="approveReport(${item.id})">Approve</button>
            </div>
          </div>`
        )
        .join("");
      return section(title, `<p>${folder.pending_count} pending of ${folder.total_count} report(s).</p>${reports}`);
    })
    .join("");
}

async function approveReport(reportId) {
  if (!currentUser || !["doctor", "dietician"].includes(currentUser.role)) {
    roleOutput.textContent = "Login as a doctor or dietician to review reports.";
    return;
  }
  await fetch(`/api/doctor/reports/${reportId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      status: "approved",
      comments: "Demo doctor review completed.",
      final_clinical_notes: "Patient should discuss persistent symptoms and preventive screening with a clinician."
    })
  });
  if (lastReportId === reportId) {
    riskPill.textContent = `${riskPill.textContent} Reviewed`;
  }
  loadHistory({ resetPage: true });
}

refreshHistory.addEventListener("click", () => loadHistory({ resetPage: true }));
registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.querySelector("#register-email").value;
  const emailError = validateEmailForRegistration(email);
  if (emailError) {
    clearPendingVerification();
    authStatus.textContent = emailError;
    return;
  }
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.querySelector("#register-name").value,
      email,
      password: document.querySelector("#register-password").value,
      role: document.querySelector("#register-role").value,
      organization: document.querySelector("#register-organization").value || null,
      license_number: document.querySelector("#register-license").value || null
    })
  });
  const data = await response.json();
  if (!response.ok) {
    clearPendingVerification();
    authStatus.textContent = formatApiError(response, data, "Registration failed.");
    return;
  }
  pendingVerificationEmail = data.email;
  clearAuthForm(registerForm);
  document.querySelector("#login-email").value = pendingVerificationEmail;
  document.querySelector("#login-email").dataset.userEdited = "true";
  setCurrentUser(null);
  openVerificationModal(pendingVerificationEmail);
  authStatus.textContent = `${data.message} Check your inbox and submit the 6-digit code.`;
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.querySelector("#login-email").value,
      password: document.querySelector("#login-password").value
    })
  });
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, "Login failed.");
    return;
  }
  pendingVerificationEmail = "";
  localStorage.removeItem("healthguardPendingEmail");
  clearAuthForm(loginForm);
  setCurrentUser(data);
});

logoutButton.addEventListener("click", () => setCurrentUser(null));
homeLogoutButton.addEventListener("click", () => setCurrentUser(null));
loadRoleData.addEventListener("click", loadRoleActions);
documentForm?.addEventListener("submit", uploadDocument);
clearDocumentContextButton?.addEventListener("click", clearDocumentContext);
foodGroupSelect?.addEventListener("change", populateFoodItems);
addFoodButton?.addEventListener("click", addSelectedFood);
verifyEmailButton.addEventListener("click", verifyEmail);
loadConfirmationEmailButton?.addEventListener("click", loadLatestConfirmationEmail);
resendConfirmationButton.addEventListener("click", resendConfirmation);
closeVerificationModalButton?.addEventListener("click", closeVerificationModal);
verificationModal?.querySelector(".modal-backdrop")?.addEventListener("click", closeVerificationModal);
document.addEventListener("click", (event) => {
  if (event.target.matches("[data-open-verification]")) {
    openVerificationModal(pendingVerificationEmail || document.querySelector("#login-email").value);
  }
  const scrollTarget = event.target.closest("[data-scroll-target]");
  if (scrollTarget) {
    document.querySelectorAll(".menu-button").forEach((button) => button.classList.remove("active"));
    if (scrollTarget.classList.contains("menu-button")) {
      scrollTarget.classList.add("active");
    }
    if (scrollTarget.dataset.scrollTarget === "reports-panel" && reportsPanel?.hidden) {
      reportsPanel.hidden = false;
    }
    document.querySelector(`#${scrollTarget.dataset.scrollTarget}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  const historyPageButton = event.target.closest("[data-history-page]");
  if (historyPageButton) {
    const totalPages = Math.ceil(savedReports.length / savedReportsPageSize);
    if (historyPageButton.dataset.historyPage === "prev") {
      savedReportsPage = Math.max(1, savedReportsPage - 1);
    }
    if (historyPageButton.dataset.historyPage === "next") {
      savedReportsPage = Math.min(totalPages, savedReportsPage + 1);
    }
    renderSavedReports();
  }
  const removeFood = event.target.closest("[data-remove-food]");
  if (removeFood) {
    selectedFoods.splice(Number(removeFood.dataset.removeFood), 1);
    renderSelectedFoods();
  }
});
document.querySelectorAll(".sso-button").forEach((button) => {
  button.addEventListener("click", () => startSso(button.dataset.provider));
});

knowledgeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/admin/knowledge", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      title: document.querySelector("#knowledge-title").value,
      content: document.querySelector("#knowledge-content").value
    })
  });
  const data = await response.json();
  roleOutput.textContent = response.ok
    ? `Knowledge #${data.id} added and approved.`
    : formatApiError(response, data, "Unable to add knowledge.");
});

async function loadRoleActions() {
  if (!currentUser) {
    roleOutput.textContent = "Login first to load role actions.";
    return;
  }
  if (["doctor", "dietician"].includes(currentUser.role)) {
    const response = await fetch("/api/doctor/reports/pending", { headers: authHeaders() });
    const data = await response.json();
    roleOutput.innerHTML = response.ok
      ? renderPatientReportFolders(data.patient_folders)
      : formatApiError(response, data, "Unable to load pending reports.");
    return;
  }
  if (["admin", "compliance"].includes(currentUser.role)) {
    const response = await fetch("/api/admin/audit-logs", { headers: authHeaders() });
    const data = await response.json();
    roleOutput.innerHTML = response.ok
      ? section("Audit logs", list(data.items.slice(0, 8).map((item) => `${item.action}: ${item.output_summary}`)))
      : formatApiError(response, data, "Unable to load audit logs.");
    return;
  }
  roleOutput.textContent = "Patient users can create profiles, generate reports, ask questions, and download reports.";
}

async function restoreSession() {
  if (!currentUser?.demo_token) {
    renderAuthState();
    return;
  }
  const response = await fetch("/api/auth/me", { headers: authHeaders() });
  if (!response.ok) {
    setCurrentUser(null);
    return;
  }
  setCurrentUser(await response.json());
}

restoreSession();
renderDocumentStatus();
populateFoodItems();
renderSelectedFoods();

async function verifyEmail() {
  const code = document.querySelector("#verification-code").value.trim();
  if (!/^\d{6}$/.test(code)) {
    authStatus.textContent = "Enter the 6-digit confirmation code from your email.";
    return;
  }
  const response = await fetch("/api/auth/verify-email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: pendingVerificationEmail || document.querySelector("#login-email").value, code })
  });
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, "Email confirmation failed.");
    return;
  }
  pendingVerificationEmail = "";
  localStorage.removeItem("healthguardPendingEmail");
  closeVerificationModal();
  setCurrentUser(data);
}

async function loadLatestConfirmationEmail() {
  const email = pendingVerificationEmail || document.querySelector("#register-email").value || document.querySelector("#login-email").value;
  const response = await fetch(`/api/auth/dev/outbox?email=${encodeURIComponent(email)}`);
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, "No confirmation email found.");
    return;
  }
  document.querySelector("#verification-code").value = data.token;
  authStatus.textContent = `Loaded the latest 6-digit demo code for ${data.recipient}.`;
}

async function resendConfirmation() {
  const email = pendingVerificationEmail || document.querySelector("#register-email").value || document.querySelector("#login-email").value;
  const response = await fetch("/api/auth/resend-confirmation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, "Unable to resend confirmation.");
    return;
  }
  pendingVerificationEmail = email;
  localStorage.setItem("healthguardPendingEmail", pendingVerificationEmail);
  authStatus.textContent = data.email_verified
    ? "This email is already verified. You can login."
    : data.email_delivery.status === "sent"
      ? `A new 6-digit code was sent to ${email}.`
      : "Real email delivery is not configured. Configure SMTP to validate inbox ownership.";
  if (!data.email_verified && data.email_delivery.status === "sent") {
    openVerificationModal(email);
  }
}

async function startSso(provider) {
  const role = document.querySelector("#register-role").value;
  const response = await fetch(`/api/auth/sso/${provider}/start?role=${encodeURIComponent(role)}`);
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, `${provider} SSO failed to start.`);
    return;
  }
  if (!data.configured) {
    authStatus.textContent = data.message;
    return;
  }
  window.location.href = data.authorization_url;
}
