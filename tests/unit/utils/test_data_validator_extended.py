"""数据验证器测试"""

import pytest
# from src.utils.data_validator import DataValidator


class TestDataValidator:
    """数据验证器测试"""

    def test_is_valid_email(self):
        """测试邮箱验证"""
        assert DataValidator.is_valid_email("test@example.com") is True
        assert DataValidator.is_valid_email("invalid") is False
        assert DataValidator.is_valid_email("") is False

    def test_validate_phone(self):
        """测试电话号码验证"""
        assert DataValidator.validate_phone("+1234567890") is True
        assert DataValidator.validate_phone("13812345678") is True
        assert DataValidator.validate_phone("abc") is False

    def test_is_valid_url(self):
        """测试URL验证"""
        assert DataValidator.is_valid_url("https://example.com") is True
        assert DataValidator.is_valid_url("http://test.org") is True
        assert DataValidator.is_valid_url("not-a-url") is False

    def test_validate_date_range(self):
        """测试日期范围验证"""
        from datetime import datetime

        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        assert DataValidator.validate_date_range(start, end) is True

        # 反向日期应返回False
        assert DataValidator.validate_date_range(end, start) is False

    def test_validate_required_fields(self):
        """测试必填字段验证"""
        data = {"name": "test", "email": "test@example.com"}
        required = ["name", "email"]
        missing = DataValidator.validate_required_fields(data, required)
        assert missing == []  # 没有缺失字段

        data = {"name": "test"}
        missing = DataValidator.validate_required_fields(data, required)
        assert "email" in missing

    def test_validate_data_types(self):
        """测试数据类型验证"""
        data = {"name": "test", "age": 25, "active": True}
        types = {"name": str, "age": int, "active": bool}
        invalid = DataValidator.validate_data_types(data, types)
        assert invalid == []  # 类型正确

        # 错误类型
        data = {"name": "test", "age": "25"}  # age应该是int
        types = {"name": str, "age": int}
        invalid = DataValidator.validate_data_types(data, types)
        assert len(invalid) == 1
        assert "age" in invalid[0]

    def test_sanitize_input(self):
        """测试输入清理"""
        dirty = "<script>alert('xss')</script>"
        clean = DataValidator.sanitize_input(dirty)
        assert "<script>" not in clean
        assert "alert" in clean

    def test_sanitize_input_none(self):
        """测试空输入清理"""
        assert DataValidator.sanitize_input(None) == ""

    def test_sanitize_input_long(self):
        """测试长输入截断"""
        long_text = "a" * 1500
        result = DataValidator.sanitize_input(long_text)
        assert len(result) == 1000
