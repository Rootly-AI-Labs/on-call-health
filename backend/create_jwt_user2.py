#!/usr/bin/env python3
"""
Create JWT token for user 2
"""
import jwt
from datetime import datetime, timedelta

# Same settings as in auth/jwt.py
SECRET_KEY = "your-secret-key-change-in-production-use-openssl-rand-hex-32"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_access_token(user_id: int) -> str:
    """Create JWT token for user."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

if __name__ == "__main__":
    token = create_access_token(2)
    print(f"JWT Token for User 2: {token}")