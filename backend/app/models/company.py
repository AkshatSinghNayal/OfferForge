"""Company, user_company, checklist_items models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


# Single source of truth for the 15 fixed checklist items. Used by the
# service layer to seed checklist_items rows when a user_company is created,
# and exposed here so the seed migration and any future tests can reuse it.
# item_key is the stable identifier (never rename); label is the human text
# (safe to reword via migration if copy changes).
CHECKLIST_ITEMS: list[tuple[str, str]] = [
    ("resume_tailored", "Resume tailored"),
    ("resume_ats_checked", "Resume ATS checked"),
    ("dsa_sheet_completed", "DSA Sheet completed"),
    ("oa_practice_completed", "OA Practice completed"),
    ("aptitude_prepared", "Aptitude prepared"),
    ("dbms_revised", "DBMS revised"),
    ("os_revised", "OS revised"),
    ("cn_revised", "CN revised"),
    ("oop_revised", "OOP revised"),
    ("hr_questions_prepared", "HR Questions prepared"),
    ("projects_revised", "Projects revised"),
    ("applied", "Applied"),
    ("oa_received", "OA Received"),
    ("interview_scheduled", "Interview Scheduled"),
    ("offer_received", "Offer Received"),
]

# Allowed application_status values. Used in CHECK constraints and Pydantic enums.
APPLICATION_STATUSES: tuple[str, ...] = (
    "Not Started",
    "Researching",
    "Applied",
    "OA Received",
    "Interview Scheduled",
    "Offer Received",
    "Rejected",
)

# Allowed cluster values.
COMPANY_CLUSTERS: tuple[str, ...] = (
    "FAANG",
    "Product-based",
    "Service-based",
    "FinTech",
    "Startups",
)


class Company(Base, TimestampMixin):
    """A company the user can track.

    Seeded companies have is_custom=false and created_by=NULL.
    User-added companies have is_custom=true and created_by=<user_id>.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    cluster: Mapped[str] = mapped_column(String(40), nullable=False)
    hiring_process: Mapped[str | None] = mapped_column(Text, nullable=True)
    oa_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequent_dsa_topics: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )
    core_cs_subjects: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )
    resume_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_experiences: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user_companies: Mapped[list[UserCompany]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            f"cluster IN {COMPANY_CLUSTERS!r}",
            name="ck_companies_cluster",
        ),
        # Filter by cluster (left nav). Partial index on seeded companies
        # for the "browse companies" page which shows seeded ones.
        Index("ix_companies_cluster", "cluster"),
        Index(
            "ix_companies_seeded_name",
            "name",
            postgresql_where="is_custom = FALSE",
        ),
        Index("ix_companies_created_by", "created_by"),
    )


class UserCompany(Base, TimestampMixin):
    """A user tracking a company. One row per (user, company)."""

    __tablename__ = "user_company"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="Not Started"
    )
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # `User` and `ResumeCompanyMap` are string-annotated; SQLAlchemy resolves
    # them via the declarative registry at mapper-configure time, so no
    # cross-module imports are needed (avoids circular imports).
    user: Mapped["User"] = relationship()  # type: ignore[name-defined]
    company: Mapped[Company] = relationship(back_populates="user_companies")
    checklist_items: Mapped[list[ChecklistItem]] = relationship(
        back_populates="user_company", cascade="all, delete-orphan"
    )
    resume_mappings: Mapped[list["ResumeCompanyMap"]] = relationship(
        back_populates="user_company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            f"application_status IN {APPLICATION_STATUSES!r}",
            name="ck_user_company_application_status",
        ),
        # One tracking row per (user, company).
        Index("uq_user_company", "user_id", "company_id", unique=True),
        # Upcoming-deadlines query.
        Index("ix_user_company_deadline", "user_id", "deadline"),
        # Active-companies count query.
        Index("ix_user_company_status", "user_id", "application_status"),
    )


class ChecklistItem(Base, TimestampMixin):
    """One of the 15 fixed checklist items for a (user, company) pair.

    Seeded when the parent user_company row is created. is_done + completed_at
    are the only mutable fields. Progress % is computed at read time, never
    stored — see checklist service in a later phase.
    """

    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_company.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user_company: Mapped[UserCompany] = relationship(back_populates="checklist_items")

    __table_args__ = (
        Index(
            "uq_checklist_user_company_item",
            "user_company_id",
            "item_key",
            unique=True,
        ),
        Index("ix_checklist_user_company", "user_company_id"),
    )
