"""Search router — GET /search?q= hits companies, dsa_problems, notes, resources.

MVP: ILIKE-based. Post-MVP: move to pg_trgm or Postgres full-text search.
See app.services.search_service for the parameterization note.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.misc import SearchResponse
from app.services import search_service

router = APIRouter()


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Search across companies, dsa_problems, notes, resources via ILIKE.

    All queries use SQLAlchemy parameterized ILIKE — no string interpolation.
    See app.services.search_service for the security + post-MVP upgrade note.
    """
    return await search_service.search(session, user=current_user, q=q, limit=limit)
