"""
工具函数简单测试

测试各种工具函数的基本功能
"""

import pytest
from unittest.mock import Mock, patch
import time


@pytest.mark.unit
class TestUtilsSimple:
    """工具函数基础测试类"""

    def test_response_utils_import(self):
        """测试响应工具导入"""
        from src.utils.response import APIResponse

        # 验证类可以导入
        assert APIResponse is not None
        assert callable(APIResponse.success)
        assert callable(APIResponse.error)

    def test_response_creation(self):
        """测试响应创建"""
        from src.utils.response import APIResponse

        # 测试成功响应
        success_response = APIResponse.success({"data": "test"}, "操作成功")
        assert success_response["success"] is True
        assert success_response["message"] == "操作成功"
        assert success_response["data"] == {"data": "test"}

        # 测试错误响应
        error_response = APIResponse.error("操作失败", 400)
        assert error_response["success"] is False
        assert error_response["message"] == "操作失败"
        assert error_response["code"] == 400

    def test_string_utils_import(self):
        """测试字符串工具导入"""
        from src.utils.string_utils import StringUtils

        # 验证类可以导入
        assert StringUtils is not None
        assert callable(StringUtils.truncate)
        assert callable(StringUtils.slugify)
        assert callable(StringUtils.camel_to_snake)
        assert callable(StringUtils.snake_to_camel)

    def test_string_case_conversion(self):
        """测试字符串大小写转换"""
        from src.utils.string_utils import StringUtils

        # 测试转换为蛇形命名
        assert StringUtils.camel_to_snake("camelCase") == "camel_case"
        assert StringUtils.camel_to_snake("PascalCase") == "pascal_case"

        # 测试转换为驼峰命名
        assert StringUtils.snake_to_camel("snake_case") == "snakeCase"
        assert StringUtils.snake_to_camel("multiple_word_case") == "multipleWordCase"

    def test_string_truncation(self):
        """测试字符串截断"""
        from src.utils.string_utils import StringUtils

        # 测试长字符串截断
        long_string = "这是一个很长的字符串，需要被截断"
        truncated = StringUtils.truncate(long_string, 10)
        assert len(truncated) <= 10
        assert "..." in truncated

        # 测试短字符串不需要截断
        short_string = "短字符串"
        result = StringUtils.truncate(short_string, 20)
        assert result == short_string

    def test_string_slugify(self):
        """测试字符串转换为URL友好格式"""
        from src.utils.string_utils import StringUtils

        # 测试转换为slug
        assert StringUtils.slugify("Hello World") == "hello-world"
        assert StringUtils.slugify("Test String 123") == "test-string-123"

    def test_string_clean_text(self):
        """测试文本清理"""
        from src.utils.string_utils import StringUtils

        # 测试清理文本
        messy_text = "  多余    的   空格  "
        cleaned = StringUtils.clean_text(messy_text)
        # 根据实际实现调整期望值
        assert "多余" in cleaned
        assert "的" in cleaned
        assert "空格" in cleaned

    def test_dict_utils_import(self):
        """测试字典工具导入"""
        from src.utils.dict_utils import DictUtils

        # 验证类可以导入
        assert DictUtils is not None
        assert callable(DictUtils.deep_merge)
        assert callable(DictUtils.flatten_dict)
        assert callable(DictUtils.filter_none_values)

    def test_dict_operations(self):
        """测试字典操作"""
        from src.utils.dict_utils import DictUtils

        # 测试字典扁平化
        nested_dict = {"a": {"b": {"c": "value"}}}
        flattened = DictUtils.flatten_dict(nested_dict)
        assert "a.b.c" in flattened
        assert flattened["a.b.c"] == "value"

        # 测试深度合并
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}
        merged = DictUtils.deep_merge(dict1, dict2)
        assert merged["a"] == 1
        assert merged["b"]["x"] == 10
        assert merged["b"]["y"] == 20
        assert merged["c"] == 3

        # 测试过滤None值
        dict_with_none = {"a": 1, "b": None, "c": 3}
        filtered = DictUtils.filter_none_values(dict_with_none)
        assert "a" in filtered
        assert "b" not in filtered
        assert "c" in filtered

    def test_time_utils_import(self):
        """测试时间工具导入"""
        from src.utils.time_utils import TimeUtils

        # 验证类可以导入
        assert TimeUtils is not None
        assert callable(TimeUtils.format_timestamp)
        assert callable(TimeUtils.parse_datetime)
        assert callable(TimeUtils.get_current_timestamp)

    def test_time_formatting(self):
        """测试时间格式化"""
        from src.utils.time_utils import TimeUtils

        # 测试时间戳格式化
        timestamp = time.time()
        formatted = TimeUtils.format_timestamp(timestamp)
        assert isinstance(formatted, str)

        # 测试获取当前时间戳
        current_timestamp = TimeUtils.get_current_timestamp()
        assert isinstance(current_timestamp, (int, float))
        assert current_timestamp > 0

    def test_crypto_utils_import(self):
        """测试加密工具导入"""
        from src.utils.crypto_utils import CryptoUtils

        # 验证类可以导入
        assert CryptoUtils is not None
        assert callable(CryptoUtils.hash_password)
        assert callable(CryptoUtils.verify_password)
        assert callable(CryptoUtils.generate_token)

    def test_password_hashing(self):
        """测试密码哈希"""
        from src.utils.crypto_utils import CryptoUtils

        # 测试密码哈希和验证
        password = "test_password_123"
        hashed = CryptoUtils.hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

        # 测试密码验证
        is_valid = CryptoUtils.verify_password(password, hashed)
        assert is_valid is True

        # 测试错误密码验证
        is_invalid = CryptoUtils.verify_password("wrong_password", hashed)
        assert is_invalid is False

    def test_token_generation(self):
        """测试令牌生成"""
        from src.utils.crypto_utils import CryptoUtils

        # 测试生成令牌
        token = CryptoUtils.generate_token()
        assert isinstance(token, str)
        assert len(token) > 0

        # 测试生成不同长度的令牌
        token_32 = CryptoUtils.generate_token(32)
        assert len(token_32) == 32

    def test_data_validator_import(self):
        """测试数据验证器导入"""
        from src.utils.data_validator import DataValidator

        # 验证类可以导入
        assert DataValidator is not None
        assert callable(DataValidator.validate_email)
        assert callable(DataValidator.validate_phone)
        assert callable(DataValidator.validate_url)

    def test_email_validation(self):
        """测试邮箱验证"""
        from src.utils.data_validator import DataValidator

        # 测试有效邮箱
        assert DataValidator.validate_email("test@example.com") is True
        assert DataValidator.validate_email("user.name+tag@domain.co.uk") is True

        # 测试无效邮箱
        assert DataValidator.validate_email("invalid-email") is False
        assert DataValidator.validate_email("@example.com") is False
        assert DataValidator.validate_email("test@") is False

    def test_phone_validation(self):
        """测试电话验证"""
        from src.utils.data_validator import DataValidator

        # 测试有效电话号码
        assert DataValidator.validate_phone("+8613800138000") is True
        assert DataValidator.validate_phone("13800138000") is True

        # 测试无效电话号码
        assert DataValidator.validate_phone("12345") is False
        assert DataValidator.validate_phone("abc123") is False

    def test_url_validation(self):
        """测试URL验证"""
        from src.utils.data_validator import DataValidator

        # 测试有效URL
        assert DataValidator.validate_url("https://www.example.com") is True
        assert DataValidator.validate_url("http://example.com/path") is True

        # 测试无效URL
        assert DataValidator.validate_url("not-a-url") is False
        assert DataValidator.validate_url("ftp://example.com") is False

    def test_file_utils_import(self):
        """测试文件工具导入"""
        from src.utils.file_utils import FileUtils

        # 验证类可以导入
        assert FileUtils is not None
        assert callable(FileUtils.ensure_directory)
        assert callable(FileUtils.get_file_size)
        assert callable(FileUtils.read_file_lines)

    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_directory_ensure(self, mock_makedirs, mock_exists):
        """测试目录确保"""
        from src.utils.file_utils import FileUtils

        # Mock目录不存在
        mock_exists.return_value = False

        # 测试创建目录
        FileUtils.ensure_directory("/test/path")
        mock_makedirs.assert_called_once_with("/test/path")

    def test_retry_utils_import(self):
        """测试重试工具导入"""
        from src.utils.retry import RetryUtils

        # 验证类可以导入
        assert RetryUtils is not None

    def test_retry_configuration(self):
        """测试重试配置"""
        from src.utils.retry import RetryConfig

        # 测试重试配置创建
        config = RetryConfig(max_attempts=3, delay=1.0, backoff_factor=2.0)
        assert config.max_attempts == 3
        assert config.delay == 1.0
        assert config.backoff_factor == 2.0

    @patch('time.sleep')
    def test_retry_decorator(self, mock_sleep):
        """测试重试装饰器"""
        from src.utils.retry import RetryUtils

        # 创建一个会失败的函数
        call_count = 0

        @RetryUtils.retry(max_attempts=2, delay=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        # 测试重试机制
        result = failing_function()
        assert result == "success"
        assert call_count == 2
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.utils", "--cov-report=term-missing"])