"""Source event dates and obsolete certificates do not determine result age."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.retention_preview import classify_analysis_result

NOW = datetime(2026, 10, 5, 2, 30, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=90)


def snapshot(*, generated_at=NOW, completed_at=NOW, status="completed"):
    old_source = (NOW - timedelta(days=120)).isoformat()
    return SimpleNamespace(
        status=status, results_generated_at=generated_at,
        completed_at=completed_at, created_at=NOW - timedelta(days=365),
        config={"include_github": True, "include_jira": True},
        results={
            "metadata": {
                "date_range": {"start": old_source, "end": NOW.isoformat()},
                "retention_window": {
                    "version": 1, "earliest_event_at": old_source,
                    "input_event_count": 1, "sources": ["incidents"],
                },
                "openai_usage": {"2026-01-01": {"total_tokens": 42}},
            },
            "raw_incident_data": [{"created_at": old_source}],
            "github_insights": {"total_commits": 12},
            "jira_tickets": [{"created_at": old_source}],
            "daily_metrics": {"2026-01-01": {"incident_count": 1}},
        },
    )


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_fresh_generated_snapshot_keeps_four_month_source_data(status):
    assert classify_analysis_result(snapshot(status=status), CUTOFF).disposition == "retained"


def test_old_generation_expires_despite_recent_completion_and_source_metadata():
    record = snapshot(generated_at=CUTOFF - timedelta(seconds=1))
    record.results["metadata"]["retention_window"]["earliest_event_at"] = NOW.isoformat()
    assert classify_analysis_result(record, CUTOFF).disposition == "expired"


def test_legacy_completed_result_uses_completion_without_source_certification():
    assert classify_analysis_result(snapshot(generated_at=None), CUTOFF).disposition == "retained"


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_source_dates_and_query_window_cannot_date_an_unknown_generation(status):
    record = snapshot(generated_at=None, completed_at=None, status=status)
    assert classify_analysis_result(record, CUTOFF).disposition == "unverifiable"


def test_failed_legacy_result_cannot_use_its_failure_completion_as_generation():
    assert classify_analysis_result(snapshot(generated_at=None, status="failed"), CUTOFF).disposition == "unverifiable"
