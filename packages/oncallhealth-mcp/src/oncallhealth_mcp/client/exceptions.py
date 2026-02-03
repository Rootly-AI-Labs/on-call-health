"""
MCP exception hierarchy and HTTP-to-exception mapping.

Provides typed exceptions for MCP error handling and a function to map
HTTP response status codes to appropriate MCP exceptions.
"""
from enum import Enum
from typing import Optional

import httpx


class MCPErrorCode(Enum):
    """MCP-specific error codes per MCP specification."""
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    REQUEST_CANCELLED = -32800
    RESOURCE_UNAVAILABLE = -32802


class MCPError(Exception):
    """Base MCP exception.

    Attributes:
        message: Human-readable error message
        code: MCP error code
        retriable: Whether the operation can be retried
    """
    def __init__(
        self,
        message: str,
        code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
        retriable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retriable = retriable


class AuthenticationError(MCPError):
    """Invalid or expired API key (401/403)."""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(
            message=message,
            code=MCPErrorCode.INVALID_PARAMS,
            retriable=False
        )


class RateLimitError(MCPError):
    """Rate limit exceeded (429).

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """
    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        if retry_after is not None:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            code=MCPErrorCode.RESOURCE_UNAVAILABLE,
            retriable=True
        )
        self.retry_after = retry_after


class NotFoundError(MCPError):
    """Resource not found (404)."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            code=MCPErrorCode.INVALID_PARAMS,
            retriable=False
        )


class ValidationError(MCPError):
    """Validation error (400/422)."""
    def __init__(self, message: str = "Validation error"):
        super().__init__(
            message=message,
            code=MCPErrorCode.INVALID_PARAMS,
            retriable=False
        )


class ServiceUnavailableError(MCPError):
    """Backend service unavailable (5xx)."""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            code=MCPErrorCode.RESOURCE_UNAVAILABLE,
            retriable=True
        )


def map_http_error_to_mcp(response: httpx.Response) -> MCPError:
    """Map HTTP error response to appropriate MCP exception.

    Args:
        response: httpx.Response with status_code >= 400

    Returns:
        MCPError subclass appropriate for the HTTP status code
    """
    status = response.status_code

    # Authentication errors (never retry)
    if status == 401:
        return AuthenticationError("Invalid API key")
    if status == 403:
        return AuthenticationError("API key lacks required permissions")

    # Client errors (never retry)
    if status == 400:
        return ValidationError("Bad request")
    if status == 404:
        return NotFoundError()
    if status == 422:
        return ValidationError("Validation error")

    # Rate limiting (retry after backoff)
    if status == 429:
        retry_after_header = response.headers.get("Retry-After")
        retry_after = None
        if retry_after_header is not None:
            try:
                retry_after = int(retry_after_header)
            except ValueError:
                pass
        return RateLimitError(retry_after=retry_after)

    # Server errors (retry)
    if status >= 500:
        return ServiceUnavailableError(f"Server error: {status}")

    # Unknown error
    return MCPError(
        message=f"HTTP {status}",
        code=MCPErrorCode.INTERNAL_ERROR,
        retriable=False
    )
