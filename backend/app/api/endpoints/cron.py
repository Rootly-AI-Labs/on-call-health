"""Scheduled job triggers for hosts without in-process schedulers.

Each endpoint runs one pass of a job that is safe to repeat: the job itself
decides what is due, so a late, missed or duplicated trigger does no harm.
"""
import asyncio
import logging
import secrets
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, status

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
    return {"daily": asdict(daily), "retries": asdict(retries)}


@router.get("/weekly-digest")
async def run_weekly_digest():
    await check_and_send_weekly_digests()
    return {"enabled": settings.WEEKLY_DIGEST_ENABLED}
