"""
MCP REST API client for oncallhealth.ai.

This module provides a resilient HTTP client for MCP server to API communication
with connection pooling, API key injection, configurable timeouts, typed
exception handling, automatic retry, circuit breaker, and health monitoring.
"""
from .base import OnCallHealthClient
from .circuit_breaker import CircuitBreakerOpenError
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
from .health import ConnectionPoolMonitor
from .retry import (
    RETRYABLE_EXCEPTIONS,
    RETRYABLE_STATUS_CODES,
    RetriableHTTPError,
)

__all__ = [
    # Client
    "OnCallHealthClient",
    "ClientConfig",
    # MCP exceptions
    "MCPError",
    "MCPErrorCode",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "ServiceUnavailableError",
    "map_http_error_to_mcp",
    # Resilience
    "CircuitBreakerOpenError",
    "ConnectionPoolMonitor",
    "RETRYABLE_EXCEPTIONS",
    "RETRYABLE_STATUS_CODES",
    "RetriableHTTPError",
]
