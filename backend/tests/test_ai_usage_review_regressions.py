"""Permission and pagination regressions for the OpenAI usage integration."""
import asyncio
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from app.api.endpoints import ai_usage
from app.models import AIUsageIntegration, User
from app.services import ai_usage_collector as collector


def test_openai_directory_denies_org_member_before_lookup_or_provider_access(monkeypatch):
    user = User(id=1, organization_id=10, role="member")
    db = MagicMock()
    lookup = MagicMock()
    decrypt = MagicMock()
    fetch_members = AsyncMock()
    monkeypatch.setattr(ai_usage, "_get_integration", lookup)
    monkeypatch.setattr(ai_usage, "_decrypt", decrypt)
    monkeypatch.setattr(collector, "fetch_openai_members", fetch_members)

    with pytest.raises(HTTPException) as error:
        asyncio.run(ai_usage.get_openai_members(current_user=user, db=db))

    assert error.value.status_code == 403
    lookup.assert_not_called()
    db.query.assert_not_called()
    decrypt.assert_not_called()
    fetch_members.assert_not_awaited()


@pytest.mark.parametrize("organization_id,role", [(10, "admin"), (None, "member")])
def test_openai_directory_allows_org_admin_and_personal_owner(monkeypatch, organization_id, role):
    user = User(id=1, organization_id=organization_id, role=role)
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.first.return_value = SimpleNamespace(
        has_openai=True, openai_api_key="encrypted-test-key"
    )
    decrypt = MagicMock(return_value="test-provider-key")
    fetch_members = AsyncMock(return_value={
        "user-b": "b@example.com", "user-a": "a@example.com"
    })
    monkeypatch.setattr(ai_usage, "_decrypt", decrypt)
    monkeypatch.setattr(collector, "fetch_openai_members", fetch_members)

    result = asyncio.run(ai_usage.get_openai_members(current_user=user, db=db))

    assert result == {"members": [
        {"id": "user-a", "email": "a@example.com"},
        {"id": "user-b", "email": "b@example.com"},
    ]}
    db.query.assert_called_once_with(AIUsageIntegration)
    filters = query.filter.call_args.args
    if organization_id is not None:
        assert len(filters) == 1
        assert filters[0].compare(AIUsageIntegration.organization_id == organization_id)
    else:
        assert len(filters) == 2
        assert filters[0].compare(AIUsageIntegration.user_id == user.id)
        assert filters[1].compare(AIUsageIntegration.organization_id.is_(None))
    decrypt.assert_called_once_with("encrypted-test-key")
    fetch_members.assert_awaited_once_with("test-provider-key")


def _mock_usage_pages(monkeypatch, pages):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=[httpx.Response(200, json=page) for page in pages])
    monkeypatch.setattr(collector.httpx, "AsyncClient", lambda **kwargs: client)
    return client


def _usage_page(day, results, next_page):
    return {
        "data": [{"start_time": collector._date_to_unix(day), "results": results}],
        "next_page": next_page,
    }


def _assert_usage_requests(client, expected_params):
    assert client.get.await_count == 3
    for request, page in zip(client.get.await_args_list, (None, "page-2", "page-3")):
        assert request.args == ("https://api.openai.com/v1/organization/usage/completions",)
        params = expected_params if page is None else {**expected_params, "page": page}
        assert request.kwargs["params"] == params
        assert request.kwargs["headers"] == {
            "Authorization": "Bearer test-provider-key",
            "Content-Type": "application/json",
            "OpenAI-Organization": "org-test",
        }


@pytest.mark.parametrize("days", [30, 60])
def test_openai_team_usage_keeps_filters_and_accumulates_all_pages(monkeypatch, days):
    today = date(2026, 10, 6)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(collector, "date", FixedDate)
    day_one, day_two = today - timedelta(days=1), today
    client = _mock_usage_pages(monkeypatch, [
        _usage_page(day_one, [{"input_tokens": 10, "output_tokens": 5, "num_model_requests": 1}], "page-2"),
        _usage_page(day_one, [{"input_tokens": 20, "output_tokens": 7, "num_model_requests": 2}], "page-3"),
        _usage_page(day_two, [{"input_tokens": 40, "output_tokens": 10, "num_model_requests": 3}], None),
    ])

    result = asyncio.run(collector.fetch_openai_usage("test-provider-key", " org-test ", days))

    assert result == {
        day_one.isoformat(): {"input_tokens": 30, "output_tokens": 12, "total_tokens": 42, "requests": 3},
        day_two.isoformat(): {"input_tokens": 40, "output_tokens": 10, "total_tokens": 50, "requests": 3},
    }
    _assert_usage_requests(client, {
        "start_time": collector._date_to_unix(today - timedelta(days=days - 1)),
        "end_time": collector._date_to_unix(today + timedelta(days=1)),
        "bucket_width": "1d",
        "limit": min(days, 31),
    })


@pytest.mark.parametrize("days", [30, 60])
def test_openai_per_user_usage_keeps_grouping_and_mapping_across_pages(monkeypatch, days):
    today = date(2026, 10, 6)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return today

    monkeypatch.setattr(collector, "date", FixedDate)
    fetch_members = AsyncMock()
    monkeypatch.setattr(collector, "fetch_openai_members", fetch_members)
    day_one, day_two = today - timedelta(days=1), today
    client = _mock_usage_pages(monkeypatch, [
        _usage_page(day_one, [
            {"user_id": "user-a", "input_tokens": 10, "output_tokens": 5, "num_model_requests": 1},
        ], "page-2"),
        _usage_page(day_one, [
            {"user_id": "user-a", "input_tokens": 20, "output_tokens": 7, "num_model_requests": 2},
            {"user_id": "user-b", "input_tokens": 5, "output_tokens": 3, "num_model_requests": 1},
            {"user_id": "unknown-user", "input_tokens": 1000, "output_tokens": 1000, "num_model_requests": 100},
        ], "page-3"),
        _usage_page(day_two, [
            {"user_id": "user-b", "input_tokens": 40, "output_tokens": 10, "num_model_requests": 3},
        ], None),
    ])

    result = asyncio.run(collector.fetch_openai_usage_per_user(
        "test-provider-key", " org-test ", days,
        {"user-a": "a@example.com", "user-b": "b@example.com"},
    ))

    assert result == {
        "a@example.com": {
            day_one.isoformat(): {"input_tokens": 30, "output_tokens": 12, "total_tokens": 42, "requests": 3},
        },
        "b@example.com": {
            day_one.isoformat(): {"input_tokens": 5, "output_tokens": 3, "total_tokens": 8, "requests": 1},
            day_two.isoformat(): {"input_tokens": 40, "output_tokens": 10, "total_tokens": 50, "requests": 3},
        },
    }
    fetch_members.assert_not_awaited()
    _assert_usage_requests(client, {
        "start_time": collector._date_to_unix(today - timedelta(days=days - 1)),
        "end_time": collector._date_to_unix(today + timedelta(days=1)),
        "bucket_width": "1d",
        "limit": min(days, 31),
        "group_by": "user_id",
    })
