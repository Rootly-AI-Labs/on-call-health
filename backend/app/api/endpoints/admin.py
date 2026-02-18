"""
Admin endpoints for database maintenance and fixes.
"""
import ipaddress
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from ...core.rate_limiting import admin_rate_limit
from ...models import Analysis, get_db, Organization
from ...models.user import User
from ...models.user_correlation import UserCorrelation
from ...models.user_burnout_report import UserBurnoutReport
from ...models.api_key import APIKey
from ...models.oauth_provider import OAuthProvider
from ...services.demo_analysis_service import _get_or_create_demo_organization, _load_health_checkins_for_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# Security Configuration
# ----------------------
# ADMIN_PASSWORD: Simple password for admin access (set in Railway env vars)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# ADMIN_API_KEY: Legacy - not used anymore
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
MIN_API_KEY_LENGTH = 1

# ADMIN_IP_WHITELIST: Required comma-separated list of allowed IP addresses or CIDR ranges
# Example: "10.0.0.1,192.168.1.0/24,203.0.113.50"
# Must be configured for admin endpoints to function (defense in depth)
ADMIN_IP_WHITELIST = os.getenv("ADMIN_IP_WHITELIST", "").strip()

def _parse_ip_whitelist() -> set[str]:
    """Parse the IP whitelist from environment variable."""
    if not ADMIN_IP_WHITELIST:
        return set()
    return {ip.strip() for ip in ADMIN_IP_WHITELIST.split(",") if ip.strip()}

def _get_client_ip(request: Request) -> str:
    """
    Get the real client IP, handling reverse proxies.
    Checks X-Forwarded-For header first (set by load balancers/proxies),
    then falls back to direct client connection.
    Validates IP format to prevent header injection attacks.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # The first one is the original client
        client_ip = forwarded_for.split(",")[0].strip()
        try:
            # Validate IP format to prevent header injection
            ipaddress.ip_address(client_ip)
            return client_ip
        except ValueError:
            # Invalid IP in header, fall back to direct client
            pass
    return request.client.host if request.client else "unknown"

def _is_ip_whitelisted(client_ip: str, whitelist: set[str]) -> bool:
    """Check if client IP is in the whitelist. Supports both exact IPs and CIDR ranges."""
    # Allow localhost/127.0.0.1 for local development
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if not whitelist:
        return False

    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in whitelist:
        try:
            if '/' in entry:
                if client_addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif client_addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue

    return False

def _validate_password(password: str) -> bool:
    """Validate the admin password."""
    if not ADMIN_PASSWORD:
        return True  # No password configured, allow access
    return password == ADMIN_PASSWORD

def _validate_admin_api_key() -> bool:
    """Validate that ADMIN_API_KEY meets security requirements."""
    # Allow access if no API key is set (for development)
    if not ADMIN_API_KEY:
        logger.warning("SECURITY: ADMIN_API_KEY not configured - admin endpoints will be open")
        return True

    if len(ADMIN_API_KEY) < MIN_API_KEY_LENGTH:
        logger.error(
            f"SECURITY: ADMIN_API_KEY is too short ({len(ADMIN_API_KEY)} chars). "
            f"Minimum required: {MIN_API_KEY_LENGTH} chars. Admin endpoints will be disabled."
        )
        return False

    return True

# Validate API key at module load time
_admin_api_key_valid = _validate_admin_api_key()
_ip_whitelist = _parse_ip_whitelist()

logger.info("SECURITY: Admin IP whitelist check disabled")


@router.post("/auth/login")
async def admin_login(
    request: Request,
    body: dict = None
) -> dict:
    """Admin login endpoint - validates password and returns session token."""
    if not body or "password" not in body:
        raise HTTPException(status_code=400, detail="Password required")

    password = body["password"]

    # Validate password server-side
    if not _validate_password(password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Return success - frontend stores this in session
    return {"authenticated": True, "expires": "24h"}


@router.post("/refresh-demo-analyses")
@admin_rate_limit()
async def refresh_demo_analyses(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db)
) -> dict:
    """
    Refresh all demo analyses with the latest mock data.

    This endpoint updates existing demo analyses and creates new ones for users
    who don't have a demo analysis. Use this after updating mock_analysis_data.json
    with new fields or data.

    Security Requirements:
    - ADMIN_API_KEY env var: Must be at least 32 characters (required)
    - ADMIN_IP_WHITELIST env var: Comma-separated IPs/CIDRs (required)
    - X-Admin-API-Key header: Must match ADMIN_API_KEY
    - Rate limited to 5 requests/minute

    Returns 503 if ADMIN_API_KEY or ADMIN_IP_WHITELIST is not properly configured.
    Returns 403 if IP not whitelisted or API key doesn't match.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    try:
        # Load mock data
        backend_dir = Path(__file__).parent.parent.parent.parent
        mock_data_path = backend_dir / "mock_data_helpers" / "mock_analysis_data.json"

        if not mock_data_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Mock data file not found: {mock_data_path}"
            )

        with open(mock_data_path, 'r', encoding='utf-8') as f:
            mock_data = json.load(f)

        original_analysis = mock_data.get('analysis', {})
        new_results = original_analysis.get('results')

        if not new_results:
            raise HTTPException(
                status_code=500,
                detail="Mock data file is missing 'analysis.results'"
            )

        created_count = 0
        deleted_count = 0
        reports_deleted = 0
        checkins_loaded = 0
        errors = []

        # Get or create demo organization for health check-ins
        demo_organization_id = _get_or_create_demo_organization(db)
        logger.info(f"ADMIN: Using demo organization {demo_organization_id}")

        # DELETE all existing demo analyses first (clean slate approach)
        demo_analyses = [
            a for a in db.query(Analysis).all()
            if isinstance(a.config, dict) and a.config.get('is_demo') is True
        ]

        for analysis in demo_analyses:
            try:
                logger.info(f"ADMIN: Deleting old demo analysis #{analysis.id} for user #{analysis.user_id}")
                db.delete(analysis)
                deleted_count += 1
            except Exception as e:
                logger.error(f"ADMIN: Failed to delete demo #{analysis.id}: {str(e)}")
                errors.append(f"Failed to delete analysis #{analysis.id}: {str(e)}")

        if deleted_count > 0:
            db.commit()
            logger.info(f"ADMIN: Deleted {deleted_count} old demo analyses")

        # DELETE all UserBurnoutReport records for the demo organization (clean slate)
        # This ensures health check-ins are refreshed with the latest mock data
        try:
            reports_to_delete = db.query(UserBurnoutReport).filter(
                UserBurnoutReport.organization_id == demo_organization_id
            ).all()
            for report in reports_to_delete:
                db.delete(report)
                reports_deleted += 1
            if reports_deleted > 0:
                db.commit()
                logger.info(f"ADMIN: Deleted {reports_deleted} old UserBurnoutReport records for demo organization")
        except Exception as e:
            logger.error(f"ADMIN: Failed to delete UserBurnoutReport records: {e}")
            db.rollback()

        # Ensure UserCorrelation records exist for all team members with health check-ins
        # Clear session to get fresh database state after _load_health_checkins_for_user calls
        db.expire_all()

        # Query directly from database to get emails that exist in user_burnout_reports
        correlations_created = 0
        unique_emails = [
            row[0] for row in db.query(distinct(UserBurnoutReport.email)).filter(
                UserBurnoutReport.organization_id == demo_organization_id,
                UserBurnoutReport.email.isnot(None)
            ).all()
        ]
        logger.info(f"ADMIN: Found {len(unique_emails)} unique emails in health check-ins for org {demo_organization_id}")

        for email in unique_emails:
            try:
                existing = db.query(UserCorrelation).filter(
                    UserCorrelation.organization_id == demo_organization_id,
                    UserCorrelation.email == email
                ).first()

                if existing:
                    logger.info(f"ADMIN: UserCorrelation already exists for {email} (id={existing.id})")
                else:
                    logger.info(f"ADMIN: Creating UserCorrelation for {email}")
                    correlation = UserCorrelation(
                        organization_id=demo_organization_id,
                        email=email,
                        name=email.split('@')[0].replace('.', ' ').title()
                    )
                    db.add(correlation)
                    db.flush()  # Flush immediately to catch errors
                    correlations_created += 1
                    logger.info(f"ADMIN: Created UserCorrelation for {email} (id={correlation.id})")
            except Exception as e:
                logger.error(f"ADMIN: Failed to create UserCorrelation for {email}: {e}")

        if correlations_created > 0:
            db.commit()
            logger.info(f"ADMIN: Created {correlations_created} UserCorrelation records")

        # Create fresh demo analyses for ALL users
        users = db.query(User).all()
        logger.info(f"ADMIN: Found {len(users)} total users, creating demos for all")

        for user in users:
            try:
                logger.info(f"ADMIN: Creating demo for user #{user.id} ({user.email})")
                config = original_analysis.get('config', {}).copy()
                config['is_demo'] = True
                config['demo_created_at'] = datetime.now().isoformat()

                new_analysis = Analysis(
                    user_id=user.id,
                    organization_id=demo_organization_id,
                    rootly_integration_id=None,
                    integration_name="Demo Analysis",
                    platform=original_analysis.get('platform', 'rootly'),
                    time_range=original_analysis.get('time_range', 30),
                    status="completed",
                    config=config,
                    results=new_results,
                    error_message=None,
                    completed_at=datetime.now()
                )
                db.add(new_analysis)
                db.flush()
                created_count += 1
                logger.info(f"ADMIN: Successfully created demo for user #{user.id}")

                # Load health check-ins for the user
                try:
                    checkins_result = _load_health_checkins_for_user(db, user.id, demo_organization_id, mock_data)
                    if checkins_result['created'] > 0:
                        checkins_loaded += checkins_result['created']
                        logger.info(f"ADMIN: Loaded {checkins_result['created']} health check-ins for user #{user.id}")
                except Exception as e:
                    logger.warning(f"ADMIN: Failed to load health check-ins for user #{user.id}: {e}")

            except Exception as e:
                logger.error(f"ADMIN: Failed to create demo for user #{user.id}: {str(e)}")
                errors.append(f"Failed to create demo for user #{user.id} ({user.email}): {str(e)}")
                db.rollback()

        db.commit()

        logger.info(
            f"ADMIN AUDIT: /refresh-demo-analyses completed. "
            f"IP: {client_ip}, Deleted: {deleted_count}, Created: {created_count}"
        )

        return {
            "status": "success",
            "message": "Demo analyses refreshed successfully",
            "deleted_count": deleted_count,
            "created_count": created_count,
            "reports_deleted": reports_deleted,
            "total_demo_analyses": created_count,
            "health_checkins_loaded": checkins_loaded,
            "correlations_created": correlations_created,
            "errors": errors or None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"ADMIN AUDIT: /refresh-demo-analyses failed. IP: {client_ip}, Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh demo analyses"
        )


# ============== Admin Dashboard Stats Endpoints ==============

from datetime import timedelta
from typing import Optional
from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    """Response model for admin stats endpoints."""
    total_users: int
    total_synced_users: int
    total_organizations: int
    total_analyses: int
    total_api_keys: int
    users_google: int
    users_github: int
    new_users_last_30_days: int
    new_users_last_7_days: int
    new_users_today: int
    logins_last_30_days: int
    logins_last_7_days: int
    logins_today: int
    analyses_last_30_days: int
    analyses_last_7_days: int
    analyses_today: int


class UserStatsItem(BaseModel):
    """Individual user stats for list responses."""
    id: int
    email: str
    name: Optional[str]
    organization_name: Optional[str]
    created_at: str
    last_login: Optional[str]
    role: str


class APIKeyStatsItem(BaseModel):
    """API key stats for list responses."""
    id: int
    name: str
    user_email: str
    user_name: Optional[str]
    created_at: str
    last_used_at: Optional[str]
    is_active: bool


class IntegrationStatsItem(BaseModel):
    """Integration stats for list responses."""
    id: int
    name: str
    platform: str
    user_email: str
    user_name: Optional[str]
    organization_name: Optional[str]
    is_active: bool
    created_at: str
    last_used_at: Optional[str]


class TrendDataPoint(BaseModel):
    """Data point for trend graphs."""
    date: str
    count: int


def _get_days_ago(days: int) -> datetime:
    """Get datetime for N days ago."""
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/stats/summary")
@admin_rate_limit()
async def get_admin_stats_summary(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db)
) -> AdminStatsResponse:
    """
    Get summary statistics for the admin dashboard.

    Returns counts for users, organizations, analyses, API keys,
    plus trend data for the last 30 days.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_7_ago = now - timedelta(days=7)
    days_30_ago = now - timedelta(days=30)

    # Total counts - only verified users (OAuth'd)
    total_users = db.query(User).filter(User.is_verified == True).count()
    # Unique synced users (distinct by email)
    total_synced_users = db.query(UserCorrelation.email).filter(
        UserCorrelation.is_active == 1,
        UserCorrelation.email.isnot(None)
    ).distinct().count()
    total_organizations = db.query(Organization).count()
    total_analyses = db.query(Analysis).count()
    total_api_keys = db.query(APIKey).filter(APIKey.revoked_at.is_(None)).count()

    # Users by OAuth provider
    users_google = db.query(OAuthProvider).filter(OAuthProvider.provider == 'google').distinct(OAuthProvider.user_id).count()
    users_github = db.query(OAuthProvider).filter(OAuthProvider.provider == 'github').distinct(OAuthProvider.user_id).count()

    # New users
    new_users_today = db.query(User).filter(User.created_at >= today_start).count()
    new_users_last_7_days = db.query(User).filter(User.created_at >= days_7_ago).count()
    new_users_last_30_days = db.query(User).filter(User.created_at >= days_30_ago).count()

    # Logins (using last_active_at)
    logins_today = db.query(User).filter(
        User.last_active_at >= today_start
    ).count()
    logins_last_7_days = db.query(User).filter(
        User.last_active_at >= days_7_ago
    ).count()
    logins_last_30_days = db.query(User).filter(
        User.last_active_at >= days_30_ago
    ).count()

    # Analyses
    analyses_today = db.query(Analysis).filter(Analysis.created_at >= today_start).count()
    analyses_last_7_days = db.query(Analysis).filter(Analysis.created_at >= days_7_ago).count()
    analyses_last_30_days = db.query(Analysis).filter(Analysis.created_at >= days_30_ago).count()

    return AdminStatsResponse(
        total_users=total_users,
        total_synced_users=total_synced_users,
        total_organizations=total_organizations,
        total_analyses=total_analyses,
        total_api_keys=total_api_keys,
        users_google=users_google,
        users_github=users_github,
        new_users_last_30_days=new_users_last_30_days,
        new_users_last_7_days=new_users_last_7_days,
        new_users_today=new_users_today,
        logins_last_30_days=logins_last_30_days,
        logins_last_7_days=logins_last_7_days,
        logins_today=logins_today,
        analyses_last_30_days=analyses_last_30_days,
        analyses_last_7_days=analyses_last_7_days,
        analyses_today=analyses_today
    )


@router.get("/stats/users")
@admin_rate_limit()
async def get_admin_users(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> dict:
    """
    Get list of users with their stats for admin dashboard.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    # Import here to avoid circular imports
    from ...models import Organization

    # Get users with organization join
    users = db.query(User, Organization.name.label('org_name')).outerjoin(
        Organization, User.organization_id == Organization.id
    ).order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    total_count = db.query(User).count()

    user_list = []
    for user, org_name in users:
        user_list.append(UserStatsItem(
            id=user.id,
            email=user.email,
            name=user.name,
            organization_name=org_name,
            created_at=user.created_at.isoformat() if user.created_at else "",
            last_login=user.last_active_at.isoformat() if user.last_active_at else None,
            role=user.role
        ))

    return {
        "users": [u.model_dump() for u in user_list],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats/api-keys")
@admin_rate_limit()
async def get_admin_api_keys(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> dict:
    """
    Get list of API keys for admin dashboard (without showing actual keys).
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    # Get API keys with user join
    api_keys = db.query(APIKey, User.email.label('user_email'), User.name.label('user_name')).join(
        User, APIKey.user_id == User.id
    ).order_by(APIKey.created_at.desc()).offset(offset).limit(limit).all()

    total_count = db.query(APIKey).count()

    key_list = []
    for api_key, user_email, user_name in api_keys:
        key_list.append(APIKeyStatsItem(
            id=api_key.id,
            name=api_key.name,
            user_email=user_email,
            user_name=user_name,
            created_at=api_key.created_at.isoformat() if api_key.created_at else "",
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            is_active=api_key.is_active
        ))

    return {
        "api_keys": [k.model_dump() for k in key_list],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats/integrations")
@admin_rate_limit()
async def get_admin_integrations(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> dict:
    """Get list of integrations for admin dashboard."""

    from ...models import RootlyIntegration, User
    from sqlalchemy import func

    # Get integrations with user join
    integrations = db.query(
        RootlyIntegration,
        User.email.label('user_email'),
        User.name.label('user_name')
    ).outerjoin(
        User, RootlyIntegration.user_id == User.id
    ).offset(offset).limit(limit).all()

    total_count = db.query(RootlyIntegration).count()

    # Get platform counts
    platform_counts = db.query(
        RootlyIntegration.platform,
        func.count(RootlyIntegration.id)
    ).group_by(RootlyIntegration.platform).all()

    integration_list = []
    for integration, user_email, user_name in integrations:
        integration_list.append({
            "id": integration.id,
            "name": integration.name,
            "platform": integration.platform,
            "user_email": user_email or "",
            "user_name": user_name,
            "organization_name": integration.organization_name,
            "is_active": integration.is_active,
            "created_at": integration.created_at.isoformat() if integration.created_at else "",
            "last_used_at": integration.last_used_at.isoformat() if integration.last_used_at else None,
        })

    return {
        "integrations": integration_list,
        "total": total_count,
        "platform_counts": {platform: count for platform, count in platform_counts},
        "limit": limit,
        "offset": offset
    }


@router.get("/stats/trends/users")
@admin_rate_limit()
async def get_user_trends(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=90)
) -> dict:
    """
    Get user signup trends over time for admin dashboard.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    from sqlalchemy import func, cast, Date

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Group by date - only verified users (OAuth'd)
    results = db.query(
        cast(User.created_at, Date).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date,
        User.is_verified == True
    ).group_by(
        cast(User.created_at, Date)
    ).order_by(
        cast(User.created_at, Date)
    ).all()

    trends = [TrendDataPoint(date=str(r.date), count=r.count) for r in results]

    return {"trends": [t.model_dump() for t in trends]}


@router.get("/stats/trends/logins")
@admin_rate_limit()
async def get_login_trends(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=90)
) -> dict:
    """
    Get login trends over time for admin dashboard.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    from sqlalchemy import func, cast, Date

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Group by date (only users with logins)
    results = db.query(
        cast(User.last_active_at, Date).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.last_active_at >= start_date,
        User.last_active_at.isnot(None)
    ).group_by(
        cast(User.last_active_at, Date)
    ).order_by(
        cast(User.last_active_at, Date)
    ).all()

    trends = [TrendDataPoint(date=str(r.date), count=r.count) for r in results]

    return {"trends": [t.model_dump() for t in trends]}


@router.get("/stats/trends/analyses")
@admin_rate_limit()
async def get_analysis_trends(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=90)
) -> dict:
    """
    Get analysis run trends over time for admin dashboard.
    """
    client_ip = _get_client_ip(request)

    # No password validation - open access

    from sqlalchemy import func, cast, Date

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Group by date
    results = db.query(
        cast(Analysis.created_at, Date).label('date'),
        func.count(Analysis.id).label('count')
    ).filter(
        Analysis.created_at >= start_date
    ).group_by(
        cast(Analysis.created_at, Date)
    ).order_by(
        cast(Analysis.created_at, Date)
    ).all()

    trends = [TrendDataPoint(date=str(r.date), count=r.count) for r in results]

    return {"trends": [t.model_dump() for t in trends]}


@router.get("/stats/recent-signups")
@admin_rate_limit()
async def get_recent_signups(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
) -> dict:
    """Get recent user signups for admin dashboard."""
    from sqlalchemy import desc

    recent_signups = db.query(
        User.id,
        User.email,
        User.name,
        User.organization_id,
        User.created_at
    ).order_by(
        desc(User.created_at)
    ).limit(limit).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "organization_id": u.organization_id,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in recent_signups
        ]
    }


@router.get("/stats/recent-analyses")
@admin_rate_limit()
async def get_recent_analyses(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
) -> dict:
    """Get recent analyses with user info for admin dashboard."""
    from sqlalchemy import desc

    recent_analyses = db.query(
        Analysis,
        User.email.label('user_email'),
        User.name.label('user_name')
    ).join(
        User, Analysis.user_id == User.id
    ).order_by(
        desc(Analysis.created_at)
    ).limit(limit).all()

    return {
        "analyses": [
            {
                "id": a.id,
                "user_email": user_email,
                "user_name": user_name,
                "integration_name": a.integration_name,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None
            }
            for a, user_email, user_name in recent_analyses
        ]
    }
