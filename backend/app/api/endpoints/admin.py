"""
Admin endpoints for database maintenance and fixes.
"""
import ipaddress
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ...core.rate_limiting import admin_rate_limit
from ...models import Analysis, get_db
from ...models.user import User
from ...services.demo_analysis_service import _get_or_create_demo_organization, _load_health_checkins_for_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# Security Configuration
# ----------------------
# ADMIN_API_KEY: Required for sensitive admin operations.
# Must be at least 32 characters for security. Store in secrets manager (AWS Secrets Manager,
# HashiCorp Vault, etc.) rather than plain environment variables in production.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
MIN_API_KEY_LENGTH = 32

# ADMIN_IP_WHITELIST: Required comma-separated list of allowed IP addresses or CIDR ranges
# Example: "10.0.0.1,192.168.1.0/24,203.0.113.50"
# Must be configured for admin endpoints to function (defense in depth)
ADMIN_IP_WHITELIST = os.getenv("ADMIN_IP_WHITELIST", "").strip()

def _parse_ip_whitelist() -> set:
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

def _is_ip_whitelisted(client_ip: str, whitelist: set) -> bool:
    """Check if client IP is in the whitelist. Supports both exact IPs and CIDR ranges."""
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

def _validate_admin_api_key() -> bool:
    """Validate that ADMIN_API_KEY meets security requirements."""
    if not ADMIN_API_KEY:
        logger.error(
            f"SECURITY: ADMIN_API_KEY is not configured. Admin endpoints will be disabled. "
            f"Set ADMIN_API_KEY env var with at least {MIN_API_KEY_LENGTH} characters."
        )
        return False

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

if _ip_whitelist:
    logger.info(f"SECURITY: Admin IP whitelist enabled with {len(_ip_whitelist)} entries")
else:
    logger.error("SECURITY: ADMIN_IP_WHITELIST is not configured. Admin endpoints will be disabled.")


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

    # Security Layer 1: Validate API key is properly configured
    if not _admin_api_key_valid:
        logger.warning(f"ADMIN AUDIT: Rejected - API key not configured. IP: {client_ip}")
        raise HTTPException(status_code=503, detail="Admin endpoint temporarily unavailable")

    # Security Layer 2: IP whitelist check (if configured)
    if not _is_ip_whitelisted(client_ip, _ip_whitelist):
        logger.warning(f"ADMIN AUDIT: Rejected - IP not whitelisted. IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Forbidden")

    # Security Layer 3: Validate API key with constant-time comparison
    if not secrets.compare_digest(x_admin_api_key or "", ADMIN_API_KEY):
        logger.warning(f"ADMIN AUDIT: Rejected - Invalid API key. IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info(f"ADMIN AUDIT: Authorized access to /refresh-demo-analyses. IP: {client_ip}")

    try:
        # Load mock data
        backend_dir = Path(__file__).parent.parent.parent.parent
        mock_data_path = backend_dir / "mock_analysis_data.json"

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

        # Get all demo analyses
        all_analyses = db.query(Analysis).all()
        demo_analyses = [
            a for a in all_analyses
            if a.config and isinstance(a.config, dict) and a.config.get('is_demo') is True
        ]

        updated_count = 0
        created_count = 0
        checkins_loaded = 0
        errors = []

        # Get or create demo organization for health check-ins
        demo_organization_id = _get_or_create_demo_organization(db)
        logger.info(f"ADMIN: Using demo organization {demo_organization_id}")

        # Update existing demo analyses
        for analysis in demo_analyses:
            try:
                logger.info(f"ADMIN: Updating demo for user #{analysis.user_id} (analysis #{analysis.id})")
                analysis.results = new_results
                analysis.organization_id = demo_organization_id  # Ensure org is set for health check-ins
                config = analysis.config.copy() if analysis.config else {}
                config['demo_updated_at'] = datetime.now().isoformat()
                analysis.config = config
                updated_count += 1
                logger.info(f"ADMIN: Successfully updated demo for user #{analysis.user_id}")
            except Exception as e:
                logger.error(f"ADMIN: Failed to update demo for user #{analysis.user_id}: {str(e)}")
                errors.append(f"Failed to update analysis #{analysis.id}: {str(e)}")

        # Commit updates before creating new ones - prevents rollback from losing updates
        if updated_count > 0:
            db.commit()
            logger.info(f"ADMIN: Committed {updated_count} demo updates")

        # Load health check-ins for users with existing demo analyses
        for analysis in demo_analyses:
            try:
                checkins_result = _load_health_checkins_for_user(db, analysis.user_id, demo_organization_id, mock_data)
                if checkins_result['created'] > 0:
                    checkins_loaded += checkins_result['created']
                    logger.info(f"ADMIN: Loaded {checkins_result['created']} health check-ins for user #{analysis.user_id}")
            except Exception as e:
                logger.warning(f"ADMIN: Failed to load health check-ins for user #{analysis.user_id}: {e}")

        # Create demo analyses for users who don't have one
        users = db.query(User).all()
        users_with_demo = {a.user_id for a in demo_analyses}

        logger.info(f"ADMIN: Found {len(users)} total users, {len(users_with_demo)} already have demos")

        for user in users:
            if user.id not in users_with_demo:
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
                    db.flush()  # Flush immediately to catch per-user errors
                    created_count += 1
                    logger.info(f"ADMIN: Successfully created demo for user #{user.id}")

                    # Load health check-ins for the new user
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
                    db.rollback()  # Rollback this specific failure

        db.commit()

        logger.info(
            f"ADMIN AUDIT: /refresh-demo-analyses completed. "
            f"IP: {client_ip}, Updated: {updated_count}, Created: {created_count}"
        )

        return {
            "status": "success",
            "message": "Demo analyses refreshed successfully",
            "updated_count": updated_count,
            "created_count": created_count,
            "total_demo_analyses": updated_count + created_count,
            "health_checkins_loaded": checkins_loaded,
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
