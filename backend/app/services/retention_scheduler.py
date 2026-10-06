"""Daily retention cleanup with targeted retries and startup recovery.

Every process may run the schedule. A PostgreSQL organization row lock claims each
attempt and remains held through cleanup's atomic commit. Policy changes and
result writers use the same lock, so process restarts and multiple instances do
not require expiring distributed locks. Disabled policies never run cleanup.
"""
import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from ..models import Organization, SessionLocal
from .data_retention import read_retention_policy
from .retention_cleanup import RetentionScopeConflict, cleanup_organization_data
from .retention_status import (
    DAILY_CLEANUP_HOUR_UTC, DAILY_CLEANUP_MINUTE_UTC, ErrorCode, cleanup_due_at, policy_and_legacy_revision,
    record_cleanup_failure,
)

logger = logging.getLogger(__name__)
PAGE_SIZE = 100
JOB_ID = "organization_data_retention"
STARTUP_JOB_ID = f"{JOB_ID}_startup"
RETRY_JOB_PREFIX = f"{JOB_ID}_retry_"
Outcome = Literal["succeeded", "failed", "skipped"]
AttemptMode = Literal["daily", "retry"]


@dataclass
class RetentionPollResult:
    candidates: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Retention scheduling requires a timezone-aware clock")
    return value.astimezone(timezone.utc)


def _record_failed_attempt(
    organization_id: int, *, session_factory, now: datetime,
    policy_version: str, legacy_request_id: str | None, error_code: ErrorCode,
    finished_at: datetime,
) -> None:
    """Record only this revision's failure after rolling cleanup back.

    The status helper also fences out attempts superseded by another process.
    Exception strings, SQL parameters and provider payloads are never persisted.
    Failure reporting itself must not prevent processing another organization.
    """
    try:
        with session_factory() as db:
            organization = db.query(Organization).populate_existing().filter(
                Organization.id == organization_id, Organization.status == "active",
            ).with_for_update().one_or_none()
            if organization is None:
                db.rollback()
                return
            recorded = record_cleanup_failure(
                organization, now=now, policy_version=policy_version,
                legacy_request_id=legacy_request_id, error_code=error_code,
                finished_at=finished_at,
            )
            if recorded:
                db.commit()
            else:
                db.rollback()
    except Exception:
        logger.error("Retention failure status unavailable org=%s code=retention_status_failed", organization_id)


def process_organization_cleanup(
    organization_id: int, *, session_factory=SessionLocal,
    clock: Callable[[], datetime] = utc_now,
    stop_event: threading.Event | None = None,
    mode: AttemptMode = "daily",
) -> Outcome:
    """Recheck current eligibility under a nonblocking organization claim.

    A separate session for each organization keeps one failure isolated. The
    claim is held by that very session through cleanup, including its commit;
    releasing a lock before handing work to another session would be unsafe.
    """
    attempt_at = _utc(clock())
    if stop_event is not None and stop_event.is_set():
        return "skipped"
    revision = None
    try:
        with session_factory() as db:
            if stop_event is not None and stop_event.is_set():
                db.rollback()
                return "skipped"
            organization = db.query(Organization).populate_existing().filter(
                Organization.id == organization_id, Organization.status == "active",
            ).with_for_update(skip_locked=True).one_or_none()
            if organization is None:
                db.rollback()
                return "skipped"
            if stop_event is not None and stop_event.is_set():
                db.rollback()
                return "skipped"
            if read_retention_policy(organization).retention_days is None:
                db.rollback()
                return "skipped"
            due_at = cleanup_due_at(organization, now=attempt_at, mode=mode)
            if due_at is None or due_at > attempt_at:
                db.rollback()
                return "skipped"
            revision = policy_and_legacy_revision(organization)
            cleanup_organization_data(
                db, organization_id, now=attempt_at, completion_clock=clock,
            )
            return "succeeded"
    except Exception as error:
        # Do not log the exception: DB exceptions may include settings or data.
        error_code: ErrorCode = (
            "dependency_conflict" if isinstance(error, RetentionScopeConflict) else
            "cache_unavailable" if isinstance(error, RedisError) else
            "database_error" if isinstance(error, SQLAlchemyError) else
            "invalid_policy" if revision is None and isinstance(error, (ValueError, TypeError)) else
            "unexpected_error"
        )
        logger.error("Retention attempt failed org=%s code=%s", organization_id, error_code)
        if revision is not None:
            _record_failed_attempt(
                organization_id, session_factory=session_factory, now=attempt_at,
                policy_version=revision[0], legacy_request_id=revision[1],
                error_code=error_code, finished_at=_utc(clock()),
            )
        return "failed"


def process_due_retention_cleanups(
    *, session_factory=SessionLocal, clock: Callable[[], datetime] = utc_now,
    stop_event: threading.Event | None = None,
    on_outcome: Callable[[int, Outcome], None] | None = None,
) -> RetentionPollResult:
    """Page over active candidate IDs only; load settings only after claiming.

    The JSON filter is just a candidate hint. It neither casts arbitrary saved
    values nor authorizes cleanup: strict policy validation happens under lock.
    A bounded page prevents loading every organization's integration settings.
    """
    _utc(clock())
    result = RetentionPollResult()
    cursor = 0
    while True:
        if stop_event is not None and stop_event.is_set():
            return result
        try:
            with session_factory() as db:
                ids = [row[0] for row in db.query(Organization.id).filter(
                    Organization.id > cursor,
                    Organization.status == "active",
                    Organization.settings["data_retention"]["retention_days"].as_string().isnot(None),
                ).order_by(Organization.id).limit(PAGE_SIZE).all()]
        except Exception:
            logger.error("Retention poll unavailable code=retention_poll_failed")
            return result
        if not ids:
            return result
        cursor = ids[-1]
        for organization_id in ids:
            if stop_event is not None and stop_event.is_set():
                return result
            result.candidates += 1
            outcome = process_organization_cleanup(
                organization_id, session_factory=session_factory, clock=clock,
                stop_event=stop_event, mode="daily",
            )
            setattr(result, outcome, getattr(result, outcome) + 1)
            if on_outcome is not None:
                try:
                    on_outcome(organization_id, outcome)
                except Exception:
                    logger.error("Retention outcome scheduling unavailable org=%s code=retention_retry_failed",
                                 organization_id)


async def run_due_retention_cleanups(
    *, session_factory=SessionLocal, clock: Callable[[], datetime] = utc_now,
) -> RetentionPollResult:
    """Keep synchronous PostgreSQL and cache operations off the event loop."""
    return await asyncio.to_thread(
        process_due_retention_cleanups, session_factory=session_factory, clock=clock,
    )


class RetentionScheduler:
    """Own a synchronous worker that can drain safely before DB shutdown.

    Cancelling an asyncio wrapper does not stop its to_thread worker. A
    BackgroundScheduler uses an executor whose shutdown(wait=True) really joins
    the running poll. The stop flag prevents claiming another organization while
    the current organization finishes its atomic transaction.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        self._started = False
        self._has_started = False
        self._stop_event = threading.Event()
        self._shutdown_task: asyncio.Task | None = None

    def _run_poll(self) -> RetentionPollResult:
        """One daily sweep; failed attempts arrange only their own retry."""
        return process_due_retention_cleanups(
            stop_event=self._stop_event, on_outcome=self._after_daily_attempt,
        )

    def _after_daily_attempt(self, organization_id: int, outcome: Outcome) -> None:
        if outcome == "failed":
            self._schedule_retry(organization_id)
        elif outcome == "succeeded":
            self._remove_retry(organization_id)

    def _remove_retry(self, organization_id: int) -> None:
        try:
            self.scheduler.remove_job(f"{RETRY_JOB_PREFIX}{organization_id}")
        except JobLookupError:
            pass

    def _schedule_retry(self, organization_id: int) -> None:
        """Read persisted, current-policy failure state before queuing a retry.

        The eventual callback rechecks everything under the organization lock.
        This read only describes a candidate; it never authorizes deletion.
        """
        if self._stop_event.is_set():
            return
        try:
            now = _utc(utc_now())
            with SessionLocal() as db:
                organization = db.query(Organization).filter(
                    Organization.id == organization_id, Organization.status == "active",
                ).one_or_none()
                due_at = cleanup_due_at(organization, now=now, mode="retry") if organization else None
            if due_at is None:
                self._remove_retry(organization_id)
                return
            if self._stop_event.is_set():
                return
            self.scheduler.add_job(
                self._run_retry, trigger=DateTrigger(run_date=max(due_at, now), timezone=timezone.utc),
                args=[organization_id], id=f"{RETRY_JOB_PREFIX}{organization_id}",
                replace_existing=True, max_instances=1, misfire_grace_time=None,
            )
        except Exception:
            logger.error("Retention retry scheduling unavailable org=%s code=retention_retry_failed", organization_id)

    def _run_retry(self, organization_id: int) -> Outcome:
        """Retry only this failed organization, without a global periodic poll."""
        outcome = process_organization_cleanup(
            organization_id, stop_event=self._stop_event, mode="retry",
        )
        if outcome == "failed":
            self._schedule_retry(organization_id)
        return outcome

    def _restore_retries(self) -> None:
        """Recover retry timers after a restart, ignoring healthy policies."""
        cursor = 0
        while not self._stop_event.is_set():
            try:
                with SessionLocal() as db:
                    ids = [row[0] for row in db.query(Organization.id).filter(
                        Organization.id > cursor,
                        Organization.status == "active",
                        Organization.settings["data_retention"]["retention_days"].as_string().isnot(None),
                        Organization.settings["data_retention_cleanup"]["state"].as_string() == "failed",
                    ).order_by(Organization.id).limit(PAGE_SIZE).all()]
            except Exception:
                logger.error("Retention retry recovery unavailable code=retention_retry_recovery_failed")
                return
            if not ids:
                return
            cursor = ids[-1]
            for organization_id in ids:
                if self._stop_event.is_set():
                    return
                self._schedule_retry(organization_id)

    def _run_startup(self) -> RetentionPollResult:
        """One recovery sweep for missed daily work, then restore retry timers."""
        result = self._run_poll()
        self._restore_retries()
        return result

    def start(self) -> None:
        if self._started:
            return
        if self._shutdown_task is not None and not self._shutdown_task.done():
            raise RuntimeError("Wait for retention scheduler shutdown before restarting")
        # BackgroundScheduler's executor is closed after shutdown; a restart
        # needs a fresh scheduler and executor rather than reusing that pool.
        if self._has_started:
            self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        self._stop_event.clear()
        self.scheduler.add_job(
            self._run_poll,
            trigger=CronTrigger(hour=DAILY_CLEANUP_HOUR_UTC, minute=DAILY_CLEANUP_MINUTE_UTC,
                                timezone=timezone.utc),
            id=JOB_ID, replace_existing=True, coalesce=True, max_instances=1,
            misfire_grace_time=None,
        )
        self.scheduler.add_job(
            self._run_startup, trigger=DateTrigger(run_date=utc_now(), timezone=timezone.utc),
            id=STARTUP_JOB_ID, replace_existing=True, max_instances=1, misfire_grace_time=None,
        )
        self.scheduler.start()
        self._started = True
        self._has_started = True
        logger.info("Retention scheduler started; daily_time_utc=%02d:%02d",
                    DAILY_CLEANUP_HOUR_UTC, DAILY_CLEANUP_MINUTE_UTC)

    async def stop(self) -> None:
        if self._shutdown_task is not None and not self._shutdown_task.done():
            await asyncio.shield(self._shutdown_task)
            return
        if not self._started:
            return
        self._started = False
        self._stop_event.set()
        self._shutdown_task = asyncio.create_task(asyncio.to_thread(self.scheduler.shutdown, wait=True))
        # Joining the background executor off-loop leaves other shutdown work
        # responsive while guaranteeing the current cleanup has finished.
        await asyncio.shield(self._shutdown_task)
        logger.info("Retention scheduler stopped")


retention_scheduler = RetentionScheduler()
