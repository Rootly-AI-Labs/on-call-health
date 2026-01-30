"""Unit tests for MCP server tools."""
import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.mcp.server import (
    _get_integration_for_user,
    _handle_task_exception,
    analysis_start,
    analysis_status,
    analysis_results,
    analysis_current,
    integrations_list,
)


class TestGetIntegrationForUser:
    """Test _get_integration_for_user helper."""

    def test_returns_integration_by_id(self):
        """Test finding integration by explicit ID."""
        mock_integration = MagicMock(id=5, user_id=1, is_active=True)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_integration

        result = _get_integration_for_user(mock_db, user_id=1, integration_id=5)

        assert result == mock_integration

    def test_raises_lookup_error_when_integration_id_not_found(self):
        """Test error when explicit integration ID doesn't exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(LookupError, match="Integration not found"):
            _get_integration_for_user(mock_db, user_id=1, integration_id=999)

    def test_returns_default_integration_when_no_id(self):
        """Test fallback to default integration when no ID provided."""
        mock_default = MagicMock(id=10, is_default=True, is_active=True)
        mock_db = MagicMock()

        # First call (by ID) - not called since integration_id is None
        # Second call (default) - returns the default integration
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_default,  # default integration query
        ]

        result = _get_integration_for_user(mock_db, user_id=1, integration_id=None)

        assert result == mock_default

    def test_returns_any_active_when_no_default(self):
        """Test fallback to any active integration when no default."""
        mock_active = MagicMock(id=15, is_default=False, is_active=True)
        mock_db = MagicMock()

        # First call (default) returns None, second call (any active) returns integration
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # no default
            mock_active,  # any active
        ]

        result = _get_integration_for_user(mock_db, user_id=1, integration_id=None)

        assert result == mock_active

    def test_raises_value_error_when_no_active_integration(self):
        """Test error when user has no active integrations."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # no default
            None,  # no active
        ]

        with pytest.raises(ValueError, match="No active Rootly integration found"):
            _get_integration_for_user(mock_db, user_id=1, integration_id=None)


class TestHandleTaskException:
    """Test _handle_task_exception callback."""

    def test_logs_exception_when_task_fails(self):
        """Test that exceptions are logged."""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = ValueError("test error")

        with patch("app.mcp.server.logger") as mock_logger:
            _handle_task_exception(mock_task)

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Background analysis task failed" in call_args[0][0]

    def test_does_nothing_when_task_cancelled(self):
        """Test that cancelled tasks are ignored."""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = True

        with patch("app.mcp.server.logger") as mock_logger:
            _handle_task_exception(mock_task)

            mock_logger.error.assert_not_called()

    def test_does_nothing_when_task_succeeds(self):
        """Test that successful tasks don't log errors."""
        mock_task = MagicMock()
        mock_task.cancelled.return_value = False
        mock_task.exception.return_value = None

        with patch("app.mcp.server.logger") as mock_logger:
            _handle_task_exception(mock_task)

            mock_logger.error.assert_not_called()


class TestAnalysisTools:
    """Test analysis MCP tools."""

    @pytest.mark.asyncio
    async def test_analysis_start_requires_auth(self):
        """Test that analysis_start requires authentication."""
        mock_ctx = SimpleNamespace()

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.side_effect = PermissionError("Missing bearer token")

            with pytest.raises(PermissionError, match="Missing bearer token"):
                await analysis_start(mock_ctx)

    @pytest.mark.asyncio
    async def test_analysis_start_creates_analysis(self):
        """Test that analysis_start creates an analysis record."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)
        mock_integration = MagicMock(id=5, name="Test Integration", organization_name="Test Org")
        mock_analysis = MagicMock(id=100)

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user, \
             patch("app.mcp.server._get_integration_for_user") as mock_get_integration, \
             patch("app.mcp.server.Analysis") as mock_analysis_cls, \
             patch("app.mcp.server.run_analysis_task") as mock_run_task:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_get_integration.return_value = mock_integration
            mock_analysis_cls.return_value = mock_analysis
            mock_run_task.return_value = AsyncMock()()

            result = await analysis_start(mock_ctx, days_back=14)

            assert result["analysis_id"] == 100
            assert result["status"] == "started"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_analysis_status_returns_analysis_info(self):
        """Test that analysis_status returns analysis information."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)
        mock_analysis = MagicMock(
            id=100,
            status="completed",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 5, 0),
            config={"days_back": 30},
            error_message=None,
            results={"team_analysis": [{"risk_level": "high"}], "team_summary": {"average_score": 65}},
        )

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = mock_analysis

            result = await analysis_status(mock_ctx, analysis_id=100)

            assert result["id"] == 100
            assert result["status"] == "completed"
            assert result["results_summary"]["high_risk_count"] == 1

    @pytest.mark.asyncio
    async def test_analysis_status_not_found(self):
        """Test that analysis_status raises error when not found."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(LookupError, match="Analysis not found"):
                await analysis_status(mock_ctx, analysis_id=999)

    @pytest.mark.asyncio
    async def test_analysis_results_requires_completed_status(self):
        """Test that analysis_results requires completed analysis."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)
        mock_analysis = MagicMock(id=100, status="pending")

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = mock_analysis

            with pytest.raises(ValueError, match="Analysis not completed yet"):
                await analysis_results(mock_ctx, analysis_id=100)

    @pytest.mark.asyncio
    async def test_analysis_current_returns_most_recent(self):
        """Test that analysis_current returns most recent analysis."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)
        mock_analysis = MagicMock(
            id=100,
            status="completed",
            created_at=datetime(2024, 1, 1),
            completed_at=datetime(2024, 1, 1),
            config={},
            error_message=None,
        )

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_analysis

            result = await analysis_current(mock_ctx)

            assert result["id"] == 100

    @pytest.mark.asyncio
    async def test_analysis_current_not_found(self):
        """Test that analysis_current raises error when no analyses exist."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user
            mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

            with pytest.raises(LookupError, match="No analyses found"):
                await analysis_current(mock_ctx)


class TestIntegrationsListTool:
    """Test integrations_list MCP tool."""

    @pytest.mark.asyncio
    async def test_integrations_list_returns_all_types(self):
        """Test that integrations_list returns all integration types."""
        mock_ctx = SimpleNamespace()
        mock_user = MagicMock(id=1)

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user, \
             patch("app.mcp.server.serialize_rootly_integration") as mock_serialize_rootly, \
             patch("app.mcp.server.serialize_github_integration") as mock_serialize_github, \
             patch("app.mcp.server.serialize_slack_integration") as mock_serialize_slack, \
             patch("app.mcp.server.serialize_jira_integration") as mock_serialize_jira, \
             patch("app.mcp.server.serialize_linear_integration") as mock_serialize_linear:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.return_value = mock_user

            # Mock each query to return empty list
            mock_db.query.return_value.filter.return_value.all.return_value = []

            result = await integrations_list(mock_ctx)

            assert "rootly" in result
            assert "github" in result
            assert "slack" in result
            assert "jira" in result
            assert "linear" in result

    @pytest.mark.asyncio
    async def test_integrations_list_requires_auth(self):
        """Test that integrations_list requires authentication."""
        mock_ctx = SimpleNamespace()

        with patch("app.mcp.server._get_db") as mock_get_db, \
             patch("app.mcp.server.require_user") as mock_require_user:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_require_user.side_effect = PermissionError("Invalid or expired token")

            with pytest.raises(PermissionError, match="Invalid or expired token"):
                await integrations_list(mock_ctx)
