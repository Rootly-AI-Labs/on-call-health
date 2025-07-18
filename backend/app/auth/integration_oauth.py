"""
OAuth providers for GitHub and Slack integrations.
These are specialized OAuth providers for data collection purposes.
"""
import httpx
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from urllib.parse import urlencode

from ..core.config import settings

class GitHubIntegrationOAuth:
    """GitHub OAuth provider for integration purposes."""
    
    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = f"{settings.FRONTEND_URL}/setup/github/callback"
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"
        self.emails_url = "https://api.github.com/user/emails"
        self.orgs_url = "https://api.github.com/user/orgs"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate GitHub OAuth authorization URL with integration scopes."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo read:user read:org",  # Broader scopes for data collection
            "state": state or ""
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange GitHub authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get GitHub user information."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.user_info_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        return response.json()
    
    async def get_all_emails(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all verified emails from GitHub."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.emails_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user emails"
            )
        
        emails = response.json()
        
        # Filter for verified emails and exclude noreply addresses
        verified_emails = [
            email for email in emails 
            if email.get("verified", False) and not email.get("email", "").endswith("noreply.github.com")
        ]
        
        return verified_emails
    
    async def get_organizations(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's GitHub organizations."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.orgs_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user organizations"
            )
        
        return response.json()
    
    async def test_permissions(self, access_token: str) -> Dict[str, Any]:
        """Test GitHub token permissions."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json"
        }
        
        permissions = {
            "user_access": False,
            "repo_access": False,
            "org_access": False,
            "errors": []
        }
        
        async with httpx.AsyncClient() as client:
            # Test user access
            try:
                response = await client.get(self.user_info_url, headers=headers)
                permissions["user_access"] = response.status_code == 200
            except Exception as e:
                permissions["errors"].append(f"User access test failed: {str(e)}")
            
            # Test repo access (try to list repos)
            try:
                response = await client.get("https://api.github.com/user/repos", headers=headers, params={"per_page": 1})
                permissions["repo_access"] = response.status_code == 200
            except Exception as e:
                permissions["errors"].append(f"Repo access test failed: {str(e)}")
            
            # Test org access
            try:
                response = await client.get(self.orgs_url, headers=headers)
                permissions["org_access"] = response.status_code == 200
            except Exception as e:
                permissions["errors"].append(f"Org access test failed: {str(e)}")
        
        return permissions


class SlackIntegrationOAuth:
    """Slack OAuth provider for integration purposes."""
    
    def __init__(self):
        self.client_id = settings.SLACK_CLIENT_ID
        self.client_secret = settings.SLACK_CLIENT_SECRET
        self.redirect_uri = f"{settings.FRONTEND_URL}/setup/slack/callback"
        self.auth_url = "https://slack.com/oauth/v2/authorize"
        self.token_url = "https://slack.com/api/oauth.v2.access"
        self.user_info_url = "https://slack.com/api/users.info"
        self.auth_test_url = "https://slack.com/api/auth.test"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Slack OAuth authorization URL with integration scopes."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "channels:history groups:history users:read conversations.history channels:read groups:read users:read.email",  # Scopes for comprehensive data collection
            "user_scope": "search:read",  # User-level scopes
            "state": state or ""
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange Slack authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        result = response.json()
        if not result.get("ok", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slack OAuth error: {result.get('error', 'Unknown error')}"
            )
        
        return result
    
    async def get_user_info(self, access_token: str, user_id: str) -> Dict[str, Any]:
        """Get Slack user information."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        params = {"user": user_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.user_info_url, headers=headers, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        result = response.json()
        if not result.get("ok", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slack API error: {result.get('error', 'Unknown error')}"
            )
        
        return result
    
    async def test_auth(self, access_token: str) -> Dict[str, Any]:
        """Test Slack token and get basic info."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.auth_test_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to test auth"
            )
        
        result = response.json()
        if not result.get("ok", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slack auth test failed: {result.get('error', 'Unknown error')}"
            )
        
        return result
    
    async def test_permissions(self, access_token: str) -> Dict[str, Any]:
        """Test Slack token permissions."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        permissions = {
            "channels_access": False,
            "users_access": False,
            "workspace_access": False,
            "conversations_history": False,
            "channels_history": False,
            "groups_history": False,
            "users_conversations": False,
            "errors": []
        }
        
        async with httpx.AsyncClient() as client:
            # Test auth (basic workspace access)
            try:
                response = await client.get(self.auth_test_url, headers=headers)
                result = response.json()
                permissions["workspace_access"] = result.get("ok", False)
                if not permissions["workspace_access"]:
                    permissions["errors"].append(f"Workspace access failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                permissions["errors"].append(f"Workspace access test failed: {str(e)}")
            
            # Test channels access
            try:
                response = await client.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 1})
                result = response.json()
                permissions["channels_access"] = result.get("ok", False)
                if not permissions["channels_access"]:
                    permissions["errors"].append(f"Channels access failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                permissions["errors"].append(f"Channels access test failed: {str(e)}")
            
            # Test users access  
            try:
                response = await client.get("https://slack.com/api/users.list", headers=headers, params={"limit": 1})
                result = response.json()
                permissions["users_access"] = result.get("ok", False)
                if not permissions["users_access"]:
                    permissions["errors"].append(f"Users access failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                permissions["errors"].append(f"Users access test failed: {str(e)}")
            
            # Test conversations history access (required for message counting)
            try:
                # Get channels where bot is a member to test history access
                channels_response = await client.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 100, "types": "public_channel"})
                channels_result = channels_response.json()
                if channels_result.get("ok") and channels_result.get("channels"):
                    # Find a channel where the bot is a member
                    bot_channels = [ch for ch in channels_result["channels"] if ch.get("is_member", False)]
                    
                    if bot_channels:
                        channel_id = bot_channels[0]["id"]
                        
                        # Test conversations.history API
                        response = await client.get("https://slack.com/api/conversations.history", headers=headers, params={"channel": channel_id, "limit": 1})
                        result = response.json()
                        permissions["conversations_history"] = result.get("ok", False)
                        permissions["channels_history"] = result.get("ok", False)  # Set both to same value
                        if not permissions["conversations_history"]:
                            permissions["errors"].append(f"Conversations history access failed: {result.get('error', 'Unknown error')}")
                    else:
                        permissions["errors"].append("Bot is not a member of any channels. Add bot to channels to enable history access.")
                else:
                    permissions["errors"].append("No channels available to test history access")
            except Exception as e:
                permissions["errors"].append(f"Conversations history test failed: {str(e)}")
            
            # Test users.conversations access (required for getting user's channels)
            try:
                # Try to get user's conversations (this requires auth.test to get user_id first)
                auth_response = await client.get("https://slack.com/api/auth.test", headers=headers)
                auth_result = auth_response.json()
                if auth_result.get("ok") and auth_result.get("user_id"):
                    user_id = auth_result["user_id"]
                    
                    response = await client.get("https://slack.com/api/users.conversations", headers=headers, params={"user": user_id, "limit": 1})
                    result = response.json()
                    permissions["users_conversations"] = result.get("ok", False)
                    if not permissions["users_conversations"]:
                        permissions["errors"].append(f"Users conversations access failed: {result.get('error', 'Unknown error')}")
                else:
                    permissions["errors"].append("Could not get user ID for conversations test")
            except Exception as e:
                permissions["errors"].append(f"Users conversations test failed: {str(e)}")
        
        return permissions


# Provider instances
github_integration_oauth = GitHubIntegrationOAuth()
slack_integration_oauth = SlackIntegrationOAuth()