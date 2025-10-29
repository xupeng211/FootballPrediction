from datetime import datetime
"""
test_date_time_utils - 第14部分
从原文件 test_date_time_utils.py 拆分
创建时间: 2025-10-26 18:25:53.307648
包含项目: 5 个 (函数/类)
"""


class TestDateTimeUtilsPart14:
    """测试类"""

    def test_format_datetime(self):
        """测试格式化日期时间"""
        dt_obj = datetime.datetime(2023, 12, 25, 14, 30, 45)
        result = DateTimeParser.format_datetime(dt_obj)
        assert result == "2023-12-25 14:30:45"

    def test_parse_iso_format(self):
        """测试解析ISO格式"""
        iso_string = "2023-12-25T14:30:45"
        result = DateTimeParser.parse_iso_format(iso_string)
        expected = datetime.datetime(2023, 12, 25, 14, 30, 45)
        assert result == expected

    def test_to_iso_format(self):
        """测试转换为ISO格式"""
        dt_obj = datetime.datetime(2023, 12, 25, 14, 30, 45)
        result = DateTimeParser.to_iso_format(dt_obj)
        assert "2023-12-25T14:30:45" in result

    def test_parse_flexible(self):
        """测试灵活解析"""
        test_cases = [
            ("2023-12-25 14:30:45", datetime.datetime(2023, 12, 25, 14, 30, 45)),
            ("2023-12-25", datetime.datetime(2023, 12, 25, 0, 0, 0)),
            ("25/12/2023", datetime.datetime(2023, 12, 25, 0, 0, 0)),
            ("20231225", datetime.datetime(2023, 12, 25, 0, 0, 0)),
        ]

        for input_str, expected in test_cases:
            result = DateTimeParser.parse_flexible(input_str)
            assert result == expected

        # 测试无效格式
        result = DateTimeParser.parse_flexible("invalid date")
        assert result is None

    """时区工具测试"""
