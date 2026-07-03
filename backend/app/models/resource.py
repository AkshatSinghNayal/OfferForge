"""Resource model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


RESOURCE_CATEGORIES: tuple[str, ...] = (
    "Career Portal",
    "Referral",
    "Coding Sheet",
    "Interview Prep",
    "YouTube",
    "Notes",
    "Article",
)


class Resource(Base, TimestampMixin):
    """A user-curated bookmark. Optional company link."""

    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_resources_user_category", "user_id", "category"),
        Index("ix_resources_user_company", "user_id", "company_id"),
        Index("ix_resources_user_created", "user_id", "created_at"),
    )
