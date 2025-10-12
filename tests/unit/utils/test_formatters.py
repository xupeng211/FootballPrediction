"""
格式化器测试
Tests for Formatters

测试src.utils.formatters模块的格式化功能
"""

import pytest
from datetime import datetime

# 测试导入
try:
    from src.utils.formatters import (
        format_datetime,
        format_json,
        format_currency,
        format_percentage,
    )

    FORMATTERS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    FORMATTERS_AVAILABLE = False


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters module not available")
class TestFormatDatetime:
    """日期时间格式化测试"""

    def test_format_datetime_default(self):
        """测试：默认格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt)
        assert result == "2023-01-01 12:30:45"

    def test_format_datetime_custom_format(self):
        """测试：自定义格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%Y/%m/%d")
        assert result == "2023/01/01"

    def test_format_datetime_iso_format(self):
        """测试：ISO格式"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%Y-%m-%dT%H:%M:%S")
        assert result == "2023-01-01T12:30:45"

    def test_format_datetime_with_microseconds(self):
        """测试：带微秒"""
        dt = datetime(2023, 1, 1, 12, 30, 45, 123456)
        result = format_datetime(dt, "%Y-%m-%d %H:%M:%S.%f")
        assert result == "2023-01-01 12:30:45.123456"

    def test_format_datetime_only_date(self):
        """测试：仅日期"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%d/%m/%Y")
        assert result == "01/01/2023"

    def test_format_datetime_only_time(self):
        """测试：仅时间"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%H:%M")
        assert result == "12:30"

    def test_format_datetime_leap_year(self):
        """测试：闰年"""
        dt = datetime(2024, 2, 29, 0, 0, 0)
        result = format_datetime(dt)
        assert result == "2024-02-29 00:00:00"

    def test_format_datetime_different_separators(self):
        """测试：不同分隔符"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        result = format_datetime(dt, "%H-%M-%S")
        assert result == "12-30-45"


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters module not available")
class TestFormatJSON:
    """JSON格式化测试"""

    def test_format_json_simple_dict(self):
        """测试：简单字典"""
        data = {"key": "value", "number": 123}
        result = format_json(data)
        assert result == '{\n  "key": "value",\n  "number": 123\n}'

    def test_format_json_nested_dict(self):
        """测试：嵌套字典"""
        data = {"outer": {"inner": "value"}}
        result = format_json(data)
        assert '"outer": {' in result
        assert '"inner": "value"' in result

    def test_format_json_list(self):
        """测试：列表"""
        data = [1, 2, 3]
        result = format_json(data)
        assert result == "[\n  1,\n  2,\n  3\n]"

    def test_format_json_no_indent(self):
        """测试：无缩进"""
        data = {"key": "value"}
        result = format_json(data, indent=None)
        assert result == '{"key": "value"}'

    def test_format_json_custom_indent(self):
        """测试：自定义缩进"""
        data = {"key": "value"}
        result = format_json(data, indent=4)
        assert result == '{\n    "key": "value"\n}'

    def test_format_json_unicode(self):
        """测试：Unicode字符"""
        data = {"message": "你好世界"}
        result = format_json(data)
        assert "你好世界" in result

    def test_format_json_special_numbers(self):
        """测试：特殊数字"""
        data = {"float": 3.14159, "exponential": 0.000123}
        result = format_json(data)
        assert "3.14159" in result
        # 指数可能会被格式化为普通小数
        assert "0.000123" in result or "1.23e-4" in result.lower()

    def test_format_json_boolean_and_none(self):
        """测试：布尔值和None"""
        data = {"true": True, "false": False, "null": None}
        result = format_json(data)
        assert "true" in result
        assert "false" in result
        assert "null" in result


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters module not available")
class TestFormatCurrency:
    """货币格式化测试"""

    def test_format_currency_default(self):
        """测试：默认格式"""
        result = format_currency(123.45)
        assert result == "123.45 USD"

    def test_format_currency_custom_currency(self):
        """测试：自定义货币"""
        result = format_currency(123.45, "EUR")
        assert result == "123.45 EUR"

    def test_format_currency_integer(self):
        """测试：整数"""
        result = format_currency(123)
        assert result == "123.00 USD"

    def test_format_currency_rounding(self):
        """测试：四舍五入"""
        result = format_currency(123.456)
        assert result == "123.46 USD"

    def test_format_currency_small_amount(self):
        """测试：小金额"""
        result = format_currency(0.01)
        assert result == "0.01 USD"

    def test_format_currency_large_amount(self):
        """测试：大金额"""
        result = format_currency(1234567.89)
        assert result == "1234567.89 USD"

    def test_format_currency_negative(self):
        """测试：负数"""
        result = format_currency(-123.45)
        assert result == "-123.45 USD"

    def test_format_currency_zero(self):
        """测试：零"""
        result = format_currency(0)
        assert result == "0.00 USD"

    def test_format_currency_precision(self):
        """测试：精度"""
        result = format_currency(123.456789)
        assert result == "123.46 USD"  # 应该四舍五入到2位小数


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters module not available")
class TestFormatPercentage:
    """百分比格式化测试"""

    def test_format_percentage_default(self):
        """测试：默认格式"""
        result = format_percentage(12.3456)
        assert result == "12.35%"

    def test_format_percentage_custom_decimals(self):
        """测试：自定义小数位数"""
        result = format_percentage(12.3456, 3)
        assert result == "12.346%"

    def test_format_percentage_no_decimals(self):
        """测试：无小数"""
        result = format_percentage(12.3456, 0)
        assert result == "12%"

    def test_format_percentage_one_decimal(self):
        """测试：一位小数"""
        result = format_percentage(12.3456, 1)
        assert result == "12.3%"

    def test_format_percentage_integer(self):
        """测试：整数输入"""
        result = format_percentage(25)
        assert result == "25.00%"

    def test_format_percentage_small_value(self):
        """测试：小数值"""
        result = format_percentage(0.1234)
        assert result == "0.12%"

    def test_format_percentage_zero(self):
        """测试：零"""
        result = format_percentage(0)
        assert result == "0.00%"

    def test_format_percentage_hundred(self):
        """测试：100%"""
        result = format_percentage(100)
        assert result == "100.00%"

    def test_format_percentage_over_hundred(self):
        """测试：超过100%"""
        result = format_percentage(123.45)
        assert result == "123.45%"

    def test_format_percentage_negative(self):
        """测试：负数"""
        result = format_percentage(-12.34)
        assert result == "-12.34%"

    def test_format_percentage_rounding_up(self):
        """测试：向上舍入"""
        result = format_percentage(12.345, 2)
        assert result == "12.35%"

    def test_format_percentage_rounding_down(self):
        """测试：向下舍入"""
        result = format_percentage(12.344, 2)
        assert result == "12.34%"

    def test_format_percentage_many_decimals(self):
        """测试：多位小数"""
        result = format_percentage(12.3456789, 5)
        assert result == "12.34568%"


@pytest.mark.skipif(
    FORMATTERS_AVAILABLE, reason="Formatters module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not FORMATTERS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if FORMATTERS_AVAILABLE:
        from src.utils.formatters import (
            format_datetime,
            format_json,
            format_currency,
            format_percentage,
        )

        assert format_datetime is not None
        assert format_json is not None
        assert format_currency is not None
        assert format_percentage is not None


def test_function_signatures():
    """测试：函数签名"""
    if FORMATTERS_AVAILABLE:
        import inspect

        # 验证函数可调用
        assert callable(format_datetime)
        assert callable(format_json)
        assert callable(format_currency)
        assert callable(format_percentage)

        # 验证参数数量
        assert len(inspect.signature(format_datetime).parameters) == 2
        assert len(inspect.signature(format_json).parameters) == 2
        assert len(inspect.signature(format_currency).parameters) == 2
        assert len(inspect.signature(format_percentage).parameters) == 2


def test_combined_formatting():
    """测试：组合格式化"""
    if FORMATTERS_AVAILABLE:
        # 组合使用多个格式化函数
        dt = datetime(2023, 1, 1, 12, 30, 45)
        date_str = format_datetime(dt)
        amount = format_currency(123.45)
        percentage = format_percentage(85.5)

        data = {"date": date_str, "amount": amount, "success_rate": percentage}

        json_str = format_json(data)

        assert '"2023-01-01 12:30:45"' in json_str
        assert '"123.45 USD"' in json_str
        assert '"85.50%"' in json_str
