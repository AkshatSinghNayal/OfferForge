"""Company business logic. Routers stay thin; this module owns all DB
reads/writes for companies + the user_company tracking join.

Cascade decision (documented per Phase 4 brief):
  When a company is deleted, every user_company row pointing at it is
  CASCADEd (FK ondelete="CASCADE" in migration 0001 + ORM
  cascade="all, delete-orphan" on Company.user_companies). Each
  user_company cascade in turn CASCADEs its checklist_items and
  resume_company_map rows. This is deliberate:
    - A company without any tracking data is just a catalog entry; deleting
      it should clean up everything tied to it.
    - Blocking deletion when tracked (the alternative) would let stale
      tracking rows accumulate for companies the user no longer wants.
    - The seeded companies (is_custom=false) are NOT deletable by users —
      only custom companies owned by the requesting user are. So cascade
      only ever affects the deleting user's own data.
  Seeded companies cannot be deleted at all (403). Custom companies can
  only be deleted by their owner (created_by == current_user.id); other
  users get 404 (not 403, to avoid leaking existence).

Tracking (user_company):
  - POST /companies/{id}/track creates the user_company row AND seeds the
    15 fixed checklist_items in the same transaction (see CHECKLIST_ITEMS
    in app.models.company). 409 if already tracking.
  - DELETE /companies/{id}/track removes the user_company row; cascade
    removes its checklist_items + resume_company_map.
  - Only one user_company per (user, company) — enforced by unique index.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import (
    APPLICATION_STATUSES,
    CHECKLIST_ITEMS,
    ChecklistItem,
    Company,
    UserCompany,
)
from app.models.resume import ResumeCompanyMap
from app.models.user import User
from app.schemas.companies import (
    CompanyCreate,
    CompanyUpdate,
    TrackRequest,
    TrackUpdateRequest,
)
from app.services.activity_log import log_activity


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------

class CompanyError(Exception):
    """Base class for company-service errors."""


class CompanyNotFound(CompanyError):
    """Company with the given id does not exist."""


class CompanyNotCustomError(CompanyError):
    """Operation requires a custom company but the company is seeded."""


class CompanyNotOwnedError(CompanyError):
    """Custom company exists but is owned by a different user."""


class AlreadyTrackingError(CompanyError):
    """User is already tracking this company."""


class NotTrackingError(CompanyError):
    """User is not tracking this company."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise CompanyNotFound(f"company not found: {company_id}")
    return company


async def _get_user_company(
    session: AsyncSession, *, user_id: uuid.UUID, user_company_id: uuid.UUID
) -> UserCompany:
    """Fetch a user_company row owned by the user. Raises NotTrackingError
    if the row doesn't exist OR is owned by a different user (404, no leak)."""
    uc = await session.scalar(
        select(UserCompany).where(
            UserCompany.id == user_company_id, UserCompany.user_id == user_id
        )
    )
    if uc is None:
        raise NotTrackingError(f"not tracking: {user_company_id}")
    return uc


def _checklist_progress(items: list[ChecklistItem]) -> float:
    """Compute progress % at read time. Never stored.

    pct = done / total * 100, rounded to 1 decimal. 0.0 if total == 0.
    The 15-item checklist is always seeded on track, so total is normally 15;
    but we guard against 0 to avoid division-by-zero.
    """
    if not items:
        return 0.0
    done = sum(1 for i in items if i.is_done)
    return round(done / len(items) * 100, 1)


# ---------------------------------------------------------------------------
# Company CRUD
# ---------------------------------------------------------------------------

async def list_companies(
    session: AsyncSession,
    *,
    cluster: str | None = None,
    is_custom: bool | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Company], int]:
    """List all companies (seeded + custom) with filters + pagination.

    Seeded companies are visible to all users. Custom companies are also
    visible to all users (they appear in the company catalog) — the
    is_custom + created_by fields let the UI show "Edit/Delete" only to
    the owner. This is intentional: a user might want to track a company
    another user added (e.g. a niche startup). If you want custom companies
    to be private, add a user_id filter here.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conditions = []
    if cluster:
        conditions.append(Company.cluster == cluster)
    if is_custom is not None:
        conditions.append(Company.is_custom == is_custom)
    if q:
        conditions.append(Company.name.ilike(f"%{q}%"))

    # Build the query. Use *conditions unpacking — when conditions is empty,
    # .where() with no args returns the unfiltered query (do NOT pass None,
    # which generates "WHERE NULL" and matches nothing).
    stmt = select(Company)
    count_stmt = select(func.count()).select_from(Company)
    if conditions:
        where_clause = and_(*conditions)
        stmt = stmt.where(where_clause)
        count_stmt = count_stmt.where(where_clause)

    total = await session.scalar(count_stmt)
    total = total or 0

    stmt = stmt.order_by(
        Company.is_custom.asc(),  # seeded first
        Company.name.asc(),
    ).limit(limit).offset(offset)
    items = (await session.scalars(stmt)).all()
    return list(items), total


async def get_company_with_user_state(
    session: AsyncSession, *, user: User, company_id: uuid.UUID
) -> tuple[Company, UserCompany | None, list[uuid.UUID]]:
    """Get a company + the current user's tracking state (if any) + list of
    mapped resume ids.

    Returns (company, user_company_or_None, mapped_resume_ids).
    Raises CompanyNotFound if the company doesn't exist.
    """
    company = await _get_company(session, company_id)

    # Look up the user's tracking row, eager-loading checklist_items.
    uc = await session.scalar(
        select(UserCompany)
        .options(selectinload(UserCompany.checklist_items))
        .where(UserCompany.user_id == user.id, UserCompany.company_id == company_id)
    )

    mapped_resume_ids: list[uuid.UUID] = []
    if uc is not None:
        rows = await session.scalars(
            select(ResumeCompanyMap.resume_id).where(
                ResumeCompanyMap.user_company_id == uc.id
            )
        )
        mapped_resume_ids = list(rows.all())

    return company, uc, mapped_resume_ids


async def create_company(
    session: AsyncSession, *, user: User, body: CompanyCreate
) -> Company:
    """Create a custom company. is_custom=true, created_by=user.id."""
    company = Company(
        name=body.name,
        cluster=body.cluster,
        hiring_process=body.hiring_process,
        oa_pattern=body.oa_pattern,
        frequent_dsa_topics=body.frequent_dsa_topics or [],
        core_cs_subjects=body.core_cs_subjects or [],
        resume_requirements=body.resume_requirements,
        interview_experiences=body.interview_experiences or [],
        is_custom=True,
        created_by=user.id,
    )
    session.add(company)
    await session.flush()

    await log_activity(
        session,
        user_id=user.id,
        action="company_created",
        entity_type="company",
        entity_id=company.id,
        metadata={"company_name": company.name, "cluster": company.cluster},
    )
    await session.commit()
    await session.refresh(company)
    return company


async def update_company(
    session: AsyncSession,
    *,
    user: User,
    company_id: uuid.UUID,
    body: CompanyUpdate,
) -> Company:
    """Patch a custom company owned by the user.

    Seeded companies (is_custom=false) → CompanyNotCustomError (403).
    Custom companies owned by another user → CompanyNotFound (404, no leak).
    """
    company = await _get_company(session, company_id)
    if not company.is_custom:
        raise CompanyNotCustomError("seeded companies cannot be edited")
    if company.created_by != user.id:
        # Pretend it doesn't exist to avoid leaking existence.
        raise CompanyNotFound(f"company not found: {company_id}")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await session.commit()
    await session.refresh(company)
    return company


async def delete_company(
    session: AsyncSession, *, user: User, company_id: uuid.UUID
) -> None:
    """Delete a custom company owned by the user.

    Cascade behavior (documented at the top of this module):
      - company → user_company rows (CASCADE)
      - user_company → checklist_items (CASCADE)
      - user_company → resume_company_map (CASCADE)
    All cleanup happens at the DB level via ON DELETE CASCADE.
    Seeded companies → 403. Custom companies owned by another user → 404.
    """
    company = await _get_company(session, company_id)
    if not company.is_custom:
        raise CompanyNotCustomError("seeded companies cannot be deleted")
    if company.created_by != user.id:
        raise CompanyNotFound(f"company not found: {company_id}")

    await log_activity(
        session,
        user_id=user.id,
        action="company_deleted",
        entity_type="company",
        entity_id=company.id,
        metadata={"company_name": company.name, "cluster": company.cluster},
    )
    await session.delete(company)
    await session.commit()


# ---------------------------------------------------------------------------
# Tracking (user_company)
# ---------------------------------------------------------------------------

async def track_company(
    session: AsyncSession,
    *,
    user: User,
    company_id: uuid.UUID,
    body: TrackRequest,
) -> tuple[UserCompany, list[ChecklistItem]]:
    """Start tracking a company. Creates user_company + seeds 15 checklist items.

    Raises CompanyNotFound if the company doesn't exist.
    Raises AlreadyTrackingError if the user is already tracking it.
    """
    company = await _get_company(session, company_id)

    # Check existing tracking.
    existing = await session.scalar(
        select(UserCompany).where(
            UserCompany.user_id == user.id, UserCompany.company_id == company_id
        )
    )
    if existing is not None:
        raise AlreadyTrackingError(f"already tracking: {company_id}")

    uc = UserCompany(
        user_id=user.id,
        company_id=company_id,
        application_status=body.application_status,
        deadline=body.deadline,
    )
    session.add(uc)
    await session.flush()  # populate uc.id

    # Seed the 15 fixed checklist items in the same transaction.
    for item_key, label in CHECKLIST_ITEMS:
        ci = ChecklistItem(
            user_company_id=uc.id,
            item_key=item_key,
            label=label,
            is_done=False,
        )
        session.add(ci)

    await log_activity(
        session,
        user_id=user.id,
        action="company_tracked",
        entity_type="company",
        entity_id=company_id,
        metadata={
            "company_name": company.name,
            "cluster": company.cluster,
            "application_status": body.application_status,
        },
    )
    await session.commit()
    await session.refresh(uc, attribute_names=["checklist_items"])
    return uc, list(uc.checklist_items)


async def update_tracking(
    session: AsyncSession,
    *,
    user: User,
    company_id: uuid.UUID,
    body: TrackUpdateRequest,
) -> UserCompany:
    """Update the user's tracking state for a company (status, deadline, notes)."""
    company = await _get_company(session, company_id)
    uc = await _get_user_company(session, user_id=user.id, user_company_id=None) if False else None
    # Actually fetch by (user_id, company_id) since we have company_id, not uc id.
    uc = await session.scalar(
        select(UserCompany).where(
            UserCompany.user_id == user.id, UserCompany.company_id == company_id
        )
    )
    if uc is None:
        raise NotTrackingError(f"not tracking: {company_id}")

    old_status = uc.application_status
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(uc, field, value)

    if body.application_status is not None and body.application_status != old_status:
        await log_activity(
            session,
            user_id=user.id,
            action="company_status_changed",
            entity_type="company",
            entity_id=company_id,
            metadata={
                "company_name": company.name,
                "previous_status": old_status,
                "new_status": body.application_status,
            },
        )

    await session.commit()
    await session.refresh(uc)
    return uc


async def untrack_company(
    session: AsyncSession, *, user: User, company_id: uuid.UUID
) -> None:
    """Stop tracking a company. Cascade removes checklist_items + resume_company_map."""
    company = await _get_company(session, company_id)
    uc = await session.scalar(
        select(UserCompany).where(
            UserCompany.user_id == user.id, UserCompany.company_id == company_id
        )
    )
    if uc is None:
        raise NotTrackingError(f"not tracking: {company_id}")

    await log_activity(
        session,
        user_id=user.id,
        action="company_untracked",
        entity_type="company",
        entity_id=company_id,
        metadata={"company_name": company.name},
    )
    await session.delete(uc)
    await session.commit()


async def list_tracked_companies(
    session: AsyncSession,
    *,
    user: User,
    cluster: str | None = None,
    application_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[tuple[UserCompany, Company]], int]:
    """List the companies the current user is tracking, with filters + pagination.

    Returns a list of (user_company, company) tuples + total count.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conditions = [UserCompany.user_id == user.id]
    if cluster:
        conditions.append(Company.cluster == cluster)
    if application_status:
        conditions.append(UserCompany.application_status == application_status)
    where_clause = and_(*conditions)

    # Total count.
    total = await session.scalar(
        select(func.count())
        .select_from(UserCompany)
        .join(Company, Company.id == UserCompany.company_id)
        .where(where_clause)
    )
    total = total or 0

    # Items.
    stmt = (
        select(UserCompany, Company)
        .join(Company, Company.id == UserCompany.company_id)
        .options(selectinload(UserCompany.checklist_items))
        .where(where_clause)
        .order_by(UserCompany.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows], total
