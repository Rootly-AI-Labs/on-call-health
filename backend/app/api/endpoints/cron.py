"""Scheduled job triggers for hosts without in-process schedulers.

Each endpoint runs one job pass and returns 500 when the pass itself failed.
Retention rechecks what is due under the organization lock, so any cadence is
safe and a missed run is caught up by the next one. Trigger weekly digests
every 30 minutes: they only send during Monday's 10:00-10:59 hour in each
user's timezone and do not catch up after that window. Duplicate digest sends
are blocked unless WEEKLY_DIGEST_FORCE_SEND is enabled.
"""
import asyncio
import logging
import secrets
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ...core.config import settings
from ...services.retention_scheduler import (
    process_due_retention_cleanups,
    process_failed_retention_retries,
)
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
