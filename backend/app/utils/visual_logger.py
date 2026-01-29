"""
Visual logging utilities for analysis progress tracking.

Provides clear, visually distinct markers for analysis steps to improve
debugging and progress tracking in production logs.
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def _calculate_progress(step_num: int, total_steps: int = 7) -> tuple:
    """Calculate progress percentage and ASCII progress bar.

    Args:
        step_num: Current step number (0-7)
        total_steps: Total number of steps (default 7)

    Returns:
        Tuple of (percentage: int, bar: str)
    """
    percentage = int((step_num / total_steps) * 100)
    filled = int(percentage / 5)  # 20 blocks total (5% each)
    bar = "█" * filled + "░" * (20 - filled)
    return percentage, bar


def _generate_feature_badges(features: Dict[str, Any]) -> str:
    """Generate feature status badges.

    Args:
        features: Dictionary of feature flags

    Returns:
        String with feature badges (e.g., "[GitHub✓] [Slack✗]")
    """
    feature_names = {
        'github': 'GitHub',
        'slack': 'Slack',
        'jira': 'Jira',
        'linear': 'Linear',
        'ai': 'AI'
    }

    badges = []
    for key, name in feature_names.items():
        status = "✓" if features.get(key) else "✗"
        badges.append(f"[{name}{status}]")

    return " ".join(badges)


def log_analysis_start(analysis_id: int, platform: str, time_range: int, features: Dict[str, Any]) -> None:
    """Log analysis initialization with clear visual markers.

    Args:
        analysis_id: Unique analysis ID
        platform: Platform name (e.g., 'rootly', 'pagerduty')
        time_range: Time range in days
        features: Dictionary of enabled features
    """
    feature_badges = _generate_feature_badges(features)

    logger.info("═" * 60)
    logger.info("🔥🔥🔥 ANALYSIS START 🔥🔥🔥")
    logger.info("═" * 60)
    logger.info(f"Analysis ID: {analysis_id}")
    logger.info(f"Platform: {platform.upper()}")
    logger.info(f"Time Range: {time_range} days")
    logger.info(f"Features Enabled: {feature_badges}")
    logger.info("═" * 60)


def log_step_header(
    step_num: int,
    step_name: str,
    file_name: str,
    operation: str,
    features: Optional[Dict[str, Any]] = None
) -> None:
    """Log step header with visual separators and progress indicator.

    Args:
        step_num: Step number (1-7)
        step_name: Human-readable step name
        file_name: Name of the file executing this step
        operation: Description of the operation
        features: Optional dictionary of feature flags for badge display
    """
    percentage, bar = _calculate_progress(step_num)
    feature_badges = _generate_feature_badges(features) if features else ""

    logger.info("")
    logger.info("═" * 60)
    logger.info(f"STEP {step_num}/7: {step_name}")
    logger.info("═" * 60)
    logger.info(f"File: {file_name}")
    logger.info(f"Operation: {operation}")

    if feature_badges:
        logger.info(f"Features: {feature_badges}")

    logger.info(f"Progress: [{bar}] {percentage}%")
    logger.info("═" * 60)


def log_step_complete(
    step_num: int,
    step_name: str,
    duration: float,
    stats: Optional[Dict[str, Any]] = None
) -> None:
    """Log step completion with timing and statistics.

    Args:
        step_num: Step number (1-7)
        step_name: Human-readable step name
        duration: Duration in seconds
        stats: Optional dictionary of statistics to display
    """
    logger.info(f"✅ STEP {step_num}/7 COMPLETE: {step_name} ({duration:.2f}s)")

    if stats:
        for key, value in stats.items():
            # Format the value nicely
            if isinstance(value, float):
                logger.info(f"   {key}: {value:.2f}")
            else:
                logger.info(f"   {key}: {value}")


def log_substep(
    substep_name: str,
    file_name: str,
    operation: str,
    status: str = "pending"
) -> None:
    """Log a substep within a major step (e.g., 2a, 2b, 2c).

    Args:
        substep_name: Name of the substep (e.g., "STEP 2a: GitHub Data")
        file_name: Name of the file executing this substep
        operation: Description of the operation
        status: Status indicator (pending, complete, skipped)
    """
    logger.info(f"{substep_name}")
    logger.info(f"File: {file_name}")
    logger.info(f"Operation: {operation}")


def log_substep_complete(
    substep_name: str,
    duration: float,
    stats: Optional[Dict[str, Any]] = None
) -> None:
    """Log a substep completion.

    Args:
        substep_name: Name of the substep
        duration: Duration in seconds
        stats: Optional dictionary of statistics
    """
    logger.info(f"{substep_name} COMPLETE ({duration:.2f}s)")

    if stats:
        for key, value in stats.items():
            if isinstance(value, float):
                logger.info(f"   {key}: {value:.2f}")
            else:
                logger.info(f"   {key}: {value}")


def log_substep_skipped(substep_name: str, reason: str) -> None:
    """Log a substep being skipped.

    Args:
        substep_name: Name of the substep
        reason: Reason for skipping
    """
    logger.info(f"{substep_name} SKIPPED: {reason}")


def log_analysis_complete(
    duration: float,
    team_size: int,
    incidents_count: int,
    health_score: float
) -> None:
    """Log analysis completion with summary statistics.

    Args:
        duration: Total analysis duration in seconds
        team_size: Number of team members analyzed
        incidents_count: Number of incidents processed
        health_score: Overall team health score
    """
    logger.info("")
    logger.info("═" * 60)
    logger.info("🏁 ANALYSIS COMPLETE 🏁")
    logger.info("═" * 60)
    logger.info(f"Total Duration: {duration:.2f}s")
    logger.info(f"Team Members Analyzed: {team_size}")
    logger.info(f"Incidents Processed: {incidents_count}")
    logger.info(f"Overall Health Score: {health_score:.2f}/100")
    logger.info("═" * 60)


def log_analysis_failed(
    duration: float,
    error: str,
    step_num: Optional[int] = None
) -> None:
    """Log analysis failure.

    Args:
        duration: Duration before failure in seconds
        error: Error message
        step_num: Optional step number where failure occurred
    """
    if step_num:
        logger.info("")
        logger.info("═" * 60)
        logger.info(f"💥 STEP {step_num}/7 FAILED")
        logger.info("═" * 60)
    else:
        logger.info("")
        logger.info("═" * 60)
        logger.info("💥 ANALYSIS FAILED")
        logger.info("═" * 60)

    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Error: {error}")
    logger.info("═" * 60)


def log_task_start(
    analysis_id: int,
    node_id: str,
    user_id: int,
    integration_name: str
) -> None:
    """Log background task start.

    Args:
        analysis_id: Unique analysis ID
        node_id: Node/process identifier
        user_id: User ID initiating the analysis
        integration_name: Name of the integration
    """
    logger.info("")
    logger.info("═" * 60)
    logger.info("🔥🔥🔥 BACKGROUND TASK STARTED 🔥🔥🔥")
    logger.info("═" * 60)
    logger.info(f"Analysis ID: {analysis_id}")
    logger.info(f"Node ID: {node_id}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Integration: {integration_name}")
    logger.info("═" * 60)


def log_task_complete(
    analysis_id: int,
    duration: float,
    status: str = "completed",
    result_size: int = 0
) -> None:
    """Log background task completion.

    Args:
        analysis_id: Unique analysis ID
        duration: Total task duration in seconds
        status: Status (completed, failed, timeout)
        result_size: Size of results in bytes
    """
    result_size_kb = result_size / 1024 if result_size > 0 else 0

    logger.info("")
    logger.info("═" * 60)
    logger.info(f"✅ BACKGROUND TASK {status.upper()}")
    logger.info("═" * 60)
    logger.info(f"Analysis ID: {analysis_id}")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Result Size: {result_size_kb:.1f} KB")
    logger.info("═" * 60)
