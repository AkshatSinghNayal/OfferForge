"""Checklist business logic.

Progress % is computed at read time, never stored. The 15 fixed items are
seeded when the parent user_company row is created (see
company_service.track_company). Toggling an item updates is_done + completed_at
and returns the full list + recomputed progress %.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import ChecklistItem, UserCompany
from app.models.user import User
from app.services.activity_log import log_activity


class ChecklistError(Exception):
    pass


class ChecklistNotFound(ChecklistError):
    """user_company not found OR not owned by the current user."""


class ChecklistItemNotFound(ChecklistError):
    """item_id not found within the given user_company."""


async def _get_user_company_owned_by(
    session: AsyncSession, *, user_id: uuid.UUID, user_company_id: uuid.UUID
) -> UserCompany:
    """Fetch a user_company + its checklist_items, owned by the user.

    404 (via ChecklistNotFound) if not owned — no existence leak.
    """
    uc = await session.scalar(
        select(UserCompany)
        .options(selectinload(UserCompany.checklist_items))
        .where(UserCompany.id == user_company_id, UserCompany.user_id == user_id)
    )
    if uc is None:
        raise ChecklistNotFound(f"checklist not found: {user_company_id}")
    return uc


def _progress(items: list[ChecklistItem]) -> float:
    if not items:
        return 0.0
    done = sum(1 for i in items if i.is_done)
    return round(done / len(items) * 100, 1)


async def list_checklist(
    session: AsyncSession, *, user: User, user_company_id: uuid.UUID
) -> tuple[list[ChecklistItem], float]:
    """Return all checklist items + progress % for a user_company."""
    uc = await _get_user_company_owned_by(
        session, user_id=user.id, user_company_id=user_company_id
    )
    items = list(uc.checklist_items)
    return items, _progress(items)


async def toggle_item(
    session: AsyncSession,
    *,
    user: User,
    user_company_id: uuid.UUID,
    item_id: uuid.UUID,
    is_done: bool,
) -> tuple[list[ChecklistItem], float]:
    """Set is_done on a single item. Sets completed_at=now() when True, NULL when False.

    Returns (all_items, progress_pct) — the full list + recomputed %.
    """
    uc = await _get_user_company_owned_by(
        session, user_id=user.id, user_company_id=user_company_id
    )
    item = next((i for i in uc.checklist_items if i.id == item_id), None)
    if item is None:
        raise ChecklistItemNotFound(f"item not found: {item_id}")

    # Only log + set completed_at when the value actually changes.
    if item.is_done != is_done:
        item.is_done = is_done
        item.completed_at = datetime.now(timezone.utc) if is_done else None

        # Activity log only when item flips to done (not when un-toggling —
        # keeps the feed focused on progress, not regressions).
        if is_done:
            await log_activity(
                session,
                user_id=user.id,
                action="checklist_item_completed",
                entity_type="checklist_item",
                entity_id=item.id,
                metadata={
                    "item_key": item.item_key,
                    "label": item.label,
                    "user_company_id": str(uc.id),
                },
            )

    await session.commit()
    # Re-fetch to get fresh state (expire_all + reload checklist_items).
    session.expire_all()
    fresh_uc = await session.scalar(
        select(UserCompany)
        .options(selectinload(UserCompany.checklist_items))
        .where(UserCompany.id == user_company_id)
    )
    items = list(fresh_uc.checklist_items) if fresh_uc else []
    return items, _progress(items)


async def bulk_toggle(
    session: AsyncSession,
    *,
    user: User,
    user_company_id: uuid.UUID,
    updates: list[dict],
) -> tuple[list[ChecklistItem], float]:
    """Set is_done on multiple items in one request.

    `updates` is a list of { item_id: uuid, is_done: bool }.
    """
    uc = await _get_user_company_owned_by(
        session, user_id=user.id, user_company_id=user_company_id
    )

    # Index existing items by id (as UUID) for O(1) lookup.
    items_by_id = {i.id: i for i in uc.checklist_items}

    now = datetime.now(timezone.utc)
    for upd in updates:
        item_id_raw = upd.get("item_id")
        is_done = upd.get("is_done")
        if item_id_raw is None or is_done is None:
            continue
        # Coerce string → UUID (JSON sends strings; ORM keys are UUIDs).
        try:
            item_id = uuid.UUID(item_id_raw) if isinstance(item_id_raw, str) else item_id_raw
        except (ValueError, AttributeError):
            continue  # malformed item_id — skip
        item = items_by_id.get(item_id)
        if item is None:
            continue  # skip unknown item_ids — don't fail the whole batch
        if item.is_done != is_done:
            item.is_done = is_done
            item.completed_at = now if is_done else None
            if is_done:
                await log_activity(
                    session,
                    user_id=user.id,
                    action="checklist_item_completed",
                    entity_type="checklist_item",
                    entity_id=item.id,
                    metadata={
                        "item_key": item.item_key,
                        "label": item.label,
                        "user_company_id": str(uc.id),
                    },
                )

    await session.commit()
    session.expire_all()
    fresh_uc = await session.scalar(
        select(UserCompany)
        .options(selectinload(UserCompany.checklist_items))
        .where(UserCompany.id == user_company_id)
    )
    items = list(fresh_uc.checklist_items) if fresh_uc else []
    return items, _progress(items)
