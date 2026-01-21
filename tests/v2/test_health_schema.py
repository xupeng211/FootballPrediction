#!/usr/bin/env python3
"""
Health API Schema 测试

专门测试修复后的 health.py 响应格式，确保完全符合Pydantic Schema定义。
验证健康检查API的响应结构和数据格式。
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.health import health_check, liveness_check, readiness_check, router
from src.api.schemas import HealthCheckResponse, ServiceCheck


class TestHealthAPISchema:
    """测试健康API响应Schema"""

    @pytest.fixture
    def app(self):
        """创建FastAPI应用实例"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_check_response_structure(self, client):
        """测试健康检查响应结构"""
        response = client.get("/health")

        assert response.status_code == 200

        # 验证Content-Type
        assert response.headers["content-type"] == "application/json"

        # 解析响应
        data = response.json()

        # 验证必需字段存在
        required_fields = [
            "status",
            "timestamp",
            "service",
            "version",
            "response_time_ms",
            "checks",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # 验证字段类型
        assert isinstance(data["status"], str)
        assert data["status"] in ["healthy", "unhealthy"]

        assert isinstance(data["timestamp"], str)
        # 验证ISO格式时间戳
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid timestamp format")

        assert isinstance(data["service"], str)
        assert data["service"] == "football-prediction-api"

        assert isinstance(data["version"], str)
        assert data["version"] == "1.0.0"

        assert isinstance(data["response_time_ms"], (int, float))
        assert data["response_time_ms"] >= 0

        assert isinstance(data["checks"], dict)

        # 验证checks中的服务
        required_services = ["database", "redis", "filesystem"]
        for service in required_services:
            assert service in data["checks"], f"Missing service check: {service}"

            # 验证每个服务检查的结构
            service_check = data["checks"][service]
            assert isinstance(service_check, dict)
            assert "status" in service_check
            assert "response_time_ms" in service_check
            assert "details" in service_check

            assert service_check["status"] in ["healthy", "unhealthy"]
            assert isinstance(service_check["response_time_ms"], (int, float))
            assert service_check["response_time_ms"] >= 0
            assert isinstance(service_check["details"], dict)

    def test_service_check_structure(self):
        """测试ServiceCheck数据结构"""
        # 创建健康的服务检查
        healthy_check = ServiceCheck(
            status="healthy",
            response_time_ms=10.5,
            details={"message": "Service is running normally"},
        )

        assert healthy_check.status == "healthy"
        assert healthy_check.response_time_ms == 10.5
        assert healthy_check.details["message"] == "Service is running normally"

        # 创建不健康的服务检查
        unhealthy_check = ServiceCheck(
            status="unhealthy",
            response_time_ms=0,
            details={"message": "Service is down", "error": "Connection timeout"},
        )

        assert unhealthy_check.status == "unhealthy"
        assert unhealthy_check.response_time_ms == 0
        assert "error" in unhealthy_check.details

    @pytest.mark.asyncio
    async def test_health_check_function_directly(self):
        """直接测试health_check函数"""
        result = await health_check()

        # 验证返回类型
        assert isinstance(result, HealthCheckResponse)

        # 验证HealthCheckResponse的字段
        assert result.status in ["healthy", "unhealthy"]
        assert isinstance(result.timestamp, str)
        assert result.service == "football-prediction-api"
        assert result.version == "1.0.0"
        assert isinstance(result.response_time_ms, (int, float))
        assert isinstance(result.checks, dict)

        # 验证服务检查
        for service_name, service_check in result.checks.items():
            assert isinstance(service_check, ServiceCheck)
            assert service_check.status in ["healthy", "unhealthy"]
            assert isinstance(service_check.response_time_ms, (int, float))
            assert isinstance(service_check.details, dict)

    def test_liveness_check_response(self, client):
        """测试存活性检查响应"""
        response = client.get("/health/liveness")

        assert response.status_code == 200

        data = response.json()

        # 验证响应结构
        required_fields = ["status", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["status"] == "alive"
        assert isinstance(data["timestamp"], str)

        # 验证时间戳格式
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid timestamp format")

    @pytest.mark.skip(reason="Legacy configuration issue - to be fixed in v2.1")
    def test_readiness_check_response_success(self, client):
        """测试就绪性检查成功响应"""
        # Mock数据库检查成功
        with patch("src.api.health._check_database") as mock_db_check:
            mock_db_check.return_value = {
                "healthy": True,
                "message": "数据库连接正常",
                "response_time_ms": 15.0,
            }

            response = client.get("/health/readiness")

            assert response.status_code == 200

            data = response.json()

            # 验证响应结构
            required_fields = ["ready", "timestamp", "checks"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            assert data["ready"] is True
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["checks"], dict)

            # 验证数据库检查结果
            assert "database" in data["checks"]
            db_check = data["checks"]["database"]
            assert db_check["status"] == "healthy"
            assert "response_time_ms" in db_check
            assert "details" in db_check

    @pytest.mark.skip(reason="Legacy configuration issue - to be fixed in v2.1")
    def test_readiness_check_response_failure(self, client):
        """测试就绪性检查失败响应"""
        # Mock数据库检查失败
        with patch("src.api.health._check_database") as mock_db_check:
            mock_db_check.return_value = {
                "healthy": False,
                "message": "数据库连接失败",
                "error": "Connection timeout",
                "response_time_ms": 5000.0,
            }

            response = client.get("/health/readiness")

            assert response.status_code == 503  # Service Unavailable

            data = response.json()

            assert data["ready"] is False
            assert "database" in data["checks"]
            db_check = data["checks"]["database"]
            assert db_check["status"] == "unhealthy"
            assert "error" in db_check["details"]

    @pytest.mark.asyncio
    async def test_get_database_service_check(self):
        """测试数据库服务检查函数"""
        result = await router._get_database_service_check() if hasattr(router, "_get_database_service_check") else None

        if result is None:
            # 如果函数不在router上，从模块导入测试
            from src.api.health import _get_database_service_check

            result = await _get_database_service_check()

        # 验证返回类型
        assert isinstance(result, ServiceCheck)
        assert result.status in ["healthy", "unhealthy"]
        assert isinstance(result.response_time_ms, (int, float))
        assert isinstance(result.details, dict)

    @pytest.mark.asyncio
    async def test_get_redis_service_check(self):
        """测试Redis服务检查函数"""
        from src.api.health import _get_redis_service_check

        result = await _get_redis_service_check()

        # 验证返回类型
        assert isinstance(result, ServiceCheck)
        assert result.status in ["healthy", "unhealthy"]
        assert isinstance(result.response_time_ms, (int, float))
        assert isinstance(result.details, dict)

    @pytest.mark.asyncio
    async def test_get_filesystem_service_check(self):
        """测试文件系统服务检查函数"""
        from src.api.health import _get_filesystem_service_check

        result = await _get_filesystem_service_check()

        # 验证返回类型
        assert isinstance(result, ServiceCheck)
        assert result.status in ["healthy", "unhealthy"]
        assert isinstance(result.response_time_ms, (int, float))
        assert isinstance(result.details, dict)

    @pytest.mark.skip(reason="Legacy configuration issue - to be fixed in v2.1")
    def test_health_check_response_serialization(self):
        """测试健康检查响应的JSON序列化"""
        # 创建HealthCheckResponse实例
        response_data = {
            "status": "healthy",
            "timestamp": "2024-01-01T12:00:00",
            "service": "football-prediction-api",
            "version": "1.0.0",
            "response_time_ms": 100.5,
            "checks": {
                "database": ServiceCheck(
                    status="healthy",
                    response_time_ms=50.0,
                    details={"message": "数据库连接正常"},
                ),
                "redis": ServiceCheck(
                    status="healthy",
                    response_time_ms=25.0,
                    details={"message": "Redis连接正常"},
                ),
                "filesystem": ServiceCheck(
                    status="healthy",
                    response_time_ms=25.5,
                    details={"message": "文件系统正常"},
                ),
            },
        }

        # 尝试JSON序列化
        json_str = json.dumps(response_data, default=str)

        # 验证可以反序列化
        parsed_data = json.loads(json_str)

        assert parsed_data["status"] == "healthy"
        assert parsed_data["service"] == "football-prediction-api"
        assert "database" in parsed_data["checks"]
        assert parsed_data["checks"]["database"]["status"] == "healthy"


# 边界测试和错误处理
class TestHealthAPIEdgeCases:
    """健康API边界情况测试"""

    def test_empty_checks_handling(self):
        """测试空检查列表处理"""
        # 测试所有服务都不健康的情况
        checks = {
            "database": ServiceCheck(
                status="unhealthy",
                response_time_ms=0,
                details={"message": "数据库不可用"},
            ),
            "redis": ServiceCheck(
                status="unhealthy",
                response_time_ms=0,
                details={"message": "Redis不可用"},
            ),
        }

        # 模拟不健康的响应
        unhealthy_response = HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            service="football-prediction-api",
            version="1.0.0",
            response_time_ms=0,
            checks=checks,
        )

        assert unhealthy_response.status == "unhealthy"

    def test_large_response_time_values(self):
        """测试大响应时间值处理"""
        large_response_time = ServiceCheck(
            status="healthy",
            response_time_ms=999999.999,
            details={"message": "High latency but functional"},
        )

        assert large_response_time.response_time_ms == 999999.999

    def test_unicode_content_in_details(self):
        """测试details中的Unicode内容"""
        unicode_check = ServiceCheck(
            status="healthy",
            response_time_ms=10.0,
            details={
                "message": "服务正常 🚀",
                "description": "系统运行良好 ✓",
                "emoji": "⚽",
            },
        )

        # 验证Unicode字符可以正确处理
        assert "🚀" in unicode_check.details["message"]
        assert "✓" in unicode_check.details["description"]
        assert "⚽" == unicode_check.details["emoji"]


# 配置测试标记
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.unit,
    pytest.mark.api,
]


if __name__ == "__main__":
    # 运行测试的示例
    pytest.main([__file__, "-v"])
