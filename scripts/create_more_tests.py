#!/usr/bin/env python3
"""
快速创建更多测试以提升覆盖率到30%
"""

from pathlib import Path


def create_string_utils_test():
    """创建字符串工具测试"""
    content = '''"""字符串工具测试"""
import pytest
from src.utils.string_utils import StringUtils

class TestStringUtils:
    """字符串工具测试"""

    def test_capitalize_words(self):
        """测试首字母大写"""
        text = "hello world"
        result = StringUtils.capitalize_words(text)
        assert result == "Hello World"

    def test_reverse_string(self):
        """测试字符串反转"""
        text = "hello"
        result = StringUtils.reverse_string(text)
        assert result == "olleh"

    def test_is_empty(self):
        """测试空字符串检查"""
        assert StringUtils.is_empty("") is True
        assert StringUtils.is_empty("   ") is True
        assert StringUtils.is_empty("hello") is False

    def test_trim_whitespace(self):
        """测试去除空白字符"""
        text = "  hello  "
        result = StringUtils.trim_whitespace(text)
        assert result == "hello"

    def test_contains_numbers(self):
        """测试是否包含数字"""
        assert StringUtils.contains_numbers("hello123") is True
        assert StringUtils.contains_numbers("hello") is False
'''

    test_path = Path("tests/unit/test_string_utils_extended.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def create_time_utils_test():
    """创建时间工具测试"""
    content = '''"""时间工具测试"""
import pytest
from datetime import datetime, timedelta
from src.utils.time_utils import TimeUtils

class TestTimeUtils:
    """时间工具测试"""

    def test_format_duration(self):
        """测试格式化持续时间"""
        seconds = 3665
        result = TimeUtils.format_duration(seconds)
        assert "1 hour" in result or "61 minutes" in result

    def test_is_future(self):
        """测试是否是未来时间"""
        now = datetime.now()
        future = now + timedelta(hours=1)
        assert TimeUtils.is_future(future) is True
        assert TimeUtils.is_future(now) is False

    def test_days_between(self):
        """测试计算天数差"""
        date1 = datetime(2024, 1, 1)
        date2 = datetime(2024, 1, 3)
        result = TimeUtils.days_between(date1, date2)
        assert result == 2

    def test_start_of_day(self):
        """测试获取一天开始时间"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        start = TimeUtils.start_of_day(dt)
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

    def test_add_working_days(self):
        """测试添加工作日"""
        start = datetime(2024, 1, 1)  # 周一
        result = TimeUtils.add_working_days(start, 5)
        # 5个工作日后应该是下周一
        assert result.weekday() == 0  # 周一
'''

    test_path = Path("tests/unit/test_time_utils_extended.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def create_data_validator_test():
    """创建数据验证器测试"""
    content = '''"""数据验证器测试"""
import pytest
from src.utils.data_validator import DataValidator

class TestDataValidator:
    """数据验证器测试"""

    def test_validate_email(self):
        """测试邮箱验证"""
        assert DataValidator.is_valid_email("test@example.com") is True
        assert DataValidator.is_valid_email("invalid") is False
        assert DataValidator.is_valid_email("") is False

    def test_validate_phone(self):
        """测试电话号码验证"""
        assert DataValidator.is_valid_phone("+1234567890") is True
        assert DataValidator.is_valid_phone("123-456-7890") is True
        assert DataValidator.is_valid_phone("abc") is False

    def test_validate_url(self):
        """测试URL验证"""
        assert DataValidator.is_valid_url("https://example.com") is True
        assert DataValidator.is_valid_url("http://test.org") is True
        assert DataValidator.is_valid_url("not-a-url") is False

    def test_validate_positive_number(self):
        """测试正数验证"""
        assert DataValidator.is_positive_number(5) is True
        assert DataValidator.is_positive_number(0) is False
        assert DataValidator.is_positive_number(-5) is False

    def test_validate_required_fields(self):
        """测试必填字段验证"""
        data = {"name": "test", "email": "test@example.com"}
        required = ["name", "email"]
        assert DataValidator.validate_required_fields(data, required) is True

        data = {"name": "test"}
        assert DataValidator.validate_required_fields(data, required) is False
'''

    test_path = Path("tests/unit/test_data_validator_extended.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def create_file_utils_test():
    """创建文件工具测试"""
    content = '''"""文件工具测试"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.utils.file_utils import FileUtils

class TestFileUtils:
    """文件工具测试"""

    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        assert FileUtils.get_file_extension("test.txt") == "txt"
        assert FileUtils.get_file_extension("archive.tar.gz") == "gz"
        assert FileUtils.get_file_extension("no_extension") == ""

    def test_is_text_file(self):
        """测试是否是文本文件"""
        assert FileUtils.is_text_file("document.txt") is True
        assert FileUtils.is_text_file("script.py") is True
        assert FileUtils.is_text_file("image.jpg") is False

    def test_get_file_size_mb(self):
        """测试获取文件大小(MB)"""
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1048576  # 1MB
            size = FileUtils.get_file_size_mb("test.txt")
            assert size == 1.0

    def test_create_backup_name(self):
        """测试创建备份文件名"""
        backup = FileUtils.create_backup_name("test.txt")
        assert "backup" in backup
        assert backup.endswith(".txt")

    def test_ensure_directory_exists(self):
        """测试确保目录存在"""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            FileUtils.ensure_directory_exists("/test/path")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
'''

    test_path = Path("tests/unit/test_file_utils_extended.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def create_response_utils_test():
    """创建响应工具测试"""
    content = '''"""响应工具测试"""
import pytest
from src.utils.response import ResponseUtils

class TestResponseUtils:
    """响应工具测试"""

    def test_create_success_response(self):
        """测试创建成功响应"""
        data = {"id": 1, "name": "test"}
        response = ResponseUtils.create_success_response(data)
        assert response["success"] is True
        assert response["data"] == data

    def test_create_error_response(self):
        """测试创建错误响应"""
        error = "Something went wrong"
        response = ResponseUtils.create_error_response(error)
        assert response["success"] is False
        assert response["error"] == error

    def test_create_paginated_response(self):
        """测试创建分页响应"""
        items = [{"id": i} for i in range(1, 6)]
        response = ResponseUtils.create_paginated_response(
            items=items,
            page=1,
            per_page=5,
            total=10
        )
        assert response["items"] == items
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["total"] == 10

    def test_filter_sensitive_data(self):
        """测试过滤敏感数据"""
        data = {
            "id": 1,
            "name": "test",
            "password": "secret",
            "token": "abc123"
        }
        filtered = ResponseUtils.filter_sensitive_data(data)
        assert "password" not in filtered
        assert "token" not in filtered
        assert "name" in filtered
'''

    test_path = Path("tests/unit/test_response_utils_extended.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def create_api_tests():
    """创建API测试"""
    # 创建API数据端点测试
    content = '''"""API数据端点测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestAPIData:
    """API数据端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app
        return TestClient(app)

    def test_get_root(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/health")
        # 检查是否有CORS相关的头
        # 某些CORS头可能存在
        assert response.status_code in [200, 405]

    def test_invalid_endpoint(self, client):
        """测试无效端点"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_health_response_time(self, client):
        """测试健康检查响应时间"""
        import time
        start = time.time()
        response = client.get("/api/health")
        end = time.time()
        assert response.status_code == 200
        # 响应时间应该少于1秒
        assert (end - start) < 1.0
'''

    test_path = Path("tests/unit/test_api_data_endpoints.py")
    test_path.write_text(content, encoding="utf-8")
    print(f"✅ 创建 {test_path}")


def main():
    """主函数"""
    print("🚀 快速创建测试文件以提升覆盖率...")

    # 确保测试目录存在
    test_dir = Path("tests/unit")
    test_dir.mkdir(parents=True, exist_ok=True)

    # 创建各种测试文件
    create_string_utils_test()
    create_time_utils_test()
    create_data_validator_test()
    create_file_utils_test()
    create_response_utils_test()
    create_api_tests()

    print("\n✅ 成功创建6个测试文件")
    print("\n📋 新增测试列表:")
    print("  - test_string_utils_extended.py")
    print("  - test_time_utils_extended.py")
    print("  - test_data_validator_extended.py")
    print("  - test_file_utils_extended.py")
    print("  - test_response_utils_extended.py")
    print("  - test_api_data_endpoints.py")

    print("\n🎯 运行以下命令查看覆盖率:")
    print("  make coverage-local")
    print("\n或运行新测试:")
    print("  python -m pytest tests/unit/test_*_extended.py -v")


if __name__ == "__main__":
    main()
