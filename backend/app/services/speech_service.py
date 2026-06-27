from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from backend.app.core.env import load_dotenv


class SpeechService:
    def __init__(self) -> None:
        load_dotenv(override=True)
        self.model = os.getenv("HUGGINGFACE_ASR_MODEL", "openai/whisper-large-v3-turbo").strip()
        self.base_url = os.getenv("HUGGINGFACE_ASR_BASE_URL", "https://router.huggingface.co/hf-inference/models").rstrip("/")
        self.timeout = int(os.getenv("HUGGINGFACE_ASR_TIMEOUT_SECONDS", os.getenv("LLM_TIMEOUT_SECONDS", "45")) or "45")
        self.max_bytes = int(os.getenv("HEALTHGUARD_VOICE_MAX_BYTES", str(10 * 1024 * 1024)))
        self.min_bytes = int(os.getenv("HEALTHGUARD_VOICE_MIN_BYTES", "1024") or "1024")
        self.retry_count = int(os.getenv("HUGGINGFACE_ASR_RETRY_COUNT", "2") or "2")
        self.retry_delay = float(os.getenv("HUGGINGFACE_ASR_RETRY_DELAY_SECONDS", "1.5") or "1.5")

    def status(self) -> dict:
        return {
            "configured": bool(self._token()),
            "provider": "huggingface",
            "model": self.model,
            "fallback_models": self._models()[1:],
            "missing": [] if self._token() else ["HF_TOKEN"],
            "max_bytes": self.max_bytes,
            "min_bytes": self.min_bytes,
        }

    def transcribe(self, filename: str, content_type: str | None, payload: bytes) -> dict:
        if not self._token():
            raise RuntimeError("Hugging Face speech transcription is not configured. Add HF_TOKEN to .env and restart the app.")
        if not payload:
            raise ValueError("Voice recording is empty.")
        if len(payload) < self.min_bytes:
            raise ValueError("Voice recording is too short or silent. Please record at least two seconds of clear speech.")
        if len(payload) > self.max_bytes:
            raise ValueError("Voice recording is too large. Please record a shorter message.")
        if content_type and not content_type.startswith("audio/") and content_type not in {"video/webm", "application/octet-stream"}:
            raise ValueError(f"Unsupported voice recording content type: {content_type}.")

        errors: list[str] = []
        for model in self._models():
            for attempt in range(self.retry_count + 1):
                try:
                    data = self._call_asr_model(model, content_type, payload)
                    text = self._extract_text(data)
                    if not text:
                        raise RuntimeError("Hugging Face ASR did not return transcript text.")
                    return {
                        "filename": filename,
                        "content_type": content_type,
                        "provider": "huggingface",
                        "model": model,
                        "transcript": text,
                    }
                except RuntimeError as exc:
                    message = str(exc)
                    if not self._is_retryable(message) or attempt >= self.retry_count:
                        errors.append(f"{model}: {message}")
                        break
                    time.sleep(self.retry_delay * (attempt + 1))
        raise RuntimeError("All Hugging Face ASR models failed. " + " | ".join(errors))

    def _call_asr_model(self, model: str, content_type: str | None, payload: bytes) -> dict:
        model_path = urllib.parse.quote(model, safe="/")
        request = urllib.request.Request(
            f"{self.base_url}/{model_path}",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": content_type or "audio/webm",
                "X-Wait-For-Model": "true",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            compact = " ".join(detail.split())
            raise RuntimeError(f"Hugging Face ASR error {exc.code}: {compact[:600]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Hugging Face ASR connection failed: {exc}") from exc

    def _extract_text(self, data: dict) -> str:
        if isinstance(data.get("text"), str):
            return data["text"].strip()
        if isinstance(data.get("chunks"), list):
            return " ".join(chunk.get("text", "") for chunk in data["chunks"] if isinstance(chunk, dict)).strip()
        return ""

    def _token(self) -> str:
        return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or ""

    def _models(self) -> list[str]:
        fallback_models = [
            model.strip()
            for model in os.getenv("HUGGINGFACE_ASR_FALLBACK_MODELS", "openai/whisper-small,openai/whisper-base").split(",")
            if model.strip()
        ]
        return list(dict.fromkeys([self.model, *fallback_models]))

    def _is_retryable(self, message: str) -> bool:
        retryable_markers = [
            "error 429",
            "error 500",
            "error 502",
            "error 503",
            "error 504",
            "currently loading",
            "connection failed",
            "timed out",
            "temporarily unavailable",
        ]
        lowered = message.lower()
        return any(marker in lowered for marker in retryable_markers)
