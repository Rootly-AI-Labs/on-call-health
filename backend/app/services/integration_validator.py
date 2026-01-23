"""
Integration validation service for pre-flight connection checks.

Validates API tokens for GitHub, Linear, and Jira integrations before
starting analysis to detect stale/expired tokens early.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, Optional
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
    # Ensure key is 32 bytes for Fernet (consistent with other integration files)
    key = urlsafe_b64encode(key[:32].ljust(32, b'\0'))
    return key


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()


def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()


def needs_refresh(expires_at: Optional[datetime], skew_minutes: int = 60) -> bool:
    """Check if token needs refresh. Use 60 min buffer for 24hr tokens."""
    if not expires_at:
        return False
    now = datetime.now(dt_timezone.utc)
    return expires_at <= now + timedelta(minutes=skew_minutes)


# Module-level cache for validation results
# Format: {user_id: {"results": {...}, "timestamp": datetime}}
# Note: In production with multiple replicas, consider migrating to Redis
# (already used for rate limiting in backend/app/core/rate_limiting.py)
_validation_cache: Dict[int, Dict] = {}
_cache_lock = threading.RLock()

# Cache validation results for 5 minutes to avoid redundant API calls
VALIDATION_CACHE_TTL_SECONDS = 300

# Maximum number of users to cache (prevents unbounded memory growth)
MAX_CACHE_SIZE = 1000


def get_cached_validation(user_id: int) -> Optional[Dict[str, Dict[str, Any]]]:
    """Get cached validation results if still fresh. Thread-safe."""
    with _cache_lock:
        if user_id not in _validation_cache:
            return None

        cached = _validation_cache[user_id]
        cache_age = (datetime.now(dt_timezone.utc) - cached["timestamp"]).total_seconds()

        if cache_age < VALIDATION_CACHE_TTL_SECONDS:
            logger.info(f"Using cached validation results for user {user_id} (age: {cache_age:.1f}s)")
            return cached["results"]

        # Cache expired, remove it
        del _validation_cache[user_id]
        return None


def set_validation_cache(user_id: int, results: Dict[str, Dict[str, Any]]):
    """Cache validation results. Thread-safe with size limit."""
    with _cache_lock:
        # Evict oldest entries if cache is full
        if len(_validation_cache) >= MAX_CACHE_SIZE and user_id not in _validation_cache:
            _evict_oldest_entries()

        _validation_cache[user_id] = {
            "results": results,
            "timestamp": datetime.now(dt_timezone.utc)
        }


def _evict_oldest_entries():
    """Remove oldest 10% of cache entries. Must be called with lock held."""
    if not _validation_cache:
        return

    entries_to_remove = max(1, len(_validation_cache) // 10)
    sorted_entries = sorted(
        _validation_cache.items(),
        key=lambda x: x[1]["timestamp"]
    )

    for user_id, _ in sorted_entries[:entries_to_remove]:
        del _validation_cache[user_id]

    logger.info(f"Evicted {entries_to_remove} oldest cache entries")


def invalidate_validation_cache(user_id: int):
    """Invalidate cache for a user (e.g., when integration is added/removed). Thread-safe."""
    with _cache_lock:
        if user_id in _validation_cache:
            del _validation_cache[user_id]
            logger.info(f"Invalidated validation cache for user {user_id}")


class IntegrationValidator:
    """Service for validating integration connections."""

    def __init__(self, db: Session):
        self.db = db

    async def validate_all_integrations(
        self,
        user_id: int,
        use_cache: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate all enabled integrations for a user.

        Args:
            user_id: The user ID to validate integrations for
            use_cache: If True, return cached results if available and fresh

        Returns dict with status for each integration:
        {
            "github": {"valid": True/False, "error": "..."},
            "linear": {"valid": True/False, "error": "..."},
            "jira": {"valid": True/False, "error": "..."}
        }
        """
        # Check cache first if enabled
        if use_cache:
            cached_results = get_cached_validation(user_id)
            if cached_results is not None:
                return cached_results

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

        # Cache the results
        set_validation_cache(user_id, results)

        return results

    async def _validate_github(self, user_id: int) -> Optional[Dict[str, Any]]:
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
            return self._error_response("Unexpected error validating GitHub. Please try again later.")

    async def _get_valid_linear_token(self, integration: LinearIntegration) -> str:
        """Get a valid Linear access token, refreshing if necessary."""
        if not integration.access_token:
            raise ValueError("No access token available for Linear integration")

        if not needs_refresh(integration.token_expires_at) or not integration.refresh_token:
            return decrypt_token(integration.access_token)

        logger.info(f"[Linear] Refreshing access token for user {integration.user_id}")
        try:
            refresh_token = decrypt_token(integration.refresh_token)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.linear.app/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": settings.LINEAR_CLIENT_ID,
                        "client_secret": settings.LINEAR_CLIENT_SECRET,
                    }
                )

            if response.status_code != 200:
                logger.warning(f"[Linear] Token refresh failed with status {response.status_code}")
                return decrypt_token(integration.access_token)

            token_data = response.json()
            new_access_token = token_data.get("access_token")
            if not new_access_token:
                logger.warning("[Linear] Token refresh response missing access_token")
                return decrypt_token(integration.access_token)

            # Update the integration with new tokens
            new_refresh_token = token_data.get("refresh_token") or refresh_token
            expires_in = token_data.get("expires_in", 86400)

            integration.access_token = encrypt_token(new_access_token)
            integration.refresh_token = encrypt_token(new_refresh_token)
            integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(seconds=expires_in)
            integration.updated_at = datetime.now(dt_timezone.utc)
            self.db.commit()

            logger.info(f"[Linear] Token refreshed successfully for user {integration.user_id}")
            return new_access_token

        except Exception as e:
            logger.warning(f"[Linear] Token refresh failed: {e}")
            return decrypt_token(integration.access_token)

    async def _validate_linear(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Validate Linear integration by making a lightweight GraphQL query.

        Makes a GraphQL query for viewer.id to verify token is valid.
        Automatically refreshes OAuth tokens if they are expired.
        """
        try:
            integration = self.db.query(LinearIntegration).filter(
                LinearIntegration.user_id == user_id
            ).first()

            if not integration or not integration.access_token:
                return None

            try:
                # Get valid token (refreshing if needed)
                token = await self._get_valid_linear_token(integration)
            except Exception as decrypt_error:
                logger.error(f"Failed to get Linear token for user {user_id}: {decrypt_error}")
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
            return self._error_response("Unexpected error validating Linear. Please try again later.")

    async def _validate_jira(self, user_id: int) -> Optional[Dict[str, Any]]:
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
            return self._error_response("Unexpected error validating Jira. Please try again later.")

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {"valid": False, "error": error_msg}

    def _handle_api_response(self, response, user_id: int, provider: str) -> Dict[str, Any]:
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

    def _handle_linear_response(self, response, user_id: int) -> Dict[str, Any]:
        """Handle Linear GraphQL responses."""
        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                # Collect all error messages for logging
                error_messages = [err.get("message", "Unknown error") for err in result["errors"]]
                combined_errors = "; ".join(error_messages)

                # Check if any error indicates auth failure
                if any("Unauthorized" in msg or "Invalid token" in msg for msg in error_messages):
                    logger.warning(f"Linear token invalid/expired for user {user_id}")
                    return self._error_response(
                        "Linear token is expired or invalid. Please reconnect your Linear integration."
                    )
                logger.warning(f"Linear GraphQL errors for user {user_id}: {combined_errors}")
                return self._error_response("Linear API error. Please try again later.")
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
