import hashlib
import os
import secrets
from urllib.parse import urlencode

from backend.app.db.store import connect, init_db, json_dumps, json_loads, now_iso, row_to_dict
from backend.app.schemas.health import LoginRequest, RegisterRequest
from backend.app.services.email_service import EmailService


ROLE_CAPABILITIES = {
    "patient": ["create_profile", "generate_report", "download_own_report", "ask_health_question"],
    "doctor": ["view_pending_reports", "review_reports", "add_clinical_notes"],
    "dietician": ["review_diet_guidance", "comment_on_reports"],
    "admin": ["manage_knowledge", "view_audit_logs", "manage_prompts"],
    "compliance": ["view_audit_logs", "review_safety_events"],
}


class AuthService:
    def __init__(self) -> None:
        init_db()

    def register(self, request: RegisterRequest) -> dict:
        email = request.email.lower()
        self._remove_pending_registration(email)
        password_hash = self._hash_password(request.password)
        verification_code = self._verification_code()
        delivery = EmailService().send_confirmation(email, verification_code)
        role_profile = {
            "organization": request.organization,
            "license_number": request.license_number,
            "specialty": request.specialty,
        }
        with connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (
                        name, email, password_hash, role, role_profile_json,
                        email_verified, verification_token, verification_sent_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        request.name,
                        email,
                        password_hash,
                        request.role,
                        json_dumps(role_profile),
                        verification_code,
                        now_iso(),
                        now_iso(),
                    ),
                )
            except Exception as exc:
                if "UNIQUE" in str(exc).upper():
                    raise ValueError("A user with this email already exists.") from exc
                raise
            user_id = cursor.lastrowid
        return {
            "id": user_id,
            "name": request.name,
            "email": email,
            "role": request.role,
            "email_verified": False,
            "message": "Registration created. Please confirm your email before logging in.",
            "email_delivery": delivery,
        }

    def _remove_pending_registration(self, email: str) -> None:
        with connect() as conn:
            existing = conn.execute("SELECT id, email_verified FROM users WHERE email = ?", (email,)).fetchone()
            if not existing:
                return
            if existing["email_verified"]:
                raise ValueError("A user with this email already exists.")
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (existing["id"],))
            conn.execute("DELETE FROM users WHERE id = ?", (existing["id"],))
            conn.execute("DELETE FROM email_outbox WHERE recipient = ?", (email,))

    def login(self, request: LoginRequest) -> dict | None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (request.email.lower(),)).fetchone()
        if not row or row["password_hash"] != self._hash_password(request.password):
            return None
        if not row["email_verified"]:
            raise PermissionError("Please confirm your email before logging in.")
        return self._public_user(row["id"])

    def verify_email(self, code: str, email: str | None = None) -> dict | None:
        with connect() as conn:
            if email:
                row = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND verification_token = ?",
                    (email.lower(), code),
                ).fetchone()
            else:
                row = conn.execute("SELECT * FROM users WHERE verification_token = ?", (code,)).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE users
                SET email_verified = 1, verification_token = NULL
                WHERE id = ?
                """,
                (row["id"],),
            )
            user_id = row["id"]
        return self._public_user(user_id)

    def resend_verification(self, email: str) -> dict:
        code = self._verification_code()
        with connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
            if not row:
                raise LookupError("No account exists with this email.")
            if row["email_verified"]:
                return {"email": email.lower(), "email_verified": True, "message": "Email is already verified."}
        delivery = EmailService().send_confirmation(email.lower(), code)
        with connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET verification_token = ?, verification_sent_at = ?
                WHERE id = ?
                """,
                (code, now_iso(), row["id"]),
            )
        return {"email": email.lower(), "email_verified": False, "email_delivery": delivery}

    def sso_start(self, provider: str, role: str = "patient") -> dict:
        provider = provider.lower()
        allowed = {"google", "facebook", "instagram"}
        if provider not in allowed:
            raise ValueError("Supported SSO providers are google, facebook, and instagram.")
        client_id = os.getenv(f"{provider.upper()}_CLIENT_ID")
        redirect_uri = os.getenv(f"{provider.upper()}_REDIRECT_URI", f"http://127.0.0.1:8001/api/auth/sso/{provider}/callback")
        if not client_id:
            return {
                "provider": provider,
                "configured": False,
                "message": f"{provider.title()} SSO is not configured. Add {provider.upper()}_CLIENT_ID and provider secrets.",
            }
        auth_base = {
            "google": "https://accounts.google.com/o/oauth2/v2/auth",
            "facebook": "https://www.facebook.com/v19.0/dialog/oauth",
            "instagram": "https://api.instagram.com/oauth/authorize",
        }[provider]
        scope = {
            "google": "openid email profile",
            "facebook": "email public_profile",
            "instagram": "user_profile",
        }[provider]
        params = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
                "state": role,
            }
        )
        return {"provider": provider, "configured": True, "authorization_url": f"{auth_base}?{params}"}

    def me(self, token: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT users.*
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
        if not row:
            return None
        return self._shape_user(dict(row), token)

    def _public_user(self, user_id: int) -> dict:
        with connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        user = row_to_dict(row)
        if not user:
            raise ValueError("User could not be loaded after registration.")
        token = self._create_session(user["id"])
        return self._shape_user(user, token)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(f"healthguard-demo:{password}".encode("utf-8")).hexdigest()

    def _verification_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def _create_session(self, user_id: int) -> str:
        token = f"demo-{user_id}-{secrets.token_urlsafe(18)}"
        with connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (token, user_id, now_iso()),
            )
        return token

    def _shape_user(self, user: dict, token: str) -> dict:
        role = user["role"]
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": role,
            "email_verified": bool(user.get("email_verified")),
            "role_profile": json_loads(user.get("role_profile_json") or "{}"),
            "demo_token": token,
            "capabilities": ROLE_CAPABILITIES.get(role, []),
            "landing_view": self._landing_view(role),
        }

    def _landing_view(self, role: str) -> str:
        return {
            "patient": "assessment",
            "doctor": "doctor_review",
            "dietician": "diet_review",
            "admin": "admin_console",
            "compliance": "audit_console",
        }.get(role, "assessment")
