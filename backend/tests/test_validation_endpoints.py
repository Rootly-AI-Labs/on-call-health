"""Tests for token validation endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestJiraValidateToken:
    """Tests for POST /api/jira/validate-token endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        user.organization_id = 1
        return user

    def test_missing_token_returns_format_error(self, mock_db, mock_user):
        """Request without token returns format error."""
        from backend.app.services.integration_validator import IntegrationValidator

        # Simulate calling validate_manual_token with empty token
        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("jira", "", "https://test.atlassian.net")
        )

        assert result["valid"] is False
        assert result["error_type"] == "format"
        assert "format" in result["message"].lower() or "token" in result["message"].lower()

    def test_missing_site_url_returns_site_url_error(self, mock_db, mock_user):
        """Request without site_url returns site_url error."""
        from backend.app.services.integration_validator import IntegrationValidator

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("jira", "test_token", "")
        )

        assert result["valid"] is False
        assert result["error_type"] == "site_url"

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_valid_token_returns_user_info(self, mock_client, mock_db):
        """Valid token returns user info from Jira API."""
        from backend.app.services.integration_validator import IntegrationValidator

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "displayName": "Test User",
            "emailAddress": "test@example.com",
            "accountId": "abc123"
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("jira", "valid_token", "https://test.atlassian.net")
        )

        assert result["valid"] is True
        assert result["user_info"]["display_name"] == "Test User"
        assert result["user_info"]["email"] == "test@example.com"

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_401_returns_authentication_error(self, mock_client, mock_db):
        """401 response returns authentication error type."""
        from backend.app.services.integration_validator import IntegrationValidator

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("jira", "bad_token", "https://test.atlassian.net")
        )

        assert result["valid"] is False
        assert result["error_type"] == "authentication"

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_403_returns_permissions_error(self, mock_client, mock_db):
        """403 response returns permissions error type."""
        from backend.app.services.integration_validator import IntegrationValidator

        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("jira", "limited_token", "https://test.atlassian.net")
        )

        assert result["valid"] is False
        assert result["error_type"] == "permissions"


class TestLinearValidateToken:
    """Tests for POST /api/linear/validate-token endpoint."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_missing_token_returns_format_error(self, mock_db):
        """Request without token returns format error."""
        from backend.app.services.integration_validator import IntegrationValidator

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("linear", "")
        )

        assert result["valid"] is False
        assert result["error_type"] == "format"

    def test_invalid_format_returns_format_error(self, mock_db):
        """Token not starting with lin_api_ returns format error."""
        from backend.app.services.integration_validator import IntegrationValidator

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("linear", "invalid_prefix_token")
        )

        assert result["valid"] is False
        assert result["error_type"] == "format"
        assert "lin_api_" in result["message"]

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_valid_token_returns_user_info(self, mock_client, mock_db):
        """Valid token returns user info from Linear API."""
        from backend.app.services.integration_validator import IntegrationValidator

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "viewer": {
                    "id": "user123",
                    "name": "Test User",
                    "email": "test@example.com"
                }
            }
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("linear", "lin_api_valid_token")
        )

        assert result["valid"] is True
        assert result["user_info"]["display_name"] == "Test User"
        assert result["user_info"]["email"] == "test@example.com"

    @patch("backend.app.services.integration_validator.httpx.AsyncClient")
    def test_401_returns_authentication_error(self, mock_client, mock_db):
        """401 response returns authentication error type."""
        from backend.app.services.integration_validator import IntegrationValidator

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        validator = IntegrationValidator(mock_db)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            validator.validate_manual_token("linear", "lin_api_bad_token")
        )

        assert result["valid"] is False
        assert result["error_type"] == "authentication"
