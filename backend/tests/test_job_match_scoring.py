"""Unit tests for deterministic resume-to-job scoring (no Gemini call)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.schemas.resumes import JobMatchRequest
from app.services.job_match_service import (
    GeminiNotConfiguredError,
    GeminiRequirement,
    _compute_scores,
    _extract_with_gemini,
)


def requirement(
    name: str,
    *,
    category: str = "skills",
    importance: str = "required",
    status: str = "matched",
) -> GeminiRequirement:
    return GeminiRequirement(
        requirement=name,
        category=category,
        importance=importance,
        status=status,
        evidence=[name] if status != "missing" else [],
    )


class JobMatchScoringTests(unittest.TestCase):
    def test_all_explicitly_matched_requirements_score_100(self) -> None:
        score, breakdown = _compute_scores([
            requirement("Python"),
            requirement("API design", category="responsibilities"),
        ])
        self.assertEqual(score, 100)
        self.assertEqual(sum(item["matched"] for item in breakdown), 2)

    def test_partial_match_receives_half_credit(self) -> None:
        score, _ = _compute_scores([
            requirement("Python", status="matched"),
            requirement("FastAPI", status="partial"),
        ])
        self.assertEqual(score, 75)

    def test_required_gap_outweighs_preferred_match(self) -> None:
        score, _ = _compute_scores([
            requirement("Five years experience", category="experience", status="missing"),
            requirement("Redis", importance="preferred", status="matched"),
        ])
        self.assertLess(score, 50)

    def test_breakdown_counts_each_status(self) -> None:
        _, breakdown = _compute_scores([
            requirement("Python", status="matched"),
            requirement("SQL", status="partial"),
            requirement("Kubernetes", status="missing"),
        ])
        self.assertEqual(
            {key: breakdown[0][key] for key in ("matched", "partial", "missing")},
            {"matched": 1, "partial": 1, "missing": 1},
        )

    def test_job_description_is_trimmed_and_validated(self) -> None:
        request = JobMatchRequest(job_description=f"  {'x' * 100}  ")
        self.assertEqual(len(request.job_description), 100)
        with self.assertRaises(ValidationError):
            JobMatchRequest(job_description="too short")


class JobMatchConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_fails_before_provider_call(self) -> None:
        request = JobMatchRequest(job_description="x" * 100)
        with patch("app.services.job_match_service.settings.GEMINI_API_KEY", ""):
            with self.assertRaises(GeminiNotConfiguredError):
                await _extract_with_gemini(pdf_data=b"%PDF-1.4", request=request)


if __name__ == "__main__":
    unittest.main()
