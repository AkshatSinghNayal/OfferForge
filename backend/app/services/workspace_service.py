"""Owned workspace records and idempotent conversion of analysis gaps to tasks."""
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.workspace import Application, PreparationTask
from app.models.resume import Resume, ResumeJobMatchAnalysis
from app.services.activity_log import log_activity

async def owned(session, model, record_id, user_id):
    row = await session.scalar(select(model).where(model.id == record_id, model.user_id == user_id))
    if row is None:
        raise HTTPException(404, 'Record not found')
    return row

async def validate_resume(session, resume_id, user_id):
    if resume_id:
        await owned(session, Resume, resume_id, user_id)

async def save_application(session, user, body, application_id=None):
    changes = body.model_dump(exclude_unset=True)
    if 'resume_id' in changes:
        await validate_resume(session, changes['resume_id'], user.id)
    now = datetime.now(timezone.utc)
    if application_id:
        row = await owned(session, Application, application_id, user.id)
        if 'stage' in changes and changes['stage'] != row.stage:
            row.history = [*row.history, {'stage': changes['stage'], 'at': now.isoformat()}]
        for key, value in changes.items():
            setattr(row, key, value)
        row.updated_at = now
    else:
        row = Application(user_id=user.id, **body.model_dump())
        row.history = [{'stage': row.stage, 'at': now.isoformat()}]
        session.add(row)
    await session.flush()
    await log_activity(session, user_id=user.id, action='application_updated' if application_id else 'application_created', entity_type='application', entity_id=row.id, metadata={'company_name': row.company_name, 'role': row.role})
    await session.commit()
    await session.refresh(row)
    return row

async def task_from_analysis(session, user, analysis_id, index):
    analysis = await owned(session, ResumeJobMatchAnalysis, analysis_id, user.id)
    requirements = analysis.result.get('requirements', [])
    if index >= len(requirements):
        raise HTTPException(422, 'Requirement not found in this analysis')
    requirement = requirements[index]
    if requirement.get('status') == 'matched':
        raise HTTPException(422, 'This requirement is already matched')
    query = select(PreparationTask).where(PreparationTask.user_id == user.id, PreparationTask.source_analysis_id == analysis.id, PreparationTask.source_index == index)
    existing = await session.scalar(query)
    if existing:
        return existing
    row = PreparationTask(
        user_id=user.id,
        title=f"Prepare: {requirement['requirement']}"[:300],
        details=(requirement.get('recommendation') or requirement.get('gap') or 'Review this requirement and document relevant experience.')[:10000],
        source_analysis_id=analysis.id, source_index=index,
        source_label=' · '.join(filter(None, [analysis.company_name, analysis.job_title]))[:330] or 'Resume analysis',
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(query)
        if existing:
            return existing
        raise
    await session.refresh(row)
    return row
