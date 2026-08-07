"""Ensure google_sub column exists on users table (for Neon Auth compatibility).

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-07

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255);")


def downgrade() -> None:
    pass
