"""
Logging context module for user ID injection using contextvars.

This module provides thread-safe context storage for user information
that can be automatically included in all log messages.
"""
import logging
from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user ID
# Default is None, which will be displayed as "anonymous" in logs
user_context: ContextVar[Optional[int]] = ContextVar('user_id', default=None)


def set_user_context(user_id: Optional[int]) -> None:
    """
    Set the current user ID in the context.

    Args:
        user_id: The user ID to set, or None for anonymous users.
    """
    user_context.set(user_id)


def get_user_context() -> Optional[int]:
    """
    Get the current user ID from the context.

    Returns:
        The current user ID, or None if not set.
    """
    return user_context.get()


def clear_user_context() -> None:
    """
    Clear the current user context by setting it to None.
    """
    user_context.set(None)


class UserContextFilter(logging.Filter):
    """
    Logging filter that adds user_id to all log records.

    This filter reads the user ID from the context variable and adds it
    to the log record, allowing it to be included in log output formats.

    Log format should include %(user_id)s to display the user ID.
    Example: '%(asctime)s - %(name)s - %(levelname)s - [user_id=%(user_id)s] - %(message)s'
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add user_id attribute to the log record.

        Args:
            record: The log record to modify.

        Returns:
            True to include the record in log output.
        """
        user_id = get_user_context()
        record.user_id = user_id if user_id is not None else "anonymous"
        return True


# Export public API
__all__ = [
    'user_context',
    'set_user_context',
    'get_user_context',
    'clear_user_context',
    'UserContextFilter',
]
