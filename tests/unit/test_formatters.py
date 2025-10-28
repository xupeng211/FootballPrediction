#!/usr/bin/env python3
"""
格式化工具测试
测试 src.utils.formatters 模块的功能
"""

from datetime import datetime

import pytest

from src.utils.formatters import (
    format_currency,
    format_datetime,
    format_json,
    format_percentage,
)


@pytest.mark.unit
class TestFormatters:
    """格式化工具测试"""

    def test_format_datetime_default(self):
        """测试默认格式的时间格式化"""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = format_datetime(dt)
        assert result == "2024-01-01 12:30:45"

    def test_format_datetime_custom(self):
        """测试自定义格式的时间格式化"""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%Y/%m/%d")
        assert result == "2024/01/01"

    def test_format_json_basic(self):
        """测试基础JSON格式化"""
        data = {"name": "test", "value": 123}
        result = format_json(data)
        assert '"name": "test"' in result
        assert '"value": 123' in result

    def test_format_json_no_indent(self):
        """测试无缩进JSON格式化"""
        data = {"key": "value"}
        result = format_json(data, indent=None)
        assert result == '{"key": "value"}'

    def test_format_json_unicode(self):
        """测试Unicode字符JSON格式化"""
        data = {"message": "测试中文"}
        result = format_json(data)
        assert "测试中文" in result

    def test_format_currency_usd(self):
        """测试USD货币格式化"""
        result = format_currency(123.456)
        assert result == "123.46 USD"

    def test_format_currency_eur(self):
        """测试EUR货币格式化"""
        result = format_currency(99.99, "EUR")
        assert result == "99.99 EUR"

    def test_format_currency_zero(self):
        """测试零值货币格式化"""
        result = format_currency(0.0)
        assert result == "0.00 USD"

    def test_format_percentage_default(self):
        """测试默认百分比格式化"""
        result = format_percentage(0.1234)
        assert result == "0.12%"

    def test_format_percentage_custom_decimals(self):
        """测试自定义小数位的百分比格式化"""
        result = format_percentage(0.123456, 4)
        assert result == "0.1235%"

    def test_format_percentage_zero(self):
        """测试零值百分比格式化"""
        result = format_percentage(0.0)
        assert result == "0.00%"

    def test_format_percentage_hundred(self):
        """测试100%格式化"""
        result = format_percentage(1.0)
        assert result == "1.00%"

    def test_format_datetime_different_formats(self):
        """测试不同的时间格式"""
        dt = datetime(2024, 12, 25, 15, 0, 0)

        # 测试不同格式
        assert format_datetime(dt, "%Y-%m-%d") == "2024-12-25"
        assert format_datetime(dt, "%H:%M") == "15:00"
        assert format_datetime(dt, "%d/%m/%Y %H:%M") == "25/12/2024 15:00"

    def test_format_json_complex_data(self):
        """测试复杂数据的JSON格式化"""
        data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "total": 2,
        }
        result = format_json(data)
        assert "Alice" in result
        assert "Bob" in result
        assert "total" in result

    def test_format_currency_large_numbers(self):
        """测试大数字货币格式化"""
        result = format_currency(1234567.89)
        assert result == "1234567.89 USD"

    def test_format_percentage_small_numbers(self):
        """测试小数百分比格式化"""
        result = format_percentage(0.0001, 4)
        assert result == "0.0001%"
