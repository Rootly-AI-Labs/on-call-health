"""Read/completion retention boundaries on a disposable PostgreSQL database.

Imported fixtures refuse normal application databases and roll test rows back.
Redis and provider collection are mocked; no live cache entries are touched.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from .test_retention_preview import (
    NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)


@pytest.fixture(autouse=True)
def isolated_clock_cache(monkeypatch):
    from app.api.endpoints import analyses

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(analyses, "datetime", Clock)
    from app.services import auto_refresh_scheduler
    monkeypatch.setattr(auto_refresh_scheduler, "datetime", Clock)
    cache = MagicMock()
    cache.get.return_value = '{"metadata":{"secret":"stale"}}'
    monkeypatch.setattr(analyses, "_get_redis_for_analysis", lambda: cache)
    return cache


@pytest.fixture
def enabled_policy(db, organizations):
    org = organizations[0]
    org.settings = {**org.settings, "data_retention": {"retention_days": 90}}
    db.commit()
    return org


@pytest.mark.parametrize("generated_at,completed_at", [(OLD, NOW), (None, None)])
def test_expired_or_unverifiable_results_cannot_be_read_from_cache(
    db, enabled_policy, analysis_factory, isolated_clock_cache, generated_at, completed_at,
):
    from app.api.endpoints.analyses import _load_analysis_data

    analysis = analysis_factory(coverage(RECENT), results_generated_at=generated_at,
                                completed_at=completed_at)
    with pytest.raises(HTTPException) as exc:
        _load_analysis_data(db, analysis.id)
    assert exc.value.status_code == 410
    isolated_clock_cache.get.assert_not_called()


def test_retained_result_bypasses_stale_cache(db, enabled_policy, analysis_factory, isolated_clock_cache):
    from app.api.endpoints.analyses import _load_analysis_data

    analysis = analysis_factory(coverage(NOW - timedelta(days=120)),
                                results_generated_at=NOW)
    result = _load_analysis_data(db, analysis.id)
    assert "secret" not in result.get("metadata", {})
    isolated_clock_cache.get.assert_not_called()


def test_running_status_does_not_expose_a_stored_snapshot(db, enabled_policy, analysis_factory):
    from app.api.endpoints.analyses import _load_analysis_data

    analysis = analysis_factory(coverage(OLD), status="running")
    with pytest.raises(HTTPException) as exc:
        _load_analysis_data(db, analysis.id)
    assert exc.value.status_code == 410


@pytest.mark.parametrize("exists", [False, True])
def test_missing_or_cleared_row_cannot_resurrect_cached_results(
    db, analysis_factory, isolated_clock_cache, exists
):
    from app.api.endpoints.analyses import _load_analysis_data

    analysis = analysis_factory(None)
    analysis_id = analysis.id
    if not exists:
        db.delete(analysis)
        db.commit()
    assert _load_analysis_data(db, analysis_id) == {}
    isolated_clock_cache.get.assert_not_called()


def test_survey_reads_enforce_age_and_organization(
    db, enabled_policy, analysis_factory, survey_factory
):
    from app.api.endpoints.analyses import get_member_surveys

    results = coverage(RECENT)
    results["team_analysis"] = {"members": [{"user_email": "same@example.com"}]}
    analysis = analysis_factory(results, time_range=365)
    survey_factory(OLD, email="same@example.com")
    recent = survey_factory(RECENT, email="same@example.com")
    survey_factory(RECENT, email="same@example.com", organization_index=1)
    surveys = get_member_surveys(analysis, db)["same@example.com"]
    assert surveys["survey_count_in_period"] == 1
    assert surveys["survey_responses"][0]["submitted_at"] == recent.submitted_at.isoformat()


def test_survey_organization_scope_even_when_retention_disabled(db, analysis_factory, survey_factory):
    from app.api.endpoints.analyses import get_member_surveys

    results = coverage(RECENT)
    results["team_analysis"] = {"members": [{"user_email": "same@example.com"}]}
    analysis = analysis_factory(results, time_range=365)
    survey_factory(RECENT, email="same@example.com", organization_index=1)
    assert get_member_surveys(analysis, db) == {}


@pytest.mark.parametrize("endpoint", ["get_user_github_daily_commits", "get_analysis_github_commits_timeline"])
def test_expired_parent_prevents_github_refetch_before_any_provider_calls(
    db, users, enabled_policy, analysis_factory, monkeypatch, endpoint
):
    from app.api.endpoints import analyses
    from app.services import github_collector

    collector = MagicMock(side_effect=AssertionError("No provider calls allowed"))
    monkeypatch.setattr(github_collector, "GitHubCollector", collector)
    analysis = analysis_factory(coverage(RECENT), results_generated_at=OLD)
    kwargs = {"analysis_id": analysis.id, "current_user": users[0], "db": db}
    if endpoint == "get_user_github_daily_commits":
        kwargs["user_email"] = "member@example.com"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(getattr(analyses, endpoint)(**kwargs))
    assert exc.value.status_code == 410
    collector.assert_not_called()


@pytest.mark.parametrize("endpoint", ["get_user_github_daily_commits", "get_analysis_github_commits_timeline"])
@pytest.mark.parametrize("policy_enabled_before", [False, True])
def test_github_old_source_payload_is_retained_for_fresh_parent_with_policy_change(
    db, users, organizations, analysis_factory, monkeypatch, endpoint,
    policy_enabled_before,
):
    from app import models
    from app.api.endpoints import analyses, github
    from app.services import github_collector

    db.add(models.GitHubIntegration(user_id=users[0].id, github_username="member", github_token="fake"))
    db.commit()
    results = coverage(RECENT)
    results["team_analysis"] = {"members": [{"user_email": "member@example.com", "github_activity": {"username": "member", "commits_count": 1}}]}
    analysis = analysis_factory(results, time_range=120, results_generated_at=NOW)
    if policy_enabled_before:
        organizations[0].settings = {"data_retention": {"retention_days": 90}}
        db.commit()

    async def collect_then_enable(**kwargs):
        organizations[0].settings = {"data_retention": {"retention_days": 90}}
        db.commit()
        return [{"date": OLD.date().isoformat(), "commits": 5, "after_hours_commits": 0, "weekend_commits": 0}]

    collector = MagicMock()
    collector.fetch_daily_commit_data = AsyncMock(side_effect=collect_then_enable)
    monkeypatch.setattr(github_collector, "GitHubCollector", lambda: collector)
    monkeypatch.setattr(github, "decrypt_token", lambda token: "fake")
    kwargs = {"analysis_id": analysis.id, "current_user": users[0], "db": db}
    if endpoint == "get_user_github_daily_commits":
        kwargs["user_email"] = "member@example.com"
    result = asyncio.run(getattr(analyses, endpoint)(**kwargs))
    assert result["status"] == "success"
    assert result["data"]["daily_commits"][0]["date"] == OLD.date().isoformat()
    call = collector.fetch_daily_commit_data.await_args.kwargs
    assert call["end_date"] - call["start_date"] == timedelta(days=120)


@pytest.mark.parametrize("endpoint", ["get_user_github_daily_commits", "get_analysis_github_commits_timeline"])
@pytest.mark.parametrize("change", ["enable_expired", "shorten_expired", "clear_result"])
def test_github_response_cannot_revive_parent_expired_or_cleared_during_collection(
    db, users, organizations, analysis_factory, monkeypatch, endpoint, change,
):
    from app import models
    from app.api.endpoints import analyses, github
    from app.services import github_collector

    db.add(models.GitHubIntegration(user_id=users[0].id, github_username="member", github_token="fake"))
    db.commit()
    payload = coverage(RECENT)
    payload["team_analysis"] = {"members": [{"user_email": "member@example.com", "github_activity": {"username": "member", "commits_count": 1}}]}
    analysis = analysis_factory(payload, results_generated_at=NOW - timedelta(days=45))
    if change == "shorten_expired":
        organizations[0].settings = {"data_retention": {"retention_days": 90}}
        db.commit()

    async def collect_and_change(**kwargs):
        organizations[0].settings = {"data_retention": {"retention_days": 30}}
        if change == "clear_result":
            analysis.results = None
        db.commit()
        return [{"date": RECENT.date().isoformat(), "commits": 5, "after_hours_commits": 0, "weekend_commits": 0}]

    collector = MagicMock()
    collector.fetch_daily_commit_data = AsyncMock(side_effect=collect_and_change)
    monkeypatch.setattr(github_collector, "GitHubCollector", lambda: collector)
    monkeypatch.setattr(github, "decrypt_token", lambda token: "fake")
    kwargs = {"analysis_id": analysis.id, "current_user": users[0], "db": db}
    if endpoint == "get_user_github_daily_commits":
        kwargs["user_email"] = "member@example.com"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(getattr(analyses, endpoint)(**kwargs))
    assert exc.value.status_code == 410
    collector.fetch_daily_commit_data.assert_awaited_once()


@pytest.mark.parametrize("result", [coverage(OLD), coverage(RECENT), {"partial_data": {}}])
def test_new_result_starts_its_lifetime_without_filtering_source_dates(
    db, db_connection, enabled_policy, analysis_factory, monkeypatch,
    result,
):
    from app import models
    from app.api.endpoints.analyses import _persist_analysis_result

    analysis = analysis_factory(None, status="running")
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    assert _persist_analysis_result(analysis.id, status="completed", results=result)
    db.refresh(analysis)
    assert analysis.status == "completed"
    assert analysis.results == result
    assert analysis.results_generated_at == NOW
    assert analysis.completed_at == NOW


def test_policy_tightened_during_collection_keeps_fresh_historical_result(
    db, db_connection, enabled_policy, analysis_factory, monkeypatch
):
    from app import models
    from app.api.endpoints.analyses import _persist_analysis_result

    analysis = analysis_factory(None, status="running")
    enabled_policy.settings = {"data_retention": {"retention_days": 30}}
    db.commit()
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    result = coverage(NOW - timedelta(days=120))
    assert _persist_analysis_result(analysis.id, status="completed", results=result)
    db.refresh(analysis)
    assert analysis.results == result
    assert analysis.status == "completed"
    assert analysis.results_generated_at == NOW


def test_failed_rerun_without_payload_does_not_renew_previous_result(
    db, db_connection, enabled_policy, analysis_factory, monkeypatch,
):
    from app import models
    from app.api.endpoints.analyses import _load_analysis_data, _persist_analysis_result

    previous = coverage(RECENT)
    analysis = analysis_factory(previous, status="running", results_generated_at=OLD,
                                completed_at=OLD)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    assert _persist_analysis_result(analysis.id, status="failed", error_message="Mock timeout")
    db.refresh(analysis)
    assert analysis.results == previous
    assert analysis.results_generated_at == OLD
    assert analysis.completed_at == NOW
    with pytest.raises(HTTPException) as exc:
        _load_analysis_data(db, analysis.id)
    assert exc.value.status_code == 410


def test_status_only_failure_preserves_known_legacy_completion_age(
    db, db_connection, enabled_policy, analysis_factory, monkeypatch,
):
    from app import models
    from app.api.endpoints.analyses import _persist_analysis_result
    from app.services.retention_preview import classify_analysis_result

    analysis = analysis_factory(coverage(RECENT), completed_at=OLD,
                                results_generated_at=None)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    assert _persist_analysis_result(analysis.id, status="failed", error_message="Mock timeout")
    db.refresh(analysis)
    assert analysis.results_generated_at == OLD
    assert analysis.completed_at == NOW
    assert classify_analysis_result(analysis, NOW - timedelta(days=90)).disposition == "expired"


@pytest.mark.parametrize("terminal_status", ["completed", "failed"])
def test_replacing_snapshot_renews_generation_only_for_new_payload(
    db, db_connection, enabled_policy, analysis_factory, monkeypatch,
    terminal_status, isolated_clock_cache,
):
    from app import models
    from app.api.endpoints.analyses import _load_analysis_data, _persist_analysis_result

    analysis = analysis_factory(coverage(OLD), status="running", results_generated_at=OLD)
    fresh = {"partial_data": {"incidents": [{"created_at": OLD.isoformat()}]}} if terminal_status == "failed" else coverage(OLD)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    assert _persist_analysis_result(analysis.id, status=terminal_status, results=fresh)
    db.refresh(analysis)
    assert analysis.results == fresh
    assert analysis.results_generated_at == NOW
    _load_analysis_data(db, analysis.id)
    isolated_clock_cache.get.assert_not_called()
    isolated_clock_cache.delete.assert_called_with(f"analysis_data:{analysis.id}")


@pytest.mark.parametrize("previous_status", ["completed", "failed"])
@pytest.mark.parametrize("redis_lock_acquired", [True, False])
def test_retention_auto_refresh_keeps_configuration_and_survey_links(
    db, db_connection, enabled_policy, analysis_factory, survey_factory, users,
    monkeypatch, previous_status, redis_lock_acquired,
):
    from app import models
    from app.services import auto_refresh_scheduler, integration_validator
    from app.core import rootly_client

    integration = models.RootlyIntegration(user_id=users[0].id, name="test", api_token="fake", platform="rootly", is_active=True)
    db.add(integration)
    db.commit()
    requested = {"include_github": True, "include_slack": True, "include_jira": True, "include_linear": True, "include_ai_usage": True}
    analysis = analysis_factory(None, status=previous_status, rootly_integration_id=integration.id,
                                is_auto_refresh=True, auto_refresh_interval="24h",
                                completed_at=NOW - timedelta(days=2), config=requested)
    analysis_id, analysis_uuid = analysis.id, analysis.uuid
    survey = survey_factory(RECENT, analysis_id=analysis.id)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))

    @asynccontextmanager
    async def acquired_lock(*args, **kwargs):
        yield redis_lock_acquired  # Missing Redis still uses database locks.

    monkeypatch.setattr(auto_refresh_scheduler, "with_distributed_lock", acquired_lock)
    primary = MagicMock()
    primary.check_permissions = AsyncMock(return_value={"incidents": {"access": True}})
    monkeypatch.setattr(rootly_client, "RootlyAPIClient", lambda *args, **kwargs: primary)
    validator = MagicMock()
    validator.validate_all_integrations = AsyncMock(return_value={
        source: {"valid": True} for source in ("github", "jira", "linear")
    })
    monkeypatch.setattr(integration_validator, "IntegrationValidator", lambda db: validator)
    dispatched = []

    def capture_task(coroutine):
        dispatched.append(coroutine)
        coroutine.close()  # Do not run real provider collection.
        return MagicMock()

    monkeypatch.setattr(auto_refresh_scheduler.asyncio, "create_task", capture_task)
    locked_tables = []

    def observe_lock_order(conn, cursor, statement, parameters, context, executemany):
        normalized = statement.lower()
        if "for share" in normalized and "from organizations" in normalized:
            locked_tables.append("organization")
        elif "for update" in normalized and "from analyses" in normalized:
            locked_tables.append("analysis")

    event.listen(db_connection, "before_cursor_execute", observe_lock_order)
    try:
        asyncio.run(auto_refresh_scheduler.check_and_run_auto_refresh_analyses("24h"))
    finally:
        event.remove(db_connection, "before_cursor_execute", observe_lock_order)
    db.refresh(analysis)
    db.refresh(survey)
    assert len(dispatched) == 1
    assert analysis.id == analysis_id and analysis.uuid == analysis_uuid
    assert survey.analysis_id == analysis_id
    assert analysis.config == requested
    assert analysis.status == "pending"
    assert analysis.results is None and analysis.completed_at is None
    assert analysis.is_auto_refresh
    assert locked_tables[:2] == ["organization", "analysis"]
    validator.validate_all_integrations.assert_awaited_once_with(user_id=users[0].id)


def test_manual_auto_refresh_rerun_retires_old_schedule_without_deleting_surveys(
    db, enabled_policy, analysis_factory, survey_factory, users, monkeypatch
):
    from fastapi import BackgroundTasks
    from app import models
    from app.api.endpoints.analyses import run_burnout_analysis
    from app.core.input_validation import AnalysisRequest
    from app.core import rootly_client

    integration = models.RootlyIntegration(user_id=users[0].id, name="test", api_token="fake", platform="rootly", is_active=True)
    db.add(integration)
    db.commit()
    original_config = {"include_github": True, "include_slack": True}
    existing = analysis_factory(coverage(RECENT), is_auto_refresh=True,
                                auto_refresh_interval="24h", config=original_config)
    old_id, old_uuid = existing.id, existing.uuid
    survey = survey_factory(RECENT, analysis_id=old_id)
    client = MagicMock()
    client.check_permissions = AsyncMock(return_value={"incidents": {"access": True}})
    monkeypatch.setattr(rootly_client, "RootlyAPIClient", lambda *args, **kwargs: client)
    tasks = BackgroundTasks()
    result = asyncio.run(run_burnout_analysis(
        req=None, request=AnalysisRequest(integration_id=integration.id, time_range=30,
                                         auto_refresh_enabled=True, auto_refresh_interval="24h"),
        background_tasks=tasks, current_user=users[0], db=db,
    ))
    db.refresh(existing)
    db.refresh(survey)
    assert result.id != old_id
    assert result.is_auto_refresh
    assert existing.uuid == old_uuid and existing.results == coverage(RECENT)
    assert not existing.is_auto_refresh and existing.config == original_config
    assert survey.analysis_id == old_id
    assert len(tasks.tasks) == 1


def test_disabled_policy_does_not_auto_retry_failed_analyses(
    db, db_connection, analysis_factory, monkeypatch
):
    from app import models
    from app.services import auto_refresh_scheduler

    analysis = analysis_factory(None, status="failed", is_auto_refresh=True,
                                auto_refresh_interval="24h", completed_at=NOW - timedelta(days=2))
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    dispatched = MagicMock()
    monkeypatch.setattr(auto_refresh_scheduler.asyncio, "create_task", dispatched)
    asyncio.run(auto_refresh_scheduler.check_and_run_auto_refresh_analyses("24h"))
    db.refresh(analysis)
    assert analysis.status == "failed"
    dispatched.assert_not_called()


def test_retention_background_task_keeps_full_window_enrichments_alerts_and_ai_usage(
    db, db_connection, enabled_policy, analysis_factory, users, monkeypatch,
):
    from app import models
    from app.api.endpoints import analyses, github, jira, rootly
    from app.core import rootly_client
    from app.services import ai_usage_collector
    from cryptography import fernet

    owner = users[0]
    integration = models.RootlyIntegration(user_id=owner.id, name="test", api_token="fake", platform="rootly", is_active=True)
    db.add_all([
        integration,
        models.GitHubIntegration(user_id=owner.id, github_username="member", github_token="encrypted-test"),
        models.JiraIntegration(user_id=owner.id, access_token="encrypted-test", jira_cloud_id="test", jira_site_url="https://test.invalid"),
        models.LinearIntegration(user_id=owner.id, access_token="linear-test", workspace_id="test"),
        models.AIUsageIntegration(user_id=owner.id, organization_id=owner.organization_id,
                                  openai_api_key="encrypted-test", openai_enabled=True),
    ])
    db.commit()
    analysis = analysis_factory(None, status="pending", time_range=120,
                                rootly_integration_id=integration.id)
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    monkeypatch.setattr(github, "decrypt_token", lambda token: "github-test")
    monkeypatch.setattr(jira, "decrypt_token", lambda token: "jira-test")
    monkeypatch.setattr(analyses.SlackTokenService, "get_oauth_token_for_user", lambda self, user: "slack-test")
    monkeypatch.setattr(rootly, "get_synced_users", AsyncMock(return_value={"users": []}))
    monkeypatch.setattr(fernet, "Fernet", lambda key: MagicMock(decrypt=lambda token: b"ai-test"))
    provider = MagicMock()
    provider.get_alerts_count = AsyncMock(return_value={"total_count": 4, "filtered_count": 4})
    monkeypatch.setattr(rootly_client, "RootlyAPIClient", lambda *args, **kwargs: provider)
    usage = AsyncMock(return_value={
        "openai": {OLD.date().isoformat(): {"total_tokens": 42}}, "anthropic": {},
    })
    monkeypatch.setattr(ai_usage_collector, "collect_ai_usage", usage)
    analyzer = MagicMock()
    analyzer.analyze_burnout = AsyncMock(return_value={
        **coverage(NOW - timedelta(days=120)), "team_analysis": {"members": []},
    })
    create_analyzer = MagicMock(return_value=analyzer)
    monkeypatch.setattr(analyses, "UnifiedBurnoutAnalyzer", create_analyzer)
    persist = analyses._persist_analysis_result
    terminal_writes = []

    def capture_terminal_write(analysis_id, **fields):
        terminal_writes.append(fields)
        return True

    # The task and terminal writer use separate production connections. Inside
    # this test's shared rollback connection, defer the write until its task
    # session closes so closing one savepoint cannot roll back another session.
    monkeypatch.setattr(analyses, "_persist_analysis_result", capture_terminal_write)

    asyncio.run(analyses.run_analysis_task(
        analysis_id=analysis.id, analysis_uuid=analysis.uuid,
        integration_id=integration.id, api_token="fake", platform="rootly",
        organization_name="Test", time_range=120, include_weekends=True,
        include_github=True, include_slack=True, include_jira=True,
        include_linear=True, include_ai_usage=True, user_id=owner.id,
    ))
    assert len(terminal_writes) == 1
    assert terminal_writes[0]["status"] == "completed"
    assert persist(analysis.id, **terminal_writes[0])
    db.refresh(analysis)
    assert analysis.status == "completed"
    assert analysis.results_generated_at == NOW
    constructor = create_analyzer.call_args.kwargs
    for source in ("github", "slack", "jira", "linear"):
        assert constructor[f"{source}_token"] == f"{source}-test"
    assert analyzer.analyze_burnout.await_args.kwargs["time_range_days"] == 120
    assert "retention_cutoff_at" not in analyzer.analyze_burnout.await_args.kwargs
    assert analysis.results["metadata"]["alerts"]["total"] == 4
    assert analysis.results["metadata"]["openai_usage"][OLD.date().isoformat()]["total_tokens"] == 42
    alerts_request = provider.get_alerts_count.await_args.kwargs
    assert alerts_request["end_date"] - alerts_request["start_date"] == timedelta(days=120)
    assert usage.await_args.kwargs["days"] == 120


@pytest.mark.parametrize("reader", ["get_analysis_status", "get_analysis_results", "get_current_analysis"])
def test_alternate_analysis_payload_readers_apply_same_parent_generation_guard(
    db, users, enabled_policy, analysis_factory, reader,
):
    from app.api.endpoints import analysis as alternate

    record = analysis_factory(coverage(RECENT), results_generated_at=OLD)
    kwargs = {"current_user": users[0], "db": db}
    if reader != "get_current_analysis":
        kwargs["analysis_id"] = record.id
    with pytest.raises(HTTPException) as exc:
        asyncio.run(getattr(alternate, reader)(**kwargs))
    assert exc.value.status_code == 410


def test_automatic_demo_snapshot_uses_creation_clock_instead_of_mock_source_dates(
    db, users, monkeypatch,
):
    from app import models
    from app.services import demo_analysis_service
    from app.api.endpoints import analyses

    monkeypatch.setattr(demo_analysis_service, "datetime", analyses.datetime)
    monkeypatch.setattr(demo_analysis_service, "_load_mock_data", lambda: {
        "analysis": {"results": coverage(OLD), "config": {}, "time_range": 120},
    })
    monkeypatch.setattr(demo_analysis_service, "_load_health_checkins_for_user", lambda *args: {
        "created": 0, "skipped": 0, "failed": 0,
    })
    assert demo_analysis_service.create_demo_analysis_for_new_user(db, users[0])
    record = db.query(models.Analysis).filter(models.Analysis.user_id == users[0].id).one()
    assert record.results == coverage(OLD)
    assert record.results_generated_at == NOW
    assert record.completed_at == NOW


@pytest.mark.parametrize("worker", ["full", "github_only"])
def test_alternate_full_snapshot_workers_use_shared_generation_writer(
    db, db_connection, enabled_policy, analysis_factory, users, monkeypatch, worker,
):
    from app import models
    from app.api.endpoints import analysis as alternate, analyses, github
    from app.services import github_collector

    owner = users[0]
    integration = models.RootlyIntegration(user_id=owner.id, name="test", api_token="fake", platform="rootly", is_active=True)
    db.add(integration)
    if worker == "github_only":
        db.add(models.GitHubIntegration(user_id=owner.id, github_username="member", github_token="fake"))
    db.commit()
    record = analysis_factory(None, status="pending", rootly_integration_id=integration.id)
    record_id = record.id
    generated = coverage(NOW - timedelta(days=120))
    analyzer = MagicMock()
    analyzer.analyze_burnout = AsyncMock(return_value=generated)
    analyzer.analyze_team_burnout = AsyncMock(return_value=generated)
    monkeypatch.setattr(alternate, "UnifiedBurnoutAnalyzer", lambda **kwargs: analyzer)
    monkeypatch.setattr(alternate, "GitHubOnlyBurnoutAnalyzer", lambda: analyzer)
    client = MagicMock()
    client.collect_analysis_data = AsyncMock(return_value={"users": [{"id": "test"}], "incidents": []})
    monkeypatch.setattr(alternate, "RootlyAPIClient", lambda *args, **kwargs: client)
    monkeypatch.setattr(alternate.SlackTokenService, "get_oauth_token_for_user", lambda *args: None)
    monkeypatch.setattr(alternate, "get_db", lambda: iter([db]))
    monkeypatch.setattr(github, "decrypt_token", lambda token: "test")
    monkeypatch.setattr(github_collector, "collect_team_github_data", AsyncMock(return_value={"test": {"commits": []}}))
    monkeypatch.setattr(models, "SessionLocal", lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"))
    writes = []
    monkeypatch.setattr(alternate, "_persist_analysis_result", lambda analysis_id, **fields: writes.append(fields) or True)

    if worker == "full":
        asyncio.run(alternate._run_analysis_task_impl(db, record.id, integration.id, 120, owner.id))
    else:
        asyncio.run(alternate.run_github_only_analysis_task(record.id, 120, [owner.email], owner.id))
    assert len(writes) == 1
    assert writes[0]["status"] == "completed"
    assert analyses._persist_analysis_result(record_id, **writes[0])
    record = db.query(models.Analysis).filter(models.Analysis.id == record_id).populate_existing().one()
    assert record.results_generated_at == NOW
    assert record.results["metadata"]["date_range"] == generated["metadata"]["date_range"]
