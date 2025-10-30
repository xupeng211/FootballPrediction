#!/usr/bin/env python3
"""
API响应工具测试
测试 src.utils.response 模块的功能
"""

from unittest.mock import patch

import pytest

# 由于这个模块依赖pydantic,我们需要模拟pydantic
with patch.dict("sys.modules", {"pydantic": __import__("types").ModuleType("pydantic")}):
    # 模拟BaseModel
    class MockBaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    import sys

    sys.modules["pydantic"].BaseModel = MockBaseModel

    from src.utils.response import APIResponse, APIResponseModel


@pytest.mark.unit
class TestAPIResponse:
    """API响应工具测试"""

    def test_api_response_success_default(self):
        """测试默认成功响应"""
        result = APIResponse.success()

        expected = {"success": True, "message": "操作成功", "data": None, "code": None}
        assert result == expected

    def test_api_response_success_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "test"}
        result = APIResponse.success(data=test_data, message="创建成功")

        expected = {
            "success": True,
            "message": "创建成功",
            "data": test_data,
            "code": None,
        }
        assert result == expected

    def test_api_response_success_with_code(self):
        """测试带状态码的成功响应"""
        test_data = {"result": "ok"}
        result = APIResponse.success(data=test_data, message="查询成功", code="SUCCESS")

        expected = {
            "success": True,
            "message": "查询成功",
            "data": test_data,
            "code": "SUCCESS",
        }
        assert result == expected

    def test_api_response_model_creation(self):
        """测试API响应模型创建"""
        model = APIResponseModel(
            success=True, message="测试成功", data={"test": "data"}, code="TEST_CODE"
        )

        assert model.success is True
        assert model.message == "测试成功"
        assert model.data == {"test": "data"}
        assert model.code == "TEST_CODE"

    def test_api_response_model_default_values(self):
        """测试API响应模型默认值"""
        model = APIResponseModel(success=True, message="简单成功")

        assert model.success is True
        assert model.message == "简单成功"
        assert model.data is None
        assert model.code is None

    def test_api_response_different_data_types(self):
        """测试不同类型的数据响应"""
        # 字符串数据
        result1 = APIResponse.success(data="string data")
        assert result1["data"] == "string data"

        # 数字数据
        result2 = APIResponse.success(data=42)
        assert result2["data"] == 42

        # 列表数据
        result3 = APIResponse.success(data=[1, 2, 3])
        assert result3["data"] == [1, 2, 3]

        # 布尔数据
        result4 = APIResponse.success(data=True)
        assert result4["data"] is True

    def test_api_response_empty_data(self):
        """测试空数据响应"""
        result = APIResponse.success(data=None, message="无数据")

        expected = {"success": True, "message": "无数据", "data": None, "code": None}
        assert result == expected

    def test_api_response_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        special_message = "操作成功！包含中文字符和符号@#$%"
        result = APIResponse.success(message=special_message)

        assert result["message"] == special_message
        assert result["success"] is True

    def test_api_response_large_data(self):
        """测试大数据响应"""
        large_data = {
            "users": [{"id": i, "name": f"user_{i}"} for i in range(1000)],
            "metadata": {"total": 1000, "page": 1},
        }

        result = APIResponse.success(data=large_data, message="大数据查询")

        assert result["success"] is True
        assert result["message"] == "大数据查询"
        assert len(result["data"]["users"]) == 1000
        assert result["data"]["metadata"]["total"] == 1000
