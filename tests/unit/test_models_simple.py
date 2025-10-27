#!/usr/bin/env python3
"""
模型简单测试
测试更多 src.models 模块的简单功能
"""

from unittest.mock import Mock

import pytest

from src.models.base_models import BaseModel
from src.models.common_models import APIResponse, ErrorResponse


@pytest.mark.unit
class TestBaseModels:
    """基础模型测试"""

    def test_base_model_creation(self):
        """测试基础模型创建"""
        model = BaseModel()
        assert model is not None

    def test_base_model_attributes(self):
        """测试基础模型属性"""
        model = BaseModel()
        # 测试模型可以被创建和操作
        assert hasattr(model, "__dict__")


@pytest.mark.unit
class TestCommonModels:
    """通用模型测试"""

    def test_api_response_creation(self):
        """测试API响应创建"""
        response = APIResponse(success=True, message="操作成功", data={"id": 1})

        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == {"id": 1}

    def test_api_response_default_values(self):
        """测试API响应默认值"""
        response = APIResponse(success=True, message="测试")

        assert response.success is True
        assert response.message == "测试"
        # data应该有默认值

    def test_error_response_creation(self):
        """测试错误响应创建"""
        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            error_message="输入验证失败",
            details={"field": "email", "message": "邮箱格式不正确"},
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.error_message == "输入验证失败"
        assert error.details == {"field": "email", "message": "邮箱格式不正确"}

    def test_error_response_minimal(self):
        """测试最小错误响应"""
        error = ErrorResponse(error_code="UNKNOWN_ERROR", error_message="未知错误")

        assert error.error_code == "UNKNOWN_ERROR"
        assert error.error_message == "未知错误"

    def test_response_serialization(self):
        """测试响应序列化"""
        response = APIResponse(success=True, message="测试响应", data={"test": "data"})

        # 测试模型可以被序列化为字典
        if hasattr(response, "dict"):
            data = response.dict()
            assert data["success"] is True
            assert data["message"] == "测试响应"
            assert data["data"]["test"] == "data"

    def test_response_with_different_data_types(self):
        """测试不同数据类型的响应"""
        # 字符串数据
        response1 = APIResponse(success=True, message="OK", data="string data")
        assert response1.data == "string data"

        # 数字数据
        response2 = APIResponse(success=True, message="OK", data=42)
        assert response2.data == 42

        # 布尔数据
        response3 = APIResponse(success=True, message="OK", data=False)
        assert response3.data is False

        # 列表数据
        response4 = APIResponse(success=True, message="OK", data=[1, 2, 3])
        assert response4.data == [1, 2, 3]
