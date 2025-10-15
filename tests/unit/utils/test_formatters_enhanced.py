"""格式化工具增强测试"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from src.utils.formatters import (
    format_currency,
    format_percentage,
    format_datetime,
    format_file_size,
    format_duration,
    format_number,
    truncate_text,
    format_phone_number,
    format_json,
    escape_html
)


class TestFormattersEnhanced:
    """格式化工具增强测试"""

    def test_format_currency_usd(self):
        """测试美元货币格式"""
        assert format_currency(1234.56, 'USD') == "$1,234.56"
        assert format_currency(0, 'USD') == "$0.00"
        assert format_currency(1234567.89, 'USD') == "$1,234,567.89"

    def test_format_currency_eur(self):
        """测试欧元货币格式"""
        assert format_currency(1234.56, 'EUR') == "€1,234.56"
        assert format_currency(1234.56, 'EUR', locale='de-DE') == "1.234,56 €"

    def test_format_currency_negative(self):
        """测试负数货币格式"""
        assert format_currency(-123.45, 'USD') == "-$123.45"

    def test_format_percentage(self):
        """测试百分比格式"""
        assert format_percentage(0.1234) == "12.34%"
        assert format_percentage(0.123456, decimals=3) == "12.346%"
        assert format_percentage(1.0) == "100.00%"

    def test_format_datetime_default(self):
        """测试默认日期时间格式"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        formatted = format_datetime(dt)
        assert "2025-01-15" in formatted
        assert "14:30:45" in formatted

    def test_format_datetime_custom(self):
        """测试自定义日期时间格式"""
        dt = datetime(2025, 1, 15, 14, 30, 45)
        formatted = format_datetime(dt, format="%Y年%m月%d日")
        assert formatted == "2025年01月15日"

    def test_format_file_size_bytes(self):
        """测试文件大小格式 - 字节"""
        assert format_file_size(512) == "512 B"
        assert format_file_size(1023) == "1023 B"

    def test_format_file_size_kb(self):
        """测试文件大小格式 - KB"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1024 - 1) == "1024.0 KB"

    def test_format_file_size_mb(self):
        """测试文件大小格式 - MB"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(2.5 * 1024 * 1024) == "2.5 MB"

    def test_format_file_size_gb(self):
        """测试文件大小格式 - GB"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1.5 * 1024 * 1024 * 1024) == "1.5 GB"

    def test_format_duration_seconds(self):
        """测试持续时间格式 - 秒"""
        assert format_duration(30) == "30秒"
        assert format_duration(1) == "1秒"
        assert format_duration(0) == "0秒"

    def test_format_duration_minutes(self):
        """测试持续时间格式 - 分钟"""
        assert format_duration(60) == "1分钟"
        assert format_duration(90) == "1分30秒"
        assert format_duration(120) == "2分钟"

    def test_format_duration_hours(self):
        """测试持续时间格式 - 小时"""
        assert format_duration(3600) == "1小时"
        assert format_duration(3665) == "1小时1分5秒"
        assert format_duration(7200) == "2小时"

    def test_format_duration_days(self):
        """测试持续时间格式 - 天"""
        assert format_duration(86400) == "1天"
        assert format_duration(90061) == "1天1小时1分1秒"

    def test_format_number_with_separator(self):
        """测试数字格式化 - 千分位分隔符"""
        assert format_number(1234567) == "1,234,567"
        assert format_number(1234) == "1,234"
        assert format_number(1234567890) == "1,234,567,890"

    def test_format_number_with_decimals(self):
        """测试数字格式化 - 小数"""
        assert format_number(1234.5678, decimals=2) == "1,234.57"
        assert format_number(1234.5, decimals=3) == "1,234.500"

    def test_truncate_text_short(self):
        """测试文本截断 - 短文本"""
        text = "Hello"
        assert truncate_text(text, 10) == "Hello"

    def test_truncate_text_long(self):
        """测试文本截断 - 长文本"""
        text = "This is a very long text that needs to be truncated"
        assert truncate_text(text, 20) == "This is a very lo..."
        assert truncate_text(text, 20, suffix=" [more]") == "This is a very [more]"

    def test_truncate_text_words(self):
        """测试文本截断 - 按单词"""
        text = "One two three four five six seven eight nine ten"
        # 按单词截断（如果实现了）
        result = truncate_text(text, 20)
        assert len(result) <= 23  # 20 + "..." length

    def test_format_phone_number_us(self):
        """测试美国电话号码格式"""
        assert format_phone_number("1234567890", country="US") == "(123) 456-7890"
        assert format_phone_number("+11234567890", country="US") == "+1 (123) 456-7890"

    def test_format_json_pretty(self):
        """测试JSON格式化 - 美化"""
        data = {"name": "John", "age": 30, "active": True}
        formatted = format_json(data, pretty=True)
        assert '"name": "John"' in formatted
        assert '"age": 30' in formatted
        assert '{\n' in formatted or '{\r\n' in formatted

    def test_format_json_compact(self):
        """测试JSON格式化 - 紧凑"""
        data = {"name": "John", "age": 30}
        formatted = format_json(data, pretty=False)
        assert formatted == '{"name": "John", "age": 30}'

    def test_escape_html_basic(self):
        """测试HTML转义 - 基础"""
        assert escape_html("<div>Hello</div>") == "&lt;div&gt;Hello&lt;/div&gt;"
        assert escape_html("&amp;") == "&amp;amp;"
        assert escape_html('"Hello"') == "&quot;Hello&quot;"

    def test_escape_html_special_chars(self):
        """测试HTML转义 - 特殊字符"""
        special_chars = "<>&\"'"
        escaped = escape_html(special_chars)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped
        assert "&quot;" in escaped

    def test_format_decimal_precision(self):
        """测试Decimal精度格式化"""
        decimal_val = Decimal("123.456789")
        assert format_number(decimal_val, decimals=3) == "123.457"
        assert format_number(decimal_val, decimals=2) == "123.46"

    def test_format_large_numbers(self):
        """测试大数字格式化"""
        large_number = 1000000000000
        assert format_number(large_number) == "1,000,000,000"

    def test_format_duration_multiple_units(self):
        """测试多单位持续时间格式化"""
        # 1小时2分钟30秒
        duration = 3600 + 120 + 30
        formatted = format_duration(duration)
        assert "1小时" in formatted
        assert "2分" in formatted
        assert "30秒" in formatted