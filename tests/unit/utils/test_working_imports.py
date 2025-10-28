"""
Utils模块集成测试 - 核心业务功能验证

该文件测试utils包中所有关键模块的实际业务功能，
确保API的正确性和业务逻辑的有效性。
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent.parent.parent / "src"
import sys

sys.path.insert(0, str(src_path))


@pytest.mark.unit
class TestCryptoUtils:
    """加密工具核心功能测试"""

    def test_uuid_generation_unique(self):
        """测试UUID生成的唯一性"""
        from utils.crypto_utils import CryptoUtils

        # 生成多个UUID，确保唯一性
        uuids = [CryptoUtils.generate_uuid() for _ in range(10)]

        # 验证UUID格式
        for uid in uuids:
            assert isinstance(uid, str)
            assert len(uid) == 36
            assert uid.count("-") == 4

        # 验证唯一性
        assert len(set(uuids)) == 10

    def test_short_id_length_control(self):
        """测试短ID长度控制"""
        from utils.crypto_utils import CryptoUtils

        # 测试不同长度
        test_cases = [0, 4, 8, 16, 32, 40]
        for length in test_cases:
            short_id = CryptoUtils.generate_short_id(length)
            assert isinstance(short_id, str)
            assert len(short_id) == length

    def test_hash_algorithms(self):
        """测试不同哈希算法"""
        from utils.crypto_utils import CryptoUtils

        text = "足球预测系统测试"

        # 测试支持的算法
        algorithms = ["md5", "sha1", "sha256"]
        hashes = {}

        for algo in algorithms:
            hash_val = CryptoUtils.hash_string(text, algo)
            hashes[algo] = hash_val
            assert isinstance(hash_val, str)
            assert len(hash_val) > 0

        # 验证相同输入相同算法产生相同输出
        for algo in algorithms:
            hash_val2 = CryptoUtils.hash_string(text, algo)
            assert hash_val2 == hashes[algo]

        # 验证不同算法产生不同输出
        assert len(set(hashes.values())) == len(algorithms)

    def test_password_security(self):
        """测试密码哈希安全性"""
        from utils.crypto_utils import CryptoUtils

        password = "Test@Password123"

        # 测试密码哈希
        hashed = CryptoUtils.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 50
        assert hashed != password  # 不应该等于明文

        # 测试密码验证
        assert CryptoUtils.verify_password(password, hashed) is True
        assert CryptoUtils.verify_password("wrong_password", hashed) is False


@pytest.mark.unit
class TestDataValidation:
    """数据验证核心功能测试"""

    def test_email_validation_comprehensive(self):
        """测试邮箱验证的全面性"""
        from utils.data_validator import DataValidator

        # 有效邮箱
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "user_name@example-domain.com",
            "123@test-domain.com",
        ]

        for email in valid_emails:
            assert (
                DataValidator.is_valid_email(email) is True
            ), f"Should be valid: {email}"

        # 无效邮箱
        invalid_emails = [
            "",
            "not-an-email",
            "@example.com",
            "test@",
            "test@.com",
            "test@example.",
        ]

        for email in invalid_emails:
            assert (
                DataValidator.is_valid_email(email) is False
            ), f"Should be invalid: {email}"

    def test_url_validation(self):
        """测试URL验证"""
        from utils.data_validator import DataValidator

        # 有效URL
        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
            "https://sub.domain.co.uk/path",
            "http://192.168.1.1:3000",
        ]

        for url in valid_urls:
            assert DataValidator.is_valid_url(url) is True, f"Should be valid: {url}"

        # 无效URL
        invalid_urls = [
            "",
            "not-a-url",
            "www.example.com",  # 缺少协议
            "example.com",
            "ftp://invalid-protocol",
        ]

        for url in invalid_urls:
            assert DataValidator.is_valid_url(url) is False, f"Should be invalid: {url}"

    def test_required_fields_validation(self):
        """测试必填字段验证"""
        from utils.data_validator import DataValidator

        # 测试完整数据
        complete_data = {"name": "张三", "age": 25, "email": "zhang@example.com"}
        required_fields = ["name", "age", "email"]
        missing = DataValidator.validate_required_fields(complete_data, required_fields)
        assert len(missing) == 0

        # 测试缺失字段
        incomplete_data = {"name": "李四"}
        missing = DataValidator.validate_required_fields(
            incomplete_data, required_fields
        )
        assert "email" in missing
        assert "age" in missing
        assert len(missing) == 2

        # 测试完全空数据
        empty_data = {}
        missing = DataValidator.validate_required_fields(empty_data, required_fields)
        assert set(missing) == set(required_fields)


@pytest.mark.unit
class TestStringProcessing:
    """字符串处理核心功能测试"""

    def test_string_cleaning(self):
        """测试字符串清理功能"""
        from utils.string_utils import StringUtils

        # 测试基本清理功能
        assert StringUtils.clean_string("  Hello World  ") == "Hello World"
        assert StringUtils.clean_string("") == ""
        assert StringUtils.clean_string("   ") == ""
        assert isinstance(StringUtils.clean_string("test"), str)

    def test_text_truncation(self):
        """测试文本截断功能"""
        from utils.string_utils import StringUtils

        long_text = "这是一个很长的文本，需要被截断处理以测试截断功能是否正常工作"

        # 测试不同长度截断
        lengths = [10, 20, 50]
        for length in lengths:
            truncated = StringUtils.truncate(long_text, length)
            assert isinstance(truncated, str)
            if len(long_text) > length:
                assert "..." in truncated or len(truncated) <= length

    def test_email_phone_validation(self):
        """测试邮箱和手机号验证正则"""
        from utils.string_utils import StringUtils

        # 测试邮箱验证
        assert StringUtils._EMAIL_REGEX.match("test@example.com")
        assert not StringUtils._EMAIL_REGEX.match("invalid-email")

        # 测试手机号验证（中国手机号）
        assert StringUtils._PHONE_REGEX.match("13800138000")
        assert not StringUtils._PHONE_REGEX.match("12800138000")  # 无效号段
        assert not StringUtils._PHONE_REGEX.match("1380013800")  # 长度不够


@pytest.mark.unit
class TestDictOperations:
    """字典操作核心功能测试"""

    def test_deep_merge_complex(self):
        """测试复杂字典深度合并"""
        from utils.dict_utils import DictUtils

        # 测试复杂嵌套结构
        dict1 = {
            "app": {"name": "足球预测", "version": "1.0"},
            "database": {"host": "localhost", "port": 5432},
            "features": ["预测", "分析"],
        }

        dict2 = {
            "app": {"version": "2.0", "author": "AI"},
            "database": {"port": 5433, "name": "football"},
            "cache": {"type": "redis"},
        }

        merged = DictUtils.deep_merge(dict1, dict2)

        # 验证合并结果
        assert merged["app"]["name"] == "足球预测"  # dict1保留
        assert merged["app"]["version"] == "2.0"  # dict2覆盖
        assert merged["app"]["author"] == "AI"  # dict2新增
        assert merged["database"]["host"] == "localhost"  # dict1保留
        assert merged["database"]["port"] == 5433  # dict2覆盖
        assert merged["database"]["name"] == "football"  # dict2新增
        assert merged["features"] == ["预测", "分析"]  # dict1保留
        assert merged["cache"]["type"] == "redis"  # dict2新增

    def test_flatten_dict_structure(self):
        """测试字典扁平化"""
        from utils.dict_utils import DictUtils

        nested = {
            "app": {
                "server": {"host": "localhost", "port": 8000},
                "database": {"name": "football"},
            },
            "features": ["预测", "分析"],
            "settings": {"debug": True},
        }

        flat = DictUtils.flatten_dict(nested)

        # 验证扁平化结果
        assert "app.server.host" in flat
        assert "app.server.port" in flat
        assert "app.database.name" in flat
        assert "features" in flat
        assert "settings.debug" in flat
        assert flat["app.server.host"] == "localhost"
        assert flat["app.server.port"] == 8000
        assert flat["features"] == ["预测", "分析"]

    def test_none_filtering(self):
        """测试None值过滤"""
        from utils.dict_utils import DictUtils

        data = {
            "name": "张三",
            "age": 25,
            "email": None,
            "phone": "",
            "address": None,
            "active": False,
            "score": 0,
        }

        filtered = DictUtils.filter_none_values(data)

        # 验证过滤结果
        assert "name" in filtered
        assert "age" in filtered
        assert "email" not in filtered  # None被过滤
        assert "phone" in filtered  # 空字符串保留
        assert "address" not in filtered  # None被过滤
        assert "active" in filtered  # False保留
        assert "score" in filtered  # 0保留


@pytest.mark.unit
class TestFormatters:
    """格式化工具核心功能测试"""

    def test_datetime_formatting(self):
        """测试日期时间格式化"""
        from utils.formatters import format_datetime

        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 测试不同格式
        formats = [
            ("%Y-%m-%d", "2024-01-15"),
            ("%H:%M:%S", "14:30:45"),
            ("%Y-%m-%d %H:%M:%S", "2024-01-15 14:30:45"),
            ("%Y年%m月%d日", "2024年01月15日"),
        ]

        for fmt, expected in formats:
            formatted = format_datetime(dt, fmt)
            assert formatted == expected

    def test_currency_formatting(self):
        """测试货币格式化"""
        from utils.formatters import format_currency

        test_cases = [
            (123.456, "USD", "123.46 USD"),
            (1000.0, "CNY", "1000.00 CNY"),
            (0.99, "EUR", "0.99 EUR"),
            (500, "JPY", "500.00 JPY"),
        ]

        for amount, currency, expected in test_cases:
            formatted = format_currency(amount, currency)
            assert formatted == expected

    def test_json_formatting(self):
        """测试JSON格式化"""
        from utils.formatters import format_json

        data = {
            "name": "足球预测系统",
            "version": "2.0",
            "features": ["预测", "分析", "统计"],
            "config": {"debug": True, "port": 8000},
        }

        # 测试格式化
        formatted = format_json(data)
        assert isinstance(formatted, str)
        assert "足球预测系统" in formatted
        assert "\n" in formatted  # 应该包含换行符（缩进）

        # 测试无缩进
        compact = format_json(data, indent=None)
        assert "\n" not in compact or compact.count("\n") <= 1


@pytest.mark.unit
class TestApiResponse:
    """API响应工具核心功能测试"""

    def test_success_response_structure(self):
        """测试成功响应结构"""
        from utils.response import APIResponse

        data = {"message": "操作成功", "count": 42}
        response = APIResponse.success(data)

        # 验证响应结构
        assert isinstance(response, dict)
        assert response["success"] is True
        assert "message" in response
        assert "timestamp" in response
        assert response["data"] == data

    def test_error_response_structure(self):
        """测试错误响应结构"""
        from utils.response import APIResponse

        error_msg = "数据验证失败"
        response = APIResponse.error(error_msg)

        # 验证响应结构
        assert isinstance(response, dict)
        assert response["success"] is False
        assert response["message"] == error_msg
        assert "timestamp" in response


@pytest.mark.unit
class TestRetryMechanism:
    """重试机制核心功能测试"""

    def test_retry_imports(self):
        """测试重试模块导入"""
        from utils.retry import retry

        # 验证retry装饰器可以被导入
        assert retry is not None
        assert callable(retry)


@pytest.mark.unit
class TestFileOperations:
    """文件操作核心功能测试"""

    def test_file_operations(self):
        """测试文件操作基础功能"""
        # 测试目录创建
        import tempfile

        from utils.file_utils import FileUtils

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = FileUtils.ensure_dir(os.path.join(temp_dir, "test", "nested"))
            assert nested_dir.exists()
            assert nested_dir.is_dir()

        # 验证FileUtils类存在关键方法
        assert hasattr(FileUtils, "ensure_dir")
        assert hasattr(FileUtils, "get_file_size")
        assert hasattr(FileUtils, "read_json")
        assert hasattr(FileUtils, "write_json")

    def test_json_file_operations(self):
        """测试JSON文件操作"""
        import tempfile

        from utils.file_utils import FileUtils

        test_data = {
            "name": "足球预测系统",
            "version": "2.0",
            "features": ["预测", "分析"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            json_file = os.path.join(temp_dir, "test.json")

            # 测试写入JSON
            FileUtils.write_json(test_data, json_file)
            assert os.path.exists(json_file)

            # 测试读取JSON
            read_data = FileUtils.read_json(json_file)
            assert read_data == test_data

            # 测试文件哈希
            file_hash = FileUtils.get_file_hash(json_file)
            assert isinstance(file_hash, str)
            assert len(file_hash) == 32  # MD5 hash length

    def test_file_size_calculation(self):
        """测试文件大小计算"""
        from utils.file_utils import FileUtils

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                content = "足球预测系统测试内容".encode("utf-8") * 100
                tmp.write(content)
                tmp.flush()

                size = FileUtils.get_file_size(tmp.name)
                assert size == len(content)
                assert size > 0
            finally:
                os.unlink(tmp.name)


@pytest.mark.unit
class TestUtilityFunctions:
    """通用工具函数测试"""

    def test_helper_functions(self):
        """测试helper模块函数"""
        from utils.helpers import generate_hash, generate_uuid, safe_get

        # 测试UUID生成
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1 != uuid2

        # 测试哈希生成
        text = "足球预测"
        hash_md5 = generate_hash(text, "md5")
        hash_sha256 = generate_hash(text, "sha256")
        assert isinstance(hash_md5, str)
        assert isinstance(hash_sha256, str)
        assert hash_md5 != hash_sha256

        # 测试安全获取
        data = {"user": {"profile": {"name": "张三", "age": 25}}}
        assert safe_get(data, "user.profile.name") == "张三"
        assert safe_get(data, "user.profile.email", "unknown") == "unknown"
        assert safe_get(None, "any.key", "default") == "default"

    def test_validator_functions(self):
        """测试validators模块函数"""
        from utils.validators import is_valid_email, is_valid_phone, is_valid_url

        # 测试邮箱验证
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("invalid-email") is False

        # 测试手机号验证
        assert is_valid_phone("+86 138 0013 8000") is True
        assert is_valid_phone("123-456-7890") is True
        assert is_valid_phone("abc") is False

        # 测试URL验证
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://localhost:8000") is True
        assert is_valid_url("not-a-url") is False

    def test_required_fields_and_types_validation(self):
        """测试必填字段和类型验证"""
        from utils.validators import validate_data_types, validate_required_fields

        # 测试必填字段验证
        data = {"name": "张三", "age": 25}
        required = ["name", "age", "email"]
        missing = validate_required_fields(data, required)
        assert missing == ["email"]

        # 测试类型验证
        schema = {"name": str, "age": int, "active": bool}
        valid_data = {"name": "李四", "age": 30, "active": True}
        invalid_data = {"name": 123, "age": "30", "active": "true"}

        valid_errors = validate_data_types(valid_data, schema)
        invalid_errors = validate_data_types(invalid_data, schema)

        assert len(valid_errors) == 0
        assert len(invalid_errors) == 3  # 所有字段类型都不匹配


@pytest.mark.unit
class TestTimeOperations:
    """时间操作核心功能测试"""

    def test_time_utils_basic_functions(self):
        """测试时间工具基础功能"""
        from utils.time_utils import TimeUtils, parse_datetime, utc_now

        # 测试TimeUtils类
        now_utc = TimeUtils.now_utc()
        assert isinstance(now_utc, datetime)
        assert now_utc.tzinfo == timezone.utc

        # 测试格式化
        formatted = TimeUtils.format_datetime(now_utc, "%Y-%m-%d")
        assert isinstance(formatted, str)
        assert len(formatted) == 10  # YYYY-MM-DD

        # 测试时间戳转换
        timestamp = TimeUtils.datetime_to_timestamp(now_utc)
        back_to_dt = TimeUtils.timestamp_to_datetime(timestamp)
        assert isinstance(back_to_dt, datetime)
        assert back_to_dt.tzinfo == timezone.utc

        # 测试函数式API
        utc_func = utc_now()
        assert isinstance(utc_func, datetime)
        assert utc_func.tzinfo == timezone.utc

        # 测试解析函数
        parsed = parse_datetime("2024-01-15 14:30:00")
        assert parsed is not None
        assert isinstance(parsed, datetime)
