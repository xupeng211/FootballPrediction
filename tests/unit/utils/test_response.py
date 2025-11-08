"""
API response utilities test
"""

import pytest
from datetime import datetime
from src.utils.response import APIResponse, APIResponseModel, ResponseUtils


class TestAPIResponse:
    """API响应工具测试"""

    def test_success_basic(self):
        """测试基础成功响应"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "timestamp" in response
        assert "data" not in response

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "test"}
        response = APIResponse.success(test_data)

        assert response["success"] is True
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_custom_message(self):
        """测试自定义消息的成功响应"""
        custom_message = "数据已成功保存"
        response = APIResponse.success(message=custom_message)

        assert response["success"] is True
        assert response["message"] == custom_message

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        test_data = {"test": "data"}
        response1 = APIResponse.success(test_data)
        response2 = APIResponse.success_response(test_data)

        # 比较核心字段，忽略时间戳差异
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["data"] == response2["data"]
        assert "timestamp" in response1
        assert "timestamp" in response2

    def test_error_basic(self):
        """测试基础错误响应"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500
        assert "timestamp" in response
        assert "data" not in response

    def test_error_with_custom_message(self):
        """测试自定义消息的错误响应"""
        custom_message = "数据验证失败"
        response = APIResponse.error(message=custom_message)

        assert response["success"] is False
        assert response["message"] == custom_message

    def test_error_with_code(self):
        """测试带错误码的错误响应"""
        error_code = 400
        response = APIResponse.error(code=error_code)

        assert response["success"] is False
        assert response["code"] == error_code

    def test_error_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"error": "validation failed"}
        response = APIResponse.error(data=error_data)

        assert response["success"] is False
        assert response["data"] == error_data

    def test_error_full(self):
        """测试完整的错误响应"""
        message = "业务规则验证失败"
        code = 422
        data = {"field": "email", "error": "invalid format"}

        response = APIResponse.error(message, code, data)

        assert response["success"] is False
        assert response["message"] == message
        assert response["code"] == code
        assert response["data"] == data
        assert "timestamp" in response

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        message = "测试错误"
        response1 = APIResponse.error(message=message)
        response2 = APIResponse.error_response(message=message)

        # 比较核心字段，忽略时间戳差异
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["code"] == response2["code"]
        assert "timestamp" in response1
        assert "timestamp" in response2

    def test_response_model_validation(self):
        """测试响应模型验证"""
        response_data = APIResponse.success({"test": "data"})

        # 应该能够成功创建模型实例
        model = APIResponseModel(
            success=response_data["success"],
            message=response_data["message"],
            data=response_data["data"],
        )

        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"test": "data"}

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = APIResponse.success()
        timestamp = response["timestamp"]

        # 验证是ISO格式
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        # 尝试解析为datetime来验证格式
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_response_utils_alias(self):
        """测试向后兼容的别名"""
        test_data = {"test": "alias"}

        response1 = APIResponse.success(test_data)
        response2 = ResponseUtils.success(test_data)

        # 比较核心字段，忽略时间戳差异
        assert response1["success"] == response2["success"]
        assert response1["data"] == response2["data"]
        assert "timestamp" in response1
        assert "timestamp" in response2

        error1 = APIResponse.error("test error")
        error2 = ResponseUtils.error("test error")

        # 比较核心字段，忽略时间戳差异
        assert error1["success"] == error2["success"]
        assert error1["message"] == error2["message"]
        assert error1["code"] == error2["code"]
        assert "timestamp" in error1
        assert "timestamp" in error2


class TestResponseIntegration:
    """响应集成测试"""

    def test_real_world_scenario(self):
        """测试真实世界场景"""
        # 模拟用户创建成功场景
        user_data = {
            "id": 123,
            "username": "testuser",
            "email": "test@example.com",
            "created_at": "2023-01-01T00:00:00",
        }

        success_response = APIResponse.success(data=user_data, message="用户创建成功")

        assert success_response["success"] is True
        assert success_response["message"] == "用户创建成功"
        assert success_response["data"]["id"] == 123

        # 模拟验证失败场景
        validation_errors = {
            "username": ["用户名不能为空"],
            "email": ["邮箱格式不正确"],
        }

        error_response = APIResponse.error(
            message="数据验证失败", code=422, data=validation_errors
        )

        assert error_response["success"] is False
        assert error_response["message"] == "数据验证失败"
        assert error_response["code"] == 422
        assert len(error_response["data"]) == 2
