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
from ..models.user_burnout_report import UserBurnoutReport
from ..models.organization import Organization
from ..models.user_correlation import UserCorrelation

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


def _get_or_create_demo_organization(db: Session) -> int:
    """
    Get or create a default organization for demo analyses.

    This ensures all demo analyses have an organization_id so that
    survey data can be queried (team members are linked via organization).

    Returns:
        int: Organization ID for demo data
    """
    try:
        # Try to find existing demo organization
        org = db.query(Organization).filter(
            Organization.name == "Demo Organization"
        ).first()

        if org:
            logger.debug(f"Using existing demo organization {org.id}")
            return org.id

        # Create a new demo organization if it doesn't exist
        # Generate a unique slug for the domain
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        domain = f"demo-{unique_id}.local"
        slug = f"demo-{unique_id}"

        org = Organization(
            name="Demo Organization",
            domain=domain,  # Required NOT NULL field
            slug=slug,  # Unique identifier
            plan_type="free",
            max_users=50,
            max_analyses_per_month=5,
            status="active"
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        logger.info(f"Created demo organization {org.id} with domain {domain}")
        return org.id

    except Exception as e:
        logger.warning(f"Failed to get/create demo organization: {e}")
        # Rollback to clear the pending transaction
        try:
            db.rollback()
        except:
            pass

        # Fallback: try to use the first organization
        try:
            org = db.query(Organization).first()
            if org:
                logger.info(f"Using first available organization {org.id}")
                return org.id
        except Exception as fallback_error:
            logger.warning(f"Failed to get first organization: {fallback_error}")

        # If all else fails, return 1 (may not exist, but at least it's consistent)
        logger.warning("No organization available for demo analysis")
        return 1


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


def _load_health_checkins_for_user(db: Session, user_id: int, organization_id: int, mock_data: dict) -> int:
    """
    Load health check-in records from mock data for a user.

    This loads the user_burnout_reports from the mock data JSON
    and creates them in the database linked to the user.
    Also creates UserCorrelation records for team members in the organization.

    Args:
        db: Database session
        user_id: User ID to link reports to
        organization_id: Organization ID for team member correlations
        mock_data: Mock analysis data containing user_burnout_reports

    Returns:
        int: Number of health check-in records loaded
    """
    try:
        reports_data = mock_data.get('user_burnout_reports', [])

        if not reports_data:
            logger.debug(f"No health check-in data found in mock data for user {user_id}")
            return 0

        logger.info(f"Loading {len(reports_data)} health check-in records for user {user_id}")

        created_count = 0

        # First, ensure team members exist in UserCorrelation for this organization
        logger.info(f"Creating UserCorrelation records for {len(reports_data)} team members")
        for report_data in reports_data:
            email = report_data.get('email', '')
            if not email:
                continue

            try:
                # Check if UserCorrelation already exists
                existing = db.query(UserCorrelation).filter(
                    UserCorrelation.organization_id == organization_id,
                    UserCorrelation.email == email
                ).first()

                if not existing:
                    # Create UserCorrelation record for team member
                    correlation = UserCorrelation(
                        organization_id=organization_id,
                        email=email,
                        # Other fields can be set if needed
                    )
                    db.add(correlation)
            except Exception as e:
                logger.warning(f"Failed to create UserCorrelation for {email}: {e}")
                continue

        # Commit UserCorrelations before creating reports
        try:
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to commit UserCorrelations: {e}")
            db.rollback()

        # Load each burnout report
        for report_data in reports_data:
            email = report_data.get('email', '')

            if not email:
                logger.warning(f"Skipping health check-in record with missing email")
                continue

            try:
                # Parse timestamps from exported data
                submitted_at = report_data.get('submitted_at')
                if isinstance(submitted_at, str):
                    # Parse ISO format datetime string
                    submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))

                # ✅ DEDUPLICATION CHECK: Prevent duplicate reports when multiple users sign up
                # Reports are organization-scoped (all demo users share the same team member data)
                existing_report = db.query(UserBurnoutReport).filter(
                    UserBurnoutReport.organization_id == organization_id,
                    UserBurnoutReport.email == email,
                    UserBurnoutReport.submitted_at == submitted_at
                ).first()

                if existing_report:
                    logger.debug(f"Report for {email} at {submitted_at} already exists in organization {organization_id}, skipping")
                    continue  # Skip duplicate

                # Create burnout report linked to the user (only if it doesn't exist)
                report = UserBurnoutReport(
                    user_id=user_id,  # Link to the user (first user who loaded it)
                    organization_id=organization_id,  # Organization-scoped data
                    email=email,
                    email_domain=report_data.get('email_domain'),
                    analysis_id=None,  # Not linked to specific analysis
                    feeling_score=report_data.get('feeling_score'),
                    workload_score=report_data.get('workload_score'),
                    stress_factors=report_data.get('stress_factors'),
                    personal_circumstances=report_data.get('personal_circumstances'),
                    additional_comments=report_data.get('additional_comments'),
                    submitted_via=report_data.get('submitted_via', 'web'),
                    is_anonymous=report_data.get('is_anonymous', False),
                    submitted_at=submitted_at  # Preserve timestamp
                )
                db.add(report)
                created_count += 1

            except Exception as e:
                logger.warning(f"Failed to load health check-in for {email}: {e}")
                # Continue loading other records even if one fails
                continue

        logger.info(f"Successfully loaded {created_count} health check-in records for user {user_id}")
        return created_count

    except Exception as e:
        logger.error(f"Failed to load health check-ins for user {user_id}: {e}", exc_info=True)
        # Don't fail - return 0 and let registration continue
        return 0


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

        # Get or create an organization for the demo analysis
        # This ensures survey data can be fetched (requires organization_id)
        organization_id = _get_or_create_demo_organization(db)

        # Assign user to the demo organization
        # This ensures the API query succeeds: organization_id == organization_id
        # Previously, new OAuth users had organization_id=NULL, causing 404 errors
        user.organization_id = organization_id
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Assigned user {user.id} to demo organization {organization_id}")

        # Create the demo analysis
        analysis = Analysis(
            user_id=user.id,
            organization_id=organization_id,  # Use demo organization for survey data
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

        # Load health check-in data (burnout reports) for the user
        try:
            checkins_loaded = _load_health_checkins_for_user(db, user.id, organization_id, mock_data)
            if checkins_loaded > 0:
                db.commit()
                logger.info(
                    f"Loaded {checkins_loaded} health check-in records for user {user.id}"
                )
        except Exception as e:
            logger.warning(f"Failed to load health check-ins for user {user.id}: {e}")
            # Don't fail the entire operation if health check-ins fail
            try:
                db.rollback()
            except:
                pass

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
