"""Full analysis input windows and feature flags; every provider is mocked."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

END = datetime(2026, 10, 5, 3, tzinfo=timezone.utc)


def collection():
    responder = {"data": {"id": "test-user", "attributes": {"email": "test@example.com"}}}
    events = [
        {"id": "four-month-old", "attributes": {
            "created_at": (END - timedelta(days=120)).isoformat(), "user": responder,
        }},
        {"id": "recent", "attributes": {"created_at": END.isoformat(), "user": responder}},
    ]
    return {
        "users": [{"id": "test-user", "name": "Test", "email": "test@example.com", "timezone": "UTC"}],
        "incidents": events,
        "collection_metadata": {
            "days_analyzed": 120,
            "date_range": {"start": (END - timedelta(days=120)).isoformat(), "end": END.isoformat()},
        },
    }


@pytest.mark.parametrize("days", [30, 90, 120, 365])
def test_analyzer_preserves_requested_window_and_all_collected_incidents(monkeypatch, days):
    from app.services.unified_burnout_analyzer import UnifiedBurnoutAnalyzer

    monkeypatch.setenv("USE_MOCK_DATA", "false")
    analyzer = UnifiedBurnoutAnalyzer(api_token="test-no-provider-calls")
    payload = collection()
    fetch = AsyncMock(return_value=payload)
    monkeypatch.setattr(analyzer, "_fetch_analysis_data", fetch)
    original_scoring = analyzer._analyze_team_data
    captured = {}

    def scoring(users, incidents, metadata, *args):
        captured["incidents"] = incidents
        return original_scoring(users, incidents, metadata, *args)

    monkeypatch.setattr(analyzer, "_analyze_team_data", scoring)
    result = asyncio.run(analyzer.analyze_burnout(time_range_days=days))
    fetch.assert_awaited_once_with(days)
    assert captured["incidents"] == payload["incidents"]
    assert result["team_analysis"]["members"][0]["incident_count"] == 2
    assert result["metadata"]["date_range"] == payload["collection_metadata"]["date_range"]
    assert "retention_window" not in result["metadata"]
    assert "retention_notice" not in result["metadata"]


def test_mock_analysis_keeps_all_source_features_and_loads_enrichment(monkeypatch):
    from app.services import unified_burnout_analyzer as analyzer_module

    loader = MagicMock()
    loader.get_unified_data.return_value = collection()
    loader.get_github_data.return_value = {}
    loader.get_slack_data.return_value = {}
    monkeypatch.setenv("USE_MOCK_DATA", "true")
    monkeypatch.setattr(analyzer_module, "MOCK_DATA_AVAILABLE", True)
    monkeypatch.setattr(analyzer_module, "MockDataLoader", lambda: loader)
    analyzer = analyzer_module.UnifiedBurnoutAnalyzer(
        api_token="test", github_token="github-test", slack_token="slack-test",
        jira_token="jira-test", linear_token="linear-test", current_user_id=42,
    )
    jira = AsyncMock(return_value={})
    linear = AsyncMock(return_value={})
    monkeypatch.setattr(analyzer, "_fetch_jira_workload_data", jira)
    monkeypatch.setattr(analyzer, "_fetch_linear_workload_data", linear)
    no_provider = AsyncMock(side_effect=AssertionError("Mock mode must not call a provider"))
    monkeypatch.setattr(analyzer, "_fetch_analysis_data", no_provider)

    result = asyncio.run(analyzer.analyze_burnout(time_range_days=120))
    assert result["team_analysis"]["members"][0]["incident_count"] == 2
    for source in ("github", "slack", "jira", "linear"):
        assert analyzer.features[source]
        assert result["metadata"][f"include_{source}"]
    loader.get_github_data.assert_called_once()
    loader.get_slack_data.assert_called_once()
    jira.assert_awaited_once_with(42)
    linear.assert_awaited_once_with(42)
    no_provider.assert_not_awaited()
    assert "retention_window" not in result["metadata"]
