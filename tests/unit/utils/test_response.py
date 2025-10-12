"""
API响应工具测试
Tests for API Response Utils

测试src.utils.response模块的响应格式化功能
"""

import pytest
from datetime import datetime
from src.utils.response import APIResponse, APIResponseModel, ResponseUtils


class TestAPIResponseModel:
    """API响应模型测试"""

    def test_model_creation_success(self):
        """测试：创建成功响应模型"""
        model = APIResponseModel(
            success=True, message="操作成功", data={"id": 1, "name": "test"}, code="200"
        )

        assert model.success is True
        assert model.message == "操作成功"
        assert model.data == {"id": 1, "name": "test"}
        assert model.code == "200"

    def test_model_creation_error(self):
        """测试：创建错误响应模型"""
        model = APIResponseModel(success=False, message="操作失败", code="500")

        assert model.success is False
        assert model.message == "操作失败"
        assert model.data is None
        assert model.code == "500"

    def test_model_defaults(self):
        """测试：模型默认值"""
        model = APIResponseModel(success=True, message="测试")

        assert model.success is True
        assert model.message == "测试"
        assert model.data is None
        assert model.code is None

    def test_model_serialization(self):
        """测试：模型序列化"""
        model = APIResponseModel(success=True, message="测试", data={"key": "value"})

        json_data = model.model_dump()
        assert json_data["success"] is True
        assert json_data["message"] == "测试"
        assert json_data["data"] == {"key": "value"}
        assert json_data["code"] is None


class TestAPIResponseSuccess:
    """API成功响应测试"""

    def test_success_without_data(self):
        """测试：成功响应（无数据）"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "timestamp" in response
        assert "data" not in response

    def test_success_with_data(self):
        """测试：成功响应（带数据）"""
        test_data = {"id": 1, "name": "test"}
        response = APIResponse.success(data=test_data)

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_with_custom_message(self):
        """测试：成功响应（自定义消息）"""
        response = APIResponse.success(message="创建成功")

        assert response["success"] is True
        assert response["message"] == "创建成功"
        assert "timestamp" in response

    def test_success_with_none_data(self):
        """测试：成功响应（数据为None）"""
        response = APIResponse.success(data=None)

        assert response["success"] is True
        assert "data" not in response

    def test_success_with_empty_data(self):
        """测试：成功响应（空数据）"""
        response = APIResponse.success(data={})

        assert response["success"] is True
        assert response["data"] == {}

    def test_success_with_list_data(self):
        """测试：成功响应（列表数据）"""
        test_data = [1, 2, 3, {"test": "value"}]
        response = APIResponse.success(data=test_data)

        assert response["success"] is True
        assert response["data"] == test_data

    def test_success_timestamp_format(self):
        """测试：成功响应时间戳格式"""
        response = APIResponse.success()
        timestamp = response["timestamp"]

        # ISO格式应该包含T和时区信息
        assert "T" in timestamp
        assert isinstance(timestamp, str)

    def test_success_response_alias(self):
        """测试：成功响应别名方法"""
        test_data = {"result": "ok"}
        response1 = APIResponse.success(data=test_data)
        response2 = APIResponse.success_response(data=test_data)

        # 比较除了时间戳之外的所有字段
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["data"] == response2["data"]
        # 时间戳会不同，所以不比较


class TestAPIResponseError:
    """API错误响应测试"""

    def test_error_default(self):
        """测试：错误响应（默认参数）"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500
        assert "timestamp" in response
        assert "data" not in response

    def test_error_with_message(self):
        """测试：错误响应（自定义消息）"""
        response = APIResponse.error(message="验证失败")

        assert response["success"] is False
        assert response["message"] == "验证失败"
        assert response["code"] == 500

    def test_error_with_code(self):
        """测试：错误响应（自定义错误码）"""
        response = APIResponse.error(code=404, message="未找到")

        assert response["success"] is False
        assert response["message"] == "未找到"
        assert response["code"] == 404

    def test_error_with_data(self):
        """测试：错误响应（带数据）"""
        error_data = {"field": "email", "error": "格式无效"}
        response = APIResponse.error(message="验证错误", code=400, data=error_data)

        assert response["success"] is False
        assert response["message"] == "验证错误"
        assert response["code"] == 400
        assert response["data"] == error_data

    def test_error_with_none_data(self):
        """测试：错误响应（数据为None）"""
        response = APIResponse.error(data=None)

        assert response["success"] is False
        assert "data" not in response

    def test_error_response_alias(self):
        """测试：错误响应别名方法"""
        response1 = APIResponse.error(message="测试错误", code=400)
        response2 = APIResponse.error_response(message="测试错误", code=400)

        # 比较除了时间戳之外的所有字段
        assert response1["success"] == response2["success"]
        assert response1["message"] == response2["message"]
        assert response1["code"] == response2["code"]
        # 时间戳会不同，所以不比较

    def test_error_different_codes(self):
        """测试：不同的错误代码"""
        codes = [200, 400, 401, 403, 404, 500, 503]

        for code in codes:
            response = APIResponse.error(code=code)
            assert response["code"] == code

    def test_error_string_code(self):
        """测试：字符串错误代码"""
        response = APIResponse.error(code="VALIDATION_ERROR")

        assert response["code"] == "VALIDATION_ERROR"


class TestResponseUtils:
    """响应工具别名测试"""

    def test_response_utils_alias(self):
        """测试：ResponseUtils别名"""
        assert ResponseUtils is APIResponse

    def test_response_utils_success(self):
        """测试：ResponseUtils成功方法"""
        response = ResponseUtils.success(data={"test": True})

        assert response["success"] is True
        assert response["data"] == {"test": True}

    def test_response_utils_error(self):
        """测试：ResponseUtils错误方法"""
        response = ResponseUtils.error(message="测试错误")

        assert response["success"] is False
        assert response["message"] == "测试错误"


class TestAPIResponseEdgeCases:
    """API响应边界情况测试"""

    def test_large_data_response(self):
        """测试：大数据响应"""
        large_data = {"items": list(range(1000))}
        response = APIResponse.success(data=large_data)

        assert response["success"] is True
        assert len(response["data"]["items"]) == 1000

    def test_nested_data_response(self):
        """测试：嵌套数据响应"""
        nested_data = {
            "user": {"profile": {"settings": {"theme": "dark", "notifications": True}}}
        }
        response = APIResponse.success(data=nested_data)

        assert response["success"] is True
        assert response["data"]["user"]["profile"]["settings"]["theme"] == "dark"

    def test_special_characters_in_message(self):
        """测试：消息中的特殊字符"""
        messages = [
            "操作成功！",
            "Error: Invalid input",
            "测试中文消息",
            'Message with "quotes"',
            "Line 1\nLine 2",
        ]

        for msg in messages:
            response = APIResponse.success(message=msg)
            assert response["message"] == msg

    def test_boolean_data_response(self):
        """测试：布尔数据响应"""
        response = APIResponse.success(data=True)
        assert response["data"] is True

        response = APIResponse.success(data=False)
        assert response["data"] is False

    def test_numeric_data_response(self):
        """测试：数值数据响应"""
        # 整数
        response = APIResponse.success(data=42)
        assert response["data"] == 42

        # 浮点数
        response = APIResponse.success(data=3.14)
        assert response["data"] == 3.14

        # 零
        response = APIResponse.success(data=0)
        assert response["data"] == 0

    def test_response_consistency(self):
        """测试：响应一致性"""
        # 多次调用应该返回相同格式的响应
        responses = [
            APIResponse.success(),
            APIResponse.success(),
            APIResponse.error(),
            APIResponse.error(),
        ]

        for response in responses:
            assert "success" in response
            assert "message" in response
            assert "timestamp" in response
            assert isinstance(response["success"], bool)
            assert isinstance(response["message"], str)
            assert isinstance(response["timestamp"], str)


class TestAPIResponsePerformance:
    """API响应性能测试"""

    def test_response_creation_speed(self):
        """测试：响应创建速度"""
        import time

        start_time = time.time()

        for _ in range(1000):
            APIResponse.success(data={"test": "data"})
            APIResponse.error(message="test error")

        end_time = time.time()

        # 1000个响应应该在1秒内创建完成
        assert end_time - start_time < 1.0

    def test_large_response_serialization(self):
        """测试：大响应序列化"""
        import json

        large_data = {
            "users": [
                {"id": i, "name": f"user_{i}", "data": "x" * 100} for i in range(100)
            ]
        }

        response = APIResponse.success(data=large_data)

        # 应该能够序列化为JSON
        json_str = json.dumps(response)
        assert len(json_str) > 1000


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    from src.utils.response import APIResponse, APIResponseModel, ResponseUtils

    assert APIResponse is not None
    assert APIResponseModel is not None
    assert ResponseUtils is not None


def test_all_classes_exported():
    """测试：所有类都被导出"""
    import src.utils.response as response_module

    expected_classes = ["APIResponseModel", "APIResponse", "ResponseUtils"]

    for class_name in expected_classes:
        assert hasattr(response_module, class_name)


def test_static_methods():
    """测试：静态方法存在"""
    assert hasattr(APIResponse, "success")
    assert hasattr(APIResponse, "success_response")
    assert hasattr(APIResponse, "error")
    assert hasattr(APIResponse, "error_response")

    # 验证它们是可调用的
    assert callable(getattr(APIResponse, "success"))
    assert callable(getattr(APIResponse, "error"))
