from typing import Optional

"""
数据格式化工具测试
Data Formatters Test
"""

import json
from datetime import datetime

import pytest

from src.utils.formatters import (
    format_currency,
    format_datetime,
    format_json,
    format_percentage,
)


class TestFormatDatetime:
    """日期时间格式化测试"""

    def test_format_datetime_default(self):
        """测试默认格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt)
        assert result == "2024-01-15 14:30:45"

    def test_format_datetime_custom_format(self):
        """测试自定义格式"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "%Y/%m/%d")
        assert result == "2024/01/15"

    def test_format_datetime_year_only(self):
        """测试仅年份格式"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "%Y")
        assert result == "2024"

    def test_format_datetime_time_only(self):
        """测试仅时间格式"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "%H:%M:%S")
        assert result == "14:30:45"

    def test_format_datetime_us_format(self):
        """测试美式日期格式"""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = format_datetime(dt, "%m/%d/%Y %I:%M %p")
        assert result == "01/15/2024 02:30 PM"

    def test_format_datetime_edge_cases(self):
        """测试边界情况"""
        # 年末日期
        dt = datetime(2024, 12, 31, 23, 59, 59)
        result = format_datetime(dt)
        assert result == "2024-12-31 23:59:59"

        # 年初日期
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = format_datetime(dt)
        assert result == "2024-01-01 00:00:00"

    def test_format_datetime_leap_year(self):
        """测试闰年日期"""
        dt = datetime(2024, 2, 29, 12, 0, 0)  # 2024是闰年
        result = format_datetime(dt, "%Y-%m-%d")
        assert result == "2024-02-29"


class TestFormatJson:
    """JSON格式化测试"""

    def test_format_json_simple(self):
        """测试简单JSON格式化"""
        data = {"name": "张三", "age": 25}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["name"] == "张三"
        assert parsed["age"] == 25

    def test_format_json_with_indent(self):
        """测试带缩进的JSON格式化"""
        data = {"name": "张三", "age": 25}
        result = format_json(data, indent=2)
        lines = result.split("\n")
        assert len(lines) > 1  # 应该有多行
        assert "  " in result  # 应该包含缩进

    def test_format_json_nested_data(self):
        """测试嵌套数据JSON格式化"""
        data = {
            "user": {"name": "李四", "profile": {"age": 30, "city": "北京"}},
            "scores": [85, 90, 78],
        }
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["user"]["name"] == "李四"
        assert parsed["user"]["profile"]["city"] == "北京"
        assert parsed["scores"] == [85, 90, 78]

    def test_format_json_unicode(self):
        """测试Unicode字符JSON格式化"""
        data = {"message": "你好世界", "emoji": "🎉"}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["message"] == "你好世界"
        assert parsed["emoji"] == "🎉"

    def test_format_json_special_types(self):
        """测试特殊类型JSON格式化"""
        # 列表数据
        data = [1, 2, 3, "test", True, None]
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3, "test", True, None]

        # 数字键（JSON中会转为字符串）
        data = {1: "one", 2: "two"}
        result = format_json(data)
        parsed = json.loads(result)
        assert parsed["1"] == "one"
        assert parsed["2"] == "two"

    def test_format_json_empty_data(self):
        """测试空数据JSON格式化"""
        # 空字典
        result = format_json({})
        assert result == "{}"

        # 空列表
        result = format_json([])
        assert result == "[]"

    def test_format_json_large_data(self):
        """测试大数据JSON格式化"""
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        result = format_json(data)
        parsed = json.loads(result)
        assert len(parsed) == 100
        assert parsed["key_0"] == "value_0"
        assert parsed["key_99"] == "value_99"


class TestFormatCurrency:
    """货币格式化测试"""

    def test_format_currency_default(self):
        """测试默认货币格式化"""
        result = format_currency(123.456)
        assert result == "123.46 USD"

    def test_format_currency_custom_currency(self):
        """测试自定义货币格式化"""
        result = format_currency(123.456, "CNY")
        assert result == "123.46 CNY"

    def test_format_currency_zero(self):
        """测试零值货币格式化"""
        result = format_currency(0.0)
        assert result == "0.00 USD"

    def test_format_currency_negative(self):
        """测试负值货币格式化"""
        result = format_currency(-123.456)
        assert result == "-123.46 USD"

    def test_format_currency_large_amount(self):
        """测试大额货币格式化"""
        result = format_currency(1234567.89)
        assert result == "1234567.89 USD"

    def test_format_currency_small_amount(self):
        """测试小额货币格式化"""
        result = format_currency(0.001)
        assert result == "0.00 USD"

    def test_format_currency_rounding(self):
        """测试货币四舍五入"""
        # 测试向上舍入
        result = format_currency(123.455)
        assert result == "123.46 USD"

        # 测试向下舍入
        result = format_currency(123.454)
        assert result == "123.45 USD"

    def test_format_currency_edge_cases(self):
        """测试货币格式化边界情况"""
        # 测试整数
        result = format_currency(123.0)
        assert result == "123.00 USD"

        # 测试很多小数位
        result = format_currency(123.456789012)
        assert result == "123.46 USD"


class TestFormatPercentage:
    """百分比格式化测试"""

    def test_format_percentage_default(self):
        """测试默认百分比格式化"""
        result = format_percentage(0.1234)
        assert result == "0.12%"

    def test_format_percentage_custom_decimals(self):
        """测试自定义小数位数百分比格式化"""
        result = format_percentage(0.1234, 3)
        assert result == "0.123%"

    def test_format_percentage_zero(self):
        """测试零值百分比格式化"""
        result = format_percentage(0.0)
        assert result == "0.00%"

    def test_format_percentage_hundred(self):
        """测试100%格式化"""
        result = format_percentage(1.0)
        assert result == "1.00%"

    def test_format_percentage_negative(self):
        """测试负值百分比格式化"""
        result = format_percentage(-0.1234)
        assert result == "-0.12%"

    def test_format_percentage_large_value(self):
        """测试大值百分比格式化"""
        result = format_percentage(123.456)
        assert result == "123.46%"

    def test_format_percentage_small_value(self):
        """测试小值百分比格式化"""
        result = format_percentage(0.0001)
        assert result == "0.00%"

    def test_format_percentage_no_decimals(self):
        """测试无小数位数百分比格式化"""
        result = format_percentage(0.1234, 0)
        assert result == "0%"

    def test_format_percentage_many_decimals(self):
        """测试多位小数百分比格式化"""
        result = format_percentage(0.123456789, 6)
        assert result == "0.123457%"

    def test_format_percentage_rounding(self):
        """测试百分比四舍五入"""
        # 测试向上舍入
        result = format_percentage(0.125, 2)
        assert result == "0.13%"

        # 测试向下舍入
        result = format_percentage(0.124, 2)
        assert result == "0.12%"

    def test_format_percentage_edge_cases(self):
        """测试百分比格式化边界情况"""
        # 测试整数百分比
        result = format_percentage(25.0, 0)
        assert result == "25%"

        # 测试科学计数法数字
        result = format_percentage(1.23e-4, 4)
        assert result == "0.0001%"


class TestFormattersIntegration:
    """格式化工具集成测试"""

    def test_datetime_workflow(self):
        """测试日期时间工作流"""
        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 格式化为不同格式
        iso_format = format_datetime(dt, "%Y-%m-%dT%H:%M:%S")
        readable_format = format_datetime(dt, "%Y年%m月%d日 %H:%M")
        time_only = format_datetime(dt, "%H:%M")

        assert iso_format == "2024-01-15T14:30:45"
        assert readable_format == "2024年01月15日 14:30"
        assert time_only == "14:30"

    def test_json_currency_workflow(self):
        """测试JSON货币工作流"""
        data = {
            "product": "测试商品",
            "price": 123.456,
            "currency": "CNY",
            "formatted_price": format_currency(123.456, "CNY"),
        }

        json_result = format_json(data, indent=2)
        parsed = json.loads(json_result)

        assert parsed["formatted_price"] == "123.46 CNY"
        assert parsed["price"] == 123.456

    def test_percentage_data_workflow(self):
        """测试百分比数据工作流"""
        data = {
            "metrics": {
                "success_rate": 0.8547,
                "error_rate": 0.1453,
                "formatted_success": format_percentage(0.8547, 1),
                "formatted_error": format_percentage(0.1453, 1),
            }
        }

        json_result = format_json(data)
        parsed = json.loads(json_result)

        assert parsed["metrics"]["formatted_success"] == "0.9%"
        assert parsed["metrics"]["formatted_error"] == "0.1%"

    def test_complex_data_structure(self):
        """测试复杂数据结构格式化"""
        dt = datetime(2024, 1, 15, 14, 30, 45)

        complex_data = {
            "timestamp": format_datetime(dt),
            "financial": {
                "revenue": 1234567.89,
                "formatted_revenue": format_currency(1234567.89, "CNY"),
                "profit_margin": 0.2345,
                "formatted_margin": format_percentage(0.2345, 2),
            },
            "metadata": {"version": "1.0.0", "author": "测试用户"},
        }

        # 确保所有格式化都正确
        assert complex_data["timestamp"] == "2024-01-15 14:30:45"
        assert complex_data["financial"]["formatted_revenue"] == "1234567.89 CNY"
        assert complex_data["financial"]["formatted_margin"] == "0.23%"

        # 确保可以序列化为JSON
        json_result = format_json(complex_data)
        parsed = json.loads(json_result)
        assert parsed["financial"]["profit_margin"] == 0.2345


class TestFormattersEdgeCases:
    """格式化工具边界情况测试"""

    def test_unicode_handling(self):
        """测试Unicode处理"""
        # 测试各种Unicode字符
        unicode_data = {
            "chinese": "中文测试",
            "emoji": "🎉🚀💻",
            "arabic": "اختبار",
            "russian": "тест",
            "currency": format_currency(123.45, "¥"),
        }

        result = format_json(unicode_data)
        parsed = json.loads(result)
        assert parsed["currency"] == "123.45 ¥"

    def test_extreme_values(self):
        """测试极值处理"""
        # 极大的数值
        large_currency = format_currency(1e15)
        assert "1000000000000000.00" in large_currency

        # 极小的百分比
        small_percentage = format_percentage(1e-10, 10)
        assert "0.0000000001%" == small_percentage

    def test_type_consistency(self):
        """测试类型一致性"""
        # 确保所有函数返回字符串
        dt = datetime(2024, 1, 1, 0, 0, 0)

        assert isinstance(format_datetime(dt), str)
        assert isinstance(format_json({}), str)
        assert isinstance(format_currency(0), str)
        assert isinstance(format_percentage(0), str)

    def test_error_tolerance(self):
        """测试错误容忍性"""
        # 格式化函数应该能够处理各种有效输入
        try:
            # 这些调用应该成功
            format_datetime(datetime.now())
            format_json({})
            format_currency(0)
            format_percentage(0)

            # 如果没有异常，测试通过
            assert True
        except Exception:
            pytest.fail(f"格式化函数不应该抛出异常: {e}")
