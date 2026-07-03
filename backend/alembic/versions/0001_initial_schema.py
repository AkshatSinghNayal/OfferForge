"""Initial schema — all 14 tables from Phase A ER diagram.

Creates the set_updated_at() trigger function once and applies it to every
table so updated_at is bumped on every UPDATE regardless of ORM vs raw SQL.

Revision ID: 0001
Revises:
Create Date: 2026-07-02 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that should get the updated_at trigger. Order doesn't matter here
# because the trigger is applied after all CREATE TABLE statements.
ALL_TABLES = [
    "users",
    "refresh_tokens",
    "companies",
    "user_company",
    "checklist_items",
    "dsa_problems",
    "dsa_tags",
    "dsa_problem_tags",
    "resumes",
    "resume_keywords",
    "resume_company_map",
    "resources",
    "notes",
    "activity_log",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Reusable trigger function: bumps updated_at on any UPDATE.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ------------------------------------------------------------------
    # 2. Tables (in FK dependency order)
    # ------------------------------------------------------------------

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("google_sub", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
        sa.CheckConstraint(
            "hashed_password IS NOT NULL OR google_sub IS NOT NULL",
            name="ck_users_has_auth_method",
        ),
    )

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    # companies
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("cluster", sa.String(40), nullable=False),
        sa.Column("hiring_process", sa.Text(), nullable=True),
        sa.Column("oa_pattern", sa.Text(), nullable=True),
        sa.Column("frequent_dsa_topics", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("core_cs_subjects", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("resume_requirements", sa.Text(), nullable=True),
        sa.Column("interview_experiences", postgresql.JSONB(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "cluster IN ('FAANG', 'Product-based', 'Service-based', 'FinTech', 'Startups')",
            name="ck_companies_cluster",
        ),
    )
    op.create_index("ix_companies_cluster", "companies", ["cluster"])
    op.create_index(
        "ix_companies_seeded_name",
        "companies",
        ["name"],
        postgresql_where=sa.text("is_custom = FALSE"),
    )
    op.create_index("ix_companies_created_by", "companies", ["created_by"])

    # user_company
    op.create_table(
        "user_company",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_status", sa.String(40), nullable=False, server_default=sa.text("'Not Started'")),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "application_status IN ('Not Started', 'Researching', 'Applied', 'OA Received', 'Interview Scheduled', 'Offer Received', 'Rejected')",
            name="ck_user_company_application_status",
        ),
    )
    op.create_index("uq_user_company", "user_company", ["user_id", "company_id"], unique=True)
    op.create_index("ix_user_company_deadline", "user_company", ["user_id", "deadline"])
    op.create_index("ix_user_company_status", "user_company", ["user_id", "application_status"])

    # checklist_items
    op.create_table(
        "checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_key", sa.String(60), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_company_id"], ["user_company.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "uq_checklist_user_company_item",
        "checklist_items",
        ["user_company_id", "item_key"],
        unique=True,
    )
    op.create_index("ix_checklist_user_company", "checklist_items", ["user_company_id"])

    # dsa_problems
    op.create_table(
        "dsa_problems",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("external_url", sa.String(2048), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'Not Started'")),
        sa.Column("revision_status", sa.String(20), nullable=False, server_default=sa.text("'None'")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("platform IN ('LeetCode', 'GFG', 'Codeforces')", name="ck_dsa_platform"),
        sa.CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="ck_dsa_difficulty"),
        sa.CheckConstraint(
            "status IN ('Not Started', 'In Progress', 'Solved', 'Skipped', 'Marked for Revision')",
            name="ck_dsa_status",
        ),
        sa.CheckConstraint("revision_status IN ('None', 'Due', 'Done')", name="ck_dsa_revision_status"),
    )
    op.create_index("ix_dsa_user_status", "dsa_problems", ["user_id", "status"])
    op.create_index("ix_dsa_user_difficulty", "dsa_problems", ["user_id", "difficulty"])
    op.create_index("ix_dsa_user_completed", "dsa_problems", ["user_id", "completed_at"])
    op.create_index("ix_dsa_user_platform", "dsa_problems", ["user_id", "platform"])
    op.create_index("ix_dsa_user_created", "dsa_problems", ["user_id", "created_at"])

    # dsa_tags
    op.create_table(
        "dsa_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Functional unique index — case-insensitive tag name.
    op.create_index(
        "uq_dsa_tags_name_lower",
        "dsa_tags",
        [sa.text("lower(name)")],
        unique=True,
    )

    # dsa_problem_tags
    op.create_table(
        "dsa_problem_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dsa_problem_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dsa_tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["dsa_problem_id"], ["dsa_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dsa_tag_id"], ["dsa_tags.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "uq_dsa_problem_tag",
        "dsa_problem_tags",
        ["dsa_problem_id", "dsa_tag_id"],
        unique=True,
    )
    op.create_index("ix_dsa_problem_tag_tag", "dsa_problem_tags", ["dsa_tag_id"])

    # resumes
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_label", sa.String(80), nullable=False),
        sa.Column("cloudinary_url", sa.String(2048), nullable=False),
        sa.Column("cloudinary_public_id", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_resumes_user_active", "resumes", ["user_id", "is_active"])
    # Partial unique index: at most one active resume per user.
    op.create_index(
        "uq_resumes_user_active",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # resume_keywords
    op.create_table(
        "resume_keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword", sa.String(120), nullable=False),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_resume_keyword", "resume_keywords", ["resume_id", "keyword"], unique=True)
    op.create_index("ix_resume_keyword_present", "resume_keywords", ["resume_id", "is_present"])

    # resume_company_map
    op.create_table(
        "resume_company_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_company_id"], ["user_company.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "uq_resume_company_map",
        "resume_company_map",
        ["user_company_id", "resume_id"],
        unique=True,
    )
    op.create_index("ix_resume_company_map_uc", "resume_company_map", ["user_company_id"])

    # resources
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "category IN ('Career Portal', 'Referral', 'Coding Sheet', 'Interview Prep', 'YouTube', 'Notes', 'Article')",
            name="ck_resources_category",
        ),
    )
    op.create_index("ix_resources_user_category", "resources", ["user_id", "category"])
    op.create_index("ix_resources_user_company", "resources", ["user_id", "company_id"])
    op.create_index("ix_resources_user_created", "resources", ["user_id", "created_at"])

    # notes
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dsa_problem_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dsa_problem_id"], ["dsa_problems.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "company_id IS NULL OR dsa_problem_id IS NULL",
            name="ck_notes_attach_xor",
        ),
        sa.CheckConstraint(
            "type IN ('Interview Note', 'Revision Schedule', 'Concept', 'HR Answer', 'Personal')",
            name="ck_notes_type",
        ),
    )
    op.create_index("ix_notes_user_type", "notes", ["user_id", "type"])
    op.create_index("ix_notes_user_company", "notes", ["user_id", "company_id"])
    op.create_index("ix_notes_user_problem", "notes", ["user_id", "dsa_problem_id"])
    op.create_index("ix_notes_user_created", "notes", ["user_id", "created_at"])

    # activity_log
    op.create_table(
        "activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_activity_user_created", "activity_log", ["user_id", "created_at"])
    op.create_index("ix_activity_user_entity", "activity_log", ["user_id", "entity_type"])

    # ------------------------------------------------------------------
    # 3. Apply updated_at trigger to every table.
    # ------------------------------------------------------------------
    for table in ALL_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER set_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    # Drop triggers first (cannot drop a table with a trigger referencing a
    # function we're about to drop, though PG would actually cascade — being
    # explicit is safer).
    for table in ALL_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS set_updated_at ON {table};")

    # Drop tables in reverse FK dependency order.
    for table in reversed(ALL_TABLES):
        op.drop_table(table)

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
