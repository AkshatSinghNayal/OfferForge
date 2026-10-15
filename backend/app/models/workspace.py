"""Persistent application pipeline and personal preparation tasks."""
import uuid
from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class Application(Base, TimestampMixin):
    __tablename__ = 'applications'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    company_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(160))
    stage: Mapped[str] = mapped_column(String(32), default='Saved')
    deadline: Mapped[date | None] = mapped_column(Date)
    next_action: Mapped[str] = mapped_column(String(300), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    resume_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('resumes.id', ondelete='SET NULL'))
    history: Mapped[list] = mapped_column(JSON, default=list)


class PreparationTask(Base, TimestampMixin):
    __tablename__ = 'preparation_tasks'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(300))
    details: Mapped[str] = mapped_column(Text, default='')
    due_date: Mapped[date | None] = mapped_column(Date)
    minutes: Mapped[int] = mapped_column(Integer, default=25)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    source_analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('resume_job_match_analyses.id', ondelete='SET NULL'))
    source_index: Mapped[int | None] = mapped_column(Integer)
    source_label: Mapped[str | None] = mapped_column(String(330))
    __table_args__ = (Index('uq_task_analysis_requirement', 'user_id', 'source_analysis_id', 'source_index', unique=True),)
