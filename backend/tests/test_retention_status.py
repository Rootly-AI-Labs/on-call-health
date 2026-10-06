"""Cleanup metadata, retry fencing and privacy using disposable PostgreSQL."""
from datetime import timedelta

import pytest

from .test_retention_preview import (
    NOW, db, db_connection, organizations, retention_engine, users,
)


def configure(organization, days=90):
    organization.settings = {**organization.settings, "data_retention": {
        "retention_days": days, "updated_at": NOW.isoformat(),
    }}


def success(organization, *, started_at=NOW, finished_at=NOW, expired=3):
    from app.services.retention_cleanup import RetentionCleanupResult
    from app.services.retention_status import policy_and_legacy_revision, record_cleanup_success
    version, legacy_id = policy_and_legacy_revision(organization)
    result = RetentionCleanupResult(organization_id=organization.id, enabled=True,
        cutoff_at=NOW-timedelta(days=90), policy_updated_at=NOW,
        analysis_results_expired=expired, survey_responses_deleted=1)
    record_cleanup_success(organization, result, started_at=started_at, finished_at=finished_at,
                           policy_version=version, legacy_request_id=legacy_id)


def test_default_disabled_status_is_read_only_and_not_scheduled(db, organizations):
    from copy import deepcopy
    from app.services.retention_status import cleanup_status_response
    before = deepcopy(organizations[0].settings)
    status = cleanup_status_response(organizations[0], now=NOW)
    assert status.state == "never" and status.next_cleanup_due_at is None
    assert status.last_success_at is None and status.counts.analysis_results_expired == 0
    assert organizations[0].settings == before


def test_success_counts_cadence_and_policy_version_preserve_other_settings(db, organizations):
    from app.services.data_retention import retention_policy_version
    from app.services.retention_status import cleanup_due_at, cleanup_status_response
    org = organizations[0]
    configure(org)
    original_version = retention_policy_version(org)
    success(org, finished_at=NOW+timedelta(minutes=2))
    db.commit()
    status = cleanup_status_response(org, now=NOW+timedelta(minutes=3))
    assert status.state == "succeeded"
    assert status.last_success_at == NOW+timedelta(minutes=2)
    assert status.counts.analysis_results_expired == 3
    assert status.counts.survey_responses_deleted == 1
    assert org.settings["unrelated"] == {"keep": True}
    assert retention_policy_version(org) == original_version
    assert cleanup_due_at(org, now=NOW+timedelta(hours=1)) == NOW.replace(hour=3, minute=0, second=0, microsecond=0)


def test_failure_retains_success_counts_and_backoff_starts_after_finish(db, organizations):
    from app.services.retention_status import (
        cleanup_due_at, policy_and_legacy_revision, read_cleanup_status, record_cleanup_failure,
    )
    org = organizations[0]
    configure(org)
    success(org)
    attempt = NOW+timedelta(days=1)
    version, legacy_id = policy_and_legacy_revision(org)
    assert record_cleanup_failure(org, now=attempt, finished_at=attempt+timedelta(minutes=5),
                                  policy_version=version, legacy_request_id=legacy_id, error_code="cache_unavailable")
    status = read_cleanup_status(org)
    assert status.last_success_at == NOW and status.counts.analysis_results_expired == 3
    assert status.next_retry_at == attempt+timedelta(minutes=20)
    assert cleanup_due_at(org, now=attempt+timedelta(minutes=6), mode="retry") == status.next_retry_at
    assert "rolled back" in status.message


def test_failed_changed_policy_obeys_its_retry_delay(db, organizations):
    from app.services.retention_status import cleanup_due_at, policy_and_legacy_revision, record_cleanup_failure
    org = organizations[0]
    configure(org)
    success(org)
    configure(org, 30)
    attempt = NOW+timedelta(minutes=1)
    version, legacy_id = policy_and_legacy_revision(org)
    assert record_cleanup_failure(org, now=attempt, policy_version=version,
                                  legacy_request_id=legacy_id, error_code="unexpected_error")
    assert cleanup_due_at(org, now=attempt+timedelta(minutes=2), mode="retry") == attempt+timedelta(minutes=15)


@pytest.mark.parametrize("change", ["policy", "disable", "newer_success", "inactive"])
def test_stale_failures_cannot_overwrite_current_outcome(db, organizations, change):
    from copy import deepcopy
    from app.services.retention_status import policy_and_legacy_revision, record_cleanup_failure
    org = organizations[0]
    configure(org)
    version, legacy_id = policy_and_legacy_revision(org)
    if change == "policy": configure(org, 30)
    if change == "disable": configure(org, None)
    if change == "inactive": org.status = "suspended"
    if change == "newer_success": success(org, started_at=NOW+timedelta(seconds=1), finished_at=NOW+timedelta(seconds=2))
    before = deepcopy(org.settings)
    assert not record_cleanup_failure(org, now=NOW, policy_version=version,
                                      legacy_request_id=legacy_id, error_code="database_error")
    assert org.settings == before


def test_retry_backoff_is_bounded_and_disabled_policy_has_no_retry(db, organizations):
    from app.services.retention_status import (
        cleanup_status_response, policy_and_legacy_revision, read_cleanup_status, record_cleanup_failure,
    )
    org = organizations[0]
    configure(org)
    version, legacy_id = policy_and_legacy_revision(org)
    attempt = NOW
    for delay in (15, 30, 60, 120, 240, 360, 360):
        assert record_cleanup_failure(org, now=attempt, policy_version=version,
                                      legacy_request_id=legacy_id, error_code="unexpected_error")
        status = read_cleanup_status(org)
        assert status.next_retry_at == attempt+timedelta(minutes=delay)
        attempt = status.next_retry_at
    configure(org, None)
    public = cleanup_status_response(org, now=attempt)
    assert public.next_retry_at is None and public.next_cleanup_due_at is None


def test_saved_free_text_and_invalid_revision_never_leak_in_status(db, organizations):
    from app.services.retention_status import STATUS_SETTINGS_KEY, read_cleanup_status
    org = organizations[0]
    org.settings = {**org.settings, STATUS_SETTINGS_KEY: {
        "state": "failed", "error_code": "database_error", "message": "private imported comment or credential",
    }}
    assert "private" not in read_cleanup_status(org).model_dump_json()
    org.settings = {**org.settings, STATUS_SETTINGS_KEY: {
        "state": "failed", "last_attempt_policy_version": "private imported comment or credential",
    }}
    public = read_cleanup_status(org)
    assert public.error_code == "invalid_status"
    assert "private" not in public.model_dump_json()


def test_counts_and_timestamps_reject_invalid_status(db, organizations):
    from app.services.retention_status import RetentionCleanupStatus
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RetentionCleanupStatus(last_success_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError):
        RetentionCleanupStatus(counts={"analysis_results_expired": True})


def test_skipped_attempt_preserves_last_success_counts(db, organizations):
    from app.services.retention_cleanup import RetentionCleanupResult
    from app.services.retention_status import policy_and_legacy_revision, read_cleanup_status, record_cleanup_success
    org = organizations[0]
    configure(org)
    success(org)
    version, legacy_id = policy_and_legacy_revision(org)
    skipped = RetentionCleanupResult(organization_id=org.id, enabled=False, cutoff_at=None, policy_updated_at=NOW)
    record_cleanup_success(org, skipped, started_at=NOW+timedelta(days=1), finished_at=NOW+timedelta(days=1),
                           policy_version=version, legacy_request_id=legacy_id)
    status = read_cleanup_status(org)
    assert status.state == "skipped" and status.last_success_at == NOW
    assert status.counts.analysis_results_expired == 3


def test_daily_cleanup_finishing_late_does_not_skip_following_day(db, organizations):
    from app.services.retention_status import cleanup_due_at
    org = organizations[0]
    configure(org)
    start = NOW.replace(hour=3, minute=0, second=0, microsecond=0)
    success(org, started_at=start, finished_at=start+timedelta(minutes=7))
    tomorrow = start+timedelta(days=1)
    assert cleanup_due_at(org, now=start+timedelta(minutes=8)) == tomorrow
    assert cleanup_due_at(org, now=tomorrow) == tomorrow


def test_newly_enabled_policy_waits_for_next_daily_slot(db, organizations):
    from app.services.retention_status import cleanup_due_at
    org = organizations[0]
    configure(org)
    after_run = NOW.replace(hour=4, minute=0, second=0, microsecond=0)
    org.settings = {**org.settings, "data_retention": {
        **org.settings["data_retention"], "updated_at": after_run.isoformat(),
    }}
    assert cleanup_due_at(org, now=after_run) == after_run.replace(hour=3)+timedelta(days=1)


def test_success_in_previous_slot_crossing_daily_boundary_does_not_cover_new_slot(db, organizations):
    from app.services.retention_status import cleanup_due_at
    org = organizations[0]
    configure(org)
    start = NOW.replace(hour=2, minute=59, second=0, microsecond=0)
    finish = start+timedelta(minutes=3)
    success(org, started_at=start, finished_at=finish)
    assert cleanup_due_at(org, now=finish) == finish.replace(hour=3, minute=0)


def test_old_status_without_start_timestamp_uses_completion_day(db, organizations):
    from app.services.retention_status import STATUS_SETTINGS_KEY, cleanup_due_at
    org = organizations[0]
    configure(org)
    start = NOW.replace(hour=3, minute=0, second=0, microsecond=0)
    success(org, started_at=start, finished_at=start+timedelta(minutes=2))
    old_status = {**org.settings[STATUS_SETTINGS_KEY]}
    old_status.pop("last_success_started_at")
    org.settings = {**org.settings, STATUS_SETTINGS_KEY: old_status}
    tomorrow = start+timedelta(days=1)
    assert cleanup_due_at(org, now=tomorrow) == tomorrow


def test_retry_cannot_run_healthy_work_even_when_daily_cleanup_is_due(db, organizations):
    from app.services.retention_status import cleanup_due_at
    org = organizations[0]
    configure(org)
    assert cleanup_due_at(org, now=NOW+timedelta(days=1), mode="retry") is None
    success(org)
    assert cleanup_due_at(org, now=NOW+timedelta(days=2), mode="retry") is None


def test_policy_change_invalidates_old_retry_and_waits_next_daily_slot(db, organizations):
    from app.services.retention_status import cleanup_due_at, policy_and_legacy_revision, record_cleanup_failure
    org = organizations[0]
    configure(org)
    attempt = NOW.replace(hour=4, minute=0, second=0, microsecond=0)
    version, request_id = policy_and_legacy_revision(org)
    assert record_cleanup_failure(org, now=attempt, policy_version=version,
                                  legacy_request_id=request_id, error_code="unexpected_error")
    change = attempt+timedelta(minutes=1)
    org.settings = {**org.settings, "data_retention": {
        **org.settings["data_retention"], "retention_days": 30, "updated_at": change.isoformat(),
    }}
    assert cleanup_due_at(org, now=attempt+timedelta(minutes=15), mode="retry") is None
    assert cleanup_due_at(org, now=change) == attempt.replace(hour=3)+timedelta(days=1)
