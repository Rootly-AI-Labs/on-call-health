"""
Unit tests for checkpoint-aware analysis runner.

Tests cover:
- Checkpoint save/resume flow
- Graceful shutdown handling
- Error recovery
- Edge cases
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.workers.analysis_runner import (
    run_analysis_with_checkpoints,
    request_shutdown,
    check_shutdown,
)


# Module-level fixtures available to all test classes
@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = Mock()
    db.query = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_analysis():
    """Create mock analysis object."""
    analysis = Mock()
    analysis.id = 123
    analysis.status = "pending"
    analysis.results = None
    analysis.last_checkpoint = 0
    analysis.checkpoint_data = None
    analysis.attempt_count = 0
    analysis.user_id = 1
    analysis.rootly_integration_id = 1
    analysis.config = {"days_back": 30}
    return analysis


@pytest.fixture
def mock_integration():
    """Create mock integration."""
    integration = Mock()
    integration.id = 1
    integration.api_token = "test_token"
    integration.platform = "rootly"
    integration.name = "Test Integration"
    return integration


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = Mock()
    user.id = 1
    user.organization_id = 1
    user.llm_token = None
    user.llm_provider = None
    return user


class TestAnalysisRunner:
    """Test checkpoint-aware analysis execution."""

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    @patch('app.workers.analysis_runner.save_checkpoint')
    @patch('app.workers.analysis_runner.clear_checkpoint')
    @patch('app.workers.analysis_runner.RootlyAPIClient')
    @patch('app.workers.analysis_runner.UnifiedBurnoutAnalyzer')
    async def test_run_analysis_from_scratch(
        self,
        mock_analyzer_class,
        mock_client_class,
        mock_clear,
        mock_save,
        mock_load,
        mock_db,
        mock_analysis,
        mock_integration,
        mock_user,
    ):
        """Test running analysis from scratch (no checkpoint)."""
        # Setup mocks
        mock_load.return_value = None  # No checkpoint

        # Mock database queries
        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = mock_integration

        mock_query_user = Mock()
        mock_query_user.filter.return_value.first.return_value = mock_user

        def query_side_effect(model):
            if model.__name__ == "Analysis":
                return mock_query_analysis
            elif model.__name__ == "RootlyIntegration":
                return mock_query_integration
            elif model.__name__ == "User":
                return mock_query_user
            else:
                mock_result = Mock()
                mock_result.filter.return_value.first.return_value = None
                mock_result.filter.return_value.all.return_value = []
                return mock_result

        mock_db.query.side_effect = query_side_effect

        # Mock API client
        mock_client = AsyncMock()
        mock_client.collect_analysis_data.return_value = {
            "users": [{"id": "1", "name": "Test User"}],
            "incidents": [{"id": "1", "title": "Test Incident"}],
            "collection_metadata": {},
        }
        mock_client_class.return_value = mock_client

        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_burnout = AsyncMock(return_value={"team_health": "good"})
        mock_analyzer_class.return_value = mock_analyzer

        # Run analysis
        result = await run_analysis_with_checkpoints(
            analysis_id=123,
            integration_id=1,
            days_back=30,
            user_id=1,
            db=mock_db,
        )

        # Verify checkpoints were saved
        assert mock_save.call_count >= 2  # At least checkpoints 1 and 2

        # Verify analysis completed
        assert result["status"] == "completed"
        assert mock_analysis.status == "completed"
        assert mock_clear.called  # Checkpoint cleared on completion

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    @patch('app.workers.analysis_runner.save_checkpoint')
    async def test_run_analysis_resume_from_checkpoint(
        self,
        mock_save,
        mock_load,
        mock_db,
        mock_analysis,
        mock_integration,
        mock_user,
    ):
        """Test resuming analysis from checkpoint."""
        # Setup checkpoint data
        checkpoint_data = {
            "checkpoint": 1,
            "collected_data": {
                "users": [{"id": "1"}],
                "incidents": [{"id": "1"}],
                "metadata": {},
            },
            "phase_durations": {"data_fetch": 10.5},
        }
        mock_load.return_value = checkpoint_data

        # Mock database queries
        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = mock_integration

        mock_query_user = Mock()
        mock_query_user.filter.return_value.first.return_value = mock_user

        def query_side_effect(model):
            if hasattr(model, '__name__'):
                if model.__name__ == "Analysis":
                    return mock_query_analysis
                elif model.__name__ == "RootlyIntegration":
                    return mock_query_integration
                elif model.__name__ == "User":
                    return mock_query_user
            mock_result = Mock()
            mock_result.filter.return_value.first.return_value = None
            mock_result.filter.return_value.all.return_value = []
            return mock_result

        mock_db.query.side_effect = query_side_effect

        # Mock analyzer to succeed
        with patch('app.workers.analysis_runner.UnifiedBurnoutAnalyzer') as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.analyze_burnout = AsyncMock(return_value={"status": "good"})
            mock_analyzer_class.return_value = mock_analyzer

            with patch('app.workers.analysis_runner.clear_checkpoint') as mock_clear:
                result = await run_analysis_with_checkpoints(
                    analysis_id=123,
                    integration_id=1,
                    days_back=30,
                    user_id=1,
                    db=mock_db,
                )

                # Verify it loaded checkpoint
                mock_load.assert_called_once()

                # Verify attempt count was incremented
                assert mock_analysis.attempt_count == 1

                # Should skip checkpoint 1 (already done)
                # and start from checkpoint 2
                assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_shutdown_request_handling(self):
        """Test that shutdown requests are detected."""
        # Request shutdown
        request_shutdown()

        # Check shutdown flag
        assert check_shutdown() is True

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    @patch('app.workers.analysis_runner.save_checkpoint')
    async def test_analysis_saves_checkpoint_on_shutdown(
        self,
        mock_save,
        mock_load,
        mock_db,
        mock_analysis,
        mock_integration,
        mock_user,
    ):
        """Test that analysis saves checkpoint when shutdown is requested."""
        mock_load.return_value = None

        # Mock database queries
        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = mock_integration

        mock_query_user = Mock()
        mock_query_user.filter.return_value.first.return_value = mock_user

        def query_side_effect(model):
            if hasattr(model, '__name__'):
                if model.__name__ == "Analysis":
                    return mock_query_analysis
                elif model.__name__ == "RootlyIntegration":
                    return mock_query_integration
                elif model.__name__ == "User":
                    return mock_query_user
            mock_result = Mock()
            mock_result.filter.return_value.first.return_value = None
            mock_result.filter.return_value.all.return_value = []
            return mock_result

        mock_db.query.side_effect = query_side_effect

        # Mock API client to trigger shutdown after data fetch
        with patch('app.workers.analysis_runner.RootlyAPIClient') as mock_client_class:
            mock_client = AsyncMock()

            async def collect_then_shutdown(*args, **kwargs):
                # Request shutdown after data collection
                request_shutdown()
                return {
                    "users": [{"id": "1"}],
                    "incidents": [{"id": "1"}],
                    "collection_metadata": {},
                }

            mock_client.collect_analysis_data = collect_then_shutdown
            mock_client_class.return_value = mock_client

            result = await run_analysis_with_checkpoints(
                analysis_id=123,
                integration_id=1,
                days_back=30,
                user_id=1,
                db=mock_db,
            )

            # Should have saved checkpoint before exiting
            assert mock_save.called
            assert result["status"] == "interrupted"

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    async def test_analysis_fails_after_max_attempts(
        self,
        mock_load,
        mock_db,
        mock_analysis,
        mock_integration,
        mock_user,
    ):
        """Test that analysis fails after 3 resume attempts."""
        # Set up checkpoint to resume
        checkpoint_data = {
            "checkpoint": 1,
            "collected_data": {"users": [], "incidents": [], "metadata": {}},
        }
        mock_load.return_value = checkpoint_data

        # Set attempt count to 3 (max)
        mock_analysis.attempt_count = 3

        # Mock database queries
        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = mock_integration

        def query_side_effect(model):
            if hasattr(model, '__name__'):
                if model.__name__ == "Analysis":
                    return mock_query_analysis
                elif model.__name__ == "RootlyIntegration":
                    return mock_query_integration
            return Mock()

        mock_db.query.side_effect = query_side_effect

        # Should raise exception for exceeding max attempts
        with pytest.raises(Exception, match="exceeded maximum resume attempts"):
            await run_analysis_with_checkpoints(
                analysis_id=123,
                integration_id=1,
                days_back=30,
                user_id=1,
                db=mock_db,
            )

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    async def test_analysis_handles_errors_gracefully(
        self,
        mock_load,
        mock_db,
        mock_analysis,
        mock_integration,
        mock_user,
    ):
        """Test that analysis marks itself as failed on errors."""
        mock_load.return_value = None

        # Mock database queries
        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = mock_integration

        def query_side_effect(model):
            if hasattr(model, '__name__'):
                if model.__name__ == "Analysis":
                    return mock_query_analysis
                elif model.__name__ == "RootlyIntegration":
                    return mock_query_integration
                elif model.__name__ == "User":
                    mock_result = Mock()
                    mock_result.filter.return_value.first.return_value = mock_user
                    return mock_result
            return Mock()

        mock_db.query.side_effect = query_side_effect

        # Mock API client to raise error
        with patch('app.workers.analysis_runner.RootlyAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.collect_analysis_data.side_effect = Exception("API Error")
            mock_client_class.return_value = mock_client

            # Should raise exception
            with pytest.raises(Exception, match="API Error"):
                await run_analysis_with_checkpoints(
                    analysis_id=123,
                    integration_id=1,
                    days_back=30,
                    user_id=1,
                    db=mock_db,
                )

            # Should have marked analysis as failed
            assert mock_analysis.status == "failed"
            assert "API Error" in mock_analysis.error_message


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    async def test_analysis_not_found(self, mock_load, mock_db):
        """Test handling when analysis doesn't exist."""
        mock_load.return_value = None

        # Mock database to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(Exception, match="Analysis 999 not found"):
            await run_analysis_with_checkpoints(
                analysis_id=999,
                integration_id=1,
                days_back=30,
                user_id=1,
                db=mock_db,
            )

    @pytest.mark.asyncio
    @patch('app.workers.analysis_runner.load_checkpoint')
    async def test_integration_not_found(self, mock_load, mock_db):
        """Test handling when integration doesn't exist."""
        mock_load.return_value = None

        # Mock analysis exists but integration doesn't
        mock_analysis = Mock()
        mock_analysis.id = 123
        mock_analysis.attempt_count = 0

        mock_query_analysis = Mock()
        mock_query_analysis.filter.return_value.first.return_value = mock_analysis

        mock_query_integration = Mock()
        mock_query_integration.filter.return_value.first.return_value = None

        def query_side_effect(model):
            if hasattr(model, '__name__') and model.__name__ == "Analysis":
                return mock_query_analysis
            else:
                return mock_query_integration

        mock_db.query.side_effect = query_side_effect

        with pytest.raises(Exception, match="Integration with ID 999 not found"):
            await run_analysis_with_checkpoints(
                analysis_id=123,
                integration_id=999,
                days_back=30,
                user_id=1,
                db=mock_db,
            )
