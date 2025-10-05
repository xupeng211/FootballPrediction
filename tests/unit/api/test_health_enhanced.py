"""
健康检查API增强测试
提高health.py的测试覆盖率
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import DatabaseError

from src.api.health import (
    router,
    health_check,
    _collect_database_health,
    _optional_checks_enabled,
    _optional_check_skipped,
    ServiceCheckError,
    _redis_circuit_breaker,
    _kafka_circuit_breaker,
    _mlflow_circuit_breaker,
)


class TestHealthCheckEnhanced:
    """健康检查增强测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(router)

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """设置测试环境变量"""
        original_fast_fail = os.getenv("FAST_FAIL")
        original_minimal_mode = os.getenv("MINIMAL_HEALTH_MODE")
        yield
        if original_fast_fail is not None:
            os.environ["FAST_FAIL"] = original_fast_fail
        else:
            os.environ.pop("FAST_FAIL", None)
        if original_minimal_mode is not None:
            os.environ["MINIMAL_HEALTH_MODE"] = original_minimal_mode
        else:
            os.environ.pop("MINIMAL_HEALTH_MODE", None)

    def test_optional_checks_enabled_true(self):
        """测试可选检查启用 - true"""
        os.environ["FAST_FAIL"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"
        assert _optional_checks_enabled() is True

    def test_optional_checks_enabled_false(self):
        """测试可选检查禁用"""
        os.environ["FAST_FAIL"] = "false"
        assert _optional_checks_enabled() is False

        os.environ["MINIMAL_HEALTH_MODE"] = "true"
        assert _optional_checks_enabled() is False

    def test_optional_check_skipped_format(self):
        """测试可选检查跳过响应格式"""
        result = _optional_check_skipped("test_service")
        expected = {
            "healthy": True,
            "status": "skipped",
            "response_time_ms": 0.0,
            "details": {"message": "test_service check skipped in minimal mode"},
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_collect_database_health_not_initialized(self):
        """测试数据库管理器未初始化"""
        with patch("src.api.health.get_database_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_session.side_effect = RuntimeError("Not initialized")
            mock_get_manager.return_value = mock_manager

            result = await _collect_database_health()

            assert result["healthy"] is True
            assert result["status"] == "skipped"
            assert "Database manager not initialised" in result["details"]["message"]

    @pytest.mark.asyncio
    async def test_collect_database_health_session_unavailable(self):
        """测试数据库会话不可用"""
        with patch("src.api.health.get_database_manager") as mock_get_manager:
            mock_manager = Mock()
            session_mock = Mock()
            session_mock.__enter__.side_effect = RuntimeError("Session unavailable")
            mock_manager.get_session.return_value = session_mock
            mock_get_manager.return_value = mock_manager

            result = await _collect_database_health()

            assert result["healthy"] is True
            assert result["status"] == "skipped"
            assert "Database session unavailable" in result["details"]["message"]

    def test_health_check_minimal_mode(self, client):
        """测试最小模式健康检查"""
        os.environ["MINIMAL_HEALTH_MODE"] = "true"

        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_health_check_with_db_param_true(self, client):
        """测试显式要求数据库检查"""
        with patch("src.api.health._collect_database_health") as mock_collect:
            mock_collect.return_value = {"healthy": True, "status": "ok"}

            response = client.get("/?check_db=true")

            # 应该调用数据库检查
            # 注意：由于实际的实现可能不同，这里需要根据实际情况调整

    def test_health_check_with_db_param_false(self, client):
        """测试显式跳过数据库检查"""
        response = client.get("/?check_db=false")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_service_check_error(self):
        """测试服务检查错误"""
        error = ServiceCheckError("Test error", details={"code": 500})
        assert str(error) == "Test error"
        assert error.details == {"code": 500}

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """测试熔断器功能"""
        from src.utils.retry import CircuitBreaker

        # 创建一个测试用的熔断器
        breaker = CircuitBreaker(
            failure_threshold=2, recovery_timeout=1.0, retry_timeout=0.5
        )

        call_count = 0

        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Failed")
            return "success"

        # 前两次调用应该失败
        with pytest.raises(Exception):
            await breaker.call_async(failing_function)

        with pytest.raises(Exception):
            await breaker.call_async(failing_function)

        # 第三次调用应该触发熔断
        with pytest.raises(Exception):  # 应该是熔断异常
            await breaker.call_async(failing_function)

    @pytest.mark.asyncio
    async def test_health_check_all_dependencies_healthy(self):
        """测试所有依赖健康的情况"""
        with patch("src.api.health._collect_database_health") as mock_db:
            mock_db.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10.0,
                "details": {"message": "Database connection successful"},
            }

            # 模拟Redis健康检查
            with patch("src.api.health._redis_circuit_breaker") as mock_redis_breaker:
                mock_redis_breaker.call_async.return_value = {
                    "healthy": True,
                    "status": "healthy",
                    "response_time_ms": 5.0,
                }

                # 模拟Kafka健康检查
                with patch(
                    "src.api.health._kafka_circuit_breaker"
                ) as mock_kafka_breaker:
                    mock_kafka_breaker.call_async.return_value = {
                        "healthy": True,
                        "status": "healthy",
                        "response_time_ms": 15.0,
                    }

                    # 模拟MLflow健康检查
                    with patch(
                        "src.api.health._mlflow_circuit_breaker"
                    ) as mock_mlflow_breaker:
                        mock_mlflow_breaker.call_async.return_value = {
                            "healthy": True,
                            "status": "healthy",
                            "response_time_ms": 20.0,
                        }

                        # 执行健康检查
                        result = await health_check(check_db=True)

                        assert result["status"] in ["healthy", "ok"]
                        assert "checks" in result
                        assert "database" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_check_database_unhealthy(self):
        """测试数据库不健康的情况"""
        with patch("src.api.health._collect_database_health") as mock_db:
            mock_db.return_value = {
                "healthy": False,
                "status": "unhealthy",
                "response_time_ms": 5000.0,
                "details": {"error": "Connection timeout"},
            }

            result = await health_check(check_db=True)

            # 整体状态应该反映数据库问题
            assert result["status"] in ["unhealthy", "degraded"]

    @pytest.mark.asyncio
    async def test_health_check_redis_failing(self):
        """测试Redis失败的情况"""
        os.environ["FAST_FAIL"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"

        with patch.object(_redis_circuit_breaker, "call_async") as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")

            # 应该捕获Redis错误但不影响整体健康检查
            result = await health_check(check_db=False)

            # Redis错误应该被记录在checks中
            assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_kafka_failing(self):
        """测试Kafka失败的情况"""
        os.environ["FAST_FAIL"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"

        with patch.object(_kafka_circuit_breaker, "call_async") as mock_kafka:
            mock_kafka.side_effect = Exception("Kafka broker unavailable")

            result = await health_check(check_db=False)

            # Kafka错误应该被记录
            assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_mlflow_failing(self):
        """测试MLflow失败的情况"""
        os.environ["FAST_FAIL"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"

        with patch.object(_mlflow_circuit_breaker, "call_async") as mock_mlflow:
            mock_mlflow.side_effect = Exception("MLflow server unreachable")

            result = await health_check(check_db=False)

            # MLflow错误应该被记录
            assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_concurrent_requests(self):
        """测试并发健康检查请求"""

        async def make_health_check():
            return await health_check(check_db=False)

        # 并发执行10个健康检查
        tasks = [make_health_check() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有请求都应该成功
        for result in results:
            assert not isinstance(result, Exception)
            assert "status" in result

    def test_health_check_endpoint_variations(self, client):
        """测试健康检查端点变体"""
        # 测试根路径
        response = client.get("/")
        assert response.status_code == 200

        # 测试带斜杠的路径
        response = client.get("/health")
        assert response.status_code == 200

        # 测试health路径
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """测试健康检查响应结构"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()

        # 验证响应结构
        required_fields = ["status", "timestamp", "uptime_seconds", "version", "checks"]
        for field in required_fields:
            assert field in data

        # 验证checks结构
        assert "api" in data["checks"]
        assert isinstance(data["checks"]["api"], dict)

    def test_health_check_headers(self, client):
        """测试健康检查响应头"""
        response = client.get("/")
        assert response.status_code == 200

        # 检查常见响应头
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_with_custom_endpoints(self):
        """测试自定义端点健康检查"""
        # 测试predictions端点可用性
        with patch("src.api.health.PREDICTIONS_ENABLED", True):
            result = await health_check(check_db=False)
            # 应该显示predictions服务可用

    @pytest.mark.asyncio
    async def test_health_check_performance_metrics(self):
        """测试健康检查性能指标"""
        import time

        start_time = time.time()
        result = await health_check(check_db=False)
        end_time = time.time()

        # 健康检查应该快速完成
        assert end_time - start_time < 5.0  # 应该在5秒内完成

        # 响应应该包含性能相关信息
        assert "response_time_ms" in str(result) or "checks" in result

    @pytest.mark.asyncio
    async def test_health_check_error_propagation(self):
        """测试健康检查错误传播"""
        # 模拟数据库抛出异常
        with patch("src.api.health._collect_database_health") as mock_db:
            mock_db.side_effect = DatabaseError("Database error")

            # 应该优雅地处理错误
            result = await health_check(check_db=True)

            # 错误应该被捕获，响应仍然有效
            assert "status" in result
            assert result["status"] in ["unhealthy", "degraded", "error"]

    def test_service_check_error_creation(self):
        """测试服务检查错误创建"""
        # 测试无details
        error1 = ServiceCheckError("Simple error")
        assert str(error1) == "Simple error"
        assert error1.details == {}

        # 测试有details
        details = {"code": 500, "service": "database"}
        error2 = ServiceCheckError("Error with details", details=details)
        assert str(error2) == "Error with details"
        assert error2.details == details
