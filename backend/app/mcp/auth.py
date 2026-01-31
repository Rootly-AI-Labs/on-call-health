"""Auth helpers for MCP tools/resources."""
from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.models import User


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
