"""DSA problem, tags, and problem-tag join models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


DSA_PLATFORMS: tuple[str, ...] = ("LeetCode", "GFG", "Codeforces")
DSA_DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")
DSA_STATUSES: tuple[str, ...] = (
    "Not Started",
    "In Progress",
    "Solved",
    "Skipped",
    "Marked for Revision",
)
DSA_REVISION_STATUSES: tuple[str, ...] = ("None", "Due", "Done")


class DsaProblem(Base, TimestampMixin):
    """A DSA problem a user is tracking."""

    __tablename__ = "dsa_problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Not Started")
    revision_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="None"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tags: Mapped[list[DsaProblemTag]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(f"platform IN {DSA_PLATFORMS!r}", name="ck_dsa_platform"),
        CheckConstraint(f"difficulty IN {DSA_DIFFICULTIES!r}", name="ck_dsa_difficulty"),
        CheckConstraint(f"status IN {DSA_STATUSES!r}", name="ck_dsa_status"),
        CheckConstraint(
            f"revision_status IN {DSA_REVISION_STATUSES!r}",
            name="ck_dsa_revision_status",
        ),
        Index("ix_dsa_user_status", "user_id", "status"),
        Index("ix_dsa_user_difficulty", "user_id", "difficulty"),
        Index("ix_dsa_user_completed", "user_id", "completed_at"),
        Index("ix_dsa_user_platform", "user_id", "platform"),
        Index("ix_dsa_user_created", "user_id", "created_at"),
    )


class DsaTag(Base, TimestampMixin):
    """A global DSA topic tag. Case-insensitive unique name.

    Two users adding "arrays" reuse the same row. Case-insensitive uniqueness
    is enforced via a functional unique index on lower(name).
    """

    __tablename__ = "dsa_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)

    problems: Mapped[list[DsaProblemTag]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Functional unique index — case-insensitive tag name. Equivalent to
        # CREATE UNIQUE INDEX ... ON dsa_tags (lower(name)).
        Index("uq_dsa_tags_name_lower", text("lower(name)"), unique=True),
    )


class DsaProblemTag(Base, TimestampMixin):
    """Join table: many-to-many between dsa_problems and dsa_tags."""

    __tablename__ = "dsa_problem_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    dsa_problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dsa_problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    dsa_tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dsa_tags.id", ondelete="CASCADE"),
        nullable=False,
    )

    problem: Mapped[DsaProblem] = relationship(back_populates="tags")
    tag: Mapped[DsaTag] = relationship(back_populates="problems")

    __table_args__ = (
        Index(
            "uq_dsa_problem_tag",
            "dsa_problem_id",
            "dsa_tag_id",
            unique=True,
        ),
        Index("ix_dsa_problem_tag_tag", "dsa_tag_id"),
    )
