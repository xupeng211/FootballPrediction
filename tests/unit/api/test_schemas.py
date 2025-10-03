"""
API响应模型测试
测试覆盖src/api/schemas.py中的所有模型
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from typing import Dict, Any

from src.api.schemas import (
    ServiceCheck,
    HealthCheckResponse,
    StatusResponse,
    MetricsResponse,
    RootResponse,
    ErrorResponse
)


class TestServiceCheck:
    """测试ServiceCheck模型"""

    def test_service_check_creation_success(self):
        """测试创建服务检查结果成功"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=15.5,
            details={"message": "服务正常"}
        )

        assert check.status == "healthy"
        assert check.response_time_ms == 15.5
        assert check.details["message"] == "服务正常"

    def test_service_check_creation_without_details(self):
        """测试创建服务检查结果（无详细信息）"""
        check = ServiceCheck(
            status="unhealthy",
            response_time_ms=100.0
        )

        assert check.status == "unhealthy"
        assert check.response_time_ms == 100.0
        assert check.details is None

    def test_service_check_validation_error(self):
        """测试ServiceCheck验证错误"""
        with pytest.raises(ValidationError) as exc_info:
            ServiceCheck()

        assert "status" in str(exc_info.value)
        assert "response_time_ms" in str(exc_info.value)

    def test_service_check_different_statuses(self):
        """测试不同的服务状态"""
        statuses = ["healthy", "unhealthy", "degraded", "skipped"]

        for status in statuses:
            check = ServiceCheck(
                status=status,
                response_time_ms=10.0
            )
            assert check.status == status

    def test_service_check_with_complex_details(self):
        """测试带有复杂详细信息的服务检查"""
        details = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "connections": 150,
            "last_check": datetime.now().isoformat(),
            "metrics": {
                "requests_per_second": 1000,
                "error_rate": 0.01
            }
        }

        check = ServiceCheck(
            status="healthy",
            response_time_ms=25.3,
            details=details
        )

        assert check.details == details
        assert check.details["metrics"]["requests_per_second"] == 1000


class TestHealthCheckResponse:
    """测试HealthCheckResponse模型"""

    def test_health_check_response_creation(self):
        """测试健康检查响应创建"""
        checks = {
            "database": ServiceCheck(status="healthy", response_time_ms=5.0),
            "redis": ServiceCheck(status="healthy", response_time_ms=2.0),
            "kafka": ServiceCheck(status="degraded", response_time_ms=50.0)
        }

        response = HealthCheckResponse(
            status="healthy",
            timestamp="2024-01-15T10:00:00Z",
            service="football-prediction-api",
            version="1.0.0",
            uptime=3600.0,
            response_time_ms=15.5,
            checks=checks
        )

        assert response.status == "healthy"
        assert response.service == "football-prediction-api"
        assert response.version == "1.0.0"
        assert response.uptime == 3600.0
        assert len(response.checks) == 3
        assert response.checks["database"].status == "healthy"

    def test_health_check_response_unhealthy(self):
        """测试不健康的健康检查响应"""
        checks = {
            "database": ServiceCheck(status="unhealthy", response_time_ms=1000.0),
            "redis": ServiceCheck(status="healthy", response_time_ms=2.0)
        }

        response = HealthCheckResponse(
            status="unhealthy",
            timestamp="2024-01-15T10:00:00Z",
            service="football-prediction-api",
            version="1.0.0",
            uptime=100.0,
            response_time_ms=1200.0,
            checks=checks
        )

        assert response.status == "unhealthy"
        assert response.checks["database"].status == "unhealthy"

    def test_health_check_response_validation(self):
        """测试健康检查响应验证"""
        # 测试缺少必要字段
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(
                status="healthy",
                timestamp="2024-01-15T10:00:00Z"
                # 缺少其他必要字段
            )

        # 检查错误信息包含缺少的字段
        assert "service" in str(exc_info.value)
        assert "version" in str(exc_info.value)

    def test_health_check_response_with_all_checks_healthy(self):
        """测试所有检查都健康的响应"""
        services = ["database", "redis", "kafka", "mlflow", "filesystem"]
        checks = {}

        for service in services:
            checks[service] = ServiceCheck(
                status="healthy",
                response_time_ms=10.0,
                details={"message": f"{service} is running"}
            )

        response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            service="test-service",
            version="2.0.0",
            uptime=86400.0,
            response_time_ms=25.0,
            checks=checks
        )

        assert all(check.status == "healthy" for check in response.checks.values())
        assert len(response.checks) == len(services)


class TestStatusResponse:
    """测试StatusResponse模型"""

    def test_status_response_creation(self):
        """测试状态响应创建"""
        services = {
            "database": "healthy",
            "redis": "healthy",
            "kafka": "degraded",
            "cache": "unhealthy"
        }

        response = StatusResponse(
            status="degraded",
            timestamp="2024-01-15T10:00:00Z",
            services=services
        )

        assert response.status == "degraded"
        assert response.services["database"] == "healthy"
        assert response.services["cache"] == "unhealthy"
        assert len(response.services) == 4

    def test_status_response_all_healthy(self):
        """测试所有服务健康的状态响应"""
        response = StatusResponse(
            status="healthy",
            timestamp="2024-01-15T10:00:00Z",
            services={
                "api": "healthy",
                "database": "healthy",
                "cache": "healthy"
            }
        )

        assert response.status == "healthy"
        assert all(status == "healthy" for status in response.services.values())

    def test_status_response_validation(self):
        """测试状态响应验证"""
        with pytest.raises(ValidationError):
            StatusResponse(
                status="healthy"
                # 缺少timestamp和services
            )


class TestMetricsResponse:
    """测试MetricsResponse模型"""

    def test_metrics_response_creation(self):
        """测试监控指标响应创建"""
        system_metrics = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 35.5
        }

        database_metrics = {
            "connection_pool": {
                "active": 10,
                "idle": 20,
                "max": 50
            },
            "query_performance": {
                "avg_response_time_ms": 25.5,
                "queries_per_second": 1000
            }
        }

        response = MetricsResponse(
            status="healthy",
            response_time_ms=10.5,
            system=system_metrics,
            database=database_metrics,
            runtime={
                "uptime": 3600,
                "version": "3.11.9"
            },
            business={
                "predictions_today": 1500,
                "active_users": 200
            }
        )

        assert response.status == "healthy"
        assert response.system["cpu_usage"] == 45.2
        assert response.database["connection_pool"]["active"] == 10
        assert response.runtime["uptime"] == 3600
        assert response.business["predictions_today"] == 1500

    def test_metrics_response_with_nested_data(self):
        """测试带有嵌套数据的监控指标响应"""
        response = MetricsResponse(
            status="healthy",
            response_time_ms=5.0,
            system={
                "load_average": [1.0, 1.2, 1.1],
                "disk": {
                    "root": {"used": "50GB", "free": "100GB"},
                    "data": {"used": "200GB", "free": "300GB"}
                }
            },
            database={},
            runtime={},
            business={}
        )

        assert len(response.system["load_average"]) == 3
        assert response.system["disk"]["root"]["used"] == "50GB"
        assert response.system["disk"]["data"]["free"] == "300GB"

    def test_metrics_response_minimal(self):
        """测试最小监控指标响应"""
        response = MetricsResponse(
            status="healthy",
            response_time_ms=1.0,
            system={},
            database={},
            runtime={},
            business={}
        )

        assert response.status == "healthy"
        assert response.system == {}
        assert response.database == {}
        assert response.runtime == {}
        assert response.business == {}


class TestRootResponse:
    """测试RootResponse模型"""

    def test_root_response_creation(self):
        """测试根路径响应创建"""
        response = RootResponse(
            service="Football Prediction API",
            version="1.2.3",
            status="healthy",
            docs_url="/docs",
            health_check="/health"
        )

        assert response.service == "Football Prediction API"
        assert response.version == "1.2.3"
        assert response.status == "healthy"
        assert response.docs_url == "/docs"
        assert response.health_check == "/health"

    def test_root_response_different_versions(self):
        """测试不同版本的根路径响应"""
        versions = ["1.0.0", "2.0.0-beta", "3.1.2"]

        for version in versions:
            response = RootResponse(
                service="Test API",
                version=version,
                status="healthy",
                docs_url="/docs",
                health_check="/health"
            )
            assert response.version == version

    def test_root_response_validation(self):
        """测试根路径响应验证"""
        with pytest.raises(ValidationError) as exc_info:
            RootResponse(
                service="Test API"
                # 缺少其他必要字段
            )

        required_fields = ["version", "status", "docs_url", "health_check"]
        for field in required_fields:
            assert field in str(exc_info.value)


class TestErrorResponse:
    """测试ErrorResponse模型"""

    def test_error_response_creation(self):
        """测试错误响应创建"""
        response = ErrorResponse(
            error=True,
            status_code=404,
            message="Resource not found",
            path="/api/v1/predictions/999"
        )

        assert response.error is True
        assert response.status_code == 404
        assert response.message == "Resource not found"
        assert response.path == "/api/v1/predictions/999"

    def test_error_response_different_codes(self):
        """测试不同错误码的响应"""
        error_cases = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable")
        ]

        for code, message in error_cases:
            response = ErrorResponse(
                error=True,
                status_code=code,
                message=message,
                path="/test"
            )
            assert response.status_code == code
            assert response.message == message

    def test_error_response_with_special_characters(self):
        """测试包含特殊字符的错误响应"""
        special_chars = "中文消息 & émoji 🚨 & special chars: <>&\"'"

        response = ErrorResponse(
            error=True,
            status_code=400,
            message=special_chars,
            path="/api/test"
        )

        assert response.message == special_chars

    def test_error_response_validation(self):
        """测试错误响应验证"""
        with pytest.raises(ValidationError):
            ErrorResponse(
                error=True
                # 缺少其他必要字段
            )


class TestModelSerialization:
    """测试模型序列化"""

    def test_service_check_serialization(self):
        """测试ServiceCheck序列化"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=10.5,
            details={"cpu": 50.0}
        )

        data = check.model_dump()

        assert data["status"] == "healthy"
        assert data["response_time_ms"] == 10.5
        assert data["details"]["cpu"] == 50.0

    def test_health_check_response_serialization(self):
        """测试HealthCheckResponse序列化"""
        checks = {
            "db": ServiceCheck(status="healthy", response_time_ms=5.0)
        }

        response = HealthCheckResponse(
            status="healthy",
            timestamp="2024-01-15T10:00:00Z",
            service="test",
            version="1.0",
            uptime=100.0,
            response_time_ms=10.0,
            checks=checks
        )

        data = response.model_dump()

        assert data["status"] == "healthy"
        assert "db" in data["checks"]
        assert data["checks"]["db"]["status"] == "healthy"

    def test_model_json_serialization(self):
        """测试模型JSON序列化"""
        response = RootResponse(
            service="Test API",
            version="1.0",
            status="healthy",
            docs_url="/docs",
            health_check="/health"
        )

        json_str = response.model_dump_json()

        assert "Test API" in json_str
        assert "1.0" in json_str
        assert "healthy" in json_str

        # 验证可以反序列化
        parsed = RootResponse.model_validate_json(json_str)
        assert parsed.service == "Test API"
        assert parsed.version == "1.0"


class TestModelEdgeCases:
    """测试模型边界情况"""

    def test_response_time_zero(self):
        """测试响应时间为0"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=0.0
        )
        assert check.response_time_ms == 0.0

    def test_negative_response_time(self):
        """测试负响应时间（应该被允许）"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=-1.0
        )
        assert check.response_time_ms == -1.0

    def test_very_large_values(self):
        """测试非常大的值"""
        large_value = 999999999.0
        check = ServiceCheck(
            status="healthy",
            response_time_ms=large_value
        )
        assert check.response_time_ms == large_value

    def test_empty_details(self):
        """测试空的详细信息"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=10.0,
            details={}
        )
        assert check.details == {}

    def test_none_details(self):
        """测试None详细信息"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=10.0,
            details=None
        )
        assert check.details is None

    def test_special_status_values(self):
        """测试特殊状态值"""
        special_statuses = ["", " ", "\n", "\t", "🚀"]

        for status in special_statuses:
            check = ServiceCheck(
                status=status,
                response_time_ms=10.0
            )
            assert check.status == status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])