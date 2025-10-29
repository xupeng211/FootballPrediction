from unittest.mock import MagicMock

"""增强的重试功能测试（简化版）"""

import time

import pytest

# from src.utils.retry import RetryConfig, retry, CircuitBreaker, CircuitState


@pytest.mark.unit
class TestRetrySimpleEnhanced:
    """增强的重试功能测试（简化版）"""

    def test_retry_config_creation(self):
        """测试RetryConfig创建"""
        _config = RetryConfig(
            max_attempts=5,
            base_delay=0.1,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(ValueError, KeyError),
        )

        assert _config.max_attempts == 5
        assert _config.base_delay == 0.1
        assert _config.max_delay == 10.0
        assert _config.exponential_base == 2.0
        assert _config.jitter is True
        assert ValueError in _config.retryable_exceptions
        assert KeyError in _config.retryable_exceptions

    def test_retry_config_default_values(self):
        """测试RetryConfig默认值"""
        _config = RetryConfig()

        assert _config.max_attempts == 3
        assert _config.base_delay == 1.0
        assert _config.max_delay == 60.0
        assert _config.exponential_base == 2.0
        assert _config.jitter is False
        assert Exception in _config.retryable_exceptions

    def test_retry_decorator_success_on_first_try(self):
        """测试重试装饰器（第一次成功）"""

        @retry(RetryConfig(max_attempts=3))
        def successful_function():
            return "success"

        _result = successful_function()
        assert _result == "success"

    def test_retry_decorator_eventual_success(self):
        """测试重试装饰器（最终成功）"""
        attempt_count = 0

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        _result = flaky_function()
        assert _result == "success"
        assert attempt_count == 3

    def test_retry_decorator_all_attempts_fail(self):
        """测试重试装饰器（所有尝试都失败）"""

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def always_failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

    def test_retry_decorator_with_non_retryable_exception(self):
        """测试重试装饰器（非可重试异常）"""

        @retry(RetryConfig(max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,)))
        def function_with_key_error():
            raise KeyError("Not retryable")

        with pytest.raises(KeyError, match="Not retryable"):
            function_with_key_error()

    def test_retry_decorator_with_jitter(self):
        """测试重试装饰器（带抖动）"""
        delays = []

        def delay_callback(delay):
            delays.append(delay)

        @retry(
            RetryConfig(
                max_attempts=3,
                base_delay=0.1,
                jitter=True,
                delay_callback=delay_callback,
            )
        )
        def failing_function():
            raise ValueError("Test failure")

        with pytest.raises(ValueError):
            failing_function()

        assert len(delays) == 2
        # 验证抖动效果：延迟应该略有不同
        assert delays[0] != delays[1] or abs(delays[0] - delays[1]) > 0.001

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """测试异步重试装饰器"""
        attempt_count = 0

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def async_flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Async temporary failure")
            return "async success"

        _result = await async_flaky_function()
        assert _result == "async success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_all_attempts_fail(self):
        """测试异步重试（所有尝试都失败）"""

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def async_always_failing_function():
            raise ValueError("Async always fails")

        with pytest.raises(ValueError, match="Async always fails"):
            await async_always_failing_function()

    def test_retry_with_timeout(self):
        """测试带超时的重试"""
        start_time = time.time()

        @retry(RetryConfig(max_attempts=5, base_delay=0.1, max_delay=0.2, timeout=0.3))
        def slow_failing_function():
            time.sleep(0.15)
            time.sleep(0.15)
            time.sleep(0.15)
            raise ValueError("Timeout test")

        with pytest.raises(ValueError):
            slow_failing_function()

        elapsed = time.time() - start_time
        # 应该在超时前停止，不会执行所有5次重试
        assert elapsed < 0.5

    def test_retry_preserves_function_metadata(self):
        """测试重试装饰器保留函数元数据"""

        @retry(RetryConfig(max_attempts=3))
        def example_function(param1, param2):
            """示例函数文档字符串"""
            return f"{param1}-{param2}"

        assert example_function.__name__ == "example_function"
        assert "示例函数文档字符串" in example_function.__doc__
        assert example_function("a", "b") == "a-b"

    def test_retry_with_callback(self):
        """测试带回调的重试"""
        callback_calls = []

        def attempt_callback(attempt, error, delay):
            callback_calls.append((attempt, str(error), delay))

        @retry(RetryConfig(max_attempts=3, base_delay=0.01, attempt_callback=attempt_callback))
        def failing_function():
            raise ValueError("Callback test")

        with pytest.raises(ValueError):
            failing_function()

        assert len(callback_calls) == 2  # 3次尝试，前2次失败
        assert callback_calls[0][0] == 1  # 第一次尝试
        assert callback_calls[1][0] == 2  # 第二次尝试
        assert "Callback test" in callback_calls[0][1]

    def test_retry_delay_calculation_without_jitter(self):
        """测试重试延迟计算（无抖动）"""
        delays = []

        def delay_callback(delay):
            delays.append(delay)

        @retry(
            RetryConfig(
                max_attempts=4,
                base_delay=0.1,
                exponential_base=2.0,
                jitter=False,
                delay_callback=delay_callback,
            )
        )
        def failing_function():
            raise ValueError("Delay test")

        with pytest.raises(ValueError):
            failing_function()

        # 验证指数退避：0.1, 0.2, 0.4
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4

    def test_retry_delay_with_max_limit(self):
        """测试重试延迟（受最大值限制）"""
        delays = []

        def delay_callback(delay):
            delays.append(delay)

        @retry(
            RetryConfig(
                max_attempts=4,
                base_delay=10,
                exponential_base=3,
                max_delay=20,
                jitter=False,
                delay_callback=delay_callback,
            )
        )
        def failing_function():
            raise ValueError("Max delay test")

        with pytest.raises(ValueError):
            failing_function()

        # 验证最大延迟限制：10, 20, 20
        assert delays[0] == 10
        assert delays[1] == 20
        assert delays[2] == 20

    # Circuit Breaker tests
    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        breaker = CircuitBreaker(
            failure_threshold=3, recovery_timeout=5, expected_exception=ValueError
        )

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None

    def test_circuit_breaker_success_keeps_closed(self):
        """测试熔断器成功保持关闭"""
        breaker = CircuitBreaker(
            failure_threshold=3, recovery_timeout=5, expected_exception=ValueError
        )

        @breaker
        def successful_function():
            return "success"

        _result = successful_function()
        assert _result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self):
        """测试熔断器达到阈值后打开"""
        breaker = CircuitBreaker(
            failure_threshold=3, recovery_timeout=5, expected_exception=ValueError
        )

        @breaker
        def failing_function():
            raise ValueError("Circuit test")

        # 失败3次
        for _ in range(3):
            with pytest.raises(ValueError):
                failing_function()

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """测试熔断器打开时阻止调用"""
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=5, expected_exception=ValueError
        )

        @breaker
        def failing_function():
            raise ValueError("Circuit test")

        # 失败2次触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        # 熔断器应该打开
        assert breaker.state == CircuitState.OPEN

        # 下次调用应该被阻止
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            failing_function()

    def test_circuit_breaker_half_open_after_timeout(self):
        """测试熔断器超时后半开"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,  # 短超时用于测试
            expected_exception=ValueError,
        )

        @breaker
        def failing_function():
            raise ValueError("Circuit test")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        assert breaker.state == CircuitState.OPEN

        # 等待超时
        time.sleep(0.15)

        # 下次调用应该触发半开状态
        with pytest.raises(ValueError):
            failing_function()

        # 状态应该是半开（因为失败）
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_on_half_open_success(self):
        """测试熔断器半开时成功后关闭"""
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=0.1, expected_exception=ValueError
        )

        call_count = 0

        @breaker
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Fail")
            return "success"

        # 触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                sometimes_failing_function()

        assert breaker.state == CircuitState.OPEN

        # 等待超时
        time.sleep(0.15)

        # 下次调用应该成功并关闭熔断器
        _result = sometimes_failing_function()
        assert _result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_ignores_unexpected_exception(self):
        """测试熔断器忽略非预期异常"""
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=5, expected_exception=ValueError
        )

        @breaker
        def function_with_key_error():
            raise KeyError("Unexpected")

        # KeyError不应该触发熔断器计数
        for _ in range(3):
            with pytest.raises(KeyError):
                function_with_key_error()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_async_circuit_breaker(self):
        """测试异步熔断器"""
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=0.1, expected_exception=ValueError
        )

        @breaker
        async def async_failing_function():
            raise ValueError("Async circuit test")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                await async_failing_function()

        assert breaker.state == CircuitState.OPEN

        # 下次调用应该被阻止
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await async_failing_function()

    def test_circuit_breaker_with_custom_exception_handler(self):
        """测试带自定义异常处理器的熔断器"""
        exception_handler = MagicMock()

        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=5,
            expected_exception=ValueError,
            on_state_change=exception_handler,
        )

        @breaker
        def failing_function():
            raise ValueError("Handler test")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        # 验证状态变化处理器被调用
        assert exception_handler.called
        call_args = exception_handler.call_args_list[-1]
        assert call_args[0][0] == CircuitState.OPEN  # 新状态

    def test_circuit_breaker_reset(self):
        """测试重置熔断器"""
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=5, expected_exception=ValueError
        )

        @breaker
        def failing_function():
            raise ValueError("Reset test")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_function()

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 2

        # 重置熔断器
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
