"""
Central settings — loaded once at startup via pydantic-settings.
All secrets come from environment variables / .env file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
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
    APP_SECRET_KEY: str = Field(..., min_length=32)
    APP_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("APP_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://casesense:casesense@localhost:5432/casesense"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Object Storage ────────────────────────────────────────────────────────
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_BUCKET_NAME: str = "casesense-documents"
    STORAGE_REGION: str = "ap-mumbai-1"

    # ── AI ────────────────────────────────────────────────────────────────────
    AI_PROVIDER: Literal["openai", "anthropic", "stub"] = "stub"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL_STRONG: str = "gpt-4o"
    AI_MODEL_FAST: str = "gpt-4o-mini"
    AI_MAX_RETRIES: int = 3

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

    # ── Observability ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()