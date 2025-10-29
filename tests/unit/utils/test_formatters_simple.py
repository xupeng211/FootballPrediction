"""
格式化工具简单测试
Simple Formatters Tests

测试src/utils/formatters.py中定义的格式化功能，专注于实现100%覆盖率。
Tests formatting functionality defined in src/utils/formatters.py, focused on achieving 100% coverage.
"""

import json

import pytest

# 导入要测试的模块
try:
    from src.utils.formatters import (
        format_currency,
        format_datetime,
        format_json,
        format_percentage,
    )

    FORMATTERS_AVAILABLE = True
except ImportError:
    FORMATTERS_AVAILABLE = False


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters module not available")
@pytest.mark.unit
class TestFormattersSimple:
    """格式化工具简单测试"""

    def test_format_datetime_basic(self):
        """测试基本日期时间格式化"""
        dt = datetime(2025, 1, 11, 15, 30, 45)
        result = format_datetime(dt)
        assert result == "2025-01-11 15:30:45"
        assert isinstance(result, str)

    def test_format_datetime_custom_format(self):
        """测试自定义格式的日期时间格式化"""
        dt = datetime(2025, 1, 11, 15, 30, 45)
        result = format_datetime(dt, "%Y/%m/%d")
        assert result == "2025/01/11"

    def test_format_json_basic(self):
        """测试基本JSON格式化"""
        data = {"name": "John", "age": 30}
        result = format_json(data)

        # 验证是有效的JSON
        parsed_data = json.loads(result)
        assert parsed_data == data
        assert isinstance(result, str)

    def test_format_json_no_indent(self):
        """测试无缩进的JSON格式化"""
        data = {"name": "John", "age": 30}
        result = format_json(data, indent=None)

        # 验证没有换行符
        assert "\n" not in result
        parsed_data = json.loads(result)
        assert parsed_data == data

    def test_format_json_unicode(self):
        """测试Unicode字符的JSON格式化"""
        data = {"chinese": "你好世界", "emoji": "🚀"}
        result = format_json(data)
        parsed_data = json.loads(result)
        assert parsed_data == data
        assert "你好世界" in result

    def test_format_currency_default(self):
        """测试默认货币格式化"""
        result = format_currency(123.456)
        assert result == "123.46 USD"
        assert isinstance(result, str)

    def test_format_currency_custom(self):
        """测试自定义货币格式化"""
        result = format_currency(100.0, "EUR")
        assert result == "100.00 EUR"

    def test_format_currency_negative(self):
        """测试负数货币格式化"""
        result = format_currency(-50.25)
        assert result == "-50.25 USD"

    def test_format_currency_rounding(self):
        """测试货币格式化四舍五入"""
        # 测试向上舍入
        result = format_currency(123.456)
        assert result == "123.46 USD"

        # 测试向下舍入
        result = format_currency(123.454)
        assert result == "123.45 USD"

    def test_format_percentage_default(self):
        """测试默认百分比格式化"""
        result = format_percentage(0.7543)
        assert result == "0.75%"
        assert isinstance(result, str)

    def test_format_percentage_custom_decimals(self):
        """测试自定义小数位的百分比格式化"""
        result = format_percentage(0.7543, 1)
        assert result == "0.8%"

    def test_format_percentage_zero_decimals(self):
        """测试零小数位的百分比格式化"""
        result = format_percentage(0.7543, 0)
        assert result == "1%"

    def test_format_percentage_negative(self):
        """测试负数百分比格式化"""
        result = format_percentage(-0.25)
        assert result == "-0.25%"

    def test_format_percentage_rounding(self):
        """测试百分比格式化四舍五入"""
        # 测试向上舍入
        result = format_percentage(0.755, 2)
        assert result == "0.76%"

        # 测试向下舍入
        result = format_percentage(0.754, 2)
        assert result == "0.75%"

    def test_all_functions_available(self):
        """测试所有函数都可用"""
        assert callable(format_datetime)
        assert callable(format_json)
        assert callable(format_currency)
        assert callable(format_percentage)

    def test_integration_workflow(self):
        """测试格式化工具集成工作流"""
        # 创建数据
        now = datetime(2025, 1, 11, 15, 30, 45)
        growth_rate = 15.6  # 已经是百分比值
        data = {
            "timestamp": format_datetime(now),
            "revenue": 1547.89,
            "growth": growth_rate,
        }

        # 格式化数据
        json_str = format_json(data, indent=None)
        revenue_str = format_currency(data["revenue"], "USD")
        growth_str = format_percentage(data["growth"], 1)

        # 验证结果
        assert "2025-01-11 15:30:45" in json_str
        assert revenue_str == "1547.89 USD"
        assert growth_str == "15.6%"  # 15.6 -> 15.6%

        # 验证JSON可以解析
        parsed = json.loads(json_str)
        assert parsed["revenue"] == 1547.89
