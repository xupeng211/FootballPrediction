"""
监控系统API测试 - Phase 3
Monitoring System API Tests - Phase 3

测试范围 / Test Scope:
- src/api/monitoring.py 的所有端点 / All endpoints in src/api/monitoring.py
- 健康检查与状态监控 / Health check and status monitoring
- 指标收集与导出 / Metrics collection and export
- Prometheus指标端点 / Prometheus metrics endpoint
- 监控收集器控制 / Metrics collector control
- 异常数据场景处理 / Abnormal data scenarios handling

测试覆盖目标 / Test Coverage Target:
- API模块平均覆盖率 ≥ 60% / API module average coverage ≥ 60%
- 每个路由至少有1个成功和1个失败测试 / Each route has at least 1 success and 1 failure test
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest


class MockAsyncResult:
    """Mock for SQLAlchemy async result with proper scalars().all() support"""

    def __init__(self, scalars_result=None, scalar_one_or_none_result=None):
        self._scalars_result = scalars_result or []
        self._scalar_one_or_none_result = scalar_one_or_none_result

    def scalars(self):
        return MockScalarResult(self._scalars_result)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none_result


class MockScalarResult:
    """Mock for SQLAlchemy scalars() result"""

    def __init__(self, result):
        self._result = result if isinstance(result, list) else [result]

    def all(self):
        return self._result

    def first(self):
        return self._result[0] if self._result else None


from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

from src.api.monitoring import (
    _get_business_metrics,
    _get_database_metrics,
    collector_health,
    collector_status,
    get_metrics,
    get_service_status,
    manual_collect,
    prometheus_metrics,
    start_collector,
    stop_collector,
)


class TestDatabaseMetrics:
    """数据库指标测试 / Database Metrics Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @pytest.mark.asyncio
    async def test_get_database_metrics_success(self, mock_db_session):
        """测试成功获取数据库指标 / Test successful database metrics retrieval"""
        # 模拟数据库查询结果
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=1)),  # SELECT 1
            Mock(fetchone=Mock(return_value=[100])),  # teams count
            Mock(fetchone=Mock(return_value=[500])),  # matches count
            Mock(fetchone=Mock(return_value=[1000])),  # predictions count
            Mock(fetchone=Mock(return_value=[10])),  # active connections
        ]

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is True
        assert result["statistics"]["teams_count"] == 100
        assert result["statistics"]["matches_count"] == 500
        assert result["statistics"]["predictions_count"] == 1000
        assert result["statistics"]["active_connections"] == 10
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_get_database_metrics_health_check_failure(self, mock_db_session):
        """测试数据库健康检查失败 / Test database health check failure"""
        mock_db_session.execute.side_effect = Exception("Database connection failed")

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is False
        assert "error" in result
        assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_database_metrics_stats_query_failure(self, mock_db_session):
        """测试统计查询失败 / Test statistics query failure"""
        # 健康检查成功，但统计查询失败
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=1)),  # SELECT 1成功
            Exception("Stats query failed"),  # 统计查询失败
        ]

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is False
        assert result["statistics"]["teams_count"] == 0
        assert result["statistics"]["matches_count"] == 0
        assert result["statistics"]["predictions_count"] == 0
        assert result["statistics"]["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_get_database_metrics_none_values(self, mock_db_session):
        """测试数据库返回None值 / Test database returns None values"""
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=1)),  # SELECT 1
            Mock(fetchone=Mock(return_value=None)),  # teams count None
            Mock(fetchone=Mock(return_value=[None])),  # matches count None
            Mock(fetchone=Mock(return_value=[500])),  # predictions count
            Mock(fetchone=Mock(return_value=[10])),  # active connections
        ]

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is True
        assert result["statistics"]["teams_count"] == 0
        assert result["statistics"]["matches_count"] == 0
        assert result["statistics"]["predictions_count"] == 500
        assert result["statistics"]["active_connections"] == 10


class TestBusinessMetrics:
    """业务指标测试 / Business Metrics Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @pytest.mark.asyncio
    async def test_get_business_metrics_success(self, mock_db_session):
        """测试成功获取业务指标 / Test successful business metrics retrieval"""
        # 模拟业务查询结果
        mock_db_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=[50])),  # recent predictions
            Mock(fetchone=Mock(return_value=[20])),  # upcoming matches
            Mock(fetchone=Mock(return_value=[85.5])),  # accuracy rate
        ]

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] == 50
        assert result["upcoming_matches_7d"] == 20
        assert result["model_accuracy_30d"] == 85.5
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_business_metrics_none_values(self, mock_db_session):
        """测试业务指标返回None值 / Test business metrics return None values"""
        mock_db_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=None)),  # recent predictions None
            Mock(fetchone=Mock(return_value=[None])),  # upcoming matches None
            Mock(fetchone=Mock(return_value=None)),  # accuracy rate None
        ]

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] is None
        assert result["upcoming_matches_7d"] is None
        assert result["model_accuracy_30d"] is None
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_business_metrics_query_exception(self, mock_db_session):
        """测试业务指标查询异常 / Test business metrics query exception"""
        mock_db_session.execute.side_effect = Exception("Query failed")

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] is None
        assert result["upcoming_matches_7d"] is None
        assert result["model_accuracy_30d"] is None
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_business_metrics_invalid_conversion(self, mock_db_session):
        """测试无效数据转换 / Test invalid data conversion"""
        mock_db_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=["invalid"])),  # invalid predictions
            Mock(fetchone=Mock(return_value=[20])),  # valid matches
            Mock(fetchone=Mock(return_value=[85.5])),  # valid accuracy
        ]

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] is None  # 无效值应转为None
        assert result["upcoming_matches_7d"] == 20
        assert result["model_accuracy_30d"] == 85.5


class TestMetricsEndpoint:
    """指标端点测试 / Metrics Endpoint Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @patch("src.api.monitoring.psutil.cpu_percent")
    @patch("src.api.monitoring.psutil.virtual_memory")
    @patch("src.api.monitoring.psutil.disk_usage")
    @patch("src.api.monitoring.os.getloadavg")
    @patch("src.api.monitoring.os.getenv")
    @pytest.mark.asyncio
    async def test_get_metrics_success(
        self,
        mock_getenv,
        mock_getloadavg,
        mock_disk_usage,
        mock_virtual_memory,
        mock_cpu_percent,
        mock_db_session,
    ):
        """测试成功获取系统指标 / Test successful system metrics retrieval"""
        # 模拟系统指标
        mock_cpu_percent.return_value = 25.5
        mock_virtual_memory.return_value = Mock(
            total=8589934592, available=4294967296, percent=50.0, used=4294967296
        )
        mock_disk_usage.return_value = Mock(
            total=100000000000, free=50000000000, percent=50.0
        )
        mock_getloadavg.return_value = (1.5, 1.2, 1.0)
        mock_getenv.side_effect = lambda key, default: {
            "PYTHON_VERSION": "3.11.0",
            "ENVIRONMENT": "development",
        }.get(key, default)

        # 模拟数据库和业务指标
        with patch(
            "src.api.monitoring._get_database_metrics"
        ) as mock_db_metrics, patch(
            "src.api.monitoring._get_business_metrics"
        ) as mock_biz_metrics:
            mock_db_metrics.return_value = {
                "healthy": True,
                "response_time_ms": 10.5,
                "statistics": {"teams_count": 100},
            }
            mock_biz_metrics.return_value = {
                "24h_predictions": 50,
                "last_updated": "2025-01-01T00:00:00",
            }

            result = await get_metrics(mock_db_session)

            assert result["status"] == "ok"
            assert "system" in result
            assert "database" in result
            assert "business" in result
            assert "runtime" in result
            assert result["system"]["cpu_percent"] == 25.5
            assert result["database"]["healthy"] is True
            assert result["business"]["24h_predictions"] == 50
            assert "response_time_ms" in result

    @patch("src.api.monitoring.psutil.cpu_percent")
    @patch("src.api.monitoring.psutil.virtual_memory")
    @pytest.mark.asyncio
    async def test_get_metrics_system_exception(
        self, mock_virtual_memory, mock_cpu_percent, mock_db_session
    ):
        """测试系统指标获取异常 / Test system metrics retrieval exception"""
        mock_cpu_percent.side_effect = Exception("System metrics failed")
        mock_virtual_memory.return_value = Mock(
            total=8589934592, available=4294967296, percent=50.0, used=4294967296
        )

        # 模拟数据库和业务指标
        with patch(
            "src.api.monitoring._get_database_metrics"
        ) as mock_db_metrics, patch(
            "src.api.monitoring._get_business_metrics"
        ) as mock_biz_metrics:
            mock_db_metrics.return_value = {"healthy": True}
            mock_biz_metrics.return_value = {"24h_predictions": 50}

            result = await get_metrics(mock_db_session)

            assert result["status"] == "error"
            assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_get_metrics_database_awaitable(self, mock_db_session):
        """测试数据库指标为可等待对象 / Test database metrics is awaitable"""

        # 创建可等待的mock对象
        async def mock_async_db_metrics():
            return {"healthy": True, "response_time_ms": 10.0}

        async def mock_async_biz_metrics():
            return {"24h_predictions": 50}

        with patch("src.api.monitoring.psutil.cpu_percent", return_value=25.0), patch(
            "src.api.monitoring.psutil.virtual_memory",
            return_value=Mock(total=1000, available=500, percent=50.0, used=500),
        ), patch(
            "src.api.monitoring.psutil.disk_usage",
            return_value=Mock(total=1000, free=500, percent=50.0),
        ), patch(
            "src.api.monitoring.os.getloadavg", return_value=(1.0, 1.0, 1.0)
        ), patch(
            "src.api.monitoring.os.getenv", return_value="test"
        ):
            with patch(
                "src.api.monitoring._get_database_metrics",
                return_value=mock_async_db_metrics(),
            ), patch(
                "src.api.monitoring._get_business_metrics",
                return_value=mock_async_biz_metrics(),
            ):
                result = await get_metrics(mock_db_session)

                assert result["status"] == "ok"
                assert result["database"]["healthy"] is True
                assert result["business"]["24h_predictions"] == 50


class TestServiceStatusEndpoint:
    """服务状态端点测试 / Service Status Endpoint Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @patch("src.api.monitoring.os.getenv")
    @patch("src.api.monitoring.redis.from_url")
    @pytest.mark.asyncio
    async def test_get_service_status_all_healthy(
        self, mock_redis_from_url, mock_getenv, mock_db_session
    ):
        """测试所有服务健康 / Test all services healthy"""
        mock_getenv.return_value = "redis://localhost:6379/0"
        mock_redis_client = Mock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        result = await get_service_status(mock_db_session)

        assert result["status"] == "healthy"
        assert result["services"]["api"] == "healthy"
        assert result["services"]["database"] == "healthy"
        assert result["services"]["cache"] == "healthy"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_service_status_database_unhealthy(self, mock_db_session):
        """测试数据库不健康 / Test database unhealthy"""
        # 数据库健康检查失败
        mock_db_session.execute.side_effect = Exception("Database failed")

        with patch(
            "src.api.monitoring.os.getenv", return_value="redis://localhost:6379/0"
        ), patch("src.api.monitoring.redis.from_url") as mock_redis_from_url:
            mock_redis_client = Mock()
            mock_redis_client.ping.return_value = True
            mock_redis_from_url.return_value = mock_redis_client

            result = await get_service_status(mock_db_session)

            assert result["status"] == "degraded"
            assert result["services"]["api"] == "healthy"
            assert result["services"]["database"] == "unhealthy"
            assert result["services"]["cache"] == "healthy"

    @patch("src.api.monitoring.os.getenv")
    @patch("src.api.monitoring.redis.from_url")
    @pytest.mark.asyncio
    async def test_get_service_status_cache_unhealthy(
        self, mock_redis_from_url, mock_getenv, mock_db_session
    ):
        """测试缓存不健康 / Test cache unhealthy"""
        mock_getenv.return_value = "redis://localhost:6379/0"
        mock_redis_client = Mock()
        mock_redis_client.ping.side_effect = Exception("Redis failed")
        mock_redis_from_url.return_value = mock_redis_client

        result = await get_service_status(mock_db_session)

        assert result["status"] == "degraded"
        assert result["services"]["api"] == "healthy"
        assert result["services"]["database"] == "healthy"
        assert result["services"]["cache"] == "unhealthy"

    @patch("src.api.monitoring.os.getenv")
    @patch("src.api.monitoring.redis.from_url")
    @pytest.mark.asyncio
    async def test_get_service_status_all_unhealthy(
        self, mock_redis_from_url, mock_getenv, mock_db_session
    ):
        """测试所有服务不健康 / Test all services unhealthy"""
        # API总是健康的（因为能到达这个端点）
        # 数据库不健康
        mock_db_session.execute.side_effect = Exception("Database failed")

        mock_getenv.return_value = "redis://localhost:6379/0"
        mock_redis_client = Mock()
        mock_redis_client.ping.side_effect = Exception("Redis failed")
        mock_redis_from_url.return_value = mock_redis_client

        result = await get_service_status(mock_db_session)

        # 根据逻辑：API健康但数据库和缓存不健康时状态为degraded
        assert result["status"] == "degraded"
        assert result["services"]["api"] == "healthy"
        assert result["services"]["database"] == "unhealthy"
        assert result["services"]["cache"] == "unhealthy"


class TestPrometheusMetricsEndpoint:
    """Prometheus指标端点测试 / Prometheus Metrics Endpoint Tests"""

    @patch("src.api.monitoring.get_metrics_exporter")
    @pytest.mark.asyncio
    async def test_prometheus_metrics_success(self, mock_get_metrics_exporter):
        """测试成功获取Prometheus指标 / Test successful Prometheus metrics retrieval"""
        mock_exporter = Mock()
        mock_exporter.get_metrics.return_value = (
            "text/plain",
            "# TYPE test_metric counter",
        )
        mock_get_metrics_exporter.return_value = mock_exporter

        response = await prometheus_metrics()

        assert isinstance(response, PlainTextResponse)
        assert response.media_type == "text/plain"
        assert "# TYPE test_metric counter" in response.body.decode()

    @patch("src.api.monitoring.get_metrics_exporter")
    @pytest.mark.asyncio
    async def test_prometheus_metrics_exception(self, mock_get_metrics_exporter):
        """测试Prometheus指标获取异常 / Test Prometheus metrics retrieval exception"""
        mock_get_metrics_exporter.side_effect = Exception("Exporter failed")

        with pytest.raises(HTTPException) as exc_info:
            await prometheus_metrics()

        assert exc_info.value.status_code == 500
        assert "获取监控指标失败" in exc_info.value.detail


class TestCollectorEndpoints:
    """监控收集器端点测试 / Collector Endpoints Tests"""

    @patch("src.api.monitoring.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_collector_health_success(self, mock_get_metrics_collector):
        """测试收集器健康检查成功 / Test collector health check success"""
        mock_collector = Mock()
        mock_collector.get_status.return_value = "running"
        mock_get_metrics_collector.return_value = mock_collector

        result = await collector_health()

        assert result["status"] == "healthy"
        assert result["metrics_collector"] == "running"
        assert "监控收集器运行正常" in result["message"]

    @patch("src.api.monitoring.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_collector_health_exception(self, mock_get_metrics_collector):
        """测试收集器健康检查异常 / Test collector health check exception"""
        mock_get_metrics_collector.side_effect = Exception("Collector failed")

        result = await collector_health()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "监控系统异常" in result["message"]

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_manual_collect_success(self, mock_get_metrics_collector):
        """测试手动收集成功 / Test manual collection success"""
        mock_collector = Mock()
        mock_collector.collect_once = AsyncMock(
            return_value={"status": "success", "metrics_collected": 100}
        )
        mock_get_metrics_collector.return_value = mock_collector

        result = await manual_collect()

        assert result["status"] == "success"
        assert result["metrics_collected"] == 100

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_manual_collect_exception(self, mock_get_metrics_collector):
        """测试手动收集异常 / Test manual collection exception"""
        mock_collector = Mock()
        mock_collector.collect_once = AsyncMock(
            side_effect=Exception("Collection failed")
        )
        mock_get_metrics_collector.return_value = mock_collector

        with pytest.raises(HTTPException) as exc_info:
            await manual_collect()

        assert exc_info.value.status_code == 500
        assert "指标收集失败" in exc_info.value.detail

    @patch("src.api.monitoring.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_collector_status_success(self, mock_get_metrics_collector):
        """测试获取收集器状态成功 / Test getting collector status success"""
        mock_collector = Mock()
        mock_collector.get_status.return_value = {
            "status": "running",
            "last_collection": "2025-01-01T00:00:00",
        }
        mock_get_metrics_collector.return_value = mock_collector

        result = await collector_status()

        assert result["status"] == "running"
        assert result["last_collection"] == "2025-01-01T00:00:00"

    @patch("src.api.monitoring.get_metrics_collector")
    @pytest.mark.asyncio
    async def test_collector_status_exception(self, mock_get_metrics_collector):
        """测试获取收集器状态异常 / Test getting collector status exception"""
        mock_get_metrics_collector.side_effect = Exception("Status check failed")

        with pytest.raises(HTTPException) as exc_info:
            await collector_status()

        assert exc_info.value.status_code == 500
        assert "获取状态失败" in exc_info.value.detail

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_start_collector_success(self, mock_get_metrics_collector):
        """测试启动收集器成功 / Test starting collector success"""
        mock_collector = Mock()
        mock_collector.start = AsyncMock()
        mock_get_metrics_collector.return_value = mock_collector

        result = await start_collector()

        assert result["message"] == "指标收集器启动成功"
        mock_collector.start.assert_called_once()

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_start_collector_exception(self, mock_get_metrics_collector):
        """测试启动收集器异常 / Test starting collector exception"""
        mock_collector = Mock()
        mock_collector.start = AsyncMock(side_effect=Exception("Start failed"))
        mock_get_metrics_collector.return_value = mock_collector

        with pytest.raises(HTTPException) as exc_info:
            await start_collector()

        assert exc_info.value.status_code == 500
        assert "启动失败" in exc_info.value.detail

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_stop_collector_success(self, mock_get_metrics_collector):
        """测试停止收集器成功 / Test stopping collector success"""
        mock_collector = Mock()
        mock_collector.stop = AsyncMock()
        mock_get_metrics_collector.return_value = mock_collector

        result = await stop_collector()

        assert result["message"] == "指标收集器停止成功"
        mock_collector.stop.assert_called_once()

    @patch("src.api.monitoring.get_metrics_collector")
    async def test_stop_collector_exception(self, mock_get_metrics_collector):
        """测试停止收集器异常 / Test stopping collector exception"""
        mock_collector = Mock()
        mock_collector.stop = AsyncMock(side_effect=Exception("Stop failed"))
        mock_get_metrics_collector.return_value = mock_collector

        with pytest.raises(HTTPException) as exc_info:
            await stop_collector()

        assert exc_info.value.status_code == 500
        assert "停止失败" in exc_info.value.detail


class TestMonitoringEdgeCases:
    """监控边界情况测试 / Monitoring Edge Cases Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @pytest.mark.asyncio
    async def test_database_metrics_empty_result(self, mock_db_session):
        """测试数据库空结果 / Test database empty results"""
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=1)),  # SELECT 1成功
            Mock(fetchone=Mock(return_value=[])),  # 空结果
            Mock(fetchone=Mock(return_value=None)),  # None结果
            Mock(fetchone=Mock(return_value=[0])),  # 零值
            Mock(fetchone=Mock(return_value=[0])),  # 零值
        ]

        result = await _get_database_metrics(mock_db_session)

        assert result["healthy"] is True
        assert result["statistics"]["teams_count"] == 0
        assert result["statistics"]["matches_count"] == 0
        assert result["statistics"]["predictions_count"] == 0
        assert result["statistics"]["active_connections"] == 0

    @pytest.mark.asyncio
    async def test_business_metrics_negative_values(self, mock_db_session):
        """测试业务指标负值 / Test business metrics negative values"""
        mock_db_session.execute.side_effect = [
            Mock(fetchone=Mock(return_value=[-5])),  # 负值
            Mock(fetchone=Mock(return_value=[20])),  # 正常值
            Mock(fetchone=Mock(return_value=[85.5])),  # 正常值
        ]

        result = await _get_business_metrics(mock_db_session)

        assert result["24h_predictions"] == -5  # 负值应保留
        assert result["upcoming_matches_7d"] == 20
        assert result["model_accuracy_30d"] == 85.5

    @patch("src.api.monitoring.psutil.cpu_percent")
    def test_metrics_psutil_exception_handling(self, mock_cpu_percent, mock_db_session):
        """测试psutil异常处理 / Test psutil exception handling"""
        mock_cpu_percent.side_effect = Exception("psutil failed")

        with patch(
            "src.api.monitoring.psutil.virtual_memory"
        ) as mock_virtual_memory, patch(
            "src.api.monitoring.psutil.disk_usage"
        ) as mock_disk_usage, patch(
            "src.api.monitoring._get_database_metrics"
        ) as mock_db_metrics, patch(
            "src.api.monitoring._get_business_metrics"
        ) as mock_biz_metrics:
            # 设置其他mock
            mock_virtual_memory.return_value = Mock(
                total=1000, available=500, percent=50.0, used=500
            )
            mock_disk_usage.return_value = Mock(total=1000, free=500, percent=50.0)
            mock_db_metrics.return_value = {"healthy": True}
            mock_biz_metrics.return_value = {"24h_predictions": 50}

            result = get_metrics(mock_db_session)

            assert result["status"] == "error"
            # 确保即使psutil失败，其他指标仍然返回
            assert "database" in result
            assert "business" in result

    def test_service_status_missing_env_vars(self, mock_db_session):
        """测试缺少环境变量 / Test missing environment variables"""
        with patch("src.api.monitoring.os.getenv", return_value=None), patch(
            "src.api.monitoring.redis.from_url"
        ) as mock_redis_from_url:
            mock_redis_client = Mock()
            mock_redis_client.ping.return_value = True
            mock_redis_from_url.return_value = mock_redis_client

            result = get_service_status(mock_db_session)

            assert result["status"] == "degraded"  # 缺少Redis URL时缓存应不健康
            assert result["services"]["api"] == "healthy"
            assert result["services"]["database"] == "healthy"
            assert result["services"]["cache"] == "unhealthy"


class TestMonitoringIntegration:
    """监控集成测试 / Monitoring Integration Tests"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话 / Mock database session"""
        session = Mock()
        session.execute = Mock()
        return session

    @patch("src.api.monitoring.psutil.cpu_percent")
    @patch("src.api.monitoring.psutil.virtual_memory")
    @patch("src.api.monitoring.psutil.disk_usage")
    @pytest.mark.asyncio
    async def test_metrics_response_structure(
        self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent, mock_db_session
    ):
        """测试指标响应结构 / Test metrics response structure"""
        mock_cpu_percent.return_value = 25.0
        mock_virtual_memory.return_value = Mock(
            total=1000, available=500, percent=50.0, used=500
        )
        mock_disk_usage.return_value = Mock(total=1000, free=500, percent=50.0)

        with patch(
            "src.api.monitoring._get_database_metrics"
        ) as mock_db_metrics, patch(
            "src.api.monitoring._get_business_metrics"
        ) as mock_biz_metrics:
            mock_db_metrics.return_value = {
                "healthy": True,
                "response_time_ms": 10.0,
                "statistics": {"teams_count": 100},
            }
            mock_biz_metrics.return_value = {"24h_predictions": 50}

            result = await get_metrics(mock_db_session)

            # 验证响应结构
            required_fields = [
                "status",
                "response_time_ms",
                "system",
                "database",
                "runtime",
                "business",
            ]
            for field in required_fields:
                assert field in result

            # 验证系统指标结构
            system_fields = ["cpu_percent", "memory", "disk", "load_avg"]
            for field in system_fields:
                assert field in result["system"]

            # 验证数据库指标结构
            db_fields = ["healthy", "statistics"]
            for field in db_fields:
                assert field in result["database"]

            # 验证运行时指标结构
            runtime_fields = ["timestamp", "python_version", "env"]
            for field in runtime_fields:
                assert field in result["runtime"]

    @pytest.mark.asyncio
    async def test_service_status_response_structure(self, mock_db_session):
        """测试服务状态响应结构 / Test service status response structure"""
        with patch(
            "src.api.monitoring.os.getenv", return_value="redis://localhost:6379/0"
        ), patch("src.api.monitoring.redis.from_url") as mock_redis_from_url:
            mock_redis_client = Mock()
            mock_redis_client.ping.return_value = True
            mock_redis_from_url.return_value = mock_redis_client

            result = await get_service_status(mock_db_session)

            # 验证响应结构
            required_fields = ["status", "timestamp", "services"]
            for field in required_fields:
                assert field in result

            # 验证服务状态结构
            services = ["api", "database", "cache"]
            for service in services:
                assert service in result["services"]
                assert result["services"][service] in ["healthy", "unhealthy"]

            # 验证整体状态
            assert result["status"] in ["healthy", "degraded", "unhealthy"]
