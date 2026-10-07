"""Conditional policy saves require the reviewed organization and audit revision.

These checks reuse guarded PostgreSQL fixtures from the policy tests. Every
test runs inside an outer rollback transaction in a retention_test database;
no application data, live cleanup, or Redis cache is used.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from .test_retention_policy import (
    PATH, client, current_user, db, db_connection, organizations,
    retention_engine, test_app,
)


def read_policy(client):
    response = client.get(PATH)
    assert response.status_code == 200, response.text
    return response.json()


def save(client, days, *, expected_version=None, include_version=True, confirmed=True, **extra):
    body = {"retention_days": days, "confirm_deletion": confirmed, **extra}
    if include_version:
        body["expected_policy_version"] = expected_version
    return client.put(PATH, json=body)


def assert_changed(response):
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == {
        "code": "retention_policy_changed",
        "message": "Your organization or retention policy changed. Refresh settings and review a new preview.",
    }


def test_current_policy_version_allows_save_and_changes_with_saved_revision(client):
    first = read_policy(client)
    response = save(client, 90, expected_version=first["policy_version"])
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["retention_days"] == 90
    assert saved["policy_version"] != first["policy_version"]
    assert read_policy(client) == saved


def test_same_policy_noop_keeps_version_and_audit_metadata(client):
    first = save(client, 90, include_version=False).json()
    response = save(client, 90, expected_version=first["policy_version"], confirmed=False)
    assert response.status_code == 200, response.text
    assert response.json() == first


def test_version_is_stable_and_excludes_unrelated_org_settings(client, db, organizations):
    first = read_policy(client)
    assert len(first["policy_version"]) == 64
    assert all(character in "0123456789abcdef" for character in first["policy_version"])
    assert read_policy(client)["policy_version"] == first["policy_version"]
    organizations[0].settings = {
        **organizations[0].settings,
        "another_setting": {"value": "Not part of retention policy"},
    }
    db.commit()
    assert read_policy(client)["policy_version"] == first["policy_version"]
    response = save(client, 90, expected_version=first["policy_version"])
    assert response.status_code == 200
    db.expire_all()
    assert organizations[0].settings["another_setting"] == {"value": "Not part of retention policy"}


def test_switching_org_with_same_session_rejects_before_any_write(
    client, db, db_connection, organizations, current_user,
):
    session_headers = {"Authorization": "Bearer unchanged-test-session"}
    first = client.get(PATH, headers=session_headers).json()
    before = [deepcopy(organization.settings) for organization in organizations]
    current_user.organization_id = organizations[1].id
    other = client.get(PATH, headers=session_headers).json()
    # Even organizations with the identical disabled policy have different versions.
    assert other["retention_days"] == first["retention_days"] is None
    assert other["policy_version"] != first["policy_version"]

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError("A stale organization save attempted a write")

    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        response = client.put(PATH, headers=session_headers, json={
            "retention_days": 90,
            "confirm_deletion": True,
            "expected_policy_version": first["policy_version"],
        })
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)
    assert_changed(response)
    db.expire_all()
    assert [organization.settings for organization in organizations] == before


@pytest.mark.parametrize("requested_days", [None, 30, 120])
def test_stale_policy_cannot_disable_shorten_or_lengthen_new_revision(client, requested_days):
    reviewed = read_policy(client)
    latest = save(client, 90, include_version=False).json()
    response = save(client, requested_days, expected_version=reviewed["policy_version"])
    assert_changed(response)
    assert read_policy(client) == latest


def test_disabled_policy_still_has_an_audited_version(client):
    originally_disabled = read_policy(client)
    enabled = save(client, 90, expected_version=originally_disabled["policy_version"]).json()
    response = save(client, None, expected_version=enabled["policy_version"], confirmed=False)
    assert response.status_code == 200
    disabled = response.json()
    assert disabled["retention_days"] is None
    assert disabled["policy_version"] != originally_disabled["policy_version"]
    assert_changed(save(client, 90, expected_version=originally_disabled["policy_version"]))
    assert read_policy(client) == disabled


def test_change_then_restore_same_days_cannot_reuse_older_review(client, test_app):
    from app.api.endpoints.retention import retention_preview_now

    clock = [datetime(2026, 10, 5, 12, tzinfo=timezone.utc)]
    test_app.dependency_overrides[retention_preview_now] = lambda: clock[0]
    reviewed = save(client, 90, include_version=False).json()
    clock[0] += timedelta(minutes=1)
    assert save(client, 30, include_version=False).status_code == 200
    clock[0] += timedelta(minutes=1)
    latest = save(client, 90, include_version=False).json()
    assert latest["retention_days"] == reviewed["retention_days"]
    assert latest["policy_version"] != reviewed["policy_version"]
    assert_changed(save(client, 120, expected_version=reviewed["policy_version"], confirmed=False))
    assert read_policy(client) == latest


def test_stale_version_rejected_before_legacy_confirmation_or_authorization(client, db, organizations):
    reviewed = read_policy(client)
    latest = save(client, 90, include_version=False).json()
    # Missing legacy confirmations would normally be a different 409; the version
    # guard must take precedence and must not stage any new cleanup authorization.
    response = save(client, 90, expected_version=reviewed["policy_version"], clear_unverifiable_analyses=True)
    assert_changed(response)
    db.expire_all()
    assert "data_retention_legacy_cleanup" not in organizations[0].settings
    assert read_policy(client) == latest


@pytest.mark.parametrize("version_kind", ["current", "stale"])
def test_expected_version_cannot_grant_member_write_access(client, current_user, db, organizations, version_kind):
    reviewed = read_policy(client)
    version = reviewed["policy_version"] if version_kind == "current" else "0" * 64
    current_user.role = "member"
    response = save(client, 90, expected_version=version)
    assert response.status_code == 403
    db.expire_all()
    assert "data_retention" not in organizations[0].settings


@pytest.mark.parametrize("include_version", [False, True])
def test_legacy_callers_can_omit_or_null_the_expected_version(client, include_version):
    response = save(client, 90, expected_version=None, include_version=include_version)
    assert response.status_code == 200, response.text
    assert response.json()["retention_days"] == 90
    assert len(response.json()["policy_version"]) == 64


@pytest.mark.parametrize("version", ["", "0" * 63, "0" * 65, "G" * 64, "A" * 64, 123, False, [], {}])
def test_malformed_version_rejected_without_policy_write(client, db, organizations, version):
    response = save(client, 90, expected_version=version)
    assert response.status_code == 422
    db.expire_all()
    assert "data_retention" not in organizations[0].settings
