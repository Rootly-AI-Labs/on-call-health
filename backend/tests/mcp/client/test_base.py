"""Tests for OnCallHealthClient base class."""
import time
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest
import respx

from app.mcp.client.base import OnCallHealthClient
from app.mcp.client.config import ClientConfig
from app.mcp.client.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


class TestOnCallHealthClientCreation:
    """Test client creation and configuration."""

    def test_create_with_default_config(self):
        """Client should use default config when not provided."""
        client = OnCallHealthClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.config.base_url == "https://api.oncallhealth.ai"
        assert client._client is None

    def test_create_with_custom_config(self):
        """Client should use provided config."""
        config = ClientConfig(
            base_url="https://custom.api.com",
            connect_timeout=10.0,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)
        assert client.config.base_url == "https://custom.api.com"
        assert client.config.connect_timeout == 10.0


class TestOnCallHealthClientLifecycle:
    """Test client lifecycle management."""

    @pytest.mark.asyncio
    async def test_get_client_creates_on_first_call(self):
        """_get_client() should create client on first call."""
        client = OnCallHealthClient(api_key="test-key")
        assert client._client is None

        httpx_client = await client._get_client()
        assert httpx_client is not None
        assert isinstance(httpx_client, httpx.AsyncClient)
        assert client._created_at > 0

        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """_get_client() should reuse existing client."""
        client = OnCallHealthClient(api_key="test-key")

        first = await client._get_client()
        second = await client._get_client()
        assert first is second

        await client.close()

    @pytest.mark.asyncio
    async def test_client_recreation_after_max_age(self):
        """Client should be recreated after max_client_age_seconds."""
        config = ClientConfig(max_client_age_seconds=1)  # 1 second for testing
        client = OnCallHealthClient(api_key="test-key", config=config)

        first = await client._get_client()
        first_created_at = client._created_at

        # Wait for client to expire
        await asyncio.sleep(1.1)

        second = await client._get_client()
        assert client._created_at > first_created_at
        # Note: The old client is closed, new one created
        assert second is not first

        await client.close()

    @pytest.mark.asyncio
    async def test_close_closes_httpx_client(self):
        """close() should close the underlying httpx client."""
        client = OnCallHealthClient(api_key="test-key")
        httpx_client = await client._get_client()

        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """close() should handle case when no client exists."""
        client = OnCallHealthClient(api_key="test-key")
        await client.close()  # Should not raise


class TestOnCallHealthClientApiKeyInjection:
    """Test API key injection via event hooks."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_key_header_injected(self, respx_mock):
        """API key should be injected via X-API-Key header."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        client = OnCallHealthClient(api_key="my-secret-key")
        try:
            await client.get("/api/v1/test")
        finally:
            await client.close()

        # Verify the header was sent
        assert respx_mock.calls[0].request.headers["X-API-Key"] == "my-secret-key"


class TestOnCallHealthClientRequests:
    """Test HTTP request methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request(self, respx_mock):
        """get() should make GET request."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/users").mock(
            return_value=httpx.Response(200, json={"users": []})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            response = await client.get("/api/v1/users")
            assert response.status_code == 200
            assert response.json() == {"users": []}
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_request(self, respx_mock):
        """post() should make POST request."""
        respx_mock.post("https://api.oncallhealth.ai/api/v1/users").mock(
            return_value=httpx.Response(201, json={"id": "123"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            response = await client.post("/api/v1/users", json={"name": "Test"})
            assert response.status_code == 201
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_put_request(self, respx_mock):
        """put() should make PUT request."""
        respx_mock.put("https://api.oncallhealth.ai/api/v1/users/123").mock(
            return_value=httpx.Response(200, json={"updated": True})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            response = await client.put("/api/v1/users/123", json={"name": "Updated"})
            assert response.status_code == 200
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_request(self, respx_mock):
        """delete() should make DELETE request."""
        respx_mock.delete("https://api.oncallhealth.ai/api/v1/users/123").mock(
            return_value=httpx.Response(204)
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            response = await client.delete("/api/v1/users/123")
            assert response.status_code == 204
        finally:
            await client.close()


class TestOnCallHealthClientErrorMapping:
    """Test HTTP error to MCP exception mapping."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_401_raises_authentication_error(self, respx_mock):
        """401 response should raise AuthenticationError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        client = OnCallHealthClient(api_key="invalid-key")
        try:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.get("/api/v1/test")
            assert "Invalid API key" in str(exc_info.value)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_403_raises_authentication_error(self, respx_mock):
        """403 response should raise AuthenticationError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/admin").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        client = OnCallHealthClient(api_key="limited-key")
        try:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.get("/api/v1/admin")
            assert "lacks required permissions" in str(exc_info.value)
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_raises_not_found_error(self, respx_mock):
        """404 response should raise NotFoundError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/users/999").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(NotFoundError):
                await client.get("/api/v1/users/999")
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_400_raises_validation_error(self, respx_mock):
        """400 response should raise ValidationError."""
        respx_mock.post("https://api.oncallhealth.ai/api/v1/users").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(ValidationError):
                await client.post("/api/v1/users", json={})
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_422_raises_validation_error(self, respx_mock):
        """422 response should raise ValidationError."""
        respx_mock.post("https://api.oncallhealth.ai/api/v1/users").mock(
            return_value=httpx.Response(422, json={"detail": "Validation failed"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(ValidationError):
                await client.post("/api/v1/users", json={"email": "invalid"})
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_raises_rate_limit_error(self, respx_mock):
        """429 response should raise RateLimitError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "60"},
                json={"error": "Rate limited"}
            )
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(RateLimitError) as exc_info:
                await client.get("/api/v1/test")
            assert exc_info.value.retry_after == 60
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_raises_service_unavailable_error(self, respx_mock):
        """500 response should raise ServiceUnavailableError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(ServiceUnavailableError):
                await client.get("/api/v1/test")
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_503_raises_service_unavailable_error(self, respx_mock):
        """503 response should raise ServiceUnavailableError."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        client = OnCallHealthClient(api_key="test-key")
        try:
            with pytest.raises(ServiceUnavailableError):
                await client.get("/api/v1/test")
        finally:
            await client.close()


class TestOnCallHealthClientContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_context_manager_usage(self, respx_mock):
        """Client should work with async context manager."""
        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async with OnCallHealthClient(api_key="test-key") as client:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200

        # Client should be closed after exiting context
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self):
        """Client should close even when exception occurs."""
        client = OnCallHealthClient(api_key="test-key")

        with pytest.raises(ValueError):
            async with client:
                # Force an exception
                raise ValueError("Test error")

        # Client should still be closed
        assert client._client is None


# Import asyncio for sleep
import asyncio
