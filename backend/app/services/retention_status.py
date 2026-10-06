"""Sanitized, organization-scoped cleanup outcomes and daily/retry eligibility."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

STATUS_SETTINGS_KEY = "data_retention_cleanup"
DAILY_CLEANUP_HOUR_UTC = 3
DAILY_CLEANUP_MINUTE_UTC = 0
RETRY_INTERVAL_MINUTES = 15
CLEANUP_INTERVAL = timedelta(days=1)
MAX_RETRY_INTERVAL = timedelta(hours=6)
Count = Annotated[StrictInt, Field(ge=0)]
ErrorCode = Literal[
    "cache_unavailable", "dependency_conflict", "database_error",
    "invalid_policy", "unexpected_error", "invalid_status",
]
ERROR_MESSAGES = {
    "cache_unavailable": "Cleanup could not clear cached results. Database changes were rolled back.",
    "dependency_conflict": "Linked records have uncertain ownership. Database changes were rolled back.",
    "database_error": "Cleanup could not complete its database transaction. No success was recorded.",
    "invalid_policy": "The saved retention policy could not be validated. No cleanup was performed.",
    "unexpected_error": "Cleanup did not complete. No success was recorded.",
    "invalid_status": "The previous cleanup status could not be read. Cleanup will be checked again.",
}


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Cleanup status requires a timezone-aware clock")
    return value.astimezone(timezone.utc)


class CleanupCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_results_expired: Count = 0
    legacy_analysis_results_cleared: Count = 0
    survey_responses_deleted: Count = 0
    survey_links_cleared: Count = 0
    survey_period_links_cleared: Count = 0
    mappings_deleted: Count = 0
    notifications_deleted: Count = 0
    digest_links_cleared: Count = 0
    analyses_unverifiable: Count = 0
    analyses_deferred: Count = 0
    legacy_analyses_skipped: Count = 0
    legacy_analyses_deferred: Count = 0
    surveys_unverifiable: Count = 0


class RetentionCleanupStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["never", "succeeded", "failed", "skipped"] = "never"
    last_attempt_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_success_at: datetime | None = None
    last_success_started_at: datetime | None = None
    next_retry_at: datetime | None = None
    next_cleanup_due_at: datetime | None = None
    consecutive_failures: Count = 0
    last_attempt_policy_version: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    last_success_policy_version: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    last_attempt_legacy_request_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    last_success_legacy_request_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    error_code: ErrorCode | None = None
    message: str | None = None
    counts: CleanupCounts = Field(default_factory=CleanupCounts)

    @field_validator("last_attempt_at", "last_finished_at", "last_success_at", "last_success_started_at", "next_retry_at", "next_cleanup_due_at")
    @classmethod
    def aware_dates(cls, value):
        return _utc(value) if value is not None else None


def read_cleanup_status(organization) -> RetentionCleanupStatus:
    settings = organization.settings
    stored = settings.get(STATUS_SETTINGS_KEY) if isinstance(settings, dict) else None
    if stored is None:
        return RetentionCleanupStatus()
    try:
        status = RetentionCleanupStatus.model_validate(stored)
    except (ValueError, TypeError):
        return RetentionCleanupStatus(state="failed", error_code="invalid_status", message=ERROR_MESSAGES["invalid_status"])
    # Display only fixed application messages, never arbitrary saved error text.
    return status.model_copy(update={"message": ERROR_MESSAGES.get(status.error_code)})


def policy_and_legacy_revision(organization) -> tuple[str, str | None]:
    from .data_retention import retention_policy_version
    from .retention_legacy import read_legacy_authorization

    authorization = read_legacy_authorization(organization)
    pending_id = authorization.request_id if authorization and authorization.state == "pending" else None
    return retention_policy_version(organization), pending_id


def daily_cleanup_slot(now: datetime) -> datetime:
    """Latest fixed UTC daily slot, independent of a prior run's duration."""
    now = _utc(now)
    slot = now.replace(hour=DAILY_CLEANUP_HOUR_UTC, minute=DAILY_CLEANUP_MINUTE_UTC, second=0, microsecond=0)
    return slot if slot <= now else slot - CLEANUP_INTERVAL


def next_daily_cleanup_at(now: datetime) -> datetime:
    return daily_cleanup_slot(now) + CLEANUP_INTERVAL


def cleanup_due_at(organization, *, now: datetime,
                   mode: Literal["daily", "retry"] = "daily") -> datetime | None:
    from .data_retention import read_retention_policy

    now = _utc(now)
    if organization.status != "active" or read_retention_policy(organization).retention_days is None:
        return None
    status = read_cleanup_status(organization)
    version, pending_id = policy_and_legacy_revision(organization)
    same_attempt = (
        status.last_attempt_policy_version == version
        and status.last_attempt_legacy_request_id == pending_id
    )
    # A retry timer cannot process healthy work, a changed policy or a newly
    # approved batch; those settings are picked up by the next daily slot.
    if mode == "retry":
        return (status.next_retry_at or now) if status.state == "failed" and same_attempt else None
    if mode != "daily":
        raise ValueError("Unknown retention scheduling mode")
    slot = daily_cleanup_slot(now)
    from .data_retention import read_retention_policy
    from .retention_legacy import read_legacy_authorization
    policy = read_retention_policy(organization)
    authorization = read_legacy_authorization(organization)
    changed_at = [value for value in (
        policy.updated_at,
        authorization.approved_at if authorization and authorization.state == "pending" else None,
    ) if value is not None]
    if any(_utc(value) > slot for value in changed_at):
        return next_daily_cleanup_at(now)
    if status.state == "failed" and same_attempt:
        return status.next_retry_at or slot
    # Existing status from the previous polling draft has only completion time.
    # New status records the successful attempt's start so a run crossing 03:00
    # cannot count as having processed a slot that began after its cutoff.
    successful_start = status.last_success_started_at or status.last_success_at
    if successful_start is not None and successful_start >= slot:
        return next_daily_cleanup_at(now)
    return slot


def cleanup_status_response(organization, *, now: datetime | None = None) -> RetentionCleanupStatus:
    now = _utc(now or datetime.now(timezone.utc))
    status = read_cleanup_status(organization)
    daily_due = cleanup_due_at(organization, now=now)
    retry_due = cleanup_due_at(organization, now=now, mode="retry")
    due = min(value for value in (daily_due, retry_due) if value is not None) if daily_due is not None or retry_due is not None else None
    version, pending_id = policy_and_legacy_revision(organization)
    current_failure = status.state == "failed" and (
        status.last_attempt_policy_version == version and status.last_attempt_legacy_request_id == pending_id
    )
    return status.model_copy(update={
        # Display the actual daily slot or targeted retry eligibility. Past
        # slots indicate startup recovery rather than another periodic poll.
        "next_cleanup_due_at": due,
        "next_retry_at": status.next_retry_at if due is not None and current_failure else None,
    })


def _save_status(organization, status: RetentionCleanupStatus):
    validated = RetentionCleanupStatus.model_validate(status.model_dump())
    organization.settings = {
        **(organization.settings or {}),
        STATUS_SETTINGS_KEY: validated.model_dump(mode="json", exclude={"next_cleanup_due_at"}),
    }


def record_cleanup_success(organization, result, *, started_at: datetime, finished_at: datetime,
                           policy_version: str, legacy_request_id: str | None):
    """Stage outcomes in the SAME transaction as cleanup; caller commits."""
    started_at = _utc(started_at)
    finished_at = max(_utc(finished_at), started_at)
    previous = read_cleanup_status(organization)
    if not result.enabled:
        _save_status(organization, previous.model_copy(update={
            "state": "skipped", "last_attempt_at": started_at, "last_finished_at": finished_at,
            "last_attempt_policy_version": policy_version, "last_attempt_legacy_request_id": legacy_request_id,
            "next_retry_at": None, "consecutive_failures": 0, "error_code": None, "message": None,
        }))
        return
    counts = CleanupCounts(**{key: getattr(result, key) for key in CleanupCounts.model_fields})
    _save_status(organization, RetentionCleanupStatus(
        state="succeeded", last_attempt_at=started_at, last_finished_at=finished_at,
        last_success_at=finished_at, last_success_started_at=started_at, last_attempt_policy_version=policy_version,
        last_success_policy_version=policy_version, last_attempt_legacy_request_id=legacy_request_id,
        last_success_legacy_request_id=legacy_request_id, counts=counts,
    ))


def record_cleanup_failure(organization, *, now: datetime, policy_version: str,
                           legacy_request_id: str | None, error_code: ErrorCode,
                           finished_at: datetime | None = None) -> bool:
    """Stage sanitized failure after rollback under a fresh organization lock."""
    from .data_retention import read_retention_policy

    now = _utc(now)
    finished_at = max(_utc(finished_at or now), now)
    if organization.status != "active" or read_retention_policy(organization).retention_days is None:
        return False
    if policy_and_legacy_revision(organization) != (policy_version, legacy_request_id):
        return False
    previous = read_cleanup_status(organization)
    if previous.last_attempt_at is not None and previous.last_attempt_at >= now:
        return False
    same_revision = (
        previous.last_attempt_policy_version == policy_version
        and previous.last_attempt_legacy_request_id == legacy_request_id
    )
    failures = previous.consecutive_failures + 1 if same_revision else 1
    delay = min(timedelta(minutes=RETRY_INTERVAL_MINUTES * 2 ** min(failures - 1, 5)), MAX_RETRY_INTERVAL)
    _save_status(organization, previous.model_copy(update={
        "state": "failed", "last_attempt_at": now, "last_finished_at": finished_at,
        "last_attempt_policy_version": policy_version, "last_attempt_legacy_request_id": legacy_request_id,
        "consecutive_failures": failures, "next_retry_at": finished_at + delay,
        "error_code": error_code, "message": ERROR_MESSAGES[error_code],
    }))
    return True
