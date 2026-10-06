"""Destructive retention checks against a disposable PostgreSQL database only.

The imported fixtures enforce a PostgreSQL database name containing
``retention_test`` and roll every test back in an outer transaction. These tests
never use the application's DATABASE_URL or contact connected providers.
"""

from datetime import timedelta

import pytest
from sqlalchemy import event, select, update

from .test_retention_preview import (
    CUTOFF,
    NOW,
    OLD,
    RECENT,
    analysis_factory,
    coverage,
    db,
    db_connection,
    organizations,
    retention_engine,
    survey_factory,
    users,
)


@pytest.fixture(autouse=True)
def isolate_retention_cache(monkeypatch):
    """Disposable database IDs must never evict keys in the live Redis cache."""
    from app.services import retention_cleanup

    original = retention_cleanup._invalidate_retention_caches
    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", lambda *args: None)
    return original


@pytest.fixture
def enabled_policy(db, organizations):
    organization = organizations[0]
    organization.settings = {
        **organization.settings,
        "data_retention": {
            "retention_days": 90,
            "age_basis": "analysis_generation",
            "updated_at": (NOW - timedelta(days=1)).isoformat(),
            "updated_by_user_id": None,
        },
    }
    db.commit()
    return organization


def cleanup(db, organization, **kwargs):
    from app.services.retention_cleanup import cleanup_organization_data

    return cleanup_organization_data(db, organization.id, now=NOW, **kwargs)


def snapshot(connection):
    """Compare complete persisted data, including unrelated fixture records."""
    from app.models import Base

    return {
        table.name: list(connection.execute(select(table).order_by(*table.primary_key.columns)).mappings())
        for table in Base.metadata.sorted_tables
    }


def snapshot_without_cleanup_metadata(connection, organization_id):
    """Only the target org's outcome metadata may change on a no-op rerun."""
    from app.services.retention_status import STATUS_SETTINGS_KEY
    data = snapshot(connection)
    data["organizations"] = [
        {**row, "updated_at": None,
         "settings": {key: value for key, value in (row["settings"] or {}).items()
                      if key != STATUS_SETTINGS_KEY}}
        if row["id"] == organization_id else row
        for row in data["organizations"]
    ]
    return data


def test_disabled_policy_has_no_database_writes(
    db, db_connection, organizations, analysis_factory, survey_factory
):
    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    before = snapshot(db_connection)

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError(f"Disabled retention issued a write: {statement}")

    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        result = cleanup(db, organizations[0])
        assert result.enabled is False
        assert result.cutoff_at is None
        assert result.analysis_results_expired == result.survey_responses_deleted == 0
        assert snapshot(db_connection) == before
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)


def test_expired_entire_result_preserves_analysis_configuration_and_credentials(
    db, enabled_policy, organizations, users, analysis_factory
):
    from app.models import Analysis, RootlyIntegration, User

    integration = RootlyIntegration(
        user_id=users[0].id,
        name="Disposable integration",
        api_token="disposable-test-token",
        platform="rootly",
        is_active=True,
    )
    db.add(integration)
    db.commit()
    config = {"team_ids": ["team-1"], "include_slack": False, "custom": {"preserved": True}}
    analysis = analysis_factory(
        coverage(RECENT, generated_at=OLD, raw_incident_data=[{"created_at": OLD.isoformat()}]),
        created_at=NOW,
        rootly_integration_id=integration.id,
        integration_name=integration.name,
        platform="rootly",
        time_range=120,
        config=config,
        is_saved=True,
        is_auto_refresh=True,
        auto_refresh_interval="24h",
        error_message="Error may include historical incident content",
    )
    identity = (analysis.id, analysis.uuid, analysis.user_id, analysis.organization_id)

    result = cleanup(db, enabled_policy)
    assert result.organization_id == organizations[0].id
    assert result.enabled is True
    assert result.cutoff_at == CUTOFF
    assert result.analysis_results_expired == 1
    db.expire_all()
    preserved = db.get(Analysis, identity[0])
    assert preserved is not None
    assert preserved.results is None
    assert preserved.error_message is None
    assert (preserved.id, preserved.uuid, preserved.user_id, preserved.organization_id) == identity
    assert preserved.config == config
    assert preserved.time_range == 120
    assert preserved.rootly_integration_id == integration.id
    assert preserved.integration_name == "Disposable integration"
    assert preserved.platform == "rootly"
    assert preserved.is_saved is True
    assert preserved.is_auto_refresh is True
    assert preserved.auto_refresh_interval == "24h"
    assert db.get(RootlyIntegration, integration.id).api_token == "disposable-test-token"
    assert db.get(User, users[0].id).organization_id == organizations[0].id
    assert organizations[0].settings["unrelated"] == {"keep": True}


@pytest.mark.parametrize("generated_at,expires", [(OLD, True), (CUTOFF, False), (RECENT, False)])
def test_expiry_respects_strict_generation_cutoff(db, enabled_policy, analysis_factory, generated_at, expires):
    from app.models import Analysis

    analysis = analysis_factory(coverage(RECENT, generated_at=generated_at), created_at=NOW if expires else OLD)
    analysis_id = analysis.id
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == int(expires)
    db.expire_all()
    stored = db.get(Analysis, analysis_id)
    assert stored is not None
    assert (stored.results is None) is expires


def test_recent_four_month_report_keeps_all_enrichment_until_its_generation_expires(
    db, enabled_policy, analysis_factory, survey_factory
):
    from app.models import Analysis, UserBurnoutReport

    source_at = NOW - timedelta(days=120)
    payload = coverage(
        source_at,
        generated_at=NOW,
        raw_incident_data=[{"created_at": source_at.isoformat()}],
        github_activity={"commits": [{"committed_at": source_at.isoformat()}]},
        slack_activity={"message_count": 10},
        jira_tickets=[{"created_at": source_at.isoformat()}],
        linear_issues=[{"created_at": source_at.isoformat()}],
        openai_usage={"total_tokens": 1200},
        rootly_alerts=[{"created_at": source_at.isoformat()}],
    )
    analysis = analysis_factory(payload, created_at=OLD, completed_at=NOW, time_range=120)
    old_survey = survey_factory(OLD, analysis_id=analysis.id)
    analysis_id, survey_id = analysis.id, old_survey.id

    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == result.analyses_unverifiable == 0
    assert result.survey_responses_deleted == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results == payload
    assert db.get(UserBurnoutReport, survey_id) is None


def test_failed_refresh_cannot_extend_an_existing_result_lifetime(db, enabled_policy, analysis_factory):
    from app.models import Analysis

    analysis = analysis_factory(coverage(RECENT, generated_at=OLD), status="failed", completed_at=NOW)
    analysis_id = analysis.id
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results is None


def test_successfully_regenerated_saved_result_survives_old_row_creation(db, enabled_policy, analysis_factory):
    from app.models import Analysis

    analysis = analysis_factory(coverage(OLD), created_at=OLD, completed_at=OLD, is_saved=True)
    analysis.results = {"score": 75, "raw_incident_data": [{"created_at": OLD.isoformat()}]}
    analysis.results_generated_at = NOW
    analysis.completed_at = NOW
    db.commit()
    analysis_id, expected = analysis.id, analysis.results
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 0
    db.expire_all()
    assert db.get(Analysis, analysis_id).results == expected
    assert db.get(Analysis, analysis_id).created_at == OLD


def test_surveys_expire_independently_and_newer_links_are_detached(
    db, enabled_policy, analysis_factory, survey_factory
):
    from app.models import Analysis, UserBurnoutReport

    expired = analysis_factory(coverage(OLD))
    recent = analysis_factory(coverage(RECENT))
    old_linked_recent = survey_factory(OLD, analysis_id=recent.id)
    old_unlinked = survey_factory(OLD)
    fresh_linked_expired = survey_factory(RECENT, analysis_id=expired.id, additional_comments="keep recent feedback")
    exact_linked_expired = survey_factory(CUTOFF, analysis_id=expired.id)
    fresh_linked_recent = survey_factory(RECENT, analysis_id=recent.id)
    ids = {
        "old_linked_recent": old_linked_recent.id,
        "old_unlinked": old_unlinked.id,
        "fresh_linked_expired": fresh_linked_expired.id,
        "exact_linked_expired": exact_linked_expired.id,
        "fresh_linked_recent": fresh_linked_recent.id,
        "expired_analysis": expired.id,
        "recent_analysis": recent.id,
    }

    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 1
    assert result.survey_responses_deleted == 2
    assert result.survey_links_cleared == 2
    db.expire_all()
    assert db.get(UserBurnoutReport, ids["old_linked_recent"]) is None
    assert db.get(UserBurnoutReport, ids["old_unlinked"]) is None
    fresh = db.get(UserBurnoutReport, ids["fresh_linked_expired"])
    assert fresh.analysis_id is None
    assert fresh.additional_comments == "keep recent feedback"
    assert db.get(UserBurnoutReport, ids["exact_linked_expired"]).analysis_id is None
    assert db.get(UserBurnoutReport, ids["fresh_linked_recent"]).analysis_id == ids["recent_analysis"]
    assert db.get(Analysis, ids["recent_analysis"]).results == coverage(RECENT)
    assert db.get(Analysis, ids["expired_analysis"]).results is None


def test_expired_dependencies_removed_or_detached_without_breaking_recent_records(
    db, enabled_policy, organizations, users, analysis_factory, survey_factory
):
    from app.models import IntegrationMapping, SurveyPeriod, UserCorrelation, UserNotification, WeeklyDigestLog

    expired = analysis_factory(coverage(OLD))
    recent = analysis_factory(coverage(RECENT))
    old_survey = survey_factory(OLD)
    fresh_survey = survey_factory(RECENT)
    correlation = UserCorrelation(
        user_id=users[0].id, organization_id=organizations[0].id, email=users[0].email
    )
    db.add(correlation)
    db.flush()

    def mapping(analysis_id, identifier):
        return IntegrationMapping(
            organization_id=organizations[0].id,
            user_id=users[0].id,
            analysis_id=analysis_id,
            source_platform="rootly",
            source_identifier=identifier,
            target_platform="slack",
        )

    expired_mapping = mapping(expired.id, "old")
    fresh_mapping = mapping(recent.id, "recent")
    expired_notification = UserNotification(
        organization_id=organizations[0].id,
        user_id=users[0].id,
        analysis_id=expired.id,
        type="analysis",
        title="Expired scores",
        message="Sensitive historical score",
        action_url=f"/dashboard/analyses/{expired.uuid}",
    )
    fresh_notification = UserNotification(
        organization_id=organizations[0].id,
        user_id=users[0].id,
        analysis_id=recent.id,
        type="analysis",
        title="Recent scores",
    )

    def period(report, event_at):
        return SurveyPeriod(
            organization_id=organizations[0].id,
            user_correlation_id=correlation.id,
            user_id=users[0].id,
            email=users[0].email,
            frequency_type="daily",
            period_start_date=event_at.date(),
            period_end_date=event_at.date(),
            initial_sent_at=event_at,
            status="completed",
            response_id=report.id,
            completed_at=event_at,
        )

    old_period = period(old_survey, OLD)
    fresh_period = period(fresh_survey, RECENT)
    old_digest = WeeklyDigestLog(user_id=users[0].id, analysis_id=expired.id, week_start_date=OLD.date())
    fresh_digest = WeeklyDigestLog(user_id=users[0].id, analysis_id=recent.id, week_start_date=NOW.date())
    records = [expired_mapping, fresh_mapping, expired_notification, fresh_notification, old_period, fresh_period, old_digest, fresh_digest]
    db.add_all(records)
    db.commit()
    ids = [record.id for record in records]
    recent_analysis_id = recent.id
    fresh_survey_id = fresh_survey.id

    result = cleanup(db, enabled_policy)
    assert result.mappings_deleted == 1
    assert result.notifications_deleted == 1
    assert result.survey_period_links_cleared == 1
    assert result.digest_links_cleared == 1
    db.expire_all()
    assert db.get(IntegrationMapping, ids[0]) is None
    assert db.get(IntegrationMapping, ids[1]).analysis_id == recent_analysis_id
    assert db.get(UserNotification, ids[2]) is None
    assert db.get(UserNotification, ids[3]).analysis_id == recent_analysis_id
    assert db.get(SurveyPeriod, ids[4]).response_id is None
    assert db.get(SurveyPeriod, ids[4]).status == "completed"
    assert db.get(SurveyPeriod, ids[5]).response_id == fresh_survey_id
    assert db.get(WeeklyDigestLog, ids[6]).analysis_id is None
    assert db.get(WeeklyDigestLog, ids[7]).analysis_id == recent_analysis_id


def test_cleanup_is_scoped_to_current_organization_and_preserves_unscoped_rows(
    db, enabled_policy, organizations, analysis_factory, survey_factory
):
    from app.models import Analysis, UserBurnoutReport

    own = analysis_factory(coverage(OLD))
    other = analysis_factory(coverage(OLD), organization_index=1)
    unscoped = analysis_factory(coverage(OLD), organization_id=None)
    own_survey = survey_factory(OLD)
    other_survey = survey_factory(OLD, organization_index=1)
    unscoped_survey = survey_factory(OLD, organization_id=None)
    analysis_ids = [own.id, other.id, unscoped.id]
    survey_ids = [own_survey.id, other_survey.id, unscoped_survey.id]
    other_settings = dict(organizations[1].settings)

    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == result.survey_responses_deleted == 1
    db.expire_all()
    assert db.get(Analysis, analysis_ids[0]).results is None
    assert db.get(Analysis, analysis_ids[1]).results == coverage(OLD)
    assert db.get(Analysis, analysis_ids[2]).results == coverage(OLD)
    assert db.get(UserBurnoutReport, survey_ids[0]) is None
    assert db.get(UserBurnoutReport, survey_ids[1]) is not None
    assert db.get(UserBurnoutReport, survey_ids[2]) is not None
    assert organizations[1].settings == other_settings


@pytest.mark.parametrize("status", ["pending", "running"])
def test_in_progress_results_are_deferred(db, enabled_policy, analysis_factory, status):
    from app.models import Analysis

    analysis = analysis_factory(coverage(OLD), status=status)
    analysis_id = analysis.id
    result = cleanup(db, enabled_policy)
    assert result.analyses_deferred == 1
    assert result.analysis_results_expired == 0
    db.expire_all()
    assert db.get(Analysis, analysis_id).results == coverage(OLD)
    assert db.get(Analysis, analysis_id).status == status


def test_second_cleanup_is_safe_and_changes_nothing_further(
    db, db_connection, enabled_policy, analysis_factory, survey_factory
):
    analysis_factory(coverage(OLD))
    analysis_factory(coverage(RECENT))
    survey_factory(OLD)
    survey_factory(RECENT)
    first = cleanup(db, enabled_policy)
    assert first.analysis_results_expired == first.survey_responses_deleted == 1
    before_second = snapshot_without_cleanup_metadata(db_connection, enabled_policy.id)
    second = cleanup(db, enabled_policy)
    assert second.analysis_results_expired == second.survey_responses_deleted == 0
    assert snapshot_without_cleanup_metadata(db_connection, enabled_policy.id) == before_second
    from app.services.retention_status import read_cleanup_status
    assert read_cleanup_status(enabled_policy).counts.analysis_results_expired == 0


def test_database_failure_rolls_back_all_organization_changes(
    db, db_connection, enabled_policy, analysis_factory, survey_factory
):
    analysis_factory(coverage(OLD))
    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    before = snapshot(db_connection)
    writes = []

    def fail_second_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)
            if len(writes) == 2:
                raise RuntimeError("Injected retention database failure")

    event.listen(db_connection, "before_cursor_execute", fail_second_write)
    try:
        with pytest.raises(RuntimeError, match="Injected retention database failure"):
            cleanup(db, enabled_policy)
    finally:
        event.remove(db_connection, "before_cursor_execute", fail_second_write)

    assert len(writes) >= 2
    db.expire_all()
    assert snapshot(db_connection) == before


@pytest.mark.parametrize("results,config", [
    ({"team_health": {"score": 55}}, {}),
    (coverage(RECENT), {"include_github": True}),
    (coverage(RECENT, raw_incident_data=[{"created_at": "invalid"}]), {}),
    ("malformed historical result", {}),
])
def test_unverifiable_results_are_reported_without_destructive_guessing(
    db, enabled_policy, analysis_factory, results, config
):
    from app.models import Analysis

    analysis = analysis_factory(results, config=config, created_at=OLD, completed_at=None, results_generated_at=None)
    analysis_id = analysis.id
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 0
    assert result.analyses_unverifiable == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results == results


def test_survey_with_unknown_age_is_preserved_and_detached_from_expired_analysis(
    db, enabled_policy, analysis_factory, survey_factory
):
    from app.models import UserBurnoutReport

    analysis = analysis_factory(coverage(OLD))
    survey = survey_factory(OLD, analysis_id=analysis.id)
    survey_id = survey.id
    db.query(UserBurnoutReport).filter_by(id=survey_id).update({"submitted_at": None})
    db.commit()
    result = cleanup(db, enabled_policy)
    assert result.surveys_unverifiable == 1
    assert result.survey_responses_deleted == 0
    assert result.survey_links_cleared == 1
    db.expire_all()
    retained = db.get(UserBurnoutReport, survey_id)
    assert retained is not None
    assert retained.submitted_at is None
    assert retained.analysis_id is None


@pytest.mark.parametrize("dependency,ownership", [
    ("mapping", "other"),
    ("mapping", "null"),
    ("notification", "other"),
    ("notification", "null"),
    ("survey", "other"),
    ("survey", "null"),
    ("digest", "other"),
    ("digest", "null"),
    ("survey_period", "other"),
])
def test_conflicting_dependent_ownership_aborts_entire_organization(
    db, db_connection, enabled_policy, organizations, users,
    analysis_factory, survey_factory, dependency, ownership
):
    from app.models import IntegrationMapping, SurveyPeriod, UserCorrelation, UserNotification, WeeklyDigestLog
    from app.services.retention_cleanup import RetentionScopeConflict

    expired = analysis_factory(coverage(OLD))
    analysis_factory(coverage(OLD))
    old_survey = survey_factory(OLD)
    owner_id = organizations[1].id if ownership == "other" else None
    if dependency == "mapping":
        db.add(IntegrationMapping(
            organization_id=owner_id,
            user_id=users[1].id,
            analysis_id=expired.id,
            source_platform="rootly",
            source_identifier="unexpected-owner",
            target_platform="slack",
        ))
    elif dependency == "notification":
        db.add(UserNotification(
            organization_id=owner_id, user_id=users[1].id,
            analysis_id=expired.id, type="analysis", title="Cross-scope result",
        ))
    elif dependency == "survey":
        survey_factory(RECENT, organization_id=owner_id, organization_index=1, analysis_id=expired.id)
    elif dependency == "digest":
        if ownership == "null":
            users[1].organization_id = None
        db.add(WeeklyDigestLog(user_id=users[1].id, analysis_id=expired.id, week_start_date=OLD.date()))
    elif dependency == "survey_period":
        correlation = UserCorrelation(
            user_id=users[1].id, organization_id=organizations[1].id, email=users[1].email
        )
        db.add(correlation)
        db.flush()
        db.add(SurveyPeriod(
            organization_id=organizations[1].id,
            user_correlation_id=correlation.id,
            user_id=users[1].id,
            email=users[1].email,
            frequency_type="daily",
            period_start_date=OLD.date(),
            period_end_date=OLD.date(),
            initial_sent_at=OLD,
            status="completed",
            response_id=old_survey.id,
            completed_at=OLD,
        ))
    db.commit()
    before = snapshot(db_connection)

    with pytest.raises(RetentionScopeConflict):
        cleanup(db, enabled_policy)

    db.expire_all()
    assert snapshot(db_connection) == before


def test_cache_invalidation_precedes_mutation(
    db, enabled_policy, analysis_factory, survey_factory
):
    from app.models import Analysis, UserBurnoutReport

    expired = analysis_factory(coverage(OLD))
    expired_survey = survey_factory(OLD)
    analysis_id, survey_id = expired.id, expired_survey.id
    calls = []

    def invalidator(session, organization_id, analysis_ids):
        assert session is db
        assert organization_id == enabled_policy.id
        assert analysis_ids == [analysis_id]
        assert session.get(Analysis, analysis_id).results == coverage(OLD)
        assert session.get(UserBurnoutReport, survey_id) is not None
        calls.append(organization_id)

    cleanup(db, enabled_policy, invalidate_cache=invalidator)
    assert calls == [enabled_policy.id]
    db.expire_all()
    assert db.get(Analysis, analysis_id).results is None
    assert db.get(UserBurnoutReport, survey_id) is None


def test_cache_failure_prevents_all_database_deletion(
    db, db_connection, enabled_policy, analysis_factory, survey_factory
):
    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    before = snapshot(db_connection)

    def fail_cache(*args):
        raise RuntimeError("Injected cache invalidation failure")

    with pytest.raises(RuntimeError, match="Injected cache invalidation failure"):
        cleanup(db, enabled_policy, invalidate_cache=fail_cache)

    db.expire_all()
    assert snapshot(db_connection) == before


def test_enabled_cleanup_checks_stale_cache_even_when_results_already_empty(
    db, enabled_policy, analysis_factory
):
    analysis_factory(None)
    calls = []
    result = cleanup(db, enabled_policy, invalidate_cache=lambda *args: calls.append(args))
    assert result.analysis_results_expired == 0
    assert len(calls) == 1
    assert calls[0][1] == enabled_policy.id
    assert calls[0][2] == []


def test_disabled_cleanup_does_not_invalidate_caches(db, organizations, analysis_factory):
    analysis_factory(coverage(OLD))

    def reject_cache(*args):
        raise AssertionError("Disabled retention must not invalidate caches")

    cleanup(db, organizations[0], invalidate_cache=reject_cache)


def test_saved_policy_is_refreshed_from_database_before_cleanup(
    db, db_connection, enabled_policy, analysis_factory
):
    from app.models import Analysis, Organization

    analysis = analysis_factory(coverage(NOW - timedelta(days=45)))
    analysis_id = analysis.id
    original_days = enabled_policy.settings["data_retention"]["retention_days"]
    settings = {
        **enabled_policy.settings,
        "data_retention": {**enabled_policy.settings["data_retention"], "retention_days": 30},
    }
    # A different writer's settings update must overrule an ORM identity map's
    # earlier policy. The outer fixture transaction still isolates this SQL write.
    db_connection.execute(update(Organization).where(Organization.id == enabled_policy.id).values(settings=settings))
    assert enabled_policy.settings["data_retention"]["retention_days"] == original_days == 90

    result = cleanup(db, enabled_policy)
    assert result.cutoff_at == NOW - timedelta(days=30)
    assert result.analysis_results_expired == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results is None


@pytest.mark.parametrize("org_status", ["pending", "inactive", "suspended"])
def test_inactive_organization_cannot_run_cleanup(
    db, db_connection, enabled_policy, analysis_factory, org_status
):
    analysis_factory(coverage(OLD))
    enabled_policy.status = org_status
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises(ValueError):
        cleanup(db, enabled_policy)
    assert snapshot(db_connection) == before


def test_missing_organization_cannot_run_cleanup(db, organizations):
    from app.services.retention_cleanup import cleanup_organization_data

    with pytest.raises(ValueError):
        cleanup_organization_data(db, organizations[1].id + 1_000_000, now=NOW)


def test_naive_clock_is_rejected_without_mutation(db, db_connection, enabled_policy, analysis_factory):
    from app.services.retention_cleanup import cleanup_organization_data

    analysis_factory(coverage(OLD))
    before = snapshot(db_connection)
    with pytest.raises(ValueError):
        cleanup_organization_data(db, enabled_policy.id, now=NOW.replace(tzinfo=None))
    assert snapshot(db_connection) == before


@pytest.mark.parametrize("days", [0, -1, "90", True, 3651])
def test_corrupt_saved_policy_fails_without_deletion(
    db, db_connection, enabled_policy, analysis_factory, survey_factory, days
):
    from pydantic import ValidationError

    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    enabled_policy.settings = {
        **enabled_policy.settings,
        "data_retention": {"retention_days": days},
    }
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises(ValidationError):
        cleanup(db, enabled_policy)
    assert snapshot(db_connection) == before


def test_default_cache_eviction_covers_retained_and_empty_copies_without_other_org_keys(
    db, enabled_policy, organizations, analysis_factory, isolate_retention_cache, monkeypatch
):
    import redis

    expired = analysis_factory(coverage(OLD))
    recent = analysis_factory(coverage(RECENT))
    empty = analysis_factory(None)
    other = analysis_factory(coverage(OLD), organization_index=1)
    own_keys = {f"analysis_data:{record.id}" for record in (expired, recent, empty)}
    other_key = f"analysis_data:{other.id}"
    api_key = "api:rootly:users:disposable-token-hash"
    cached = {key: "disposable cached result" for key in own_keys | {other_key, api_key}}
    deleted_keys = []

    class FakeRedis:
        def ping(self):
            return True

        def delete(self, *keys):
            deleted_keys.extend(keys)
            for key in keys:
                cached.pop(key, None)

    monkeypatch.setenv("REDIS_URL", "redis://retention-test.invalid:6379/0")
    monkeypatch.setattr(redis, "from_url", lambda *args, **kwargs: FakeRedis())
    result = cleanup(db, enabled_policy, invalidate_cache=isolate_retention_cache)
    assert result.analysis_results_expired == 1
    assert set(deleted_keys) == own_keys
    assert set(cached) == {other_key, api_key}


def test_default_cache_eviction_is_batched_and_does_not_use_preview_sample_limit(
    db, enabled_policy, organizations, users, isolate_retention_cache, monkeypatch
):
    import redis
    from app.models import Analysis

    records = [
        Analysis(
            organization_id=organizations[0].id,
            user_id=users[0].id,
            status="completed",
            results=None,
            created_at=NOW,
        )
        for _ in range(205)
    ]
    db.add_all(records)
    db.commit()
    expected_keys = {f"analysis_data:{record.id}" for record in records}
    delete_batches = []

    class FakeRedis:
        def ping(self):
            return True

        def delete(self, *keys):
            delete_batches.append(keys)

    monkeypatch.setenv("REDIS_URL", "redis://retention-test.invalid:6379/0")
    monkeypatch.setattr(redis, "from_url", lambda *args, **kwargs: FakeRedis())
    cleanup(db, enabled_policy, invalidate_cache=isolate_retention_cache)
    assert {key for batch in delete_batches for key in batch} == expected_keys
    assert all(0 < len(batch) <= 100 for batch in delete_batches)


@pytest.mark.parametrize("failure_stage", ["connect", "ping", "delete"])
def test_configured_redis_failure_rolls_back_database_cleanup(
    db, db_connection, enabled_policy, analysis_factory, survey_factory,
    isolate_retention_cache, monkeypatch, failure_stage
):
    import redis

    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    before = snapshot(db_connection)

    class FakeRedis:
        def ping(self):
            if failure_stage == "ping":
                raise redis.exceptions.ConnectionError("Disposable Redis unavailable")
            return True

        def delete(self, *keys):
            if failure_stage == "delete":
                raise redis.exceptions.ConnectionError("Disposable Redis unavailable")

    def connect(*args, **kwargs):
        if failure_stage == "connect":
            raise redis.exceptions.ConnectionError("Disposable Redis unavailable")
        return FakeRedis()

    monkeypatch.setenv("REDIS_URL", "redis://retention-test.invalid:6379/0")
    monkeypatch.setattr(redis, "from_url", connect)
    with pytest.raises(redis.exceptions.ConnectionError, match="Disposable Redis unavailable"):
        cleanup(db, enabled_policy, invalidate_cache=isolate_retention_cache)
    assert snapshot(db_connection) == before


def test_cleanup_processes_all_expiry_candidates_across_query_batches(
    db, enabled_policy, organizations, users
):
    from app.models import Analysis, UserBurnoutReport

    analyses = [
        Analysis(
            organization_id=organizations[0].id,
            user_id=users[0].id,
            status="completed",
            results=coverage(OLD),
            created_at=NOW,
            results_generated_at=OLD,
        )
        for _ in range(503)
    ]
    surveys = [
        UserBurnoutReport(
            organization_id=organizations[0].id,
            user_id=users[0].id,
            email=f"batch-survey-{index}@example.com",
            feeling_score=3,
            workload_score=3,
            submitted_at=OLD,
            updated_at=NOW,
        )
        for index in range(503)
    ]
    db.add_all(analyses + surveys)
    db.commit()
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == result.survey_responses_deleted == 503
    db.expire_all()
    # The existing JSON column serializes Python None as JSON null, which is
    # distinct from SQL NULL. Check the decoded stored result payloads directly.
    stored = db.query(Analysis.results).filter(Analysis.organization_id == enabled_policy.id).all()
    assert len(stored) == 503
    assert all(results is None for (results,) in stored)
    assert db.query(UserBurnoutReport).filter(UserBurnoutReport.organization_id == enabled_policy.id).count() == 0
