#!/usr/bin/env python3
""""""""
通用模型测试
测试 src.models.common_models 模块的功能
""""""""


import pytest

from src.models.common_models import APIResponse, ErrorResponse


@pytest.mark.unit
class TestAPIResponse:
    """API响应测试"""

    def test_api_response_creation_basic(self):
        """测试基础API响应创建"""
        response = APIResponse(success=True, message="操作成功")

        assert response.success is True
        assert response.message == "操作成功"
        assert response.data is None
        assert response.code is None

    def test_api_response_creation_with_data(self):
        """测试带数据的API响应创建"""
        test_data = {"id": 1, "name": "test"}
        response = APIResponse(
            success=True, message="查询成功", data=test_data, code="SUCCESS"
        )

        assert response.success is True
        assert response.message == "查询成功"
        assert response.data == test_data
        assert response.code == "SUCCESS"

    def test_api_response_creation_error(self):
        """测试错误API响应创建"""
        response = APIResponse(success=False, message="操作失败", code="ERROR_CODE")

        assert response.success is False
        assert response.message == "操作失败"
        assert response.code == "ERROR_CODE"

    def test_api_response_different_data_types(self):
        """测试不同数据类型的API响应"""
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

        # 字典数据
        response5 = APIResponse(success=True, message="OK", data={"key": "value"})
        assert response5.data == {"key": "value"}

    def test_api_response_empty_data(self):
        """测试空数据的API响应"""
        response = APIResponse(success=True, message="OK", data=None)
        assert response.data is None

    def test_api_response_long_message(self):
        """测试长消息的API响应"""
        long_message = "这是一个很长的消息，包含很多文字内容，用于测试API响应是否能正确处理长文本消息的情况,确保系统稳定性。"
        response = APIResponse(success=True, message=long_message)

        assert response.message == long_message
        assert len(response.message) > 50

    def test_api_response_special_characters(self):
        """测试特殊字符的API响应"""
        special_message = "测试特殊字符:@#$%^&*()_+-=[]{}|\\;':\",./<>?"
        response = APIResponse(success=True, message=special_message)

        assert response.message == special_message
        assert "@" in response.message
        assert "#" in response.message

    def test_api_response_unicode_content(self):
        """测试Unicode内容的API响应"""
        unicode_data = {"测试": "中文", "emoji": "🎉", "symbols": "αβγ"}
        response = APIResponse(success=True, message="Unicode测试", data=unicode_data)

        assert response.message == "Unicode测试"
        assert response.data["测试"] == "中文"
        assert response.data["emoji"] == "🎉"
        assert response.data["symbols"] == "αβγ"


@pytest.mark.unit
class TestErrorResponse:
    """错误响应测试"""

    def test_error_response_creation_basic(self):
        """测试基础错误响应创建"""
        error = ErrorResponse(
            error_code="VALIDATION_ERROR", error_message="输入验证失败"
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.error_message == "输入验证失败"

    def test_error_response_with_details(self):
        """测试带详情的错误响应创建"""
        details = {
            "field": "email",
            "message": "邮箱格式不正确",
            "expected_format": "user@domain.com",
        }
        error = ErrorResponse(
            error_code="VALIDATION_ERROR", error_message="输入验证失败", details=details
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.error_message == "输入验证失败"
        assert error.details == details

    def test_error_response_different_error_codes(self):
        """测试不同错误码的错误响应"""
        error_codes = [
            "VALIDATION_ERROR",
            "AUTHENTICATION_ERROR",
            "AUTHORIZATION_ERROR",
            "NOT_FOUND_ERROR",
            "INTERNAL_SERVER_ERROR",
            "RATE_LIMIT_ERROR",
        ]

        for error_code in error_codes:
            error = ErrorResponse(error_code=error_code, error_message="Test error")
            assert error.error_code == error_code
            assert error.error_message == "Test error"

    def test_error_response_complex_details(self):
        """测试复杂详情的错误响应"""
        complex_details = {
            "validation_errors": [
                {"field": "email", "errors": ["invalid_format", "required"]},
                {"field": "password", "errors": ["too_short", "missing_uppercase"]},
            ],
            "request_info": {
                "endpoint": "/api/users",
                "method": "POST",
                "timestamp": "2024-01-01T12:00:00Z",
            },
            "suggestions": ["检查邮箱格式", "使用更强的密码"],
        }

        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            error_message="多个验证错误",
            details=complex_details,
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.error_message == "多个验证错误"
        assert len(error.details["validation_errors"]) == 2
        assert "email" in str(error.details)
        assert "password" in str(error.details)

    def test_error_response_empty_details(self):
        """测试空详情的错误响应"""
        error = ErrorResponse(
            error_code="GENERIC_ERROR", error_message="通用错误", details={}
        )

        assert error.error_code == "GENERIC_ERROR"
        assert error.error_message == "通用错误"
        assert error.details == {}

    def test_error_response_long_messages(self):
        """测试长消息的错误响应"""
        long_error_message =
    "这是一个非常长的错误消息，详细描述了系统中发生的错误情况，包括错误的原因,影响范围以及可能的解决方案。这个消息可能会被记录到日志中,用于后续的错误分析和系统改进工作。"

        error = ErrorResponse(
            error_code="DETAILED_ERROR", error_message=long_error_message
        )

        assert error.error_code == "DETAILED_ERROR"
        assert error.error_message == long_error_message
        assert len(error.error_message) > 100

    def test_error_response_special_characters_in_code(self):
        """测试错误码中特殊字符的处理"""
        error = ErrorResponse(
            error_code="ERROR_WITH_SPECIAL_CHARS_!@#$%",
            error_message="Test error message",
        )

        assert error.error_code == "ERROR_WITH_SPECIAL_CHARS_!@#$%"
        assert error.error_message == "Test error message"
