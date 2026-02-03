"""Unit tests for MCP server tools using REST client.

Tests verify that the refactored analysis tools correctly:
1. Use OnCallHealthClient for REST API calls
2. Normalize responses to match existing MCP tool contracts
3. Handle errors appropriately (mapping to correct exception types)
"""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.mcp.server import (
    analysis_status,
    analysis_results,
    analysis_current,
    analysis_start,
)
from app.mcp.client import NotFoundError


def _mock_ctx_with_api_key(api_key: str = "och_live_test123"):
    """Create mock MCP context with API key header."""
    ctx = SimpleNamespace()
    ctx.request_headers = {"X-API-Key": api_key}
    return ctx


def _mock_ctx_without_api_key():
    """Create mock MCP context without API key header."""
    ctx = SimpleNamespace()
    ctx.request_headers = {}
    return ctx


def _mock_response(json_data: dict, status_code: int = 200):
    """Create mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.json.return_value = json_data
    response.status_code = status_code
    return response


class TestAnalysisStatus:
    """Tests for analysis_status tool."""

    @pytest.mark.asyncio
    async def test_returns_normalized_response(self):
        """Verify REST response is normalized to MCP contract."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 100,
            "status": "completed",
            "created_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:05:00",
            "config": {"days_back": 30},
            "analysis_data": {
                "team_analysis": [
                    {"risk_level": "high"},
                    {"risk_level": "medium"},
                ],
                "team_summary": {"average_score": 75},
            },
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_status(ctx, analysis_id=100)

            assert result["id"] == 100
            assert result["status"] == "completed"
            assert result["created_at"] == "2024-01-01T12:00:00"
            assert result["completed_at"] == "2024-01-01T12:05:00"
            assert result["config"] == {"days_back": 30}
            # Verify results_summary is computed from analysis_data
            assert result["results_summary"]["total_users"] == 2
            assert result["results_summary"]["high_risk_count"] == 1
            assert result["results_summary"]["team_average_score"] == 75
            mock_client.get.assert_called_once_with("/analyses/100")

    @pytest.mark.asyncio
    async def test_raises_lookup_error_when_not_found(self):
        """Verify NotFoundError maps to LookupError."""
        ctx = _mock_ctx_with_api_key()

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = NotFoundError("Resource not found")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LookupError, match="Analysis not found"):
                await analysis_status(ctx, analysis_id=999)

    @pytest.mark.asyncio
    async def test_raises_permission_error_without_api_key(self):
        """Verify missing key handling."""
        ctx = _mock_ctx_without_api_key()

        with pytest.raises(PermissionError, match="Missing API key"):
            await analysis_status(ctx, analysis_id=100)

    @pytest.mark.asyncio
    async def test_handles_pending_status(self):
        """Verify pending analysis status is returned correctly."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 100,
            "status": "pending",
            "created_at": "2024-01-01T12:00:00",
            "completed_at": None,
            "config": {"days_back": 30},
            "analysis_data": None,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_status(ctx, analysis_id=100)

            assert result["id"] == 100
            assert result["status"] == "pending"
            assert result["completed_at"] is None
            # No results_summary for pending status
            assert "results_summary" not in result


class TestAnalysisResults:
    """Tests for analysis_results tool."""

    @pytest.mark.asyncio
    async def test_returns_full_results_when_completed(self):
        """Verify analysis_data is returned for completed analysis."""
        ctx = _mock_ctx_with_api_key()
        analysis_data = {
            "team_analysis": [
                {"email": "user1@example.com", "risk_level": "high"},
                {"email": "user2@example.com", "risk_level": "low"},
            ],
            "team_summary": {"average_score": 65, "total_incidents": 42},
        }
        mock_response = _mock_response({
            "id": 100,
            "status": "completed",
            "analysis_data": analysis_data,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_results(ctx, analysis_id=100)

            assert result == analysis_data
            mock_client.get.assert_called_once_with("/analyses/100")

    @pytest.mark.asyncio
    async def test_raises_value_error_when_not_completed(self):
        """Verify status check raises error for incomplete analysis."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 100,
            "status": "pending",
            "analysis_data": None,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="Analysis not completed yet"):
                await analysis_results(ctx, analysis_id=100)

    @pytest.mark.asyncio
    async def test_raises_lookup_error_when_not_found(self):
        """Verify NotFoundError maps to LookupError."""
        ctx = _mock_ctx_with_api_key()

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = NotFoundError("Resource not found")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LookupError, match="Analysis not found"):
                await analysis_results(ctx, analysis_id=999)

    @pytest.mark.asyncio
    async def test_raises_permission_error_without_api_key(self):
        """Verify missing key handling."""
        ctx = _mock_ctx_without_api_key()

        with pytest.raises(PermissionError, match="Missing API key"):
            await analysis_results(ctx, analysis_id=100)

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_analysis_data(self):
        """Verify empty dict returned when analysis_data is None."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 100,
            "status": "completed",
            "analysis_data": None,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_results(ctx, analysis_id=100)

            assert result == {}


class TestAnalysisCurrent:
    """Tests for analysis_current tool."""

    @pytest.mark.asyncio
    async def test_returns_most_recent(self):
        """Verify first item from list is returned."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "analyses": [
                {
                    "id": 100,
                    "status": "completed",
                    "created_at": "2024-01-01T12:00:00",
                    "completed_at": "2024-01-01T12:05:00",
                    "config": {"days_back": 30},
                    "analysis_data": {
                        "team_analysis": [],
                        "team_summary": {"average_score": 80},
                    },
                },
            ],
            "total": 5,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_current(ctx)

            assert result["id"] == 100
            assert result["status"] == "completed"
            mock_client.get.assert_called_once_with("/analyses", params={"limit": 1})

    @pytest.mark.asyncio
    async def test_raises_lookup_error_when_empty(self):
        """Verify empty list handling."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "analyses": [],
            "total": 0,
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LookupError, match="No analyses found"):
                await analysis_current(ctx)

    @pytest.mark.asyncio
    async def test_raises_permission_error_without_api_key(self):
        """Verify missing key handling."""
        ctx = _mock_ctx_without_api_key()

        with pytest.raises(PermissionError, match="Missing API key"):
            await analysis_current(ctx)


class TestAnalysisStart:
    """Tests for analysis_start tool."""

    @pytest.mark.asyncio
    async def test_posts_to_run_endpoint(self):
        """Verify POST body and response."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 200,
            "status": "pending",
            "integration_name": "Test Integration",
            "config": {"days_back": 14},
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_start(ctx, days_back=14, include_weekends=False)

            assert result["analysis_id"] == 200
            assert result["status"] == "started"
            assert "Test Integration" in result["message"]
            assert "14 days" in result["message"]
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "/analyses/run"
            assert call_args[1]["json"]["time_range"] == 14
            assert call_args[1]["json"]["include_weekends"] is False

    @pytest.mark.asyncio
    async def test_uses_default_integration_when_none(self):
        """Verify None integration_id is not included in request."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 200,
            "status": "pending",
            "config": {"integration_name": "Default Integration"},
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_start(ctx, integration_id=None)

            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            # integration_id should not be in request when None
            assert "integration_id" not in request_body
            assert result["analysis_id"] == 200

    @pytest.mark.asyncio
    async def test_includes_explicit_integration_id(self):
        """Verify explicit integration_id is included in request."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 200,
            "status": "pending",
            "integration_name": "My Integration",
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await analysis_start(ctx, integration_id=5)

            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            assert request_body["integration_id"] == 5

    @pytest.mark.asyncio
    async def test_raises_lookup_error_when_integration_not_found(self):
        """Verify NotFoundError maps to LookupError for integration."""
        ctx = _mock_ctx_with_api_key()

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = NotFoundError("Integration not found")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LookupError, match="Integration not found"):
                await analysis_start(ctx, integration_id=999)

    @pytest.mark.asyncio
    async def test_raises_permission_error_without_api_key(self):
        """Verify missing key handling."""
        ctx = _mock_ctx_without_api_key()

        with pytest.raises(PermissionError, match="Missing API key"):
            await analysis_start(ctx)

    @pytest.mark.asyncio
    async def test_extracts_integration_name_from_config(self):
        """Verify integration_name fallback to config when not at top level."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 200,
            "status": "pending",
            # No top-level integration_name
            "config": {"integration_name": "Config Integration"},
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_start(ctx)

            assert "Config Integration" in result["message"]

    @pytest.mark.asyncio
    async def test_uses_fallback_integration_name(self):
        """Verify fallback when no integration_name in response."""
        ctx = _mock_ctx_with_api_key()
        mock_response = _mock_response({
            "id": 200,
            "status": "pending",
            "config": {},
        })

        with patch("app.mcp.server.OnCallHealthClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await analysis_start(ctx)

            # Should use "integration" as fallback
            assert "integration" in result["message"]
