"""Survey cron dispatch: trigger windows and once-per-occurrence claims.

Dispatch tests need RETENTION_TEST_DATABASE_URL naming a disposable PostgreSQL
database containing ``retention_test``; each test rolls its rows back.
"""
import asyncio
import os
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytz
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api.endpoints import cron
from app.services import survey_scheduler as scheduler_module
from app.services.survey_scheduler import SURVEY_DISPATCH_WINDOW, SurveyDispatchResult, SurveyScheduler

NEW_YORK = pytz.timezone("America/New_York")
# Wednesday
WEDNESDAY = datetime(2026, 10, 28)
SATURDAY = datetime(2026, 10, 31)


def schedule(**overrides):
    values = dict(
        id=1,
        organization_id=42,
        timezone="America/New_York",
        send_time=time(9, 0),
        frequency_type="daily",
        send_weekdays_only=False,
        day_of_week=None,
        send_reminder=False,
        reminder_time=None,
        reminder_hours_after=4,
        follow_up_reminders_enabled=False,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def local(day: datetime, hour: int, minute: int) -> datetime:
    return NEW_YORK.localize(day.replace(hour=hour, minute=minute)).astimezone(timezone.utc)


def due_kinds(survey_schedule, now):
    kinds = []
    for kind, trigger in SurveyScheduler()._schedule_triggers(survey_schedule):
        fire_time = trigger.get_next_fire_time(None, now - SURVEY_DISPATCH_WINDOW)
        if fire_time is not None and fire_time <= now:
            kinds.append(kind)
    return kinds


@pytest.mark.parametrize("hour,minute,expected", [
    (8, 59, []),
    (9, 0, ["initial"]),
    (9, 14, ["initial"]),
    (9, 16, []),
])
def test_initial_survey_is_due_within_window_after_local_send_time(hour, minute, expected):
    assert due_kinds(schedule(), local(WEDNESDAY, hour, minute)) == expected


def test_weekday_schedule_is_not_due_on_saturday():
    assert due_kinds(schedule(frequency_type="weekday"), local(SATURDAY, 9, 5)) == []
    assert due_kinds(schedule(frequency_type="weekday"), local(WEDNESDAY, 9, 5)) == ["initial"]


def test_weekly_schedule_is_only_due_on_its_day():
    assert due_kinds(schedule(frequency_type="weekly", day_of_week=2), local(WEDNESDAY, 9, 5)) == ["initial"]
    assert due_kinds(schedule(frequency_type="weekly", day_of_week=3), local(WEDNESDAY, 9, 5)) == []


def test_weekly_schedule_without_day_is_skipped():
    assert due_kinds(schedule(frequency_type="weekly", day_of_week=None), local(WEDNESDAY, 9, 5)) == []


def test_reminder_and_follow_up_use_their_own_times():
    survey_schedule = schedule(send_reminder=True, reminder_hours_after=4, follow_up_reminders_enabled=True)

    assert due_kinds(survey_schedule, local(WEDNESDAY, 9, 5)) == ["initial", "follow_up"]
    assert due_kinds(survey_schedule, local(WEDNESDAY, 13, 5)) == ["reminder"]
    assert due_kinds(schedule(send_reminder=True, reminder_time=time(15, 30)), local(WEDNESDAY, 15, 40)) == ["reminder"]


def test_follow_up_runs_daily_even_for_weekday_schedules():
    survey_schedule = schedule(frequency_type="weekday", follow_up_reminders_enabled=True)

    assert due_kinds(survey_schedule, local(SATURDAY, 9, 5)) == ["follow_up"]


def test_in_process_jobs_keep_their_ids():
    survey_scheduler = SurveyScheduler()

    survey_scheduler._add_schedule_job(schedule(send_reminder=True, follow_up_reminders_enabled=True))

    assert sorted(job.id for job in survey_scheduler.scheduler.get_jobs()) == ["followup_org_42", "reminder_org_42", "survey_org_42"]


@pytest.fixture(scope="module")
def dispatch_engine():
    database_url = os.getenv("RETENTION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set RETENTION_TEST_DATABASE_URL to a disposable PostgreSQL retention_test database")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql" or "retention_test" not in (url.database or "").lower():
        pytest.fail("Dispatch tests require PostgreSQL and a database name containing retention_test")

    from app.models import Base

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(dispatch_engine):
    connection = dispatch_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def organization_ids(db_connection):
    from app.models import Organization

    suffix = uuid4().hex
    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as db:
        records = [
            Organization(name=f"Dispatch {index}", domain=f"dispatch-{suffix}-{index}.example.com",
                         slug=f"dispatch-{suffix}-{index}", status="active")
            for index in range(2)
        ]
        db.add_all(records)
        db.commit()
        return [record.id for record in records]


@pytest.fixture
def dispatcher(db_connection):
    survey_scheduler = SurveyScheduler()
    survey_scheduler._run_survey_job = AsyncMock(return_value=True)
    survey_scheduler._run_follow_up_job = AsyncMock(return_value=True)

    def session():
        return Session(bind=db_connection, join_transaction_mode="create_savepoint")

    with patch.object(scheduler_module, "SessionLocal", session):
        yield survey_scheduler


def dispatch(survey_scheduler, schedules, now):
    with patch.object(survey_scheduler, "_enabled_schedules", return_value=schedules):
        return asyncio.run(survey_scheduler.dispatch_due_jobs(now=now))


def test_each_occurrence_runs_once_across_repeated_calls(dispatcher, organization_ids):
    schedules = [schedule(organization_id=organization_ids[0], send_reminder=True, follow_up_reminders_enabled=True)]

    first = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 1))
    second = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 2))
    later = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 14))

    assert first == SurveyDispatchResult(schedules=1, ran=2, failed=0)
    assert second == later == SurveyDispatchResult(schedules=1, ran=0, failed=0)
    dispatcher._run_survey_job.assert_awaited_once_with(organization_ids[0], False)
    dispatcher._run_follow_up_job.assert_awaited_once_with(organization_ids[0])


def test_occurrence_near_utc_midnight_is_not_repeated_after_midnight(dispatcher, organization_ids):
    # 19:55 New York during daylight saving time is 23:55 UTC.
    schedules = [schedule(organization_id=organization_ids[0], send_time=time(19, 55))]

    before_midnight = dispatch(dispatcher, schedules, local(WEDNESDAY, 19, 56))
    after_midnight = dispatch(dispatcher, schedules, local(WEDNESDAY, 20, 5))

    assert before_midnight.ran == 1
    assert after_midnight.ran == 0
    dispatcher._run_survey_job.assert_awaited_once()


def test_late_trigger_still_runs_the_occurrence_once(dispatcher, organization_ids):
    schedules = [schedule(organization_id=organization_ids[0])]

    result = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 12))

    assert result.ran == 1


def test_reminder_inside_window_runs_once(dispatcher, organization_ids):
    schedules = [schedule(organization_id=organization_ids[0], send_reminder=True, reminder_time=time(13, 0))]

    for minute in range(0, 15):
        dispatch(dispatcher, schedules, local(WEDNESDAY, 13, minute))

    dispatcher._run_survey_job.assert_awaited_once_with(organization_ids[0], True)


def test_failed_delivery_is_counted_and_not_retried(dispatcher, organization_ids):
    dispatcher._run_survey_job = AsyncMock(return_value=False)
    schedules = [schedule(organization_id=organization_ids[0])]

    first = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 1))
    second = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 2))

    assert first == SurveyDispatchResult(schedules=1, ran=0, failed=1)
    assert second == SurveyDispatchResult(schedules=1, ran=0, failed=0)
    dispatcher._run_survey_job.assert_awaited_once()


def test_crashed_job_is_counted_and_others_still_run(dispatcher, organization_ids):
    dispatcher._run_survey_job = AsyncMock(side_effect=[RuntimeError("slack down"), True])
    schedules = [schedule(organization_id=organization_id) for organization_id in organization_ids]

    result = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 1))

    assert result == SurveyDispatchResult(schedules=2, ran=1, failed=1)


def test_invalid_schedule_does_not_block_other_organizations(dispatcher, organization_ids):
    schedules = [
        schedule(id=1, organization_id=organization_ids[0], timezone="Not/AZone"),
        schedule(id=2, organization_id=organization_ids[1]),
    ]

    result = dispatch(dispatcher, schedules, local(WEDNESDAY, 9, 1))

    assert result == SurveyDispatchResult(schedules=2, ran=1, failed=1)
    dispatcher._run_survey_job.assert_awaited_once_with(organization_ids[1], False)


def test_old_claims_are_pruned(dispatcher, db_connection, organization_ids):
    from app.models import SurveyDispatchClaim

    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as db:
        db.add(SurveyDispatchClaim(organization_id=organization_ids[0], job_kind="initial",
                                   fire_time=local(WEDNESDAY, 9, 0) - timedelta(days=30),
                                   claimed_at=local(WEDNESDAY, 9, 0) - timedelta(days=30)))
        db.commit()

    dispatch(dispatcher, [], local(WEDNESDAY, 9, 1))

    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as db:
        assert db.query(SurveyDispatchClaim).filter(SurveyDispatchClaim.organization_id == organization_ids[0]).count() == 0


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cron.settings, "CRON_SECRET", "test-cron-secret")
    app = FastAPI()
    app.include_router(cron.router, prefix="/internal/cron")
    return TestClient(app)


@pytest.mark.parametrize("failed,status_code", [(0, 200), (1, 500)])
def test_surveys_endpoint_reports_failed_jobs(client, failed, status_code):
    result = SurveyDispatchResult(schedules=3, ran=2, failed=failed)
    with patch.object(cron.survey_scheduler, "dispatch_due_jobs", new=AsyncMock(return_value=result)):
        response = client.get("/internal/cron/surveys", headers={"Authorization": "Bearer test-cron-secret"})

    assert response.status_code == status_code
    assert response.json() == {"schedules": 3, "ran": 2, "failed": failed}


class _Lock:
    def __init__(self, acquired=True, error=None):
        self.acquired, self.error = acquired, error

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self.acquired

    async def __aexit__(self, *exc):
        return False


@pytest.mark.parametrize("method,args", [
    ("_send_organization_surveys", (42, None, False)),
    ("_send_organization_surveys", (42, None, True)),
    ("_send_follow_up_reminders", (42, None)),
])
@pytest.mark.parametrize("lock", [_Lock(acquired=False), _Lock(error=RuntimeError("redis down"))])
def test_delivery_reports_failure_when_it_cannot_run(method, args, lock):
    db = SimpleNamespace(rollback=lambda: None)
    with patch.object(scheduler_module, "with_distributed_lock", return_value=lock):
        delivered = asyncio.run(getattr(SurveyScheduler(), method)(*args[:1], db, *args[2:]))

    assert delivered is False


def test_delivery_without_enabled_schedule_has_nothing_to_fail():
    survey_scheduler = SurveyScheduler()
    with patch.object(scheduler_module, "with_distributed_lock", return_value=_Lock()), \
         patch.object(survey_scheduler, "_get_enabled_schedule", return_value=None):
        delivered = asyncio.run(survey_scheduler._send_organization_surveys(42, SimpleNamespace(), False))

    assert delivered is True
