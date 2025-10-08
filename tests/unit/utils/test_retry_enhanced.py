"""增强的重试功能测试"""

import asyncio
import time

import pytest

from src.utils.retry import RetryConfig, retry


class TestRetryEnhanced:
    """增强的重试功能测试"""

    def test_retry_config_attributes(self):
        """测试RetryConfig的所有属性"""
        config = RetryConfig(
            max_attempts=5,
            backoff_factor=2,
            max_delay=60,
            jitter=True,
            retryable_exceptions=(ValueError, KeyError),
        )

        assert config.max_attempts == 5
        assert config.backoff_factor == 2
        assert config.max_delay == 60
        assert config.jitter is True
        assert ValueError in config.retryable_exceptions
        assert KeyError in config.retryable_exceptions

    def test_retry_config_default(self):
        """测试RetryConfig默认值"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.backoff_factor == 2
        assert config.max_delay == 60
        assert config.jitter is False
        assert Exception in config.retryable_exceptions

    def test_retry_with_backoff_success(self):
        """测试重试后成功"""
        attempt_count = 0
        config = RetryConfig(max_attempts=3, base_delay=0.01)

        @retry(config)
        def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_with_backoff_failure(self):
        """测试重试后仍然失败"""

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

    def test_retry_with_specific_exception(self):
        """测试只重试特定异常"""

        @retry_with_backoff(
            max_attempts=3, retryable_exceptions=(ValueError,), base_delay=0.01
        )
        def function_with_different_errors():
            raise KeyError("Not retryable")

        with pytest.raises(KeyError):
            function_with_different_errors()

    def test_exponential_backoff(self):
        """测试指数退避"""
        delays = list(exponential_backoff(base=1, factor=2, max_delay=10, attempts=4))
        assert len(delays) == 4
        assert delays[0] == 1
        assert delays[1] == 2
        assert delays[2] == 4
        assert delays[3] == 8  # 没有超过max_delay

    def test_exponential_backoff_with_max_delay(self):
        """测试指数退避的最大延迟限制"""
        delays = list(exponential_backoff(base=1, factor=3, max_delay=5, attempts=5))
        assert delays[0] == 1
        assert delays[1] == 3
        assert delays[2] == 5  # 受max_delay限制
        assert delays[3] == 5  # 受max_delay限制
        assert delays[4] == 5  # 受max_delay限制

    def test_linear_backoff(self):
        """测试线性退避"""
        delays = list(linear_backoff(start=1, increment=2, max_delay=10, attempts=4))
        assert delays == [1, 3, 5, 7]

    def test_linear_backoff_with_max_delay(self):
        """测试线性退避的最大延迟限制"""
        delays = list(linear_backoff(start=5, increment=3, max_delay=10, attempts=4))
        assert delays == [5, 8, 10, 10]

    def test_retry_with_jitter(self):
        """测试带抖动的重试"""
        delays = []

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.1,
            jitter=True,
            delay_callback=lambda d: delays.append(d),
        )
        def test_function():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            test_function()

        assert len(delays) == 2  # 失败2次，产生2个延迟
        # 验证抖动：延迟应该略有不同
        assert delays[0] != delays[1] or abs(delays[0] - delays[1]) > 0.001

    def test_retry_timeout(self):
        """测试重试超时"""
        start_time = time.time()

        @retry_with_backoff(max_attempts=3, base_delay=0.1, timeout=0.2)
        def slow_function():
            time.sleep(0.15)
            raise ValueError("Timeout test")

        with pytest.raises(ValueError):
            slow_function()

        elapsed = time.time() - start_time
        assert elapsed < 0.3  # 应该在超时前停止

    @pytest.mark.asyncio
    async def test_async_retry_with_backoff(self):
        """测试异步函数的重试"""
        attempt_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def async_flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Async temporary failure")
            return "async success"

        result = await async_flaky_function()
        assert result == "async success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_timeout(self):
        """测试异步重试超时"""
        start_time = time.time()

        @retry_with_backoff(max_attempts=3, base_delay=0.1, timeout=0.2)
        async def async_slow_function():
            await asyncio.sleep(0.15)
            raise ValueError("Async timeout test")

        with pytest.raises(ValueError):
            await async_slow_function()

        elapsed = time.time() - start_time
        assert elapsed < 0.3

    def test_retry_with_callback(self):
        """测试带回调的重试"""
        callback_calls = []

        def attempt_callback(attempt, error, delay):
            callback_calls.append((attempt, str(error), delay))

        @retry_with_backoff(
            max_attempts=3, base_delay=0.01, attempt_callback=attempt_callback
        )
        def failing_function():
            raise ValueError("Attempt failed")

        with pytest.raises(ValueError):
            failing_function()

        assert len(callback_calls) == 2  # 3次尝试，前2次失败
        assert callback_calls[0][0] == 1  # 第一次尝试
        assert callback_calls[1][0] == 2  # 第二次尝试
        assert "Attempt failed" in callback_calls[0][1]

    def test_retry_with_delay_callback(self):
        """测试带延迟回调的重试"""
        delays = []

        def delay_callback(delay):
            delays.append(delay)

        @retry_with_backoff(
            max_attempts=3, base_delay=0.1, delay_callback=delay_callback
        )
        def failing_function():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            failing_function()

        assert len(delays) == 2
        assert all(d > 0 for d in delays)

    def test_retry_decorator_preserves_metadata(self):
        """测试重试装饰器保留函数元数据"""

        @retry_with_backoff(max_attempts=3)
        def example_function(param1, param2):
            """示例函数文档字符串"""
            return f"{param1}-{param2}"

        assert example_function.__name__ == "example_function"
        assert "示例函数文档字符串" in example_function.__doc__
        assert example_function("a", "b") == "a-b"

    def test_retry_config_validation(self):
        """测试RetryConfig参数验证"""
        # 测试负数
        with pytest.raises(ValueError):
            RetryConfig(max_attempts=-1)

        with pytest.raises(ValueError):
            RetryConfig(backoff_factor=-1)

        with pytest.raises(ValueError):
            RetryConfig(max_delay=-1)

    def test_retry_with_custom_retry_condition(self):
        """测试自定义重试条件"""

        def should_retry(error):
            return "retry" in str(error).lower()

        attempt_count = 0

        @retry_with_backoff(
            max_attempts=3, base_delay=0.01, retry_condition=should_retry
        )
        def conditional_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ValueError("Should retry this")
            elif attempt_count == 2:
                raise ValueError("Don't retry")
            return "success"

        with pytest.raises(ValueError, match="Don't retry"):
            conditional_function()

        assert attempt_count == 2

    def test_retry_statistics(self):
        """测试重试统计功能"""
        stats = {"attempts": 0, "delays": []}

        def collect_stats(attempt, error, delay):
            stats["attempts"] = attempt
            stats["delays"].append(delay)

        @retry_with_backoff(
            max_attempts=3, base_delay=0.1, attempt_callback=collect_stats
        )
        def stats_function():
            raise ValueError("Stats test")

        with pytest.raises(ValueError):
            stats_function()

        assert stats["attempts"] == 2
        assert len(stats["delays"]) == 2
        assert stats["delays"][0] == 0.1
        assert stats["delays"][1] == 0.2  # 指数退避

    def test_retry_with_different_strategies(self):
        """测试不同的退避策略"""
        # 指数退避
        exponential_delays = []

        @retry_with_backoff(
            max_attempts=4,
            base_delay=0.01,
            strategy="exponential",
            delay_callback=lambda d: exponential_delays.append(d),
        )
        def exponential_retry():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            exponential_retry()

        # 线性退避
        linear_delays = []

        @retry_with_backoff(
            max_attempts=4,
            base_delay=0.01,
            strategy="linear",
            delay_callback=lambda d: linear_delays.append(d),
        )
        def linear_retry():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            linear_retry()

        # 验证不同的模式
        assert exponential_delays != linear_delays
        assert len(exponential_delays) == 3
        assert len(linear_delays) == 3
