"""Digest policy checks using disposable PostgreSQL data and mocked email only."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from .test_retention_preview import (
    NOW as FIXTURE_NOW, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, users,
)


NOW = FIXTURE_NOW.replace(hour=10, minute=0)
CUTOFF = NOW - timedelta(days=90)


@pytest.fixture
def service(monkeypatch, db_connection):
    from app.services import weekly_digest_service

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(weekly_digest_service, "datetime", FixedDatetime)
    monkeypatch.setattr(weekly_digest_service.settings, "WEEKLY_DIGEST_ENABLED", True)
    monkeypatch.setattr(weekly_digest_service.settings, "WEEKLY_DIGEST_FORCE_SEND", True)
    monkeypatch.setattr(weekly_digest_service, "_get_user_timezone", lambda *args: "UTC")
    monkeypatch.setattr(weekly_digest_service, "_generate_unsubscribe_token", lambda *args: "test-token")
    monkeypatch.setattr(
        weekly_digest_service, "SessionLocal",
        lambda: Session(bind=db_connection, join_transaction_mode="create_savepoint"),
    )
    builds, sends = [], []

    def build(**kwargs):
        builds.append(kwargs["results"])
        return {"subject": "Test", "text": "Test", "html": "Test"}

    async def send(**kwargs):
        sends.append(kwargs)
        return True

    monkeypatch.setattr(weekly_digest_service, "_build_email_content", build)
    monkeypatch.setattr(weekly_digest_service, "_send_resend_email", send)
    return weekly_digest_service, builds, sends


@pytest.fixture
def enable_policy(db, organizations, users):
    organizations[0].settings = {"data_retention": {"retention_days": 90, "age_basis": "analysis_generation"}}
    users[0].weekly_digest_enabled = True
    db.commit()


@pytest.mark.parametrize("mode", ["test", "scheduled"])
@pytest.mark.parametrize("kind", ["expired", "unverifiable", "empty", "foreign", "unknown_organization"])
def test_invalid_result_never_builds_or_sends_digest(
    db, service, enable_policy, users, organizations, analysis_factory, mode, kind,
):
    digest, builds, sends = service
    fields = {"is_auto_refresh": True}
    result = coverage(NOW - timedelta(days=1), end=NOW)
    if kind == "expired":
        result = coverage(CUTOFF - timedelta(seconds=1), end=NOW)
    elif kind == "unverifiable":
        result = {"team_health": {"overall_score": 1}}
    elif kind == "empty":
        result = None
    elif kind == "foreign":
        fields["organization_id"] = organizations[1].id
    elif kind == "unknown_organization":
        fields["organization_id"] = None
    analysis_factory(result, **fields)

    if mode == "test":
        response = asyncio.run(digest.send_weekly_digest_test(db, users[0].id))
        assert response["sent"] is False
    else:
        asyncio.run(digest.check_and_send_weekly_digests())
    assert builds == sends == []


@pytest.mark.parametrize("mode", ["test", "scheduled"])
def test_retained_result_can_send(db, service, enable_policy, users, analysis_factory, mode):
    digest, builds, sends = service
    result = coverage(NOW - timedelta(days=1), end=NOW)
    analysis_factory(result, is_auto_refresh=True)
    if mode == "test":
        assert asyncio.run(digest.send_weekly_digest_test(db, users[0].id))["sent"] is True
    else:
        asyncio.run(digest.check_and_send_weekly_digests())
    assert builds == [result]
    assert len(sends) == 1


def test_disabled_policy_preserves_legacy_digest(db, service, users, analysis_factory):
    digest, builds, sends = service
    result = {"team_health": {"overall_score": 1}}
    analysis_factory(result, is_auto_refresh=True, completed_at=NOW)
    assert asyncio.run(digest.send_weekly_digest_test(db, users[0].id))["sent"] is True
    assert builds == [result]
    assert len(sends) == 1


@pytest.mark.parametrize("mode", ["test", "scheduled"])
def test_personal_analysis_without_org_preserves_legacy_digest(
    db, service, users, analysis_factory, mode,
):
    digest, builds, sends = service
    users[0].organization_id = None
    users[0].weekly_digest_enabled = True
    db.commit()
    result = {"team_health": {"overall_score": 1}}
    analysis_factory(result, is_auto_refresh=True, organization_id=None, completed_at=NOW)
    if mode == "test":
        assert asyncio.run(digest.send_weekly_digest_test(db, users[0].id))["sent"] is True
    else:
        asyncio.run(digest.check_and_send_weekly_digests())
    assert builds == [result]
    assert len(sends) == 1


def test_deleted_result_is_refreshed_instead_of_using_identity_map_snapshot(
    db, service, enable_policy, users, analysis_factory,
):
    from app.models import Analysis

    digest, builds, sends = service
    record = analysis_factory(coverage(NOW - timedelta(days=1), end=NOW), is_auto_refresh=True)
    old_results = record.results
    db.execute(update(Analysis).where(Analysis.id == record.id).values(results=None).execution_options(synchronize_session=False))
    db.flush()
    assert record.results == old_results
    assert digest._get_digest_analysis_if_retained(db, users[0], record.id) is None
    assert record.results is None
    assert builds == sends == []


def test_policy_is_refreshed_before_using_cached_result(
    db, service, enable_policy, users, organizations, analysis_factory,
):
    from app.models import Organization

    digest, builds, sends = service
    record = analysis_factory(coverage(NOW - timedelta(days=2), end=NOW), is_auto_refresh=True)
    db.execute(update(Organization).where(Organization.id == organizations[0].id).values(
        settings={"data_retention": {"retention_days": 1, "age_basis": "analysis_generation"}},
    ).execution_options(synchronize_session=False))
    db.flush()
    assert digest._get_digest_analysis_if_retained(db, users[0], record.id) is None
    assert builds == sends == []


@pytest.mark.parametrize("state", ["missing", "inactive", "invalid_policy"])
def test_org_without_valid_policy_context_is_blocked(
    db, service, enable_policy, users, organizations, analysis_factory, state,
):
    digest, builds, sends = service
    record = analysis_factory(coverage(NOW - timedelta(days=1), end=NOW), is_auto_refresh=True)
    if state == "missing":
        users[0].organization_id = None
    elif state == "inactive":
        organizations[0].status = "inactive"
    else:
        organizations[0].settings = {"data_retention": {"retention_days": "invalid"}}
    db.commit()
    assert digest._get_digest_analysis_if_retained(db, users[0], record.id) is None
    assert builds == sends == []


def test_policy_change_after_claim_skips_email_and_releases_claim_for_regeneration(
    db, service, enable_policy, users, organizations, analysis_factory, monkeypatch,
):
    from app.models import Organization, WeeklyDigestLog

    digest, builds, sends = service
    monkeypatch.setattr(digest.settings, "WEEKLY_DIGEST_FORCE_SEND", False)
    record = analysis_factory(coverage(NOW - timedelta(days=2), end=NOW), is_auto_refresh=True)
    original_guard = digest._get_digest_analysis_if_retained
    organization_id = organizations[0].id
    user_id = users[0].id
    db.commit()
    calls = 0

    def change_after_claim(session, user, analysis_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            session.execute(update(Organization).where(Organization.id == organization_id).values(
                settings={"data_retention": {"retention_days": 1, "age_basis": "analysis_generation"}},
            ).execution_options(synchronize_session=False))
            session.flush()
        return original_guard(session, user, analysis_id)

    monkeypatch.setattr(digest, "_get_digest_analysis_if_retained", change_after_claim)
    asyncio.run(digest.check_and_send_weekly_digests())
    assert calls == 2
    assert builds == sends == []
    assert db.query(WeeklyDigestLog).filter(WeeklyDigestLog.user_id == user_id).count() == 0

    record.results = coverage(NOW - timedelta(hours=1), end=NOW)
    record.results_generated_at = NOW
    record.completed_at = NOW
    db.commit()
    asyncio.run(digest.check_and_send_weekly_digests())
    assert len(sends) == 1
    assert db.query(WeeklyDigestLog).filter(WeeklyDigestLog.user_id == user_id).count() == 1


def test_failed_claim_cleanup_does_not_abort_other_recipients(
    db, service, enable_policy, users, analysis_factory, monkeypatch, caplog,
):
    from app.models import WeeklyDigestLog

    digest, builds, sends = service
    monkeypatch.setattr(digest.settings, "WEEKLY_DIGEST_FORCE_SEND", False)
    users[1].weekly_digest_enabled = True
    db.commit()
    first = analysis_factory(coverage(NOW - timedelta(days=1), end=NOW), is_auto_refresh=True)
    analysis_factory(coverage(NOW - timedelta(hours=1), end=NOW), organization_index=1, is_auto_refresh=True)
    first_analysis_id, first_user_id, second_email = first.id, users[0].id, users[1].email
    db.commit()
    original_guard = digest._get_digest_analysis_if_retained
    original_delete = Session.delete
    first_calls = 0

    def guard(session, user, analysis_id):
        nonlocal first_calls
        if analysis_id == first_analysis_id:
            first_calls += 1
            if first_calls == 2:
                return None
        return original_guard(session, user, analysis_id)

    def fail_claim_cleanup(session, record):
        if isinstance(record, WeeklyDigestLog) and record.user_id == first_user_id:
            raise RuntimeError("Simulated send-slot cleanup failure")
        return original_delete(session, record)

    monkeypatch.setattr(digest, "_get_digest_analysis_if_retained", guard)
    monkeypatch.setattr(Session, "delete", fail_claim_cleanup)
    asyncio.run(digest.check_and_send_weekly_digests())
    assert first_calls == 2
    assert len(sends) == 1
    assert sends[0]["to_email"] == second_email
    assert f"Weekly digest failed for analysis {first_analysis_id}" in caplog.text
    assert "Weekly digest scheduler error" not in caplog.text
