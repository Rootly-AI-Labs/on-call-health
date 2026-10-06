"""Cleanup/read performance and controlled-organization flow on staging code.

Fixtures refuse application databases. All synthetic rows roll back; providers,
authentication and Redis are isolated, while HTTP handlers/cleanup use real SQL.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from .test_retention_preview import (
    NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)
from .test_retention_cleanup import cleanup, enabled_policy, isolate_retention_cache


@contextmanager
def observed_sql(connection):
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", observe)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", observe)


def full_result_selects(statements):
    return [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")
            and re.search(r"analyses\.results AS analyses_results\b", sql)]


@pytest.fixture
def http_client(db, users, monkeypatch):
    from app.api.endpoints import analyses, retention
    from app.auth.dependencies import get_current_active_user, get_current_user_flexible
    from app.core.rate_limiting import limiter
    from app.models import get_db

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz else NOW.replace(tzinfo=None)

    monkeypatch.setattr(analyses, "datetime", Clock)
    monkeypatch.setattr(analyses, "_get_redis_for_analysis", lambda: None)
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.include_router(analyses.router, prefix="/analyses")
    app.include_router(retention.router, prefix="/retention")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: users[0]
    app.dependency_overrides[get_current_user_flexible] = lambda: users[0]
    app.dependency_overrides[retention.retention_preview_now] = lambda: NOW
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("route", ["/analyses/{id}", "/analyses/uuid/{uuid}", "/analyses/by-id/{uuid}"])
def test_full_report_reads_project_once_and_share_the_roster(
    db, db_connection, enabled_policy, analysis_factory, survey_factory, http_client, route,
):
    record = analysis_factory(coverage(OLD, generated_at=NOW, team_analysis={"members": [
        {"user_email": "member@example.test"},
    ]}, unused_raw_payload="large raw source payload"), time_range=180)
    survey_factory(RECENT, email="member@example.test")
    url = route.format(id=record.id, uuid=record.uuid)
    db.expire_all()
    with observed_sql(db_connection) as statements:
        response = http_client.get(url)
    assert response.status_code == 200, response.text
    data = response.json()["analysis_data"]
    assert "unused_raw_payload" not in data
    assert "member@example.test" in data["member_surveys"]
    assert data["metadata"]["date_range"]["start"] == OLD.isoformat()
    assert full_result_selects(statements) == []
    assert sum("results->" in sql or "results ->" in sql for sql in statements) == 1


def test_cleanup_never_loads_full_json_for_ordinary_expiry(
    db, db_connection, enabled_policy, analysis_factory, survey_factory,
):
    expired = analysis_factory(coverage(OLD, unused_raw_payload="old large content"), is_saved=True)
    recent = analysis_factory(coverage(RECENT, unused_raw_payload="recent large content"), is_saved=True)
    survey_factory(OLD, analysis_id=expired.id)
    survey_factory(RECENT, analysis_id=recent.id)
    with observed_sql(db_connection) as statements:
        result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == result.survey_responses_deleted == 1
    assert full_result_selects(statements) == []
    candidate_sql = next(sql for sql in statements if "AS has_results" in sql and "FOR UPDATE" in sql)
    assert "coalesce(" in candidate_sql.lower() and "results_generated_at" in candidate_sql
    # Metadata and eligibility are projected; recent full reports are not transferred.
    assert "analyses.results AS analyses_results" not in candidate_sql


@pytest.mark.parametrize("already_cleared", [False, True])
@pytest.mark.parametrize("fields", [
    {"config": {"retired_auto_refresh": True}},
    {"auto_refresh_interval": "24h"},  # Historical carriers from before the marker.
])
def test_expired_retired_carriers_are_deleted_and_recent_surveys_detached(
    db, enabled_policy, analysis_factory, survey_factory, fields, already_cleared,
):
    from app.models import Analysis, UserBurnoutReport

    record = analysis_factory(None if already_cleared else coverage(OLD),
                              results_generated_at=OLD, is_saved=False, is_auto_refresh=False, **fields)
    survey = survey_factory(RECENT, analysis_id=record.id)
    record_id, survey_id = record.id, survey.id
    result = cleanup(db, enabled_policy)
    assert result.analysis_results_expired == result.survey_links_cleared == 1
    db.expire_all()
    assert db.get(Analysis, record_id) is None
    assert db.get(UserBurnoutReport, survey_id).analysis_id is None


@pytest.mark.parametrize("generation,status", [(RECENT, "completed"), (None, "completed"), (OLD, "running")])
def test_retirement_does_not_bypass_age_or_active_run_rules(
    db, enabled_policy, analysis_factory, generation, status,
):
    from app.models import Analysis

    record = analysis_factory(coverage(OLD), results_generated_at=generation, completed_at=None,
                              status=status, config={"retired_auto_refresh": True})
    record_id = record.id
    assert cleanup(db, enabled_policy).analysis_results_expired == 0
    db.expire_all()
    assert db.get(Analysis, record_id).results is not None


def test_controlled_org_http_policy_daily_worker_and_report_flow(
    db, db_connection, organizations, analysis_factory, survey_factory, http_client,
):
    """Exercise default -> preview -> save -> guarded reads -> daily worker -> disable."""
    from app.models import Analysis, UserBurnoutReport
    from app.services.retention_scheduler import process_organization_cleanup

    manual = analysis_factory(coverage(OLD), is_saved=True)
    retired = analysis_factory(coverage(OLD), auto_refresh_interval="24h")
    recurring = analysis_factory(coverage(OLD), is_auto_refresh=True, auto_refresh_interval="24h")
    fresh = analysis_factory(coverage(NOW - timedelta(days=180), generated_at=NOW), is_saved=True, time_range=180)
    demo = analysis_factory(coverage(OLD), config={"is_demo": True}, is_saved=True)
    unknown = analysis_factory(coverage(OLD), results_generated_at=None, completed_at=None, is_saved=True)
    other = analysis_factory(coverage(OLD), organization_index=1, is_saved=True)
    old_survey = survey_factory(OLD, analysis_id=manual.id)
    newer_survey = survey_factory(NOW, analysis_id=retired.id)
    ids = {name: row.id for name, row in locals().copy().items() if name in (
        "manual", "retired", "recurring", "fresh", "demo", "unknown", "other", "old_survey", "newer_survey",
    )}
    organization_id = organizations[0].id

    policy = http_client.get("/retention").json()
    assert policy["enabled"] is False
    preview = http_client.post("/retention/preview", json={"retention_days": 90})
    assert preview.status_code == 200
    assert preview.json()["analyses"]["expired"] == 3
    assert preview.json()["survey_responses"]["expired"] == 1
    assert http_client.get("/retention").json()["enabled"] is False
    saved = http_client.put("/retention", json={
        "retention_days": 90, "confirm_deletion": True, "expected_policy_version": policy["policy_version"],
    })
    assert saved.status_code == 200, saved.text
    # Saving only changes visibility; physical rows still exist until cleanup.
    assert db.get(Analysis, ids["manual"]) is not None
    assert http_client.get(f"/analyses/{ids['manual']}").status_code == 410
    assert http_client.get(f"/analyses/{ids['unknown']}").status_code == 410
    fresh_response = http_client.get(f"/analyses/{ids['fresh']}")
    assert fresh_response.status_code == 200
    assert fresh_response.json()["time_range"] == 180
    assert fresh_response.json()["analysis_data"]["metadata"]["date_range"]["start"] == (NOW - timedelta(days=180)).isoformat()

    # A separate worker session runs the real due/claim/cleanup code. The outer
    # disposable fixture transaction keeps all changes rollback-only.
    worker_factory = lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint")
    assert process_organization_cleanup(organization_id, session_factory=worker_factory,
                                        clock=lambda: NOW + timedelta(hours=1)) == "succeeded"
    db.expire_all()
    assert db.get(Analysis, ids["manual"]) is None
    assert db.get(Analysis, ids["retired"]) is None
    retained_setup = db.get(Analysis, ids["recurring"])
    assert retained_setup.is_auto_refresh is True and retained_setup.results is None
    assert retained_setup.auto_refresh_interval == "24h"
    assert db.get(UserBurnoutReport, ids["old_survey"]) is None
    assert db.get(UserBurnoutReport, ids["newer_survey"]).analysis_id is None
    for name in ("fresh", "demo", "unknown", "other"):
        assert db.get(Analysis, ids[name]).results is not None
    assert http_client.get(f"/analyses/{ids['manual']}").status_code == 404
    assert http_client.get(f"/analyses/{ids['recurring']}").status_code == 410
    status = http_client.get("/retention").json()
    assert status["cleanup_status"]["state"] == "succeeded"
    assert status["cleanup_status"]["counts"]["analysis_results_expired"] == 3
    assert http_client.put("/retention", json={"retention_days": None,
                            "expected_policy_version": status["policy_version"]}).status_code == 200
    assert http_client.get(f"/analyses/{ids['recurring']}").status_code == 410
    assert http_client.get(f"/analyses/{ids['unknown']}").status_code == 200
