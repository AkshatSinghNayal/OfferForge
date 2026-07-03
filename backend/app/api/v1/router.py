"""Aggregates all v1 routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    checklist,
    companies,
    dashboard,
    dsa,
    health,
    notes,
    resources,
    resumes,
    search,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dsa.router, prefix="/dsa", tags=["dsa"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(checklist.router, prefix="/checklist", tags=["checklist"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# All routers are now wired. Backend is feature-complete through Phase 7.
