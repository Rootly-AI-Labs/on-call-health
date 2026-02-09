"""
User logging middleware for automatic user ID injection into logs.

This middleware extracts the user ID from JWT tokens and sets it in
the logging context so all subsequent log messages include the user ID.
"""
import logging
import time
from threading import Lock
from typing import Callable, Optional

from fastapi import Request, Response

from ..auth.jwt import get_user_id_from_token
from ..models import SessionLocal, User
from .logging_context import set_user_context, clear_user_context

logger = logging.getLogger(__name__)

# LRU cache with TTL for user emails to avoid DB query on every request
_email_cache: dict[int, tuple[str, float]] = {}
_email_cache_lock = Lock()
_EMAIL_CACHE_TTL = 300  # 5 minutes
_EMAIL_CACHE_MAX_SIZE = 1000


def _get_cached_email(user_id: int) -> Optional[str]:
    """Get user email from cache if not expired."""
    with _email_cache_lock:
        if user_id in _email_cache:
            email, timestamp = _email_cache[user_id]
            if time.time() - timestamp < _EMAIL_CACHE_TTL:
                return email
            del _email_cache[user_id]
    return None


def _cache_email(user_id: int, email: str) -> None:
    """Cache user email with current timestamp."""
    with _email_cache_lock:
        # Evict oldest entries if cache is full
        if len(_email_cache) >= _EMAIL_CACHE_MAX_SIZE:
            oldest_key = min(_email_cache, key=lambda k: _email_cache[k][1])
            del _email_cache[oldest_key]
        _email_cache[user_id] = (email, time.time())


def _extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extract JWT token from request (Authorization header or cookie).

    Args:
        request: The incoming FastAPI request.

    Returns:
        The JWT token string, or None if not found.
    """
    # First, try Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    # If no header token, try httpOnly cookie
    token = request.cookies.get("auth_token")
    if token:
        return token

    return None


async def user_logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware that sets user context for logging based on JWT authentication.

    This middleware:
    1. Extracts the JWT token from the request (header or cookie)
    2. Decodes the token to get the user ID
    3. Sets the user context for logging
    4. Processes the request
    5. Clears the user context after the request completes

    Args:
        request: The incoming FastAPI request.
        call_next: The next middleware or route handler.

    Returns:
        The response from the route handler.
    """
    user_id = None
    user_email = None

    try:
        # Extract token and get user ID
        token = _extract_token_from_request(request)
        if token:
            user_id = get_user_id_from_token(token)
            if user_id is None:
                logger.debug(f"Failed to extract user ID from token for {request.url.path}")
            else:
                # Try cache first to avoid DB query on every request
                user_email = _get_cached_email(user_id)
                if user_email is None:
                    db = SessionLocal()
                    try:
                        user = db.query(User.email).filter(User.id == user_id).first()
                        if user:
                            user_email = user[0]
                            _cache_email(user_id, user_email)
                        else:
                            logger.debug(f"No user found for ID {user_id} while resolving email for logging")
                    except Exception as e:
                        logger.warning(f"Failed to resolve user email for logging: {e}")
                    finally:
                        db.close()
    except Exception as e:
        # Only log token extraction errors, don't fail the request
        logger.warning(f"Failed to extract user ID for logging: {e}")

    # Set user context for logging: prefer email, fall back to user_id, or None
    context_value = user_email or (str(user_id) if user_id is not None else None)
    set_user_context(context_value)

    try:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        # Log slow requests (>5s) so we know when clients are likely timing out
        if duration > 5 and not request.url.path.startswith(("/docs", "/openapi", "/health")):
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration:.1f}s (user={context_value})"
            )

        return response
    except Exception as e:
        duration = time.time() - start
        # Client disconnect shows up as asyncio.CancelledError or similar
        logger.warning(
            f"Client disconnected: {request.method} {request.url.path} "
            f"after {duration:.1f}s (user={context_value}): {type(e).__name__}"
        )
        raise
    finally:
        # Always clear the user context after request processing
        clear_user_context()


# Export public API
__all__ = [
    'user_logging_middleware',
]
