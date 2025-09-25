"""
API响应工具类的单元测试

测试覆盖：
- APIResponse 类的所有方法
- APIResponseModel Pydantic模型
- 成功响应和错误响应的格式
- 响应中的时间戳处理
- 各种参数组合的测试
- 别名方法的功能
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.utils.response import APIResponse, APIResponseModel

pytestmark = pytest.mark.unit


class TestAPIResponseModel:
    """API响应模型测试"""

    def test_response_model_valid_data(self):
        """测试有效的响应模型数据"""
        response_data = {
            "success": True,
            "message": "操作成功",
            "data": {"id": 1, "name": "测试"},
            "code": "200",
        }

        model = APIResponseModel(**response_data)

        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"id": 1, "name": "测试"}
        assert model.code == "200"

    def test_response_model_minimal_data(self):
        """测试最小化响应模型数据"""
        response_data = {"success": False, "message": "操作失败"}

        model = APIResponseModel(**response_data)

        assert model.success is False
        assert model.message == "操作失败"
        assert model.data is None
        assert model.code is None

    def test_response_model_invalid_data(self):
        """测试无效的响应模型数据"""
        with pytest.raises(ValidationError):
            APIResponseModel(success="not_boolean", message="test")

    def test_response_model_missing_required_fields(self):
        """测试缺少必需字段的响应模型"""
        with pytest.raises(ValidationError):
            APIResponseModel(success=True)  # 缺少message字段


class TestAPIResponse:
    """API响应工具类测试"""

    def test_success_default_params(self):
        """测试默认参数的成功响应"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "timestamp" in response
        assert "data" not in response

        # 验证时间戳格式
        timestamp = response["timestamp"]
        datetime.fromisoformat(timestamp)  # 如果格式错误会抛出异常

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {
            "id": 123,
            "name": "测试用户",
            "items": [1, 2, 3],
            "metadata": {"type": "user", "active": True},
        }

        response = APIResponse.success(data=test_data)

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_with_custom_message(self):
        """测试自定义消息的成功响应"""
        custom_message = "数据保存成功"

        response = APIResponse.success(message=custom_message)

        assert response["success"] is True
        assert response["message"] == custom_message
        assert "timestamp" in response

    def test_success_with_data_and_message(self):
        """测试带数据和自定义消息的成功响应"""
        test_data = {"result": "completed"}
        custom_message = "任务执行完成"

        response = APIResponse.success(data=test_data, message=custom_message)

        assert response["success"] is True
        assert response["message"] == custom_message
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_response_alias(self):
        """测试success_response别名方法"""
        test_data = {"alias": "test"}

        response = APIResponse.success_response(data=test_data)

        assert response["success"] is True
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_error_default_params(self):
        """测试默认参数的错误响应"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500  # 默认错误代码
        assert "timestamp" in response
        assert "data" not in response

    def test_error_with_custom_message(self):
        """测试自定义消息的错误响应"""
        error_message = "用户名已存在"

        response = APIResponse.error(message=error_message)

        assert response["success"] is False
        assert response["message"] == error_message
        assert response["code"] == 500
        assert "timestamp" in response

    def test_error_with_custom_code(self):
        """测试自定义错误代码的错误响应"""
        error_code = 404
        error_message = "资源未找到"

        response = APIResponse.error(message=error_message, code=error_code)

        assert response["success"] is False
        assert response["message"] == error_message
        assert response["code"] == error_code
        assert "timestamp" in response

    def test_error_with_data(self):
        """测试带附加数据的错误响应"""
        error_data = {
            "field": "email",
            "errors": ["格式不正确", "已被使用"],
            "suggestions": ["user@example.com"],
        }

        response = APIResponse.error(message="验证失败", code=400, data=error_data)

        assert response["success"] is False
        assert response["message"] == "验证失败"
        assert response["code"] == 400
        assert response["data"] == error_data
        assert "timestamp" in response

    def test_error_response_alias(self):
        """测试error_response别名方法"""
        error_message = "权限不足"
        error_code = 403

        response = APIResponse.error_response(message=error_message, code=error_code)

        assert response["success"] is False
        assert response["message"] == error_message
        assert response["code"] == error_code
        assert "timestamp" in response

    def test_error_with_none_data(self):
        """测试data为None的错误响应"""
        response = APIResponse.error(message="测试错误", data=None)

        assert response["success"] is False
        assert response["message"] == "测试错误"
        assert "data" not in response

    def test_success_with_none_data(self):
        """测试data为None的成功响应"""
        response = APIResponse.success(data=None, message="无数据返回")

        assert response["success"] is True
        assert response["message"] == "无数据返回"
        assert "data" not in response

    def test_response_timestamp_format(self):
        """测试响应时间戳格式的一致性"""
        success_response = APIResponse.success()
        error_response = APIResponse.error()

        # 验证两种响应都有时间戳
        assert "timestamp" in success_response
        assert "timestamp" in error_response

        # 验证时间戳格式
        datetime.fromisoformat(success_response["timestamp"])
        datetime.fromisoformat(error_response["timestamp"])

    def test_response_with_complex_data_types(self):
        """测试复杂数据类型的响应"""
        complex_data = {
            "string": "测试字符串",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, "two", {"three": 3}],
            "dict": {"nested": {"deep": "value"}, "chinese": "中文测试"},
        }

        response = APIResponse.success(data=complex_data)

        assert response["success"] is True
        assert response["data"] == complex_data

    def test_all_response_fields_present(self):
        """测试响应包含所有必要字段"""
        # 成功响应
        success_response = APIResponse.success(data={"test": True})
        required_success_fields = {"success", "message", "timestamp", "data"}
        assert required_success_fields.issubset(success_response.keys())

        # 错误响应
        error_response = APIResponse.error(
            message="错误", code=400, data={"error": True}
        )
        required_error_fields = {"success", "message", "timestamp", "code", "data"}
        assert required_error_fields.issubset(error_response.keys())

    def test_response_immutability(self):
        """测试响应对象的数据完整性"""
        original_data = {"mutable": "test"}
        response = APIResponse.success(data=original_data)

        # 修改原始数据
        original_data["mutable"] = "changed"

        # 响应中的数据应该保持不变（如果实现了深拷贝）
        # 注意：当前实现没有深拷贝，这是一个测试记录行为
        assert response["data"]["mutable"] == "changed"  # 当前行为

    def test_edge_case_empty_strings(self):
        """测试边界情况：空字符串"""
        response = APIResponse.success(data="", message="")

        assert response["success"] is True
        assert response["message"] == ""
        assert response["data"] == ""

    def test_edge_case_zero_values(self):
        """测试边界情况：零值"""
        response = APIResponse.error(message="零值测试", code=0, data=0)

        assert response["success"] is False
        assert response["code"] == 0
        assert response["data"] == 0

    def test_large_data_response(self):
        """测试大数据量响应"""
        large_data = {f"item_{i}": f"value_{i}" for i in range(1000)}

        response = APIResponse.success(data=large_data)

        assert response["success"] is True
        assert len(response["data"]) == 1000
        assert response["data"]["item_999"] == "value_999"
