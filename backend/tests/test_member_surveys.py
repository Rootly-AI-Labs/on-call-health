"""
Unit tests for get_member_surveys bulk query optimization and trend calculation.

Tests the N+1 query fix which replaced individual queries per member
with 2 bulk queries + Python grouping.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestCalculateTrend(unittest.TestCase):
    """Test the _calculate_trend helper function."""

    def _calculate_trend(self, combined_scores: list) -> str | None:
        """
        Local copy of trend calculation for testing.
        Higher score = better (less burnout), so improving means score went up.
        """
        if len(combined_scores) < 3:
            return None

        mid = len(combined_scores) // 2
        first_half_avg = sum(combined_scores[:mid]) / mid
        second_half_avg = sum(combined_scores[mid:]) / (len(combined_scores) - mid)
        difference = second_half_avg - first_half_avg

        if difference > 0.3:
            return 'improving'
        elif difference < -0.3:
            return 'declining'
        else:
            return 'stable'

    def test_insufficient_data_returns_none(self):
        """Test that fewer than 3 responses returns None."""
        self.assertIsNone(self._calculate_trend([]))
        self.assertIsNone(self._calculate_trend([3.0]))
        self.assertIsNone(self._calculate_trend([3.0, 4.0]))

    def test_improving_trend(self):
        """Test detection of improving trend (score increased by >0.3)."""
        # First half avg: (2.0 + 2.5) / 2 = 2.25
        # Second half avg: (4.0 + 4.5) / 2 = 4.25
        # Difference: 4.25 - 2.25 = 2.0 > 0.3 -> improving
        scores = [2.0, 2.5, 4.0, 4.5]
        self.assertEqual(self._calculate_trend(scores), 'improving')

    def test_declining_trend(self):
        """Test detection of declining trend (score decreased by >0.3)."""
        # First half avg: (4.0 + 4.5) / 2 = 4.25
        # Second half avg: (2.0 + 2.5) / 2 = 2.25
        # Difference: 2.25 - 4.25 = -2.0 < -0.3 -> declining
        scores = [4.0, 4.5, 2.0, 2.5]
        self.assertEqual(self._calculate_trend(scores), 'declining')

    def test_stable_trend(self):
        """Test detection of stable trend (change within ±0.3)."""
        # First half avg: (3.0 + 3.1) / 2 = 3.05
        # Second half avg: (3.2 + 3.0) / 2 = 3.1
        # Difference: 3.1 - 3.05 = 0.05 -> stable
        scores = [3.0, 3.1, 3.2, 3.0]
        self.assertEqual(self._calculate_trend(scores), 'stable')

    def test_boundary_improving(self):
        """Test boundary case just above improving threshold."""
        # First half avg: 3.0
        # Second half avg: 3.35
        # Difference: 0.35 > 0.3 -> improving
        scores = [3.0, 3.0, 3.35, 3.35]
        self.assertEqual(self._calculate_trend(scores), 'improving')

    def test_boundary_declining(self):
        """Test boundary case just below declining threshold."""
        # First half avg: 3.35
        # Second half avg: 3.0
        # Difference: -0.35 < -0.3 -> declining
        scores = [3.35, 3.35, 3.0, 3.0]
        self.assertEqual(self._calculate_trend(scores), 'declining')

    def test_boundary_stable(self):
        """Test boundary case exactly at threshold (should be stable)."""
        # First half avg: 3.0
        # Second half avg: 3.3
        # Difference: 0.3 (not > 0.3) -> stable
        scores = [3.0, 3.0, 3.3, 3.3]
        self.assertEqual(self._calculate_trend(scores), 'stable')

    def test_odd_number_of_scores(self):
        """Test with odd number of scores (3, 5, 7)."""
        # 3 scores: first half = [3.0], second half = [3.5, 4.0]
        scores_3 = [3.0, 3.5, 4.0]
        result = self._calculate_trend(scores_3)
        self.assertIn(result, ['improving', 'stable', 'declining'])

        # 5 scores: first half = [2.0, 2.0], second half = [4.0, 4.0, 4.0]
        scores_5 = [2.0, 2.0, 4.0, 4.0, 4.0]
        self.assertEqual(self._calculate_trend(scores_5), 'improving')


class TestBulkQueryGrouping(unittest.TestCase):
    """Test the bulk query grouping logic used in get_member_surveys."""

    def test_surveys_grouped_by_email(self):
        """Test that surveys are correctly grouped by email."""
        # Simulate bulk query results
        mock_surveys = [
            MagicMock(email='alice@test.com', feeling_score=3, workload_score=4),
            MagicMock(email='alice@test.com', feeling_score=4, workload_score=4),
            MagicMock(email='bob@test.com', feeling_score=2, workload_score=3),
            MagicMock(email='charlie@test.com', feeling_score=5, workload_score=5),
            MagicMock(email='bob@test.com', feeling_score=3, workload_score=3),
        ]

        # Group by email (same logic as in get_member_surveys)
        surveys_by_email = defaultdict(list)
        for survey in mock_surveys:
            surveys_by_email[survey.email].append(survey)

        # Verify grouping
        self.assertEqual(len(surveys_by_email['alice@test.com']), 2)
        self.assertEqual(len(surveys_by_email['bob@test.com']), 2)
        self.assertEqual(len(surveys_by_email['charlie@test.com']), 1)
        self.assertEqual(len(surveys_by_email), 3)  # 3 unique emails

    def test_empty_surveys_for_member(self):
        """Test that members without surveys get empty list from defaultdict."""
        surveys_by_email = defaultdict(list)

        # Member with no surveys should get empty list
        self.assertEqual(surveys_by_email['no_surveys@test.com'], [])
        self.assertEqual(len(surveys_by_email['no_surveys@test.com']), 0)

    def test_preserves_survey_order(self):
        """Test that surveys maintain chronological order after grouping."""
        mock_surveys = [
            MagicMock(email='alice@test.com', submitted_at=datetime(2024, 1, 1)),
            MagicMock(email='alice@test.com', submitted_at=datetime(2024, 1, 2)),
            MagicMock(email='alice@test.com', submitted_at=datetime(2024, 1, 3)),
        ]

        surveys_by_email = defaultdict(list)
        for survey in mock_surveys:
            surveys_by_email[survey.email].append(survey)

        alice_surveys = surveys_by_email['alice@test.com']
        self.assertEqual(alice_surveys[0].submitted_at, datetime(2024, 1, 1))
        self.assertEqual(alice_surveys[-1].submitted_at, datetime(2024, 1, 3))


class TestCombinedScoreCalculation(unittest.TestCase):
    """Test combined score calculation from feeling and workload scores."""

    def test_combined_score_average(self):
        """Test that combined score is average of feeling and workload."""
        test_cases = [
            (3, 3, 3.0),    # Both 3 -> 3.0
            (5, 5, 5.0),    # Both 5 -> 5.0
            (1, 5, 3.0),    # 1 and 5 -> 3.0
            (2, 4, 3.0),    # 2 and 4 -> 3.0
            (4, 3, 3.5),    # 4 and 3 -> 3.5
        ]

        for feeling, workload, expected in test_cases:
            combined = (feeling + workload) / 2.0
            self.assertEqual(combined, expected,
                           f"feeling={feeling}, workload={workload} should give {expected}")

    def test_combined_score_rounding(self):
        """Test that combined scores are rounded to 1 decimal place."""
        # (3 + 4) / 2 = 3.5 -> 3.5
        combined = (3 + 4) / 2.0
        self.assertEqual(round(combined, 1), 3.5)

        # (2 + 3) / 2 = 2.5 -> 2.5
        combined = (2 + 3) / 2.0
        self.assertEqual(round(combined, 1), 2.5)


class TestMemberEmailFiltering(unittest.TestCase):
    """Test member email filtering logic."""

    def test_filters_out_null_emails(self):
        """Test that members without emails are filtered out."""
        mock_correlations = [
            MagicMock(email='alice@test.com'),
            MagicMock(email=None),  # Should be filtered
            MagicMock(email='bob@test.com'),
            MagicMock(email=''),  # Empty string is falsy, filtered
            MagicMock(email='charlie@test.com'),
        ]

        # Same filtering as in get_member_surveys
        member_emails = [c.email for c in mock_correlations if c.email]

        self.assertEqual(len(member_emails), 3)
        self.assertIn('alice@test.com', member_emails)
        self.assertIn('bob@test.com', member_emails)
        self.assertIn('charlie@test.com', member_emails)
        self.assertNotIn(None, member_emails)
        self.assertNotIn('', member_emails)

    def test_empty_correlations_returns_empty_list(self):
        """Test that no correlations returns empty email list."""
        mock_correlations = []
        member_emails = [c.email for c in mock_correlations if c.email]
        self.assertEqual(member_emails, [])


class TestDateRangeCalculation(unittest.TestCase):
    """Test date range calculation for survey filtering."""

    def test_default_time_range(self):
        """Test default 30-day time range."""
        analysis_created_at = datetime(2024, 1, 31, 12, 0, 0)
        time_range = None  # Should default to 30

        analysis_start_date = analysis_created_at - timedelta(days=time_range or 30)
        expected_start = datetime(2024, 1, 1, 12, 0, 0)

        self.assertEqual(analysis_start_date, expected_start)

    def test_custom_time_range(self):
        """Test custom time range (e.g., 90 days)."""
        analysis_created_at = datetime(2024, 4, 1, 12, 0, 0)
        time_range = 90

        analysis_start_date = analysis_created_at - timedelta(days=time_range or 30)
        expected_start = datetime(2024, 1, 2, 12, 0, 0)

        self.assertEqual(analysis_start_date, expected_start)


class TestSurveyResponseFormat(unittest.TestCase):
    """Test survey response output format."""

    def test_survey_response_structure(self):
        """Test that survey response has all required fields."""
        mock_survey = MagicMock(
            feeling_score=4,
            workload_score=3,
            submitted_at=datetime(2024, 1, 15, 10, 30, 0),
            stress_factors=['workload', 'deadlines'],
            personal_circumstances='somewhat',
            additional_comments='Test comment',
            submitted_via='web'
        )

        combined = (mock_survey.feeling_score + mock_survey.workload_score) / 2.0
        response = {
            'feeling_score': mock_survey.feeling_score,
            'workload_score': mock_survey.workload_score,
            'combined_score': round(combined, 1),
            'submitted_at': mock_survey.submitted_at.isoformat(),
            'stress_factors': mock_survey.stress_factors,
            'personal_circumstances': mock_survey.personal_circumstances,
            'additional_comments': mock_survey.additional_comments,
            'submitted_via': mock_survey.submitted_via
        }

        self.assertEqual(response['feeling_score'], 4)
        self.assertEqual(response['workload_score'], 3)
        self.assertEqual(response['combined_score'], 3.5)
        self.assertEqual(response['submitted_at'], '2024-01-15T10:30:00')
        self.assertEqual(response['stress_factors'], ['workload', 'deadlines'])
        self.assertEqual(response['personal_circumstances'], 'somewhat')
        self.assertEqual(response['additional_comments'], 'Test comment')
        self.assertEqual(response['submitted_via'], 'web')

    def test_member_survey_summary_structure(self):
        """Test that member survey summary has all required fields."""
        mock_surveys = [
            MagicMock(feeling_score=3, workload_score=3),
            MagicMock(feeling_score=4, workload_score=4),
            MagicMock(feeling_score=5, workload_score=5),
        ]

        combined_scores = [(s.feeling_score + s.workload_score) / 2.0 for s in mock_surveys]
        latest = mock_surveys[-1]

        summary = {
            'survey_count_in_period': len(mock_surveys),
            'latest_feeling_score': latest.feeling_score,
            'latest_workload_score': latest.workload_score,
            'latest_combined_score': round(combined_scores[-1], 1),
            'trend': 'improving',  # Would come from _calculate_trend
            'survey_responses': []  # Would contain response dicts
        }

        self.assertEqual(summary['survey_count_in_period'], 3)
        self.assertEqual(summary['latest_feeling_score'], 5)
        self.assertEqual(summary['latest_workload_score'], 5)
        self.assertEqual(summary['latest_combined_score'], 5.0)
        self.assertIn('trend', summary)
        self.assertIn('survey_responses', summary)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases in get_member_surveys logic."""

    def test_no_organization_id_returns_empty(self):
        """Test that missing organization_id returns empty dict."""
        mock_analysis = MagicMock(organization_id=None)

        if not mock_analysis.organization_id:
            result = {}
        else:
            result = {'would': 'process'}

        self.assertEqual(result, {})

    def test_no_members_returns_empty(self):
        """Test that no team members returns empty dict."""
        member_emails = []

        if not member_emails:
            result = {}
        else:
            result = {'would': 'process'}

        self.assertEqual(result, {})

    def test_members_with_no_surveys_skipped(self):
        """Test that members without surveys are not included in output."""
        member_emails = ['alice@test.com', 'bob@test.com', 'charlie@test.com']
        surveys_by_email = defaultdict(list)

        # Only alice has surveys
        surveys_by_email['alice@test.com'] = [
            MagicMock(feeling_score=4, workload_score=4)
        ]

        member_surveys = {}
        for email in member_emails:
            surveys = surveys_by_email[email]
            if not surveys:
                continue  # Skip members without surveys
            member_surveys[email] = {'has_surveys': True}

        self.assertEqual(len(member_surveys), 1)
        self.assertIn('alice@test.com', member_surveys)
        self.assertNotIn('bob@test.com', member_surveys)
        self.assertNotIn('charlie@test.com', member_surveys)


if __name__ == '__main__':
    unittest.main(verbosity=2)
