"""
Unit tests for SIGTERM signal handler.

Tests cover:
- Signal handler registration and unregistration
- Graceful shutdown behavior and timeout handling
- Event loop creation when none exists
- Error handling and edge cases
"""
import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.workers.signal_handler import (
    SHUTDOWN_TIMEOUT_SECONDS,
    graceful_shutdown_handler,
    register_signal_handlers,
    unregister_signal_handlers,
)
import app.workers.signal_handler as handler_module


class TestGracefulShutdownHandler:
    """Test graceful_shutdown_handler behavior."""

    @pytest.mark.asyncio
    async def test_requests_shutdown_on_signal(self):
        """Handler calls request_shutdown and exits cleanly."""
        with patch('app.workers.analysis_runner.request_shutdown') as mock_request:
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch('sys.exit') as mock_exit:
                    await graceful_shutdown_handler(signal.SIGTERM, None)

                    mock_request.assert_called_once()
                    mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_waits_configured_timeout_for_checkpoint(self):
        """Handler waits SHUTDOWN_TIMEOUT_SECONDS for checkpoint save."""
        with patch('app.workers.analysis_runner.request_shutdown'):
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                with patch('sys.exit'):
                    await graceful_shutdown_handler(signal.SIGTERM, None)

                    mock_sleep.assert_called_once_with(SHUTDOWN_TIMEOUT_SECONDS)

    @pytest.mark.asyncio
    async def test_exits_cleanly_despite_errors(self):
        """Handler exits with code 0 even when errors occur during shutdown."""
        with patch('app.workers.analysis_runner.request_shutdown'):
            with patch('asyncio.sleep', side_effect=Exception("Simulated error")):
                with patch('sys.exit') as mock_exit:
                    await graceful_shutdown_handler(signal.SIGTERM, None)

                    mock_exit.assert_called_once_with(0)


def reset_handler_state():
    """Reset handler module state and restore default SIGTERM handler."""
    handler_module._handler_registered = False
    handler_module._original_handler = None
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


class TestSignalRegistration:
    """Test signal handler registration and unregistration."""

    def teardown_method(self):
        """Cleanup after each test."""
        reset_handler_state()

    def test_register_changes_sigterm_handler(self):
        """Registration installs a new SIGTERM handler."""
        original = signal.getsignal(signal.SIGTERM)

        register_signal_handlers()

        new_handler = signal.getsignal(signal.SIGTERM)
        assert new_handler != original
        assert new_handler is not None

    def test_register_is_idempotent(self):
        """Multiple registration calls use the same handler."""
        register_signal_handlers()
        handler_first = signal.getsignal(signal.SIGTERM)

        register_signal_handlers()
        handler_second = signal.getsignal(signal.SIGTERM)

        assert handler_first == handler_second

    def test_unregister_restores_original_handler(self):
        """Unregistration restores the original SIGTERM handler."""
        original = signal.getsignal(signal.SIGTERM)

        register_signal_handlers()
        unregister_signal_handlers()

        restored = signal.getsignal(signal.SIGTERM)
        assert restored == original

    def test_unregister_without_register_is_safe(self):
        """Unregistration is safe when no handler was registered."""
        unregister_signal_handlers()

    def test_register_handles_errors_gracefully(self):
        """Registration errors do not crash the worker."""
        with patch('signal.signal', side_effect=Exception("Signal error")):
            register_signal_handlers()

            assert handler_module._handler_registered is False


class TestSignalHandlerIntegration:
    """Integration tests for signal handling."""

    def teardown_method(self):
        """Cleanup after each test."""
        reset_handler_state()

    def test_registered_handler_is_callable(self):
        """Registered handler is callable."""
        register_signal_handlers()

        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)

    def test_sync_wrapper_invokes_async_handler(self):
        """Sync wrapper correctly invokes the async handler."""
        register_signal_handlers()
        handler = signal.getsignal(signal.SIGTERM)

        with patch('app.workers.signal_handler.graceful_shutdown_handler', new_callable=AsyncMock) as mock_async:
            with patch('sys.exit'):
                try:
                    handler(signal.SIGTERM, None)
                except SystemExit:
                    pass

                mock_async.assert_called_once()

    def test_handler_creates_event_loop_when_none_exists(self):
        """Handler creates a new event loop if none exists."""
        register_signal_handlers()
        handler = signal.getsignal(signal.SIGTERM)

        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.new_event_loop') as mock_new_loop:
                with patch('asyncio.set_event_loop') as mock_set_loop:
                    mock_loop = Mock()
                    mock_loop.run_until_complete = Mock()
                    mock_new_loop.return_value = mock_loop

                    with patch('sys.exit'):
                        try:
                            handler(signal.SIGTERM, None)
                        except SystemExit:
                            pass

                    mock_new_loop.assert_called_once()
                    mock_set_loop.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def teardown_method(self):
        """Cleanup after each test."""
        reset_handler_state()

    @pytest.mark.asyncio
    async def test_handler_accepts_none_frame(self):
        """Handler works with None frame (valid signal API scenario)."""
        with patch('app.workers.analysis_runner.request_shutdown'):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch('sys.exit'):
                    await graceful_shutdown_handler(signal.SIGTERM, None)

    @pytest.mark.asyncio
    async def test_handler_accepts_different_signal_numbers(self):
        """Handler works with various signal numbers."""
        with patch('app.workers.analysis_runner.request_shutdown'):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch('sys.exit'):
                    await graceful_shutdown_handler(signal.SIGTERM, None)
                    await graceful_shutdown_handler(signal.SIGINT, None)

    def test_register_preserves_custom_handler(self):
        """Registration preserves the existing custom handler for restoration."""
        custom_handler = lambda s, f: None
        signal.signal(signal.SIGTERM, custom_handler)

        register_signal_handlers()

        assert handler_module._original_handler == custom_handler

    def test_multiple_unregister_calls_are_safe(self):
        """Multiple unregister calls do not raise exceptions."""
        register_signal_handlers()

        unregister_signal_handlers()
        unregister_signal_handlers()
        unregister_signal_handlers()

    def test_fatal_handler_error_exits_with_error_code(self):
        """Fatal errors in handler cause exit with code 1."""
        register_signal_handlers()
        handler = signal.getsignal(signal.SIGTERM)

        with patch('app.workers.signal_handler.graceful_shutdown_handler', side_effect=Exception("Fatal")):
            with patch('sys.exit') as mock_exit:
                try:
                    handler(signal.SIGTERM, None)
                except SystemExit:
                    pass

                mock_exit.assert_called_once_with(1)
