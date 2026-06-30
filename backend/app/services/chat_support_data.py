from __future__ import annotations


SIMPLE_CHAT_ANSWERS: list[tuple[tuple[str, ...], str]] = [
    (("hi", "hello", "hey"), "Hi. Ask one health question."),
    (("who are you", "what are you"), "I am HealthGuard, a safety-focused health assistant."),
    (("what can you do", "help me", "chatbot", "what kind of answer"), "I answer health doubts, explain documents, ask follow-ups, and suggest doctor-ready questions."),
    (("fever",), "Track temperature, fluids, duration, breathlessness, confusion."),
    (("headache",), "Note severity, triggers, vision changes, vomiting, sudden onset."),
    (("tired", "fatigue", "weakness"), "Track sleep, stress, diet, fever, and persistence."),
    (("back pain",), "Track duration, injury, leg numbness, weakness, bladder changes."),
    (("stomach pain", "abdominal pain"), "Track location, food trigger, vomiting, fever, stool changes."),
    (("diet", "food", "eat"), "Choose protein, vegetables, whole grains, fruit, water."),
    (("water", "hydration"), "Drink regularly. Increase fluids with heat, fever, sweating."),
    (("sleep",), "Keep fixed timing, reduce caffeine, avoid screens before bed."),
    (("exercise", "workout"), "Start with walking and stretching. Stop for chest pain."),
    (("report",), "Reports summarize risks, precautions, doctor questions, documents."),
    (("upload", "document"), "Upload lab reports, prescriptions, discharge summaries, scan notes, or doctor notes. Avoid ID, bank, resume, or unrelated files."),
    (("doctor", "consult"), "Consult if symptoms persist, worsen, repeat, or disrupt life."),
]

CHATBOT_PROMPT_VERSION = "healthguard-chat-concise-v2"

FAQ_KNOWLEDGE_BASE: list[dict] = [
    {
        "id": "uploadable_documents",
        "patterns": (
            "what kind of docs",
            "what documents",
            "what can i upload",
            "which documents",
            "upload documents",
            "upload reports",
        ),
        "answer": "Upload lab reports, prescriptions, discharge summaries, scan notes, or doctor notes. Avoid ID, bank, resume, or unrelated files.",
    },
    {
        "id": "expected_chatbot_answers",
        "patterns": (
            "what kind of answer",
            "what answer",
            "what can chatbot answer",
            "what can bot answer",
            "what can i expect",
            "chatbot response",
        ),
        "answer": "Chatbot gives short health guidance, follow-up questions, document explanations, and doctor-visit prep.",
    },
    {
        "id": "healthguard_purpose",
        "patterns": (
            "what is healthguard",
            "what does healthguard do",
            "application purpose",
            "app purpose",
        ),
        "answer": "HealthGuard AI helps you ask health doubts, complete assessments, upload documents, and prepare doctor-ready reports.",
    },
    {
        "id": "medicine_policy",
        "patterns": (
            "can i get medicine advice",
            "can you prescribe",
            "give medicine",
            "suggest medicine",
            "recommend medicine",
            "dosage",
        ),
        "answer": "I cannot prescribe medicine or dosage. Share symptoms and duration; a clinician should confirm safe treatment.",
    },
    {
        "id": "doctor_visit",
        "patterns": (
            "when should i visit doctor",
            "when should i see a doctor",
            "doctor visit",
            "consult doctor",
        ),
        "answer": "See a doctor if symptoms persist, worsen, repeat, or affect breathing, chest comfort, alertness, or hydration.",
    },
]

CONCISE_CHAT_RULES = [
    "Answer in 1-3 short lines.",
    "Use minimal words.",
    "Use bullets only when needed.",
    "Ask one follow-up question only if required.",
    "Treat voice and chat as lightweight Q&A, not report generation.",
    "Do not diagnose.",
    "Do not prescribe medicine.",
    "Use trusted retrieved context when available.",
    "Do not repeat disclaimers.",
]

VOICE_INTENT_TRAINING_DATA = {
    "fever_rash": {
        "keywords": ("fever", "rash", "rashes", "spots"),
        "requires_any": ("rash", "rashes", "spots"),
        "concern": "fever with rash",
        "guidance": "Drink water, rest, avoid scratching, avoid new foods/medicines, and note temperature/rash changes.",
        "followups": [
            {
                "slot": "duration",
                "question": "How many days have you had the fever?",
                "markers": ("day", "days", "week", "weeks", "hour", "hours", "today", "yesterday", "since"),
            },
            {
                "slot": "rash_detail",
                "question": "Is the rash spreading, itchy, painful, or blister-like?",
                "markers": ("spreading", "itchy", "painful", "blister", "not spreading", "no itch"),
            },
            {
                "slot": "red_flags",
                "question": "Any high fever, weakness, vomiting, bleeding, or breathing difficulty?",
                "markers": ("breathing", "weakness", "vomiting", "bleeding", "confusion", "swelling", "no breathing"),
            },
            {
                "slot": "trigger",
                "question": "Did you take any new medicine or eat anything unusual recently?",
                "markers": ("new medicine", "new medication", "new food", "allergy", "unusual", "ate"),
            },
        ],
    },
    "cough_cold": {
        "keywords": ("cough", "cold", "sore throat", "runny nose"),
        "concern": "cough/cold symptoms",
        "guidance": "Rest, warm fluids, steam if comfortable, light food, and track fever, mucus, chest pain, or breathing.",
        "followups": [
            {
                "slot": "duration",
                "question": "How many days have you had the cough or cold?",
                "markers": ("day", "days", "week", "weeks", "hour", "hours", "today", "yesterday", "since"),
            },
            {
                "slot": "red_flags",
                "question": "Do you have fever, breathing difficulty, or chest pain?",
                "markers": ("fever", "temperature", "breathing", "chest pain", "no fever", "no breathing"),
            },
            {
                "slot": "cough_type",
                "question": "Is the cough dry or with mucus?",
                "markers": ("dry", "mucus", "phlegm", "wet cough"),
            },
        ],
    },
    "stomach": {
        "keywords": ("stomach pain", "abdominal pain", "loose motion", "diarrhea", "vomiting"),
        "concern": "stomach symptoms",
        "guidance": "Sip fluids, eat light foods, avoid oily/spicy meals, and note pain location, stool changes, vomiting.",
        "followups": [
            {
                "slot": "pain_location",
                "question": "Where is the stomach pain located?",
                "markers": ("left", "right", "upper", "lower", "middle", "near", "around"),
            },
            {
                "slot": "stool",
                "question": "Any vomiting, loose motions, fever, or blood in stool?",
                "markers": ("loose", "motion", "stool", "blood", "vomiting", "nausea", "fever"),
            },
            {
                "slot": "duration",
                "question": "How long has this been happening?",
                "markers": ("day", "days", "week", "weeks", "hour", "hours", "today", "yesterday", "since"),
            },
        ],
    },
    "fever": {
        "keywords": ("fever", "temperature", "temp"),
        "concern": "fever",
        "guidance": "Rest, hydrate, eat light balanced food, and write temperature, duration, triggers, medicines.",
        "followups": [
            {
                "slot": "duration",
                "question": "How many days have you had the fever?",
                "markers": ("day", "days", "week", "weeks", "hour", "hours", "today", "yesterday", "since"),
            },
            {
                "slot": "red_flags",
                "question": "Any breathing trouble, confusion, vomiting, or severe weakness?",
                "markers": ("breathing", "confusion", "vomiting", "weakness", "no breathing"),
            },
        ],
    },
    "general": {
        "keywords": (),
        "concern": "your symptoms",
        "guidance": "Rest, hydrate, eat light balanced food, and write symptom duration, triggers, and medicines.",
        "followups": [
            {
                "slot": "duration",
                "question": "How long has this been happening?",
                "markers": ("day", "days", "week", "weeks", "hour", "hours", "today", "yesterday", "since"),
            },
            {
                "slot": "red_flags",
                "question": "Is it worsening or causing breathing trouble, confusion, or severe weakness?",
                "markers": ("worse", "worsening", "breathing", "confusion", "weakness", "no breathing"),
            },
        ],
    },
}
