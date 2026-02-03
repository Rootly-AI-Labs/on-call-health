"""Auth helpers for MCP tools/resources."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.models import User, APIKey
from app.services.api_key_service import compute_sha256_hash, verify_api_key


def _normalize_header_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip()


def _parse_bearer_token(value: Optional[str]) -> Optional[str]:
    value = _normalize_header_value(value)
    if not value:
        return None
    parts = value.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def _get_header(headers: Any, name: str) -> Optional[str]:
    if headers is None:
        return None
    if hasattr(headers, "get"):
        direct = headers.get(name)
        if direct:
            return direct
        lower = headers.get(name.lower())
        if lower:
            return lower
        upper = headers.get(name.upper())
        if upper:
            return upper
    try:
        items: Iterable[tuple[str, str]] = headers.items()
    except Exception:
        return None
    name_lower = name.lower()
    for key, value in items:
        if isinstance(key, str) and key.lower() == name_lower:
            return value
    return None


def extract_bearer_token(ctx: Any) -> Optional[str]:
    """Extract bearer token from various MCP context shapes."""
    headers = getattr(ctx, "request_headers", None)
    token = _parse_bearer_token(_get_header(headers, "Authorization"))
    if token:
        return token

    headers = getattr(ctx, "headers", None)
    token = _parse_bearer_token(_get_header(headers, "Authorization"))
    if token:
        return token

    request = getattr(ctx, "request", None)
    if request is not None:
        req_headers = getattr(request, "headers", None)
        token = _parse_bearer_token(_get_header(req_headers, "Authorization"))
        if token:
            return token

    return None


def extract_api_key_header(ctx: Any) -> Optional[str]:
    """Extract X-API-Key header from various MCP context shapes."""
    # Try request_headers
    headers = getattr(ctx, "request_headers", None)
    key = _get_header(headers, "X-API-Key")
    if key:
        return _normalize_header_value(key)

    # Try headers
    headers = getattr(ctx, "headers", None)
    key = _get_header(headers, "X-API-Key")
    if key:
        return _normalize_header_value(key)

    # Try request.headers
    request = getattr(ctx, "request", None)
    if request is not None:
        req_headers = getattr(request, "headers", None)
        key = _get_header(req_headers, "X-API-Key")
        if key:
            return _normalize_header_value(key)

    return None


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
