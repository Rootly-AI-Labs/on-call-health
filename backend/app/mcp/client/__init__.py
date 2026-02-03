"""
MCP REST API client for oncallhealth.ai.

This module provides a resilient HTTP client for MCP server to API communication
with connection pooling, API key injection, configurable timeouts, and typed
exception handling.
"""
from .base import OnCallHealthClient
from .config import ClientConfig
from .exceptions import (
    AuthenticationError,
    MCPError,
    MCPErrorCode,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    map_http_error_to_mcp,
)

__all__ = [
    "OnCallHealthClient",
    "ClientConfig",
    "MCPError",
    "MCPErrorCode",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "ServiceUnavailableError",
    "map_http_error_to_mcp",
]
