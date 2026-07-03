"""Search service — ILIKE across companies, dsa_problems, notes, resources.

MVP note: this uses Postgres ILIKE with `%query%` patterns. For a small
dataset this is fine. Post-MVP, this should move to pg_trgm (trigram
indexing) for fuzzy matching, or Postgres full-text search (tsvector +
tsquery) for ranked relevance. The response shape is designed to stay
the same across both upgrades — only the underlying query changes.

CRITICAL: every query uses SQLAlchemy's bound-parameter mechanism
(.ilike() with a Python string is compiled to a parameterized LIKE
clause). No raw string interpolation, no f-strings in SQL, no
text() with .format(). This prevents SQL injection even if the query
contains single quotes or semicolons.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.dsa import DsaProblem
from app.models.note import Note
from app.models.resource import Resource
from app.models.user import User
from app.schemas.misc import (
    SearchCompanyHit,
    SearchDsaHit,
    SearchNoteHit,
    SearchResourceHit,
    SearchResponse,
)


async def search(
    session: AsyncSession, *, user: User, q: str, limit: int = 10
) -> SearchResponse:
    """Search across companies, dsa_problems, notes, resources.

    - companies: searched by name (includes seeded global companies +
      all users' custom companies — companies are not user-private).
    - dsa_problems: searched by title, scoped to the current user.
    - notes: searched by title OR content, scoped to the current user.
    - resources: searched by title OR url, scoped to the current user.

    All queries use SQLAlchemy parameterized ILIKE — no string
    interpolation. The `f"%{q}%"` pattern is passed as a VALUE to
    .ilike(), which SQLAlchemy compiles to a bound parameter, so
    special characters in q (quotes, semicolons, %) cannot break out
    of the query.
    """
    limit = max(1, min(limit, 50))
    pattern = f"%{q}%"

    # --- Companies (global — includes seeded + all users' custom) ---
    company_rows = (
        await session.scalars(
            select(Company)
            .where(Company.name.ilike(pattern))
            .order_by(Company.name.asc())
            .limit(limit)
        )
    ).all()
    companies = [
        SearchCompanyHit(id=c.id, name=c.name, cluster=c.cluster)
        for c in company_rows
    ]

    # --- DSA problems (user-scoped) ---
    dsa_rows = (
        await session.scalars(
            select(DsaProblem)
            .where(
                DsaProblem.user_id == user.id,
                DsaProblem.title.ilike(pattern),
            )
            .order_by(DsaProblem.created_at.desc())
            .limit(limit)
        )
    ).all()
    dsa_problems = [
        SearchDsaHit(
            id=p.id, title=p.title, difficulty=p.difficulty, status=p.status
        )
        for p in dsa_rows
    ]

    # --- Notes (user-scoped, search title OR content) ---
    note_rows = (
        await session.scalars(
            select(Note)
            .where(
                Note.user_id == user.id,
                or_(
                    Note.title.ilike(pattern),
                    Note.content.ilike(pattern),
                ),
            )
            .order_by(Note.created_at.desc())
            .limit(limit)
        )
    ).all()
    notes = [
        SearchNoteHit(id=n.id, title=n.title, type=n.type)
        for n in note_rows
    ]

    # --- Resources (user-scoped, search title OR url) ---
    resource_rows = (
        await session.scalars(
            select(Resource)
            .where(
                Resource.user_id == user.id,
                or_(
                    Resource.title.ilike(pattern),
                    Resource.url.ilike(pattern),
                ),
            )
            .order_by(Resource.created_at.desc())
            .limit(limit)
        )
    ).all()
    resources = [
        SearchResourceHit(
            id=r.id, title=r.title, url=r.url, category=r.category
        )
        for r in resource_rows
    ]

    total = len(companies) + len(dsa_problems) + len(notes) + len(resources)

    return SearchResponse(
        companies=companies,
        dsa_problems=dsa_problems,
        notes=notes,
        resources=resources,
        total=total,
        q=q,
        limit=limit,
    )
