"""Resume business logic.

Readiness score formula (commented at every computation point per Phase 5
brief — tune the weights here when the rubric changes):

  readiness_score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4

  - keyword_coverage_pct = (keywords with is_present=true) / (total keywords) * 100
    If user has defined zero keywords, coverage defaults to 0.
  - has_active_resume = 1.0 if this resume (or any of the user's resumes)
    is_active=true, else 0.0
  - If user has no resumes at all, readiness_score = 0.

The formula is computed at read time — never stored — so it always
reflects the current keyword + active state.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import Resume, ResumeCompanyMap, ResumeKeyword
from app.models.user import User
from app.schemas.resumes import (
    KeywordCreate,
    KeywordUpdate,
    MapCompanyRequest,
)
from app.services.activity_log import log_activity


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PDF_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"application/pdf"}
PDF_MAGIC = b"%PDF-"  # first 5 bytes of a valid PDF


# ---------------------------------------------------------------------------
# Typed errors
# ---------------------------------------------------------------------------

class ResumeError(Exception):
    pass


class ResumeNotFound(ResumeError):
    pass


class ResumeNotOwnedError(ResumeError):
    pass


class InvalidFileError(ResumeError):
    """Wrong content type, too large, or not a valid PDF."""


class KeywordNotFound(ResumeError):
    pass


class MappingNotFound(ResumeError):
    pass


class UserCompanyNotOwnedError(ResumeError):
    """user_company_id in a map-company request doesn't belong to the user."""


# ---------------------------------------------------------------------------
# Readiness formula (documented per Phase 5 brief)
# ---------------------------------------------------------------------------

READINESS_FORMULA = (
    "readiness_score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4"
)


def _compute_readiness(
    *, keyword_total: int, keyword_present: int, has_active_resume: bool
) -> tuple[float, float, bool]:
    """Compute (keyword_coverage_pct, readiness_score, has_active_resume_bool).

    Readiness score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4
      - keyword_coverage_pct = (keywords with is_present=true) / (total keywords) * 100
        If user has defined zero keywords, coverage defaults to 0.
      - has_active_resume = 1.0 if this resume (or any of the user's resumes)
        is_active=true, else 0.0
      - If user has no resumes at all, readiness_score = 0.
    Tune the 0.6 / 0.4 weights here when the rubric changes.
    """
    # Readiness score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4
    if keyword_total == 0:
        coverage = 0.0
    else:
        coverage = round(keyword_present / keyword_total * 100, 1)
    active_val = 1.0 if has_active_resume else 0.0
    score = round(coverage * 0.6 + active_val * 0.4, 1)
    # Scale to 0-100: 0.6*100 + 0.4*1.0 = 60.4 max from coverage=100 + active=1.
    # We want readiness on a 0-100 scale, so:
    # score = coverage * 0.6 + (active ? 40 : 0)  → max = 60 + 40 = 100.
    score = round(coverage * 0.6 + (40.0 if has_active_resume else 0.0), 1)
    return coverage, score, has_active_resume


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_resume_owned_by(
    session: AsyncSession, *, resume_id: uuid.UUID, user_id: uuid.UUID
) -> Resume:
    """Fetch a resume owned by the user. 404 (via ResumeNotFound) if not owned."""
    resume = await session.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if resume is None:
        raise ResumeNotFound(f"resume not found: {resume_id}")
    return resume


async def _keyword_counts(session: AsyncSession, resume_id: uuid.UUID) -> tuple[int, int]:
    """Return (total, present) counts for a resume's keywords."""
    total = await session.scalar(
        select(func.count()).select_from(ResumeKeyword).where(ResumeKeyword.resume_id == resume_id)
    )
    present = await session.scalar(
        select(func.count())
        .select_from(ResumeKeyword)
        .where(ResumeKeyword.resume_id == resume_id, ResumeKeyword.is_present == True)  # noqa: E712
    )
    return total or 0, present or 0


async def _user_has_active_resume(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """True if the user has ANY resume with is_active=true."""
    count = await session.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.user_id == user_id, Resume.is_active == True)  # noqa: E712
    )
    return (count or 0) > 0


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _validate_pdf(file_bytes: bytes, content_type: str | None, filename: str) -> None:
    """Validate the uploaded file is a PDF and under 5MB. Raises InvalidFileError."""
    if not file_bytes:
        raise InvalidFileError("empty file")
    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        raise InvalidFileError(
            f"file too large: {len(file_bytes)} bytes (max {MAX_PDF_SIZE_BYTES} bytes / 5MB)"
        )
    # Check content type if provided — but don't trust it alone.
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidFileError(
            f"only PDF files are accepted (got content-type {content_type!r})"
        )
    # Magic-byte check: a real PDF starts with %PDF-.
    if not file_bytes[:5] == PDF_MAGIC:
        raise InvalidFileError(
            "file does not appear to be a valid PDF (missing %PDF- header)"
        )
    # Also check the extension as a hint (defense in depth).
    if filename and not filename.lower().endswith(".pdf"):
        raise InvalidFileError(
            f"only .pdf files are accepted (got filename {filename!r})"
        )


async def upload_resume(
    session: AsyncSession,
    *,
    user: User,
    file_bytes: bytes,
    filename: str,
    version_label: str,
    content_type: str | None,
) -> Resume:
    """Store a PDF in Postgres and record metadata.

    If this is the user's first resume, it auto-activates (is_active=true).
    """
    _validate_pdf(file_bytes, content_type, filename)

    # Check if this is the user's first resume.
    existing_count = await session.scalar(
        select(func.count()).select_from(Resume).where(Resume.user_id == user.id)
    )
    is_first = (existing_count or 0) == 0

    resume = Resume(
        user_id=user.id,
        version_label=version_label,
        pdf_data=file_bytes,
        is_active=is_first,
    )
    session.add(resume)
    await session.flush()

    await log_activity(
        session,
        user_id=user.id,
        action="resume_uploaded",
        entity_type="resume",
        entity_id=resume.id,
        metadata={
            "version_label": version_label,
            "is_active": is_first,
            "filename": filename,
        },
    )
    await session.commit()
    await session.refresh(resume)
    return resume


# ---------------------------------------------------------------------------
# List / get
# ---------------------------------------------------------------------------

async def list_resumes(session: AsyncSession, *, user: User) -> list[tuple[Resume, float, float]]:
    """List all of the user's resumes with computed readiness scores.

    Returns a list of (resume, keyword_coverage_pct, readiness_score) tuples.
    """
    resumes = (
        await session.scalars(
            select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
        )
    ).all()

    # Single has_active check for the whole list (any resume is_active).
    has_active = any(r.is_active for r in resumes)

    result: list[tuple[Resume, float, float]] = []
    for r in resumes:
        total, present = await _keyword_counts(session, r.id)
        coverage, score, _ = _compute_readiness(
            keyword_total=total, keyword_present=present, has_active_resume=has_active
        )
        result.append((r, coverage, score))
    return result


async def get_resume(session: AsyncSession, *, user: User, resume_id: uuid.UUID) -> Resume:
    return await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)


# ---------------------------------------------------------------------------
# Activate / delete
# ---------------------------------------------------------------------------

async def activate_resume(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID
) -> Resume:
    """Set a resume as the user's active one. Unsets any previously active resume.

    Uses a single UPDATE statement to flip all the user's other resumes to
    is_active=false, then sets the target to true — in one transaction.
    """
    resume = await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)

    # Unset all the user's other active resumes.
    await session.execute(
        update(Resume)
        .where(Resume.user_id == user.id, Resume.is_active == True, Resume.id != resume_id)  # noqa: E712
        .values(is_active=False)
    )
    # Set the target active.
    resume.is_active = True

    await log_activity(
        session,
        user_id=user.id,
        action="resume_activated",
        entity_type="resume",
        entity_id=resume.id,
        metadata={"version_label": resume.version_label},
    )
    await session.commit()
    await session.refresh(resume)
    return resume


async def delete_resume(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID
) -> None:
    """Delete a resume. If the deleted resume was active, auto-activates the
    most recent remaining one (if any)."""
    resume = await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    was_active = resume.is_active

    await session.delete(resume)
    await session.commit()

    # If we just deleted the active resume, auto-activate the most recent remaining.
    if was_active:
        most_recent = await session.scalar(
            select(Resume)
            .where(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        if most_recent is not None:
            most_recent.is_active = True
            await session.commit()


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

async def list_keywords(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID
) -> list[ResumeKeyword]:
    await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    rows = (
        await session.scalars(
            select(ResumeKeyword)
            .where(ResumeKeyword.resume_id == resume_id)
            .order_by(ResumeKeyword.created_at.asc())
        )
    ).all()
    return list(rows)


async def add_keyword(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID, body: KeywordCreate
) -> ResumeKeyword:
    resume = await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    # Idempotency: if the keyword already exists, return the existing row.
    existing = await session.scalar(
        select(ResumeKeyword).where(
            ResumeKeyword.resume_id == resume_id,
            ResumeKeyword.keyword == body.keyword,
        )
    )
    if existing is not None:
        return existing

    kw = ResumeKeyword(
        resume_id=resume_id,
        keyword=body.keyword,
        is_present=False,
    )
    session.add(kw)
    await session.commit()
    await session.refresh(kw)
    return kw


async def update_keyword(
    session: AsyncSession,
    *,
    user: User,
    resume_id: uuid.UUID,
    keyword_id: uuid.UUID,
    body: KeywordUpdate,
) -> ResumeKeyword:
    await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    kw = await session.scalar(
        select(ResumeKeyword).where(
            ResumeKeyword.id == keyword_id, ResumeKeyword.resume_id == resume_id
        )
    )
    if kw is None:
        raise KeywordNotFound(f"keyword not found: {keyword_id}")
    kw.is_present = body.is_present
    await session.commit()
    await session.refresh(kw)
    return kw


async def delete_keyword(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID, keyword_id: uuid.UUID
) -> None:
    await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    kw = await session.scalar(
        select(ResumeKeyword).where(
            ResumeKeyword.id == keyword_id, ResumeKeyword.resume_id == resume_id
        )
    )
    if kw is None:
        raise KeywordNotFound(f"keyword not found: {keyword_id}")
    await session.delete(kw)
    await session.commit()


# ---------------------------------------------------------------------------
# Resume ↔ company mapping
# ---------------------------------------------------------------------------

async def map_company(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID, body: MapCompanyRequest
) -> ResumeCompanyMap:
    """Associate a resume with a tracked company (user_company)."""
    resume = await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)

    # Verify the user_company belongs to the user.
    from app.models.company import UserCompany
    uc = await session.scalar(
        select(UserCompany).where(
            UserCompany.id == body.user_company_id, UserCompany.user_id == user.id
        )
    )
    if uc is None:
        raise UserCompanyNotOwnedError(
            f"user_company not found or not owned: {body.user_company_id}"
        )

    # Idempotent: if the mapping already exists, update notes + return.
    existing = await session.scalar(
        select(ResumeCompanyMap).where(
            ResumeCompanyMap.user_company_id == body.user_company_id,
            ResumeCompanyMap.resume_id == resume_id,
        )
    )
    if existing is not None:
        if body.notes is not None:
            existing.notes = body.notes
        await session.commit()
        await session.refresh(existing)
        return existing

    mapping = ResumeCompanyMap(
        user_company_id=body.user_company_id,
        resume_id=resume_id,
        notes=body.notes,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

async def get_readiness(
    session: AsyncSession, *, user: User, resume_id: uuid.UUID
) -> dict:
    """Return the readiness breakdown for a resume."""
    resume = await _get_resume_owned_by(session, resume_id=resume_id, user_id=user.id)
    total, present = await _keyword_counts(session, resume_id)
    has_active = await _user_has_active_resume(session, user.id)
    coverage, score, _ = _compute_readiness(
        keyword_total=total, keyword_present=present, has_active_resume=has_active
    )
    return {
        "keyword_coverage_pct": coverage,
        "has_active_resume": has_active,
        "readiness_score": score,
        "formula": READINESS_FORMULA,
        "keyword_total": total,
        "keyword_present": present,
    }
