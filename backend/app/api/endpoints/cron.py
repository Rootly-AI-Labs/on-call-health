"""Scheduled job triggers for hosts without in-process schedulers.

Each endpoint runs one job pass and returns 500 when the pass itself failed.
Retention rechecks what is due under the organization lock, so any cadence is
safe and a missed run is caught up by the next one. Trigger surveys every
minute: each call runs jobs whose local send time fell in the last 15 minutes,
and delivery skips anyone already contacted that day. Trigger weekly digests
every 30 minutes: they only send during Monday's 10:00-10:59 hour in each
user's timezone and do not catch up after that window. Duplicate digest sends
are blocked unless WEEKLY_DIGEST_FORCE_SEND is enabled.

The analysis and auto-refresh triggers only run work when ANALYSIS_EXECUTION is
"queue". Trigger analyses every minute; each call fails stale claims and runs at
most one queued analysis, so calls may overlap while long analyses finish.
Trigger auto-refresh hourly; it queues analyses whose interval has elapsed.
"""
import asyncio
import logging
import secrets
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ...core.config import settings
from ...services.analysis_queue import run_next_queued_analysis
from ...services.auto_refresh_scheduler import check_and_run_auto_refresh_analyses
from ...services.retention_scheduler import (
    process_due_retention_cleanups,
    process_failed_retention_retries,
)
from ...services.survey_scheduler import survey_scheduler
from ...services.weekly_digest_service import check_and_send_weekly_digests

logger = logging.getLogger(__name__)


def require_cron_secret(request: Request) -> None:
    expected = settings.CRON_SECRET
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cron triggers are not configured")
    provided = request.headers.get("authorization", "")
    if not secrets.compare_digest(provided.encode(), f"Bearer {expected}".encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


router = APIRouter(dependencies=[Depends(require_cron_secret)])


@router.get("/retention")
async def run_retention():
    """Daily cleanup for due organizations, then retries for failed ones."""
    daily = await asyncio.to_thread(process_due_retention_cleanups)
    retries = await asyncio.to_thread(process_failed_retention_retries)
    logger.info("Retention cron daily=%s retries=%s", asdict(daily), asdict(retries))
    body = {"daily": asdict(daily), "retries": asdict(retries)}
    if daily.poll_failed or retries.poll_failed:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)
    return body


@router.get("/weekly-digest")
async def run_weekly_digest():
    body = {"enabled": settings.WEEKLY_DIGEST_ENABLED}
    if not await check_and_send_weekly_digests():
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)
    return body


@router.get("/surveys")
async def run_surveys():
    """Survey sends, same-day reminders and follow-ups that are due now."""
    result = await survey_scheduler.dispatch_due_jobs()
    logger.info("Survey cron %s", asdict(result))
    body = asdict(result)
    if result.failed:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)
    return body


def _queue_disabled() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "ANALYSIS_EXECUTION is not queue"})


@router.get("/analyses")
async def run_queued_analysis():
    if settings.ANALYSIS_EXECUTION != "queue":
        return _queue_disabled()
    result = await run_next_queued_analysis()
    logger.info("Analysis cron %s", asdict(result))
    return asdict(result)


@router.get("/auto-refresh")
async def run_auto_refresh():
    if settings.ANALYSIS_EXECUTION != "queue":
        return _queue_disabled()
    if not await check_and_run_auto_refresh_analyses():
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Auto-refresh check failed"})
    return {"checked": True}
