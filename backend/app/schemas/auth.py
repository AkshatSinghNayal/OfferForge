"""Pydantic v2 schemas for the auth router.

Critical invariant: UserPublic NEVER contains hashed_password, google_sub,
or any secret. Every endpoint that returns a user must go through UserPublic
so we cannot accidentally leak the hash.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# User (public, safe to return to clients)
# ---------------------------------------------------------------------------

class UserPublic(BaseModel):
    """The user shape returned by every auth endpoint. No secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    # True if the user has linked Google. Lets the frontend show "Link Google"
    # vs "Unlink Google" without exposing the google_sub itself.
    has_google_linked: bool = False
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Auth request bodies
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Auth response bodies
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Returned by signup + login + refresh. The refresh token is NOT in
    the JSON body — it rides in the httpOnly cookie set on the response."""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MessageResponse(BaseModel):
    """Generic { message: str } envelope for endpoints that don't return data."""

    message: str


# ---------------------------------------------------------------------------
# OAuth helper (not exposed via API — used internally by the OAuth service)
# ---------------------------------------------------------------------------

class GoogleUserInfo(BaseModel):
    """Subset of the fields returned by Google's userinfo endpoint."""

    sub: str
    email: EmailStr
    name: str | None = None
