"""响应工具测试"""

import pytest


@pytest.mark.unit
class TestResponseUtils:
    """测试响应工具函数"""

    def test_create_success_response(self):
        """测试创建成功响应"""
        _data = {"message": "Success"}
        response = APIResponse.success(data)

        assert response["success"] is True
        assert response["data"] == data
        assert "timestamp" in response

    def test_create_error_response(self):
        """测试创建错误响应"""
        error = "Something went wrong"
        response = APIResponse.error(error)

        assert response["success"] is False
        assert response["message"] == error
        assert response["code"] == 500
        assert "timestamp" in response

    def test_api_response_model(self):
        """测试API响应模型"""
        if hasattr(APIResponseModel, "__init__"):
            response = APIResponseModel(success=True, message="OK", _data={"test": "data"})
            assert response.success is True
            assert response._data == {"test": "data"}
