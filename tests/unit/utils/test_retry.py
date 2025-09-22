"""
重试机制测试 / Retry Mechanism Tests

测试重试机制的功能，包括重试装饰器、熔断器和配置。

Tests for retry mechanism functionality, including retry decorator, circuit breaker, and configuration.

测试类 / Test Classes:
    TestRetryConfig: 重试配置测试 / Retry configuration tests
    TestRetryDecorator: 重试装饰器测试 / Retry decorator tests
    TestCircuitBreaker: 熔断器测试 / Circuit breaker tests

测试方法 / Test Methods:
    test_retry_config_creation: 测试重试配置创建 / Test retry configuration creation
    test_retry_decorator_sync: 测试同步函数重试装饰器 / Test sync function retry decorator
    test_retry_decorator_async: 测试异步函数重试装饰器 / Test async function retry decorator
    test_circuit_breaker_state_transitions: 测试熔断器状态转换 / Test circuit breaker state transitions

使用示例 / Usage Example:
    ```bash
    # 运行重试机制测试
    pytest tests/unit/utils/test_retry.py -v

    # 运行特定测试
    pytest tests/unit/utils/test_retry.py::TestRetryDecorator::test_retry_decorator_async -v
    ```
"""

import asyncio
from unittest.mock import ANY, Mock

import pytest

from src.utils.retry import CircuitBreaker, CircuitState, RetryConfig, retry


class TestRetryConfig:
    """重试配置测试 / Retry Configuration Tests"""

    def test_retry_config_creation(self):
        """测试重试配置创建 / Test retry configuration creation"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(ValueError, ConnectionError),
        )

        assert config.max_attempts == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (ValueError, ConnectionError)

    def test_retry_config_default_values(self):
        """测试重试配置默认值 / Test retry configuration default values"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (Exception,)


class TestRetryDecorator:
    """重试装饰器测试 / Retry Decorator Tests"""

    @pytest.mark.asyncio
    async def test_retry_decorator_async_success(self):
        """测试异步函数重试装饰器成功 / Test async function retry decorator success"""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry(config)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_decorator_async_retry_success(self):
        """测试异步函数重试装饰器重试后成功 / Test async function retry decorator retry then success"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry(config)
        async def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = await sometimes_failing_function()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator_async_max_attempts_reached(self):
        """测试异步函数重试装饰器达到最大尝试次数 / Test async function retry decorator max attempts reached"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry(config)
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError, match="Permanent failure"):
            await always_failing_function()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_decorator_async_with_callback(self):
        """测试异步函数重试装饰器带回调 / Test async function retry decorator with callback"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        retry_callback = Mock()
        call_count = 0

        @retry(config, on_retry=retry_callback)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        with pytest.raises(ValueError, match="Failure"):
            await failing_function()

        assert call_count == 3
        assert retry_callback.call_count == 2  # Called after attempt 1 and 2 failures
        retry_callback.assert_any_call(1, ANY)
        retry_callback.assert_any_call(2, ANY)
        seen_attempts = set()
        for call in retry_callback.call_args_list:
            attempt, error = call.args
            assert attempt in (1, 2)
            seen_attempts.add(attempt)
            assert isinstance(error, ValueError)
        assert seen_attempts == {1, 2}

    def test_retry_decorator_sync_success(self):
        """测试同步函数重试装饰器成功 / Test sync function retry decorator success"""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry(config)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_decorator_sync_retry_success(self):
        """测试同步函数重试装饰器重试后成功 / Test sync function retry decorator retry then success"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry(config)
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = sometimes_failing_function()

        assert result == "success"
        assert call_count == 2

    def test_retry_decorator_sync_max_attempts_reached(self):
        """测试同步函数重试装饰器达到最大尝试次数 / Test sync function retry decorator max attempts reached"""
        config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)

        call_count = 0

        @retry(config)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent failure")

        with pytest.raises(ValueError, match="Permanent failure"):
            always_failing_function()

        assert call_count == 3


class TestCircuitBreaker:
    """熔断器测试 / Circuit Breaker Tests"""

    @pytest.fixture
    def circuit_breaker(self):
        """创建熔断器实例 / Create circuit breaker instance"""
        return CircuitBreaker(
            failure_threshold=3, recovery_timeout=0.1, retry_timeout=0.05
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, circuit_breaker):
        """测试熔断器初始状态 / Test circuit breaker initial state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_successful_call(self, circuit_breaker):
        """测试熔断器成功调用 / Test circuit breaker successful call"""

        async def successful_function():
            return "success"

        result = await circuit_breaker.call(successful_function)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_count(self, circuit_breaker):
        """测试熔断器失败计数 / Test circuit breaker failure count"""

        async def failing_function():
            raise ValueError("Failure")

        # 进行两次失败调用
        for _ in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.failure_count == 2
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self, circuit_breaker):
        """测试熔断器打开状态 / Test circuit breaker open state"""

        async def failing_function():
            raise ValueError("Failure")

        # 进行足够多的失败调用以打开熔断器
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.state == CircuitState.OPEN

        # 尝试在打开状态下调用应该失败
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self, circuit_breaker):
        """测试熔断器半开状态 / Test circuit breaker half-open state"""

        async def failing_function():
            raise ValueError("Failure")

        # 打开熔断器
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.state == CircuitState.OPEN

        # 直接快进恢复时间，避免真实等待
        assert circuit_breaker.last_failure_time is not None
        circuit_breaker.last_failure_time -= circuit_breaker.recovery_timeout + 0.01

        # 在半开状态下，应该允许一次调用
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_function)

        # 失败后应该回到打开状态
        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, circuit_breaker):
        """测试熔断器恢复 / Test circuit breaker recovery"""

        async def failing_function():
            raise ValueError("Failure")

        async def successful_function():
            return "success"

        # 打开熔断器
        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_function)

        assert circuit_breaker.state == CircuitState.OPEN

        # 直接快进恢复时间，避免真实等待
        assert circuit_breaker.last_failure_time is not None
        circuit_breaker.last_failure_time -= circuit_breaker.recovery_timeout + 0.01

        # 在半开状态下成功调用应该恢复熔断器
        result = await circuit_breaker.call(successful_function)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
