"""
Auto-generated tests for src.api.schemas module
"""

import pytest
from datetime import datetime
from src.api.schemas import (
    ServiceCheck,
    HealthCheckResponse,
    StatusResponse,
    MetricsResponse
)


class TestServiceCheck:
    """测试服务检查结果模型"""

    def test_service_check_creation(self):
        """测试服务检查创建"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=150.5
        )
        assert check.status == "healthy"
        assert check.response_time_ms == 150.5
        assert check.details is None

    def test_service_check_with_details(self):
        """测试带详细信息的服务检查"""
        details = {"cpu_usage": 45.2, "memory_usage": 67.8}
        check = ServiceCheck(
            status="warning",
            response_time_ms=200.0,
            details=details
        )
        assert check.status == "warning"
        assert check.response_time_ms == 200.0
        assert check.details == details

    def test_service_check_field_validation(self):
        """测试服务检查字段验证"""
        # 测试必填字段
        with pytest.raises(ValueError):
            ServiceCheck()

        # 测试有效值
        check = ServiceCheck(status="healthy", response_time_ms=100.0)
        assert check.status == "healthy"
        assert check.response_time_ms == 100.0

    @pytest.mark.parametrize("status", ["healthy", "warning", "critical", "degraded"])
    def test_service_check_different_statuses(self, status):
        """测试不同服务状态"""
        check = ServiceCheck(status=status, response_time_ms=50.0)
        assert check.status == status

    @pytest.mark.parametrize("response_time", [0.1, 50.5, 1000.0, 5000.5])
    def test_service_check_response_times(self, response_time):
        """测试不同响应时间"""
        check = ServiceCheck(status="healthy", response_time_ms=response_time)
        assert check.response_time_ms == response_time

    def test_service_check_empty_details(self):
        """测试空详细信息"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=100.0,
            details={}
        )
        assert check.details == {}

    def test_service_check_complex_details(self):
        """测试复杂详细信息"""
        details = {
            "performance": {
                "cpu": 45.2,
                "memory": 67.8,
                "disk": 82.1
            },
            "connections": {
                "active": 15,
                "idle": 3,
                "total": 18
            }
        }
        check = ServiceCheck(
            status="healthy",
            response_time_ms=150.0,
            details=details
        )
        assert check.details == details


class TestHealthCheckResponse:
    """测试健康检查响应模型"""

    def test_health_check_response_creation(self):
        """测试健康检查响应创建"""
        checks = {
            "database": ServiceCheck(status="healthy", response_time_ms=50.0),
            "redis": ServiceCheck(status="healthy", response_time_ms=10.0)
        }
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            service="football-prediction",
            version="1.0.0",
            uptime=3600.0,
            response_time_ms=100.0,
            checks=checks
        )
        assert response.status == "healthy"
        assert response.timestamp == "2023-01-01T00:00:00"
        assert response.service == "football-prediction"
        assert response.version == "1.0.0"
        assert response.uptime == 3600.0
        assert response.response_time_ms == 100.0
        assert response.checks == checks

    def test_health_check_response_minimal(self):
        """测试最小健康检查响应"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            service="test",
            version="1.0.0",
            uptime=0.0,
            response_time_ms=1.0,
            checks=checks
        )
        assert response.status == "healthy"
        assert len(response.checks) == 1

    @pytest.mark.parametrize("status", ["healthy", "unhealthy", "degraded"])
    def test_health_check_different_statuses(self, status):
        """测试不同健康状态"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        response = HealthCheckResponse(
            status=status,
            timestamp="2023-01-01T00:00:00",
            service="test",
            version="1.0.0",
            uptime=0.0,
            response_time_ms=1.0,
            checks=checks
        )
        assert response.status == status

    def test_health_check_multiple_checks(self):
        """测试多个服务检查"""
        checks = {
            "database": ServiceCheck(status="healthy", response_time_ms=50.0),
            "redis": ServiceCheck(status="warning", response_time_ms=15.0),
            "cache": ServiceCheck(status="healthy", response_time_ms=5.0),
            "storage": ServiceCheck(status="critical", response_time_ms=200.0)
        }
        response = HealthCheckResponse(
            status="degraded",
            timestamp="2023-01-01T00:00:00",
            service="test",
            version="1.0.0",
            uptime=7200.0,
            response_time_ms=250.0,
            checks=checks
        )
        assert len(response.checks) == 4
        assert response.checks["redis"].status == "warning"
        assert response.checks["storage"].status == "critical"


class TestStatusResponse:
    """测试状态响应模型"""

    def test_status_response_creation(self):
        """测试状态响应创建"""
        services = {
            "database": "healthy",
            "redis": "healthy",
            "cache": "warning"
        }
        response = StatusResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            services=services
        )
        assert response.status == "healthy"
        assert response.timestamp == "2023-01-01T00:00:00"
        assert response.services == services

    def test_status_response_empty_services(self):
        """测试空服务状态"""
        response = StatusResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            services={}
        )
        assert response.services == {}

    def test_status_response_mixed_status(self):
        """测试混合服务状态"""
        services = {
            "database": "healthy",
            "redis": "degraded",
            "cache": "critical",
            "storage": "healthy"
        }
        response = StatusResponse(
            status="degraded",
            timestamp="2023-01-01T00:00:00",
            services=services
        )
        assert len(response.services) == 4
        assert response.services["redis"] == "degraded"
        assert response.services["cache"] == "critical"


class TestMetricsResponse:
    """测试监控指标响应模型"""

    def test_metrics_response_creation(self):
        """测试监控指标响应创建"""
        system = {"cpu_usage": 45.2, "memory_usage": 67.8}
        database = {"connection_count": 15, "query_time_avg": 25.5}
        runtime = {"active_requests": 3, "response_time_avg": 150.0}
        business = {"predictions_today": 1250, "accuracy_rate": 0.87}

        response = MetricsResponse(
            status="healthy",
            response_time_ms=100.0,
            system=system,
            database=database,
            runtime=runtime,
            business=business
        )
        assert response.status == "healthy"
        assert response.response_time_ms == 100.0
        assert response.system == system
        assert response.database == database
        assert response.runtime == runtime
        assert response.business == business

    def test_metrics_response_partial_data(self):
        """测试部分监控数据"""
        response = MetricsResponse(
            status="healthy",
            response_time_ms=50.0,
            system={},
            database={"connection_count": 10},
            runtime={},
            business={"predictions_today": 100}
        )
        assert response.system == {}
        assert response.database["connection_count"] == 10
        assert response.runtime == {}
        assert response.business["predictions_today"] == 100

    def test_metrics_response_complex_nested_data(self):
        """测试复杂嵌套监控数据"""
        system = {
            "cpu": {
                "usage": 45.2,
                "cores": 4,
                "temperature": 65.0
            },
            "memory": {
                "total": 8589934592,
                "used": 3221225472,
                "available": 5368709120
            }
        }
        response = MetricsResponse(
            status="healthy",
            response_time_ms=75.0,
            system=system,
            database={},
            runtime={},
            business={}
        )
        assert response.system["cpu"]["usage"] == 45.2
        assert response.system["memory"]["total"] == 8589934592


class TestSchemaSerialization:
    """测试模式序列化"""

    def test_service_check_serialization(self):
        """测试服务检查序列化"""
        check = ServiceCheck(
            status="healthy",
            response_time_ms=100.0,
            details={"test": "value"}
        )
        serialized = check.model_dump()
        assert serialized["status"] == "healthy"
        assert serialized["response_time_ms"] == 100.0
        assert serialized["details"] == {"test": "value"}

    def test_health_check_response_serialization(self):
        """测试健康检查响应序列化"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            service="test",
            version="1.0.0",
            uptime=0.0,
            response_time_ms=1.0,
            checks=checks
        )
        serialized = response.model_dump()
        assert serialized["status"] == "healthy"
        assert serialized["checks"]["test"]["status"] == "healthy"

    def test_status_response_serialization(self):
        """测试状态响应序列化"""
        response = StatusResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            services={"test": "healthy"}
        )
        serialized = response.model_dump()
        assert serialized["status"] == "healthy"
        assert serialized["services"]["test"] == "healthy"

    def test_metrics_response_serialization(self):
        """测试监控指标响应序列化"""
        response = MetricsResponse(
            status="healthy",
            response_time_ms=100.0,
            system={"cpu": 50.0},
            database={},
            runtime={},
            business={}
        )
        serialized = response.model_dump()
        assert serialized["status"] == "healthy"
        assert serialized["system"]["cpu"] == 50.0

    def test_schema_json_serialization(self):
        """测试模式JSON序列化"""
        check = ServiceCheck(status="healthy", response_time_ms=100.0)
        json_str = check.model_dump_json()
        assert isinstance(json_str, str)
        assert "healthy" in json_str
        assert "100.0" in json_str


class TestSchemaFieldValidation:
    """测试模式字段验证"""

    def test_service_check_field_types(self):
        """测试服务检查字段类型"""
        check = ServiceCheck(status="healthy", response_time_ms=100.0)
        assert isinstance(check.status, str)
        assert isinstance(check.response_time_ms, float)
        assert check.details is None or isinstance(check.details, dict)

    def test_health_check_response_field_types(self):
        """测试健康检查响应字段类型"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",
            service="test",
            version="1.0.0",
            uptime=0.0,
            response_time_ms=1.0,
            checks=checks
        )
        assert isinstance(response.status, str)
        assert isinstance(response.timestamp, str)
        assert isinstance(response.service, str)
        assert isinstance(response.version, str)
        assert isinstance(response.uptime, float)
        assert isinstance(response.response_time_ms, float)
        assert isinstance(response.checks, dict)

    def test_negative_response_time_handling(self):
        """测试负响应时间处理"""
        with pytest.raises(ValueError):
            ServiceCheck(status="healthy", response_time_ms=-1.0)

    def test_negative_uptime_handling(self):
        """测试负运行时间处理"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        with pytest.raises(ValueError):
            HealthCheckResponse(
                status="healthy",
                timestamp="2023-01-01T00:00:00",
                service="test",
                version="1.0.0",
                uptime=-1.0,
                response_time_ms=1.0,
                checks=checks
            )

    def test_timestamp_format_validation(self):
        """测试时间戳格式验证"""
        checks = {"test": ServiceCheck(status="healthy", response_time_ms=1.0)}
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2023-01-01T00:00:00",  # ISO格式
            service="test",
            version="1.0.0",
            uptime=0.0,
            response_time_ms=1.0,
            checks=checks
        )
        # 验证可以解析为datetime
        datetime.fromisoformat(response.timestamp)