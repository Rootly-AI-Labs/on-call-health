"""
Logging context module for user email injection using contextvars.

This module provides thread-safe context storage for user information
that can be automatically included in all log messages.
"""
import logging
from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user email
# Default is None, which will be displayed as "anonymous" in logs
user_context: ContextVar[Optional[str]] = ContextVar('user_email', default=None)


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


class UserContextFilter(logging.Filter):
    """
    Logging filter that adds user email to all log records.

    This filter reads the user email from the context variable and adds it
    to the log record, allowing it to be included in log output formats.

    Log format should include %(user_id)s to display the user email.
    Example: '%(asctime)s - %(name)s - %(levelname)s - [user_id=%(user_id)s] - %(message)s'
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add user_id attribute (email) to the log record.

        Args:
            record: The log record to modify.

        Returns:
            True to include the record in log output.
        """
        user_email = get_user_context()
        record.user_id = user_email if user_email is not None else "anonymous"
        return True


# Export public API
__all__ = [
    'user_context',
    'set_user_context',
    'get_user_context',
    'clear_user_context',
    'UserContextFilter',
]
