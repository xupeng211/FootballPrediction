from unittest.mock import Mock, patch

"""
健康检查API路由器测试
Tests for health check API router

测试健康检查API的各个端点功能。
"""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.health import router as health_router


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.external_api
@pytest.mark.slow
class TestHealthRouter:
    """健康检查API路由器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(health_router, prefix="/api/v1/health")
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    # ========================================
    # 基础健康检查端点测试
    # ========================================

    def test_basic_health_check(self, client):
        """测试基础健康检查端点"""
        with patch("time.time", return_value=1704067200.0):  # 2024-01-01 00:00:00
            response = client.get("/api/v1/health/")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["timestamp"] == 1704067200.0
            assert "checks" in data
            assert "database" in data["checks"]
            assert data["checks"]["database"]["status"] == "healthy"
            assert data["checks"]["database"]["latency_ms"] == 10

    def test_basic_health_check_with_database_unhealthy(self, client):
        """测试数据库不健康时的健康检查"""
        with patch("src.api.health._check_database") as mock_check:
            mock_check.return_value = {"status": "unhealthy", "latency_ms": 5000}

            response = client.get("/api/v1/health/")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["checks"]["database"]["status"] == "unhealthy"
            assert data["checks"]["database"]["latency_ms"] == 5000

    # ========================================
    # 存活检查端点测试
    # ========================================

    def test_liveness_check(self, client):
        """测试存活检查端点"""
        with patch("time.time", return_value=1704067200.0):
            response = client.get("/api/v1/health/liveness")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"
            assert data["timestamp"] == 1704067200.0
            assert data["service"] == "football-prediction-api"

    def test_liveness_check_different_timestamp(self, client):
        """测试不同时间戳的存活检查"""
        with patch("time.time", return_value=1704067260.0):  # 1分钟后
            response = client.get("/api/v1/health/liveness")

            assert response.status_code == 200
            data = response.json()
            assert data["timestamp"] == 1704067260.0

    # ========================================
    # 就绪检查端点测试
    # ========================================

    def test_readiness_check_ready(self, client):
        """测试就绪检查端点（就绪状态）"""
        with patch("time.time", return_value=1704067200.0):
            response = client.get("/api/v1/health/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["timestamp"] == 1704067200.0
            assert "checks" in data
            assert data["checks"]["database"]["status"] == "healthy"

    def test_readiness_check_not_ready(self, client):
        """测试就绪检查端点（未就绪状态）"""
        with patch("src.api.health._check_database") as mock_check:
            mock_check.return_value = {"status": "unhealthy", "latency_ms": 5000}

            response = client.get("/api/v1/health/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"]["status"] == "unhealthy"

    # ========================================
    # 详细健康检查端点测试
    # ========================================

    def test_detailed_health_check(self, client):
        """测试详细健康检查端点"""
        with patch("time.time", return_value=1704067200.0):
            response = client.get("/api/v1/health/detailed")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["timestamp"] == 1704067200.0
            assert "checks" in data

            # 检查各个组件状态
            checks = data["checks"]
            assert checks["database"]["status"] == "ok"
            assert checks["database"]["latency_ms"] == 5
            assert checks["redis"]["status"] == "ok"
            assert checks["redis"]["latency_ms"] == 5
            assert checks["system"]["status"] == "ok"
            assert checks["system"]["cpu_usage"] == "15%"
            assert checks["system"]["memory_usage"] == "45%"

    # ========================================
    # 数据库检查函数测试
    # ========================================

    def test_database_check_function(self):
        """测试数据库检查内部函数"""
        from src.api.health import _check_database

        result = _check_database()
        assert result["status"] == "healthy"
        assert result["latency_ms"] == 10
        assert isinstance(result["latency_ms"], int)

    # ========================================
    # 错误处理测试
    # ========================================

    def test_health_check_with_time_error(self, client):
        """测试时间函数出错时的健康检查"""
        with patch("time.time", side_effect=Exception("Time error")):
            response = client.get("/api/v1/health/")

            # 应该仍然返回200，因为time.time()错误不会阻止响应
            assert response.status_code == 200

    def test_database_check_with_exception(self, client):
        """测试数据库检查异常时的处理"""
        with patch("src.api.health._check_database", side_effect=Exception("DB error")):
            # 这应该会导致500错误，因为异常没有被捕获
            response = client.get("/api/v1/health/")
            assert response.status_code == 500

    # ========================================
    # 边界条件测试
    # ========================================

    def test_health_check_response_structure(self, client):
        """测试健康检查响应结构"""
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        data = response.json()

        # 验证必需字段存在
        required_fields = ["status", "timestamp", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # 验证checks结构
        assert "database" in data["checks"]
        assert isinstance(data["checks"]["database"], dict)

    def test_liveness_check_response_structure(self, client):
        """测试存活检查响应结构"""
        response = client.get("/api/v1/health/liveness")

        assert response.status_code == 200
        data = response.json()

        required_fields = ["status", "timestamp", "service"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["status"] == "alive"
        assert data["service"] == "football-prediction-api"

    def test_readiness_check_response_structure(self, client):
        """测试就绪检查响应结构"""
        response = client.get("/api/v1/health/readiness")

        assert response.status_code == 200
        data = response.json()

        required_fields = ["status", "timestamp", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        assert data["status"] in ["ready", "not_ready"]
        assert "database" in data["checks"]

    def test_detailed_health_check_response_structure(self, client):
        """测试详细健康检查响应结构"""
        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        required_fields = ["status", "timestamp", "checks"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # 验证详细检查包含所有组件
        expected_components = ["database", "redis", "system"]
        for component in expected_components:
            assert component in data["checks"], f"Missing component: {component}"

    # ========================================
    # 性能测试
    # ========================================

    def test_health_check_performance(self, client):
        """测试健康检查端点性能"""
        import time

        start_time = time.time()
        response = client.get("/api/v1/health/")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_liveness_check_performance(self, client):
        """测试存活检查端点性能"""
        import time

        start_time = time.time()
        response = client.get("/api/v1/health/liveness")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 0.5  # 应该在0.5秒内完成

    # ========================================
    # 不同的路由前缀测试
    # ========================================

    def test_health_check_without_prefix(self):
        """测试无前缀的健康检查"""
        app = FastAPI()
        app.include_router(health_router)
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

    def test_liveness_check_without_prefix(self):
        """测试无前缀的存活检查"""
        app = FastAPI()
        app.include_router(health_router)
        client = TestClient(app)

        response = client.get("/liveness")
        assert response.status_code == 200

    # ========================================
    # 并发测试
    # ========================================

    def test_concurrent_health_checks(self, client):
        """测试并发健康检查"""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/api/v1/health/")
            results.append(response.status_code)

        # 创建10个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(status == 200 for status in results)

    # ========================================
    # HTTP方法测试
    # ========================================

    def test_health_check_wrong_method(self, client):
        """测试错误的HTTP方法"""
        # POST请求应该失败
        response = client.post("/api/v1/health/")
        assert response.status_code == 405

        # PUT请求应该失败
        response = client.put("/api/v1/health/")
        assert response.status_code == 405

        # DELETE请求应该失败
        response = client.delete("/api/v1/health/")
        assert response.status_code == 405

    def test_liveness_check_wrong_method(self, client):
        """测试存活检查错误的HTTP方法"""
        response = client.post("/api/v1/health/liveness")
        assert response.status_code == 405

    # ========================================
    # 内容类型测试
    # ========================================

    def test_health_check_content_type(self, client):
        """测试响应内容类型"""
        response = client.get("/api/v1/health/")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    # ========================================
    # 时间戳精度测试
    # ========================================

    def test_timestamp_precision(self, client):
        """测试时间戳精度"""
        response1 = client.get("/api/v1/health/")
        time.sleep(0.001)  # 等待1毫秒
        time.sleep(0.001)  # 等待1毫秒
        time.sleep(0.001)  # 等待1毫秒
        response2 = client.get("/api/v1/health/")

        data1 = response1.json()
        data2 = response2.json()

        # 时间戳应该是浮点数
        assert isinstance(data1["timestamp"], float)
        assert isinstance(data2["timestamp"], float)

        # 第二个请求的时间戳应该更大
        assert data2["timestamp"] > data1["timestamp"]
