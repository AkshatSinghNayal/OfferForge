import uuid
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.db.session import get_async_session
from app.models.user import User
from app.models.workspace import Application, PreparationTask
from app.schemas.workspace import ApplicationCreate, ApplicationUpdate, ApplicationPublic, TaskCreate, TaskUpdate, TaskPublic, AnalysisTaskRequest
from app.services import workspace_service as service
from app.services.activity_log import log_activity

router = APIRouter()

@router.get('/applications', response_model=list[ApplicationPublic])
async def applications(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return (await session.scalars(select(Application).where(Application.user_id == user.id).order_by(Application.is_pinned.desc(), Application.created_at.desc()))).all()

@router.post('/applications', response_model=ApplicationPublic, status_code=201)
async def create_application(body: ApplicationCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return await service.save_application(session, user, body)

@router.patch('/applications/{application_id}', response_model=ApplicationPublic)
async def update_application(application_id: uuid.UUID, body: ApplicationUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return await service.save_application(session, user, body, application_id)

@router.delete('/applications/{application_id}', status_code=204)
async def delete_application(application_id: uuid.UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    row = await service.owned(session, Application, application_id, user.id)
    await session.delete(row)
    await session.commit()
    return Response(status_code=204)

@router.get('/tasks', response_model=list[TaskPublic])
async def tasks(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return (await session.scalars(select(PreparationTask).where(PreparationTask.user_id == user.id).order_by(PreparationTask.is_done, PreparationTask.due_date.asc().nulls_last(), PreparationTask.created_at.desc()))).all()

@router.post('/tasks', response_model=TaskPublic, status_code=201)
async def create_task(body: TaskCreate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    row = PreparationTask(user_id=user.id, **body.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row

@router.patch('/tasks/{task_id}', response_model=TaskPublic)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    row = await service.owned(session, PreparationTask, task_id, user.id)
    if row.is_done != body.is_done and body.is_done:
        await log_activity(session, user_id=user.id, action='preparation_task_completed', entity_type='task', entity_id=row.id, metadata={'title': row.title})
    row.is_done = body.is_done
    await session.commit()
    await session.refresh(row)
    return row

@router.delete('/tasks/{task_id}', status_code=204)
async def delete_task(task_id: uuid.UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    row = await service.owned(session, PreparationTask, task_id, user.id)
    await session.delete(row)
    await session.commit()
    return Response(status_code=204)

@router.post('/analyses/{analysis_id}/tasks', response_model=TaskPublic)
async def analysis_task(analysis_id: uuid.UUID, body: AnalysisTaskRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return await service.task_from_analysis(session, user, analysis_id, body.requirement_index)
