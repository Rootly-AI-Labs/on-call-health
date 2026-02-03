"""
Token manager service for unified token retrieval.

Provides get_valid_token() abstraction that handles:
- OAuth tokens: checks expiry, refreshes if needed, returns decrypted token
- Manual tokens: returns decrypted token directly (no refresh, no validation)

Callers don't need to know the token source - this service handles it.
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Union

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ..core.config import settings
from ..models import JiraIntegration, LinearIntegration
from .integration_validator import (
    decrypt_token,
    encrypt_token,
    needs_refresh,
    _parse_expires_in,
)
from .token_refresh_coordinator import refresh_token_with_lock

logger = logging.getLogger(__name__)


class TokenManager:
    """Abstraction layer for retrieving valid tokens from integrations.

    Provides get_valid_token() that handles:
    - OAuth tokens: checks expiry, refreshes if needed, returns decrypted token
    - Manual tokens: returns decrypted token directly (no refresh, no validation)

    Callers don't need to know the token source - this service handles it.

    Note: Manual token validation (checking if token still works) is Phase 2 scope.
    This class only handles token retrieval and OAuth refresh.
    """

    def __init__(self, db: Session):
        self.db = db

    async def get_valid_token(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Get a valid access token for the integration.

        For OAuth tokens: Checks expiry, refreshes if needed, returns decrypted token
        For manual tokens: Returns decrypted token directly (no refresh possible)

        Args:
            integration: JiraIntegration or LinearIntegration instance

        Returns:
            Valid decrypted access token

        Raises:
            ValueError: If no token available or refresh fails
        """
        if integration.is_oauth:
            return await self._get_oauth_token(integration)
        elif integration.is_manual:
            return self._get_manual_token(integration)
        else:
            raise ValueError(f"Unknown token source: {integration.token_source}")

    async def _get_oauth_token(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Get OAuth token, refreshing if expired.

        Args:
            integration: Integration with OAuth token

        Returns:
            Valid decrypted access token

        Raises:
            ValueError: If token missing or refresh fails
        """
        if not integration.has_token:
            provider = self._get_provider_name(integration)
            raise ValueError(f"No access token available for {provider} integration")

        # Refresh integration from DB to get latest state
        self.db.refresh(integration)

        # Check if refresh is needed
        token_needs_refresh = needs_refresh(integration.token_expires_at)
        has_refresh_token = integration.has_refresh_token

        # Return current token if still valid (most common path)
        if not token_needs_refresh:
            logger.debug(
                f"[{self._get_provider_name(integration)}] Token still valid for user {integration.user_id}"
            )
            return decrypt_token(integration.access_token)

        # Token needs refresh - verify we can refresh before proceeding
        if not integration.supports_refresh:
            provider = self._get_provider_name(integration)
            raise ValueError(f"Authentication error. Please reconnect {provider}.")

        # Use coordinator with distributed locking
        provider = "jira" if isinstance(integration, JiraIntegration) else "linear"
        logger.info(
            f"[{provider.title()}] Token refresh needed for user {integration.user_id}"
        )

        try:
            token = await refresh_token_with_lock(
                provider=provider,
                integration_id=integration.id,
                user_id=integration.user_id,
                refresh_func=lambda: self._perform_oauth_refresh(integration),
                fallback_func=lambda: self._perform_oauth_refresh_with_db_lock(
                    integration
                ),
            )
            return token

        except RuntimeError:
            # RuntimeError from database lock timeout already handled rollback
            raise
        except Exception as e:
            logger.warning(
                f"[{provider.title()}] Token refresh failed: user_id={integration.user_id}, "
                f"error={e}"
            )
            self._safe_rollback(e)
            provider_name = self._get_provider_name(integration)
            raise ValueError(
                f"Authentication error. Please reconnect {provider_name}."
            ) from e

    async def _perform_oauth_refresh(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Perform OAuth token refresh (no locking - caller handles coordination).

        Args:
            integration: Integration to refresh

        Returns:
            New access token (decrypted)

        Raises:
            ValueError: If refresh fails
        """
        # Refresh from DB to check latest state
        self.db.refresh(integration)

        # Double-check: another process may have refreshed while we waited for lock
        if not needs_refresh(integration.token_expires_at):
            provider = self._get_provider_name(integration)
            logger.info(
                f"[{provider}] Token already refreshed for user {integration.user_id}"
            )
            # Note: There's a small theoretical window between checking expiry and
            # returning the token where it could be invalidated. However, this is
            # extremely rare and any issues would be caught by error handling in
            # API calls that use the token, triggering a retry with fresh state.
            return decrypt_token(integration.access_token)

        provider = self._get_provider_name(integration)
        logger.info(f"[{provider}] Refreshing access token for user {integration.user_id}")

        # Decrypt refresh token
        refresh_token = decrypt_token(integration.refresh_token)

        # Call appropriate OAuth API based on integration type
        if isinstance(integration, JiraIntegration):
            token_data = await self._call_jira_token_refresh_api(refresh_token)
        else:
            token_data = await self._call_linear_token_refresh_api(refresh_token)

        # Update integration with new tokens
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token") or refresh_token
        expires_in = _parse_expires_in(token_data.get("expires_in"))

        integration.access_token = encrypt_token(new_access_token)
        integration.refresh_token = encrypt_token(new_refresh_token)
        integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(
            seconds=expires_in
        )
        integration.updated_at = datetime.now(dt_timezone.utc)

        # Commit to DB
        self.db.commit()

        logger.info(
            f"[{provider}] Token refreshed successfully for user {integration.user_id}"
        )
        return new_access_token

    async def _perform_oauth_refresh_with_db_lock(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Perform OAuth token refresh with database row locking.

        Fallback when Redis unavailable.

        Args:
            integration: Integration to refresh

        Returns:
            New access token (decrypted)

        Raises:
            RuntimeError: If database lock times out
            ValueError: If refresh fails
        """
        provider = self._get_provider_name(integration)
        logger.info(
            f"[{provider}] Using database lock for token refresh (user {integration.user_id})"
        )
        lock_timeout_seconds = 10  # Default lock timeout

        try:
            with self.db.begin_nested():
                self.db.execute(
                    text("SET LOCAL lock_timeout = :lock_timeout"),
                    {"lock_timeout": f"{lock_timeout_seconds}s"},
                )

                # Acquire row lock
                model_class = (
                    JiraIntegration
                    if isinstance(integration, JiraIntegration)
                    else LinearIntegration
                )
                locked_integration = (
                    self.db.query(model_class)
                    .filter(model_class.id == integration.id)
                    .with_for_update()
                    .first()
                )

                if not locked_integration:
                    raise ValueError(
                        f"Authentication error. Please reconnect {provider}."
                    )

                # Double-check: another request may have refreshed while we waited
                if not needs_refresh(locked_integration.token_expires_at):
                    logger.info(
                        f"[{provider}] Token already refreshed for user {integration.user_id}"
                    )
                    return decrypt_token(locked_integration.access_token)

                logger.info(
                    f"[{provider}] Refreshing access token for user {integration.user_id}"
                )

                # Decrypt refresh token
                refresh_token = decrypt_token(locked_integration.refresh_token)

                # Call appropriate OAuth API
                if isinstance(locked_integration, JiraIntegration):
                    token_data = await self._call_jira_token_refresh_api(refresh_token)
                else:
                    token_data = await self._call_linear_token_refresh_api(
                        refresh_token
                    )

                # Update integration with new tokens
                new_access_token = token_data["access_token"]
                new_refresh_token = token_data.get("refresh_token") or refresh_token
                expires_in = _parse_expires_in(token_data.get("expires_in"))

                locked_integration.access_token = encrypt_token(new_access_token)
                locked_integration.refresh_token = encrypt_token(new_refresh_token)
                locked_integration.token_expires_at = datetime.now(
                    dt_timezone.utc
                ) + timedelta(seconds=expires_in)
                locked_integration.updated_at = datetime.now(dt_timezone.utc)

            logger.info(
                f"[{provider}] Token refreshed successfully for user {integration.user_id}"
            )
            return new_access_token

        except OperationalError as db_error:
            error_type = "lock_timeout" if "lock" in str(db_error).lower() else "db_error"
            logger.warning(
                f"[{provider}] Database contention during token refresh: "
                f"user_id={integration.user_id}, error_type={error_type}"
            )
            logger.debug(f"[{provider}] Full database error: {db_error}", exc_info=True)
            self._safe_rollback(db_error)
            raise RuntimeError("Temporary error. Please retry.") from db_error

    async def _call_jira_token_refresh_api(self, refresh_token: str) -> dict:
        """Call Jira OAuth token refresh API.

        Args:
            refresh_token: Refresh token to use

        Returns:
            Token data dict with access_token, refresh_token, expires_in

        Raises:
            ValueError: If refresh fails
        """
        if not settings.JIRA_CLIENT_ID or not settings.JIRA_CLIENT_SECRET:
            raise ValueError("Authentication error. Please reconnect Jira.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": settings.JIRA_CLIENT_ID,
                    "client_secret": settings.JIRA_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/json"},
            )

        if response.status_code != 200:
            logger.error(
                f"[Jira] Token refresh failed: {response.status_code} {response.text}"
            )
            raise ValueError("Authentication error. Please reconnect Jira.")

        token_data = response.json()
        if not token_data.get("access_token"):
            raise ValueError("Authentication error. Please reconnect Jira.")

        return token_data

    async def _call_linear_token_refresh_api(self, refresh_token: str) -> dict:
        """Call Linear OAuth token refresh API.

        Args:
            refresh_token: Refresh token to use

        Returns:
            Token data dict with access_token, refresh_token, expires_in

        Raises:
            ValueError: If refresh fails
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.linear.app/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.LINEAR_CLIENT_ID,
                    "client_secret": settings.LINEAR_CLIENT_SECRET,
                },
            )

        if response.status_code != 200:
            raise ValueError("Authentication error. Please reconnect Linear.")

        token_data = response.json()
        if not token_data.get("access_token"):
            raise ValueError("Authentication error. Please reconnect Linear.")

        return token_data

    def _get_manual_token(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Get manual token (no refresh, no validation).

        Manual token validation is Phase 2 scope. This method only retrieves
        and decrypts the token.

        Args:
            integration: Integration with manual token

        Returns:
            Decrypted access token

        Raises:
            ValueError: If no token available
        """
        if not integration.has_token:
            provider = self._get_provider_name(integration)
            raise ValueError(f"No access token available for {provider} integration")

        logger.debug(
            f"[{self._get_provider_name(integration)}] Retrieving manual token for user {integration.user_id}"
        )
        return decrypt_token(integration.access_token)

    def _get_provider_name(
        self, integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Get provider name for logging and error messages."""
        return "Jira" if isinstance(integration, JiraIntegration) else "Linear"

    def _safe_rollback(self, original_error: BaseException = None):
        """Safely rollback a transaction, handling potential rollback failures."""
        try:
            self.db.rollback()
        except Exception as rollback_error:
            context = f" after {original_error}" if original_error else ""
            logger.error(
                f"Failed to rollback transaction{context}: {rollback_error}",
                exc_info=True,
            )
            self.db.close()
