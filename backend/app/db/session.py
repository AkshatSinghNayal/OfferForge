"""Async SQLAlchemy session + engine factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base

# Build connect_args: if DB_SCHEMA is set, tell asyncpg to set search_path
# so all DDL/DML targets that schema instead of "public".
# If DB_SSLMODE is set and not already present in DATABASE_URL, set ssl mode.
_connect_args: dict = {}
if settings.DB_SCHEMA:
    _connect_args["server_settings"] = {"search_path": settings.DB_SCHEMA}
if settings.DB_SSLMODE and "sslmode=" not in settings.DATABASE_URL and "ssl=" not in settings.DATABASE_URL:
    ssl_val: str | bool = settings.DB_SSLMODE
    if settings.DB_SSLMODE.lower() in ("true", "1"):
        ssl_val = True
    elif settings.DB_SSLMODE.lower() in ("false", "0"):
        ssl_val = False
    _connect_args["ssl"] = ssl_val

# Module-level async engine. Created once at import time; reused for the
# lifetime of the process. Pool parameters are conservative defaults —
# tune when we measure real load.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "dev",  # log SQL in dev only
    pool_pre_ping=True,  # recover from idle-in-transaction / DB restarts
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

# Session factory. Routers depend on `AsyncSession` via FastAPI's `Depends`.
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a per-request async session.

    Usage in routers:
        async def handler(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with async_session_factory() as session:
        yield session


__all__ = ["Base", "engine", "async_session_factory", "get_async_session"]
