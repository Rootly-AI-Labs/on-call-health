"""
Slack integration API endpoints for OAuth and data collection.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import secrets
import json
import logging
from cryptography.fernet import Fernet
import base64
from datetime import datetime
from pydantic import BaseModel

from ...models import get_db, User, SlackIntegration, UserCorrelation
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
        logging.getLogger(__name__).error(f"Slack API exception for channels: {channels_error}")
    
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