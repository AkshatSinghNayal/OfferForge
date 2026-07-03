"""Resume, resume_keywords, resume_company_map models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, LargeBinary, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    """A resume version uploaded by a user.

    pdf_data stores the raw PDF bytes in Postgres (BYTEA). Exactly one
    resume per user can be is_active=true, enforced by a partial unique index.
    """

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(String(80), nullable=False)
    pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    cloudinary_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    cloudinary_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    keywords: Mapped[list[ResumeKeyword]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    company_mappings: Mapped[list[ResumeCompanyMap]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_resumes_user_active", "user_id", "is_active"),
        # Partial unique index: at most one active resume per user. Enforced
        # at the DB level so concurrent requests cannot create two actives.
        Index(
            "uq_resumes_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
    )


class ResumeKeyword(Base, TimestampMixin):
    """An ATS keyword tracked against a resume version, with is_present flag."""

    __tablename__ = "resume_keywords"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    keyword: Mapped[str] = mapped_column(String(120), nullable=False)
    is_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped[Resume] = relationship(back_populates="keywords")

    __table_args__ = (
        Index("uq_resume_keyword", "resume_id", "keyword", unique=True),
        Index("ix_resume_keyword_present", "resume_id", "is_present"),
    )


class ResumeCompanyMap(Base, TimestampMixin):
    """Records which resume version was used for a tracked company."""

    __tablename__ = "resume_company_map"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_company.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_company: Mapped["UserCompany"] = relationship(  # type: ignore[name-defined]
        back_populates="resume_mappings"
    )
    resume: Mapped[Resume] = relationship(back_populates="company_mappings")

    __table_args__ = (
        Index(
            "uq_resume_company_map",
            "user_company_id",
            "resume_id",
            unique=True,
        ),
        Index("ix_resume_company_map_uc", "user_company_id"),
    )
