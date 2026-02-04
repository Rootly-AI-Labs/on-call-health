"""Tests for circuit breaker in the MCP client."""
import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from aiobreaker import CircuitBreakerError, CircuitBreakerState

from app.mcp.client.circuit_breaker import (
    CircuitBreakerLogger,
    CircuitBreakerOpenError,
    create_circuit_breaker,
)


class TestCreateCircuitBreaker:
    """Test create_circuit_breaker function."""

    def test_create_with_defaults(self):
        """Should create circuit breaker with default settings."""
        breaker = create_circuit_breaker()
        assert breaker.name == "oncallhealth-api"
        assert breaker.fail_max == 5
        assert breaker.timeout_duration == timedelta(seconds=30)

    def test_create_with_custom_settings(self):
        """Should create circuit breaker with custom settings."""
        breaker = create_circuit_breaker(
            name="custom-breaker",
            fail_max=3,
            timeout_seconds=60,
        )
        assert breaker.name == "custom-breaker"
        assert breaker.fail_max == 3
        assert breaker.timeout_duration == timedelta(seconds=60)

    def test_breaker_has_logger_listener(self):
        """Circuit breaker should have CircuitBreakerLogger listener."""
        breaker = create_circuit_breaker()
        assert len(breaker.listeners) == 1
        assert isinstance(breaker.listeners[0], CircuitBreakerLogger)


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError exception."""

    def test_error_stores_name_and_time(self):
        """Error should store breaker name and time remaining."""
        time_remaining = timedelta(seconds=25)
        error = CircuitBreakerOpenError("my-breaker", time_remaining)
        assert error.name == "my-breaker"
        assert error.time_remaining == time_remaining

    def test_error_message(self):
        """Error should have descriptive message."""
        time_remaining = timedelta(seconds=25)
        error = CircuitBreakerOpenError("my-breaker", time_remaining)
        assert "my-breaker" in str(error)
        assert "open" in str(error).lower()
        assert "25" in str(error)

    def test_error_message_with_minutes(self):
        """Error should format time correctly for longer durations."""
        time_remaining = timedelta(minutes=2)
        error = CircuitBreakerOpenError("my-breaker", time_remaining)
        assert "120" in str(error)  # 120 seconds


class TestCircuitBreakerLogger:
    """Test CircuitBreakerLogger listener."""

    def test_state_change_logs(self):
        """state_change should log state transitions."""
        logger = CircuitBreakerLogger()
        breaker = MagicMock()
        breaker.name = "test-breaker"
        old_state = MagicMock()
        old_state.state = "closed"
        new_state = MagicMock()
        new_state.state = "open"

        # Should not raise
        logger.state_change(breaker, old_state, new_state)

    def test_failure_logs(self):
        """failure should log failures."""
        logger = CircuitBreakerLogger()
        breaker = MagicMock()
        breaker.name = "test-breaker"
        exception = Exception("test error")

        # Should not raise
        logger.failure(breaker, exception)

    def test_success_logs(self):
        """success should log successes."""
        logger = CircuitBreakerLogger()
        breaker = MagicMock()
        breaker.name = "test-breaker"

        # Should not raise
        logger.success(breaker)


class TestCircuitBreakerBehavior:
    """Test actual circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_breaker_stays_closed_on_success(self):
        """Circuit breaker should stay closed on successful calls."""
        breaker = create_circuit_breaker(fail_max=2, timeout_seconds=1)

        async def success_func():
            return "ok"

        for _ in range(5):
            result = await breaker.call_async(success_func)
            assert result == "ok"

        # Breaker should still be closed
        assert breaker.current_state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_breaker_opens_after_consecutive_failures(self):
        """Circuit breaker should open after fail_max consecutive failures."""
        breaker = create_circuit_breaker(fail_max=2, timeout_seconds=10)

        async def failing_func():
            raise Exception("Service error")

        # First failure - breaker stays closed
        with pytest.raises(Exception, match="Service error"):
            await breaker.call_async(failing_func)

        assert breaker.current_state == CircuitBreakerState.CLOSED

        # Second failure - breaker opens (raises CircuitBreakerError wrapping original)
        with pytest.raises(CircuitBreakerError):
            await breaker.call_async(failing_func)

        # Breaker should now be open
        assert breaker.current_state == CircuitBreakerState.OPEN

        # Next call should also raise CircuitBreakerError (without calling function)
        with pytest.raises(CircuitBreakerError):
            await breaker.call_async(failing_func)

    @pytest.mark.asyncio
    async def test_breaker_resets_failure_count_on_success(self):
        """Circuit breaker should reset failure count on success."""
        breaker = create_circuit_breaker(fail_max=3, timeout_seconds=10)

        async def conditional_func(should_fail):
            if should_fail:
                raise Exception("Error")
            return "ok"

        # Two failures
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call_async(conditional_func, True)

        # Success should reset the count
        result = await breaker.call_async(conditional_func, False)
        assert result == "ok"

        # Two more failures - should not open breaker
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call_async(conditional_func, True)

        # Breaker should still be closed
        assert breaker.current_state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_breaker_half_open_allows_one_request(self):
        """Circuit breaker should allow one request in half-open state."""
        breaker = create_circuit_breaker(fail_max=1, timeout_seconds=0.1)

        call_count = 0

        async def counting_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failure")
            return "ok"

        # Trip the breaker (fail_max=1 means first failure opens it)
        # When fail_max is reached, CircuitBreakerError is raised wrapping the original
        with pytest.raises(CircuitBreakerError):
            await breaker.call_async(counting_func)

        assert breaker.current_state == CircuitBreakerState.OPEN

        # Wait for timeout to transition to half-open
        await asyncio.sleep(0.15)

        # Next call should be allowed (half-open state)
        result = await breaker.call_async(counting_func)
        assert result == "ok"
        assert call_count == 2

        # Breaker should now be closed
        assert breaker.current_state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_breaker_circuit_breaker_error_has_time_remaining(self):
        """CircuitBreakerError should include time remaining."""
        breaker = create_circuit_breaker(fail_max=1, timeout_seconds=5)

        async def failing_func():
            raise Exception("Error")

        # Trip the breaker
        with pytest.raises(Exception):
            await breaker.call_async(failing_func)

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            await breaker.call_async(failing_func)

        # Check that time remaining is available
        error = exc_info.value
        assert hasattr(error, "time_remaining")
        # Should be close to 5 seconds (allow some tolerance for large time value)
        # aiobreaker returns time_remaining relative to when circuit was opened
        assert error.time_remaining.total_seconds() > 4
