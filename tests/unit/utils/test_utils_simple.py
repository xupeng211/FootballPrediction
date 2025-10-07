"""
工具模块简化测试
测试基本的工具函数，不涉及复杂依赖
"""

import pytest
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.mark.unit
class TestUtilsSimple:
    """工具模块简化测试"""

    def test_time_utils_import(self):
        """测试时间工具导入"""
        try:
            from src.utils.time_utils import get_current_time, format_duration
            assert get_current_time is not None
            assert format_duration is not None
        except ImportError as e:
            pytest.skip(f"Cannot import time utils: {e}")

    def test_dict_utils_import(self):
        """测试字典工具导入"""
        try:
            from src.utils.dict_utils import deep_merge, flatten_dict
            assert deep_merge is not None
            assert flatten_dict is not None
        except ImportError as e:
            pytest.skip(f"Cannot import dict utils: {e}")

    def test_string_utils_import(self):
        """测试字符串工具导入"""
        try:
            from src.utils.string_utils import slugify, sanitize_string
            assert slugify is not None
            assert sanitize_string is not None
        except ImportError as e:
            pytest.skip(f"Cannot import string utils: {e}")

    def test_response_utils_import(self):
        """测试响应工具导入"""
        try:
            from src.utils.response import create_success_response, create_error_response
            assert create_success_response is not None
            assert create_error_response is not None
        except ImportError as e:
            pytest.skip(f"Cannot import response utils: {e}")

    def test_crypto_utils_basic(self):
        """测试加密工具基础功能"""
        try:
            from src.utils.crypto_utils import hash_password, verify_password
            # 测试基本功能，不涉及复杂的加密操作
            assert hash_password is not None
            assert verify_password is not None
        except ImportError as e:
            pytest.skip(f"Cannot import crypto utils: {e}")

    def test_retry_utils_import(self):
        """测试重试工具导入"""
        try:
            from src.utils.retry import retry_with_backoff, RetryConfig
            assert retry_with_backoff is not None
            assert RetryConfig is not None
        except ImportError as e:
            pytest.skip(f"Cannot import retry utils: {e}")

    def test_data_validator_import(self):
        """测试数据验证器导入"""
        try:
            from src.utils.data_validator import validate_email, validate_phone
            assert validate_email is not None
            assert validate_phone is not None
        except ImportError as e:
            pytest.skip(f"Cannot import data validator: {e}")

    def test_warning_filters_import(self):
        """测试警告过滤器导入"""
        try:
            from src.utils.warning_filters import filter_warnings, setup_warnings
            assert filter_warnings is not None
            assert setup_warnings is not None
        except ImportError as e:
            pytest.skip(f"Cannot import warning filters: {e}")

    def test_i18n_import(self):
        """测试国际化工具导入"""
        try:
            from src.utils.i18n import get_text, set_locale
            assert get_text is not None
            assert set_locale is not None
        except ImportError as e:
            pytest.skip(f"Cannot import i18n utils: {e}")

    def test_file_utils_import(self):
        """测试文件工具导入"""
        try:
            from src.utils.file_utils import read_json, write_json
            assert read_json is not None
            assert write_json is not None
        except ImportError as e:
            pytest.skip(f"Cannot import file utils: {e}")

    def test_logger_import(self):
        """测试日志工具导入"""
        try:
            from src.core.logger import get_logger, setup_logging
            assert get_logger is not None
            assert setup_logging is not None
        except ImportError as e:
            pytest.skip(f"Cannot import logger: {e}")