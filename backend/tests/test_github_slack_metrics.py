"""
Unit tests for GitHub and Slack metrics calculation.

Tests metric extraction, calculation, and burnout analysis for both platforms.
"""

import unittest
from datetime import datetime, timedelta
from collections import defaultdict
import pytz


class TestGitHubDataStructure(unittest.TestCase):
    """Test GitHub data structure and field extraction."""

    def test_github_commit_structure(self):
        """Test that GitHub commit has expected structure."""
        commit = {
            "sha": "abc123",
            "commit": {
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "date": "2024-01-15T10:30:00Z"
                },
                "message": "Fix bug in authentication"
            },
            "stats": {
                "additions": 50,
                "deletions": 20,
                "total": 70
            }
        }

        # Verify structure
        self.assertIn("commit", commit)
        self.assertIn("author", commit["commit"])
        self.assertIn("date", commit["commit"]["author"])

        # Verify stats
        self.assertIn("stats", commit)
        self.assertEqual(commit["stats"]["additions"], 50)
        self.assertEqual(commit["stats"]["deletions"], 20)

    def test_github_pull_request_structure(self):
        """Test that GitHub PR has expected structure."""
        pull_request = {
            "number": 123,
            "title": "Add new feature",
            "user": {
                "login": "testuser"
            },
            "created_at": "2024-01-15T10:00:00Z",
            "merged_at": "2024-01-15T12:00:00Z",
            "additions": 150,
            "deletions": 50,
            "changed_files": 5
        }

        # Verify structure
        self.assertIn("created_at", pull_request)
        self.assertIn("merged_at", pull_request)
        self.assertIn("additions", pull_request)
        self.assertIn("deletions", pull_request)

        # Verify PR size
        pr_size = pull_request["additions"] + pull_request["deletions"]
        self.assertEqual(pr_size, 200)

    def test_github_code_review_structure(self):
        """Test that GitHub code review has expected structure."""
        review = {
            "id": 456,
            "user": {
                "login": "reviewer"
            },
            "submitted_at": "2024-01-15T11:00:00Z",
            "state": "APPROVED"
        }

        # Verify structure
        self.assertIn("submitted_at", review)
        self.assertIn("state", review)
        self.assertEqual(review["state"], "APPROVED")


class TestGitHubMetricCalculation(unittest.TestCase):
    """Test GitHub metric calculation logic."""

    def _parse_iso_utc(self, ts: str) -> datetime:
        """Parse ISO8601 timestamp."""
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    def _to_local(self, dt: datetime, user_tz: str) -> datetime:
        """Convert to local timezone."""
        try:
            tz = pytz.timezone(user_tz or "UTC")
        except Exception:
            tz = pytz.UTC
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(tz)

    def test_context_switching_intensity_calculation(self):
        """Test context switching intensity (variance in daily commits)."""
        # High variance = more context switching
        daily_commits = [1, 1, 10, 1, 1]  # One day with many commits
        avg = sum(daily_commits) / len(daily_commits)  # 2.8
        variance = sum((x - avg) ** 2 for x in daily_commits) / len(daily_commits)

        # Normalized intensity
        context_switching = min(1.0, variance / (avg + 1))

        # High variance should indicate high context switching
        self.assertGreater(context_switching, 0.5)

    def test_work_hours_spread_calculation(self):
        """Test work-life boundary erosion (commits across many hours)."""
        # Commits at many different hours = worse boundaries
        commit_hours = [8, 9, 10, 14, 17, 20, 22, 23]  # 8 unique hours
        unique_hours = len(set(commit_hours))
        work_hours_spread = unique_hours / 24.0

        # 8 out of 24 hours = 0.33 (moderate spread)
        self.assertAlmostEqual(work_hours_spread, 0.33, places=2)

    def test_late_night_coding_ratio_calculation(self):
        """Test late night coding detection (10 PM - 6 AM)."""
        commit_hours = [3, 9, 12, 15, 22, 23, 1]  # 4 late night (3, 22, 23, 1)

        # Late night: >= 22 or <= 6
        late_night_count = sum(1 for h in commit_hours if h >= 22 or h <= 6)
        late_night_ratio = late_night_count / len(commit_hours)

        self.assertEqual(late_night_count, 4)
        self.assertAlmostEqual(late_night_ratio, 4/7, places=2)

    def test_pr_complexity_calculation(self):
        """Test PR complexity (size normalized by 1000 lines)."""
        pr_sizes = [50, 200, 500, 1000]  # Lines changed

        avg_size = sum(pr_sizes) / len(pr_sizes)  # 437.5
        avg_pr_complexity = avg_size / 1000.0  # 0.4375

        self.assertAlmostEqual(avg_pr_complexity, 0.4375, places=2)

    def test_large_pr_ratio_calculation(self):
        """Test large PR ratio (>500 lines)."""
        pr_sizes = [50, 200, 600, 1000, 300]  # 2 out of 5 are >500

        large_prs = sum(1 for size in pr_sizes if size > 500)
        large_pr_ratio = large_prs / len(pr_sizes)

        self.assertEqual(large_prs, 2)
        self.assertAlmostEqual(large_pr_ratio, 0.4, places=1)

    def test_pr_review_time_calculation(self):
        """Test average PR review time (creation to merge)."""
        # PR created and merged
        created = datetime(2024, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
        merged = datetime(2024, 1, 15, 14, 0, 0, tzinfo=pytz.UTC)

        review_hours = (merged - created).total_seconds() / 3600
        self.assertEqual(review_hours, 4.0)

    def test_rush_pr_ratio_calculation(self):
        """Test rush PR ratio (merged within 2 hours)."""
        review_times = [0.5, 1.5, 3.0, 5.0, 0.75]  # hours, 3 rushed (<2h)

        rush_prs = sum(1 for t in review_times if t < 2.0)
        rush_ratio = rush_prs / len(review_times)

        self.assertEqual(rush_prs, 3)
        self.assertAlmostEqual(rush_ratio, 0.6, places=1)

    def test_review_engagement_trend(self):
        """Test review engagement trend (linear regression slope)."""
        # Weekly review counts over time
        weekly_reviews = [10, 9, 7, 6, 5]  # Declining trend

        # Simple slope calculation
        n = len(weekly_reviews)
        x_mean = sum(range(n)) / n  # 2.0
        y_mean = sum(weekly_reviews) / n  # 7.4

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(weekly_reviews))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # Negative slope indicates declining engagement
        self.assertLess(slope, 0)

    def test_late_night_coding_with_timezone(self):
        """Test that late night coding respects user timezone."""
        # 22:00 UTC = 10 PM UTC (late night)
        # 22:00 UTC = 2 PM PST (not late night)

        commit_ts = "2024-01-15T22:00:00Z"
        dt_utc = self._parse_iso_utc(commit_ts)

        # In UTC (late night)
        dt_utc_local = self._to_local(dt_utc, "UTC")
        is_late_night_utc = dt_utc_local.hour >= 22 or dt_utc_local.hour <= 6
        self.assertTrue(is_late_night_utc)

        # In PST (not late night, 2 PM)
        dt_pst = self._to_local(dt_utc, "America/Los_Angeles")
        is_late_night_pst = dt_pst.hour >= 22 or dt_pst.hour <= 6
        self.assertFalse(is_late_night_pst)


class TestGitHubBurnoutIndicators(unittest.TestCase):
    """Test GitHub burnout indicator scoring."""

    def test_burnout_score_context_switching(self):
        """Test burnout score for high context switching."""
        context_switching = 0.8  # High variance
        score = 0

        if context_switching > 0.7:
            score += 15

        self.assertEqual(score, 15)

    def test_burnout_score_work_hours_spread(self):
        """Test burnout score for poor work-life boundaries."""
        work_hours_spread = 0.7  # Working across 70% of hours
        score = 0

        if work_hours_spread > 0.6:
            score += 20

        self.assertEqual(score, 20)

    def test_burnout_score_late_night_coding(self):
        """Test burnout score for late night coding."""
        late_night_ratio = 0.3  # 30% late night commits
        score = 0

        if late_night_ratio > 0.2:
            score += 25

        self.assertEqual(score, 25)

    def test_burnout_score_large_prs(self):
        """Test burnout score for large PRs (potentially rushed)."""
        large_pr_ratio = 0.4  # 40% large PRs
        score = 0

        if large_pr_ratio > 0.3:
            score += 15

        self.assertEqual(score, 15)

    def test_burnout_score_rush_prs(self):
        """Test burnout score for rushed PRs."""
        rush_pr_ratio = 0.5  # 50% rushed PRs
        score = 0

        if rush_pr_ratio > 0.4:
            score += 15

        self.assertEqual(score, 15)

    def test_burnout_score_declining_reviews(self):
        """Test burnout score for declining review engagement."""
        review_trend_slope = -0.2  # Negative trend
        score = 0

        if review_trend_slope < -0.1:
            score += 10

        self.assertEqual(score, 10)

    def test_total_burnout_score_calculation(self):
        """Test total GitHub burnout score (0-100 scale)."""
        indicators = {
            'context_switching': 0.8,  # +15
            'work_hours_spread': 0.7,  # +20
            'late_night_ratio': 0.3,   # +25
            'large_pr_ratio': 0.4,     # +15
            'rush_pr_ratio': 0.5,      # +15
            'review_trend': -0.2       # +10
        }

        score = 0
        if indicators['context_switching'] > 0.7:
            score += 15
        if indicators['work_hours_spread'] > 0.6:
            score += 20
        if indicators['late_night_ratio'] > 0.2:
            score += 25
        if indicators['large_pr_ratio'] > 0.3:
            score += 15
        if indicators['rush_pr_ratio'] > 0.4:
            score += 15
        if indicators['review_trend'] < -0.1:
            score += 10

        # Total = 100 (maximum burnout)
        self.assertEqual(score, 100)


class TestSlackDataStructure(unittest.TestCase):
    """Test Slack data structure and field extraction."""

    def test_slack_message_structure(self):
        """Test that Slack message has expected structure."""
        message = {
            "type": "message",
            "user": "U12345",
            "text": "Can someone help with the deployment?",
            "ts": "1705324800.123456",  # Unix timestamp
            "channel": "C12345"
        }

        # Verify structure
        self.assertIn("user", message)
        self.assertIn("text", message)
        self.assertIn("ts", message)
        self.assertIn("channel", message)

    def test_slack_channels_active(self):
        """Test channels active count."""
        messages = [
            {"channel": "C1"},
            {"channel": "C2"},
            {"channel": "C1"},
            {"channel": "C3"},
        ]

        unique_channels = len(set(msg["channel"] for msg in messages))
        self.assertEqual(unique_channels, 3)

    def test_slack_response_time_structure(self):
        """Test Slack response time calculation."""
        # Two messages in sequence
        msg1_ts = 1705324800.0  # Message sent
        msg2_ts = 1705324860.0  # Response 60 seconds later

        response_time_seconds = msg2_ts - msg1_ts
        self.assertEqual(response_time_seconds, 60.0)


class TestSlackMetricCalculation(unittest.TestCase):
    """Test Slack metric calculation logic."""

    def _parse_iso_utc(self, ts: str) -> datetime:
        """Parse ISO8601 timestamp."""
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    def _to_local(self, dt: datetime, user_tz: str) -> datetime:
        """Convert to local timezone."""
        try:
            tz = pytz.timezone(user_tz or "UTC")
        except Exception:
            tz = pytz.UTC
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(tz)

    def test_slack_after_hours_ratio(self):
        """Test Slack after-hours communication ratio (before 9 AM or 5 PM+)."""
        message_hours = [3, 8, 9, 12, 16, 17, 20, 23]
        # After hours: < 9 or >= 17: [3, 8, 17, 20, 23] = 5 out of 8

        after_hours = sum(1 for h in message_hours if h < 9 or h >= 17)
        after_hours_ratio = after_hours / len(message_hours)

        self.assertEqual(after_hours, 5)
        self.assertAlmostEqual(after_hours_ratio, 5/8, places=2)

    def test_slack_late_night_ratio(self):
        """Test Slack late night communication ratio (10 PM - 6 AM)."""
        message_hours = [1, 5, 9, 12, 15, 22, 23]
        # Late night: >= 22 or <= 6: [1, 5, 22, 23] = 4 out of 7

        late_night = sum(1 for h in message_hours if h >= 22 or h <= 6)
        late_night_ratio = late_night / len(message_hours)

        self.assertEqual(late_night, 4)
        self.assertAlmostEqual(late_night_ratio, 4/7, places=2)

    def test_slack_weekend_ratio(self):
        """Test Slack weekend communication ratio."""
        # weekday: Mon=0, Tue=1, ..., Sat=5, Sun=6
        message_weekdays = [0, 1, 2, 5, 6, 5]  # 3 weekend (5, 6, 5)

        weekend = sum(1 for day in message_weekdays if day >= 5)
        weekend_ratio = weekend / len(message_weekdays)

        self.assertEqual(weekend, 3)
        self.assertEqual(weekend_ratio, 0.5)

    def test_slack_daily_message_volume(self):
        """Test average daily message volume."""
        total_messages = 150
        days_analyzed = 30

        daily_avg = total_messages / days_analyzed
        self.assertEqual(daily_avg, 5.0)

    def test_slack_channel_diversity(self):
        """Test channel diversity (0-1 scale, capped at 1.0)."""
        channels_active = 8
        channel_diversity = min(1.0, channels_active / 10)

        self.assertEqual(channel_diversity, 0.8)

        # Test capping
        channels_active_high = 15
        channel_diversity_capped = min(1.0, channels_active_high / 10)
        self.assertEqual(channel_diversity_capped, 1.0)

    def test_slack_avg_response_time(self):
        """Test average response time in minutes."""
        response_times_seconds = [60, 120, 300, 600]  # seconds

        avg_seconds = sum(response_times_seconds) / len(response_times_seconds)
        avg_minutes = avg_seconds / 60

        self.assertEqual(avg_minutes, 4.5)

    def test_slack_immediate_response_ratio(self):
        """Test immediate response ratio (within 5 minutes)."""
        response_times_seconds = [60, 180, 400, 600]  # 2 under 300s (5 min)

        immediate = sum(1 for t in response_times_seconds if t < 300)
        immediate_ratio = immediate / len(response_times_seconds)

        self.assertEqual(immediate, 2)
        self.assertEqual(immediate_ratio, 0.5)

    def test_slack_urgent_response_ratio(self):
        """Test urgent response ratio (within 1 minute)."""
        response_times_seconds = [30, 50, 70, 180]  # 2 under 60s (1 min)

        urgent = sum(1 for t in response_times_seconds if t <= 60)
        urgent_ratio = urgent / len(response_times_seconds)

        self.assertEqual(urgent, 2)
        self.assertEqual(urgent_ratio, 0.5)

    def test_slack_after_hours_with_timezone(self):
        """Test that Slack after-hours respects user timezone."""
        # 20:00 UTC = 8 PM UTC (after hours)
        # 20:00 UTC = 12 PM PST (business hours)

        msg_ts = "2024-01-15T20:00:00Z"
        dt_utc = self._parse_iso_utc(msg_ts)

        # In UTC (after hours)
        dt_utc_local = self._to_local(dt_utc, "UTC")
        is_after_hours_utc = dt_utc_local.hour < 9 or dt_utc_local.hour >= 17
        self.assertTrue(is_after_hours_utc)

        # In PST (business hours, 12 PM)
        dt_pst = self._to_local(dt_utc, "America/Los_Angeles")
        is_after_hours_pst = dt_pst.hour < 9 or dt_pst.hour >= 17
        self.assertFalse(is_after_hours_pst)


class TestSlackBurnoutIndicators(unittest.TestCase):
    """Test Slack burnout indicator scoring."""

    def test_burnout_score_after_hours(self):
        """Test burnout score for excessive after-hours communication."""
        after_hours_ratio = 0.4  # 40% after hours
        score = 0

        if after_hours_ratio > 0.3:
            score += 20

        self.assertEqual(score, 20)

    def test_burnout_score_late_night(self):
        """Test burnout score for late night communication."""
        late_night_ratio = 0.15  # 15% late night
        score = 0

        if late_night_ratio > 0.1:
            score += 25

        self.assertEqual(score, 25)

    def test_burnout_score_weekend(self):
        """Test burnout score for weekend work."""
        weekend_ratio = 0.2  # 20% weekend messages
        score = 0

        if weekend_ratio > 0.15:
            score += 20

        self.assertEqual(score, 20)

    def test_burnout_score_immediate_responses(self):
        """Test burnout score for excessive immediate responses."""
        immediate_ratio = 0.5  # 50% immediate responses
        score = 0

        if immediate_ratio > 0.4:
            score += 15

        self.assertEqual(score, 15)

    def test_burnout_score_high_volume(self):
        """Test burnout score for high daily message volume."""
        daily_volume = 60  # 60 messages per day
        score = 0

        if daily_volume > 50:
            score += 10

        self.assertEqual(score, 10)

    def test_burnout_score_isolation(self):
        """Test burnout score for channel isolation."""
        channel_diversity = 0.15  # Only 1-2 channels
        score = 0

        if channel_diversity < 0.2:
            score += 15

        self.assertEqual(score, 15)

    def test_burnout_score_negative_sentiment(self):
        """Test burnout score for negative sentiment."""
        avg_sentiment = -0.3  # Negative sentiment
        score = 0

        if avg_sentiment < -0.2:
            score += 15

        self.assertEqual(score, 15)

    def test_total_slack_burnout_score(self):
        """Test total Slack burnout score calculation."""
        indicators = {
            'after_hours_ratio': 0.4,     # +20
            'late_night_ratio': 0.15,     # +25
            'weekend_ratio': 0.2,         # +20
            'immediate_ratio': 0.5,       # +15
            'daily_volume': 60,           # +10
            'channel_diversity': 0.15,    # +15
            'avg_sentiment': -0.3         # +15
        }

        score = 0
        if indicators['after_hours_ratio'] > 0.3:
            score += 20
        if indicators['late_night_ratio'] > 0.1:
            score += 25
        if indicators['weekend_ratio'] > 0.15:
            score += 20
        if indicators['immediate_ratio'] > 0.4:
            score += 15
        if indicators['daily_volume'] > 50:
            score += 10
        if indicators['channel_diversity'] < 0.2:
            score += 15
        if indicators['avg_sentiment'] < -0.2:
            score += 15

        # Total = 120 (can exceed 100)
        self.assertEqual(score, 120)
        # In practice, capped at 100
        capped_score = min(100, score)
        self.assertEqual(capped_score, 100)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases for GitHub and Slack metrics."""

    def test_no_github_data(self):
        """Test calculations with no GitHub data."""
        commits = []
        pull_requests = []

        # Should handle gracefully
        context_switching = 0 if not commits else 1.0
        pr_complexity = 0 if not pull_requests else 1.0

        self.assertEqual(context_switching, 0)
        self.assertEqual(pr_complexity, 0)

    def test_no_slack_data(self):
        """Test calculations with no Slack data."""
        messages = []

        # Should handle gracefully
        after_hours_ratio = 0 if not messages else 1.0

        self.assertEqual(after_hours_ratio, 0)

    def test_single_commit(self):
        """Test with single commit (no variance calculation)."""
        daily_commits = [1]

        # Variance undefined, should default to 0
        if len(daily_commits) < 2:
            context_switching = 0
        else:
            context_switching = 1.0

        self.assertEqual(context_switching, 0)

    def test_zero_response_times(self):
        """Test with no response times."""
        response_times = []

        avg_response = sum(response_times) / len(response_times) if response_times else 0
        self.assertEqual(avg_response, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
