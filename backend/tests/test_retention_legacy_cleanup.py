"""Explicit legacy-result approvals use a disposable PostgreSQL database only.

The imported full-metadata fixtures require a PostgreSQL database name containing
``retention_test`` and roll every test's rows back. Cache eviction is mocked;
these checks never use the application's database or live Redis cache.
"""
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event

from .test_retention_preview import (
    CUTOFF, NOW, OLD, RECENT, analysis_factory, coverage, current_user,
    db, db_connection, organizations, retention_engine, survey_factory, users,
)
from .test_retention_cleanup import snapshot


PATH = "/auth/organizations/retention"
LEGACY = {"team_health": {"score": 55}, "legacy_note": "Disposable unknown-age result"}


@pytest.fixture(autouse=True)
def isolate_legacy_clock_and_cache(monkeypatch):
    from app.services import data_retention, retention_cleanup

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(data_retention, "datetime", Clock)
    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", lambda *args: None)


@pytest.fixture
def test_app(db, current_user):
    from app.api.endpoints.retention import retention_preview_now, router
    from app.auth.dependencies import get_current_active_user
    from app.models import get_db

    app = FastAPI()
    app.include_router(router, prefix=PATH)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[retention_preview_now] = lambda: NOW
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


def preview(client, days=90, *, clear_legacy=True):
    response = client.post(f"{PATH}/preview", json={
        "retention_days": days, "clear_unverifiable_analyses": clear_legacy,
    })
    assert response.status_code == 200, response.text
    return response.json()


def cleanup(db, organization, **kwargs):
    from app.services.retention_cleanup import cleanup_organization_data

    return cleanup_organization_data(db, organization.id, now=NOW, **kwargs)


def approve(client, token, *, days=90, **overrides):
    body = {
        "retention_days": days,
        "confirm_deletion": True,
        "clear_unverifiable_analyses": True,
        "confirm_legacy_deletion": True,
        "legacy_preview_token": token,
    }
    body.update(overrides)
    return client.put(PATH, json=body)


def approve_preview(client, *, days=90):
    token = preview(client, days)["legacy_cleanup"]["preview_token"]
    assert token
    response = approve(client, token, days=days)
    assert response.status_code == 200, response.text
    return response.json(), token


def legacy_status(client):
    response = client.get(PATH)
    assert response.status_code == 200, response.text
    return response.json()["legacy_cleanup"]


def assert_rejected(response, code, *, status=409):
    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code


def test_disabled_policy_keeps_legacy_data_untouched(db, organizations, analysis_factory, survey_factory):
    analysis_factory(LEGACY)
    survey_factory(OLD)
    before = snapshot(db.connection())
    result = cleanup(db, organizations[0])
    assert result.enabled is False
    assert snapshot(db.connection()) == before


def test_first_cleanup_applies_age_to_existing_data_without_waiting_n_days(
    client, db, organizations, analysis_factory, survey_factory
):
    from app.models import Analysis, UserBurnoutReport

    expired = analysis_factory(coverage(OLD), created_at=NOW)
    recent = analysis_factory(coverage(RECENT), created_at=OLD)
    old_survey = survey_factory(OLD)
    recent_survey = survey_factory(RECENT)
    ids = (expired.id, recent.id, old_survey.id, recent_survey.id)
    response = client.put(PATH, json={"retention_days": 90, "confirm_deletion": True})
    assert response.status_code == 200, response.text
    # Saving configuration is still separate from performing cleanup.
    db.expire_all()
    assert db.get(Analysis, ids[0]).results == coverage(OLD)
    assert db.get(UserBurnoutReport, ids[2]) is not None

    result = cleanup(db, organizations[0])
    assert result.analysis_results_expired == result.survey_responses_deleted == 1
    db.expire_all()
    assert db.get(Analysis, ids[0]).results is None
    assert db.get(Analysis, ids[1]).results == coverage(RECENT)
    assert db.get(UserBurnoutReport, ids[2]) is None
    assert db.get(UserBurnoutReport, ids[3]) is not None


def test_ordinary_policy_confirmation_does_not_authorize_unknown_age_cleanup(
    client, db, organizations, analysis_factory
):
    from app.models import Analysis

    legacy = analysis_factory(LEGACY, created_at=OLD)
    legacy_id = legacy.id
    response = client.put(PATH, json={"retention_days": 90, "confirm_deletion": True})
    assert response.status_code == 200, response.text
    result = cleanup(db, organizations[0])
    assert result.analyses_unverifiable == 1
    db.expire_all()
    assert db.get(Analysis, legacy_id).results == LEGACY


def test_legacy_preview_is_read_only_and_marks_exact_scoped_unknown_results(
    client, db, db_connection, analysis_factory, survey_factory
):
    from jose import jwt
    from app.models import UserBurnoutReport

    first = analysis_factory(LEGACY)
    second = analysis_factory({"team_health": {"score": 30}})
    analysis_factory(coverage(OLD))
    analysis_factory(coverage(RECENT))
    other = analysis_factory(LEGACY, organization_index=1)
    unknown_survey = survey_factory(OLD)
    db.query(UserBurnoutReport).filter_by(id=unknown_survey.id).update({"submitted_at": None})
    db.commit()
    before = snapshot(db_connection)

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError(f"Legacy preview issued a write: {statement}")

    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        result = preview(client)
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)

    assert snapshot(db_connection) == before
    summary = result["legacy_cleanup"]
    assert summary["requested"] is True
    assert summary["analysis_candidates"] == 2
    assert summary["pending_analyses"] == 0
    assert summary["unverifiable_surveys"] == 1
    assert summary["preview_token"]
    assert datetime.fromisoformat(summary["preview_expires_at"].replace("Z", "+00:00")) == NOW + timedelta(minutes=15)
    assert {sample["analysis_id"] for sample in result["samples"] if sample["will_clear_as_legacy"]} == {first.id, second.id}
    assert other.id not in {sample["analysis_id"] for sample in result["samples"]}
    claims = jwt.get_unverified_claims(summary["preview_token"])
    assert claims["analysis_count"] == 2
    assert "entries" not in claims and "results" not in claims
    assert "Disposable unknown-age result" not in str(result)


def test_normal_preview_does_not_create_legacy_authorization_token(client, analysis_factory):
    analysis_factory(LEGACY)
    result = preview(client, clear_legacy=False)
    assert result["legacy_cleanup"]["requested"] is False
    assert result["legacy_cleanup"]["preview_token"] is None
    assert not any(sample["will_clear_as_legacy"] for sample in result["samples"])


@pytest.mark.parametrize("overrides,code", [
    ({"confirm_legacy_deletion": False}, "legacy_confirmation_required"),
    ({"legacy_preview_token": None}, "legacy_preview_required"),
])
def test_legacy_clear_requires_separate_confirmation_and_reviewed_preview(
    client, db_connection, analysis_factory, overrides, code
):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    before = snapshot(db_connection)
    response = approve(client, token, **overrides)
    assert_rejected(response, code)
    assert snapshot(db_connection) == before


def test_normal_confirmation_is_still_required_when_enabling_with_legacy_clear(client, analysis_factory):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    response = approve(client, token, confirm_deletion=False)
    assert_rejected(response, "retention_confirmation_required")


@pytest.mark.parametrize("field", ["clear_unverifiable_analyses", "confirm_legacy_deletion"])
@pytest.mark.parametrize("value", [1, 0, "true", "false", None, []])
def test_legacy_flags_require_strict_booleans(client, analysis_factory, field, value):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    response = approve(client, token, **{field: value})
    assert response.status_code == 422


@pytest.mark.parametrize("role", ["member", "viewer"])
def test_non_admin_cannot_approve_legacy_clear(client, current_user, analysis_factory, role):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    current_user.role = role
    assert approve(client, token).status_code == 403


def test_non_admin_cannot_request_legacy_preview(client, current_user):
    current_user.role = "member"
    response = client.post(f"{PATH}/preview", json={"retention_days": 90, "clear_unverifiable_analyses": True})
    assert response.status_code == 403


@pytest.mark.parametrize("token", ["not-a-preview", "", "A.B.C"])
def test_invalid_legacy_preview_token_is_rejected(client, analysis_factory, token):
    analysis_factory(LEGACY)
    response = approve(client, token)
    # Empty tokens are missing receipts; other strings fail signature validation.
    assert_rejected(response, "legacy_preview_required" if token == "" else "legacy_preview_invalid")


def test_tampering_with_signed_preview_token_is_rejected(client, analysis_factory):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    # Modify a meaningful signature character rather than base64 padding bits.
    header, payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    response = approve(client, f"{header}.{payload}.{replacement}{signature[1:]}")
    assert_rejected(response, "legacy_preview_invalid")


def test_expired_preview_must_be_reviewed_again(client, test_app, analysis_factory):
    from app.api.endpoints.retention import retention_preview_now

    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    test_app.dependency_overrides[retention_preview_now] = lambda: NOW + timedelta(minutes=16)
    assert_rejected(approve(client, token), "legacy_preview_expired")


def test_preview_cannot_authorize_another_organization(
    client, current_user, organizations, analysis_factory
):
    analysis_factory(LEGACY)
    analysis_factory(LEGACY, organization_index=1)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    current_user.organization_id = organizations[1].id
    assert_rejected(approve(client, token), "legacy_preview_stale")


def test_preview_cannot_be_applied_to_another_retention_period(client, analysis_factory):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    assert_rejected(approve(client, token, days=30), "legacy_preview_stale")


def test_policy_revision_change_requires_new_legacy_preview(client, analysis_factory):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    saved = client.put(PATH, json={"retention_days": 180, "confirm_deletion": True})
    assert saved.status_code == 200, saved.text
    assert_rejected(approve(client, token), "legacy_preview_stale")


@pytest.mark.parametrize("change", ["payload", "generation", "canonical-generation", "new-candidate"])
def test_changed_preview_snapshot_is_rejected_without_saving_policy(
    client, db, db_connection, organizations, analysis_factory, change
):
    legacy = analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    if change == "payload":
        legacy.results = {"team_health": {"score": 99}}
    elif change == "generation":
        legacy.completed_at = NOW + timedelta(seconds=1)
    elif change == "canonical-generation":
        legacy.results_generated_at = NOW
    else:
        analysis_factory(LEGACY)
    db.commit()
    before = snapshot(db_connection)
    response = approve(client, token)
    assert_rejected(response, "legacy_preview_stale")
    assert snapshot(db_connection) == before
    assert "data_retention" not in organizations[0].settings


def test_approval_saves_one_time_pending_scope_without_immediate_deletion(
    client, db, organizations, analysis_factory
):
    from app.models import Analysis

    legacy = analysis_factory(LEGACY, is_saved=True, is_auto_refresh=True, auto_refresh_interval="24h")
    legacy_id = legacy.id
    saved, _ = approve_preview(client)
    status = saved["legacy_cleanup"]
    assert status["state"] == "pending"
    assert status["requested_count"] == status["pending_count"] == 1
    assert status["cleared_count"] == status["skipped_count"] == 0
    db.expire_all()
    assert db.get(Analysis, legacy_id).results == LEGACY
    assert organizations[0].settings["unrelated"] == {"keep": True}
    assert "data_retention_legacy_cleanup" in organizations[0].settings
    assert "clear_unverifiable_analyses" not in organizations[0].settings["data_retention"]


def test_first_cleanup_clears_only_approved_legacy_results_and_keeps_new_unknown_data(
    client, db, organizations, analysis_factory
):
    from app.models import Analysis

    approved = analysis_factory(LEGACY, config={"team_ids": ["keep"]}, is_saved=True, is_auto_refresh=True, auto_refresh_interval="24h")
    approved_id = approved.id
    approve_preview(client)
    new = analysis_factory(LEGACY)
    other = analysis_factory(LEGACY, organization_index=1)
    new_id, other_id = new.id, other.id
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert result.analysis_results_expired == 0
    db.expire_all()
    preserved = db.get(Analysis, approved_id)
    assert preserved.results is None
    assert preserved.config == {"team_ids": ["keep"]}
    assert preserved.is_saved is True and preserved.is_auto_refresh is True
    assert preserved.auto_refresh_interval == "24h"
    assert db.get(Analysis, new_id).results == LEGACY
    assert db.get(Analysis, other_id).results == LEGACY
    status = legacy_status(client)
    assert status["state"] == "completed"
    assert status["pending_count"] == 0
    assert status["cleared_count"] == 1
    second = cleanup(db, organizations[0])
    assert second.legacy_analysis_results_cleared == 0
    assert db.get(Analysis, new_id).results == LEGACY


@pytest.mark.parametrize("change", ["payload", "generation", "canonical-generation", "retained", "empty", "deleted"])
def test_replaced_results_do_not_inherit_one_time_approval(
    client, db, organizations, analysis_factory, change
):
    from app.models import Analysis

    legacy = analysis_factory(LEGACY)
    legacy_id = legacy.id
    approve_preview(client)
    if change == "payload":
        legacy.results = {"team_health": {"score": 99}}
    elif change == "generation":
        legacy.completed_at = NOW + timedelta(seconds=1)
    elif change == "canonical-generation":
        legacy.results_generated_at = NOW
    elif change == "retained":
        legacy.results = coverage(RECENT)
    elif change == "empty":
        legacy.results = None
    else:
        db.delete(legacy)
    db.commit()
    expected = None if change == "deleted" else db.get(Analysis, legacy_id).results
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 0
    assert result.legacy_analyses_skipped == 1
    db.expire_all()
    stored = db.get(Analysis, legacy_id)
    assert (stored.results if stored else None) == expected
    assert legacy_status(client)["state"] == "completed"


@pytest.mark.parametrize("status", ["pending", "running"])
def test_approved_unchanged_running_snapshot_defers_then_clears_when_terminal(
    client, db, organizations, analysis_factory, status
):
    from app.models import Analysis

    legacy = analysis_factory(LEGACY)
    legacy_id = legacy.id
    approve_preview(client)
    legacy.status = status
    db.commit()
    first = cleanup(db, organizations[0])
    assert first.legacy_analysis_results_cleared == 0
    assert first.legacy_analyses_deferred == 1
    db.expire_all()
    assert db.get(Analysis, legacy_id).results == LEGACY
    assert legacy_status(client)["pending_count"] == 1
    db.get(Analysis, legacy_id).status = "completed"
    db.commit()
    second = cleanup(db, organizations[0])
    assert second.legacy_analysis_results_cleared == 1
    assert legacy_status(client)["state"] == "completed"


def test_legacy_approval_never_deletes_unknown_age_surveys(
    client, db, organizations, analysis_factory, survey_factory
):
    from app.models import UserBurnoutReport

    legacy = analysis_factory(LEGACY)
    unknown = survey_factory(OLD, analysis_id=legacy.id)
    unknown_id = unknown.id
    db.query(UserBurnoutReport).filter_by(id=unknown_id).update({"submitted_at": None})
    db.commit()
    approve_preview(client)
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert result.survey_responses_deleted == 0
    assert result.surveys_unverifiable == 1
    db.expire_all()
    retained = db.get(UserBurnoutReport, unknown_id)
    assert retained is not None
    assert retained.submitted_at is None
    assert retained.analysis_id is None


def test_legacy_and_normal_expiry_share_cleanup_but_have_distinct_counts(
    client, db, organizations, analysis_factory, survey_factory
):
    analysis_factory(LEGACY)
    analysis_factory(coverage(OLD))
    analysis_factory(coverage(RECENT))
    survey_factory(OLD)
    survey_factory(RECENT)
    approve_preview(client)
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert result.analysis_results_expired == 1
    assert result.survey_responses_deleted == 1


def test_transient_cache_failure_preserves_pending_approval_for_retry(
    client, db, db_connection, organizations, analysis_factory
):
    analysis_factory(LEGACY)
    approve_preview(client)
    before = snapshot(db_connection)

    def fail_cache(*args):
        raise RuntimeError("Disposable cache failure")

    with pytest.raises(RuntimeError, match="Disposable cache failure"):
        cleanup(db, organizations[0], invalidate_cache=fail_cache)
    assert snapshot(db_connection) == before
    assert legacy_status(client)["state"] == "pending"
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert legacy_status(client)["state"] == "completed"


def test_failure_committing_approval_consumption_rolls_back_actual_result_deletion(
    client, db, db_connection, organizations, analysis_factory
):
    analysis_factory(LEGACY)
    approve_preview(client)
    before = snapshot(db_connection)

    def reject_consumption(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("UPDATE ORGANIZATIONS"):
            raise RuntimeError("Disposable approval consumption failure")

    event.listen(db_connection, "before_cursor_execute", reject_consumption)
    try:
        with pytest.raises(RuntimeError, match="Disposable approval consumption failure"):
            cleanup(db, organizations[0])
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_consumption)
    assert snapshot(db_connection) == before
    assert legacy_status(client)["state"] == "pending"
    assert cleanup(db, organizations[0]).legacy_analysis_results_cleared == 1


def test_disabling_retention_cancels_pending_legacy_approval(
    client, db, organizations, analysis_factory
):
    from app.models import Analysis

    legacy = analysis_factory(LEGACY)
    legacy_id = legacy.id
    approve_preview(client)
    disabled = client.put(PATH, json={"retention_days": None})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["legacy_cleanup"]["state"] == "cancelled"
    assert disabled.json()["legacy_cleanup"]["pending_count"] == 0
    assert cleanup(db, organizations[0]).enabled is False
    enabled_again = client.put(PATH, json={"retention_days": 90, "confirm_deletion": True})
    assert enabled_again.status_code == 200, enabled_again.text
    assert cleanup(db, organizations[0]).legacy_analysis_results_cleared == 0
    db.expire_all()
    assert db.get(Analysis, legacy_id).results == LEGACY


def test_same_reviewed_preview_cannot_be_replayed_to_reauthorize_cleanup(client, analysis_factory):
    analysis_factory(LEGACY)
    saved = client.put(PATH, json={"retention_days": 90, "confirm_deletion": True})
    assert saved.status_code == 200
    _, token = approve_preview(client)
    assert_rejected(approve(client, token), "legacy_preview_already_used")


def test_new_preview_cannot_silently_replace_an_existing_pending_approval(
    client, db_connection, analysis_factory
):
    analysis_factory(LEGACY)
    approve_preview(client)
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    before = snapshot(db_connection)
    assert_rejected(approve(client, token), "legacy_cleanup_pending")
    assert snapshot(db_connection) == before
    assert legacy_status(client)["requested_count"] == 1


def test_legacy_cleanup_uses_same_dependency_rules_and_keeps_recent_linked_feedback(
    client, db, organizations, users, analysis_factory, survey_factory
):
    from app.models import IntegrationMapping, UserBurnoutReport, UserNotification, WeeklyDigestLog

    legacy = analysis_factory(LEGACY)
    recent_survey = survey_factory(RECENT, analysis_id=legacy.id, additional_comments="Keep recent feedback")
    mapping = IntegrationMapping(
        organization_id=organizations[0].id, user_id=users[0].id,
        analysis_id=legacy.id, source_platform="rootly",
        source_identifier="disposable legacy member", target_platform="slack",
    )
    notification = UserNotification(
        organization_id=organizations[0].id, user_id=users[0].id,
        analysis_id=legacy.id, type="analysis", title="Legacy result",
    )
    digest = WeeklyDigestLog(user_id=users[0].id, analysis_id=legacy.id, week_start_date=OLD.date())
    db.add_all([mapping, notification, digest])
    db.commit()
    ids = (recent_survey.id, mapping.id, notification.id, digest.id)
    approve_preview(client)
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert result.survey_responses_deleted == 0
    assert result.survey_links_cleared == 1
    assert result.mappings_deleted == result.notifications_deleted == result.digest_links_cleared == 1
    db.expire_all()
    retained = db.get(UserBurnoutReport, ids[0])
    assert retained.additional_comments == "Keep recent feedback"
    assert retained.analysis_id is None
    assert db.get(IntegrationMapping, ids[1]) is None
    assert db.get(UserNotification, ids[2]) is None
    assert db.get(WeeklyDigestLog, ids[3]).analysis_id is None


def test_conflicting_legacy_dependencies_leave_approval_pending_and_data_unchanged(
    client, db, db_connection, organizations, users, analysis_factory
):
    from app.models import UserNotification
    from app.services.retention_cleanup import RetentionScopeConflict

    legacy = analysis_factory(LEGACY)
    db.add(UserNotification(
        organization_id=organizations[1].id, user_id=users[1].id,
        analysis_id=legacy.id, type="analysis", title="Conflicting ownership",
    ))
    db.commit()
    approve_preview(client)
    before = snapshot(db_connection)
    with pytest.raises(RetentionScopeConflict):
        cleanup(db, organizations[0])
    assert snapshot(db_connection) == before
    assert legacy_status(client)["state"] == "pending"


def test_legacy_preview_and_cleanup_cover_candidates_beyond_sample_limit(
    client, db, organizations, users
):
    from app.models import Analysis

    records = [
        Analysis(
            organization_id=organizations[0].id,
            user_id=users[0].id,
            status="completed",
            results=LEGACY,
            created_at=NOW,
            completed_at=None,
            results_generated_at=None,
        )
        for _ in range(105)
    ]
    db.add_all(records)
    db.commit()
    result = preview(client)
    assert result["legacy_cleanup"]["analysis_candidates"] == 105
    assert len(result["samples"]) == 100
    assert result["samples_truncated"] is True
    saved = approve(client, result["legacy_cleanup"]["preview_token"])
    assert saved.status_code == 200, saved.text
    assert saved.json()["legacy_cleanup"]["pending_count"] == 105
    assert cleanup(db, organizations[0]).legacy_analysis_results_cleared == 105
    db.expire_all()
    assert all(result is None for (result,) in db.query(Analysis.results).filter(
        Analysis.organization_id == organizations[0].id,
    ).all())


def test_legacy_option_cannot_be_enabled_without_a_retention_period(client, analysis_factory):
    analysis_factory(LEGACY)
    response = client.post(f"{PATH}/preview", json={
        "retention_days": None, "clear_unverifiable_analyses": True,
    })
    assert response.status_code == 422
    token = preview(client)["legacy_cleanup"]["preview_token"]
    assert approve(client, token, days=None).status_code == 422


def test_confirmation_fields_cannot_silently_apply_without_explicit_legacy_option(client, analysis_factory):
    analysis_factory(LEGACY)
    token = preview(client)["legacy_cleanup"]["preview_token"]
    assert approve(client, token, clear_unverifiable_analyses=False).status_code == 422


def test_zero_legacy_candidates_complete_without_changing_retained_data(
    client, db, organizations, analysis_factory
):
    from app.models import Analysis

    recent = analysis_factory(coverage(RECENT))
    recent_id = recent.id
    saved, _ = approve_preview(client)
    assert saved["legacy_cleanup"]["state"] == "completed"
    assert saved["legacy_cleanup"]["requested_count"] == saved["legacy_cleanup"]["pending_count"] == 0
    assert cleanup(db, organizations[0]).legacy_analysis_results_cleared == 0
    db.expire_all()
    assert db.get(Analysis, recent_id).results == coverage(RECENT)


def test_cancellation_accounts_for_remaining_entries_after_partial_cleanup(
    client, db, organizations, analysis_factory
):
    analysis_factory(LEGACY)
    changed = analysis_factory(LEGACY)
    deferred = analysis_factory(LEGACY)
    approve_preview(client)
    changed.results = {"team_health": {"score": 99}}
    deferred.status = "running"
    db.commit()
    result = cleanup(db, organizations[0])
    assert result.legacy_analysis_results_cleared == 1
    assert result.legacy_analyses_skipped == 1
    assert result.legacy_analyses_deferred == 1
    pending = legacy_status(client)
    assert pending["state"] == "pending"
    assert pending["pending_count"] == 1

    response = client.put(PATH, json={"retention_days": None})
    assert response.status_code == 200, response.text
    cancelled = response.json()["legacy_cleanup"]
    assert cancelled["state"] == "cancelled"
    assert cancelled["requested_count"] == 3
    assert cancelled["pending_count"] == 0
    assert cancelled["cleared_count"] == cancelled["skipped_count"] == cancelled["cancelled_count"] == 1
    assert cancelled["requested_count"] == sum(cancelled[field] for field in (
        "cleared_count", "skipped_count", "cancelled_count",
    ))


def test_older_zero_candidate_receipt_cannot_be_replayed_after_another_completed_approval(client):
    enabled = client.put(PATH, json={"retention_days": 90, "confirm_deletion": True})
    assert enabled.status_code == 200, enabled.text
    first = preview(client)["legacy_cleanup"]["preview_token"]
    second = preview(client)["legacy_cleanup"]["preview_token"]
    assert first != second
    for token in (first, second):
        approved = approve(client, token)
        assert approved.status_code == 200, approved.text
        assert approved.json()["legacy_cleanup"]["state"] == "completed"
        assert approved.json()["legacy_cleanup"]["requested_count"] == 0
    assert_rejected(approve(client, first), "legacy_preview_already_used")
