"""Alembic async env.py.

Reads DATABASE_URL from app.core.config (single source of truth), uses an
async engine, and runs migrations inside an event loop. Target metadata is
imported from app.models so autogenerate sees every model.

To create a new revision (run from backend/):
    alembic revision --autogenerate -m "describe change"
To apply:
    alembic upgrade head
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- Make `app` importable when running `alembic` from backend/ -------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# --- Import app config + all models so metadata is fully populated ----------
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401 — side-effect: register all models on Base.metadata

# --- Alembic config objects -------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the async DSN into alembic's config dict (it has no sqlalchemy.url
# in alembic.ini on purpose — single source of truth in app settings).
# Escape '%' to '%%' so configparser's interpolation doesn't choke on
# percent-encoded query-string characters (e.g. %3D in search_path option).
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline mode — emit SQL to stdout without connecting to the DB."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Online mode — use an async engine."""
    connect_args: dict = {}
    if settings.DB_SCHEMA:
        connect_args["server_settings"] = {"search_path": settings.DB_SCHEMA}

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
