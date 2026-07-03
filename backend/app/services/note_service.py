"""Note business logic.

A note can attach to nothing, a company, or a DSA problem — but NOT both
(XOR enforced by DB CHECK constraint ck_notes_attach_xor). The service
layer enforces this at validation time too, returning a clear 400 instead
of relying on the DB to raise a generic IntegrityError.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.user import User
from app.schemas.misc import NoteCreate, NoteUpdate
from app.services.activity_log import log_activity


class NoteError(Exception):
    pass


class NoteNotFound(NoteError):
    pass


class NoteXorError(NoteError):
    """Both company_id and dsa_problem_id were set — violates XOR constraint."""


def _validate_xor(body: NoteCreate | NoteUpdate) -> None:
    """Reject notes that set BOTH company_id and dsa_problem_id.

    The DB CHECK constraint is the last line of defense, but we catch this
    early with a clear 400 so the client gets a helpful error message
    instead of a generic 500 from an IntegrityError.
    """
    cid = getattr(body, "company_id", None)
    pid = getattr(body, "dsa_problem_id", None)
    if cid is not None and pid is not None:
        raise NoteXorError(
            "a note can attach to a company OR a dsa_problem, not both"
        )


async def list_notes(
    session: AsyncSession,
    *,
    user: User,
    type_filter: str | None = None,
    company_id: uuid.UUID | None = None,
    dsa_problem_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Note], int]:
    """List the user's notes with filters + pagination."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    conditions = [Note.user_id == user.id]
    if type_filter:
        conditions.append(Note.type == type_filter)
    if company_id is not None:
        conditions.append(Note.company_id == company_id)
    if dsa_problem_id is not None:
        conditions.append(Note.dsa_problem_id == dsa_problem_id)
    if q:
        # Search title OR content.
        conditions.append(Note.title.ilike(f"%{q}%") | Note.content.ilike(f"%{q}%"))

    where_clause = and_(*conditions)

    total = await session.scalar(
        select(func.count()).select_from(Note).where(where_clause)
    )
    total = total or 0

    stmt = (
        select(Note)
        .where(where_clause)
        .order_by(Note.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.scalars(stmt)).all()
    return list(items), total


async def create_note(
    session: AsyncSession, *, user: User, body: NoteCreate
) -> Note:
    _validate_xor(body)
    note = Note(
        user_id=user.id,
        title=body.title,
        content=body.content,
        type=body.type,
        company_id=body.company_id,
        dsa_problem_id=body.dsa_problem_id,
    )
    session.add(note)
    await session.flush()

    await log_activity(
        session,
        user_id=user.id,
        action="note_created",
        entity_type="note",
        entity_id=note.id,
        metadata={
            "title": note.title,
            "type": note.type,
            "has_company": note.company_id is not None,
            "has_dsa_problem": note.dsa_problem_id is not None,
        },
    )
    await session.commit()
    await session.refresh(note)
    return note


async def get_note(
    session: AsyncSession, *, user: User, note_id: uuid.UUID
) -> Note:
    n = await session.scalar(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    if n is None:
        raise NoteNotFound(f"note not found: {note_id}")
    return n


async def update_note(
    session: AsyncSession, *, user: User, note_id: uuid.UUID, body: NoteUpdate
) -> Note:
    note = await get_note(session, user=user, note_id=note_id)
    _validate_xor(body)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)
    await session.commit()
    await session.refresh(note)
    return note


async def delete_note(
    session: AsyncSession, *, user: User, note_id: uuid.UUID
) -> None:
    note = await get_note(session, user=user, note_id=note_id)
    await session.delete(note)
    await session.commit()
