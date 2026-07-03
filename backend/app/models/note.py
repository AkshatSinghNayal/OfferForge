"""Note model."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


NOTE_TYPES: tuple[str, ...] = (
    "Interview Note",
    "Revision Schedule",
    "Concept",
    "HR Answer",
    "Personal",
)


class Note(Base, TimestampMixin):
    """A markdown note. Attaches to at most one of {company, dsa_problem}.

    XOR enforced via CHECK constraint: (company_id IS NULL OR dsa_problem_id IS NULL).
    A note with both null is allowed (a free-floating personal note).
    """

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    dsa_problem_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dsa_problems.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "company_id IS NULL OR dsa_problem_id IS NULL",
            name="ck_notes_attach_xor",
        ),
        CheckConstraint(f"type IN {NOTE_TYPES!r}", name="ck_notes_type"),
        Index("ix_notes_user_type", "user_id", "type"),
        Index("ix_notes_user_company", "user_id", "company_id"),
        Index("ix_notes_user_problem", "user_id", "dsa_problem_id"),
        Index("ix_notes_user_created", "user_id", "created_at"),
    )
