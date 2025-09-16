"""
工具模块全面测试 - 提升覆盖率
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from src.utils.crypto_utils import CryptoUtils
from src.utils.data_validator import DataValidator
from src.utils.file_utils import FileUtils
from src.utils.response import APIResponse


class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_salt(self):
        """测试生成盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()

        assert len(salt1) > 0
        assert len(salt2) > 0
        assert salt1 != salt2  # 每次生成的盐值应该不同

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password_123"

        hash1 = CryptoUtils.hash_password(password)
        hash2 = CryptoUtils.hash_password(password)

        assert hash1 != hash2  # 使用bcrypt时，每次哈希都应不同
        assert len(hash1) > 0
        assert CryptoUtils.verify_password(password, hash1)
        assert CryptoUtils.verify_password(password, hash2)

    def test_verify_password(self):
        """测试密码验证"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        password_hash = CryptoUtils.hash_password(password)

        assert CryptoUtils.verify_password(password, password_hash) is True
        assert CryptoUtils.verify_password(wrong_password, password_hash) is False


class TestDataValidator:
    """数据验证器测试"""

    def test_validate_email_valid(self):
        """测试有效邮箱验证"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
        ]

        for email in valid_emails:
            assert DataValidator.validate_email(email) is True

    def test_validate_email_invalid(self):
        """测试无效邮箱验证"""
        invalid_emails = ["invalid_email", "@domain.com", "user@", "user@domain", ""]

        for email in invalid_emails:
            assert DataValidator.validate_email(email) is False

    def test_validate_phone_valid(self):
        """测试有效电话号码验证"""
        valid_phones = ["+1234567890", "1234567890", "+86-138-0013-8000"]

        for phone in valid_phones:
            assert DataValidator.validate_phone(phone) is True

    def test_validate_phone_invalid(self):
        """测试无效电话号码验证"""
        invalid_phones = ["123", "abcdefghij", "", "123-abc-456"]

        for phone in invalid_phones:
            assert DataValidator.validate_phone(phone) is False

    def test_validate_date_range_valid(self):
        """测试有效日期范围验证"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        assert DataValidator.validate_date_range(start_date, end_date) is True

    def test_validate_date_range_invalid(self):
        """测试无效日期范围验证"""
        start_date = datetime.now()
        end_date = start_date - timedelta(days=7)  # 结束日期早于开始日期

        assert DataValidator.validate_date_range(start_date, end_date) is False

    def test_validate_required_fields_valid(self):
        """测试必填字段验证 - 有效"""
        data = {"name": "John Doe", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email"]

        missing = DataValidator.validate_required_fields(data, required_fields)
        assert missing == []  # 无缺失字段表示验证通过

    def test_validate_required_fields_invalid(self):
        """测试必填字段验证 - 无效"""
        data = {"name": "John Doe", "age": 30}
        required_fields = ["name", "email"]  # 缺少email字段

        missing = DataValidator.validate_required_fields(data, required_fields)
        assert "email" in missing  # 缺失email字段

    def test_validate_required_fields_empty_value(self):
        """测试必填字段验证 - 空值"""
        data = {"name": "", "email": "john@example.com"}
        required_fields = ["name", "email"]

        missing = DataValidator.validate_required_fields(data, required_fields)
        # 注意：当前实现只检查字段是否存在且不为None，空字符串不被视为缺失
        assert missing == []


class TestFileUtils:
    """文件工具测试"""

    def test_ensure_directory_create(self, tmp_path):
        """测试创建目录"""
        test_dir = tmp_path / "new_dir"
        assert not test_dir.exists()

        result = FileUtils.ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert result == test_dir or result is True

    def test_ensure_directory_exists(self, tmp_path):
        """测试目录已存在"""
        test_dir = tmp_path / "existing_dir"
        test_dir.mkdir()
        assert test_dir.exists()

        result = FileUtils.ensure_directory(str(test_dir))

        assert test_dir.exists()
        assert result == test_dir or result is True

    def test_get_file_size_exists(self, tmp_path):
        """测试获取文件大小 - 文件存在"""
        test_file = tmp_path / "test_file.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        size = FileUtils.get_file_size(str(test_file))

        assert size == len(test_content.encode("utf-8"))

    def test_get_file_size_not_exists(self):
        """测试获取文件大小 - 文件不存在"""
        size = FileUtils.get_file_size("/nonexistent/file.txt")
        assert size == 0

    @patch("builtins.open")
    @patch("json.load")
    @patch("os.path.exists")
    def test_read_json_file_success(self, mock_exists, mock_json_load, mock_open):
        """测试读取JSON文件成功"""
        mock_exists.return_value = True
        mock_json_load.return_value = {"key": "value"}

        data = FileUtils.read_json_file("/test/data.json")

        assert data == {"key": "value"}

    def test_read_json_file_not_exists(self):
        """测试读取不存在的JSON文件"""
        data = FileUtils.read_json_file("/nonexistent/data.json")
        assert data is None

    def test_write_json_file_success(self, tmp_path):
        """测试写入JSON文件成功"""
        test_file = tmp_path / "output.json"
        data = {"key": "value"}

        result = FileUtils.write_json_file(data, str(test_file))

        assert result is True
        assert test_file.exists()
        written_data = json.loads(test_file.read_text())
        assert written_data == data

    def test_cleanup_old_files(self, tmp_path):
        """测试清理旧文件"""
        # 创建测试文件
        old_file1 = tmp_path / "old_file1.txt"
        old_file2 = tmp_path / "old_file2.txt"
        new_file = tmp_path / "new_file.txt"

        # 创建文件
        old_file1.write_text("old content 1")
        old_file2.write_text("old content 2")
        new_file.write_text("new content")

        # 模拟旧文件的修改时间
        import os
        import time

        old_time = time.time() - (8 * 24 * 3600)  # 8天前
        os.utime(str(old_file1), (old_time, old_time))
        os.utime(str(old_file2), (old_time, old_time))

        removed_count = FileUtils.cleanup_old_files(str(tmp_path), days=7)

        assert removed_count == 2
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert new_file.exists()


class TestAPIResponse:
    """API响应工具测试"""

    def test_success_response(self):
        """测试成功响应"""
        data = {"result": "success"}
        response = APIResponse.success(data=data, message="操作成功")

        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "操作成功"
        assert "timestamp" in response

    def test_success_response_no_data(self):
        """测试无数据的成功响应"""
        response = APIResponse.success()

        assert response["success"] is True
        assert "data" not in response  # 当data为None时，不包含data键
        assert response["message"] == "操作成功"

    def test_error_response(self):
        """测试错误响应"""
        response = APIResponse.error(message="操作失败", code=400)

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 400
        assert "timestamp" in response

    def test_error_response_default_code(self):
        """测试默认错误代码"""
        response = APIResponse.error(message="操作失败")

        assert response["success"] is False
        assert response["code"] == 500

    def test_response_timestamp_format(self):
        """测试响应时间戳格式"""
        response = APIResponse.success()

        # 验证时间戳是ISO格式
        timestamp = response["timestamp"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO格式包含T分隔符

    def test_response_structure(self):
        """测试响应结构完整性"""
        response = APIResponse.success(data={"test": "data"})

        required_fields = ["success", "data", "message", "timestamp"]
        for field in required_fields:
            assert field in response

        response = APIResponse.error(message="错误信息")

        required_fields = ["success", "message", "code", "timestamp"]
        for field in required_fields:
            assert field in response
