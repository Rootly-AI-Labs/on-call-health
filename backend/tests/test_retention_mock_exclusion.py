"""Mock analysis exclusions against a disposable PostgreSQL database only.

The shared fixtures refuse databases whose names do not contain retention_test
and roll all data back. Live caches and connected providers are never used.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import update

from .test_retention_preview import (
    CUTOFF, NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)


@pytest.fixture(autouse=True)
def isolate_clock_and_caches(monkeypatch):
    from app.api.endpoints import analyses
    from app.services import retention_cleanup

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(analyses, "datetime", Clock)
    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", lambda *args: None)
    cache = MagicMock()
    cache.get.return_value = None
    monkeypatch.setattr(analyses, "_get_redis_for_analysis", lambda: cache)
    return cache


@pytest.fixture
def enabled_policy(db, organizations):
    organization = organizations[0]
    organization.settings = {
        **organization.settings,
        "data_retention": {"retention_days": 90},
    }
    db.commit()
    return organization


def preview(db, organization, *, days=90, legacy=False):
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview

    return build_retention_preview(
        db, organization,
        RetentionPreviewRequest(retention_days=days, clear_unverifiable_analyses=legacy),
        now=NOW,
    )


def cleanup(db, organization):
    from app.services.retention_cleanup import cleanup_organization_data

    return cleanup_organization_data(db, organization.id, now=NOW)


def add_dependencies(db, organization, user, analysis):
    from app.models import IntegrationMapping, UserNotification

    mapping = IntegrationMapping(
        organization_id=organization.id, user_id=user.id, analysis_id=analysis.id,
        source_platform="rootly", source_identifier="synthetic@example.invalid",
        target_platform="github", target_identifier="synthetic-teammate",
        mapping_successful=True,
    )
    notification = UserNotification(
        organization_id=organization.id, user_id=user.id, analysis_id=analysis.id,
        type="analysis", title="Synthetic analysis result", message="Disposable sample content",
    )
    db.add_all([mapping, notification])
    db.commit()
    return mapping.id, notification.id


@pytest.mark.parametrize("status", ["completed", "failed", "running", "pending"])
@pytest.mark.parametrize("generated_at", [OLD, None])
def test_ordinary_demo_is_excluded_before_age_or_run_status(status, generated_at):
    from app.services.retention_preview import classify_analysis_result

    analysis = SimpleNamespace(
        config={"is_demo": True}, rootly_integration_id=None, status=status,
        results={"team_health": {"score": 55}}, results_generated_at=generated_at,
        completed_at=None,
    )
    eligibility = classify_analysis_result(analysis, CUTOFF)
    assert eligibility.disposition == "excluded"
    assert eligibility.reason == "mock_demo_analysis"


@pytest.mark.parametrize("days", [90, None])
def test_preview_omits_expired_and_undated_demos_from_totals_samples_and_dependencies(
    db, organizations, users, analysis_factory, days,
):
    ordinary = analysis_factory(coverage(OLD))
    old_demo = analysis_factory(coverage(OLD), config={"is_demo": True})
    undated_demo = analysis_factory(
        {"team_health": {"score": 55}}, config={"is_demo": True}, completed_at=None,
    )
    add_dependencies(db, organizations[0], users[0], old_demo)
    add_dependencies(db, organizations[0], users[0], undated_demo)
    analysis_factory(coverage(OLD), organization_index=1, config={"is_demo": True})

    result = preview(db, organizations[0], days=days)
    assert result.analyses.total == 1
    assert result.analyses.excluded == 2
    assert result.analyses.expired == int(days is not None)
    assert result.analyses.unverifiable == result.analyses.deferred == 0
    assert {sample.analysis_id for sample in result.samples} == (
        {ordinary.id} if days is not None else set()
    )
    assert result.related_records.analysis_mappings == 0
    assert result.related_records.analysis_notifications == 0
    assert result.legacy_cleanup.analysis_candidates == 0


def test_legacy_preview_and_snapshot_cannot_authorize_undated_demo(
    db, organizations, analysis_factory,
):
    from app.services.retention_legacy import collect_unverifiable_snapshot

    real_undated = analysis_factory({"team_health": {"score": 30}})
    demo = analysis_factory({"team_health": {"score": 55}}, config={"is_demo": True})
    result = preview(db, organizations[0], legacy=True)
    assert result.analyses.total == result.analyses.unverifiable == 1
    assert result.analyses.excluded == 1
    assert result.legacy_cleanup.analysis_candidates == 1
    assert {sample.analysis_id for sample in result.samples} == {real_undated.id}
    assert all(sample.analysis_id != demo.id for sample in result.samples)
    entries = collect_unverifiable_snapshot(db, organizations[0].id, CUTOFF)
    assert {entry.analysis_id for entry in entries} == {real_undated.id}


def test_cleanup_preserves_demo_payload_and_dependencies_while_expiring_real_data(
    db, enabled_policy, users, analysis_factory, survey_factory,
):
    from app.models import Analysis, IntegrationMapping, UserBurnoutReport, UserNotification

    old_payload = coverage(OLD, team_health={"score": 55})
    undated_payload = {"team_health": {"score": 30}}
    old_demo = analysis_factory(
        old_payload, config={"is_demo": True}, error_message="Synthetic sample error",
    )
    undated_demo = analysis_factory(undated_payload, config={"is_demo": True})
    real = analysis_factory(coverage(OLD))
    demo_dependencies = [
        add_dependencies(db, enabled_policy, users[0], analysis)
        for analysis in (old_demo, undated_demo)
    ]
    real_mapping_id, real_notification_id = add_dependencies(db, enabled_policy, users[0], real)
    # Responses keep their independent age rule, even when linked to a demo.
    old_survey = survey_factory(OLD, analysis_id=old_demo.id)
    recent_survey = survey_factory(RECENT, analysis_id=old_demo.id)
    ids = (old_demo.id, undated_demo.id, real.id, old_survey.id, recent_survey.id)

    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 1
    assert result.analyses_unverifiable == result.analyses_deferred == 0
    assert result.legacy_analysis_results_cleared == 0
    assert result.mappings_deleted == result.notifications_deleted == 1
    assert result.survey_responses_deleted == 1
    assert result.survey_links_cleared == 0
    db.expire_all()
    assert db.get(Analysis, ids[0]).results == old_payload
    assert db.get(Analysis, ids[0]).error_message == "Synthetic sample error"
    assert db.get(Analysis, ids[1]).results == undated_payload
    assert db.get(Analysis, ids[2]).results is None
    for mapping_id, notification_id in demo_dependencies:
        assert db.get(IntegrationMapping, mapping_id) is not None
        assert db.get(UserNotification, notification_id) is not None
    assert db.get(IntegrationMapping, real_mapping_id) is None
    assert db.get(UserNotification, real_notification_id) is None
    assert db.get(UserBurnoutReport, ids[3]) is None
    assert db.get(UserBurnoutReport, ids[4]).analysis_id == ids[0]


def test_prior_legacy_authorization_skips_and_finishes_excluded_demos(
    db, enabled_policy, users, analysis_factory,
):
    from app.models import Analysis
    from app.services.retention_legacy import (
        LegacyAnalysisEntry, LegacyCleanupAuthorization, fingerprint_analysis_result,
        legacy_cleanup_status, save_legacy_authorization,
    )

    demos = [
        analysis_factory(coverage(OLD), config={"is_demo": True}),
        analysis_factory({"team_health": {"score": 55}}, config={"is_demo": True}),
    ]
    ids = [analysis.id for analysis in demos]
    payloads = [analysis.results for analysis in demos]
    save_legacy_authorization(enabled_policy, LegacyCleanupAuthorization(
        state="pending", request_id=uuid4().hex, approved_at=NOW,
        approved_by_user_id=users[0].id, requested_count=len(demos),
        entries=[LegacyAnalysisEntry(
            analysis_id=analysis.id, result_fingerprint=fingerprint_analysis_result(analysis),
        ) for analysis in demos],
    ))
    db.commit()
    result = preview(db, enabled_policy)
    assert result.analyses.total == result.analyses.unverifiable == 0
    assert result.analyses.excluded == 2
    assert result.legacy_cleanup.analysis_candidates == 0

    outcome = cleanup(db, enabled_policy)
    assert outcome.analysis_results_expired == outcome.legacy_analysis_results_cleared == 0
    assert outcome.legacy_analyses_skipped == 2
    db.expire_all()
    assert [db.get(Analysis, analysis_id).results for analysis_id in ids] == payloads
    state = legacy_cleanup_status(enabled_policy)
    assert state.state == "completed"
    assert state.pending_count == state.cleared_count == 0
    assert state.skipped_count == 2


@pytest.mark.parametrize("config", [
    None, {}, {"is_demo": False}, {"is_demo": "true"}, {"is_demo": 1},
    {"is_demo": True, "local_retention_demo": "deliberate-retention-test"},
])
def test_malformed_markers_and_deliberate_retention_fixtures_keep_normal_expiry(
    db, enabled_policy, analysis_factory, config,
):
    from app.models import Analysis

    analysis = analysis_factory(coverage(OLD), config=config, integration_name="Demo Analysis")
    analysis_id = analysis.id
    result = preview(db, enabled_policy)
    assert result.analyses.total == result.analyses.expired == 1
    assert result.analyses.excluded == 0
    assert cleanup(db, enabled_policy).analysis_results_expired == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results is None


def test_real_integration_link_prevents_demo_marker_from_bypassing_retention(
    db, enabled_policy, users, analysis_factory,
):
    from app.models import Analysis, RootlyIntegration
    from app.api.endpoints.analyses import _require_retained_result

    integration = RootlyIntegration(
        user_id=users[0].id, name="Disposable real integration", api_token="fake-test-token",
        platform="rootly", is_active=True,
    )
    db.add(integration)
    db.commit()
    analysis = analysis_factory(
        coverage(OLD), config={"is_demo": True}, rootly_integration_id=integration.id,
    )
    analysis_id = analysis.id
    result = preview(db, enabled_policy)
    assert result.analyses.excluded == 0
    assert result.analyses.total == result.analyses.expired == 1
    with pytest.raises(HTTPException) as error:
        _require_retained_result(db, analysis)
    assert error.value.status_code == 410
    assert cleanup(db, enabled_policy).analysis_results_expired == 1
    db.expire_all()
    assert db.get(Analysis, analysis_id).results is None


@pytest.mark.parametrize("generated_at", [OLD, None])
def test_analysis_reads_serve_ordinary_demos_and_reject_expired_real_results(
    db, enabled_policy, analysis_factory, generated_at,
):
    from app.api.endpoints.analyses import _load_analysis_data

    payload = {"team_health": {"score": 55}, "metadata": {"sample": True}}
    demo = analysis_factory(
        payload, config={"is_demo": True}, results_generated_at=generated_at,
        completed_at=None,
    )
    real = analysis_factory(coverage(OLD))
    assert _load_analysis_data(db, demo.id)["team_health"] == payload["team_health"]
    with pytest.raises(HTTPException) as error:
        _load_analysis_data(db, real.id)
    assert error.value.status_code == 410


def test_read_exemption_uses_refreshed_integration_identity(
    db, enabled_policy, users, analysis_factory,
):
    from app.api.endpoints.analyses import _require_retained_result
    from app.models import Analysis, RootlyIntegration

    integration = RootlyIntegration(
        user_id=users[0].id, name="Disposable integration", api_token="fake-test-token",
        platform="rootly", is_active=True,
    )
    db.add(integration)
    db.commit()
    demo = analysis_factory(coverage(OLD), config={"is_demo": True})
    assert demo.rootly_integration_id is None
    db.execute(update(Analysis).where(Analysis.id == demo.id).values(
        rootly_integration_id=integration.id,
    ), execution_options={"synchronize_session": False})
    db.flush()
    # The identity map still has the obsolete demo identity. The read guard must
    # reload the integration link before granting an exemption.
    assert demo.rootly_integration_id is None
    with pytest.raises(HTTPException) as error:
        _require_retained_result(db, demo)
    assert error.value.status_code == 410
