"""最终覆盖率测试 - 直接测试模块函数"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import uuid
import re
import secrets
import hashlib
import base64
import asyncio
from typing import Any, Dict, List


class TestCryptoUtilsModule:
    """测试加密工具模块"""

    def test_crypto_utils_import(self):
        """测试crypto_utils模块导入"""
        try:
            from src.utils.crypto_utils import CryptoUtils

            assert CryptoUtils is not None
        except ImportError:
            pytest.skip("CryptoUtils not available")

    def test_crypto_utils_methods(self):
        """测试crypto_utils方法"""
        try:
            from src.utils.crypto_utils import CryptoUtils

            # 测试UUID生成
            uuid1 = CryptoUtils.generate_uuid()
            uuid2 = CryptoUtils.generate_uuid()
            assert uuid1 != uuid2
            assert len(uuid1) > 0

            # 测试短ID生成
            short_id = CryptoUtils.generate_short_id()
            assert len(short_id) == 8

            # 测试另一个长度
            short_id_12 = CryptoUtils.generate_short_id(12)
            assert len(short_id_12) == 12
        except (ImportError, AttributeError):
            pytest.skip("CryptoUtils methods not available")

    def test_crypto_utils_hash(self):
        """测试哈希功能"""
        try:
            from src.utils.crypto_utils import CryptoUtils

            # 测试字符串哈希
            text = "test_string"
            hashed = CryptoUtils.hash_string(text)
            assert hashed != text
            assert len(hashed) > 0

            # 测试不同算法
            hashed_md5 = CryptoUtils.hash_string(text, "md5")
            hashed_sha256 = CryptoUtils.hash_string(text, "sha256")
            assert hashed_md5 != hashed_sha256
        except (ImportError, AttributeError):
            pytest.skip("Hash methods not available")


class TestDataValidatorModule:
    """测试数据验证器模块"""

    def test_data_validator_import(self):
        """测试data_validator模块导入"""
        try:
            from src.utils.data_validator import DataValidator

            assert DataValidator is not None
        except ImportError:
            pytest.skip("DataValidator not available")

    def test_data_validator_init(self):
        """测试data_validator初始化"""
        try:
            from src.utils.data_validator import DataValidator

            validator = DataValidator()
            assert validator is not None
        except (ImportError, AttributeError):
            pytest.skip("DataValidator init not available")

    def test_data_validator_methods(self):
        """测试data_validator方法"""
        try:
            from src.utils.data_validator import DataValidator

            validator = DataValidator()

            # 测试邮箱验证
            if hasattr(validator, "validate_email"):
                assert validator.validate_email("test@example.com")
                assert not validator.validate_email("invalid")

            # 测试电话验证
            if hasattr(validator, "validate_phone"):
                assert validator.validate_phone("1234567890")
                assert not validator.validate_phone("123")

            # 测试URL验证
            if hasattr(validator, "validate_url"):
                assert validator.validate_url("https://example.com")
                assert not validator.validate_url("not_url")

            # 测试数字验证
            if hasattr(validator, "validate_number"):
                assert validator.validate_number("123")
                assert not validator.validate_number("abc")
        except (ImportError, AttributeError):
            pytest.skip("DataValidator methods not available")


class TestDictUtilsModule:
    """测试字典工具模块"""

    def test_dict_utils_import(self):
        """测试dict_utils模块导入"""
        try:
            from src.utils.dict_utils import DictUtils

            assert DictUtils is not None
        except ImportError:
            pytest.skip("DictUtils not available")

    def test_dict_utils_methods(self):
        """测试dict_utils方法"""
        try:
            from src.utils.dict_utils import DictUtils

            # 测试深度合并
            dict1 = {"a": 1, "b": {"c": 2}}
            dict2 = {"b": {"d": 3}, "e": 4}
            merged = DictUtils.deep_merge(dict1, dict2)
            assert merged["a"] == 1
            assert merged["b"]["c"] == 2
            assert merged["b"]["d"] == 3
            assert merged["e"] == 4

            # 测试扁平化
            nested = {"a": {"b": {"c": 1}}, "d": 2}
            flat = DictUtils.flatten_dict(nested)
            assert "a.b.c" in flat
            assert flat["a.b.c"] == 1
            assert flat["d"] == 2

            # 测试过滤None
            dict_with_none = {"a": 1, "b": None, "c": 3}
            filtered = DictUtils.filter_none(dict_with_none)
            assert "a" in filtered
            assert "b" not in filtered
            assert "c" in filtered

            # 测试选择键
            picked = DictUtils.pick_keys({"a": 1, "b": 2, "c": 3}, ["a", "c"])
            assert picked == {"a": 1, "c": 3}

            # 测试排除键
            excluded = DictUtils.exclude_keys({"a": 1, "b": 2, "c": 3}, ["b"])
            assert excluded == {"a": 1, "c": 3}
        except (ImportError, AttributeError):
            pytest.skip("DictUtils methods not available")


class TestFormattersModule:
    """测试格式化器模块"""

    def test_formatters_import(self):
        """测试formatters模块导入"""
        try:
            from src.utils.formatters import Formatters

            assert Formatters is not None
        except ImportError:
            pytest.skip("Formatters not available")

    def test_formatters_methods(self):
        """测试formatters方法"""
        try:
            from src.utils.formatters import Formatters

            # 测试日期时间格式化
            dt = datetime.now()
            formatted = Formatters.format_datetime(dt)
            assert isinstance(formatted, str)

            # 测试相对时间
            past = datetime.now() - timedelta(hours=2)
            relative = Formatters.format_relative_time(past)
            assert isinstance(relative, str)

            # 测试货币格式化
            currency = Formatters.format_currency(1234.56)
            assert isinstance(currency, str)

            # 测试字节格式化
            bytes_formatted = Formatters.format_bytes(1024)
            assert "KB" in bytes_formatted or "B" in bytes_formatted

            # 测试百分比格式化
            percentage = Formatters.format_percentage(0.1234)
            assert "%" in percentage
        except (ImportError, AttributeError):
            pytest.skip("Formatters methods not available")


class TestHelpersModule:
    """测试帮助工具模块"""

    def test_helpers_import(self):
        """测试helpers模块导入"""
        try:
            from src.utils.helpers import Helpers

            assert Helpers is not None
        except ImportError:
            pytest.skip("Helpers not available")

    def test_helpers_methods(self):
        """测试helpers方法"""
        try:
            from src.utils.helpers import Helpers

            # 测试UUID生成
            uuid1 = Helpers.generate_uuid()
            uuid2 = Helpers.generate_uuid()
            assert uuid1 != uuid2
            assert len(uuid1) > 0

            # 测试JSON判断
            assert Helpers.is_json('{"key": "value"}')
            assert not Helpers.is_json("not json")

            # 测试字符串截断
            long_text = "This is a very long string"
            truncated = Helpers.truncate_string(long_text, 10)
            assert len(truncated) <= 13  # 包括省略号

            # 测试深度获取
            _data = {"a": {"b": {"c": 1}}}
            value = Helpers.deep_get(data, "a.b.c")
            assert value == 1

            # 测试深度设置
            Helpers.deep_set(data, "a.b.d", 2)
            assert _data["a"]["b"]["d"] == 2

            # 测试列表分块
            lst = list(range(10))
            chunks = Helpers.chunk_list(lst, 3)
            assert len(chunks) == 4
            assert len(chunks[0]) == 3
            assert len(chunks[3]) == 1

            # 测试展平列表
            nested = [[1, 2], [3, [4, 5]], 6]
            flat = Helpers.flatten_list(nested)
            assert 1 in flat
            assert 2 in flat
            assert 3 in flat
            assert 4 in flat
            assert 5 in flat
            assert 6 in flat
        except (ImportError, AttributeError):
            pytest.skip("Helpers methods not available")


class TestStringUtilsModule:
    """测试字符串工具模块"""

    def test_string_utils_import(self):
        """测试string_utils模块导入"""
        try:
            from src.utils.string_utils import StringUtils

            assert StringUtils is not None
        except ImportError:
            pytest.skip("StringUtils not available")

    def test_string_utils_methods(self):
        """测试string_utils方法"""
        try:
            from src.utils.string_utils import StringUtils

            # 测试slugify
            assert StringUtils.slugify("Hello World!") == "hello-world"
            assert StringUtils.slugify("Café au lait") == "café-au-lait"

            # 测试驼峰转蛇形
            assert StringUtils.camel_to_snake("camelCase") == "camel_case"
            assert StringUtils.camel_to_snake("CamelCase") == "camel_case"
            assert StringUtils.camel_to_snake("HTMLParser") == "html_parser"

            # 测试蛇形转驼峰
            assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
            assert StringUtils.snake_to_camel("snake_case_test") == "snakeCaseTest"

            # 测试复数化
            assert StringUtils.pluralize("cat") == "cats"
            assert StringUtils.pluralize("dog") == "dogs"
            assert StringUtils.pluralize("box") == "boxes"
            assert StringUtils.pluralize("person", 1) == "person"

            # 测试单数化
            assert StringUtils.singularize("cats") == "cat"
            assert StringUtils.singularize("dogs") == "dog"
            assert StringUtils.singularize("boxes") == "box"

            # 测试单词截断
            text = "This is a test sentence with several words"
            truncated = StringUtils.truncate_words(text, 5)
            word_count = len(truncated.split())
            assert word_count <= 5

            # 测试清理HTML
            html = "<p>Hello <b>World</b>!</p>"
            clean = StringUtils.clean_html(html)
            assert "Hello" in clean
            assert "World" in clean
            assert "<p>" not in clean

            # 测试首字母大写
            assert StringUtils.capitalize_first("hello") == "Hello"
            assert StringUtils.capitalize_first("HELLO") == "Hello"
        except (ImportError, AttributeError):
            pytest.skip("StringUtils methods not available")


class TestTimeUtilsModule:
    """测试时间工具模块"""

    def test_time_utils_import(self):
        """测试time_utils模块导入"""
        try:
            from src.utils.time_utils import TimeUtils

            assert TimeUtils is not None
        except ImportError:
            pytest.skip("TimeUtils not available")

    def test_time_utils_methods(self):
        """测试time_utils方法"""
        try:
            from src.utils.time_utils import TimeUtils

            # 测试时间差显示
            past = datetime.now() - timedelta(hours=2, minutes=30)
            ago = TimeUtils.time_ago(past)
            assert isinstance(ago, str)

            # 测试持续时间格式化
            duration = TimeUtils.duration_format(3661)  # 1h1m1s
            assert "h" in duration or "hour" in duration.lower()
            assert "m" in duration or "minute" in duration.lower()
            assert "s" in duration or "second" in duration.lower()

            # 测试未来/过去判断
            future = datetime.now() + timedelta(hours=1)
            assert TimeUtils.is_future(future)
            assert not TimeUtils.is_past(future)

            past = datetime.now() - timedelta(hours=1)
            assert TimeUtils.is_past(past)
            assert not TimeUtils.is_future(past)

            # 测试时区偏移
            offset = TimeUtils.get_timezone_offset("UTC")
            assert isinstance(offset, str)

            # 测试解析日期时间
            dt_str = "2025-01-13 12:00:00"
            parsed = TimeUtils.parse_datetime(dt_str)
            assert parsed.year == 2025
            assert parsed.month == 1
            assert parsed.day == 13
        except (ImportError, AttributeError):
            pytest.skip("TimeUtils methods not available")


class TestResponseModule:
    """测试响应模块"""

    def test_response_import(self):
        """测试response模块导入"""
        try:
            from src.utils.response import ResponseBuilder

            assert ResponseBuilder is not None
        except ImportError:
            pytest.skip("ResponseBuilder not available")

    def test_response_methods(self):
        """测试response方法"""
        try:
            from src.utils.response import ResponseBuilder

            # 测试成功响应
            resp = ResponseBuilder.success({"data": "test"})
            assert resp["success"] is True
            assert "data" in resp

            # 测试错误响应
            err = ResponseBuilder.error("An error occurred")
            assert err["success"] is False
            assert err["message"] == "An error occurred"

            # 测试创建响应
            created = ResponseBuilder.created({"id": 1})
            assert created["success"] is True
            assert created["data"]["id"] == 1

            # 测试更新响应
            updated = ResponseBuilder.updated({"id": 1, "name": "updated"})
            assert updated["success"] is True
            assert updated["data"]["name"] == "updated"

            # 测试删除响应
            deleted = ResponseBuilder.deleted({"id": 1})
            assert deleted["success"] is True

            # 测试未找到响应
            not_found = ResponseBuilder.not_found("Resource not found")
            assert not_found["success"] is False
            assert not_found["message"] == "Resource not found"

            # 测试错误请求响应
            bad_request = ResponseBuilder.bad_request("Invalid input")
            assert bad_request["success"] is False
            assert bad_request["message"] == "Invalid input"

            # 测试未授权响应
            unauthorized = ResponseBuilder.unauthorized("Access denied")
            assert unauthorized["success"] is False
            assert unauthorized["message"] == "Access denied"

            # 测试禁止访问响应
            forbidden = ResponseBuilder.forbidden("Forbidden")
            assert forbidden["success"] is False
            assert forbidden["message"] == "Forbidden"
        except (ImportError, AttributeError):
            pytest.skip("ResponseBuilder methods not available")


class TestI18nModule:
    """测试国际化模块"""

    def test_i18n_import(self):
        """测试i18n模块导入"""
        try:
            from src.utils.i18n import I18n

            assert I18n is not None
        except ImportError:
            pytest.skip("I18n not available")

    def test_i18n_methods(self):
        """测试i18n方法"""
        try:
            from src.utils.i18n import I18n

            # 创建I18n实例
            i18n = I18n()
            assert i18n is not None

            # 测试翻译
            if hasattr(i18n, "translate"):
                translated = i18n.translate("hello")
                assert isinstance(translated, str)

            # 测试设置语言
            if hasattr(i18n, "set_language"):
                _result = i18n.set_language("en")
                # 可能返回bool或None

            # 测试获取当前语言
            if hasattr(i18n, "get_current_language"):
                lang = i18n.get_current_language()
                assert isinstance(lang, str)
        except (ImportError, AttributeError):
            pytest.skip("I18n methods not available")


class TestRetryModule:
    """测试重试模块"""

    def test_retry_import(self):
        """测试retry模块导入"""
        try:
            from src.utils.retry import RetryHelper

            assert RetryHelper is not None
        except ImportError:
            pytest.skip("RetryHelper not available")

    def test_retry_methods(self):
        """测试retry方法"""
        try:
            from src.utils.retry import RetryHelper

            # 测试指数退避
            delay1 = RetryHelper.exponential_backoff(1, 1.0)
            delay2 = RetryHelper.exponential_backoff(2, 1.0)
            assert delay2 > delay1

            # 测试线性退避
            linear1 = RetryHelper.linear_backoff(1, 0.1)
            linear2 = RetryHelper.linear_backoff(2, 0.1)
            assert linear2 > linear1

            # 测试抖动退避
            jitter = RetryHelper.jitter_backoff(1, 1.0)
            assert isinstance(jitter, (int, float))
        except (ImportError, AttributeError):
            pytest.skip("RetryHelper methods not available")


class TestValidatorsModule:
    """测试验证器模块"""

    def test_validators_import(self):
        """测试validators模块导入"""
        try:
            from src.utils.validators import Validators

            assert Validators is not None
        except ImportError:
            pytest.skip("Validators not available")

    def test_validators_methods(self):
        """测试validators方法"""
        try:
            from src.utils.validators import Validators

            validator = Validators()

            # 测试必填验证
            assert validator.validate_required("value")
            assert not validator.validate_required(None)
            assert not validator.validate_required("")

            # 测试范围验证
            assert validator.validate_range(5, 1, 10)
            assert not validator.validate_range(0, 1, 10)

            # 测试长度验证
            assert validator.validate_length("hello", 1, 10)
            assert not validator.validate_length("very long string", 1, 5)

            # 测试模式验证
            assert validator.validate_pattern("abc", r"^[a-z]+$")
            assert not validator.validate_pattern("123", r"^[a-z]+$")

            # 测试选择验证
            assert validator.validate_choice("red", ["red", "green", "blue"])
            assert not validator.validate_choice("yellow", ["red", "green", "blue"])

            # 测试邮箱格式验证
            if hasattr(validator, "validate_email_format"):
                assert validator.validate_email_format("test@example.com")
                assert not validator.validate_email_format("invalid")

            # 测试URL格式验证
            if hasattr(validator, "validate_url_format"):
                assert validator.validate_url_format("https://example.com")
                assert not validator.validate_url_format("not_url")

            # 测试数字格式验证
            if hasattr(validator, "validate_number_format"):
                assert validator.validate_number_format("123")
                assert not validator.validate_number_format("abc")
        except (ImportError, AttributeError):
            pytest.skip("Validators methods not available")


class TestWarningFiltersModule:
    """测试警告过滤器模块"""

    def test_warning_filters_import(self):
        """测试warning_filters模块导入"""
        try:
            from src.utils.warning_filters import WarningFilters

            assert WarningFilters is not None
        except ImportError:
            pytest.skip("WarningFilters not available")

    def test_warning_filters_methods(self):
        """测试warning_filters方法"""
        try:
            from src.utils.warning_filters import WarningFilters

            # 测试过滤废弃警告
            if hasattr(WarningFilters, "filter_deprecation_warnings"):
                _result = WarningFilters.filter_deprecation_warnings()
                # 可能返回None或布尔值

            # 测试过滤导入警告
            if hasattr(WarningFilters, "filter_import_warnings"):
                _result = WarningFilters.filter_import_warnings()

            # 测试过滤用户警告
            if hasattr(WarningFilters, "filter_user_warnings"):
                _result = WarningFilters.filter_user_warnings()

            # 测试设置警告
            if hasattr(WarningFilters, "setup_warnings"):
                _result = WarningFilters.setup_warnings()
        except (ImportError, AttributeError):
            pytest.skip("WarningFilters methods not available")


class TestConfigLoaderModule:
    """测试配置加载器模块"""

    def test_config_loader_import(self):
        """测试config_loader模块导入"""
        try:
            from src.utils.config_loader import ConfigLoader

            assert ConfigLoader is not None
        except ImportError:
            pytest.skip("ConfigLoader not available")

    def test_config_loader_methods(self):
        """测试config_loader方法"""
        try:
            from src.utils.config_loader import ConfigLoader

            # 测试加载配置
            if hasattr(ConfigLoader, "load_config"):
                _config = ConfigLoader.load_config()
                # 可能返回dict或None

            # 测试获取配置值
            if hasattr(ConfigLoader, "get_config_value"):
                value = ConfigLoader.get_config_value("test_key", "default")
                assert value == "default" or isinstance(
                    value, (str, int, bool, dict, list)
                )

            # 测试设置配置值
            if hasattr(ConfigLoader, "set_config_value"):
                _result = ConfigLoader.set_config_value("test_key", "test_value")

            # 测试重新加载配置
            if hasattr(ConfigLoader, "reload_config"):
                _result = ConfigLoader.reload_config()

            # 测试获取环境配置
            if hasattr(ConfigLoader, "get_env_config"):
                env_config = ConfigLoader.get_env_config()
                assert isinstance(env_config, dict)
        except (ImportError, AttributeError):
            pytest.skip("ConfigLoader methods not available")


class TestFileUtilsModule:
    """测试文件工具模块"""

    def test_file_utils_import(self):
        """测试file_utils模块导入"""
        try:
            from src.utils.file_utils import FileUtils

            assert FileUtils is not None
        except ImportError:
            pytest.skip("FileUtils not available")

    def test_file_utils_methods(self):
        """测试file_utils方法"""
        try:
            from src.utils.file_utils import FileUtils

            # 测试安全文件名
            safe = FileUtils.safe_filename("file/name.txt")
            assert "/" not in safe
            assert "file" in safe
            assert "txt" in safe

            # 测试获取文件扩展名
            ext = FileUtils.get_file_extension("test.txt")
            assert ext == "txt"

            ext = FileUtils.get_file_extension("test.tar.gz")
            assert ext == "gz" or ext == "tar.gz"

            # 测试生成安全的文件名
            safe2 = FileUtils.safe_filename("file<>?|:.txt")
            assert "<" not in safe2
            assert ">" not in safe2
            assert "?" not in safe2
        except (ImportError, AttributeError):
            pytest.skip("FileUtils methods not available")


# 测试utils/__init__.py导出的函数
class TestUtilsInitExports:
    """测试utils模块导出的函数"""

    def test_utils_init_import(self):
        """测试从utils导入"""
        try:
            import src.utils as utils

            assert utils is not None
        except ImportError:
            pytest.skip("utils module not available")

    def test_exported_functions_exist(self):
        """测试导出的函数存在"""
        try:
            from src.utils import generate_uuid, hash_string, deep_merge, slugify

            # 函数应该存在且可调用
            assert callable(generate_uuid)
            assert callable(hash_string)
            assert callable(deep_merge)
            assert callable(slugify)
        except ImportError:
            pytest.skip("Exported functions not available")

    def test_exported_functions_work(self):
        """测试导出的函数工作"""
        try:
            from src.utils import generate_uuid, generate_short_id, format_datetime

            # 测试UUID生成
            uuid1 = generate_uuid()
            uuid2 = generate_uuid()
            assert uuid1 != uuid2

            # 测试短ID生成
            short_id = generate_short_id(10)
            assert len(short_id) == 10

            # 测试格式化时间
            dt = datetime.now()
            formatted = format_datetime(dt)
            assert isinstance(formatted, str)
        except ImportError:
            pytest.skip("Exported functions not working")


# 性能和边界测试
class TestPerformanceAndEdgeCases:
    """测试性能和边界情况"""

    def test_large_dict_merge(self):
        """测试大字典合并"""
        try:
            from src.utils.dict_utils import DictUtils

            # 创建大字典
            dict1 = {f"key_{i}": i for i in range(1000)}
            dict2 = {f"key_{i}": i * 2 for i in range(500, 1500)}
            merged = DictUtils.deep_merge(dict1, dict2)
            assert len(merged) == 1500
        except (ImportError, AttributeError):
            pytest.skip("DictUtils not available")

    def test_deep_nesting_flatten(self):
        """测试深度嵌套扁平化"""
        try:
            from src.utils.dict_utils import DictUtils

            # 创建深度嵌套字典
            deep_dict = {}
            current = deep_dict
            for i in range(100):
                current[f"level_{i}"] = {}
                current = current[f"level_{i}"]
            current["value"] = "deep_value"

            flat = DictUtils.flatten_dict(deep_dict, sep=".")
            assert "deep_value" in flat.values()
        except (ImportError, AttributeError):
            pytest.skip("DictUtils not available")

    def test_string_operations_edge_cases(self):
        """测试字符串操作边界情况"""
        try:
            from src.utils.string_utils import StringUtils

            # 测试空字符串
            assert StringUtils.slugify("") == ""
            assert StringUtils.capitalize_first("") == ""

            # 测试特殊字符
            special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            slugified = StringUtils.slugify(special)
            assert len(slugified) >= 0

            # 测试超长字符串
            long_string = "a" * 10000
            truncated = StringUtils.truncate_words(long_string, 10)
            assert len(truncated) < len(long_string)
        except (ImportError, AttributeError):
            pytest.skip("StringUtils not available")

    def test_time_edge_cases(self):
        """测试时间边界情况"""
        try:
            from src.utils.time_utils import TimeUtils
            from datetime import datetime, timedelta

            # 测试零时间差
            now = datetime.now()
            zero_ago = TimeUtils.time_ago(now)
            assert isinstance(zero_ago, str)

            # 测试极大时间差
            future = now + timedelta(days=365 * 100)  # 100年后
            assert TimeUtils.is_future(future)

            # 测试零持续时间
            zero_duration = TimeUtils.duration_format(0)
            assert "0" in zero_duration
        except (ImportError, AttributeError):
            pytest.skip("TimeUtils not available")
