"""重试功能测试（实际可用功能）"""

import pytest
# from src.utils.retry import RetryConfig, retry


class TestRetryActual:
    """重试功能测试（实际可用功能）"""

    def test_retry_config_creation(self):
        """测试RetryConfig创建"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.1,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(ValueError, KeyError),
        )

        assert config.max_attempts == 5
        assert config.base_delay == 0.1
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ValueError in config.retryable_exceptions
        assert KeyError in config.retryable_exceptions

    def test_retry_config_defaults(self):
        """测试RetryConfig默认值"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is False
        assert Exception in config.retryable_exceptions

    def test_retry_decorator_success(self):
        """测试重试装饰器（成功）"""

        @retry(RetryConfig(max_attempts=3))
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

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

        result = flaky_function()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_decorator_all_fail(self):
        """测试重试装饰器（全部失败）"""

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def always_failing_function():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

    def test_retry_with_specific_exception(self):
        """测试特定异常重试"""

        @retry(
            RetryConfig(
                max_attempts=3, base_delay=0.01, retryable_exceptions=(ValueError,)
            )
        )
        def function_with_key_error():
            raise KeyError("Not retryable")

        with pytest.raises(KeyError, match="Not retryable"):
            function_with_key_error()

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """测试异步重试成功"""

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def async_successful_function():
            return "async success"

        result = await async_successful_function()
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_async_retry_eventual_success(self):
        """测试异步重试最终成功"""
        attempt_count = 0

        @retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def async_flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Async temporary failure")
            return "async success"

        result = await async_flaky_function()
        assert result == "async success"
        assert attempt_count == 3

    def test_retry_preserves_metadata(self):
        """测试重试保留元数据"""

        @retry(RetryConfig(max_attempts=3))
        def example_function(param1, param2):
            """示例函数文档字符串"""
            return f"{param1}-{param2}"

        assert example_function.__name__ == "example_function"
        assert "示例函数文档字符串" in example_function.__doc__
        assert example_function("a", "b") == "a-b"
