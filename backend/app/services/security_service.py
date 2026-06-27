from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def mask_pii(value: Any) -> str:
    text = str(value or "")
    text = EMAIL_RE.sub(lambda match: _mask_email(match.group(0)), text)
    text = PHONE_RE.sub(lambda match: _mask_digits(match.group(0)), text)
    return text[:500]


def _mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _mask_digits(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8:
        return value
    return f"***{digits[-4:]}"


class RateLimiter:
    _events: dict[str, list[float]] = {}

    def check(self, key: str, limit: int = 80, window_seconds: int = 60) -> None:
        now = time.time()
        cutoff = now - window_seconds
        bucket = [item for item in self._events.get(key, []) if item >= cutoff]
        if len(bucket) >= limit:
            raise PermissionError("Too many requests. Please wait and try again.")
        bucket.append(now)
        self._events[key] = bucket


@dataclass
class UploadScanResult:
    allowed: bool
    status: str
    details: str
    sha256: str


class UploadSecurityScanner:
    blocked_extensions = {".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".scr", ".msi"}
    allowed_extensions = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
    executable_signatures = [b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe"]
    max_bytes = int(os.getenv("HEALTHGUARD_UPLOAD_MAX_BYTES", str(5 * 1024 * 1024)))

    def scan(self, filename: str, content_type: str | None, payload: bytes) -> UploadScanResult:
        digest = hashlib.sha256(payload).hexdigest()
        lower_name = (filename or "").lower()
        extension = os.path.splitext(lower_name)[1]
        if not payload:
            return UploadScanResult(False, "blocked", "Empty files cannot be scanned or processed.", digest)
        if len(payload) > self.max_bytes:
            return UploadScanResult(False, "blocked", "File exceeds the configured upload size limit.", digest)
        if extension in self.blocked_extensions:
            return UploadScanResult(False, "blocked", f"Blocked executable/script file type: {extension}.", digest)
        if extension and extension not in self.allowed_extensions:
            return UploadScanResult(False, "blocked", f"Unsupported file type: {extension}.", digest)
        if any(payload.startswith(signature) for signature in self.executable_signatures):
            return UploadScanResult(False, "blocked", "Executable file signature detected.", digest)
        if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR" in payload:
            return UploadScanResult(False, "blocked", "Antivirus test signature detected.", digest)
        return UploadScanResult(True, "clean", f"Clean scan for {content_type or 'unknown content type'}.", digest)


def audit_metadata_from_request(request: Any | None, user: dict | None = None, extra: dict | None = None) -> dict:
    headers = getattr(request, "headers", {}) if request else {}
    client = getattr(request, "client", None)
    forwarded_for = headers.get("x-forwarded-for") if headers else None
    ip_address = (forwarded_for.split(",", 1)[0].strip() if forwarded_for else None) or getattr(client, "host", None)
    return {
        "user_id": user.get("id") if user else None,
        "role": user.get("role") if user else None,
        "ip_address": ip_address,
        "user_agent": headers.get("user-agent") if headers else None,
        **(extra or {}),
    }


def retention_until(days: int | None = None) -> str:
    retention_days = days or int(os.getenv("AUDIT_RETENTION_DAYS", "365"))
    return (datetime.now(UTC) + timedelta(days=retention_days)).isoformat()


def rows_to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    fieldnames = sorted({key for row in rows for key in row.keys()})
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def canonical_event_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
