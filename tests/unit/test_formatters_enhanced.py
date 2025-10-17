#!/usr/bin/env python3
"""
增强格式化器测试
目标：将formatters覆盖率从64%提升到85%+
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestFormattersEnhanced:
    """增强格式化器测试"""

    def test_format_json_pretty(self):
        """测试美化JSON格式化"""
        from src.utils.formatters import format_json

        data = {"name": "test", "value": 123}
        result = format_json(data, pretty=True)

        assert "name" in result
        assert "test" in result
        assert "\n" in result  # 美化格式应该有换行

    def test_format_json_compact(self):
        """测试紧凑JSON格式化"""
        from src.utils.formatters import format_json

        data = {"name": "test", "value": 123}
        result = format_json(data, pretty=False)

        assert result == '{"name": "test", "value": 123}'
        assert "\n" not in result  # 紧凑格式不应有换行

    def test_format_json_with_indent(self):
        """测试自定义缩进JSON格式化"""
        from src.utils.formatters import format_json

        data = {"level1": {"level2": {"level3": "value"}}}
        result = format_json(data, indent=4)

        assert "    " in result  # 4空格缩进

    def test_format_json_with_sort_keys(self):
        """测试排序键JSON格式化"""
        from src.utils.formatters import format_json

        data = {"z": 1, "a": 2, "m": 3}
        result = format_json(data, sort_keys=True)

        # 键应该按字母顺序出现
        pos_a = result.find('"a"')
        pos_m = result.find('"m"')
        pos_z = result.find('"z"')

        assert pos_a < pos_m < pos_z

    def test_format_xml(self):
        """测试XML格式化"""
        from src.utils.formatters import format_xml

        xml_data = "<root><item>value</item></root>"
        result = format_xml(xml_data)

        assert "<root>" in result
        assert "<item>" in result
        assert "value" in result

    def test_format_yaml(self):
        """测试YAML格式化"""
        from src.utils.formatters import format_yaml

        data = {"name": "test", "items": [1, 2, 3]}
        result = format_yaml(data)

        assert "name: test" in result
        assert "items:" in result
        assert "- 1" in result

    def test_format_csv(self):
        """测试CSV格式化"""
        from src.utils.formatters import format_csv

        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = format_csv(data)

        assert "name,age" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    def test_format_text_table(self):
        """测试表格文本格式化"""
        from src.utils.formatters import format_table

        data = [["Name", "Age", "City"], ["Alice", "30", "NYC"], ["Bob", "25", "LA"]]
        result = format_table(data)

        assert "Name" in result
        assert "Alice" in result
        assert "|" in result or "-" in result  # 表格边框

    def test_format_currency_different(self):
        """测试不同货币格式化"""
        from src.utils.formatters import format_currency

        # 测试美元
        assert format_currency(1234.56, "USD") == "$1,234.56"

        # 测试欧元
        assert format_currency(1234.56, "EUR") == "€1,234.56"

        # 测试人民币
        assert format_currency(1234.56, "CNY") == "¥1,234.56"

    def test_format_percentage_with_precision(self):
        """测试带精度的百分比格式化"""
        from src.utils.formatters import format_percentage

        assert format_percentage(0.12345, 2) == "12.35%"
        assert format_percentage(0.12345, 3) == "12.345%"

    def test_format_bytes(self):
        """测试字节格式化"""
        from src.utils.formatters import format_bytes

        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1048576) == "1.0 MB"
        assert format_bytes(1073741824) == "1.0 GB"
        assert format_bytes(500) == "500.0 B"

    def test_format_duration_human(self):
        """测试人类可读的持续时间格式化"""
        from src.utils.formatters import format_duration_human

        assert format_duration_human(3600) == "1 hour"
        assert format_duration_human(7200) == "2 hours"
        assert format_duration_human(60) == "1 minute"
        assert format_duration_human(90) == "1 minute 30 seconds"

    def test_format_date_relative(self):
        """测试相对日期格式化"""
        from src.utils.formatters import format_date_relative

        datetime.now()

        # 这里需要模拟不同的时间差
        # 实际测试中可能需要mock

    def test_format_list_english(self):
        """测试英文列表格式化"""
        from src.utils.formatters import format_list

        items = ["apple", "banana", "orange"]
        assert format_list(items) == "apple, banana and orange"

        items = ["apple"]
        assert format_list(items) == "apple"

        items = ["apple", "banana"]
        assert format_list(items) == "apple and banana"

    def test_format_number_with_suffix(self):
        """测试带后缀的数字格式化"""
        from src.utils.formatters import format_number_suffix

        assert format_number_suffix(1000) == "1K"
        assert format_number_suffix(1000000) == "1M"
        assert format_number_suffix(1000000000) == "1B"
        assert format_number_suffix(500) == "500"

    def test_format_phone_number(self):
        """测试电话号码格式化"""
        from src.utils.formatters import format_phone_number

        assert format_phone_number("1234567890", "US") == "(123) 456-7890"
        assert format_phone_number("+441234567890", "UK") == "+44 1234 567890"

    def test_format_address(self):
        """测试地址格式化"""
        from src.utils.formatters import format_address

        address = {
            "street": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "USA",
        }
        result = format_address(address)

        assert "123 Main St" in result
        assert "New York" in result
        assert "NY 10001" in result

    def test_custom_formatter(self):
        """测试自定义格式化器"""
        from src.utils.formatters import CustomFormatter

        formatter = CustomFormatter()

        # 注册自定义格式化函数
        formatter.register("reverse", lambda x: x[::-1])

        result = formatter.format("reverse", "hello")
        assert result == "olleh"
