"""FastAPI application factory.

Phase 2 scope: CORS + /api/v1/health + /api/v1/auth/* (signup, login,
refresh, logout, me, Google OAuth, password reset). Feature routers
(dsa, companies, etc.) are added in Phase 3+.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GzipMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Build the FastAPI application. Called by uvicorn in main.py."""
    app = FastAPI(
        title="OfferForge API",
        version="0.2.0",
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
    app.add_middleware(GzipMiddleware, minimum_size=1000)

    app.include_router(api_router)

    return app


# uvicorn entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
app = create_app()
