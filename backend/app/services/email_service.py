import os
import smtplib
from email.message import EmailMessage

from backend.app.core.env import load_dotenv
from backend.app.db.store import connect, init_db, now_iso


class EmailService:
    def __init__(self) -> None:
        load_dotenv()
        init_db()

    def send_confirmation(self, recipient: str, code: str) -> dict:
        if os.getenv("SMTP_TEST_MODE") == "1":
            return self._record_outbox(recipient, "Confirm your HealthGuard AI email", self._body(code), code, "sent")
        if not self._smtp_configured():
            raise RuntimeError("SMTP is not configured. Registration cannot be completed until email delivery is available.")
        subject = "Confirm your HealthGuard AI email"
        body = self._body(code)
        try:
            self._send_smtp(recipient, subject, body)
        except (smtplib.SMTPException, OSError) as exc:
            raise RuntimeError(f"SMTP send failed: {type(exc).__name__}: {exc}") from exc
        return self._record_outbox(recipient, subject, body, code, "sent")

    def _record_outbox(self, recipient: str, subject: str, body: str, code: str, status: str) -> dict:
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO email_outbox (recipient, subject, body, token, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (recipient, subject, body, code, status, now_iso()),
            )
        return {"id": cursor.lastrowid, "recipient": recipient, "status": status}

    def _body(self, code: str) -> str:
        return (
            "Welcome to HealthGuard AI.\n\n"
            "Use this 6-digit confirmation code before signing in:\n"
            f"{code}\n\n"
            "This code is required to unlock your dashboard.\n\n"
            "If you did not create this account, you can ignore this message."
        )

    def latest_for(self, recipient: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT id, recipient, subject, body, token, status, created_at
                FROM email_outbox
                WHERE recipient = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (recipient.lower(),),
            ).fetchone()
        return dict(row) if row else None

    def smtp_status(self) -> dict:
        missing = [
            name
            for name in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"]
            if not os.getenv(name)
        ]
        return {
            "configured": not missing or os.getenv("SMTP_TEST_MODE") == "1",
            "test_mode": os.getenv("SMTP_TEST_MODE") == "1",
            "missing": missing,
            "host": os.getenv("SMTP_HOST") or None,
            "from": os.getenv("SMTP_FROM") or None,
        }

    def _smtp_configured(self) -> bool:
        return all(
            os.getenv(name)
            for name in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"]
        )

    def _send_smtp(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = os.environ["SMTP_FROM"]
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as smtp:
            smtp.starttls()
            smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(message)
