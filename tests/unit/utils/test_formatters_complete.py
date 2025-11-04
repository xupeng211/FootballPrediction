"""
Formatters完整测试 - 从0%提升到100%覆盖率
覆盖所有格式化函数
"""

from datetime import datetime

from src.utils.formatters import (
    format_currency,
    format_datetime,
    format_json,
    format_percentage,
)


class TestFormattersComplete:
    """Formatters完整测试类 - 提升覆盖率到100%"""

    def test_format_datetime_function(self):
        """测试日期时间格式化功能"""
        dt = datetime(2024, 1, 15, 14, 30, 45)

        # 默认格式
        result = format_datetime(dt)
        assert result == "2024-01-15 14:30:45"

        # 自定义格式
        result = format_datetime(dt, "%Y年%m月%d日")
        assert result == "2024年01月15日"

        # 日期格式
        result = format_datetime(dt, "%Y-%m-%d")
        assert result == "2024-01-15"

        # 时间格式
        result = format_datetime(dt, "%H:%M:%S")
        assert result == "14:30:45"

    def test_format_json_function(self):
        """测试JSON格式化功能"""
        # 基本对象
        data = {"name": "John", "age": 30}
        result = format_json(data)
        assert isinstance(result, str)
        assert "name" in result
        assert "John" in result

        # 数组
        data = [1, 2, 3]
        result = format_json(data)
        assert "[1, 2, 3]" in result

        # 嵌套对象
        data = {"user": {"name": "John", "age": 30}, "active": True}
        result = format_json(data)
        assert isinstance(result, str)
        assert "user" in result

        # 无缩进
        data = {"key": "value"}
        result = format_json(data, indent=None)
        assert isinstance(result, str)

    def test_format_currency_function(self):
        """测试货币格式化功能"""
        # 默认货币
        result = format_currency(123.456)
        assert result == "123.46 USD"

        # 自定义货币
        result = format_currency(99.99, "EUR")
        assert result == "99.99 EUR"

        # 整数金额
        result = format_currency(100, "CNY")
        assert result == "100.00 CNY"

        # 零金额
        result = format_currency(0, "JPY")
        assert result == "0.00 JPY"

        # 负数金额
        result = format_currency(-50.25, "GBP")
        assert result == "-50.25 GBP"

    def test_format_percentage_function(self):
        """测试百分比格式化功能"""
        # 默认小数位
        result = format_percentage(0.1234)
        assert result == "0.12%"

        # 自定义小数位
        result = format_percentage(0.1234, 3)
        assert result == "0.123%"

        # 整数百分比
        result = format_percentage(75)
        assert result == "75.00%"

        # 零百分比
        result = format_percentage(0)
        assert result == "0.00%"

        # 负数百分比
        result = format_percentage(-25.5)
        assert result == "-25.50%"

        # 一位小数
        result = format_percentage(33.333, 1)
        assert result == "33.3%"

    def test_comprehensive_formatting_workflow(self):
        """测试完整的格式化工作流程"""
        # 1. 日期时间格式化
        dt = datetime(2024, 1, 15, 14, 30, 45)
        formatted_dt = format_datetime(dt, "%Y-%m-%d %H:%M:%S")
        assert formatted_dt == "2024-01-15 14:30:45"

        # 2. JSON格式化
        data = {
            "timestamp": formatted_dt,
            "amount": 1234.56,
            "percentage": 85.67,
            "currency": "USD",
        }
        json_str = format_json(data)
        assert isinstance(json_str, str)
        assert "timestamp" in json_str

        # 3. 货币格式化
        amount = 1234.56
        currency_str = format_currency(amount, "USD")
        assert currency_str == "1234.56 USD"

        # 4. 百分比格式化
        percentage = 85.67
        percentage_str = format_percentage(percentage, 2)
        assert percentage_str == "85.67%"

        # 验证所有格式化结果都是字符串
        assert isinstance(formatted_dt, str)
        assert isinstance(json_str, str)
        assert isinstance(currency_str, str)
        assert isinstance(percentage_str, str)

    def test_edge_cases_and_special_values(self):
        """测试边界情况和特殊值"""
        # 测试极小数值
        assert format_currency(0.001) == "0.00 USD"
        assert format_percentage(0.001) == "0.00%"

        # 测试极大数值
        large_amount = 999999999.99
        assert "999999999.99" in format_currency(large_amount)

        large_percentage = 999.999
        assert "999.999%" in format_percentage(large_percentage, 3)

        # 测试精度
        precise_value = 3.14159265359
        assert format_percentage(precise_value, 5) == "3.14159%"
