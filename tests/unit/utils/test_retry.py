"""重试工具测试"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from time import sleep
from datetime import datetime, timedelta


class RetryError(Exception):
    """重试错误类"""

    pass


def retry(max_attempts=3, delay=0.1, backoff=1.0, exceptions=(Exception,)):
    """重试装饰器"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise RetryError(f"Failed after {max_attempts} attempts") from e

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

        def sync_wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise RetryError(f"Failed after {max_attempts} attempts") from e

                    sleep(current_delay)
                    current_delay *= backoff

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class TestRetryUtils:
    """测试重试工具"""

    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """测试第一次尝试就成功"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        _result = await test_function()

        assert _result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_attempts(self):
        """测试失败几次后成功"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        _result = await test_function()

        assert _result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_failure_after_max_attempts(self):
        """测试达到最大重试次数后失败"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            await test_function()

        assert "Failed after 3 attempts" in str(exc_info.value)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        """测试指数退避"""
        call_count = 0
        start_time = datetime.utcnow()

        @retry(max_attempts=3, delay=0.01, backoff=2.0)
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        await test_function()

        end_time = datetime.utcnow()
        elapsed = (end_time - start_time).total_seconds()

        # 验证延迟时间（0.01 + 0.02 = 至少0.03秒）
        assert elapsed >= 0.03
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """测试只重试特定异常"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise TypeError("Don't retry this")

        # TypeError不应该被重试
        with pytest.raises(TypeError):
            await test_function()

        assert call_count == 2

    def test_sync_retry_success(self):
        """测试同步函数重试成功"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        _result = test_function()

        assert _result == "success"
        assert call_count == 2

    def test_sync_retry_failure(self):
        """测试同步函数重试失败"""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            test_function()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_error_message(self):
        """测试重试错误消息"""

        @retry(max_attempts=2, delay=0.01)
        async def test_function():
            raise ConnectionError("Network error")

        with pytest.raises(RetryError) as exc_info:
            await test_function()

        assert exc_info.value.__cause__.__class__ is ConnectionError
        assert str(exc_info.value.__cause__) == "Network error"

    @pytest.mark.asyncio
    async def test_retry_zero_attempts(self):
        """测试零次重试"""

        @retry(max_attempts=1, delay=0.01)
        async def test_function():
            raise ValueError("Always fails")

        with pytest.raises(RetryError):
            await test_function()

    @pytest.mark.asyncio
    async def test_retry_with_custom_delay(self):
        """测试自定义延迟"""
        call_times = []

        @retry(max_attempts=3, delay=0.05)
        async def test_function():
            call_times.append(datetime.utcnow())
            if len(call_times) < 3:
                raise ValueError("Temporary failure")

        await test_function()

        # 验证间隔
        interval1 = (call_times[1] - call_times[0]).total_seconds()
        interval2 = (call_times[2] - call_times[1]).total_seconds()

        assert interval1 >= 0.04  # 允许一些时间误差
        assert interval2 >= 0.04

    @pytest.mark.asyncio
    async def test_retry_preserves_function_attributes(self):
        """测试重试装饰器保留函数属性"""

        @retry(max_attempts=3, delay=0.01)
        async def test_function():
            """测试函数文档"""
            return "success"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "测试函数文档"

    @pytest.mark.asyncio
    async def test_retry_with_multiple_exception_types(self):
        """测试多种异常类型的重试"""
        call_count = 0

        @retry(max_attempts=4, delay=0.01, exceptions=(ValueError, TypeError))
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise TypeError("Second error")
            elif call_count == 3:
                raise RuntimeError("Don't retry")

        # RuntimeError不应该被重试
        with pytest.raises(RuntimeError):
            await test_function()

        assert call_count == 3
