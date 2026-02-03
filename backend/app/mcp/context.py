"""MCP context management without FastMCP Context type dependency.

This module provides a workaround for accessing HTTP request context
in MCP tools without requiring FastMCP Context as a type parameter,
which can cause Pydantic schema generation issues.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from starlette.requests import Request

# Context variable to store current request
_request_context: ContextVar[Optional["Request"]] = ContextVar("mcp_request", default=None)


def set_request_context(request: "Request") -> None:
    """Store the current HTTP request in context."""
    _request_context.set(request)


def get_request_context() -> Optional["Request"]:
    """Get the current HTTP request from context."""
    return _request_context.get()


@contextmanager
def request_context(request: "Request"):
    """Context manager for setting request context."""
    token = _request_context.set(request)
    try:
        yield
    finally:
        _request_context.reset(token)


def get_api_key() -> Optional[str]:
    """Extract API key from current request context."""
    request = get_request_context()
    if request is None:
        return None

    # Check X-API-Key header (case-insensitive)
    for key in request.headers.keys():
        if key.lower() == "x-api-key":
            return request.headers[key]

    return None
