"""
Integration validation service for pre-flight connection checks.

Validates API tokens for GitHub, Linear, and Jira integrations before
starting analysis to detect stale/expired tokens early.
"""
import logging
import os
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from cryptography.fernet import Fernet
import httpx

from ..core.config import settings
from ..core.validation_cache import (
    get_cached_validation,
    set_cached_validation,
    invalidate_validation_cache,
)
from ..core.error_messages import get_error_response
from ..models import GitHubIntegration, LinearIntegration, JiraIntegration
from .token_refresh_coordinator import refresh_token_with_lock

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """Get the encryption key from settings.

    Uses ENCRYPTION_KEY if set, otherwise falls back to old default
    for backward compatibility with tokens encrypted before PR #269.
    """
    from base64 import urlsafe_b64encode

    key = settings.ENCRYPTION_KEY.encode()
    # Ensure key is 32 bytes for Fernet (consistent with other integration files)
    key = urlsafe_b64encode(key[:32].ljust(32, b'\0'))

    # Debug logging to verify correct key is being used
    logger.debug(f"Using encryption key (first 40 chars): {key.decode()[:40]}")

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


EXPIRES_IN_MIN_SECONDS = 60
EXPIRES_IN_MAX_SECONDS = 86400 * 30
EXPIRES_IN_DEFAULT_SECONDS = 86400

LINEAR_LOCK_TIMEOUT_SECONDS_DEFAULT = 10
LINEAR_LOCK_TIMEOUT_SECONDS_MIN = 1
LINEAR_LOCK_TIMEOUT_SECONDS_MAX = 60


def _is_ascii_digits(s: str) -> bool:
    """Check if string contains only ASCII digits 0-9 (rejects Unicode digits)."""
    return bool(s) and all(c in '0123456789' for c in s)


def _parse_expires_in(raw_expires_in: Any) -> int:
    """Parse expires_in from OAuth response, returning bounded value or default.

    Bounds: EXPIRES_IN_MIN_SECONDS (60) to EXPIRES_IN_MAX_SECONDS (30 days).
    Floats are bounds-checked before conversion to prevent overflow.
    """
    if raw_expires_in is None or isinstance(raw_expires_in, bool):
        return EXPIRES_IN_DEFAULT_SECONDS

    try:
        if isinstance(raw_expires_in, str):
            candidate = raw_expires_in.strip()
            if not _is_ascii_digits(candidate):
                raise ValueError("Invalid expires_in format")
            value = int(candidate)
        elif isinstance(raw_expires_in, float):
            # Check if integer first to prevent issues with large floats like 1e20
            if not raw_expires_in.is_integer():
                raise ValueError("Non-integer expires_in value")
            # Check bounds BEFORE conversion to prevent overflow with large floats (e.g., 1e9)
            if raw_expires_in > EXPIRES_IN_MAX_SECONDS or raw_expires_in < EXPIRES_IN_MIN_SECONDS:
                logger.warning(
                    f"Float expires_in {raw_expires_in} outside valid range, using default. "
                    f"This may indicate an API change or malformed response."
                )
                return EXPIRES_IN_DEFAULT_SECONDS
            value = int(raw_expires_in)
        elif isinstance(raw_expires_in, int):
            value = raw_expires_in
        else:
            raise ValueError("Invalid expires_in type")
    except (ValueError, OverflowError):
        logger.warning(f"Invalid expires_in value '{raw_expires_in}', using default")
        return EXPIRES_IN_DEFAULT_SECONDS

    if EXPIRES_IN_MIN_SECONDS <= value <= EXPIRES_IN_MAX_SECONDS:
        # Warn if token lifetime is unusually short (< 5 minutes) - may indicate issue
        if value < 300:
            logger.warning(f"Unusually short token lifetime: {value}s (expected >= 300s)")
        return value

    logger.warning(f"expires_in {value} outside valid range [{EXPIRES_IN_MIN_SECONDS}, {EXPIRES_IN_MAX_SECONDS}], using default")
    return EXPIRES_IN_DEFAULT_SECONDS


def _get_linear_lock_timeout_seconds() -> int:
    raw_timeout = os.getenv("LINEAR_TOKEN_REFRESH_LOCK_TIMEOUT_SECONDS")
    if raw_timeout is None:
        return LINEAR_LOCK_TIMEOUT_SECONDS_DEFAULT

    try:
        timeout_seconds = int(raw_timeout)
    except (TypeError, ValueError):
        return LINEAR_LOCK_TIMEOUT_SECONDS_DEFAULT

    return max(LINEAR_LOCK_TIMEOUT_SECONDS_MIN, min(timeout_seconds, LINEAR_LOCK_TIMEOUT_SECONDS_MAX))


class IntegrationValidator:
    """Service for validating integration connections."""

    def __init__(self, db: Session):
        self.db = db

    async def validate_manual_token(
        self,
        provider: str,
        token: str,
        site_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate a manual API token before saving to database.

        Args:
            provider: 'jira' or 'linear'
            token: The API token to validate (plaintext, not encrypted)
            site_url: Jira site URL (required for Jira, ignored for Linear)

        Returns:
            Dict with 'valid' (bool), 'error' (str), 'error_type' (str),
            and optional 'user_info' (dict with display_name, email)
        """
        if provider == "jira":
            return await self._validate_jira_manual_token(token, site_url)
        elif provider == "linear":
            return await self._validate_linear_manual_token(token)
        else:
            return {"valid": False, "error": f"Unknown provider: {provider}", "error_type": "unknown"}

    async def _validate_jira_manual_token(
        self,
        token: str,
        site_url: Optional[str]
    ) -> Dict[str, Any]:
        """Validate Jira Personal Access Token."""
        # Format validation
        if not token or not token.strip():
            error = get_error_response("jira", "format")
            return {"valid": False, **error}

        if not site_url or not site_url.strip():
            error = get_error_response("jira", "site_url")
            return {"valid": False, **error}

        # Normalize site URL
        site_url = site_url.strip().rstrip("/")
        if not site_url.startswith("https://"):
            site_url = f"https://{site_url}"

        # Basic format check - Jira tokens are base64-ish alphanumeric
        token = token.strip()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use /myself endpoint to validate token and get user info
                response = await client.get(
                    f"{site_url}/rest/api/3/myself",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )

                logger.info(f"Jira API response: status={response.status_code}, body={response.text[:500]}")

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "valid": True,
                        "error": None,
                        "error_type": None,
                        "user_info": {
                            "display_name": data.get("displayName"),
                            "email": data.get("emailAddress"),
                            "account_id": data.get("accountId")
                        }
                    }
                elif response.status_code == 401:
                    logger.warning(f"Jira 401: {response.text[:300]}")
                    error = get_error_response("jira", "authentication")
                    return {"valid": False, **error}
                elif response.status_code == 403:
                    logger.warning(f"Jira 403: {response.text[:300]}")
                    error = get_error_response("jira", "permissions")
                    return {"valid": False, **error}
                else:
                    logger.warning(f"Jira validation returned status {response.status_code}: {response.text[:300]}")
                    error = get_error_response("jira", "authentication")
                    return {"valid": False, **error}

        except httpx.TimeoutException:
            error = get_error_response("jira", "network")
            error["message"] = "Jira API request timed out. The site may be slow or unreachable."
            return {"valid": False, **error}
        except httpx.NetworkError:
            error = get_error_response("jira", "network")
            return {"valid": False, **error}
        except Exception as e:
            logger.exception(f"Unexpected error validating Jira token: {e}")
            error = get_error_response("jira", "network")
            return {"valid": False, **error}

    async def _validate_linear_manual_token(self, token: str) -> Dict[str, Any]:
        """Validate Linear Personal API Key."""
        # Format validation
        if not token or not token.strip():
            error = get_error_response("linear", "format")
            return {"valid": False, **error}

        token = token.strip()

        # Linear API keys typically start with lin_api_
        if not token.startswith("lin_api_"):
            error = get_error_response("linear", "format")
            return {"valid": False, **error}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use GraphQL viewer query to validate token and get user info
                # IMPORTANT: Linear API Keys do NOT use Bearer prefix (only OAuth tokens do)
                # See: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
                response = await client.post(
                    "https://api.linear.app/graphql",
                    headers={
                        "Authorization": token,  # API keys: no Bearer prefix
                        "Content-Type": "application/json"
                    },
                    json={
                        "query": "query { viewer { id name email } }"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if "errors" in data:
                        # GraphQL returned errors
                        error_msg = data["errors"][0].get("message", "")
                        if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                            error = get_error_response("linear", "authentication")
                        else:
                            error = get_error_response("linear", "permissions")
                        return {"valid": False, **error}

                    viewer = data.get("data", {}).get("viewer", {})
                    return {
                        "valid": True,
                        "error": None,
                        "error_type": None,
                        "user_info": {
                            "display_name": viewer.get("name"),
                            "email": viewer.get("email"),
                            "linear_id": viewer.get("id")
                        }
                    }
                elif response.status_code == 401:
                    error = get_error_response("linear", "authentication")
                    return {"valid": False, **error}
                elif response.status_code == 403:
                    error = get_error_response("linear", "permissions")
                    return {"valid": False, **error}
                else:
                    logger.warning(f"Linear validation returned status {response.status_code}")
                    error = get_error_response("linear", "authentication")
                    return {"valid": False, **error}

        except httpx.TimeoutException:
            error = get_error_response("linear", "network")
            error["message"] = "Linear API request timed out."
            return {"valid": False, **error}
        except httpx.NetworkError:
            error = get_error_response("linear", "network")
            return {"valid": False, **error}
        except Exception as e:
            logger.exception(f"Unexpected error validating Linear token: {e}")
            error = get_error_response("linear", "network")
            return {"valid": False, **error}

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
        set_cached_validation(user_id, results)

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
        """Get a valid Linear access token, refreshing if necessary.

        Uses distributed lock via Redis to prevent race conditions when multiple
        concurrent requests try to refresh the token. Falls back to database
        row locking if Redis is unavailable.
        """
        if not integration.access_token:
            raise ValueError("No access token available for Linear integration")

        self.db.refresh(integration)

        # Determine if refresh is needed and possible
        token_needs_refresh = needs_refresh(integration.token_expires_at)
        has_refresh_token = bool(integration.refresh_token)

        # Return current token if still valid (most common path)
        if not token_needs_refresh:
            return decrypt_token(integration.access_token)

        # Token needs refresh - verify we can refresh before proceeding
        if not has_refresh_token:
            raise ValueError("Authentication error. Please reconnect Linear.")

        # Use coordinator with distributed locking
        logger.info(f"[Linear] Token refresh initiated for user {integration.user_id}")

        try:
            token = await refresh_token_with_lock(
                provider="linear",
                integration_id=integration.id,
                user_id=integration.user_id,
                refresh_func=lambda: self._perform_linear_token_refresh(integration),
                fallback_func=lambda: self._perform_linear_token_refresh_with_db_lock(integration)
            )
            return token

        except RuntimeError:
            # RuntimeError from database lock timeout already handled rollback in fallback
            raise
        except Exception as e:
            # Other exceptions from refresh need rollback
            logger.warning(
                f"[Linear] Token refresh failed: user_id={integration.user_id}, "
                f"error_type={type(e).__name__}, message={e}"
            )
            self._safe_rollback(e)
            raise

    async def _call_linear_token_refresh_api(self, refresh_token: str) -> dict:
        """Call Linear OAuth token refresh API. Returns token data dict or raises ValueError."""
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
            raise ValueError("Authentication error. Please reconnect Linear.")

        token_data = response.json()
        if not token_data.get("access_token"):
            raise ValueError("Authentication error. Please reconnect Linear.")

        return token_data

    def _update_linear_integration_tokens(
        self,
        integration: LinearIntegration,
        token_data: dict,
        original_refresh_token: str
    ) -> str:
        """Update integration with new tokens. Returns decrypted access token."""
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token") or original_refresh_token
        expires_in = _parse_expires_in(token_data.get("expires_in"))

        integration.access_token = encrypt_token(new_access_token)
        integration.refresh_token = encrypt_token(new_refresh_token)
        integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(seconds=expires_in)
        integration.updated_at = datetime.now(dt_timezone.utc)

        return new_access_token

    async def _perform_linear_token_refresh(self, integration: LinearIntegration) -> str:
        """
        Perform Linear token refresh (no locking - caller handles coordination).

        Returns:
            New access token (decrypted)
        """
        self.db.refresh(integration)

        # Double-check: another process may have refreshed while we waited for lock
        if not needs_refresh(integration.token_expires_at):
            logger.info(f"[Linear] Token already refreshed for user {integration.user_id}")
            return decrypt_token(integration.access_token)

        logger.info(f"[Linear] Refreshing access token for user {integration.user_id}")
        refresh_token = decrypt_token(integration.refresh_token)

        token_data = await self._call_linear_token_refresh_api(refresh_token)
        new_access_token = self._update_linear_integration_tokens(integration, token_data, refresh_token)
        self.db.commit()

        logger.info(f"[Linear] Token refreshed successfully for user {integration.user_id}")
        return new_access_token

    async def _perform_linear_token_refresh_with_db_lock(self, integration: LinearIntegration) -> str:
        """
        Perform Linear token refresh with database row locking (fallback when Redis unavailable).

        Returns:
            New access token (decrypted)
        """
        logger.info(f"[Linear] Using database lock for token refresh (user {integration.user_id})")
        lock_timeout_seconds = _get_linear_lock_timeout_seconds()

        try:
            with self.db.begin_nested():
                self.db.execute(
                    text("SET LOCAL lock_timeout = :lock_timeout"),
                    {"lock_timeout": f"{lock_timeout_seconds}s"}
                )

                locked_integration = self.db.query(LinearIntegration).filter(
                    LinearIntegration.id == integration.id
                ).with_for_update().first()

                if not locked_integration:
                    raise ValueError("Authentication error. Please reconnect Linear.")

                # Double-check: another request may have refreshed while we waited
                if not needs_refresh(locked_integration.token_expires_at):
                    logger.info(f"[Linear] Token already refreshed for user {integration.user_id}")
                    return decrypt_token(locked_integration.access_token)

                logger.info(f"[Linear] Refreshing access token for user {integration.user_id}")
                refresh_token = decrypt_token(locked_integration.refresh_token)

                token_data = await self._call_linear_token_refresh_api(refresh_token)
                new_access_token = self._update_linear_integration_tokens(
                    locked_integration, token_data, refresh_token
                )

            logger.info(f"[Linear] Token refreshed successfully for user {integration.user_id}")
            return new_access_token

        except OperationalError as db_error:
            error_type = "lock_timeout" if "lock" in str(db_error).lower() else "db_error"
            logger.warning(
                f"[Linear] Database contention during token refresh: "
                f"user_id={integration.user_id}, error_type={error_type}, "
                f"lock_timeout_setting={lock_timeout_seconds}s"
            )
            logger.debug(f"[Linear] Full database error: {db_error}", exc_info=True)
            self._safe_rollback(db_error)
            raise RuntimeError("Temporary error. Please retry.") from db_error

    def _safe_rollback(self, original_error: Optional[BaseException] = None):
        """Safely rollback a transaction, handling potential rollback failures."""
        try:
            self.db.rollback()
        except Exception as rollback_error:
            context = f" after {original_error}" if original_error else ""
            logger.error(f"Failed to rollback transaction{context}: {rollback_error}", exc_info=True)
            self.db.close()

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

            # API keys (lin_api_*) don't use Bearer prefix, OAuth tokens do
            if token.startswith("lin_api_"):
                auth_header = token
            else:
                auth_header = f"Bearer {token}"
            headers = {
                "Authorization": auth_header,
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

    async def _get_valid_jira_token(self, integration: JiraIntegration) -> str:
        """Get a valid Jira access token, refreshing if necessary.

        Uses distributed lock via Redis to prevent race conditions when multiple
        concurrent requests try to refresh the token. Falls back to database
        row locking if Redis is unavailable.
        """
        if not integration.access_token:
            raise ValueError("No access token available for Jira integration")

        self.db.refresh(integration)

        # Determine if refresh is needed and possible
        token_needs_refresh = needs_refresh(integration.token_expires_at)
        has_refresh_token = bool(integration.refresh_token)

        # Return current token if still valid (most common path)
        if not token_needs_refresh:
            return decrypt_token(integration.access_token)

        # Token needs refresh - verify we can refresh before proceeding
        if not has_refresh_token:
            raise ValueError("Authentication error. Please reconnect Jira.")

        # Use coordinator with distributed locking
        logger.info(f"[Jira] Token refresh initiated for user {integration.user_id}")

        try:
            token = await refresh_token_with_lock(
                provider="jira",
                integration_id=integration.id,
                user_id=integration.user_id,
                refresh_func=lambda: self._perform_jira_token_refresh(integration),
                fallback_func=lambda: self._perform_jira_token_refresh_with_db_lock(integration)
            )
            return token

        except RuntimeError:
            # RuntimeError from database lock timeout already handled rollback in fallback
            raise
        except Exception as e:
            # Other exceptions from refresh need rollback
            logger.warning(
                f"[Jira] Token refresh failed for user {integration.user_id}: {e}",
                exc_info=True
            )
            self._safe_rollback(e)
            raise ValueError("Authentication error. Please reconnect Jira.") from e

    async def _perform_jira_token_refresh(self, integration: JiraIntegration) -> str:
        """
        Perform Jira token refresh without database locking (for use with Redis lock).

        Returns:
            New access token (decrypted)
        """
        # Verify integration still needs refresh
        self.db.refresh(integration)
        if not needs_refresh(integration.token_expires_at):
            logger.info(f"[Jira] Token already refreshed for user {integration.user_id}")
            return decrypt_token(integration.access_token)

        logger.info(f"[Jira] Refreshing access token for user {integration.user_id}")
        refresh_token = decrypt_token(integration.refresh_token)

        token_data = await self._call_jira_token_refresh_api(refresh_token)
        new_access_token = self._update_jira_integration_tokens(integration, token_data, refresh_token)
        self.db.commit()

        logger.info(f"[Jira] Token refreshed successfully for user {integration.user_id}")
        return new_access_token

    async def _perform_jira_token_refresh_with_db_lock(self, integration: JiraIntegration) -> str:
        """
        Perform Jira token refresh with database row locking (fallback when Redis unavailable).

        Returns:
            New access token (decrypted)
        """
        logger.info(f"[Jira] Using database lock for token refresh (user {integration.user_id})")
        lock_timeout_seconds = _get_linear_lock_timeout_seconds()  # Reuse Linear config

        try:
            with self.db.begin_nested():
                self.db.execute(
                    text("SET LOCAL lock_timeout = :lock_timeout"),
                    {"lock_timeout": f"{lock_timeout_seconds}s"}
                )

                locked_integration = self.db.query(JiraIntegration).filter(
                    JiraIntegration.id == integration.id
                ).with_for_update().first()

                if not locked_integration:
                    raise ValueError("Authentication error. Please reconnect Jira.")

                # Double-check: another request may have refreshed while we waited
                if not needs_refresh(locked_integration.token_expires_at):
                    logger.info(f"[Jira] Token already refreshed for user {integration.user_id}")
                    return decrypt_token(locked_integration.access_token)

                logger.info(f"[Jira] Refreshing access token for user {integration.user_id}")
                refresh_token = decrypt_token(locked_integration.refresh_token)

                token_data = await self._call_jira_token_refresh_api(refresh_token)
                new_access_token = self._update_jira_integration_tokens(
                    locked_integration, token_data, refresh_token
                )

            logger.info(f"[Jira] Token refreshed successfully for user {integration.user_id}")
            return new_access_token

        except OperationalError as db_error:
            error_type = "lock_timeout" if "lock" in str(db_error).lower() else "db_error"
            logger.warning(
                f"[Jira] Database contention during token refresh: "
                f"user_id={integration.user_id}, error_type={error_type}, "
                f"lock_timeout_setting={lock_timeout_seconds}s"
            )
            logger.debug(f"[Jira] Full database error: {db_error}", exc_info=True)
            self._safe_rollback(db_error)
            raise RuntimeError("Temporary error. Please retry.") from db_error

    async def _call_jira_token_refresh_api(self, refresh_token: str) -> dict:
        """Call Jira OAuth token refresh API. Returns token data dict or raises ValueError."""
        if not settings.JIRA_CLIENT_ID or not settings.JIRA_CLIENT_SECRET:
            raise ValueError("Authentication error. Please reconnect Jira.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": settings.JIRA_CLIENT_ID,
                    "client_secret": settings.JIRA_CLIENT_SECRET,
                    "refresh_token": refresh_token
                },
                headers={"Content-Type": "application/json"}
            )

        if response.status_code != 200:
            logger.error(f"[Jira] Token refresh failed: {response.status_code} {response.text}")
            raise ValueError("Authentication error. Please reconnect Jira.")

        token_data = response.json()
        if not token_data.get("access_token"):
            raise ValueError("Authentication error. Please reconnect Jira.")

        return token_data

    def _update_jira_integration_tokens(
        self,
        integration: JiraIntegration,
        token_data: dict,
        original_refresh_token: str
    ) -> str:
        """Update Jira integration with new tokens. Returns decrypted access token."""
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token") or original_refresh_token
        expires_in = _parse_expires_in(token_data.get("expires_in"))

        integration.access_token = encrypt_token(new_access_token)
        integration.refresh_token = encrypt_token(new_refresh_token)
        integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(seconds=expires_in)
        integration.updated_at = datetime.now(dt_timezone.utc)

        return new_access_token

    async def _validate_jira(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Validate Jira integration by making a lightweight API call.

        Makes a GET request to /api/3/myself endpoint to verify token is valid.
        Automatically refreshes OAuth tokens if they are expired.
        """
        try:
            integration = self.db.query(JiraIntegration).filter(
                JiraIntegration.user_id == user_id
            ).first()

            if not integration or not integration.access_token:
                return None

            try:
                # Get valid token (refreshing if needed)
                token = await self._get_valid_jira_token(integration)
            except Exception as token_error:
                logger.error(f"Failed to get Jira token for user {user_id}: {token_error}")
                return self._error_response(
                    "Jira token refresh failed. Please reconnect your Jira integration."
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
