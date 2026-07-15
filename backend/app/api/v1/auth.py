"""Auth router — signup, login, refresh, logout, me, Google OAuth, password reset.

All endpoints are under /api/v1/auth. The refresh cookie is scoped to
Path=/api/v1/auth so the browser only sends it on these endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignupRequest,
    TokenResponse,
    UserPublic,
)
from app.seed_demo import DEMO_EMAIL, DEMO_PASSWORD, seed_demo_data
from app.services import auth_service, oauth
from app.services.auth_service import (
    AuthError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    OAuthUserConflictError,
    PasswordResetError,
    RefreshTokenError,
    UserInactiveError,
)
from app.services.oauth import OAuthError, exchange_code_for_userinfo, generate_state, verify_state, build_authorization_url

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_to_public(user: User) -> UserPublic:
    """Map the ORM row to the public Pydantic schema.

    Crucially: this never includes hashed_password or google_sub. The
    has_google_linked boolean is the only OAuth signal we expose.
    """
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        has_google_linked=user.google_sub is not None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _read_refresh_cookie(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)


# ---------------------------------------------------------------------------
# Signup / login
# ---------------------------------------------------------------------------

@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    body: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        user, access, raw_refresh = await auth_service.signup(
            session, email=body.email, password=body.password, full_name=body.full_name
        )
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access, user=_user_to_public(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    try:
        user, access, raw_refresh = await auth_service.login(
            session, email=body.email, password=body.password
        )
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except UserInactiveError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access, user=_user_to_public(user))


@router.post("/demo", response_model=TokenResponse)
async def demo_login(
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    """Seed demo data (idempotent) and log in as the demo user."""
    user = await seed_demo_data(session)
    _, access, raw_refresh = await auth_service.login(
        session, email=DEMO_EMAIL, password=DEMO_PASSWORD
    )
    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=access, user=_user_to_public(user))


# ---------------------------------------------------------------------------
# Refresh / logout
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    raw = _read_refresh_cookie(request)
    try:
        user, access, new_raw = await auth_service.refresh_session(session, raw or "")
    except RefreshTokenError as e:
        # Clear the cookie so the browser stops sending a bad token.
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=access, user=_user_to_public(user))


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    raw = _read_refresh_cookie(request)
    await auth_service.logout(session, raw)
    clear_refresh_cookie(response)
    return MessageResponse(message="logged out")


# ---------------------------------------------------------------------------
# /me (protected — proves get_current_user works)
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently-authenticated user. Used by the frontend on boot
    to populate the auth context, and as a smoke test for protected routes."""
    return _user_to_public(current_user)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@router.get("/google/login")
async def google_login():
    """Redirect to Google's consent screen with a signed state token.

    The state is an HMAC-SHA256-signed token (nonce + timestamp). The callback
    verifies the signature and expiry without needing a cookie, which sidesteps
    cross-site cookie delivery issues in the vercel→render deployment.
    """
    state = generate_state()
    url = build_authorization_url(state)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Handle the redirect back from Google.

    On success: 302 → FRONTEND_URL/auth/google/callback?success=1 with the
                refresh cookie set.
    On failure: 302 → FRONTEND_URL/login?error=<reason> with no cookie.
    """
    # Google-side error (user declined, etc.)
    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/login?error=oauth_declined",
            status_code=status.HTTP_302_FOUND,
        )

    if not code or not state:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/login?error=oauth_missing_params",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify the signed state token (signature + expiry).  No cookie required —
    # the state is self-validating via HMAC-SHA256 signed with JWT_SECRET_KEY.
    if not verify_state(state):
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/login?error=oauth_state_mismatch",
            status_code=status.HTTP_302_FOUND,
        )

    # Exchange code → userinfo → user.
    try:
        info = await exchange_code_for_userinfo(code)
        user, access, raw_refresh = await auth_service.oauth_link_or_create(session, info)
    except (OAuthError, AuthError) as e:
        resp = RedirectResponse(
            f"{settings.FRONTEND_URL}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
        # Include the detail in a header for debugging — not in the URL (could leak).
        resp.headers["X-OAuth-Error"] = str(e)[:200]
        return resp

    resp = RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/google/callback?success=1",
        status_code=status.HTTP_302_FOUND,
    )
    set_refresh_cookie(resp, raw_refresh)
    # We don't return the access token in the URL (leak risk). The frontend
    # will call POST /auth/refresh on load to get a fresh access token using
    # the just-set cookie.
    return resp


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
)
async def password_reset_request(
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Request a password reset email.

    Always returns 200 with the same message — does NOT reveal whether the
    email exists. The email send is stubbed (console.log per Prompt 0);
    the token generation / hashing / storage / expiry logic is real.
    """
    await auth_service.request_password_reset(session, body.email)
    return MessageResponse(message="if the email is registered, a reset link has been sent")


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
)
async def password_reset_confirm(
    body: PasswordResetConfirm,
    session: AsyncSession = Depends(get_async_session),
):
    """Consume a reset token and set the new password."""
    try:
        await auth_service.confirm_password_reset(session, body.token, body.new_password)
    except PasswordResetError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserInactiveError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return MessageResponse(message="password updated")
