"""Run analyses from a database queue instead of the request process.

With ANALYSIS_EXECUTION=queue, new analyses are saved as pending with a
``queued`` marker in their config. A scheduled trigger claims one at a time with
FOR UPDATE SKIP LOCKED, records the claim time, and runs the usual analysis task,
which moves the row to running and then completed or failed. Claimed analyses
that never finish are failed by the reaper.

The claim leaves status as pending on purpose: run_analysis_task only starts
work for pending analyses.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Analysis, RootlyIntegration, SessionLocal

logger = logging.getLogger(__name__)

STALE_CLAIM_AFTER = timedelta(minutes=35)
STALE_ERROR_MESSAGE = "Analysis did not finish in time and was stopped. Please run it again."


@dataclass
class AnalysisQueueResult:
    ran: Optional[int] = None
    failed_stale: int = 0


def mark_queued(config: Optional[dict], *, enable_ai: bool, include_ai_usage: bool) -> dict:
    """Config for a pending analysis that the queue worker should pick up.

    Drops any claim left from an earlier run of a reused analysis row.
    """
    queued = {key: value for key, value in (config or {}).items() if key != "queue_claimed_at"}
    return {**queued, "queued": True, "enable_ai": enable_ai, "include_ai_usage": include_ai_usage}


def claim_next_queued_analysis(db: Session, now: datetime) -> Optional[int]:
    claimed_id = db.execute(text("""
        UPDATE analyses
        SET config = (COALESCE(config::jsonb, '{}'::jsonb)
                      || jsonb_build_object('queue_claimed_at', CAST(:now AS text)))::json
        WHERE id = (
            SELECT id FROM analyses
            WHERE status = 'pending'
              AND config::jsonb ->> 'queued' = 'true'
              AND config::jsonb ->> 'queue_claimed_at' IS NULL
            ORDER BY created_at, id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING id
    """), {"now": now.isoformat()}).scalar()
    db.commit()
    return claimed_id


def fail_stale_queued_analyses(db: Session, now: datetime) -> int:
    stale_ids = db.execute(text("""
        UPDATE analyses
        SET status = 'failed', error_message = :message, error_generated_at = :now
        WHERE status IN ('pending', 'running')
          AND config::jsonb ->> 'queued' = 'true'
          AND (config::jsonb ->> 'queue_claimed_at')::timestamptz < :cutoff
        RETURNING id
    """), {"message": STALE_ERROR_MESSAGE, "now": now, "cutoff": now - STALE_CLAIM_AFTER}).scalars().all()
    db.commit()
    for analysis_id in stale_ids:
        logger.error("Queued analysis %s did not finish within %s; marked failed", analysis_id, STALE_CLAIM_AFTER)
    return len(stale_ids)


async def run_analysis(analysis_id: int) -> None:
    from ..api.endpoints.analyses import run_analysis_task

    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).one()
        integration = db.query(RootlyIntegration).filter(RootlyIntegration.id == analysis.rootly_integration_id).one()
        config = analysis.config or {}
        kwargs = dict(
            analysis_id=analysis.id,
            analysis_uuid=analysis.uuid,
            integration_id=integration.id,
            api_token=integration.api_token,
            platform=integration.platform,
            organization_name=config.get("organization_name") or integration.organization_name or integration.name,
            time_range=analysis.time_range,
            include_weekends=config.get("include_weekends", True),
            include_github=config.get("include_github", False),
            include_slack=config.get("include_slack", False),
            include_jira=config.get("include_jira", False),
            include_linear=config.get("include_linear", False),
            user_id=analysis.user_id,
            enable_ai=config.get("enable_ai", False),
            pagerduty_team_id=config.get("pagerduty_team_id"),
            include_ai_usage=config.get("include_ai_usage", True),
        )
    finally:
        db.close()
    await run_analysis_task(**kwargs)


async def run_next_queued_analysis(now: Optional[datetime] = None) -> AnalysisQueueResult:
    """Fail stale claims, then claim and run at most one queued analysis."""
    now = now or datetime.now(timezone.utc)
    result = AnalysisQueueResult()
    db = SessionLocal()
    try:
        result.failed_stale = fail_stale_queued_analyses(db, now)
        analysis_id = claim_next_queued_analysis(db, now)
    finally:
        db.close()
    if analysis_id is not None:
        await run_analysis(analysis_id)
        result.ran = analysis_id
    return result
