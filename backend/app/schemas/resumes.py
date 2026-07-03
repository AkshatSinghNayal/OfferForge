"""Pydantic v2 schemas for the resumes router."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumePublic(BaseModel):
    """The canonical resume shape returned by every endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    version_label: str
    cloudinary_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResumeWithScore(ResumePublic):
    """Resume + computed readiness score."""

    keyword_coverage_pct: float
    readiness_score: float


class ResumeList(BaseModel):
    items: list[ResumeWithScore]


class KeywordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    keyword: str
    is_present: bool
    created_at: datetime
    updated_at: datetime


class KeywordCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)


class KeywordUpdate(BaseModel):
    is_present: bool


class ResumeCompanyMapPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_company_id: uuid.UUID
    resume_id: uuid.UUID
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MapCompanyRequest(BaseModel):
    user_company_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=10000)


class ReadinessResponse(BaseModel):
    keyword_coverage_pct: float
    has_active_resume: bool
    readiness_score: float
    formula: str
    keyword_total: int
    keyword_present: int
