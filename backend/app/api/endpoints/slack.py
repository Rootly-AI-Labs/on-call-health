"""
Slack integration API endpoints for OAuth and data collection.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Dict, Any
import secrets
import json
import logging
from cryptography.fernet import Fernet
import base64
from datetime import datetime
from pydantic import BaseModel

from ...models import get_db, User, SlackIntegration, UserCorrelation, UserBurnoutReport, Analysis, SlackWorkspaceMapping
from ...auth.dependencies import get_current_user
from ...auth.integration_oauth import slack_integration_oauth
from ...core.config import settings
from ...services.notification_service import NotificationService

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack-integration"])

# Helper function to get the user isolation key (organization_id or user_id for beta)
def get_user_isolation_key(user: User) -> tuple:
    """
    Get the isolation key for queries - organization_id if available, otherwise user_id.
    Returns: (key_name, key_value) tuple
    """
    if user.organization_id:
        return ("organization_id", user.organization_id)
    else:
        # Beta mode: isolate by user_id
        return ("user_id", user.id)

# Simple encryption for tokens (in production, use proper key management)
def get_encryption_key():
    """Get or create encryption key for tokens."""
    key = settings.JWT_SECRET_KEY.encode()
    # Ensure key is 32 bytes for Fernet
    key = base64.urlsafe_b64encode(key[:32].ljust(32, b'\0'))
    return key

def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()

@router.post("/connect")
async def connect_slack(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Slack OAuth flow for integration.
    Returns authorization URL for frontend to redirect to.
    """
    # Check if OAuth credentials are configured
    if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack OAuth is not configured. Please contact your administrator to set up Slack integration."
        )
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    # Store state in session or database (simplified for this example)
    # In production, you'd want to store this more securely
    auth_url = slack_integration_oauth.get_authorization_url(state=state)
    
    return {
        "authorization_url": auth_url,
        "state": state
    }

@router.get("/test-endpoint")
async def test_slack_endpoint():
    """Simple test endpoint to verify routing is working."""
    return {"message": "Slack OAuth endpoint is reachable", "endpoint": "/api/integrations/slack/test-endpoint"}

@router.get("/oauth/callback")
async def slack_oauth_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """
    Handle Slack OAuth callback for workspace-level app installation.
    Creates a workspace mapping and redirects to the frontend with success status.
    """
    logger.info(f"🔵 Slack OAuth callback received - code: {code[:20]}..., state: {state[:50] if state else 'None'}...")

    try:
        # Parse state parameter to get organization info
        organization_id = None
        user_email = None

        if state:
            import base64
            try:
                decoded_state = json.loads(base64.b64decode(state + '=='))  # Add padding
                organization_id = decoded_state.get("orgId")
                user_email = decoded_state.get("email")
                logger.info(f"📋 Decoded state - org_id: {organization_id}, email: {user_email}")
            except Exception as state_error:
                # If state parsing fails, continue without org mapping
                logger.warning(f"⚠️ Failed to parse state parameter: {state_error}")
                pass

        # Exchange code for token using Slack's OAuth API
        import httpx
        async with httpx.AsyncClient() as client:
            # Construct the same redirect_uri that was used in the OAuth request
            frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
            backend_base = settings.DATABASE_URL.replace("postgresql://", "https://").split("@")[1].split("/")[0] if settings.DATABASE_URL else "localhost:8000"

            # For Railway deployment, construct the correct backend URL
            if "railway" in str(settings.DATABASE_URL):
                backend_url = f"https://rootly-burnout-detector-web-development.up.railway.app"
            else:
                backend_url = "http://localhost:8000"

            redirect_uri = f"{backend_url}/integrations/slack/oauth/callback"

            token_response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.SLACK_CLIENT_ID,
                    "client_secret": settings.SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange code for token"
                )

            token_data = token_response.json()

            if not token_data.get("ok"):
                error_msg = token_data.get('error', 'Unknown error')
                logger.error(f"❌ Slack OAuth token exchange failed: {error_msg}")
                logger.error(f"Full token response: {token_data}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Slack OAuth error: {error_msg}"
                )

            # Extract token and team info
            access_token = token_data.get("access_token")
            team_info = token_data.get("team", {})
            workspace_id = team_info.get("id")
            workspace_name = team_info.get("name")

            if not access_token or not workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token or workspace ID from Slack"
                )

        # For now, we'll store the bot token in SlackIntegration model instead
        # and create a basic workspace mapping without token storage

        # Find a user from the organization if we have organization_id
        owner_user = None
        if organization_id:
            owner_user = db.query(User).filter(
                User.organization_id == organization_id
            ).first()

        # If no specific owner found, find any user to be the owner
        # This allows the workspace to be registered and functional
        if not owner_user:
            # Use the first available user as the owner for the workspace mapping
            owner_user = db.query(User).first()

            if not owner_user:
                # If absolutely no users exist, we can't create the mapping
                from fastapi.responses import RedirectResponse
                frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
                redirect_url = f"{frontend_url}/integrations?slack_connected=false&error=no_users_found"
                return RedirectResponse(url=redirect_url, status_code=302)

        # Create or update workspace mapping
        existing_mapping = db.query(SlackWorkspaceMapping).filter(
            SlackWorkspaceMapping.workspace_id == workspace_id
        ).first()

        if existing_mapping:
            # Update existing mapping
            existing_mapping.workspace_name = workspace_name
            if organization_id:
                existing_mapping.organization_id = organization_id
            mapping = existing_mapping
        else:
            # Create new mapping
            mapping = SlackWorkspaceMapping(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                organization_id=organization_id,
                owner_user_id=owner_user.id,
                status='active'
            )
            db.add(mapping)

        # Store the bot token separately in a SlackIntegration record for the workspace
        # This is a simplified approach - in production you might want a dedicated bot token table
        slack_integration = db.query(SlackIntegration).filter(
            SlackIntegration.workspace_id == workspace_id
        ).first()

        if slack_integration:
            slack_integration.slack_token = encrypt_token(access_token)
            slack_integration.updated_at = datetime.utcnow()
        else:
            # Create a workspace-level integration record
            slack_integration = SlackIntegration(
                user_id=owner_user.id,
                slack_token=encrypt_token(access_token),
                workspace_id=workspace_id,
                token_source="oauth"
            )
            db.add(slack_integration)

        db.commit()
        logger.info(f"✅ Slack OAuth successful - workspace: {workspace_name}, workspace_id: {workspace_id}")

        # Redirect to frontend with success message
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        import urllib.parse
        encoded_workspace = urllib.parse.quote(workspace_name) if workspace_name else "unknown"
        redirect_url = f"{frontend_url}/integrations?slack_connected=true&workspace={encoded_workspace}"

        logger.info(f"🔗 Redirecting to: {redirect_url}")

        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url, status_code=302)

    except HTTPException as he:
        logger.error(f"❌ Slack OAuth HTTPException: {he.detail}")
        # Redirect to frontend with error
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        from fastapi.responses import RedirectResponse
        import urllib.parse
        error_msg = urllib.parse.quote(str(he.detail))
        redirect_url = f"{frontend_url}/integrations?slack_connected=false&error={error_msg}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Slack OAuth unexpected error: {str(e)}")
        logger.exception(e)
        # Redirect to frontend with error
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        from fastapi.responses import RedirectResponse
        import urllib.parse
        error_msg = urllib.parse.quote(f"Unexpected error: {str(e)}")
        redirect_url = f"{frontend_url}/integrations?slack_connected=false&error={error_msg}"
        return RedirectResponse(url=redirect_url, status_code=302)

@router.get("/check-scopes")
async def check_slack_scopes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check what scopes the current Slack token has."""
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()
    
    if not integration or not integration.slack_token:
        return {"error": "No Slack integration found"}
    
    try:
        # Decrypt token
        access_token = decrypt_token(integration.slack_token)
        
        # Get token info to see what scopes it has
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        import httpx
        async with httpx.AsyncClient() as client:
            # Test auth.test to get basic info
            response = await client.get("https://slack.com/api/auth.test", headers=headers)
            auth_result = response.json()
            
            # Test various API endpoints to see what works
            scope_tests = {
                "conversations.list": False,
                "conversations.history": False,
                "users.conversations": False,
                "users.list": False,
                "channels.history": False,
                "groups.history": False
            }
            
            # Test conversations.list
            try:
                response = await client.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 1})
                result = response.json()
                scope_tests["conversations.list"] = result.get("ok", False)
                if not scope_tests["conversations.list"]:
                    scope_tests["conversations.list"] = f"Error: {result.get('error', 'Unknown')}"
            except Exception as e:
                scope_tests["conversations.list"] = f"Exception: {str(e)}"
            
            # Test conversations.history (need a channel first)
            if scope_tests["conversations.list"] is True:
                try:
                    # Get a channel to test history
                    channels_response = await client.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 1})
                    channels_result = channels_response.json()
                    if channels_result.get("ok") and channels_result.get("channels"):
                        channel_id = channels_result["channels"][0]["id"]
                        
                        response = await client.get("https://slack.com/api/conversations.history", headers=headers, params={"channel": channel_id, "limit": 1})
                        result = response.json()
                        scope_tests["conversations.history"] = result.get("ok", False)
                        if not scope_tests["conversations.history"]:
                            scope_tests["conversations.history"] = f"Error: {result.get('error', 'Unknown')}"
                except Exception as e:
                    scope_tests["conversations.history"] = f"Exception: {str(e)}"
            
            # Test users.conversations
            if auth_result.get("ok") and auth_result.get("user_id"):
                user_id = auth_result["user_id"]
                try:
                    response = await client.get("https://slack.com/api/users.conversations", headers=headers, params={"user": user_id, "limit": 1})
                    result = response.json()
                    scope_tests["users.conversations"] = result.get("ok", False)
                    if not scope_tests["users.conversations"]:
                        scope_tests["users.conversations"] = f"Error: {result.get('error', 'Unknown')}"
                except Exception as e:
                    scope_tests["users.conversations"] = f"Exception: {str(e)}"
            
            return {
                "auth_info": auth_result,
                "scope_tests": scope_tests,
                "integration_info": {
                    "token_source": integration.token_source,
                    "workspace_id": integration.workspace_id,
                    "created_at": integration.created_at.isoformat()
                }
            }
        
    except Exception as e:
        return {"error": f"Failed to check scopes: {str(e)}"}

@router.post("/test")
async def test_slack_integration(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test Slack integration permissions and connectivity.
    """
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()
    
    if not integration or not integration.slack_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found"
        )
    
    try:
        # Decrypt token
        access_token = decrypt_token(integration.slack_token)
        
        # Test permissions
        permissions = await slack_integration_oauth.test_permissions(access_token)
        
        # Get auth info
        auth_info = await slack_integration_oauth.test_auth(access_token)
        
        # Get user info
        user_info = await slack_integration_oauth.get_user_info(access_token, integration.slack_user_id)
        user_profile = user_info.get("user", {}).get("profile", {})
        
        return {
            "success": True,
            "integration": {
                "slack_user_id": integration.slack_user_id,
                "workspace_id": integration.workspace_id,
                "connected_at": integration.created_at.isoformat(),
                "last_updated": integration.updated_at.isoformat()
            },
            "permissions": permissions,
            "workspace_info": {
                "team_id": auth_info.get("team_id"),
                "team_name": auth_info.get("team"),
                "url": auth_info.get("url")
            },
            "user_info": {
                "user_id": integration.slack_user_id,
                "name": user_profile.get("real_name") or user_profile.get("display_name"),
                "email": user_profile.get("email"),
                "title": user_profile.get("title"),
                "timezone": user_profile.get("tz")
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Slack integration: {str(e)}"
        )

@router.get("/status")
async def get_slack_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Slack integration status for current user.
    Checks both SlackIntegration (manual setup) and SlackWorkspaceMapping (OAuth setup).
    """
    logger.info(f"🔍 Checking Slack status for user {current_user.id} (org: {current_user.organization_id})")

    # Check for manual SlackIntegration first
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()

    logger.info(f"Manual integration found: {integration is not None}")

    # If no manual integration, check for OAuth workspace mapping
    workspace_mapping = None
    if not integration:
        # Check if there's a workspace mapping for this user's organization
        if current_user.organization_id:
            workspace_mapping = db.query(SlackWorkspaceMapping).filter(
                SlackWorkspaceMapping.organization_id == current_user.organization_id,
                SlackWorkspaceMapping.status == 'active'
            ).first()
            logger.info(f"Org workspace mapping found: {workspace_mapping is not None}")

        # Also check if user is the owner of any workspace mapping
        if not workspace_mapping:
            workspace_mapping = db.query(SlackWorkspaceMapping).filter(
                SlackWorkspaceMapping.owner_user_id == current_user.id,
                SlackWorkspaceMapping.status == 'active'
            ).first()
            logger.info(f"Owner workspace mapping found: {workspace_mapping is not None}")

        # If we have a workspace mapping, get the SlackIntegration for that workspace
        if workspace_mapping:
            integration = db.query(SlackIntegration).filter(
                SlackIntegration.workspace_id == workspace_mapping.workspace_id
            ).first()
            logger.info(f"Integration for workspace {workspace_mapping.workspace_id}: {integration is not None}")

    if not integration and not workspace_mapping:
        return {
            "connected": False,
            "integration": None
        }
    
    # Get channel count and names dynamically
    total_channels = 0
    channel_names = []
    channels_error = None
    token_preview = None
    webhook_preview = None
    access_token = None  # Initialize to None

    try:
        # Decrypt token and get preview (only for manual integrations)
        if integration:
            access_token = decrypt_token(integration.slack_token)
            token_preview = f"...{access_token[-4:]}" if access_token else None

            # Get webhook preview if available
            if integration.webhook_url:
                webhook_preview = f"...{integration.webhook_url[-4:]}"

        if not access_token:
            # No token to fetch channels with
            raise Exception("No access token available")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        import httpx
        async with httpx.AsyncClient() as client:
            # Try to get public channels first (requires channels:read scope)
            channels_response = await client.get(
                "https://slack.com/api/conversations.list", 
                headers=headers,
                params={"types": "public_channel", "limit": 1000}
            )
            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                if channels_data.get("ok", False):
                    channels = channels_data.get("channels", [])
                    total_channels = len(channels)
                    # Extract channel names (limit to first 10 for display)
                    channel_names = [ch.get("name", "") for ch in channels[:10] if ch.get("name")]
                    logging.getLogger(__name__).info(f"Successfully got {total_channels} public channels")
                else:
                    channels_error = channels_data.get("error", "unknown_error")
                    logging.getLogger(__name__).error(f"Slack API error for channels: {channels_error}")
            else:
                channels_error = f"HTTP {channels_response.status_code}"
                logging.getLogger(__name__).error(f"Slack API HTTP error for channels: {channels_error}")
                
            # If public channels failed, try with minimal scope (may work with some tokens)
            if total_channels == 0 and not channels_error:
                try:
                    basic_response = await client.get(
                        "https://slack.com/api/conversations.list", 
                        headers=headers,
                        params={"limit": 100}  # No specific type - uses default
                    )
                    if basic_response.status_code == 200:
                        basic_data = basic_response.json()
                        if basic_data.get("ok", False):
                            channels = basic_data.get("channels", [])
                            total_channels = len(channels)
                            channel_names = [ch.get("name", "") for ch in channels[:10] if ch.get("name")]
                            logging.getLogger(__name__).info(f"Fallback: got {total_channels} channels with basic request")
                except Exception:
                    pass  # Fallback failed, keep original count
    except Exception as e:
        channels_error = str(e)
        # Only log as warning since this is just a preview/test, not critical functionality
        logging.getLogger(__name__).warning(f"Slack API preview failed for channels: {channels_error[:100]}...")
    
    # Build response data based on connection type
    if integration:
        # Manual SlackIntegration - fetch workspace name from Slack API
        workspace_name = None
        try:
            import httpx
            # Get workspace name from Slack API using the already decrypted token
            if access_token:
                async with httpx.AsyncClient() as client:
                    team_response = await client.get(
                        "https://slack.com/api/team.info",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    if team_response.status_code == 200:
                        team_data = team_response.json()
                        if team_data.get("ok"):
                            workspace_name = team_data.get("team", {}).get("name")
                            logger.info(f"Successfully fetched workspace name: {workspace_name}")
                        else:
                            logger.warning(f"Slack team.info API returned ok=false: {team_data.get('error')}")
                    else:
                        logger.warning(f"Slack team.info API returned status {team_response.status_code}")
        except Exception as e:
            logger.warning(f"Could not fetch workspace name: {e}")

        response_data = {
            "connected": True,
            "integration": {
                "id": integration.id,
                "slack_user_id": integration.slack_user_id,
                "workspace_id": integration.workspace_id,
                "workspace_name": workspace_name,
                "token_source": integration.token_source,
                "is_oauth": integration.is_oauth,
                "supports_refresh": integration.supports_refresh,
                "has_webhook": integration.webhook_url is not None,
                "webhook_configured": integration.webhook_url is not None,
                "connected_at": integration.created_at.isoformat(),
                "last_updated": integration.updated_at.isoformat(),
                "total_channels": total_channels,
                "channel_names": channel_names,
                "token_preview": token_preview,
                "webhook_preview": webhook_preview,
                "connection_type": "manual"
            }
        }
    else:
        # OAuth SlackWorkspaceMapping
        workspace_name_oauth = workspace_mapping.workspace_name
        if not workspace_name_oauth:
            logger.warning(f"OAuth workspace {workspace_mapping.workspace_id} has no name in database")

        response_data = {
            "connected": True,
            "integration": {
                "id": workspace_mapping.id,
                "slack_user_id": None,  # Not stored in workspace mapping
                "workspace_id": workspace_mapping.workspace_id,
                "workspace_name": workspace_name_oauth or workspace_mapping.workspace_id,  # Fallback to ID
                "token_source": "oauth",
                "is_oauth": True,
                "supports_refresh": False,
                "has_webhook": False,
                "webhook_configured": False,
                "connected_at": workspace_mapping.registered_at.isoformat(),
                "last_updated": workspace_mapping.registered_at.isoformat(),
                "total_channels": 0,  # Not fetched for workspace mappings
                "channel_names": [],
                "token_preview": None,
                "webhook_preview": None,
                "connection_type": "oauth",
                "status": workspace_mapping.status,
                "owner_user_id": workspace_mapping.owner_user_id
            }
        }
    
    # Add error information if there was an issue getting channel count
    if channels_error:
        response_data["integration"]["channels_error"] = channels_error
        response_data["integration"]["channels_error_message"] = f"Unable to fetch channels: {channels_error}"
    
    return response_data

class TokenRequest(BaseModel):
    token: str

class TokenWebhookRequest(BaseModel):
    token: str
    webhook_url: str

@router.post("/token")
async def connect_slack_with_token(
    request: TokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect Slack integration using a personal access token.
    """
    try:
        # Validate token by making a test API call
        headers = {
            "Authorization": f"Bearer {request.token}",
            "Content-Type": "application/json"
        }
        
        # Test the token by getting auth info
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("https://slack.com/api/auth.test", headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to validate Slack token"
                )
            
            auth_info = response.json()
            if not auth_info.get("ok", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Slack token: {auth_info.get('error', 'Unknown error')}"
                )
            
            slack_user_id = auth_info.get("user_id")
            workspace_id = auth_info.get("team_id")
            
            if not slack_user_id or not workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get Slack user ID or workspace ID from token"
                )
            
            # Get user info (optional)
            user_email = None
            user_name = None
            try:
                user_response = await client.get(
                    "https://slack.com/api/users.info", 
                    headers=headers, 
                    params={"user": slack_user_id}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    if user_data.get("ok", False):
                        user_profile = user_data.get("user", {}).get("profile", {})
                        user_email = user_profile.get("email")
                        user_name = user_profile.get("real_name") or user_profile.get("display_name")
            except Exception:
                pass  # User info is optional
            
            # Get channel count (optional)
            total_channels = 0
            try:
                # Get public channels
                channels_response = await client.get(
                    "https://slack.com/api/conversations.list", 
                    headers=headers,
                    params={"types": "public_channel,private_channel", "limit": 1000}
                )
                if channels_response.status_code == 200:
                    channels_data = channels_response.json()
                    if channels_data.get("ok", False):
                        channels = channels_data.get("channels", [])
                        total_channels = len(channels)
            except Exception:
                pass  # Channel count is optional
        
        # Encrypt the token
        encrypted_token = encrypt_token(request.token)
        
        # Check if integration already exists
        existing_integration = db.query(SlackIntegration).filter(
            SlackIntegration.user_id == current_user.id
        ).first()
        
        if existing_integration:
            # Update existing integration
            existing_integration.slack_token = encrypted_token
            existing_integration.slack_user_id = slack_user_id
            existing_integration.workspace_id = workspace_id
            existing_integration.webhook_url = None  # Clear webhook URL for token-only setup
            existing_integration.token_source = "manual"
            existing_integration.updated_at = datetime.utcnow()
            integration = existing_integration
        else:
            # Create new integration
            integration = SlackIntegration(
                user_id=current_user.id,
                slack_token=encrypted_token,
                slack_user_id=slack_user_id,
                workspace_id=workspace_id,
                webhook_url=None,  # No webhook URL for token-only setup
                token_source="manual"
            )
            db.add(integration)
        
        # Update user correlations if email is available
        if user_email:
            # Use organization_id for multi-tenancy
            existing_correlation = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == current_user.organization_id,
                UserCorrelation.email == user_email
            ).first()

            if existing_correlation:
                existing_correlation.slack_user_id = slack_user_id
            else:
                correlation = UserCorrelation(
                    user_id=current_user.id,
                    organization_id=current_user.organization_id,
                    email=user_email,
                    slack_user_id=slack_user_id
                )
                db.add(correlation)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Slack integration connected successfully with personal access token",
            "integration": {
                "id": integration.id,
                "slack_user_id": slack_user_id,
                "workspace_id": workspace_id,
                "token_source": "manual",
                "user_email": user_email,
                "user_name": user_name,
                "total_channels": total_channels
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Slack integration: {str(e)}"
        )

@router.post("/setup")
async def setup_slack_with_token_and_webhook(
    request: TokenWebhookRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect Slack integration using both a bot token and webhook URL.
    This provides full functionality for data collection and notifications.
    """
    try:
        # Validate webhook URL format
        if not request.webhook_url.startswith("https://hooks.slack.com/services/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Slack webhook URL format. Should start with https://hooks.slack.com/services/"
            )
        
        # Validate token by making a test API call
        headers = {
            "Authorization": f"Bearer {request.token}",
            "Content-Type": "application/json"
        }
        
        # Test the token by getting auth info
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("https://slack.com/api/auth.test", headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to validate Slack token"
                )
            
            auth_info = response.json()
            if not auth_info.get("ok", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Slack token: {auth_info.get('error', 'Unknown error')}"
                )
            
            slack_user_id = auth_info.get("user_id")
            workspace_id = auth_info.get("team_id")
            
            if not slack_user_id or not workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get Slack user ID or workspace ID from token"
                )
            
            # Test webhook URL by sending a test message
            try:
                webhook_test_response = await client.post(
                    request.webhook_url,
                    json={
                        "text": "🔗 Slack integration test from Rootly Burnout Detector",
                        "username": "Rootly Bot",
                        "icon_emoji": ":robot_face:"
                    }
                )
                if webhook_test_response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Webhook URL test failed. Please check the URL and permissions."
                    )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to reach webhook URL. Please check the URL."
                )
            
            # Get user info (optional)
            user_email = None
            user_name = None
            try:
                user_response = await client.get(
                    "https://slack.com/api/users.info", 
                    headers=headers, 
                    params={"user": slack_user_id}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    if user_data.get("ok", False):
                        user_profile = user_data.get("user", {}).get("profile", {})
                        user_email = user_profile.get("email")
                        user_name = user_profile.get("real_name") or user_profile.get("display_name")
            except Exception:
                pass  # User info is optional
            
            # Get channel count (optional)
            total_channels = 0
            try:
                channels_response = await client.get(
                    "https://slack.com/api/conversations.list", 
                    headers=headers,
                    params={"types": "public_channel,private_channel", "limit": 1000}
                )
                if channels_response.status_code == 200:
                    channels_data = channels_response.json()
                    if channels_data.get("ok", False):
                        channels = channels_data.get("channels", [])
                        total_channels = len(channels)
            except Exception:
                pass  # Channel count is optional
        
        # Encrypt the token
        encrypted_token = encrypt_token(request.token)
        
        # Check if integration already exists
        existing_integration = db.query(SlackIntegration).filter(
            SlackIntegration.user_id == current_user.id
        ).first()
        
        if existing_integration:
            # Update existing integration
            existing_integration.slack_token = encrypted_token
            existing_integration.slack_user_id = slack_user_id
            existing_integration.workspace_id = workspace_id
            existing_integration.webhook_url = request.webhook_url
            existing_integration.token_source = "manual"
            existing_integration.updated_at = datetime.utcnow()
            integration = existing_integration
        else:
            # Create new integration
            integration = SlackIntegration(
                user_id=current_user.id,
                slack_token=encrypted_token,
                slack_user_id=slack_user_id,
                workspace_id=workspace_id,
                webhook_url=request.webhook_url,
                token_source="manual"
            )
            db.add(integration)
        
        # Update user correlations if email is available
        if user_email:
            # Use organization_id for multi-tenancy
            existing_correlation = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == current_user.organization_id,
                UserCorrelation.email == user_email
            ).first()

            if existing_correlation:
                existing_correlation.slack_user_id = slack_user_id
            else:
                correlation = UserCorrelation(
                    user_id=current_user.id,
                    organization_id=current_user.organization_id,
                    email=user_email,
                    slack_user_id=slack_user_id
                )
                db.add(correlation)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Slack integration connected successfully with bot token and webhook URL",
            "integration": {
                "id": integration.id,
                "slack_user_id": slack_user_id,
                "workspace_id": workspace_id,
                "has_webhook": True,
                "token_source": "manual",
                "user_email": user_email,
                "user_name": user_name,
                "total_channels": total_channels
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Slack integration: {str(e)}"
        )


@router.delete("/disconnect")
async def disconnect_slack(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Slack integration for current user.
    Handles both manual SlackIntegration and OAuth SlackWorkspaceMapping.
    """
    logger.info(f"Disconnect request from user {current_user.id} (email: {current_user.email})")

    # Check for manual SlackIntegration first
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()

    logger.info(f"Manual integration found: {integration is not None}")

    # If no manual integration, check for OAuth workspace mapping
    workspace_mapping = None
    if not integration:
        workspace_mapping = db.query(SlackWorkspaceMapping).filter(
            SlackWorkspaceMapping.owner_user_id == current_user.id,
            SlackWorkspaceMapping.status == 'active'
        ).first()

        logger.info(f"OAuth workspace mapping found: {workspace_mapping is not None}")

    if not integration and not workspace_mapping:
        logger.warning(f"No Slack integration found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found"
        )
    
    try:
        # Remove Slack data from user correlations (organization-scoped)
        if current_user.organization_id:
            correlations = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == current_user.organization_id
            ).all()
        else:
            # Beta mode: use user_id
            correlations = db.query(UserCorrelation).filter(
                UserCorrelation.user_id == current_user.id
            ).all()

        for correlation in correlations:
            correlation.slack_user_id = None

        # Delete the integration or workspace mapping
        if integration:
            db.delete(integration)
        elif workspace_mapping:
            workspace_mapping.status = 'disconnected'
            # Note: We mark as disconnected rather than deleting to preserve history

        db.commit()

        return {
            "success": True,
            "message": "Slack integration disconnected successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect Slack integration: {str(e)}"
        )


# Survey-related models and endpoints
class SlackSurveySubmission(BaseModel):
    """Model for Slack burnout survey submissions."""
    analysis_id: int
    user_email: str
    self_reported_score: int  # 0-100 scale
    energy_level: int  # 1-5 scale
    stress_factors: list[str]  # Array of stress factors
    personal_circumstances: str = None  # 'significantly', 'somewhat', 'no', 'prefer_not_say'
    additional_comments: str = ""
    is_anonymous: bool = False


class SlackModalPayload(BaseModel):
    """Model for Slack modal interaction payloads."""
    trigger_id: str
    user_id: str
    team_id: str
    user_email: str = ""


@router.get("/debug/correlation")
async def debug_user_correlation(
    email: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check if a user exists in user_correlations table.
    If email not provided, checks current user's organization for all correlations.
    """
    try:
        if email:
            # Check specific email
            correlation = db.query(UserCorrelation).filter(
                UserCorrelation.email == email.lower()
            ).first()

            if correlation:
                return {
                    "found": True,
                    "email": correlation.email,
                    "name": correlation.name,
                    "slack_user_id": correlation.slack_user_id,
                    "github_username": correlation.github_username,
                    "rootly_email": correlation.rootly_email,
                    "pagerduty_user_id": correlation.pagerduty_user_id,
                    "user_id": correlation.user_id,
                    "created_at": correlation.created_at.isoformat() if correlation.created_at else None
                }
            else:
                return {
                    "found": False,
                    "email": email,
                    "message": f"No user_correlation found for {email}"
                }
        else:
            # Show all correlations for current user's organization
            correlations = db.query(UserCorrelation).filter(
                UserCorrelation.organization_id == current_user.organization_id
            ).all()

            return {
                "total_correlations": len(correlations),
                "correlations": [
                    {
                        "email": c.email,
                        "name": c.name,
                        "slack_user_id": c.slack_user_id,
                        "github_username": c.github_username
                    }
                    for c in correlations
                ]
            }

    except Exception as e:
        logging.error(f"Error debugging correlation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.get("/user/me")
async def get_slack_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Slack information including email.
    Useful for debugging user correlation issues.
    """
    try:
        # Get user's Slack integration
        slack_integration = db.query(SlackIntegration).filter(
            SlackIntegration.user_id == current_user.id
        ).first()

        if not slack_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Slack integration found. Please connect Slack first."
            )

        # Decrypt token
        slack_token = decrypt_token(slack_integration.slack_token)

        # Call Slack API to get user info
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/users.info",
                params={"user": slack_integration.slack_user_id},
                headers={"Authorization": f"Bearer {slack_token}"}
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch Slack user info"
                )

            data = response.json()

            if not data.get("ok"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Slack API error: {data.get('error', 'Unknown error')}"
                )

            user_info = data.get("user", {})
            profile = user_info.get("profile", {})

            return {
                "slack_user_id": slack_integration.slack_user_id,
                "workspace_id": slack_integration.workspace_id,
                "real_name": user_info.get("real_name"),
                "display_name": profile.get("display_name"),
                "email": profile.get("email"),  # This is what you need!
                "is_admin": user_info.get("is_admin"),
                "is_owner": user_info.get("is_owner")
            }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching Slack user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Slack user info: {str(e)}"
        )


@router.post("/commands/burnout-survey")
async def handle_burnout_survey_command(
    token: str = Form(...),
    team_id: str = Form(...),
    team_domain: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    command: str = Form(...),
    text: str = Form(""),
    response_url: str = Form(...),
    trigger_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle /burnout-survey slash command from Slack.
    Opens a modal with the 3-question burnout survey.
    """
    try:
        # Extract user info from Slack command form data
        # user_id, trigger_id, team_id are already available as form parameters

        if not user_id or not trigger_id:
            return {"text": "⚠️ Sorry, there was an error processing your request. Please try again."}

        # Find workspace mapping to get organization
        workspace_mapping = db.query(SlackWorkspaceMapping).filter(
            SlackWorkspaceMapping.workspace_id == team_id,
            SlackWorkspaceMapping.status == 'active'
        ).first()

        if not workspace_mapping:
            return {
                "text": "⚠️ This Slack workspace is not registered with any organization. Please ask your admin to connect this workspace through the dashboard.",
                "response_type": "ephemeral"
            }

        # Get organization
        organization = workspace_mapping.organization
        if not organization:
            return {
                "text": f"⚠️ Workspace is registered but not linked to an organization (mapping org_id: {workspace_mapping.organization_id}). Please contact support.",
                "response_type": "ephemeral"
            }

        if organization.status != 'active':
            return {
                "text": f"⚠️ Organization '{organization.name}' has status '{organization.status}' (needs 'active'). Please contact support.",
                "response_type": "ephemeral"
            }

        # Find the current active analysis FOR THIS ORGANIZATION (optional - surveys can be submitted without analysis)
        latest_analysis = db.query(Analysis).filter(
            Analysis.status == "completed",
            Analysis.organization_id == organization.id
        ).order_by(Analysis.created_at.desc()).first()

        # Check if user is in the organization roster (ORGANIZATION-SCOPED)
        # Use organization_id directly for multi-tenancy support
        user_correlation = db.query(UserCorrelation).filter(
            UserCorrelation.slack_user_id == user_id,
            UserCorrelation.organization_id == organization.id
        ).first()

        # If not found by slack_user_id, try to get Slack email and match by email
        if not user_correlation:
            # Try to fetch user's email from Slack API
            try:
                # Get workspace bot token from SlackIntegration
                slack_integration = db.query(SlackIntegration).filter(
                    SlackIntegration.workspace_id == team_id
                ).first()

                if slack_integration and slack_integration.slack_token:
                    import httpx
                    slack_token = decrypt_token(slack_integration.slack_token)

                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://slack.com/api/users.info",
                            params={"user": user_id},
                            headers={"Authorization": f"Bearer {slack_token}"}
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data.get("ok"):
                                user_email = data.get("user", {}).get("profile", {}).get("email")

                                if user_email:
                                    # Try to find by email using organization_id for multi-tenancy
                                    user_correlation = db.query(UserCorrelation).filter(
                                        UserCorrelation.email == user_email.lower(),
                                        UserCorrelation.organization_id == organization.id
                                    ).first()

                                    # If found, update with Slack user ID for future lookups
                                    if user_correlation:
                                        user_correlation.slack_user_id = user_id
                                        db.commit()
                                        logging.info(f"Auto-populated Slack user ID for {user_email}")
            except Exception as e:
                logging.error(f"Error fetching Slack user email: {str(e)}")
                # Continue without Slack email lookup

        if not user_correlation:
            return {
                "text": f"👋 Hi! I couldn't find you in the {organization.name} team roster. Please ask your manager to ensure you're included in the burnout analysis.",
                "response_type": "ephemeral"
            }

        # Check for existing survey response today
        from datetime import datetime
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        existing_report = db.query(UserBurnoutReport).filter(
            UserBurnoutReport.user_id == user_correlation.user_id,
            UserBurnoutReport.organization_id == organization.id,
            UserBurnoutReport.submitted_at >= today_start
        ).first()

        # Create and open interactive Slack modal
        # Pass organization_id and optional analysis_id
        modal_view = create_burnout_survey_modal(
            organization_id=organization.id,
            user_id=user_correlation.user_id,
            analysis_id=latest_analysis.id if latest_analysis else None,
            is_update=bool(existing_report)
        )

        # Get workspace bot token to open modal
        slack_integration = db.query(SlackIntegration).filter(
            SlackIntegration.workspace_id == team_id
        ).first()

        if not slack_integration or not slack_integration.slack_token:
            # Fallback to old button-based approach if no token
            survey_url = f"{settings.FRONTEND_URL}/survey?user={user_correlation.user_id}"
            if latest_analysis:
                survey_url += f"&analysis={latest_analysis.id}"

            return {
                "text": "📝 Opening your 2-minute burnout survey...",
                "response_type": "ephemeral",
                "attachments": [{
                    "fallback": "Burnout Survey",
                    "color": "good",
                    "actions": [{
                        "type": "button",
                        "text": "Open Survey",
                        "url": survey_url,
                        "style": "primary"
                    }]
                }]
            }

        # Open modal using Slack API
        import httpx
        slack_token = decrypt_token(slack_integration.slack_token)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/views.open",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "trigger_id": trigger_id,
                    "view": modal_view
                }
            )

            result = response.json()

            if not result.get("ok"):
                logging.error(f"Failed to open modal: {result.get('error')}")
                # Fallback to button approach
                survey_url = f"{settings.FRONTEND_URL}/survey?user={user_correlation.user_id}"
                if latest_analysis:
                    survey_url += f"&analysis={latest_analysis.id}"

                return {
                    "text": "📝 Click below to open your burnout survey:",
                    "response_type": "ephemeral",
                    "attachments": [{
                        "fallback": "Burnout Survey",
                        "actions": [{
                            "type": "button",
                            "text": "Open Survey",
                            "url": survey_url,
                            "style": "primary"
                        }]
                    }]
                }

        # Modal opened successfully - return 200 with no body
        # Slack will show the modal, so no command response needed
        from fastapi.responses import Response
        return Response(status_code=200)

    except Exception as e:
        logging.error(f"Error handling burnout survey command: {str(e)}")
        return {
            "text": "⚠️ Sorry, there was an error opening the survey. Please try again or contact your manager.",
            "response_type": "ephemeral"
        }


@router.post("/interactions")
async def handle_slack_interactions(
    payload: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle Slack interactive component submissions (modals, buttons, etc).
    This is called when user submits the burnout survey modal.
    """
    try:
        import json
        logging.info(f"Received Slack interaction payload: {payload[:500]}...")  # Log first 500 chars
        data = json.loads(payload)
        logging.info(f"Parsed interaction type: {data.get('type')}")

        interaction_type = data.get("type")

        # Handle button clicks (e.g., "Take Survey" button from DM)
        if interaction_type == "block_actions":
            actions = data.get("actions", [])
            for action in actions:
                if action.get("action_id") == "open_burnout_survey":
                    # Extract user and org IDs from button value
                    value = action.get("value", "")
                    try:
                        user_id, organization_id = map(int, value.split("|"))
                    except:
                        return {"text": "Invalid survey data"}

                    # Get user's Slack ID
                    slack_user = data.get("user", {})
                    slack_user_id = slack_user.get("id")
                    trigger_id = data.get("trigger_id")

                    # Get organization and check for existing report
                    from datetime import datetime
                    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                    existing_report = db.query(UserBurnoutReport).filter(
                        UserBurnoutReport.user_id == user_id,
                        UserBurnoutReport.organization_id == organization_id,
                        UserBurnoutReport.submitted_at >= today_start
                    ).first()

                    # Open modal
                    modal_view = create_burnout_survey_modal(
                        organization_id=organization_id,
                        user_id=user_id,
                        analysis_id=None,  # No specific analysis for daily check-ins
                        is_update=bool(existing_report)
                    )

                    # Get Slack token to open modal
                    team_id = data.get("team", {}).get("id")
                    slack_integration = db.query(SlackIntegration).filter(
                        SlackIntegration.workspace_id == team_id
                    ).first()

                    if slack_integration and slack_integration.slack_token:
                        import httpx
                        slack_token = decrypt_token(slack_integration.slack_token)

                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                "https://slack.com/api/views.open",
                                headers={"Authorization": f"Bearer {slack_token}"},
                                json={"trigger_id": trigger_id, "view": modal_view}
                            )

                            result = response.json()
                            if not result.get("ok"):
                                logging.error(f"Failed to open modal: {result.get('error')}")
                                return {"text": "Sorry, couldn't open the survey. Please try again."}

                    # Acknowledge the button click
                    return {"response_action": "clear"}

        # Handle modal submission
        if interaction_type == "view_submission":
            view = data.get("view", {})
            callback_id = view.get("callback_id")

            if callback_id == "burnout_survey_modal":
                # Extract form values from modal
                values = view.get("state", {}).get("values", {})

                # Get burnout score (0-100 scale) - already in correct format
                self_reported_score = int(values.get("burnout_score_block", {}).get("burnout_score_input", {}).get("selected_option", {}).get("value", "50"))

                # Get energy level (radio buttons) - convert to 1-5 integer
                energy_level_str = values.get("energy_level_block", {}).get("energy_level_input", {}).get("selected_option", {}).get("value", "moderate")
                energy_level_map = {
                    "very_low": 1,
                    "low": 2,
                    "moderate": 3,
                    "high": 4,
                    "very_high": 5
                }
                energy_level = energy_level_map.get(energy_level_str, 3)

                # Get stress factors (checkboxes)
                stress_factors_options = values.get("stress_factors_block", {}).get("stress_factors_input", {}).get("selected_options", [])
                stress_factors = [opt.get("value") for opt in stress_factors_options]

                # Get personal circumstances (optional)
                personal_circumstances = values.get("personal_circumstances_block", {}).get("personal_circumstances_input", {}).get("selected_option", {}).get("value")

                # Get optional comments
                comments = values.get("comments_block", {}).get("comments_input", {}).get("value", "")

                # Extract user and organization IDs from private_metadata
                metadata = json.loads(view.get("private_metadata", "{}"))
                user_id = metadata.get("user_id")
                organization_id = metadata.get("organization_id")
                analysis_id = metadata.get("analysis_id")  # Optional - may be None

                if not user_id or not organization_id:
                    return {"response_action": "errors", "errors": {"comments_block": "Invalid survey data"}}

                # Check if user already submitted today (within last 24 hours)
                from datetime import datetime, timedelta
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

                existing_report = db.query(UserBurnoutReport).filter(
                    UserBurnoutReport.user_id == user_id,
                    UserBurnoutReport.organization_id == organization_id,
                    UserBurnoutReport.submitted_at >= today_start
                ).order_by(UserBurnoutReport.submitted_at.desc()).first()

                is_update = False
                if existing_report:
                    # Update existing report
                    existing_report.self_reported_score = self_reported_score
                    existing_report.energy_level = energy_level
                    existing_report.stress_factors = stress_factors
                    existing_report.personal_circumstances = personal_circumstances
                    existing_report.additional_comments = comments
                    existing_report.submitted_via = 'slack'
                    existing_report.analysis_id = analysis_id  # Update linked analysis if provided
                    existing_report.updated_at = datetime.utcnow()
                    logging.info(f"Updated existing report ID {existing_report.id} for user {user_id}")
                    is_update = True
                else:
                    # Create new burnout report
                    new_report = UserBurnoutReport(
                        user_id=user_id,
                        organization_id=organization_id,
                        analysis_id=analysis_id,  # Optional - may be None
                        self_reported_score=self_reported_score,
                        energy_level=energy_level,
                        stress_factors=stress_factors,
                        personal_circumstances=personal_circumstances,
                        additional_comments=comments,
                        submitted_via='slack',
                        submitted_at=datetime.utcnow()
                    )
                    db.add(new_report)
                    logging.info(f"Created new report for user {user_id}")

                db.commit()

                # Notify org admins about survey submission (only for new submissions, not updates)
                if not is_update:
                    try:
                        notification_service = NotificationService(db)
                        # Get user info for notification
                        user = db.query(User).filter(User.id == user_id).first()
                        if user and analysis_id:
                            # Get analysis for notification context
                            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
                            if analysis:
                                notification_service.create_survey_submission_notification(
                                    user=user,
                                    organization_id=organization_id,
                                    analysis=analysis
                                )
                                logging.info(f"Created survey submission notifications for org {organization_id}")
                    except Exception as e:
                        logging.error(f"Failed to create survey submission notifications: {str(e)}")
                        # Don't fail the survey submission if notification fails

                # Return success response with different message for updates
                if is_update:
                    success_message = f"✅ *Survey updated successfully*\n\n_You already submitted a survey today. Your burnout score has been updated to {self_reported_score}/100._\n\nYour updated feedback helps us:\n• Validate automated burnout detection\n• Catch stress before it impacts you\n• Make data-driven team improvements\n\nThank you for contributing to a healthier team."
                else:
                    success_message = "✅ *Survey submitted successfully*\n\nYour feedback helps us:\n• Validate automated burnout detection\n• Catch stress before it impacts you\n• Make data-driven team improvements\n\nThank you for contributing to a healthier team."

                return {
                    "response_action": "update",
                    "view": {
                        "type": "modal",
                        "title": {"type": "plain_text", "text": "Thank You"},
                        "close": {"type": "plain_text", "text": "Close"},
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": success_message
                                }
                            }
                        ]
                    }
                }

        # For other interaction types, just acknowledge
        return {}

    except Exception as e:
        logging.error(f"Error handling Slack interaction: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {
            "response_action": "errors",
            "errors": {
                "comments_block": f"Error: {str(e)}"
            }
        }


@router.post("/survey/submit")
async def submit_slack_burnout_survey(
    submission: SlackSurveySubmission,
    db: Session = Depends(get_db)
):
    """
    Submit burnout survey response from Slack.
    """
    try:
        # Find the user by email
        user_correlation = db.query(UserCorrelation).filter(
            UserCorrelation.user_email == submission.user_email.lower()
        ).first()

        if not user_correlation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in team roster"
            )

        # Validate analysis exists
        analysis = db.query(Analysis).filter(
            Analysis.id == submission.analysis_id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )

        # Check for duplicate submission
        existing_report = db.query(UserBurnoutReport).filter(
            UserBurnoutReport.user_id == user_correlation.user_id,
            UserBurnoutReport.analysis_id == submission.analysis_id
        ).first()

        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Survey already submitted for this analysis"
            )

        # Create new burnout report
        new_report = UserBurnoutReport(
            user_id=user_correlation.user_id,
            analysis_id=submission.analysis_id,
            self_reported_score=submission.self_reported_score,
            energy_level=submission.energy_level,
            stress_factors=submission.stress_factors,
            personal_circumstances=submission.personal_circumstances,
            additional_comments=submission.additional_comments,
            submitted_via='slack',
            is_anonymous=submission.is_anonymous
        )

        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return {
            "success": True,
            "message": "Survey submitted successfully!",
            "report_id": new_report.id,
            "submitted_at": new_report.submitted_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error submitting burnout survey: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit survey"
        )


@router.get("/survey/status/{analysis_id}")
async def get_team_survey_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get team survey response status for an analysis (manager view).
    """
    try:
        # Validate analysis exists and belongs to current user
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id
        ).first()

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )

        # Get all survey responses for this analysis
        survey_responses = db.query(UserBurnoutReport).filter(
            UserBurnoutReport.analysis_id == analysis_id
        ).all()

        # Get team members from the analysis results
        team_members = []
        if analysis.results and isinstance(analysis.results, dict):
            team_analysis = analysis.results.get('team_analysis', {})
            members = team_analysis.get('members', [])
            team_members = [member.get('user_email', '').lower() for member in members if member.get('user_email')]

        # Calculate response statistics
        total_members = len(team_members)
        responses_collected = len(survey_responses)
        response_rate = (responses_collected / total_members * 100) if total_members > 0 else 0

        # Identify non-responders
        responded_emails = {
            db.query(UserCorrelation).filter(
                UserCorrelation.user_id == response.user_id
            ).first().user_email.lower()
            for response in survey_responses
        }

        non_responders = [email for email in team_members if email not in responded_emails]

        return {
            "analysis_id": analysis_id,
            "total_members": total_members,
            "responses_collected": responses_collected,
            "response_rate": round(response_rate, 1),
            "non_responders": non_responders,
            "survey_responses": [
                {
                    "user_email": db.query(UserCorrelation).filter(
                        UserCorrelation.user_id == response.user_id
                    ).first().user_email,
                    "self_reported_score": response.self_reported_score,
                    "energy_level": response.energy_level,
                    "stress_factors": response.stress_factors,
                    "submitted_at": response.submitted_at.isoformat(),
                    "submitted_via": response.submitted_via,
                    "is_anonymous": response.is_anonymous
                }
                for response in survey_responses
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting survey status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get survey status"
        )


def create_burnout_survey_modal(organization_id: int, user_id: int, analysis_id: int = None, is_update: bool = False) -> dict:
    """
    Create Slack modal view for burnout survey.

    Args:
        organization_id: Organization ID (required)
        user_id: User ID (required)
        analysis_id: Analysis ID (optional - for linking survey to specific analysis)
        is_update: Whether this is updating an existing survey today
    """
    import json

    # Store metadata to be retrieved on submission
    metadata = {
        "user_id": user_id,
        "organization_id": organization_id,
        "analysis_id": analysis_id
    }

    modal_title = "Update Check-in" if is_update else "Burnout Check-in"
    intro_text = "📋 *Update your burnout check-in*\n\nYou already submitted today. Your previous response will be updated." if is_update else "📋 *2-minute burnout check-in*\n\nYour responses help improve team health and workload distribution. All responses are confidential."

    return {
        "type": "modal",
        "callback_id": "burnout_survey_modal",
        "private_metadata": json.dumps(metadata),
        "title": {
            "type": "plain_text",
            "text": modal_title,
            "emoji": True
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit",
            "emoji": True
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": intro_text
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "input",
                "block_id": "burnout_score_block",
                "element": {
                    "type": "static_select",
                    "action_id": "burnout_score_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select level (0-10)"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "0 - Not at all"}, "value": "0"},
                        {"text": {"type": "plain_text", "text": "1 - Very slightly"}, "value": "10"},
                        {"text": {"type": "plain_text", "text": "2 - Slightly"}, "value": "20"},
                        {"text": {"type": "plain_text", "text": "3 - Somewhat"}, "value": "30"},
                        {"text": {"type": "plain_text", "text": "4 - Moderately"}, "value": "40"},
                        {"text": {"type": "plain_text", "text": "5 - Considerably"}, "value": "50"},
                        {"text": {"type": "plain_text", "text": "6 - Quite a bit"}, "value": "60"},
                        {"text": {"type": "plain_text", "text": "7 - Very much"}, "value": "70"},
                        {"text": {"type": "plain_text", "text": "8 - Extremely"}, "value": "80"},
                        {"text": {"type": "plain_text", "text": "9 - Almost completely"}, "value": "90"},
                        {"text": {"type": "plain_text", "text": "10 - Completely"}, "value": "100"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Question 1: How burned out do you feel right now?"
                }
            },
            {
                "type": "input",
                "block_id": "energy_level_block",
                "element": {
                    "type": "static_select",
                    "action_id": "energy_level_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select energy level"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Very Low"}, "value": "very_low"},
                        {"text": {"type": "plain_text", "text": "Low"}, "value": "low"},
                        {"text": {"type": "plain_text", "text": "Moderate"}, "value": "moderate"},
                        {"text": {"type": "plain_text", "text": "High"}, "value": "high"},
                        {"text": {"type": "plain_text", "text": "Very High"}, "value": "very_high"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Question 2: What's your energy level this week?"
                }
            },
            {
                "type": "input",
                "block_id": "stress_factors_block",
                "element": {
                    "type": "multi_static_select",
                    "action_id": "stress_factors_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select stress factors"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Incident volume"}, "value": "incident_volume"},
                        {"text": {"type": "plain_text", "text": "Work hours"}, "value": "work_hours"},
                        {"text": {"type": "plain_text", "text": "On-call burden"}, "value": "on_call_burden"},
                        {"text": {"type": "plain_text", "text": "Workload"}, "value": "workload"},
                        {"text": {"type": "plain_text", "text": "Team dynamics"}, "value": "team_dynamics"},
                        {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Question 3: Main stress factors? (select all that apply)"
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "personal_circumstances_block",
                "element": {
                    "type": "static_select",
                    "action_id": "personal_circumstances_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select option"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Yes, significantly"}, "value": "significantly"},
                        {"text": {"type": "plain_text", "text": "Yes, somewhat"}, "value": "somewhat"},
                        {"text": {"type": "plain_text", "text": "No, this is work-related"}, "value": "no"},
                        {"text": {"type": "plain_text", "text": "Prefer not to say"}, "value": "prefer_not_say"}
                    ]
                },
                "label": {
                    "type": "plain_text",
                    "text": "Question 4: Are personal circumstances (e.g., sleep, family matters) affecting how you feel today?"
                },
                "optional": True
            },
            {
                "type": "input",
                "block_id": "comments_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "comments_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Anything else affecting your stress? (optional)"
                    },
                    "multiline": True
                },
                "label": {
                    "type": "plain_text",
                    "text": "Additional Comments (Optional)"
                },
                "optional": True
            }
        ]
    }


@router.get("/workspace/status")
async def get_workspace_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Diagnostic endpoint to check Slack workspace registration status.
    Returns detailed information about workspace mappings and integrations.
    """
    try:
        from ...models import Organization

        # Check for workspace mappings
        workspace_mappings = db.query(SlackWorkspaceMapping).filter(
            SlackWorkspaceMapping.owner_user_id == current_user.id
        ).all()

        # Check for user's Slack integrations
        slack_integrations = db.query(SlackIntegration).filter(
            SlackIntegration.user_id == current_user.id
        ).all()

        # Check for organization-level mappings
        org_mappings = []
        if current_user.organization_id:
            org_mappings = db.query(SlackWorkspaceMapping).filter(
                SlackWorkspaceMapping.organization_id == current_user.organization_id
            ).all()

        # Check organization status
        organization_info = None
        if current_user.organization_id:
            org = db.query(Organization).filter(
                Organization.id == current_user.organization_id
            ).first()
            if org:
                organization_info = {
                    "id": org.id,
                    "name": org.name,
                    "status": org.status if hasattr(org, 'status') else "unknown"
                }

        return {
            "user_workspace_mappings": [
                {
                    "workspace_id": m.workspace_id,
                    "workspace_name": m.workspace_name,
                    "organization_id": m.organization_id,
                    "status": m.status,
                    "created_at": m.registered_at.isoformat() if m.registered_at else None
                }
                for m in workspace_mappings
            ],
            "organization_workspace_mappings": [
                {
                    "workspace_id": m.workspace_id,
                    "workspace_name": m.workspace_name,
                    "owner_user_id": m.owner_user_id,
                    "organization_id": m.organization_id,
                    "status": m.status
                }
                for m in org_mappings
            ],
            "slack_integrations": [
                {
                    "workspace_id": si.workspace_id,
                    "token_source": si.token_source,
                    "connected_at": si.created_at.isoformat() if si.created_at else None
                }
                for si in slack_integrations
            ],
            "current_user": {
                "id": current_user.id,
                "email": current_user.email,
                "organization_id": current_user.organization_id
            },
            "organization": organization_info,
            "diagnosis": {
                "has_workspace_mapping": len(workspace_mappings) > 0 or len(org_mappings) > 0,
                "has_slack_integration": len(slack_integrations) > 0,
                "organization_exists": organization_info is not None,
                "organization_active": organization_info.get("status") == "active" if organization_info else False,
                "issue": None if (len(workspace_mappings) > 0 or len(org_mappings) > 0) else
                        "No workspace mapping found. Slack /burnout-survey command will not work."
            }
        }

    except Exception as e:
        logging.error(f"Error checking workspace status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking workspace status: {str(e)}"
        )


@router.post("/workspace/register")
async def register_workspace_manual(
    workspace_id: str = Form(...),
    workspace_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually register a Slack workspace that wasn't properly registered during OAuth.
    This fixes the "workspace not registered" error for /burnout-survey command.
    """
    try:
        # Check if workspace mapping already exists
        existing_mapping = db.query(SlackWorkspaceMapping).filter(
            SlackWorkspaceMapping.workspace_id == workspace_id
        ).first()

        if existing_mapping:
            # Update existing mapping
            existing_mapping.workspace_name = workspace_name
            existing_mapping.organization_id = current_user.organization_id
            existing_mapping.status = 'active'
            # Don't set updated_at manually - SQLAlchemy handles it with onupdate
            db.commit()

            return {
                "success": True,
                "message": "Workspace mapping updated successfully",
                "mapping": {
                    "workspace_id": existing_mapping.workspace_id,
                    "workspace_name": existing_mapping.workspace_name,
                    "organization_id": existing_mapping.organization_id,
                    "status": existing_mapping.status
                }
            }
        else:
            # Create new mapping
            # Don't pass created_at/updated_at - they're auto-generated by server_default
            new_mapping = SlackWorkspaceMapping(
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                organization_id=current_user.organization_id,
                owner_user_id=current_user.id,
                status='active'
            )
            db.add(new_mapping)
            db.commit()

            return {
                "success": True,
                "message": "Workspace registered successfully! /burnout-survey command should now work.",
                "mapping": {
                    "workspace_id": new_mapping.workspace_id,
                    "workspace_name": new_mapping.workspace_name,
                    "organization_id": new_mapping.organization_id,
                    "status": new_mapping.status
                }
            }

    except Exception as e:
        db.rollback()
        logging.error(f"Error registering workspace: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering workspace: {str(e)}"
        )