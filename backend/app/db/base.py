"""Database base + async session factory.

Why Postgres over Mongo (per Phase A architecture decision):
  Placement Preparation Tracker is fundamentally relational. A user tracks
  companies, each tracked company owns a 15-item checklist, each user owns
  DSA problems tagged via a many-to-many join, resumes map to companies,
  notes attach to either a company or a DSA problem (XOR). The dashboard
  alone needs ~6 joins + GROUP BY across dsa_problems / dsa_problem_tags /
  user_company / checklist_items / activity_log / resumes to compute the
  weighted progress, solved-over-time series, topic distribution, and
  per-company readiness. Postgres gives us:
    - real FKs with ON DELETE CASCADE / SET NULL (data integrity Mongo
      emulates only via application code),
    - partial unique indexes (exactly one active resume per user) and
      case-insensitive unique indexes (case-insensitive tag names) that
      cannot leak through concurrent inserts,
    - ARRAY + JSONB columns for the places where semi-structured data is
      genuinely better (frequent_dsa_topics[], interview_experiences JSONB),
    - a clean path to pg_trgm / FTS later for the /search endpoint without
      a service swap,
    - transactional multi-statement updates (seed 15 checklist items in the
      same txn as the user_company row, rotate refresh tokens atomically).
  Mongo would force us to re-implement joins in application code, lose
  transactional guarantees across collections, and pay denormalisation costs
  for data that is genuinely relational. The schema is not "documents with
  optional nested fields" — it is a graph of typed entities with constraints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by all models and Alembic autogenerate."""

    # DeclarativeBase stores metadata here; Alembic's env.py imports this
    # class to enumerate target tables for autogenerate.
    pass


class TimestampMixin:
    """Adds created_at / updated_at to every model.

    Both columns are NOT NULL with a server-side default of now().
    updated_at is also bumped by a BEFORE UPDATE trigger installed in the
    initial Alembic migration (see alembic/versions/0001_initial_schema.py).
    The trigger fires regardless of whether the row is updated via the ORM
    or via raw SQL, which is more robust than relying on SQLAlchemy's
    `onupdate=func.now()` (ORM-only).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
