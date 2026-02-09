"""Tests for analysis data trimming to ensure frontend receives only needed keys."""
import unittest

from app.api.endpoints.analyses import _trim_analysis_data, _load_analysis_data, _ANALYSIS_DATA_KEYS


class TestTrimAnalysisData(unittest.TestCase):

    def test_keeps_all_frontend_keys(self):
        """All keys the frontend uses should be preserved."""
        data = {k: f"value_{k}" for k in _ANALYSIS_DATA_KEYS}
        result = _trim_analysis_data(data)
        self.assertEqual(set(result.keys()), set(_ANALYSIS_DATA_KEYS))

    def test_strips_unused_keys(self):
        """Keys the frontend doesn't use should be removed."""
        data = {
            "team_analysis": {"members": []},
            "team_health": {"overall_score": 22},
            "insights": "should be removed",
            "recommendations": "should be removed",
            "period_summary": "should be removed",
            "github_insights": "should be removed",
            "slack_insights": "should be removed",
            "timeout_metadata": "should be removed",
            "analysis_timestamp": "should be removed",
            "chart_mode": "should be removed",
        }
        result = _trim_analysis_data(data)
        self.assertIn("team_analysis", result)
        self.assertIn("team_health", result)
        for key in ("insights", "recommendations", "period_summary",
                     "github_insights", "slack_insights", "timeout_metadata",
                     "analysis_timestamp", "chart_mode"):
            self.assertNotIn(key, result)

    def test_empty_dict(self):
        """Empty results should return empty dict."""
        self.assertEqual(_trim_analysis_data({}), {})

    def test_preserves_values(self):
        """Values should not be modified, only filtered by key."""
        members = [{"name": "Alice", "score": 42}]
        data = {
            "team_analysis": {"members": members},
            "recommendations": "remove me",
        }
        result = _trim_analysis_data(data)
        self.assertEqual(result["team_analysis"]["members"], members)

    def test_preserves_error_state_keys(self):
        """Error/partial data keys should be preserved for failed analyses."""
        data = {
            "partial_data": {"users": [], "incidents": []},
            "error": "Analysis failed at data collection",
            "data_collection_successful": False,
            "failure_stage": "github_collection",
        }
        result = _trim_analysis_data(data)
        self.assertEqual(len(result), 4)
        self.assertFalse(result["data_collection_successful"])

    def test_member_surveys_not_in_whitelist(self):
        """member_surveys is added after trimming, so it should not be in the whitelist."""
        self.assertNotIn("member_surveys", _ANALYSIS_DATA_KEYS)

    def test_member_surveys_in_stored_results_is_stripped(self):
        """If stored results contain member_surveys, trim should strip it
        since the endpoint re-adds it from a fresh DB query."""
        data = {
            "team_analysis": {"members": []},
            "member_surveys": {"old@example.com": {"survey_count_in_period": 1}},
        }
        result = _trim_analysis_data(data)
        self.assertNotIn("member_surveys", result)


if __name__ == "__main__":
    unittest.main()
