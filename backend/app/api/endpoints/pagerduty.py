"""
PagerDuty integration API endpoints.
"""

from datetime import datetime
from typing import List, Optional
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ...models import get_db, User, Organization
from ...models.rootly_integration import RootlyIntegration
from ...auth.dependencies import get_current_active_user
from ...core.pagerduty_client import PagerDutyAPIClient

router = APIRouter()
logger = logging.getLogger(__name__)

def get_or_create_organization(
    db: Session,
    organization_name: str,
    user: User,
    platform: str = "pagerduty"
) -> Organization:
    """
    Get or create an Organization record based on the integration's organization name.

    This is called when users add PagerDuty integrations.
    Organizations are created from the integration's organization_name, not email domains.
    """
    if not organization_name:
        # Fallback to email domain if no organization name provided
        domain = user.email.split('@')[1] if '@' in user.email else None
        if not domain:
            raise ValueError("Cannot determine organization - no organization name or valid email")
        organization_name = domain.split('.')[0].title() + " Organization"

    # Clean the organization name
    organization_name = organization_name.strip()

    # Create a unique domain identifier from the organization name
    # Use a slug-like format: "acme-corp-pagerduty"
    slug = organization_name.lower().replace(' ', '-').replace('.', '-')[:50]
    domain = f"{slug}.{platform}.com"

    # Check if organization already exists by name or domain
    organization = db.query(Organization).filter(
        (Organization.name == organization_name) | (Organization.domain == domain)
    ).first()

    if not organization:
        # Create new organization
        counter = 1
        unique_domain = domain
        unique_slug = slug

        # Ensure domain and slug are unique
        while db.query(Organization).filter(Organization.domain == unique_domain).first():
            unique_domain = f"{slug}-{counter}.{platform}.com"
            unique_slug = f"{slug}-{counter}"
            counter += 1

        organization = Organization(
            name=organization_name,
            domain=unique_domain,
            slug=unique_slug,
            status='active',
            plan_type='free',
            max_users=50,
            max_analyses_per_month=5
        )
        db.add(organization)
        db.flush()  # Get the organization.id without committing yet

        logger.info(f"Created new organization: {organization_name} (id={organization.id})")

    return organization

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
    
    if result["valid"]:
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
        
        # Add can_add flag
        result["account_info"]["can_add"] = True
    
    return result

@router.get("/integrations")
async def get_pagerduty_integrations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all PagerDuty integrations for the current user."""
    integrations = db.query(RootlyIntegration).filter(
        and_(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.platform == "pagerduty"
        )
    ).all()
    
    result_integrations = []
    for i in integrations:
        integration_data = {
            "id": i.id,
            "name": i.name,
            "organization_name": i.organization_name,
            "total_users": i.total_users,
            "is_default": i.is_default,
            "created_at": i.created_at.isoformat(),
            "last_used_at": i.last_used_at.isoformat() if i.last_used_at else None,
            "token_suffix": f"****{i.api_token[-4:]}" if i.api_token and len(i.api_token) >= 4 else "****",
            "platform": i.platform
        }
        
        # Check permissions for this integration
        if i.api_token:
            try:
                client = PagerDutyAPIClient(i.api_token)
                permissions = await client.check_permissions()
                integration_data["permissions"] = permissions
            except Exception as e:
                logger.warning(f"Failed to check permissions for integration {i.id}: {e}")
                # If we can't check permissions, include a note
                integration_data["permissions"] = {
                    "users": {"access": False, "error": f"Permission check failed: {str(e)}"},
                    "incidents": {"access": False, "error": f"Permission check failed: {str(e)}"}
                }
        
        result_integrations.append(integration_data)
    
    # Add beta fallback integration if available
    beta_pagerduty_token = os.getenv('PAGERDUTY_API_TOKEN')
    logger.info(f"Beta PagerDuty token check: exists={beta_pagerduty_token is not None}, length={len(beta_pagerduty_token) if beta_pagerduty_token else 0}")
    if beta_pagerduty_token:
        try:
            # Test the beta token and get organization info
            logger.info(f"Testing beta PagerDuty token: {beta_pagerduty_token[:10]}...")
            client = PagerDutyAPIClient(beta_pagerduty_token)
            test_result = await client.test_connection()
            logger.info(f"Beta PagerDuty test_result: {test_result}")
            
            if test_result.get("valid"):
                account_info = test_result.get("account_info", {})
                logger.info(f"Beta PagerDuty account_info: {account_info}")
                
                # Check permissions for the beta token
                try:
                    permissions = await client.check_permissions()
                    logger.info(f"Beta PagerDuty permissions: {permissions}")
                except Exception as e:
                    logger.warning(f"Failed to check beta PagerDuty permissions: {e}")
                    permissions = {}
                
                beta_integration = {
                    "id": "beta-pagerduty",  # Special ID for beta integration
                    "name": "PagerDuty (Beta Access)",
                    "organization_name": account_info.get("organization_name") or "Beta Organization",
                    "total_users": account_info.get("total_users", 0),
                    "is_default": True,
                    "is_beta": True,  # Special flag to indicate beta integration
                    "created_at": datetime.now().isoformat(),
                    "last_used_at": None,
                    "token_suffix": f"***{beta_pagerduty_token[-4:]}",
                    "platform": "pagerduty",
                    "permissions": permissions  # Add permission info for frontend display
                }
                
                # Add beta integration at the beginning of the list
                result_integrations.insert(0, beta_integration)
                logger.info(f"Added beta PagerDuty integration for user {current_user.id}")
            else:
                logger.warning(f"Beta PagerDuty test_connection failed: {test_result}")
                # Add fallback integration with limited info
                beta_integration = {
                    "id": "beta-pagerduty",
                    "name": "PagerDuty (Beta Access)",
                    "organization_name": "Beta Organization", 
                    "total_users": 0,
                    "is_default": True,
                    "is_beta": True,
                    "created_at": datetime.now().isoformat(),
                    "last_used_at": None,
                    "token_suffix": f"***{beta_pagerduty_token[-4:]}",
                    "platform": "pagerduty"
                }
                result_integrations.insert(0, beta_integration)
                logger.info(f"Added fallback beta PagerDuty integration for user {current_user.id}")
        except Exception as e:
            logger.warning(f"Failed to add beta PagerDuty integration: {str(e)}")
            # Add fallback integration even on exception
            beta_integration = {
                "id": "beta-pagerduty",
                "name": "PagerDuty (Beta Access)",
                "organization_name": "Beta Organization",
                "total_users": 0,
                "is_default": True,
                "is_beta": True,
                "created_at": datetime.now().isoformat(),
                "last_used_at": None,
                "token_suffix": "***BETA",
                "platform": "pagerduty"
            }
            result_integrations.insert(0, beta_integration)
            logger.info(f"Added exception fallback beta PagerDuty integration for user {current_user.id}")
    
    return {
        "integrations": result_integrations,
        "total": len(result_integrations)
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PagerDuty API token"
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

    # Get or create organization based on PagerDuty's organization name
    organization = get_or_create_organization(db, org_name, current_user, platform="pagerduty")

    # Link user to organization if they don't have one
    if not current_user.organization_id:
        current_user.organization_id = organization.id
        current_user.role = 'org_admin'  # First user becomes admin
        current_user.joined_org_at = datetime.utcnow()
        logger.info(f"Linked user {current_user.id} to organization {organization.id}")

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