"""
Logging context module for user email and analysis ID injection using contextvars.

This module provides thread-safe context storage for user and analysis information
that can be automatically included in all log messages.
"""
import logging
from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user email
# Default is None, which will be displayed as "anonymous" in logs
user_context: ContextVar[Optional[str]] = ContextVar('user_email', default=None)

# Context variable to store the current analysis reference (id + uuid)
# Default is None, which means no analysis context
analysis_context: ContextVar[Optional[str]] = ContextVar('analysis_ref', default=None)


def set_user_context(user_email: Optional[str]) -> None:
    """
    Set the current user email in the context.

    Args:
        user_email: The user email to set, or None for anonymous users.
    """
    user_context.set(user_email)


def get_user_context() -> Optional[str]:
    """
    Get the current user email from the context.

    Returns:
        The current user email, or None if not set.
    """
    return user_context.get()


def clear_user_context() -> None:
    """
    Clear the current user context by setting it to None.
    """
    user_context.set(None)


def set_analysis_context(analysis_uuid: str) -> None:
    """
    Set the current analysis context for logging.

    Args:
        analysis_uuid: The analysis UUID (shown in browser URL).
    """
    analysis_context.set(analysis_uuid)


def get_analysis_context() -> Optional[str]:
    """
    Get the current analysis reference from the context.

    Returns:
        The analysis reference string (e.g., "123 (uuid)"), or None if not set.
    """
    return analysis_context.get()


def clear_analysis_context() -> None:
    """
    Clear the current analysis context.
    """
    analysis_context.set(None)


class UserContextFilter(logging.Filter):
    """
    Logging filter that adds user email and analysis ID to all log records.

    This filter reads the user email and analysis context from context variables
    and adds them to the log record, allowing them to be included in log output.

    Log format should include %(user_id)s and optionally %(analysis_ref)s.
    Example: '%(asctime)s - %(name)s - %(levelname)s - [user_id=%(user_id)s] - %(message)s'
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add user_id and analysis_ref attributes to the log record.

        Args:
            record: The log record to modify.

        Returns:
            True to include the record in log output.
        """
        user_email = get_user_context()
        record.user_id = user_email if user_email is not None else "anonymous"

        analysis_ref = get_analysis_context()
        # Format analysis_ref with brackets only if set, otherwise empty string
        record.analysis_ref = f"[analysis={analysis_ref}]" if analysis_ref else ""
        return True


# Export public API
__all__ = [
    'user_context',
    'set_user_context',
    'get_user_context',
    'clear_user_context',
    'analysis_context',
    'set_analysis_context',
    'get_analysis_context',
    'clear_analysis_context',
    'UserContextFilter',
]
