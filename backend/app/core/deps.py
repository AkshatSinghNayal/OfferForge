"""FastAPI dependencies for auth-protected routes.

Usage in feature routers (Phase 3+):
    from app.core.deps import get_current_user
    from app.models.user import User

    @router.get("/things")
    async def list_things(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
    ):
        ...
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenExpiredError, TokenInvalidError, decode_access_token
from app.db.session import get_async_session
from app.models.user import User

# auto_error=True means FastAPI returns 403 if no Authorization header is
# present. We override to 401 below for the no-token case.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Resolve the bearer token to a User row.

    Raises:
      401 — no Authorization header (no token).
      401 — token expired.
      401 — token invalid (bad signature, wrong type, malformed).
      401 — token valid but user no longer exists or is inactive.
    """
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials
    try:
        user_id = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="access token expired",
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Token-Expired": "true",
            },
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid access token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience dependency — same as get_current_user but with a clearer
    name for feature routers that want to express 'must be active'."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive user")
    return current_user
