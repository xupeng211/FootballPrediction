from datetime import datetime
# from src.utils.response import APIResponse, APIResponseModel

"""
测试API响应工具模块
"""


class TestAPIResponse:
    """测试APIResponse类"""

    def test_success_without_data(self):
        """测试成功响应（无数据）"""
        response = APIResponse.success()

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "timestamp" in response
        assert "data" not in response

    def test_success_with_data(self):
        """测试成功响应（有数据）"""
        test_data = {"id": 1, "name": "测试"}
        response = APIResponse.success(data=test_data)

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert response["data"] == test_data
        assert "timestamp" in response

    def test_success_custom_message(self):
        """测试成功响应（自定义消息）"""
        response = APIResponse.success(message="创建成功")

        assert response["success"] is True
        assert response["message"] == "创建成功"
        assert "timestamp" in response

    def test_success_none_data(self):
        """测试成功响应（数据为None）"""
        response = APIResponse.success(data=None)

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "data" not in response

    def test_success_with_empty_data(self):
        """测试成功响应（空数据）"""
        response = APIResponse.success(data="")

        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert response["data"] == ""

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        test_data = {"test": "value"}
        response = APIResponse.success_response(data=test_data, message="别名测试")

        assert response["success"] is True
        assert response["message"] == "别名测试"
        assert response["data"] == test_data

    def test_error_default(self):
        """测试错误响应（默认参数）"""
        response = APIResponse.error()

        assert response["success"] is False
        assert response["message"] == "操作失败"
        assert response["code"] == 500
        assert "timestamp" in response
        assert "data" not in response

    def test_error_with_message(self):
        """测试错误响应（自定义消息）"""
        response = APIResponse.error(message="权限不足")

        assert response["success"] is False
        assert response["message"] == "权限不足"
        assert response["code"] == 500

    def test_error_with_code(self):
        """测试错误响应（自定义代码）"""
        response = APIResponse.error(code=404)

        assert response["success"] is False
        assert response["code"] == 404

    def test_error_with_data(self):
        """测试错误响应（附加数据）"""
        error_data = {"field": "username", "error": "必填"}
        response = APIResponse.error(data=error_data)

        assert response["success"] is False
        assert response["data"] == error_data

    def test_error_with_all_params(self):
        """测试错误响应（所有参数）"""
        error_data = {"details": "详细错误信息"}
        response = APIResponse.error(message="验证失败", code=400, data=error_data)

        assert response["success"] is False
        assert response["message"] == "验证失败"
        assert response["code"] == 400
        assert response["data"] == error_data

    def test_error_with_none_code(self):
        """测试错误响应（代码为None）"""
        response = APIResponse.error(code=None)

        assert response["success"] is False
        assert response["code"] == 500  # 应该使用默认值

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        response = APIResponse.error_response(
            message="别名错误测试", code=422, data={"test": "error"}
        )

        assert response["success"] is False
        assert response["message"] == "别名错误测试"
        assert response["code"] == 422
        assert response["data"] == {"test": "error"}

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = APIResponse.success()
        timestamp = response["timestamp"]

        # 验证ISO格式
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)

    def test_response_structure(self):
        """测试响应结构完整性"""
        # 成功响应
        success = APIResponse.success(data={"test": "data"})
        assert all(
            key in success for key in ["success", "message", "timestamp", "data"]
        )

        # 错误响应
        error = APIResponse.error(code=400)
        assert all(key in error for key in ["success", "message", "timestamp", "code"])


class TestAPIResponseModel:
    """测试APIResponseModel"""

    def test_model_creation(self):
        """测试模型创建"""
        model = APIResponseModel(
            success=True, message="测试消息", data={"key": "value"}, code="TEST_001"
        )

        assert model.success is True
        assert model.message == "测试消息"
        assert model.data == {"key": "value"}
        assert model.code == "TEST_001"

    def test_model_optional_fields(self):
        """测试模型的可选字段"""
        model = APIResponseModel(success=False, message="错误消息")

        assert model.success is False
        assert model.message == "错误消息"
        assert model.data is None
        assert model.code is None

    def test_model_serialization(self):
        """测试模型序列化"""
        model = APIResponseModel(
            success=True, message="测试", data={"id": 1}, code="SUCCESS"
        )

        data = model.model_dump()

        assert data["success"] is True
        assert data["message"] == "测试"
        assert data["data"] == {"id": 1}
        assert data["code"] == "SUCCESS"
