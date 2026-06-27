from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.app.core.env import load_dotenv
from backend.app.db.store import json_dumps
from backend.app.schemas.health import AssessmentRequest, ChatRequest, KnowledgeSource


class LLMService:
    def __init__(self) -> None:
        load_dotenv(override=True)
        self.provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
        self.model = self._model_for_provider()
        self.active_model = self.model
        self.timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "25") or "25")

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured(),
            "provider": self.provider,
            "model": self.model,
            "test_mode": os.getenv("LLM_TEST_MODE") == "1",
            "missing": [] if self.configured() else [self._api_key_name()],
        }

    def configured(self) -> bool:
        return os.getenv("LLM_TEST_MODE") == "1" or bool(self._api_key_value())

    def _api_key_name(self) -> str:
        if self.provider == "gemini":
            return "GEMINI_API_KEY"
        if self.provider == "openai":
            return "OPENAI_API_KEY"
        if self.provider in {"huggingface", "hf"}:
            return "HF_TOKEN"
        return f"{self.provider.upper()}_API_KEY"

    def _api_key_value(self) -> str:
        if self.provider in {"huggingface", "hf"}:
            return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or ""
        return os.getenv(self._api_key_name(), "")

    def _model_for_provider(self) -> str:
        if self.provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        if self.provider in {"huggingface", "hf"}:
            return os.getenv("HUGGINGFACE_MODEL", "openai/gpt-oss-120b:cerebras").strip()
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

    def enhance_report(self, request: AssessmentRequest, base_report: dict, sources: list[KnowledgeSource]) -> dict:
        if not self.configured():
            return {"generation_engine": "rules", "llm_summary": None}
        if os.getenv("LLM_TEST_MODE") == "1":
            return self._test_report_response(request, base_report)

        prompt = {
            "task": "Enhance this educational preventive health report without diagnosing or prescribing.",
            "patient_input": {
                "age": request.profile.age,
                "gender": request.profile.gender,
                "location": request.profile.location,
                "climate": request.profile.climate,
                "occupation": request.profile.occupation,
                "sleep_hours": request.profile.sleep_hours,
                "exercise": request.profile.exercise_frequency,
                "diet": request.profile.diet_style,
                "foods": request.profile.food_habits[:12],
                "conditions": request.profile.existing_conditions[:8],
                "symptoms": [symptom.model_dump(mode="json") for symptom in request.symptoms[:5]],
                "question": request.question,
            },
            "base_report": {
                "risk_level": base_report["risk_summary"].overall_risk_level,
                "risk_score": base_report["risk_summary"].risk_score,
                "risk_factors": base_report["risk_summary"].key_risk_factors[:10],
                "concerns": base_report["possible_health_concerns_to_discuss_with_doctor"][:10],
                "precautions": base_report["precautions"][:10],
                "emergency_warning": base_report["emergency_warning"],
                "red_flags": base_report["red_flags"],
            },
            "retrieved_context": [
                {"title": source.title, "excerpt": source.excerpt[:280]}
                for source in sources[:3]
            ],
            "requirements": [
                "Do not diagnose.",
                "Do not prescribe, start, stop, or change medication.",
                "Escalate emergency red flags.",
                "Use the uploaded document context only as user-provided supporting context.",
                "Return concise JSON only.",
            ],
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "llm_summary": {"type": "string"},
                "additional_precautions": {"type": "array", "items": {"type": "string"}},
                "doctor_questions": {"type": "array", "items": {"type": "string"}},
                "follow_up_reminders": {"type": "array", "items": {"type": "string"}},
                "concerns_to_discuss": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "llm_summary",
                "additional_precautions",
                "doctor_questions",
                "follow_up_reminders",
                "concerns_to_discuss",
            ],
        }
        result = self._responses_json(
            "You are a cautious health education assistant for a patient safety application.",
            json_dumps(prompt),
            schema,
            "health_report_enhancement",
        )
        result["generation_engine"] = f"{self.provider}:{self.active_model}"
        return result

    def answer_chat(self, request: ChatRequest, fallback_answer: str, sources: list[KnowledgeSource]) -> dict:
        if not self.configured():
            return {"answer": fallback_answer, "generation_engine": "rules"}
        if os.getenv("LLM_TEST_MODE") == "1":
            return {"answer": f"{fallback_answer} This response was enhanced with demo LLM mode.", "generation_engine": "test-llm"}

        prompt = {
            "task": "Answer the health education question safely.",
            "question": request.question,
            "profile": request.profile.model_dump(mode="json") if request.profile else None,
            "retrieved_context": [source.model_dump(mode="json") for source in sources],
            "fallback_answer": fallback_answer,
            "requirements": [
                "Do not diagnose.",
                "Do not prescribe, start, stop, or change medication.",
                "Tell the user to seek emergency care for red flag symptoms.",
                "Keep the answer concise and educational.",
            ],
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }
        result = self._responses_json(
            "You are a cautious health education assistant.",
            json_dumps(prompt),
            schema,
            "health_chat_answer",
        )
        result["generation_engine"] = f"{self.provider}:{self.active_model}"
        return result

    def _responses_json(self, system: str, user: str, schema: dict, schema_name: str) -> dict:
        if self.provider == "gemini":
            return self._gemini_json(system, user, schema)
        if self.provider in {"huggingface", "hf"}:
            return self._huggingface_json(system, user, schema, schema_name)
        if self.provider != "openai":
            raise RuntimeError(f"Unsupported LLM_PROVIDER: {self.provider}")
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI API connection failed: {exc}") from exc
        return self._load_json_output(self._extract_text(data))

    def _huggingface_json(self, system: str, user: str, schema: dict, schema_name: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": int(os.getenv("HUGGINGFACE_MAX_TOKENS", "900") or "900"),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        }
        request = urllib.request.Request(
            os.getenv("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1").rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key_value()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(self._format_http_error("Hugging Face", exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Hugging Face API connection failed: {exc}") from exc
        self.active_model = data.get("model") or self.model
        return self._load_json_output(self._extract_text(data))

    def _gemini_json(self, system: str, user: str, schema: dict) -> dict:
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": self._gemini_schema(schema),
                "temperature": 0.2,
            },
        }
        errors: list[str] = []
        retry_count = int(os.getenv("GEMINI_RETRY_COUNT", "4") or "4")
        retry_delay = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "3") or "3")
        for model in self._gemini_models():
            model_path = urllib.parse.quote(model, safe="")
            last_error = ""
            for attempt in range(retry_count + 1):
                request = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent?key={urllib.parse.quote(os.environ['GEMINI_API_KEY'])}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(request, timeout=self.timeout) as response:
                        data = json.loads(response.read().decode("utf-8"))
                    self.active_model = model
                    return self._load_json_output(self._extract_text(data))
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="ignore")
                    last_error = self._format_http_error("Gemini", exc.code, detail)
                    if exc.code not in {429, 500, 502, 503, 504} or attempt >= retry_count:
                        break
                except urllib.error.URLError as exc:
                    last_error = f"Gemini API connection failed: {exc}"
                    if attempt >= retry_count:
                        break
                time.sleep(retry_delay)
            if last_error:
                errors.append(f"{model} failed after {retry_count + 1} attempt(s): {last_error}")
        raise RuntimeError("All Gemini models failed. " + " | ".join(errors))

    def _format_http_error(self, provider: str, code: int, detail: str) -> str:
        try:
            parsed = json.loads(detail)
            error = parsed.get("error", {})
            status = error.get("status")
            message = error.get("message")
            if message:
                prefix = f"{provider} API error {code}"
                if status:
                    prefix = f"{prefix} {status}"
                return f"{prefix}: {message}"
        except json.JSONDecodeError:
            pass
        compact_detail = " ".join(detail.split())
        return f"{provider} API error {code}: {compact_detail[:600]}"

    def _gemini_models(self) -> list[str]:
        fallback_models = [
            model.strip()
            for model in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite").split(",")
            if model.strip()
        ]
        return list(dict.fromkeys([self.model, *fallback_models]))

    def _gemini_schema(self, schema: dict) -> dict:
        if isinstance(schema, list):
            return [self._gemini_schema(item) for item in schema]
        if not isinstance(schema, dict):
            return schema
        allowed = {"type", "format", "description", "nullable", "enum", "maxItems", "minItems", "properties", "required", "propertyOrdering", "items", "anyOf"}
        converted: dict[str, Any] = {}
        for key, value in schema.items():
            if key not in allowed:
                continue
            if key == "type" and isinstance(value, str):
                converted[key] = value.upper()
            elif key == "properties" and isinstance(value, dict):
                converted[key] = {property_name: self._gemini_schema(property_schema) for property_name, property_schema in value.items()}
            else:
                converted[key] = self._gemini_schema(value)
        if "properties" in converted and isinstance(converted["properties"], dict):
            converted["propertyOrdering"] = list(converted["properties"].keys())
        return converted

    def _extract_text(self, data: dict) -> str:
        if data.get("output_text"):
            return data["output_text"]
        for step in data.get("steps", []):
            for content in step.get("content", []):
                if isinstance(content, dict) and content.get("type") == "text" and content.get("text"):
                    return content["text"]
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return content["text"]
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if part.get("text"):
                    return part["text"]
        for choice in data.get("choices", []):
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
                if text:
                    return text
        raise RuntimeError(f"{self.provider.title()} response did not contain output text.")

    def _load_json_output(self, text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{self.provider.title()} response was not valid JSON: {cleaned[:500]}") from exc

    def _test_report_response(self, request: AssessmentRequest, base_report: dict) -> dict:
        return {
            "generation_engine": "test-llm",
            "llm_summary": "Demo LLM enhancement generated from the patient profile, selected foods, symptoms, and supporting context.",
            "additional_precautions": ["Discuss the combined lifestyle and symptom pattern with a qualified clinician."],
            "doctor_questions": ["Which risk factors should I prioritize during my next clinical visit?"],
            "follow_up_reminders": ["Track symptom changes and bring uploaded document details to the appointment."],
            "concerns_to_discuss": ["LLM-highlighted preventive care review needs"],
        }
