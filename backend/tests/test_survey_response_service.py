"""Tests for shared survey response helpers."""

import importlib.util
import os
import unittest
from datetime import datetime, timezone

MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "app",
    "services",
    "survey_response_service.py",
)
MODULE_SPEC = importlib.util.spec_from_file_location("survey_response_service", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
survey_response_service = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(survey_response_service)

extract_analysis_member_emails = survey_response_service.extract_analysis_member_emails
get_utc_day_bounds = survey_response_service.get_utc_day_bounds
normalize_survey_email = survey_response_service.normalize_survey_email


class TestSurveyResponseService(unittest.TestCase):
    def test_normalize_survey_email(self):
        self.assertEqual(normalize_survey_email("  Alice@Example.com "), "alice@example.com")
        self.assertEqual(normalize_survey_email(None), "")

    def test_get_utc_day_bounds_uses_reference_day(self):
        reference = datetime(2026, 3, 13, 22, 30, tzinfo=timezone.utc)
        day_start, day_end = get_utc_day_bounds(reference)

        self.assertEqual(day_start.isoformat(), "2026-03-13T00:00:00+00:00")
        self.assertEqual(day_end.isoformat(), "2026-03-13T23:59:59.999999+00:00")

    def test_extract_analysis_member_emails_from_dict_team_analysis(self):
        results = {
            "team_analysis": {
                "members": [
                    {"user_email": "ALICE@example.com"},
                    {"email": "bob@example.com"},
                    {"user_email": "alice@example.com"},
                    {"user_email": ""},
                ]
            }
        }

        self.assertEqual(
            extract_analysis_member_emails(results),
            ["alice@example.com", "bob@example.com"],
        )

    def test_extract_analysis_member_emails_from_list_team_analysis(self):
        results = {
            "team_analysis": [
                {"user_email": "carol@example.com"},
                {"user_email": "dave@example.com"},
            ]
        }

        self.assertEqual(
            extract_analysis_member_emails(results),
            ["carol@example.com", "dave@example.com"],
        )

    def test_extract_analysis_member_emails_returns_empty_for_missing_results(self):
        self.assertEqual(extract_analysis_member_emails(None), [])
        self.assertEqual(extract_analysis_member_emails({}), [])


if __name__ == "__main__":
    unittest.main()
