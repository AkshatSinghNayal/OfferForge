"""Google OAuth2 integration via authlib.

Flow:
  1. GET /auth/google/login
       - generate state nonce
       - set oauth_state cookie
       - 302 redirect to Google's consent screen with redirect_uri
         = BACKEND_URL/api/v1/auth/google/callback
  2. User approves on Google → Google 302s to /auth/google/callback?code=...&state=...
  3. GET /auth/google/callback
       - verify state matches oauth_state cookie
       - exchange code for tokens (authlib OAuth2Session.fetch_token)
       - fetch userinfo from googleapis.com/oauth2/v3/userinfo
       - look up user by google_sub OR email; create if neither exists
       - issue refresh token, set refresh cookie, 302 to FRONTEND_URL/auth/google/callback?success=1

State nonce: a 32-byte urlsafe secret, stored in a short-lived httpOnly
cookie (10 min, SameSite=Lax — required for the cross-site redirect back
from Google to carry the cookie).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import TYPE_CHECKING

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2 import OAuth2Error

from app.core.config import settings
from app.schemas.auth import GoogleUserInfo

if TYPE_CHECKING:
    pass


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Scopes: openid + email + profile. We need email + name to create the user.
GOOGLE_SCOPES = ["openid", "email", "profile"]


def generate_state() -> str:
    """Generate a self-validating OAuth state token.

    Format: <nonce>.<unix_ts>.<hmac_sha256_hex>

    Signing with the server secret makes the token tamper-evident and gives it
    a built-in expiry without requiring a cookie or any server-side storage.
    This sidesteps the cross-site cookie delivery problem (SameSite=Lax cookies
    set on a cross-origin redirect from Google back to the backend are not
    reliably forwarded by all browsers / proxy configurations).
    """
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    payload = f"{nonce}.{ts}"
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_state(token: str, max_age: int = 600) -> bool:
    """Return True iff *token* was produced by generate_state() and has not expired."""
    try:
        last_dot = token.rfind(".")
        if last_dot == -1:
            return False
        payload, sig = token[:last_dot], token[last_dot + 1:]
        parts = payload.split(".")
        if len(parts) < 2:
            return False
        ts = int(parts[-1])
        if time.time() - ts > max_age:
            return False
        expected = hmac.new(
            settings.JWT_SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False


def build_authorization_url(state: str) -> str:
    """Build the Google consent-screen URL with the right redirect_uri + state.

    authlib's OAuth2Session.create_authorization_url could be used here, but
    building the URL manually is simpler (no async client needed for a pure
    URL build) and the params are stable.
    """
    from urllib.parse import urlencode

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
        "access_type": "offline",  # hint for refresh token (we don't use it)
        "prompt": "select_account",  # force account picker, even if 1 account
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_userinfo(code: str) -> GoogleUserInfo:
    """Exchange the authorization code for access/id tokens, then fetch
    the user's profile info.

    Uses authlib's AsyncOAuth2Client to do the token exchange. We do NOT
    store the Google access_token or refresh_token — we only need userinfo
    to identify the user.

    Raises:
      OAuthError — on any failure (bad code, network error, malformed response).
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise OAuthError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET in .env."
        )

    async with AsyncOAuth2Client(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.google_oauth_redirect_uri,
        state=None,  # we verify state ourselves in the router
    ) as client:
        # Exchange code → tokens. authlib handles PKCE-less code flow here.
        try:
            await client.fetch_token(
                GOOGLE_TOKEN_URL,
                authorization_response=None,
                code=code,
                grant_type="authorization_code",
            )
        except OAuth2Error as e:
            raise OAuthError(f"Google token exchange failed: {e}") from e

        # Fetch userinfo.
        try:
            resp = await client.get(GOOGLE_USERINFO_URL)
            resp.raise_for_status()
        except Exception as e:
            raise OAuthError(f"Failed to fetch Google userinfo: {e}") from e

        try:
            data = resp.json()
        except Exception as e:
            raise OAuthError(f"Google userinfo returned non-JSON: {e}") from e

    # Validate the bare minimum.
    if "sub" not in data or "email" not in data:
        raise OAuthError(
            f"Google userinfo missing required fields (sub/email). Got: {data}"
        )

    return GoogleUserInfo(
        sub=data["sub"],
        email=data["email"],
        name=data.get("name") or data.get("given_name") or data["email"].split("@")[0],
    )


class OAuthError(Exception):
    """Raised on any OAuth flow failure (bad code, network, malformed response,
    missing config)."""
