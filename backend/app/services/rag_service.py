from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable

from backend.app.db.store import connect, init_db, json_dumps, json_loads, now_iso
from backend.app.schemas.health import KnowledgeSource


class RAGService:
    embedding_dimensions = 128
    chunk_words = 140
    chunk_overlap = 30

    def __init__(self) -> None:
        init_db()

    def index_document(self, title: str, content: str, source_type: str, user_id: int | None = None, filename: str | None = None) -> dict:
        cleaned = self._clean_text(content)
        if not cleaned:
            raise ValueError("No readable document text was available for indexing.")
        content_hash = hashlib.sha256(f"{user_id}:{source_type}:{title}:{cleaned}".encode("utf-8")).hexdigest()
        chunks = self._chunk_text(cleaned)
        timestamp = now_iso()
        with connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM rag_documents
                WHERE content_hash = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
                """,
                (content_hash, user_id, user_id),
            ).fetchone()
            if existing:
                document_id = existing["id"]
                conn.execute("DELETE FROM rag_chunks WHERE document_id = ?", (document_id,))
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO rag_documents (user_id, title, source_type, filename, content_hash, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'indexed', ?)
                    """,
                    (user_id, title, source_type, filename, content_hash, timestamp),
                )
                document_id = cursor.lastrowid
            for index, chunk in enumerate(chunks):
                conn.execute(
                    """
                    INSERT INTO rag_chunks (document_id, user_id, chunk_index, content, embedding_json, token_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        user_id,
                        index,
                        chunk,
                        json_dumps(self.embed(chunk)),
                        len(chunk.split()),
                        timestamp,
                    ),
                )
        return {"document_id": document_id, "chunk_count": len(chunks), "content_hash": content_hash}

    def retrieve(self, query: str | None, user_id: int | None = None, limit: int = 6) -> list[KnowledgeSource]:
        query_text = self._clean_text(query or "")
        if not query_text:
            query_text = "preventive health safety symptoms lifestyle diet emergency"
        query_embedding = self.embed(query_text)
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT rag_chunks.content, rag_chunks.embedding_json, rag_chunks.chunk_index,
                       rag_documents.title, rag_documents.source_type, rag_documents.user_id
                FROM rag_chunks
                JOIN rag_documents ON rag_documents.id = rag_chunks.document_id
                WHERE rag_documents.user_id IS NULL OR rag_documents.user_id = ?
                ORDER BY rag_documents.user_id DESC, rag_documents.id DESC, rag_chunks.chunk_index ASC
                LIMIT 500
                """,
                (user_id,),
            ).fetchall()
        ranked: list[tuple[float, dict]] = []
        for row in rows:
            score = self.cosine(query_embedding, json_loads(row["embedding_json"]))
            if score > 0:
                ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        sources: list[KnowledgeSource] = []
        for score, row in ranked[:limit]:
            source_type = "patient_document_rag" if row.get("user_id") else row["source_type"]
            sources.append(
                KnowledgeSource(
                    title=f"{row['title']} (score {score:.2f})",
                    source_type=source_type,
                    excerpt=row["content"],
                )
            )
        return sources

    def seed_global_knowledge(self, sources: Iterable[KnowledgeSource]) -> None:
        for source in sources:
            self.index_document(
                title=source.title,
                content=source.excerpt,
                source_type=source.source_type,
                user_id=None,
                filename=None,
            )

    def status(self, user_id: int | None = None) -> dict:
        with connect() as conn:
            total_docs = conn.execute("SELECT COUNT(*) AS count FROM rag_documents").fetchone()["count"]
            total_chunks = conn.execute("SELECT COUNT(*) AS count FROM rag_chunks").fetchone()["count"]
            user_docs = conn.execute("SELECT COUNT(*) AS count FROM rag_documents WHERE user_id = ?", (user_id,)).fetchone()["count"] if user_id else 0
            user_chunks = conn.execute("SELECT COUNT(*) AS count FROM rag_chunks WHERE user_id = ?", (user_id,)).fetchone()["count"] if user_id else 0
        return {
            "enabled": True,
            "embedding_provider": "local_hashing_embedding",
            "vector_store": "database_embedding_json",
            "semantic_similarity": "cosine",
            "chunk_words": self.chunk_words,
            "chunk_overlap": self.chunk_overlap,
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "user_documents": user_docs,
            "user_chunks": user_chunks,
        }

    def embed(self, text: str) -> list[float]:
        tokens = self._tokens(text)
        counts = Counter(tokens)
        vector = [0.0] * self.embedding_dimensions
        for token, count in counts.items():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.embedding_dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[slot] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [round(value / norm, 6) for value in vector]

    def cosine(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self.chunk_words:
            return [text]
        chunks: list[str] = []
        step = max(1, self.chunk_words - self.chunk_overlap)
        for start in range(0, len(words), step):
            chunk = " ".join(words[start : start + self.chunk_words]).strip()
            if chunk:
                chunks.append(chunk)
            if start + self.chunk_words >= len(words):
                break
        return chunks

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _tokens(self, text: str) -> list[str]:
        return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1]
