"""Activity log helper — reusable across all feature services.

Phase 3 (DSA) writes `dsa_created`, `dsa_solved`, `dsa_status_changed`
actions. Later phases (companies, checklist, resumes, notes, resources)
will write their own actions through this same helper.

Design notes:
  - The activity_log table is append-only. We never UPDATE or DELETE rows
    here (the dashboard reads them later).
  - `metadata` carries display context (problem title, platform, etc.) so
    the activity feed can render without re-querying the source row. This
    matters because the source row may be deleted (cascade) while the
    activity entry should persist for history.
  - `entity_id` is the polymorphic FK-free reference to the source row.
    Nullable in case the action isn't tied to a specific row.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


async def log_activity(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a row to activity_log. Does NOT commit — caller commits.

    Keeping the commit in the caller lets the activity row participate in
    the same transaction as the business operation it describes, so we
    never have a logged activity for a rolled-back change.
    """
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata,
    )
    session.add(entry)


__all__ = ["log_activity"]
