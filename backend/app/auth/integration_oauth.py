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
    
class JiraIntegrationOAuth:
    """
    Jira OAuth provider for integration purposes (frontend redirect style).

    Notes:
    - Uses OAuth 2.0 (3LO). Ensure the Atlassian app's Redirect URL exactly matches
      settings.FRONTEND_URL + "/setup/jira/callback".
    - Scopes used: read:jira-work read:jira-user offline_access
    """

    def __init__(self):
        self.client_id = settings.JIRA_CLIENT_ID
        self.client_secret = settings.JIRA_CLIENT_SECRET
        # The provider redirects back to FRONTEND, which then calls backend /callback
        self.redirect_uri = f"{settings.FRONTEND_URL}/setup/jira/callback"
        self.auth_url = "https://auth.atlassian.com/authorize"
        self.token_url = "https://auth.atlassian.com/oauth/token"
        self.accessible_resources_url = "https://api.atlassian.com/oauth/token/accessible-resources"
        self.api_base = "https://api.atlassian.com/ex/jira"

    def get_authorization_url(self, state: str = "") -> str:
        from urllib.parse import urlencode
        params = {
            "audience": "api.atlassian.com",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,  # must match Atlassian app config
            "scope": "read:jira-work read:jira-user offline_access",
            "response_type": "code",
            "prompt": "consent",
            "state": state or "",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,  # must match exactly
        }
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, json=data, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for token: {resp.text}",
            )
        return resp.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.token_url, json=data, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh access token: {resp.text}",
            )
        return resp.json()

    async def get_accessible_resources(self, access_token: str) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.accessible_resources_url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get accessible resources: {resp.text}",
            )
        return resp.json()

    async def get_user_info(self, access_token: str, cloud_id: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        url = f"{self.api_base}/{cloud_id}/rest/api/3/myself"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info: {resp.text}",
            )
        return resp.json()

    async def search_issues(
        self,
        access_token: str,
        cloud_id: str,
        jql: str,
        *,
        fields: Optional[List[str]] = None,
        max_results: int = 100,
        next_page_token: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use the enhanced JQL search API:
          GET /rest/api/3/search/jql
        Supports pagination via nextPageToken. Old /rest/api/3/search is being removed.
        """
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        url = f"{self.api_base}/{cloud_id}/rest/api/3/search/jql"

        params: Dict[str, Any] = {
            "jql": jql,
            "maxResults": max(1, min(1000, int(max_results))),
        }
        if fields:
            params["fields"] = ",".join(fields)
        if next_page_token:
            params["nextPageToken"] = next_page_token
        if expand:
            params["expand"] = expand

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)

        # Atlassian sends 410 Gone when calling old endpoints; surface error if any non-200
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to search issues: {resp.text}",
            )
        return resp.json()

    async def test_permissions(self, access_token: str, cloud_id: str) -> Dict[str, Any]:
        """
        Basic permission smoke tests:
        - /myself => user_access
        - /project => project_access
        - /search/jql => issue_access (try a small query)
        - /issue/{key}/worklog => worklog_access (on first issue if exists)
        """
        perms = {
            "user_access": False,
            "project_access": False,
            "issue_access": False,
            "worklog_access": False,
            "errors": [],
        }
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            # /myself
            try:
                r = await client.get(f"{self.api_base}/{cloud_id}/rest/api/3/myself", headers=headers)
                perms["user_access"] = r.status_code == 200
                if not perms["user_access"]:
                    perms["errors"].append(f"myself: {r.text}")
            except Exception as e:
                perms["errors"].append(f"myself err: {e}")

            # /project
            try:
                r = await client.get(
                    f"{self.api_base}/{cloud_id}/rest/api/3/project",
                    headers=headers,
                    params={"maxResults": 1},
                )
                perms["project_access"] = r.status_code == 200
                if not perms["project_access"]:
                    perms["errors"].append(f"project: {r.text}")
            except Exception as e:
                perms["errors"].append(f"project err: {e}")

        # Issue access via enhanced JQL (GET)
        try:
            sr = await self.search_issues(
                access_token,
                cloud_id,
                jql="updated >= -7d",
                fields=["key"],
                max_results=1,
            )
            perms["issue_access"] = True
            # Worklog access on the first returned issue (if any)
            issues = (sr or {}).get("issues") or []
            if issues:
                key = issues[0].get("key")
                if key:
                    async with httpx.AsyncClient() as client:
                        wr = await client.get(
                            f"{self.api_base}/{cloud_id}/rest/api/3/issue/{key}/worklog",
                            headers=headers,
                        )
                    perms["worklog_access"] = wr.status_code == 200
                    if not perms["worklog_access"]:
                        perms["errors"].append(f"worklog: {wr.text}")
        except HTTPException as e:
            perms["errors"].append(f"search/jql: {e.detail}")
        except Exception as e:
            perms["errors"].append(f"search/jql err: {e}")

        return perms


# Provider instances
github_integration_oauth = GitHubIntegrationOAuth()
slack_integration_oauth = SlackIntegrationOAuth()
jira_integration_oauth = JiraIntegrationOAuth()
