from __future__ import annotations

import unittest

from prototype.heuristics import extract_requirements, generate_with_heuristics
from prototype.models import GenerationRequest


class PrototypeHeuristicTests(unittest.TestCase):
    def test_extract_requirements_returns_multiple_items(self) -> None:
        text = """
        Responsibilities
        - Analyze user feedback and summarize insights.
        - Prepare structured written updates.
        Qualifications
        - Strong written communication skills.
        - Ability to work with spreadsheets.
        """
        requirements = extract_requirements(text, limit=4)
        self.assertGreaterEqual(len(requirements), 3)

    def test_generate_with_heuristics_returns_core_outputs(self) -> None:
        request = GenerationRequest(
            resume_text="Led a class project and summarized survey results in presentation slides.",
            activity_text="Used Excel to clean data and wrote weekly updates for a student club.",
            job_posting_text="We need someone with communication skills, spreadsheet skills, and experience summarizing user feedback.",
            goal="product operations internship",
            mode="heuristic",
        )
        response = generate_with_heuristics(request)
        self.assertEqual(response.backend, "heuristic")
        self.assertTrue(response.tailored_summary)
        self.assertEqual(len(response.resume_bullets), 3)
        self.assertEqual(len(response.cover_letter_points), 3)
        self.assertGreaterEqual(len(response.evidence_matches), 1)


if __name__ == "__main__":
    unittest.main()

