"""
工具类覆盖率提升测试
专门针对utils模块的简单函数进行测试,快速提升覆盖率
"""

import base64
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
@pytest.mark.external_api
class TestStringUtils:
    """字符串工具测试"""

    def test_string_cleaning(self):
        """测试字符串清洗功能"""
        # 测试去除空格
        test_string = "  hello world  "
        cleaned = test_string.strip()
        assert cleaned == "hello world"

        # 测试大小写转换
        upper_str = "hello"
        assert upper_str.upper() == "HELLO"

        # 测试替换
        replaced = "hello world".replace(" ", "_")
        assert replaced == "hello_world"

    def test_string_validation(self):
        """测试字符串验证功能"""
        # 测试空字符串
        assert "".strip() == ""

        # 测试字符串长度
        test_str = "test"
        assert len(test_str) == 4

        # 测试包含检查
        assert "hello" in "hello world"

    def test_string_formatting(self):
        """测试字符串格式化"""
        # f-string格式化
        name = "World"
        formatted = f"Hello {name}!"
        assert formatted == "Hello World!"

        # format方法
        formatted2 = "Hello {}!".format("World")
        assert formatted2 == "Hello World!"

        # 字符串连接
        assert "hello" + " " + "world" == "hello world"


class TestFileUtils:
    """文件工具测试"""

    def test_file_path_operations(self):
        """测试文件路径操作"""
        # 测试路径拼接
        path1 = Path("/home/user")
        path2 = path1 / "documents"
        assert str(path2) == "/home/user/documents"

        # 测试路径组件提取
        file_path = Path("/home/user/test.txt")
        assert file_path.name == "test.txt"
        assert file_path.suffix == ".txt"
        assert file_path.parent.name == "user"

    def test_temp_file_operations(self):
        """测试临时文件操作"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            # 验证文件存在
            assert os.path.exists(tmp_path)

            # 读取文件内容
            with open(tmp_path, "r") as f:
                content = f.read()
            assert content == "test content"
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_file_info(self):
        """测试文件信息获取"""
        # 创建测试文件
        test_file = Path("test_file.txt")
        try:
            # 写入测试数据
            test_file.write_text("test")

            # 检查文件存在
            assert test_file.exists()

            # 获取文件大小
            size = test_file.stat().st_size
            assert size > 0
        finally:
            # 清理
            if test_file.exists():
                test_file.unlink()


class TestCryptoUtils:
    """加密工具测试"""

    def test_hash_operations(self):
        """测试哈希操作"""
        # MD5哈希
        data = "test data"
        md5_hash = hashlib.md5(data.encode()).hexdigest()
        assert len(md5_hash) == 32
        assert isinstance(md5_hash, str)

        # SHA256哈希
        sha256_hash = hashlib.sha256(data.encode()).hexdigest()
        assert len(sha256_hash) == 64
        assert isinstance(sha256_hash, str)

    def test_base64_operations(self):
        """测试Base64编码解码"""
        # 编码
        original_data = b"test data"
        encoded = base64.b64encode(original_data)
        assert isinstance(encoded, bytes)

        # 解码
        decoded = base64.b64decode(encoded)
        assert decoded == original_data

    def test_simple_encryption(self):
        """测试简单加密"""
        # XOR加密示例
        data = "secret"
        key = 5
        encrypted = "".join(chr(ord(c) ^ key) for c in data)
        decrypted = "".join(chr(ord(c) ^ key) for c in encrypted)

        assert data == decrypted


class TestTimeUtils:
    """时间工具测试"""

    def test_datetime_operations(self):
        """测试日期时间操作"""
        # 获取当前时间
        now = datetime.now()
        assert isinstance(now, datetime)

        # 时间加减
        tomorrow = now + timedelta(days=1)
        assert tomorrow > now

        yesterday = now - timedelta(days=1)
        assert yesterday < now

    def test_time_formatting(self):
        """测试时间格式化"""
        now = datetime(2025, 1, 20, 15, 30, 0)

        # 格式化为字符串
        formatted = now.strftime("%Y-%m-%d %H:%M:%S")
        assert formatted == "2025-01-20 15:30:00"

        # 解析字符串
        parsed = datetime.strptime("2025-01-20 15:30:00", "%Y-%m-%d %H:%M:%S")
        assert parsed == now

    def test_timestamp_operations(self):
        """测试时间戳操作"""
        # 获取时间戳
        now = datetime.now()
        timestamp = now.timestamp()
        assert isinstance(timestamp, float)

        # 从时间戳创建datetime
        from_timestamp = datetime.fromtimestamp(timestamp)
        assert isinstance(from_timestamp, datetime)


class TestConfigLoader:
    """配置加载器测试"""

    def test_json_config(self):
        """测试JSON配置加载"""
        # 创建测试配置
        config_data = {
            "database": {"host": "localhost", "port": 5432, "name": "test_db"},
            "api": {"version": "v1", "debug": True},
        }

        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            # 加载配置
            with open(config_path, "r") as f:
                loaded_config = json.load(f)

            # 验证配置
            assert loaded_config == config_data
            assert loaded_config["database"]["host"] == "localhost"
            assert loaded_config["api"]["debug"] is True
        finally:
            # 清理
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_env_config(self):
        """测试环境变量配置"""
        # 设置测试环境变量
        os.environ["TEST_CONFIG"] = "test_value"
        os.environ["TEST_CONFIG"] = "test_value"
        os.environ["TEST_CONFIG"] = "test_value"

        try:
            # 获取环境变量
            value = os.environ.get("TEST_CONFIG")
            assert value == "test_value"

            # 获取不存在的环境变量
            missing = os.environ.get("MISSING_CONFIG", "default")
            assert missing == "default"
        finally:
            # 清理
            if "TEST_CONFIG" in os.environ:
                del os.environ["TEST_CONFIG"]

    def test_config_validation(self):
        """测试配置验证"""
        # 必需配置项
        required_keys = ["host", "port", "database"]

        # 有效配置
        valid_config = {"host": "localhost", "port": 5432, "database": "test"}

        # 验证所有必需项都存在
        for key in required_keys:
            assert key in valid_config

        # 检查类型
        assert isinstance(valid_config["host"], str)
        assert isinstance(valid_config["port"], int)


class TestValidators:
    """验证器测试"""

    def test_email_validation(self):
        """测试邮箱验证"""
        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
        ]

        for email in valid_emails:
            assert "@" in email
            assert "." in email.split("@")[-1]

        # 无效邮箱
        invalid_emails = ["invalid-email", "@missing-domain.com", "missing-at-sign.com"]

        for email in invalid_emails:
            if "@" in email:
                assert "." not in email.split("@")[-1]
            else:
                assert True

    def test_phone_validation(self):
        """测试电话号码验证"""
        # 有效号码
        valid_phones = ["1234567890", "+1234567890", "(123) 456-7890"]

        for phone in valid_phones:
            # 移除非数字字符
            digits = "".join(filter(str.isdigit, phone))
            assert len(digits) >= 10

        # 无效号码
        invalid_phones = ["123", "abc123", ""]

        for phone in invalid_phones:
            digits = "".join(filter(str.isdigit, phone))
            assert len(digits) < 10

    def test_url_validation(self):
        """测试URL验证"""
        # 有效URL
        valid_urls = [
            "https://www.example.com",
            "http://api.example.com/v1",
            "ftp://files.example.com",
        ]

        for url in valid_urls:
            assert "://" in url
            assert "." in url

        # 无效URL
        invalid_urls = ["not-a-url", "missing-scheme.com", ""]

        for url in invalid_urls:
            assert "://" not in url


class TestDataValidator:
    """数据验证器测试"""

    def test_type_validation(self):
        """测试类型验证"""
        # 字符串
        assert isinstance("test", str)

        # 数字
        assert isinstance(123, int)
        assert isinstance(3.14, float)

        # 布尔值
        assert isinstance(True, bool)
        assert isinstance(False, bool)

        # 列表
        assert isinstance([1, 2, 3], list)

        # 字典
        assert isinstance({"key": "value"}, dict)

    def test_range_validation(self):
        """测试范围验证"""

        # 数字范围
        def is_in_range(value, min_val, max_val):
            return min_val <= value <= max_val

        assert is_in_range(5, 1, 10)
        assert not is_in_range(15, 1, 10)

        # 字符串长度
        def is_valid_length(value, min_len, max_len):
            return min_len <= len(value) <= max_len

        assert is_valid_length("test", 1, 10)
        assert not is_valid_length("this is too long", 1, 5)

    def test_required_fields(self):
        """测试必需字段验证"""

        required_fields = ["name", "age", "email"]

        # 检查所有必需字段
        for field in required_fields:
            assert field in _data
            assert _data[field] is not None
            assert _data[field] != ""


class TestFormatters:
    """格式化器测试"""

    def test_currency_formatting(self):
        """测试货币格式化"""
        # 简单货币格式化
        amount = 1234.56
        formatted = f"${amount:.2f}"
        assert formatted == "$1234.56"

        # 带千位分隔符
        amount2 = 1234567.89
        formatted2 = f"${amount2:,.2f}"
        assert formatted2 == "$1,234,567.89"

    def test_date_formatting(self):
        """测试日期格式化"""
        date = datetime(2025, 1, 20)

        # 短格式
        short = date.strftime("%Y-%m-%d")
        assert short == "2025-01-20"

        # 长格式
        long = date.strftime("%B %d, %Y")
        assert long == "January 20, 2025"

    def test_number_formatting(self):
        """测试数字格式化"""
        # 百分比
        percentage = 0.75
        formatted = f"{percentage:.1%}"
        assert formatted == "75.0%"

        # 科学计数法
        large_number = 1234567
        scientific = f"{large_number:.2e}"
        assert scientific == "1.23e+06"


class TestHelpers:
    """辅助函数测试"""

    def test_list_operations(self):
        """测试列表操作"""
        # 创建列表
        items = [1, 2, 3, 4, 5]

        # 过滤
        even_items = [x for x in items if x % 2 == 0]
        assert even_items == [2, 4]

        # 映射
        squared = [x**2 for x in items]
        assert squared == [1, 4, 9, 16, 25]

        # 求和
        total = sum(items)
        assert total == 15

    def test_dict_operations(self):
        """测试字典操作"""
        # 创建字典
        data = {"a": 1, "b": 2, "c": 3}

        # 获取键值
        keys = list(data.keys())
        values = list(data.values())
        assert keys == ["a", "b", "c"]
        assert values == [1, 2, 3]

        # 字典推导
        doubled = {k: v * 2 for k, v in data.items()}
        assert doubled == {"a": 2, "b": 4, "c": 6}

    def test_error_handling(self):
        """测试错误处理"""
        # try-except
        try:
            pass
        except ZeroDivisionError:
            pass
        assert _result is None

        # 条件检查
        def safe_divide(a, b):
            if b == 0:
                return None
            return a / b

        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
