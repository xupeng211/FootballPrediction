"""
格式化器测试
Tests for Formatters

测试src.utils.formatters模块的格式化功能
"""

import pytest
from datetime import datetime

from src.utils.formatters import (
    format_currency,
    format_percentage,
    format_datetime,
    format_json
)


class TestFormatters:
    """测试格式化工具"""

    def test_format_currency(self):
        """测试货币格式化"""
        # 测试默认格式
        result = format_currency(1234.56)
        assert isinstance(result, str)
        assert result == "1234.56 USD"

        # 测试不同货币
        result_usd = format_currency(1234.56, "USD")
        assert result_usd == "1234.56 USD"

        result_eur = format_currency(1234.56, "EUR")
        assert result_eur == "1234.56 EUR"

        # 测试负数
        result_neg = format_currency(-1234.56)
        assert isinstance(result_neg, str)
        assert result_neg == "-1234.56 USD"

        # 测试零
        result_zero = format_currency(0)
        assert result_zero == "0.00 USD"

    def test_format_percentage(self):
        """测试百分比格式化"""
        # 测试基本百分比
        result = format_percentage(0.25)
        assert isinstance(result, str)
        assert "%" in result

        # 测试小数位数
        result_1 = format_percentage(0.1234, 1)
        assert isinstance(result_1, str)

        # 测试负数
        result_neg = format_percentage(-0.25)
        assert isinstance(result_neg, str)

    def test_format_datetime(self):
        """测试日期时间格式化"""
        dt = datetime(2023, 6, 15, 14, 30, 45)

        # 测试默认格式
        result = format_datetime(dt)
        assert isinstance(result, str)
        assert "2023" in result
        assert "06" in result
        assert "15" in result
        assert "14:30:45" in result

        # 测试自定义格式
        result_custom = format_datetime(dt, "%Y-%m-%d")
        assert result_custom == "2023-06-15"

    def test_format_json(self):
        """测试JSON格式化"""
        # 测试字典
        data = {"name": "test", "value": 123}
        result = format_json(data)
        assert isinstance(result, str)
        assert '"name": "test"' in result
        assert '"value": 123' in result

        # 测试列表
        data_list = [1, 2, 3]
        result_list = format_json(data_list)
        assert isinstance(result_list, str)
        assert "1" in result_list and "2" in result_list and "3" in result_list

        # 测试无缩进
        result_compact = format_json(data, indent=None)
        assert isinstance(result_compact, str)
        assert result_compact == '{"name": "test", "value": 123}'

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试零值
        result_zero = format_currency(0)
        assert isinstance(result_zero, str)
        assert "0.00" in result_zero

        # 测试空JSON
        result_empty = format_json({})
        assert isinstance(result_empty, str)
        assert result_empty == "{}"

        # 测试空列表
        result_list_empty = format_json([])
        assert isinstance(result_list_empty, str)
        assert result_list_empty == "[]"
