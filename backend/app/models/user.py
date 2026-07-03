"""User + refresh-token models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """A user of the placement tracker.

    Email/password users have hashed_password set and google_sub NULL.
    Google-only users have google_sub set and hashed_password NULL.
    Both can be set if a user links Google to an existing email/password account.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Nullable: null for Google-only users.
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nullable: null for email/password-only users.
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Either auth method (or both) must be present. A user with neither
        # is invalid and should never be creatable.
        CheckConstraint(
            "hashed_password IS NOT NULL OR google_sub IS NOT NULL",
            name="ck_users_has_auth_method",
        ),
    )


class RefreshToken(Base, TimestampMixin):
    """A persisted, hashed refresh token.

    The client sends the raw token in the httpOnly `refresh_token` cookie.
    The server SHA-256s it and looks up token_hash, so a DB dump alone
    cannot replay a session. Tokens are rotated on every refresh (old row
    is marked revoked, new row is inserted).
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class PasswordResetToken(Base, TimestampMixin):
    """A single-use password-reset token.

    Flow:
      1. POST /auth/password-reset/request { email }
         → look up user by email. If found, generate a 32-byte urlsafe
           token, hash with SHA-256, store here with expires_at, "send"
           the email (stubbed via console.log in app.services.email_stub).
      2. POST /auth/password-reset/confirm { token, new_password }
         → hash the token, look it up, verify expires_at > now() and
           used_at IS NULL. Set user.hashed_password to bcrypt(new_password),
           mark used_at = now(), revoke all of the user's refresh tokens.

    Tokens are stored hashed (same pattern as refresh_tokens) so a DB dump
    alone cannot be used to reset passwords. 30-minute expiry, single-use.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")
