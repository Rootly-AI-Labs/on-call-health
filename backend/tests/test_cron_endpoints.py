from contextlib import nullcontext
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import cron
from app.services import retention_scheduler
from app.services.retention_scheduler import RetentionPollResult

SECRET = "test-cron-secret"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cron.settings, "CRON_SECRET", SECRET)
    app = FastAPI()
    app.include_router(cron.router, prefix="/internal/cron")
    return TestClient(app)


def authorized():
    return {"Authorization": f"Bearer {SECRET}"}


def test_refuses_every_request_when_secret_is_unset(client, monkeypatch):
    monkeypatch.setattr(cron.settings, "CRON_SECRET", None)

    response = client.get("/internal/cron/retention", headers=authorized())

    assert response.status_code == 503


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": SECRET}])
def test_rejects_missing_or_wrong_secret(client, headers):
    with patch.object(cron, "process_due_retention_cleanups") as daily:
        response = client.get("/internal/cron/retention", headers=headers)

    assert response.status_code == 401
    daily.assert_not_called()


def test_retention_runs_daily_pass_then_retries(client):
    calls = []
    with patch.object(cron, "process_due_retention_cleanups", side_effect=lambda: calls.append("daily") or RetentionPollResult(candidates=2, succeeded=2)), \
         patch.object(cron, "process_failed_retention_retries", side_effect=lambda: calls.append("retries") or RetentionPollResult(candidates=1, failed=1)):
        response = client.get("/internal/cron/retention", headers=authorized())

    assert response.status_code == 200
    assert calls == ["daily", "retries"]
    assert response.json() == {
        "daily": {"candidates": 2, "succeeded": 2, "failed": 0, "skipped": 0, "poll_failed": False},
        "retries": {"candidates": 1, "succeeded": 0, "failed": 1, "skipped": 0, "poll_failed": False},
    }


def test_weekly_digest_runs_one_check(client):
    with patch.object(cron, "check_and_send_weekly_digests", new=AsyncMock(return_value=True)) as check:
        response = client.get("/internal/cron/weekly-digest", headers=authorized())

    assert response.status_code == 200
    check.assert_awaited_once()


def test_failed_retries_page_through_failed_orgs_in_retry_mode():
    pages = {0: [3, 7], 7: [9], 9: []}
    attempts = []

    def attempt(organization_id, **kwargs):
        attempts.append((organization_id, kwargs["mode"]))
        return "failed" if organization_id == 7 else "succeeded"

    with patch.object(retention_scheduler, "_failed_cleanup_ids", side_effect=lambda db, cursor: pages[cursor]), \
         patch.object(retention_scheduler, "process_organization_cleanup", side_effect=attempt):
        result = retention_scheduler.process_failed_retention_retries(session_factory=nullcontext)

    assert attempts == [(3, "retry"), (7, "retry"), (9, "retry")]
    assert result == RetentionPollResult(candidates=3, succeeded=2, failed=1)


def test_failed_retries_report_poll_failure_when_database_is_unavailable():
    def broken_session():
        raise RuntimeError("database down")

    with patch.object(retention_scheduler, "process_organization_cleanup") as attempt:
        result = retention_scheduler.process_failed_retention_retries(session_factory=broken_session)

    attempt.assert_not_called()
    assert result == RetentionPollResult(poll_failed=True)


@pytest.mark.parametrize("failed_pass", ["daily", "retries"])
def test_retention_returns_500_when_a_poll_fails(client, failed_pass):
    daily = RetentionPollResult(poll_failed=failed_pass == "daily")
    retries = RetentionPollResult(poll_failed=failed_pass == "retries")
    with patch.object(cron, "process_due_retention_cleanups", return_value=daily), \
         patch.object(cron, "process_failed_retention_retries", return_value=retries):
        response = client.get("/internal/cron/retention", headers=authorized())

    assert response.status_code == 500
    assert response.json()[failed_pass]["poll_failed"] is True


def test_weekly_digest_returns_500_when_the_check_fails(client):
    with patch.object(cron, "check_and_send_weekly_digests", new=AsyncMock(return_value=False)):
        response = client.get("/internal/cron/weekly-digest", headers=authorized())

    assert response.status_code == 500


def test_daily_retention_reports_poll_failure():
    def broken_session():
        raise RuntimeError("database down")

    result = retention_scheduler.process_due_retention_cleanups(session_factory=broken_session)

    assert result == RetentionPollResult(poll_failed=True)
