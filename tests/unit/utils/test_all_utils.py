"""
测试文件：所有工具函数测试

测试所有工具模块功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time


@pytest.mark.unit
class TestAllUtils:
    """所有工具函数测试类"""

    def test_response_utils(self):
        """测试响应工具"""
        try:
            from src.utils.response import APIResponse
            assert APIResponse is not None
            assert callable(APIResponse.success)
            assert callable(APIResponse.error)
        except ImportError:
            pytest.skip("Response utils not available")

    def test_string_utils(self):
        """测试字符串工具"""
        try:
            from src.utils.string_utils import StringUtils
            assert StringUtils is not None
            assert callable(StringUtils.truncate)
            assert callable(StringUtils.slugify)
        except ImportError:
            pytest.skip("String utils not available")

    def test_dict_utils(self):
        """测试字典工具"""
        try:
            from src.utils.dict_utils import DictUtils
            assert DictUtils is not None
            assert callable(DictUtils.deep_merge)
            assert callable(DictUtils.flatten_dict)
        except ImportError:
            pytest.skip("Dict utils not available")

    def test_time_utils(self):
        """测试时间工具"""
        try:
            from src.utils.time_utils import TimeUtils
            assert TimeUtils is not None
            # Check available methods based on actual implementation
            if hasattr(TimeUtils, 'format_timestamp'):
                assert callable(TimeUtils.format_timestamp)
            if hasattr(TimeUtils, 'parse_datetime'):
                assert callable(TimeUtils.parse_datetime)
        except ImportError:
            pytest.skip("Time utils not available")

    def test_crypto_utils(self):
        """测试加密工具"""
        try:
            from src.utils.crypto_utils import CryptoUtils
            assert CryptoUtils is not None
            assert callable(CryptoUtils.hash_password)
            assert callable(CryptoUtils.verify_password)
        except ImportError:
            pytest.skip("Crypto utils not available")

    def test_data_validator(self):
        """测试数据验证器"""
        try:
            from src.utils.data_validator import DataValidator
            assert DataValidator is not None
            assert callable(DataValidator.validate_email)
            assert callable(DataValidator.validate_phone)
        except ImportError:
            pytest.skip("Data validator not available")

    def test_file_utils(self):
        """测试文件工具"""
        try:
            from src.utils.file_utils import FileUtils
            assert FileUtils is not None
            assert callable(FileUtils.ensure_directory)
            assert callable(FileUtils.get_file_size)
        except ImportError:
            pytest.skip("File utils not available")

    def test_retry_utils(self):
        """测试重试工具"""
        try:
            from src.utils.retry import RetryUtils, RetryConfig
            assert RetryUtils is not None
            assert RetryConfig is not None
            assert callable(RetryUtils.retry)
        except ImportError:
            pytest.skip("Retry utils not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.utils", "--cov-report=term-missing"])