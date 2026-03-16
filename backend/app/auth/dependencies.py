"""
Authentication dependencies for FastAPI.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..models import get_db, User
from .jwt import decode_access_token
from .api_key_auth import get_current_user_from_api_key, api_key_header

security = HTTPBearer(auto_error=False)  # Don't auto-error, we'll check cookies too

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token (Authorization header or httpOnly cookie)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # ✅ SECURITY FIX: Check both Authorization header and httpOnly cookies
    token = None
    
    # First, try Authorization header (for API calls with stored tokens)
    if credentials and credentials.credentials:
        token = credentials.credentials
    
    # If no header token, try httpOnly cookie (for same-domain OAuth flow)
    if not token:
        token = request.cookies.get("auth_token")
    
    # If still no token, authentication failed
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (can add additional checks here)."""
    return current_user

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None (for optional auth endpoints)."""
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        # If authentication fails, return None instead of raising exception
        return None


async def get_current_user_flexible(
    request: Request,
    background_tasks: BackgroundTasks,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Flexible authentication: accepts both API keys and JWT tokens.

    This dependency enables endpoints to accept authentication from:
    1. X-API-Key header (for programmatic access)
    2. Authorization: Bearer header (for web app with JWT)
    3. auth_token cookie (for web app with httpOnly cookie)

    Priority order:
    - If X-API-Key header present → use API key authentication
    - Otherwise → use JWT authentication (header or cookie)

    Args:
        request: FastAPI request object
        background_tasks: Background tasks for async last_used update
        credentials: Optional JWT credentials from Authorization header
        api_key: Optional API key from X-API-Key header
        db: Database session

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: 401 if both authentication methods fail
    """
    # Priority 1: Try API key authentication if X-API-Key header present
    if api_key:
        return await get_current_user_from_api_key(
            request, background_tasks, api_key, db
        )

    # Priority 2: Fall back to JWT authentication (Authorization header or cookie)
    return await get_current_user(request, credentials, db)