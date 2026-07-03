"""Dashboard + analytics router.

All endpoints protected by get_current_user. All computations are at read
time — no stored aggregates.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummary,
    StreakResponse,
    TimelineResponse,
    WeeklyProductivityResponse,
)
from app.services import dashboard_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Full dashboard summary: weighted progress, KPIs, deadlines, recent
    activity, and chart-ready data.

    Weighting: overall_progress = dsa_completion_pct * 0.5
             + resume_readiness_score * 0.3 + checklist_completion_pct * 0.2
    """
    return await dashboard_service.get_summary(session, user=current_user)


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Daily streak from activity_log. Current + longest consecutive-day
    streak. Breaks on the first missed day."""
    return await dashboard_service.get_streak(session, user=current_user)


@router.get("/weekly-productivity", response_model=WeeklyProductivityResponse)
async def get_weekly_productivity(
    weeks: int = Query(default=12, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Activity count grouped by ISO week (last N weeks)."""
    return await dashboard_service.get_weekly_productivity(
        session, user=current_user, weeks=weeks
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Merged chronological timeline: DSA completions + checklist milestones
    + application status changes. Sorted newest-first."""
    return await dashboard_service.get_timeline(
        session, user=current_user, limit=limit, offset=offset
    )
