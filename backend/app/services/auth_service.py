import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlencode

from backend.app.core.env import load_dotenv
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
        load_dotenv()
        self._load_sso_env()
        init_db()

    def _load_sso_env(self) -> None:
        env_path = ".env"
        if not os.path.exists(env_path):
            return
        sso_keys = {
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REDIRECT_URI",
            "FACEBOOK_CLIENT_ID",
            "FACEBOOK_CLIENT_SECRET",
            "FACEBOOK_REDIRECT_URI",
            "INSTAGRAM_CLIENT_ID",
            "INSTAGRAM_CLIENT_SECRET",
            "INSTAGRAM_REDIRECT_URI",
        }
        with open(env_path, encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in sso_keys:
                    os.environ[key] = value.strip().strip('"').strip("'")

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
        client_secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET")
        redirect_uri = os.getenv(f"{provider.upper()}_REDIRECT_URI", f"http://127.0.0.1:8001/api/auth/sso/{provider}/callback")
        if not client_id or (provider == "google" and not client_secret):
            return {
                "provider": provider,
                "configured": False,
                "message": (
                    f"{provider.title()} SSO is not configured. Add {provider.upper()}_CLIENT_ID, "
                    f"{provider.upper()}_CLIENT_SECRET, and {provider.upper()}_REDIRECT_URI."
                ),
                "redirect_uri": redirect_uri,
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

    def google_sso_status(self) -> dict:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8001/api/auth/sso/google/callback")
        configured = bool(client_id and client_secret and redirect_uri)
        status = {
            "configured": configured,
            "client_id_set": bool(client_id),
            "client_secret_set": bool(client_secret),
            "redirect_uri": redirect_uri,
            "token_endpoint_reachable": False,
        }
        if not configured:
            return status
        payload = urllib.parse.urlencode({"grant_type": "authorization_code"}).encode("utf-8")
        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            status["token_endpoint_reachable"] = exc.code in {400, 401}
            status["token_endpoint_status"] = exc.code
        except urllib.error.URLError as exc:
            status["token_endpoint_error"] = str(exc)
        return status

    def sso_callback(self, provider: str, code: str | None, state: str | None = None) -> dict:
        provider = provider.lower()
        if provider != "google":
            raise NotImplementedError("Live SSO callback is currently implemented for Google only.")
        if not code:
            raise ValueError("Google did not return an authorization code.")
        token_data = self._google_token_exchange(code)
        userinfo = self._google_userinfo(token_data["access_token"])
        email = (userinfo.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Google account did not provide an email address.")
        if userinfo.get("email_verified") is False:
            raise PermissionError("Google account email is not verified.")
        role = state if state in ROLE_CAPABILITIES else "patient"
        subject = str(userinfo.get("sub") or "")
        name = userinfo.get("name") or email.split("@", 1)[0]
        user_id = self._upsert_sso_user(email, name, role, provider, subject)
        return self._public_user(user_id)

    def _google_token_exchange(self, code: str) -> dict:
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8001/api/auth/sso/google/callback")
        payload = urllib.parse.urlencode(
            {
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Google token exchange failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Google token exchange connection failed: {exc}") from exc

    def _google_userinfo(self, access_token: str) -> dict:
        request = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Google userinfo failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Google userinfo connection failed: {exc}") from exc

    def _upsert_sso_user(self, email: str, name: str, role: str, provider: str, subject: str) -> int:
        role_profile = {"sso_provider": provider}
        with connect() as conn:
            existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE users
                    SET name = ?, role = ?, role_profile_json = ?, email_verified = 1,
                        verification_token = NULL, sso_provider = ?, sso_subject = ?
                    WHERE id = ?
                    """,
                    (name, role, json_dumps(role_profile), provider, subject, existing["id"]),
                )
                return existing["id"]
            cursor = conn.execute(
                """
                INSERT INTO users (
                    name, email, password_hash, role, role_profile_json,
                    email_verified, verification_token, verification_sent_at,
                    sso_provider, sso_subject, created_at
                )
                VALUES (?, ?, ?, ?, ?, 1, NULL, NULL, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    self._hash_password(f"sso:{provider}:{subject}:{secrets.token_urlsafe(16)}"),
                    role,
                    json_dumps(role_profile),
                    provider,
                    subject,
                    now_iso(),
                ),
            )
            return cursor.lastrowid

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
