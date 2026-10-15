import uuid
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Stage = Literal['Saved', 'Applied', 'Assessment', 'Interview', 'Offer', 'Closed']

class ApplicationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=160)
    stage: Stage = 'Saved'
    deadline: date | None = None
    next_action: str = Field(default='', max_length=300)
    notes: str = Field(default='', max_length=10000)
    is_pinned: bool = False
    resume_id: uuid.UUID | None = None

class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    company_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: str | None = Field(default=None, min_length=1, max_length=160)
    stage: Stage | None = None
    deadline: date | None = None
    next_action: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=10000)
    is_pinned: bool | None = None
    resume_id: uuid.UUID | None = None

    @model_validator(mode='after')
    def required_values(self):
        for name in self.model_fields_set - {'deadline', 'resume_id'}:
            if getattr(self, name) is None:
                raise ValueError(f'{name} cannot be null')
        return self

class ApplicationPublic(ApplicationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    history: list[dict]
    created_at: datetime
    updated_at: datetime

class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=300)
    details: str = Field(default='', max_length=10000)
    due_date: date | None = None
    minutes: int = Field(default=25, ge=5, le=240)

class TaskUpdate(BaseModel):
    is_done: bool

class TaskPublic(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_done: bool
    source_analysis_id: uuid.UUID | None
    source_index: int | None
    source_label: str | None
    created_at: datetime

class AnalysisTaskRequest(BaseModel):
    requirement_index: int = Field(ge=0)
