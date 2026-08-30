"""Reconcile job-match storage when revision 0006 was stamped without its table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-30

This migration is intentionally idempotent. Some existing deployments report
revision 0006 even though resume_job_match_analyses is absent. A new revision
forces Alembic to revisit that expected schema without damaging installations
where 0006 was applied correctly.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "resume_job_match_analyses"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("job_title", sa.String(length=160), nullable=True),
            sa.Column("company_name", sa.String(length=160), nullable=True),
            sa.Column("job_description", sa.Text(), nullable=False),
            sa.Column("overall_score", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.String(length=16), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("model_name", sa.String(length=120), nullable=False),
            sa.Column("prompt_version", sa.String(length=32), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_indexes: set[str] = set()
    else:
        # Refresh the inspector after checking the pre-existing table.
        existing_indexes = {
            index["name"] for index in inspector.get_indexes(TABLE_NAME) if index.get("name")
        }

    if "ix_resume_job_match_user_created" not in existing_indexes:
        op.create_index(
            "ix_resume_job_match_user_created", TABLE_NAME, ["user_id", "created_at"]
        )
    if "ix_resume_job_match_resume_created" not in existing_indexes:
        op.create_index(
            "ix_resume_job_match_resume_created", TABLE_NAME, ["resume_id", "created_at"]
        )

    # Trigger names are scoped per table. Add it only if this table does not
    # already have one, preserving correctly-applied 0006 installations.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgname = 'set_updated_at'
                  AND tgrelid = '{TABLE_NAME}'::regclass
                  AND NOT tgisinternal
            ) THEN
                CREATE TRIGGER set_updated_at
                BEFORE UPDATE ON {TABLE_NAME}
                FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Revision 0006 expects this table to exist. Reverting this reconciliation
    # marker must therefore preserve the repaired 0006 schema.
    pass
