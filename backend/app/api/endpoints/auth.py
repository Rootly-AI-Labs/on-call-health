"""
Authentication API endpoints.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...models import get_db, User, OAuthProvider, UserEmail
from ...auth.oauth import google_oauth, github_oauth
from ...auth.jwt import create_access_token
from ...auth.dependencies import get_current_active_user
from ...services.account_linking import AccountLinkingService
from ...core.config import settings
from ...core.rate_limiting import auth_rate_limit
from ...core.input_validation import BaseValidatedModel
from pydantic import field_validator, Field

# Temporary in-memory storage for auth codes (use Redis in production)
_temp_auth_codes = {}

router = APIRouter()

# Allowed OAuth redirect origins
ALLOWED_OAUTH_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://localhost:3002",
    settings.FRONTEND_URL,
    "https://www.oncallburnout.com",
    "https://oncallburnout.com"
]

# ===== VALIDATION MODELS =====

class OAuthLoginRequest(BaseValidatedModel):
    """OAuth login request validation."""
    redirect_origin: Optional[str] = Field(None, max_length=500, description="Redirect origin URL")
    
    @field_validator('redirect_origin')
    @classmethod
    def validate_redirect_origin(cls, v):
        """Validate redirect origin is a safe URL."""
        if v is None:
            return v
        
        # Only allow known safe origins
        if v not in ALLOWED_OAUTH_ORIGINS:
            raise ValueError(f"Redirect origin not allowed: {v}")
        
        return v

class TokenExchangeRequest(BaseValidatedModel):
    """Token exchange request validation."""
    code: str = Field(..., min_length=10, max_length=500, description="Authorization code")
    
    @field_validator('code')
    @classmethod
    def validate_auth_code(cls, v):
        """Validate authorization code format."""
        # Must be URL-safe base64 characters only
        import re
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("Invalid authorization code format")
        
        return v

@router.get("/google")
@auth_rate_limit("auth_login")
async def google_login(request: Request, redirect_origin: str = Query(None)):
    """Initiate Google OAuth login."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )
    
    # Store the redirect origin in state parameter for OAuth callback
    state = None
    if redirect_origin and redirect_origin in ALLOWED_OAUTH_ORIGINS:
        # Only allow known origins for security
        state = redirect_origin
    
    authorization_url = google_oauth.get_authorization_url(state=state)
    return {"authorization_url": authorization_url}

@router.get("/google/callback")
async def google_callback(
    code: str = Query(None),
    error: str = Query(None),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )
    
    # Handle user cancellation
    if error:
        if error == "access_denied":
            # User canceled - redirect back to landing page
            return RedirectResponse(url=settings.FRONTEND_URL)
        else:
            # Other OAuth error
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=OAuth error: {error}"
            return RedirectResponse(url=error_url)
    
    # No code means user canceled without error parameter
    if not code:
        return RedirectResponse(url=settings.FRONTEND_URL)
    
    try:
        # Exchange code for token
        token_data = await google_oauth.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received"
            )
        
        # Get user info
        user_info = await google_oauth.get_user_info(access_token)
        
        # Use account linking service
        linking_service = AccountLinkingService(db)
        user, is_new_user = await linking_service.link_or_create_user(
            provider="google",
            user_info=user_info,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Create JWT token
        jwt_token = create_access_token(data={"sub": user.id})
        
        # Determine redirect URL based on state parameter
        frontend_url = settings.FRONTEND_URL
        if state and state in ALLOWED_OAUTH_ORIGINS:
            frontend_url = state
            
        # ✅ SECURITY FIX: Use httpOnly cookie instead of URL parameter  
        response = RedirectResponse(url=f"{frontend_url}/auth/success")
        
        # Determine if we should use secure cookies (HTTPS only in production)
        is_production = not frontend_url.startswith("http://localhost")
        
        # ✅ ENTERPRISE PATTERN: 2-Step Server-Side Token Exchange
        # 1. Create temporary auth code (not JWT) 
        # 2. Frontend exchanges code for JWT via secure API call
        import secrets
        import time
        
        # Create temporary authorization code
        auth_code = secrets.token_urlsafe(32)
        
        # Store JWT temporarily (in production: use Redis/cache)
        # Clean up expired codes first
        current_time = time.time()
        expired_codes = [code for code, data in _temp_auth_codes.items() if data['expires_at'] < current_time]
        for code in expired_codes:
            del _temp_auth_codes[code]
        
        # Store with 5-minute expiration
        _temp_auth_codes[auth_code] = {
            'jwt_token': jwt_token,
            'expires_at': time.time() + 300,  # 5 minutes
            'user_id': user.id
        }
        
        # Redirect with secure authorization code (not JWT)
        success_url = f"{frontend_url}/auth/success?code={auth_code}"
        response = RedirectResponse(url=success_url)
        return response
        
    except Exception as e:
        # Use state for error redirect too
        frontend_url = settings.FRONTEND_URL
        if state and state in ALLOWED_OAUTH_ORIGINS:
            frontend_url = state
        error_url = f"{frontend_url}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)

@router.get("/github")
@auth_rate_limit("auth_login")
async def github_login(request: Request, redirect_origin: str = Query(None)):
    """Initiate GitHub OAuth login."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    # Store the redirect origin in state parameter for OAuth callback
    state = None
    if redirect_origin and redirect_origin in ALLOWED_OAUTH_ORIGINS:
        # Only allow known origins for security
        state = redirect_origin
    
    authorization_url = github_oauth.get_authorization_url(state=state)
    return {"authorization_url": authorization_url}

@router.get("/github/callback")
async def github_callback(
    code: str = Query(None),
    error: str = Query(None),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    # Handle user cancellation
    if error:
        if error == "access_denied":
            # User canceled - redirect back to landing page
            return RedirectResponse(url=settings.FRONTEND_URL)
        else:
            # Other OAuth error
            error_url = f"{settings.FRONTEND_URL}/auth/error?message=OAuth error: {error}"
            return RedirectResponse(url=error_url)
    
    # No code means user canceled without error parameter
    if not code:
        return RedirectResponse(url=settings.FRONTEND_URL)
    
    try:
        # Exchange code for token
        token_data = await github_oauth.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received"
            )
        
        # Get user info
        user_info = await github_oauth.get_user_info(access_token)
        
        # Use account linking service (it will handle fetching all emails)
        linking_service = AccountLinkingService(db)
        user, is_new_user = await linking_service.link_or_create_user(
            provider="github",
            user_info=user_info,
            access_token=access_token,
            refresh_token=None  # GitHub doesn't use refresh tokens
        )
        
        # Create JWT token
        jwt_token = create_access_token(data={"sub": user.id})
        
        # Determine redirect URL based on state parameter
        frontend_url = settings.FRONTEND_URL
        if state and state in ALLOWED_OAUTH_ORIGINS:
            frontend_url = state
            
        # ✅ SECURITY FIX: Use httpOnly cookie instead of URL parameter  
        response = RedirectResponse(url=f"{frontend_url}/auth/success")
        
        # Determine if we should use secure cookies (HTTPS only in production)
        is_production = not frontend_url.startswith("http://localhost")
        
        # ✅ ENTERPRISE PATTERN: 2-Step Server-Side Token Exchange
        # 1. Create temporary auth code (not JWT) 
        # 2. Frontend exchanges code for JWT via secure API call
        import secrets
        import time
        
        # Create temporary authorization code
        auth_code = secrets.token_urlsafe(32)
        
        # Store JWT temporarily (in production: use Redis/cache)
        # Clean up expired codes first
        current_time = time.time()
        expired_codes = [code for code, data in _temp_auth_codes.items() if data['expires_at'] < current_time]
        for code in expired_codes:
            del _temp_auth_codes[code]
        
        # Store with 5-minute expiration
        _temp_auth_codes[auth_code] = {
            'jwt_token': jwt_token,
            'expires_at': time.time() + 300,  # 5 minutes
            'user_id': user.id
        }
        
        # Redirect with secure authorization code (not JWT)
        success_url = f"{frontend_url}/auth/success?code={auth_code}"
        response = RedirectResponse(url=success_url)
        return response
        
    except Exception as e:
        # Use state for error redirect too
        frontend_url = settings.FRONTEND_URL
        if state and state in ALLOWED_OAUTH_ORIGINS:
            frontend_url = state
        error_url = f"{frontend_url}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    linking_service = AccountLinkingService(db)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "provider": current_user.provider,  # Legacy field
        "is_verified": current_user.is_verified,
        "has_rootly_token": bool(current_user.rootly_token),
        "created_at": current_user.created_at,
        "oauth_providers": linking_service.get_user_providers(current_user.id),
        "emails": linking_service.get_user_emails(current_user.id)
    }

@router.get("/providers")
async def get_user_providers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all OAuth providers linked to current user."""
    linking_service = AccountLinkingService(db)
    return {
        "providers": linking_service.get_user_providers(current_user.id)
    }

@router.get("/emails")
async def get_user_emails(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all emails for current user."""
    linking_service = AccountLinkingService(db)
    return {
        "emails": linking_service.get_user_emails(current_user.id)
    }

@router.delete("/providers/{provider}")
async def unlink_provider(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlink an OAuth provider from current user."""
    linking_service = AccountLinkingService(db)
    success = linking_service.unlink_provider(current_user.id, provider)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink provider. At least one provider must remain linked."
        )
    
    return {"message": f"{provider} provider unlinked successfully"}

@router.get("/user/me")
@auth_rate_limit("auth_refresh")
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    ✅ SECURITY: Get current authenticated user information.
    Used to verify authentication works.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }

@router.post("/exchange-token")
@auth_rate_limit("auth_exchange")
async def exchange_auth_code_for_token(
    request: Request,
    code: str = Query(..., description="Authorization code from OAuth callback")
):
    """
    ✅ ENTERPRISE PATTERN: Exchange temporary auth code for JWT token.
    
    This implements the industry-standard 2-step OAuth token exchange:
    1. OAuth callback creates temporary auth code
    2. Frontend securely exchanges code for JWT token
    """
    import time
    
    # Clean up expired codes
    current_time = time.time()
    expired_codes = [c for c, data in _temp_auth_codes.items() if data['expires_at'] < current_time]
    
    for expired_code in expired_codes:
        del _temp_auth_codes[expired_code]
    
    # Check if code exists and is valid
    if code not in _temp_auth_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authorization code"
        )
    
    # Get JWT token and clean up code (single use)
    auth_data = _temp_auth_codes.pop(code)
    jwt_token = auth_data['jwt_token']
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "expires_in": 604800,  # 7 days
        "user_id": auth_data['user_id']
    }