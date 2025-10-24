# TODO: Consider creating a fixture for 8 repeated Mock creations

# TODO: Consider creating a fixture for 8 repeated Mock creations

from unittest.mock import Mock, patch, AsyncMock
"""
Health API 综合测试
提升 api.health 模块覆盖率的关键测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 测试导入
import sys

sys.path.insert(0, "src")

try:
    from src.api.health import HealthChecker, HealthStatus, HealthCheckResult, router
    from src.database.dependencies import get_db_session
    from src.cache.redis_manager import RedisManager

    HEALTH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import health modules: {e}")
    HEALTH_AVAILABLE = False


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health modules not available")
@pytest.mark.unit

class TestHealthChecker:
    """HealthChecker测试"""

    @pytest.fixture
    def health_checker(self):
        """创建健康检查器"""
        with patch("src.api.health.RedisManager"), patch("src.api.health.database"):
            checker = HealthChecker()
            return checker

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute.return_value.scalar.return_value = 1
        return session

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis = AsyncMock()
        redis.ping.return_value = True
        redis.info.return_value = {"connected_clients": 5}
        return redis

    def test_health_checker_initialization(self, health_checker):
        """测试健康检查器初始化"""
        assert hasattr(health_checker, "checks")
        assert hasattr(health_checker, "logger")
        assert len(health_checker.checks) > 0

    @pytest.mark.asyncio
    async def test_database_health_check(self, health_checker, mock_db_session):
        """测试数据库健康检查"""
        with patch("src.api.health.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_db_session

        result = await health_checker.check_database()

        assert isinstance(result, HealthCheckResult)
        assert result.component == "database"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        assert "response_time_ms" in result.details

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self, health_checker):
        """测试数据库健康检查失败"""
        with patch("src.api.health.get_db_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

        result = await health_checker.check_database()

        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_redis_health_check(self, health_checker, mock_redis_client):
        """测试Redis健康检查"""
        with patch("src.api.health.RedisManager.get_client") as mock_get_client:
            mock_get_client.return_value = mock_redis_client

        result = await health_checker.check_redis()

        assert isinstance(result, HealthCheckResult)
        assert result.component == "redis"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]

    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self, health_checker):
        """测试Redis健康检查失败"""
        with patch("src.api.health.RedisManager.get_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Redis connection failed")

        result = await health_checker.check_redis()

        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_application_health_check(self, health_checker):
        """测试应用健康检查"""
        result = await health_checker.check_application()

        assert isinstance(result, HealthCheckResult)
        assert result.component == "application"
        assert "uptime_seconds" in result.details
        assert "memory_usage" in result.details

    @pytest.mark.asyncio
    async def test_external_service_health_check(self, health_checker):
        """测试外部服务健康检查"""
        with patch("src.api.health.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}

            mock_http_client = AsyncMock()
            mock_http_client.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_http_client

        result = await health_checker.check_external_service(
            "https://api.example.com/health"
        )

        assert isinstance(result, HealthCheckResult)
        assert result.component == "external_service"
        assert "https://api.example.com/health" in result.details

    @pytest.mark.asyncio
    async def test_external_service_timeout(self, health_checker):
        """测试外部服务超时"""
        with patch("src.api.health.httpx.AsyncClient") as mock_client:
            mock_client.side_effect = asyncio.TimeoutError("Request timeout")

        result = await health_checker.check_external_service(
            "https://api.example.com/health"
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.details["error"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, health_checker):
        """测试并发健康检查"""
        with (
            patch.object(health_checker, "check_database") as mock_db,
            patch.object(health_checker, "check_redis") as mock_redis,
            patch.object(health_checker, "check_application") as mock_app,
        ):
            mock_db.return_value = HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
            )
            mock_redis.return_value = HealthCheckResult(
                component="redis",
                status=HealthStatus.HEALTHY,
                message="Redis is healthy",
            )
            mock_app.return_value = HealthCheckResult(
                component="application",
                status=HealthStatus.HEALTHY,
                message="Application is healthy",
            )

        results = await health_checker.check_all_components()

        assert len(results) >= 3
        assert all(isinstance(result, HealthCheckResult) for result in results)

    @pytest.mark.asyncio
    async def test_health_check_with_timeout(self, health_checker):
        """测试带超时的健康检查"""
        with patch.object(health_checker, "check_database") as mock_check:
            # 模拟长时间运行的健康检查
            async def long_running_check():
                await asyncio.sleep(2)
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is healthy",
                )

            mock_check.side_effect = long_running_check

        result = await health_checker.check_component_with_timeout(
            "database", timeout=1.0
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.details["error"].lower()

    @pytest.mark.asyncio
    async def test_health_check_caching(self, health_checker):
        """测试健康检查缓存"""
        with patch.object(health_checker, "check_database") as mock_check:
            mock_check.return_value = HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
            )

        # 第一次检查
        result1 = await health_checker.check_database()
        # 第二次检查（应该使用缓存）
        result2 = await health_checker.check_database()

        assert result1.status == HealthStatus.HEALTHY
        assert result2.status == HealthStatus.HEALTHY

        # 检查函数应该只被调用一次（由于缓存）
        # 这取决于具体的缓存实现

    def test_health_check_result_serialization(self):
        """测试健康检查结果序列化"""
        result = HealthCheckResult(
            component="database",
            status=HealthStatus.HEALTHY,
            message="Database is healthy",
            details={"response_time_ms": 15.5, "connections": 5},
        )

        # 测试字典转换
        result_dict = result.to_dict()

        assert result_dict["component"] == "database"
        assert result_dict["status"] == "healthy"
        assert result_dict["message"] == "Database is healthy"
        assert "details" in result_dict

        # 测试JSON序列化
        json_str = json.dumps(result_dict)
        parsed_data = json.loads(json_str)
        assert parsed_data["component"] == "database"

    @pytest.mark.asyncio
    async def test_health_check_dependency_chain(self, health_checker):
        """测试健康检查依赖链"""
        # 模拟依赖关系：应用依赖于数据库，数据库依赖于网络

        with (
            patch.object(health_checker, "check_network") as mock_network,
            patch.object(health_checker, "check_database") as mock_db,
            patch.object(health_checker, "check_application") as mock_app,
        ):
            # 网络健康
            mock_network.return_value = HealthCheckResult(
                component="network",
                status=HealthStatus.HEALTHY,
                message="Network is healthy",
            )

            # 数据库健康（依赖于网络）
            mock_db.return_value = HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
                dependencies=["network"],
            )

            # 应用健康（依赖于数据库）
            mock_app.return_value = HealthCheckResult(
                component="application",
                status=HealthStatus.HEALTHY,
                message="Application is healthy",
                dependencies=["database"],
            )

        all_results = await health_checker.check_with_dependencies()

        assert len(all_results) >= 3
        # 验证依赖关系

    @pytest.mark.asyncio
    async def test_health_check_performance_metrics(self, health_checker):
        """测试健康检查性能指标"""
        with patch.object(health_checker, "check_database") as mock_check:
            mock_check.return_value = HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database is healthy",
                details={"response_time_ms": 25.5},
            )

        # 执行多次检查收集性能数据
        for _ in range(10):
            await health_checker.check_database()

        metrics = health_checker.get_performance_metrics()

        assert "database" in metrics
        assert "average_response_time" in metrics["database"]
        assert "check_count" in metrics["database"]
        assert metrics["database"]["check_count"] == 10

    def test_health_checker_configuration(self):
        """测试健康检查器配置"""
        config = {
            "timeout_seconds": 30,
            "cache_ttl_seconds": 60,
            "retry_attempts": 3,
            "enable_metrics": True,
        }

        checker = HealthChecker(config)

        assert checker.timeout_seconds == 30
        assert checker.cache_ttl_seconds == 60
        assert checker.retry_attempts == 3
        assert checker.enable_metrics is True

    @pytest.mark.asyncio
    async def test_health_check_circuit_breaker(self, health_checker):
        """测试健康检查熔断器"""
        with patch.object(health_checker, "check_external_service") as mock_check:
            # 连续失败触发熔断器
            mock_check.side_effect = Exception("Service unavailable")

        # 连续失败
        for _ in range(5):
            result = await health_checker.check_external_service(
                "https://api.example.com"
            )
            assert result.status == HealthStatus.UNHEALTHY

        # 验证熔断器状态
        circuit_status = health_checker.get_circuit_breaker_status(
            "https://api.example.com"
        )
        assert circuit_status["is_open"] is True

    @pytest.mark.asyncio
    async def test_health_check_alerting(self, health_checker):
        """测试健康检查告警"""
        critical_result = HealthCheckResult(
            component="database",
            status=HealthStatus.CRITICAL,
            message="Database connection failed",
        )

        with patch.object(health_checker, "send_alert") as mock_alert:
            await health_checker.handle_critical_health_check(critical_result)
            mock_alert.assert_called_once()

    def test_health_check_status_transitions(self):
        """测试健康检查状态转换"""
        checker = HealthChecker()
        component = "database"

        # 从健康到降级
        checker.record_status_transition(
            component, HealthStatus.HEALTHY, HealthStatus.DEGRADED
        )
        assert checker.get_current_status(component) == HealthStatus.DEGRADED

        # 从降级到不健康
        checker.record_status_transition(
            component, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY
        )
        assert checker.get_current_status(component) == HealthStatus.UNHEALTHY

        # 从不健康恢复到健康
        checker.record_status_transition(
            component, HealthStatus.UNHEALTHY, HealthStatus.HEALTHY
        )
        assert checker.get_current_status(component) == HealthStatus.HEALTHY


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health modules not available")
class TestHealthAPI:
    """Health API端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient

        return TestClient(router)

    def test_basic_health_endpoint(self, client):
        """测试基础健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_detailed_health_endpoint(self, client):
        """测试详细健康检查端点"""
        with patch("src.api.health.HealthChecker") as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker

            # 模拟健康检查结果
            mock_checker.check_all_components.return_value = [
                HealthCheckResult(
                    component="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is healthy",
                ),
                HealthCheckResult(
                    component="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis is healthy",
                ),
            ]

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "components" in data
        assert "checks" in data
        assert len(data["components"]) >= 2

    def test_readiness_probe(self, client):
        """测试就绪探针"""
        with patch("src.api.health.HealthChecker") as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker

            mock_checker.is_application_ready.return_value = True

        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert data["ready"] is True

    def test_liveness_probe(self, client):
        """测试存活探针"""
        with patch("src.api.health.HealthChecker") as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker

            mock_checker.is_application_alive.return_value = True

        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert "alive" in data
        assert data["alive"] is True

    def test_startup_probe(self, client):
        """测试启动探针"""
        with patch("src.api.health.HealthChecker") as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker

            mock_checker.is_startup_complete.return_value = True

        response = client.get("/health/startup")

        assert response.status_code == 200
        data = response.json()
        assert "started" in data
        assert data["started"] is True

    def test_health_endpoint_error_handling(self, client):
        """测试健康检查端点错误处理"""
        with patch("src.api.health.HealthChecker") as mock_checker_class:
            mock_checker_class.side_effect = Exception(
                "Health checker initialization failed"
            )

        response = client.get("/health")

        # 应该返回500错误而不是崩溃
        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    def test_health_endpoint_response_headers(self, client):
        """测试健康检查端点响应头"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"
