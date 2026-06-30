const form = document.querySelector("#assessment-form");
const registerForm = document.querySelector("#register-form");
const loginForm = document.querySelector("#login-form");
const logoutButton = document.querySelector("#logout");
const homeLogoutButton = document.querySelector("#home-logout");
const menuLogoutButton = document.querySelector("#menu-logout");
const mobileMenuToggle = document.querySelector("#mobile-menu-toggle");
const workspaceMenu = document.querySelector("#workspace-menu");
const authStatus = document.querySelector("#auth-status");
const verifyEmailButton = document.querySelector("#verify-email");
const loadConfirmationEmailButton = document.querySelector("#load-confirmation-email");
const resendConfirmationButton = document.querySelector("#resend-confirmation");
const verificationModal = document.querySelector("#verification-modal");
const closeVerificationModalButton = document.querySelector("#close-verification-modal");
const verificationCopy = document.querySelector("#verification-copy");
const passwordResetModal = document.querySelector("#password-reset-modal");
const requestPasswordResetButton = document.querySelector("#request-password-reset");
const closePasswordResetModalButton = document.querySelector("#close-password-reset-modal");
const sendPasswordResetButton = document.querySelector("#send-password-reset");
const confirmPasswordResetButton = document.querySelector("#confirm-password-reset");
const tourModal = document.querySelector("#tour-modal");
const openTourButton = document.querySelector("#open-tour");
const closeTourButton = document.querySelector("#close-tour");
const tourTitle = document.querySelector("#tour-title");
const tourCopy = document.querySelector("#tour-copy");
const tourVisual = document.querySelector("#tour-visual");
const tourProgress = document.querySelector("#tour-progress");
const tourPrevButton = document.querySelector("#tour-prev");
const tourNextButton = document.querySelector("#tour-next");
const tourSkipButton = document.querySelector("#tour-skip");
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
const roleOnlyElements = document.querySelectorAll(".role-only");
const documentForm = document.querySelector("#document-form");
const documentFile = document.querySelector("#document-file");
const documentStatus = document.querySelector("#document-status");
const clearDocumentContextButton = document.querySelector("#clear-document-context");
const foodGroupSelect = document.querySelector("#food-group");
const foodItemSelect = document.querySelector("#food-item");
const addFoodButton = document.querySelector("#add-food");
const selectedFoodsPanel = document.querySelector("#selected-foods");
const voiceStartButton = document.querySelector("#voice-start");
const voiceStopButton = document.querySelector("#voice-stop");
const voiceSubmitButton = document.querySelector("#voice-submit");
const voiceReadButton = document.querySelector("#voice-read");
const voiceClearButton = document.querySelector("#voice-clear");
const voiceTranscript = document.querySelector("#voice-transcript");
const voiceStatus = document.querySelector("#voice-status");
const voicePill = document.querySelector("#voice-pill");
const chatQuestion = document.querySelector("#chat-question");
const chatSubmitButton = document.querySelector("#chat-submit");
const chatCopyAssessmentButton = document.querySelector("#chat-copy-assessment");
const chatClearButton = document.querySelector("#chat-clear");
const chatStatus = document.querySelector("#chat-status");
const chatDialog = document.querySelector("#chat-dialog");
const chatLauncher = document.querySelector("#chat-launcher");
const chatCloseButton = document.querySelector("#chat-close");
const chatHistoryPanel = document.querySelector("#chat-history");
const chatStartersPanel = document.querySelector("#chat-starters");
const chatUrgentPanel = document.querySelector("#chat-urgent");
const chatFeedbackPanel = document.querySelector("#chat-feedback");
const chatConversationSelect = document.querySelector("#chat-conversation-select");
const chatNewButton = document.querySelector("#chat-new");
const chatExportButton = document.querySelector("#chat-export");
const chatDialogScroll = document.querySelector(".chat-dialog-scroll");
let lastReportId = null;
let savedReports = [];
let savedReportsPage = 1;
const savedReportsPageSize = 5;
let patientNotifications = [];
let doctorQueueStatus = "pending";
let currentUser = JSON.parse(localStorage.getItem("healthguardUser") || "null");
let pendingVerificationEmail = localStorage.getItem("healthguardPendingEmail") || "";
let uploadedDocumentContext = null;
let selectedFoods = [];
let voiceRecognition = null;
let lastVoiceAnswer = "";
let activeChatConversationId = Number(localStorage.getItem(chatConversationStorageKey()) || "0") || null;
let activeVoiceConversationId = Number(localStorage.getItem(voiceConversationStorageKey()) || "0") || null;
let lastChatAssistantMessageId = null;
let visibleChatMessages = [];
let voiceFinalTranscript = "";
let voiceManualStop = false;
let voiceMediaRecorder = null;
let voiceAudioChunks = [];
let voiceAudioStream = null;
let voiceRecordingStartedAt = 0;
let voiceSilenceTimer = null;
let voiceRestartTimer = null;
let voiceIsCapturing = false;
let voiceFinalizing = false;
let voiceDiscardCapture = false;
const voiceSilenceTimeoutMs = 5000;
let tourStepIndex = 0;

function chatConversationStorageKey(user = currentUser) {
  return user?.id ? `healthguardChatConversationId:${user.id}` : "healthguardChatConversationId";
}

function voiceConversationStorageKey(user = currentUser) {
  return user?.id ? `healthguardVoiceConversationId:${user.id}` : "healthguardVoiceConversationId";
}

const tourSteps = [
  {
    title: "Welcome to your clinical safety workspace",
    copy: "HealthGuard AI helps patients create educational preventive-health reports with safety checks, supporting knowledge, and clear doctor-review handoff.",
    target: "home-panel",
    visual: "start"
  },
  {
    title: "Step 1: Complete the assessment",
    copy: "Enter mandatory demographics, lifestyle, diet, symptoms, conditions, medications, allergies, and consent. Reports are not generated from blank demo data.",
    target: "assessment-panel",
    visual: "assessment"
  },
  {
    title: "Step 2: Ask the floating chatbot",
    copy: "Use the bot icon to open a compact right-side assistant for health doubts, symptom questions, lifestyle concerns, or uploaded-report follow-ups.",
    target: "home-panel",
    visual: "voice"
  },
  {
    title: "Step 3: Use voice intake when helpful",
    copy: "Speak symptoms or a health question. The app captures a transcript when the browser supports speech input, then sends it through the safe chat flow.",
    target: "voice-panel",
    visual: "voice"
  },
  {
    title: "Step 4: Upload optional health documents",
    copy: "Patients can add lab notes or previous reports. Extracted content is indexed for patient-isolated supporting context and used only when generating or answering relevant questions.",
    target: "documents-panel",
    visual: "documents"
  },
  {
    title: "Step 5: Generate and review the report",
    copy: "The report combines structured intake, safety rules, retrieved knowledge, and the configured LLM. If the LLM fails, no report is saved.",
    target: "reports-panel",
    visual: "report"
  },
  {
    title: "Step 6: Saved reports and clinician workflow",
    copy: "Patients only see their own reports. Doctors and dieticians can review patient folders, assign priority, add signatures, escalate, and maintain review history.",
    target: "history",
    visual: "review"
  }
];

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

function setFieldValue(selector, value) {
  const field = document.querySelector(selector);
  if (field && value && !field.value) {
    field.value = value;
  }
}

function setSelectValue(selector, value) {
  const field = document.querySelector(selector);
  if (!field || field.value || !value) {
    return;
  }
  const normalized = value.toLowerCase();
  const option = Array.from(field.options).find((item) => item.value.toLowerCase() === normalized || item.textContent.toLowerCase() === normalized);
  if (option) {
    field.value = option.value;
  }
}

function extractVoiceIntake(transcript) {
  const text = transcript.toLowerCase();
  const valueFor = (pattern) => {
    const match = text.match(pattern);
    return match ? match[1].trim() : "";
  };
  setFieldValue("#age", valueFor(/\b(?:i am|age is|aged)\s+(\d{1,3})\b/));
  setFieldValue("#height", valueFor(/\bheight(?: is)?\s+(\d{2,3})\b/));
  setFieldValue("#weight", valueFor(/\bweight(?: is)?\s+(\d{2,3})\b/));
  setFieldValue("#sleep", valueFor(/\bsleep(?:ing)?\s+(\d{1,2}(?:\.\d)?)\s*(?:hours|hrs)?\b/));
  setFieldValue("#location", valueFor(/\b(?:location is|live in|from)\s+([a-z ]{3,40})(?:\.|,| and | with |$)/));
  if (text.includes("hot")) setSelectValue("#climate", "hot weather");
  if (text.includes("humid")) setSelectValue("#climate", "humid weather");
  if (text.includes("cold")) setSelectValue("#climate", "cold weather");
  if (text.includes("pollution")) setSelectValue("#climate", "high pollution");
  if (text.includes("software")) setFieldValue("#occupation", "Software Engineer");
  if (text.includes("smoker") || text.includes("smoking")) setSelectValue("#smoking", "current smoker");
  if (text.includes("no smoking") || text.includes("non smoker")) setSelectValue("#smoking", "none");
  if (text.includes("alcohol")) setSelectValue("#alcohol", text.includes("frequent") ? "frequent alcohol" : "occasional alcohol");
  if (text.includes("no alcohol")) setSelectValue("#alcohol", "none");
  if (text.includes("processed") || text.includes("sugar")) setSelectValue("#diet-pattern", "processed food, high sugar");
  if (text.includes("balanced")) setSelectValue("#diet-pattern", "balanced home food");
  if (text.includes("low water")) setSelectValue("#water-intake", "low water");
  const symptom = ["fever", "headache", "fatigue", "weakness", "cough", "chest pain", "back pain", "stomach pain", "dizziness"].find((item) => text.includes(item));
  setFieldValue("#symptom-name", symptom || "");
  if (text.includes("severe")) setSelectValue("#symptom-severity", "7");
  if (text.includes("mild")) setSelectValue("#symptom-severity", "1");
  setFieldValue("#symptom-duration", valueFor(/\b(?:for|duration)\s+(\d{1,4})\s+(?:day|days)\b/));
  if (!document.querySelector("#question").value) {
    document.querySelector("#question").value = transcript;
  }
}

function optionalVoiceProfile() {
  const age = Number(document.querySelector("#age").value);
  if (!age) {
    return null;
  }
  return {
    age,
    gender: document.querySelector("#gender").value || null,
    location: document.querySelector("#location").value || null,
    climate: document.querySelector("#climate").value || null,
    occupation: document.querySelector("#occupation").value || null,
    sleep_hours: Number(document.querySelector("#sleep").value) || null,
    exercise_frequency: document.querySelector("#exercise").value || null,
    diet_style: [
      document.querySelector("#diet-pattern").value,
      document.querySelector("#water-intake").value,
      selectedFoods.join(", ")
    ].filter(Boolean).join(", ") || null,
    food_habits: selectedFoods,
    smoking_status: document.querySelector("#smoking").value || null,
    alcohol_status: document.querySelector("#alcohol").value || null,
    existing_conditions: csvValues("#conditions"),
    allergies: csvValues("#allergies"),
    family_history: csvValues("#family-history"),
    current_medications: csvValues("#medications").map((medicine) => ({ medicine_name: medicine })),
    height_cm: Number(document.querySelector("#height").value) || null,
    weight_kg: Number(document.querySelector("#weight").value) || null
  };
}

function setVoiceStatus(message, state = "Idle") {
  if (voiceStatus) {
    voiceStatus.innerHTML = message;
  }
  if (voicePill) {
    voicePill.textContent = state;
    voicePill.className = state.toLowerCase().includes("error") ? "pill urgent" : "pill";
  }
}

function setChatStatus(message, state = "Ready") {
  if (chatStatus) {
    chatStatus.innerHTML = message;
    chatStatus.hidden = !message;
  }
  scrollChatToLatest();
}

function scrollChatToLatest() {
  window.setTimeout(() => {
    if (chatDialogScroll) {
      chatDialogScroll.scrollTop = chatDialogScroll.scrollHeight;
    }
  }, 30);
}

function openChatDialog() {
  chatDialog?.classList.add("open");
  chatDialog?.setAttribute("aria-hidden", "false");
  chatLauncher?.setAttribute("aria-expanded", "true");
  document.body.classList.add("chat-open");
  window.setTimeout(() => chatQuestion?.focus(), 120);
}

function closeChatDialog() {
  chatDialog?.classList.remove("open");
  chatDialog?.setAttribute("aria-hidden", "true");
  chatLauncher?.setAttribute("aria-expanded", "false");
  document.body.classList.remove("chat-open");
}

function setMobileMenu(open) {
  workspaceMenu?.classList.toggle("open", open);
  mobileMenuToggle?.classList.toggle("open", open);
  mobileMenuToggle?.setAttribute("aria-expanded", String(open));
  mobileMenuToggle?.setAttribute("aria-label", open ? "Close workspace menu" : "Open workspace menu");
}

function renderChatAnswer(question, data) {
  const answerTitle = data.conversation_stage === "asking_followup" ? "Follow-up question" : data.conversation_stage === "summary_ready" ? "Summary and next steps" : "Answer";
  return [
    section("Question", `<p>${escapeHtml(question)}</p>`),
    data.red_flags?.length ? section("Safety alerts", list(data.red_flags.map(escapeHtml))) : "",
    section(answerTitle, `<p>${escapeHtml(data.answer)}</p>`),
    data.sources?.length
      ? section("Source", `<p>${escapeHtml(data.sources.slice(0, 2).map((source) => source.citation || source.title).join(", "))}</p>`)
      : ""
  ].join("");
}

function voiceStageLabel(data) {
  if (data.red_flags?.length || data.conversation_stage === "urgent") {
    return "Alert";
  }
  if (data.conversation_stage === "asking_followup") {
    return "Asking follow-up";
  }
  if (data.conversation_stage === "summary_ready") {
    return "Summary ready";
  }
  return "Answered";
}

function renderChatLoading(question) {
  return [
    section("Question", `<p>${escapeHtml(question)}</p>`),
    section("Answer", `<div class="chat-loading"><span></span><span></span><span></span>HealthGuard is checking trusted guidance...</div>`)
  ].join("");
}

function renderVisibleChatMessages() {
  if (!chatHistoryPanel) {
    return;
  }
  chatHistoryPanel.innerHTML = visibleChatMessages.map((message) => `
    <div class="chat-message ${message.role === "assistant" ? "assistant" : "user"}">
      <strong>${message.role === "assistant" ? "HealthGuard" : "You"}</strong>
      <p>${escapeHtml(message.content)}</p>
    </div>
  `).join("");
  scrollChatToLatest();
}

function appendVisibleChatMessage(role, content) {
  visibleChatMessages.push({ role, content });
  renderVisibleChatMessages();
}

function updateLastVisibleAssistantMessage(content) {
  const lastAssistantIndex = visibleChatMessages.map((message) => message.role).lastIndexOf("assistant");
  if (lastAssistantIndex >= 0) {
    visibleChatMessages[lastAssistantIndex].content = content;
  } else {
    visibleChatMessages.push({ role: "assistant", content });
  }
  renderVisibleChatMessages();
}

function renderChatHistory(messages = []) {
  if (!chatHistoryPanel) {
    return;
  }
  renderVisibleChatMessages();
  scrollChatToLatest();
}

function renderChatConversationOptions(conversations = []) {
  if (!chatConversationSelect) {
    return;
  }
  chatConversationSelect.innerHTML = [
    `<option value="">New chat</option>`,
    ...conversations.map((item) => {
      const title = item.title || `Chat #${item.id}`;
      const active = item.id === activeChatConversationId ? " selected" : "";
      return `<option value="${item.id}"${active}>${escapeHtml(title.slice(0, 44))}</option>`;
    })
  ].join("");
}

async function loadChatHistory() {
  if (!currentUser) {
    return;
  }
  const response = await fetch("/api/chat/conversations", { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    return;
  }
  renderChatConversationOptions(data.items || []);
  const conversation = activeChatConversationId
    ? data.items.find((item) => item.id === activeChatConversationId)
    : data.items[0];
  if (conversation) {
    activeChatConversationId = conversation.id;
    localStorage.setItem(chatConversationStorageKey(), String(conversation.id));
    renderChatHistory(conversation.messages || []);
  } else {
    activeChatConversationId = null;
    localStorage.removeItem(chatConversationStorageKey());
    renderChatHistory([]);
  }
}

function startNewChatConversation() {
  activeChatConversationId = null;
  localStorage.removeItem(chatConversationStorageKey());
  renderChatHistory([]);
  renderChatFeedback(null);
  if (chatConversationSelect) {
    chatConversationSelect.value = "";
  }
  setChatStatus("New chat started. Ask one health question.", "Ready");
  chatQuestion?.focus();
}

async function exportActiveChat() {
  if (!activeChatConversationId) {
    setChatStatus("No chat selected to export.", "Error");
    return;
  }
  const response = await fetch("/api/chat/export", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ conversation_id: activeChatConversationId, report_id: lastReportId })
  });
  const data = await response.json();
  if (!response.ok) {
    setChatStatus(formatApiError(response, data, "Chat export failed."), `Error ${response.status}`);
    return;
  }
  const blob = new Blob([data.content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `healthguard-chat-${data.conversation_id}.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setChatStatus("Chat exported for doctor review.", "Ready");
}

async function loadChatStarters() {
  if (!currentUser || !chatStartersPanel) {
    return;
  }
  const defaultFaqs = [
    "What should I track for fever?",
    "When should I see a doctor?",
    "What should I eat today?"
  ];
  const response = await fetch("/api/chat/starter-questions", { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) {
    chatStartersPanel.innerHTML = defaultFaqs.map((question) => (
      `<button type="button" data-chat-starter="${encodeURIComponent(question)}">${escapeHtml(question)}</button>`
    )).join("");
    return;
  }
  const questions = (data.items && data.items.length ? data.items : defaultFaqs).slice(0, 3);
  chatStartersPanel.innerHTML = questions.map((question) => (
    `<button type="button" data-chat-starter="${encodeURIComponent(question)}">${escapeHtml(question)}</button>`
  )).join("");
}

function renderUrgentChatState(data) {
  if (!chatUrgentPanel) {
    return;
  }
  const urgent = Boolean(data.emergency_escalation || data.red_flags?.length);
  chatUrgentPanel.hidden = !urgent;
  if (urgent && data.red_flags?.length) {
    chatUrgentPanel.innerHTML = `<strong>Urgent symptom alert</strong>${list(data.red_flags.map(escapeHtml))}<p>Seek emergency care now if symptoms are severe, sudden, or worsening.</p>`;
  }
}

function renderChatFeedback(messageId) {
  lastChatAssistantMessageId = messageId || null;
  if (chatFeedbackPanel) {
    chatFeedbackPanel.hidden = !lastChatAssistantMessageId;
  }
}

async function sendChatFeedback(rating) {
  if (!lastChatAssistantMessageId) {
    return;
  }
  const response = await fetch("/api/chat/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message_id: lastChatAssistantMessageId, rating })
  });
  chatFeedbackPanel.hidden = true;
  setChatStatus(response.ok ? "Thanks. Your chatbot feedback was saved." : "Feedback could not be saved.", response.ok ? "Ready" : "Error");
}

function voiceErrorMessage(errorCode) {
  const messages = {
    "not-allowed": "Microphone permission was blocked. Allow microphone access for this site, then try again.",
    "service-not-allowed": "The browser speech service is blocked. Try Chrome/Edge with microphone permission enabled.",
    "audio-capture": "No microphone was detected. Check the mic device and Windows privacy settings.",
    "network": "The browser speech service could not connect. Check internet access or try another browser.",
    "no-speech": "No speech was detected. Try again and speak closer to the microphone.",
    "aborted": "Voice capture was stopped before speech was detected.",
    "language-not-supported": "The selected voice language is not supported by this browser."
  };
  return messages[errorCode] || `Voice input failed: ${errorCode || "unknown browser error"}.`;
}

async function getMicrophoneStream() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not expose microphone access. Use Chrome or Edge on localhost.");
  }
  return navigator.mediaDevices.getUserMedia({ audio: true });
}

async function ensureMicrophoneAccess() {
  const stream = await getMicrophoneStream();
  stream.getTracks().forEach((track) => track.stop());
}

function clearVoiceTimers() {
  if (voiceSilenceTimer) {
    window.clearTimeout(voiceSilenceTimer);
    voiceSilenceTimer = null;
  }
  if (voiceRestartTimer) {
    window.clearTimeout(voiceRestartTimer);
    voiceRestartTimer = null;
  }
}

function scheduleVoiceSilenceStop() {
  if (!voiceIsCapturing || voiceFinalizing) {
    return;
  }
  if (voiceSilenceTimer) {
    window.clearTimeout(voiceSilenceTimer);
  }
  voiceSilenceTimer = window.setTimeout(() => {
    if (!voiceIsCapturing || voiceFinalizing) {
      return;
    }
    voiceFinalizing = true;
    setVoiceStatus("Processing...", "Processing...");
    try {
      voiceRecognition?.stop();
    } catch {
      finishBrowserVoiceCapture();
    }
  }, voiceSilenceTimeoutMs);
}

async function finishBrowserVoiceCapture() {
  clearVoiceTimers();
  voiceIsCapturing = false;
  voiceFinalizing = false;
  if (voiceDiscardCapture) {
    voiceDiscardCapture = false;
    voiceRecognition = null;
    voiceStartButton.disabled = false;
    voiceStopButton.disabled = true;
    voiceStartButton.setAttribute("aria-pressed", "false");
    return;
  }
  voiceStartButton.disabled = false;
  voiceStopButton.disabled = true;
  voiceStartButton.setAttribute("aria-pressed", "false");
  voiceRecognition = null;
  const transcript = voiceTranscript.value.trim();
  if (!transcript) {
    setVoiceStatus("No speech captured. Try again or type your question.", "Error");
    return;
  }
  setVoiceStatus("Responding...", "Responding...");
  await submitVoiceQuestion();
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

function openPasswordResetModal() {
  if (!passwordResetModal) {
    return;
  }
  const email = document.querySelector("#login-email").value || document.querySelector("#register-email").value;
  document.querySelector("#password-reset-email").value = email;
  passwordResetModal.classList.add("open");
  passwordResetModal.style.display = "grid";
  passwordResetModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#password-reset-email").focus(), 0);
}

function closePasswordResetModal() {
  if (!passwordResetModal) {
    return;
  }
  passwordResetModal.classList.remove("open");
  passwordResetModal.style.display = "";
  passwordResetModal.setAttribute("aria-hidden", "true");
}

function tourStorageKey(user = currentUser) {
  return user?.id ? `healthguardTourSeen:${user.id}` : "healthguardTourSeen:anonymous";
}

function shouldShowFirstTour(user) {
  return Boolean(user?.id && localStorage.getItem(tourStorageKey(user)) !== "1");
}

function markTourSeen(user = currentUser) {
  if (user?.id) {
    localStorage.setItem(tourStorageKey(user), "1");
  }
}

function openTour(options = {}) {
  if (!tourModal) {
    return;
  }
  tourStepIndex = options.stepIndex ?? 0;
  renderTourStep();
  tourModal.classList.add("open");
  tourModal.style.display = "grid";
  tourModal.setAttribute("aria-hidden", "false");
  setTimeout(() => tourNextButton?.focus(), 0);
}

function closeTour(markSeen = true) {
  if (!tourModal) {
    return;
  }
  tourModal.classList.remove("open");
  tourModal.style.display = "";
  tourModal.setAttribute("aria-hidden", "true");
  clearTourHighlight();
  if (markSeen) {
    markTourSeen();
  }
}

function renderTourStep() {
  const step = tourSteps[tourStepIndex];
  if (!step) {
    return;
  }
  tourTitle.textContent = step.title;
  tourCopy.textContent = step.copy;
  tourVisual.className = `tour-visual tour-visual-${step.visual}`;
  tourProgress.innerHTML = tourSteps
    .map((_, index) => `<span class="${index === tourStepIndex ? "active" : ""}" aria-label="Step ${index + 1} of ${tourSteps.length}"></span>`)
    .join("");
  tourPrevButton.disabled = tourStepIndex === 0;
  tourNextButton.textContent = tourStepIndex === tourSteps.length - 1 ? "Finish" : "Next";
  highlightTourTarget(step.target);
}

function highlightTourTarget(targetId) {
  clearTourHighlight();
  const target = document.querySelector(`#${targetId}`);
  if (!target) {
    return;
  }
  if (targetId === "reports-panel" && reportsPanel?.hidden) {
    reportsPanel.hidden = false;
  }
  target.classList.add("tour-highlight");
  target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearTourHighlight() {
  document.querySelectorAll(".tour-highlight").forEach((element) => element.classList.remove("tour-highlight"));
}

function nextTourStep() {
  if (tourStepIndex >= tourSteps.length - 1) {
    closeTour(true);
    return;
  }
  tourStepIndex += 1;
  renderTourStep();
}

function previousTourStep() {
  tourStepIndex = Math.max(0, tourStepIndex - 1);
  renderTourStep();
}

function maybeOpenFirstTour(user) {
  if (!shouldShowFirstTour(user)) {
    return;
  }
  setTimeout(() => openTour({ stepIndex: 0 }), 450);
}

function setCurrentUser(user, options = {}) {
  const previousUser = currentUser;
  currentUser = user;
  if (user) {
    localStorage.setItem("healthguardUser", JSON.stringify(user));
    activeChatConversationId = Number(localStorage.getItem(chatConversationStorageKey(user)) || "0") || null;
    activeVoiceConversationId = Number(localStorage.getItem(voiceConversationStorageKey(user)) || "0") || null;
    loadDocumentContextForCurrentUser();
  } else {
    localStorage.removeItem("healthguardUser");
    clearDocumentContext({ silent: true, user: previousUser });
  }
  renderAuthState();
  if (user && options.showTour) {
    maybeOpenFirstTour(user);
  }
}

function renderAuthState() {
  const showRoleTools = currentUser && currentUser.role !== "patient";
  roleOnlyElements.forEach((element) => {
    element.hidden = !showRoleTools;
  });
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
  homeTitle.textContent = "HealthGuard AI dashboard";
  homeSubtitle.textContent = currentUser.role === "patient"
    ? `Welcome, ${currentUser.name}. HealthGuard AI is your clinical safety workspace for asking health questions, completing guided symptom and lifestyle assessments, uploading medical documents, and creating doctor-ready educational reports.`
    : `Welcome, ${currentUser.name}. HealthGuard AI helps ${currentUser.role} users review safe health outputs, support clinical workflows, and manage doctor-ready educational reports.`;
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

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
    uploadedDocumentContext.safety_alerts?.length ? section("Safety alerts", list(uploadedDocumentContext.safety_alerts.map(escapeHtml))) : "",
    uploadedDocumentContext.detected_topics?.length ? section("Detected health topics", list(uploadedDocumentContext.detected_topics.map(escapeHtml))) : "",
    uploadedDocumentContext.suggested_actions?.length ? section("Relevant suggestions", list(uploadedDocumentContext.suggested_actions.map(escapeHtml))) : "",
    uploadedDocumentContext.doctor_questions?.length ? section("Questions for doctor", list(uploadedDocumentContext.doctor_questions.map(escapeHtml))) : "",
    section("Processing note", `<p>${uploadedDocumentContext.disclaimer}</p>`)
  ].join("");
}

function renderSourceCitations(sources = []) {
  const citedSources = sources.filter((source) => source?.excerpt);
  if (!citedSources.length) {
    return "";
  }
  return section(
    "Source citations",
    list(
      citedSources.slice(0, 6).map((source) => {
        const label = source.citation ? `[${source.citation}] ` : "";
        const score = source.similarity_score ? ` · score ${source.similarity_score}` : "";
        return escapeHtml(`${label}${source.title} (${source.source_type || "source"}${score}): ${source.excerpt}`);
      })
    )
  );
}

function documentContextKey(user = currentUser) {
  return user?.id ? `healthguardDocumentContext:${user.id}` : "healthguardDocumentContext";
}

function loadDocumentContextForCurrentUser() {
  const legacyContext = localStorage.getItem("healthguardDocumentContext");
  if (legacyContext) {
    localStorage.removeItem("healthguardDocumentContext");
  }
  uploadedDocumentContext = JSON.parse(localStorage.getItem(documentContextKey()) || "null");
}

function saveDocumentContextForCurrentUser() {
  if (!currentUser) {
    return;
  }
  localStorage.setItem(documentContextKey(), JSON.stringify(uploadedDocumentContext));
}

function consumeDocumentContextAfterReport() {
  if (!uploadedDocumentContext) {
    return;
  }
  clearDocumentContext({ silent: true });
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

  const consumedDocumentContext = uploadedDocumentContext;
  const generated = data.report;
  lastReportId = data.report_id;
  riskPill.textContent = `${generated.risk_summary.overall_risk_level} ${generated.risk_summary.risk_score}`;
  riskPill.className = generated.emergency_warning ? "pill urgent" : "pill";
  report.innerHTML = [
    section("Saved report", `<p>Report #${data.report_id} version v${data.report_version || 1} is saved for doctor review.</p>`),
    generated.emergency_warning ? section("Emergency warning", `<p>${generated.precautions[0]}</p>`) : "",
    section("Risk factors", list(generated.risk_summary.key_risk_factors)),
    section("Concerns to discuss with a doctor", list(generated.possible_health_concerns_to_discuss_with_doctor)),
    section("Precautions", list(generated.precautions)),
    generated.diet_plan?.length ? section("Diet plan", list(generated.diet_plan)) : "",
    generated.wellness_recommendations?.length ? section("Feel-better precautions", list(generated.wellness_recommendations)) : "",
    generated.physical_activity_plan?.length ? section("Physical activity plan", list(generated.physical_activity_plan)) : "",
    generated.doctor_department_guidance?.length ? section("Which doctor to consult", list(generated.doctor_department_guidance)) : "",
    generated.llm_summary ? section("AI summary", `<p>${generated.llm_summary}</p>`) : "",
    renderSourceCitations(generated.sources),
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
    consumedDocumentContext?.tuned_context
      ? section(
          "Uploaded document details",
          [
            `<p>${escapeHtml(consumedDocumentContext.rag_summary)}</p>`,
            consumedDocumentContext.suggested_actions?.length ? list(consumedDocumentContext.suggested_actions.map(escapeHtml)) : ""
          ].join("")
        )
      : "",
    section("Disclaimer", `<p>${generated.disclaimer}</p>`)
  ].join("");
  consumeDocumentContextAfterReport();
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
  saveDocumentContextForCurrentUser();
  renderDocumentStatus();
}

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

async function startVoiceInput() {
  if (!currentUser) {
    setVoiceStatus("Login first to use voice input.", "Error");
    return;
  }
  const Recognition = getSpeechRecognition();
  if (Recognition) {
    await startBrowserVoiceRecognition(Recognition);
    return;
  }
  if (window.MediaRecorder) {
    await startServerVoiceRecording();
    return;
  }
  setVoiceStatus("Voice input is not supported here. Type your question and tap Ask HealthGuard.", "Error");
}

async function startBrowserVoiceRecognition(Recognition) {
  try {
    await ensureMicrophoneAccess();
  } catch (error) {
    setVoiceStatus(`${escapeHtml(error.message || "Microphone permission failed.")} Type the transcript manually if needed.`, "Error");
    return;
  }
  window.speechSynthesis?.cancel();
  stopVoiceInput();
  clearVoiceTimers();
  voiceFinalTranscript = "";
  voiceManualStop = false;
  voiceDiscardCapture = false;
  voiceIsCapturing = true;
  voiceFinalizing = false;
  voiceRecognition = new Recognition();
  voiceRecognition.lang = "en-IN";
  voiceRecognition.interimResults = true;
  voiceRecognition.continuous = true;
  voiceRecognition.maxAlternatives = 1;
  voiceRecognition.onstart = () => {
    voiceStartButton.disabled = true;
    voiceStopButton.disabled = false;
    voiceStartButton.setAttribute("aria-pressed", "true");
    setVoiceStatus("Listening...", "Listening...");
    scheduleVoiceSilenceStop();
  };
  voiceRecognition.onresult = (event) => {
    let interim = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript;
      if (event.results[index].isFinal) {
        voiceFinalTranscript += `${transcript} `;
      } else {
        interim += transcript;
      }
    }
    const combined = `${voiceFinalTranscript}${interim}`.trim();
    voiceTranscript.value = combined;
    if (combined) {
      setVoiceStatus("Listening...", "Listening...");
      scheduleVoiceSilenceStop();
    }
  };
  voiceRecognition.onerror = (event) => {
    if (event.error === "no-speech" && voiceTranscript.value.trim()) {
      scheduleVoiceSilenceStop();
      return;
    }
    clearVoiceTimers();
    voiceIsCapturing = false;
    voiceFinalizing = false;
    voiceRecognition = null;
    voiceStartButton.disabled = false;
    voiceStopButton.disabled = true;
    voiceStartButton.setAttribute("aria-pressed", "false");
    setVoiceStatus(`${voiceErrorMessage(event.error)} You can still type the transcript and submit it.`, "Error");
  };
  voiceRecognition.onend = async () => {
    if (voiceFinalizing || voiceManualStop) {
      await finishBrowserVoiceCapture();
      return;
    }
    if (voiceIsCapturing) {
      voiceRestartTimer = window.setTimeout(() => {
        try {
          voiceRecognition?.start();
        } catch {
          voiceFinalizing = true;
          finishBrowserVoiceCapture();
        }
      }, 250);
      return;
    }
    voiceRecognition = null;
    voiceStartButton.disabled = false;
    voiceStopButton.disabled = true;
    voiceStartButton.setAttribute("aria-pressed", "false");
  };
  try {
    voiceRecognition.start();
  } catch (error) {
    setVoiceStatus(`${escapeHtml(error.message || "Voice recognition could not start.")} Trying server transcription instead...`, "Error");
    clearVoiceTimers();
    voiceIsCapturing = false;
    voiceFinalizing = false;
    voiceRecognition = null;
    voiceStartButton.disabled = false;
    voiceStopButton.disabled = true;
    voiceStartButton.setAttribute("aria-pressed", "false");
    if (window.MediaRecorder) {
      await startServerVoiceRecording();
    }
  }
}

function stopVoiceInput(options = {}) {
  voiceDiscardCapture = Boolean(options.discard);
  if (voiceMediaRecorder && voiceMediaRecorder.state === "recording") {
    voiceManualStop = true;
    if (!voiceDiscardCapture) {
      setVoiceStatus("Processing...", "Processing...");
    }
    voiceMediaRecorder.stop();
    return;
  }
  if (voiceRecognition) {
    voiceManualStop = true;
    voiceFinalizing = !voiceDiscardCapture;
    clearVoiceTimers();
    if (!voiceDiscardCapture) {
      setVoiceStatus("Processing...", "Processing...");
    }
    voiceRecognition.stop();
  }
}

async function startServerVoiceRecording() {
  stopVoiceInput();
  stopVoiceTracks();
  clearVoiceTimers();
  try {
    voiceAudioStream = await getMicrophoneStream();
  } catch (error) {
    setVoiceStatus(`${escapeHtml(error.message || "Microphone permission failed.")} Type the transcript manually if needed.`, "Error");
    return;
  }
  window.speechSynthesis?.cancel();
  voiceAudioChunks = [];
  voiceManualStop = false;
  voiceDiscardCapture = false;
  voiceIsCapturing = true;
  voiceFinalizing = false;
  const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
    ? "audio/webm;codecs=opus"
    : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "";
  voiceMediaRecorder = new MediaRecorder(voiceAudioStream, mimeType ? { mimeType } : undefined);
  voiceMediaRecorder.ondataavailable = (event) => {
    if (event.data?.size) {
      voiceAudioChunks.push(event.data);
    }
  };
  voiceMediaRecorder.onerror = (event) => {
    setVoiceStatus(`Audio recording failed: ${escapeHtml(event.error?.message || "unknown recording error")}.`, "Error");
    stopVoiceTracks();
  };
  voiceMediaRecorder.onstop = async () => {
    voiceStartButton.disabled = false;
    voiceStopButton.disabled = true;
    voiceStartButton.setAttribute("aria-pressed", "false");
    stopVoiceTracks();
    const blob = new Blob(voiceAudioChunks, { type: voiceMediaRecorder?.mimeType || "audio/webm" });
    const durationMs = Date.now() - voiceRecordingStartedAt;
    voiceMediaRecorder = null;
    voiceIsCapturing = false;
    voiceFinalizing = false;
    if (voiceDiscardCapture) {
      voiceDiscardCapture = false;
      return;
    }
    if (!blob.size || durationMs < 1500) {
      setVoiceStatus("Recording was too short. Hold the mic for at least two seconds, speak clearly, then press Stop.", "Error");
      return;
    }
    await transcribeRecordedVoice(blob);
  };
  voiceRecordingStartedAt = Date.now();
  voiceMediaRecorder.start(1000);
  voiceStartButton.disabled = true;
  voiceStopButton.disabled = false;
  voiceStartButton.setAttribute("aria-pressed", "true");
  setVoiceStatus("Listening...", "Listening...");
}

function stopVoiceTracks() {
  if (voiceAudioStream) {
    voiceAudioStream.getTracks().forEach((track) => track.stop());
    voiceAudioStream = null;
  }
}

async function transcribeRecordedVoice(blob) {
  setVoiceStatus("Processing...", "Processing...");
  const body = new FormData();
  body.append("audio", blob, "voice-input.webm");
  const response = await fetch("/api/voice/transcribe", {
    method: "POST",
    headers: authHeaders(),
    body
  });
  const data = await response.json();
  if (!response.ok) {
    setVoiceStatus("Voice transcription is temporarily unavailable. Type your question in the transcript box and tap Ask HealthGuard.", `Error ${response.status}`);
    return;
  }
  voiceTranscript.value = data.transcript;
  setVoiceStatus("Responding...", "Responding...");
  await submitVoiceQuestion();
}

async function submitChatQuestion() {
  if (!currentUser) {
    setChatStatus("Login first to ask HealthGuard.", "Error");
    return;
  }
  const question = chatQuestion?.value.trim() || "";
  if (!question) {
    setChatStatus("Type a health question before submitting.", "Error");
    chatQuestion?.focus();
    return;
  }
  if (!document.querySelector("#consent").checked) {
    setChatStatus("Consent is required before processing health information.", "Error");
    return;
  }
  if (chatSubmitButton) {
    chatSubmitButton.disabled = true;
  }
  if (chatQuestion) {
    chatQuestion.value = "";
  }
  appendVisibleChatMessage("user", question);
  appendVisibleChatMessage("assistant", "HealthGuard is checking trusted guidance...");
  setChatStatus("", "Working");
  const payload = {
    question: uploadedDocumentContext?.tuned_context
      ? `${question}\n\nUploaded document context:\n${uploadedDocumentContext.tuned_context}`
      : question,
    profile: optionalVoiceProfile(),
    consent_to_process_health_data: true,
    conversation_id: activeChatConversationId,
    report_id: lastReportId
  };
  try {
    renderChatFeedback(null);
    if (chatUrgentPanel) {
      chatUrgentPanel.hidden = true;
    }
    const response = await fetch("/api/chat/health-question/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const data = await response.json();
      updateLastVisibleAssistantMessage("Chatbot failed. Please try again.");
      setChatStatus(formatApiError(response, data, "Chatbot failed."), `Error ${response.status}`);
      return;
    }
    if (!response.body) {
      const data = await response.json();
      activeChatConversationId = data.conversation_id || activeChatConversationId;
      localStorage.setItem(chatConversationStorageKey(), String(activeChatConversationId));
      renderUrgentChatState(data);
      updateLastVisibleAssistantMessage(data.answer);
      setChatStatus("", data.red_flags?.length ? "Alert" : "Answered");
      renderChatFeedback(data.assistant_message_id);
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let streamedAnswer = "";
    setChatStatus("", "Working");
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";
      for (const chunk of chunks) {
        const line = chunk.split("\n").find((item) => item.startsWith("data: "));
        if (!line) {
          continue;
        }
        const event = JSON.parse(line.slice(6));
        if (event.type === "token") {
          streamedAnswer += event.text;
          updateLastVisibleAssistantMessage(streamedAnswer.trim() || "HealthGuard is checking trusted guidance...");
        }
        if (event.type === "done") {
          const data = event.payload;
          activeChatConversationId = data.conversation_id || activeChatConversationId;
          localStorage.setItem(chatConversationStorageKey(), String(activeChatConversationId));
          renderUrgentChatState(data);
          updateLastVisibleAssistantMessage(data.answer);
          setChatStatus("", data.red_flags?.length ? "Alert" : "Answered");
          renderChatFeedback(data.assistant_message_id);
        }
      }
    }
  } catch (error) {
    updateLastVisibleAssistantMessage("Chatbot request failed. Please try again.");
    setChatStatus(`Chatbot request failed: ${escapeHtml(error.message || "network error")}.`, "Error");
  } finally {
    if (chatSubmitButton) {
      chatSubmitButton.disabled = false;
    }
  }
}

function copyAssessmentQuestionToChat() {
  const assessmentQuestion = document.querySelector("#question").value.trim();
  if (!assessmentQuestion) {
    setChatStatus("The assessment question is empty. Type a question here or fill the assessment field first.", "Error");
    return;
  }
  chatQuestion.value = assessmentQuestion;
  chatQuestion.focus();
  setChatStatus("Assessment question copied. You can edit it before asking the chatbot.", "Ready");
}

function clearChatAssistant() {
  if (chatQuestion) {
    chatQuestion.value = "";
  }
  visibleChatMessages = [];
  if (chatHistoryPanel) {
    chatHistoryPanel.innerHTML = "";
  }
  if (chatUrgentPanel) {
    chatUrgentPanel.hidden = true;
  }
  renderChatFeedback(null);
  setChatStatus("Cleared. Type a health question below.", "Ready");
  chatQuestion?.focus();
}

async function submitVoiceQuestion() {
  if (!currentUser) {
    setVoiceStatus("Login first to ask HealthGuard.", "Error");
    return;
  }
  const transcript = voiceTranscript.value.trim();
  if (!transcript) {
    setVoiceStatus("Speak or type a question before submitting.", "Error");
    return;
  }
  if (!document.querySelector("#consent").checked) {
    setVoiceStatus("Consent is required before processing health information.", "Error");
    return;
  }
  setVoiceStatus("Responding...", "Responding...");
  const payload = {
    question: transcript,
    consent_to_process_health_data: true,
    conversation_id: activeVoiceConversationId,
    voice_mode: true,
    source: "voice"
  };
  voiceTranscript.value = "";
  const response = await fetch("/api/chat/health-question", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    lastVoiceAnswer = "";
    voiceReadButton.disabled = true;
    setVoiceStatus(formatApiError(response, data, "Voice assistant failed."), `Error ${response.status}`);
    return;
  }
  activeVoiceConversationId = data.conversation_id || activeVoiceConversationId;
  if (activeVoiceConversationId) {
    localStorage.setItem(voiceConversationStorageKey(), String(activeVoiceConversationId));
  }
  lastVoiceAnswer = data.answer;
  voiceReadButton.disabled = false;
  setVoiceStatus(
    renderChatAnswer(transcript, data).replace("<h3>Question</h3>", "<h3>Transcript</h3>"),
    voiceStageLabel(data)
  );
  speakVoiceAnswer();
}

function speakVoiceAnswer() {
  if (!lastVoiceAnswer || !window.speechSynthesis) {
    setVoiceStatus(voiceStatus.innerHTML || "No answer is ready to read.", "Error");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(lastVoiceAnswer);
  utterance.lang = "en-IN";
  utterance.rate = 0.95;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function clearVoiceAssistant() {
  stopVoiceInput({ discard: true });
  clearVoiceTimers();
  voiceIsCapturing = false;
  voiceFinalizing = false;
  voiceDiscardCapture = false;
  window.speechSynthesis?.cancel();
  voiceTranscript.value = "";
  voiceFinalTranscript = "";
  lastVoiceAnswer = "";
  voiceReadButton.disabled = true;
  setVoiceStatus("Press Start mic and speak clearly. Your browser may ask for microphone permission.", "Idle");
}

function clearDocumentContext(options = {}) {
  uploadedDocumentContext = null;
  localStorage.removeItem("healthguardDocumentContext");
  localStorage.removeItem(documentContextKey(options.user || currentUser));
  if (documentFile) {
    documentFile.value = "";
  }
  if (!options.silent) {
    renderDocumentStatus();
  }
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
  await loadNotifications();
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

async function loadNotifications() {
  patientNotifications = [];
  if (!currentUser) {
    return;
  }
  const response = await fetch("/api/notifications", { headers: authHeaders() });
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  patientNotifications = data.items || [];
}

function renderNotifications() {
  if (!patientNotifications.length) {
    return "";
  }
  const items = patientNotifications
    .slice(0, 5)
    .map(
      (item) => `<div class="notification-item ${item.status === "unread" ? "unread" : ""}">
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.message)}</p>
          <small>${escapeHtml(item.created_at)}</small>
        </div>
        ${item.status === "unread" ? `<button class="secondary" type="button" data-read-notification="${item.id}">Mark read</button>` : ""}
      </div>`
    )
    .join("");
  return section("Patient notifications", items);
}

function renderSavedReports() {
  if (!savedReports.length) {
    historyPanel.textContent = "No saved reports yet.";
    return;
  }
  const totalPages = Math.ceil(savedReports.length / savedReportsPageSize);
  const pageStart = (savedReportsPage - 1) * savedReportsPageSize;
  const pageItems = savedReports.slice(pageStart, pageStart + savedReportsPageSize);
  const canReviewReports = currentUser && ["doctor", "dietician"].includes(currentUser.role);
  const reportList = pageItems
    .map(
      (item) => {
        const reviewAction = canReviewReports
          ? `<button class="secondary" type="button" onclick="approveReport(${item.id})">Approve</button>`
          : "";
        return `<div class="history-item">
        <div>
          <strong>#${item.id}</strong> ${item.patient_summary.location || "Unknown location"} -
          ${item.patient_summary.occupation || "Unknown occupation"} -
          ${item.risk_level} ${item.risk_score}
          <br />
          Review: ${item.doctor_review_status} · Version v${item.current_version || 1}
          ${(item.version_history || []).length ? `<br /><small>${item.version_history.length} version event(s) recorded</small>` : ""}
        </div>
        <div class="actions">
          <a class="button-link" href="/api/reports/${item.id}/download?demo_token=${encodeURIComponent(currentUser.demo_token)}">PDF</a>
          ${reviewAction}
        </div>
      </div>`;
      }
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
  const privacyNote = currentUser?.role === "patient"
    ? `<p class="privacy-note">Showing reports saved for ${escapeHtml(currentUser.name)} only.</p>`
    : `<p class="privacy-note">Showing reports owned by this logged-in account only. Use Role tools for patient review queues.</p>`;
  historyPanel.innerHTML = `${renderNotifications()}${privacyNote}${reportList}${pager}`;
}

function renderPatientReportFolders(folders = []) {
  const controls = `<div class="doctor-filter-bar">
    <button class="secondary ${doctorQueueStatus === "pending" ? "active-filter" : ""}" type="button" data-doctor-filter="pending">Pending</button>
    <button class="secondary ${doctorQueueStatus === "reviewed" ? "active-filter" : ""}" type="button" data-doctor-filter="reviewed">Reviewed</button>
    <button class="secondary ${doctorQueueStatus === "urgent" ? "active-filter" : ""}" type="button" data-doctor-filter="urgent">Urgent</button>
    <button class="secondary ${doctorQueueStatus === "all" ? "active-filter" : ""}" type="button" data-doctor-filter="all">All</button>
  </div>`;
  if (!folders.length) {
    return `${controls}${section("Patient folders", "<p>No patient reports match this filter.</p>")}`;
  }
  return controls + folders
    .map((folder) => {
      const summary = folder.patient_summary || {};
      const title = [
        `Patient #${folder.patient_id}`,
        summary.location || "Unknown location",
        summary.occupation || "Unknown occupation"
      ].join(" - ");
      const reports = folder.reports
        .map(
          (item) => {
            const factors = (item.risk_factors || []).slice(0, 3).map(escapeHtml).join(", ");
            const questions = (item.doctor_questions || []).slice(0, 2).map(escapeHtml);
            return `<div class="history-item patient-folder-report">
            <div>
              <strong>#${item.id}</strong> ${item.risk_level} ${item.risk_score}
              <br />
              Review: ${item.doctor_review_status} · Version v${item.current_version || 1}
              <div class="patient-problem">
                <span>Patient problem</span>
                <p>${escapeHtml(item.problem_summary || "Review generated report.")}</p>
                ${factors ? `<small>Key factors: ${factors}</small>` : ""}
                ${item.uses_uploaded_document ? `<small>Includes uploaded document context.</small>` : ""}
                ${questions.length ? `<small>Doctor questions: ${questions.join(" | ")}</small>` : ""}
              </div>
            </div>
            <div class="actions">
              <a class="button-link" href="/api/reports/${item.id}/download?demo_token=${encodeURIComponent(currentUser.demo_token)}">PDF</a>
              <button class="secondary" type="button" onclick="assignReport(${item.id})">Assign</button>
            </div>
            <div class="doctor-review-controls">
              <label>
                Priority
                <select id="priority-${item.id}">
                  <option value="routine" ${item.review_priority === "routine" ? "selected" : ""}>Routine</option>
                  <option value="priority" ${item.review_priority === "priority" ? "selected" : ""}>Priority</option>
                  <option value="urgent" ${item.review_priority === "urgent" ? "selected" : ""}>Urgent</option>
                </select>
              </label>
              <label>
                Status
                <select id="status-${item.id}">
                  ${["submitted", "assigned", "in_review", "needs_patient_followup", "reviewed", "approved", "escalated", "closed"].map((status) => `<option value="${status}" ${item.doctor_review_status === status ? "selected" : ""}>${status.replaceAll("_", " ")}</option>`).join("")}
                </select>
              </label>
              <label>
                Comments
                <input id="comments-${item.id}" placeholder="Doctor comments for patient" value="${escapeHtml(item.doctor_comments || "")}" />
              </label>
              <label>
                Signature
                <input id="signature-${item.id}" placeholder="Clinician signature" value="${escapeHtml(item.clinician_signature || currentUser.name || "")}" />
              </label>
              <button type="button" onclick="submitDoctorReview(${item.id})">Update review</button>
            </div>
          </div>`;
          }
        )
        .join("");
      return section(title, `<p>${folder.pending_count} pending of ${folder.total_count} report(s).</p>${reports}`);
    })
    .join("");
}

async function assignReport(reportId) {
  if (!currentUser || !["doctor", "dietician"].includes(currentUser.role)) {
    roleOutput.textContent = "Login as a doctor or dietician to assign reports.";
    return;
  }
  const priority = document.querySelector(`#priority-${reportId}`)?.value || "routine";
  const response = await fetch(`/api/doctor/reports/${reportId}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ reviewer_id: currentUser.id, priority })
  });
  const data = await response.json();
  roleOutput.innerHTML = response.ok
    ? `${section("Assignment updated", `<p>Report #${data.id} assigned to ${currentUser.name} with ${priority} priority.</p>`)}${await loadDoctorQueue({ returnHtml: true })}`
    : formatApiError(response, data, "Unable to assign report.");
}

async function submitDoctorReview(reportId) {
  if (!currentUser || !["doctor", "dietician"].includes(currentUser.role)) {
    roleOutput.textContent = "Login as a doctor or dietician to review reports.";
    return;
  }
  const payload = {
    status: document.querySelector(`#status-${reportId}`)?.value || "in_review",
    comments: document.querySelector(`#comments-${reportId}`)?.value || null,
    final_clinical_notes: document.querySelector(`#comments-${reportId}`)?.value || null,
    clinician_signature: document.querySelector(`#signature-${reportId}`)?.value || currentUser.name,
    review_priority: document.querySelector(`#priority-${reportId}`)?.value || "routine"
  };
  const response = await fetch(`/api/doctor/reports/${reportId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  roleOutput.innerHTML = response.ok
    ? `${section("Review updated", `<p>Report #${data.id} status changed to ${data.doctor_review_status}. Patient notification was created.</p>`)}${await loadDoctorQueue({ returnHtml: true })}`
    : formatApiError(response, data, "Unable to update review.");
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
  setCurrentUser(data, { showTour: true });
});

async function logoutCurrentUser() {
  if (currentUser?.demo_token) {
    await fetch("/api/auth/logout", { method: "POST", headers: authHeaders() }).catch(() => null);
  }
  closeTour(false);
  activeChatConversationId = null;
  activeVoiceConversationId = null;
  lastChatAssistantMessageId = null;
  localStorage.removeItem(chatConversationStorageKey(currentUser));
  localStorage.removeItem(voiceConversationStorageKey(currentUser));
  closeChatDialog();
  setCurrentUser(null);
}

async function requestPasswordReset() {
  const email = document.querySelector("#password-reset-email").value || document.querySelector("#login-email").value;
  const response = await fetch("/api/auth/password-reset/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });
  const data = await response.json();
  authStatus.textContent = response.ok ? data.message : formatApiError(response, data, "Password reset request failed.");
}

async function confirmPasswordReset() {
  const response = await fetch("/api/auth/password-reset/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.querySelector("#password-reset-email").value,
      token: document.querySelector("#password-reset-token").value,
      new_password: document.querySelector("#password-reset-new-password").value
    })
  });
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = formatApiError(response, data, "Password reset failed.");
    return;
  }
  closePasswordResetModal();
  authStatus.textContent = data.message;
}

logoutButton.addEventListener("click", logoutCurrentUser);
homeLogoutButton.addEventListener("click", logoutCurrentUser);
menuLogoutButton?.addEventListener("click", logoutCurrentUser);
mobileMenuToggle?.addEventListener("click", () => {
  setMobileMenu(!workspaceMenu?.classList.contains("open"));
});
loadRoleData.addEventListener("click", loadRoleActions);
documentForm?.addEventListener("submit", uploadDocument);
clearDocumentContextButton?.addEventListener("click", clearDocumentContext);
foodGroupSelect?.addEventListener("change", populateFoodItems);
addFoodButton?.addEventListener("click", addSelectedFood);
voiceStartButton?.addEventListener("click", startVoiceInput);
voiceStopButton?.addEventListener("click", stopVoiceInput);
voiceSubmitButton?.addEventListener("click", submitVoiceQuestion);
voiceReadButton?.addEventListener("click", speakVoiceAnswer);
voiceClearButton?.addEventListener("click", clearVoiceAssistant);
chatSubmitButton?.addEventListener("click", submitChatQuestion);
chatCopyAssessmentButton?.addEventListener("click", copyAssessmentQuestionToChat);
chatClearButton?.addEventListener("click", clearChatAssistant);
chatLauncher?.addEventListener("click", openChatDialog);
chatCloseButton?.addEventListener("click", closeChatDialog);
chatNewButton?.addEventListener("click", startNewChatConversation);
chatExportButton?.addEventListener("click", exportActiveChat);
chatConversationSelect?.addEventListener("change", async () => {
  const selected = Number(chatConversationSelect.value || "0") || null;
  activeChatConversationId = selected;
  if (selected) {
    localStorage.setItem(chatConversationStorageKey(), String(selected));
  } else {
    localStorage.removeItem(chatConversationStorageKey());
    renderChatHistory([]);
    setChatStatus("New chat started. Ask one health question.", "Ready");
    return;
  }
  await loadChatHistory();
});
chatStartersPanel?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-chat-starter]");
  if (!button) {
    return;
  }
  chatQuestion.value = decodeURIComponent(button.dataset.chatStarter);
  chatQuestion.focus();
});
chatFeedbackPanel?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-chat-feedback]");
  if (!button) {
    return;
  }
  sendChatFeedback(button.dataset.chatFeedback);
});
chatQuestion?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitChatQuestion();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && chatDialog?.classList.contains("open")) {
    closeChatDialog();
  }
  if (event.key === "Escape" && workspaceMenu?.classList.contains("open")) {
    setMobileMenu(false);
  }
});
verifyEmailButton.addEventListener("click", verifyEmail);
loadConfirmationEmailButton?.addEventListener("click", loadLatestConfirmationEmail);
resendConfirmationButton.addEventListener("click", resendConfirmation);
closeVerificationModalButton?.addEventListener("click", closeVerificationModal);
verificationModal?.querySelector(".modal-backdrop")?.addEventListener("click", closeVerificationModal);
requestPasswordResetButton?.addEventListener("click", openPasswordResetModal);
closePasswordResetModalButton?.addEventListener("click", closePasswordResetModal);
passwordResetModal?.querySelector(".modal-backdrop")?.addEventListener("click", closePasswordResetModal);
sendPasswordResetButton?.addEventListener("click", requestPasswordReset);
confirmPasswordResetButton?.addEventListener("click", confirmPasswordReset);
openTourButton?.addEventListener("click", () => {
  setMobileMenu(false);
  openTour({ stepIndex: 0 });
});
closeTourButton?.addEventListener("click", () => closeTour(true));
tourModal?.querySelector(".modal-backdrop")?.addEventListener("click", () => closeTour(true));
tourNextButton?.addEventListener("click", nextTourStep);
tourPrevButton?.addEventListener("click", previousTourStep);
tourSkipButton?.addEventListener("click", () => closeTour(true));
document.addEventListener("click", (event) => {
  if (event.target.matches("[data-open-verification]")) {
    openVerificationModal(pendingVerificationEmail || document.querySelector("#login-email").value);
  }
  const scrollTarget = event.target.closest("[data-scroll-target]");
  if (scrollTarget) {
    if (scrollTarget.hidden || scrollTarget.closest("[hidden]")) {
      return;
    }
    document.querySelectorAll(".menu-button").forEach((button) => button.classList.remove("active"));
    if (scrollTarget.classList.contains("menu-button")) {
      scrollTarget.classList.add("active");
    }
    if (scrollTarget.dataset.scrollTarget === "reports-panel" && reportsPanel?.hidden) {
      reportsPanel.hidden = false;
    }
    document.querySelector(`#${scrollTarget.dataset.scrollTarget}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setMobileMenu(false);
  } else if (
    workspaceMenu?.classList.contains("open")
    && !event.target.closest("#workspace-menu")
    && !event.target.closest("#mobile-menu-toggle")
  ) {
    setMobileMenu(false);
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
  const doctorFilter = event.target.closest("[data-doctor-filter]");
  if (doctorFilter) {
    doctorQueueStatus = doctorFilter.dataset.doctorFilter;
    loadDoctorQueue();
  }
  const readNotification = event.target.closest("[data-read-notification]");
  if (readNotification) {
    fetch(`/api/notifications/${readNotification.dataset.readNotification}/read`, {
      method: "POST",
      headers: authHeaders()
    }).then(() => loadHistory({ resetPage: false }));
  }
  const removeFood = event.target.closest("[data-remove-food]");
  if (removeFood) {
    selectedFoods.splice(Number(removeFood.dataset.removeFood), 1);
    renderSelectedFoods();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && tourModal?.classList.contains("open")) {
    closeTour(true);
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
      category: document.querySelector("#knowledge-category").value || "General",
      citation: document.querySelector("#knowledge-citation").value || null,
      content: document.querySelector("#knowledge-content").value
    })
  });
  const data = await response.json();
  roleOutput.textContent = response.ok
    ? `Knowledge #${data.id} added in ${data.category} and approved.`
    : formatApiError(response, data, "Unable to add knowledge.");
});

async function loadRoleActions() {
  if (!currentUser) {
    roleOutput.textContent = "Login first to load role actions.";
    return;
  }
  if (["doctor", "dietician"].includes(currentUser.role)) {
    await loadDoctorQueue();
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

async function loadDoctorQueue(options = {}) {
  const response = await fetch(`/api/doctor/reports/queue?status=${encodeURIComponent(doctorQueueStatus)}`, { headers: authHeaders() });
  const data = await response.json();
  const html = response.ok
    ? `${renderDoctorQueueCounts(data.counts)}${renderPatientReportFolders(data.patient_folders)}`
    : formatApiError(response, data, "Unable to load doctor queue.");
  if (options.returnHtml) {
    return html;
  }
  roleOutput.innerHTML = html;
  return html;
}

function renderDoctorQueueCounts(counts = {}) {
  return `<div class="doctor-queue-counts">
    <span>All ${counts.all || 0}</span>
    <span>Pending ${counts.pending || 0}</span>
    <span>Reviewed ${counts.reviewed || 0}</span>
    <span>Urgent ${counts.urgent || 0}</span>
  </div>`;
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
  setCurrentUser(data, { showTour: true });
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
