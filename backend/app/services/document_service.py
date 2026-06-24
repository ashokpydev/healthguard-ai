from __future__ import annotations

import re
import zipfile
from html import unescape
from io import BytesIO

from pydantic import BaseModel, Field


class DocumentExplanation(BaseModel):
    filename: str
    status: str
    message: str
    extracted_text: str = ""
    tuned_context: str = ""
    rag_summary: str = ""
    sources: list[str] = Field(default_factory=list)
    disclaimer: str


class DocumentService:
    max_bytes = 4 * 1024 * 1024
    max_context_chars = 2800

    def process_upload(self, filename: str, content_type: str | None, payload: bytes) -> DocumentExplanation:
        if not payload:
            raise ValueError("The uploaded document is empty.")
        if len(payload) > self.max_bytes:
            raise ValueError("Upload limit is 4 MB for demo document processing.")

        extracted = self._extract_text(filename, content_type, payload)
        tuned = self._tune_for_rag(extracted)
        summary = self._summarize(tuned)
        status = "processed_for_rag" if tuned else "received_needs_review"
        return DocumentExplanation(
            filename=filename,
            status=status,
            message=f"{filename} was processed and can be used as optional supporting context for the next report.",
            extracted_text=extracted[: self.max_context_chars],
            tuned_context=tuned,
            rag_summary=summary,
            sources=[filename] if tuned else [],
            disclaimer="Reference ranges may vary by lab. Please consult your doctor for interpretation.",
        )

    def _extract_text(self, filename: str, content_type: str | None, payload: bytes) -> str:
        name = filename.lower()
        if name.endswith(".docx"):
            return self._extract_docx(payload)
        if name.endswith(".pdf") or content_type == "application/pdf":
            return self._extract_pdf_text(payload)
        return self._decode_text(payload)

    def _decode_text(self, payload: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="ignore")

    def _extract_docx(self, payload: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(payload)) as docx:
                xml = docx.read("word/document.xml").decode("utf-8", errors="ignore")
        except (KeyError, zipfile.BadZipFile):
            return self._decode_text(payload)
        text = re.sub(r"<[^>]+>", " ", xml)
        return unescape(text)

    def _extract_pdf_text(self, payload: bytes) -> str:
        decoded = payload.decode("latin-1", errors="ignore")
        chunks = re.findall(r"\(([^()]{2,})\)\s*Tj", decoded)
        if not chunks:
            chunks = re.findall(r"\(([^()]{2,})\)", decoded)
        return " ".join(unescape(chunk.replace("\\)", ")").replace("\\(", "(")) for chunk in chunks)

    def _tune_for_rag(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = re.sub(r"(?i)(password|secret|token)\s*[:=]\s*\S+", r"\1: [redacted]", cleaned)
        if not cleaned:
            return ""
        return cleaned[: self.max_context_chars]

    def _summarize(self, text: str) -> str:
        if not text:
            return "No readable text was extracted. The file was received for manual review."
        sentences = re.split(r"(?<=[.!?])\s+", text)
        summary = " ".join(sentence for sentence in sentences[:3] if sentence)
        return summary[:700] or text[:700]
