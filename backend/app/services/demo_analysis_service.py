"""
Demo Analysis Service

Automatically creates a demo analysis for new users so they can explore
the dashboard and see example burnout analysis data without setting up integrations.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.analysis import Analysis

logger = logging.getLogger(__name__)

# Cache for mock data to avoid loading 7.4MB JSON file on every user signup
_MOCK_DATA_CACHE: Optional[dict] = None


def _load_mock_data() -> dict:
    """
    Load mock analysis data from JSON file with caching.

    Returns:
        dict: Mock analysis data
    """
    global _MOCK_DATA_CACHE

    if _MOCK_DATA_CACHE is not None:
        logger.debug("Using cached mock analysis data")
        return _MOCK_DATA_CACHE

    try:
        # Navigate to backend directory from services directory
        backend_dir = Path(__file__).parent.parent.parent
        mock_data_path = backend_dir / "mock_analysis_data.json"

        logger.info(f"Loading mock analysis data from: {mock_data_path}")

        if not mock_data_path.exists():
            logger.error(f"Mock data file not found: {mock_data_path}")
            raise FileNotFoundError(f"Mock data file not found: {mock_data_path}")

        with open(mock_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Cache the data
        _MOCK_DATA_CACHE = data
        logger.info("Mock analysis data loaded and cached successfully")

        return data

    except Exception as e:
        logger.error(f"Failed to load mock analysis data: {e}")
        raise


def _has_demo_analysis(db: Session, user_id: int) -> bool:
    """
    Check if user already has a demo analysis.

    Args:
        db: Database session
        user_id: User ID to check

    Returns:
        bool: True if user has a demo analysis, False otherwise
    """
    user_analyses = db.query(Analysis).filter(
        Analysis.user_id == user_id
    ).all()

    for analysis in user_analyses:
        if analysis.config and isinstance(analysis.config, dict):
            if analysis.config.get('is_demo') is True:
                return True

    return False


def create_demo_analysis_for_new_user(db: Session, user: User) -> bool:
    """
    Create a demo analysis for a newly registered user.

    This function is called automatically when a new user signs up via OAuth.
    It creates a completed analysis with sample data so users can explore
    the dashboard features before setting up their own integrations.

    Args:
        db: Database session
        user: Newly created User object (must have valid user.id)

    Returns:
        bool: True if demo analysis was created successfully, False otherwise

    Note:
        This function handles its own errors and will not raise exceptions.
        If demo creation fails, it logs the error and returns False, allowing
        the user registration flow to continue normally.
    """
    try:
        logger.info(f"Creating demo analysis for new user {user.id} ({user.email})")

        # Safety check: ensure user already has demo
        if _has_demo_analysis(db, user.id):
            logger.warning(f"User {user.id} already has a demo analysis, skipping")
            return False

        # Load mock data (from cache if available)
        mock_data = _load_mock_data()
        original_analysis = mock_data['analysis']

        # Prepare config with demo marker
        config = original_analysis.get('config', {}).copy()
        config['is_demo'] = True
        config['demo_created_at'] = datetime.now().isoformat()
        config['demo_note'] = 'This is a sample analysis to help you explore the platform'

        # Create the demo analysis
        analysis = Analysis(
            user_id=user.id,
            organization_id=user.organization_id if hasattr(user, 'organization_id') else None,
            rootly_integration_id=None,  # Demo doesn't need real integration
            integration_name="Demo Analysis",
            platform=original_analysis.get('platform', 'pagerduty'),
            time_range=original_analysis.get('time_range', 30),
            status="completed",
            config=config,
            results=original_analysis.get('results'),
            error_message=None,
            completed_at=datetime.now()
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        logger.info(
            f"Successfully created demo analysis {analysis.id} for user {user.id}. "
            f"UUID: {analysis.uuid}"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to create demo analysis for user {user.id}: {e}", exc_info=True)

        # Rollback to prevent any partial changes
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback demo analysis transaction: {rollback_error}")

        # Don't raise - allow user registration to continue
        return False


def clear_mock_data_cache():
    """
    Clear the cached mock data.

    This is useful for testing or if the mock data file is updated.
    """
    global _MOCK_DATA_CACHE
    _MOCK_DATA_CACHE = None
    logger.info("Mock data cache cleared")
