"""Checklist router — list + toggle + bulk toggle. Progress % computed at read time."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.companies import (
    ChecklistBulkUpdate,
    ChecklistItemPublic,
    ChecklistResponse,
    ChecklistToggleRequest,
)
from app.services import checklist_service
from app.services.checklist_service import ChecklistItemNotFound, ChecklistNotFound

router = APIRouter()


def _item_to_public(item) -> ChecklistItemPublic:
    return ChecklistItemPublic(
        id=item.id,
        user_company_id=item.user_company_id,
        item_key=item.item_key,
        label=item.label,
        is_done=item.is_done,
        completed_at=item.completed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/{user_company_id}", response_model=ChecklistResponse)
async def list_checklist(
    user_company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all 15 checklist items + computed progress %."""
    try:
        items, pct = await checklist_service.list_checklist(
            session, user=current_user, user_company_id=user_company_id
        )
    except ChecklistNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checklist not found")
    return ChecklistResponse(
        items=[_item_to_public(i) for i in items],
        progress_pct=pct,
    )


# IMPORTANT: /bulk must be registered BEFORE /{item_id} so FastAPI doesn't
# try to parse "bulk" as a UUID path param. Route matching is order-sensitive.
@router.patch("/{user_company_id}/bulk", response_model=ChecklistResponse)
async def bulk_toggle(
    user_company_id: uuid.UUID,
    body: ChecklistBulkUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Set is_done on multiple items in one request."""
    try:
        items, pct = await checklist_service.bulk_toggle(
            session, user=current_user,
            user_company_id=user_company_id, updates=body.updates,
        )
    except ChecklistNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checklist not found")
    return ChecklistResponse(
        items=[_item_to_public(i) for i in items],
        progress_pct=pct,
    )


@router.patch("/{user_company_id}/{item_id}", response_model=ChecklistResponse)
async def toggle_item(
    user_company_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ChecklistToggleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Set is_done on a single item. Returns the full list + recomputed progress %."""
    try:
        items, pct = await checklist_service.toggle_item(
            session, user=current_user,
            user_company_id=user_company_id, item_id=item_id, is_done=body.is_done,
        )
    except ChecklistNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checklist not found")
    except ChecklistItemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checklist item not found")
    return ChecklistResponse(
        items=[_item_to_public(i) for i in items],
        progress_pct=pct,
    )
