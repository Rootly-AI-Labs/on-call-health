"""Scheduler checks; destructive cases use guarded disposable PostgreSQL only.

Database fixtures enforce ``retention_test`` in the database name and roll back
each case. All Redis/provider calls are replaced. Pure scheduler checks require
neither a database nor the application's credentials.
"""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from .test_retention_preview import (
    NOW as FIXTURE_NOW, OLD, analysis_factory, coverage, db, db_connection, organizations,
    retention_engine, survey_factory, users,
)
from .test_retention_cleanup import enabled_policy, isolate_retention_cache, snapshot

# Daily cases use a clock after the fixed 03:00 UTC boundary. Source fixtures
# retain their own generation times; this does not change what is expired.
NOW = FIXTURE_NOW.replace(hour=4, minute=0)
NEXT_DAILY = (NOW + timedelta(days=1)).replace(hour=3, minute=0)


def policy_org(organization_id=7, *, days=90):
    return SimpleNamespace(id=organization_id, status="active", settings={
        "data_retention": {
            "retention_days": days, "age_basis": "analysis_generation",
            "updated_at": (NOW - timedelta(days=1)).isoformat(), "updated_by_user_id": None,
        },
    })


class FakeQuery:
    def __init__(self, session):
        self.session = session

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            if name == "with_for_update":
                self.session.locks.append(kwargs)
            return self
        return chain

    def one_or_none(self):
        return self.session.organization

    def all(self):
        return self.session.rows


class FakeSession:
    def __init__(self, organization=None, rows=()):
        self.organization = organization
        self.rows = rows
        self.locks = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def query(self, *args):
        return FakeQuery(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if args[0] is not None:
            self.rollback()
        self.closed = True


@pytest.fixture
def scheduler(monkeypatch):
    from app.services import retention_scheduler
    # In-memory lifecycle tests must never restore retry timers from the app DB.
    monkeypatch.setattr(retention_scheduler, "SessionLocal", lambda: FakeSession())
    return retention_scheduler


@pytest.fixture
def fixture_session_factory(db):
    @contextmanager
    def factory():
        # The shared fixture owns its rollback-protected connection lifecycle.
        yield db
    return factory


@pytest.mark.parametrize("organization", [None, policy_org(days=None)])
def test_unavailable_or_disabled_org_never_calls_cleanup(scheduler, monkeypatch, organization):
    session = FakeSession(organization)
    monkeypatch.setattr(scheduler, "cleanup_organization_data", lambda *args, **kwargs: pytest.fail("Cleanup ran"))
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: NOW) == "skipped"
    assert session.locks == [{"skip_locked": True}]
    assert session.rollbacks == 1
    assert session.commits == 0


def test_claim_lock_is_held_by_cleanup_session(scheduler, monkeypatch):
    session = FakeSession(policy_org())
    monkeypatch.setattr(scheduler, "cleanup_due_at", lambda *args, **kwargs: NOW)
    monkeypatch.setattr(scheduler, "policy_and_legacy_revision", lambda org: ("a" * 64, None))
    calls = []

    def cleanup(given_session, organization_id, *, now, completion_clock):
        assert given_session is session
        assert not session.closed
        assert session.locks == [{"skip_locked": True}]
        assert session.rollbacks == 0
        calls.append((organization_id, now, completion_clock()))
        session.commit()

    monkeypatch.setattr(scheduler, "cleanup_organization_data", cleanup)
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: NOW) == "succeeded"
    assert calls == [(7, NOW, NOW)]
    assert session.closed


@pytest.mark.parametrize("due_at", [None, NOW + timedelta(microseconds=1)])
def test_not_yet_due_is_rechecked_after_claim(scheduler, monkeypatch, due_at):
    session = FakeSession(policy_org())
    monkeypatch.setattr(scheduler, "cleanup_due_at", lambda *args, **kwargs: due_at)
    monkeypatch.setattr(scheduler, "cleanup_organization_data", lambda *args, **kwargs: pytest.fail("Cleanup ran"))
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: NOW) == "skipped"
    assert session.rollbacks == 1


@pytest.mark.parametrize("bad", [0, -1, True, "90", 3651])
def test_malformed_policy_cannot_authorize_cleanup(scheduler, monkeypatch, bad):
    session = FakeSession(policy_org(days=bad))
    monkeypatch.setattr(scheduler, "cleanup_organization_data", lambda *args, **kwargs: pytest.fail("Cleanup ran"))
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: NOW) == "failed"
    assert session.closed
    assert session.commits == 0


def test_failure_rolls_back_before_separate_status_transaction(scheduler, monkeypatch, caplog):
    attempt = FakeSession(policy_org())
    report = FakeSession(policy_org())
    sessions = iter([attempt, report])
    monkeypatch.setattr(scheduler, "cleanup_due_at", lambda *args, **kwargs: NOW)
    monkeypatch.setattr(scheduler, "policy_and_legacy_revision", lambda org: ("a" * 64, None))

    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE SQL PAYLOAD TOKEN")

    def record(org, **kwargs):
        assert attempt.closed and attempt.rollbacks == 1
        assert kwargs == {
            "now": NOW, "policy_version": "a" * 64, "legacy_request_id": None,
            "error_code": "unexpected_error", "finished_at": NOW,
        }
        return True

    monkeypatch.setattr(scheduler, "cleanup_organization_data", fail)
    monkeypatch.setattr(scheduler, "record_cleanup_failure", record)
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: next(sessions), clock=lambda: NOW) == "failed"
    assert report.locks == [{}]
    assert report.commits == 1
    assert "PRIVATE" not in caplog.text and "TOKEN" not in caplog.text


@pytest.mark.parametrize("organization,recorded", [(None, False), (policy_org(), False)])
def test_failure_reporting_cannot_overwrite_superseding_attempt(scheduler, monkeypatch, organization, recorded):
    session = FakeSession(organization)
    monkeypatch.setattr(scheduler, "record_cleanup_failure", lambda *args, **kwargs: recorded)
    scheduler._record_failed_attempt(7, session_factory=lambda: session, now=NOW,
                                     policy_version="a" * 64, legacy_request_id=None,
                                     error_code="unexpected_error", finished_at=NOW)
    assert session.commits == 0
    assert session.rollbacks == 1


def test_failure_status_error_is_sanitized_and_contained(scheduler, monkeypatch, caplog):
    def broken_factory():
        raise RuntimeError("SECRET CONNECTION URL")
    scheduler._record_failed_attempt(7, session_factory=broken_factory, now=NOW,
                                     policy_version="a" * 64, legacy_request_id=None,
                                     error_code="unexpected_error", finished_at=NOW)
    assert "retention_status_failed" in caplog.text
    assert "SECRET" not in caplog.text


def test_poll_pages_ids_and_isolates_org_failure(scheduler, monkeypatch):
    sessions = iter([FakeSession(rows=[(1,), (2,)]), FakeSession(rows=[(3,)]), FakeSession()])
    processed = []

    def process(organization_id, **kwargs):
        processed.append(organization_id)
        return "failed" if organization_id == 2 else "succeeded"

    monkeypatch.setattr(scheduler, "process_organization_cleanup", process)
    result = scheduler.process_due_retention_cleanups(session_factory=lambda: next(sessions), clock=lambda: NOW)
    assert processed == [1, 2, 3]
    assert (result.candidates, result.succeeded, result.failed, result.skipped) == (3, 2, 1, 0)


def test_poll_database_failure_returns_sanitized_summary(scheduler, caplog):
    def broken_factory():
        raise RuntimeError("SECRET DATABASE URL")
    result = scheduler.process_due_retention_cleanups(session_factory=broken_factory, clock=lambda: NOW)
    assert result.candidates == result.failed == 0
    assert "retention_poll_failed" in caplog.text
    assert "SECRET" not in caplog.text


def test_outcome_callback_failure_does_not_abort_other_organizations(scheduler, monkeypatch, caplog):
    sessions = iter([FakeSession(rows=[(1,), (2,)]), FakeSession()])
    processed = []

    def process(organization_id, **kwargs):
        processed.append(organization_id)
        return "succeeded"

    def report(*args):
        raise RuntimeError("SECRET TIMER PAYLOAD")

    monkeypatch.setattr(scheduler, "process_organization_cleanup", process)
    result = scheduler.process_due_retention_cleanups(
        session_factory=lambda: next(sessions), clock=lambda: NOW, on_outcome=report,
    )
    assert processed == [1, 2]
    assert result.succeeded == 2
    assert "retention_retry_failed" in caplog.text
    assert "SECRET" not in caplog.text


@pytest.mark.parametrize("entrypoint", ["process_due_retention_cleanups", "process_organization_cleanup"])
def test_naive_clock_is_rejected_before_database_access(scheduler, entrypoint):
    def forbidden_factory():
        pytest.fail("Opened database before clock validation")
    args = (7,) if entrypoint == "process_organization_cleanup" else ()
    with pytest.raises(ValueError, match="timezone-aware"):
        getattr(scheduler, entrypoint)(*args, session_factory=forbidden_factory,
                                      clock=lambda: datetime(2026, 10, 5))


def test_async_callback_runs_synchronous_work_in_another_thread(scheduler, monkeypatch):
    import threading
    current_thread = threading.get_ident()
    seen = []

    def work(**kwargs):
        seen.append(threading.get_ident())
        return scheduler.RetentionPollResult(candidates=1)

    monkeypatch.setattr(scheduler, "process_due_retention_cleanups", work)
    result = asyncio.run(scheduler.run_due_retention_cleanups())
    assert result.candidates == 1
    assert seen and seen[0] != current_thread


def test_lifecycle_registers_daily_utc_job_and_one_startup_recovery(scheduler, monkeypatch):
    class FakeScheduler:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.running = False
            self.jobs = []
            self.starts = self.stops = 0

        def add_job(self, callback, **kwargs):
            self.jobs.append((callback, kwargs))

        def start(self):
            self.starts += 1
            self.running = True

        def remove_job(self, job_id):
            raise scheduler.JobLookupError(job_id)

        def shutdown(self, **kwargs):
            assert kwargs == {"wait": True}
            self.stops += 1
            self.running = False

    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW)
    instance = scheduler.RetentionScheduler()
    asyncio.run(instance.stop())
    instance.start()
    instance.start()
    assert instance.scheduler.starts == 1
    callback, options = instance.scheduler.jobs[0]
    assert callback.__self__ is instance
    assert callback.__func__ is scheduler.RetentionScheduler._run_poll
    assert options["id"] == scheduler.JOB_ID
    assert options["max_instances"] == 1 and options["coalesce"] is True
    assert "next_run_time" not in options
    assert options["trigger"].get_next_fire_time(None, NOW) == NEXT_DAILY
    assert options["misfire_grace_time"] is None
    assert len(instance.scheduler.jobs) == 2
    startup_callback, startup_options = instance.scheduler.jobs[1]
    assert startup_callback.__func__ is scheduler.RetentionScheduler._run_startup
    assert startup_options["id"] == scheduler.STARTUP_JOB_ID
    assert startup_options["trigger"].run_date == NOW
    assert instance.scheduler.options["timezone"] is timezone.utc
    asyncio.run(instance.stop())
    asyncio.run(instance.stop())
    assert instance.scheduler.stops == 1


class QueuedScheduler:
    def __init__(self):
        self.jobs = {}
        self.removed = []

    def add_job(self, callback, **kwargs):
        if kwargs["id"] in self.jobs and not kwargs.get("replace_existing", False):
            from apscheduler.jobstores.base import ConflictingIdError
            raise ConflictingIdError(kwargs["id"])
        self.jobs[kwargs["id"]] = (callback, kwargs)

    def remove_job(self, job_id):
        self.removed.append(job_id)
        if self.jobs.pop(job_id, None) is None:
            from apscheduler.jobstores.base import JobLookupError
            raise JobLookupError(job_id)


def failed_org():
    from app.services.retention_status import policy_and_legacy_revision, record_cleanup_failure
    organization = policy_org()
    version, legacy_id = policy_and_legacy_revision(organization)
    assert record_cleanup_failure(
        organization, now=NOW, finished_at=NOW, policy_version=version,
        legacy_request_id=legacy_id, error_code="cache_unavailable",
    )
    return organization


def test_failed_organization_gets_targeted_future_date_trigger(scheduler, monkeypatch):
    organization = failed_org()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW)
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._schedule_retry(organization.id)
    callback, options = instance.scheduler.jobs[f"{scheduler.RETRY_JOB_PREFIX}{organization.id}"]
    assert callback.__func__ is scheduler.RetentionScheduler._run_retry
    assert options["args"] == [organization.id]
    assert options["trigger"].run_date == NOW + timedelta(minutes=15)
    assert options["replace_existing"] is True
    assert options["max_instances"] == 1
    assert options["misfire_grace_time"] is None


@pytest.mark.parametrize("organization", [None, policy_org(), policy_org(days=None)])
def test_healthy_new_disabled_or_missing_org_has_no_retry_timer(scheduler, monkeypatch, organization):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW)
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._schedule_retry(7)
    assert not instance.scheduler.jobs


def test_new_policy_does_not_reuse_old_failure_retry(scheduler, monkeypatch):
    organization = failed_org()
    organization.settings = {
        **organization.settings,
        "data_retention": {**organization.settings["data_retention"], "retention_days": 30},
    }
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW + timedelta(days=1))
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._schedule_retry(7)
    assert not instance.scheduler.jobs


def test_retry_callback_rechecks_failure_and_skipped_claims(scheduler, monkeypatch):
    instance = scheduler.RetentionScheduler()
    scheduled = []
    monkeypatch.setattr(instance, "_schedule_retry", lambda organization_id, **kwargs: scheduled.append((organization_id, kwargs)))
    seen = []
    outcomes = iter(["failed", "succeeded", "skipped"])

    def process(organization_id, **kwargs):
        seen.append((organization_id, kwargs))
        return next(outcomes)

    monkeypatch.setattr(scheduler, "process_organization_cleanup", process)
    assert instance._run_retry(7) == "failed"
    assert instance._run_retry(7) == "succeeded"
    assert instance._run_retry(7) == "skipped"
    assert scheduled == [(7, {}), (7, {"deferred": True})]
    assert all(organization_id == 7 and kwargs["mode"] == "retry" for organization_id, kwargs in seen)


def test_locked_retry_requeues_overdue_current_failure_with_future_floor(scheduler, monkeypatch):
    from copy import deepcopy

    organization = failed_org()
    before = deepcopy(organization.settings)
    due_at = NOW + timedelta(minutes=15)
    monkeypatch.setattr(scheduler, "utc_now", lambda: due_at)
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    real_process = scheduler.process_organization_cleanup
    monkeypatch.setattr(scheduler, "process_organization_cleanup", lambda organization_id, **kwargs: real_process(
        organization_id, session_factory=lambda: FakeSession(None), clock=lambda: due_at, **kwargs,
    ))
    assert instance._run_retry(7) == "skipped"
    callback, options = instance.scheduler.jobs[f"{scheduler.RETRY_JOB_PREFIX}7"]
    assert callback.__func__ is scheduler.RetentionScheduler._run_retry
    assert options["trigger"].run_date == due_at + timedelta(minutes=15)
    assert options["replace_existing"] is False
    assert organization.settings == before


@pytest.mark.parametrize("case", ["healthy", "disabled", "missing", "inactive", "changed_policy", "changed_legacy"])
def test_skipped_retry_does_not_requeue_ineligible_or_changed_revision(scheduler, monkeypatch, case):
    organization = failed_org()
    if case == "healthy": organization = policy_org()
    if case == "disabled":
        organization.settings = {**organization.settings, "data_retention": {
            **organization.settings["data_retention"], "retention_days": None,
        }}
    if case == "missing": organization = None
    if case == "inactive": organization.status = "suspended"
    if case == "changed_policy":
        organization.settings = {**organization.settings, "data_retention": {
            **organization.settings["data_retention"], "retention_days": 30,
        }}
    if case == "changed_legacy":
        from app.services.retention_legacy import (
            LegacyAnalysisEntry, LegacyCleanupAuthorization, save_legacy_authorization,
        )
        save_legacy_authorization(organization, LegacyCleanupAuthorization(
            state="pending", request_id="a" * 32, approved_at=NOW,
            approved_by_user_id=1, requested_count=1,
            entries=[LegacyAnalysisEntry(analysis_id=1, result_fingerprint="b" * 64)],
        ))
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW + timedelta(minutes=15))
    monkeypatch.setattr(scheduler, "process_organization_cleanup", lambda *args, **kwargs: "skipped")
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    assert instance._run_retry(7) == "skipped"
    assert not instance.scheduler.jobs


def test_skipped_retry_after_shutdown_does_not_open_session_or_queue(scheduler, monkeypatch):
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._stop_event.set()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: pytest.fail("Read failure state after stop"))
    assert instance._run_retry(7) == "skipped"
    assert not instance.scheduler.jobs


def test_deferred_retry_honors_later_persisted_backoff(scheduler, monkeypatch):
    organization = failed_org()
    later_due = NOW + timedelta(hours=6)
    organization.settings = {**organization.settings, "data_retention_cleanup": {
        **organization.settings["data_retention_cleanup"], "next_retry_at": later_due.isoformat(),
    }}
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW + timedelta(minutes=15))
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._schedule_retry(7, deferred=True)
    _, options = instance.scheduler.jobs[f"{scheduler.RETRY_JOB_PREFIX}7"]
    assert options["trigger"].run_date == later_due


def test_deferred_retry_delay_starts_after_metadata_read(scheduler, monkeypatch):
    organization = failed_org()
    clock = [NOW + timedelta(minutes=15)]

    class SlowSession(FakeSession):
        def __exit__(self, *args):
            clock[0] += timedelta(minutes=20)
            return super().__exit__(*args)

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: SlowSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: clock[0])
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    instance._schedule_retry(7, deferred=True)
    _, options = instance.scheduler.jobs[f"{scheduler.RETRY_JOB_PREFIX}7"]
    assert options["trigger"].run_date == clock[0] + timedelta(minutes=15)


@pytest.mark.parametrize("queued_delay", [20, 60])
def test_deferred_retry_never_overwrites_an_existing_timer(scheduler, monkeypatch, queued_delay):
    organization = failed_org()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: FakeSession(organization))
    monkeypatch.setattr(scheduler, "utc_now", lambda: NOW + timedelta(minutes=15))
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    job_id = f"{scheduler.RETRY_JOB_PREFIX}7"
    instance.scheduler.add_job(instance._run_retry, args=[7], id=job_id,
                               trigger=scheduler.DateTrigger(run_date=NOW + timedelta(minutes=queued_delay)),
                               replace_existing=True)
    existing = instance.scheduler.jobs[job_id]
    instance._schedule_retry(7, deferred=True)
    assert instance.scheduler.jobs[job_id] is existing


def test_healthy_due_daily_policy_cannot_be_claimed_by_stale_retry(scheduler, monkeypatch):
    session = FakeSession(policy_org())
    monkeypatch.setattr(scheduler, "cleanup_organization_data", lambda *args, **kwargs: pytest.fail("Stale retry deleted data"))
    assert scheduler.process_organization_cleanup(
        7, session_factory=lambda: session, clock=lambda: NOW, mode="retry",
    ) == "skipped"
    assert session.locks == [{"skip_locked": True}]


def test_retry_timer_restoration_only_queues_failed_candidates(scheduler, monkeypatch):
    sessions = iter([FakeSession(rows=[(7,), (8,)]), FakeSession()])
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: next(sessions))
    instance = scheduler.RetentionScheduler()
    restored = []
    monkeypatch.setattr(instance, "_schedule_retry", lambda organization_id: restored.append(organization_id))
    instance._restore_retries()
    assert restored == [7, 8]


def test_startup_recovers_missed_daily_work_then_restores_retry_timers(scheduler, monkeypatch):
    instance = scheduler.RetentionScheduler()
    events = []
    summary = scheduler.RetentionPollResult(succeeded=1)
    monkeypatch.setattr(instance, "_run_poll", lambda: events.append("daily") or summary)
    monkeypatch.setattr(instance, "_restore_retries", lambda: events.append("retries"))
    assert instance._run_startup() is summary
    assert events == ["daily", "retries"]


def test_shutdown_prevents_retry_registration_or_recovery(scheduler, monkeypatch):
    instance = scheduler.RetentionScheduler()
    instance._stop_event.set()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: pytest.fail("Opened retry database after stop"))
    instance._schedule_retry(7)
    instance._restore_retries()


def test_retry_registration_error_is_sanitized(scheduler, monkeypatch, caplog):
    def broken_factory():
        raise RuntimeError("PRIVATE DATABASE URL")

    monkeypatch.setattr(scheduler, "SessionLocal", broken_factory)
    instance = scheduler.RetentionScheduler()
    instance._schedule_retry(7)
    assert "retention_retry_failed" in caplog.text
    assert "PRIVATE" not in caplog.text


def test_retry_recovery_error_is_sanitized(scheduler, monkeypatch, caplog):
    def broken_factory():
        raise RuntimeError("PRIVATE DATABASE URL")

    monkeypatch.setattr(scheduler, "SessionLocal", broken_factory)
    instance = scheduler.RetentionScheduler()
    instance._restore_retries()
    assert "retention_retry_recovery_failed" in caplog.text
    assert "PRIVATE" not in caplog.text


def test_restart_waits_for_pending_shutdown_and_uses_fresh_executor(scheduler, monkeypatch):
    import threading
    entered = threading.Event()
    release = threading.Event()

    class PendingScheduler:
        def __init__(self, **kwargs):
            self.running = False
        def add_job(self, *args, **kwargs):
            pass
        def start(self):
            self.running = True
        def shutdown(self, **kwargs):
            assert kwargs == {"wait": True}
            entered.set()
            assert release.wait(timeout=5)

    monkeypatch.setattr(scheduler, "BackgroundScheduler", PendingScheduler)

    async def verify():
        instance = scheduler.RetentionScheduler()
        instance.start()
        first = instance.scheduler
        stopping = asyncio.create_task(instance.stop())
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            with pytest.raises(RuntimeError, match="shutdown"):
                instance.start()
            release.set()
            await stopping
            instance.start()
            assert instance.scheduler is not first
            assert instance.scheduler.running
        finally:
            release.set()
            await stopping
            await instance.stop()

    asyncio.run(verify())


def test_real_background_scheduler_starts_immediately_and_restarts_cleanly(scheduler, monkeypatch):
    import threading
    calls = []

    async def verify():
        invoked = threading.Event()

        def poll(**kwargs):
            calls.append(True)
            invoked.set()

        monkeypatch.setattr(scheduler, "process_due_retention_cleanups", poll)
        instance = scheduler.RetentionScheduler()
        try:
            instance.start()
            instance.start()
            assert await asyncio.to_thread(invoked.wait, 2)
            assert len(calls) == 1
            invoked.clear()
            await instance.stop()
            await instance.stop()
            instance.start()
            assert await asyncio.to_thread(invoked.wait, 2)
            assert len(calls) == 2
        finally:
            await instance.stop()
        assert not instance.scheduler.running

    asyncio.run(verify())


def test_stop_drains_current_org_and_never_claims_next_org(scheduler, monkeypatch):
    import threading
    current_entered = threading.Event()
    current_release = threading.Event()
    current_finished = threading.Event()
    claims = []
    real_poll = scheduler.process_due_retention_cleanups

    def factory():
        return FakeSession(rows=[(1,), (2,)])

    def cleanup(organization_id, *, stop_event, **kwargs):
        claims.append(organization_id)
        current_entered.set()
        assert current_release.wait(timeout=5)
        current_finished.set()
        return "succeeded"

    monkeypatch.setattr(scheduler, "process_organization_cleanup", cleanup)
    monkeypatch.setattr(scheduler, "process_due_retention_cleanups", lambda **kwargs: real_poll(
        session_factory=factory, **kwargs,
    ))

    async def verify():
        instance = scheduler.RetentionScheduler()
        instance.start()
        stopping = None
        try:
            assert await asyncio.to_thread(current_entered.wait, 2)
            stopping = asyncio.create_task(instance.stop())
            # The stop flag is set before executor shutdown is dispatched.
            await asyncio.sleep(0)
            assert instance._stop_event.is_set()
            assert not stopping.done()
            assert not current_finished.is_set()
            current_release.set()
            await asyncio.wait_for(stopping, timeout=3)
            assert current_finished.is_set()
            assert claims == [1]
            assert not instance.scheduler.running
        finally:
            current_release.set()
            if stopping is not None:
                await stopping
            await instance.stop()

    asyncio.run(verify())


def test_stop_flag_prevents_new_claim_before_opening_session(scheduler):
    import threading
    stop_event = threading.Event()
    stop_event.set()

    def forbidden_factory():
        pytest.fail("Claimed work after shutdown")

    assert scheduler.process_organization_cleanup(
        7, session_factory=forbidden_factory, clock=lambda: NOW, stop_event=stop_event,
    ) == "skipped"
    result = scheduler.process_due_retention_cleanups(
        session_factory=forbidden_factory, clock=lambda: NOW, stop_event=stop_event,
    )
    assert result.candidates == 0


def test_stop_flag_is_rechecked_after_claim(scheduler, monkeypatch):
    import threading
    stop_event = threading.Event()
    session = FakeSession(policy_org())

    class StopOnClaim(FakeQuery):
        def one_or_none(self):
            stop_event.set()
            return super().one_or_none()

    session.query = lambda *args: StopOnClaim(session)
    monkeypatch.setattr(scheduler, "cleanup_organization_data", lambda *args, **kwargs: pytest.fail("Cleanup after stop"))
    assert scheduler.process_organization_cleanup(
        7, session_factory=lambda: session, clock=lambda: NOW, stop_event=stop_event,
    ) == "skipped"
    assert session.rollbacks == 1


@pytest.mark.parametrize("kind,expected", [
    ("dependency", "dependency_conflict"),
    ("database", "database_error"),
    ("cache", "cache_unavailable"),
])
def test_failure_codes_classify_without_exception_payload(scheduler, monkeypatch, kind, expected):
    from redis.exceptions import ConnectionError
    from sqlalchemy.exc import SQLAlchemyError
    errors = {
        "dependency": scheduler.RetentionScopeConflict("SECRET"),
        "database": SQLAlchemyError("SECRET"),
        "cache": ConnectionError("SECRET"),
    }
    session = FakeSession(policy_org())
    monkeypatch.setattr(scheduler, "cleanup_due_at", lambda *args, **kwargs: NOW)
    monkeypatch.setattr(scheduler, "policy_and_legacy_revision", lambda org: ("a" * 64, None))
    recorded = []

    def fail(*args, **kwargs):
        raise errors[kind]

    monkeypatch.setattr(scheduler, "cleanup_organization_data", fail)
    monkeypatch.setattr(scheduler, "_record_failed_attempt", lambda *args, **kwargs: recorded.append(kwargs))
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: NOW) == "failed"
    assert recorded[0]["error_code"] == expected


def test_failure_retry_clock_is_sampled_after_rollback(scheduler, monkeypatch):
    session = FakeSession(policy_org())
    times = iter([NOW, NOW + timedelta(minutes=20)])
    monkeypatch.setattr(scheduler, "cleanup_due_at", lambda *args, **kwargs: NOW)
    monkeypatch.setattr(scheduler, "policy_and_legacy_revision", lambda org: ("a" * 64, None))
    recorded = []

    def fail(*args, **kwargs):
        raise RuntimeError("Test failure")

    monkeypatch.setattr(scheduler, "cleanup_organization_data", fail)
    monkeypatch.setattr(scheduler, "_record_failed_attempt", lambda *args, **kwargs: recorded.append(kwargs))
    assert scheduler.process_organization_cleanup(7, session_factory=lambda: session, clock=lambda: next(times)) == "failed"
    assert recorded[0]["now"] == NOW
    assert recorded[0]["finished_at"] == NOW + timedelta(minutes=20)


def test_first_run_records_counts_and_next_attempt_at_daily_slot(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory, survey_factory,
):
    from app.services.retention_status import cleanup_due_at, read_cleanup_status
    expired = analysis_factory(coverage(OLD))
    survey = survey_factory(OLD)
    survey_id = survey.id
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW) == "succeeded"
    db.refresh(expired)
    db.refresh(enabled_policy)
    assert expired.results is None
    assert db.query(type(survey)).filter_by(id=survey_id).first() is None
    status = read_cleanup_status(enabled_policy)
    assert status.state == "succeeded"
    assert status.last_success_at == NOW
    assert status.consecutive_failures == 0
    assert status.counts.analysis_results_expired == 1
    assert status.counts.survey_responses_deleted == 1
    assert cleanup_due_at(enabled_policy, now=NOW, mode="daily") == NEXT_DAILY
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NEXT_DAILY - timedelta(seconds=1)) == "skipped"
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NEXT_DAILY) == "succeeded"


def test_cleanup_finishing_after_boundary_does_not_skip_tomorrow(
    scheduler, fixture_session_factory, db, enabled_policy,
):
    from app.services.retention_status import cleanup_due_at, read_cleanup_status
    started_at = NOW.replace(hour=3)
    finished_at = started_at + timedelta(minutes=3)
    ticks = iter([started_at, finished_at])
    assert scheduler.process_organization_cleanup(
        enabled_policy.id, session_factory=fixture_session_factory, clock=lambda: next(ticks),
    ) == "succeeded"
    db.refresh(enabled_policy)
    status = read_cleanup_status(enabled_policy)
    assert status.last_success_at == finished_at
    assert status.last_success_started_at == started_at
    assert cleanup_due_at(enabled_policy, now=finished_at, mode="daily") == NEXT_DAILY
    assert scheduler.process_organization_cleanup(
        enabled_policy.id, session_factory=fixture_session_factory, clock=lambda: NEXT_DAILY,
    ) == "succeeded"


def test_restart_recovery_runs_only_once_in_same_daily_slot(
    scheduler, fixture_session_factory, enabled_policy,
):
    first = scheduler.process_due_retention_cleanups(session_factory=fixture_session_factory, clock=lambda: NOW)
    again = scheduler.process_due_retention_cleanups(
        session_factory=fixture_session_factory, clock=lambda: NOW + timedelta(minutes=1),
    )
    assert first.succeeded == 1
    assert again.succeeded == 0 and again.skipped == 1


def test_failed_cache_rolls_back_data_and_records_retry(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory, monkeypatch,
):
    from app.services import retention_cleanup
    from app.services.retention_status import cleanup_due_at, read_cleanup_status
    expired = analysis_factory(coverage(OLD))
    original = expired.results

    def fail(*args):
        raise RuntimeError("SECRET REDIS URL")

    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", fail)
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW) == "failed"
    db.refresh(expired)
    db.refresh(enabled_policy)
    assert expired.results == original
    status = read_cleanup_status(enabled_policy)
    assert status.state == "failed" and status.consecutive_failures == 1
    assert status.error_code == "unexpected_error"
    assert "SECRET" not in status.model_dump_json()
    assert cleanup_due_at(enabled_policy, now=NOW, mode="retry") == NOW + timedelta(minutes=15)
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW + timedelta(minutes=14), mode="retry") == "skipped"


def test_failure_retry_runs_only_due_failed_org_and_stops_after_success(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory, monkeypatch,
):
    from app.services import retention_cleanup
    from app.services.retention_status import read_cleanup_status
    expired = analysis_factory(coverage(OLD))
    calls = []

    def fail_once(*args):
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("Test cache failure")

    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", fail_once)
    assert scheduler.process_organization_cleanup(
        enabled_policy.id, session_factory=fixture_session_factory, clock=lambda: NOW,
    ) == "failed"
    due_at = NOW + timedelta(minutes=15)
    assert scheduler.process_organization_cleanup(
        enabled_policy.id, session_factory=fixture_session_factory, clock=lambda: due_at, mode="retry",
    ) == "succeeded"
    db.refresh(expired)
    db.refresh(enabled_policy)
    assert expired.results is None
    assert read_cleanup_status(enabled_policy).next_retry_at is None
    assert scheduler.process_organization_cleanup(
        enabled_policy.id, session_factory=fixture_session_factory,
        clock=lambda: NEXT_DAILY + timedelta(days=1), mode="retry",
    ) == "skipped"
    assert len(calls) == 2


def test_policy_change_after_success_waits_until_next_daily_slot(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory,
):
    analysis_factory(coverage(OLD))
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW) == "succeeded"
    enabled_policy.settings = {
        **enabled_policy.settings,
        "data_retention": {**enabled_policy.settings["data_retention"], "retention_days": 30,
                           "updated_at": (NOW + timedelta(minutes=1)).isoformat()},
    }
    db.commit()
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW + timedelta(minutes=2)) == "skipped"
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NEXT_DAILY) == "succeeded"


def test_actual_poll_ignores_disabled_and_inactive_orgs_without_writes(
    scheduler, fixture_session_factory, db, db_connection, organizations,
):
    organizations[1].status = "suspended"
    organizations[1].settings = policy_org().settings
    db.commit()
    before = snapshot(db_connection)
    result = scheduler.process_due_retention_cleanups(session_factory=fixture_session_factory, clock=lambda: NOW)
    assert result.candidates == result.succeeded == result.failed == 0
    assert snapshot(db_connection) == before


def test_cleanup_commit_failure_cannot_report_success(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory, monkeypatch,
):
    from app.services.retention_status import read_cleanup_status
    expired = analysis_factory(coverage(OLD))
    original_commit = db.commit
    commits = []

    def fail_first_commit():
        commits.append(True)
        if len(commits) == 1:
            raise RuntimeError("SECRET COMMIT PAYLOAD")
        return original_commit()

    monkeypatch.setattr(db, "commit", fail_first_commit)
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW) == "failed"
    db.refresh(expired)
    db.refresh(enabled_policy)
    assert expired.results is not None
    status = read_cleanup_status(enabled_policy)
    assert status.state == "failed"
    assert status.last_success_at is None
    assert status.consecutive_failures == 1


def test_pending_legacy_batch_waits_next_daily_slot_and_completion_does_not_loop(
    scheduler, fixture_session_factory, db, enabled_policy, analysis_factory, users,
):
    from uuid import uuid4
    from app.services.retention_legacy import (
        LegacyAnalysisEntry, LegacyCleanupAuthorization, fingerprint_analysis_result,
        read_legacy_authorization, save_legacy_authorization,
    )
    from app.services.retention_status import read_cleanup_status
    legacy = analysis_factory({"unknown_generation": True}, completed_at=None, results_generated_at=None)
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW) == "succeeded"
    save_legacy_authorization(enabled_policy, LegacyCleanupAuthorization(
        state="pending", request_id=uuid4().hex, approved_at=NOW + timedelta(minutes=1),
        approved_by_user_id=users[0].id, requested_count=1,
        entries=[LegacyAnalysisEntry(analysis_id=legacy.id,
                                    result_fingerprint=fingerprint_analysis_result(legacy))],
    ))
    db.commit()
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NOW + timedelta(minutes=2)) == "skipped"
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NEXT_DAILY) == "succeeded"
    db.refresh(legacy)
    db.refresh(enabled_policy)
    assert legacy.results is None
    assert read_legacy_authorization(enabled_policy).state == "completed"
    assert read_cleanup_status(enabled_policy).counts.legacy_analysis_results_cleared == 1
    assert scheduler.process_organization_cleanup(enabled_policy.id, session_factory=fixture_session_factory,
                                                 clock=lambda: NEXT_DAILY + timedelta(minutes=3)) == "skipped"


def test_real_poll_continues_after_an_org_failure_and_keeps_other_data_scoped(
    scheduler, fixture_session_factory, db, organizations, analysis_factory, monkeypatch,
):
    from app.services import retention_cleanup
    from app.services.retention_status import read_cleanup_status
    for organization in organizations:
        organization.settings = {**organization.settings, **policy_org().settings}
    db.commit()
    first = analysis_factory(coverage(OLD))
    second = analysis_factory(coverage(OLD), organization_index=1)

    def invalidate(session, organization_id, ids):
        if organization_id == organizations[0].id:
            raise RuntimeError("Test failure")

    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", invalidate)
    result = scheduler.process_due_retention_cleanups(session_factory=fixture_session_factory, clock=lambda: NOW)
    assert (result.candidates, result.failed, result.succeeded) == (2, 1, 1)
    db.refresh(first)
    db.refresh(second)
    db.refresh(organizations[0])
    db.refresh(organizations[1])
    assert first.results is not None
    assert second.results is None
    assert read_cleanup_status(organizations[0]).state == "failed"
    assert read_cleanup_status(organizations[1]).state == "succeeded"


def test_postgres_claim_prevents_daily_retry_overlap_and_restart_duplication(
    scheduler, retention_engine, monkeypatch,
):
    """Independent sessions need committed fixtures, isolated in the test DB.

    This temporary org is created only after the retention_engine name guard,
    contains no users or provider credentials, and is removed in finally.
    """
    import threading
    from uuid import uuid4
    from sqlalchemy import delete, insert
    from sqlalchemy.orm import sessionmaker
    from app.models import Organization
    from app.services import retention_cleanup
    from app.services.retention_status import policy_and_legacy_revision, read_cleanup_status, record_cleanup_failure

    suffix = uuid4().hex
    with retention_engine.begin() as connection:
        organization_id = connection.execute(insert(Organization).values(
            name="Retention Scheduler Concurrency Test", domain=f"scheduler-{suffix}.invalid",
            slug=f"scheduler-{suffix}", status="active", settings=policy_org().settings,
        ).returning(Organization.id)).scalar_one()
    factory = sessionmaker(bind=retention_engine)
    with factory() as session:
        organization = session.get(Organization, organization_id)
        version, legacy_id = policy_and_legacy_revision(organization)
        assert record_cleanup_failure(
            organization, now=NOW, finished_at=NOW, policy_version=version,
            legacy_request_id=legacy_id, error_code="cache_unavailable",
        )
        session.commit()
    due_at = NOW + timedelta(minutes=15)
    reached_cleanup = threading.Event()
    release_cleanup = threading.Event()
    outcomes = []

    def gated_cache(*args):
        reached_cleanup.set()
        if not release_cleanup.wait(timeout=10):
            raise RuntimeError("Test cleanup gate timed out")

    monkeypatch.setattr(retention_cleanup, "_invalidate_retention_caches", gated_cache)
    worker = threading.Thread(target=lambda: outcomes.append(scheduler.process_organization_cleanup(
        organization_id, session_factory=factory, clock=lambda: due_at, mode="retry",
    )))
    try:
        worker.start()
        assert reached_cleanup.wait(timeout=5)
        assert scheduler.process_organization_cleanup(
            organization_id, session_factory=factory, clock=lambda: due_at + timedelta(seconds=1), mode="daily",
        ) == "skipped"
        release_cleanup.set()
        worker.join(timeout=10)
        assert not worker.is_alive()
        assert outcomes == ["succeeded"]
        assert scheduler.process_organization_cleanup(
            organization_id, session_factory=factory, clock=lambda: due_at + timedelta(seconds=2), mode="retry",
        ) == "skipped"
        with factory() as session:
            status = read_cleanup_status(session.get(Organization, organization_id))
            assert status.last_success_at == due_at
            assert status.consecutive_failures == 0
    finally:
        release_cleanup.set()
        if worker.ident is not None:
            worker.join(timeout=10)
        with retention_engine.begin() as connection:
            connection.execute(delete(Organization).where(Organization.id == organization_id))


def test_postgres_retry_survives_persistent_analysis_lock_then_succeeds_after_release(
    scheduler, retention_engine, monkeypatch,
):
    """Only a guarded temporary test org is committed for independent sessions.

    An analysis read's shared row lock cannot report cleanup success or arrange
    another failure retry. Two skipped one-shot callbacks must therefore keep
    a bounded future timer until the lock releases.
    """
    from uuid import uuid4
    from sqlalchemy import delete, insert
    from sqlalchemy.orm import sessionmaker
    from app.models import Organization
    from app.services.retention_status import (
        policy_and_legacy_revision, read_cleanup_status, record_cleanup_failure,
    )

    suffix = uuid4().hex
    with retention_engine.begin() as connection:
        organization_id = connection.execute(insert(Organization).values(
            name="Retention Retry Lock Test", domain=f"retry-lock-{suffix}.invalid",
            slug=f"retry-lock-{suffix}", status="active", settings=policy_org().settings,
        ).returning(Organization.id)).scalar_one()
    factory = sessionmaker(bind=retention_engine)
    with factory() as session:
        organization = session.get(Organization, organization_id)
        version, legacy_id = policy_and_legacy_revision(organization)
        assert record_cleanup_failure(
            organization, now=NOW, policy_version=version,
            legacy_request_id=legacy_id, error_code="cache_unavailable",
        )
        session.commit()

    # All sessions, including scheduling's metadata reads, use the guarded DB.
    clock = [NOW + timedelta(minutes=15)]
    real_process = scheduler.process_organization_cleanup
    monkeypatch.setattr(scheduler, "SessionLocal", factory)
    monkeypatch.setattr(scheduler, "utc_now", lambda: clock[0])
    monkeypatch.setattr(scheduler, "process_organization_cleanup", lambda organization_id, **kwargs: real_process(
        organization_id, session_factory=factory, clock=lambda: clock[0], **kwargs,
    ))
    instance = scheduler.RetentionScheduler()
    instance.scheduler = QueuedScheduler()
    job_id = f"{scheduler.RETRY_JOB_PREFIX}{organization_id}"
    locker = factory()
    try:
        locker.query(Organization).filter_by(id=organization_id).with_for_update(read=True).one()
        for _ in range(2):
            assert instance._run_retry(organization_id) == "skipped"
            _, queued = instance.scheduler.jobs[job_id]
            assert queued["trigger"].run_date == clock[0] + timedelta(minutes=15)
            with factory() as session:
                status = read_cleanup_status(session.get(Organization, organization_id))
                assert status.state == "failed" and status.consecutive_failures == 1
                assert status.next_retry_at == NOW + timedelta(minutes=15)
            clock[0] = queued["trigger"].run_date
            # APScheduler removes each DateTrigger job before its callback.
            instance.scheduler.jobs.pop(job_id)

        locker.rollback()
        assert instance._run_retry(organization_id) == "succeeded"
        assert not instance.scheduler.jobs
        with factory() as session:
            status = read_cleanup_status(session.get(Organization, organization_id))
            assert status.state == "succeeded" and status.consecutive_failures == 0
            assert status.last_success_at == clock[0]
            assert status.next_retry_at is None
        # A stale timer cannot restart the chain after success.
        assert instance._run_retry(organization_id) == "skipped"
        assert not instance.scheduler.jobs
    finally:
        locker.rollback()
        locker.close()
        with retention_engine.begin() as connection:
            connection.execute(delete(Organization).where(Organization.id == organization_id))
