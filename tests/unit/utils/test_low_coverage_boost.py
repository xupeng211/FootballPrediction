"""工具模块单元测试 - 覆盖率提升专用"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.utils.config_loader import load_config_from_file
from src.utils.crypto_utils import CryptoUtils
from src.utils.file_utils import FileUtils
from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_data_types,
    validate_required_fields,
)
from src.utils.warning_filters import setup_warning_filters


@pytest.mark.unit
class TestConfigLoader:
    """配置加载器测试"""

    def test_load_json_config_success(self):
        """测试成功加载JSON配置"""
        test_config = {"database": {"url": "sqlite:///test.db"}, "api": {"port": 8000}}

        with patch("builtins.open", mock_open(read_data=json.dumps(test_config))):
            with patch("os.path.exists", return_value=True):
                result = load_config_from_file("config.json")
                assert result == test_config

    def test_load_yaml_config_success(self):
        """测试成功加载YAML配置"""
        test_config = {
            "database": {"url": "postgresql://localhost"},
            "redis": {"host": "localhost"},
        }

        with patch(
            "builtins.open",
            mock_open(
                read_data="database:\n  url: postgresql://localhost\nredis:\n  host: localhost"
            ),
        ):
            with patch("os.path.exists", return_value=True):
                with patch("yaml.safe_load", return_value=test_config):
                    result = load_config_from_file("config.yaml")
                    assert result == test_config

    def test_load_config_file_not_exists(self):
        """测试文件不存在时返回空字典"""
        with patch("os.path.exists", return_value=False):
            result = load_config_from_file("nonexistent.json")
            assert result == {}

    def test_load_config_invalid_json(self):
        """测试无效JSON文件"""
        with patch("builtins.open", mock_open(read_data="invalid json content")):
            with patch("os.path.exists", return_value=True):
                result = load_config_from_file("invalid.json")
                assert result == {}

    def test_load_config_unsupported_format(self):
        """测试不支持的文件格式"""
        with patch("builtins.open", mock_open(read_data="some content")):
            with patch("os.path.exists", return_value=True):
                result = load_config_from_file("config.txt")
                assert result == {}

    def test_load_config_yaml_import_error(self):
        """测试YAML模块导入错误"""
        with patch("builtins.open", mock_open(read_data="some: yaml")):
            with patch("os.path.exists", return_value=True):
                with patch("yaml.safe_load", side_effect=ImportError()):
                    result = load_config_from_file("config.yaml")
                    assert result == {}


@pytest.mark.unit
class TestValidators:
    """验证器测试"""

    def test_is_valid_email_valid_emails(self):
        """测试有效邮箱地址"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
        ]
        for email in valid_emails:
            assert is_valid_email(email) is True

    def test_is_valid_email_invalid_emails(self):
        """测试无效邮箱地址"""
        invalid_emails = [
            "invalid",
            "@domain.com",
            "user@",
            "user@.com",
            "",
            None,
        ]
        for email in invalid_emails:
            if email is not None:  # 函数期望字符串类型
                assert is_valid_email(email) is False

    def test_is_valid_phone_valid_numbers(self):
        """测试有效电话号码"""
        valid_phones = [
            "+1234567890",
            "123 456 7890",
            "(123) 456-7890",
            "+1 123-456-7890",
        ]
        for phone in valid_phones:
            assert is_valid_phone(phone) is True

    def test_is_valid_phone_invalid_numbers(self):
        """测试无效电话号码"""
        invalid_phones = [
            "abc123",
            "",
            "123!@#",
            None,
        ]
        for phone in invalid_phones:
            if phone is not None:
                assert is_valid_phone(phone) is False

    def test_is_valid_url_valid_urls(self):
        """测试有效URL"""
        valid_urls = [
            "https://www.example.com",
            "http://localhost:8000",
            "https://api.example.com/v1/users",
            "http://127.0.0.1:3000",
        ]
        for url in valid_urls:
            assert is_valid_url(url) is True

    def test_is_valid_url_invalid_urls(self):
        """测试无效URL"""
        invalid_urls = [
            "not_a_url",
            "www.example.com",
            "example.com",
            "",
            None,
        ]
        for url in invalid_urls:
            if url is not None:
                assert is_valid_url(url) is False

    def test_validate_required_fields_all_present(self):
        """测试所有必填字段都存在"""
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required = ["name", "email"]
        result = validate_required_fields(data, required)
        assert result == []

    def test_validate_required_fields_missing_fields(self):
        """测试缺少必填字段"""
        data = {"name": "John"}
        required = ["name", "email", "age"]
        result = validate_required_fields(data, required)
        assert set(result) == {"email", "age"}

    def test_validate_required_fields_empty_values(self):
        """测试空值字段"""
        data = {"name": "", "email": None, "age": 0}
        required = ["name", "email", "age"]
        result = validate_required_fields(data, required)
        assert set(result) == {"name", "email"}  # 0不被视为空值

    def test_validate_data_types_valid_types(self):
        """测试正确的数据类型"""
        data = {"name": "John", "age": 30, "active": True}
        schema = {"name": str, "age": int, "active": bool}
        result = validate_data_types(data, schema)
        assert result == []

    def test_validate_data_types_invalid_types(self):
        """测试错误的数据类型"""
        data = {"name": 123, "age": "30", "active": "true"}
        schema = {"name": str, "age": int, "active": bool}
        result = validate_data_types(data, schema)
        assert len(result) == 3
        assert "should be str, got int" in result[0]
        assert "should be int, got str" in result[1]
        assert "should be bool, got str" in result[2]

    def test_validate_data_types_partial_schema(self):
        """测试部分schema验证"""
        data = {"name": "John", "age": 30, "extra": "value"}
        schema = {"name": str, "age": int}
        result = validate_data_types(data, schema)
        assert result == []  # extra字段被忽略


@pytest.mark.unit
class TestFileUtils:
    """文件工具测试"""

    def test_ensure_dir_create_new(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "new_dir" / "sub_dir"
            result = FileUtils.ensure_dir(test_dir)

            assert result == test_dir
            assert test_dir.exists()
            assert test_dir.is_dir()

    def test_ensure_dir_existing(self):
        """测试确保已存在的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "existing_dir"
            test_dir.mkdir()

            result = FileUtils.ensure_dir(test_dir)
            assert result == test_dir
            assert test_dir.exists()

    def test_read_json_success(self):
        """测试成功读取JSON文件"""
        test_data = {"key": "value", "number": 123, "nested": {"inner": "data"}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = FileUtils.read_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError):
            FileUtils.read_json("nonexistent.json")

    def test_read_json_invalid_json(self):
        """测试读取无效JSON文件"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(FileNotFoundError):
                FileUtils.read_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_write_json_success(self):
        """测试成功写入JSON文件"""
        test_data = {"key": "value", "number": 123, "nested": {"inner": "data"}}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            FileUtils.write_json(test_data, temp_path)

            # 验证文件内容
            with open(temp_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data
        finally:
            os.unlink(temp_path)

    def test_write_json_create_dir(self):
        """测试写入JSON文件时自动创建目录"""
        test_data = {"key": "value"}

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "new_dir" / "sub_dir" / "test.json"

            FileUtils.write_json(test_data, temp_path)

            assert temp_path.parent.exists()
            with open(temp_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_get_file_size_existing(self):
        """测试获取存在文件的大小"""
        content = b"test content for size check"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            size = FileUtils.get_file_size(temp_path)
            assert size == len(content)
        finally:
            os.unlink(temp_path)

    def test_get_file_size_nonexistent(self):
        """测试获取不存在文件的大小"""
        size = FileUtils.get_file_size("nonexistent.txt")
        assert size == 0

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        content = b"test content for hash"

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            file_hash = FileUtils.get_file_hash(temp_path)
            assert len(file_hash) == 32  # MD5哈希长度
            assert isinstance(file_hash, str)

            # 验证哈希值正确性
            import hashlib

            expected_hash = hashlib.md5(content, usedforsecurity=False).hexdigest()
            assert file_hash == expected_hash
        finally:
            os.unlink(temp_path)

    def test_ensure_directory_alias(self):
        """测试ensure_directory别名方法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "alias_test"
            result = FileUtils.ensure_directory(test_dir)

            assert result == test_dir
            assert test_dir.exists()

    def test_read_json_file_safe(self):
        """测试安全的JSON文件读取（别名方法）"""
        test_data = {"key": "value"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = FileUtils.read_json_file(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_read_json_file_not_found_safe(self):
        """测试读取不存在文件的安全版本"""
        result = FileUtils.read_json_file("nonexistent.json")
        assert result is None

    def test_write_json_file_success(self):
        """测试JSON文件写入（别名方法）"""
        test_data = {"key": "value"}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            result = FileUtils.write_json_file(test_data, temp_path)
            assert result is True

            with open(temp_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data
        finally:
            os.unlink(temp_path)

    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个旧文件（通过修改修改时间）
            old_file = Path(tmpdir) / "old_file.txt"
            old_file.write_text("old content")

            # 设置文件修改时间为2天前
            old_time = time.time() - (2 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))

            # 清理超过1天的文件
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=1)
            assert removed_count == 1
            assert not old_file.exists()

    def test_cleanup_old_files_no_files(self):
        """测试清理不存在的目录"""
        removed_count = FileUtils.cleanup_old_files("/nonexistent/directory", days=30)
        assert removed_count == 0

    def test_cleanup_old_files_recent(self):
        """测试清理没有旧文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个新文件
            new_file = Path(tmpdir) / "new_file.txt"
            new_file.write_text("new content")

            # 清理超过30天的文件
            removed_count = FileUtils.cleanup_old_files(tmpdir, days=30)
            assert removed_count == 0
            assert new_file.exists()


@pytest.mark.unit
class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_uuid_uniqueness(self):
        """测试UUID生成的唯一性"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert uuid1 != uuid2
        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)

        # 验证UUID格式
        parsed = uuid.UUID(uuid1)
        assert str(parsed) == uuid1

    def test_generate_short_id_default(self):
        """测试生成默认长度的短ID"""
        short_id = CryptoUtils.generate_short_id()
        assert len(short_id) == 8
        assert isinstance(short_id, str)

    def test_generate_short_id_custom_length(self):
        """测试生成自定义长度的短ID"""
        # 测试不同长度
        for length in [4, 16, 32]:
            short_id = CryptoUtils.generate_short_id(length)
            assert len(short_id) == length
            assert isinstance(short_id, str)

    def test_generate_short_id_zero_length(self):
        """测试生成零长度短ID"""
        short_id = CryptoUtils.generate_short_id(0)
        assert short_id == ""

    def test_generate_short_id_large_length(self):
        """测试生成大长度短ID"""
        short_id = CryptoUtils.generate_short_id(64)
        assert len(short_id) == 64
        assert isinstance(short_id, str)

    def test_hash_string_md5(self):
        """测试MD5字符串哈希"""
        text = "test_string"
        hash_value = CryptoUtils.hash_string(text, "md5")

        assert len(hash_value) == 32
        assert isinstance(hash_value, str)

        # 验证哈希值正确性
        import hashlib

        expected = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        assert hash_value == expected

    def test_hash_string_sha256(self):
        """测试SHA256字符串哈希"""
        text = "test_string"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        assert len(hash_value) == 64
        assert isinstance(hash_value, str)

        # 验证哈希值正确性
        import hashlib

        expected = hashlib.sha256(text.encode()).hexdigest()
        assert hash_value == expected

    def test_hash_string_default_algorithm(self):
        """测试默认哈希算法"""
        text = "test_string"
        hash_value = CryptoUtils.hash_string(text)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # 默认是SHA256

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        with pytest.raises(ValueError):
            CryptoUtils.hash_string("test", "unsupported")

    def test_hash_string_non_string_input(self):
        """测试非字符串输入"""
        result = CryptoUtils.hash_string(123)
        assert result == ""

        result = CryptoUtils.hash_string(None)
        assert result == ""

    def test_encode_base64(self):
        """测试Base64编码"""
        text = "Hello, World!"
        encoded = CryptoUtils.encode_base64(text)

        assert isinstance(encoded, str)
        assert encoded == "SGVsbG8sIFdvcmxkIQ=="

    def test_encode_base64_non_string(self):
        """测试Base64编码非字符串"""
        result = CryptoUtils.encode_base64(123)
        assert result == ""

    def test_decode_base64(self):
        """测试Base64解码"""
        encoded = "SGVsbG8sIFdvcmxkIQ=="
        decoded = CryptoUtils.decode_base64(encoded)

        assert isinstance(decoded, str)
        assert decoded == "Hello, World!"

    def test_decode_base64_invalid(self):
        """测试Base64解码无效输入"""
        result = CryptoUtils.decode_base64("invalid_base64!")
        assert result == ""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "my_password_123"
        hashed = CryptoUtils.hash_password(password)

        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$12$")  # bcrypt格式或模拟格式

    def test_hash_password_with_salt(self):
        """测试带盐的密码哈希"""
        password = "my_password_123"
        salt = "custom_salt"

        hashed_with_salt = CryptoUtils.hash_password(password, salt)
        hashed_without_salt = CryptoUtils.hash_password(password)

        assert hashed_with_salt != hashed_without_salt
        assert hashed_with_salt != password

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "my_password_123"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "my_password_123"
        wrong_password = "wrong_password"
        hashed = CryptoUtils.hash_password(password)

        result = CryptoUtils.verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_password_empty(self):
        """测试验证空密码"""
        result = CryptoUtils.verify_password("", "")
        assert result is True

    def test_verify_password_invalid_format(self):
        """测试验证无效格式的哈希"""
        result = CryptoUtils.verify_password("password", "invalid_hash")
        assert result is False

    def test_generate_salt(self):
        """测试生成盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()

        assert salt1 != salt2
        assert isinstance(salt1, str)
        assert len(salt1) == 32  # 16字节的hex编码

    def test_generate_salt_custom_length(self):
        """测试生成自定义长度盐值"""
        salt = CryptoUtils.generate_salt(8)
        assert isinstance(salt, str)
        assert len(salt) == 16  # 8字节的hex编码

    def test_generate_token(self):
        """测试生成令牌"""
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()

        assert token1 != token2
        assert isinstance(token1, str)
        assert len(token1) == 64  # 32字节的hex编码

    def test_generate_token_custom_length(self):
        """测试生成自定义长度令牌"""
        token = CryptoUtils.generate_token(16)
        assert isinstance(token, str)
        assert len(token) == 32  # 16字节的hex编码


@pytest.mark.unit
class TestWarningFilters:
    """警告过滤器测试"""

    def test_setup_warning_filters(self):
        """测试设置警告过滤器"""
        # 该函数主要是设置warnings过滤器，我们验证它不会抛出异常
        try:
            result = setup_warning_filters()
            assert result is None  # 函数没有返回值
        except Exception as e:
            pytest.fail(f"setup_warning_filters raised an exception: {e}")

    def test_setup_warning_filters_idempotent(self):
        """测试警告过滤器设置是幂等的"""
        # 多次调用不应该有问题
        setup_warning_filters()
        setup_warning_filters()
        setup_warning_filters()

        # 如果没有异常，测试通过
        assert True


@pytest.mark.unit
@pytest.mark.integration
class TestModuleIntegration:
    """模块集成测试"""

    def test_config_loader_with_file_utils(self):
        """测试配置加载器与文件工具集成"""
        test_config = {"app": {"name": "test_app", "version": "1.0.0"}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(test_config, f)
            temp_path = f.name

        try:
            # 使用配置加载器读取
            config = load_config_from_file(temp_path)
            assert config == test_config

            # 使用文件工具读取验证
            file_config = FileUtils.read_json(temp_path)
            assert file_config == test_config
        finally:
            os.unlink(temp_path)

    def test_crypto_utils_with_file_utils(self):
        """测试加密工具与文件工具集成"""
        # 创建测试数据
        test_data = {"secret": "confidential_data", "token": "abc123"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # 加密数据文件路径
            data_file = Path(tmpdir) / "data.json"
            hash_file = Path(tmpdir) / "data.hash"

            # 写入数据文件
            FileUtils.write_json(test_data, data_file)

            # 计算文件哈希
            file_hash = FileUtils.get_file_hash(data_file)
            FileUtils.write_json({"hash": file_hash}, hash_file)

            # 验证集成
            assert data_file.exists()
            assert hash_file.exists()

            # 读取并验证
            loaded_data = FileUtils.read_json(data_file)
            hash_data = FileUtils.read_json(hash_file)

            assert loaded_data == test_data
            assert hash_data["hash"] == file_hash

    def test_validators_with_real_data(self):
        """测试验证器与真实数据"""
        # 创建测试用户数据
        user_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "website": "https://johndoe.example.com",
            "age": 30,
            "active": True,
        }

        # 验证邮箱
        assert is_valid_email(user_data["email"]) is True

        # 验证电话
        assert is_valid_phone(user_data["phone"]) is True

        # 验证URL
        assert is_valid_url(user_data["website"]) is True

        # 验证必填字段
        required_fields = ["name", "email", "age"]
        missing = validate_required_fields(user_data, required_fields)
        assert missing == []

        # 验证数据类型
        schema = {
            "name": str,
            "email": str,
            "age": int,
            "active": bool,
        }
        type_errors = validate_data_types(user_data, schema)
        assert type_errors == []
