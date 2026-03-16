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
from sqlalchemy import text

from ..core.distributed_lock import with_distributed_lock

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
    from ..models import SessionLocal, Analysis, RootlyIntegration, User
    from ..api.endpoints.analyses import run_analysis_task
    from ..services.integration_validator import IntegrationValidator
    from ..services.notification_service import NotificationService
    from ..core.rootly_client import RootlyAPIClient
    from ..core.pagerduty_client import PagerDutyAPIClient

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
                lock_key = f"auto_refresh:analysis:{old_analysis.id}"

                # Distributed lock prevents cross-instance duplication.
                # Always take a DB row lock to ensure only one worker mutates the analysis.
                async with with_distributed_lock(lock_key, ttl_seconds=600, timeout_seconds=2) as lock_acquired:
                    try:
                        db.execute(text("SET LOCAL lock_timeout = :lock_timeout"), {"lock_timeout": "5s"})
                    except Exception:
                        # Non-critical: lock_timeout not supported on all DBs
                        pass

                    locked_analysis = (
                        db.query(Analysis)
                        .filter(Analysis.id == old_analysis.id)
                        .with_for_update(skip_locked=True)
                        .execution_options(populate_existing=True)
                        .first()
                    )

                    if not locked_analysis:
                        logger.info(
                            f"🔄 [AUTO_REFRESH_SCHEDULER] Skipping analysis {old_analysis.id}: "
                            f"locked by another worker"
                        )
                        continue

                    old_analysis = locked_analysis

                    # Re-check due state under lock (avoids TOCTOU duplicates)
                    if not old_analysis.is_auto_refresh or old_analysis.status != "completed":
                        continue
                    if not old_analysis.auto_refresh_interval or not old_analysis.completed_at:
                        continue

                    interval = _parse_interval(old_analysis.auto_refresh_interval)
                    completed_at = old_analysis.completed_at
                    if completed_at.tzinfo is None:
                        completed_at = completed_at.replace(tzinfo=timezone.utc)
                    if now < completed_at + interval:
                        continue

                    # Look up integration to get api_token
                    integration = db.query(RootlyIntegration).filter(
                        RootlyIntegration.id == old_analysis.rootly_integration_id
                    ).first()
                    
                    # Use a shallow copy so SQLAlchemy detects JSON changes
                    config = dict(old_analysis.config or {})
                    
                    def _mark_blocked(reason: str, message: str, provider: str = "primary integration") -> None:
                        logger.warning(
                            f"[AUTO_REFRESH_SCHEDULER] Skipping analysis {old_analysis.id}: "
                            f"{reason} ({provider}) - {message}"
                        )
                        try:
                            blocked_at = datetime.now(timezone.utc).isoformat()
                            config["auto_refresh_blocked"] = {
                                "provider": provider,
                                "reason": reason,
                                "message": message,
                                "blocked_at": blocked_at,
                            }
                            old_analysis.config = config
                            db.commit()
                        except Exception as config_error:
                            logger.error(
                                f"[AUTO_REFRESH_SCHEDULER] Failed to persist auto_refresh_blocked for "
                                f"analysis {old_analysis.id}: {config_error}"
                            )
                            db.rollback()
                    
                    if not integration:
                        _mark_blocked(
                            reason="integration_missing",
                            message="Primary integration is not connected.",
                            provider="primary integration",
                        )
                        continue
                    
                    if not integration.is_active:
                        _mark_blocked(
                            reason="integration_inactive",
                            message="Primary integration is inactive or disconnected.",
                            provider=integration.platform,
                        )
                        continue
                    
                    if not integration.api_token or not integration.api_token.strip():
                        _mark_blocked(
                            reason="token_missing",
                            message="Primary integration token is missing. Reconnect to resume auto-refresh.",
                            provider=integration.platform,
                        )
                        continue
    
                    # Validate primary integration (Rootly/PagerDuty) before running auto-refresh.
                    primary_ok = True
                    primary_error = None
                    try:
                        if integration.platform == "rootly":
                            client = RootlyAPIClient(integration.api_token)
                            permissions = await client.check_permissions()
                            primary_ok = permissions.get("incidents", {}).get("access", False)
                            primary_error = permissions.get("incidents", {}).get("error")
                        elif integration.platform == "pagerduty":
                            client = PagerDutyAPIClient(integration.api_token)
                            permissions = await client.check_permissions()
                            primary_ok = permissions.get("incidents", {}).get("access", False)
                            primary_error = permissions.get("incidents", {}).get("error")
                        else:
                            primary_ok = False
                            primary_error = f"Unknown platform: {integration.platform}"
                    except Exception as e:
                        primary_ok = False
                        primary_error = str(e)
    
                    if not primary_ok:
                        logger.warning(
                            f"ðŸ”„ [AUTO_REFRESH_SCHEDULER] Skipping analysis {old_analysis.id}: "
                            f"primary integration invalid ({integration.platform}) - {primary_error}"
                        )
    
                        # Mark analysis as blocked so UI can show a clear "Token Expired" badge
                        try:
                            blocked_at = datetime.now(timezone.utc).isoformat()
                            config["auto_refresh_blocked"] = {
                                "provider": integration.platform,
                                "reason": "token_expired",
                                "message": primary_error or "Primary integration token invalid or expired.",
                                "blocked_at": blocked_at,
                            }
                            old_analysis.config = config
                            db.commit()
                        except Exception as config_error:
                            logger.error(
                                f"ðŸ”„ [AUTO_REFRESH_SCHEDULER] Failed to persist auto_refresh_blocked for "
                                f"analysis {old_analysis.id}: {config_error}"
                            )
                            db.rollback()
    
                        # Emit a warning notification (best-effort)
                        try:
                            user = db.query(User).filter(User.id == old_analysis.user_id).first()
                            if user:
                                notification_service = NotificationService(db)
                                notification_service.create_token_validation_failure_notification(
                                    user=user,
                                    provider=integration.platform,
                                    error_type="authentication",
                                    error_message=primary_error or "Primary integration token invalid or expired."
                                )
                        except Exception as notify_error:
                            logger.error(
                                f"ðŸ”„ [AUTO_REFRESH_SCHEDULER] Failed to create notification for user "
                                f"{old_analysis.user_id}: {notify_error}"
                            )
                        continue
    
                    # Clear any previous blocked state now that primary integration is valid
                    if "auto_refresh_blocked" in config:
                        config.pop("auto_refresh_blocked", None)
    
                    # Validate secondary integrations and disable invalid ones (GitHub/Jira/Linear)
                    include_github = bool(config.get("include_github", False))
                    include_jira = bool(config.get("include_jira", False))
                    include_linear = bool(config.get("include_linear", False))
                    include_slack = bool(config.get("include_slack", False))
    
                    invalid_secondary = []
                    if include_github or include_jira or include_linear:
                        validator = IntegrationValidator(db)
                        validation_results = await validator.validate_all_integrations(
                            user_id=old_analysis.user_id
                        )
    
                        if include_github and not validation_results.get("github", {}).get("valid", False):
                            include_github = False
                            invalid_secondary.append("github")
                        if include_jira and not validation_results.get("jira", {}).get("valid", False):
                            include_jira = False
                            invalid_secondary.append("jira")
                        if include_linear and not validation_results.get("linear", {}).get("valid", False):
                            include_linear = False
                            invalid_secondary.append("linear")
    
                    if invalid_secondary:
                        logger.warning(
                            f"ðŸ”„ [AUTO_REFRESH_SCHEDULER] Disabling invalid integrations for "
                            f"user {old_analysis.user_id}: {', '.join(invalid_secondary)}"
                        )
                        warnings = config.get("permission_warnings", [])
                        if not isinstance(warnings, list):
                            warnings = [str(warnings)]
                        warnings.append(
                            f"Auto-refresh disabled invalid integrations: {', '.join(invalid_secondary)}"
                        )
                        config["permission_warnings"] = warnings
    
                    # Persist updated include flags in config
                    config["include_github"] = include_github
                    config["include_jira"] = include_jira
                    config["include_linear"] = include_linear
                    config["include_slack"] = include_slack
    
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
    
                    user_obj = db.query(User).filter(User.id == old_analysis.user_id).first()
                    user_label = user_obj.email if user_obj else str(old_analysis.user_id)
                    logger.info(
                        f"🔄 [AUTO_REFRESH_SCHEDULER] Replaced analysis {old_analysis.id} → new analysis {new_id} "
                        f"(user={user_label}, interval={old_analysis.auto_refresh_interval})"
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
                            include_github=include_github,
                            include_slack=include_slack,
                            include_jira=include_jira,
                            include_linear=include_linear,
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
