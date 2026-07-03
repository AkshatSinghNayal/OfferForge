"""Security primitives: password hashing, JWT, opaque-token hashing.

This module contains pure-function helpers only. DB access + business logic
lives in app.services.auth_service so routers stay thin.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ---------------------------------------------------------------------------
# Password hashing (Passlib / bcrypt)
# ---------------------------------------------------------------------------

# bcrypt is the algorithm. Passlib auto-handles salt generation + versioning.
# `deprecated="auto"` lets Passlib upgrade hash formats in future if needed.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password. Returns a bcrypt hash string."""
    if not plain:
        raise ValueError("password cannot be empty")
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns False (not raises) on mismatch — callers branch on the bool.
    """
    if not plain or not hashed:
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        # Malformed hash — treat as failed verification, never raise.
        return False


# ---------------------------------------------------------------------------
# JWT (access tokens)
# ---------------------------------------------------------------------------

AccessTokenSubject = str  # str(user_id)


def create_access_token(
    user_id: uuid.UUID,
    *,
    ttl_minutes: int | None = None,
) -> str:
    """Mint a short-lived JWT access token.

    Claims:
      sub   = str(user_id)
      type  = "access"
      iat   = issued-at (unix seconds)
      exp   = expiry (unix seconds)
      jti   = random UUID (for future revocation-list support, not used yet)
    """
    now = datetime.now(timezone.utc)
    ttl = ttl_minutes if ttl_minutes is not None else settings.ACCESS_TOKEN_TTL_MINUTES
    expires_at = now + timedelta(minutes=ttl)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or fails claim validation."""


class TokenExpiredError(TokenError):
    """Raised when a JWT is structurally valid but past its exp."""


class TokenInvalidError(TokenError):
    """Raised when a JWT is malformed, signed with the wrong key, or has
    a wrong `type` claim."""


def decode_access_token(token: str) -> uuid.UUID:
    """Decode + validate an access JWT. Returns the user_id.

    Raises:
      TokenExpiredError — exp is in the past.
      TokenInvalidError — bad signature, malformed, or wrong `type` claim.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("access token expired") from e
    except JWTError as e:
        raise TokenInvalidError(f"invalid access token: {e}") from e

    if payload.get("type") != "access":
        raise TokenInvalidError(f"expected access token, got type={payload.get('type')!r}")

    sub = payload.get("sub")
    if not sub:
        raise TokenInvalidError("missing sub claim")
    try:
        return uuid.UUID(sub)
    except (ValueError, AttributeError) as e:
        raise TokenInvalidError(f"invalid sub claim: {sub!r}") from e


# ---------------------------------------------------------------------------
# Opaque token hashing (refresh tokens + password reset tokens)
# ---------------------------------------------------------------------------

def hash_token(raw: str) -> str:
    """SHA-256 a raw opaque token. Used for refresh tokens and password-reset
    tokens. We don't need bcrypt's slowness here because the raw token has
    32 bytes of entropy — SHA-256 is sufficient and much faster on every
    lookup.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_raw_token() -> str:
    """Generate a 32-byte urlsafe opaque token (43 chars)."""
    import secrets
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# TTL helpers (used by the auth service)
# ---------------------------------------------------------------------------

def access_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)


def password_reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES)
