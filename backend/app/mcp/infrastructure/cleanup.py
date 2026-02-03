"""Periodic cleanup task for stale MCP connections.

Runs every 5 minutes via APScheduler to remove connections that have been
inactive for longer than the staleness threshold. This prevents resource
leaks from abandoned connections.

Uses graceful cleanup: errors are logged but don't crash the cleanup job.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.triggers.interval import IntervalTrigger

from app.mcp.infrastructure.connection_tracker import connection_tracker
from app.mcp.infrastructure.logging import (
    log_cleanup_completed,
    log_cleanup_failed,
    log_connection_close,
)

# Connections inactive for this many minutes are considered stale
# Set to 2x the cleanup interval (5 min) for safety margin
STALE_CONNECTION_TIMEOUT_MINUTES = 10


async def cleanup_stale_connections() -> None:
    """Remove connections with no activity for > 10 minutes.

    Runs every 5 minutes via APScheduler. Uses graceful cleanup:
    1. Identify stale connections
    2. Remove from tracker
    3. Log cleanup results

    Errors are logged but don't crash the cleanup job.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=STALE_CONNECTION_TIMEOUT_MINUTES
        )
        stale_connections = await connection_tracker.get_stale_connections(cutoff)

        if not stale_connections:
            return  # Nothing to clean up, don't log

        cleaned_count = 0
        for api_key_id, connection_id in stale_connections:
            try:
                await connection_tracker.remove_connection(api_key_id, connection_id)
                log_connection_close(api_key_id, connection_id)
                cleaned_count += 1
            except Exception as e:
                log_cleanup_failed(f"Failed to remove {connection_id}: {str(e)}")

        if cleaned_count > 0:
            log_cleanup_completed(cleaned_count)

    except Exception as e:
        log_cleanup_failed(f"Cleanup task error: {str(e)}")


def get_cleanup_job_config() -> dict:
    """Get APScheduler job configuration for the cleanup task.

    Returns:
        Dictionary with APScheduler job parameters:
        - func: The async cleanup function
        - trigger: IntervalTrigger every 5 minutes
        - id: Job identifier for management
        - replace_existing: Allow updating existing job
    """
    return {
        "func": cleanup_stale_connections,
        "trigger": IntervalTrigger(minutes=5),
        "id": "mcp_connection_cleanup",
        "replace_existing": True,
    }
