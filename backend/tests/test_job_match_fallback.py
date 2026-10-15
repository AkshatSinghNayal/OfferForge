"""Provider failures are simulated; these tests never use a real API key."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai.errors import ClientError, ServerError
from app.schemas.resumes import JobMatchRequest
from app.services.job_match_service import (
    GeminiAnalysisError, GeminiNotConfiguredError, GeminiRateLimitError,
    _extract_with_gemini, _model_candidates,
)


def model(name):
    return SimpleNamespace(name=f"models/{name}", supported_actions=["generateContent"])


class Catalog:
    def __aiter__(self):
        async def items():
            for name in ('gemini-new-flash', 'gemini-new-flash-lite'):
                yield model(name)
        return items()


def error(code, message):
    cls = ServerError if code >= 500 else ClientError
    return cls(code, {'error': {'code': code, 'message': message}})


VALID = SimpleNamespace(text='''{"confidence":"high","summary":"Evidence found","requirements":[{"requirement":"Python","category":"skills","importance":"required","status":"matched","evidence":["Python"]}]}''')


class FallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = SimpleNamespace(models=SimpleNamespace(
            list=AsyncMock(side_effect=lambda: Catalog()),
            generate_content=AsyncMock(),
        ))
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=self.client)
        manager.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock(return_value=SimpleNamespace(aio=manager))
        for patcher in (
            patch('app.services.job_match_service.genai.Client', factory),
            patch('app.services.job_match_service.settings.GEMINI_API_KEY', 'test-key'),
            patch('app.services.job_match_service.settings.GEMINI_BACKUP_API_KEY', ''),
            patch('app.services.job_match_service.settings.GEMINI_MODEL', 'retired-model'),
            patch('app.services.job_match_service.settings.GEMINI_FALLBACK_MODEL', ''),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def run_analysis(self):
        return await _extract_with_gemini(pdf_data=b'%PDF-test', request=JobMatchRequest(job_description='Python software developer. ' * 8))

    async def test_discovery_replaces_retired_model(self):
        self.client.models.generate_content.return_value = VALID
        _, used = await self.run_analysis()
        self.assertEqual(used, 'gemini-new-flash')

    async def test_quota_missing_and_denied_model_fall_back(self):
        for code in (429, 404, 403):
            with self.subTest(code=code):
                self.client.models.generate_content.side_effect = [error(code, 'Unavailable'), VALID]
                _, used = await self.run_analysis()
                self.assertEqual(used, 'gemini-new-flash-lite')

    async def test_transient_error_retries(self):
        self.client.models.generate_content.side_effect = [error(503, 'Unavailable'), VALID]
        _, used = await self.run_analysis()
        self.assertEqual(used, 'gemini-new-flash')

    async def test_invalid_key_uses_backup(self):
        self.client.models.generate_content.side_effect = [error(400, 'API key not valid'), VALID]
        with patch('app.services.job_match_service.settings.GEMINI_BACKUP_API_KEY', 'backup'):
            await self.run_analysis()
        self.assertEqual(self.client.models.list.await_count, 2)

    async def test_invalid_key_is_not_reported_as_pdf_error(self):
        self.client.models.generate_content.side_effect = error(400, 'API key not valid')
        with self.assertRaises(GeminiNotConfiguredError):
            await self.run_analysis()
        self.assertEqual(self.client.models.generate_content.await_count, 1)

    async def test_all_models_exhausted(self):
        self.client.models.generate_content.side_effect = error(429, 'Quota exceeded')
        with self.assertRaises(GeminiRateLimitError):
            await self.run_analysis()

    async def test_schema_fallback_keeps_explicit_json_shape(self):
        self.client.models.generate_content.side_effect = [error(400, 'response_schema unsupported'), VALID]
        await self.run_analysis()
        call = self.client.models.generate_content.call_args.kwargs
        self.assertIsNone(call['config'].response_schema)
        self.assertIn('Return JSON matching this schema', call['contents'][1])

    async def test_empty_requirements_retry(self):
        self.client.models.generate_content.side_effect = [SimpleNamespace(text='{"confidence":"low","summary":"Nothing","requirements":[]}'), VALID]
        extraction, _ = await self.run_analysis()
        self.assertEqual(len(extraction.requirements), 1)

    async def test_discovery_outage_uses_configured_model(self):
        self.client.models.list.side_effect = TimeoutError()
        self.client.models.generate_content.return_value = VALID
        with patch('app.services.job_match_service.settings.GEMINI_MODEL', 'gemini-configured-flash'):
            _, used = await self.run_analysis()
        self.assertEqual(used, 'gemini-configured-flash')

    async def test_model_timeout_uses_next_model(self):
        self.client.models.generate_content.side_effect = [TimeoutError(), VALID]
        _, used = await self.run_analysis()
        self.assertEqual(used, 'gemini-new-flash-lite')

    async def test_discovery_rejects_key_then_uses_backup(self):
        self.client.models.list.side_effect = [error(400, 'API key not valid'), Catalog()]
        self.client.models.generate_content.return_value = VALID
        with patch('app.services.job_match_service.settings.GEMINI_BACKUP_API_KEY', 'backup'):
            await self.run_analysis()
        self.assertEqual(self.client.models.list.await_count, 2)

    async def test_total_deadline_cancels_request(self):
        async def slow(**kwargs):
            await asyncio.sleep(10)
        self.client.models.generate_content.side_effect = slow
        with patch('app.services.job_match_service.settings.GEMINI_TIMEOUT_SECONDS', 0.02):
            with self.assertRaisesRegex(GeminiAnalysisError, 'timed out'):
                await self.run_analysis()

    def test_specialized_models_filtered(self):
        models = [model('gemini-flash-image'), model('gemini-flash-tts'), model('gemini-new-flash')]
        self.assertEqual(_model_candidates(models, []), ['gemini-new-flash'])
