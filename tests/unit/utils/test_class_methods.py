"""测试工具类方法"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.utils.response import ResponseUtils
from src.utils.time_utils import TimeUtils
from src.utils.string_utils import StringUtils
from src.utils.dict_utils import DictUtils
from src.utils.validators import Validators  # Validators类不存在，删除此行


@pytest.mark.unit
class TestResponseUtils:
    """测试响应工具方法"""

    def test_create_success_response(self):
        """测试创建成功响应"""
        _data = {"id": 1, "name": "test"}
        response = ResponseUtils.success(data)

        assert response["status"] == "success"
        assert response["data"] == data
        assert "timestamp" in response
        assert isinstance(response["timestamp"], datetime)

    def test_create_error_response(self):
        """测试创建错误响应"""
        error_msg = "Not found"
        response = ResponseUtils.error(error_msg, code=404)

        assert response["status"] == "error"
        assert response["message"] == error_msg
        assert response["code"] == 404
        assert "timestamp" in response

    def test_create_paginated_response(self):
        """测试创建分页响应"""
        items = [{"id": i} for i in range(1, 11)]
        response = ResponseUtils.paginated(items=items, page=1, per_page=10, total=100)

        assert response["status"] == "success"
        assert response["data"]["items"] == items
        assert response["data"]["pagination"]["page"] == 1
        assert response["data"]["pagination"]["per_page"] == 10
        assert response["data"]["pagination"]["total"] == 100
        assert response["data"]["pagination"]["total_pages"] == 10


@pytest.mark.unit
class TestTimeUtils:
    """测试时间工具方法"""

    def test_format_duration(self):
        """测试格式化持续时间"""
        # 测试秒数
        assert TimeUtils.format_duration(30) == "30s"

        # 测试分钟
        assert TimeUtils.format_duration(90) == "1m 30s"

        # 测试小时
        assert TimeUtils.format_duration(3661) == "1h 1m 1s"

        # 测试零值
        assert TimeUtils.format_duration(0) == "0s"

    def test_is_expired(self):
        """测试检查过期"""
        # 过去的时间戳
        past_time = datetime.utcnow() - timedelta(hours=1)
        assert TimeUtils.is_expired(past_time, ttl_minutes=30) is True

        # 未过期的时间戳
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        assert TimeUtils.is_expired(recent_time, ttl_minutes=30) is False

        # 边界情况
        exactly_30_min = datetime.utcnow() - timedelta(minutes=30)
        assert TimeUtils.is_expired(exactly_30_min, ttl_minutes=30) is True

    def test_parse_iso_string(self):
        """测试解析ISO时间字符串"""
        iso_str = "2024-01-15T10:30:00Z"
        parsed = TimeUtils.parse_iso_string(iso_str)

        assert isinstance(parsed, datetime)
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 15

    def test_get_time_range(self):
        """测试获取时间范围"""
        start, end = TimeUtils.get_time_range(days=7)

        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert (end - start).days == 7


@pytest.mark.unit
class TestStringUtils:
    """测试字符串工具方法"""

    def test_slugify(self):
        """测试生成slug"""
        assert StringUtils.slugify("Hello World") == "hello-world"
        assert StringUtils.slugify("Python & AI") == "python-ai"
        assert StringUtils.slugify("  Trim spaces  ") == "trim-spaces"
        assert StringUtils.slugify("") == ""

    def test_truncate(self):
        """测试截断字符串"""
        text = "This is a long text"
        assert StringUtils.truncate(text, 10) == "This is..."
        assert StringUtils.truncate(text, 20) == text
        assert StringUtils.truncate("", 10) == ""

    def test_is_email(self):
        """测试邮箱验证"""
        assert StringUtils.is_email("test@example.com") is True
        assert StringUtils.is_email("invalid.email") is False
        assert StringUtils.is_email("@domain.com") is False
        assert StringUtils.is_email("") is False

    def test_extract_numbers(self):
        """测试提取数字"""
        assert StringUtils.extract_numbers("abc123def456") == "123456"
        assert StringUtils.extract_numbers("no numbers") == ""
        assert StringUtils.extract_numbers("100") == "100"

    def test_capitalize_words(self):
        """测试单词首字母大写"""
        assert StringUtils.capitalize_words("hello world") == "Hello World"
        assert StringUtils.capitalize_words("PYTHON ROCKS") == "Python Rocks"
        assert StringUtils.capitalize_words("") == ""


@pytest.mark.unit
class TestDictUtils:
    """测试字典工具方法"""

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        _data = {"user": {"profile": {"name": "John"}}}

        # 存在的路径
        assert DictUtils.get_nested(data, "user.profile.name") == "John"

        # 不存在的路径
        assert DictUtils.get_nested(data, "user.profile.age") is None
        assert DictUtils.get_nested(data, "user.profile.age", default=0) == 0

        # 部分路径不存在
        assert DictUtils.get_nested(data, "user.settings.theme") is None

    def test_set_nested_value(self):
        """测试设置嵌套值"""
        _data = {}

        # 设置新值
        DictUtils.set_nested(data, "a.b.c", 123)
        assert _data == {"a": {"b": {"c": 123}}}

        # 覆盖现有值
        DictUtils.set_nested(data, "a.b.c", 456)
        assert data["a"]["b"]["c"] == 456

    def test_flatten_dict(self):
        """测试扁平化字典"""
        _data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}

        flat = DictUtils.flatten(data)
        expected = {"a": 1, "b.c": 2, "b.d.e": 3}
        assert flat == expected

    def test_filter_keys(self):
        """测试过滤键"""
        _data = {
            "id": 1,
            "name": "test",
            "password": "secret",
            "email": "test@example.com",
        }

        # 保留特定键
        filtered = DictUtils.filter_keys(data, ["id", "name"])
        assert filtered == {"id": 1, "name": "test"}

        # 排除特定键
        filtered = DictUtils.filter_keys(data, exclude=["password"])
        assert "password" not in filtered
        assert len(filtered) == 3

    def test_merge_dicts(self):
        """测试合并字典"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        merged = DictUtils.merge(dict1, dict2)
        assert merged == {"a": 1, "b": 3, "c": 4}

        # 深度合并
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": {"y": 2}}
        merged = DictUtils.merge(dict1, dict2, deep=True)
        assert merged == {"a": {"x": 1, "y": 2}}


# @pytest.mark.unit
# class TestValidators:
#     """测试验证器方法"""
#
#     def test_validate_positive_number(self):
#         """测试验证正数"""
#         assert Validators.validate_positive(5) is True
#         assert Validators.validate_positive(0) is False
#         assert Validators.validate_positive(-1) is False
#         assert Validators.validate_positive(Decimal("10.5")) is True
#
#     def test_validate_phone(self):
#         """测试验证电话号码"""
#         assert Validators.validate_phone("13800138000") is True
#         assert Validators.validate_phone("18812345678") is True
#         assert Validators.validate_phone("123456") is False
#         assert Validators.validate_phone("abc123") is False
#
#     def test_validate_date_range(self):
#         """测试验证日期范围"""
#         start = datetime(2024, 1, 1)
#         end = datetime(2024, 1, 31)
#
#         # 有效范围
#         assert Validators.validate_date_range(start, end) is True
#
#         # 无效范围（结束早于开始）
#         invalid_end = datetime(2023, 12, 31)
#         assert Validators.validate_date_range(start, invalid_end) is False
#
#         # 相同日期
#         assert Validators.validate_date_range(start, start) is True
#
#     def test_validate_required_fields(self):
#         """测试验证必填字段"""
#         _data = {"name": "John", "email": "john@example.com"}
#         required = ["name", "email"]
#
#         # 所有字段存在
#         assert Validators.validate_required_fields(data, required) is True
#
#         # 缺少字段
#         data2 = {"name": "John"}
#         assert Validators.validate_required_fields(data2, required) is False
#
#         # 空值
#         data3 = {"name": "", "email": None}
#         assert Validators.validate_required_fields(data3, required) is False
