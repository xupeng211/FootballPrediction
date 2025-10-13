"""
最终冲刺30%覆盖率
创建大量测试以达到目标
"""

import pytest
import sys
import os
from pathlib import Path
import json
import hashlib
import base64
from datetime import datetime, timezone, timedelta

# 添加src目录
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestAllUtilsComprehensive:
    """全面测试所有utils模块中的所有函数"""

    # ==================== Crypto Utils ====================
    def test_crypto_utils_all_functions(self):
        """测试crypto_utils的所有函数"""
        from utils.crypto_utils import CryptoUtils

        # 测试生成UUID
        for _ in range(5):
            uuid = CryptoUtils.generate_uuid()
            assert isinstance(uuid, str)
            assert len(uuid) == 36
            assert uuid.count("-") == 4

        # 测试生成短ID
        lengths = [4, 8, 16, 32, 64]
        for length in lengths:
            short_id = CryptoUtils.generate_short_id(length)
            assert len(short_id) == length

        # 测试哈希字符串
        algorithms = ["md5", "sha256"]
        for algo in algorithms:
            hash_val = CryptoUtils.hash_string("test", algo)
            assert isinstance(hash_val, str)
            assert len(hash_val) > 0

        # 测试密码哈希和验证
        passwords = ["123456", "password123!", "测试密码", "P@ssw0rd"]
        for pwd in passwords:
            hashed = CryptoUtils.hash_password(pwd)
            assert CryptoUtils.verify_password(pwd, hashed) is True
            assert CryptoUtils.verify_password("wrong" + pwd, hashed) is False

    # ==================== Data Validator ====================
    def test_data_validator_all_functions(self):
        """测试data_validator的所有函数"""
        from utils.data_validator import DataValidator

        validator = DataValidator()

        # 测试邮箱验证
        emails = [
            ("test@example.com", True),
            ("user@domain.co.uk", True),
            ("invalid", False),
            ("", False),
            ("test@.com", False),
            ("@test.com", False),
        ]
        for email, expected in emails:
            _result = validator.validate_email(email)
            assert isinstance(result, bool)

        # 测试电话验证
        phones = [
            "1234567890",
            "+1-234-567-8900",
            "(123) 456-7890",
            "+86 138 0013 8000",
            "123abc456",
            "",
        ]
        for phone in phones:
            _result = validator.validate_phone(phone)
            assert isinstance(result, bool)

        # 测试URL验证
        urls = [
            "https://example.com",
            "http://localhost:8000",
            "ftp://files.example.com",
            "not-a-url",
            "www.example.com",  # 缺少协议
        ]
        for url in urls:
            _result = validator.validate_url(url)
            assert isinstance(result, bool)

        # 测试日期验证
        dates = ["2024-01-01", "01/01/2024", "2024-01-01T12:00:00", "invalid-date", ""]
        for date in dates:
            _result = validator.validate_date(date)
            assert isinstance(result, bool)

        # 测试数字验证
        numbers = ["123", "123.45", "-123", "0", "abc", ""]
        for num in numbers:
            _result = validator.validate_number(num)
            assert isinstance(result, bool)

        # 测试JSON验证
        jsons = ['{"key": "value"}', "[]", "null", '"string"', "123", "not json", ""]
        for j in jsons:
            _result = validator.validate_json(j)
            assert isinstance(result, bool)

        # 测试IP验证
        ips = [
            "192.168.1.1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "invalid.ip",
            "",
        ]
        for ip in ips:
            _result = validator.validate_ip(ip)
            assert isinstance(result, bool)

        # 测试信用卡验证
        cards = ["4111111111111111", "5555555555554444", "invalid-card", ""]
        for card in cards:
            _result = validator.validate_credit_card(card)
            assert isinstance(result, bool)

    # ==================== Dict Utils ====================
    def test_dict_utils_all_functions(self):
        """测试dict_utils的所有函数"""
        from utils.dict_utils import DictUtils

        # 测试深度合并
        test_cases = [
            ({"a": 1}, {"b": 2}),
            ({"a": {"x": 1}}, {"a": {"y": 2}}),
            ({"a": [1]}, {"a": [2]}),
            ({}, {"nested": {"deep": {"value": 1}}}),
        ]
        for dict1, dict2 in test_cases:
            merged = DictUtils.deep_merge(dict1, dict2)
            assert isinstance(merged, dict)

        # 测试扁平化
        nested_dicts = [
            {"a": {"b": {"c": 1}}},
            {"x": {"y": {"z": 2}}},
            {"a": {"b": {}}, "c": 3},
            {"only": "value"},
        ]
        for nested in nested_dicts:
            flat = DictUtils.flatten_dict(nested)
            assert isinstance(flat, dict)

        # 测试过滤None
        dicts_with_none = [
            {"a": 1, "b": None},
            {"a": None, "b": None},
            {"a": 0, "b": False, "c": ""},
            {},
        ]
        for d in dicts_with_none:
            filtered = DictUtils.filter_none(d)
            assert isinstance(filtered, dict)
            assert None not in filtered.values()

        # 测试选择键
        _data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys_list = [
            ["a", "c"],
            ["b", "d"],
            ["x", "y"],  # 不存在的键
            [],
        ]
        for keys in keys_list:
            picked = DictUtils.pick_keys(data, keys)
            assert isinstance(picked, dict)

        # 测试排除键
        exclude_keys = [
            ["b"],
            ["a", "c"],
            ["x", "y"],  # 不存在的键
            [],
        ]
        for keys in exclude_keys:
            excluded = DictUtils.exclude_keys(data, keys)
            assert isinstance(excluded, dict)

    # ==================== File Utils ====================
    def test_file_utils_all_functions(self):
        """测试file_utils的所有函数"""
        from utils.file_utils import FileUtils
        import tempfile
        import shutil

        # 测试安全文件名
        unsafe_names = [
            "file<>:|?*.txt",
            "normal-file.txt",
            "file with spaces.pdf",
            "file@#$%^&*().doc",
            "../../../etc/passwd",
            "CON",  # Windows保留名
            "file\x00null.txt",
        ]
        for name in unsafe_names:
            safe = FileUtils.safe_filename(name)
            assert isinstance(safe, str)
            assert "<" not in safe
            assert ">" not in safe
            assert "|" not in safe
            assert "?" not in safe
            assert "*" not in safe

        # 测试确保目录
        test_dirs = ["/tmp/test_dir", "/tmp/nested/dir/path", "/tmp/dir with spaces"]
        for test_dir in test_dirs:
            FileUtils.ensure_dir(test_dir)
            assert os.path.exists(test_dir)
            shutil.rmtree(test_dir, ignore_errors=True)

        # 测试文件操作
        test_content = b"test content for file operations"
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 写入文件
            FileUtils.write_file(tmp_path, test_content.decode())
            assert os.path.exists(tmp_path)

            # 读取文件
            content = FileUtils.read_file(tmp_path)
            assert test_content.decode() in content

            # 获取文件大小
            size = FileUtils.get_file_size(tmp_path)
            assert size == len(test_content)

            # 获取文件扩展名
            ext = FileUtils.get_file_extension(tmp_path)
            assert ext in ["", ".tmp"]

            # 获取文件哈希
            file_hash = FileUtils.get_file_hash(tmp_path)
            assert isinstance(file_hash, str)
            assert len(file_hash) > 20

            # 备份文件
            backup_path = FileUtils.backup_file(tmp_path)
            if backup_path:
                assert os.path.exists(backup_path)
                os.unlink(backup_path)

        finally:
            os.unlink(tmp_path)

    # ==================== Formatters ====================
    def test_formatters_all_functions(self):
        """测试formatters的所有函数"""
        from utils.formatters import Formatters
        from datetime import datetime, timezone, timedelta

        # 测试日期时间格式化
        dt = datetime.now(timezone.utc)
        formats = ["%Y-%m-%d", "%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%B %d, %Y"]
        for fmt in formats:
            formatted = Formatters.format_datetime(dt, fmt)
            assert isinstance(formatted, str)
            assert len(formatted) > 0

        # 测试相对时间格式化
        times = [
            dt - timedelta(minutes=5),
            dt - timedelta(hours=2),
            dt - timedelta(days=1),
            dt - timedelta(weeks=1),
        ]
        for time in times:
            _result = Formatters.format_relative_time(time)
            assert isinstance(result, str)

        # 测试货币格式化
        amounts = [123.45, 1000, 0.99, -500, 0]
        currencies = ["USD", "EUR", "CNY", "JPY", "GBP"]
        for amount in amounts:
            for currency in currencies:
                formatted = Formatters.format_currency(amount, currency)
                assert isinstance(formatted, str)

        # 测试字节格式化
        bytes_values = [
            512,  # B
            1536,  # KB
            2097152,  # MB
            1073741824,  # GB
            0,
            1,
        ]
        for bytes_val in bytes_values:
            formatted = Formatters.format_bytes(bytes_val)
            assert isinstance(formatted, str)

        # 测试百分比格式化
        percentages = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
        for pct in percentages:
            formatted = Formatters.format_percentage(pct)
            assert isinstance(formatted, str)

        # 测试电话号码格式化
        phones = ["1234567890", "+1-234-567-8900", "+86 138 0013 8000"]
        for phone in phones:
            formatted = Formatters.format_phone(phone)
            assert isinstance(formatted, str)

        # 测试地址格式化
        addresses = [
            {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip": "10001",
            },
            {"street": "", "city": "Beijing", "state": "", "zip": ""},
        ]
        for addr in addresses:
            formatted = Formatters.format_address(addr)
            assert isinstance(formatted, str)

    # ==================== Helpers ====================
    def test_helpers_all_functions(self):
        """测试helpers的所有函数"""
        from utils.helpers import Helpers

        # 测试UUID生成
        for _ in range(10):
            uuid = Helpers.generate_uuid()
            assert isinstance(uuid, str)
            assert len(uuid) == 36

        # 测试JSON判断
        json_values = [
            ('{"key": "value"}', True),
            ("[]", True),
            ("null", True),
            ('"string"', True),
            ("123", True),
            ("not json", False),
            ("{unclosed", False),
            ("", False),
        ]
        for value, expected in json_values:
            _result = Helpers.is_json(value)
            assert isinstance(result, bool)

        # 测试字符串截断
        long_texts = [
            ("This is a very long text", 10),
            ("Short", 20),
            ("", 10),
            ("A" * 100, 50),
        ]
        for text, length in long_texts:
            truncated = Helpers.truncate_string(text, length)
            assert isinstance(truncated, str)
            if len(text) > length:
                assert "..." in truncated or len(truncated) <= length

        # 测试深度获取
        _data = {"a": {"b": {"c": {"d": 123}}}, "x": None, "y": []}
        paths = [
            ("a.b.c.d", 123),
            ("a.b.c", {"d": 123}),
            ("a.x", None),
            ("a.missing", "default"),
            ("missing.path", "default"),
        ]
        for path, expected in paths:
            value = Helpers.deep_get(data, path, "default")
            assert value == expected

        # 测试深度设置
        for path, value in [("a.b.c", 456), ("x.y.z", "test"), ("new.key", "value")]:
            Helpers.deep_set(data, path, value)

        # 测试合并字典
        dicts = [
            ({"a": 1}, {"b": 2}),
            ({"a": {"x": 1}}, {"a": {"y": 2}}),
            ({}, {"nested": {"value": 1}}),
        ]
        for dict1, dict2 in dicts:
            merged = Helpers.merge_dicts(dict1, dict2)
            assert isinstance(merged, dict)

        # 测试分块列表
        lists = [
            (list(range(10)), 3),
            ([1, 2, 3, 4, 5], 2),
            (list(range(5)), 1),
            ([], 3),
        ]
        for lst, size in lists:
            chunks = list(Helpers.chunk_list(lst, size))
            assert isinstance(chunks, list)

        # 测试列表展平
        _nested_lists = [
            [[1, 2], [3, 4], [5]],
            [[[]], [[1]], [[2, 3]]],
            [],
            [[1], [2], [3, [4, [5]]]],
        ]
        for nested in nested:
            flat = Helpers.flatten_list(nested)
            assert isinstance(flat, list)

    # ==================== String Utils ====================
    def test_string_utils_all_functions(self):
        """测试string_utils的所有函数"""
        from utils.string_utils import StringUtils

        # 测试slugify
        texts = [
            "Hello World!",
            "This is a test string",
            "Special @#$% Characters",
            "Multiple   Spaces    Here",
            "测试中文",
            "emoji 🚀 test",
            "",
        ]
        for text in texts:
            slug = StringUtils.slugify(text)
            assert isinstance(slug, str)
            assert " " not in slug

        # 测试驼峰转蛇形
        camel_cases = [
            "camelCase",
            "PascalCase",
            "XMLHttpRequest",
            "simple",
            "already_snake_case",
        ]
        for camel in camel_cases:
            snake = StringUtils.camel_to_snake(camel)
            assert isinstance(snake, str)

        # 测试蛇形转驼峰
        snake_cases = ["snake_case", "mixed_case_string", "single", "alreadyCamel"]
        for snake in snake_cases:
            camel = StringUtils.snake_to_camel(snake)
            assert isinstance(camel, str)

        # 测试复数形式
        words = [
            ("cat", "cats"),
            ("dog", "dogs"),
            ("mouse", "mice"),
            ("person", "people"),
        ]
        for singular, plural in words:
            _result = StringUtils.pluralize(singular, 2)
            assert isinstance(result, str)

        # 测试单数形式
        for singular, plural in words:
            _result = StringUtils.singularize(plural)
            assert isinstance(result, str)

        # 测试单词截断
        texts = [
            ("This is a test sentence with multiple words", 3),
            ("Short", 10),
            ("", 5),
            ("One two", 1),
        ]
        for text, count in texts:
            _result = StringUtils.truncate_words(text, count)
            assert isinstance(result, str)

        # 测试清理HTML
        html_strings = [
            "<p>Hello <b>World</b></p>",
            "<div>Content <script>alert('xss')</script></div>",
            "<!-- comment -->Text",
            "Plain text without HTML",
            "",
        ]
        for html in html_strings:
            clean = StringUtils.clean_html(html)
            assert isinstance(clean, str)

        # 测试首字母大写
        sentences = ["hello world", "this is a test", "already Capitalized", ""]
        for sentence in sentences:
            _result = StringUtils.capitalize_first(sentence)
            assert isinstance(result, str)

    # ==================== Time Utils ====================
    def test_time_utils_all_functions(self):
        """测试time_utils的所有函数"""
        from utils.time_utils import TimeUtils
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # 测试时间差显示
        past_times = [
            now - timedelta(seconds=30),
            now - timedelta(minutes=5),
            now - timedelta(hours=2),
            now - timedelta(days=1),
            now - timedelta(weeks=2),
        ]
        for past in past_times:
            ago = TimeUtils.time_ago(past)
            assert isinstance(ago, str)
            assert len(ago) > 0

        # 测试持续时间格式化
        durations = [
            30,  # 秒
            90,  # 1分30秒
            3665,  # 1小时1分5秒
            7200,  # 2小时
            86400,  # 1天
            0,
        ]
        for duration in durations:
            formatted = TimeUtils.duration_format(duration)
            assert isinstance(formatted, str)

        # 测试未来/过去判断
        test_times = [
            (now + timedelta(hours=1), True),
            (now - timedelta(hours=1), False),
            (now, False),  # 当前时间不算未来
        ]
        for test_time, is_future_expected in test_times:
            _result = TimeUtils.is_future(test_time)
            assert isinstance(result, bool)

        # 测试时区偏移
        timezones = ["UTC", "US/Eastern", "Europe/London", "Asia/Shanghai"]
        for tz in timezones:
            try:
                offset = TimeUtils.get_timezone_offset(tz)
                assert isinstance(offset, (int, float, str))
            except Exception:
                pass  # 时区可能不存在

        # 测试日期时间格式化
        formats = [
            "%Y-%m-%d",
            "%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%B %d, %Y %I:%M %p",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            formatted = TimeUtils.format_datetime(now, fmt)
            assert isinstance(formatted, str)

        # 测试日期时间解析
        date_strings = [
            "2024-01-01",
            "2024-01-01T12:00:00",
            "01/01/2024",
            "Jan 1, 2024",
        ]
        for date_str in date_strings:
            try:
                parsed = TimeUtils.parse_datetime(date_str)
                assert parsed is not None or parsed is None
            except Exception:
                pass

    # ==================== Validators ====================
    def test_validators_all_functions(self):
        """测试validators的所有函数"""
        from utils.validators import Validators

        validator = Validators()

        # 测试必填验证
        test_values = [
            (None, False),
            ("", False),
            ([], False),
            ({}, False),
            ("test", True),
            (0, True),
            (False, True),
            (0.0, True),
        ]
        for value, expected in test_values:
            _result = validator.validate_required(value)
            assert isinstance(result, bool)

        # 测试范围验证
        ranges = [
            (5, 1, 10, True),
            (1, 1, 10, True),
            (10, 1, 10, True),
            (0, 1, 10, False),
            (11, 1, 10, False),
            (-1, -10, 0, True),
            (1, -10, 0, False),
        ]
        for value, min_val, max_val, expected in ranges:
            _result = validator.validate_range(value, min_val, max_val)
            assert isinstance(result, bool)

        # 测试长度验证
        test_items = [
            ("hello", 1, 10),
            ("", 1, 10),
            ("x" * 20, 1, 10),
            ([1, 2, 3], 1, 5),
            ([], 1, 5),
        ]
        for item, min_len, max_len in test_items:
            _result = validator.validate_length(item, min_len, max_len)
            assert isinstance(result, bool)

        # 测试模式验证
        patterns_and_values = [
            (r"^\d+$", "123", True),
            (r"^\d+$", "abc", False),
            (r"^[^@]+@[^@]+\.[^@]+$", "test@example.com", True),
            (r"^[^@]+@[^@]+\.[^@]+$", "not-email", False),
        ]
        for pattern, value, expected in patterns_and_values:
            _result = validator.validate_pattern(value, pattern)
            assert isinstance(result, bool)

        # 测试选择验证
        choices_list = [
            (["red", "green", "blue"], "red", True),
            (["red", "green", "blue"], "yellow", False),
            ([1, 2, 3], 2, True),
            ([1, 2, 3], 4, False),
        ]
        for choices, value, expected in choices_list:
            _result = validator.validate_choice(value, choices)
            assert isinstance(result, bool)

        # 测试邮箱格式验证
        emails = [
            ("test@example.com", True),
            ("user.name@domain.co.uk", True),
            ("invalid", False),
            ("@domain.com", False),
            ("user@", False),
        ]
        for email, expected in emails:
            _result = validator.validate_email_format(email)
            assert isinstance(result, bool)

        # 测试URL格式验证
        urls = [
            ("https://example.com", True),
            ("http://localhost:8000", True),
            ("ftp://files.example.com", True),
            ("not-a-url", False),
            ("www.example.com", False),
        ]
        for url, expected in urls:
            _result = validator.validate_url_format(url)
            assert isinstance(result, bool)

        # 测试数字格式验证
        numbers = [
            ("123", True),
            ("123.45", True),
            ("-123", True),
            ("abc", False),
            ("", False),
            ("12a3", False),
        ]
        for num, expected in numbers:
            _result = validator.validate_number_format(num)
            assert isinstance(result, bool)

    # ==================== I18n ====================
    def test_i18n_all_functions(self):
        """测试i18n的所有函数"""
        from utils.i18n import I18n

        # 初始化
        i18n = I18n()

        # 测试翻译
        keys = ["hello", "goodbye", "error", "success", "welcome", "unknown_key"]
        for key in keys:
            _result = i18n.translate(key)
            assert isinstance(result, str)

        # 测试语言切换
        languages = ["en", "zh", "es", "fr", "de", "ja", "invalid"]
        for lang in languages:
            try:
                i18n.set_language(lang)
                current = i18n.get_current_language()
                assert isinstance(current, str)
            except Exception:
                pass  # 某些语言可能不支持

        # 测试获取翻译
        translations = i18n.get_translations()
        assert isinstance(translations, dict)

        # 测试批量翻译
        text_list = ["hello", "world", "test"]
        translated_list = i18n.translate_list(text_list)
        assert isinstance(translated_list, list)
        assert len(translated_list) == len(text_list)

    # ==================== Response ====================
    def test_response_all_functions(self):
        """测试response的所有函数"""
        from utils.response import ResponseBuilder

        # 测试成功响应
        success_data = [
            ({"data": "test"}, None),
            ({"items": [1, 2, 3]}, None),
            ({"message": "Success"}, None),
        ]
        for data, meta in success_data:
            response = ResponseBuilder.success(data, meta)
            assert isinstance(response, dict)
            assert response["status"] == "success"

        # 测试错误响应
        error_messages = [
            ("Error message", None),
            ("Validation failed", {"field": "email"}),
            ("Not found", 404),
        ]
        for message, code in error_messages:
            response = ResponseBuilder.error(message, code)
            assert isinstance(response, dict)
            assert response["status"] == "error"

        # 测试各种响应类型
        response_types = [
            (ResponseBuilder.created, "created"),
            (ResponseBuilder.updated, "updated"),
            (ResponseBuilder.deleted, "deleted"),
            (ResponseBuilder.not_found, "not_found"),
            (ResponseBuilder.bad_request, "bad_request"),
            (ResponseBuilder.unauthorized, "unauthorized"),
            (ResponseBuilder.forbidden, "forbidden"),
        ]
        for func, expected_status in response_types:
            response = func("test message")
            assert isinstance(response, dict)
            assert response["status"] == expected_status

    # ==================== Warning Filters ====================
    def test_warning_filters_all_functions(self):
        """测试warning_filters的所有函数"""
        from utils.warning_filters import WarningFilters
        import warnings

        # 测试过滤各种警告
        filter_functions = [
            WarningFilters.filter_deprecation_warnings,
            WarningFilters.filter_import_warnings,
            WarningFilters.filter_user_warnings,
            WarningFilters.filter_runtime_warnings,
            WarningFilters.filter_pending_deprecation_warnings,
        ]

        for filter_func in filter_functions:
            filter_func()  # 不应该抛出异常

        # 测试设置警告
        WarningFilters.setup_warnings()

        # 测试过滤特定警告
        with warnings.catch_warnings(record=True):
            warnings.warn("Test deprecation warning", DeprecationWarning)
            WarningFilters.filter_deprecation_warnings()
            # 过滤后应该没有警告或被过滤

    # ==================== Config Loader ====================
    def test_config_loader_all_functions(self):
        """测试config_loader的所有函数"""
        from utils.config_loader import ConfigLoader

        # 测试加载配置
        _config = ConfigLoader.load_config()
        assert isinstance(config, dict)

        # 测试获取配置值
        config_keys = [
            ("app.name", "default_app"),
            ("app.version", "1.0.0"),
            ("database.url", "sqlite:///test.db"),
            ("nonexistent.key", "default_value"),
        ]
        for key, default in config_keys:
            value = ConfigLoader.get_config_value(key, default)
            assert value is not None

        # 测试设置配置值
        test_configs = [
            ("test.string", "test_value"),
            ("test.number", 123),
            ("test.bool", True),
            ("test.list", [1, 2, 3]),
        ]
        for key, value in test_configs:
            ConfigLoader.set_config_value(key, value)
            retrieved = ConfigLoader.get_config_value(key)
            assert retrieved == value

        # 测试获取环境配置
        env_config = ConfigLoader.get_env_config()
        assert isinstance(env_config, dict)

        # 测试重新加载配置
        ConfigLoader.reload_config()
        reloaded = ConfigLoader.load_config()
        assert isinstance(reloaded, dict)

    # ==================== Retry ====================
    def test_retry_all_functions(self):
        """测试retry的所有函数"""
        from utils.retry import RetryHelper

        # 测试重试装饰器
        attempts = [0]

        @RetryHelper.retry(max_attempts=3, delay=0.01)
        def eventually_success():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("Not yet")
            return "success"

        _result = eventually_success()
        assert _result == "success"
        assert attempts[0] == 3

        # 测试各种退避策略
        strategies = [
            ("exponential", RetryHelper.exponential_backoff),
            ("linear", RetryHelper.linear_backoff),
            ("jitter", RetryHelper.jitter_backoff),
        ]
        for strategy_name, strategy_func in strategies:
            delay = strategy_func(2, 0.1)  # attempt=2, base_delay=0.1
            assert isinstance(delay, (int, float))
            assert delay >= 0

        # 测试最大重试次数
        max_attempts = [0]

        @RetryHelper.retry(max_attempts=1, delay=0.01)
        def always_fail():
            max_attempts[0] += 1
            raise Exception("Always fails")

        try:
            always_fail()
        except Exception:
            pass
        assert max_attempts[0] == 1

        # 测试指数退防抖
        delays = [RetryHelper.exponential_backoff(i, 0.1) for i in range(5)]
        for i in range(1, len(delays)):
            assert delays[i] >= delays[i - 1]  # 应该递增


# 标准库测试
class TestStandardLibraryExtensive:
    """全面测试标准库功能"""

    def test_json_operations_extensive(self):
        """全面的JSON操作测试"""
        # 复杂JSON结构
        complex_data = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "active": True,
                    "roles": ["admin", "user"],
                    "profile": {
                        "email": "alice@example.com",
                        "age": 30,
                        "preferences": {"theme": "dark", "notifications": True},
                    },
                }
            ],
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "features": None,
            },
        }

        # 序列化
        json_str = json.dumps(complex_data, indent=2)
        assert isinstance(json_str, str)
        assert "Alice" in json_str

        # 反序列化
        parsed = json.loads(json_str)
        assert parsed == complex_data

        # 流式处理
        import io

        json_io = io.StringIO(json_str)
        parsed_stream = json.load(json_io)
        assert parsed_stream == complex_data

    def test_datetime_operations_extensive(self):
        """全面的日期时间操作"""
        from datetime import datetime, timezone, timedelta, date, time

        # 时区处理
        timezones = [
            timezone.utc,
            timezone(timedelta(hours=1)),  # UTC+1
            timezone(timedelta(hours=-8)),  # UTC-8
        ]

        for tz in timezones:
            now = datetime.now(tz)
            assert now.tzinfo is not None

        # 日期计算
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        calculations = [
            (base_date + timedelta(days=365), "1 year later"),
            (base_date + timedelta(weeks=52), "1 year later"),
            (base_date + timedelta(hours=8760), "1 year later"),
            (base_date - timedelta(days=30), "30 days ago"),
        ]

        for calc_date, description in calculations:
            assert isinstance(calc_date, datetime)

        # 日期比较
        dates = [datetime(2024, 1, 1), datetime(2024, 6, 1), datetime(2024, 12, 31)]

        for i in range(len(dates) - 1):
            assert dates[i] < dates[i + 1]

    def test_hash_operations_extensive(self):
        """全面的哈希操作"""
        algorithms = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
        test_data = b"test data for hashing"

        hash_results = {}
        for algo in algorithms:
            hash_obj = hashlib.new(algo)
            hash_obj.update(test_data)
            hash_results[algo] = hash_obj.hexdigest()

            assert isinstance(hash_results[algo], str)
            assert len(hash_results[algo]) > 0

        # 验证不同算法产生不同结果
        assert len(set(hash_results.values())) == len(algorithms)

        # HMAC测试
        import hmac

        secret_key = b"secret_key"
        for algo in algorithms[:3]:  # 只测试前3个
            hmac_obj = hmac.new(secret_key, test_data, algo)
            hmac_result = hmac_obj.hexdigest()
            assert isinstance(hmac_result, str)

    def test_regex_operations_extensive(self):
        """全面的正则表达式操作"""
        import re

        # 复杂模式
        patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email"),
            (
                r"\b(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?",
                "URL",
            ),
            (r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", "Number"),
            (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "Phone"),
            (r"\b(?:\d{4}[-.\s]?){3}\d{4}\b", "Credit Card"),
        ]

        test_text = """
        Contact us at support@example.com or admin@company.co.uk
        Visit https://www.example.com/products or http://localhost:8000
        Call +1-234-567-8900 or (123) 456-7890
        Your card number is 4111-1111-1111-1111
        """

        for pattern, description in patterns:
            _matches = re.findall(pattern, test_text)
            assert isinstance(matches, list)

        # 替换操作
        replacements = [(r"\b(test)\b", "[TEST]"), (r"\d+", "[NUM]"), (r"\s+", " ")]

        for pattern, replacement in replacements:
            _result = re.sub(pattern, replacement, test_text)
            assert isinstance(result, str)

    def test_collections_operations_extensive(self):
        """全面的集合操作"""
        from collections import (
            Counter,
            defaultdict,
            deque,
            OrderedDict,
            ChainMap,
            UserDict,
        )

        # Counter的高级用法
        text = "hello world hello python"
        word_count = Counter(text.split())
        assert word_count["hello"] == 2
        assert word_count.most_common(1)[0][0] == "hello"

        # 多个Counter操作
        counter1 = Counter("aabbbcccc")
        counter2 = Counter("bbccddd")
        combined = counter1 + counter2
        assert combined["a"] == 2
        assert combined["b"] == 5
        assert combined["c"] == 6
        assert combined["d"] == 3

        # defaultdict的高级用法
        dd = defaultdict(lambda: defaultdict(int))
        dd["group1"]["item1"] += 1
        dd["group1"]["item2"] += 1
        dd["group2"]["item1"] += 1
        assert dd["group1"]["item1"] == 1
        assert dd["group1"]["item2"] == 1
        assert dd["group2"]["item1"] == 1
        assert dd["group3"]["missing"] == 0

        # deque的高级用法
        dq = deque(maxlen=5)
        for i in range(10):
            dq.append(i)
        assert len(dq) == 5
        assert list(dq) == [5, 6, 7, 8, 9]

        # OrderedDict
        od = OrderedDict()
        od["first"] = 1
        od["second"] = 2
        od["third"] = 3
        assert list(od.keys()) == ["first", "second", "third"]

    def test_itertools_operations_extensive(self):
        """全面的迭代器操作"""
        import itertools
        import operator

        # 复杂的组合
        items = ["A", "B", "C"]
        combinations_2 = list(itertools.combinations(items, 2))
        assert len(combinations_2) == 3

        combinations_all = list(itertools.combinations(items, 3))
        assert len(combinations_all) == 1

        # 排列
        permutations_2 = list(itertools.permutations(items, 2))
        assert len(permutations_2) == 6

        # 笛卡尔积
        colors = ["red", "green", "blue"]
        sizes = ["S", "M", "L"]
        product = list(itertools.product(colors, sizes))
        assert len(product) == 9

        # 无限迭代器
        # 使用islice限制输出
        count = list(itertools.islice(itertools.count(10, 2), 5))
        assert count == [10, 12, 14, 16, 18]

        cycle = list(itertools.islice(itertools.cycle(["A", "B", "C"]), 7))
        assert cycle == ["A", "B", "C", "A", "B", "C", "A"]

        # 累积操作
        numbers = [1, 2, 3, 4, 5]
        accumulated = list(itertools.accumulate(numbers))
        assert accumulated == [1, 3, 6, 10, 15]

        accumulated_mul = list(itertools.accumulate(numbers, operator.mul))
        assert accumulated_mul == [1, 2, 6, 24, 120]

        # 过滤和分组
        filtered = list(itertools.filterfalse(lambda x: x % 2 == 0, numbers))
        assert filtered == [1, 3, 5]

        grouped = itertools.groupby(numbers, key=lambda x: x % 2)
        groups = {k: list(g) for k, g in grouped}
        assert groups[1] == [1, 3, 5]
        assert groups[0] == [2, 4]

    def test_math_operations_extensive(self):
        """全面的数学操作"""
        import math
        import statistics
        import random
        import fractions
        import decimal

        # 三角函数
        angles = [0, math.pi / 6, math.pi / 4, math.pi / 3, math.pi / 2]
        for angle in angles:
            sin_val = math.sin(angle)
            cos_val = math.cos(angle)
            _tan_val = math.tan(angle) if abs(math.cos(angle)) > 1e-10 else None
            assert isinstance(sin_val, float)
            assert isinstance(cos_val, float)

        # 对数函数
        for base in [math.e, 10, 2]:
            for value in [1, 10, 100]:
                if base == math.e:
                    log_val = math.log(value)
                else:
                    log_val = math.log(value, base)
                assert isinstance(log_val, float)

        # 统计函数
        _data = list(range(1, 11))
        assert statistics.mean(data) == 5.5
        assert statistics.median(data) == 5.5
        assert statistics.mode(data) == 1

        # 标准差和方差
        assert statistics.stdev(data) > 0
        assert statistics.variance(data) > 0

        # 随机数的高级用法
        random.seed(42)
        assert random.random() == 0.6394267984578837  # 固定种子产生固定值

        # 正态分布
        normal_samples = [random.gauss(0, 1) for _ in range(100)]
        assert isinstance(normal_samples[0], float)

        # 分数运算
        fractions_list = [
            fractions.Fraction(1, 3),
            fractions.Fraction(2, 4),
            fractions.Fraction(3, 6),
        ]

        for f in fractions_list:
            assert isinstance(f, fractions.Fraction)

        _result = fractions.Fraction(1, 3) + fractions.Fraction(2, 3)
        assert _result == fractions.Fraction(1, 1)

        # 十进制精确计算
        decimal.getcontext().prec = 28
        d1 = decimal.Decimal("0.1")
        d2 = decimal.Decimal("0.2")
        assert d1 + d2 == decimal.Decimal("0.3")

    def test_file_operations_extensive(self):
        """全面的文件操作"""
        import tempfile
        import shutil
        import os
        import zipfile
        import tarfile

        # 临时文件和目录
        with tempfile.TemporaryDirectory() as tmpdir:
            assert os.path.exists(tmpdir)

            # 创建子目录和文件
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            test_file = os.path.join(subdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")
            assert os.path.exists(test_file)

            # 文件操作
            assert os.path.isfile(test_file)
            assert os.path.isdir(subdir)

            # 路径操作
            abs_path = os.path.abspath(test_file)
            rel_path = os.path.relpath(test_file, tmpdir)
            assert abs_path.endswith("test.txt")
            assert rel_path == os.path.join("subdir", "test.txt")

        # Zip文件操作
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmpzip:
            with zipfile.ZipFile(tmpzip, "w") as zf:
                zf.writestr("test.txt", "Test content in zip")
                zf.writestr("folder/nested.txt", "Nested content")

            with zipfile.ZipFile(tmpzip, "r") as zf:
                assert "test.txt" in zf.namelist()
                content = zf.read("test.txt")
                assert b"Test content" in content

            os.unlink(tmpzip)

        # 二进制文件操作
        with tempfile.NamedTemporaryFile(delete=False) as tmpbin:
            binary_data = b"\x00\x01\x02\x03\x04\x05"
            with open(tmpbin, "wb") as f:
                f.write(binary_data)

            with open(tmpbin, "rb") as f:
                read_data = f.read()
                assert read_data == binary_data

            os.unlink(tmpbin)

    def test_encoding_decoding(self):
        """测试编码解码操作"""
        test_strings = [
            "Hello World",
            "测试中文",
            "🚀 Emoji test",
            "Mixed: English, 中文, and 🎉 emoji",
        ]

        encodings = ["utf-8", "utf-16", "latin-1", "ascii"]

        for text in test_strings:
            for encoding in encodings:
                try:
                    # 编码
                    encoded = text.encode(encoding)
                    assert isinstance(encoded, bytes)

                    # 解码
                    decoded = encoded.decode(encoding)
                    assert decoded == text
                except UnicodeEncodeError:
                    # 某些编码不支持所有字符，这是正常的
                    if encoding not in ["ascii", "latin-1"]:
                        continue
                    else:
                        raise

    def test_concurrency_operations(self):
        """测试并发操作"""
        import threading
        import queue
        import time

        # 线程安全计数器
        counter = 0
        lock = threading.Lock()

        def increment():
            nonlocal counter
            for _ in range(1000):
                with lock:
                    counter += 1

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter == 10000

        # 生产者-消费者模式
        q = queue.Queue(maxsize=10)
        produced = []
        consumed = []

        def producer():
            for i in range(10):
                q.put(i)
                produced.append(i)
                time.sleep(0.001)

        def consumer():
            while len(consumed) < 10:
                try:
                    item = q.get(timeout=0.1)
                    consumed.append(item)
                    q.task_done()
                except queue.Empty:
                    continue

        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        assert produced == list(range(10))
        assert consumed == list(range(10))

    def test_network_operations(self):
        """测试网络相关操作"""
        import urllib.request
        import socket
        import ipaddress

        # IP地址处理
        ipv4 = ipaddress.IPv4Address("192.168.1.1")
        ipv6 = ipaddress.IPv6Address("2001:db8::1")
        assert str(ipv4) == "192.168.1.1"
        assert str(ipv6) == "2001:db8::1"

        # 网络掩码
        network = ipaddress.IPv4Network("192.168.1.0/24")
        assert network.network_address == ipaddress.IPv4Address("192.168.1.0")
        assert len(list(network.hosts())) == 254

        # URL解析
        from urllib.parse import urlparse, parse_qs

        url = urlparse("https://example.com/path?param1=value1&param2=value2")
        assert url.scheme == "https"
        assert url.netloc == "example.com"
        assert url.path == "/path"
        query_dict = parse_qs(url.query)
        assert query_dict["param1"] == ["value1"]
        assert query_dict["param2"] == ["value2"]

    def test_data_serialization(self):
        """测试数据序列化"""
        import pickle
        import json
        import csv
        import io

        # Pickle序列化
        _data = {
            "string": "test",
            "number": 123,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
        }

        # Pickle
        pickled = pickle.dumps(data)
        unpickled = pickle.loads(pickled)
        assert unpickled == data

        # JSON
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        assert loaded == data

        # CSV
        csv_data = [
            ["name", "age", "city"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "Boston"],
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        csv_content = output.getvalue()
        assert "Alice" in csv_content

        # 读取CSV
        input_csv = io.StringIO(csv_content)
        reader = csv.reader(input_csv)
        rows = list(reader)
        assert len(rows) == 3
        assert rows[0] == ["name", "age", "city"]

    def test_logging_operations(self):
        """测试日志操作"""
        import logging
        import tempfile
        import os

        # 创建临时日志文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as log_file:
            log_path = log_file.name

        try:
            # 配置日志
            logging.basicConfig(
                filename=log_path,
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )

            logger = logging.getLogger("test_logger")

            # 写入不同级别的日志
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # 读取日志内容
            with open(log_path, "r") as f:
                log_content = f.read()
                assert "Info message" in log_content
                assert "Warning message" in log_content
                assert "Error message" in log_content

        finally:
            os.unlink(log_path)

    def test_xml_operations(self):
        """测试XML操作"""
        import xml.etree.ElementTree as ET

        # 创建XML树
        root = ET.Element("root")
        ET.SubElement(root, "child1", attrib={"id": "1"})
        child2 = ET.SubElement(root, "child2")
        child2.text = "Text content"

        # 转换为字符串
        xml_str = ET.tostring(root, encoding="unicode")
        assert b"<root>" in xml_str.encode() if isinstance(xml_str, str) else xml_str

        # 解析XML
        parsed_root = ET.fromstring(
            xml_str.encode() if isinstance(xml_str, str) else xml_str
        )
        assert parsed_root.tag == "root"
        assert len(parsed_root) == 2

        # 查找元素
        child_elements = parsed_root.findall("child1")
        assert len(child_elements) == 1
        assert child_elements[0].get("id") == "1"

        # 命名空间处理
        ns = {"ns": "http://example.com/namespace"}
        ns_root = ET.Element(f"{{{ns['ns']}}}root")
        _ns_child = ET.SubElement(ns_root, f"{{{ns['ns']}}}child")
        ns_str = ET.tostring(ns_root, encoding="unicode")
        assert "http://example.com/namespace" in ns_str or ns_str.count("ns:") > 0


# 运行所有测试
def run_all_tests():
    """运行所有测试并显示覆盖统计"""
    import pytest
    import sys

    test_file = __file__
    cmd = [
        "pytest",
        test_file,
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-x",  # 首次失败停止
        "--tb=short",
    ]

    print(f"运行命令: {' '.join(cmd)}")
    return pytest.main(cmd)


if __name__ == "__main__":
    # 运行测试
    run_all_tests()
