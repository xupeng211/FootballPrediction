"""
响应工具模块完整测试
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.utils.response import APIResponse, APIResponseModel, ResponseUtils


class TestAPIResponse:
    """API响应工具类测试"""

    def test_success_default(self):
        """测试默认成功响应"""
        _result = APIResponse.success()

        assert _result["success"] is True
        assert _result["message"] == "操作成功"
        assert "data" not in result
        assert "timestamp" in result
        assert isinstance(_result["timestamp"], str)

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "test"}
        _result = APIResponse.success(_data=test_data)

        assert _result["success"] is True
        assert _result["message"] == "操作成功"
        assert _result["data"] == test_data
        assert "timestamp" in result

    def test_success_with_custom_message(self):
        """测试带自定义消息的成功响应"""
        custom_message = "创建成功"
        _result = APIResponse.success(message=custom_message)

        assert _result["success"] is True
        assert _result["message"] == custom_message
        assert "data" not in result
        assert "timestamp" in result

    def test_success_with_data_and_message(self):
        """测试带数据和消息的成功响应"""
        test_data = {"count": 10}
        custom_message = "查询完成"
        _result = APIResponse.success(_data=test_data, message=custom_message)

        assert _result["success"] is True
        assert _result["message"] == custom_message
        assert _result["data"] == test_data
        assert "timestamp" in result

    def test_success_with_none_data(self):
        """测试数据为None时的成功响应"""
        _result = APIResponse.success(_data=None)

        assert _result["success"] is True
        assert _result["message"] == "操作成功"
        assert "data" not in result
        assert "timestamp" in result

    def test_success_with_empty_data(self):
        """测试空数据的成功响应"""
        test_data = []
        _result = APIResponse.success(_data=test_data)

        assert _result["success"] is True
        assert _result["message"] == "操作成功"
        assert _result["data"] == []
        assert "timestamp" in result

    def test_success_with_complex_data(self):
        """测试复杂数据的成功响应"""
        test_data = {
            "users": [
                {"id": 1, "name": "User 1", "active": True},
                {"id": 2, "name": "User 2", "active": False},
            ],
            "pagination": {"page": 1, "total": 100, "has_next": True},
        }
        _result = APIResponse.success(_data=test_data)

        assert _result["success"] is True
        assert _result["data"] == test_data
        assert "timestamp" in result

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        test_data = {"test": "alias"}
        _result = APIResponse.success_response(_data=test_data, message="别名测试")

        assert _result["success"] is True
        assert _result["message"] == "别名测试"
        assert _result["data"] == test_data
        assert "timestamp" in result

    def test_error_default(self):
        """测试默认错误响应"""
        _result = APIResponse.error()

        assert _result["success"] is False
        assert _result["message"] == "操作失败"
        assert _result["code"] == 500  # 默认错误代码
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_custom_message(self):
        """测试带自定义消息的错误响应"""
        error_message = "用户不存在"
        _result = APIResponse.error(message=error_message)

        assert _result["success"] is False
        assert _result["message"] == error_message
        assert _result["code"] == 500
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_custom_code(self):
        """测试带自定义代码的错误响应"""
        _result = APIResponse.error(code=404, message="资源未找到")

        assert _result["success"] is False
        assert _result["message"] == "资源未找到"
        assert _result["code"] == 404
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"field": "email", "error": "邮箱格式不正确"}
        _result = APIResponse.error(_data=error_data, message="验证失败")

        assert _result["success"] is False
        assert _result["message"] == "验证失败"
        assert _result["code"] == 500
        assert _result["data"] == error_data
        assert "timestamp" in result

    def test_error_with_all_parameters(self):
        """测试带所有参数的错误响应"""
        error_data = {"details": "用户ID不能为空"}
        _result = APIResponse.error(message="参数错误", code=400, _data=error_data)

        assert _result["success"] is False
        assert _result["message"] == "参数错误"
        assert _result["code"] == 400
        assert _result["data"] == error_data
        assert "timestamp" in result

    def test_error_with_zero_code(self):
        """测试零错误代码"""
        _result = APIResponse.error(code=0, message="未知错误")

        assert _result["success"] is False
        assert _result["code"] == 0
        assert _result["message"] == "未知错误"

    def test_error_with_negative_code(self):
        """测试负数错误代码"""
        _result = APIResponse.error(code=-1, message="自定义错误")

        assert _result["success"] is False
        assert _result["code"] == -1
        assert _result["message"] == "自定义错误"

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        error_data = {"type": "validation"}
        _result = APIResponse.error_response(
            message="别名错误", code=422, _data=error_data
        )

        assert _result["success"] is False
        assert _result["message"] == "别名错误"
        assert _result["code"] == 422
        assert _result["data"] == error_data
        assert "timestamp" in result

    def test_timestamp_format(self):
        """测试时间戳格式"""
        _result = APIResponse.success()
        timestamp_str = _result["timestamp"]

        # 验证时间戳格式 (ISO 8601)
        timestamp = datetime.fromisoformat(timestamp_str)
        assert isinstance(timestamp, datetime)

        # 验证时间戳是最近的（5秒内）
        now = datetime.now()
        time_diff = abs((now - timestamp).total_seconds())
        assert time_diff < 5

    def test_different_data_types(self):
        """测试不同数据类型"""
        # 字符串
        _result = APIResponse.success(_data="string value")
        assert _result["data"] == "string value"

        # 数字
        _result = APIResponse.success(_data=42)
        assert _result["data"] == 42

        # 布尔值
        _result = APIResponse.success(_data=True)
        assert _result["data"] is True

        # 列表
        _result = APIResponse.success(_data=[1, 2, 3])
        assert _result["data"] == [1, 2, 3]

        # None（应该被忽略）
        _result = APIResponse.success(_data=None)
        assert "data" not in result

    def test_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        special_messages = [
            "包含中文的消息",
            "Message with emoji 🏈⚽",
            "Message with 'quotes'",
            'Message with "double quotes"',
            "Message with <script>alert('xss')</script>",
            "Line 1\nLine 2\tTabbed",
            "Message with & special chars",
        ]

        for message in special_messages:
            _result = APIResponse.success(message=message)
            assert _result["message"] == message
            assert _result["success"] is True

    def test_response_structure_consistency(self):
        """测试响应结构一致性"""
        success_response = APIResponse.success(_data={"test": "data"})
        error_response = APIResponse.error(message="test error", code=400)

        # 检查必要字段
        assert "success" in success_response
        assert "message" in success_response
        assert "timestamp" in success_response
        assert "data" in success_response

        assert "success" in error_response
        assert "message" in error_response
        assert "timestamp" in error_response
        assert "code" in error_response
        assert "data" not in error_response  # 没有数据时不应该包含

    def test_api_response_model_creation(self):
        """测试API响应模型创建"""
        model = APIResponseModel(
            success=True, message="测试响应", _data={"key": "value"}, code="200"
        )

        assert model.success is True
        assert model.message == "测试响应"
        assert model._data == {"key": "value"}
        assert model.code == "200"

    def test_api_response_model_optional_fields(self):
        """测试API响应模型可选字段"""
        model = APIResponseModel(success=False, message="错误响应")

        assert model.success is False
        assert model.message == "错误响应"
        assert model.data is None
        assert model.code is None

    def test_response_immutability(self):
        """测试响应是否可修改（应该可以修改，因为返回的是字典）"""
        _result = APIResponse.success(_data={"initial": "value"})

        # 修改响应
        _result["additional_field"] = "added"
        _result["data"]["new_key"] = "new_value"

        assert _result["additional_field"] == "added"
        assert _result["data"]["new_key"] == "new_value"

    def test_multiple_calls_independence(self):
        """测试多次调用的独立性"""
        # 第一次调用
        result1 = APIResponse.success(_data={"call": 1})

        # 等待一小段时间确保时间戳不同
        import time

        time.sleep(0.001)

        # 第二次调用
        _result2 = APIResponse.success(_data={"call": 2})

        # 验证结果独立
        assert result1["data"]["call"] == 1
        assert result2["data"]["call"] == 2
        assert result1["timestamp"] != result2["timestamp"]
        assert result1 != result2


class TestResponseUtils:
    """ResponseUtils别名测试"""

    def test_response_utils_is_alias(self):
        """测试：ResponseUtils是APIResponse的别名"""
        assert ResponseUtils is APIResponse
        assert hasattr(ResponseUtils, "success")
        assert hasattr(ResponseUtils, "error")
        assert ResponseUtils.success == APIResponse.success
        assert ResponseUtils.error == APIResponse.error
        assert ResponseUtils.success_response == APIResponse.success_response
        assert ResponseUtils.error_response == APIResponse.error_response

    def test_response_utils_functionality(self):
        """测试：ResponseUtils功能与APIResponse一致"""
        test_data = {"test": "ResponseUtils"}
        success1 = APIResponse.success(_data=test_data, message="APIResponse成功")
        success2 = ResponseUtils.success(_data=test_data, message="ResponseUtils成功")

        assert success1["success"] is True
        assert success2["success"] is True
        assert success1["data"] == success2["data"]
        assert success1["message"] != success2["message"]
        assert success2["message"] == "ResponseUtils成功"

        error1 = APIResponse.error(code=404, message="API错误")
        error2 = ResponseUtils.error(code=404, message="Utils错误")

        assert error1["success"] is False
        assert error2["success"] is False
        assert error1["code"] == error2["code"]
        assert error1["message"] != error2["message"]
        assert error2["message"] == "Utils错误"

    def test_response_utils_comprehensive(self):
        """测试：ResponseUtils综合功能"""
        # 成功响应
        success = ResponseUtils.success_response(
            _data={"items": ["item1", "item2"]}, message="通过别名获取数据成功"
        )
        assert success["success"] is True
        assert success["message"] == "通过别名获取数据成功"
        assert success["data"]["items"] == ["item1", "item2"]

        # 错误响应
        error = ResponseUtils.error_response(
            message="通过别名处理错误",
            code=422,
            _data={"field": "name", "reason": "不能为空"},
        )
        assert error["success"] is False
        assert error["message"] == "通过别名处理错误"
        assert error["code"] == 422
        assert error["data"]["field"] == "name"
        assert error["data"]["reason"] == "不能为空"
