"""Pydantic v2 schemas for the resumes router."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


JobRequirementCategory = Literal[
    "skills", "experience", "education", "responsibilities", "domain", "other"
]
JobRequirementImportance = Literal["required", "preferred"]
JobRequirementStatus = Literal["matched", "partial", "missing"]


class JobMatchRequest(BaseModel):
    job_description: str = Field(min_length=100, max_length=50000)
    job_title: str | None = Field(default=None, max_length=160)
    company_name: str | None = Field(default=None, max_length=160)

    @field_validator("job_description")
    @classmethod
    def _clean_job_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 100:
            raise ValueError("job description must contain at least 100 characters")
        return value

    @field_validator("job_title", "company_name")
    @classmethod
    def _clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class JobRequirementAssessment(BaseModel):
    requirement: str
    category: JobRequirementCategory
    importance: JobRequirementImportance
    status: JobRequirementStatus
    evidence: list[str]
    gap: str | None = None
    recommendation: str | None = None


class JobMatchCategoryScore(BaseModel):
    category: JobRequirementCategory
    label: str
    score: int
    matched: int
    partial: int
    missing: int


class JobMatchAnalysisPublic(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_title: str | None
    company_name: str | None
    overall_score: int = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    summary: str
    breakdown: list[JobMatchCategoryScore]
    requirements: list[JobRequirementAssessment]
    strengths: list[str]
    recommendations: list[str]
    created_at: datetime


class JobMatchAnalysisList(BaseModel):
    items: list[JobMatchAnalysisPublic]
