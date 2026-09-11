"""
Central settings — loaded once at startup via pydantic-settings.
All secrets come from environment variables / .env file.

Blueprint §40 (env vars) + v2.2 additions (Gemini provider, email, OAuth).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

# pyrefly: ignore [missing-import]
from pydantic import Field, field_validator
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    # Dev defaults so the app boots without a .env; production must set real secrets.
    APP_SECRET_KEY: str = "dev-only-app-secret-0123456789abcdef0123456789abcdef"
    APP_ALLOWED_ORIGINS: str = "http://localhost:3000"

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def _app_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters")
        return v

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.APP_ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://casesense:casesense@localhost:5433/casesense"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-only-jwt-secret-0123456789abcdef0123456789abcdef"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _jwt_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    # ── Object Storage (OCI / S3-compatible) ─────────────────────────────────
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_BUCKET_NAME: str = "casesense-documents"
    STORAGE_REGION: str = "ap-south-1"

    # ── AI (v2.2: Google Gemini is the selected MVP provider) ────────────────
    AI_PROVIDER: Literal["gemini", "openai", "stub"] = "stub"
    AI_API_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL_STRONG: str = "gemini-3.6-flash"
    AI_MODEL_FAST: str = "gemini-3.6-flash-lite"
    # The database stores 1,536-dimensional vectors.  ``gemini-embedding-001``
    # supports that output size through the OpenAI-compatible ``dimensions``
    # parameter, unlike the retired text-embedding-004 default.
    AI_MODEL_EMBED: str = "gemini-embedding-001"
    AI_MAX_RETRIES: int = 3
    AI_FALLBACK_ALLOW_LEGAL: bool = False

    # ── Legal Source ──────────────────────────────────────────────────────────
    LEGAL_SOURCE_PROVIDER: Literal["indiankanoon", "stub"] = "stub"
    INDIANKANOON_API_KEY: str = ""
    LEGAL_SOURCE_BASE_URL: str = "https://api.indiankanoon.org"

    # ── Arq Workers ───────────────────────────────────────────────────────────
    ARQ_MAX_JOBS: int = 10
    ARQ_JOB_TIMEOUT: int = 600
    ARQ_RETRY_JOBS: int = 3

    # ── Security / Argon2 ─────────────────────────────────────────────────────
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 2

    # ── Email (v2.1 §75.6) ────────────────────────────────────────────────────
    EMAIL_TRANSPORT: Literal["console", "smtp", "api_generic"] = "console"
    SMTP_URL: str | None = None
    EMAIL_API_KEY: str | None = None
    EMAIL_API_BASE: str = "https://api.brevo.com/v3/smtp/email"
    EMAIL_FROM: str = "CaseSense <no-reply@casesense.local>"
    VERIFICATION_TOKEN_TTL_HOURS: int = 24
    EMAIL_VERIFICATION_OTP_TTL_MINUTES: int = 10
    RESET_TOKEN_TTL_MINUTES: int = 60

    # ── Auth / OAuth (v2.1) ───────────────────────────────────────────────────
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    OAUTH_CLIENT_ID: str = ""
    OAUTH_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = ""
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GOOGLE_ISSUER: str = "https://accounts.google.com"

    # ── Rate limiting (§75.1) ───────────────────────────────────────────────
    RATE_LIMITING_ENABLED: bool = True
    GUEST_SEARCH_LIMIT: int = 2
    GUEST_SEARCH_WINDOW_HOURS: int = 24

    # ── Observability ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV in ("development", "dev", "test")

    @property
    def storage_enabled(self) -> bool:
        """Real object storage requires configured credentials; otherwise local FS."""
        return bool(self.STORAGE_ENDPOINT_URL and self.STORAGE_ACCESS_KEY_ID)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
