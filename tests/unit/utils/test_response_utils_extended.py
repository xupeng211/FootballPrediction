"""响应工具测试"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.utils.response import APIResponse, APIResponseModel, ResponseUtils


class TestAPIResponse:
    """API响应工具测试"""

    def test_success_response(self):
        """测试创建成功响应"""
        _data = {"id": 1, "name": "test"}
        response = APIResponse.success(data, "操作成功")
        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "操作成功"
        assert "timestamp" in response

    def test_success_response_without_data(self):
        """测试无数据的成功响应"""
        response = APIResponse.success()
        assert response["success"] is True
        assert response["message"] == "操作成功"
        assert "data" not in response

    def test_error_response(self):
        """测试创建错误响应"""
        error = "Something went wrong"
        response = APIResponse.error(error, 400)
        assert response["success"] is False
        assert response["message"] == error
        assert response["code"] == 400
        assert "timestamp" in response

    def test_error_response_with_default_code(self):
        """测试默认错误代码的错误响应"""
        response = APIResponse.error("服务器错误")
        assert response["success"] is False
        assert response["code"] == 500

    def test_success_response_alias(self):
        """测试成功响应别名方法"""
        _data = {"test": "data"}
        response = APIResponse.success_response(data, "成功")
        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "成功"

    def test_error_response_alias(self):
        """测试错误响应别名方法"""
        response = APIResponse.error_response("失败", 404)
        assert response["success"] is False
        assert response["message"] == "失败"
        assert response["code"] == 404

    def test_api_response_model(self):
        """测试API响应模型"""
        model = APIResponseModel(
            success=True, message="测试消息", _data ={"key": "value"}, code="TEST_001"
        )
        assert model.success is True
        assert model.message == "测试消息"
        assert model._data == {"key": "value"}
        assert model.code == "TEST_001"
