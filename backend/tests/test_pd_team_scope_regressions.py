"""Selected PagerDuty teams must never expand into account-wide analyses."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pagerduty_client import (
    PagerDutyAPIClient,
    PagerDutyAnalyticsUnavailable,
    PagerDutyDataCollectionError,
    PagerDutyDataCollector,
    PagerDutyTeamScopeError,
)
from app.services.unified_burnout_analyzer import UnifiedBurnoutAnalyzer


MEMBER = {"id": "MEMBER1", "email": "member@example.invalid", "name": "Member"}
OUTSIDER = {"id": "OUTSIDER", "email": "outside@example.invalid", "name": "Other"}
SINCE = datetime.now(timezone.utc) - timedelta(days=7)


def response(status, body):
    result = MagicMock(status=status)
    result.__aenter__ = AsyncMock(return_value=result)
    result.__aexit__ = AsyncMock(return_value=False)
    result.json = AsyncMock(return_value=body)
    result.text = AsyncMock(return_value="Mock provider failure")
    return result


def session(responses):
    result = MagicMock()
    result.__aenter__ = AsyncMock(return_value=result)
    result.__aexit__ = AsyncMock(return_value=False)
    result.get.side_effect = responses
    return result


@pytest.mark.parametrize("team_ids", [["TEAM1"], None])
def test_rest_incidents_preserve_optional_team_filter_on_every_page(team_ids):
    http = session([
        response(200, {"incidents": [{"id": "INC1"}], "more": True}),
        response(200, {"incidents": [{"id": "INC2"}], "more": False}),
    ])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        result = asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE, team_ids=team_ids))
    assert [incident["id"] for incident in result] == ["INC1", "INC2"]
    assert [call.kwargs["params"]["offset"] for call in http.get.call_args_list] == [0, 1]
    for call in http.get.call_args_list:
        params = call.kwargs["params"]
        if team_ids:
            assert params["team_ids[]"] == team_ids
        else:
            assert "team_ids[]" not in params


@pytest.mark.parametrize("status", [403, 404, 500])
def test_failed_member_page_never_returns_or_caches_partial_roster(status):
    http = session([
        response(200, {"members": [{"user": MEMBER}], "more": True}),
        response(status, {}),
    ])
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http),
    ):
        with pytest.raises(PagerDutyTeamScopeError, match=f"HTTP {status}"):
            asyncio.run(PagerDutyAPIClient("fake").get_team_members("TEAM1"))
    cache.assert_not_called()


def test_membership_timeout_fails_closed_without_caching():
    http = session([asyncio.TimeoutError()])
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http),
    ):
        with pytest.raises(PagerDutyTeamScopeError, match="Could not load"):
            asyncio.run(PagerDutyAPIClient("fake").get_team_members("TEAM1"))
    cache.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"members": [], "more": True}])
def test_invalid_or_stalled_membership_pagination_fails_closed(body):
    http = session([response(200, body)])
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http),
    ):
        with pytest.raises(PagerDutyTeamScopeError):
            asyncio.run(PagerDutyAPIClient("fake").get_team_members("TEAM1"))
    cache.assert_not_called()


def test_successful_member_pagination_keeps_complete_roster():
    http = session([
        response(200, {"members": [{"user": MEMBER}], "more": True}),
        response(200, {"members": [{"user": OUTSIDER}], "more": False}),
    ])
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http),
    ):
        result = asyncio.run(PagerDutyAPIClient("fake").get_team_members("TEAM1"))
    assert result == [MEMBER, OUTSIDER]
    assert http.get.call_args_list[1].kwargs["params"]["offset"] == 1
    assert all(call.kwargs["params"]["include[]"] == "users" for call in http.get.call_args_list)
    assert cache.call_args.args[3] == [MEMBER, OUTSIDER]


@pytest.mark.parametrize("invalid_member", [
    {}, {"user": None}, {"user": {}}, {"user": "invalid"}, "invalid",
    {"user": {"email": "missing-id@example.invalid"}},
    {"user": {"id": None}}, {"user": {"id": ""}},
    {"user": {"id": "  "}}, {"user": {"id": 42}},
])
def test_mixed_membership_page_rejects_every_missing_or_malformed_identity(invalid_member):
    http = session([response(200, {
        "members": [{"user": MEMBER}, invalid_member], "more": False,
    })])
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http),
    ):
        with pytest.raises(PagerDutyTeamScopeError, match="incomplete team member list"):
            asyncio.run(PagerDutyAPIClient("fake").get_team_scoped_users("TEAM1", [MEMBER]))
    cache.assert_not_called()


@pytest.mark.parametrize("failure_page", [1, 2])
def test_malformed_later_member_page_never_returns_previous_members(failure_page):
    pages = [response(200, {"members": [{"user": MEMBER}], "more": True})] * (failure_page - 1)
    pages.append(response(200, {"members": [{"role": "responder"}], "more": False}))
    with (
        patch("app.core.pagerduty_client.get_cached_api_response", return_value=None),
        patch("app.core.pagerduty_client.set_cached_api_response") as cache,
        patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=session(pages)),
    ):
        with pytest.raises(PagerDutyTeamScopeError):
            asyncio.run(PagerDutyAPIClient("fake").get_team_members("TEAM1"))
    cache.assert_not_called()


@pytest.mark.parametrize("failure_page, status", [(1, 403), (2, 500)])
def test_scoped_rest_http_failure_never_returns_empty_or_partial_incidents(failure_page, status):
    pages = [response(200, {"incidents": [{"id": "INC1"}], "more": True})] * (failure_page - 1)
    pages.append(response(status, {}))
    http = session(pages)
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        with pytest.raises(PagerDutyDataCollectionError, match=f"HTTP {status}"):
            asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE, team_ids=["TEAM1"]))
    assert all(call.kwargs["params"]["team_ids[]"] == ["TEAM1"] for call in http.get.call_args_list)


@pytest.mark.parametrize("failure_page", [1, 2])
def test_scoped_rest_timeout_never_returns_empty_or_partial_incidents(failure_page):
    pages = [response(200, {"incidents": [{"id": "INC1"}], "more": True})] * (failure_page - 1)
    pages.append(asyncio.TimeoutError())
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=session(pages)):
        with pytest.raises(PagerDutyDataCollectionError, match="timed out"):
            asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE, team_ids=["TEAM1"]))


@pytest.mark.parametrize("body", [
    None, [], {}, {"incidents": None, "more": False},
    {"incidents": [], "more": "false"}, {"incidents": [], "more": True},
    {"incidents": [None], "more": False}, {"incidents": [{}], "more": False},
    {"incidents": [{"id": ""}], "more": False},
])
def test_scoped_rest_malformed_page_never_returns_partial_incidents(body):
    http = session([
        response(200, {"incidents": [{"id": "INC1"}], "more": True}),
        response(200, body),
    ])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        with pytest.raises(PagerDutyDataCollectionError):
            asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE, team_ids=["TEAM1"]))


def test_scoped_rest_connection_error_never_becomes_an_empty_report():
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=session([OSError("Offline")])):
        with pytest.raises(PagerDutyDataCollectionError, match="Could not complete"):
            asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE, team_ids=["TEAM1"]))


@pytest.mark.parametrize("status", [403, 500])
def test_unscoped_rest_keeps_previous_partial_collection_behavior(status):
    http = session([
        response(200, {"incidents": [{"id": "INC1"}], "more": True}),
        response(status, {}),
    ])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        assert asyncio.run(PagerDutyAPIClient("fake").get_incidents(SINCE)) == [{"id": "INC1"}]


@pytest.mark.parametrize("members, users", [([], [MEMBER]), ([MEMBER], []), ([MEMBER], [OUTSIDER])])
def test_empty_team_or_no_matching_synced_users_never_widens(members, users):
    client = PagerDutyAPIClient("fake")
    client.get_team_members = AsyncMock(return_value=members)
    with pytest.raises(PagerDutyTeamScopeError):
        asyncio.run(client.get_team_scoped_users("TEAM1", users))


@pytest.mark.parametrize("members", [None, {}, ["invalid"]])
def test_malformed_cached_roster_raises_scope_error_instead_of_generic_fallback(members):
    instance = analyzer([MEMBER])
    instance.client.get_team_members.return_value = members
    with pytest.raises(PagerDutyTeamScopeError, match="invalid team member list"):
        asyncio.run(instance._fetch_analysis_data(7))
    instance.client.get_analytics_incidents.assert_not_awaited()
    instance.client.collect_analysis_data.assert_not_awaited()


def test_valid_scope_matches_platform_id_and_case_insensitive_email():
    client = PagerDutyAPIClient("fake")
    client.get_team_members = AsyncMock(return_value=[MEMBER])
    matching = [
        {"id": "app-id", "pagerduty_user_id": "MEMBER1", "github_username": "member"},
        {"id": "other-id", "email": "MEMBER@EXAMPLE.INVALID"},
    ]
    assert asyncio.run(client.get_team_scoped_users("TEAM1", [*matching, OUTSIDER])) == matching


def test_no_synced_users_uses_verified_team_members():
    client = PagerDutyAPIClient("fake")
    client.get_team_members = AsyncMock(return_value=[MEMBER])
    assert asyncio.run(client.get_team_scoped_users("TEAM1", None)) == [MEMBER]


@pytest.mark.parametrize("reference_type", ["user_reference", "external_user_reference"])
def test_unexpanded_member_references_without_sync_fail_before_account_lookup(reference_type):
    instance = analyzer(None)
    instance.client.get_team_members.return_value = [
        {"id": "MEMBER1", "type": reference_type, "summary": "Member"}
    ]
    with pytest.raises(PagerDutyTeamScopeError, match="full profiles"):
        asyncio.run(instance._fetch_analysis_data(7))
    instance.client.get_users.assert_not_awaited()
    instance.client.get_analytics_incidents.assert_not_awaited()
    instance.client.collect_analysis_data.assert_not_awaited()


def test_collector_rest_fallback_retains_team_filter_and_roster():
    collector = PagerDutyDataCollector("fake")
    collector.client.get_team_members = AsyncMock(return_value=[MEMBER])
    collector.client.get_users = AsyncMock(return_value=[MEMBER, OUTSIDER])
    collector.client.get_analytics_incidents = AsyncMock(side_effect=PagerDutyAnalyticsUnavailable(402))
    collector.client.get_incidents = AsyncMock(return_value=[])
    result = asyncio.run(collector.collect_all_data(days_back=7, team_ids=["TEAM1"]))
    collector.client.get_users.assert_not_awaited()
    assert collector.client.get_analytics_incidents.await_args.kwargs["team_ids"] == ["TEAM1"]
    assert collector.client.get_incidents.await_args.kwargs["team_ids"] == ["TEAM1"]
    assert [user["id"] for user in result["users"]] == ["MEMBER1"]


@pytest.mark.parametrize("status", [403, 500])
def test_collector_rest_fallback_propagates_collection_failure_without_normalizing(status):
    collector = PagerDutyDataCollector("fake")
    collector.client.get_team_members = AsyncMock(return_value=[MEMBER])
    collector.client.get_analytics_incidents = AsyncMock(side_effect=PagerDutyAnalyticsUnavailable(402))
    collector.client.get_incidents = AsyncMock(side_effect=PagerDutyDataCollectionError(f"HTTP {status}"))
    collector._normalize_with_enhanced_assignment_extraction = MagicMock()
    with pytest.raises(PagerDutyDataCollectionError, match=f"HTTP {status}"):
        asyncio.run(collector.collect_all_data(7, team_ids=["TEAM1"]))
    assert collector.client.get_incidents.await_args.kwargs["team_ids"] == ["TEAM1"]
    collector._normalize_with_enhanced_assignment_extraction.assert_not_called()


def analyzer(users):
    result = UnifiedBurnoutAnalyzer.__new__(UnifiedBurnoutAnalyzer)
    result.platform = "pagerduty"
    result.pagerduty_team_id = "TEAM1"
    result.team_name = None
    result.synced_users = users
    result.client = PagerDutyAPIClient("fake")
    result.client.get_team_members = AsyncMock(return_value=[MEMBER])
    result.client.get_users = AsyncMock(return_value=[MEMBER, OUTSIDER])
    result.client.get_analytics_incidents = AsyncMock(return_value=[])
    result.client.get_incidents = AsyncMock(return_value=[])
    result.client.collect_analysis_data = AsyncMock(return_value={"users": [MEMBER, OUTSIDER], "incidents": []})
    return result


@pytest.mark.parametrize("users", [None, [MEMBER, OUTSIDER]])
def test_analyzer_preserves_team_scope_through_rest_fallback(users):
    instance = analyzer(users)
    instance.client.get_analytics_incidents.side_effect = PagerDutyAnalyticsUnavailable(403)
    result = asyncio.run(instance._fetch_analysis_data(7))
    assert result["users"] == [MEMBER]
    assert instance.client.get_incidents.await_args.kwargs["team_ids"] == ["TEAM1"]
    instance.client.collect_analysis_data.assert_not_awaited()


@pytest.mark.parametrize("users, members", [(None, []), ([], [MEMBER]), ([OUTSIDER], [MEMBER])])
def test_analyzer_does_not_turn_scope_error_into_successful_empty_or_account_report(users, members):
    instance = analyzer(users)
    instance.client.get_team_members.return_value = members
    with pytest.raises(PagerDutyTeamScopeError):
        asyncio.run(instance._fetch_analysis_data(7))
    instance.client.get_users.assert_not_awaited()
    instance.client.get_analytics_incidents.assert_not_awaited()
    instance.client.get_incidents.assert_not_awaited()
    instance.client.collect_analysis_data.assert_not_awaited()


def test_analyzer_membership_error_prevents_incident_collection():
    instance = analyzer([MEMBER, OUTSIDER])
    instance.client.get_team_members.side_effect = PagerDutyTeamScopeError("Unavailable team")
    with pytest.raises(PagerDutyTeamScopeError, match="Unavailable team"):
        asyncio.run(instance._fetch_analysis_data(7))
    instance.client.get_analytics_incidents.assert_not_awaited()
    instance.client.get_incidents.assert_not_awaited()


def test_analyzer_rest_fallback_propagates_collection_failure_instead_of_empty_success():
    instance = analyzer([MEMBER])
    instance.client.get_analytics_incidents.side_effect = PagerDutyAnalyticsUnavailable(402)
    instance.client.get_incidents.side_effect = PagerDutyDataCollectionError("HTTP 403")
    with pytest.raises(PagerDutyDataCollectionError, match="HTTP 403"):
        asyncio.run(instance._fetch_analysis_data(7))


def test_unscoped_analyzer_preserves_account_collection():
    instance = analyzer(None)
    instance.pagerduty_team_id = None
    result = asyncio.run(instance._fetch_analysis_data(7))
    assert result["users"] == [MEMBER, OUTSIDER]
    instance.client.get_team_members.assert_not_awaited()
    instance.client.collect_analysis_data.assert_awaited_once_with(days_back=7, team_ids=None)


def background_harness(monkeypatch, members):
    from app import models
    from app.api.endpoints import analyses
    from app.core import pagerduty_client

    record = MagicMock(id=101, status="pending")
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = record
    db.query.return_value.filter.return_value.first.return_value = record
    monkeypatch.setattr(models, "SessionLocal", lambda: db)

    client = PagerDutyAPIClient("fake")
    client.get_team_members = AsyncMock(return_value=members)
    client.collect_analysis_data = AsyncMock(return_value={"users": [MEMBER], "incidents": []})
    monkeypatch.setattr(pagerduty_client, "PagerDutyAPIClient", lambda token: client)

    service = MagicMock(client=client)
    service.analyze_burnout = AsyncMock(side_effect=RuntimeError("Processing failed"))
    create_service = MagicMock(return_value=service)
    monkeypatch.setattr(analyses, "UnifiedBurnoutAnalyzer", create_service)
    persist = MagicMock(return_value=True)
    monkeypatch.setattr(analyses, "_persist_analysis_result", persist)
    return analyses, client, service, create_service, persist


def run_background(analyses):
    asyncio.run(analyses.run_analysis_task(
        analysis_id=101, analysis_uuid="scope-test", integration_id=None,
        api_token="fake", platform="pagerduty", organization_name="Test",
        time_range=7, include_weekends=True, user_id=None,
        pagerduty_team_id="TEAM1", include_ai_usage=False,
    ))


@pytest.mark.parametrize("unavailable", [False, True])
def test_background_without_sync_rejects_empty_or_unavailable_team(monkeypatch, unavailable):
    analyses, client, service, create_service, persist = background_harness(monkeypatch, [])
    if unavailable:
        client.get_team_members.side_effect = PagerDutyTeamScopeError("Team unavailable")
    run_background(analyses)
    create_service.assert_not_called()
    service.analyze_burnout.assert_not_awaited()
    client.collect_analysis_data.assert_not_awaited()
    persist.assert_called_once()
    assert persist.call_args.kwargs["status"] == "failed"
    assert "results" not in persist.call_args.kwargs


def test_background_passes_team_roster_without_sync_and_preserves_scope_in_error_recovery(monkeypatch):
    analyses, client, service, create_service, persist = background_harness(monkeypatch, [MEMBER])
    run_background(analyses)
    assert create_service.call_args.kwargs["synced_users"] == [MEMBER]
    assert create_service.call_args.kwargs["pagerduty_team_id"] == "TEAM1"
    client.collect_analysis_data.assert_awaited_once_with(days_back=7, team_ids=["TEAM1"])
    persist.assert_called_once()
    assert persist.call_args.kwargs["status"] == "failed"
    assert persist.call_args.kwargs["results"]["partial_data"]["users"] == [MEMBER]


def test_background_analyzer_scope_error_does_not_attempt_partial_account_recovery(monkeypatch):
    analyses, client, service, create_service, persist = background_harness(monkeypatch, [MEMBER])
    service.analyze_burnout.side_effect = PagerDutyTeamScopeError("Team changed")
    run_background(analyses)
    client.collect_analysis_data.assert_not_awaited()
    persist.assert_called_once_with(101, status="failed", error_message="Team changed")


def test_background_collection_failure_marks_failed_without_recovery_or_results(monkeypatch):
    analyses, client, service, create_service, persist = background_harness(monkeypatch, [MEMBER])
    service.analyze_burnout.side_effect = PagerDutyDataCollectionError("HTTP 403")
    run_background(analyses)
    client.collect_analysis_data.assert_not_awaited()
    persist.assert_called_once_with(101, status="failed", error_message="HTTP 403")


@pytest.mark.parametrize("failure", [
    PagerDutyDataCollectionError("HTTP 500"), PagerDutyTeamScopeError("Incomplete roster"),
])
def test_background_recovery_collection_failure_never_persists_partial_results(monkeypatch, failure):
    analyses, client, service, create_service, persist = background_harness(monkeypatch, [MEMBER])
    client.collect_analysis_data.side_effect = failure
    run_background(analyses)
    client.collect_analysis_data.assert_awaited_once_with(days_back=7, team_ids=["TEAM1"])
    persist.assert_called_once()
    assert persist.call_args.kwargs["status"] == "failed"
    assert "results" not in persist.call_args.kwargs
