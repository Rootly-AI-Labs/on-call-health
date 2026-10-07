"""Review regressions; database cases use guarded rollback fixtures only."""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import null, update
from sqlalchemy.orm import Session

from .test_retention_preview import (
    NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, users,
)
from .test_retention_analysis_guards import enabled_policy, isolated_clock_cache


def test_missing_organization_uses_domain_error_and_http_read_still_returns_gone(db):
    from app.services.retention_access import RetentionOrganizationMissing, organization_retention_cutoff
    from app.api.endpoints.analyses import _retention_cutoff

    with pytest.raises(RetentionOrganizationMissing):
        organization_retention_cutoff(db, -999)
    with pytest.raises(HTTPException) as error:
        _retention_cutoff(db, -999)
    assert error.value.status_code == 410


def test_missing_org_candidate_does_not_stop_healthy_refresh(
    db, db_connection, enabled_policy, organizations, users, analysis_factory, monkeypatch,
):
    from datetime import timedelta
    from app import models
    from app.core import rootly_client
    from app.services import auto_refresh_scheduler, integration_validator, retention_access

    integration = models.RootlyIntegration(user_id=users[0].id, name="Review fixture",
                                          api_token="fake", platform="rootly", is_active=True)
    db.add(integration)
    db.commit()
    broken = analysis_factory(None, organization_index=1, status="failed",
                              is_auto_refresh=True, auto_refresh_interval="24h",
                              completed_at=NOW - timedelta(days=2))
    healthy = analysis_factory(coverage(RECENT), rootly_integration_id=integration.id,
                               is_auto_refresh=True, auto_refresh_interval="24h",
                               completed_at=NOW - timedelta(days=2), config={})
    missing_id = broken.organization_id
    original = retention_access.organization_retention_cutoff

    def missing_parent(session, organization_id, **kwargs):
        if organization_id == missing_id:
            raise retention_access.RetentionOrganizationMissing("Simulated parent deletion")
        return original(session, organization_id, **kwargs)

    monkeypatch.setattr(retention_access, "organization_retention_cutoff", missing_parent)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    primary = MagicMock()
    primary.check_permissions = AsyncMock(return_value={"incidents": {"access": True}})
    monkeypatch.setattr(rootly_client, "RootlyAPIClient", lambda *args, **kwargs: primary)
    validator = MagicMock()
    validator.validate_all_integrations = AsyncMock(return_value={})
    monkeypatch.setattr(integration_validator, "IntegrationValidator", lambda *args: validator)

    @asynccontextmanager
    async def acquired(*args, **kwargs):
        yield True

    monkeypatch.setattr(auto_refresh_scheduler, "with_distributed_lock", acquired)
    dispatched = []

    def capture(task):
        dispatched.append(True)
        task.close()
        return MagicMock()

    monkeypatch.setattr(auto_refresh_scheduler.asyncio, "create_task", capture)
    asyncio.run(auto_refresh_scheduler.check_and_run_auto_refresh_analyses("24h"))
    db.refresh(healthy)
    db.refresh(broken)
    assert dispatched == [True]
    assert healthy.status == "pending"
    assert broken.status == "failed"


def test_missing_parent_terminal_write_stops_running_without_saving_new_payload(
    db, db_connection, analysis_factory, monkeypatch,
):
    from app import models
    from app.api.endpoints import analyses
    from app.services.retention_access import RetentionOrganizationMissing

    old = coverage(RECENT)
    record = analysis_factory(old, status="running", is_auto_refresh=True)
    generated = record.results_generated_at
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    monkeypatch.setattr(analyses, "organization_retention_cutoff", MagicMock(side_effect=RetentionOrganizationMissing()))
    assert not analyses._persist_analysis_result(record.id, status="completed", results={"private": "discard"})
    db.refresh(record)
    assert record.status == "failed"
    assert not record.is_auto_refresh
    assert record.error_message == "Analysis organization no longer exists."
    assert record.error_generated_at == NOW
    assert record.results == old and record.results_generated_at == generated


def test_deleted_parent_and_analysis_terminal_write_returns_false(monkeypatch):
    from app import models
    from app.api.endpoints import analyses
    from app.services.retention_access import RetentionOrganizationMissing

    session = MagicMock()
    session.query.return_value.filter.return_value.scalar.return_value = 123
    session.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
    monkeypatch.setattr(models, "SessionLocal", lambda: session)
    monkeypatch.setattr(analyses, "organization_retention_cutoff", MagicMock(side_effect=RetentionOrganizationMissing()))
    assert not analyses._persist_analysis_result(123, status="failed", error_message="ignored")
    session.commit.assert_not_called()
    session.close.assert_called_once()


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize("sql_null", [False, True])
def test_cleared_completed_reports_return_gone_even_after_disabling(
    db, organizations, users, analysis_factory, isolated_clock_cache, enabled, automatic, sql_null,
):
    from app.models import Analysis
    from app.api.endpoints.analyses import get_analysis

    organizations[0].settings = {"data_retention": {"retention_days": 90 if enabled else None}}
    db.commit()
    record = analysis_factory(None, results_generated_at=OLD, is_auto_refresh=automatic)
    if sql_null:
        db.execute(update(Analysis).where(Analysis.id == record.id).values(results=null()))
        db.commit()
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_analysis(record.id, current_user=users[0], db=db))
    assert error.value.status_code == 410
    assert error.value.detail["reason"] == "result_cleared"
    isolated_clock_cache.get.assert_not_called()


@pytest.mark.parametrize("status", ["pending", "running"])
def test_cleared_recurring_report_keeps_active_polling_metadata(
    db, enabled_policy, users, analysis_factory, status,
):
    from app.api.endpoints.analyses import get_analysis

    record = analysis_factory(None, results_generated_at=OLD, status=status, is_auto_refresh=True)
    result = asyncio.run(get_analysis(record.id, current_user=users[0], db=db))
    assert result.status == status and result.analysis_data == {}


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("results,generated", [(None, None), ({}, NOW), (coverage(RECENT), NOW)])
def test_never_generated_and_valid_empty_reports_remain_readable(
    db, organizations, users, analysis_factory, isolated_clock_cache, results, generated, enabled,
):
    from app.api.endpoints.analyses import get_analysis

    organizations[0].settings = {"data_retention": {"retention_days": 90 if enabled else None}}
    db.commit()
    isolated_clock_cache.get.return_value = None
    record = analysis_factory(results, results_generated_at=generated)
    assert asyncio.run(get_analysis(record.id, current_user=users[0], db=db)).status == "completed"


def test_error_only_failure_with_prior_generation_remains_readable(db, enabled_policy, analysis_factory):
    from app.api.endpoints.analyses import _require_retained_result

    record = analysis_factory(None, status="failed", results_generated_at=OLD,
                              error_message="Current provider error", error_generated_at=NOW)
    _require_retained_result(db, record)
