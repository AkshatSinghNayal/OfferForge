"""DSA problem business logic. Routers stay thin; this module owns all DB
reads/writes for the DSA tracker.

Scope:
  - Every query filters by user_id = current_user.id. Problems are
    user-private; one user can never see another's problems.
  - Tags are global (shared across users), but the problem-tag link is
    per-problem. Adding "arrays" as a tag on two different users' problems
    reuses the same dsa_tags row.
  - `tag_names` on create/update is a list of strings. The service upserts
    each name into dsa_tags (case-insensitive — "Arrays" and "arrays" map
    to the same row), then rebuilds the dsa_problem_tags rows for that
    problem. On update, passing `tag_names` REPLACES the full tag set
    (tags not in the list are unlinked from this problem — but NOT deleted
    from dsa_tags, since other problems may use them).
  - Activity log: writes `dsa_created` on POST, `dsa_solved` when status
    transitions to "Solved", `dsa_status_changed` on other status changes.

Errors:
  - ProblemNotFound — GET/PATCH/DELETE on a problem the user doesn't own
    (or that doesn't exist). 404 in the router (not 403, to avoid leaking
    existence).
  - TagError — tag operation on a problem not owned by the user.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dsa import DsaProblem, DsaProblemTag, DsaTag
from app.models.user import User
from app.schemas.dsa import (
    DifficultyStat,
    DsaStats,
    ProblemCreate,
    ProblemUpdate,
    TopicStat,
)
from app.services.activity_log import log_activity


# ---------------------------------------------------------------------------
# Typed errors (router maps these to HTTP statuses)
# ---------------------------------------------------------------------------

class DsaError(Exception):
    """Base class for DSA-service errors."""


class ProblemNotFound(DsaError):
    """Problem with the given id does not exist OR is not owned by the user."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_problem_owned_by(
    session: AsyncSession, *, problem_id: uuid.UUID, user_id: uuid.UUID
) -> DsaProblem:
    """Fetch a problem, eager-loading its tags. Raises ProblemNotFound if
    the row doesn't exist OR is owned by a different user."""
    stmt = (
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(DsaProblem.id == problem_id, DsaProblem.user_id == user_id)
    )
    problem = await session.scalar(stmt)
    if problem is None:
        raise ProblemNotFound(f"problem not found: {problem_id}")
    return problem


async def _upsert_tags(
    session: AsyncSession, names: list[str]
) -> list[DsaTag]:
    """Resolve a list of tag names to DsaTag rows, creating missing ones.

    Case-insensitive: "Arrays", "arrays", "ARRAYS" all map to the same row
    (the first-seen casing wins as the canonical stored name). Returns the
    list of DsaTag rows in the same order as the input names (deduplicated
    case-insensitively).
    """
    if not names:
        return []

    # Normalize: strip, dedupe case-insensitively preserving first-seen order.
    seen_lower: set[str] = set()
    normalized: list[str] = []
    for n in names:
        s = n.strip()
        if not s:
            continue
        key = s.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        normalized.append(s)

    if not normalized:
        return []

    lowered = [n.lower() for n in normalized]

    # SELECT existing tags matching lower(name) IN (...).
    existing = (
        await session.scalars(
            select(DsaTag).where(func.lower(DsaTag.name).in_(lowered))
        )
    ).all()

    # Map lower(name) → row for the ones that exist.
    existing_by_lower: dict[str, DsaTag] = {t.name.lower(): t for t in existing}

    # Create the missing ones.
    to_create: list[DsaTag] = []
    result: list[DsaTag] = []
    for orig_name in normalized:
        key = orig_name.lower()
        if key in existing_by_lower:
            result.append(existing_by_lower[key])
        else:
            new_tag = DsaTag(name=orig_name)
            session.add(new_tag)
            to_create.append(new_tag)
            # Track in the map so duplicates within the same request reuse
            # the newly-created instance.
            existing_by_lower[key] = new_tag
            result.append(new_tag)

    # Flush so newly-created tags get their ids before we link them.
    if to_create:
        await session.flush()

    return result


async def _set_problem_tags(
    session: AsyncSession, problem: DsaProblem, names: list[str]
) -> list[DsaTag]:
    """Replace the problem's tag set with the resolved tags for `names`.

    Deletes existing dsa_problem_tags rows for this problem, then inserts
    new ones. Flushes so the links are visible in the DB before the caller
    commits. Returns the final list of DsaTag rows.
    """
    # Wipe existing links.
    await session.execute(
        delete(DsaProblemTag).where(DsaProblemTag.dsa_problem_id == problem.id)
    )

    tags = await _upsert_tags(session, names)
    for tag in tags:
        link = DsaProblemTag(dsa_problem_id=problem.id, dsa_tag_id=tag.id)
        session.add(link)

    # Flush so the new DsaProblemTag rows are in the DB. Without this, the
    # caller's subsequent selectinload fetch might not see them (the session
    # autoflush is disabled in our session factory).
    await session.flush()
    return tags


def _tag_public_list(problem: DsaProblem) -> list[dict]:
    """Build the JSON-serializable list of {id, name} for activity metadata."""
    return [{"id": str(t.tag.id), "name": t.tag.name} for t in problem.tags if t.tag]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def create_problem(
    session: AsyncSession, *, user: User, body: ProblemCreate
) -> DsaProblem:
    """Create a new DSA problem for the user. Sets completed_at if status is
    Solved at creation time."""
    completed_at = (
        datetime.now(timezone.utc) if body.status == "Solved" else None
    )
    problem = DsaProblem(
        user_id=user.id,
        title=body.title,
        platform=body.platform,
        external_url=body.external_url,
        difficulty=body.difficulty,
        status=body.status,
        revision_status=body.revision_status,
        completed_at=completed_at,
        notes=body.notes,
    )
    session.add(problem)
    await session.flush()  # populate problem.id

    if body.tag_names:
        await _set_problem_tags(session, problem, body.tag_names)

    # Activity log: dsa_created.
    # Use body.tag_names (the input) for the metadata rather than
    # problem.tags (the relationship), because accessing the relationship
    # here would trigger a lazy-load that fails under async SQLAlchemy
    # (MissingGreenlet) when no tags were set.
    await log_activity(
        session,
        user_id=user.id,
        action="dsa_created",
        entity_type="dsa_problem",
        entity_id=problem.id,
        metadata={
            "problem_title": problem.title,
            "platform": problem.platform,
            "difficulty": problem.difficulty,
            "status": problem.status,
            "tags": list(body.tag_names),
        },
    )
    # If created directly as Solved, also log dsa_solved.
    if problem.status == "Solved":
        await log_activity(
            session,
            user_id=user.id,
            action="dsa_solved",
            entity_type="dsa_problem",
            entity_id=problem.id,
            metadata={
                "problem_title": problem.title,
                "platform": problem.platform,
                "difficulty": problem.difficulty,
            },
        )

    await session.commit()
    # Expire all cached objects so the re-fetch below actually hits the DB
    # (SQLAlchemy's identity map would otherwise return the stale problem
    # with its old tag set).
    problem_id_snapshot = problem.id
    session.expire_all()
    # Re-fetch with selectinload to populate tag.tag cleanly for the response.
    fresh = await session.scalar(
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(DsaProblem.id == problem_id_snapshot)
    )
    return fresh if fresh is not None else problem


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

async def get_problem(
    session: AsyncSession, *, user: User, problem_id: uuid.UUID
) -> DsaProblem:
    return await _get_problem_owned_by(session, problem_id=problem_id, user_id=user.id)


async def list_problems(
    session: AsyncSession,
    *,
    user: User,
    topic: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    platform: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DsaProblem], int]:
    """List the user's problems with filters + pagination.

    Returns (items, total). `total` is the count BEFORE pagination so the
    client can render "showing 1-20 of 137".

    Filters:
      topic     — problems tagged with a tag whose name matches (case-insensitive)
      difficulty — Easy/Medium/Hard
      status    — one of DSA_STATUSES
      platform  — LeetCode/GFG/Codeforces
      q         — ILIKE against title
    """
    # Clamp pagination.
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Base filter: user's problems.
    conditions = [DsaProblem.user_id == user.id]

    if difficulty:
        conditions.append(DsaProblem.difficulty == difficulty)
    if status:
        conditions.append(DsaProblem.status == status)
    if platform:
        conditions.append(DsaProblem.platform == platform)
    if q:
        conditions.append(DsaProblem.title.ilike(f"%{q}%"))

    # Topic filter requires a join to dsa_problem_tags + dsa_tags.
    topic_join_needed = topic is not None and topic.strip() != ""
    if topic_join_needed:
        topic_lower = topic.strip().lower()
        # EXISTS subquery: problem has a tag whose lower(name) = topic_lower.
        topic_exists = (
            select(DsaProblemTag.dsa_problem_id)
            .join(DsaTag, DsaTag.id == DsaProblemTag.dsa_tag_id)
            .where(
                DsaProblemTag.dsa_problem_id == DsaProblem.id,
                func.lower(DsaTag.name) == topic_lower,
            )
            .exists()
        )
        conditions.append(topic_exists)

    where_clause = and_(*conditions)

    # Total count (before pagination).
    total = await session.scalar(
        select(func.count()).select_from(DsaProblem).where(where_clause)
    )
    total = total or 0

    # Items with pagination + eager-loaded tags.
    stmt = (
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(where_clause)
        .order_by(DsaProblem.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.scalars(stmt)).all()
    return list(items), total


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def update_problem(
    session: AsyncSession,
    *,
    user: User,
    problem_id: uuid.UUID,
    body: ProblemUpdate,
) -> DsaProblem:
    """Patch a problem. Only fields present in `body` are applied.

    If `tag_names` is present, the full tag set is replaced.

    If `status` transitions to "Solved", sets completed_at = now() (if not
    already set) and logs dsa_solved. If `status` transitions away from
    "Solved", clears completed_at.
    """
    problem = await _get_problem_owned_by(session, problem_id=problem_id, user_id=user.id)

    # Snapshot the old status to detect transitions.
    old_status = problem.status

    # Apply scalar fields.
    update_data = body.model_dump(exclude_unset=True)
    tag_names = update_data.pop("tag_names", None)

    for field, value in update_data.items():
        setattr(problem, field, value)

    # Status transition side-effects.
    new_status = problem.status
    if new_status == "Solved" and old_status != "Solved":
        if problem.completed_at is None:
            problem.completed_at = datetime.now(timezone.utc)
    elif new_status != "Solved" and old_status == "Solved":
        problem.completed_at = None

    # Apply tag replacement if requested.
    if tag_names is not None:
        await _set_problem_tags(session, problem, tag_names)

    # Activity log: dsa_solved on transition to Solved, dsa_status_changed
    # on other status transitions. dsa_created is logged only at create time.
    if new_status == "Solved" and old_status != "Solved":
        await log_activity(
            session,
            user_id=user.id,
            action="dsa_solved",
            entity_type="dsa_problem",
            entity_id=problem.id,
            metadata={
                "problem_title": problem.title,
                "platform": problem.platform,
                "difficulty": problem.difficulty,
                "previous_status": old_status,
            },
        )
    elif new_status != old_status:
        await log_activity(
            session,
            user_id=user.id,
            action="dsa_status_changed",
            entity_type="dsa_problem",
            entity_id=problem.id,
            metadata={
                "problem_title": problem.title,
                "platform": problem.platform,
                "previous_status": old_status,
                "new_status": new_status,
            },
        )

    await session.commit()
    problem_id_snapshot = problem.id
    session.expire_all()
    # Re-fetch with selectinload to populate tag.tag cleanly for the response.
    fresh = await session.scalar(
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(DsaProblem.id == problem_id_snapshot)
    )
    return fresh if fresh is not None else problem


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def delete_problem(
    session: AsyncSession, *, user: User, problem_id: uuid.UUID
) -> None:
    """Delete a problem. Cascade removes its dsa_problem_tags rows."""
    problem = await _get_problem_owned_by(session, problem_id=problem_id, user_id=user.id)
    await session.delete(problem)
    await session.commit()


# ---------------------------------------------------------------------------
# Tag operations (add/remove on a single problem)
# ---------------------------------------------------------------------------

async def add_tag_to_problem(
    session: AsyncSession, *, user: User, problem_id: uuid.UUID, tag_name: str
) -> DsaProblem:
    """Add a single tag to a problem. Idempotent — if the tag is already
    linked, this is a no-op (but still returns the problem)."""
    problem = await _get_problem_owned_by(session, problem_id=problem_id, user_id=user.id)
    tag_name = tag_name.strip()
    if not tag_name:
        raise DsaError("tag name cannot be empty")

    # Build the union of existing tag names + new one, then replace.
    current_names = [t.tag.name for t in problem.tags if t.tag]
    if tag_name.lower() in [n.lower() for n in current_names]:
        # Already linked — no-op.
        return problem
    new_names = current_names + [tag_name]
    await _set_problem_tags(session, problem, new_names)
    await session.commit()
    problem_id_snapshot = problem.id
    session.expire_all()
    # Re-fetch with selectinload so the response includes the updated tags.
    fresh = await session.scalar(
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(DsaProblem.id == problem_id_snapshot)
    )
    return fresh if fresh is not None else problem


async def remove_tag_from_problem(
    session: AsyncSession, *, user: User, problem_id: uuid.UUID, tag_name: str
) -> DsaProblem:
    """Remove a single tag from a problem. Idempotent — if the tag isn't
    linked, this is a no-op."""
    problem = await _get_problem_owned_by(session, problem_id=problem_id, user_id=user.id)
    tag_name = tag_name.strip()
    if not tag_name:
        raise DsaError("tag name cannot be empty")

    current_names = [t.tag.name for t in problem.tags if t.tag]
    new_names = [n for n in current_names if n.lower() != tag_name.lower()]
    if len(new_names) == len(current_names):
        # Tag wasn't linked — no-op.
        return problem
    await _set_problem_tags(session, problem, new_names)
    await session.commit()
    problem_id_snapshot = problem.id
    session.expire_all()
    # Re-fetch with selectinload so the response includes the updated tags.
    fresh = await session.scalar(
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(DsaProblem.id == problem_id_snapshot)
    )
    return fresh if fresh is not None else problem


# ---------------------------------------------------------------------------
# Tag list (reverse direction: see all problems for a tag, plus tag catalog)
# ---------------------------------------------------------------------------

async def list_tags(session: AsyncSession, *, user: User) -> list[tuple[DsaTag, int]]:
    """List all tags, with the count of the current user's problems using each.

    Returns a list of (DsaTag, problem_count) tuples. Tags with zero of the
    user's problems are still included — the frontend uses this to populate
    the tag picker.
    """
    # Left join: every dsa_tag, plus the count of the user's problems linked
    # to it. Tags not used by this user show count=0.
    stmt = (
        select(
            DsaTag,
            func.count(DsaProblemTag.id).label("problem_count"),
        )
        .outerjoin(DsaProblemTag, DsaProblemTag.dsa_tag_id == DsaTag.id)
        .outerjoin(DsaProblem, DsaProblem.id == DsaProblemTag.dsa_problem_id)
        .group_by(DsaTag.id)
        .order_by(DsaTag.name)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1] or 0) for row in rows]


async def list_problems_for_tag(
    session: AsyncSession,
    *,
    user: User,
    tag_name: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[DsaProblem], int]:
    """List the user's problems tagged with `tag_name` (case-insensitive).

    This is the 'reverse direction' of tag management: 'see all problems
    for a tag'. Returns (items, total).
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    tag_lower = tag_name.strip().lower()
    if not tag_lower:
        return [], 0

    # EXISTS subquery for the tag.
    tag_exists = (
        select(DsaProblemTag.dsa_problem_id)
        .join(DsaTag, DsaTag.id == DsaProblemTag.dsa_tag_id)
        .where(
            DsaProblemTag.dsa_problem_id == DsaProblem.id,
            func.lower(DsaTag.name) == tag_lower,
        )
        .exists()
    )
    where_clause = and_(DsaProblem.user_id == user.id, tag_exists)

    total = await session.scalar(
        select(func.count()).select_from(DsaProblem).where(where_clause)
    )
    total = total or 0

    stmt = (
        select(DsaProblem)
        .options(selectinload(DsaProblem.tags).selectinload(DsaProblemTag.tag))
        .where(where_clause)
        .order_by(DsaProblem.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.scalars(stmt)).all()
    return list(items), total


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

async def get_stats(session: AsyncSession, *, user: User) -> DsaStats:
    """Compute topic-wise and difficulty-wise completion stats.

    'Solved' = status = 'Solved'. 'Total' = all problems for the user.
    pct = solved / total * 100, rounded to 1 decimal. If total = 0, pct = 0.

    Topic-wise stats are computed across all tags the user has used (even
    tags with 0 solved). Difficulty-wise stats always include all three
    difficulties (Easy/Medium/Hard) even if total = 0 for some.
    """
    # --- Difficulty-wise ---
    diff_rows = (
        await session.execute(
            select(
                DsaProblem.difficulty,
                func.count().label("total"),
                func.count().filter(DsaProblem.status == "Solved").label("solved"),
            )
            .where(DsaProblem.user_id == user.id)
            .group_by(DsaProblem.difficulty)
        )
    ).all()
    diff_map: dict[str, tuple[int, int]] = {r[0]: (r[2] or 0, r[1] or 0) for r in diff_rows}

    difficulty_wise: list[DifficultyStat] = []
    for d in ("Easy", "Medium", "Hard"):
        solved, total = diff_map.get(d, (0, 0))
        pct = round(solved / total * 100, 1) if total else 0.0
        difficulty_wise.append(
            DifficultyStat(difficulty=d, total=total, solved=solved, pct=pct)
        )

    # --- Topic-wise ---
    # All tags the user has linked to ANY of their problems, with solved/total.
    topic_rows = (
        await session.execute(
            select(
                DsaTag.name,
                func.count(DsaProblem.id).label("total"),
                func.count(DsaProblem.id).filter(DsaProblem.status == "Solved").label("solved"),
            )
            .select_from(DsaTag)
            .join(DsaProblemTag, DsaProblemTag.dsa_tag_id == DsaTag.id)
            .join(DsaProblem, DsaProblem.id == DsaProblemTag.dsa_problem_id)
            .where(DsaProblem.user_id == user.id)
            .group_by(DsaTag.id, DsaTag.name)
            .order_by(DsaTag.name)
        )
    ).all()
    topic_wise: list[TopicStat] = []
    for r in topic_rows:
        name = r[0]
        total = r[1] or 0
        solved = r[2] or 0
        pct = round(solved / total * 100, 1) if total else 0.0
        topic_wise.append(TopicStat(tag=name, total=total, solved=solved, pct=pct))

    # --- Overall ---
    overall_total = await session.scalar(
        select(func.count()).select_from(DsaProblem).where(DsaProblem.user_id == user.id)
    )
    overall_solved = await session.scalar(
        select(func.count())
        .select_from(DsaProblem)
        .where(DsaProblem.user_id == user.id, DsaProblem.status == "Solved")
    )
    overall_total = overall_total or 0
    overall_solved = overall_solved or 0
    overall_pct = round(overall_solved / overall_total * 100, 1) if overall_total else 0.0

    return DsaStats(
        topic_wise=topic_wise,
        difficulty_wise=difficulty_wise,
        overall_total=overall_total,
        overall_solved=overall_solved,
        overall_pct=overall_pct,
    )
