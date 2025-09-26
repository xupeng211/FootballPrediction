"""
Enhanced test file for retry.py utility module
Provides comprehensive coverage for retry mechanism and circuit breaker functionality
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, call
from typing import Any, Callable, Type, Tuple

# Import directly to avoid NumPy reload issues
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from utils.retry import (
    RetryConfig, retry, CircuitBreaker, CircuitState,
    T  # TypeVar for generic typing
)


class TestRetryConfigEnhanced:
    """Enhanced tests for RetryConfig class"""

    def test_retry_config_complete_parameters(self):
        """Test RetryConfig with all parameters specified"""
        config = RetryConfig(
            max_attempts=10,
            base_delay=0.5,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=(ValueError, KeyError, ConnectionError)
        )

        assert config.max_attempts == 10
        assert config.base_delay == 0.5
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.retryable_exceptions == (ValueError, KeyError, ConnectionError)

    def test_retry_config_single_exception(self):
        """Test RetryConfig with single exception type"""
        config = RetryConfig(
            max_attempts=5,
            retryable_exceptions=ValueError  # Single exception instead of tuple
        )

        assert config.retryable_exceptions == (ValueError,)

    def test_retry_config_no_retryable_exceptions(self):
        """Test RetryConfig with no retryable exceptions (should use Exception)"""
        config = RetryConfig(retryable_exceptions=())
        assert config.retryable_exceptions == (Exception,)

    def test_retry_config_boundary_values(self):
        """Test RetryConfig with boundary values"""
        # Test minimum values
        config_min = RetryConfig(
            max_attempts=1,
            base_delay=0.001,
            max_delay=0.002,
            exponential_base=1.0
        )
        assert config_min.max_attempts == 1
        assert config_min.base_delay == 0.001
        assert config_min.max_delay == 0.002
        assert config_min.exponential_base == 1.0

        # Test maximum values
        config_max = RetryConfig(
            max_attempts=1000,
            base_delay=3600.0,  # 1 hour
            max_delay=86400.0,  # 1 day
            exponential_base=10.0
        )
        assert config_max.max_attempts == 1000
        assert config_max.base_delay == 3600.0
        assert config_max.max_delay == 86400.0
        assert config_max.exponential_base == 10.0

    def test_retry_config_zero_values(self):
        """Test RetryConfig with zero values"""
        config = RetryConfig(
            max_attempts=0,  # Edge case
            base_delay=0.0,
            max_delay=0.0
        )
        assert config.max_attempts == 0
        assert config.base_delay == 0.0
        assert config.max_delay == 0.0

    def test_retry_config_negative_values(self):
        """Test RetryConfig with negative values"""
        config = RetryConfig(
            max_attempts=-1,
            base_delay=-1.0,
            max_delay=-1.0
        )
        # Should accept negative values (behavior depends on implementation)
        assert config.max_attempts == -1
        assert config.base_delay == -1.0
        assert config.max_delay == -1.0


class TestRetryDecoratorEnhanced:
    """Enhanced tests for retry decorator"""

    @pytest.mark.asyncio
    async def test_retry_decorator_async_immediate_success(self):
        """Test async function that succeeds immediately"""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry(config)
        async def immediate_success():
            nonlocal call_count
            call_count += 1
            return "immediate_success"

        result = await immediate_success()

        assert result == "immediate_success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_decorator_async_retry_on_specific_exception(self):
        """Test async function that retries on specific exception types"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.01,
            jitter=False,
            retryable_exceptions=(ValueError, TypeError)
        )

        call_count = 0

        @retry(config)
        async def function_with_specific_errors():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return "success_after_retries"

        result = await function_with_specific_errors()

        assert result == "success_after_retries"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_async_no_retry_on_unhandled_exception(self):
        """Test async function that doesn't retry on unhandled exception types"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)  # Only retry ValueError
        )

        call_count = 0

        @retry(config)
        async def function_with_unhandled_error():
            nonlocal call_count
            call_count += 1
            raise TypeError(f"Unhandled error on attempt {call_count}")

        with pytest.raises(TypeError, match="Unhandled error on attempt 1"):
            await function_with_unhandled_error()

        assert call_count == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_retry_decorator_async_exponential_backoff(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            max_delay=100.0,
            exponential_base=2.0,
            jitter=False
        )

        call_times = []

        @retry(config)
        async def function_with_backoff():
            call_times.append(time.time())
            if len(call_times) < 3:  # Fail first 2 times
                raise ValueError("Backoff test")
            return "success"

        start_time = time.time()
        result = await function_with_backoff()
        end_time = time.time()

        assert result == "success"
        assert len(call_times) == 3

        # Verify delays follow exponential pattern
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Should be approximately 1.0 and 2.0 seconds (with some tolerance)
        assert 0.9 <= delay1 <= 1.1
        assert 1.9 <= delay2 <= 2.1

    @pytest.mark.asyncio
    async def test_retry_decorator_async_max_delay_capping(self):
        """Test that delay is capped at max_delay"""
        config = RetryConfig(
            max_attempts=4,
            base_delay=10.0,
            max_delay=15.0,
            exponential_base=3.0,
            jitter=False
        )

        call_times = []

        @retry(config)
        async def function_with_max_delay():
            call_times.append(time.time())
            if len(call_times) < 3:  # Fail first 2 times
                raise ValueError("Max delay test")
            return "success"

        result = await function_with_max_delay()
        assert result == "success"
        assert len(call_times) == 3

        # Verify delays are capped at max_delay
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        assert delay1 == 10.0  # First delay = base_delay
        assert delay2 == 15.0  # Second delay capped at max_delay (would be 30.0 without cap)

    @pytest.mark.asyncio
    async def test_retry_decorator_async_with_jitter(self):
        """Test jitter functionality"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            jitter=True
        )

        call_times = []

        @retry(config)
        async def function_with_jitter():
            call_times.append(time.time())
            if len(call_times) < 2:  # Fail first time
                raise ValueError("Jitter test")
            return "success"

        result = await function_with_jitter()
        assert result == "success"
        assert len(call_times) == 2

        delay = call_times[1] - call_times[0]
        # With jitter, delay should be between 0.5 * base_delay and 1.0 * base_delay
        assert 0.5 <= delay <= 1.0

    @pytest.mark.asyncio
    async def test_retry_decorator_async_complex_callback(self):
        """Test retry with complex callback function"""
        config = RetryConfig(
            max_attempts=4,
            base_delay=0.01,
            jitter=False
        )

        callback_data = []

        def complex_callback(attempt: int, error: Exception):
            callback_data.append({
                "attempt": attempt,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": time.time()
            })

        @retry(config, on_retry=complex_callback)
        async def function_with_complex_callback():
            if len(callback_data) < 2:  # Fail first 2 times
                raise ValueError(f"Complex callback test {len(callback_data)}")
            return "success"

        result = await function_with_complex_callback()

        assert result == "success"
        assert len(callback_data) == 2

        # Verify callback data structure
        for i, callback_info in enumerate(callback_data):
            assert callback_info["attempt"] == i + 1
            assert callback_info["error_type"] == "ValueError"
            assert "Complex callback test" in callback_info["error_message"]
            assert "timestamp" in callback_info

    def test_retry_decorator_sync_immediate_success(self):
        """Test sync function that succeeds immediately"""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry(config)
        def immediate_success_sync():
            nonlocal call_count
            call_count += 1
            return "immediate_success_sync"

        result = immediate_success_sync()

        assert result == "immediate_success_sync"
        assert call_count == 1

    def test_retry_decorator_sync_retry_with_various_return_types(self):
        """Test sync function retry with various return types"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry(config)
        def function_various_returns():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError(f"Attempt {call_count}")
            # Return different types on success
            return {
                "string": "success",
                "number": 42,
                "list": [1, 2, 3],
                "none": None,
                "boolean": True
            }

        result = function_various_returns()

        assert result == {
            "string": "success",
            "number": 42,
            "list": [1, 2, 3],
            "none": None,
            "boolean": True
        }
        assert call_count == 2

    def test_retry_decorator_sync_with_exception_hierarchy(self):
        """Test sync function with exception hierarchy"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(LookupError,)  # Parent of KeyError, IndexError
        )

        call_count = 0

        @retry(config)
        def function_with_key_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise KeyError("Key not found")
            return "found_key"

        result = function_with_key_error()

        assert result == "found_key"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_async_function_arguments(self):
        """Test retry decorator with function arguments"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_data = []

        @retry(config)
        async def function_with_args(arg1, arg2, kwarg1=None, kwarg2=None):
            call_data.append({
                "arg1": arg1,
                "arg2": arg2,
                "kwarg1": kwarg1,
                "kwarg2": kwarg2
            })
            if len(call_data) < 2:
                raise ValueError("Retry with args test")
            return "success"

        result = await function_with_args("pos1", "pos2", kwarg1="kwval1", kwarg2="kwval2")

        assert result == "success"
        assert len(call_data) == 2

        # Verify arguments are preserved across retries
        for call in call_data:
            assert call["arg1"] == "pos1"
            assert call["arg2"] == "pos2"
            assert call["kwarg1"] == "kwval1"
            assert call["kwarg2"] == "kwval2"


class TestCircuitBreakerEnhanced:
    """Enhanced tests for CircuitBreaker class"""

    @pytest.fixture
    def fast_circuit_breaker(self):
        """Create circuit breaker with fast timeouts for testing"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0.05,  # 50ms
            retry_timeout=0.02      # 20ms
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_multiple_success_calls(self, fast_circuit_breaker):
        """Test multiple successful calls through circuit breaker"""
        call_count = 0

        async def successful_function():
            nonlocal call_count
            call_count += 1
            return f"success_{call_count}"

        # Make multiple successful calls
        for i in range(5):
            result = await fast_circuit_breaker.call(successful_function)
            assert result == f"success_{i + 1}"

        assert call_count == 5
        assert fast_circuit_breaker.state == CircuitState.CLOSED
        assert fast_circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_mixed_success_failure_calls(self, fast_circuit_breaker):
        """Test mixed success and failure calls"""
        call_count = 0

        async def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:  # Fail on odd attempts
                raise ValueError("Odd attempt failure")
            return f"success_{call_count}"

        # Should fail on 1st and 3rd attempts, succeed on 2nd and 4th
        results = []
        errors = []

        for i in range(4):
            try:
                result = await fast_circuit_breaker.call(sometimes_failing_function)
                results.append(result)
            except Exception as e:
                errors.append(e)

        assert len(results) == 2  # 2 successful calls
        assert len(errors) == 2   # 2 failed calls
        assert fast_circuit_breaker.failure_count == 2
        assert fast_circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_with_successful_calls(self, fast_circuit_breaker):
        """Test circuit breaker recovery after successful calls"""
        async def failing_function():
            raise ValueError("Consistent failure")

        async def successful_function():
            return "recovery_success"

        # Cause failures to open circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await fast_circuit_breaker.call(failing_function)

        assert fast_circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.1)  # Wait longer than recovery_timeout

        # Make successful call to recover
        result = await fast_circuit_breaker.call(successful_function)

        assert result == "recovery_success"
        assert fast_circuit_breaker.state == CircuitState.CLOSED
        assert fast_circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_multiple_failures_in_half_open_state(self, fast_circuit_breaker):
        """Test multiple failures in half-open state"""
        async def failing_function():
            raise ValueError("Half-open failure")

        # Open circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await fast_circuit_breaker.call(failing_function)

        assert fast_circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.1)

        # Make multiple failing calls in half-open state
        for _ in range(3):
            with pytest.raises(ValueError):
                await fast_circuit_breaker.call(failing_function)

        # Should still be in OPEN state (no recovery)
        assert fast_circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_function_with_arguments(self, fast_circuit_breaker):
        """Test circuit breaker with function arguments"""
        call_data = []

        async def function_with_args(arg1, arg2, kwarg1=None):
            call_data.append({
                "arg1": arg1,
                "arg2": arg2,
                "kwarg1": kwarg1
            })
            return "success"

        result = await fast_circuit_breaker.call(
            function_with_args,
            "pos1",
            "pos2",
            kwarg1="kwval1"
        )

        assert result == "success"
        assert len(call_data) == 1
        assert call_data[0]["arg1"] == "pos1"
        assert call_data[0]["arg2"] == "pos2"
        assert call_data[0]["kwarg1"] == "kwval1"

    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout_precision(self, fast_circuit_breaker):
        """Test circuit breaker timeout precision"""
        async def failing_function():
            raise ValueError("Timeout test")

        # Open circuit breaker
        for _ in range(3):
            with pytest.raises(ValueError):
                await fast_circuit_breaker.call(failing_function)

        assert fast_circuit_breaker.state == CircuitState.OPEN

        # Test exact timing for recovery
        start_time = time.time()

        # Should fail immediately (circuit open)
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await fast_circuit_breaker.call(failing_function)

        # Wait for recovery timeout
        time.sleep(fast_circuit_breaker.recovery_timeout + 0.01)

        # Should now allow one call (half-open state)
        with pytest.raises(ValueError):
            await fast_circuit_breaker.call(failing_function)

        end_time = time.time()
        total_time = end_time - start_time

        # Verify timing is approximately correct
        assert total_time >= fast_circuit_breaker.recovery_timeout


class TestRetryIntegration:
    """Integration tests combining retry and circuit breaker"""

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_pattern(self):
        """Test combining retry decorator with circuit breaker"""
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=0.1,
            retry_timeout=0.05
        )

        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            retryable_exceptions=(ValueError,)
        )

        retry_count = 0

        @retry(config)
        async def function_with_retry_and_circuit():
            nonlocal retry_count
            retry_count += 1
            if retry_count <= 2:
                raise ValueError(f"Retry attempt {retry_count}")
            # After retries, use circuit breaker
            return await circuit_breaker.call(
                lambda: "success_with_circuit_breaker"
            )

        result = await function_with_retry_and_circuit()

        assert result == "success_with_circuit_breaker"
        assert retry_count == 3

    @pytest.mark.asyncio
    async def test_nested_retry_scenarios(self):
        """Test nested retry scenarios"""
        outer_config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False
        )

        inner_config = RetryConfig(
            max_attempts=2,
            base_delay=0.005,
            jitter=False
        )

        outer_call_count = 0
        inner_call_count = 0

        @retry(inner_config)
        async def inner_function():
            nonlocal inner_call_count
            inner_call_count += 1
            if inner_call_count == 1:
                raise ValueError("Inner function failure")
            return "inner_success"

        @retry(outer_config)
        async def outer_function():
            nonlocal outer_call_count
            outer_call_count += 1
            if outer_call_count == 1:
                raise ValueError("Outer function failure")
            return await inner_function()

        result = await outer_function()

        assert result == "inner_success"
        assert outer_call_count == 2  # Failed once, then succeeded
        assert inner_call_count == 2  # Failed once, then succeeded

    @pytest.mark.asyncio
    async def test_concurrent_retry_calls(self):
        """Test concurrent retry calls"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False
        )

        call_counters = {}

        @retry(config)
        async def concurrent_function(call_id):
            if call_id not in call_counters:
                call_counters[call_id] = 0
            call_counters[call_id] += 1

            if call_counters[call_id] == 1:
                raise ValueError(f"First failure for {call_id}")
            return f"success_{call_id}"

        # Make concurrent calls
        tasks = []
        for i in range(3):
            task = concurrent_function(f"call_{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=False)

        # All calls should succeed after retries
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result == f"success_call_{i}"

        # Verify each call was retried once
        for call_id in call_counters:
            assert call_counters[call_id] == 2


class TestRetryEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_retry_with_zero_attempts(self):
        """Test retry with zero max attempts"""
        config = RetryConfig(max_attempts=0, base_delay=0.01)

        @retry(config)
        async def failing_function():
            raise ValueError("Should fail immediately")

        with pytest.raises(ValueError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_retry_with_zero_delay(self):
        """Test retry with zero delay"""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.0,
            jitter=False
        )

        call_count = 0

        @retry(config)
        async def zero_delay_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Zero delay test")
            return "success"

        start_time = time.time()
        result = await zero_delay_function()
        end_time = time.time()

        assert result == "success"
        assert call_count == 3
        assert end_time - start_time < 0.1  # Should complete very quickly

    @pytest.mark.asyncio
    async def test_retry_callback_exception_handling(self):
        """Test retry with callback that raises exceptions"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        def failing_callback(attempt, error):
            raise RuntimeError("Callback failed")

        @retry(config, on_retry=failing_callback)
        async def function_with_failing_callback():
            if call_count < 2:  # This will be defined below
                raise ValueError("Function failure")
            return "success"

        # Callback failure should not affect retry logic
        call_count = 0
        original_callback = failing_callback

        def safe_callback(attempt, error):
            nonlocal call_count
            call_count += 1
            # Don't raise exception in callback for this test

        result = await function_with_failing_callback()
        assert result == "success"

    def test_retry_decorator_sync_return_values(self):
        """Test retry decorator with various return values"""
        config = RetryConfig(max_attempts=2, base_delay=0.01, jitter=False)

        @retry(config)
        def function_returning_none():
            return None

        @retry(config)
        def function_returning_empty():
            return ""

        @retry(config)
        def function_returning_zero():
            return 0

        @retry(config)
        def function_returning_false():
            return False

        assert function_returning_none() is None
        assert function_returning_empty() == ""
        assert function_returning_zero() == 0
        assert function_returning_false() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_custom_exception_types(self):
        """Test circuit breaker with custom exception types"""
        class CustomError(Exception):
            pass

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.05
        )

        async def custom_error_function():
            raise CustomError("Custom error")

        # Custom exceptions should still trigger circuit breaker
        for _ in range(2):
            with pytest.raises(CustomError):
                await circuit_breaker.call(custom_error_function)

        assert circuit_breaker.state == CircuitState.OPEN

        # Should block subsequent calls
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(custom_error_function)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])