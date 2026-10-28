"""Queued analysis execution: claims, stale-claim reaper and task arguments.

Database tests need RETENTION_TEST_DATABASE_URL naming a disposable PostgreSQL
database containing ``retention_test``; each test rolls its rows back.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.endpoints import cron
from app.services import analysis_queue
from app.services.analysis_queue import AnalysisQueueResult, STALE_CLAIM_AFTER, mark_queued

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def test_mark_queued_sets_flags_and_drops_an_old_claim():
    config = {"include_github": True, "queue_claimed_at": "2026-10-01T00:00:00+00:00"}

    queued = mark_queued(config, enable_ai=True, include_ai_usage=False)

    assert queued == {"include_github": True, "queued": True, "enable_ai": True, "include_ai_usage": False}
    assert "queue_claimed_at" in config


@pytest.fixture(scope="module")
def queue_engine():
    database_url = os.getenv("RETENTION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set RETENTION_TEST_DATABASE_URL to a disposable PostgreSQL retention_test database")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or "retention_test" not in (url.database or "").lower():
        pytest.fail("Queue tests require PostgreSQL and a database name containing retention_test")

    from app.models import Base

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS results_generated_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS error_generated_at TIMESTAMPTZ"))
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(queue_engine):
    connection = queue_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def session_factory(db_connection):
    def factory():
        return Session(bind=db_connection, join_transaction_mode="create_savepoint")

    with patch.object(analysis_queue, "SessionLocal", factory):
        yield factory


@pytest.fixture
def integration(session_factory):
    from app.models import Organization, RootlyIntegration, User

    suffix = uuid4().hex
    with session_factory() as db:
        organization = Organization(name="Queue Org", domain=f"queue-{suffix}.example.com", slug=f"queue-{suffix}", status="active")
        db.add(organization)
        db.flush()
        user = User(email=f"queue-{suffix}@example.com", organization_id=organization.id, role="admin", status="active")
        db.add(user)
        db.flush()
        record = RootlyIntegration(user_id=user.id, name="Queue Rootly",
                                   organization_name="Queue Rootly Org", api_token="rootly_queue-token", platform="rootly")
        db.add(record)
        db.commit()
        return {"id": record.id, "user_id": user.id, "organization_id": organization.id}


def add_analysis(session_factory, integration, *, status="pending", config=None, created_at=None):
    from app.models import Analysis

    with session_factory() as db:
        analysis = Analysis(user_id=integration["user_id"], organization_id=integration["organization_id"],
                            rootly_integration_id=integration["id"], platform="rootly", time_range=30,
                            status=status, config=config)
        if created_at is not None:
            analysis.created_at = created_at
        db.add(analysis)
        db.commit()
        return analysis.id


def read(session_factory, analysis_id):
    from app.models import Analysis

    with session_factory() as db:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).one()
        return analysis.status, analysis.config, analysis.error_message


def queued(**extra):
    return mark_queued({"include_weekends": False, **extra}, enable_ai=False, include_ai_usage=True)


def test_claims_oldest_queued_pending_analysis_without_changing_status(session_factory, integration):
    add_analysis(session_factory, integration, config={"include_weekends": True})
    newer = add_analysis(session_factory, integration, config=queued(), created_at=NOW - timedelta(minutes=1))
    older = add_analysis(session_factory, integration, config=queued(), created_at=NOW - timedelta(minutes=5))
    add_analysis(session_factory, integration, status="running", config=queued(), created_at=NOW - timedelta(minutes=9))

    with session_factory() as db:
        first = analysis_queue.claim_next_queued_analysis(db, NOW)
        second = analysis_queue.claim_next_queued_analysis(db, NOW)
        third = analysis_queue.claim_next_queued_analysis(db, NOW)

    assert (first, second, third) == (older, newer, None)
    status, config, _ = read(session_factory, older)
    assert status == "pending"
    assert config["queue_claimed_at"] == NOW.isoformat()
    assert config["include_weekends"] is False


def test_reaper_fails_only_stale_claims(session_factory, integration):
    stale_at = (NOW - STALE_CLAIM_AFTER - timedelta(minutes=1)).isoformat()
    fresh_at = (NOW - timedelta(minutes=5)).isoformat()
    stale_running = add_analysis(session_factory, integration, status="running", config={**queued(), "queue_claimed_at": stale_at})
    stale_pending = add_analysis(session_factory, integration, config={**queued(), "queue_claimed_at": stale_at})
    fresh = add_analysis(session_factory, integration, status="running", config={**queued(), "queue_claimed_at": fresh_at})
    finished = add_analysis(session_factory, integration, status="completed", config={**queued(), "queue_claimed_at": stale_at})
    inline = add_analysis(session_factory, integration, status="running", config={"queue_claimed_at": stale_at})

    with session_factory() as db:
        failed = analysis_queue.fail_stale_queued_analyses(db, NOW)

    assert failed == 2
    assert read(session_factory, stale_running)[0] == read(session_factory, stale_pending)[0] == "failed"
    assert read(session_factory, stale_running)[2] == analysis_queue.STALE_ERROR_MESSAGE
    from app.models import Analysis

    with session_factory() as db:
        assert db.query(Analysis.completed_at).filter(Analysis.id == stale_running).scalar() == NOW
    assert [read(session_factory, analysis_id)[0] for analysis_id in (fresh, finished, inline)] == ["running", "completed", "running"]


def test_runs_the_task_with_stored_settings_and_the_integration_token(session_factory, integration):
    analysis_id = add_analysis(session_factory, integration, config=mark_queued(
        {"include_weekends": False, "include_github": True, "include_slack": True, "include_jira": False,
         "include_linear": True, "organization_name": "Stored Org", "pagerduty_team_id": "PT1"},
        enable_ai=True, include_ai_usage=False,
    ))

    with patch("app.api.endpoints.analyses.run_analysis_task", new=AsyncMock()) as task:
        result = asyncio.run(analysis_queue.run_next_queued_analysis(now=NOW))

    assert result == AnalysisQueueResult(ran=analysis_id, failed_stale=0)
    kwargs = task.await_args.kwargs
    assert kwargs["analysis_id"] == analysis_id
    assert kwargs["integration_id"] == integration["id"]
    assert kwargs["api_token"] == "rootly_queue-token"
    assert kwargs["platform"] == "rootly"
    assert kwargs["organization_name"] == "Stored Org"
    assert kwargs["time_range"] == 30
    assert kwargs["user_id"] == integration["user_id"]
    assert (kwargs["include_weekends"], kwargs["include_github"], kwargs["include_slack"],
            kwargs["include_jira"], kwargs["include_linear"]) == (False, True, True, False, True)
    assert (kwargs["enable_ai"], kwargs["include_ai_usage"], kwargs["pagerduty_team_id"]) == (True, False, "PT1")


def test_does_nothing_when_queue_is_empty(session_factory, integration):
    with patch("app.api.endpoints.analyses.run_analysis_task", new=AsyncMock()) as task:
        result = asyncio.run(analysis_queue.run_next_queued_analysis(now=NOW))

    assert result == AnalysisQueueResult(ran=None, failed_stale=0)
    task.assert_not_awaited()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cron.settings, "CRON_SECRET", "test-cron-secret")
    monkeypatch.setattr(cron.settings, "ANALYSIS_EXECUTION", "queue")
    app = FastAPI()
    app.include_router(cron.router, prefix="/internal/cron")
    return TestClient(app)


AUTH = {"Authorization": "Bearer test-cron-secret"}


@pytest.mark.parametrize("path", ["/internal/cron/analyses", "/internal/cron/auto-refresh"])
def test_queue_routes_refuse_inline_execution(client, monkeypatch, path):
    monkeypatch.setattr(cron.settings, "ANALYSIS_EXECUTION", "inline")
    with patch.object(cron, "run_next_queued_analysis", new=AsyncMock()) as run, \
         patch.object(cron, "check_and_run_auto_refresh_analyses", new=AsyncMock()) as check:
        response = client.get(path, headers=AUTH)

    assert response.status_code == 409
    run.assert_not_awaited()
    check.assert_not_awaited()


def test_analyses_route_runs_one_queued_analysis(client):
    with patch.object(cron, "run_next_queued_analysis", new=AsyncMock(return_value=AnalysisQueueResult(ran=7, failed_stale=1))):
        response = client.get("/internal/cron/analyses", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"ran": 7, "failed_stale": 1}


@pytest.mark.parametrize("checked,status_code", [(True, 200), (False, 500)])
def test_auto_refresh_route_reports_failed_check(client, checked, status_code):
    with patch.object(cron, "check_and_run_auto_refresh_analyses", new=AsyncMock(return_value=checked)) as check:
        response = client.get("/internal/cron/auto-refresh", headers=AUTH)

    assert response.status_code == status_code
    check.assert_awaited_once_with()
