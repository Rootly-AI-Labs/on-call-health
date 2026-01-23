"""
Tests for integration validation service.
"""
import unittest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
import httpx
import asyncio

from app.services.integration_validator import IntegrationValidator
from app.models import GitHubIntegration, LinearIntegration, JiraIntegration


class TestIntegrationValidator(unittest.TestCase):
    """Test suite for IntegrationValidator service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    # GitHub Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_success(self, mock_decrypt):
        """Test successful GitHub validation."""
        # Setup
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.user_id = 1
        mock_integration.github_token = "encrypted_token"

        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        # Mock httpx response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # Execute
            result = self._run_async(self.validator._validate_github(user_id=1))

        # Assert
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_expired_token(self, mock_decrypt):
        """Test GitHub validation with expired token (401)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_forbidden(self, mock_decrypt):
        """Test GitHub validation with forbidden token (403)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "forbidden_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("lacks required permissions", result["error"])

    def test_validate_github_no_integration(self):
        """Test GitHub validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertIsNone(result)

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_timeout(self, mock_decrypt):
        """Test GitHub validation with timeout."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("timed out", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_network_error(self, mock_decrypt):
        """Test GitHub validation with network error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.NetworkError("Network error")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("Cannot reach", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_decryption_error(self, mock_decrypt):
        """Test GitHub validation with decryption error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.side_effect = Exception("Decryption failed")

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("decryption failed", result["error"].lower())

    # Linear Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_success(self, mock_decrypt):
        """Test successful Linear validation."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_graphql_error(self, mock_decrypt):
        """Test Linear validation with GraphQL unauthorized error."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "invalid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}]}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_linear_no_integration(self):
        """Test Linear validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertIsNone(result)

    # Jira Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_success(self, mock_decrypt):
        """Test successful Jira validation."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_expired_token(self, mock_decrypt):
        """Test Jira validation with expired token (401)."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_jira_no_integration(self):
        """Test Jira validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
