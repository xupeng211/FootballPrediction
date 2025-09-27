"""
Auto-generated tests for src.utils.retry module
"""

import asyncio
import pytest
import time
from unittest.mock import patch, MagicMock
from src.utils.retry import (
    RetryConfig,
    retry,
    CircuitBreaker,
    CircuitState
)


class TestRetryConfig:
    """测试重试配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (Exception,)

    def test_custom_config(self):
        """测试自定义配置"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.retryable_exceptions == (ConnectionError, TimeoutError)

    @pytest.mark.parametrize("max_attempts", [1, 2, 3, 5, 10])
    def test_different_max_attempts(self, max_attempts):
        """测试不同最大尝试次数"""
        config = RetryConfig(max_attempts=max_attempts)
        assert config.max_attempts == max_attempts

    @pytest.mark.parametrize("base_delay,max_delay", [
        (0.1, 5.0),
        (1.0, 10.0),
        (2.0, 60.0),
        (5.0, 300.0)
    ])
    def test_different_delays(self, base_delay, max_delay):
        """测试不同延迟配置"""
        config = RetryConfig(base_delay=base_delay, max_delay=max_delay)
        assert config.base_delay == base_delay
        assert config.max_delay == max_delay

    @pytest.mark.parametrize("exponential_base", [1.5, 2.0, 3.0, 5.0])
    def test_different_exponential_bases(self, exponential_base):
        """测试不同指数退避基数"""
        config = RetryConfig(exponential_base=exponential_base)
        assert config.exponential_base == exponential_base

    @pytest.mark.parametrize("jitter", [True, False])
    def test_different_jitter_settings(self, jitter):
        """测试不同抖动设置"""
        config = RetryConfig(jitter=jitter)
        assert config.jitter == jitter

    def test_custom_exceptions(self):
        """测试自定义异常类型"""
        exceptions = (ValueError, TypeError, ConnectionError)
        config = RetryConfig(retryable_exceptions=exceptions)
        assert config.retryable_exceptions == exceptions


class TestRetryDecorator:
    """测试重试装饰器"""

    def test_retry_success_on_first_attempt(self):
        """测试第一次尝试就成功"""
        mock_func = MagicMock(return_value="success")
        config = RetryConfig(max_attempts=3)

        @retry(config)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_after_failures(self):
        """测试几次失败后成功"""
        mock_func = MagicMock(side_effect=[Exception("error"), Exception("error"), "success"])
        config = RetryConfig(max_attempts=3)

        @retry(config)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_max_attempts_reached(self):
        """测试达到最大重试次数"""
        mock_func = MagicMock(side_effect=Exception("persistent error"))
        config = RetryConfig(max_attempts=2)

        @retry(config)
        def test_function():
            return mock_func()

        with pytest.raises(Exception, match="persistent error"):
            test_function()

        assert mock_func.call_count == 2

    def test_retry_non_retryable_exception(self):
        """测试不可重试的异常"""
        mock_func = MagicMock(side_effect=ValueError("non-retryable"))
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

        @retry(config)
        def test_function():
            return mock_func()

        with pytest.raises(ValueError, match="non-retryable"):
            test_function()

        assert mock_func.call_count == 1  # 不应该重试

    @patch('time.sleep')
    def test_retry_delay_calculation(self, mock_sleep):
        """测试重试延迟计算"""
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )

        @retry(config)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(1.0)  # 第一次重试延迟1秒

    @patch('time.sleep')
    def test_retry_max_delay_enforcement(self, mock_sleep):
        """测试最大延迟限制"""
        mock_func = MagicMock(side_effect=[Exception("error"), Exception("error"), "success"])
        config = RetryConfig(
            max_attempts=4,
            base_delay=10.0,
            max_delay=15.0,
            exponential_base=2.0,
            jitter=False
        )

        @retry(config)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert mock_func.call_count == 3

        # 检查延迟调用：第一次10秒，第二次应该被限制在15秒
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(10.0)
        mock_sleep.assert_any_call(15.0)

    @patch('time.sleep')
    @patch('random.random')
    def test_retry_with_jitter(self, mock_random, mock_sleep):
        """测试带抖动的重试"""
        mock_random.return_value = 0.3  # 固定随机数用于测试
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            jitter=True
        )

        @retry(config)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"

        # 抖动计算：1.0 * (0.5 + 0.3 * 0.5) = 1.0 * 0.65 = 0.65
        mock_sleep.assert_called_once()
        # 验证延迟时间在抖动范围内
        delay = mock_sleep.call_args[0][0]
        assert 0.5 <= delay <= 1.0

    def test_retry_callback_function(self):
        """测试重试回调函数"""
        callback_calls = []
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])
        config = RetryConfig(max_attempts=3)

        def retry_callback(attempt, error):
            callback_calls.append((attempt, str(error)))

        @retry(config, on_retry=retry_callback)
        def test_function():
            return mock_func()

        result = test_function()
        assert result == "success"
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # 第一次重试
        assert "error" in callback_calls[0][1]

    @pytest.mark.asyncio
    async def test_async_retry_success_on_first_attempt(self):
        """测试异步函数第一次尝试就成功"""
        mock_func = MagicMock(return_value="success")
        config = RetryConfig(max_attempts=3)

        @retry(config)
        async def async_test_function():
            return mock_func()

        result = await async_test_function()
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """测试异步函数几次失败后成功"""
        mock_func = MagicMock(side_effect=[Exception("error"), Exception("error"), "success"])
        config = RetryConfig(max_attempts=3)

        @retry(config)
        async def async_test_function():
            return mock_func()

        result = await async_test_function()
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_async_retry_delay_calculation(self, mock_sleep):
        """测试异步重试延迟计算"""
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )

        @retry(config)
        async def async_test_function():
            return mock_func()

        result = await async_test_function()
        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    async def test_async_retry_max_attempts_reached(self):
        """测试异步函数达到最大重试次数"""
        mock_func = MagicMock(side_effect=Exception("persistent error"))
        config = RetryConfig(max_attempts=2)

        @retry(config)
        async def async_test_function():
            return mock_func()

        with pytest.raises(Exception, match="persistent error"):
            await async_test_function()

        assert mock_func.call_count == 2


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        cb = CircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60.0
        assert cb.retry_timeout == 30.0
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_custom_config(self):
        """测试熔断器自定义配置"""
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
            retry_timeout=15.0
        )

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30.0
        assert cb.retry_timeout == 15.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_call(self):
        """测试熔断器成功调用"""
        cb = CircuitBreaker()
        mock_func = MagicMock(return_value="success")

        result = await cb.call(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_counting(self):
        """测试熔断器失败计数"""
        cb = CircuitBreaker(failure_threshold=3)
        mock_func = MagicMock(side_effect=Exception("error"))

        # 连续失败2次，但未达到阈值
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(mock_func)

        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

        # 第三次失败，应该打开熔断器
        with pytest.raises(Exception):
            await cb.call(mock_func)

        assert cb.failure_count == 3
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_calls(self):
        """测试熔断器打开状态阻止调用"""
        cb = CircuitBreaker(failure_threshold=2)
        mock_func = MagicMock(side_effect=Exception("error"))

        # 让熔断器打开
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(mock_func)

        assert cb.state == CircuitState.OPEN

        # 尝试再次调用，应该立即被拒绝
        mock_func.reset_mock()
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await cb.call(mock_func)

        assert mock_func.call_count == 0  # 函数不应该被调用

    @pytest.mark.asyncio
    @patch('time.time')
    async def test_circuit_breaker_recovery_after_timeout(self, mock_time):
        """测试熔断器超时后恢复"""
        mock_time.side_effect = [0, 0, 0, 0, 70]  # 模拟时间流逝
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60.0
        )
        mock_func = MagicMock(side_effect=Exception("error"))

        # 让熔断器打开
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(mock_func)

        assert cb.state == CircuitState.OPEN

        # 模拟时间已过恢复超时
        mock_func.side_effect = Exception("still failing")
        with pytest.raises(Exception):
            await cb.call(mock_func)

        # 应该尝试恢复，状态变为半开
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    @patch('time.time')
    async def test_circuit_breaker_successful_recovery(self, mock_time):
        """测试熔断器成功恢复"""
        mock_time.side_effect = [0, 0, 0, 0, 70]  # 模拟时间流逝
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60.0
        )
        mock_func = MagicMock(side_effect=[Exception("error"), Exception("error"), "success"])

        # 让熔断器打开
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(mock_func)

        assert cb.state == CircuitState.OPEN

        # 模拟时间已过恢复超时，且函数调用成功
        result = await cb.call(mock_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_function_args(self):
        """测试熔断器带函数参数的调用"""
        cb = CircuitBreaker()
        mock_func = MagicMock(return_value="result")

        result = await cb.call(mock_func, "arg1", "arg2", kwarg1="value1")
        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")

    def test_circuit_breaker_should_attempt_reset(self):
        """测试熔断器重置判断逻辑"""
        cb = CircuitBreaker(recovery_timeout=60.0)

        # 没有失败历史
        assert cb._should_attempt_reset() is False

        # 有失败历史但未超时
        cb.last_failure_time = time.time() - 30  # 30秒前
        assert cb._should_attempt_reset() is False

        # 有失败历史且已超时
        cb.last_failure_time = time.time() - 90  # 90秒前
        assert cb._should_attempt_reset() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_retry_timeout(self):
        """测试熔断器半开状态的重试超时"""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60.0,
            retry_timeout=30.0
        )

        # 设置为半开状态
        cb.state = CircuitState.HALF_OPEN
        cb.last_failure_time = time.time() - 45  # 45秒前

        # 应该使用重试超时而不是恢复超时
        assert cb._should_attempt_reset() is True

    # Integration tests
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker_integration(self):
        """测试重试与熔断器集成"""
        cb = CircuitBreaker(failure_threshold=3)
        config = RetryConfig(max_attempts=2)

        @retry(config)
        async def failing_function():
            raise Exception("Service unavailable")

        # 使用熔断器调用重试函数
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_function)

        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

        # 第三次调用应该打开熔断器
        with pytest.raises(Exception):
            await cb.call(failing_function)

        assert cb.state == CircuitState.OPEN

    def test_circuit_state_enum_values(self):
        """测试熔断器状态枚举值"""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"