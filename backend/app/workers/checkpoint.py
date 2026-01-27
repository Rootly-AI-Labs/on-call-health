"""
Checkpoint Management for Analysis Tasks.

Provides atomic checkpoint save/load operations for deployment resilience.
Checkpoints enable analysis tasks to resume from the last saved state after
container restarts or deployments.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models import Analysis

logger = logging.getLogger(__name__)

# Maximum checkpoint data size (5MB) to prevent memory issues
MAX_CHECKPOINT_SIZE_BYTES = 5 * 1024 * 1024

# Checkpoint phase names for logging
CHECKPOINT_PHASES = {
    0: "starting",
    1: "data_fetch_complete",
    2: "all_data_collected",
    3: "team_analysis_complete",
    4: "health_calculation_complete",
    5: "insights_generated",
    6: "building_result",
    7: "complete",
}


class CheckpointError(Exception):
    """Raised when checkpoint operations fail."""


class CheckpointDataTooLargeError(CheckpointError):
    """Raised when checkpoint data exceeds size limit."""


def validate_checkpoint_data(checkpoint_data: dict[str, Any]) -> None:
    """
    Validate checkpoint data before saving.

    Args:
        checkpoint_data: Checkpoint data dictionary to validate

    Raises:
        CheckpointError: If validation fails
        CheckpointDataTooLargeError: If data exceeds size limit

    Security:
        - Validates data size to prevent memory exhaustion
        - Ensures JSON serializability
        - Prevents malformed data from being saved
    """
    if not isinstance(checkpoint_data, dict):
        raise CheckpointError(f"Checkpoint data must be dict, got {type(checkpoint_data)}")

    try:
        serialized = json.dumps(checkpoint_data)
    except (TypeError, ValueError) as e:
        raise CheckpointError(f"Checkpoint data is not JSON serializable: {e}") from e

    size_bytes = len(serialized.encode("utf-8"))
    if size_bytes > MAX_CHECKPOINT_SIZE_BYTES:
        raise CheckpointDataTooLargeError(
            f"Checkpoint data size ({size_bytes} bytes) exceeds limit ({MAX_CHECKPOINT_SIZE_BYTES} bytes)"
        )


async def save_checkpoint(
    db: Session,
    analysis_id: int,
    checkpoint: int,
    checkpoint_data: dict[str, Any],
) -> None:
    """
    Atomically save checkpoint to database.

    Uses database transaction with row-level locking to ensure
    atomicity even with concurrent access.

    Args:
        db: Database session
        analysis_id: Analysis ID to save checkpoint for
        checkpoint: Checkpoint number (0-7)
        checkpoint_data: Checkpoint data dictionary

    Raises:
        CheckpointError: If save fails
        CheckpointDataTooLargeError: If data exceeds size limit

    Security:
        - Row-level lock prevents concurrent modification
        - Validates data before saving
        - Size limit prevents memory exhaustion
        - Transaction rollback on any error

    Example:
        >>> checkpoint_data = {
        ...     "collected_data": {"users": [...], "incidents": [...]},
        ...     "phase_durations": {"data_fetch": 12.5}
        ... }
        >>> await save_checkpoint(db, analysis_id=123, checkpoint=1, checkpoint_data)
    """
    # Validate checkpoint number
    if not 0 <= checkpoint <= 7:
        raise CheckpointError(f"Invalid checkpoint number: {checkpoint}. Must be 0-7")

    # Validate checkpoint data
    validate_checkpoint_data(checkpoint_data)

    try:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id)
            .with_for_update()
            .first()
        )

        if not analysis:
            raise CheckpointError(f"Analysis {analysis_id} not found")

        analysis.last_checkpoint = checkpoint
        analysis.checkpoint_data = checkpoint_data
        analysis.updated_at = datetime.now(timezone.utc)

        db.commit()

        phase_name = get_checkpoint_phase_name(checkpoint)
        logger.info(
            f"Checkpoint saved: analysis_id={analysis_id}, checkpoint={checkpoint} ({phase_name}), "
            f"data_size={len(json.dumps(checkpoint_data))} bytes"
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to save checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Database error saving checkpoint: {e}") from e
    except CheckpointError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error saving checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Failed to save checkpoint: {e}") from e


async def load_checkpoint(
    db: Session,
    analysis_id: int,
) -> Optional[dict[str, Any]]:
    """
    Load checkpoint data from database.

    Args:
        db: Database session
        analysis_id: Analysis ID to load checkpoint for

    Returns:
        Checkpoint data dictionary if exists, None otherwise
        Returns None if analysis has no checkpoint (last_checkpoint is 0 or None)

    Raises:
        CheckpointError: If load fails

    Example:
        >>> checkpoint_data = await load_checkpoint(db, analysis_id=123)
        >>> if checkpoint_data:
        ...     checkpoint_num = checkpoint_data.get("checkpoint")
        ...     users = checkpoint_data.get("collected_data", {}).get("users", [])
    """
    try:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id)
            .first()
        )

        if not analysis:
            raise CheckpointError(f"Analysis {analysis_id} not found")

        if not analysis.last_checkpoint:
            return None

        checkpoint_data = analysis.checkpoint_data or {}

        if "checkpoint" not in checkpoint_data:
            checkpoint_data["checkpoint"] = analysis.last_checkpoint

        phase_name = get_checkpoint_phase_name(analysis.last_checkpoint)
        logger.info(
            f"Checkpoint loaded: analysis_id={analysis_id}, checkpoint={analysis.last_checkpoint} ({phase_name})"
        )

        return checkpoint_data

    except SQLAlchemyError as e:
        logger.error(f"Failed to load checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Database error loading checkpoint: {e}") from e
    except CheckpointError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Failed to load checkpoint: {e}") from e


async def clear_checkpoint(
    db: Session,
    analysis_id: int,
) -> None:
    """
    Clear checkpoint data from analysis.

    Called when analysis completes successfully or fails permanently.
    Frees up database space by removing large checkpoint_data JSON.

    Args:
        db: Database session
        analysis_id: Analysis ID to clear checkpoint for

    Raises:
        CheckpointError: If clear fails
    """
    try:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id)
            .with_for_update()
            .first()
        )

        if not analysis:
            raise CheckpointError(f"Analysis {analysis_id} not found")

        analysis.last_checkpoint = 0
        analysis.checkpoint_data = None

        db.commit()

        logger.info(f"Checkpoint cleared: analysis_id={analysis_id}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to clear checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Database error clearing checkpoint: {e}") from e
    except CheckpointError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error clearing checkpoint for analysis {analysis_id}: {e}")
        raise CheckpointError(f"Failed to clear checkpoint: {e}") from e


def get_checkpoint_phase_name(checkpoint: int) -> str:
    """
    Get human-readable name for checkpoint phase.

    Args:
        checkpoint: Checkpoint number (0-7)

    Returns:
        Phase name string

    Example:
        >>> get_checkpoint_phase_name(1)
        'data_fetch_complete'
        >>> get_checkpoint_phase_name(99)
        'unknown_99'
    """
    return CHECKPOINT_PHASES.get(checkpoint, f"unknown_{checkpoint}")


def should_resume_from_checkpoint(checkpoint: int) -> bool:
    """
    Determine if analysis should resume from checkpoint or restart.

    Some checkpoints are too early to be worth resuming from.

    Args:
        checkpoint: Last completed checkpoint number

    Returns:
        True if should resume, False if should restart from beginning

    Logic:
        - Checkpoint 0 (starting): Restart (no work done)
        - Checkpoint 1+ (data fetched): Resume (significant work done)
    """
    return checkpoint >= 1


__all__ = [
    "save_checkpoint",
    "load_checkpoint",
    "clear_checkpoint",
    "get_checkpoint_phase_name",
    "should_resume_from_checkpoint",
    "CheckpointError",
    "CheckpointDataTooLargeError",
    "CHECKPOINT_PHASES",
]
