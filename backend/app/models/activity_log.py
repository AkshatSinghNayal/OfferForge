"""Activity log model.

entity_id is intentionally NOT a foreign key — it is polymorphic. The
referenced entity may be deleted (cascade deletes the source row, but we
keep the activity entry for history). Display context is carried in
metadata JSONB so the feed can render without re-querying the source row.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ActivityLog(Base, TimestampMixin):
    """Append-only activity feed for a user."""

    __tablename__ = "activity_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    __table_args__ = (
        # Recent-activity feed query: WHERE user_id = ? ORDER BY created_at DESC LIMIT 10.
        Index("ix_activity_user_created", "user_id", "created_at"),
        Index("ix_activity_user_entity", "user_id", "entity_type"),
    )
