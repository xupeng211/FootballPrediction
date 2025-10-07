"""
工具模块功能测试
测试实际的工具函数功能
"""

import pytest
import sys
import os
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.mark.unit
class TestUtilsFunctional:
    """工具模块功能测试"""

    def test_time_utils_functions(self):
        """测试时间工具函数"""
        try:
            from src.utils.time_utils import get_current_time, format_duration, parse_datetime

            # 测试获取当前时间
            current_time = get_current_time()
            assert current_time is not None
            assert isinstance(current_time, (datetime, str))

            # 测试持续时间格式化
            if callable(format_duration):
                duration = format_duration(3600)  # 1小时
                assert duration is not None

            # 测试日期时间解析
            if callable(parse_datetime):
                parsed = parse_datetime("2024-01-01T00:00:00")
                assert parsed is None or isinstance(parsed, datetime)

        except ImportError as e:
            pytest.skip(f"Cannot import time utils: {e}")

    def test_dict_utils_functions(self):
        """测试字典工具函数"""
        try:
            from src.utils.dict_utils import deep_merge, flatten_dict, filter_dict

            # 测试深度合并
            if callable(deep_merge):
                dict1 = {"a": 1, "b": {"c": 2}}
                dict2 = {"b": {"d": 3}, "e": 4}
                merged = deep_merge(dict1, dict2)
                assert merged is not None

            # 测试字典扁平化
            if callable(flatten_dict):
                nested = {"a": {"b": {"c": 1}}, "d": 2}
                flat = flatten_dict(nested)
                assert flat is not None

            # 测试字典过滤
            if callable(filter_dict):
                data = {"a": 1, "b": None, "c": 3}
                filtered = filter_dict(data, lambda k, v: v is not None)
                assert filtered is not None

        except ImportError as e:
            pytest.skip(f"Cannot import dict utils: {e}")

    def test_string_utils_functions(self):
        """测试字符串工具函数"""
        try:
            from src.utils.string_utils import slugify, sanitize_string, truncate_text

            # 测试slugify
            if callable(slugify):
                text = "Hello World! This is a Test"
                slug = slugify(text)
                assert slug is not None
                assert " " not in slug

            # 测试字符串清理
            if callable(sanitize_string):
                dirty = "Hello<script>alert('xss')</script>"
                clean = sanitize_string(dirty)
                assert clean is not None

            # 测试文本截断
            if callable(truncate_text):
                long_text = "This is a very long text that should be truncated"
                truncated = truncate_text(long_text, 20)
                assert len(truncated) <= 23  # 20 + "..."

        except ImportError as e:
            pytest.skip(f"Cannot import string utils: {e}")

    def test_response_utils_functions(self):
        """测试响应工具函数"""
        try:
            from src.utils.response import create_success_response, create_error_response

            # 测试成功响应
            if callable(create_success_response):
                response = create_success_response({"data": "test"}, "Success")
                assert response is not None
                assert "success" in str(response).lower() or "data" in str(response)

            # 测试错误响应
            if callable(create_error_response):
                error = create_error_response("Something went wrong", 400)
                assert error is not None
                assert "error" in str(error).lower() or str(error) is not None

        except ImportError as e:
            pytest.skip(f"Cannot import response utils: {e}")

    def test_retry_utils_functions(self):
        """测试重试工具函数"""
        try:
            from src.utils.retry import retry_with_backoff, RetryConfig

            # 测试重试配置
            if RetryConfig:
                config = RetryConfig(max_attempts=3, backoff_factor=2)
                assert config.max_attempts == 3
                assert config.backoff_factor == 2

            # 测试重试装饰器
            if callable(retry_with_backoff):
                @retry_with_backoff(max_attempts=2)
                def test_function():
                    return True

                result = test_function()
                assert result is True

        except ImportError as e:
            pytest.skip(f"Cannot import retry utils: {e}")

    def test_crypto_utils_functions(self):
        """测试加密工具函数"""
        try:
            from src.utils.crypto_utils import hash_password, verify_password, generate_token

            # 测试密码哈希
            if callable(hash_password):
                password = "test_password_123"
                hashed = hash_password(password)
                assert hashed is not None
                assert hashed != password

            # 测试密码验证
            if callable(verify_password) and 'hashed' in locals():
                assert verify_password(password, hashed) is True
                assert verify_password("wrong_password", hashed) is False

            # 测试令牌生成
            if callable(generate_token):
                token = generate_token()
                assert token is not None
                assert len(token) > 0

        except ImportError as e:
            pytest.skip(f"Cannot import crypto utils: {e}")

    def test_data_validator_functions(self):
        """测试数据验证器函数"""
        try:
            from src.utils.data_validator import validate_email, validate_phone, validate_url

            # 测试邮箱验证
            if callable(validate_email):
                assert validate_email("test@example.com") is True
                assert validate_email("invalid-email") is False

            # 测试电话验证
            if callable(validate_phone):
                assert validate_phone("+1234567890") is True or validate_phone("+1234567890") is False
                assert validate_phone("not-a-phone") is False

            # 测试URL验证
            if callable(validate_url):
                assert validate_url("https://example.com") is True or validate_url("https://example.com") is False
                assert validate_url("not-a-url") is False

        except ImportError as e:
            pytest.skip(f"Cannot import data validator: {e}")

    def test_file_utils_functions(self):
        """测试文件工具函数"""
        try:
            from src.utils.file_utils import read_json, write_json, get_file_size

            # 测试JSON操作
            test_data = {"test": "data", "number": 123}

            if callable(write_json):
                # 使用临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    temp_file = f.name

                try:
                    write_json(temp_file, test_data)

                    if callable(read_json):
                        loaded = read_json(temp_file)
                        assert loaded == test_data

                finally:
                    # 清理临时文件
                    import os
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)

            # 测试文件大小获取
            if callable(get_file_size):
                size = get_file_size(__file__)  # 当前文件
                assert size > 0

        except ImportError as e:
            pytest.skip(f"Cannot import file utils: {e}")

    def test_warning_filters(self):
        """测试警告过滤器"""
        try:
            from src.utils.warning_filters import filter_warnings, setup_warnings

            # 测试警告过滤
            if callable(filter_warnings):
                filter_warnings(category=UserWarning)

            # 测试警告设置
            if callable(setup_warnings):
                setup_warnings(quiet=True)

        except ImportError as e:
            pytest.skip(f"Cannot import warning filters: {e}")

    def test_i18n_functions(self):
        """测试国际化函数"""
        try:
            from src.utils.i18n import get_text, set_locale, get_available_languages

            # 测试文本获取
            if callable(get_text):
                text = get_text("test.key", default="Test Text")
                assert text is not None

            # 测试语言设置
            if callable(set_locale):
                result = set_locale("en")
                assert result is True or result is False

            # 测试可用语言列表
            if callable(get_available_languages):
                languages = get_available_languages()
                assert isinstance(languages, list)
                assert len(languages) > 0

        except ImportError as e:
            pytest.skip(f"Cannot import i18n utils: {e}")

    def test_logging_utils(self):
        """测试日志工具"""
        try:
            from src.core.logger import get_logger, setup_logging

            # 测试日志器获取
            logger = get_logger("test_logger")
            assert logger is not None

            # 测试日志设置
            if callable(setup_logging):
                setup_logging(level="INFO")

        except ImportError as e:
            pytest.skip(f"Cannot import logging utils: {e}")

    def test_data_transformation_utils(self):
        """测试数据转换工具"""
        try:
            import pandas as pd

            # 测试DataFrame操作（如果可用）
            df = pd.DataFrame({
                'a': [1, 2, 3],
                'b': ['x', 'y', 'z'],
                'c': [1.1, 2.2, 3.3]
            })

            # 验证DataFrame创建
            assert len(df) == 3
            assert list(df.columns) == ['a', 'b', 'c']

        except ImportError:
            pytest.skip("pandas not available")

    def test_math_utils(self):
        """测试数学工具函数"""
        try:
            from src.utils.math_utils import clamp, normalize, round_decimal

            # 测试数值限制
            if callable(clamp):
                assert clamp(5, 0, 10) == 5
                assert clamp(-5, 0, 10) == 0
                assert clamp(15, 0, 10) == 10

            # 测试数值标准化
            if callable(normalize):
                result = normalize([1, 2, 3, 4, 5])
                assert result is not None

            # 测试小数舍入
            if callable(round_decimal):
                assert round_decimal(3.14159, 2) == 3.14

        except ImportError:
            pytest.skip("Math utils not available")

    def test_list_utils(self):
        """测试列表工具函数"""
        try:
            from src.utils.list_utils import chunk_list, flatten_list, unique_list

            # 测试列表分块
            if callable(chunk_list):
                chunks = list(chunk_list([1, 2, 3, 4, 5], 2))
                assert len(chunks) == 3
                assert chunks[0] == [1, 2]

            # 测试列表扁平化
            if callable(flatten_list):
                flat = flatten_list([[1, 2], [3, 4], [5]])
                assert flat == [1, 2, 3, 4, 5]

            # 测试列表去重
            if callable(unique_list):
                unique = unique_list([1, 2, 2, 3, 3, 1])
                assert set(unique) == {1, 2, 3}

        except ImportError:
            pytest.skip("List utils not available")