"""Pydantic v2 schemas for the dashboard + analytics endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

class UpcomingDeadline(BaseModel):
    user_company_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    deadline: datetime
    application_status: str


class ActivityEntry(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    metadata: dict[str, Any] | None
    created_at: datetime


class DsaSolvedOverTimePoint(BaseModel):
    date: date  # calendar date (not datetime) for chart x-axis
    count: int


class TopicDistributionPoint(BaseModel):
    tag: str
    solved: int
    total: int


class CompanyReadinessPoint(BaseModel):
    user_company_id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    checklist_progress_pct: float


class DashboardCharts(BaseModel):
    dsa_solved_over_time: list[DsaSolvedOverTimePoint]
    topic_distribution: list[TopicDistributionPoint]
    company_readiness: list[CompanyReadinessPoint]


class DashboardSummary(BaseModel):
    """Response for GET /api/v1/dashboard/summary.

    Weighting (documented per Phase A open decision #5, confirmed in Phase 2):
      overall_progress = dsa_completion_pct * 0.5
                       + resume_readiness_score * 0.3
                       + checklist_completion_pct * 0.2
    """
    overall_progress: float
    dsa_completion_pct: float
    resume_readiness_score: float
    checklist_completion_pct: float
    active_companies_count: int
    upcoming_deadlines: list[UpcomingDeadline]
    recent_activity: list[ActivityEntry]
    charts: DashboardCharts


# ---------------------------------------------------------------------------
# Analytics — daily streak
# ---------------------------------------------------------------------------

class StreakResponse(BaseModel):
    """Current consecutive-day streak based on activity_log.

    A day "counts" if there is ≥1 activity_log entry with created_at on
    that calendar date. The streak counts backwards from today (or the
    most recent active day) and breaks on the first missed day.
    """
    current_streak: int
    longest_streak: int
    last_active_date: date | None
    today_active: bool


# ---------------------------------------------------------------------------
# Analytics — weekly productivity
# ---------------------------------------------------------------------------

class WeeklyProductivityPoint(BaseModel):
    iso_week: str  # e.g. "2026-W27"
    activity_count: int


class WeeklyProductivityResponse(BaseModel):
    weeks: list[WeeklyProductivityPoint]
    total_activities: int


# ---------------------------------------------------------------------------
# Analytics — merged timeline
# ---------------------------------------------------------------------------

class TimelineEntry(BaseModel):
    """A single merged-timeline event.

    Merges DSA completions (dsa_solved), checklist milestones
    (checklist_item_completed), and application status changes
    (company_status_changed) into one chronological feed.
    """
    timestamp: datetime
    event_type: str  # "dsa_solved" | "checklist_item_completed" | "company_status_changed"
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    metadata: dict[str, Any] | None


class TimelineResponse(BaseModel):
    entries: list[TimelineEntry]
    total: int
    limit: int
    offset: int
