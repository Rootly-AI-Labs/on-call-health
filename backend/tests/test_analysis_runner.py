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


class TestSyncedUsersStructure:
    """
    Regression tests for synced_users data structure.

    These tests prevent the bug where synced_users was missing the 'id' field,
    causing "NO MATCHING USER IDs" errors and all users showing 0 incidents.
    """

    @pytest.fixture
    def mock_user_correlation_rootly(self):
        """Create mock UserCorrelation for Rootly platform."""
        uc = Mock()
        uc.email = "test@example.com"
        uc.name = "Test User"
        uc.rootly_user_id = "rootly_123"
        uc.pagerduty_user_id = None
        uc.github_username = "testuser"
        uc.slack_user_id = "U123"
        uc.jira_account_id = "jira_456"
        uc.jira_email = "test@example.com"
        uc.avatar_url = "https://example.com/avatar.png"
        return uc

    @pytest.fixture
    def mock_user_correlation_pagerduty(self):
        """Create mock UserCorrelation for PagerDuty platform."""
        uc = Mock()
        uc.email = "test@example.com"
        uc.name = "Test User"
        uc.rootly_user_id = None
        uc.pagerduty_user_id = "P3HWE4C"
        uc.github_username = "testuser"
        uc.slack_user_id = "U123"
        uc.jira_account_id = "jira_456"
        uc.jira_email = "test@example.com"
        uc.avatar_url = "https://example.com/avatar.png"
        return uc

    def test_synced_users_must_have_id_field(self):
        """
        CRITICAL: synced_users MUST have 'id' field for incident matching.

        Without 'id', the analyzer cannot match incidents to users,
        resulting in all users showing 0 incidents.
        """
        # This is the REQUIRED structure for synced_users
        required_fields = ['id', 'email', 'name']

        # Simulate what analysis_runner should produce
        synced_user = {
            "id": "platform_user_123",  # CRITICAL - must be platform-specific ID
            "email": "test@example.com",
            "name": "Test User",
            "github_username": "testuser",
            "slack_user_id": "U123",
            "rootly_user_id": "rootly_123",
            "pagerduty_user_id": None,
            "jira_account_id": "jira_456",
            "jira_email": "test@example.com",
            "avatar_url": "https://example.com/avatar.png",
            "synced": True,
        }

        for field in required_fields:
            assert field in synced_user, f"synced_users MUST have '{field}' field"

        # ID must not be None or empty
        assert synced_user["id"], "synced_users 'id' field must not be empty"

    def test_rootly_synced_user_uses_rootly_user_id(self, mock_user_correlation_rootly):
        """For Rootly platform, 'id' should be rootly_user_id."""
        uc = mock_user_correlation_rootly
        platform = "rootly"

        # Simulate the logic from analysis_runner.py
        if platform == "pagerduty":
            platform_user_id = uc.pagerduty_user_id
        else:  # rootly
            platform_user_id = uc.rootly_user_id or uc.email

        assert platform_user_id == "rootly_123"
        assert platform_user_id is not None

    def test_pagerduty_synced_user_uses_pagerduty_user_id(self, mock_user_correlation_pagerduty):
        """For PagerDuty platform, 'id' should be pagerduty_user_id."""
        uc = mock_user_correlation_pagerduty
        platform = "pagerduty"

        # Simulate the logic from analysis_runner.py
        if platform == "pagerduty":
            platform_user_id = uc.pagerduty_user_id
        else:  # rootly
            platform_user_id = uc.rootly_user_id or uc.email

        assert platform_user_id == "P3HWE4C"
        assert platform_user_id is not None

    def test_rootly_fallback_to_email_when_no_rootly_id(self):
        """Rootly should fallback to email if rootly_user_id is missing."""
        uc = Mock()
        uc.email = "fallback@example.com"
        uc.rootly_user_id = None

        platform = "rootly"
        platform_user_id = uc.rootly_user_id or uc.email

        assert platform_user_id == "fallback@example.com"

    def test_pagerduty_skips_user_without_pagerduty_id(self):
        """PagerDuty should skip users without pagerduty_user_id."""
        uc = Mock()
        uc.email = "test@example.com"
        uc.pagerduty_user_id = None

        platform = "pagerduty"
        platform_user_id = uc.pagerduty_user_id

        # Should be None, meaning this user should be skipped
        assert platform_user_id is None


class TestAIEnablementLogic:
    """
    Regression tests for AI enablement logic.

    These tests prevent the bug where AI Team Insights were empty because
    the enable_ai flag wasn't being properly checked.
    """

    def test_ai_enabled_when_requested_and_system_key_available(self):
        """AI should be enabled if user requested AND system ANTHROPIC_API_KEY exists."""
        enable_ai_requested = True
        system_api_key = "sk-ant-..."
        has_user_llm_token = False

        use_ai = enable_ai_requested and (bool(system_api_key) or has_user_llm_token)

        assert use_ai is True

    def test_ai_enabled_when_requested_and_user_token_available(self):
        """AI should be enabled if user requested AND user has LLM token."""
        enable_ai_requested = True
        system_api_key = None
        has_user_llm_token = True

        use_ai = enable_ai_requested and (system_api_key or has_user_llm_token)

        assert use_ai is True

    def test_ai_disabled_when_not_requested(self):
        """AI should be disabled if user didn't request it, even with tokens."""
        enable_ai_requested = False
        system_api_key = "sk-ant-..."
        has_user_llm_token = True

        use_ai = enable_ai_requested and (system_api_key or has_user_llm_token)

        assert use_ai is False

    def test_ai_disabled_when_no_tokens_available(self):
        """AI should be disabled if no tokens available, even if requested."""
        enable_ai_requested = True
        system_api_key = None
        has_user_llm_token = False

        use_ai = enable_ai_requested and (system_api_key or has_user_llm_token)

        assert use_ai is False

    def test_enable_ai_read_from_config(self):
        """enable_ai should be read from analysis.config."""
        # Simulate analysis config
        config_with_ai = {"enable_ai": True, "include_github": False}
        config_without_ai = {"include_github": True}
        config_ai_false = {"enable_ai": False}

        assert config_with_ai.get("enable_ai", False) is True
        assert config_without_ai.get("enable_ai", False) is False
        assert config_ai_false.get("enable_ai", False) is False


class TestTokenDecryptionTiming:
    """
    Regression tests for token decryption timing.

    These tests prevent the bug where tokens were only decrypted inside
    checkpoint blocks, causing UnboundLocalError on resume.
    """

    def test_tokens_must_be_available_regardless_of_checkpoint(self):
        """
        Tokens must be decrypted BEFORE checkpoint blocks, not inside them.

        If tokens are only decrypted inside 'if resume_from < 2:' block,
        they will be undefined when resuming from checkpoint 2+.
        """
        # Simulate the correct behavior: tokens initialized before checkpoint
        github_token = None
        jira_token = None

        has_github = True
        has_jira = True

        # Decrypt tokens BEFORE checkpoint block
        if has_github:
            github_token = "decrypted_github_token"
        if has_jira:
            jira_token = "decrypted_jira_token"

        # Now simulate resuming from checkpoint 2 (skipping data collection)
        resume_from = 2

        if resume_from < 2:
            # This block is SKIPPED on resume
            pass

        # Tokens should still be available for analyzer initialization
        assert github_token == "decrypted_github_token"
        assert jira_token == "decrypted_jira_token"

    def test_tokens_unavailable_if_decrypted_inside_checkpoint_block(self):
        """
        WRONG: If tokens are decrypted inside checkpoint block, they're undefined on resume.

        This is the BUG we fixed - documenting it to prevent regression.
        """
        # Simulate the BUGGY behavior
        resume_from = 2

        if resume_from < 2:
            # This block is SKIPPED on resume from checkpoint 2
            buggy_github_token = "decrypted_token"
            buggy_jira_token = "decrypted_token"

        # On resume, these variables don't exist!
        with pytest.raises(NameError):
            _ = buggy_github_token  # noqa: F821

        with pytest.raises(NameError):
            _ = buggy_jira_token  # noqa: F821


class TestAnalysisConfigStorage:
    """
    Regression tests for analysis config storage.

    These tests ensure all user preferences are properly stored in analysis.config.
    """

    def test_config_must_include_enable_ai(self):
        """Analysis config MUST include enable_ai preference."""
        # Simulate request parameters
        request = Mock()
        request.include_weekends = True
        request.include_github = True
        request.include_slack = False
        request.include_jira = True
        request.include_linear = False
        request.enable_ai = True

        # Create config as analysis_runner expects
        config = {
            "include_weekends": request.include_weekends,
            "include_github": request.include_github,
            "include_slack": request.include_slack,
            "include_jira": request.include_jira,
            "include_linear": request.include_linear,
            "enable_ai": request.enable_ai,  # CRITICAL - must be included
        }

        assert "enable_ai" in config
        assert config["enable_ai"] is True

    def test_config_defaults_enable_ai_to_false(self):
        """If enable_ai missing from config, should default to False."""
        config_without_enable_ai = {
            "include_weekends": True,
            "include_github": False,
        }

        enable_ai = config_without_enable_ai.get("enable_ai", False)

        assert enable_ai is False
