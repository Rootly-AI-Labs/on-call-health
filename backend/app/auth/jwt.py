"""
JWT token handling utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt
from ..core.config import settings

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    # Ensure sub claim is a string (required by JWT spec)
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.JWTError:
        return None

def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user ID from JWT token."""
    payload = decode_access_token(token)
    if payload:
        sub = payload.get("sub")
        if sub:
            try:
                return int(sub)
            except (ValueError, TypeError):
                return None
    return None