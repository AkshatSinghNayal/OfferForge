"""DSA router — full CRUD + tag management + stats. All endpoints protected
by get_current_user. Every query is scoped to the current user.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.dsa import (
    DSA_DIFFICULTIES,
    DSA_PLATFORMS,
    DSA_STATUSES,
)
from app.models.user import User
from app.schemas.dsa import (
    DifficultyStat,
    DsaStats,
    ProblemCreate,
    ProblemList,
    ProblemPublic,
    ProblemUpdate,
    TagPublic,
)
from app.services import dsa_service
from app.services.dsa_service import DsaError, ProblemNotFound

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _problem_to_public(problem) -> ProblemPublic:
    """Map the ORM row to the public Pydantic schema, including tags."""
    return ProblemPublic(
        id=problem.id,
        user_id=problem.user_id,
        title=problem.title,
        platform=problem.platform,
        external_url=problem.external_url,
        difficulty=problem.difficulty,
        status=problem.status,
        revision_status=problem.revision_status,
        completed_at=problem.completed_at,
        notes=problem.notes,
        tags=[
            TagPublic(id=pt.tag.id, name=pt.tag.name)
            for pt in problem.tags
            if pt.tag is not None
        ],
        created_at=problem.created_at,
        updated_at=problem.updated_at,
    )


def _validate_filter_values(
    *, difficulty: str | None, status_filter: str | None, platform: str | None
) -> None:
    """Reject unknown filter values with 400 instead of silently returning [].

    Note: parameter is named `status_filter` (not `status`) to avoid
    shadowing the `fastapi.status` module imported at the top of this file.
    """
    if difficulty is not None and difficulty not in DSA_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"difficulty must be one of {DSA_DIFFICULTIES}, got {difficulty!r}",
        )
    if status_filter is not None and status_filter not in DSA_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of {DSA_STATUSES}, got {status_filter!r}",
        )
    if platform is not None and platform not in DSA_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"platform must be one of {DSA_PLATFORMS}, got {platform!r}",
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/problems", response_model=ProblemList)
async def list_problems(
    topic: str | None = Query(default=None, description="Filter by tag name (case-insensitive)"),
    difficulty: str | None = Query(default=None, description="Easy | Medium | Hard"),
    status: str | None = Query(default=None, description="One of DSA_STATUSES"),
    platform: str | None = Query(default=None, description="LeetCode | GFG | Codeforces"),
    q: str | None = Query(default=None, description="ILIKE against title"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List the current user's problems with filters + pagination."""
    _validate_filter_values(difficulty=difficulty, status_filter=status, platform=platform)
    items, total = await dsa_service.list_problems(
        session,
        user=current_user,
        topic=topic,
        difficulty=difficulty,
        status=status,
        platform=platform,
        q=q,
        limit=limit,
        offset=offset,
    )
    return ProblemList(
        items=[_problem_to_public(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/problems", response_model=ProblemPublic, status_code=status.HTTP_201_CREATED)
async def create_problem(
    body: ProblemCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    problem = await dsa_service.create_problem(session, user=current_user, body=body)
    return _problem_to_public(problem)


@router.get("/problems/{problem_id}", response_model=ProblemPublic)
async def get_problem(
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        problem = await dsa_service.get_problem(session, user=current_user, problem_id=problem_id)
    except ProblemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="problem not found")
    return _problem_to_public(problem)


@router.patch("/problems/{problem_id}", response_model=ProblemPublic)
async def update_problem(
    problem_id: uuid.UUID,
    body: ProblemUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        problem = await dsa_service.update_problem(
            session, user=current_user, problem_id=problem_id, body=body
        )
    except ProblemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="problem not found")
    return _problem_to_public(problem)


@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem(
    problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await dsa_service.delete_problem(session, user=current_user, problem_id=problem_id)
    except ProblemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="problem not found")
    return None


# ---------------------------------------------------------------------------
# Tag management — add/remove on a single problem
# ---------------------------------------------------------------------------

@router.post("/problems/{problem_id}/tags", response_model=ProblemPublic)
async def add_tag(
    problem_id: uuid.UUID,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Add a single tag to a problem. Body: { "name": "arrays" }.
    Idempotent — adding an already-linked tag is a no-op."""
    name = (body or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
    try:
        problem = await dsa_service.add_tag_to_problem(
            session, user=current_user, problem_id=problem_id, tag_name=name
        )
    except ProblemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="problem not found")
    except DsaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _problem_to_public(problem)


@router.delete("/problems/{problem_id}/tags/{tag_name}", response_model=ProblemPublic)
async def remove_tag(
    problem_id: uuid.UUID,
    tag_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove a tag (by name, case-insensitive) from a problem. Idempotent."""
    try:
        problem = await dsa_service.remove_tag_from_problem(
            session, user=current_user, problem_id=problem_id, tag_name=tag_name
        )
    except ProblemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="problem not found")
    except DsaError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _problem_to_public(problem)


# ---------------------------------------------------------------------------
# Tag catalog + reverse-direction listing
# ---------------------------------------------------------------------------

@router.get("/tags", response_model=list[TagPublic])
async def list_tags(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all tags with the count of the current user's problems using each."""
    rows = await dsa_service.list_tags(session, user=current_user)
    return [TagPublic(id=t.id, name=t.name, problem_count=count) for t, count in rows]


@router.get("/tags/{tag_name}/problems", response_model=ProblemList)
async def list_problems_for_tag(
    tag_name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List the current user's problems tagged with `tag_name` (case-insensitive).
    This is the 'reverse direction' of tag management."""
    items, total = await dsa_service.list_problems_for_tag(
        session, user=current_user, tag_name=tag_name, limit=limit, offset=offset
    )
    return ProblemList(
        items=[_problem_to_public(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=DsaStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Topic-wise + difficulty-wise completion stats for the current user."""
    return await dsa_service.get_stats(session, user=current_user)
