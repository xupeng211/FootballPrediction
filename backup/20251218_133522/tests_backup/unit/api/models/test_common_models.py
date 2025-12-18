"""测试通用模型."""

import pytest
from datetime import datetime
from typing import List, Any, Optional, Dict
from pydantic import BaseModel


# 临时定义模型类用于测试
class BaseResponse(BaseModel):
    """基础响应模型."""

    success: bool
    timestamp: datetime

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class ErrorResponse(BaseResponse):
    """错误响应模型."""

    success: bool = False
    error_code: str
    message: str
    details: Optional[dict[str, Any]] = None


class SuccessResponse(BaseResponse):
    """成功响应模型."""

    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None


class ValidationError(BaseModel):
    """验证错误模型."""

    field: str
    message: str


class HealthCheckResponse(BaseModel):
    """健康检查响应模型."""

    status: str
    checks: dict[str, Any]


class TestBaseResponse:
    """测试基础响应模型."""

    def test_base_response_creation(self):
        """测试创建."""
        response = BaseResponse(success=True)
        assert response.success is True
        assert isinstance(response.timestamp, datetime)

    def test_base_response_serialization(self):
        """测试序列化."""
        response = BaseResponse(success=False)
        data = response.model_dump()

        assert "success" in data
        assert "timestamp" in data
        assert data["success"] is False


class TestErrorResponse:
    """测试错误响应模型."""

    def test_error_response_creation(self):
        """测试创建."""
        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "email", "issue": "invalid format"},
        )

        assert error.success is False
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Invalid input data"
        assert error.details["field"] == "email"

    def test_error_response_minimal(self):
        """测试最小错误响应."""
        error = ErrorResponse(error_code="NOT_FOUND", message="Resource not found")

        assert error.error_code == "NOT_FOUND"
        assert error.details is None


class TestSuccessResponse:
    """测试成功响应模型."""

    def test_success_response_creation(self):
        """测试创建."""
        data = {"id": 123, "name": "Test Match"}
        response = SuccessResponse(
            data=data, message="Operation completed successfully"
        )

        assert response.success is True
        assert response.data == data
        assert response.message == "Operation completed successfully"

    def test_success_response_without_message(self):
        """测试无消息的成功响应."""
        data = {"result": "success"}
        response = SuccessResponse(data=data)

        assert response.success is True
        assert response.data == data
        assert response.message is None


class TestValidationError:
    """测试验证错误模型."""

    def test_validation_error_creation(self):
        """测试创建."""
        errors = [
            ValidationError(field="email", message="Invalid email format"),
            ValidationError(field="age", message="Must be positive number"),
        ]

        assert len(errors) == 2
        assert errors[0].field == "email"
        assert errors[1].message == "Must be positive number"


class TestHealthCheckResponse:
    """测试健康检查响应模型."""

    def test_health_check_response_creation(self):
        """测试创建."""
        checks = {
            "database": {"status": "healthy", "response_time": 12},
            "redis": {"status": "healthy", "response_time": 5},
            "external_api": {"status": "unhealthy", "error": "timeout"},
        }

        health = HealthCheckResponse(status="degraded", checks=checks)

        assert health.status == "degraded"
        assert len(health.checks) == 3
        assert health.checks["database"]["status"] == "healthy"
        assert health.checks["external_api"]["error"] == "timeout"

    def test_health_check_all_healthy(self):
        """测试全部健康."""
        checks = {"database": {"status": "healthy"}, "redis": {"status": "healthy"}}

        health = HealthCheckResponse(status="healthy", checks=checks)

        assert health.status == "healthy"
        assert all(check["status"] == "healthy" for check in health.checks.values())
