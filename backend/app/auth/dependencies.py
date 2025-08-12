"""
Authentication dependencies for FastAPI.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..models import get_db, User
from .jwt import decode_access_token

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
    
    # Enhanced debug logging for both authentication methods
    print(f"🔍 AUTH DEBUG: === Authentication Request Debug ===")
    print(f"🔍 AUTH DEBUG: Authorization header present: {bool(credentials and credentials.credentials)}")
    if credentials and credentials.credentials:
        print(f"🔍 AUTH DEBUG: Authorization header value: Bearer {credentials.credentials[:50]}...")
    print(f"🔍 AUTH DEBUG: cookies available: {list(request.cookies.keys())}")
    print(f"🔍 AUTH DEBUG: auth_token cookie: {request.cookies.get('auth_token', 'NOT_FOUND')[:50]}...")
    
    # First, try Authorization header (for API calls with stored tokens)
    if credentials and credentials.credentials:
        token = credentials.credentials
        print(f"🔍 AUTH DEBUG: Using Authorization header token")
    
    # If no header token, try httpOnly cookie (for same-domain OAuth flow)
    if not token:
        token = request.cookies.get("auth_token")
        if token:
            print(f"🔍 AUTH DEBUG: Using cookie token: {token[:50]}...")
        else:
            print(f"🔍 AUTH DEBUG: No cookie token found")
    
    # If still no token, authentication failed
    if not token:
        print(f"🔍 AUTH DEBUG: AUTHENTICATION FAILED - No token found via header or cookie")
        raise credentials_exception
    
    print(f"🔍 AUTH DEBUG: Proceeding with token validation...")
    
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