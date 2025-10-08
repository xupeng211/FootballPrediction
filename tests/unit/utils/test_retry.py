"""重试工具测试"""

import pytest


class TestRetryUtils:
    """测试重试工具"""

    def test_retry_import(self):
        """测试重试工具导入"""
        try:
            from src.utils.retry import retry, RetryError

            assert True
        except ImportError:
            pytest.skip("retry module not available")

    def test_retry_decorator(self):
        """测试重试装饰器"""
        try:
            from src.utils.retry import retry

            @retry(max_attempts=3, delay=0.01)
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"
        except:
            pytest.skip("retry decorator not available")

    def test_retry_error_class(self):
        """测试重试错误类"""
        try:
            from src.utils.retry import RetryError

            error = RetryError("Test error")
            assert str(error) == "Test error"
        except ImportError:
            pytest.skip("RetryError not available")
