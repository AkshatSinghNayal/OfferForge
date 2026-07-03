"""Resumes router — upload, activate, delete, keywords, map-company, readiness.

All endpoints protected by get_current_user. Every query is scoped to the
current user's resumes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.resumes import (
    KeywordCreate,
    KeywordPublic,
    KeywordUpdate,
    MapCompanyRequest,
    ReadinessResponse,
    ResumeCompanyMapPublic,
    ResumeList,
    ResumePublic,
    ResumeWithScore,
)
from app.services import resume_service
from app.services.resume_service import (
    InvalidFileError,
    KeywordNotFound,
    ResumeNotFound,
    UserCompanyNotOwnedError,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resume_to_public(resume) -> ResumePublic:
    return ResumePublic(
        id=resume.id,
        user_id=resume.user_id,
        version_label=resume.version_label,
        cloudinary_url=resume.cloudinary_url,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


def _resume_with_score(resume, coverage: float, score: float) -> ResumeWithScore:
    return ResumeWithScore(
        id=resume.id,
        user_id=resume.user_id,
        version_label=resume.version_label,
        cloudinary_url=resume.cloudinary_url,
        is_active=resume.is_active,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        keyword_coverage_pct=coverage,
        readiness_score=score,
    )


# ---------------------------------------------------------------------------
# Upload + list
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=ResumePublic, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(..., description="PDF file, max 5MB"),
    version_label: str = Form(..., min_length=1, max_length=80),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload a resume PDF. If this is the user's first resume, auto-activates it."""
    file_bytes = await file.read()
    try:
        resume = await resume_service.upload_resume(
            session,
            user=current_user,
            file_bytes=file_bytes,
            filename=file.filename or "upload.pdf",
            version_label=version_label,
            content_type=file.content_type,
        )
    except InvalidFileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _resume_to_public(resume)


@router.get("", response_model=ResumeList)
async def list_resumes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all of the user's resumes with computed readiness scores."""
    rows = await resume_service.list_resumes(session, user=current_user)
    return ResumeList(
        items=[_resume_with_score(r, cov, score) for r, cov, score in rows]
    )


# ---------------------------------------------------------------------------
# Activate / delete
# ---------------------------------------------------------------------------

@router.post("/{resume_id}/activate", response_model=ResumePublic)
async def activate_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Set a resume as the user's active one. Unsets any previously active resume."""
    try:
        resume = await resume_service.activate_resume(
            session, user=current_user, resume_id=resume_id
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    return _resume_to_public(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a resume. Cloudinary file destroyed; if deleted was active,
    auto-activates the most recent remaining resume (if any)."""
    try:
        await resume_service.delete_resume(session, user=current_user, resume_id=resume_id)
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    return None


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

@router.get("/{resume_id}/keywords", response_model=list[KeywordPublic])
async def list_keywords(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        kws = await resume_service.list_keywords(
            session, user=current_user, resume_id=resume_id
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    return [KeywordPublic.model_validate(k) for k in kws]


@router.post("/{resume_id}/keywords", response_model=KeywordPublic, status_code=status.HTTP_201_CREATED)
async def add_keyword(
    resume_id: uuid.UUID,
    body: KeywordCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        kw = await resume_service.add_keyword(
            session, user=current_user, resume_id=resume_id, body=body
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    return KeywordPublic.model_validate(kw)


@router.patch("/{resume_id}/keywords/{keyword_id}", response_model=KeywordPublic)
async def update_keyword(
    resume_id: uuid.UUID,
    keyword_id: uuid.UUID,
    body: KeywordUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        kw = await resume_service.update_keyword(
            session, user=current_user,
            resume_id=resume_id, keyword_id=keyword_id, body=body,
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    except KeywordNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="keyword not found")
    return KeywordPublic.model_validate(kw)


@router.delete("/{resume_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    resume_id: uuid.UUID,
    keyword_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await resume_service.delete_keyword(
            session, user=current_user,
            resume_id=resume_id, keyword_id=keyword_id,
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    except KeywordNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="keyword not found")
    return None


# ---------------------------------------------------------------------------
# Resume ↔ company mapping
# ---------------------------------------------------------------------------

@router.post("/{resume_id}/map-company", response_model=ResumeCompanyMapPublic, status_code=status.HTTP_201_CREATED)
async def map_company(
    resume_id: uuid.UUID,
    body: MapCompanyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Associate a resume with a tracked company (user_company)."""
    try:
        mapping = await resume_service.map_company(
            session, user=current_user, resume_id=resume_id, body=body
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    except UserCompanyNotOwnedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ResumeCompanyMapPublic.model_validate(mapping)


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

@router.get("/{resume_id}/readiness", response_model=ReadinessResponse)
async def get_readiness(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return the readiness breakdown for a resume.

    Formula (also in the response body):
      readiness_score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4
    """
    try:
        data = await resume_service.get_readiness(
            session, user=current_user, resume_id=resume_id
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")
    return ReadinessResponse(**data)


# ---------------------------------------------------------------------------
# PDF — serve directly from the pdf_data BYTEA column stored in Postgres.
# ---------------------------------------------------------------------------

@router.get("/{resume_id}/pdf")
async def serve_pdf(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return the resume PDF bytes stored in Postgres."""
    try:
        resume = await resume_service.get_resume(
            session, user=current_user, resume_id=resume_id
        )
    except ResumeNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resume not found")

    if not resume.pdf_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not available")

    return Response(
        content=resume.pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
