"""
监控API端点测试

测试系统性能指标、业务指标监控和运行时统计信息API。
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.monitoring import _get_business_metrics, _get_database_metrics
from src.database.connection import get_db_session
from src.main import app


# 创建测试用的数据库会话模拟
def override_get_db_session():
    """测试用的数据库会话依赖覆盖"""
    mock_session = MagicMock(spec=Session)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = [1]
    mock_session.execute.return_value = mock_result
    try:
        yield mock_session
    finally:
        pass


# 覆盖依赖注入
app.dependency_overrides[get_db_session] = override_get_db_session

client = TestClient(app)


class TestMonitoringAPI:
    """监控API端点测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        mock_session = MagicMock(spec=Session)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [1]
        mock_session.execute.return_value = mock_result
        return mock_session

    @patch("src.api.monitoring.psutil")
    @patch("src.api.monitoring._get_database_metrics")
    @patch("src.api.monitoring._get_business_metrics")
    def test_get_metrics_success(self, mock_business, mock_db_metrics, mock_psutil):
        """测试获取应用性能指标 - 成功场景"""
        # 模拟psutil返回数据
        mock_psutil.cpu_percent.return_value = 15.5
        mock_memory = MagicMock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_memory.used = 4294967296  # 4GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.total = 1099511627776  # 1TB
        mock_disk.free = 549755813888  # 500GB
        mock_disk.percent = 50.0
        mock_psutil.disk_usage.return_value = mock_disk

        # 模拟异步函数返回值
        mock_db_metrics.return_value = {
            "healthy": True,
            "response_time_ms": 12.5,
            "statistics": {"teams_count": 100, "matches_count": 500},
        }

        mock_business.return_value = {
            "24h_predictions": 25,
            "upcoming_matches_7d": 10,
            "model_accuracy_30d": 85.6,
        }

        with patch("os.getloadavg", return_value=[0.5, 0.7, 0.8]):
            response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "response_time_ms" in data
        assert "system" in data
        assert "database" in data
        assert "runtime" in data
        assert "business" in data

        # 验证系统指标
        assert data["system"]["cpu_percent"] == 15.5
        assert data["system"]["memory"]["percent"] == 50.0
        assert data["system"]["disk"]["percent"] == 50.0

    @patch("src.api.monitoring.psutil")
    def test_get_metrics_with_exception(self, mock_psutil):
        """测试获取应用性能指标 - 异常场景"""
        # 模拟psutil抛出异常
        mock_psutil.cpu_percent.side_effect = Exception("系统监控错误")

        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "response_time_ms" in data
        assert "system" in data
        assert "database" in data
        assert "runtime" in data
        assert "business" in data

    @pytest.mark.asyncio
    async def test_get_database_metrics_success(self, mock_db_session):
        """测试获取数据库性能指标 - 成功场景"""
        # 模拟数据库查询结果
        mock_results = {
            "SELECT 1": [1],
            "SELECT COUNT(*) FROM teams": [150],
            "SELECT COUNT(*) FROM matches": [800],
            "SELECT COUNT(*) FROM predictions": [320],
            "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'": [5],
        }

        def mock_execute(query):
            mock_result = MagicMock()
            query_str = str(query)
            if "SELECT 1" in query_str:
                mock_result.fetchone.return_value = mock_results["SELECT 1"]
            elif "teams" in query_str:
                mock_result.fetchone.return_value = mock_results[
                    "SELECT COUNT(*) FROM teams"
                ]
            elif "matches" in query_str:
                mock_result.fetchone.return_value = mock_results[
                    "SELECT COUNT(*) FROM matches"
                ]
            elif "predictions" in query_str:
                mock_result.fetchone.return_value = mock_results[
                    "SELECT COUNT(*) FROM predictions"
                ]
            elif "pg_stat_activity" in query_str:
                mock_result.fetchone.return_value = mock_results[
                    "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
                ]
            return mock_result

        mock_db_session.execute.side_effect = mock_execute

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is True
        assert "response_time_ms" in result
        assert result["statistics"]["teams_count"] == 150
        assert result["statistics"]["matches_count"] == 800
        assert result["statistics"]["predictions_count"] == 320
        assert result["statistics"]["active_connections"] == 5

    @pytest.mark.asyncio
    async def test_get_database_metrics_with_exception(self, mock_db_session):
        """测试获取数据库性能指标 - 异常场景"""
        # 模拟数据库连接失败
        mock_db_session.execute.side_effect = Exception("数据库连接失败")

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_business_metrics_success(self, mock_db_session):
        """测试获取业务指标统计 - 成功场景"""
        # 模拟业务查询结果
        mock_results = {
            "recent_predictions": [42],
            "upcoming_matches": [15],
            "accuracy_rate": [87.25],
        }

        def mock_execute(query):
            mock_result = MagicMock()
            query_str = str(query)
            if "recent_predictions" in query_str or "24 hours" in query_str:
                mock_result.fetchone.return_value = mock_results["recent_predictions"]
            elif "upcoming_matches" in query_str or "7 days" in query_str:
                mock_result.fetchone.return_value = mock_results["upcoming_matches"]
            elif "accuracy_rate" in query_str or "30 days" in query_str:
                mock_result.fetchone.return_value = mock_results["accuracy_rate"]
            return mock_result

        mock_db_session.execute.side_effect = mock_execute

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] == 42
        assert result["upcoming_matches_7d"] == 15
        assert result["model_accuracy_30d"] == 87.25
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_business_metrics_with_exception(self, mock_db_session):
        """测试获取业务指标统计 - 异常场景"""
        # 模拟查询失败
        mock_db_session.execute.side_effect = Exception("业务查询失败")

        result = await _get_business_metrics(mock_db_session)

        # 验证异常时返回None值，而不是error字段
        assert result["24h_predictions"] is None
        assert result["upcoming_matches_7d"] is None
        assert result["model_accuracy_30d"] is None
        assert "last_updated" in result

    def test_get_service_status_all_healthy(self):
        """测试服务状态检查 - 所有服务健康"""
        # 模拟Redis连接成功
        with patch("redis.from_url") as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis.return_value = mock_redis_instance

            response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["services"]["api"] == "healthy"
        assert data["services"]["database"] == "healthy"
        assert data["services"]["cache"] == "healthy"
        assert "timestamp" in data

    def test_get_service_status_database_unhealthy(self):
        """测试服务状态检查 - 数据库不健康"""

        # 覆盖依赖注入，模拟数据库连接失败
        def override_get_db_session_fail():
            mock_session = MagicMock(spec=Session)
            mock_session.execute.side_effect = Exception("数据库连接失败")
            try:
                yield mock_session
            finally:
                pass

        # 临时覆盖依赖
        original_override = app.dependency_overrides.get(get_db_session)
        app.dependency_overrides[get_db_session] = override_get_db_session_fail

        try:
            # 模拟Redis连接失败
            with patch("redis.from_url", side_effect=Exception("Redis连接失败")):
                response = client.get("/api/v1/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "degraded"
            assert data["services"]["api"] == "healthy"
            assert data["services"]["database"] == "unhealthy"
            assert data["services"]["cache"] == "unhealthy"
        finally:
            # 恢复原始依赖
            if original_override:
                app.dependency_overrides[get_db_session] = original_override
            else:
                app.dependency_overrides[get_db_session] = override_get_db_session

    @patch.dict(os.environ, {"REDIS_URL": "redis://test:6379/0"})
    def test_get_service_status_with_custom_redis_url(self):
        """测试服务状态检查 - 自定义Redis URL"""
        # 模拟Redis连接成功，验证使用了自定义URL
        with patch("redis.from_url") as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis.return_value = mock_redis_instance

            response = client.get("/api/v1/status")

            # 验证使用了环境变量中的Redis URL
            mock_redis.assert_called_with("redis://test:6379/0")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_monitoring_endpoints_registered(self):
        """测试监控端点是否正确注册"""
        # 验证路由是否存在
        routes = [route.path for route in app.routes]
        assert "/api/v1/metrics" in routes or any(
            "/metrics" in route for route in routes
        )
        assert "/api/v1/status" in routes or any("/status" in route for route in routes)

    def test_error_logging(self):
        """测试错误日志记录"""

        # 覆盖依赖注入，模拟数据库连接失败
        def override_get_db_session_fail():
            mock_session = MagicMock(spec=Session)
            mock_session.execute.side_effect = Exception("测试错误")
            try:
                yield mock_session
            finally:
                pass

        # 临时覆盖依赖
        original_override = app.dependency_overrides.get(get_db_session)
        app.dependency_overrides[get_db_session] = override_get_db_session_fail

        try:
            # 验证响应正常返回
            response = client.get("/api/v1/status")
            assert response.status_code == 200
            data = response.json()
            assert data["services"]["database"] == "unhealthy"
        finally:
            # 恢复原始依赖
            if original_override:
                app.dependency_overrides[get_db_session] = original_override
            else:
                app.dependency_overrides[get_db_session] = override_get_db_session


class TestMonitoringMetricsStructure:
    """监控指标数据结构测试"""

    def test_metrics_response_structure(self):
        """测试metrics响应数据结构"""
        with patch("src.api.monitoring.psutil"), patch(
            "src.api.monitoring._get_database_metrics", return_value={}
        ), patch("src.api.monitoring._get_business_metrics", return_value={}):
            response = client.get("/api/v1/metrics")
            data = response.json()

            # 验证必需字段存在
            required_fields = [
                "status",
                "response_time_ms",
                "system",
                "database",
                "runtime",
                "business",
            ]
            for field in required_fields:
                assert field in data, f"缺少必需字段: {field}"

    def test_status_response_structure(self):
        """测试status响应数据结构"""
        response = client.get("/api/v1/status")
        data = response.json()

        # 验证必需字段存在
        required_fields = ["status", "timestamp", "services"]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"

        # 验证services子字段
        services_fields = ["api", "database", "cache"]
        for field in services_fields:
            assert field in data["services"], f"services中缺少字段: {field}"


class TestMonitoringPerformance:
    """监控API性能测试"""

    def test_metrics_response_time(self):
        """测试metrics端点响应时间合理性"""
        with patch("src.api.monitoring.psutil"), patch(
            "src.api.monitoring._get_database_metrics", return_value={}
        ), patch("src.api.monitoring._get_business_metrics", return_value={}):
            import time

            start_time = time.time()
            response = client.get("/api/v1/metrics")
            end_time = time.time()

            # 响应时间应该在合理范围内（考虑到mocking，应该很快）
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            assert response_time < 1000, f"响应时间过长: {response_time}ms"

            # 验证返回的response_time_ms字段存在且为数字
            data = response.json()
            if "response_time_ms" in data:
                assert isinstance(data["response_time_ms"], (int, float))

    def test_status_response_time(self):
        """测试status端点响应时间合理性"""
        import time

        start_time = time.time()
        response = client.get("/api/v1/status")
        end_time = time.time()

        # 状态检查应该很快
        response_time = (end_time - start_time) * 1000
        assert response_time < 1000, f"状态检查响应时间过长: {response_time}ms"
        assert response.status_code == 200
