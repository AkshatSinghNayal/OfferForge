"""Pydantic v2 schemas for the companies + checklist routers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.company import APPLICATION_STATUSES, COMPANY_CLUSTERS


Cluster = Literal["FAANG", "Product-based", "Service-based", "FinTech", "Startups"]
ApplicationStatus = Literal[
    "Not Started",
    "Researching",
    "Applied",
    "OA Received",
    "Interview Scheduled",
    "Offer Received",
    "Rejected",
]


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class CompanyPublic(BaseModel):
    """The canonical company shape returned by every endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    cluster: Cluster
    hiring_process: str | None
    oa_pattern: str | None
    frequent_dsa_topics: list[str] = Field(default_factory=list)
    core_cs_subjects: list[str] = Field(default_factory=list)
    resume_requirements: str | None
    interview_experiences: list[Any] = Field(default_factory=list)
    is_custom: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CompanyCreate(BaseModel):
    """Request body for POST /companies. Always creates a custom company
    (is_custom=true, created_by=current_user)."""

    name: str = Field(min_length=1, max_length=160)
    cluster: Cluster
    hiring_process: str | None = Field(default=None, max_length=10000)
    oa_pattern: str | None = Field(default=None, max_length=10000)
    frequent_dsa_topics: list[str] = Field(default_factory=list, max_length=30)
    core_cs_subjects: list[str] = Field(default_factory=list, max_length=30)
    resume_requirements: str | None = Field(default=None, max_length=10000)
    interview_experiences: list[Any] = Field(default_factory=list, max_length=50)


class CompanyUpdate(BaseModel):
    """Request body for PATCH /companies/{id}. Only fields present are applied.
    Only the owner of a custom company can patch it."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    cluster: Cluster | None = None
    hiring_process: str | None = Field(default=None, max_length=10000)
    oa_pattern: str | None = Field(default=None, max_length=10000)
    frequent_dsa_topics: list[str] | None = Field(default=None, max_length=30)
    core_cs_subjects: list[str] | None = Field(default=None, max_length=30)
    resume_requirements: str | None = Field(default=None, max_length=10000)
    interview_experiences: list[Any] | None = Field(default=None, max_length=50)


class CompanyList(BaseModel):
    """Paginated list response."""

    items: list[CompanyPublic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Company detail (with user_state when the user is tracking it)
# ---------------------------------------------------------------------------

class UserState(BaseModel):
    """Per-user state attached to a company when the user is tracking it."""

    user_company_id: uuid.UUID
    application_status: ApplicationStatus
    deadline: datetime | None
    checklist_progress_pct: float
    mapped_resume_ids: list[uuid.UUID] = Field(default_factory=list)


class CompanyDetail(CompanyPublic):
    """Company + the current user's tracking state (if any)."""

    user_state: UserState | None = None


# ---------------------------------------------------------------------------
# Tracked companies (user_company join)
# ---------------------------------------------------------------------------

class TrackRequest(BaseModel):
    """Body for POST /companies/{id}/track."""

    application_status: ApplicationStatus = "Not Started"
    deadline: datetime | None = None


class TrackUpdateRequest(BaseModel):
    """Body for PATCH /companies/{id}/track."""

    application_status: ApplicationStatus | None = None
    deadline: datetime | None = None
    notes_summary: str | None = Field(default=None, max_length=10000)


class TrackedCompany(BaseModel):
    """A company the user is tracking, with tracking metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID  # user_company.id
    company_id: uuid.UUID
    company_name: str
    cluster: Cluster
    application_status: ApplicationStatus
    deadline: datetime | None
    notes_summary: str | None
    checklist_progress_pct: float
    created_at: datetime
    updated_at: datetime


class TrackedCompanyList(BaseModel):
    items: list[TrackedCompany]
    total: int
    limit: int
    offset: int


class TrackResponse(BaseModel):
    """Response for POST /companies/{id}/track — includes seeded checklist."""

    user_company_id: uuid.UUID
    company_id: uuid.UUID
    application_status: ApplicationStatus
    deadline: datetime | None
    checklist_items: list["ChecklistItemPublic"]
    checklist_progress_pct: float


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------

class ChecklistItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_company_id: uuid.UUID
    item_key: str
    label: str
    is_done: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChecklistResponse(BaseModel):
    """List of checklist items + computed progress %."""

    items: list[ChecklistItemPublic]
    progress_pct: float


class ChecklistToggleRequest(BaseModel):
    is_done: bool


class ChecklistBulkUpdate(BaseModel):
    """Body for PATCH /checklist/{user_company_id}/bulk."""

    updates: list[dict]  # [{ item_id: uuid, is_done: bool }, ...]


# Resolve forward ref — TrackResponse references ChecklistItemPublic.
TrackResponse.model_rebuild()
