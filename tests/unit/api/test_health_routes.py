from typing import Optional

"""
健康检查路由API测试
Health Check Routes API Tests
"""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.health.routes import router


class TestHealthRoutes:
    """健康检查路由测试类"""

    def setup_method(self):
        """测试设置"""
        # 创建测试客户端
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    def test_health_check_basic(self, mock_get_db_manager, mock_datetime):
        """测试基础健康检查"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        # Mock时间戳
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        response = self.client.get("/api/health/")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "football-prediction-api"
        assert "version" in data
        assert data["timestamp"] == mock_now.isoformat()
        assert data["checks"]["database"]["status"] == "healthy"

        # 验证时间戳格式
        datetime.fromisoformat(data["timestamp"])

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    def test_health_check_response_structure(self, mock_get_db_manager, mock_datetime):
        """测试健康检查响应结构"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        # Mock时间戳
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        response = self.client.get("/api/health/")

        expected_keys = {"status", "timestamp", "service", "version", "checks"}
        actual_keys = set(response.json().keys())

        assert expected_keys.issubset(actual_keys)

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    def test_health_check_service_info(self, mock_get_db_manager, mock_datetime):
        """测试服务信息"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        response = self.client.get("/api/health/")
        data = response.json()

        assert data["service"] == "football-prediction-api"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    @patch("redis.from_url")
    def test_detailed_health_check_basic(
        self, mock_redis_from_url, mock_get_db_manager, mock_datetime
    ):
        """测试详细健康检查基础功能"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        # Mock Redis客户端
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        response = self.client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
        assert "checks" in data

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    @patch("redis.from_url")
    def test_detailed_health_check_response_structure(
        self, mock_redis_from_url, mock_get_db_manager, mock_datetime
    ):
        """测试详细健康检查响应结构"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        # Mock Redis客户端
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        response = self.client.get("/api/health/detailed")

        expected_keys = {"status", "timestamp", "service", "version", "checks"}
        actual_keys = set(response.json().keys())

        assert expected_keys == actual_keys

    @patch("src.api.health.routes.datetime")
    @patch("src.database.definitions.get_database_manager")
    @patch("redis.from_url")
    def test_detailed_health_check_components(
        self, mock_redis_from_url, mock_get_db_manager, mock_datetime
    ):
        """测试详细健康检查组件信息"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        # Mock Redis客户端
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        response = self.client.get("/api/health/detailed")
        data = response.json()

        components = data["checks"]
        assert isinstance(components, dict)

        # 应该包含数据库和Redis组件
        assert "database" in components
        assert "redis" in components

    @patch("src.database.definitions.get_database_manager")
    def test_health_check_timestamp_validity(self, mock_get_db_manager):
        """测试健康检查时间戳有效性"""
        # Mock数据库管理器为已初始化状态
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        response = self.client.get("/api/health/")
        data = response.json()

        # 时间戳应该是有效的ISO格式字符串
        timestamp_str = data["timestamp"]
        assert isinstance(timestamp_str, str), (
            f"Timestamp should be string, got {type(timestamp_str)}"
        )

        timestamp = datetime.fromisoformat(timestamp_str)

        # 时间戳应该接近当前时间（允许5分钟误差）
        now = datetime.utcnow()
        time_diff = abs((now - timestamp).total_seconds())
        assert time_diff < 300  # 5分钟

    def test_health_check_consistency(self):
        """测试健康检查一致性"""
        # 多次调用应该返回一致的基础信息
        response1 = self.client.get("/api/health/")
        response2 = self.client.get("/api/health/")

        data1 = response1.json()
        data2 = response2.json()

        assert data1["service"] == data2["service"]
        assert data1["version"] == data2["version"]

    def test_health_check_headers(self):
        """测试健康检查响应头"""
        response = self.client.get("/api/health/")

        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_detailed_health_check_error_handling(self):
        """测试详细健康检查错误处理"""
        response = self.client.get("/api/health/detailed")

        # 即使组件检查失败，也应该返回200状态码
        assert response.status_code == 200
        data = response.json()

        # 状态应该根据组件健康状况设置
        if data["status"] == "unhealthy":
            # 如果状态不健康，至少有一个组件应该有问题
            checks = data["checks"]
            assert any(
                "unhealthy" in str(check.get("status", "")) for check in checks.values()
            )

    def test_health_check_performance(self):
        """测试健康检查性能"""
        # 健康检查应该快速响应
        import time

        start_time = time.time()
        response = self.client.get("/api/health/")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 应该在1秒内响应

    @patch("redis.from_url")
    @patch("src.database.definitions.get_database_manager")
    def test_detailed_health_check_performance(self, mock_get_db_manager, mock_redis):
        """测试详细健康检查性能"""
        # Mock Redis to avoid connection timeout
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis.return_value = mock_redis_client

        # Mock database manager
        mock_db_manager = MagicMock()
        mock_db_manager.initialized = True
        mock_get_db_manager.return_value = mock_db_manager

        import time

        start_time = time.time()
        response = self.client.get("/api/health/detailed")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # 应该在2秒内响应

    def test_health_check_cors_headers(self):
        """测试健康检查CORS头"""
        response = self.client.options("/api/health/")

        # OPTIONS请求应该被正确处理
        assert response.status_code in [200, 405]

    def test_invalid_endpoint_handling(self):
        """测试无效端点处理"""
        response = self.client.get("/api/health/invalid")

        # 无效端点应该返回404
        assert response.status_code == 404

    def test_health_check_content_encoding(self):
        """测试健康检查内容编码"""
        response = self.client.get("/api/health/")

        assert response.status_code == 200
        assert response.headers.get("content-encoding") != "gzip"  # 简单响应不需要压缩

    def test_detailed_health_check_service_info(self):
        """测试详细健康检查服务信息"""
        response = self.client.get("/api/health/detailed")
        data = response.json()

        assert data["service"] == "football-prediction-api"
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
        assert data["timestamp"] is not None

    def test_health_check_multiple_requests(self):
        """测试多次健康检查请求"""
        # 多次请求应该都成功
        responses = []
        for _ in range(5):
            response = self.client.get("/api/health/")
            responses.append(response)
            assert response.status_code == 200

        # 所有响应应该具有相同的基本结构
        first_data = responses[0].json()
        for response in responses:
            data = response.json()
            assert data["service"] == first_data["service"]
            assert data["version"] == first_data["version"]