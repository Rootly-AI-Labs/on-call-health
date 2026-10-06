"""Local retention demo safety checks against disposable PostgreSQL only.

The imported fixtures require a database name containing ``retention_test`` and
wrap every test in an outer rollback transaction. Demo cache invalidation is
mocked, so fixture IDs cannot evict the application's Redis keys.
"""
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import event, text

from .test_retention_preview import (
    NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)
from .test_retention_cleanup import snapshot, snapshot_without_cleanup_metadata


@pytest.fixture
def demo(monkeypatch):
    from scripts import retention_demo
    from app.services import retention_cleanup

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(retention_demo, "datetime", Clock)
    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", lambda *args: None)
    return retention_demo


@pytest.fixture(autouse=True)
def oauth_exchange_table(db):
    """Mirror the migration-managed table inside the outer rollback transaction."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS oauth_temp_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(255) UNIQUE NOT NULL,
            jwt_token TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            auth_method VARCHAR(50)
        )
    """))
    db.commit()


def membership(user):
    return {
        "organization_id": user.organization_id,
        "role": user.role,
        "joined_org_at": user.joined_org_at,
        "weekly_digest_enabled": user.weekly_digest_enabled,
    }


def seed(demo, db, owner):
    from app.models import Organization

    original = membership(owner)
    result = demo.seed_demo(db, owner.email, now=NOW)
    db.expire_all()
    organization = db.get(Organization, owner.organization_id)
    assert organization is not None and organization.id != original["organization_id"]
    return organization, original, result


@pytest.mark.parametrize("host", ["postgres", "localhost", "127.0.0.1"])
def test_database_guard_accepts_only_explicit_local_compose_target(demo, host):
    demo.guard_local_database(f"postgresql://postgres:password@{host}:5432/burnout_detector", confirmed=True)


@pytest.mark.parametrize("url,confirmed", [
    ("postgresql://postgres:password@postgres:5432/burnout_detector", False),
    ("postgresql://postgres:password@database.example.com:5432/burnout_detector", True),
    ("postgresql://postgres:password@localhost:5432/production", True),
    ("postgresql://postgres:password@postgres:5432/oncall_health_retention_test", True),
    ("sqlite:///burnout_detector", True),
    ("postgresql:///burnout_detector", True),
    ("postgresql://postgres:password@postgres:5432/burnout_detector?host=production.example.com", True),
    ("postgresql://postgres:password@localhost:5432/burnout_detector?service=production", True),
    ("postgresql://postgres:password@localhost:5432/burnout_detector?dbname=production", True),
])
def test_database_guard_refuses_remote_alternate_or_unconfirmed_targets(demo, url, confirmed):
    with pytest.raises((ValueError, RuntimeError)):
        demo.guard_local_database(url, confirmed=confirmed)


def test_seed_preserves_existing_organization_data_and_credentials(
    demo, db, db_connection, users, organizations, analysis_factory, survey_factory,
):
    from app.models import Analysis, RootlyIntegration, UserBurnoutReport

    owner = users[0]
    original_analysis = analysis_factory(coverage(OLD))
    original_survey = survey_factory(OLD, analysis_id=original_analysis.id)
    integration = RootlyIntegration(
        user_id=owner.id, name="Unrelated disposable credential", api_token="fixture-token",
        platform="rootly", is_active=True,
    )
    db.add(integration)
    db.commit()
    original_ids = (organizations[0].id, original_analysis.id, original_survey.id, integration.id)
    before = snapshot(db_connection)

    organization, original_membership, _ = seed(demo, db, owner)

    assert owner.role == "admin" and owner.status == "active"
    assert owner.weekly_digest_enabled is False
    assert original_membership["organization_id"] == original_ids[0]
    assert organizations[0].settings == {"unrelated": {"keep": True}}
    assert "data_retention" not in organization.settings
    assert db.get(Analysis, original_ids[1]).results == coverage(OLD)
    assert db.get(UserBurnoutReport, original_ids[2]).analysis_id == original_ids[1]
    assert db.get(RootlyIntegration, original_ids[3]).api_token == "fixture-token"
    after = snapshot(db_connection)
    for table_name, rows in before.items():
        if table_name == "users":
            rows = [row for row in rows if row["id"] != owner.id]
        assert all(row in after[table_name] for row in rows), table_name


def test_mock_members_have_no_provider_credentials_or_background_work(demo, db, users):
    from app.models import Analysis, OAuthProvider, User
    from app.models.survey_schedule import SurveySchedule

    organization, _, _ = seed(demo, db, users[0])
    mock_users = db.query(User).filter(User.organization_id == organization.id, User.id != users[0].id).all()
    assert len(mock_users) == 3
    assert all(user.status == "active" and user.weekly_digest_enabled is False for user in mock_users)
    assert {user.role for user in mock_users}.issubset({"admin", "member"})
    assert all(user.email.endswith(".invalid") for user in mock_users)
    assert all(not user.password_hash for user in mock_users)
    stubs = db.query(OAuthProvider).filter(OAuthProvider.user_id.in_([user.id for user in mock_users])).all()
    assert len(stubs) == len(mock_users)
    assert all(stub.access_token is None and stub.refresh_token is None for stub in stubs)
    analyses = db.query(Analysis).filter(Analysis.organization_id == organization.id).all()
    assert analyses and all(not analysis.is_auto_refresh for analysis in analyses)
    assert all(analysis.rootly_integration_id is None and analysis.config.get("is_demo") is True for analysis in analyses)
    assert db.query(SurveySchedule).filter_by(organization_id=organization.id).count() == 0


def test_seed_is_idempotent_and_does_not_reenable_a_changed_policy(demo, db, db_connection, users):
    organization, _, _ = seed(demo, db, users[0])
    organization.settings = {
        **organization.settings,
        "data_retention": {"retention_days": 30, "age_basis": "analysis_generation", "updated_at": NOW.isoformat(), "updated_by_user_id": users[0].id},
    }
    db.commit()
    before = snapshot(db_connection)
    demo.seed_demo(db, users[0].email, now=NOW + timedelta(days=1))
    assert snapshot(db_connection) == before


def test_seed_refuses_missing_account_without_creating_any_data(demo, db, db_connection):
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        demo.seed_demo(db, "missing-retention-owner@example.invalid", now=NOW)
    assert snapshot(db_connection) == before


@pytest.mark.parametrize("fields", [
    {"status": "running"},
    {"status": "pending"},
    {"is_auto_refresh": True, "auto_refresh_interval": "24h"},
])
def test_seed_refuses_owner_with_active_or_scheduled_nonfixture_analysis(
    demo, db, db_connection, users, analysis_factory, fields,
):
    analysis_factory(coverage(RECENT), **fields)
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        demo.seed_demo(db, users[0].email, now=NOW)
    assert snapshot(db_connection) == before


def test_status_is_read_only_and_does_not_expose_receipts(demo, db, db_connection, users):
    seed(demo, db, users[0])
    before = snapshot(db_connection)

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError(f"Demo status issued a write: {statement}")

    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        result = demo.demo_status(db)
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)
    assert snapshot(db_connection) == before
    encoded = json.dumps(result, default=str)
    assert "eyJ" not in encoded  # JWT receipts must not appear in CLI output.


def test_status_explains_expected_90_day_examples_without_enabling_policy(demo, db, users):
    from app.services.data_retention import read_retention_policy

    organization, _, result = seed(demo, db, users[0])
    assert result["preview_at_90_days"]["analyses"] == {
        "total": 7, "excluded": 0, "expired": 3, "retained": 1, "unverifiable": 1, "deferred": 1, "empty": 1,
        "regeneration_candidates": 0,
    }
    assert result["preview_at_90_days"]["surveys"] == {
        "total": 4, "expired": 1, "retained": 2, "unverifiable": 1,
    }
    assert result["preview_at_90_days"]["related_records"]["survey_links_to_clear"] == 2
    assert read_retention_policy(organization).retention_days is None


def prior_event_age_demo(demo, db, owner):
    """Model the prior locally seeded fixture without deleting or reseeding it."""
    from app.models import Analysis

    organization, original, _ = seed(demo, db, owner)
    marker = dict(organization.settings[demo.MARKER_KEY])
    marker.pop("result_age_fixture_version", None)
    organization.settings = {**organization.settings, demo.MARKER_KEY: marker}
    for analysis in db.query(Analysis).filter_by(organization_id=organization.id):
        analysis.results_generated_at = NOW
        analysis.completed_at = NOW
    db.commit()
    return organization, original, marker


def test_upgrade_converts_prior_fixture_without_changing_members_surveys_or_configuration(
    demo, db, db_connection, users
):
    from app.models import Analysis
    from app.services.data_retention import read_retention_policy

    organization, original, marker = prior_event_age_demo(demo, db, users[0])
    before = snapshot(db_connection)
    configurations = {
        row.id: (row.uuid, row.user_id, row.organization_id, row.config,
                 row.is_saved, row.is_auto_refresh, row.auto_refresh_interval, row.created_at)
        for row in db.query(Analysis).filter_by(organization_id=organization.id)
    }
    result = demo.upgrade_demo(db)
    db.expire_all()
    assert organization.settings[demo.MARKER_KEY]["result_age_fixture_version"] == 2
    assert organization.settings[demo.MARKER_KEY]["original_membership"] == marker["original_membership"]
    assert original["organization_id"] != organization.id
    assert read_retention_policy(organization).retention_days is None
    assert result["preview_at_90_days"]["analyses"] == {
        "total": 7, "excluded": 0, "expired": 3, "retained": 1, "unverifiable": 1, "deferred": 1, "empty": 1,
        "regeneration_candidates": 0,
    }
    assert result["preview_at_90_days"]["surveys"] == {
        "total": 4, "expired": 1, "retained": 2, "unverifiable": 1,
    }
    assert result["preview_at_90_days"]["related_records"]["survey_links_to_clear"] == 2
    after = snapshot(db_connection)
    for table, rows in before.items():
        if table not in {"analyses", "organizations"}:
            assert after[table] == rows, table
    for row in db.query(Analysis).filter_by(organization_id=organization.id):
        assert (row.uuid, row.user_id, row.organization_id, row.config,
                row.is_saved, row.is_auto_refresh, row.auto_refresh_interval, row.created_at) == configurations[row.id]
    for case in ("old", "mixed", "saved_old"):
        row = db.get(Analysis, marker["analysis_ids"][case])
        assert row.results_generated_at == row.completed_at == NOW - timedelta(days=120)
    legacy = db.get(Analysis, marker["analysis_ids"]["legacy"])
    assert legacy.results_generated_at is legacy.completed_at is None


def test_upgraded_recent_four_month_report_survives_its_old_source_events(demo, db, users):
    from app.models import Analysis
    from app.services.retention_preview import classify_analysis_result

    _, _, marker = prior_event_age_demo(demo, db, users[0])
    demo.upgrade_demo(db)
    db.expire_all()
    recent = db.get(Analysis, marker["analysis_ids"]["recent"])
    assert recent.results_generated_at == recent.completed_at == NOW
    assert recent.time_range == 130
    source_start = datetime.fromisoformat(recent.results["metadata"]["date_range"]["start"])
    assert source_start == NOW - timedelta(days=120)
    assert any(datetime.fromisoformat(event["created_at"]) == source_start for event in recent.results["raw_incident_data"])
    assert classify_analysis_result(recent, NOW - timedelta(days=90)).disposition == "retained"


@pytest.mark.parametrize("previous_version", [False, True], ids=["new-seed", "upgraded-prior-fixture"])
def test_upgrade_is_idempotent_and_does_not_renew_generation_dates(demo, db, db_connection, users, monkeypatch, previous_version):
    if previous_version:
        prior_event_age_demo(demo, db, users[0])
        demo.upgrade_demo(db)
    else:
        seed(demo, db, users[0])
    before = snapshot(db_connection)
    monkeypatch.setattr(demo, "_now", lambda: NOW + timedelta(days=7))
    demo.upgrade_demo(db)
    assert snapshot(db_connection) == before


def test_upgrade_refuses_enabled_policy_without_mutating_fixture(demo, db, db_connection, users):
    organization, _, _ = prior_event_age_demo(demo, db, users[0])
    organization.settings = {**organization.settings, "data_retention": {"retention_days": 90}}
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises(ValueError, match="Disable"):
        demo.upgrade_demo(db)
    assert snapshot(db_connection) == before


def test_upgrade_refuses_unexpected_dependent_data_without_mutating_fixture(demo, db, db_connection, users):
    from app.models import UserNotification

    organization, _, marker = prior_event_age_demo(demo, db, users[0])
    db.add(UserNotification(
        user_id=users[0].id, organization_id=organization.id,
        analysis_id=marker["analysis_ids"]["recent"],
        type="analysis", title="Unexpected newer data", message="Preserve me",
    ))
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises(ValueError, match="Unexpected"):
        demo.upgrade_demo(db)
    assert snapshot(db_connection) == before


def test_upgrade_fixture_failure_rolls_back_every_timestamp_and_marker_change(demo, db, db_connection, users, monkeypatch):
    from scripts import retention_demo_fixtures

    prior_event_age_demo(demo, db, users[0])
    before = snapshot(db_connection)

    def fail_payload(*args, **kwargs):
        raise RuntimeError("Synthetic payload upgrade failed")

    monkeypatch.setattr(retention_demo_fixtures, "_result_payload", fail_payload)
    with pytest.raises(RuntimeError, match="Synthetic payload upgrade failed"):
        demo.upgrade_demo(db)
    assert snapshot(db_connection) == before


def test_restore_recovers_original_membership_without_deleting_fixture_history(demo, db, users):
    from app.models import Analysis, Organization, User, UserBurnoutReport

    organization, original, _ = seed(demo, db, users[0])
    org_id = organization.id
    counts = (
        db.query(Analysis).filter_by(organization_id=org_id).count(),
        db.query(UserBurnoutReport).filter_by(organization_id=org_id).count(),
        db.query(User).filter_by(organization_id=org_id).count(),
    )
    demo.restore_membership(db)
    db.expire_all()
    assert membership(users[0]) == original
    assert db.get(Organization, org_id) is not None
    assert db.query(Analysis).filter_by(organization_id=org_id).count() == counts[0]
    assert db.query(UserBurnoutReport).filter_by(organization_id=org_id).count() == counts[1]
    assert db.query(User).filter_by(organization_id=org_id).count() == counts[2] - 1


@pytest.mark.parametrize("changed_field", ["organization_id", "role", "joined_org_at"])
@pytest.mark.parametrize("operation", ["restore_membership", "reset_demo"])
def test_restore_and_reset_refuse_overwriting_membership_changed_after_seed(
    demo, db, db_connection, users, organizations, changed_field, operation,
):
    seed(demo, db, users[0])
    value = {
        "organization_id": organizations[1].id,
        "role": "member",
        "joined_org_at": NOW + timedelta(hours=1),
    }[changed_field]
    setattr(users[0], changed_field, value)
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        getattr(demo, operation)(db)
    assert snapshot(db_connection) == before


def test_reset_restores_owner_and_deletes_only_manifest_rows(
    demo, db, users, organizations, analysis_factory, survey_factory,
):
    from app.models import Analysis, OAuthProvider, Organization, User, UserBurnoutReport

    original_analysis = analysis_factory(coverage(OLD))
    original_survey = survey_factory(OLD, analysis_id=original_analysis.id)
    original_ids = (original_analysis.id, original_survey.id, users[0].id, users[1].id, organizations[0].id)
    organization, original_membership, _ = seed(demo, db, users[0])
    org_id = organization.id
    fixture_user_ids = [user.id for user in db.query(User).filter(User.organization_id == org_id, User.id != users[0].id)]
    demo.reset_demo(db)
    db.expire_all()
    assert membership(users[0]) == original_membership
    assert db.get(Organization, org_id) is None
    assert db.query(Analysis).filter_by(organization_id=org_id).count() == 0
    assert db.query(UserBurnoutReport).filter_by(organization_id=org_id).count() == 0
    assert db.query(User).filter(User.id.in_(fixture_user_ids)).count() == 0
    assert db.query(OAuthProvider).filter(OAuthProvider.user_id.in_(fixture_user_ids)).count() == 0
    assert db.get(Analysis, original_ids[0]).results == coverage(OLD)
    assert db.get(UserBurnoutReport, original_ids[1]).analysis_id == original_ids[0]
    assert all(db.get(model, row_id) is not None for model, row_id in [
        (User, original_ids[2]), (User, original_ids[3]), (Organization, original_ids[4]),
    ])


@pytest.mark.parametrize("extra_type", ["user", "analysis", "survey", "notification"])
@pytest.mark.parametrize("operation", ["reset_demo", "run_demo_cleanup"])
def test_destructive_commands_refuse_unexpected_org_rows(
    demo, db, db_connection, users, extra_type, operation,
):
    from app.models import Analysis, User, UserBurnoutReport
    from app.models.user_notification import UserNotification

    organization, _, _ = seed(demo, db, users[0])
    fields = {"organization_id": organization.id}
    record = {
        "user": lambda: User(**fields, email="unexpected-retention-member@example.invalid", role="member", status="active"),
        "analysis": lambda: Analysis(**fields, user_id=users[0].id, status="completed", results=coverage(OLD)),
        "survey": lambda: UserBurnoutReport(**fields, user_id=users[0].id, email=users[0].email, feeling_score=3, workload_score=3, submitted_at=OLD),
        "notification": lambda: UserNotification(**fields, user_id=users[0].id, type="analysis", title="Untracked fixture-org record"),
    }[extra_type]()
    db.add(record)
    organization.settings = {
        **organization.settings,
        "data_retention": {"retention_days": 90, "age_basis": "analysis_generation", "updated_at": NOW.isoformat(), "updated_by_user_id": users[0].id},
    }
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        getattr(demo, operation)(db)
    assert snapshot(db_connection) == before


def test_seed_rolls_back_membership_and_all_partial_fixture_rows_on_database_failure(
    demo, db, db_connection, users,
):
    from sqlalchemy.exc import SQLAlchemyError

    before = snapshot(db_connection)

    def fail_fixture_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO USER_BURNOUT_REPORTS"):
            raise SQLAlchemyError("Disposable seed insert failure")

    event.listen(db_connection, "before_cursor_execute", fail_fixture_insert)
    try:
        with pytest.raises((SQLAlchemyError, ValueError, RuntimeError)):
            demo.seed_demo(db, users[0].email, now=NOW)
    finally:
        event.remove(db_connection, "before_cursor_execute", fail_fixture_insert)
    assert snapshot(db_connection) == before


@pytest.mark.parametrize("operation", ["reset_demo", "run_demo_cleanup"])
def test_destructive_commands_refuse_foreign_links_to_fixture_analyses(
    demo, db, db_connection, users, organizations, operation,
):
    from app.models import Analysis, UserBurnoutReport

    organization, _, _ = seed(demo, db, users[0])
    fixture_analysis = db.query(Analysis).filter_by(organization_id=organization.id).first()
    foreign_report = UserBurnoutReport(
        organization_id=organizations[1].id, user_id=users[1].id,
        analysis_id=fixture_analysis.id, email=users[1].email,
        feeling_score=3, workload_score=3, submitted_at=RECENT,
    )
    db.add(foreign_report)
    organization.settings = {
        **organization.settings,
        "data_retention": {"retention_days": 90, "age_basis": "analysis_generation", "updated_at": NOW.isoformat(), "updated_by_user_id": users[0].id},
    }
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        getattr(demo, operation)(db)
    assert snapshot(db_connection) == before


def test_cleanup_failure_leaves_fixture_and_original_data_unchanged(
    demo, db, db_connection, users, monkeypatch,
):
    from app.services import retention_cleanup

    organization, _, _ = seed(demo, db, users[0])
    organization.settings = {
        **organization.settings,
        "data_retention": {"retention_days": 90, "age_basis": "analysis_generation", "updated_at": NOW.isoformat(), "updated_by_user_id": users[0].id},
    }
    db.commit()
    before = snapshot(db_connection)

    def fail_cache(*args):
        raise RuntimeError("Disposable cache unavailable")

    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", fail_cache)
    with pytest.raises(RuntimeError, match="Disposable cache unavailable"):
        demo.run_demo_cleanup(db)
    assert snapshot(db_connection) == before


def test_cleanup_applies_generation_age_and_preserves_newer_surveys_and_other_org_data(
    demo, db, db_connection, users, organizations, analysis_factory, survey_factory,
):
    from app.models import Analysis, UserBurnoutReport
    from app.services.data_retention import RetentionPolicyUpdate, update_retention_policy
    from app.services.retention_preview import classify_analysis_result

    original_analysis = analysis_factory(coverage(OLD))
    original_survey = survey_factory(OLD, analysis_id=original_analysis.id)
    original_ids = (original_analysis.id, original_survey.id)
    original_settings = dict(organizations[0].settings)
    organization, _, _ = seed(demo, db, users[0])
    cutoff = NOW - timedelta(days=90)
    analyses = db.query(Analysis).filter_by(organization_id=organization.id).all()
    by_disposition = {
        name: [row.id for row in analyses if classify_analysis_result(row, cutoff).disposition == name]
        for name in ["expired", "retained", "unverifiable"]
    }
    assert all(by_disposition.values()), "The demo should exercise old, recent, and unknown-age results"
    payloads = {row.id: row.results for row in analyses}
    reports = db.query(UserBurnoutReport).filter_by(organization_id=organization.id).all()
    expired_surveys = [row.id for row in reports if row.submitted_at is not None and row.submitted_at < cutoff]
    retained_surveys = [row.id for row in reports if row.submitted_at is None or row.submitted_at >= cutoff]
    recent_links_to_expired = [
        row.id for row in reports if row.id in retained_surveys and row.analysis_id in by_disposition["expired"]
    ]
    assert expired_surveys and retained_surveys and recent_links_to_expired
    update_retention_policy(db, users[0], RetentionPolicyUpdate(retention_days=90, confirm_deletion=True), now=NOW)

    demo.run_demo_cleanup(db)
    db.expire_all()
    for row_id in by_disposition["expired"]:
        assert db.get(Analysis, row_id) is None
    for row_id in by_disposition["retained"] + by_disposition["unverifiable"]:
        assert db.get(Analysis, row_id).results == payloads[row_id]
    assert all(db.get(UserBurnoutReport, row_id) is None for row_id in expired_surveys)
    assert all(db.get(UserBurnoutReport, row_id) is not None for row_id in retained_surveys)
    assert all(db.get(UserBurnoutReport, row_id).analysis_id is None for row_id in recent_links_to_expired)
    assert db.get(Analysis, original_ids[0]).results == coverage(OLD)
    assert db.get(UserBurnoutReport, original_ids[1]).analysis_id == original_ids[0]
    assert organizations[0].settings == original_settings
    before_repeat = snapshot_without_cleanup_metadata(db_connection, organization.id)
    demo.run_demo_cleanup(db)
    assert snapshot_without_cleanup_metadata(db_connection, organization.id) == before_repeat
    from app.services.retention_status import read_cleanup_status
    assert read_cleanup_status(organization).counts.analysis_results_expired == 0


def test_legacy_preview_confirmation_and_cleanup_work_with_mock_fixture(demo, db, users):
    from app.models import Analysis, UserBurnoutReport
    from app.services.data_retention import RetentionPolicyUpdate, update_retention_policy
    from app.services.retention_legacy import legacy_cleanup_status
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview, classify_analysis_result

    organization, _, _ = seed(demo, db, users[0])
    cutoff = NOW - timedelta(days=90)
    legacy_ids = [
        row.id for row in db.query(Analysis).filter_by(organization_id=organization.id)
        if classify_analysis_result(row, cutoff).disposition == "unverifiable"
    ]
    assert legacy_ids
    preview = build_retention_preview(db, organization, RetentionPreviewRequest(
        retention_days=90, clear_unverifiable_analyses=True,
    ), now=NOW)
    assert preview.legacy_cleanup.analysis_candidates == len(legacy_ids)
    update_retention_policy(db, users[0], RetentionPolicyUpdate(
        retention_days=90, confirm_deletion=True,
        clear_unverifiable_analyses=True, confirm_legacy_deletion=True,
        legacy_preview_token=preview.legacy_cleanup.preview_token,
    ), now=NOW)
    assert legacy_cleanup_status(organization).state == "pending"
    unknown_surveys = [
        row.id for row in db.query(UserBurnoutReport).filter_by(organization_id=organization.id)
        if row.submitted_at is None
    ]

    demo.run_demo_cleanup(db)
    db.expire_all()
    assert all(db.get(Analysis, row_id).results is None for row_id in legacy_ids)
    assert legacy_cleanup_status(organization).state == "completed"
    assert all(db.get(UserBurnoutReport, row_id) is not None for row_id in unknown_surveys)


def test_restoring_membership_disables_policy_and_cancels_pending_legacy_clear(demo, db, users):
    from app.services.data_retention import RetentionPolicyUpdate, read_retention_policy, update_retention_policy
    from app.services.retention_legacy import legacy_cleanup_status
    from app.services.retention_preview import RetentionPreviewRequest, build_retention_preview

    organization, original, _ = seed(demo, db, users[0])
    preview = build_retention_preview(db, organization, RetentionPreviewRequest(
        retention_days=90, clear_unverifiable_analyses=True,
    ), now=NOW)
    update_retention_policy(db, users[0], RetentionPolicyUpdate(
        retention_days=90, confirm_deletion=True,
        clear_unverifiable_analyses=True, confirm_legacy_deletion=True,
        legacy_preview_token=preview.legacy_cleanup.preview_token,
    ), now=NOW)
    assert legacy_cleanup_status(organization).state == "pending"
    demo.restore_membership(db)
    db.expire_all()
    assert membership(users[0]) == original
    assert read_retention_policy(organization).retention_days is None
    assert legacy_cleanup_status(organization).state == "cancelled"


@pytest.mark.parametrize("member", [None, "alex", "priya", "noah"])
def test_demo_login_links_use_existing_single_use_exchange_without_passwords(
    demo, db, users, monkeypatch, member,
):
    from urllib.parse import parse_qs, urlparse
    from app.api.endpoints import auth
    from app.auth.jwt import decode_access_token
    from app.models import User

    organization, _, _ = seed(demo, db, users[0])
    before_hash = users[0].password_hash
    monkeypatch.setattr(auth, "datetime", demo.datetime)
    result = demo.login_link(db, member)
    url = urlparse(result["login_url"])
    assert (url.scheme, url.netloc, url.path) == ("http", "localhost:3000", "/auth/success")
    code = parse_qs(url.query)["code"][0]
    row = db.execute(text("SELECT user_id, expires_at, auth_method FROM oauth_temp_codes WHERE code = :code"), {"code": code}).mappings().one()
    selected = users[0] if member is None else db.query(User).filter_by(
        organization_id=organization.id, email=f"{member}@{demo.DEMO_DOMAIN}",
    ).one()
    assert row["user_id"] == selected.id
    assert row["expires_at"] == NOW + timedelta(minutes=5)
    assert row["auth_method"] == "local_retention_demo"
    exchanged = auth.get_oauth_code(db, code)
    assert exchanged["user_id"] == selected.id
    assert decode_access_token(exchanged["jwt_token"])["sub"] == str(selected.id)
    assert auth.get_oauth_code(db, code) is None
    assert users[0].password_hash == before_hash


@pytest.mark.parametrize("provider", ["github", "jira", "linear"])
@pytest.mark.parametrize("member", [None, "alex"])
def test_login_links_refuse_integrations_that_frontend_would_warm(
    demo, db, db_connection, users, provider, member,
):
    from app.models import User
    from app.models.github_integration import GitHubIntegration
    from app.models.jira_integration import JiraIntegration
    from app.models.linear_integration import LinearIntegration

    organization, _, _ = seed(demo, db, users[0])
    selected = users[0] if member is None else db.query(User).filter_by(
        organization_id=organization.id, email=f"{member}@{demo.DEMO_DOMAIN}",
    ).one()
    integration = {
        "github": lambda: GitHubIntegration(user_id=selected.id, github_username="disposable-fixture", github_token=None),
        "jira": lambda: JiraIntegration(user_id=selected.id, jira_cloud_id="disposable-cloud", jira_site_url="disposable.example.invalid", access_token=None),
        "linear": lambda: LinearIntegration(user_id=selected.id, workspace_id="disposable-workspace", access_token=None),
    }[provider]()
    db.add(integration)
    db.commit()
    before = snapshot(db_connection)
    assert db.execute(text("SELECT count(*) FROM oauth_temp_codes")).scalar_one() == 0
    with pytest.raises(ValueError, match="integrations"):
        demo.login_link(db, member)
    assert db.execute(text("SELECT count(*) FROM oauth_temp_codes")).scalar_one() == 0
    assert snapshot(db_connection) == before


def test_reset_preserves_unrelated_auth_codes_and_owner_login_history(demo, db, users):
    from app.models.user_login_event import UserLoginEvent

    organization, original, _ = seed(demo, db, users[0])
    org_id = organization.id
    unrelated_code = "unrelated-disposable-login-code"
    db.execute(text("""
        INSERT INTO oauth_temp_codes (code, jwt_token, user_id, expires_at, auth_method)
        VALUES (:code, :token, :user_id, :expires, 'fixture')
    """), {"code": unrelated_code, "token": "disposable-unrelated-token", "user_id": users[1].id, "expires": NOW + timedelta(minutes=5)})
    login_event = UserLoginEvent(user_id=users[0].id, organization_id=org_id, auth_method="fixture", logged_in_at=NOW)
    db.add(login_event)
    db.commit()
    event_id = login_event.id
    demo.login_link(db)
    demo.login_link(db, "alex")
    demo.reset_demo(db)
    db.expire_all()
    assert membership(users[0]) == original
    assert db.execute(text("SELECT user_id FROM oauth_temp_codes WHERE code = :code"), {"code": unrelated_code}).scalar_one() == users[1].id
    retained_event = db.get(UserLoginEvent, event_id)
    assert retained_event is not None and retained_event.organization_id is None
    assert retained_event.user_id == users[0].id


def test_reset_refuses_demo_prefix_auth_code_owned_by_unrelated_account(
    demo, db, db_connection, users,
):
    organization, _, _ = seed(demo, db, users[0])
    marker = organization.settings[demo.MARKER_KEY]
    code = f"retention_demo_{marker['instance']}_foreign-owner"
    db.execute(text("""
        INSERT INTO oauth_temp_codes (code, jwt_token, user_id, expires_at, auth_method)
        VALUES (:code, :token, :user_id, :expires, 'fixture')
    """), {"code": code, "token": "disposable-unrelated-token", "user_id": users[1].id, "expires": NOW + timedelta(minutes=5)})
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        demo.reset_demo(db)
    assert snapshot(db_connection) == before
    assert db.execute(text("SELECT user_id FROM oauth_temp_codes WHERE code = :code"), {"code": code}).scalar_one() == users[1].id


@pytest.mark.parametrize("before_reset", ["cleanup", "restore"])
def test_reset_completes_after_a_fixture_only_cleanup_or_membership_restore(demo, db, users, before_reset):
    from app.models import Organization
    from app.services.data_retention import RetentionPolicyUpdate, update_retention_policy

    organization, original, _ = seed(demo, db, users[0])
    org_id = organization.id
    if before_reset == "cleanup":
        update_retention_policy(db, users[0], RetentionPolicyUpdate(retention_days=90, confirm_deletion=True), now=NOW)
        demo.run_demo_cleanup(db)
    else:
        demo.restore_membership(db)
    demo.reset_demo(db)
    db.expire_all()
    assert db.get(Organization, org_id) is None
    assert membership(users[0]) == original


@pytest.mark.parametrize("dependent", ["foreign_login_event", "foreign_survey_period"])
def test_reset_refuses_foreign_audit_or_roster_dependencies(
    demo, db, db_connection, users, organizations, dependent,
):
    from app.models import UserCorrelation
    from app.models.survey_period import SurveyPeriod
    from app.models.user_login_event import UserLoginEvent

    organization, _, _ = seed(demo, db, users[0])
    if dependent == "foreign_login_event":
        record = UserLoginEvent(
            user_id=users[1].id, organization_id=organization.id,
            auth_method="disposable-fixture", logged_in_at=NOW,
        )
    else:
        correlation = db.query(UserCorrelation).filter_by(organization_id=organization.id).first()
        record = SurveyPeriod(
            organization_id=organizations[1].id, user_correlation_id=correlation.id,
            user_id=users[1].id, email=users[1].email,
            frequency_type="weekly", period_start_date=NOW.date(),
            period_end_date=(NOW + timedelta(days=6)).date(),
            status="completed", initial_sent_at=NOW, completed_at=NOW,
        )
    db.add(record)
    db.commit()
    before = snapshot(db_connection)
    with pytest.raises((ValueError, RuntimeError)):
        demo.reset_demo(db)
    assert snapshot(db_connection) == before
