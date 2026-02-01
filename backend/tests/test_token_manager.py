"""Unit tests for TokenManager service."""
import asyncio
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, patch

from app.models import JiraIntegration, LinearIntegration
from app.services.token_manager import TokenManager


class TestTokenManager(TestCase):
    """Test cases for TokenManager service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.manager = TokenManager(self.mock_db)

    def _run_async(self, coro):
        """Helper to run async tests."""
        return asyncio.get_event_loop().run_until_complete(coro)

    # OAuth token tests

    @patch("app.services.token_manager.decrypt_token")
    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_oauth_no_refresh_needed(
        self, mock_needs_refresh, mock_decrypt
    ):
        """Test OAuth token retrieval when no refresh needed."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = True
        mock_integration.is_manual = False
        mock_integration.has_token = True
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(
            hours=12
        )
        mock_integration.user_id = 1

        mock_needs_refresh.return_value = False
        mock_decrypt.return_value = "decrypted_token"

        token = self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertEqual(token, "decrypted_token")
        mock_decrypt.assert_called_once_with("encrypted_token")
        self.mock_db.refresh.assert_called_once_with(mock_integration)

    @patch("app.services.token_manager.refresh_token_with_lock", new_callable=AsyncMock)
    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_oauth_refresh_needed(
        self, mock_needs_refresh, mock_refresh_lock
    ):
        """Test OAuth token retrieval when refresh is needed."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = True
        mock_integration.is_manual = False
        mock_integration.has_token = True
        mock_integration.supports_refresh = True
        mock_integration.has_refresh_token = True
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(
            minutes=5
        )
        mock_integration.user_id = 1
        mock_integration.id = 123

        mock_needs_refresh.return_value = True
        mock_refresh_lock.return_value = "new_decrypted_token"

        token = self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertEqual(token, "new_decrypted_token")
        mock_refresh_lock.assert_called_once()
        call_args = mock_refresh_lock.call_args
        self.assertEqual(call_args.kwargs["provider"], "jira")
        self.assertEqual(call_args.kwargs["integration_id"], 123)
        self.assertEqual(call_args.kwargs["user_id"], 1)

    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_oauth_no_access_token(self, mock_needs_refresh):
        """Test OAuth token retrieval when access token is missing."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = True
        mock_integration.is_manual = False
        mock_integration.has_token = False

        with self.assertRaises(ValueError) as context:
            self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertIn("No access token available", str(context.exception))

    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_oauth_no_refresh_token(self, mock_needs_refresh):
        """Test OAuth token retrieval when expired but no refresh token."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.is_oauth = True
        mock_integration.is_manual = False
        mock_integration.has_token = True
        mock_integration.supports_refresh = False
        mock_integration.has_refresh_token = False
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(
            minutes=5
        )
        mock_integration.user_id = 1

        mock_needs_refresh.return_value = True

        with self.assertRaises(ValueError) as context:
            self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertIn("Please reconnect Linear", str(context.exception))

    # Manual token tests

    @patch("app.services.token_manager.decrypt_token")
    def test_get_valid_token_manual_success(self, mock_decrypt):
        """Test manual token retrieval returns decrypted token directly."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.is_oauth = False
        mock_integration.is_manual = True
        mock_integration.has_token = True
        mock_integration.access_token = "encrypted_manual_token"
        mock_integration.user_id = 1

        mock_decrypt.return_value = "decrypted_manual_token"

        token = self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertEqual(token, "decrypted_manual_token")
        mock_decrypt.assert_called_once_with("encrypted_manual_token")

    def test_get_valid_token_manual_no_access_token(self):
        """Test manual token retrieval when token is missing."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = False
        mock_integration.is_manual = True
        mock_integration.has_token = False

        with self.assertRaises(ValueError) as context:
            self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertIn("No access token available", str(context.exception))

    @patch("app.services.token_manager.decrypt_token")
    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_manual_no_validation(
        self, mock_needs_refresh, mock_decrypt
    ):
        """Test that manual tokens don't trigger validation or API calls."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = False
        mock_integration.is_manual = True
        mock_integration.has_token = True
        mock_integration.access_token = "encrypted_manual_token"
        mock_integration.user_id = 1

        mock_decrypt.return_value = "decrypted_manual_token"

        token = self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertEqual(token, "decrypted_manual_token")
        # Verify needs_refresh was NOT called for manual tokens
        mock_needs_refresh.assert_not_called()

    # Edge case tests

    def test_get_valid_token_unknown_source(self):
        """Test that unknown token_source raises ValueError."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = False
        mock_integration.is_manual = False
        mock_integration.token_source = "unknown"

        with self.assertRaises(ValueError) as context:
            self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertIn("Unknown token source", str(context.exception))

    @patch("app.services.token_manager.decrypt_token")
    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_jira_vs_linear(self, mock_needs_refresh, mock_decrypt):
        """Test that both Jira and Linear integrations work correctly."""
        # Test Jira
        jira_integration = Mock(spec=JiraIntegration)
        jira_integration.is_oauth = True
        jira_integration.is_manual = False
        jira_integration.has_token = True
        jira_integration.access_token = "encrypted_jira_token"
        jira_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(
            hours=12
        )
        jira_integration.user_id = 1

        mock_needs_refresh.return_value = False
        mock_decrypt.return_value = "decrypted_jira_token"

        jira_token = self._run_async(self.manager.get_valid_token(jira_integration))
        self.assertEqual(jira_token, "decrypted_jira_token")

        # Test Linear
        linear_integration = Mock(spec=LinearIntegration)
        linear_integration.is_oauth = True
        linear_integration.is_manual = False
        linear_integration.has_token = True
        linear_integration.access_token = "encrypted_linear_token"
        linear_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(
            hours=12
        )
        linear_integration.user_id = 2

        mock_decrypt.return_value = "decrypted_linear_token"

        linear_token = self._run_async(self.manager.get_valid_token(linear_integration))
        self.assertEqual(linear_token, "decrypted_linear_token")

    @patch("app.services.token_manager.refresh_token_with_lock", new_callable=AsyncMock)
    @patch("app.services.token_manager.needs_refresh")
    def test_get_valid_token_refresh_exception_handling(
        self, mock_needs_refresh, mock_refresh_lock
    ):
        """Test that refresh exceptions are properly handled."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.is_oauth = True
        mock_integration.is_manual = False
        mock_integration.has_token = True
        mock_integration.supports_refresh = True
        mock_integration.has_refresh_token = True
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(
            minutes=5
        )
        mock_integration.user_id = 1
        mock_integration.id = 123

        mock_needs_refresh.return_value = True

        # Simulate refresh failure
        mock_refresh_lock.side_effect = Exception("OAuth API error")

        with self.assertRaises(ValueError) as context:
            self._run_async(self.manager.get_valid_token(mock_integration))

        self.assertIn("Please reconnect Jira", str(context.exception))
        # Verify rollback was attempted
        self.mock_db.rollback.assert_called_once()
