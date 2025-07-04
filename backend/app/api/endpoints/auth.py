"""
Authentication API endpoints.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...models import get_db, User, OAuthProvider, UserEmail
from ...auth.oauth import google_oauth, github_oauth
from ...auth.jwt import create_access_token
from ...auth.dependencies import get_current_active_user
from ...services.account_linking import AccountLinkingService
from ...core.config import settings

router = APIRouter()

@router.get("/google")
async def google_login():
    """Initiate Google OAuth login."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )
    
    authorization_url = google_oauth.get_authorization_url()
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
        
        # Redirect to frontend with token
        redirect_url = f"{settings.FRONTEND_URL}/auth/success?token={jwt_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        error_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)

@router.get("/github")
async def github_login():
    """Initiate GitHub OAuth login."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    authorization_url = github_oauth.get_authorization_url()
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
        
        # Redirect to frontend with token
        redirect_url = f"{settings.FRONTEND_URL}/auth/success?token={jwt_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        error_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
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