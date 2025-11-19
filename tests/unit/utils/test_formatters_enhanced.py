from typing import Optional

"""
Formatters模块增强测试 - 快速提升覆盖率
测试format_datetime, format_json, format_currency, format_percentage函数
"""

import json
from datetime import datetime

from src.utils.formatters import (
    format_currency,
    format_datetime,
    format_json,
    format_percentage,
)


class TestFormattersEnhanced:
    """Formatters增强测试类"""

    def test_format_datetime_default_format(self):
        """测试默认格式化日期时间"""
        dt = datetime(2023, 12, 25, 15, 30, 45)
        result = format_datetime(dt)
        assert result == "2023-12-25 15:30:45"
        assert isinstance(result, str)

    def test_format_datetime_custom_format(self):
        """测试自定义格式化日期时间"""
        dt = datetime(2023, 12, 25, 15, 30, 45)

        # 测试不同格式
        assert format_datetime(dt, "%Y-%m-%d") == "2023-12-25"
        assert format_datetime(dt, "%H:%M:%S") == "15:30:45"
        assert format_datetime(dt, "%d/%m/%Y") == "25/12/2023"
        assert format_datetime(dt, "%Y年%m月%d日") == "2023年12月25日"

    def test_format_datetime_edge_cases(self):
        """测试日期时间格式化边界情况"""
        # 测试新年
        dt_new_year = datetime(2024, 1, 1, 0, 0, 0)
        assert format_datetime(dt_new_year) == "2024-01-01 00:00:00"

        # 测试闰年
        dt_leap = datetime(2024, 2, 29, 12, 0, 0)
        assert format_datetime(dt_leap) == "2024-02-29 12:00:00"

    def test_format_json_basic(self):
        """测试基本JSON格式化"""
        data = {"name": "John", "age": 30}
        result = format_json(data)

        # 验证结果
        parsed = json.loads(result)
        assert parsed["name"] == "John"
        assert parsed["age"] == 30

    def test_format_json_with_indent(self):
        """测试带缩进的JSON格式化"""
        data = {"name": "John", "age": 30, "city": "New York"}
        result = format_json(data, indent=2)

        # 验证包含换行符和缩进
        assert "\n" in result
        assert "  " in result

    def test_format_json_complex_data(self):
        """测试复杂JSON数据格式化"""
        data = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ],
            "total": 2,
            "metadata": None,
        }

        result = format_json(data)
        parsed = json.loads(result)

        assert parsed["total"] == 2
        assert len(parsed["users"]) == 2
        assert parsed["users"][0]["name"] == "Alice"

    def test_format_json_unicode(self):
        """测试Unicode数据JSON格式化"""
        data = {"message": "你好世界", "emoji": "🌍"}
        result = format_json(data)

        parsed = json.loads(result)
        assert parsed["message"] == "你好世界"
        assert parsed["emoji"] == "🌍"

    def test_format_currency_default(self):
        """测试默认货币格式化"""
        result = format_currency(123.456)
        assert result == "123.46 USD"
        assert isinstance(result, str)

    def test_format_currency_different_currencies(self):
        """测试不同货币格式化"""
        assert format_currency(100.0, "EUR") == "100.00 EUR"
        assert format_currency(50.5, "CNY") == "50.50 CNY"
        assert format_currency(0.99, "JPY") == "0.99 JPY"

    def test_format_currency_edge_cases(self):
        """测试货币格式化边界情况"""
        # 测试整数
        assert format_currency(100) == "100.00 USD"

        # 测试小数
        assert format_currency(0.01) == "0.01 USD"

        # 测试大数
        assert format_currency(999999.99) == "999999.99 USD"

        # 测试负数
        assert format_currency(-50.25) == "-50.25 USD"

    def test_format_currency_rounding(self):
        """测试货币四舍五入"""
        # 测试向上舍入
        assert format_currency(123.456) == "123.46 USD"
        assert format_currency(123.454) == "123.45 USD"

        # 测试边界情况 - 使用四舍五入法
        assert format_currency(123.455) == "123.46 USD"  # 四舍五入法

    def test_format_percentage_default(self):
        """测试默认百分比格式化"""
        result = format_percentage(25.5678)
        assert result == "25.57%"
        assert isinstance(result, str)

    def test_format_percentage_custom_decimals(self):
        """测试自定义小数位数百分比格式化"""
        assert format_percentage(25.5678, 0) == "26%"
        assert format_percentage(25.5678, 1) == "25.6%"
        assert format_percentage(25.5678, 3) == "25.568%"

    def test_format_percentage_edge_cases(self):
        """测试百分比格式化边界情况"""
        # 测试整数
        assert format_percentage(100) == "100.00%"

        # 测试小数
        assert format_percentage(0.1234) == "0.12%"

        # 测试零
        assert format_percentage(0) == "0.00%"

        # 测试负数
        assert format_percentage(-15.5) == "-15.50%"

    def test_format_percentage_rounding(self):
        """测试百分比四舍五入"""
        # 测试向上舍入
        assert format_percentage(25.556) == "25.56%"
        assert format_percentage(25.554) == "25.55%"

        # 测试边界情况 - 使用四舍五入法
        assert format_percentage(25.555) == "25.56%"  # 四舍五入法

    def test_formatters_integration_workflow(self):
        """测试格式化器集成工作流程"""
        # 模拟实际应用场景
        order_data = {
            "order_id": "ORD-001",
            "customer": "张三",
            "amount": 1234.56,
            "discount_rate": 0.15,
            "order_date": datetime(2023, 12, 25, 14, 30, 0),
        }

        # 格式化各个字段
        formatted_date = format_datetime(order_data["order_date"])
        formatted_amount = format_currency(order_data["amount"], "CNY")
        formatted_discount = format_percentage(order_data["discount_rate"] * 100)

        # 创建格式化摘要
        summary = {
            "订单号": order_data["order_id"],
            "客户": order_data["customer"],
            "日期": formatted_date,
            "金额": formatted_amount,
            "折扣": formatted_discount,
        }

        # 转换为JSON
        json_result = format_json(summary, indent=2)

        # 验证结果
        assert "ORD-001" in json_result
        assert "张三" in json_result
        assert "2023-12-25 14:30:00" in json_result
        assert "1234.56 CNY" in json_result
        assert "15.00%" in json_result

    def test_error_handling_and_robustness(self):
        """测试错误处理和健壮性"""
        # 测试format_datetime处理不同datetime对象
        dt1 = datetime.now()
        dt2 = datetime.utcnow()

        result1 = format_datetime(dt1)
        result2 = format_datetime(dt2)

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert len(result1) == 19  # YYYY-MM-DD HH:MM:SS
        assert len(result2) == 19

        # 测试format_json处理不同数据类型
        assert format_json(None) == "null"
        assert format_json(True) == "true"
        assert format_json(False) == "false"
        assert format_json(42) == "42"
        assert format_json("hello") == '"hello"'

        # 测试format_currency处理特殊数值
        assert format_currency(0) == "0.00 USD"
        assert format_currency(1e6) == "1000000.00 USD"

        # 测试format_percentage处理特殊数值
        assert format_percentage(0) == "0.00%"
        assert format_percentage(100) == "100.00%"
        assert format_percentage(123.456789, 4) == "123.4568%"
