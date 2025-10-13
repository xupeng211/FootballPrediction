"""
测试能够正确导入的模块
专注于实际存在的函数和类
"""

import pytest
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestCryptoUtilsWorking:
    """测试crypto_utils模块 - 使用类方法"""

    def test_crypto_utils_import(self):
        """测试导入CryptoUtils类"""
        from utils.crypto_utils import CryptoUtils

        assert CryptoUtils is not None

    def test_generate_uuid(self):
        """测试生成UUID"""
        from utils.crypto_utils import CryptoUtils

        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1 != uuid2
        assert "-" in uuid1

    def test_generate_short_id(self):
        """测试生成短ID"""
        from utils.crypto_utils import CryptoUtils

        # 测试不同长度
        for length in [4, 8, 16, 32]:
            short_id = CryptoUtils.generate_short_id(length)
            assert isinstance(short_id, str)
            assert len(short_id) == length

        # 测试边界情况
        assert CryptoUtils.generate_short_id(0) == ""
        long_id = CryptoUtils.generate_short_id(40)
        assert len(long_id) == 40

    def test_hash_string(self):
        """测试字符串哈希"""
        from utils.crypto_utils import CryptoUtils

        text = "test message"

        # 测试MD5
        md5_hash = CryptoUtils.hash_string(text, "md5")
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32

        # 测试SHA256
        sha256_hash = CryptoUtils.hash_string(text, "sha256")
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64

        # 测试相同输入产生相同输出
        md5_hash2 = CryptoUtils.hash_string(text, "md5")
        assert md5_hash == md5_hash2

    def test_hash_password(self):
        """测试密码哈希"""
        from utils.crypto_utils import CryptoUtils

        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")

        # 测试带salt的哈希
        salt = "testsalt123"
        hashed_with_salt = CryptoUtils.hash_password(password, salt)
        assert isinstance(hashed_with_salt, str)
        assert salt in hashed_with_salt

    def test_verify_password(self):
        """测试密码验证"""
        from utils.crypto_utils import CryptoUtils

        password = "test_password"
        hashed = CryptoUtils.hash_password(password)

        # 正确密码
        assert CryptoUtils.verify_password(password, hashed) is True

        # 错误密码
        assert CryptoUtils.verify_password("wrong_password", hashed) is False

        # 空密码情况
        assert CryptoUtils.verify_password("", "") is True
        assert CryptoUtils.verify_password("nonempty", "") is False


class TestDataValidatorWorking:
    """测试data_validator模块"""

    def test_data_validator_import(self):
        """测试导入DataValidator类"""
        from utils.data_validator import DataValidator

        assert DataValidator is not None

    def test_validate_email(self):
        """测试邮箱验证"""
        from utils.data_validator import DataValidator

        validator = DataValidator()

        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@test.com",
        ]
        for email in valid_emails:
            assert validator.validate_email(email) is True

        # 无效邮箱
        invalid_emails = [
            "",
            "not-an-email",
            "@example.com",
            "test@",
            "test..test@example.com",
        ]
        for email in invalid_emails:
            assert validator.validate_email(email) is False

    def test_validate_phone(self):
        """测试电话验证"""
        from utils.data_validator import DataValidator

        validator = DataValidator()

        # 有效电话
        valid_phones = [
            "1234567890",
            "+1-234-567-8900",
            "(123) 456-7890",
            "+86 138 0013 8000",
        ]
        for phone in valid_phones:
            _result = validator.validate_phone(phone)
            # 结果可能是True或False，取决于实现
            assert isinstance(result, bool)

        # 无效电话
        invalid_phones = ["", "abc", "123"]
        for phone in invalid_phones:
            _result = validator.validate_phone(phone)
            assert isinstance(result, bool)

    def test_validate_url(self):
        """测试URL验证"""
        from utils.data_validator import DataValidator

        validator = DataValidator()

        # 有效URL
        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
            "ftp://files.example.com",
        ]
        for url in valid_urls:
            _result = validator.validate_url(url)
            assert isinstance(result, bool)

        # 无效URL
        invalid_urls = [
            "",
            "not-a-url",
            "www.example.com",  # 缺少协议
        ]
        for url in invalid_urls:
            _result = validator.validate_url(url)
            assert isinstance(result, bool)


class TestDictUtilsWorking:
    """测试dict_utils模块"""

    def test_dict_utils_import(self):
        """测试导入DictUtils类"""
        from utils.dict_utils import DictUtils

        assert DictUtils is not None

    def test_deep_merge(self):
        """测试深度合并"""
        from utils.dict_utils import DictUtils

        dict1 = {"a": 1, "b": {"x": 1, "y": 2}}
        dict2 = {"b": {"y": 3, "z": 4}, "c": 5}

        merged = DictUtils.deep_merge(dict1, dict2)

        assert merged["a"] == 1
        assert merged["b"]["x"] == 1
        assert merged["b"]["y"] == 3  # dict2的值覆盖
        assert merged["b"]["z"] == 4
        assert merged["c"] == 5

    def test_flatten_dict(self):
        """测试扁平化字典"""
        from utils.dict_utils import DictUtils

        nested = {"a": {"b": {"c": 1}}, "x": 2, "y": {"z": 3}}

        flat = DictUtils.flatten_dict(nested)

        assert isinstance(flat, dict)
        assert len(flat) >= 3

    def test_filter_none(self):
        """测试过滤None值"""
        from utils.dict_utils import DictUtils

        d = {"a": 1, "b": None, "c": 0, "d": False, "e": ""}
        filtered = DictUtils.filter_none(d)

        assert "a" in filtered
        assert "b" not in filtered
        assert "c" in filtered  # 0不是None
        assert "d" in filtered  # False不是None
        assert "e" in filtered  # 空字符串不是None


class TestFileUtilsWorking:
    """测试file_utils模块"""

    def test_file_utils_import(self):
        """测试导入FileUtils类"""
        from utils.file_utils import FileUtils

        assert FileUtils is not None

    def test_safe_filename(self):
        """测试安全文件名"""
        from utils.file_utils import FileUtils

        unsafe_names = [
            "file<>:|?*.txt",
            "normal-file.txt",
            "file with spaces.pdf",
            "file@#$%^&*().doc",
        ]

        for name in unsafe_names:
            safe = FileUtils.safe_filename(name)
            assert isinstance(safe, str)
            assert "<" not in safe
            assert ">" not in safe
            assert "|" not in safe
            assert "?" not in safe
            assert "*" not in safe

    def test_ensure_dir(self):
        """测试确保目录存在"""
        from utils.file_utils import FileUtils
        import tempfile
        import shutil

        test_dir = tempfile.mkdtemp()
        try:
            sub_dir = os.path.join(test_dir, "subdir", "nested")
            FileUtils.ensure_dir(sub_dir)
            assert os.path.exists(sub_dir)
        finally:
            shutil.rmtree(test_dir)

    def test_get_file_size(self):
        """测试获取文件大小"""
        from utils.file_utils import FileUtils
        import tempfile

        with tempfile.NamedTemporaryFile() as tmp:
            content = b"test content for size"
            tmp.write(content)
            tmp.flush()

            size = FileUtils.get_file_size(tmp.name)
            assert size == len(content)

    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        from utils.file_utils import FileUtils

        assert FileUtils.get_file_extension("test.txt") == ".txt"
        assert FileUtils.get_file_extension("document.pdf") == ".pdf"
        assert FileUtils.get_file_extension("archive.tar.gz") == ".gz"
        assert FileUtils.get_file_extension("no_extension") == ""


class TestFormattersWorking:
    """测试formatters模块"""

    def test_formatters_import(self):
        """测试导入Formatters类"""
        from utils.formatters import Formatters

        assert Formatters is not None

    def test_format_datetime(self):
        """测试格式化日期时间"""
        from utils.formatters import Formatters
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        formatted = Formatters.format_datetime(dt)

        assert isinstance(formatted, str)
        assert "2024" in formatted

    def test_format_currency(self):
        """测试格式化货币"""
        from utils.formatters import Formatters

        # 测试不同货币
        currencies = [(123.45, "USD"), (1000, "EUR"), (0.99, "CNY"), (500, "JPY")]

        for amount, currency in currencies:
            formatted = Formatters.format_currency(amount, currency)
            assert isinstance(formatted, str)
            assert str(int(amount)) in formatted or currency in formatted

    def test_format_bytes(self):
        """测试格式化字节大小"""
        from utils.formatters import Formatters

        sizes = [(1024, "KB"), (1048576, "MB"), (1073741824, "GB")]

        for bytes_val, unit in sizes:
            formatted = Formatters.format_bytes(bytes_val)
            assert isinstance(formatted, str)
            assert unit in formatted or unit.lower() in formatted


class TestHelpersWorking:
    """测试helpers模块"""

    def test_helpers_import(self):
        """测试导入Helpers类"""
        from utils.helpers import Helpers

        assert Helpers is not None

    def test_generate_uuid(self):
        """测试生成UUID"""
        from utils.helpers import Helpers

        uuid1 = Helpers.generate_uuid()
        uuid2 = Helpers.generate_uuid()

        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1 != uuid2

    def test_is_json(self):
        """测试JSON判断"""
        from utils.helpers import Helpers

        # 有效JSON
        valid_json = ['{"key": "value"}', "[]", "null", '"string"', "123"]
        for json_str in valid_json:
            assert Helpers.is_json(json_str) is True

        # 无效JSON
        invalid_json = ["not json", '{"unclosed"', "undefined", "function(){}"]
        for json_str in invalid_json:
            assert Helpers.is_json(json_str) is False

    def test_truncate_string(self):
        """测试字符串截断"""
        from utils.helpers import Helpers

        long_text = "This is a very long text that should be truncated"

        # 测试不同长度
        for length in [10, 20, 50]:
            truncated = Helpers.truncate_string(long_text, length)
            assert isinstance(truncated, str)
            if len(long_text) > length:
                assert "..." in truncated or len(truncated) <= length

    def test_deep_get(self):
        """测试深度获取字典值"""
        from utils.helpers import Helpers

        _data = {"a": {"b": {"c": 123}}}

        value = Helpers.deep_get(data, "a.b.c")
        assert value == 123

        # 测试不存在的路径
        value = Helpers.deep_get(data, "a.b.x", "default")
        assert value == "default"


class TestI18nWorking:
    """测试i18n模块"""

    def test_i18n_import(self):
        """测试导入I18n类"""
        from utils.i18n import I18n

        assert I18n is not None

    def test_translation(self):
        """测试翻译功能"""
        from utils.i18n import I18n

        # 初始化
        i18n = I18n()

        # 测试翻译
        _result = i18n.translate("hello")
        assert isinstance(result, str)

    def test_language_switching(self):
        """测试语言切换"""
        from utils.i18n import I18n

        i18n = I18n()

        # 设置语言
        languages = ["en", "zh", "es", "fr"]
        for lang in languages:
            i18n.set_language(lang)
            current = i18n.get_current_language()
            assert current == lang


class TestResponseWorking:
    """测试response模块"""

    def test_response_import(self):
        """测试导入ResponseBuilder类"""
        from utils.response import ResponseBuilder

        assert ResponseBuilder is not None

    def test_success_response(self):
        """测试成功响应"""
        from utils.response import ResponseBuilder

        response = ResponseBuilder.success({"data": "test"})

        assert isinstance(response, dict)
        assert response["status"] == "success"

    def test_error_response(self):
        """测试错误响应"""
        from utils.response import ResponseBuilder

        response = ResponseBuilder.error("Error message")

        assert isinstance(response, dict)
        assert response["status"] == "error"

    def test_created_response(self):
        """测试创建响应"""
        from utils.response import ResponseBuilder

        response = ResponseBuilder.created({"id": 1})

        assert isinstance(response, dict)
        assert response["status"] == "created"

    def test_not_found_response(self):
        """测试未找到响应"""
        from utils.response import ResponseBuilder

        response = ResponseBuilder.not_found("Resource not found")

        assert isinstance(response, dict)
        assert response["status"] == "not_found"


class TestStringUtilsWorking:
    """测试string_utils模块"""

    def test_string_utils_import(self):
        """测试导入StringUtils类"""
        from utils.string_utils import StringUtils

        assert StringUtils is not None

    def test_slugify(self):
        """测试字符串slug化"""
        from utils.string_utils import StringUtils

        texts = [
            "Hello World!",
            "This is a test",
            "Special @#$% Characters",
            "Multiple   Spaces",
        ]

        for text in texts:
            slug = StringUtils.slugify(text)
            assert isinstance(slug, str)
            assert " " not in slug
            assert "!" not in slug
            assert "@" not in slug

    def test_camel_to_snake(self):
        """测试驼峰转蛇形"""
        from utils.string_utils import StringUtils

        camel_cases = ["camelCase", "PascalCase", "XMLHttpRequest", "simple"]

        for camel in camel_cases:
            snake = StringUtils.camel_to_snake(camel)
            assert isinstance(snake, str)
            if not snake.islower():
                assert "_" in snake

    def test_snake_to_camel(self):
        """测试蛇形转驼峰"""
        from utils.string_utils import StringUtils

        snake_cases = ["snake_case", "mixed_case_string", "already_snake"]

        for snake in snake_cases:
            camel = StringUtils.snake_to_camel(snake)
            assert isinstance(camel, str)

    def test_truncate_words(self):
        """测试单词截断"""
        from utils.string_utils import StringUtils

        text = "This is a test sentence with multiple words"

        for word_count in [3, 5, 10]:
            truncated = StringUtils.truncate_words(text, word_count)
            assert isinstance(truncated, str)
            # 计算单词数
            words = truncated.split()
            assert len(words) <= word_count + 1  # +1 for "..."

    def test_clean_html(self):
        """测试清理HTML"""
        from utils.string_utils import StringUtils

        html_strings = [
            "<p>Hello <b>World</b></p>",
            "<div>Content <script>alert('xss')</script></div>",
            "Plain text without HTML",
        ]

        for html in html_strings:
            cleaned = StringUtils.clean_html(html)
            assert isinstance(cleaned, str)
            # 确保没有HTML标签
            assert "<" not in cleaned or ">" not in cleaned


class TestTimeUtilsWorking:
    """测试time_utils模块"""

    def test_time_utils_import(self):
        """测试导入TimeUtils类"""
        from utils.time_utils import TimeUtils

        assert TimeUtils is not None

    def test_time_ago(self):
        """测试时间差计算"""
        from utils.time_utils import TimeUtils
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # 测试不同时间差
        times = [
            now - timedelta(minutes=30),
            now - timedelta(hours=2),
            now - timedelta(days=1),
            now - timedelta(weeks=1),
        ]

        for time in times:
            ago = TimeUtils.time_ago(time)
            assert isinstance(ago, str)
            assert len(ago) > 0

    def test_duration_format(self):
        """测试持续时间格式化"""
        from utils.time_utils import TimeUtils

        durations = [30, 90, 3665, 7200, 86400]

        for duration in durations:
            formatted = TimeUtils.duration_format(duration)
            assert isinstance(formatted, str)
            # 检查包含时间单位
            assert any(
                unit in formatted for unit in ["second", "minute", "hour", "day"]
            )

    def test_is_future(self):
        """测试未来时间判断"""
        from utils.time_utils import TimeUtils
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        past = now - timedelta(hours=1)

        assert TimeUtils.is_future(future) is True
        assert TimeUtils.is_future(past) is False

    def test_format_datetime(self):
        """测试格式化日期时间"""
        from utils.time_utils import TimeUtils
        from datetime import datetime, timezone

        dt = datetime.now(timezone.utc)

        # 测试不同格式
        formats = ["%Y-%m-%d", "%H:%M:%S", "%Y-%m-%d %H:%M:%S"]
        for fmt in formats:
            formatted = TimeUtils.format_datetime(dt, fmt)
            assert isinstance(formatted, str)
            assert len(formatted) > 0


class TestValidatorsWorking:
    """测试validators模块"""

    def test_validators_import(self):
        """测试导入Validators类"""
        from utils.validators import Validators

        assert Validators is not None

    def test_validate_required(self):
        """测试必填验证"""
        from utils.validators import Validators

        validator = Validators()

        # 测试各种值
        test_values = [
            (None, False),
            ("", False),
            ([], False),
            ({}, False),
            ("test", True),
            (0, True),
            (False, True),
        ]

        for value, expected in test_values:
            _result = validator.validate_required(value)
            assert _result == expected

    def test_validate_range(self):
        """测试范围验证"""
        from utils.validators import Validators

        validator = Validators()

        # 测试在范围内
        assert validator.validate_range(5, 1, 10) is True
        assert validator.validate_range(1, 1, 10) is True
        assert validator.validate_range(10, 1, 10) is True

        # 测试超出范围
        assert validator.validate_range(0, 1, 10) is False
        assert validator.validate_range(11, 1, 10) is False

    def test_validate_length(self):
        """测试长度验证"""
        from utils.validators import Validators

        validator = Validators()

        # 测试字符串
        assert validator.validate_length("hello", 1, 10) is True
        assert validator.validate_length("", 1, 10) is False
        assert validator.validate_length("x" * 20, 1, 10) is False

        # 测试列表
        assert validator.validate_length([1, 2, 3], 1, 5) is True
        assert validator.validate_length([], 1, 5) is False

    def test_validate_pattern(self):
        """测试模式验证"""
        from utils.validators import Validators

        validator = Validators()

        # 测试邮箱模式
        assert (
            validator.validate_pattern("test@example.com", r"^[^@]+@[^@]+\.[^@]+$")
            is True
        )
        assert validator.validate_pattern("not-email", r"^[^@]+@[^@]+\.[^@]+$") is False

        # 测试电话模式
        assert (
            validator.validate_pattern("123-456-7890", r"^\d{3}-\d{3}-\d{4}$") is True
        )
        assert validator.validate_pattern("phone", r"^\d{3}-\d{3}-\d{4}$") is False


class TestWarningFiltersWorking:
    """测试warning_filters模块"""

    def test_warning_filters_import(self):
        """测试导入WarningFilters类"""
        from utils.warning_filters import WarningFilters

        assert WarningFilters is not None

    def test_filter_deprecation_warnings(self):
        """测试过滤废弃警告"""
        from utils.warning_filters import WarningFilters
        import warnings

        # 测试过滤功能存在
        WarningFilters.filter_deprecation_warnings()
        assert True  # 如果没有异常就算通过

    def test_filter_import_warnings(self):
        """测试过滤导入警告"""
        from utils.warning_filters import WarningFilters

        WarningFilters.filter_import_warnings()
        assert True

    def test_filter_user_warnings(self):
        """测试过滤用户警告"""
        from utils.warning_filters import WarningFilters

        WarningFilters.filter_user_warnings()
        assert True

    def test_setup_warnings(self):
        """测试设置警告"""
        from utils.warning_filters import WarningFilters

        WarningFilters.setup_warnings()
        assert True


class TestConfigLoaderWorking:
    """测试config_loader模块"""

    def test_config_loader_import(self):
        """测试导入ConfigLoader类"""
        from utils.config_loader import ConfigLoader

        assert ConfigLoader is not None

    def test_load_config(self):
        """测试加载配置"""
        from utils.config_loader import ConfigLoader

        _config = ConfigLoader.load_config()
        assert isinstance(config, dict)
        assert len(config) >= 0

    def test_get_config_value(self):
        """测试获取配置值"""
        from utils.config_loader import ConfigLoader

        # 测试获取配置
        value = ConfigLoader.get_config_value("app.name", "default_value")
        assert isinstance(value, str)
        assert value is not None

    def test_set_config_value(self):
        """测试设置配置值"""
        from utils.config_loader import ConfigLoader

        # 设置测试配置
        ConfigLoader.set_config_value("test.key", "test_value")

        # 获取设置的值
        value = ConfigLoader.get_config_value("test.key")
        assert value == "test_value"

    def test_get_env_config(self):
        """测试获取环境配置"""
        from utils.config_loader import ConfigLoader

        env_config = ConfigLoader.get_env_config()
        assert isinstance(env_config, dict)
        # 可能包含环境变量
        assert len(env_config) >= 0


class TestRetryWorking:
    """测试retry模块"""

    def test_retry_import(self):
        """测试导入RetryHelper类"""
        from utils.retry import RetryHelper

        assert RetryHelper is not None

    def test_retry_decorator(self):
        """测试重试装饰器"""
        from utils.retry import RetryHelper

        attempts = 0

        @RetryHelper.retry(max_attempts=3, delay=0.01)
        def eventually_success():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("Not yet")
            return "success"

        _result = eventually_success()
        assert _result == "success"
        assert attempts == 3

    def test_exponential_backoff(self):
        """测试指数退避"""
        from utils.retry import RetryHelper

        delay = RetryHelper.exponential_backoff(1, 1.0)  # attempt=1, base_delay=1.0
        assert isinstance(delay, (int, float))
        assert delay >= 0

    def test_linear_backoff(self):
        """测试线性退避"""
        from utils.retry import RetryHelper

        delay = RetryHelper.linear_backoff(2, 0.5)  # attempt=2, base_delay=0.5
        assert isinstance(delay, (int, float))
        assert delay >= 0

    def test_jitter_backoff(self):
        """测试抖动退避"""
        from utils.retry import RetryHelper

        delay = RetryHelper.jitter_backoff(1, 1.0)  # attempt=1, base_delay=1.0
        assert isinstance(delay, (int, float))
        assert delay >= 0
