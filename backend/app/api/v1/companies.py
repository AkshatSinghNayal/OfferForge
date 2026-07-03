"""Companies router — CRUD + tracking (user_company) endpoints.

All endpoints protected by get_current_user. Seeded companies are visible
to all users but not editable/deletable. Custom companies are editable/
deletable only by their owner.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.company import APPLICATION_STATUSES, COMPANY_CLUSTERS
from app.models.user import User
from app.schemas.companies import (
    ChecklistItemPublic,
    CompanyCreate,
    CompanyDetail,
    CompanyList,
    CompanyPublic,
    CompanyUpdate,
    TrackRequest,
    TrackResponse,
    TrackUpdateRequest,
    TrackedCompany,
    TrackedCompanyList,
    UserState,
)
from app.services import company_service
from app.services.company_service import (
    AlreadyTrackingError,
    CompanyNotCustomError,
    CompanyNotFound,
    CompanyNotOwnedError,
    NotTrackingError,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _company_to_public(company) -> CompanyPublic:
    return CompanyPublic(
        id=company.id,
        name=company.name,
        cluster=company.cluster,
        hiring_process=company.hiring_process,
        oa_pattern=company.oa_pattern,
        frequent_dsa_topics=company.frequent_dsa_topics or [],
        core_cs_subjects=company.core_cs_subjects or [],
        resume_requirements=company.resume_requirements,
        interview_experiences=company.interview_experiences or [],
        is_custom=company.is_custom,
        created_by=company.created_by,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def _validate_cluster(cluster: str | None) -> None:
    if cluster is not None and cluster not in COMPANY_CLUSTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"cluster must be one of {COMPANY_CLUSTERS}, got {cluster!r}",
        )


def _validate_application_status(s: str | None) -> None:
    if s is not None and s not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"application_status must be one of {APPLICATION_STATUSES}, got {s!r}",
        )


def _checklist_progress(items) -> float:
    if not items:
        return 0.0
    done = sum(1 for i in items if i.is_done)
    return round(done / len(items) * 100, 1)


# ---------------------------------------------------------------------------
# Company CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=CompanyList)
async def list_companies(
    cluster: str | None = Query(default=None),
    is_custom: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all companies (seeded + custom) with filters + pagination."""
    _validate_cluster(cluster)
    items, total = await company_service.list_companies(
        session,
        cluster=cluster,
        is_custom=is_custom,
        q=q,
        limit=limit,
        offset=offset,
    )
    return CompanyList(
        items=[_company_to_public(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CompanyPublic, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    company = await company_service.create_company(session, user=current_user, body=body)
    return _company_to_public(company)


@router.get("/{company_id}", response_model=CompanyDetail)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a company + the current user's tracking state (if any)."""
    try:
        company, uc, mapped_resume_ids = await company_service.get_company_with_user_state(
            session, user=current_user, company_id=company_id
        )
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")

    user_state = None
    if uc is not None:
        user_state = UserState(
            user_company_id=uc.id,
            application_status=uc.application_status,
            deadline=uc.deadline,
            checklist_progress_pct=_checklist_progress(uc.checklist_items),
            mapped_resume_ids=mapped_resume_ids,
        )
    return CompanyDetail(**_company_to_public(company).model_dump(), user_state=user_state)


@router.patch("/{company_id}", response_model=CompanyPublic)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        company = await company_service.update_company(
            session, user=current_user, company_id=company_id, body=body
        )
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    except CompanyNotCustomError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _company_to_public(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a custom company owned by the user. Cascade removes all
    user_company + checklist_items + resume_company_map rows pointing at it."""
    try:
        await company_service.delete_company(session, user=current_user, company_id=company_id)
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    except CompanyNotCustomError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return None


# ---------------------------------------------------------------------------
# Tracking (user_company)
# ---------------------------------------------------------------------------

@router.post("/{company_id}/track", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def track_company(
    company_id: uuid.UUID,
    body: TrackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Start tracking a company. Seeds the 15 fixed checklist items in the same txn."""
    try:
        uc, items = await company_service.track_company(
            session, user=current_user, company_id=company_id, body=body
        )
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    except AlreadyTrackingError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return TrackResponse(
        user_company_id=uc.id,
        company_id=uc.company_id,
        application_status=uc.application_status,
        deadline=uc.deadline,
        checklist_items=[
            ChecklistItemPublic(
                id=i.id, user_company_id=i.user_company_id, item_key=i.item_key,
                label=i.label, is_done=i.is_done, completed_at=i.completed_at,
                created_at=i.created_at, updated_at=i.updated_at,
            ) for i in items
        ],
        checklist_progress_pct=0.0,  # just seeded — all items is_done=False
    )


@router.patch("/{company_id}/track", response_model=TrackedCompany)
async def update_tracking(
    company_id: uuid.UUID,
    body: TrackUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update the user's tracking state (status, deadline, notes)."""
    try:
        uc = await company_service.update_tracking(
            session, user=current_user, company_id=company_id, body=body
        )
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    except NotTrackingError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not tracking this company")
    # Fetch the company for the response shape.
    from app.models.company import Company
    company = await session.get(Company, uc.company_id)
    return TrackedCompany(
        id=uc.id, company_id=uc.company_id, company_name=company.name if company else "",
        cluster=company.cluster if company else "",
        application_status=uc.application_status, deadline=uc.deadline,
        notes_summary=uc.notes_summary, checklist_progress_pct=0.0,
        created_at=uc.created_at, updated_at=uc.updated_at,
    )


@router.delete("/{company_id}/track", status_code=status.HTTP_204_NO_CONTENT)
async def untrack_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Stop tracking a company. Cascade removes checklist_items + resume_company_map."""
    try:
        await company_service.untrack_company(session, user=current_user, company_id=company_id)
    except CompanyNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    except NotTrackingError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not tracking this company")
    return None


# ---------------------------------------------------------------------------
# Tracked companies list
# ---------------------------------------------------------------------------

@router.get("/tracked/list", response_model=TrackedCompanyList)
async def list_tracked(
    cluster: str | None = Query(default=None),
    application_status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List the companies the current user is tracking, with filters + pagination."""
    _validate_cluster(cluster)
    _validate_application_status(application_status)
    rows, total = await company_service.list_tracked_companies(
        session,
        user=current_user,
        cluster=cluster,
        application_status=application_status,
        limit=limit,
        offset=offset,
    )
    items = [
        TrackedCompany(
            id=uc.id, company_id=company.id, company_name=company.name,
            cluster=company.cluster, application_status=uc.application_status,
            deadline=uc.deadline, notes_summary=uc.notes_summary,
            checklist_progress_pct=_checklist_progress(uc.checklist_items),
            created_at=uc.created_at, updated_at=uc.updated_at,
        )
        for uc, company in rows
    ]
    return TrackedCompanyList(items=items, total=total, limit=limit, offset=offset)
