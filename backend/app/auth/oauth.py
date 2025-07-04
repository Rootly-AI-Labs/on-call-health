"""
OAuth authentication handlers for Google and GitHub.
"""
import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from urllib.parse import urlencode

from ..core.config import settings

class OAuthProvider:
    """Base OAuth provider class."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL."""
        raise NotImplementedError
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        raise NotImplementedError
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token."""
        raise NotImplementedError

class GoogleOAuth(OAuthProvider):
    """Google OAuth provider."""
    
    def __init__(self):
        super().__init__(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent"
        }
        if state:
            params["state"] = state
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange Google authorization code for access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)
            
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Google user information."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.user_info_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )
        
        return response.json()

class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider."""
    
    def __init__(self):
        super().__init__(
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
            redirect_uri=settings.GITHUB_REDIRECT_URI
        )
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"
        self.emails_url = "https://api.github.com/user/emails"
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate GitHub OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",
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
    
    async def get_all_emails(self, access_token: str) -> list[Dict[str, Any]]:
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
    
    def select_primary_email(self, github_emails: list[Dict[str, Any]]) -> Optional[str]:
        """Select the best primary email from GitHub emails."""
        if not github_emails:
            return None
        
        # Prioritize work domains (common business email domains)
        work_domains = [
            ".com", ".org", ".net", ".edu", ".gov",  # General business
            "company", "corp", "inc", "ltd", "llc"   # Business keywords
        ]
        
        # First, look for primary email
        for email_data in github_emails:
            if email_data.get("primary", False):
                return email_data["email"]
        
        # Then, prefer work-looking emails
        for email_data in github_emails:
            email = email_data["email"]
            # Skip obvious personal domains
            if not any(personal in email.lower() for personal in ["gmail", "yahoo", "hotmail", "outlook", "icloud"]):
                return email
        
        # Fall back to first verified email
        return github_emails[0]["email"] if github_emails else None

# Provider instances
google_oauth = GoogleOAuth()
github_oauth = GitHubOAuth()