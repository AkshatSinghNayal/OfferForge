"""Pydantic v2 schemas for resources + notes + search."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.note import NOTE_TYPES
from app.models.resource import RESOURCE_CATEGORIES


ResourceCategory = Literal[
    "Career Portal", "Referral", "Coding Sheet",
    "Interview Prep", "YouTube", "Notes", "Article",
]
NoteType = Literal[
    "Interview Note", "Revision Schedule", "Concept", "HR Answer", "Personal",
]


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------

class ResourcePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID | None
    title: str
    url: str
    category: ResourceCategory
    description: str | None
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    category: ResourceCategory
    company_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=10000)


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    category: ResourceCategory | None = None
    company_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=10000)


class ResourceList(BaseModel):
    items: list[ResourcePublic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------

class NotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    content: str
    type: NoteType
    company_id: uuid.UUID | None
    dsa_problem_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=50000)
    type: NoteType
    company_id: uuid.UUID | None = None
    dsa_problem_id: uuid.UUID | None = None


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    type: NoteType | None = None
    company_id: uuid.UUID | None = None
    dsa_problem_id: uuid.UUID | None = None


class NoteList(BaseModel):
    items: list[NotePublic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchCompanyHit(BaseModel):
    id: uuid.UUID
    name: str
    cluster: str


class SearchDsaHit(BaseModel):
    id: uuid.UUID
    title: str
    difficulty: str
    status: str


class SearchNoteHit(BaseModel):
    id: uuid.UUID
    title: str
    type: str


class SearchResourceHit(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    category: str


class SearchResponse(BaseModel):
    companies: list[SearchCompanyHit]
    dsa_problems: list[SearchDsaHit]
    notes: list[SearchNoteHit]
    resources: list[SearchResourceHit]
    total: int
    q: str
    limit: int
