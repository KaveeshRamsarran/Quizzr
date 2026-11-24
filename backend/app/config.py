"""
Application Configuration
Loads settings from environment variables (and an optional .env file).
"""

import secrets
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SECRET = "change-me"


def _persistent_dev_secret() -> str:
    """Return a random signing key kept in backend/.secret_key.

    Used when SECRET_KEY is not configured so that local sessions survive
    server restarts without shipping a hard-coded key.
    """
    path = BACKEND_DIR / ".secret_key"
    try:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if len(value) >= 32:
                return value
        value = secrets.token_urlsafe(48)
        path.write_text(value, encoding="utf-8")
        return value
    except OSError:
        return secrets.token_urlsafe(48)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR.parent / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Quizzr"
    environment: str = "development"
    debug: bool = False

    # Database (SQLite for local use, PostgreSQL for production)
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'quizzr.db').as_posix()}"

    # Security
    secret_key: str = DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Supabase Auth. When SUPABASE_URL and SUPABASE_ANON_KEY are set, sign-up, sign-in,
    # email confirmation and password reset are handled by Supabase and the API accepts
    # Supabase access tokens. Otherwise Quizzr uses its own email/password accounts.
    supabase_url: str = ""
    supabase_anon_key: str = ""  # public "anon"/"publishable" key, sent to the browser
    supabase_jwt_secret: str = ""  # only for projects still on the legacy HS256 JWT secret
    supabase_service_role_key: str = ""  # optional: lets account deletion remove the Supabase user too
    supabase_oauth_providers: str = ""  # e.g. "google,github" (enable them in Supabase first)
    # With SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set, uploaded PDFs are kept in this
    # private Supabase Storage bucket (created on startup) instead of UPLOAD_DIR.
    supabase_storage_bucket: str = "documents"

    # File upload
    max_upload_size_mb: int = 50
    upload_dir: str = str(BACKEND_DIR / "uploads")
    allowed_extensions: str = "pdf"
    storage_quota_mb: int = 500

    # Generation limits
    max_cards_per_document: int = 500
    max_quiz_questions: int = 50
    max_chunks_per_generation: int = 40

    # Frontend URL (CORS)
    frontend_url: str = "http://localhost:3000"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def supabase_base_url(self) -> str:
        return self.supabase_url.rstrip("/")

    @property
    def supabase_oauth_providers_list(self) -> List[str]:
        return [p.strip().lower() for p in self.supabase_oauth_providers.split(",") if p.strip()]

    @property
    def cors_origins(self) -> List[str]:
        origins = {self.frontend_url}
        if self.environment == "development":
            for port in (3000, 4173, 5173):
                origins.add(f"http://localhost:{port}")
                origins.add(f"http://127.0.0.1:{port}")
        return sorted(origins)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    s = Settings()
    if not s.secret_key or s.secret_key in {DEFAULT_SECRET, "your-super-secret-key-change-in-production-min-32-chars"}:
        s.secret_key = _persistent_dev_secret()
    return s


settings = get_settings()
