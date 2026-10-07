"""Refresh preservation and error-content retention in disposable PostgreSQL.

Imported fixtures require a retention_test database and roll every row back.
Provider collection and live caches are mocked throughout.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .test_retention_preview import (
    CUTOFF, NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, users,
)
from .test_retention_cleanup import enabled_policy, isolate_retention_cache


@pytest.fixture(autouse=True)
def isolated_writers(db_connection, monkeypatch):
    from app import models
    from app.api.endpoints import analyses
    from app.services import auto_refresh_scheduler

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(analyses, "datetime", Clock)
    monkeypatch.setattr(auto_refresh_scheduler, "datetime", Clock)
    monkeypatch.setattr(analyses, "_get_redis_for_analysis", lambda: None)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(
        bind=db_connection, join_transaction_mode="create_savepoint"
    ))


@pytest.mark.parametrize("legacy_generation", [False, True])
@pytest.mark.parametrize("generation_at", [NOW - timedelta(days=2), OLD])
def test_actual_scheduler_then_failed_refresh_preserves_previous_snapshot(
    db, users, enabled_policy, analysis_factory, monkeypatch, generation_at, legacy_generation,
):
    from app.models import RootlyIntegration
    from app.core import rootly_client
    from app.services import auto_refresh_scheduler
    from app.api.endpoints.analyses import _persist_analysis_result, _require_retained_result

    integration = RootlyIntegration(user_id=users[0].id, name="Disposable refresh",
                                    api_token="fake-test-token", platform="rootly", is_active=True)
    db.add(integration)
    db.commit()
    payload = coverage(RECENT, team_health={"score": 42})
    record = analysis_factory(payload, rootly_integration_id=integration.id,
                              completed_at=generation_at,
                              results_generated_at=None if legacy_generation else generation_at,
                              is_auto_refresh=True, auto_refresh_interval="24h", config={})
    identity = record.id, record.uuid
    primary = MagicMock()
    primary.check_permissions = AsyncMock(return_value={"incidents": {"access": True}})
    monkeypatch.setattr(rootly_client, "RootlyAPIClient", lambda *args, **kwargs: primary)

    @asynccontextmanager
    async def acquired_lock(*args, **kwargs):
        yield True

    monkeypatch.setattr(auto_refresh_scheduler, "with_distributed_lock", acquired_lock)
    dispatched = []

    def capture_task(coroutine):
        dispatched.append(True)
        coroutine.close()
        return MagicMock()

    monkeypatch.setattr(auto_refresh_scheduler.asyncio, "create_task", capture_task)
    asyncio.run(auto_refresh_scheduler.check_and_run_auto_refresh_analyses("24h"))
    db.refresh(record)
    assert dispatched == [True]
    assert record.status == "pending" and record.completed_at is None
    assert record.results == payload
    assert record.results_generated_at == generation_at

    assert _persist_analysis_result(record.id, status="failed", error_message="Synthetic failed refresh")
    db.refresh(record)
    assert (record.id, record.uuid) == identity
    assert record.results == payload
    assert record.results_generated_at == generation_at
    assert record.error_generated_at == NOW
    if generation_at < CUTOFF:
        with pytest.raises(HTTPException) as error:
            _require_retained_result(db, record)
        assert error.value.status_code == 410
    else:
        _require_retained_result(db, record)


@pytest.mark.parametrize("error_at", [OLD, CUTOFF, RECENT, None])
def test_error_only_content_uses_its_own_age_for_preview_reads_and_cleanup(
    db, users, enabled_policy, analysis_factory, error_at,
):
    from app.api.endpoints.analysis import get_analysis_status
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview
    from app.services.retention_cleanup import cleanup_organization_data

    record = analysis_factory(None, status="failed", completed_at=NOW,
                              results_generated_at=NOW, error_generated_at=error_at,
                              error_message="Synthetic error content", config={"keep": True})
    preview = build_retention_preview(db, enabled_policy, RetentionPreviewRequest(), now=NOW)
    expected = "unverifiable" if error_at is None else "expired" if error_at < CUTOFF else "retained"
    assert preview.samples[0].disposition == expected
    assert getattr(preview.analyses, expected) == 1
    assert preview.analyses.empty == 0
    if expected in ("expired", "unverifiable"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(get_analysis_status(record.id, current_user=users[0], db=db))
        assert error.value.status_code == 410
    else:
        response = asyncio.run(get_analysis_status(record.id, current_user=users[0], db=db))
        assert response["error"] == "Synthetic error content"

    result = cleanup_organization_data(db, enabled_policy.id, now=NOW,
                                       invalidate_cache=lambda *args: None)
    db.refresh(record)
    assert result.analysis_results_expired == int(expected == "expired")
    assert record.results is None and record.config == {"keep": True}
    assert record.error_message == (None if expected == "expired" else "Synthetic error content")
    assert record.error_generated_at == (None if expected == "expired" else error_at)


def test_status_only_failure_does_not_renew_error_but_replacement_drops_stale_error(
    db, enabled_policy, analysis_factory,
):
    from app.api.endpoints.analyses import _persist_analysis_result, _require_retained_result

    record = analysis_factory(None, status="failed", completed_at=OLD,
                              error_generated_at=OLD, error_message="Synthetic old error")
    assert _persist_analysis_result(record.id, status="failed")
    db.refresh(record)
    assert record.completed_at == NOW and record.error_generated_at == OLD
    with pytest.raises(HTTPException) as error:
        _require_retained_result(db, record)
    assert error.value.status_code == 410
    assert _persist_analysis_result(record.id, status="completed", results={"team_health": {"score": 61}})
    db.refresh(record)
    assert record.results_generated_at == NOW
    assert record.error_message is None and record.error_generated_at is None
    _require_retained_result(db, record)


@pytest.mark.parametrize("active_status", ["pending", "running"])
@pytest.mark.parametrize("generation_at", [RECENT, OLD, None])
@pytest.mark.parametrize("reader", ["get_analysis", "get_analysis_by_uuid", "get_analysis_by_identifier"])
def test_active_refresh_returns_only_pollable_metadata_without_prior_content(
    db, users, enabled_policy, analysis_factory, monkeypatch, active_status, generation_at, reader,
):
    from app.api.endpoints import analyses

    record = analysis_factory({"private_previous_result": True}, status=active_status,
                              results_generated_at=generation_at,
                              error_message="Synthetic prior private error", error_generated_at=OLD,
                              is_saved=True, is_auto_refresh=True, auto_refresh_interval="24h")
    monkeypatch.setattr(analyses, "get_member_surveys", lambda *args: pytest.fail("Read preserved content during refresh"))
    kwargs = {"current_user": users[0], "db": db}
    if reader == "get_analysis":
        kwargs["analysis_id"] = record.id
    elif reader == "get_analysis_by_uuid":
        kwargs["analysis_uuid"] = record.uuid
    else:
        kwargs["analysis_identifier"] = record.uuid
    response = asyncio.run(getattr(analyses, reader)(**kwargs))
    assert response.status == active_status
    assert response.analysis_data == {}
    assert response.is_saved and response.is_auto_refresh
    assert "Synthetic prior private error" not in response.model_dump_json()
    db.refresh(record)
    assert record.results == {"private_previous_result": True}
    assert record.error_message == "Synthetic prior private error"


@pytest.mark.parametrize("active_status", ["pending", "running"])
@pytest.mark.parametrize("reader", ["get_analysis", "get_analysis_by_uuid", "get_analysis_by_identifier"])
def test_polling_read_returns_404_if_cleanup_deletes_row_before_metadata_refresh(
    db, db_connection, users, enabled_policy, analysis_factory, monkeypatch, active_status, reader,
):
    from app.api.endpoints import analyses
    from app.services.retention_cleanup import cleanup_organization_data

    record = analysis_factory({"private_previous_result": True}, status=active_status,
                              results_generated_at=OLD, is_saved=True)
    record_id, record_uuid, org_id = record.id, record.uuid, record.organization_id
    original_cutoff = analyses._retention_cutoff
    interleaved = False

    def finish_then_cleanup(session, organization_id, *, lock=False):
        nonlocal interleaved
        if not interleaved:
            interleaved = True
            assert analyses._persist_analysis_result(record_id, status="failed",
                                                     error_message="Synthetic failed refresh")
            # A separate session leaves the reader's pending instance stale.
            # The shared connection is guarded by the rollback-only test fixture.
            with Session(bind=db_connection, join_transaction_mode="create_savepoint") as worker:
                result = cleanup_organization_data(worker, org_id, now=NOW)
                assert result.analysis_results_expired == 1
        return original_cutoff(session, organization_id, lock=lock)

    monkeypatch.setattr(analyses, "_retention_cutoff", finish_then_cleanup)
    kwargs = {"current_user": users[0], "db": db}
    if reader == "get_analysis":
        kwargs["analysis_id"] = record_id
    elif reader == "get_analysis_by_uuid":
        kwargs["analysis_uuid"] = record_uuid
    else:
        kwargs["analysis_identifier"] = record_uuid
    with pytest.raises(HTTPException) as error:
        asyncio.run(getattr(analyses, reader)(**kwargs))
    assert error.value.status_code == 404


def test_error_timestamp_changes_invalidate_legacy_snapshot_approval(db, analysis_factory):
    from app.services.retention_legacy import fingerprint_analysis_result

    record = analysis_factory({"unknown_result": True}, error_message="Synthetic same error",
                              error_generated_at=OLD)
    before = fingerprint_analysis_result(record)
    record.error_generated_at = RECENT
    assert fingerprint_analysis_result(record) != before


def test_error_migration_backfills_only_known_failed_run_dates(db, analysis_factory):
    from migrations.migration_runner import MigrationRunner

    failed = analysis_factory(None, status="failed", completed_at=OLD, error_message="Known old failure")
    unknown = analysis_factory(None, status="failed", completed_at=None, error_message="Unknown failure")
    stale = analysis_factory(None, status="completed", completed_at=NOW, error_message="Unverified stale error")
    canonical = analysis_factory(None, status="failed", completed_at=OLD,
                                 error_message="Already dated error", error_generated_at=RECENT)
    empty = analysis_factory(None, status="failed", completed_at=OLD, error_message="")
    records = [failed, unknown, stale, canonical, empty]
    payloads = [record.error_message for record in records]
    runner = MigrationRunner.__new__(MigrationRunner)
    commands = runner.load_sql_file("2026_10_06_add_analysis_error_generated_at.sql")
    assert len(commands) == 3
    for _ in range(2):
        for command in commands:
            db.execute(text(command))
        db.commit()
        for record in records:
            db.refresh(record)
        assert failed.error_generated_at == OLD
        assert unknown.error_generated_at is None and stale.error_generated_at is None
        assert canonical.error_generated_at == RECENT and empty.error_generated_at is None
        assert [record.error_message for record in records] == payloads
