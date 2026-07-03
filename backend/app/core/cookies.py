"""Cookie helpers for the refresh token.

The refresh token is sent as an httpOnly cookie scoped to Path=/api/v1/auth.

SameSite policy:
  - Production (HTTPS): SameSite=None; Secure=True
      Required because the frontend (vercel.app) and backend (onrender.com)
      are on different domains. SameSite=Lax only sends cookies on top-level
      GET navigations — it does NOT send them on cross-site POST/fetch calls,
      so POST /auth/refresh from the frontend would receive a 401 with Lax.
      SameSite=None allows the cookie on cross-site subresource requests;
      the CORS allow_origins=[FRONTEND_URL] + allow_credentials=True on the
      backend restricts which origins can actually use it.
  - Development (HTTP): SameSite=Lax; Secure=False
      Browsers reject SameSite=None without Secure, so we fall back to Lax
      for local dev where both frontend and backend are on localhost (same site).
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _is_https(url: str) -> bool:
    return url.lower().startswith("https://")


def _cookie_flags() -> tuple[bool, str]:
    """Return (secure, samesite) appropriate for the current environment."""
    secure = _is_https(settings.BACKEND_URL) or settings.APP_ENV == "prod"
    samesite = "none" if secure else "lax"
    return secure, samesite


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set the httpOnly refresh_token cookie on the given response."""
    secure, samesite = _cookie_flags()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clear the httpOnly refresh_token cookie."""
    secure, samesite = _cookie_flags()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=REFRESH_COOKIE_PATH,
    )
