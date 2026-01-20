"""
PagerDuty integration API endpoints.
"""

import asyncio
from datetime import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ...models import get_db, User
from ...models.rootly_integration import RootlyIntegration
from ...auth.dependencies import get_current_active_user
from ...core.pagerduty_client import PagerDutyAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory cache for permission checks (key: integration_id, value: {permissions, timestamp})
_permissions_cache = {}
PERMISSIONS_CACHE_TTL = 60  # Cache for 60 seconds

def get_cached_permissions(integration_id: int) -> Optional[dict]:
    """Get cached permissions if still valid."""
    if integration_id not in _permissions_cache:
        return None

    cached = _permissions_cache[integration_id]
    cache_age = (datetime.now() - cached['timestamp']).total_seconds()

    if cache_age > PERMISSIONS_CACHE_TTL:
        del _permissions_cache[integration_id]
        return None

    logger.info(f"Using cached PagerDuty permissions for integration {integration_id} (age: {cache_age:.1f}s)")
    return cached['permissions']


def set_cached_permissions(integration_id: int, permissions: dict) -> None:
    """Cache permissions for an integration."""
    _permissions_cache[integration_id] = {
        'permissions': permissions,
        'timestamp': datetime.now()
    }
    logger.info(f"Cached PagerDuty permissions for integration {integration_id}")

class TokenTestRequest(BaseModel):
    token: str

class TokenTestResponse(BaseModel):
    valid: bool
    account_info: Optional[dict] = None
    error: Optional[str] = None

class AddIntegrationRequest(BaseModel):
    token: str
    name: Optional[str] = None
    platform: str = "pagerduty"

class IntegrationResponse(BaseModel):
    id: int
    name: str
    organization_name: str
    total_users: int
    total_services: Optional[int] = None
    is_default: bool
    created_at: str
    last_used_at: Optional[str] = None
    token_suffix: str
    platform: str

class UpdateIntegrationRequest(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None

@router.post("/token/test", response_model=TokenTestResponse)
async def test_pagerduty_token(
    request: TokenTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Test a PagerDuty API token and get account information."""
    client = PagerDutyAPIClient(request.token)
    result = await client.test_connection()

    if not result["valid"]:
        # Map error codes to user-friendly messages with actionable guidance
        error_code = result.get("error_code")
        error_details = {
            "error_code": error_code,
            "technical_message": result.get("error", "Unknown error")
        }

        # Determine appropriate HTTP status code and user message
        if error_code == "UNAUTHORIZED":
            status_code = status.HTTP_401_UNAUTHORIZED
            user_message = "Invalid PagerDuty API token"
            user_guidance = "Please verify that:\n• Your token is a valid PagerDuty API token\n• The token hasn't been revoked in PagerDuty\n• You copied the entire token without extra spaces"
        elif error_code == "FORBIDDEN":
            status_code = status.HTTP_403_FORBIDDEN
            user_message = "PagerDuty API token lacks required permissions"
            user_guidance = "The token needs read access to users and incidents. Please use a token with sufficient permissions."
        elif error_code == "NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
            user_message = "Cannot connect to PagerDuty API"
            user_guidance = "This may indicate:\n• The API endpoint is incorrect\n• Your token doesn't have access to the users endpoint"
        elif error_code == "CONNECTION_ERROR":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            user_message = "Cannot reach PagerDuty servers"
            user_guidance = "Please check:\n• Your internet connection is working\n• api.pagerduty.com is accessible from your network\n• Your firewall/proxy isn't blocking the connection"
        elif error_code == "API_ERROR":
            status_code = status.HTTP_502_BAD_GATEWAY
            user_message = "PagerDuty API returned an error"
            user_guidance = "The PagerDuty API is experiencing issues. Please try again in a few moments."
        else:  # UNKNOWN_ERROR or other
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            user_message = "Unexpected error connecting to PagerDuty"
            user_guidance = "An unexpected error occurred. Please contact support if this persists."

        error_details["user_message"] = user_message
        error_details["user_guidance"] = user_guidance

        raise HTTPException(
            status_code=status_code,
            detail=error_details
        )

    # Check if this organization is already connected
    org_name = result["account_info"]["organization_name"]
    logger.info(f"PagerDuty organization: {org_name}")

    # Get all existing integrations for debugging
    all_existing = db.query(RootlyIntegration).filter(
        RootlyIntegration.user_id == current_user.id
    ).all()
    logger.debug(f"Existing integrations: {len(all_existing)} found for user {current_user.id}")

    existing = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.organization_name == org_name,
            RootlyIntegration.platform == "pagerduty"
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This PagerDuty account is already connected",
                "existing_integration": existing.name
            }
        )

    # Generate suggested name (avoid duplicates like Rootly does)
    existing_names = [
        integration.name for integration in
        db.query(RootlyIntegration).filter(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.platform == "pagerduty"
        ).all()
    ]

    # Format: "PagerDuty - Organization Name"
    base_name = f"PagerDuty - {org_name}"
    suggested_name = base_name
    counter = 2
    while suggested_name in existing_names:
        suggested_name = f"{base_name} #{counter}"
        counter += 1

    # Add can_add flag and suggested_name
    result["account_info"]["can_add"] = True
    result["account_info"]["suggested_name"] = suggested_name

    return result

@router.get("/integrations")
async def get_pagerduty_integrations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get all PagerDuty integrations for the current user."""
    integrations = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.platform == "pagerduty"
        )
    ).all()

    integration_data_list = []
    uncached_integrations = []

    for integration in integrations:
        has_valid_token = integration.api_token and len(integration.api_token) >= 4
        token_suffix = f"****{integration.api_token[-4:]}" if has_valid_token else "****"

        data = {
            "id": integration.id,
            "name": integration.name,
            "organization_name": integration.organization_name,
            "total_users": integration.total_users,
            "is_default": integration.is_default,
            "created_at": integration.created_at.isoformat(),
            "last_used_at": integration.last_used_at.isoformat() if integration.last_used_at else None,
            "token_suffix": token_suffix,
            "platform": integration.platform
        }

        cached_permissions = get_cached_permissions(integration.id)
        if cached_permissions:
            data["permissions"] = cached_permissions
        elif integration.api_token:
            uncached_integrations.append((integration.id, integration.api_token, len(integration_data_list)))

        integration_data_list.append(data)

    if uncached_integrations:
        await _fetch_and_apply_permissions(uncached_integrations, integration_data_list)

    return {
        "integrations": integration_data_list,
        "total": len(integration_data_list)
    }


async def _fetch_and_apply_permissions(
    uncached_integrations: list,
    integration_data_list: list
) -> None:
    """Fetch permissions for integrations in parallel and apply results."""
    async def fetch_single(integration_id: int, api_token: str, index: int):
        try:
            client = PagerDutyAPIClient(api_token)
            permissions = await client.check_permissions()
            set_cached_permissions(integration_id, permissions)
            return (index, permissions, None)
        except Exception as e:
            logger.warning(f"Failed to check permissions for integration {integration_id}: {e}")
            return (index, None, str(e))

    results = await asyncio.gather(
        *[fetch_single(int_id, token, idx) for int_id, token, idx in uncached_integrations]
    )

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Permission check failed with exception: {result}")
            continue

        index, permissions, error = result
        if permissions:
            integration_data_list[index]["permissions"] = permissions
        else:
            error_permission = {"access": False, "error": f"Permission check failed: {error}"}
            integration_data_list[index]["permissions"] = {
                "users": error_permission,
                "incidents": error_permission
            }

@router.post("/integrations", response_model=IntegrationResponse)
async def add_pagerduty_integration(
    request: AddIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new PagerDuty integration."""
    # Test the token first
    client = PagerDutyAPIClient(request.token)
    test_result = await client.test_connection()

    if not test_result["valid"]:
        # Map error codes to user-friendly messages with actionable guidance
        error_code = test_result.get("error_code")
        error_details = {
            "error_code": error_code,
            "technical_message": test_result.get("error", "Unknown error")
        }

        # Determine appropriate HTTP status code and user message
        if error_code == "UNAUTHORIZED":
            status_code = status.HTTP_401_UNAUTHORIZED
            user_message = "PagerDuty API token is no longer valid"
            user_guidance = "The token may have been revoked. Please generate a new token from PagerDuty and try again."
        elif error_code == "FORBIDDEN":
            status_code = status.HTTP_403_FORBIDDEN
            user_message = "PagerDuty API token lacks required permissions"
            user_guidance = "The token needs read access to users and incidents. Please use a token with sufficient permissions."
        elif error_code == "NOT_FOUND":
            status_code = status.HTTP_404_NOT_FOUND
            user_message = "Cannot connect to PagerDuty API"
            user_guidance = "This may indicate:\n• The API endpoint is incorrect\n• Your token doesn't have access to the users endpoint"
        elif error_code == "CONNECTION_ERROR":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            user_message = "Cannot reach PagerDuty servers"
            user_guidance = "Please check:\n• Your internet connection is working\n• api.pagerduty.com is accessible from your network\n• Your firewall/proxy isn't blocking the connection"
        elif error_code == "API_ERROR":
            status_code = status.HTTP_502_BAD_GATEWAY
            user_message = "PagerDuty API returned an error"
            user_guidance = "The PagerDuty API is experiencing issues. Please try again in a few moments."
        else:  # UNKNOWN_ERROR or other
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            user_message = "Unexpected error connecting to PagerDuty"
            user_guidance = "An unexpected error occurred. Please contact support if this persists."

        error_details["user_message"] = user_message
        error_details["user_guidance"] = user_guidance

        raise HTTPException(
            status_code=status_code,
            detail=error_details
        )
    
    account_info = test_result["account_info"]
    org_name = account_info["organization_name"]
    
    # Check for duplicates
    existing = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.organization_name == org_name,
            RootlyIntegration.platform == "pagerduty"
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This PagerDuty account is already connected"
        )
    
    # Check if this is the first integration
    existing_count = db.query(RootlyIntegration).filter(
        RootlyIntegration.user_id == current_user.id
    ).count()
    
    # Create new integration
    integration = RootlyIntegration(
        user_id=current_user.id,
        name=request.name or org_name,
        api_token=request.token,
        organization_name=org_name,
        total_users=account_info["total_users"],
        is_default=(existing_count == 0),
        platform="pagerduty"
    )
    
    db.add(integration)
    db.commit()
    db.refresh(integration)
    
    return IntegrationResponse(
        id=integration.id,
        name=integration.name,
        organization_name=integration.organization_name,
        total_users=integration.total_users,
        total_services=account_info.get("total_services", 0),
        is_default=integration.is_default,
        created_at=integration.created_at.isoformat(),
        last_used_at=None,
        token_suffix=integration.api_token[-4:] if len(integration.api_token) > 4 else "****",
        platform=integration.platform
    )

@router.put("/integrations/{integration_id}", response_model=IntegrationResponse)
def update_pagerduty_integration(
    integration_id: int,
    request: UpdateIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a PagerDuty integration."""
    integration = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.id == integration_id,
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.platform == "pagerduty"
        )
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    if request.name is not None:
        integration.name = request.name
    
    if request.is_default is not None:
        # If setting as default, unset other defaults
        if request.is_default:
            db.query(RootlyIntegration).filter(
                and_(
                    RootlyIntegration.user_id == current_user.id,
                    RootlyIntegration.id != integration_id
                )
            ).update({"is_default": False})
        integration.is_default = request.is_default
    
    db.commit()
    db.refresh(integration)
    
    return IntegrationResponse(
        id=integration.id,
        name=integration.name,
        organization_name=integration.organization_name,
        total_users=integration.total_users,
        total_services=integration.total_users,
        is_default=integration.is_default,
        created_at=integration.created_at.isoformat(),
        last_used_at=integration.last_used_at.isoformat() if integration.last_used_at else None,
        token_suffix=integration.api_token[-4:] if len(integration.api_token) > 4 else "****",
        platform=integration.platform
    )


@router.delete("/integrations/{integration_id}")
def delete_pagerduty_integration(
    integration_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a PagerDuty integration."""
    integration = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.id == integration_id,
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.platform == "pagerduty"
        )
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # If this was default, make another one default
    if integration.is_default:
        other_integration = db.query(RootlyIntegration).filter(
            and_(
                RootlyIntegration.user_id == current_user.id,
                RootlyIntegration.id != integration_id
            )
        ).first()
        
        if other_integration:
            other_integration.is_default = True
    
    db.delete(integration)
    db.commit()
    
    return {"status": "success", "message": "Integration deleted successfully"}