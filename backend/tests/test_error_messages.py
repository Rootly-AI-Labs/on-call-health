"""Tests for error message security - ensure no token leakage."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestErrorMessageSecurity:
    """Tests to verify error messages never contain actual tokens."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def sample_tokens(self):
        """Sample tokens that should NEVER appear in error messages."""
        return [
            "super_secret_jira_token_12345",
            "lin_api_secret_linear_key_67890",
            "gAAAA_encrypted_looking_token",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ]

    def test_jira_error_messages_contain_no_tokens(self):
        """Verify JIRA_ERROR_MESSAGES never contain sample token patterns."""
        from backend.app.core.error_messages import JIRA_ERROR_MESSAGES

        for error_type, error_info in JIRA_ERROR_MESSAGES.items():
            message = error_info.get("message", "")
            action = error_info.get("action", "")

            # Should not contain token-like strings
            assert "secret" not in message.lower()
            assert "secret" not in action.lower()
            assert "password" not in message.lower()
            assert "password" not in action.lower()

            # Should contain helpful guidance
            assert len(message) > 10
            assert len(action) > 10

    def test_linear_error_messages_contain_no_tokens(self):
        """Verify LINEAR_ERROR_MESSAGES never contain sample token patterns."""
        from backend.app.core.error_messages import LINEAR_ERROR_MESSAGES

        for error_type, error_info in LINEAR_ERROR_MESSAGES.items():
            message = error_info.get("message", "")
            action = error_info.get("action", "")

            # Should not contain token-like strings
            assert "secret" not in message.lower()
            assert "secret" not in action.lower()
            assert "lin_api_" not in message

    def test_get_error_response_never_includes_token(self, sample_tokens):
        """get_error_response never includes actual token values."""
        from backend.app.core.error_messages import get_error_response

        for provider in ["jira", "linear"]:
            for error_type in ["authentication", "permissions", "network", "format"]:
                response = get_error_response(provider, error_type)

                # Check response doesn't contain any sample tokens
                response_str = str(response)
                for token in sample_tokens:
                    assert token not in response_str

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_jira_validation_error_excludes_token(self, mock_client, mock_db, sample_tokens):
        """Jira validation errors never include the actual token."""
        from backend.app.services.integration_validator import IntegrationValidator

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        for token in sample_tokens:
            result = asyncio.get_event_loop().run_until_complete(
                validator.validate_manual_token("jira", token, "https://test.atlassian.net")
            )

            # Token should never appear in response
            result_str = str(result)
            assert token not in result_str, f"Token leaked in response: {token}"

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_linear_validation_error_excludes_token(self, mock_client, mock_db):
        """Linear validation errors never include the actual token."""
        from backend.app.services.integration_validator import IntegrationValidator

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        secret_token = "lin_api_super_secret_key_12345"

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("linear", secret_token)
        )

        # Token should never appear in response
        result_str = str(result)
        assert secret_token not in result_str
        assert "super_secret" not in result_str

    def test_notification_message_excludes_token(self, mock_db):
        """Token validation failure notification never includes token."""
        from backend.app.services.notification_service import NotificationService
        from unittest.mock import MagicMock

        # Mock user
        user = MagicMock()
        user.id = 1
        user.organization_id = 1

        # Mock db session
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        service = NotificationService(mock_db)

        # Create notification with error message
        notification = service.create_token_validation_failure_notification(
            user=user,
            provider="jira",
            error_type="authentication",
            error_message="Your Jira token is invalid. Please reconnect."
        )

        # Notification should not contain any token-like strings
        assert "lin_api_" not in notification.message
        assert "secret" not in notification.message.lower()
        assert "password" not in notification.message.lower()


class TestErrorMessageContent:
    """Tests for error message content quality."""

    def test_all_jira_errors_have_required_fields(self):
        """All Jira error messages have message and action fields."""
        from backend.app.core.error_messages import JIRA_ERROR_MESSAGES

        for error_type, error_info in JIRA_ERROR_MESSAGES.items():
            assert "message" in error_info, f"Missing 'message' for {error_type}"
            assert "action" in error_info, f"Missing 'action' for {error_type}"
            assert len(error_info["message"]) > 20, f"Message too short for {error_type}"
            assert len(error_info["action"]) > 10, f"Action too short for {error_type}"

    def test_all_linear_errors_have_required_fields(self):
        """All Linear error messages have message and action fields."""
        from backend.app.core.error_messages import LINEAR_ERROR_MESSAGES

        for error_type, error_info in LINEAR_ERROR_MESSAGES.items():
            assert "message" in error_info, f"Missing 'message' for {error_type}"
            assert "action" in error_info, f"Missing 'action' for {error_type}"
            assert len(error_info["message"]) > 20, f"Message too short for {error_type}"
            assert len(error_info["action"]) > 10, f"Action too short for {error_type}"

    def test_error_messages_are_platform_specific(self):
        """Jira and Linear error messages reference their respective platforms."""
        from backend.app.core.error_messages import JIRA_ERROR_MESSAGES, LINEAR_ERROR_MESSAGES

        # Jira messages should reference Jira concepts
        jira_auth = JIRA_ERROR_MESSAGES["authentication"]["message"]
        assert "jira" in jira_auth.lower() or "atlassian" in jira_auth.lower()

        # Linear messages should reference Linear concepts
        linear_auth = LINEAR_ERROR_MESSAGES["authentication"]["message"]
        assert "linear" in linear_auth.lower()

    def test_help_urls_are_valid_format(self):
        """Help URLs are valid HTTPS URLs."""
        from backend.app.core.error_messages import JIRA_ERROR_MESSAGES, LINEAR_ERROR_MESSAGES

        for error_info in JIRA_ERROR_MESSAGES.values():
            if "help_url" in error_info:
                url = error_info["help_url"]
                assert url.startswith("https://"), f"Invalid URL: {url}"

        for error_info in LINEAR_ERROR_MESSAGES.values():
            if "help_url" in error_info:
                url = error_info["help_url"]
                assert url.startswith("https://"), f"Invalid URL: {url}"
