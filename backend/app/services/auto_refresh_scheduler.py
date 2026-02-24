"""
Auto-refresh analysis scheduler.

Registers one CronTrigger job per supported interval (24h / 3d / 7d) so each
fires at exactly the right cadence and only processes analyses for that interval.
"""
import asyncio
import logging
import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _make_cron_trigger(interval_str: str) -> CronTrigger:
    """Map an interval string to the appropriate CronTrigger."""
    if interval_str == "10m":
        return CronTrigger(minute="*/10")                # every 10 minutes (testing)
    elif interval_str == "24h":
        return CronTrigger(hour=0, minute=0)             # daily at midnight
    elif interval_str == "3d":
        return CronTrigger(day="*/3", hour=0, minute=0)  # every 3 days at midnight
    elif interval_str == "7d":
        return CronTrigger(day="*/7", hour=0, minute=0)  # every 7 days at midnight
    else:
        return CronTrigger(hour=0, minute=0)              # fallback: daily


def _parse_interval(interval_str: str) -> timedelta:
    """Parse an interval string like '24h', '3d', '7d' into a timedelta."""
    if not interval_str:
        return timedelta(days=1)
    interval_str = interval_str.strip().lower()
    if interval_str.endswith("m"):
        return timedelta(minutes=int(interval_str[:-1]))
    if interval_str.endswith("h"):
        return timedelta(hours=int(interval_str[:-1]))
    if interval_str.endswith("d"):
        return timedelta(days=int(interval_str[:-1]))
    # Fallback: treat as days
    try:
        return timedelta(days=int(interval_str))
    except ValueError:
        return timedelta(days=1)


async def check_and_run_auto_refresh_analyses(interval_filter: str = None):
    """
    Cron job: find auto-refresh analyses matching `interval_filter` that are due
    and re-run them.  Pass interval_filter=None to process all intervals.
    """
    from ..models import SessionLocal, Analysis, RootlyIntegration
    from ..api.endpoints.analyses import run_analysis_task

    label = interval_filter or "all"
    logger.info(f"🔄 [AUTO_REFRESH_SCHEDULER] Checking for due auto-refresh analyses (interval={label})...")

    db = SessionLocal()
    due_analyses = []

    try:
        # Fetch completed auto-refresh analyses, optionally scoped to one interval
        candidates = db.query(Analysis).filter(
            Analysis.is_auto_refresh == True,
            Analysis.status == "completed",
            Analysis.auto_refresh_interval != None,
            Analysis.completed_at != None,
        )
        if interval_filter:
            candidates = candidates.filter(Analysis.auto_refresh_interval == interval_filter)
        candidates = candidates.all()

        now = datetime.now(timezone.utc)

        for analysis in candidates:
            interval = _parse_interval(analysis.auto_refresh_interval)
            completed_at = analysis.completed_at
            # Ensure timezone-aware comparison
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            if now >= completed_at + interval:
                due_analyses.append(analysis)

        logger.info(
            f"🔄 [AUTO_REFRESH_SCHEDULER] {len(candidates)} auto-refresh analyses found, "
            f"{len(due_analyses)} due for refresh"
        )

        for old_analysis in due_analyses:
            try:
                # Look up integration to get api_token
                integration = db.query(RootlyIntegration).filter(
                    RootlyIntegration.id == old_analysis.rootly_integration_id
                ).first()

                if not integration:
                    logger.warning(
                        f"🔄 [AUTO_REFRESH_SCHEDULER] Integration {old_analysis.rootly_integration_id} "
                        f"not found for analysis {old_analysis.id}, skipping"
                    )
                    continue

                config = old_analysis.config or {}

                # Create new analysis record with same params
                new_analysis = Analysis(
                    user_id=old_analysis.user_id,
                    organization_id=old_analysis.organization_id,
                    rootly_integration_id=old_analysis.rootly_integration_id,
                    integration_name=old_analysis.integration_name,
                    platform=old_analysis.platform,
                    time_range=old_analysis.time_range,
                    status="pending",
                    is_saved=False,
                    is_auto_refresh=True,
                    auto_refresh_interval=old_analysis.auto_refresh_interval,
                    config=config,
                )
                db.add(new_analysis)
                db.flush()  # Get the new ID without committing yet

                new_id = new_analysis.id
                new_uuid = new_analysis.uuid

                # Delete the old analysis
                db.delete(old_analysis)
                db.commit()

                logger.info(
                    f"🔄 [AUTO_REFRESH_SCHEDULER] Replaced analysis {old_analysis.id} → new analysis {new_id} "
                    f"(user={old_analysis.user_id}, interval={old_analysis.auto_refresh_interval})"
                )

                # Fire the background task
                asyncio.create_task(
                    run_analysis_task(
                        analysis_id=new_id,
                        analysis_uuid=new_uuid,
                        integration_id=integration.id,
                        api_token=integration.api_token,
                        platform=integration.platform,
                        organization_name=integration.organization_name or integration.name,
                        time_range=old_analysis.time_range,
                        include_weekends=config.get("include_weekends", True),
                        include_github=config.get("include_github", False),
                        include_slack=config.get("include_slack", False),
                        include_jira=config.get("include_jira", False),
                        include_linear=config.get("include_linear", False),
                        user_id=old_analysis.user_id,
                        enable_ai=False,
                    )
                )

            except Exception as e:
                logger.error(
                    f"🔄 [AUTO_REFRESH_SCHEDULER] Failed to refresh analysis {old_analysis.id}: {e}",
                    exc_info=True,
                )
                db.rollback()

    except Exception as e:
        logger.error(f"🔄 [AUTO_REFRESH_SCHEDULER] Unexpected error: {e}", exc_info=True)
    finally:
        db.close()
