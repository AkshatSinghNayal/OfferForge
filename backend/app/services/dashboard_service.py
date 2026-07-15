"""Dashboard + analytics business logic.

All computations are at read time — no stored aggregates. The queries are
designed to be single-pass where possible (one round-trip per metric).

Weighting (Phase A open decision #5, confirmed in Phase 2):
  overall_progress = dsa_completion_pct * 0.5
                   + resume_readiness_score * 0.3
                   + checklist_completion_pct * 0.2

Streak logic:
  A day "counts" if there is ≥1 activity_log entry with created_at on that
  calendar date. The current streak counts backwards from today: if today
  has activity, start at today; else start at yesterday (grace for "today
  not over yet"). Walk backwards day-by-day until a day has no activity —
  that's the break point. The streak is the count of consecutive active
  days including the start day.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.company import ChecklistItem, Company, UserCompany
from app.models.dsa import DsaProblem, DsaProblemTag, DsaTag
from app.models.resume import Resume, ResumeKeyword
from app.models.user import User
from app.schemas.dashboard import (
    ActivityEntry,
    CompanyReadinessPoint,
    DashboardCharts,
    DashboardSummary,
    DsaSolvedOverTimePoint,
    StreakResponse,
    TimelineEntry,
    TimelineResponse,
    TopicDistributionPoint,
    UpcomingDeadline,
    WeeklyProductivityPoint,
    WeeklyProductivityResponse,
)


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

async def get_summary(session: AsyncSession, *, user: User) -> DashboardSummary:
    """Compute the full dashboard summary in as few round-trips as possible.

    Each metric is computed independently so a slow one doesn't block the
    others, and so we can later cache them individually if needed.
    """
    # --- DSA completion % ---
    dsa_total = await session.scalar(
        select(func.count()).select_from(DsaProblem).where(DsaProblem.user_id == user.id)
    )
    dsa_solved = await session.scalar(
        select(func.count())
        .select_from(DsaProblem)
        .where(DsaProblem.user_id == user.id, DsaProblem.status == "Solved")
    )
    dsa_total = dsa_total or 0
    dsa_solved = dsa_solved or 0
    dsa_completion_pct = round(dsa_solved / dsa_total * 100, 1) if dsa_total else 0.0

    # --- Resume readiness score ---
    # readiness_score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4
    # (formula from Phase 5, reused here for the dashboard)
    active_resume_count = await session.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.user_id == user.id, Resume.is_active == True)  # noqa: E712
    )
    has_active_resume = (active_resume_count or 0) > 0

    # Keyword coverage across ALL of the user's resumes (aggregate).
    kw_total = await session.scalar(
        select(func.count())
        .select_from(ResumeKeyword)
        .join(Resume, Resume.id == ResumeKeyword.resume_id)
        .where(Resume.user_id == user.id)
    )
    kw_present = await session.scalar(
        select(func.count())
        .select_from(ResumeKeyword)
        .join(Resume, Resume.id == ResumeKeyword.resume_id)
        .where(Resume.user_id == user.id, ResumeKeyword.is_present == True)  # noqa: E712
    )
    kw_total = kw_total or 0
    kw_present = kw_present or 0
    keyword_coverage_pct = round(kw_present / kw_total * 100, 1) if kw_total else 0.0
    # readiness_score = keyword_coverage_pct * 0.6 + has_active_resume * 0.4
    resume_readiness_score = round(
        keyword_coverage_pct * 0.6 + (40.0 if has_active_resume else 0.0), 1
    )

    # --- Checklist completion % (across all tracked companies) ---
    ci_total = await session.scalar(
        select(func.count())
        .select_from(ChecklistItem)
        .join(UserCompany, UserCompany.id == ChecklistItem.user_company_id)
        .where(UserCompany.user_id == user.id)
    )
    ci_done = await session.scalar(
        select(func.count())
        .select_from(ChecklistItem)
        .join(UserCompany, UserCompany.id == ChecklistItem.user_company_id)
        .where(UserCompany.user_id == user.id, ChecklistItem.is_done == True)  # noqa: E712
    )
    ci_total = ci_total or 0
    ci_done = ci_done or 0
    checklist_completion_pct = round(ci_done / ci_total * 100, 1) if ci_total else 0.0

    # --- Overall progress (weighted) ---
    # overall_progress = dsa_completion_pct * 0.5
    #                  + resume_readiness_score * 0.3
    #                  + checklist_completion_pct * 0.2
    overall_progress = round(
        dsa_completion_pct * 0.5
        + resume_readiness_score * 0.3
        + checklist_completion_pct * 0.2,
        1,
    )

    # --- Active companies count ---
    # "Active" = tracked AND application_status NOT IN (Not Started, Offer Received, Rejected)
    terminal_statuses = ("Not Started", "Offer Received", "Rejected")
    active_companies_count = await session.scalar(
        select(func.count())
        .select_from(UserCompany)
        .where(
            UserCompany.user_id == user.id,
            ~UserCompany.application_status.in_(terminal_statuses),
        )
    )
    active_companies_count = active_companies_count or 0

    # --- Upcoming deadlines (next 5, future dates only, sorted ascending) ---
    now = datetime.now(timezone.utc)
    deadline_rows = (
        await session.execute(
            select(UserCompany, Company)
            .join(Company, Company.id == UserCompany.company_id)
            .where(
                UserCompany.user_id == user.id,
                UserCompany.deadline.is_not(None),
                UserCompany.deadline > now,
                ~UserCompany.application_status.in_(("Offer Received", "Rejected")),
            )
            .order_by(UserCompany.deadline.asc())
            .limit(5)
        )
    ).all()
    upcoming_deadlines = [
        UpcomingDeadline(
            user_company_id=uc.id,
            company_id=company.id,
            company_name=company.name,
            deadline=uc.deadline,
            application_status=uc.application_status,
        )
        for uc, company in deadline_rows
    ]

    # --- Recent activity (last 10) ---
    recent_rows = (
        await session.scalars(
            select(ActivityLog)
            .where(ActivityLog.user_id == user.id)
            .order_by(ActivityLog.created_at.desc())
            .limit(10)
        )
    ).all()
    recent_activity = [
        ActivityEntry(
            id=r.id,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            metadata=r.metadata_,
            created_at=r.created_at,
        )
        for r in recent_rows
    ]

    # --- Charts ---
    charts = await _build_charts(session, user=user, dsa_solved=dsa_solved)

    return DashboardSummary(
        overall_progress=overall_progress,
        dsa_completion_pct=dsa_completion_pct,
        resume_readiness_score=resume_readiness_score,
        checklist_completion_pct=checklist_completion_pct,
        active_companies_count=active_companies_count,
        upcoming_deadlines=upcoming_deadlines,
        recent_activity=recent_activity,
        charts=charts,
    )


async def _build_charts(
    session: AsyncSession, *, user: User, dsa_solved: int
    ) -> DashboardCharts:
        """Build the three chart datasets.

        1. dsa_solved_over_time: grouped by calendar date of completed_at
           (NOT created_at — this is the critical distinction per Phase 7 brief).
           All-time completions so the cumulative curve grows monotonically.
        2. topic_distribution: per-tag solved/total across the user's problems.
        3. company_readiness: per-tracked-company checklist completion %.
        """
        # --- 1. DSA solved over time (by completed_at date, all time) ---
        # Group by DATE(completed_at) — cast timestamptz to date.
        solved_rows = (
            await session.execute(
                select(
                    func.date(DsaProblem.completed_at).label("d"),
                    func.count().label("c"),
                )
                .where(
                    DsaProblem.user_id == user.id,
                    DsaProblem.completed_at.is_not(None),
                )
                .group_by(func.date(DsaProblem.completed_at))
                .order_by(func.date(DsaProblem.completed_at).asc())
            )
        ).all()
    dsa_solved_over_time = [
        DsaSolvedOverTimePoint(date=row[0], count=row[1])
        for row in solved_rows
        if row[0] is not None
    ]

    # --- 2. Topic distribution (per-tag solved/total) ---
    topic_rows = (
        await session.execute(
            select(
                DsaTag.name,
                func.count(DsaProblem.id).label("total"),
                func.count(DsaProblem.id).filter(
                    DsaProblem.status == "Solved"
                ).label("solved"),
            )
            .select_from(DsaTag)
            .join(DsaProblemTag, DsaProblemTag.dsa_tag_id == DsaTag.id)
            .join(DsaProblem, DsaProblem.id == DsaProblemTag.dsa_problem_id)
            .where(DsaProblem.user_id == user.id)
            .group_by(DsaTag.id, DsaTag.name)
            .order_by(DsaTag.name)
        )
    ).all()
    topic_distribution = [
        TopicDistributionPoint(tag=row[0], solved=row[2] or 0, total=row[1] or 0)
        for row in topic_rows
    ]

    # --- 3. Company readiness (per-tracked-company checklist %) ---
    company_rows = (
        await session.execute(
            select(UserCompany, Company)
            .join(Company, Company.id == UserCompany.company_id)
            .options()  # no selectinload — we compute counts via subqueries
            .where(UserCompany.user_id == user.id)
            .order_by(UserCompany.created_at.desc())
        )
    ).all()

    company_readiness: list[CompanyReadinessPoint] = []
    for uc, company in company_rows:
        # Per-company checklist counts.
        ci_total = await session.scalar(
            select(func.count())
            .select_from(ChecklistItem)
            .where(ChecklistItem.user_company_id == uc.id)
        )
        ci_done = await session.scalar(
            select(func.count())
            .select_from(ChecklistItem)
            .where(ChecklistItem.user_company_id == uc.id, ChecklistItem.is_done == True)  # noqa: E712
        )
        ci_total = ci_total or 0
        ci_done = ci_done or 0
        pct = round(ci_done / ci_total * 100, 1) if ci_total else 0.0
        company_readiness.append(
            CompanyReadinessPoint(
                user_company_id=uc.id,
                company_id=company.id,
                company_name=company.name,
                checklist_progress_pct=pct,
            )
        )

    return DashboardCharts(
        dsa_solved_over_time=dsa_solved_over_time,
        topic_distribution=topic_distribution,
        company_readiness=company_readiness,
    )


# ---------------------------------------------------------------------------
# Analytics — daily streak
# ---------------------------------------------------------------------------

async def get_streak(session: AsyncSession, *, user: User) -> StreakResponse:
    """Compute the current + longest consecutive-day streak from activity_log.

    Logic:
      1. Get the set of distinct calendar dates that have ≥1 activity.
      2. Current streak: start from today (or yesterday if today has no
         activity yet — grace for "today not over"). Walk backwards
         day-by-day. The streak is the count of consecutive days in the
         active set, including the start day. Breaks on the first missing
         day.
      3. Longest streak: sort the dates, walk forward, track the longest
         run of consecutive days.
    """
    # Fetch distinct activity dates.
    date_rows = (
        await session.execute(
            select(func.date(ActivityLog.created_at).label("d"))
            .where(ActivityLog.user_id == user.id)
            .group_by(func.date(ActivityLog.created_at))
            .order_by(func.date(ActivityLog.created_at).asc())
        )
    ).all()
    active_dates: set[date] = {row[0] for row in date_rows if row[0] is not None}

    if not active_dates:
        return StreakResponse(
            current_streak=0, longest_streak=0, last_active_date=None, today_active=False
        )

    today = datetime.now(timezone.utc).date()
    today_active = today in active_dates

    # --- Current streak ---
    # Start from today if active, else yesterday (grace).
    if today_active:
        cursor = today
    elif (today - timedelta(days=1)) in active_dates:
        cursor = today - timedelta(days=1)
    else:
        cursor = None

    current_streak = 0
    if cursor is not None:
        while cursor in active_dates:
            current_streak += 1
            cursor -= timedelta(days=1)

    # --- Longest streak ---
    sorted_dates = sorted(active_dates)
    longest_streak = 0
    run = 0
    prev: date | None = None
    for d in sorted_dates:
        if prev is not None and d == prev + timedelta(days=1):
            run += 1
        else:
            run = 1
        longest_streak = max(longest_streak, run)
        prev = d

    last_active_date = max(active_dates)

    return StreakResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        last_active_date=last_active_date,
        today_active=today_active,
    )


# ---------------------------------------------------------------------------
# Analytics — weekly productivity
# ---------------------------------------------------------------------------

async def get_weekly_productivity(
    session: AsyncSession, *, user: User, weeks: int = 12
) -> WeeklyProductivityResponse:
    """Activity count grouped by ISO week (last N weeks)."""
    weeks = max(1, min(weeks, 52))

    # Postgres: to_char(created_at, 'IYYY-WIW') gives ISO year-week with "W" prefix
    # (e.g. "2026-W27"). Using 'IYYY-IW' gives "2026-27" (no W) which is less readable.
    rows = (
        await session.execute(
            select(
                func.to_char(ActivityLog.created_at, 'IYYY-"W"IW').label("iso_week"),
                func.count().label("c"),
            )
            .where(ActivityLog.user_id == user.id)
            .group_by("iso_week")
            .order_by("iso_week")
        )
    ).all()

    points = [
        WeeklyProductivityPoint(iso_week=row[0], activity_count=row[1])
        for row in rows
        if row[0] is not None
    ]
    # Keep only the last N weeks.
    points = points[-weeks:]
    total = sum(p.activity_count for p in points)
    return WeeklyProductivityResponse(weeks=points, total_activities=total)


# ---------------------------------------------------------------------------
# Analytics — merged timeline
# ---------------------------------------------------------------------------

async def get_timeline(
    session: AsyncSession, *, user: User, limit: int = 50, offset: int = 0
) -> TimelineResponse:
    """Merged chronological timeline of DSA completions + checklist milestones
    + application status changes.

    Pulls from activity_log (which already records all three event types)
    and filters to the relevant actions. Sorts newest-first.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    timeline_actions = (
        "dsa_solved",
        "checklist_item_completed",
        "company_status_changed",
    )

    where_clause = and_(
        ActivityLog.user_id == user.id,
        ActivityLog.action.in_(timeline_actions),
    )

    total = await session.scalar(
        select(func.count()).select_from(ActivityLog).where(where_clause)
    )
    total = total or 0

    rows = (
        await session.scalars(
            select(ActivityLog)
            .where(where_clause)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    entries = [
        TimelineEntry(
            timestamp=r.created_at,
            event_type=r.action,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            metadata=r.metadata_,
        )
        for r in rows
    ]

    return TimelineResponse(entries=entries, total=total, limit=limit, offset=offset)
