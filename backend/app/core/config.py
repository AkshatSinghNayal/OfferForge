"""Application configuration.

Reads all environment variables from .env / os.environ via pydantic-settings.
Settings are exposed as a singleton `settings` consumed across the app.

Why pydantic-settings over plain os.getenv:
  - typed validation (DATABASE_URL must be a string, secrets must be non-empty
    in prod, etc.)
  - one source of truth for defaults and overrides
  - integrates cleanly with FastAPI dependency injection
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Loaded once via lru_cache below."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://placement:placement@db:5432/placement_tracker",
        description="Async SQLAlchemy DSN. Must use the asyncpg driver.",
    )
    # Optional Postgres schema to isolate tables (e.g. "offerforge").
    # When set, the app sets search_path on every connection so all DDL/DML
    # targets this schema instead of "public".
    DB_SCHEMA: str = Field(default="")

    # --- JWT ---
    # Phase 2 correction to Phase A open decision #3: refresh TTL is 7 days,
    # not 30. Access stays at 15 minutes. If you want to revert to 30 days,
    # set REFRESH_TOKEN_TTL_DAYS=30 in .env.
    JWT_SECRET_KEY: str = Field(default="dev-only-not-secret-change-me")
    JWT_REFRESH_SECRET_KEY: str = Field(default="dev-only-not-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 7
    # Password reset tokens: 30 min expiry, single-use (stored in DB so they
    # can be revoked / marked-used). Token is a 32-byte urlsafe secret, hashed
    # at rest with SHA-256 (same pattern as refresh tokens).
    PASSWORD_RESET_TTL_MINUTES: int = 30

    # --- Google OAuth2 ---
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")

    # --- Cloudinary ---
    CLOUDINARY_CLOUD_NAME: str = Field(default="")
    CLOUDINARY_API_KEY: str = Field(default="")
    CLOUDINARY_API_SECRET: str = Field(default="")
    # Alternative single-URL format: cloudinary://api_key:api_secret@cloud_name
    # Set this OR the three individual vars above — not both.
    CLOUDINARY_URL: str = Field(default="")

    # --- App URLs ---
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    BACKEND_URL: str = Field(default="http://localhost:8000")

    # --- Runtime mode ---
    # "dev" allows insecure defaults (e.g. dummy JWT secrets). "prod" requires
    # real secrets and fails fast if they are missing.
    APP_ENV: Literal["dev", "prod", "test"] = "dev"

    @field_validator("DATABASE_URL")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the asyncpg driver "
                "(postgresql+asyncpg://...). Got: " + v
            )
        return v

    @field_validator("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY")
    @classmethod
    def _block_default_secret_in_prod(cls, v: str, info) -> str:
        # info.data holds previously-validated fields; APP_ENV is declared
        # above JWT secrets so it should be present by the time this runs.
        env = info.data.get("APP_ENV", "dev")
        if env == "prod" and v.startswith("dev-only"):
            raise ValueError(
                f"{info.field_name} must be set to a real secret in prod "
                "(generate with: python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
            )
        return v

    @property
    def cors_origins(self) -> list[str]:
        """List of allowed CORS origins. For MVP, just the frontend URL."""
        return [self.FRONTEND_URL]

    @property
    def google_oauth_redirect_uri(self) -> str:
        """The exact URI registered in Google Cloud Console."""
        return f"{self.BACKEND_URL}/api/v1/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Import via `from app.core.config import settings`."""
    return Settings()


settings = get_settings()
