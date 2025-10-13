"""
健康检查API测试
Tests for Health Check API

测试src.api.health模块的健康检查功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 测试导入
try:
    from src.api.health import router
    from src.api.health import _check_database

    HEALTH_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    HEALTH_AVAILABLE = False
    router = None
    _check_database = None


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthCheck:
    """健康检查测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router, prefix="/health")
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_router_exists(self):
        """测试：路由器存在"""
        assert router is not None
        assert hasattr(router, "routes")

    def test_check_database_function(self):
        """测试：数据库检查函数"""
        _result = _check_database()
        assert isinstance(result, dict)
        assert "status" in result
        assert "latency_ms" in result
        assert result["status"] == "healthy"
        assert isinstance(result["latency_ms"], int)

    def test_health_check_endpoint(self, client):
        """测试：基础健康检查端点"""
        response = client.get("/health/")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert data["status"] in ["healthy", "unhealthy"]
        assert "database" in data["checks"]

    def test_liveness_check_endpoint(self, client):
        """测试：存活检查端点"""
        response = client.get("/health/liveness")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data

        assert data["status"] == "alive"
        assert data["service"] == "football-prediction-api"

    def test_readiness_check_endpoint(self, client):
        """测试：就绪检查端点"""
        response = client.get("/health/readiness")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        assert data["status"] in ["ready", "not_ready"]
        assert "database" in data["checks"]

    def test_detailed_health_endpoint(self, client):
        """测试：详细健康检查端点"""
        response = client.get("/health/detailed")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        # 应该包含多个检查项
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "system" in data["checks"]

        # 检查Redis状态
        redis_status = data["checks"]["redis"]
        assert redis_status["status"] == "ok"
        assert "latency_ms" in redis_status

        # 检查系统状态
        system_status = data["checks"]["system"]
        assert system_status["status"] == "ok"
        assert "cpu_usage" in system_status
        assert "memory_usage" in system_status


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthCheckMocked:
    """使用模拟的健康检查测试"""

    def test_health_check_with_unhealthy_database(self):
        """测试：数据库不健康时的整体状态"""
        with patch("src.api.health._check_database") as mock_check:
            mock_check.return_value = {"status": "unhealthy", "latency_ms": 1000}

            # 创建测试应用
            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)

            response = client.get("/health/")
            assert response.status_code == 200

            _data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"

    def test_readiness_check_with_unhealthy_database(self):
        """测试：数据库不健康时的就绪状态"""
        with patch("src.api.health._check_database") as mock_check:
            mock_check.return_value = {
                "status": "unhealthy",
                "error": "Connection timeout",
            }

            app = FastAPI()
            app.include_router(router, prefix="/health")
            client = TestClient(app)

            response = client.get("/health/readiness")
            assert response.status_code == 200

            _data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"]["status"] == "unhealthy"

    def test_health_check_timestamp_changes(self):
        """测试：健康检查时间戳变化"""
        app = FastAPI()
        app.include_router(router, prefix="/health")
        client = TestClient(app)

        # 第一次请求
        response1 = client.get("/health/")
        time1 = response1.json()["timestamp"]

        # 等待一小段时间
        time.sleep(0.01)

        # 第二次请求
        response2 = client.get("/health/")
        time2 = response2.json()["timestamp"]

        # 时间戳应该不同
        assert time1 != time2
        assert time2 > time1


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="Health module not available")
class TestHealthCheckIntegration:
    """健康检查集成测试"""

    def test_all_endpoints_respond(self):
        """测试：所有端点都有响应"""
        app = FastAPI()
        app.include_router(router, prefix="/health")
        client = TestClient(app)

        endpoints = [
            "/health/",
            "/health/liveness",
            "/health/readiness",
            "/health/detailed",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert "status" in response.json()

    def test_response_headers(self):
        """测试：响应头"""
        app = FastAPI()
        app.include_router(router, prefix="/health")
        client = TestClient(app)

        response = client.get("/health/")
        assert response.headers["content-type"] == "application/json"

    def test_health_check_structure(self):
        """测试：健康检查响应结构"""
        app = FastAPI()
        app.include_router(router, prefix="/health")
        client = TestClient(app)

        response = client.get("/health/")
        _data = response.json()

        # 验证必需字段
        required_fields = ["status", "timestamp", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # 验证数据类型
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], float)
        assert isinstance(data["checks"], dict)

    def test_database_check_consistency(self):
        """测试：数据库检查一致性"""
        # 多次调用数据库检查函数
        result1 = _check_database()
        _result2 = _check_database()

        # 结果应该结构相同
        assert list(result1.keys()) == list(result2.keys())
        assert result1["status"] == result2["status"]


@pytest.mark.skipif(HEALTH_AVAILABLE, reason="Health module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not HEALTH_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if HEALTH_AVAILABLE:
        from src.api.health import router, _check_database

        assert router is not None
        assert _check_database is not None
        assert callable(_check_database)


def test_router_routes():
    """测试：路由器路由"""
    if HEALTH_AVAILABLE:
        routes = [route.path for route in router.routes]
        expected_routes = ["/", "/liveness", "/readiness", "/detailed"]

        for route in expected_routes:
            assert route in routes, f"Missing route: {route}"


@pytest.mark.asyncio
async def test_async_endpoints():
    """测试：异步端点"""
    if HEALTH_AVAILABLE:
        # 直接调用端点函数
        from src.api.health import (
            health_check,
            liveness_check,
            readiness_check,
            detailed_health,
        )

        # 测试health_check
        _result = await health_check()
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result

        # 测试liveness_check
        _result = await liveness_check()
        assert result["status"] == "alive"
        assert "service" in result

        # 测试readiness_check
        _result = await readiness_check()
        assert result["status"] in ["ready", "not_ready"]

        # 测试detailed_health
        _result = await detailed_health()
        assert "database" in result["checks"]
        assert "redis" in result["checks"]
        assert "system" in result["checks"]
