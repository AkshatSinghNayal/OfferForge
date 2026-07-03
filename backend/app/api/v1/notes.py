"""Notes router — CRUD, nullable company_id, nullable dsa_problem_id (XOR)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.note import NOTE_TYPES
from app.models.user import User
from app.schemas.misc import NoteCreate, NoteList, NotePublic, NoteUpdate
from app.services import note_service
from app.services.note_service import NoteNotFound, NoteXorError

router = APIRouter()


@router.get("", response_model=NoteList)
async def list_notes(
    type: str | None = Query(default=None, description="Filter by note type"),
    company_id: uuid.UUID | None = Query(default=None),
    dsa_problem_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None, description="Search title OR content"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if type is not None and type not in NOTE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"type must be one of {NOTE_TYPES}, got {type!r}",
        )
    items, total = await note_service.list_notes(
        session, user=current_user, type_filter=type,
        company_id=company_id, dsa_problem_id=dsa_problem_id,
        q=q, limit=limit, offset=offset,
    )
    return NoteList(
        items=[NotePublic.model_validate(n) for n in items],
        total=total, limit=limit, offset=offset,
    )


@router.post("", response_model=NotePublic, status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        n = await note_service.create_note(session, user=current_user, body=body)
    except NoteXorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return NotePublic.model_validate(n)


@router.get("/{note_id}", response_model=NotePublic)
async def get_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        n = await note_service.get_note(session, user=current_user, note_id=note_id)
    except NoteNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note not found")
    return NotePublic.model_validate(n)


@router.patch("/{note_id}", response_model=NotePublic)
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        n = await note_service.update_note(
            session, user=current_user, note_id=note_id, body=body
        )
    except NoteNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note not found")
    except NoteXorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return NotePublic.model_validate(n)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await note_service.delete_note(session, user=current_user, note_id=note_id)
    except NoteNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note not found")
    return None
