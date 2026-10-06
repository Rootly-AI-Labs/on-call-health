"""Survey read boundaries use disposable PostgreSQL rows and a fixed clock."""
import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import event

from .test_retention_preview import (
    CUTOFF, NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, survey_factory, users,
)


@pytest.fixture(autouse=True)
def fixed_survey_clock(monkeypatch):
    from app.api.endpoints import analyses, rootly, slack, surveys

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    for module in (analyses, rootly, slack, surveys):
        monkeypatch.setattr(module, "datetime", Clock)
    monkeypatch.setattr(
        slack, "get_utc_day_bounds",
        lambda: (NOW.replace(hour=0, minute=0, second=0, microsecond=0), NOW),
    )


@pytest.fixture
def enabled_policy(db, organizations):
    organization = organizations[0]
    organization.settings = {**organization.settings, "data_retention": {"retention_days": 90}}
    db.commit()
    return organization


def roster_result(*emails):
    return coverage(RECENT, team_analysis={"members": [{"user_email": email} for email in emails]})


def survey_status(db, user, analysis):
    from app.api.endpoints.slack import get_team_survey_status

    return asyncio.run(get_team_survey_status(analysis.id, current_user=user, db=db))


def user_results(db, user, *, target=None, days=365):
    from app.api.endpoints.surveys import get_user_survey_results

    return get_user_survey_results((target or user).id, days=days, current_user=user, db=db)


def test_linked_survey_status_respects_own_submission_age_and_exact_cutoff(
    db, enabled_policy, users, analysis_factory, survey_factory
):
    from app.models import UserBurnoutReport

    emails = ["old@example.com", "boundary@example.com", "recent@example.com", "unknown@example.com", "future@example.com"]
    analysis = analysis_factory(roster_result(*emails))
    survey_factory(OLD, email=emails[0], analysis_id=analysis.id)
    survey_factory(CUTOFF, email=emails[1], analysis_id=analysis.id)
    survey_factory(RECENT, email=emails[2], analysis_id=analysis.id)
    unknown = survey_factory(OLD, email=emails[3], analysis_id=analysis.id)
    survey_factory(NOW + timedelta(days=1), email=emails[4], analysis_id=analysis.id)
    db.query(UserBurnoutReport).filter_by(id=unknown.id).update({"submitted_at": None})
    db.commit()

    result = survey_status(db, users[0], analysis)
    assert result["responses_collected"] == 2
    assert {row["user_email"] for row in result["survey_responses"]} == set(emails[1:3])


@pytest.mark.parametrize("enabled", [False, True])
def test_survey_status_scopes_same_email_and_analysis_links_to_organization(
    db, organizations, users, analysis_factory, survey_factory, enabled
):
    if enabled:
        organizations[0].settings = {"data_retention": {"retention_days": 90}}
        db.commit()
    email = "shared@example.com"
    analysis = analysis_factory(roster_result(email))
    survey_factory(RECENT, email=email, analysis_id=analysis.id, feeling_score=2)
    # These newer records must not mask the organization's own linked response.
    survey_factory(NOW, email=email, organization_index=1, analysis_id=analysis.id, feeling_score=5)
    survey_factory(NOW, email=email, organization_id=None, analysis_id=analysis.id, feeling_score=4)
    result = survey_status(db, users[0], analysis)
    assert result["responses_collected"] == 1
    assert result["survey_responses"][0]["feeling_score"] == 2


def test_retention_does_not_prevent_current_unlinked_team_responses(
    db, enabled_policy, users, analysis_factory, survey_factory
):
    email = "scheduled@example.com"
    analysis = analysis_factory(roster_result(email))
    survey_factory(NOW, email=email, analysis_id=None)
    result = survey_status(db, users[0], analysis)
    assert result["responses_collected"] == 1
    assert result["non_responders"] == []


@pytest.mark.parametrize("results,status", [
    (coverage(OLD), "completed"),
    ({"team_analysis": {"members": [{"user_email": "member@example.com"}]}}, "completed"),
    (coverage(RECENT), "pending"),
    (coverage(RECENT), "running"),
])
def test_survey_status_rejects_expired_unverifiable_and_in_progress_snapshots(
    db, enabled_policy, users, analysis_factory, results, status
):
    analysis = analysis_factory(results, status=status)
    with pytest.raises(HTTPException) as exc:
        survey_status(db, users[0], analysis)
    assert exc.value.status_code == 410


def test_empty_preserved_analysis_returns_no_survey_roster(
    db, enabled_policy, users, analysis_factory, survey_factory
):
    analysis = analysis_factory(None)
    survey_factory(NOW, email="retained@example.com", analysis_id=analysis.id)
    result = survey_status(db, users[0], analysis)
    assert result["total_members"] == result["responses_collected"] == 0
    assert result["survey_responses"] == []


def test_disabled_policy_keeps_older_linked_survey_status_behavior(
    db, users, analysis_factory, survey_factory
):
    email = "old@example.com"
    analysis = analysis_factory(roster_result(email))
    survey_factory(OLD, email=email, analysis_id=analysis.id)
    result = survey_status(db, users[0], analysis)
    assert result["responses_collected"] == 1


def test_analysis_from_users_previous_organization_is_not_visible(
    db, organizations, users, analysis_factory
):
    analysis = analysis_factory(roster_result("member@example.com"))
    users[0].organization_id = organizations[1].id
    db.commit()
    with pytest.raises(HTTPException) as exc:
        survey_status(db, users[0], analysis)
    assert exc.value.status_code == 404


def test_orgless_demo_survey_status_is_scoped_to_its_user(
    db, users, analysis_factory, survey_factory
):
    users[0].organization_id = None
    db.commit()
    email = "same-demo@example.com"
    analysis = analysis_factory(roster_result(email), organization_id=None)
    survey_factory(RECENT, email=email, organization_id=None, user_id=users[0].id, analysis_id=analysis.id, feeling_score=2)
    survey_factory(NOW, email=email, organization_id=None, user_id=users[1].id, analysis_id=analysis.id, feeling_score=5)
    result = survey_status(db, users[0], analysis)
    assert result["responses_collected"] == 1
    assert result["survey_responses"][0]["feeling_score"] == 2


def test_user_results_respect_saved_policy_independently_of_requested_days(
    db, enabled_policy, users, survey_factory
):
    expired = survey_factory(OLD)
    boundary = survey_factory(CUTOFF)
    recent = survey_factory(RECENT)
    future = survey_factory(NOW + timedelta(days=1))
    result = user_results(db, users[0])
    assert {record["id"] for record in result["results"]} == {boundary.id, recent.id}
    assert expired.id not in {record["id"] for record in result["results"]}
    assert future.id not in {record["id"] for record in result["results"]}


def test_requested_shorter_user_results_window_still_applies(
    db, enabled_policy, users, survey_factory
):
    survey_factory(NOW - timedelta(days=10))
    within_request = survey_factory(NOW - timedelta(days=1))
    result = user_results(db, users[0], days=7)
    assert [record["id"] for record in result["results"]] == [within_request.id]


@pytest.mark.parametrize("enabled", [False, True])
def test_user_results_exclude_other_and_unscoped_organization_reports(
    db, organizations, users, survey_factory, enabled
):
    if enabled:
        organizations[0].settings = {"data_retention": {"retention_days": 90}}
        db.commit()
    own = survey_factory(NOW, user_id=users[0].id)
    survey_factory(NOW, organization_index=1, user_id=users[0].id)
    survey_factory(NOW, organization_id=None, user_id=users[0].id)
    result = user_results(db, users[0])
    assert [record["id"] for record in result["results"]] == [own.id]


def test_disabled_user_results_keeps_requested_historical_window(db, users, survey_factory):
    historical = survey_factory(OLD)
    result = user_results(db, users[0])
    assert [record["id"] for record in result["results"]] == [historical.id]


def test_other_organization_target_user_remains_forbidden(db, users):
    with pytest.raises(HTTPException) as exc:
        user_results(db, users[0], target=users[1])
    assert exc.value.status_code == 403


def test_personal_admin_can_read_only_their_own_personal_reports(db, users, survey_factory):
    users[0].organization_id = None
    users[1].organization_id = None
    db.commit()
    own = survey_factory(NOW, user_id=users[0].id, organization_id=None)
    survey_factory(NOW, user_id=users[1].id, organization_id=None)
    result = user_results(db, users[0])
    assert [record["id"] for record in result["results"]] == [own.id]


def test_null_organization_does_not_authorize_another_personal_account(db, users):
    users[0].organization_id = None
    users[1].organization_id = None
    db.commit()
    with pytest.raises(HTTPException) as exc:
        user_results(db, users[0], target=users[1])
    assert exc.value.status_code == 403


def test_member_cannot_read_admin_user_results(db, users):
    users[0].role = "member"
    with pytest.raises(HTTPException) as exc:
        user_results(db, users[0])
    assert exc.value.status_code == 403


def test_survey_reads_do_not_write_or_delete_any_records(
    db, db_connection, enabled_policy, users, analysis_factory, survey_factory
):
    email = "member@example.com"
    analysis = analysis_factory(roster_result(email))
    survey_factory(OLD, email=email, analysis_id=analysis.id)
    survey_factory(NOW, email=email, analysis_id=analysis.id)

    def reject_write(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(maxsplit=1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}:
            raise AssertionError(f"Survey read issued a write: {statement}")

    event.listen(db_connection, "before_cursor_execute", reject_write)
    try:
        assert survey_status(db, users[0], analysis)["responses_collected"] == 1
        assert len(user_results(db, users[0])["results"]) == 1
    finally:
        event.remove(db_connection, "before_cursor_execute", reject_write)


def test_connected_user_survey_count_enforces_submission_age_and_exact_cutoff(
    db, users, survey_factory
):
    from app.api.endpoints.rootly import _get_scoped_survey_count
    from app.models import UserBurnoutReport

    email = "counted@example.com"
    survey_factory(OLD, email=email)
    survey_factory(CUTOFF, email=email)
    survey_factory(RECENT, email=email)
    survey_factory(NOW + timedelta(days=1), email=email)
    unknown = survey_factory(NOW, email=email)
    db.query(UserBurnoutReport).filter_by(id=unknown.id).update({"submitted_at": None})
    db.commit()
    assert _get_scoped_survey_count(db, users[0], email, CUTOFF) == 2


@pytest.mark.parametrize("cutoff", [None, CUTOFF])
def test_connected_user_survey_count_never_counts_other_organization_or_personal_rows(
    db, users, survey_factory, cutoff
):
    from app.api.endpoints.rootly import _get_scoped_survey_count

    email = "shared-count@example.com"
    survey_factory(NOW, email=email)
    survey_factory(NOW, email=email, organization_index=1)
    survey_factory(NOW, email=email, organization_id=None)
    assert _get_scoped_survey_count(db, users[0], email, cutoff) == 1


def test_personal_connected_user_count_excludes_same_email_from_other_personal_accounts(
    db, users, survey_factory
):
    from app.api.endpoints.rootly import _get_scoped_survey_count

    users[0].organization_id = None
    users[1].organization_id = None
    db.commit()
    email = "personal-count@example.com"
    survey_factory(NOW, email=email, user_id=users[0].id, organization_id=None)
    survey_factory(NOW, email=email, user_id=users[1].id, organization_id=None)
    assert _get_scoped_survey_count(db, users[0], email, None) == 1


def test_disabled_connected_user_count_preserves_historical_total(db, users, survey_factory):
    from app.api.endpoints.rootly import _get_scoped_survey_count

    email = "historical-count@example.com"
    survey_factory(OLD, email=email)
    survey_factory(RECENT, email=email)
    assert _get_scoped_survey_count(db, users[0], email, None) == 2


def test_connected_user_page_applies_saved_policy_before_counting(
    db, enabled_policy, organizations, users, survey_factory
):
    from app.api.endpoints.rootly import get_synced_users
    from app.models import UserCorrelation

    email = "roster-count@example.com"
    correlation = UserCorrelation(
        organization_id=organizations[0].id,
        user_id=None,
        email=email,
        name="Retention Count Test",
    )
    db.add(correlation)
    db.commit()
    survey_factory(OLD, email=email)
    survey_factory(CUTOFF, email=email)
    survey_factory(NOW, email=email, organization_index=1)
    result = asyncio.run(get_synced_users(
        integration_id=None, include_oncall_status=False, current_user=users[0], db=db,
    ))
    assert next(member for member in result["users"] if member["email"] == email)["survey_count"] == 1
