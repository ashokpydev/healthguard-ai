from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from backend.app.core.env import load_dotenv


load_dotenv()

SQLITE_PATH = Path(
    os.getenv("HEALTHGUARD_DB_PATH") or str(Path(tempfile.gettempdir()) / "healthguard-ai" / "healthguard.db")
)


def database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def using_postgres() -> bool:
    return database_url().startswith(("postgresql://", "postgres://"))


def db_status() -> dict[str, Any]:
    try:
        with connect() as conn:
            if conn.backend == "postgres":
                row = conn.execute("SELECT current_database() AS database_name").fetchone()
                return {
                    "configured": True,
                    "backend": "postgres",
                    "database": row["database_name"] if row else None,
                }
            return {
                "configured": True,
                "backend": "sqlite",
                "database": str(SQLITE_PATH),
            }
    except Exception as exc:
        return {
            "configured": False,
            "backend": "postgres" if using_postgres() else "sqlite",
            "error": str(exc).splitlines()[0],
        }


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class CursorAdapter:
    def __init__(self, cursor: Any, lastrowid: int | None = None) -> None:
        self._cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = getattr(cursor, "rowcount", -1)

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._cursor.fetchall()]


class ConnectionAdapter:
    def __init__(self, conn: Any, backend: str) -> None:
        self._conn = conn
        self.backend = backend

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> CursorAdapter:
        if self.backend == "postgres":
            statement = sql.replace("?", "%s")
            returns_id = self._insert_returns_id(statement)
            if returns_id:
                statement = f"{statement.rstrip()} RETURNING id"
            cursor = self._conn.execute(statement, params)
            lastrowid = cursor.fetchone()["id"] if returns_id else None
            return CursorAdapter(cursor, lastrowid)

        cursor = self._conn.execute(sql, params)
        return CursorAdapter(cursor, getattr(cursor, "lastrowid", None))

    def executescript(self, sql: str) -> None:
        if self.backend == "postgres":
            for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                self._conn.execute(statement)
            return
        self._conn.executescript(sql)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _insert_returns_id(self, sql: str) -> bool:
        normalized = " ".join(sql.lower().split())
        if " returning " in normalized or not normalized.startswith("insert into "):
            return False
        return any(
            normalized.startswith(f"insert into {table} ")
            for table in [
                "users",
                "email_outbox",
                "patient_profiles",
                "assessments",
                "reports",
                "knowledge_documents",
                "audit_logs",
            ]
        )


@contextmanager
def connect() -> Iterator[ConnectionAdapter]:
    if using_postgres():
        adapter = ConnectionAdapter(psycopg.connect(database_url(), row_factory=dict_row), "postgres")
    else:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        adapter = ConnectionAdapter(conn, "sqlite")

    try:
        yield adapter
        adapter.commit()
    finally:
        adapter.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_postgres_schema() if conn.backend == "postgres" else _sqlite_schema())
        _ensure_column(conn, "users", "role_profile_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "users", "email_verified", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "verification_token", "TEXT")
        _ensure_column(conn, "users", "verification_sent_at", "TEXT")
        _ensure_column(conn, "users", "sso_provider", "TEXT")
        _ensure_column(conn, "users", "sso_subject", "TEXT")


def _sqlite_schema() -> str:
    return _shared_schema("INTEGER PRIMARY KEY AUTOINCREMENT")


def _postgres_schema() -> str:
    return _shared_schema("SERIAL PRIMARY KEY")


def _shared_schema(id_definition: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS users (
        id {id_definition},
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'patient',
        role_profile_json TEXT NOT NULL DEFAULT '{{}}',
        email_verified INTEGER NOT NULL DEFAULT 0,
        verification_token TEXT,
        verification_sent_at TEXT,
        sso_provider TEXT,
        sso_subject TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS email_outbox (
        id {id_definition},
        recipient TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        token TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS patient_profiles (
        id {id_definition},
        user_id INTEGER REFERENCES users(id),
        profile_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assessments (
        id {id_definition},
        patient_id INTEGER REFERENCES patient_profiles(id),
        input_json TEXT NOT NULL,
        risk_score INTEGER NOT NULL,
        risk_level TEXT NOT NULL,
        red_flags_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reports (
        id {id_definition},
        patient_id INTEGER REFERENCES patient_profiles(id),
        assessment_id INTEGER REFERENCES assessments(id),
        report_json TEXT NOT NULL,
        doctor_review_status TEXT NOT NULL DEFAULT 'pending',
        doctor_comments TEXT,
        final_clinical_notes TEXT,
        created_at TEXT NOT NULL,
        reviewed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id {id_definition},
        title TEXT NOT NULL,
        source_type TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'approved',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id {id_definition},
        user_id INTEGER,
        action TEXT NOT NULL,
        input_summary TEXT NOT NULL,
        output_summary TEXT NOT NULL,
        risk_flags TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """


def _ensure_column(conn: ConnectionAdapter, table_name: str, column_name: str, definition: str) -> None:
    if conn.backend == "postgres":
        row = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
    else:
        row = next(
            (item for item in conn.execute(f"PRAGMA table_info({table_name})").fetchall() if item["name"] == column_name),
            None,
        )
    if not row:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def row_to_dict(row: dict[str, Any] | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def json_loads(value: str) -> Any:
    return json.loads(value)
