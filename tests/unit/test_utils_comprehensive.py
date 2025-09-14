"""
工具模块全面测试 - 提升覆盖率
"""

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

    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_ensure_directory_create(self, mock_exists, mock_makedirs):
        """测试创建目录"""
        mock_exists.return_value = False

        FileUtils.ensure_directory("/test/path")

        mock_makedirs.assert_called_once_with("/test/path", exist_ok=True)

    @patch("os.path.exists")
    def test_ensure_directory_exists(self, mock_exists):
        """测试目录已存在"""
        mock_exists.return_value = True

        result = FileUtils.ensure_directory("/existing/path")

        assert result is True

    @patch("os.path.getsize")
    @patch("os.path.exists")
    def test_get_file_size_exists(self, mock_exists, mock_getsize):
        """测试获取文件大小 - 文件存在"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024

        size = FileUtils.get_file_size("/test/file.txt")

        assert size == 1024

    @patch("os.path.exists")
    def test_get_file_size_not_exists(self, mock_exists):
        """测试获取文件大小 - 文件不存在"""
        mock_exists.return_value = False

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

    @patch("os.path.exists")
    def test_read_json_file_not_exists(self, mock_exists):
        """测试读取不存在的JSON文件"""
        mock_exists.return_value = False

        data = FileUtils.read_json_file("/nonexistent/data.json")

        assert data is None

    @patch("builtins.open")
    @patch("json.dump")
    def test_write_json_file_success(self, mock_json_dump, mock_open):
        """测试写入JSON文件成功"""
        data = {"key": "value"}

        result = FileUtils.write_json_file("/test/output.json", data)

        assert result is True
        mock_open.assert_called_once()

    @patch("os.listdir")
    @patch("os.path.isfile")
    @patch("os.path.getmtime")
    @patch("os.remove")
    def test_cleanup_old_files(
        self, mock_remove, mock_getmtime, mock_isfile, mock_listdir
    ):
        """测试清理旧文件"""
        mock_listdir.return_value = ["file1.txt", "file2.txt", "file3.txt"]
        mock_isfile.return_value = True

        # 模拟文件时间 - file1和file2是旧文件，file3是新文件
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        new_time = datetime.now().timestamp()
        mock_getmtime.side_effect = [old_time, old_time, new_time]

        removed_count = FileUtils.cleanup_old_files("/test/directory", days=7)

        assert removed_count == 2
        assert mock_remove.call_count == 2


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
        assert response["data"] is None
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
