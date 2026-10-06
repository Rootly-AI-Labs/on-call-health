"""PostgreSQL integration checks for organization retention policy permissions.

Run against a dedicated disposable database, never the application's database::

    RETENTION_TEST_DATABASE_URL=postgresql://.../och_retention_test pytest tests/test_retention_policy.py

Only the organizations table is created. Each test runs in an outer transaction;
API commits release savepoints, and teardown rolls back all fixture/test records.
"""

import os
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

PATH = "/auth/organizations/retention"


@pytest.fixture(scope="module")
def retention_engine():
    database_url = os.getenv("RETENTION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set RETENTION_TEST_DATABASE_URL to a disposable PostgreSQL retention_test database")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or "retention_test" not in (url.database or "").lower():
        pytest.fail("Retention tests require PostgreSQL and a database name containing retention_test")

    from app.models import Organization

    engine = create_engine(database_url, pool_pre_ping=True)
    Organization.__table__.create(engine, checkfirst=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(retention_engine):
    connection = retention_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def db(db_connection):
    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest.fixture
def organizations(db):
    from app.models import Organization

    suffix = uuid4().hex
    organizations = [
        Organization(
            name=f"Retention Test {index}",
            domain=f"retention-{suffix}-{index}.example.com",
            slug=f"retention-{suffix}-{index}",
            status="active",
            settings={"unrelated": {"keep": True}},
        )
        for index in range(2)
    ]
    db.add_all(organizations)
    db.commit()
    return organizations


@pytest.fixture
def current_user(organizations):
    return SimpleNamespace(
        id=101,
        organization_id=organizations[0].id,
        role="admin",
        status="active",
    )


@pytest.fixture
def test_app(db, current_user):
    from app.api.endpoints.retention import router
    from app.auth.dependencies import get_current_active_user
    from app.models import get_db

    app = FastAPI()
    app.include_router(router, prefix=PATH)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: current_user
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


def set_policy(client, retention_days, *, confirmed=True):
    return client.put(
        PATH,
        json={"retention_days": retention_days, "confirm_deletion": confirmed},
    )


def test_policy_defaults_to_disabled(client, organizations):
    response = client.get(PATH)
    assert response.status_code == 200
    result = response.json()
    cleanup_status = result.pop("cleanup_status")
    assert cleanup_status["state"] == "never"
    assert cleanup_status["last_success_at"] is None
    assert cleanup_status["next_cleanup_due_at"] is None
    assert cleanup_status["next_retry_at"] is None
    assert all(count == 0 for count in cleanup_status["counts"].values())
    version = result.pop("policy_version")
    assert len(version) == 64 and all(character in "0123456789abcdef" for character in version)
    assert result == {
        "organization_id": organizations[0].id,
        "retention_days": None,
        "enabled": False,
        "age_basis": "analysis_generation",
        "survey_age_basis": "submission",
        "scope": ["analyses", "survey_responses"],
        "updated_at": None,
        "legacy_cleanup": {
            "state": "none", "requested_count": 0, "pending_count": 0,
            "cleared_count": 0, "skipped_count": 0,
            "cancelled_count": 0,
            "approved_at": None, "finished_at": None,
        },
    }


def test_null_organization_settings_defaults_to_disabled(client, db, organizations):
    organizations[0].settings = None
    db.commit()
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json()["retention_days"] is None
    assert response.json()["enabled"] is False


def test_pre_generation_policy_uses_new_basis_without_losing_period_or_mutating_settings(client, db, organizations):
    stored = {"retention_days": 90, "age_basis": "event"}
    organizations[0].settings = {"data_retention": stored, "unrelated": {"keep": True}}
    db.commit()
    response = client.get(PATH)
    assert response.status_code == 200, response.text
    assert response.json()["retention_days"] == 90
    assert response.json()["age_basis"] == "analysis_generation"
    assert response.json()["survey_age_basis"] == "submission"
    db.expire_all()
    assert organizations[0].settings == {"data_retention": stored, "unrelated": {"keep": True}}


@pytest.mark.parametrize("method", ["get", "put"])
def test_authentication_is_required(client, test_app, method):
    from app.auth.dependencies import get_current_active_user

    del test_app.dependency_overrides[get_current_active_user]
    options = {"json": {"retention_days": 90}} if method == "put" else {}
    response = getattr(client, method)(PATH, **options)
    assert response.status_code == 401


def test_members_can_read_their_organization_policy(client, current_user, organizations):
    current_user.role = "member"
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json()["organization_id"] == organizations[0].id


def test_members_cannot_update_policy(client, current_user, db, organizations):
    current_user.role = "member"
    response = set_policy(client, 90)
    assert response.status_code == 403
    db.expire_all()
    assert "data_retention" not in organizations[0].settings


@pytest.mark.parametrize("method", ["get", "put"])
def test_users_without_an_organization_are_rejected(client, current_user, method):
    current_user.organization_id = None
    options = {"json": {"retention_days": 90, "confirm_deletion": True}} if method == "put" else {}
    assert getattr(client, method)(PATH, **options).status_code == 400


@pytest.mark.parametrize("method", ["get", "put"])
def test_missing_organization_is_rejected(client, current_user, db, method):
    from app.models import Organization

    current_user.organization_id = db.scalar(select(func.max(Organization.id))) + 1
    options = {"json": {"retention_days": 90, "confirm_deletion": True}} if method == "put" else {}
    assert getattr(client, method)(PATH, **options).status_code == 404


@pytest.mark.parametrize("method", ["get", "put"])
@pytest.mark.parametrize("status", ["suspended", "pending", "inactive"])
def test_inactive_organization_is_rejected(client, db, organizations, method, status):
    organizations[0].status = status
    db.commit()
    options = {"json": {"retention_days": 90, "confirm_deletion": True}} if method == "put" else {}
    assert getattr(client, method)(PATH, **options).status_code == 403


@pytest.mark.parametrize("method", ["get", "put"])
@pytest.mark.parametrize("status", ["pending", "inactive", "suspended"])
def test_inactive_user_is_rejected(client, current_user, method, status):
    current_user.status = status
    options = {"json": {"retention_days": 90, "confirm_deletion": True}} if method == "put" else {}
    assert getattr(client, method)(PATH, **options).status_code == 403


@pytest.mark.parametrize("days", [1, 30, 90, 3650])
def test_valid_policy_persists_across_sessions_and_preserves_settings(
    client, db_connection, organizations, days
):
    from app.models import Organization

    response = set_policy(client, days)
    assert response.status_code == 200
    result = response.json()
    assert result["organization_id"] == organizations[0].id
    assert result["retention_days"] == days
    assert result["enabled"] is True
    assert result["age_basis"] == "analysis_generation"
    assert result["survey_age_basis"] == "submission"
    assert result["scope"] == ["analyses", "survey_responses"]
    assert datetime.fromisoformat(result["updated_at"].replace("Z", "+00:00")).tzinfo is not None

    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as reloaded:
        organization = reloaded.get(Organization, organizations[0].id)
        assert organization.settings["data_retention"]["retention_days"] == days
        assert organization.settings["unrelated"] == {"keep": True}
        other_organization = reloaded.get(Organization, organizations[1].id)
        assert "data_retention" not in other_organization.settings
    assert client.get(PATH).json() == result


@pytest.mark.parametrize("days", [-1, 0, 3651, 1.5, "90", True, False, [], {}])
def test_invalid_retention_values_are_rejected_without_writing(client, db, organizations, days):
    response = set_policy(client, days)
    assert response.status_code == 422
    db.expire_all()
    assert "data_retention" not in organizations[0].settings


def test_omitting_retention_days_is_rejected(client):
    assert client.put(PATH, json={"confirm_deletion": True}).status_code == 422


@pytest.mark.parametrize("confirmation", ["true", "false", 1, 0, None])
def test_confirmation_requires_boolean(client, confirmation):
    response = client.put(PATH, json={"retention_days": 90, "confirm_deletion": confirmation})
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["organization_id", "org_id", "scope", "age_basis", "enabled"])
def test_extra_fields_and_organization_injection_are_rejected(client, db, organizations, field):
    response = client.put(
        PATH,
        json={"retention_days": 90, "confirm_deletion": True, field: organizations[1].id},
    )
    assert response.status_code == 422
    db.expire_all()
    assert "data_retention" not in organizations[0].settings
    assert "data_retention" not in organizations[1].settings


def test_query_organization_id_cannot_target_another_organization(client, db, organizations):
    path = f"{PATH}?organization_id={organizations[1].id}"
    response = client.put(path, json={"retention_days": 90, "confirm_deletion": True})
    assert response.status_code == 200
    assert response.json()["organization_id"] == organizations[0].id
    assert client.get(path).json()["organization_id"] == organizations[0].id
    db.expire_all()
    assert "data_retention" not in organizations[1].settings


@pytest.mark.parametrize("body", [{"retention_days": 90}, {"retention_days": 90, "confirm_deletion": False}])
def test_first_enable_requires_confirmation_and_does_not_write(client, db, organizations, body):
    response = client.put(PATH, json=body)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "retention_confirmation_required"
    db.expire_all()
    assert "data_retention" not in organizations[0].settings


def test_shortening_requires_confirmation_and_keeps_old_policy(client):
    assert set_policy(client, 90).status_code == 200
    response = set_policy(client, 30, confirmed=False)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "retention_confirmation_required"
    assert client.get(PATH).json()["retention_days"] == 90
    assert set_policy(client, 30).status_code == 200
    assert client.get(PATH).json()["retention_days"] == 30


@pytest.mark.parametrize("days", [90, 180])
def test_unchanged_or_longer_policy_does_not_require_confirmation(client, days):
    assert set_policy(client, 90).status_code == 200
    response = client.put(PATH, json={"retention_days": days})
    assert response.status_code == 200
    assert client.get(PATH).json()["retention_days"] == days


def test_disabling_requires_no_confirmation_and_reenabling_does(client, db, organizations):
    assert set_policy(client, 90).status_code == 200
    response = client.put(PATH, json={"retention_days": None})
    assert response.status_code == 200
    assert response.json()["retention_days"] is None
    assert response.json()["enabled"] is False
    db.expire_all()
    assert organizations[0].settings["data_retention"]["retention_days"] is None
    assert organizations[0].settings["unrelated"] == {"keep": True}
    assert client.put(PATH, json={"retention_days": 90}).status_code == 409


def test_disabling_an_unconfigured_policy_is_allowed(client):
    response = client.put(PATH, json={"retention_days": None})
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_other_organization_admin_can_only_read_and_change_their_own_policy(
    client, current_user, organizations
):
    assert set_policy(client, 90).status_code == 200
    current_user.organization_id = organizations[1].id
    assert client.get(PATH).json()["retention_days"] is None
    assert set_policy(client, 30).status_code == 200
    assert client.get(PATH).json()["retention_days"] == 30
    current_user.organization_id = organizations[0].id
    assert client.get(PATH).json()["retention_days"] == 90
