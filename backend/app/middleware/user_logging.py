"""
User logging middleware for automatic user ID injection into logs.

This middleware extracts the user ID from JWT tokens and sets it in
the logging context so all subsequent log messages include the user ID.
"""
import logging
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from ..auth.jwt import get_user_id_from_token
from .logging_context import set_user_context, clear_user_context

logger = logging.getLogger(__name__)


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

    try:
        # Extract token and get user ID
        token = _extract_token_from_request(request)
        if token:
            user_id = get_user_id_from_token(token)

        # Set user context for logging
        set_user_context(user_id)

        # Process the request
        response = await call_next(request)

        return response

    except Exception as e:
        # Log any middleware errors (user context may or may not be set)
        logger.error(f"Error in user logging middleware: {e}")

        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An internal error occurred"
            }
        )

    finally:
        # Always clear the user context after request processing
        clear_user_context()


# Export public API
__all__ = [
    'user_logging_middleware',
]
