"""Integration checks against an explicitly supplied disposable PostgreSQL DB.

Run Alembic first, then set WORKSPACE_TEST_DATABASE_URL to that database.
No production data is read or deleted; each test removes only its own users.
"""
import os
import unittest
import uuid
from datetime import date
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import create_app
from app.db.session import get_async_session
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.resume import Resume, ResumeJobMatchAnalysis
from app.models.workspace import Application

DSN = os.environ.get('WORKSPACE_TEST_DATABASE_URL')

@unittest.skipUnless(DSN, 'Requires a disposable WORKSPACE_TEST_DATABASE_URL')
class WorkspaceIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(DSN, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user_id, self.other_id = uuid.uuid4(), uuid.uuid4()
        self.resume_id, self.analysis_id = uuid.uuid4(), uuid.uuid4()
        async with self.sessions() as session:
            session.add_all([User(id=id, email=f'{id}@example.com', full_name='Test User', hashed_password='test-hash') for id in (self.user_id, self.other_id)])
            await session.flush()
            session.add(Resume(id=self.resume_id, user_id=self.user_id, version_label='Test resume', pdf_data=b'%PDF-test', cloudinary_url='test', is_active=False))
            await session.flush()
            session.add(ResumeJobMatchAnalysis(id=self.analysis_id, resume_id=self.resume_id, user_id=self.user_id, job_title='Engineer', company_name='Example', job_description='Synthetic job', overall_score=50, confidence='low', summary='Synthetic analysis', model_name='test', prompt_version='test', result={'requirements': [{'requirement': 'Docker', 'status': 'missing', 'recommendation': 'Containerize a small project.'}, {'requirement': 'Python', 'status': 'matched'}]}))
            await session.commit()
        app = create_app()
        async def session_override():
            async with self.sessions() as session:
                yield session
        app.dependency_overrides[get_async_session] = session_override
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url='http://test', headers={'Authorization': f'Bearer {create_access_token(self.user_id)}'})
        self.foreign_headers = {'Authorization': f'Bearer {create_access_token(self.other_id)}'}

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.sessions() as session:
            await session.execute(delete(User).where(User.id.in_([self.user_id, self.other_id])))
            await session.commit()
        await self.engine.dispose()

    async def make_application(self, **overrides):
        r = await self.client.post('/api/v1/workspace/applications', json={'company_name': 'Example', 'role': 'Engineer', 'resume_id': str(self.resume_id), **overrides})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    async def test_multiple_roles_pin_history_and_nullable_date(self):
        one = await self.make_application(deadline='2026-11-01')
        two = await self.make_application(role='Intern')
        self.assertNotEqual(one['id'], two['id'])
        url = f"/api/v1/workspace/applications/{one['id']}"
        r = await self.client.patch(url, json={'stage': 'Interview', 'is_pinned': True, 'deadline': None})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([e['stage'] for e in r.json()['history']], ['Saved', 'Interview'])
        self.assertIsNone(r.json()['deadline'])
        listed = (await self.client.get('/api/v1/workspace/applications')).json()
        self.assertEqual(listed[0]['id'], one['id'])
        async with self.sessions() as session:
            persisted = await session.get(Application, uuid.UUID(one['id']))
            self.assertTrue(persisted.is_pinned)
            self.assertEqual(persisted.stage, 'Interview')

    async def test_application_and_resume_ownership(self):
        app = await self.make_application()
        url = f"/api/v1/workspace/applications/{app['id']}"
        self.assertEqual((await self.client.patch(url, json={'stage': 'Offer'}, headers=self.foreign_headers)).status_code, 404)
        self.assertEqual((await self.client.delete(url, headers=self.foreign_headers)).status_code, 404)
        self.assertEqual((await self.client.get('/api/v1/workspace/applications', headers=self.foreign_headers)).json(), [])
        self.assertEqual((await self.client.post('/api/v1/workspace/applications', json={'company_name': 'Other', 'role': 'Intern', 'resume_id': str(self.resume_id)}, headers=self.foreign_headers)).status_code, 404)

    async def test_blank_fields_invalid_stage_and_null_rejected(self):
        self.assertEqual((await self.client.post('/api/v1/workspace/applications', json={'company_name': '   ', 'role': 'Engineer'})).status_code, 422)
        app = await self.make_application()
        for body in ({'stage': 'fake'}, {'role': None}, {'is_pinned': None}):
            self.assertEqual((await self.client.patch(f"/api/v1/workspace/applications/{app['id']}", json=body)).status_code, 422)

    async def test_analysis_task_idempotency_and_ownership(self):
        url = f'/api/v1/workspace/analyses/{self.analysis_id}/tasks'
        one = await self.client.post(url, json={'requirement_index': 0})
        two = await self.client.post(url, json={'requirement_index': 0})
        self.assertEqual(one.status_code, 200, one.text)
        self.assertEqual(one.json()['id'], two.json()['id'])
        self.assertEqual(one.json()['details'], 'Containerize a small project.')
        self.assertEqual((await self.client.post(url, json={'requirement_index': 0}, headers=self.foreign_headers)).status_code, 404)
        for index in (-1, 1, 50):
            self.assertEqual((await self.client.post(url, json={'requirement_index': index})).status_code, 422)

    async def test_task_completion_undo_delete_and_ownership(self):
        r = await self.client.post('/api/v1/workspace/tasks', json={'title': 'Practice SQL', 'minutes': 30, 'due_date': date.today().isoformat()})
        self.assertEqual(r.status_code, 201, r.text)
        url = '/api/v1/workspace/tasks/' + r.json()['id']
        self.assertTrue((await self.client.patch(url, json={'is_done': True})).json()['is_done'])
        self.assertFalse((await self.client.patch(url, json={'is_done': False})).json()['is_done'])
        self.assertEqual((await self.client.patch(url, json={'is_done': True}, headers=self.foreign_headers)).status_code, 404)
        self.assertEqual((await self.client.delete(url, headers=self.foreign_headers)).status_code, 404)
        self.assertEqual((await self.client.delete(url)).status_code, 204)
        self.assertEqual((await self.client.get('/api/v1/workspace/tasks')).json(), [])

    async def test_authentication_required(self):
        r = await self.client.get('/api/v1/workspace/tasks', headers={'Authorization': ''})
        self.assertEqual(r.status_code, 401)

    async def test_real_profile_and_password_changes(self):
        async with self.sessions() as session:
            user = await session.get(User, self.user_id)
            user.hashed_password = await hash_password('old-test-password')
            await session.commit()
        r = await self.client.patch('/api/v1/auth/profile', json={'full_name': 'Updated Name'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['full_name'], 'Updated Name')
        self.assertNotIn('hashed_password', r.json())
        r = await self.client.post('/api/v1/auth/password', json={'current_password': 'incorrect', 'new_password': 'new-test-password'})
        self.assertEqual(r.status_code, 400)
        r = await self.client.post('/api/v1/auth/password', json={'current_password': 'old-test-password', 'new_password': 'new-test-password'})
        self.assertEqual(r.status_code, 200, r.text)
        async with self.sessions() as session:
            user = await session.get(User, self.user_id)
            self.assertTrue(await verify_password('new-test-password', user.hashed_password))
