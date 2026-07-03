"""Pydantic v2 schemas for the DSA router."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.dsa import (
    DSA_DIFFICULTIES,
    DSA_PLATFORMS,
    DSA_REVISION_STATUSES,
    DSA_STATUSES,
)


# Re-export the allowed-value tuples as Literal types for request validation.
Platform = Literal["LeetCode", "GFG", "Codeforces"]
Difficulty = Literal["Easy", "Medium", "Hard"]
Status = Literal[
    "Not Started", "In Progress", "Solved", "Skipped", "Marked for Revision"
]
RevisionStatus = Literal["None", "Due", "Done"]


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagPublic(BaseModel):
    """A DSA tag, plus the number of the current user's problems using it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    problem_count: int = 0


# ---------------------------------------------------------------------------
# Problem
# ---------------------------------------------------------------------------

class ProblemPublic(BaseModel):
    """A DSA problem with its tags. This is the canonical response shape."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    platform: Platform
    external_url: str
    difficulty: Difficulty
    status: Status
    revision_status: RevisionStatus
    completed_at: datetime | None
    notes: str | None
    tags: list[TagPublic] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProblemCreate(BaseModel):
    """Request body for POST /dsa/problems.

    `tag_names` is a list of strings; the service upserts them into dsa_tags
    (case-insensitive) and rebuilds the dsa_problem_tags rows.
    """

    title: str = Field(min_length=1, max_length=255)
    platform: Platform
    external_url: str = Field(min_length=1, max_length=2048)
    difficulty: Difficulty
    status: Status = "Not Started"
    revision_status: RevisionStatus = "None"
    tag_names: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=10000)


class ProblemUpdate(BaseModel):
    """Request body for PATCH /dsa/problems/{id}.

    All fields optional — only the fields present in the request body are
    applied. `tag_names` (when present) replaces the full tag set.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    platform: Platform | None = None
    external_url: str | None = Field(default=None, min_length=1, max_length=2048)
    difficulty: Difficulty | None = None
    status: Status | None = None
    revision_status: RevisionStatus | None = None
    tag_names: list[str] | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=10000)


# ---------------------------------------------------------------------------
# List + pagination envelope
# ---------------------------------------------------------------------------

class ProblemList(BaseModel):
    """Paginated list response. `total` is the count before pagination."""

    items: list[ProblemPublic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TopicStat(BaseModel):
    """Per-topic stat row. `pct` is solved/total * 100, rounded to 1 decimal."""

    tag: str
    total: int
    solved: int
    pct: float


class DifficultyStat(BaseModel):
    """Per-difficulty stat row."""

    difficulty: Difficulty
    total: int
    solved: int
    pct: float


class DsaStats(BaseModel):
    """Response shape for GET /dsa/stats."""

    topic_wise: list[TopicStat]
    difficulty_wise: list[DifficultyStat]
    overall_total: int
    overall_solved: int
    overall_pct: float
