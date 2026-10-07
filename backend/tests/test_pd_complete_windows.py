"""Complete incident windows, including REST pagination's provider ceiling."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.pagerduty_client import PagerDutyDataCollectionError
from .test_pd_team_scope_regressions import analytics_client, response, session

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=30)


@pytest.mark.parametrize("teams", [None, ["TEAM1"]])
def test_analytics_collects_more_than_old_analysis_limit(teams):
    http = session([])
    http.post.side_effect = [
        response(200, {"data": [{"id": str(page * 1000 + i)} for i in range(1000)],
                       "next_cursor": str(page + 1)}) for page in range(5)
    ] + [response(200, {"data": [{"id": "5000"}], "next_cursor": None})]
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        results = asyncio.run(analytics_client().get_analytics_incidents(
            START, END, limit=5000, team_ids=teams, complete_window=True,
        ))
    assert len(results) == 5001
    assert http.post.call_count == 6
    filters = http.post.call_args_list[0].kwargs["json"]["filters"]
    assert all(call.kwargs["json"]["filters"] == filters for call in http.post.call_args_list)


@pytest.mark.parametrize("teams", [None, ["TEAM1"]])
def test_rest_collects_more_than_old_analysis_limit(teams):
    http = session([
        response(200, {"incidents": [{"id": str(page * 100 + i)} for i in range(100)], "more": True})
        for page in range(50)
    ] + [response(200, {"incidents": [{"id": "5000"}], "more": False})])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        results = asyncio.run(analytics_client().get_incidents(
            START, END, limit=5000, team_ids=teams, complete_window=True,
        ))
    assert len(results) == 5001
    assert http.get.call_count == 51
    assert all(call.kwargs["params"].get("team_ids[]") == teams for call in http.get.call_args_list)


def test_rest_bisects_capped_window_and_deduplicates_inclusive_boundary():
    http = session([
        response(200, {"incidents": [{"id": "discard-capped-1"}, {"id": "discard-capped-2"}], "more": True}),
        response(200, {"incidents": [{"id": "left"}, {"id": "boundary"}], "more": False}),
        response(200, {"incidents": [{"id": "boundary"}, {"id": "right"}], "more": False}),
    ])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http), \
            patch("app.core.pagerduty_client.REST_PAGINATION_CEILING", 2):
        results = asyncio.run(analytics_client().get_incidents(START, END, team_ids=["TEAM1"]))
    assert {item["id"] for item in results} == {"left", "boundary", "right"}
    assert len(results) == 3
    parent, left, right = [call.kwargs["params"] for call in http.get.call_args_list]
    assert left["since"] == parent["since"] and right["until"] == parent["until"]
    assert left["until"] == right["since"]
    assert all(params["team_ids[]"] == ["TEAM1"] for params in (parent, left, right))


def test_rest_partitions_long_requested_history_without_truncation():
    http = session([response(200, {"incidents": [{"id": str(i)}], "more": False}) for i in range(5)])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        results = asyncio.run(analytics_client().get_incidents(
            START, START + timedelta(days=400), complete_window=True,
        ))
    assert len(results) == 5
    windows = [call.kwargs["params"] for call in http.get.call_args_list]
    assert windows[0]["since"] == "2026-01-01T00:00:00Z"
    assert windows[-1]["until"] == (START + timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert all(left["until"] == right["since"] for left, right in zip(windows, windows[1:]))


def test_rest_unsplittable_density_is_failure_not_partial_success():
    http = session([response(200, {"incidents": [{"id": "1"}, {"id": "2"}], "more": True})])
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http), \
            patch("app.core.pagerduty_client.REST_PAGINATION_CEILING", 2):
        with pytest.raises(PagerDutyDataCollectionError, match="one-second"):
            asyncio.run(analytics_client().get_incidents(START, START + timedelta(seconds=1), complete_window=True))


@pytest.mark.parametrize("api", ["analytics", "rest"])
def test_unscoped_analysis_collection_also_rejects_failed_second_page(api):
    http = session([])
    if api == "analytics":
        http.post.side_effect = [response(200, {"data": [{"id": "1"}], "next_cursor": "next"}), response(500, {})]
        collect = analytics_client().get_analytics_incidents
    else:
        http.get.side_effect = [response(200, {"incidents": [{"id": "1"}], "more": True}), response(500, {})]
        collect = analytics_client().get_incidents
    with patch("app.core.pagerduty_client.aiohttp.ClientSession", return_value=http):
        with pytest.raises(PagerDutyDataCollectionError):
            asyncio.run(collect(START, END, complete_window=True))
