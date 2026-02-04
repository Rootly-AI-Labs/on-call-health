"""Tests for MCP exceptions and HTTP error mapping."""
from unittest.mock import MagicMock

import pytest

from app.mcp.client.exceptions import (
    AuthenticationError,
    MCPError,
    MCPErrorCode,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    map_http_error_to_mcp,
)


class TestMCPErrorCodes:
    """Test MCPErrorCode enum values."""

    def test_error_codes_match_spec(self):
        """Error codes should match MCP specification."""
        assert MCPErrorCode.INVALID_REQUEST.value == -32600
        assert MCPErrorCode.METHOD_NOT_FOUND.value == -32601
        assert MCPErrorCode.INVALID_PARAMS.value == -32602
        assert MCPErrorCode.INTERNAL_ERROR.value == -32603
        assert MCPErrorCode.REQUEST_CANCELLED.value == -32800
        assert MCPErrorCode.RESOURCE_UNAVAILABLE.value == -32802


class TestMCPError:
    """Test MCPError base exception."""

    def test_mcp_error_attributes(self):
        """MCPError should have message, code, and retriable attributes."""
        error = MCPError(
            message="Test error",
            code=MCPErrorCode.INTERNAL_ERROR,
            retriable=True
        )
        assert error.message == "Test error"
        assert error.code == MCPErrorCode.INTERNAL_ERROR
        assert error.retriable is True

    def test_mcp_error_default_retriable(self):
        """MCPError should default to retriable=False."""
        error = MCPError(message="Test", code=MCPErrorCode.INTERNAL_ERROR)
        assert error.retriable is False


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_default_message(self):
        """AuthenticationError should have default message."""
        error = AuthenticationError()
        assert error.message == "Invalid API key"

    def test_custom_message(self):
        """AuthenticationError should accept custom message."""
        error = AuthenticationError("Custom auth error")
        assert error.message == "Custom auth error"

    def test_error_code(self):
        """AuthenticationError should use INVALID_PARAMS code."""
        error = AuthenticationError()
        assert error.code == MCPErrorCode.INVALID_PARAMS

    def test_not_retriable(self):
        """AuthenticationError should not be retriable."""
        error = AuthenticationError()
        assert error.retriable is False


class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_no_retry_after(self):
        """RateLimitError without retry_after."""
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.retry_after is None

    def test_with_retry_after(self):
        """RateLimitError with retry_after value."""
        error = RateLimitError(retry_after=60)
        assert error.message == "Rate limit exceeded. Retry after 60 seconds"
        assert error.retry_after == 60

    def test_error_code(self):
        """RateLimitError should use RESOURCE_UNAVAILABLE code."""
        error = RateLimitError()
        assert error.code == MCPErrorCode.RESOURCE_UNAVAILABLE

    def test_is_retriable(self):
        """RateLimitError should be retriable."""
        error = RateLimitError()
        assert error.retriable is True


class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_default_message(self):
        """NotFoundError should have default message."""
        error = NotFoundError()
        assert error.message == "Resource not found"

    def test_custom_message(self):
        """NotFoundError should accept custom message."""
        error = NotFoundError("User not found")
        assert error.message == "User not found"

    def test_error_code(self):
        """NotFoundError should use INVALID_PARAMS code."""
        error = NotFoundError()
        assert error.code == MCPErrorCode.INVALID_PARAMS

    def test_not_retriable(self):
        """NotFoundError should not be retriable."""
        error = NotFoundError()
        assert error.retriable is False


class TestValidationError:
    """Test ValidationError exception."""

    def test_default_message(self):
        """ValidationError should have default message."""
        error = ValidationError()
        assert error.message == "Validation error"

    def test_custom_message(self):
        """ValidationError should accept custom message."""
        error = ValidationError("Invalid field")
        assert error.message == "Invalid field"

    def test_error_code(self):
        """ValidationError should use INVALID_PARAMS code."""
        error = ValidationError()
        assert error.code == MCPErrorCode.INVALID_PARAMS

    def test_not_retriable(self):
        """ValidationError should not be retriable."""
        error = ValidationError()
        assert error.retriable is False


class TestServiceUnavailableError:
    """Test ServiceUnavailableError exception."""

    def test_default_message(self):
        """ServiceUnavailableError should have default message."""
        error = ServiceUnavailableError()
        assert error.message == "Service temporarily unavailable"

    def test_custom_message(self):
        """ServiceUnavailableError should accept custom message."""
        error = ServiceUnavailableError("Server overloaded")
        assert error.message == "Server overloaded"

    def test_error_code(self):
        """ServiceUnavailableError should use RESOURCE_UNAVAILABLE code."""
        error = ServiceUnavailableError()
        assert error.code == MCPErrorCode.RESOURCE_UNAVAILABLE

    def test_is_retriable(self):
        """ServiceUnavailableError should be retriable."""
        error = ServiceUnavailableError()
        assert error.retriable is True


class TestMapHttpErrorToMcp:
    """Test map_http_error_to_mcp function."""

    def _mock_response(self, status_code: int, headers: dict = None):
        """Create a mock httpx.Response."""
        response = MagicMock()
        response.status_code = status_code
        response.headers = headers or {}
        return response

    def test_400_returns_validation_error(self):
        """400 Bad Request should return ValidationError."""
        response = self._mock_response(400)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ValidationError)
        assert error.message == "Bad request"
        assert error.retriable is False

    def test_401_returns_authentication_error(self):
        """401 Unauthorized should return AuthenticationError."""
        response = self._mock_response(401)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, AuthenticationError)
        assert error.message == "Invalid API key"
        assert error.retriable is False

    def test_403_returns_authentication_error(self):
        """403 Forbidden should return AuthenticationError."""
        response = self._mock_response(403)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, AuthenticationError)
        assert error.message == "API key lacks required permissions"
        assert error.retriable is False

    def test_404_returns_not_found_error(self):
        """404 Not Found should return NotFoundError."""
        response = self._mock_response(404)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, NotFoundError)
        assert error.retriable is False

    def test_422_returns_validation_error(self):
        """422 Unprocessable Entity should return ValidationError."""
        response = self._mock_response(422)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ValidationError)
        assert error.message == "Validation error"
        assert error.retriable is False

    def test_429_returns_rate_limit_error_without_header(self):
        """429 Too Many Requests without Retry-After header."""
        response = self._mock_response(429)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after is None
        assert error.retriable is True

    def test_429_returns_rate_limit_error_with_header(self):
        """429 Too Many Requests with Retry-After header."""
        response = self._mock_response(429, headers={"Retry-After": "120"})
        error = map_http_error_to_mcp(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 120
        assert error.retriable is True

    def test_429_handles_invalid_retry_after(self):
        """429 with invalid Retry-After header should not crash."""
        response = self._mock_response(429, headers={"Retry-After": "invalid"})
        error = map_http_error_to_mcp(response)
        assert isinstance(error, RateLimitError)
        assert error.retry_after is None

    def test_500_returns_service_unavailable(self):
        """500 Internal Server Error should return ServiceUnavailableError."""
        response = self._mock_response(500)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ServiceUnavailableError)
        assert "500" in error.message
        assert error.retriable is True

    def test_502_returns_service_unavailable(self):
        """502 Bad Gateway should return ServiceUnavailableError."""
        response = self._mock_response(502)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ServiceUnavailableError)
        assert error.retriable is True

    def test_503_returns_service_unavailable(self):
        """503 Service Unavailable should return ServiceUnavailableError."""
        response = self._mock_response(503)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ServiceUnavailableError)
        assert error.retriable is True

    def test_504_returns_service_unavailable(self):
        """504 Gateway Timeout should return ServiceUnavailableError."""
        response = self._mock_response(504)
        error = map_http_error_to_mcp(response)
        assert isinstance(error, ServiceUnavailableError)
        assert error.retriable is True

    def test_unknown_4xx_returns_mcp_error(self):
        """Unknown 4xx status should return generic MCPError."""
        response = self._mock_response(418)  # I'm a teapot
        error = map_http_error_to_mcp(response)
        assert isinstance(error, MCPError)
        assert error.message == "HTTP 418"
        assert error.code == MCPErrorCode.INTERNAL_ERROR
        assert error.retriable is False


class TestExceptionRetriableFlags:
    """Test that retriable flags are correct for each exception type."""

    def test_non_retriable_exceptions(self):
        """Auth, NotFound, Validation errors should not be retriable."""
        assert AuthenticationError().retriable is False
        assert NotFoundError().retriable is False
        assert ValidationError().retriable is False

    def test_retriable_exceptions(self):
        """RateLimit and ServiceUnavailable should be retriable."""
        assert RateLimitError().retriable is True
        assert ServiceUnavailableError().retriable is True
