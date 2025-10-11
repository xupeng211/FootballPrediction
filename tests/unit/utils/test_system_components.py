"""
测试系统监控组件

验证拆分后的各个系统监控组件的功能。
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from prometheus_client import CollectorRegistry

from src.monitoring.system import (
    ApplicationCollector,
    CacheCollector,
    DatabaseCollector,
    HealthChecker,
    SystemCollector,
    SystemMonitor,
    get_system_monitor,
    record_db_query,
    record_cache_op,
    record_http_request,
    record_prediction,
)
from src.monitoring.system.metrics.system_metrics import SystemMetrics


class TestSystemMetrics:
    """测试系统指标"""

    @pytest.fixture
    def metrics(self):
        """创建指标实例"""
        registry = CollectorRegistry()
        return SystemMetrics(registry)

    def test_metrics_initialization(self, metrics):
        """测试指标初始化"""
        # 检查各种指标是否创建
        assert hasattr(metrics, "system_cpu_percent")
        assert hasattr(metrics, "app_requests_total")
        assert hasattr(metrics, "db_connections_active")
        assert hasattr(metrics, "cache_operations_total")
        assert hasattr(metrics, "business_predictions_total")

    def test_create_counter_with_mock(self, metrics):
        """测试创建Counter指标（使用Mock）"""
        counter = metrics._create_counter("test_counter", "Test counter", ["label"])
        assert counter is not None
        counter.inc.assert_not_called()

    def test_create_gauge_with_mock(self, metrics):
        """测试创建Gauge指标（使用Mock）"""
        gauge = metrics._create_gauge("test_gauge", "Test gauge", ["label"])
        assert gauge is not None
        gauge.set.assert_not_called()

    def test_create_histogram_with_mock(self, metrics):
        """测试创建Histogram指标（使用Mock）"""
        histogram = metrics._create_histogram(
            "test_histogram", "Test histogram", ["label"]
        )
        assert histogram is not None
        histogram.observe.assert_not_called()


class TestSystemCollector:
    """测试系统收集器"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        registry = CollectorRegistry()
        metrics = SystemMetrics(registry)
        return SystemCollector(metrics, time.time())

    @pytest.mark.asyncio
    async def test_collect_metrics(self, collector):
        """测试收集系统指标"""
        with (
            patch("psutil.cpu_percent", return_value=25.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.Process") as mock_process,
        ):
            # 模拟内存信息
            mock_memory.return_value = MagicMock(percent=60.0)
            # 模拟磁盘信息
            mock_disk.return_value = MagicMock(used=50, total=100)
            # 模拟进程信息
            mock_process.return_value = MagicMock(
                memory_info=MagicMock(return_value=MagicMock(rss=1000000)),
                cpu_percent=MagicMock(return_value=15.0),
            )

            metrics_data = await collector.collect()

            assert "cpu_percent" in metrics_data
            assert "memory_percent" in metrics_data
            assert "disk_percent" in metrics_data
            assert metrics_data["cpu_percent"] == 25.0

    def test_get_system_info(self, collector):
        """测试获取系统信息"""
        with (
            patch("psutil.boot_time", return_value=1609459200),
            patch("psutil.cpu_count", side_effect=[8, 16]),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.pids", return_value=[1, 2, 3]),
        ):
            mock_memory.return_value = MagicMock(total=8000000000, available=4000000000)
            mock_disk.return_value = MagicMock(total=100000000000, free=50000000000)

            info = collector.get_system_info()

            assert "cpu_count" in info
            assert "memory_total" in info
            assert "disk_total" in info
            assert "process_count" in info


class TestDatabaseCollector:
    """测试数据库收集器"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        registry = CollectorRegistry()
        metrics = SystemMetrics(registry)
        return DatabaseCollector(metrics)

    @pytest.mark.asyncio
    async def test_record_query(self, collector):
        """测试记录查询"""
        collector.record_query("SELECT", "matches", 0.123)
        collector.record_query("INSERT", "matches", 0.456)
        collector.record_query("SELECT", "matches", 0.789, is_slow=True)

        stats = collector.get_query_stats()

        assert "SELECT.matches" in stats
        assert "INSERT.matches" in stats
        assert stats["SELECT.matches"]["count"] == 2
        assert stats["SELECT.matches"]["slow_queries"] == 1

    @pytest.mark.asyncio
    async def test_test_connection_success(self, collector):
        """测试数据库连接成功"""
        with patch("src.database.connection.get_async_session") as mock_get_session:
            # 模拟成功的会话
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await collector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, collector):
        """测试数据库连接失败"""
        with patch("src.database.connection.get_async_session") as mock_get_session:
            mock_get_session.side_effect = Exception("连接失败")

            result = await collector.test_connection()
            assert result is False


class TestCacheCollector:
    """测试缓存收集器"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        registry = CollectorRegistry()
        metrics = SystemMetrics(registry)
        return CacheCollector(metrics)

    @pytest.mark.asyncio
    async def test_record_operation(self, collector):
        """测试记录缓存操作"""
        collector.record_operation("get", "redis", "hit")
        collector.record_operation("get", "redis", "miss")
        collector.record_operation("set", "redis", "hit")

        stats = collector.get_cache_stats()

        assert stats["total_hits"] == 2
        assert stats["total_misses"] == 1
        assert stats["operations"]["get"]["hit"] == 1
        assert stats["operations"]["get"]["miss"] == 1

    @pytest.mark.asyncio
    async def test_test_connection(self, collector):
        """测试缓存连接"""
        with patch("src.cache.redis_manager.get_redis_manager") as mock_get_manager:
            # 模拟Redis管理器
            mock_manager = AsyncMock()
            mock_manager.ping.return_value = True
            mock_get_manager.return_value = mock_manager

            result = await collector.test_connection()
            assert result is True

            # 检查是否记录了操作
            stats = collector.get_cache_stats()
            assert stats["operations"]["ping"]["hit"] == 1


class TestApplicationCollector:
    """测试应用收集器"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        registry = CollectorRegistry()
        metrics = SystemMetrics(registry)
        return ApplicationCollector(metrics)

    def test_record_request(self, collector):
        """测试记录请求"""
        collector.record_request("GET", "/api/health", 200, 0.123)
        collector.record_request("POST", "/api/predict", 400, 0.456)

        assert len(collector.request_stats) == 2
        assert collector.request_stats[0]["method"] == "GET"
        assert collector.request_stats[0]["status_code"] == 200

    def test_record_prediction(self, collector):
        """测试记录预测"""
        collector.record_prediction("v1.0", "premier_league")
        collector.record_prediction("v1.0", "la_liga")
        collector.record_prediction("v2.0", "premier_league")

        assert len(collector.prediction_stats) == 3
        assert "v1.0.premier_league" in collector.prediction_stats
        assert collector.prediction_stats["v1.0.premier_league"]["count"] == 1

    def test_record_data_collection_job(self, collector):
        """测试记录数据收集任务"""
        collector.record_data_collection_job("football_api", "success")
        collector.record_data_collection_job("weather_api", "failed")

        assert len(collector.data_collection_stats) == 2
        assert collector.data_collection_stats["football_api"]["success"] == 1
        assert collector.data_collection_stats["weather_api"]["failed"] == 1


class TestHealthChecker:
    """测试健康检查器"""

    @pytest.fixture
    def checker(self):
        """创建健康检查器"""
        db_collector = MagicMock()
        cache_collector = MagicMock()
        return HealthChecker(db_collector, cache_collector)

    @pytest.mark.asyncio
    async def test_check_all(self, checker):
        """测试执行所有检查"""
        # 模拟各个检查方法
        checker._check_database = AsyncMock(
            return_value={"status": "healthy", "message": "数据库正常"}
        )
        checker._check_redis = AsyncMock(
            return_value={"status": "healthy", "message": "Redis正常"}
        )
        checker._check_system_resources = AsyncMock(
            return_value={"status": "healthy", "message": "系统资源正常"}
        )
        checker._check_application_health = AsyncMock(
            return_value={"status": "healthy", "message": "应用正常"}
        )
        checker._check_external_services = AsyncMock(
            return_value={"status": "healthy", "message": "外部服务正常"}
        )
        checker._check_data_pipeline = AsyncMock(
            return_value={"status": "healthy", "message": "数据管道正常"}
        )

        report = await checker.check_all()

        assert report["status"] == "healthy"
        assert "checks" in report
        assert "summary" in report
        assert len(report["checks"]) == 6
        assert report["summary"]["passed"] == 6

    @pytest.mark.asyncio
    async def test_check_with_warnings(self, checker):
        """测试包含警告的健康检查"""
        checker._check_database = AsyncMock(
            return_value={"status": "warning", "message": "存在慢查询"}
        )
        checker._check_redis = AsyncMock(
            return_value={"status": "healthy", "message": "Redis正常"}
        )
        checker._check_system_resources = AsyncMock(
            return_value={"status": "healthy", "message": "系统资源正常"}
        )
        checker._check_application_health = AsyncMock(
            return_value={"status": "healthy", "message": "应用正常"}
        )
        checker._check_external_services = AsyncMock(
            return_value={"status": "healthy", "message": "外部服务正常"}
        )
        checker._check_data_pipeline = AsyncMock(
            return_value={"status": "healthy", "message": "数据管道正常"}
        )

        report = await checker.check_all()

        assert report["status"] == "warning"
        assert report["summary"]["warnings"] == 1

    @pytest.mark.asyncio
    async def test_check_database(self, checker):
        """测试数据库检查"""
        checker.database_collector.test_connection = AsyncMock(return_value=True)
        checker.database_collector.get_query_stats = MagicMock(
            return_value={
                "SELECT.matches": {"avg_time": 0.5},
                "INSERT.matches": {"avg_time": 2.0},
            }
        )

        result = await checker._check_database()

        assert result["status"] == "healthy"
        assert "response_time" in result
        assert result["slow_queries"] == 1


class TestSystemMonitor:
    """测试系统监控器"""

    @pytest.fixture
    def monitor(self):
        """创建监控器实例"""
        return SystemMonitor(CollectorRegistry())

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """测试启动和停止监控"""
        assert not monitor.is_monitoring

        # 启动监控
        await monitor.start_monitoring(interval=1)
        assert monitor.is_monitoring is True
        assert monitor.monitor_task is not None

        # 等待一小段时间让监控循环执行
        await asyncio.sleep(0.1)

        # 停止监控
        await monitor.stop_monitoring()
        assert monitor.is_monitoring is False

    def test_record_request(self, monitor):
        """测试记录请求"""
        monitor.record_request("GET", "/test", 200, 0.123)

        stats = monitor.application_collector._get_request_summary()
        assert stats["total_requests"] == 1
        assert stats["status_distribution"] == {200: 1}

    def test_record_database_query(self, monitor):
        """测试记录数据库查询"""
        monitor.record_database_query("SELECT", "matches", 0.123)
        monitor.record_database_query("SELECT", "matches", 0.456, is_slow=True)

        stats = monitor.database_collector.get_query_stats()
        assert "SELECT.matches" in stats
        assert stats["SELECT.matches"]["count"] == 2

    def test_record_cache_operation(self, monitor):
        """测试记录缓存操作"""
        monitor.record_cache_operation("get", "redis", "hit")
        monitor.record_cache_operation("get", "redis", "miss")

        stats = monitor.cache_collector.get_cache_stats()
        assert stats["total_hits"] == 1
        assert stats["total_misses"] == 1

    def test_record_prediction(self, monitor):
        """测试记录预测"""
        monitor.record_prediction("v1.0", "premier_league")
        monitor.record_prediction("v1.0", "la_liga")

        stats = monitor.application_collector._get_prediction_summary()
        assert stats["total_predictions"] == 2

    @pytest.mark.asyncio
    async def test_get_health_status(self, monitor):
        """测试获取健康状态"""
        # 模拟健康检查返回
        with patch.object(monitor.health_checker, "check_all") as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "checks": {},
                "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
            }

            status = await monitor.get_health_status()
            assert status["status"] == "healthy"
            mock_check.assert_called_once()


class TestGlobalFunctions:
    """测试全局便捷函数"""

    def test_get_system_monitor(self):
        """测试获取全局监控器"""
        monitor = get_system_monitor()
        assert isinstance(monitor, SystemMonitor)

        # 再次调用应该返回同一个实例
        monitor2 = get_system_monitor()
        assert monitor is monitor2

    def test_record_functions(self):
        """测试记录函数"""
        # 这些函数应该调用全局监控器
        with patch("src.monitoring.system.get_system_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_get_monitor.return_value = mock_monitor

            record_http_request("GET", "/test", 200, 0.123)
            mock_monitor.record_request.assert_called_once_with(
                "GET", "/test", 200, 0.123
            )

            record_db_query("SELECT", "test", 0.456)
            mock_monitor.record_database_query.assert_called_once_with(
                "SELECT", "test", 0.456, False
            )

            record_cache_op("get", "redis", "hit")
            mock_monitor.record_cache_operation.assert_called_once_with(
                "get", "redis", "hit"
            )

            record_prediction("v1.0", "test")
            mock_monitor.record_prediction.assert_called_once_with("v1.0", "test")

    @pytest.mark.asyncio
    async def test_start_stop_functions(self):
        """测试启动停止函数"""
        with patch("src.monitoring.system.get_system_monitor") as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_monitor.start_monitoring = AsyncMock()
            mock_monitor.stop_monitoring = AsyncMock()
            mock_get_monitor.return_value = mock_monitor

            await start_system_monitoring(interval=10)
            mock_monitor.start_monitoring.assert_called_once_with(10)

            await stop_system_monitoring()
            mock_monitor.stop_monitoring.assert_called_once()
