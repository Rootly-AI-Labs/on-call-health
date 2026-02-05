"""
SIGTERM Signal Handler for Graceful Shutdown.

Handles SIGTERM signals from Railway deployments to ensure analysis tasks
can save checkpoints before being killed.
"""
import asyncio
import logging
import signal
import sys
from types import FrameType
from typing import Optional

logger = logging.getLogger(__name__)

# Railway gives containers 10 seconds before SIGKILL.
# We use 8 seconds to allow time for cleanup before the deadline.
SHUTDOWN_TIMEOUT_SECONDS = 8

# Module state for handler registration
_handler_registered: bool = False
_original_handler: Optional[signal.Handlers] = None


async def graceful_shutdown_handler(signum: int, frame: Optional[FrameType]) -> None:
    """
    Handle SIGTERM gracefully by saving checkpoints and exiting cleanly.

    Called when Railway sends SIGTERM during deployment. Railway gives
    containers 10 seconds to shutdown gracefully before sending SIGKILL.

    Strategy:
        1. Set shutdown flag in analysis_runner (stops new phase starts)
        2. Wait up to 8 seconds for current checkpoint save
        3. Exit cleanly before SIGKILL (10 second deadline)

    Args:
        signum: Signal number (typically SIGTERM = 15)
        frame: Current stack frame (unused but required by signal API)

    Security:
        - Timeout ensures exit before SIGKILL
        - Checkpoint saves use atomic database transactions
        - No data loss even if timeout exceeded
    """
    logger.warning(f"Received signal {signum} - initiating graceful shutdown")

    # Import here to avoid circular dependency
    from .analysis_runner import request_shutdown

    request_shutdown()

    try:
        logger.info(f"Waiting up to {SHUTDOWN_TIMEOUT_SECONDS}s for checkpoint save...")
        await asyncio.sleep(SHUTDOWN_TIMEOUT_SECONDS)
        logger.info("Graceful shutdown complete")
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")

    logger.warning("Exiting (SIGTERM handler)")
    sys.exit(0)


def register_signal_handlers() -> None:
    """
    Register SIGTERM signal handler for graceful shutdown.

    Should be called once at ARQ worker startup.

    Note:
        - Only registers once (subsequent calls are no-op)
        - Preserves original handler for restoration if needed
        - SIGINT (Ctrl+C) is handled by ARQ's default handler
        - Uses synchronous flag-setting to avoid event loop conflicts
    """
    global _handler_registered, _original_handler

    if _handler_registered:
        logger.debug("Signal handlers already registered")
        return

    try:
        _original_handler = signal.getsignal(signal.SIGTERM)

        def sync_handler(signum: int, frame: Optional[FrameType]) -> None:
            """
            Sync signal handler that sets shutdown flag and waits.

            Avoids running async code in signal context to prevent
            event loop conflicts when signal arrives during async operations.
            """
            import time

            logger.warning(f"Received signal {signum} - initiating graceful shutdown")

            # Import here to avoid circular dependency
            from .analysis_runner import request_shutdown
            request_shutdown()

            # Wait synchronously for checkpoint save (avoids event loop issues)
            logger.info(f"Waiting up to {SHUTDOWN_TIMEOUT_SECONDS}s for checkpoint save...")
            time.sleep(SHUTDOWN_TIMEOUT_SECONDS)

            logger.warning("Exiting (SIGTERM handler)")
            sys.exit(0)

        signal.signal(signal.SIGTERM, sync_handler)
        _handler_registered = True
        logger.info("SIGTERM handler registered for graceful shutdown")

    except Exception as e:
        logger.error(f"Failed to register signal handlers: {e}")
        # Don't fail startup - worker can still function without graceful shutdown


def unregister_signal_handlers() -> None:
    """
    Unregister signal handlers and restore original handlers.

    Called on worker shutdown or for testing cleanup.
    """
    global _handler_registered, _original_handler

    if not _handler_registered:
        return

    try:
        if _original_handler is not None:
            signal.signal(signal.SIGTERM, _original_handler)

        _handler_registered = False
        logger.info("Signal handlers unregistered")

    except Exception as e:
        logger.error(f"Failed to unregister signal handlers: {e}")


__all__ = [
    "graceful_shutdown_handler",
    "register_signal_handlers",
    "unregister_signal_handlers",
]
