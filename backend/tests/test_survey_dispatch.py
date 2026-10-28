import asyncio
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import cron
from app.services import survey_scheduler as scheduler_module
from app.services.survey_scheduler import SurveyDispatchResult, SurveyScheduler

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
    triggers = SurveyScheduler()._schedule_triggers(survey_schedule)
    return [
        kind for kind, trigger in triggers
        if scheduler_module._fires_between(trigger, now - scheduler_module.SURVEY_DISPATCH_WINDOW, now)
    ]


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


def fake_session(schedules):
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = schedules
    return lambda: session


def test_dispatch_runs_each_due_job_once():
    survey_scheduler = SurveyScheduler()
    survey_schedule = schedule(send_reminder=True, follow_up_reminders_enabled=True)
    with patch.object(scheduler_module, "SessionLocal", fake_session([survey_schedule, schedule(organization_id=7, send_time=time(18, 0))])), \
         patch.object(survey_scheduler, "_run_survey_job", new=AsyncMock()) as survey_job, \
         patch.object(survey_scheduler, "_run_follow_up_job", new=AsyncMock()) as follow_up_job:
        result = asyncio.run(survey_scheduler.dispatch_due_jobs(now=local(WEDNESDAY, 9, 2)))

    survey_job.assert_awaited_once_with(42, False)
    follow_up_job.assert_awaited_once_with(42)
    assert result == SurveyDispatchResult(schedules=2, ran=2, failed=0)


def test_dispatch_counts_failed_jobs_and_keeps_going():
    survey_scheduler = SurveyScheduler()
    schedules = [schedule(organization_id=1), schedule(organization_id=2)]
    with patch.object(scheduler_module, "SessionLocal", fake_session(schedules)), \
         patch.object(survey_scheduler, "_run_survey_job", new=AsyncMock(side_effect=[RuntimeError("slack down"), None])) as survey_job:
        result = asyncio.run(survey_scheduler.dispatch_due_jobs(now=local(WEDNESDAY, 9, 2)))

    assert survey_job.await_count == 2
    assert result == SurveyDispatchResult(schedules=2, ran=1, failed=1)


def test_in_process_jobs_keep_their_ids():
    survey_scheduler = SurveyScheduler()

    survey_scheduler._add_schedule_job(schedule(send_reminder=True, follow_up_reminders_enabled=True))

    assert sorted(job.id for job in survey_scheduler.scheduler.get_jobs()) == ["followup_org_42", "reminder_org_42", "survey_org_42"]


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
