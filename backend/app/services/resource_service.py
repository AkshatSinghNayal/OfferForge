"""Resource business logic. CRUD scoped to current user. Nullable company_id."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import Resource
from app.models.user import User
from app.schemas.misc import ResourceCreate, ResourceUpdate
from app.services.activity_log import log_activity


class ResourceError(Exception):
    pass


class ResourceNotFound(ResourceError):
    pass


async def list_resources(
    session: AsyncSession,
    *,
    user: User,
    category: str | None = None,
    company_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Resource], int]:
    """List the user's resources with filters + pagination."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conditions = [Resource.user_id == user.id]
    if category:
        conditions.append(Resource.category == category)
    if company_id is not None:
        conditions.append(Resource.company_id == company_id)
    if q:
        conditions.append(Resource.title.ilike(f"%{q}%"))

    where_clause = and_(*conditions)

    total = await session.scalar(
        select(func.count()).select_from(Resource).where(where_clause)
    )
    total = total or 0

    stmt = (
        select(Resource)
        .where(where_clause)
        .order_by(Resource.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.scalars(stmt)).all()
    return list(items), total


async def create_resource(
    session: AsyncSession, *, user: User, body: ResourceCreate
) -> Resource:
    resource = Resource(
        user_id=user.id,
        company_id=body.company_id,
        title=body.title,
        url=body.url,
        category=body.category,
        description=body.description,
    )
    session.add(resource)
    await session.flush()

    await log_activity(
        session,
        user_id=user.id,
        action="resource_added",
        entity_type="resource",
        entity_id=resource.id,
        metadata={"title": resource.title, "category": resource.category},
    )
    await session.commit()
    await session.refresh(resource)
    return resource


async def get_resource(
    session: AsyncSession, *, user: User, resource_id: uuid.UUID
) -> Resource:
    r = await session.scalar(
        select(Resource).where(Resource.id == resource_id, Resource.user_id == user.id)
    )
    if r is None:
        raise ResourceNotFound(f"resource not found: {resource_id}")
    return r


async def update_resource(
    session: AsyncSession, *, user: User, resource_id: uuid.UUID, body: ResourceUpdate
) -> Resource:
    resource = await get_resource(session, user=user, resource_id=resource_id)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)
    await session.commit()
    await session.refresh(resource)
    return resource


async def delete_resource(
    session: AsyncSession, *, user: User, resource_id: uuid.UUID
) -> None:
    resource = await get_resource(session, user=user, resource_id=resource_id)
    await session.delete(resource)
    await session.commit()
