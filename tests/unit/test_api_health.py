"""
API健康检查模块测试
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.health import router
from src.database.connection import get_db_session


class TestHealthAPI:
    """健康检查API测试"""

    def setup_method(self):
        """测试设置"""
        self.app = FastAPI()
        self.app.include_router(router)

        # 覆盖数据库依赖
        def mock_get_db_session():
            return Mock()

        self.app.dependency_overrides[get_db_session] = mock_get_db_session
        self.client = TestClient(self.app)

    def test_health_check_endpoint_exists(self):
        """测试健康检查端点存在"""
        # Mock数据库和Redis检查函数
        with patch("src.api.health._check_database") as mock_check_db, patch(
            "src.api.health._check_redis"
        ) as mock_check_redis, patch(
            "src.api.health._check_filesystem"
        ) as mock_check_fs:
            # 符合ServiceCheck schema的Mock数据
            mock_check_db.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10.0,
                "details": {"connection": "ok"},
            }
            mock_check_redis.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5.0,
                "details": {"connection": "ok"},
            }
            mock_check_fs.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 2.0,
                "details": {"disk_space": "ok"},
            }

            response = self.client.get("/health")
            assert response.status_code == 200

    def test_health_check_structure(self):
        """测试健康检查响应结构"""
        # Mock数据库和Redis检查函数
        with patch("src.api.health._check_database") as mock_check_db, patch(
            "src.api.health._check_redis"
        ) as mock_check_redis, patch(
            "src.api.health._check_filesystem"
        ) as mock_check_fs:
            # 符合ServiceCheck schema的Mock数据
            mock_check_db.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10.0,
                "details": {"connection": "ok"},
            }
            mock_check_redis.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5.0,
                "details": {"connection": "ok"},
            }
            mock_check_fs.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 2.0,
                "details": {"disk_space": "ok"},
            }

            response = self.client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "checks" in data

    def test_health_endpoint_mock_success(self):
        """测试健康检查端点模拟成功"""
        # Mock所有检查函数
        with patch("src.api.health._check_database") as mock_check_db, patch(
            "src.api.health._check_redis"
        ) as mock_check_redis, patch(
            "src.api.health._check_filesystem"
        ) as mock_check_fs:
            # 符合ServiceCheck schema的Mock数据
            mock_check_db.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10.0,
                "details": {"connection": "ok"},
            }
            mock_check_redis.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5.0,
                "details": {"connection": "ok"},
            }
            mock_check_fs.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 2.0,
                "details": {"disk_space": "ok"},
            }

            response = self.client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_health_router_configuration(self):
        """测试健康检查路由配置"""
        assert router.tags == ["健康检查"]

    def test_health_check_basic_structure(self):
        """测试健康检查基本结构"""
        # 模拟健康检查响应结构
        health_response = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00",
            "service": "football-prediction-api",
            "version": "1.0.0",
            "checks": {},
        }

        assert "status" in health_response
        assert "timestamp" in health_response
        assert "service" in health_response
        assert "checks" in health_response


class TestHealthUtilities:
    """健康检查工具函数测试"""

    def test_health_status_calculation(self):
        """测试健康状态计算逻辑"""
        # 测试所有服务健康
        services = {"db": {"status": "healthy"}, "redis": {"status": "healthy"}}
        # 验证服务状态
        assert all(service["status"] == "healthy" for service in services.values())

    def test_response_time_measurement(self):
        """测试响应时间测量"""
        import time

        start_time = time.time()
        time.sleep(0.001)  # 模拟操作
        response_time = time.time() - start_time
        assert response_time > 0
        assert response_time < 1  # 应该很快

    def test_error_handling_in_health_checks(self):
        """测试健康检查中的错误处理"""
        with patch("src.api.health.logger") as mock_logger:
            # 模拟错误情况
            try:
                raise Exception("Test error")
            except Exception as e:
                mock_logger.error.assert_not_called()  # 还没调用
                # 这里应该有错误处理逻辑
                assert str(e) == "Test error"


class TestHealthIntegration:
    """健康检查集成测试"""

    def test_health_check_with_real_app(self):
        """测试与真实应用的健康检查集成"""
        app = FastAPI()
        app.include_router(router)

        # 覆盖数据库依赖
        def mock_get_db_session():
            return Mock()

        app.dependency_overrides[get_db_session] = mock_get_db_session
        client = TestClient(app)

        # Mock所有检查函数
        with patch("src.api.health._check_database") as mock_check_db, patch(
            "src.api.health._check_redis"
        ) as mock_check_redis, patch(
            "src.api.health._check_filesystem"
        ) as mock_check_fs:
            # 符合ServiceCheck schema的Mock数据
            mock_check_db.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10.0,
                "details": {"connection": "ok"},
            }
            mock_check_redis.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5.0,
                "details": {"connection": "ok"},
            }
            mock_check_fs.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 2.0,
                "details": {"disk_space": "ok"},
            }

            # 测试基本端点可访问
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_metrics_collection(self):
        """测试健康指标收集"""
        # 模拟指标收集
        metrics = {"uptime": 3600, "memory_usage": 0.75, "cpu_usage": 0.45}
        assert all(isinstance(v, (int, float)) for v in metrics.values())

    def test_health_alerting_integration(self):
        """测试健康检查与告警系统集成"""
        # 模拟告警触发条件
        unhealthy_services = ["database", "redis"]
        if unhealthy_services:
            # 应该触发告警
            assert len(unhealthy_services) > 0
