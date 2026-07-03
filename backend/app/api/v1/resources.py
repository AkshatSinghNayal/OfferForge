"""Resources router — CRUD, filter by category, nullable company_id."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.resource import RESOURCE_CATEGORIES
from app.models.user import User
from app.schemas.misc import ResourceCreate, ResourceList, ResourcePublic, ResourceUpdate
from app.services import resource_service
from app.services.resource_service import ResourceNotFound

router = APIRouter()


@router.get("", response_model=ResourceList)
async def list_resources(
    category: str | None = Query(default=None),
    company_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if category is not None and category not in RESOURCE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"category must be one of {RESOURCE_CATEGORIES}, got {category!r}",
        )
    items, total = await resource_service.list_resources(
        session, user=current_user, category=category, company_id=company_id,
        q=q, limit=limit, offset=offset,
    )
    return ResourceList(
        items=[ResourcePublic.model_validate(r) for r in items],
        total=total, limit=limit, offset=offset,
    )


@router.post("", response_model=ResourcePublic, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ResourceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    r = await resource_service.create_resource(session, user=current_user, body=body)
    return ResourcePublic.model_validate(r)


@router.get("/{resource_id}", response_model=ResourcePublic)
async def get_resource(
    resource_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        r = await resource_service.get_resource(session, user=current_user, resource_id=resource_id)
    except ResourceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return ResourcePublic.model_validate(r)


@router.patch("/{resource_id}", response_model=ResourcePublic)
async def update_resource(
    resource_id: uuid.UUID,
    body: ResourceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        r = await resource_service.update_resource(
            session, user=current_user, resource_id=resource_id, body=body
        )
    except ResourceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return ResourcePublic.model_validate(r)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await resource_service.delete_resource(session, user=current_user, resource_id=resource_id)
    except ResourceNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return None
