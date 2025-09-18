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

from ...models import get_db, User, SlackIntegration, UserCorrelation, UserBurnoutReport, Analysis
from ...auth.dependencies import get_current_user
from ...auth.integration_oauth import slack_integration_oauth
from ...core.config import settings

router = APIRouter(prefix="/slack", tags=["slack-integration"])

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

@router.get("/callback")
async def slack_callback(
    code: str,
    state: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handle Slack OAuth callback and store integration.
    """
    try:
        # Exchange code for token
        token_data = await slack_integration_oauth.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Slack"
            )
        
        # Get auth info and user ID
        auth_info = await slack_integration_oauth.test_auth(access_token)
        slack_user_id = auth_info.get("user_id")
        workspace_id = auth_info.get("team_id")
        
        if not slack_user_id or not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get Slack user ID or workspace ID"
            )
        
        # Get user info
        user_info = await slack_integration_oauth.get_user_info(access_token, slack_user_id)
        user_profile = user_info.get("user", {}).get("profile", {})
        user_email = user_profile.get("email")
        
        # Encrypt the token
        encrypted_token = encrypt_token(access_token)
        
        # Check if integration already exists
        existing_integration = db.query(SlackIntegration).filter(
            SlackIntegration.user_id == current_user.id
        ).first()
        
        if existing_integration:
            # Update existing integration
            existing_integration.slack_token = encrypted_token
            existing_integration.slack_user_id = slack_user_id
            existing_integration.workspace_id = workspace_id
            existing_integration.token_source = "oauth"
            existing_integration.updated_at = datetime.utcnow()
            integration = existing_integration
        else:
            # Create new integration
            integration = SlackIntegration(
                user_id=current_user.id,
                slack_token=encrypted_token,
                slack_user_id=slack_user_id,
                workspace_id=workspace_id,
                token_source="oauth"
            )
            db.add(integration)
        
        # Update user correlations if email is available
        if user_email:
            existing_correlation = db.query(UserCorrelation).filter(
                UserCorrelation.user_id == current_user.id,
                UserCorrelation.email == user_email
            ).first()
            
            if existing_correlation:
                existing_correlation.slack_user_id = slack_user_id
            else:
                correlation = UserCorrelation(
                    user_id=current_user.id,
                    email=user_email,
                    slack_user_id=slack_user_id
                )
                db.add(correlation)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Slack integration connected successfully",
            "integration": {
                "id": integration.id,
                "slack_user_id": slack_user_id,
                "workspace_id": workspace_id,
                "user_email": user_email,
                "user_name": user_profile.get("real_name") or user_profile.get("display_name")
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
    """
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
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
    
    try:
        # Decrypt token and get preview
        access_token = decrypt_token(integration.slack_token)
        token_preview = f"...{access_token[-4:]}" if access_token else None
        
        # Get webhook preview if available
        if integration.webhook_url:
            webhook_preview = f"...{integration.webhook_url[-4:]}"
        
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
    
    response_data = {
        "connected": True,
        "integration": {
            "id": integration.id,
            "slack_user_id": integration.slack_user_id,
            "workspace_id": integration.workspace_id,
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
            "webhook_preview": webhook_preview
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
            existing_correlation = db.query(UserCorrelation).filter(
                UserCorrelation.user_id == current_user.id,
                UserCorrelation.email == user_email
            ).first()
            
            if existing_correlation:
                existing_correlation.slack_user_id = slack_user_id
            else:
                correlation = UserCorrelation(
                    user_id=current_user.id,
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
            existing_correlation = db.query(UserCorrelation).filter(
                UserCorrelation.user_id == current_user.id,
                UserCorrelation.email == user_email
            ).first()
            
            if existing_correlation:
                existing_correlation.slack_user_id = slack_user_id
            else:
                correlation = UserCorrelation(
                    user_id=current_user.id,
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
    """
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found"
        )
    
    try:
        # Remove Slack data from user correlations
        correlations = db.query(UserCorrelation).filter(
            UserCorrelation.user_id == current_user.id
        ).all()
        
        for correlation in correlations:
            correlation.slack_user_id = None
        
        # Delete the integration
        db.delete(integration)
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
    additional_comments: str = ""
    is_anonymous: bool = False


class SlackModalPayload(BaseModel):
    """Model for Slack modal interaction payloads."""
    trigger_id: str
    user_id: str
    team_id: str
    user_email: str = ""


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

        # Find the current active analysis
        latest_analysis = db.query(Analysis).filter(
            Analysis.status == "completed"
        ).order_by(Analysis.created_at.desc()).first()

        if not latest_analysis:
            return {
                "text": "📋 No active burnout analysis found. Your manager will start a new analysis soon!",
                "response_type": "ephemeral"
            }

        # Check if user already submitted survey for this analysis
        # First, try to find user by correlating Slack user_id to email
        user_correlation = db.query(UserCorrelation).filter(
            UserCorrelation.slack_user_id == user_id
        ).first()

        if not user_correlation:
            return {
                "text": "👋 Hi! I couldn't find you in our team roster. Please ask your manager to ensure you're included in the burnout analysis.",
                "response_type": "ephemeral"
            }

        # Check for existing survey response
        existing_report = db.query(UserBurnoutReport).filter(
            UserBurnoutReport.user_id == user_correlation.user_id,
            UserBurnoutReport.analysis_id == latest_analysis.id
        ).first()

        if existing_report:
            return {
                "text": f"✅ Thanks! You already completed the burnout survey on {existing_report.submitted_at.strftime('%B %d')}.\n\n"
                       f"Your responses help improve team health insights. 🌟",
                "response_type": "ephemeral"
            }

        # Create and return survey modal
        modal_view = create_burnout_survey_modal(latest_analysis.id, user_correlation.user_id)

        # In a real implementation, you would send this modal to Slack using their API
        # For now, return a simple response indicating the survey would open
        return {
            "text": "📝 Opening your 2-minute burnout survey...\n\n"
                   "This helps us:\n"
                   "• Validate our automated detection\n"
                   "• Catch stress before it impacts you\n"
                   "• Make data-driven team improvements",
            "response_type": "ephemeral",
            "attachments": [
                {
                    "fallback": "Burnout Survey",
                    "color": "good",
                    "fields": [
                        {
                            "title": "Quick Survey Questions:",
                            "value": "1. How burned out do you feel? (0-10 scale)\n"
                                   "2. What's your energy level? (Very Low to Very High)\n"
                                   "3. Main stress factors? (Select all that apply)",
                            "short": False
                        }
                    ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "Open Survey",
                            "url": f"{settings.FRONTEND_URL}/survey?analysis={latest_analysis.id}&user={user_correlation.user_id}",
                            "style": "primary"
                        }
                    ]
                }
            ]
        }

    except Exception as e:
        logging.error(f"Error handling burnout survey command: {str(e)}")
        return {
            "text": "⚠️ Sorry, there was an error opening the survey. Please try again or contact your manager.",
            "response_type": "ephemeral"
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


def create_burnout_survey_modal(analysis_id: int, user_id: int) -> dict:
    """
    Create Slack modal view for burnout survey.
    This would be used with Slack's views.open API in a real implementation.
    """
    return {
        "type": "modal",
        "callback_id": f"burnout_survey_{analysis_id}",
        "title": {
            "type": "plain_text",
            "text": "Burnout Check-in",
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
                    "text": "📋 *2-minute burnout check-in*\n\nYour responses help improve team health and workload distribution. All responses are confidential."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Question 1: How burned out do you feel right now?*"
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "burnout_score",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select level (0-10)",
                        "emoji": True
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
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Question 2: What's your energy level this week?*"
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "energy_level",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select energy level",
                        "emoji": True
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Very Low"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "Low"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "Moderate"}, "value": "3"},
                        {"text": {"type": "plain_text", "text": "High"}, "value": "4"},
                        {"text": {"type": "plain_text", "text": "Very High"}, "value": "5"}
                    ]
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Question 3: Main stress factors? (select all that apply)*"
                },
                "accessory": {
                    "type": "multi_static_select",
                    "action_id": "stress_factors",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select stress factors",
                        "emoji": True
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Incident volume"}, "value": "incident_volume"},
                        {"text": {"type": "plain_text", "text": "Work hours"}, "value": "work_hours"},
                        {"text": {"type": "plain_text", "text": "On-call burden"}, "value": "on_call_burden"},
                        {"text": {"type": "plain_text", "text": "Workload"}, "value": "workload"},
                        {"text": {"type": "plain_text", "text": "Team dynamics"}, "value": "team_dynamics"},
                        {"text": {"type": "plain_text", "text": "Other"}, "value": "other"}
                    ]
                }
            },
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "additional_comments",
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