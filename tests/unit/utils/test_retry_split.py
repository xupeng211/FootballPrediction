"""
测试拆分后的重试机制
Test Split Retry Mechanism
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch


# 测试导入
def test_import_retry_config():
    """测试能否正常导入重试配置"""
    # from src.utils.retry import RetryConfig

    assert RetryConfig is not None

    config = RetryConfig(max_attempts=5)
    assert config.max_attempts == 5


def test_import_strategies():
    """测试能否正常导入退避策略"""
    from src.utils.retry import (
        BackoffStrategy,
        ExponentialBackoffStrategy,
        FixedBackoffStrategy,
        LinearBackoffStrategy,
        PolynomialBackoffStrategy,
    )

    assert BackoffStrategy is not None
    assert ExponentialBackoffStrategy is not None
    assert FixedBackoffStrategy is not None
    assert LinearBackoffStrategy is not None
    assert PolynomialBackoffStrategy is not None


def test_import_decorators():
    """测试能否正常导入重试装饰器"""
    # from src.utils.retry import retry, retry_async, retry_sync

    assert retry is not None
    assert retry_async is not None
    assert retry_sync is not None


def test_import_circuit():
    """测试能否正常导入熔断器"""
    # from src.utils.retry import CircuitState, CircuitBreaker

    assert CircuitState is not None
    assert CircuitBreaker is not None


# 测试退避策略
def test_fixed_backoff_strategy():
    """测试固定退避策略"""
    from src.utils.retry.strategies import FixedBackoffStrategy

    strategy = FixedBackoffStrategy(delay=2.0)

    assert strategy.get_delay(attempt=0) == 2.0
    assert strategy.get_delay(attempt=5) == 2.0


def test_linear_backoff_strategy():
    """测试线性退避策略"""
    from src.utils.retry.strategies import LinearBackoffStrategy

    strategy = LinearBackoffStrategy(base_delay=1.0, increment=0.5, max_delay=5.0)

    assert strategy.get_delay(attempt=0) == 1.0
    assert strategy.get_delay(attempt=1) == 1.5
    assert strategy.get_delay(attempt=2) == 2.0
    assert strategy.get_delay(attempt=10) == 5.0  # 受max_delay限制


def test_exponential_backoff_strategy():
    """测试指数退避策略"""
    from src.utils.retry.strategies import ExponentialBackoffStrategy

    strategy = ExponentialBackoffStrategy(
        base_delay=1.0, exponential_base=2.0, max_delay=10.0, jitter=False
    )

    assert strategy.get_delay(attempt=0) == 1.0
    assert strategy.get_delay(attempt=1) == 2.0
    assert strategy.get_delay(attempt=2) == 4.0
    assert strategy.get_delay(attempt=3) == 8.0
    assert strategy.get_delay(attempt=4) == 10.0  # 受max_delay限制


def test_polynomial_backoff_strategy():
    """测试多项式退避策略"""
    from src.utils.retry.strategies import PolynomialBackoffStrategy

    strategy = PolynomialBackoffStrategy(
        base_delay=1.0, power=2.0, max_delay=10.0, jitter=False
    )

    assert strategy.get_delay(attempt=0) == 1.0
    assert strategy.get_delay(attempt=1) == 4.0
    assert strategy.get_delay(attempt=2) == 9.0
    assert strategy.get_delay(attempt=3) == 10.0  # 受max_delay限制


# 测试重试配置
def test_retry_config_creation():
    """测试创建重试配置"""
    from src.utils.retry.config import RetryConfig

    config = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=30.0,
        exponential_base=3.0,
        jitter=False,
        retryable_exceptions=(ValueError, TypeError),
    )

    assert config.max_attempts == 5
    assert config.base_delay == 2.0
    assert config.max_delay == 30.0
    assert config.exponential_base == 3.0
    assert config.jitter is False
    assert config.retryable_exceptions == (ValueError, TypeError)
    assert config.backoff_strategy is not None


# 测试重试装饰器
def test_retry_decorator_sync():
    """测试同步重试装饰器"""
    # from src.utils.retry import retry, RetryConfig

    config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
    call_count = 0

    @retry(config)
    def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Test error")
        return "success"

    result = failing_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_decorator_async():
    """测试异步重试装饰器"""
    # from src.utils.retry import retry, RetryConfig

    config = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
    call_count = 0

    @retry(config)
    async def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Test error")
        return "success"

    result = await failing_function()
    assert result == "success"
    assert call_count == 3


def test_retry_decorator_with_callback():
    """测试带回调的重试装饰器"""
    # from src.utils.retry import retry, RetryConfig

    config = RetryConfig(max_attempts=2, base_delay=0.01)
    callback_calls = []

    def retry_callback(attempt: int, error: Exception):
        callback_calls.append((attempt, str(error)))

    @retry(config, on_retry=retry_callback)
    def failing_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        failing_function()

    # 应该只调用一次回调（第一次重试）
    assert len(callback_calls) == 1
    assert callback_calls[0][0] == 1  # 第一次重试


# 测试熔断器
@pytest.mark.asyncio
async def test_circuit_breaker_initial_state():
    """测试熔断器初始状态"""
    from src.utils.retry.circuit import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(failure_threshold=3)

    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.get_failure_count() == 0


@pytest.mark.asyncio
async def test_circuit_breaker_success():
    """测试熔断器成功调用"""
    from src.utils.retry.circuit import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(failure_threshold=3)

    async def success_func():
        return "success"

    result = await breaker.call(success_func)
    assert result == "success"
    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.get_failure_count() == 0


@pytest.mark.asyncio
async def test_circuit_breaker_failure():
    """测试熔断器失败调用"""
    from src.utils.retry.circuit import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(failure_threshold=2)

    async def failing_func():
        raise ValueError("Test error")

    # 第一次失败
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.get_failure_count() == 1

    # 第二次失败，应该打开熔断器
    with pytest.raises(ValueError):
        await breaker.call(failing_func)
    assert breaker.get_state() == CircuitState.OPEN
    assert breaker.get_failure_count() == 2


@pytest.mark.asyncio
async def test_circuit_breaker_open_blocks_calls():
    """测试熔断器打开时阻止调用"""
    from src.utils.retry.circuit import CircuitBreaker, CircuitState

    breaker = CircuitBreaker(failure_threshold=1)

    async def failing_func():
        raise ValueError("Test error")

    # 第一次失败，打开熔断器
    with pytest.raises(ValueError):
        await breaker.call(failing_func)

    # 熔断器打开，应该阻止调用
    with pytest.raises(Exception, match="熔断器已打开"):
        await breaker.call(failing_func)


def test_circuit_breaker_reset():
    """测试熔断器重置"""
    from src.utils.retry.circuit import CircuitBreaker, CircuitState

    breaker = CircuitBreaker()
    breaker.failure_count = 5
    breaker.state = CircuitState.OPEN

    breaker.reset()

    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.get_failure_count() == 0


# 测试向后兼容性
def test_backward_compatibility_import():
    """测试向后兼容的导入"""
    from src.utils.retry import (
        RetryConfig,
        ExponentialBackoffStrategy,
        FixedBackoffStrategy,
        retry,
        retry_async,
        retry_sync,
        CircuitState,
        CircuitBreaker,
    )

    assert RetryConfig is not None
    assert ExponentialBackoffStrategy is not None
    assert FixedBackoffStrategy is not None
    assert retry is not None
    assert retry_async is not None
    assert retry_sync is not None
    assert CircuitState is not None
    assert CircuitBreaker is not None


def test_backward_compatibility_usage():
    """测试向后兼容的使用方式"""
    # from src.utils.retry import retry, RetryConfig

    config = RetryConfig(max_attempts=2, base_delay=0.01)

    @retry(config)
    def test_function():
        return "test"

    result = test_function()
    assert result == "test"
