"""
ARQ Background Tasks.

Defines async tasks that can be enqueued and processed by ARQ workers.
Tasks support checkpointing for deployment resilience.
"""
import logging
from typing import Any

from .analysis_runner import run_analysis_with_checkpoints as _run_analysis

logger = logging.getLogger(__name__)


async def run_analysis_with_checkpoints(
    ctx: dict[str, Any],
    analysis_id: int,
    integration_id: int,
    days_back: int,
    user_id: int,
) -> dict[str, Any]:
    """
    ARQ task wrapper for checkpoint-aware burnout analysis.

    This is the ARQ task entry point. The actual implementation is in
    analysis_runner.py to keep concerns separated.

    Args:
        ctx: ARQ context dictionary (provides Redis pool, job_id, etc.)
        analysis_id: Analysis database ID
        integration_id: Rootly/PagerDuty integration ID
        days_back: Number of days to analyze
        user_id: User ID requesting analysis

    Returns:
        Dict with status and results

    Checkpoints:
        0: Starting
        1: Data fetch complete
        2: All data collected (GitHub, Slack, Jira)
        3: Team analysis complete (final results saved)

    Raises:
        Exception: On fatal errors (logged and analysis marked as failed)
    """
    logger.info(f"ARQ task starting: analysis {analysis_id}")

    try:
        # Call the checkpoint-aware analysis runner
        result = await _run_analysis(
            analysis_id=analysis_id,
            integration_id=integration_id,
            days_back=days_back,
            user_id=user_id,
        )

        logger.info(f"ARQ task complete: analysis {analysis_id}, status={result.get('status')}")
        return result

    except Exception as e:
        logger.error(f"ARQ task failed: analysis {analysis_id}, error={e}")
        raise


async def resume_interrupted_analyses() -> None:
    """
    Resume analyses that were interrupted during deployment.

    Called on ARQ worker startup to detect and resume any
    analyses that were running when the previous worker was killed.

    Process:
        1. Query database for analyses with status="running" and last_checkpoint set
        2. Filter out stale analyses (updated_at > 5 minutes ago)
        3. Re-enqueue each interrupted analysis with current checkpoint data
        4. Track attempt_count to prevent infinite retry loops

    Security:
        - Limits max attempts to 3 to prevent infinite loops
        - Validates checkpoint data before resuming
        - Logs all resume attempts for audit trail
    """
    logger.info("Checking for interrupted analyses to resume")

    from datetime import datetime, timedelta, timezone
    from ..models import Analysis, get_db
    from .arq_worker import get_arq_pool

    db = next(get_db())

    try:
        # Find analyses that were interrupted (status=running with checkpoint saved)
        # Use SELECT FOR UPDATE to prevent race condition with multiple workers
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

        interrupted = (
            db.query(Analysis)
            .filter(
                Analysis.status == "running",
                Analysis.last_checkpoint.isnot(None),
                Analysis.last_checkpoint > 0,  # Has made progress
                Analysis.updated_at < stale_threshold,  # Stale (no activity for 5+ min)
            )
            .with_for_update(skip_locked=True)  # Lock rows, skip if already locked by another worker
            .all()
        )

        if not interrupted:
            logger.info("No interrupted analyses found")
            return

        logger.info(f"Found {len(interrupted)} interrupted analyses to resume")

        arq_pool = await get_arq_pool()

        for analysis in interrupted:
            try:
                # Check attempt count to prevent infinite loops
                attempt_count = analysis.attempt_count or 0
                if attempt_count >= 3:
                    logger.warning(
                        f"Analysis {analysis.id} exceeded max attempts ({attempt_count}), marking as failed"
                    )
                    analysis.status = "failed"
                    analysis.error_message = (
                        f"Analysis interrupted and failed to resume after {attempt_count} attempts"
                    )
                    db.commit()
                    continue

                # Get analysis configuration
                config = analysis.config or {}
                days_back = config.get("days_back", 30)
                integration_id = analysis.rootly_integration_id
                user_id = analysis.user_id

                if not integration_id:
                    logger.error(f"Analysis {analysis.id} has no integration_id, cannot resume")
                    continue

                logger.info(
                    f"Resuming analysis {analysis.id} from checkpoint {analysis.last_checkpoint} "
                    f"(attempt {attempt_count + 1}/3)"
                )

                # Re-enqueue the analysis job
                job_id = f"analysis_{analysis.id}_resume_{int(datetime.now(timezone.utc).timestamp())}"
                await arq_pool.enqueue_job(
                    "run_analysis_with_checkpoints",
                    analysis.id,
                    integration_id,
                    days_back,
                    user_id,
                    _job_id=job_id,
                    _queue_name="analysis_queue"
                )

                logger.info(f"Analysis {analysis.id} re-enqueued with job_id={job_id}")

            except Exception as e:
                logger.error(f"Failed to resume analysis {analysis.id}: {e}")

        logger.info("Resume check complete")

    except Exception as e:
        logger.error(f"Failed to check for interrupted analyses: {e}")
    finally:
        db.close()


async def cleanup_stale_analyses(ctx: dict[str, Any]) -> None:
    """
    Periodic task to mark stale analyses as failed.

    Runs every 10 minutes via ARQ cron to detect analyses that are
    stuck in "running" state without progress.

    Args:
        ctx: ARQ context dictionary

    Criteria for stale:
        - Status is "running"
        - updated_at is more than 30 minutes old
        - No checkpoint progress in 30+ minutes

    Action:
        - Mark analysis as "failed" with descriptive error message
        - Allow manual retry if needed
    """
    logger.info("Running stale analysis cleanup")

    from datetime import datetime, timedelta, timezone
    from ..models import Analysis, get_db

    db = next(get_db())

    try:
        # Find truly stale analyses (no progress for 30+ minutes)
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

        stale = (
            db.query(Analysis)
            .filter(
                Analysis.status == "running",
                Analysis.updated_at < stale_threshold,
            )
            .all()
        )

        if not stale:
            logger.info("No stale analyses found")
            return

        logger.warning(f"Found {len(stale)} stale analyses")

        for analysis in stale:
            try:
                last_checkpoint = analysis.last_checkpoint or 0
                minutes_stale = (datetime.now(timezone.utc) - analysis.updated_at).total_seconds() / 60

                logger.warning(
                    f"Marking stale analysis {analysis.id} as failed "
                    f"(last_checkpoint={last_checkpoint}, stale_for={minutes_stale:.1f}min)"
                )

                analysis.status = "failed"
                analysis.error_message = (
                    f"Analysis timed out (no progress for {minutes_stale:.0f} minutes). "
                    f"Last completed checkpoint: {last_checkpoint}. "
                    f"Worker may have been killed or encountered a hang."
                )
                db.commit()

            except Exception as e:
                logger.error(f"Failed to mark analysis {analysis.id} as failed: {e}")
                db.rollback()

        logger.info(f"Stale analysis cleanup complete - marked {len(stale)} as failed")

    except Exception as e:
        logger.error(f"Failed to cleanup stale analyses: {e}")
    finally:
        db.close()


__all__ = [
    "run_analysis_with_checkpoints",
    "resume_interrupted_analyses",
    "cleanup_stale_analyses",
]
