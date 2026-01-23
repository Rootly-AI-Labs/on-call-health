"""
Integration validation service for pre-flight connection checks.

Validates API tokens for GitHub, Linear, and Jira integrations before
starting analysis to detect stale/expired tokens early.
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import httpx

from ..core.config import settings
from ..models import GitHubIntegration, LinearIntegration, JiraIntegration

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """Get the encryption key from settings."""
    from base64 import urlsafe_b64encode

    key = settings.JWT_SECRET_KEY.encode()
    if len(key) < 32:
        key = key.ljust(32, b'0')
    else:
        key = key[:32]
    return urlsafe_b64encode(key)


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()


class IntegrationValidator:
    """Service for validating integration connections."""

    def __init__(self, db: Session):
        self.db = db

    async def validate_all_integrations(
        self,
        user_id: int,
        integration_id: int
    ) -> Dict[str, Dict[str, any]]:
        """
        Validate all enabled integrations for a user.

        Returns dict with status for each integration:
        {
            "github": {"valid": True/False, "error": "..."},
            "linear": {"valid": True/False, "error": "..."},
            "jira": {"valid": True/False, "error": "..."}
        }
        """
        validators = [
            ("github", self._validate_github),
            ("linear", self._validate_linear),
            ("jira", self._validate_jira),
        ]

        results = {}
        for name, validator_func in validators:
            result = await validator_func(user_id)
            if result:
                results[name] = result

        return results

    async def _validate_github(self, user_id: int) -> Optional[Dict[str, any]]:
        """
        Validate GitHub integration by making a lightweight API call.

        Makes a GET request to /user endpoint to verify token is valid.
        """
        try:
            integration = self.db.query(GitHubIntegration).filter(
                GitHubIntegration.user_id == user_id
            ).first()

            if not integration or not integration.github_token:
                return None

            try:
                token = decrypt_token(integration.github_token)
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt GitHub token for user {user_id}: {decrypt_error}")
                return self._error_response(
                    "GitHub token decryption failed. Please reconnect your GitHub integration."
                )

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/json"
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get("https://api.github.com/user", headers=headers)
            except httpx.TimeoutException:
                logger.warning(f"GitHub API timeout for user {user_id}")
                return self._error_response("GitHub API request timed out. Please try again.")
            except httpx.NetworkError as net_error:
                logger.error(f"GitHub API network error for user {user_id}: {net_error}")
                return self._error_response("Cannot reach GitHub API. Check your network connection.")

            return self._handle_api_response(response, user_id, "GitHub")

        except Exception as e:
            logger.error(f"GitHub validation unexpected error for user {user_id}: {e}", exc_info=True)
            return self._error_response(f"Unexpected error validating GitHub: {str(e)}")

    async def _validate_linear(self, user_id: int) -> Optional[Dict[str, any]]:
        """
        Validate Linear integration by making a lightweight GraphQL query.

        Makes a GraphQL query for viewer.id to verify token is valid.
        """
        try:
            integration = self.db.query(LinearIntegration).filter(
                LinearIntegration.user_id == user_id
            ).first()

            if not integration or not integration.access_token:
                return None

            try:
                token = decrypt_token(integration.access_token)
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt Linear token for user {user_id}: {decrypt_error}")
                return self._error_response(
                    "Linear token decryption failed. Please reconnect your Linear integration."
                )

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            query = "query Viewer { viewer { id } }"

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://api.linear.app/graphql",
                        json={"query": query},
                        headers=headers
                    )
            except httpx.TimeoutException:
                logger.warning(f"Linear API timeout for user {user_id}")
                return self._error_response("Linear API request timed out. Please try again.")
            except httpx.NetworkError as net_error:
                logger.error(f"Linear API network error for user {user_id}: {net_error}")
                return self._error_response("Cannot reach Linear API. Check your network connection.")

            return self._handle_linear_response(response, user_id)

        except Exception as e:
            logger.error(f"Linear validation unexpected error for user {user_id}: {e}", exc_info=True)
            return self._error_response(f"Unexpected error validating Linear: {str(e)}")

    async def _validate_jira(self, user_id: int) -> Optional[Dict[str, any]]:
        """
        Validate Jira integration by making a lightweight API call.

        Makes a GET request to /api/3/myself endpoint to verify token is valid.
        """
        try:
            integration = self.db.query(JiraIntegration).filter(
                JiraIntegration.user_id == user_id
            ).first()

            if not integration or not integration.access_token:
                return None

            try:
                token = decrypt_token(integration.access_token)
            except Exception as decrypt_error:
                logger.error(f"Failed to decrypt Jira token for user {user_id}: {decrypt_error}")
                return self._error_response(
                    "Jira token decryption failed. Please reconnect your Jira integration."
                )

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            url = f"https://api.atlassian.com/ex/jira/{integration.jira_cloud_id}/rest/api/3/myself"

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers)
            except httpx.TimeoutException:
                logger.warning(f"Jira API timeout for user {user_id}")
                return self._error_response("Jira API request timed out. Please try again.")
            except httpx.NetworkError as net_error:
                logger.error(f"Jira API network error for user {user_id}: {net_error}")
                return self._error_response("Cannot reach Jira API. Check your network connection.")

            return self._handle_api_response(response, user_id, "Jira")

        except Exception as e:
            logger.error(f"Jira validation unexpected error for user {user_id}: {e}", exc_info=True)
            return self._error_response(f"Unexpected error validating Jira: {str(e)}")

    def _error_response(self, error_msg: str) -> Dict[str, any]:
        """Create a standardized error response."""
        return {"valid": False, "error": error_msg}

    def _handle_api_response(self, response, user_id: int, provider: str) -> Dict[str, any]:
        """Handle REST API responses with standard status codes."""
        if response.status_code == 200:
            logger.info(f"{provider} validation successful for user {user_id}")
            return {"valid": True, "error": None}
        elif response.status_code == 401:
            logger.warning(f"{provider} token invalid/expired for user {user_id}")
            return self._error_response(
                f"{provider} token is expired or invalid. Please reconnect your {provider} integration."
            )
        elif response.status_code == 403:
            logger.warning(f"{provider} token forbidden for user {user_id}")
            return self._error_response(
                f"{provider} token lacks required permissions. Please reconnect with proper scopes."
            )
        else:
            logger.warning(f"{provider} API returned {response.status_code} for user {user_id}")
            return self._error_response(f"{provider} API error (status {response.status_code})")

    def _handle_linear_response(self, response, user_id: int) -> Dict[str, any]:
        """Handle Linear GraphQL responses."""
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown error")
                if "Unauthorized" in error_msg or "Invalid token" in error_msg:
                    logger.warning(f"Linear token invalid/expired for user {user_id}")
                    return self._error_response(
                        "Linear token is expired or invalid. Please reconnect your Linear integration."
                    )
                logger.warning(f"Linear GraphQL error for user {user_id}: {error_msg}")
                return self._error_response(f"Linear API error: {error_msg}")
            logger.info(f"Linear validation successful for user {user_id}")
            return {"valid": True, "error": None}
        elif response.status_code == 401:
            logger.warning(f"Linear token invalid/expired for user {user_id}")
            return self._error_response(
                "Linear token is expired or invalid. Please reconnect your Linear integration."
            )
        else:
            logger.warning(f"Linear API returned {response.status_code} for user {user_id}")
            return self._error_response(f"Linear API error (status {response.status_code})")
