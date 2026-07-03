"""Store PDF bytes in Postgres instead of Cloudinary.

Adds a pdf_data BYTEA column to resumes and makes cloudinary_url /
cloudinary_public_id nullable (kept for schema compatibility but no longer
populated by new uploads).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("pdf_data", sa.LargeBinary(), nullable=True))
    op.alter_column("resumes", "cloudinary_url", nullable=True)
    op.alter_column("resumes", "cloudinary_public_id", nullable=True)


def downgrade() -> None:
    # Restore NOT NULL constraints (rows with NULL will fail — acceptable for a rollback).
    op.alter_column("resumes", "cloudinary_public_id", nullable=False)
    op.alter_column("resumes", "cloudinary_url", nullable=False)
    op.drop_column("resumes", "pdf_data")
