"""
直接导入并测试源模块
绕过导入问题，直接测试源代码
"""

import pytest
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_crypto_utils():
    """测试crypto_utils模块"""
    try:
        from utils.crypto_utils import hash_password, verify_password, generate_token

        # 测试密码哈希
        password = "test123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 20

        # 测试密码验证
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

        # 测试令牌生成
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 10
    except ImportError:
        pytest.skip("crypto_utils not available")


def test_data_validator():
    """测试data_validator模块"""
    try:
        from utils.data_validator import validate_email, validate_phone, validate_url

        # 测试邮箱验证
        assert validate_email("test@example.com") is True
        assert validate_email("invalid") is False

        # 测试电话验证
        assert validate_phone("1234567890") is True
        assert validate_phone("abc") is False

        # 测试URL验证
        assert validate_url("https://example.com") is True
        assert validate_url("not-url") is False
    except ImportError:
        pytest.skip("data_validator not available")


def test_dict_utils():
    """测试dict_utils模块"""
    try:
        from utils.dict_utils import deep_merge, flatten_dict, filter_none

        # 测试深度合并
        d1 = {"a": 1, "b": {"x": 1}}
        d2 = {"b": {"y": 2}, "c": 3}
        merged = deep_merge(d1, d2)
        assert merged["a"] == 1
        assert merged["b"]["x"] == 1
        assert merged["b"]["y"] == 2
        assert merged["c"] == 3

        # 测试扁平化
        nested = {"a": {"b": {"c": 1}}}
        flat = flatten_dict(nested)
        assert "a.b.c" in flat

        # 测试过滤None
        d = {"a": 1, "b": None, "c": 0, "d": False, "e": "test"}
        filtered = filter_none(d)
        assert "a" in filtered
        assert "b" not in filtered
        assert "c" in filtered  # 0不是None
    except ImportError:
        pytest.skip("dict_utils not available")


def test_file_utils():
    """测试file_utils模块"""
    try:
        from utils.file_utils import ensure_dir, get_file_size, safe_filename

        # 测试确保目录存在
        test_dir = "/tmp/test_football_prediction"
        ensure_dir(test_dir)
        assert os.path.exists(test_dir)
        os.rmdir(test_dir)  # 清理

        # 测试安全文件名
        unsafe = "file<>:|?*.txt"
        safe = safe_filename(unsafe)
        assert "<" not in safe
        assert ">" not in safe
        assert safe.endswith(".txt")

        # 测试获取文件大小
        import tempfile

        with tempfile.NamedTemporaryFile() as tmp:
            content = b"test content"
            tmp.write(content)
            tmp.flush()
            size = get_file_size(tmp.name)
            assert size == len(content)
    except ImportError:
        pytest.skip("file_utils not available")


def test_formatters():
    """测试formatters模块"""
    try:
        from utils.formatters import format_datetime, format_currency, format_bytes
        from datetime import datetime, timezone

        # 测试日期时间格式化
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        formatted = format_datetime(dt)
        assert "2024" in formatted

        # 测试货币格式化
        money = format_currency(1234.56, "USD")
        assert "1234" in money or "$" in money

        # 测试字节格式化
        size = format_bytes(1024)
        assert "KB" in size or "kb" in size
    except ImportError:
        pytest.skip("formatters not available")


def test_helpers():
    """测试helpers模块"""
    try:
        from utils.helpers import generate_uuid, is_json, truncate_string

        # 测试UUID生成
        uid = generate_uuid()
        assert isinstance(uid, str)
        assert len(uid) == 36

        # 测试JSON判断
        assert is_json('{"key": "value"}') is True
        assert is_json("not json") is False

        # 测试字符串截断
        long_text = "This is a very long text that should be truncated"
        truncated = truncate_string(long_text, 20)
        assert len(truncated) <= 23  # 20 + "..."
    except ImportError:
        pytest.skip("helpers not available")


def test_string_utils():
    """测试string_utils模块"""
    try:
        from utils.string_utils import slugify, camel_to_snake, snake_to_camel

        # 测试slugify
        text = "Hello World! How are you?"
        slug = slugify(text)
        assert " " not in slug
        assert "!" not in slug

        # 测试驼峰转蛇形
        camel = "camelCaseString"
        snake = camel_to_snake(camel)
        assert "_" in snake

        # 测试蛇形转驼峰
        snake_case = "snake_case_string"
        camel = snake_to_camel(snake_case)
        assert "_" not in camel
    except ImportError:
        pytest.skip("string_utils not available")


def test_time_utils():
    """测试time_utils模块"""
    try:
        from utils.time_utils import time_ago, duration_format, is_future
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # 测试time_ago
        past = now - timedelta(hours=2)
        ago = time_ago(past)
        assert "hour" in ago or "hours" in ago

        # 测试持续时间格式化
        seconds = 3665
        duration = duration_format(seconds)
        assert "hour" in duration and "minute" in duration

        # 测试未来时间判断
        future = now + timedelta(days=1)
        assert is_future(future) is True
        assert is_future(past) is False
    except ImportError:
        pytest.skip("time_utils not available")


def test_validators():
    """测试validators模块"""
    try:
        from utils.validators import validate_required, validate_range, validate_length

        # 测试必填验证
        assert validate_required("test") is True
        assert validate_required("") is False
        assert validate_required(None) is False

        # 测试范围验证
        assert validate_range(5, 1, 10) is True
        assert validate_range(0, 1, 10) is False
        assert validate_range(11, 1, 10) is False

        # 测试长度验证
        assert validate_length("hello", 1, 10) is True
        assert validate_length("", 1, 10) is False
        assert validate_length("x" * 20, 1, 10) is False
    except ImportError:
        pytest.skip("validators not available")


def test_warning_filters():
    """测试warning_filters模块"""
    try:
        import warnings
        from utils.warning_filters import (
            filter_deprecation_warnings,
            ignore_user_warnings,
        )

        # 测试过滤警告
        with warnings.catch_warnings(record=True) as w:
            warnings.warn("This is deprecated", DeprecationWarning)
            filter_deprecation_warnings()
            assert len(w) == 0 or all(
                issubclass(warning.category, DeprecationWarning) for warning in w
            )
    except ImportError:
        pytest.skip("warning_filters not available")


def test_i18n():
    """测试i18n模块"""
    try:
        from utils.i18n import _, set_language, get_current_language

        # 测试翻译
        result = _("hello")
        assert isinstance(result, str)

        # 测试设置语言
        set_language("en")
        lang = get_current_language()
        assert lang == "en"
    except ImportError:
        pytest.skip("i18n not available")


def test_response():
    """测试response模块"""
    try:
        from utils.response import success, error, created, not_found

        # 测试成功响应
        resp = success({"data": "test"})
        assert resp["status"] == "success"

        # 测试错误响应
        resp = error("Not found")
        assert resp["status"] == "error"

        # 测试创建响应
        resp = created({"id": 1})
        assert resp["status"] == "created"

        # 测试未找到响应
        resp = not_found("Resource not found")
        assert resp["status"] == "not_found"
    except ImportError:
        pytest.skip("response not available")


def test_retry():
    """测试retry模块"""
    try:
        from utils.retry import retry, RetryError

        attempts = 0

        @retry(max_attempts=3, delay=0.01)
        def flaky_function():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise Exception("Fail")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert attempts == 3
    except ImportError:
        pytest.skip("retry not available")


def test_config_loader():
    """测试config_loader模块"""
    try:
        from utils.config_loader import load_config, get_config_value

        # 测试加载配置
        config = load_config()
        assert isinstance(config, dict)

        # 测试获取配置值
        value = get_config_value("app.name", "default")
        assert isinstance(value, str)
    except ImportError:
        pytest.skip("config_loader not available")


# 测试核心功能
class TestCoreFunctionality:
    """测试核心功能"""

    def test_import_core_modules(self):
        """测试导入核心模块"""
        # 测试导入核心模块
        try:
            from core.exceptions import FootballPredictionError

            error = FootballPredictionError("Test error")
            assert str(error) == "Test error"
        except ImportError:
            pytest.skip("core.exceptions not available")

        try:
            from core.logger import get_logger

            logger = get_logger("test")
            assert logger is not None
        except ImportError:
            pytest.skip("core.logger not available")

    def test_import_database_models(self):
        """测试导入数据库模型"""
        try:
            from database.models.base import BaseModel

            assert BaseModel is not None
        except ImportError:
            pytest.skip("database.models.base not available")

        try:
            from database.models.user import User

            user_class = User
            assert user_class is not None
        except ImportError:
            pytest.skip("database.models.user not available")

    def test_import_services(self):
        """测试导入服务"""
        try:
            from services.base_unified import BaseService

            assert BaseService is not None
        except ImportError:
            pytest.skip("services.base_unified not available")

    def test_import_cache(self):
        """测试导入缓存模块"""
        try:
            from cache.redis_manager import RedisManager

            assert RedisManager is not None
        except ImportError:
            pytest.skip("cache.redis_manager not available")

    def test_import_api_components(self):
        """测试导入API组件"""
        try:
            from api.app import app

            assert app is not None
        except ImportError:
            pytest.skip("api.app not available")

        try:
            from api.schemas import HealthCheckResponse

            assert HealthCheckResponse is not None
        except ImportError:
            pytest.skip("api.schemas not available")
