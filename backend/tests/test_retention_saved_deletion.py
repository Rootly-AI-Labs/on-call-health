"""Full saved-report expiry in the guarded, rollback-only retention database."""
from datetime import timedelta

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from .test_retention_preview import (
    CUTOFF, NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)
from .test_retention_cleanup import cleanup, enabled_policy, isolate_retention_cache, snapshot


@pytest.mark.parametrize("saved,auto_refresh", [(True, False), (True, True), (False, False), (False, True)])
def test_only_expired_manual_saved_records_are_fully_deleted(
    db, enabled_policy, analysis_factory, saved, auto_refresh,
):
    from app.models import Analysis

    record = analysis_factory(coverage(RECENT, generated_at=OLD), is_saved=saved,
                              is_auto_refresh=auto_refresh, config={"team_ids": ["team-1"]},
                              auto_refresh_interval="24h" if auto_refresh else None)
    record_id = record.id
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == 1
    db.expire_all()
    stored = db.get(Analysis, record_id)
    if saved and not auto_refresh:
        assert stored is None
    else:
        assert stored.results is None
        assert stored.config == {"team_ids": ["team-1"]}
        assert stored.is_auto_refresh is auto_refresh
        assert stored.auto_refresh_interval == ("24h" if auto_refresh else None)


@pytest.mark.parametrize("submitted_at", [OLD, RECENT, CUTOFF, None])
def test_linked_surveys_keep_their_own_age_when_saved_parent_is_deleted(
    db, enabled_policy, analysis_factory, survey_factory, submitted_at,
):
    from app.models import Analysis, UserBurnoutReport

    record = analysis_factory(coverage(OLD), is_saved=True)
    response = survey_factory(submitted_at, analysis_id=record.id)
    if submitted_at is None:
        # INSERT's server default supplies now; model a genuinely undated
        # legacy response by explicitly clearing the persisted timestamp.
        response.submitted_at = None
        db.commit()
    record_id, response_id = record.id, response.id
    result = cleanup(db, enabled_policy)
    db.expire_all()
    assert db.get(Analysis, record_id) is None
    stored = db.get(UserBurnoutReport, response_id)
    if submitted_at == OLD:
        assert stored is None
        assert result.survey_responses_deleted == 1
        assert result.survey_links_cleared == 0
    else:
        assert stored is not None and stored.analysis_id is None
        assert stored.feeling_score == stored.workload_score == 3
        assert stored.submitted_at == submitted_at
        assert result.survey_responses_deleted == 0
        assert result.survey_links_cleared == 1


@pytest.mark.parametrize("generation_at,completed_at,expires", [
    (OLD, NOW, True), (CUTOFF, OLD, False), (RECENT, OLD, False), (None, OLD, False),
])
def test_already_cleared_saved_entries_expire_only_with_a_canonical_snapshot_age(
    db, enabled_policy, analysis_factory, generation_at, completed_at, expires,
):
    from app.models import Analysis
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview

    record = analysis_factory(None, is_saved=True, results_generated_at=generation_at,
                              completed_at=completed_at)
    record_id = record.id
    preview = build_retention_preview(db, enabled_policy, RetentionPreviewRequest(), now=NOW)
    assert preview.analyses.expired == int(expires)
    assert preview.samples[0].disposition == ("expired" if expires else "empty")
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == int(expires)
    db.expire_all()
    assert (db.get(Analysis, record_id) is None) is expires
    assert cleanup(db, enabled_policy).analysis_results_expired == 0


@pytest.mark.parametrize("fields,disposition", [
    ({"results_generated_at": CUTOFF}, "retained"),
    ({"results_generated_at": RECENT}, "retained"),
    ({"results_generated_at": None, "completed_at": None}, "unverifiable"),
    ({"status": "pending"}, "deferred"),
    ({"status": "running"}, "deferred"),
    ({"config": {"is_demo": True}}, "excluded"),
    ({"organization_index": 1}, None),
    ({"organization_id": None}, None),
])
def test_fresh_unknown_active_demo_and_other_org_saved_records_survive(
    db, enabled_policy, analysis_factory, fields, disposition,
):
    from app.models import Analysis
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview

    record = analysis_factory(coverage(OLD), is_saved=True, **fields)
    record_id, payload = record.id, record.results
    preview = build_retention_preview(db, enabled_policy, RetentionPreviewRequest(), now=NOW)
    assert preview.analyses.expired == 0
    if disposition is not None:
        assert getattr(preview.analyses, disposition) == 1
    cleanup(db, enabled_policy)
    db.expire_all()
    assert db.get(Analysis, record_id).results == payload


def test_fresh_error_does_not_expire_an_already_cleared_saved_report(
    db, enabled_policy, analysis_factory,
):
    from app.models import Analysis

    record = analysis_factory(None, is_saved=True, status="failed", results_generated_at=OLD,
                              error_message="Recent failure", error_generated_at=RECENT)
    record_id = record.id
    assert cleanup(db, enabled_policy).analysis_results_expired == 0
    assert db.get(Analysis, record_id).error_message == "Recent failure"


def test_only_preserved_configuration_is_offered_for_regeneration(
    db, enabled_policy, analysis_factory, users,
):
    from app.models import RootlyIntegration
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview

    integration = RootlyIntegration(user_id=users[0].id, name="Disposable preview",
                                    api_token="fake-test-token", platform="rootly", is_active=True)
    db.add(integration)
    db.commit()
    analysis_factory(coverage(OLD), is_saved=True, rootly_integration_id=integration.id)
    analysis_factory(coverage(OLD), is_saved=True, is_auto_refresh=True,
                     rootly_integration_id=integration.id)
    preview = build_retention_preview(db, enabled_policy, RetentionPreviewRequest(), now=NOW)
    assert preview.analyses.expired == 2
    assert preview.analyses.regeneration_candidates == 1


def test_expired_error_only_manual_saved_record_is_deleted(db, enabled_policy, analysis_factory):
    from app.models import Analysis

    record = analysis_factory(None, is_saved=True, status="failed",
                              error_message="Old diagnostics", error_generated_at=OLD)
    record_id = record.id
    assert cleanup(db, enabled_policy).analysis_results_expired == 1
    assert db.get(Analysis, record_id) is None


def test_saved_list_and_deleted_report_reads_after_cleanup(
    db, enabled_policy, analysis_factory, users, monkeypatch,
):
    from app.api.endpoints.analyses import router
    from app.auth.dependencies import get_current_user_flexible
    from app.core.rate_limiting import limiter
    from app.models import get_db

    old = analysis_factory(coverage(OLD), is_saved=True)
    fresh = analysis_factory(coverage(RECENT), is_saved=True, results_generated_at=NOW,
                             created_at=OLD, completed_at=NOW + timedelta(hours=1))
    analysis_factory(coverage(OLD), is_saved=True, is_auto_refresh=True)
    old_id, fresh_id = old.id, fresh.id
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.include_router(router, prefix="/analyses")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user_flexible] = lambda: users[0]
    with TestClient(app) as client:
        before = client.get("/analyses")
        assert before.status_code == 200
        assert {row["id"] for row in before.json()["analyses"]} == {old_id, fresh_id}
        fresh_summary = next(row for row in before.json()["analyses"] if row["id"] == fresh_id)
        assert fresh_summary["results_generated_at"] == NOW.isoformat().replace("+00:00", "Z")
        assert fresh_summary["results_generated_at"] != fresh_summary["created_at"]
        assert fresh_summary["results_generated_at"] != fresh_summary["completed_at"]
        cleanup(db, enabled_policy)
        after = client.get("/analyses")
        assert after.status_code == 200
        assert after.json()["total"] == 1
        assert [row["id"] for row in after.json()["analyses"]] == [fresh_id]
        assert after.json()["analyses"][0]["results_generated_at"] == fresh_summary["results_generated_at"]
        assert client.get(f"/analyses/{old_id}").status_code == 404


def test_full_saved_deletion_and_detachment_roll_back_together(
    db, db_connection, enabled_policy, analysis_factory, survey_factory,
):
    record = analysis_factory(coverage(OLD), is_saved=True)
    survey_factory(OLD, analysis_id=record.id)
    survey_factory(RECENT, analysis_id=record.id)
    before = snapshot(db_connection)

    def fail_after_deletion():
        raise RuntimeError("Failure while recording cleanup outcome")

    with pytest.raises(RuntimeError, match="recording cleanup outcome"):
        cleanup(db, enabled_policy, completion_clock=fail_after_deletion)
    assert snapshot(db_connection) == before


@pytest.mark.parametrize("reader", ["_require_retained_result", "_require_result_after_collection"])
def test_request_waiting_on_deleted_saved_report_returns_not_found(
    db, enabled_policy, analysis_factory, reader,
):
    from app.api.endpoints import analyses

    record = analysis_factory(coverage(OLD), is_saved=True)
    cleanup(db, enabled_policy)
    with pytest.raises(HTTPException) as error:
        getattr(analyses, reader)(db, record)
    assert error.value.status_code == 404
