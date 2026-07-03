"""Auth business logic. Routers stay thin; this module owns all DB writes
for the auth flow.

Design notes:
  - Refresh tokens are stored hashed (SHA-256) in the DB. The client only
    ever sees the raw token via the httpOnly cookie. On refresh, we rotate:
    the old token is marked revoked and a new one is issued, so a stolen
    refresh cookie becomes useless after one legitimate refresh.
  - Signup with an existing email returns a typed `EmailAlreadyExistsError`
    so the router can map it to 409 (not 500).
  - Login with a wrong password returns False (not raise) so the router
    can map to 401.
  - On password reset confirm, we revoke ALL the user's outstanding refresh
    tokens — if an attacker had stolen the old password, they should not
    be able to keep using existing sessions.
  - Google OAuth: if a user with the OAuth email already exists, we link
    google_sub to that user (instead of creating a duplicate). If a user
    with the google_sub already exists, we just log them in.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_raw_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    password_reset_token_expiry,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User
from app.schemas.auth import GoogleUserInfo
from app.services.email_stub import build_password_reset_email, send_email


# ---------------------------------------------------------------------------
# Typed errors (routers map these to HTTP statuses)
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Base class for all auth-service errors."""


class EmailAlreadyExistsError(AuthError):
    """Signup attempted with an email that's already registered."""


class InvalidCredentialsError(AuthError):
    """Login failed (wrong email or password)."""


class UserInactiveError(AuthError):
    """User.is_active is False."""


class RefreshTokenError(AuthError):
    """Any refresh-token failure: missing, not found, revoked, expired."""


class PasswordResetError(AuthError):
    """Any password-reset failure: token not found, used, or expired."""


class OAuthUserConflictError(AuthError):
    """A different user account already has this google_sub linked."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issue_refresh_token(session: AsyncSession, user: User) -> tuple[str, RefreshToken]:
    """Generate a new refresh token, persist its hash, return (raw, row).

    The raw token is returned to the caller so it can be set as a cookie.
    Only the hash is persisted.
    """
    raw = generate_raw_token()
    token_hash = hash_token(raw)
    row = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=refresh_token_expiry(),
        revoked=False,
    )
    session.add(row)
    return raw, row


# ---------------------------------------------------------------------------
# Signup / login
# ---------------------------------------------------------------------------

async def signup(
    session: AsyncSession, *, email: str, password: str, full_name: str
) -> tuple[User, str, str]:
    """Create a new email/password user.

    Returns (user, access_token, raw_refresh_token). The caller is
    responsible for setting the refresh cookie on the response.

    Raises:
      EmailAlreadyExistsError — email already in users table.
    """
    # Check existing email first — doing this explicitly avoids relying on
    # the unique constraint to surface as IntegrityError, which would also
    # fire for the google_sub unique constraint and be ambiguous.
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyExistsError(f"email already registered: {email}")

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        google_sub=None,
        is_active=True,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as e:
        # Race: another signup inserted the same email between our SELECT
        # and INSERT. Map to the same typed error.
        await session.rollback()
        raise EmailAlreadyExistsError(f"email already registered: {email}") from e

    # Issue refresh token.
    from app.core.security import create_access_token
    raw_refresh, _ = _issue_refresh_token(session, user)
    access = create_access_token(user.id)
    await session.commit()
    await session.refresh(user)
    return user, access, raw_refresh


async def login(
    session: AsyncSession, *, email: str, password: str
) -> tuple[User, str, str]:
    """Log a user in with email + password.

    Returns (user, access_token, raw_refresh_token).

    Raises:
      InvalidCredentialsError — no user with that email OR wrong password.
      UserInactiveError — user.is_active is False.
    """
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        # Use the same error message for both branches to avoid leaking
        # which emails are registered (user enumeration).
        raise InvalidCredentialsError("invalid email or password")
    if not user.is_active:
        raise UserInactiveError("account is inactive")
    if not user.hashed_password:
        # User exists but is Google-only — they have no password to verify.
        # Treat as invalid credentials rather than revealing the account type.
        raise InvalidCredentialsError("invalid email or password")
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("invalid email or password")

    from app.core.security import create_access_token
    raw_refresh, _ = _issue_refresh_token(session, user)
    access = create_access_token(user.id)
    await session.commit()
    return user, access, raw_refresh


# ---------------------------------------------------------------------------
# Refresh + logout
# ---------------------------------------------------------------------------

async def refresh_session(
    session: AsyncSession, raw_refresh_token: str
) -> tuple[User, str, str]:
    """Rotate a refresh token: revoke the old one, issue a new one.

    Returns (user, new_access_token, new_raw_refresh_token).

    Raises:
      RefreshTokenError — cookie missing, token not found, revoked, or expired.
    """
    if not raw_refresh_token:
        raise RefreshTokenError("missing refresh token")

    token_hash = hash_token(raw_refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if row is None:
        raise RefreshTokenError("refresh token not found")
    if row.revoked:
        raise RefreshTokenError("refresh token revoked")
    if row.expires_at <= datetime.now(timezone.utc):
        # Mark it revoked so it can't be reused even after expiry (housekeeping).
        row.revoked = True
        await session.commit()
        raise RefreshTokenError("refresh token expired")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise RefreshTokenError("user not found or inactive")

    # Rotate: revoke old, issue new.
    row.revoked = True
    new_raw, _ = _issue_refresh_token(session, user)

    from app.core.security import create_access_token
    access = create_access_token(user.id)
    await session.commit()
    return user, access, new_raw


async def logout(session: AsyncSession, raw_refresh_token: str | None) -> None:
    """Revoke the refresh token (if present). Idempotent — calling logout
    with no cookie is a no-op rather than an error."""
    if not raw_refresh_token:
        return
    token_hash = hash_token(raw_refresh_token)
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if row is not None and not row.revoked:
        row.revoked = True
        await session.commit()


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

async def oauth_link_or_create(
    session: AsyncSession, info: GoogleUserInfo
) -> tuple[User, str, str]:
    """Given Google userinfo, return (user, access_token, raw_refresh_token).

    Linking logic:
      1. Look up by google_sub. If found → that's the user.
      2. Else look up by email. If found → link google_sub to that user
         (sets user.google_sub = info.sub).
      3. Else → create a new user with google_sub set, hashed_password NULL.

    Raises:
      OAuthUserConflictError — google_sub is somehow already on a different
        user row (should not happen given the unique constraint, but guard).
    """
    # 1. Existing Google link.
    user = await session.scalar(select(User).where(User.google_sub == info.sub))
    if user is not None:
        if not user.is_active:
            raise UserInactiveError("account is inactive")
        # Already linked — just issue tokens.
        from app.core.security import create_access_token
        raw_refresh, _ = _issue_refresh_token(session, user)
        access = create_access_token(user.id)
        await session.commit()
        return user, access, raw_refresh

    # 2. Existing email account — link Google to it.
    user = await session.scalar(select(User).where(User.email == info.email))
    if user is not None:
        if not user.is_active:
            raise UserInactiveError("account is inactive")
        user.google_sub = info.sub
        # If the user previously had a different name from Google, update it.
        # (Optional — keeping the existing name to avoid surprising overwrites.)
        from app.core.security import create_access_token
        raw_refresh, _ = _issue_refresh_token(session, user)
        access = create_access_token(user.id)
        await session.commit()
        await session.refresh(user)
        return user, access, raw_refresh

    # 3. Brand new user.
    user = User(
        email=info.email,
        full_name=info.name or info.email.split("@")[0],
        hashed_password=None,
        google_sub=info.sub,
        is_active=True,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise OAuthUserConflictError(
            f"could not create/link OAuth user: {e}"
        ) from e

    from app.core.security import create_access_token
    raw_refresh, _ = _issue_refresh_token(session, user)
    access = create_access_token(user.id)
    await session.commit()
    await session.refresh(user)
    return user, access, raw_refresh


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

async def request_password_reset(session: AsyncSession, email: str) -> None:
    """Issue a password-reset token for the user with the given email, if any.

    Always returns None — callers should respond with the same message
    regardless of whether the email exists, to avoid user enumeration.

    If the user exists, a reset token is generated, hashed, stored with a
    30-minute expiry, and the (stubbed) email is "sent" with the reset link.
    """
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        # Silently no-op. Don't reveal whether the email is registered.
        return

    raw = generate_raw_token()
    token_hash = hash_token(raw)
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=password_reset_token_expiry(),
        used_at=None,
    )
    session.add(row)
    await session.commit()

    # "Send" the email (stubbed — prints to stdout).
    subject, body = build_password_reset_email(user.email, user.full_name, raw)
    send_email(to_email=user.email, subject=subject, body=body)


async def confirm_password_reset(
    session: AsyncSession, token: str, new_password: str
) -> User:
    """Consume a password-reset token and set the new password.

    Raises:
      PasswordResetError — token not found, already used, or expired.
    """
    token_hash = hash_token(token)
    row = await session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if row is None:
        raise PasswordResetError("invalid or unknown reset token")
    if row.used_at is not None:
        raise PasswordResetError("reset token already used")
    if row.expires_at <= datetime.now(timezone.utc):
        raise PasswordResetError("reset token expired")

    user = await session.get(User, row.user_id)
    if user is None:
        raise PasswordResetError("user not found for reset token")
    if not user.is_active:
        raise UserInactiveError("account is inactive")

    # Set new password.
    user.hashed_password = hash_password(new_password)
    row.used_at = datetime.now(timezone.utc)

    # Revoke all outstanding refresh tokens for this user — force re-login
    # everywhere after a password reset.
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )

    await session.commit()
    await session.refresh(user)
    return user
