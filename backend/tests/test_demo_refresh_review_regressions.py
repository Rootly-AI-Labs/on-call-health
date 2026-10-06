"""Demo refresh preserves real analyses, regardless of user verification.

Database fixtures require an explicit disposable PostgreSQL ``retention_test``
database and roll back every test. Only the rate-limit wrapper is unwrapped:
the endpoint's API-key, IP, and refresh-lock checks still execute. Demo loading
is mocked; no provider, check-in loader, application database, or Redis is used.
"""
import inspect
import io
import json
import threading
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from .test_retention_preview import (
    NOW, analysis_factory, db, db_connection, organizations, retention_engine,
    survey_factory, users,
)

PATH = "/admin/refresh-demo-analyses"
TEST_KEY = "demo-refresh-regression-test-key-32"
ALLOWED_IP = "127.0.0.1"


@pytest.fixture
def refresh_endpoint(monkeypatch, db, organizations):
    # A standalone run must not initialize rate-limit Redis from Compose env.
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("REDIS_HOST", "")
    from app.api.endpoints import admin

    monkeypatch.setattr(admin, "ADMIN_API_KEY", TEST_KEY)
    monkeypatch.setattr(admin, "_admin_api_key_valid", True)
    monkeypatch.setattr(admin, "_ip_whitelist", {ALLOWED_IP})
    monkeypatch.setattr(admin, "_refresh_lock", threading.Lock())
    monkeypatch.setattr(admin, "_get_or_create_demo_organization", lambda session: organizations[0].id)
    mock_data = {"analysis": {
        "config": {"test_mock": True}, "platform": "rootly", "time_range": 30,
        "results": {"team_health": {"score": 73}, "test_mock": True},
    }}
    monkeypatch.setattr(admin, "open", lambda *args, **kwargs: io.StringIO(json.dumps(mock_data)), raising=False)
    checkins = []

    def load_checkins(session, user_id, organization_id, data):
        assert session is db
        assert organization_id == organizations[0].id
        checkins.append(user_id)
        return {"created": 0, "skipped": 0, "failed": 0}

    monkeypatch.setattr(admin, "_load_health_checkins_for_user", load_checkins)
    return admin, checkins


@pytest.fixture
def client(refresh_endpoint, db):
    from app.models import get_db

    admin, _ = refresh_endpoint
    app = FastAPI()
    app.add_api_route(PATH, inspect.unwrap(admin.refresh_demo_analyses), methods=["POST"])
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def verified_user(db, organizations):
    from app.models import User

    user = User(email=f"demo-refresh-{uuid4().hex}@example.com",
                organization_id=organizations[0].id, is_verified=True,
                role="member", status="active")
    db.add(user)
    db.commit()
    return user


def refresh(client, *, key=TEST_KEY, ip=ALLOWED_IP):
    return client.post(PATH, headers={"X-Admin-API-Key": key, "X-Forwarded-For": ip})


def analysis_snapshot(analysis):
    return {column.name: deepcopy(getattr(analysis, column.name))
            for column in analysis.__table__.columns}


@pytest.mark.parametrize("config", [None, {}, {"is_demo": False}, {"is_demo": False, "include_github": True}])
def test_authorized_refresh_preserves_real_results_of_unverified_users_in_both_orgs(
    client, db, analysis_factory, users, verified_user, config,
):
    from app.models import Analysis

    assert not users[0].is_verified and not users[1].is_verified
    real = [analysis_factory(
        {"private_result": f"real-org-{index}", "team_health": {"score": 51 + index}},
        organization_index=index, config=deepcopy(config), completed_at=NOW,
        results_generated_at=NOW, is_saved=True,
    ) for index in range(2)]
    original = {record.id: analysis_snapshot(record) for record in real}

    response = refresh(client)

    assert response.status_code == 200, response.text
    assert response.json()["unverified_analyses_deleted"] == 0
    assert response.json()["deleted_count"] == 0
    assert response.json()["created_count"] == 1
    assert response.json()["errors"] is None
    db.expire_all()
    for analysis_id, before in original.items():
        preserved = db.query(Analysis).filter_by(id=analysis_id).one()
        assert analysis_snapshot(preserved) == before


def test_refresh_replaces_only_marked_demo_analyses_and_keeps_normal_demo_cleanup(
    client, db, organizations, users, verified_user, analysis_factory, survey_factory, refresh_endpoint,
):
    from app.models import Analysis, UserBurnoutReport

    real = analysis_factory({"real_result": True}, organization_index=1, config={"is_demo": False})
    real_id = real.id
    old_demos = [analysis_factory({"old_demo": index}, organization_index=index,
                                  config={"is_demo": True}) for index in range(2)]
    old_demo_ids = [record.id for record in old_demos]
    demo_report = survey_factory(NOW, organization_index=0)
    other_report = survey_factory(NOW, organization_index=1)
    demo_report_id, other_report_id = demo_report.id, other_report.id
    other_report_before = {column.name: deepcopy(getattr(other_report, column.name))
                           for column in other_report.__table__.columns}

    response = refresh(client)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["unverified_analyses_deleted"] == 0
    assert payload["deleted_count"] == 2
    assert payload["reports_deleted"] == 1
    assert payload["created_count"] == payload["total_demo_analyses"] == 1
    assert payload["errors"] is None
    db.expire_all()
    assert db.query(Analysis).filter(Analysis.id.in_(old_demo_ids)).count() == 0
    assert db.query(Analysis).filter_by(id=real_id).one().results == {"real_result": True}
    assert db.query(UserBurnoutReport).filter_by(id=demo_report_id).first() is None
    preserved_report = db.query(UserBurnoutReport).filter_by(id=other_report_id).one()
    assert {column.name: getattr(preserved_report, column.name)
            for column in preserved_report.__table__.columns} == other_report_before
    demos = db.query(Analysis).filter(Analysis.config["is_demo"].as_boolean() == True).all()
    assert len(demos) == 1
    assert demos[0].user_id == verified_user.id
    assert demos[0].organization_id == organizations[0].id
    assert demos[0].results == {"team_health": {"score": 73}, "test_mock": True}
    assert demos[0].results_generated_at is not None
    assert demos[0].completed_at == demos[0].results_generated_at
    assert refresh_endpoint[1] == [verified_user.id]


@pytest.mark.parametrize("case,expected_status", [
    ("invalid_key", 403), ("unlisted_ip", 403),
    ("unconfigured_key", 503), ("empty_whitelist", 403), ("refresh_busy", 409),
])
def test_refresh_security_and_concurrency_guards_still_prevent_mutations(
    client, db, analysis_factory, refresh_endpoint, monkeypatch, case, expected_status,
):
    from app.models import Analysis

    admin, checkins = refresh_endpoint
    analysis = analysis_factory({"unchanged": True}, config={"is_demo": True})
    analysis_id, before = analysis.id, analysis_snapshot(analysis)
    key, ip = TEST_KEY, ALLOWED_IP
    if case == "invalid_key": key = "wrong-test-key"
    if case == "unlisted_ip": ip = "198.51.100.44"
    if case == "unconfigured_key": monkeypatch.setattr(admin, "_admin_api_key_valid", False)
    if case == "empty_whitelist": monkeypatch.setattr(admin, "_ip_whitelist", set())
    if case == "refresh_busy": assert admin._refresh_lock.acquire(blocking=False)
    try:
        response = refresh(client, key=key, ip=ip)
        assert response.status_code == expected_status, response.text
        db.expire_all()
        assert analysis_snapshot(db.query(Analysis).filter_by(id=analysis_id).one()) == before
        assert checkins == []
    finally:
        if case == "refresh_busy": admin._refresh_lock.release()
