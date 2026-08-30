"""FastAPI application factory.

Phase 2 scope: CORS + /api/v1/health + /api/v1/auth/* (signup, login,
refresh, logout, me, Google OAuth, password reset). Feature routers
(dsa, companies, etc.) are added in Phase 3+.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _run_database_migrations() -> None:
    """Upgrade Postgres using this deployment's bundled Alembic revisions."""
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Bring the schema to head before accepting any API requests."""
    if settings.AUTO_MIGRATE_ON_STARTUP:
        logger.info("Running database migrations from application startup")
        # Alembic's async env owns its own event loop, so run it in a worker
        # thread rather than nesting asyncio.run() in Uvicorn's loop.
        await asyncio.to_thread(_run_database_migrations)
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application. Called by uvicorn in main.py."""
    app = FastAPI(
        title="OfferForge API",
        version="0.2.0",
        lifespan=lifespan,
        description=(
            "Backend API for OfferForge. "
            "Phase 2: scaffold + schema + /health + auth (signup/login/refresh/"
            "logout/me/Google-OAuth/password-reset)."
        ),
    )

    # CORS — allow ONLY the frontend origin. allow_credentials is required so
    # the httpOnly refresh_token cookie is sent on cross-origin requests
    # between the Vercel frontend and the Render backend. This satisfies the
    # Phase 2 requirement: "CORS configured to allow only FRONTEND_URL,
    # credentials enabled."
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # = [FRONTEND_URL]
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Compress response payloads above 1000 bytes
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(api_router)

    return app


# uvicorn entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
app = create_app()
