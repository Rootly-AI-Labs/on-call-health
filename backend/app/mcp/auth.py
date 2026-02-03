"""Auth helpers for MCP tools/resources.

This module provides authentication functions that require database access
(JWT validation, API key verification). For standalone deployment without
database dependencies, use auth_helpers.py instead.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.models import User, APIKey
from app.services.api_key_service import compute_sha256_hash, verify_api_key

# Re-export header extraction utilities for backward compatibility
from app.mcp.auth_helpers import (
    extract_bearer_token,
    extract_api_key_header,
)


def get_user_from_token(token: str, db: Session) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise PermissionError("Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise PermissionError("Invalid token payload")

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise PermissionError("Invalid token subject")

    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        raise PermissionError("User not found")

    return user


def require_user(ctx: Any, db: Session) -> User:
    token = extract_bearer_token(ctx)
    if not token:
        raise PermissionError("Missing bearer token")
    return get_user_from_token(token, db)


def require_user_api_key(ctx: Any, db: Session) -> User:
    """
    Require authenticated user from API key for MCP context.

    MCP endpoints are API-key-only per CONTEXT.md decision.
    Rejects JWT authentication with helpful error message.

    Args:
        ctx: MCP context object
        db: Database session

    Returns:
        Authenticated User

    Raises:
        PermissionError: If authentication fails
    """
    # Check for JWT (reject it - MCP is API-key-only)
    bearer_token = extract_bearer_token(ctx)
    if bearer_token:
        raise PermissionError(
            "MCP endpoints require API key authentication. "
            "Use X-API-Key header instead of Bearer token."
        )

    # Extract API key
    api_key = extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    # Validate format
    if not api_key.startswith("och_live_"):
        raise PermissionError("Invalid API key format. Keys should start with 'och_live_'.")

    # Phase 1: SHA-256 lookup (fast)
    sha256_hash = compute_sha256_hash(api_key)
    api_key_model = db.query(APIKey).filter(
        APIKey.key_hash_sha256 == sha256_hash
    ).first()

    if not api_key_model:
        raise PermissionError("Invalid API key")

    # Check revocation (cheap check before expensive Argon2)
    if api_key_model.revoked_at is not None:
        raise PermissionError("API key has been revoked")

    # Check expiration (cheap check before expensive Argon2)
    if api_key_model.expires_at is not None:
        if datetime.now(timezone.utc) >= api_key_model.expires_at:
            expiry_date = api_key_model.expires_at.strftime("%Y-%m-%d")
            raise PermissionError(f"API key expired on {expiry_date}")

    # Phase 2: Argon2 verification (timing-safe)
    # Note: MCP handlers are sync, so we call verify_api_key directly
    is_valid = verify_api_key(api_key, api_key_model.key_hash_argon2)
    if not is_valid:
        raise PermissionError("Invalid API key")

    # Load user
    user = db.query(User).filter(User.id == api_key_model.user_id).first()
    if not user:
        raise PermissionError("API key owner not found")

    return user
