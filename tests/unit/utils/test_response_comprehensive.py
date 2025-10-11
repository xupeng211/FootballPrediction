"""
响应工具模块完整测试
"""

import pytest
from datetime import datetime
from src.utils.response import APIResponse, APIResponseModel


class TestAPIResponse:
    """API响应工具类测试"""

    def test_success_default(self):
        """测试默认成功响应"""
        result = APIResponse.success()

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert "data" not in result
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "test"}
        result = APIResponse.success(data=test_data)

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_success_with_custom_message(self):
        """测试带自定义消息的成功响应"""
        custom_message = "创建成功"
        result = APIResponse.success(message=custom_message)

        assert result["success"] is True
        assert result["message"] == custom_message
        assert "data" not in result
        assert "timestamp" in result

    def test_success_with_data_and_message(self):
        """测试带数据和消息的成功响应"""
        test_data = {"count": 10}
        custom_message = "查询完成"
        result = APIResponse.success(data=test_data, message=custom_message)

        assert result["success"] is True
        assert result["message"] == custom_message
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_success_with_none_data(self):
        """测试数据为None时的成功响应"""
        result = APIResponse.success(data=None)

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert "data" not in result
        assert "timestamp" in result

    def test_success_with_empty_data(self):
        """测试空数据的成功响应"""
        test_data = []
        result = APIResponse.success(data=test_data)

        assert result["success"] is True
        assert result["message"] == "操作成功"
        assert result["data"] == []
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
        result = APIResponse.success(data=test_data)

        assert result["success"] is True
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        test_data = {"test": "alias"}
        result = APIResponse.success_response(data=test_data, message="别名测试")

        assert result["success"] is True
        assert result["message"] == "别名测试"
        assert result["data"] == test_data
        assert "timestamp" in result

    def test_error_default(self):
        """测试默认错误响应"""
        result = APIResponse.error()

        assert result["success"] is False
        assert result["message"] == "操作失败"
        assert result["code"] == 500  # 默认错误代码
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_custom_message(self):
        """测试带自定义消息的错误响应"""
        error_message = "用户不存在"
        result = APIResponse.error(message=error_message)

        assert result["success"] is False
        assert result["message"] == error_message
        assert result["code"] == 500
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_custom_code(self):
        """测试带自定义代码的错误响应"""
        result = APIResponse.error(code=404, message="资源未找到")

        assert result["success"] is False
        assert result["message"] == "资源未找到"
        assert result["code"] == 404
        assert "data" not in result
        assert "timestamp" in result

    def test_error_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"field": "email", "error": "邮箱格式不正确"}
        result = APIResponse.error(data=error_data, message="验证失败")

        assert result["success"] is False
        assert result["message"] == "验证失败"
        assert result["code"] == 500
        assert result["data"] == error_data
        assert "timestamp" in result

    def test_error_with_all_parameters(self):
        """测试带所有参数的错误响应"""
        error_data = {"details": "用户ID不能为空"}
        result = APIResponse.error(message="参数错误", code=400, data=error_data)

        assert result["success"] is False
        assert result["message"] == "参数错误"
        assert result["code"] == 400
        assert result["data"] == error_data
        assert "timestamp" in result

    def test_error_with_zero_code(self):
        """测试零错误代码"""
        result = APIResponse.error(code=0, message="未知错误")

        assert result["success"] is False
        assert result["code"] == 0
        assert result["message"] == "未知错误"

    def test_error_with_negative_code(self):
        """测试负数错误代码"""
        result = APIResponse.error(code=-1, message="自定义错误")

        assert result["success"] is False
        assert result["code"] == -1
        assert result["message"] == "自定义错误"

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        error_data = {"type": "validation"}
        result = APIResponse.error_response(
            message="别名错误", code=422, data=error_data
        )

        assert result["success"] is False
        assert result["message"] == "别名错误"
        assert result["code"] == 422
        assert result["data"] == error_data
        assert "timestamp" in result

    def test_timestamp_format(self):
        """测试时间戳格式"""
        result = APIResponse.success()
        timestamp_str = result["timestamp"]

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
        result = APIResponse.success(data="string value")
        assert result["data"] == "string value"

        # 数字
        result = APIResponse.success(data=42)
        assert result["data"] == 42

        # 布尔值
        result = APIResponse.success(data=True)
        assert result["data"] is True

        # 列表
        result = APIResponse.success(data=[1, 2, 3])
        assert result["data"] == [1, 2, 3]

        # None（应该被忽略）
        result = APIResponse.success(data=None)
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
            result = APIResponse.success(message=message)
            assert result["message"] == message
            assert result["success"] is True

    def test_response_structure_consistency(self):
        """测试响应结构一致性"""
        success_response = APIResponse.success(data={"test": "data"})
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
            success=True, message="测试响应", data={"key": "value"}, code="200"
        )

        assert model.success is True
        assert model.message == "测试响应"
        assert model.data == {"key": "value"}
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
        result = APIResponse.success(data={"initial": "value"})

        # 修改响应
        result["additional_field"] = "added"
        result["data"]["new_key"] = "new_value"

        assert result["additional_field"] == "added"
        assert result["data"]["new_key"] == "new_value"

    def test_multiple_calls_independence(self):
        """测试多次调用的独立性"""
        # 第一次调用
        result1 = APIResponse.success(data={"call": 1})

        # 等待一小段时间确保时间戳不同
        import time

        time.sleep(0.001)

        # 第二次调用
        result2 = APIResponse.success(data={"call": 2})

        # 验证结果独立
        assert result1["data"]["call"] == 1
        assert result2["data"]["call"] == 2
        assert result1["timestamp"] != result2["timestamp"]
        assert result1 != result2
