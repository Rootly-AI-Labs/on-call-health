"""Read-only retention preview checks against a disposable PostgreSQL database.

RETENTION_TEST_DATABASE_URL must name a PostgreSQL database containing
``retention_test``. The full real model metadata is created in that database;
each test rolls its fixture rows back in an outer transaction. The application's
normal DATABASE_URL is never used by this module's database fixtures.
"""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

PATH = "/auth/organizations/retention/preview"
NOW = datetime(2026, 10, 5, 2, 30, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=90)
OLD = CUTOFF - timedelta(seconds=1)
RECENT = CUTOFF + timedelta(seconds=1)


@pytest.fixture(scope="module")
def retention_engine():
    database_url = os.getenv("RETENTION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set RETENTION_TEST_DATABASE_URL to a disposable PostgreSQL retention_test database")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or "retention_test" not in (url.database or "").lower():
        pytest.fail("Retention tests require PostgreSQL and a database name containing retention_test")

    from app.models import Base

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    # create_all does not upgrade a pre-existing disposable table. This mirrors
    # migration 055 only after the explicit retention_test target guard above.
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS results_generated_at TIMESTAMPTZ"
        ))
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
    records = [
        Organization(
            name=f"Retention Preview {index}",
            domain=f"retention-{suffix}-{index}.example.com",
            slug=f"retention-{suffix}-{index}",
            status="active",
            settings={"unrelated": {"keep": True}},
        )
        for index in range(2)
    ]
    db.add_all(records)
    db.commit()
    return records


@pytest.fixture
def users(db, organizations):
    from app.models import User

    suffix = uuid4().hex
    records = [
        User(
            email=f"retention-{suffix}-{index}@example.com",
            organization_id=organization.id,
            role="admin",
            status="active",
        )
        for index, organization in enumerate(organizations)
    ]
    db.add_all(records)
    db.commit()
    return records


@pytest.fixture
def current_user(users):
    return SimpleNamespace(
        id=users[0].id,
        organization_id=users[0].organization_id,
        role="admin",
        status="active",
    )


@pytest.fixture
def test_app(db, current_user):
    from app.api.endpoints.retention import retention_preview_now, router
    from app.auth.dependencies import get_current_active_user
    from app.models import get_db

    app = FastAPI()
    app.include_router(router, prefix="/auth/organizations/retention")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[retention_preview_now] = lambda: NOW
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def analysis_factory(db, organizations, users):
    from app.models import Analysis

    def make(results=None, *, organization_index=0, **fields):
        defaults = {
            "organization_id": organizations[organization_index].id,
            "user_id": users[organization_index].id,
            "status": "completed",
            "created_at": NOW,
            # Generation belongs to the stored snapshot, independently of the
            # row's creation/completion dates and its source event timestamps.
            "completed_at": NOW if getattr(results, "fixture_generated_at", None) is not None else None,
            "results_generated_at": getattr(results, "fixture_generated_at", None),
            "results": results,
        }
        defaults.update(fields)
        analysis = Analysis(**defaults)
        db.add(analysis)
        db.commit()
        return analysis

    return make


@pytest.fixture
def survey_factory(db, organizations, users):
    from app.models import UserBurnoutReport

    def make(submitted_at=NOW, *, organization_index=0, **fields):
        defaults = {
            "organization_id": organizations[organization_index].id,
            "user_id": users[organization_index].id,
            "email": f"report-{uuid4().hex}@example.com",
            "feeling_score": 3,
            "workload_score": 3,
            "submitted_at": submitted_at,
            "updated_at": NOW,
        }
        defaults.update(fields)
        report = UserBurnoutReport(**defaults)
        db.add(report)
        db.commit()
        return report

    return make


_INFER_GENERATION = object()


class FixtureResult(dict):
    """Carry a fixture generation clock without putting authority in JSON."""


def coverage(start=RECENT, end=NOW, *, generated_at=_INFER_GENERATION, **data):
    result = FixtureResult({
        "metadata": {"date_range": {"start": start.isoformat(), "end": end.isoformat()}},
        **data,
    })
    # Existing test callers use start as their fixture's age. This attribute is
    # consumed ONLY by analysis_factory; JSON persisted by SQLAlchemy has no
    # trusted generation date, and production classification never reads it.
    result.fixture_generated_at = start if generated_at is _INFER_GENERATION else generated_at
    return result


def preview(client, body=None):
    response = client.post(PATH, json={"retention_days": 90} if body is None else body)
    assert response.status_code == 200, response.text
    return response.json()


def parse_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sample_for(result, analysis):
    return next(sample for sample in result["samples"] if sample["analysis_id"] == analysis.id)


def test_disabled_policy_returns_totals_without_candidates(client, analysis_factory, survey_factory, organizations):
    analysis_factory(coverage(OLD))
    survey_factory(OLD)
    result = preview(client, {})
    assert result["organization_id"] == organizations[0].id
    assert result["preview_only"] is True
    assert result["policy_source"] == "saved"
    assert result["enabled"] is False
    assert result["retention_days"] is None
    assert result["cutoff_at"] is None
    assert result["analyses"]["total"] == 1
    assert result["survey_responses"]["total"] == 1
    assert result["analyses"]["expired"] == 0
    assert result["survey_responses"]["expired"] == 0
    assert result["samples"] == []
    assert not any(result["related_records"].values())


def test_proposed_policy_uses_fixed_clock_without_enabling_saved_policy(client, db, organizations):
    result = preview(client)
    assert result["policy_source"] == "proposed"
    assert result["retention_days"] == 90
    assert result["enabled"] is True
    assert parse_datetime(result["evaluated_at"]) == NOW
    assert parse_datetime(result["cutoff_at"]) == CUTOFF
    db.expire_all()
    assert "data_retention" not in organizations[0].settings


def test_saved_policy_and_proposed_disable(client, db, organizations, analysis_factory):
    updated_at = NOW - timedelta(days=1)
    organizations[0].settings = {
        "data_retention": {
            "retention_days": 30,
            "age_basis": "analysis_generation",
            "updated_at": updated_at.isoformat(),
            "updated_by_user_id": 101,
        }
    }
    db.commit()
    analysis_factory(coverage(NOW - timedelta(days=45)))
    saved = preview(client, {})
    assert saved["policy_source"] == "saved"
    assert saved["retention_days"] == 30
    assert parse_datetime(saved["policy_updated_at"]) == updated_at
    assert saved["analyses"]["expired"] == 1
    disabled = preview(client, {"retention_days": None})
    assert disabled["policy_source"] == "proposed"
    assert disabled["enabled"] is False
    assert disabled["analyses"]["expired"] == 0
    db.expire_all()
    assert organizations[0].settings["data_retention"]["retention_days"] == 30


@pytest.mark.parametrize("generated_at,expected", [(OLD, "expired"), (CUTOFF, "retained"), (RECENT, "retained")])
def test_generation_cutoff_is_strictly_older(client, analysis_factory, generated_at, expected):
    analysis = analysis_factory(coverage(RECENT, generated_at=generated_at))
    result = preview(client)
    assert result["analyses"][expected] == 1
    sample = sample_for(result, analysis)
    assert sample["disposition"] == expected
    assert parse_datetime(sample["generation_at"]) == generated_at


def test_generation_age_ignores_creation_completion_and_event_age(client, analysis_factory):
    old = analysis_factory(coverage(RECENT, generated_at=OLD), created_at=NOW, completed_at=NOW)
    recent = analysis_factory(coverage(OLD, generated_at=NOW), created_at=OLD, completed_at=OLD)
    result = preview(client)
    assert result["analyses"]["expired"] == 1
    assert result["analyses"]["retained"] == 1
    assert sample_for(result, old)["disposition"] == "expired"
    assert sample_for(result, recent)["disposition"] == "retained"


@pytest.mark.parametrize("evidence", [
    {"raw_incident_data": [{"attributes": {"created_at": OLD.isoformat()}}]},
    {"raw_incident_data": [{"created_at": OLD.isoformat()}]},
    {"partial_data": {"incidents": [{"attributes": {"created_at": OLD.isoformat()}}]}},
    {"daily_trends": [{"date": (CUTOFF - timedelta(days=1)).date().isoformat()}]},
    {"individual_daily_data": {"person@example.com": {(CUTOFF - timedelta(days=1)).date().isoformat(): {"score": 2}}}},
    {"member_surveys": {"person@example.com": {"survey_responses": [{"submitted_at": OLD.isoformat()}]}}},
], ids=["rootly", "flat-incident", "partial", "daily-trend", "individual-day", "copied-survey"])
def test_recent_generation_retains_all_old_and_mixed_source_content(client, analysis_factory, evidence):
    analysis = analysis_factory(coverage(NOW - timedelta(days=120), generated_at=NOW, **evidence))
    result = preview(client)
    assert result["analyses"]["expired"] == result["analyses"]["unverifiable"] == 0
    assert sample_for(result, analysis)["disposition"] == "retained"


@pytest.mark.parametrize("flag", ["include_github", "include_slack", "include_jira", "include_linear", "include_ai_usage"])
def test_recent_generation_keeps_enabled_enrichment_sources(client, analysis_factory, flag):
    analysis = analysis_factory(coverage(OLD, generated_at=NOW), config={flag: True})
    result = preview(client)
    assert result["analyses"]["retained"] == 1
    assert result["analyses"]["unverifiable"] == 0
    assert sample_for(result, analysis)["disposition"] == "retained"


@pytest.mark.parametrize("field,payload", [
    ("jira_tickets", [{"id": "JIRA-1", "created_at": OLD.isoformat()}]),
    ("linear_issues", [{"id": "LINEAR-1", "created_at": OLD.isoformat()}]),
    ("github_activity", {"commits": [{"committed_at": OLD.isoformat()}]}),
    ("slack_activity", {"message_count": 5}),
    ("openai_usage", {"total_tokens": 1234}),
    ("anthropic_usage", {"tokens": 250}),
    ("rootly_alerts", [{"created_at": OLD.isoformat()}]),
])
@pytest.mark.parametrize("generated_at,expected", [(OLD, "expired"), (NOW, "retained")])
def test_enrichment_content_expires_with_its_generation(client, analysis_factory, field, payload, generated_at, expected):
    analysis = analysis_factory(coverage(RECENT, generated_at=generated_at, **{field: payload}))
    result = preview(client)
    assert result["analyses"][expected] == 1
    assert result["analyses"]["unverifiable"] == 0
    assert sample_for(result, analysis)["disposition"] == expected


def test_timezone_offset_is_normalized_before_generation_cutoff_comparison(client, analysis_factory):
    offset = timezone(timedelta(hours=-4))
    analysis_factory(coverage(RECENT, generated_at=CUTOFF.astimezone(offset)))
    analysis_factory(coverage(RECENT, generated_at=OLD.astimezone(offset)))
    result = preview(client)
    assert result["analyses"]["expired"] == result["analyses"]["retained"] == 1


def test_legacy_serialized_json_uses_completed_generation_fallback(client, analysis_factory):
    import json

    analysis = analysis_factory(json.dumps(coverage(RECENT)), completed_at=OLD)
    result = preview(client)
    assert sample_for(result, analysis)["disposition"] == "expired"
    assert parse_datetime(sample_for(result, analysis)["generation_at"]) == OLD


@pytest.mark.parametrize("completed_at,expected", [(OLD, "expired"), (CUTOFF, "retained"), (NOW, "retained")])
def test_successful_existing_report_uses_completion_when_canonical_stamp_is_missing(
    client, analysis_factory, completed_at, expected
):
    analysis = analysis_factory(
        {"github_activity": {"commit_count": 10}, "slack_activity": {"messages": 12}},
        completed_at=completed_at,
        results_generated_at=None,
        created_at=OLD,
    )
    result = preview(client)
    assert sample_for(result, analysis)["disposition"] == expected
    assert parse_datetime(sample_for(result, analysis)["generation_at"]) == completed_at


@pytest.mark.parametrize("results", [
    {"team_health": {"score": 50}},
    {"raw_incident_data": [{"created_at": RECENT.isoformat()}]},
    {"metadata": {"date_range": {"start": "nonsense", "end": NOW.isoformat()}}},
    {"metadata": {"date_range": {"start": OLD.isoformat(), "end": NOW.isoformat()}}},
    {"metadata": {"generated_at": NOW.isoformat(), "completed_at": NOW.isoformat()}},
    ["legacy unexpected format"],
    coverage(RECENT, generated_at=None, raw_incident_data=[{"attributes": {"created_at": "invalid"}}]),
])
def test_unknown_generation_is_not_inferred_from_creation_source_or_metadata(client, analysis_factory, results):
    analysis = analysis_factory(results, created_at=OLD, completed_at=None, results_generated_at=None)
    result = preview(client)
    assert result["analyses"]["unverifiable"] == 1
    assert result["analyses"]["expired"] == 0
    assert sample_for(result, analysis)["generation_at"] is None
    assert result["warnings"]


@pytest.mark.parametrize("results", [
    {"team_health": {"score": 50}},
    {"raw_incident_data": [{"created_at": "invalid"}]},
    {"metadata": {"date_range": {"start": "nonsense"}}},
    {"messages": [{"ts": True}]},
    ["legacy unexpected format"],
    "malformed historical result",
])
def test_known_generation_does_not_require_source_date_certification(client, analysis_factory, results):
    analysis = analysis_factory(results, results_generated_at=NOW)
    assert sample_for(preview(client), analysis)["disposition"] == "retained"


@pytest.mark.parametrize("timestamp", [True, False, "nonsense", "2026-10-05", NOW.replace(tzinfo=None)])
def test_invalid_canonical_generation_timestamp_fails_closed(timestamp):
    from app.services.retention_preview import classify_analysis_result

    analysis = SimpleNamespace(status="completed", results={"score": 1}, results_generated_at=timestamp, completed_at=NOW, created_at=NOW)
    result = classify_analysis_result(analysis, CUTOFF)
    assert result.disposition == "unverifiable"


@pytest.mark.parametrize("status", ["completed", "failed"])
def test_canonical_generation_survives_terminal_status_changes(client, analysis_factory, status):
    analysis = analysis_factory(coverage(RECENT, generated_at=OLD), status=status, completed_at=NOW)
    assert sample_for(preview(client), analysis)["disposition"] == "expired"


def test_failed_legacy_rerun_completion_cannot_renew_unknown_snapshot(client, analysis_factory):
    analysis = analysis_factory({"score": 1}, status="failed", completed_at=NOW)
    assert sample_for(preview(client), analysis)["disposition"] == "unverifiable"


def test_successful_regeneration_renews_same_saved_analysis(client, db, analysis_factory):
    analysis = analysis_factory(coverage(OLD), created_at=OLD, completed_at=OLD, is_saved=True)
    assert sample_for(preview(client), analysis)["disposition"] == "expired"
    analysis.results = {"score": 2, "raw_incident_data": [{"created_at": OLD.isoformat()}]}
    analysis.results_generated_at = NOW
    analysis.completed_at = NOW
    db.commit()
    result = preview(client)
    assert sample_for(result, analysis)["disposition"] == "retained"
    assert analysis.created_at == OLD


@pytest.mark.parametrize("results", [None, {}])
def test_empty_results_are_distinguished_from_expired_data(client, analysis_factory, results):
    analysis = analysis_factory(results, created_at=OLD)
    result = preview(client)
    assert result["analyses"]["empty"] == 1
    assert result["analyses"]["expired"] == 0
    assert sample_for(result, analysis)["disposition"] == "empty"


@pytest.mark.parametrize("status", ["pending", "running"])
def test_active_analysis_is_deferred(client, analysis_factory, status):
    analysis = analysis_factory(coverage(OLD), status=status)
    result = preview(client)
    assert result["analyses"]["deferred"] == 1
    assert result["analyses"]["expired"] == 0
    assert sample_for(result, analysis)["disposition"] == "deferred"


def test_saved_and_auto_refresh_results_still_expire(client, analysis_factory):
    analysis = analysis_factory(coverage(OLD), is_saved=True, is_auto_refresh=True, auto_refresh_interval="24h")
    result = preview(client)
    assert result["analyses"]["expired"] == 1
    sample = sample_for(result, analysis)
    assert sample["is_saved"] is True
    assert sample["is_auto_refresh"] is True


def test_integration_backed_expired_snapshot_is_regeneration_candidate(client, db, users, analysis_factory):
    from app.models import RootlyIntegration

    integration = RootlyIntegration(user_id=users[0].id, name="Test Integration", api_token="disposable-test-token", platform="rootly")
    db.add(integration)
    db.commit()
    analysis_factory(coverage(OLD), rootly_integration_id=integration.id)
    analysis_factory(coverage(OLD))
    analysis_factory(coverage(RECENT), rootly_integration_id=integration.id)
    result = preview(client)
    assert result["analyses"]["expired"] == 2
    assert result["analyses"]["regeneration_candidates"] == 1


def test_inactive_integration_does_not_count_as_regeneration_candidate(client, db, users, analysis_factory):
    from app.models import RootlyIntegration

    integration = RootlyIntegration(user_id=users[0].id, name="Inactive Test Integration", api_token="disposable-test-token", platform="rootly", is_active=False)
    db.add(integration)
    db.commit()
    analysis_factory(coverage(OLD), rootly_integration_id=integration.id)
    result = preview(client)
    assert result["analyses"]["expired"] == 1
    assert result["analyses"]["regeneration_candidates"] == 0


def test_survey_expiry_uses_submission_time_and_exact_boundary(client, survey_factory):
    survey_factory(OLD)
    survey_factory(CUTOFF)
    survey_factory(RECENT)
    result = preview(client)
    assert result["survey_responses"] == {"total": 3, "expired": 1, "retained": 2, "unverifiable": 0}


def test_missing_survey_submission_age_is_unverifiable(client, db, survey_factory):
    from app.models import UserBurnoutReport

    report = survey_factory(OLD)
    db.query(UserBurnoutReport).filter_by(id=report.id).update({"submitted_at": None})
    db.commit()
    result = preview(client)
    assert result["survey_responses"]["unverifiable"] == 1
    assert result["survey_responses"]["expired"] == 0


def test_other_and_unscoped_organization_records_are_excluded(client, analysis_factory, survey_factory, organizations):
    own = analysis_factory(coverage(OLD))
    analysis_factory(coverage(OLD), organization_index=1)
    analysis_factory(coverage(OLD), organization_id=None)
    survey_factory(OLD)
    survey_factory(OLD, organization_index=1)
    survey_factory(OLD, organization_id=None)
    response = client.post(f"{PATH}?organization_id={organizations[1].id}", json={"retention_days": 90})
    assert response.status_code == 200
    result = response.json()
    assert result["organization_id"] == organizations[0].id
    assert result["analyses"]["total"] == result["analyses"]["expired"] == 1
    assert result["survey_responses"]["total"] == result["survey_responses"]["expired"] == 1
    assert [sample["analysis_id"] for sample in result["samples"]] == [own.id]


def test_counts_linked_records_without_expiring_recent_surveys(client, db, organizations, users, analysis_factory, survey_factory):
    from app.models import IntegrationMapping, SurveyPeriod, UserCorrelation, UserNotification, WeeklyDigestLog

    expired = analysis_factory(coverage(OLD))
    retained = analysis_factory(coverage(RECENT))
    old_report = survey_factory(OLD)
    survey_factory(RECENT, analysis_id=expired.id)
    survey_factory(RECENT, analysis_id=retained.id)
    correlation = UserCorrelation(user_id=users[0].id, organization_id=organizations[0].id, email=users[0].email)
    db.add(correlation)
    db.flush()
    db.add_all([
        IntegrationMapping(organization_id=organizations[0].id, user_id=users[0].id, analysis_id=expired.id, source_platform="rootly", source_identifier="expired", target_platform="slack"),
        IntegrationMapping(organization_id=organizations[0].id, user_id=users[0].id, analysis_id=retained.id, source_platform="rootly", source_identifier="retained", target_platform="slack"),
        UserNotification(organization_id=organizations[0].id, user_id=users[0].id, analysis_id=expired.id, type="analysis", title="Expired results"),
        UserNotification(organization_id=organizations[0].id, user_id=users[0].id, analysis_id=retained.id, type="analysis", title="Retained results"),
        SurveyPeriod(organization_id=organizations[0].id, user_correlation_id=correlation.id, user_id=users[0].id, email=users[0].email, frequency_type="daily", period_start_date=OLD.date(), period_end_date=OLD.date(), initial_sent_at=OLD, response_id=old_report.id),
        WeeklyDigestLog(user_id=users[0].id, analysis_id=expired.id, week_start_date=OLD.date()),
    ])
    db.commit()
    result = preview(client)
    assert result["analyses"]["expired"] == 1
    assert result["survey_responses"]["expired"] == 1
    assert result["survey_responses"]["retained"] == 2
    assert result["related_records"] == {
        "analysis_mappings": 1,
        "analysis_notifications": 1,
        "survey_links_to_clear": 1,
        "survey_period_links_to_clear": 1,
        "digest_links_to_clear": 1,
        "references_requiring_review": 0,
    }


def test_cross_organization_linked_rows_require_review(client, db, organizations, users, analysis_factory, survey_factory):
    from app.models import IntegrationMapping, UserNotification, WeeklyDigestLog

    expired = analysis_factory(coverage(OLD))
    survey_factory(RECENT, organization_index=1, analysis_id=expired.id)
    db.add_all([
        IntegrationMapping(organization_id=organizations[1].id, user_id=users[1].id, analysis_id=expired.id, source_platform="rootly", source_identifier="wrong-org", target_platform="slack"),
        UserNotification(organization_id=None, user_id=users[0].id, analysis_id=expired.id, type="analysis", title="Unscoped results"),
        WeeklyDigestLog(user_id=users[1].id, analysis_id=expired.id, week_start_date=OLD.date()),
    ])
    db.commit()
    result = preview(client)
    assert result["related_records"]["references_requiring_review"] == 4
    assert result["related_records"]["analysis_mappings"] == 0
    assert result["related_records"]["analysis_notifications"] == 0
    assert result["related_records"]["survey_links_to_clear"] == 0
    assert result["related_records"]["digest_links_to_clear"] == 0
    assert result["warnings"]


def test_preview_is_read_only_and_repeatable(client, db, db_connection, organizations, analysis_factory, survey_factory, monkeypatch):
    from app.models import Base

    analysis_factory(coverage(OLD), is_saved=True)
    survey_factory(OLD)
    organizations[0].settings = {"data_retention": {"retention_days": 90}, "unrelated": {"keep": True}}
    db.commit()

    def snapshot():
        return {
            table.name: list(db_connection.execute(select(table).order_by(*table.primary_key.columns)).mappings())
            for table in Base.metadata.sorted_tables
        }

    before = snapshot()

    def reject_commit(*args, **kwargs):
        raise AssertionError("Preview must not commit")

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError(f"Preview issued a write: {statement}")

    monkeypatch.setattr(db, "commit", reject_commit)
    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        first = preview(client, {})
        second = preview(client, {})
        assert first == second
        assert snapshot() == before
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)


def test_preview_does_not_autoflush_pending_changes(client, db, organizations, analysis_factory, monkeypatch):
    analysis_factory(coverage(OLD))
    organizations[0].name = "Pending unrelated edit"

    def reject_flush(*args, **kwargs):
        raise AssertionError("Preview must not autoflush pending changes")

    monkeypatch.setattr(db, "flush", reject_flush)
    assert preview(client)["analyses"]["expired"] == 1


def test_sample_cap_preserves_full_counts(client, db, organizations, users):
    from app.models import Analysis

    db.add_all([
        Analysis(organization_id=organizations[0].id, user_id=users[0].id, results=coverage(OLD), status="completed", created_at=NOW, results_generated_at=OLD)
        for _ in range(105)
    ])
    db.commit()
    result = preview(client)
    assert result["analyses"]["total"] == result["analyses"]["expired"] == 105
    assert len(result["samples"]) == 100
    assert result["samples_truncated"] is True


@pytest.mark.parametrize("days", [-1, 0, 3651, 1.5, "90", True, False, [], {}])
def test_invalid_proposed_policy_is_rejected(client, days):
    assert client.post(PATH, json={"retention_days": days}).status_code == 422


@pytest.mark.parametrize("field", ["organization_id", "scope", "age_basis", "confirm_deletion"])
def test_preview_rejects_extra_body_fields(client, organizations, field):
    assert client.post(PATH, json={"retention_days": 90, field: organizations[1].id}).status_code == 422


def test_preview_requires_authentication(client, test_app):
    from app.auth.dependencies import get_current_active_user

    del test_app.dependency_overrides[get_current_active_user]
    assert client.post(PATH, json={"retention_days": 90}).status_code == 401


def test_member_cannot_preview_deletion(client, current_user):
    current_user.role = "member"
    assert client.post(PATH, json={"retention_days": 90}).status_code == 403


def test_user_without_organization_cannot_preview(client, current_user):
    current_user.organization_id = None
    assert client.post(PATH, json={"retention_days": 90}).status_code == 400


def test_missing_organization_cannot_preview(client, current_user, db):
    from app.models import Organization

    current_user.organization_id = db.scalar(select(func.max(Organization.id))) + 1
    assert client.post(PATH, json={"retention_days": 90}).status_code == 404


@pytest.mark.parametrize("status", ["pending", "inactive", "suspended"])
def test_inactive_user_cannot_preview(client, current_user, status):
    current_user.status = status
    assert client.post(PATH, json={"retention_days": 90}).status_code == 403


@pytest.mark.parametrize("status", ["pending", "inactive", "suspended"])
def test_inactive_organization_cannot_preview(client, db, organizations, status):
    organizations[0].status = status
    db.commit()
    assert client.post(PATH, json={"retention_days": 90}).status_code == 403
