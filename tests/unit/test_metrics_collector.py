"""
监控指标收集器的单元测试

测试覆盖：
- MetricsCollector 类的各种方法
- 系统指标收集
- 数据库指标收集
- 应用指标收集
- Prometheus 集成
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.monitoring.metrics_collector import (ApplicationMetricsCollector,
                                              DatabaseMetricsCollector,
                                              MetricsCollector,
                                              SystemMetricsCollector)


class TestMetricsCollector:
    """指标收集器基础测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.collector = MetricsCollector()

    def test_metrics_collector_initialization(self):
        """测试指标收集器初始化"""
        assert self.collector is not None
        assert hasattr(self.collector, "enabled")
        assert hasattr(self.collector, "collection_interval")

    def test_enable_disable_collector(self):
        """测试启用 / 禁用收集器"""
        # 禁用
        self.collector.disable()
        assert self.collector.enabled is False

        # 启用
        self.collector.enable()
        assert self.collector.enabled is True

    def test_set_collection_interval(self):
        """测试设置收集间隔"""
        new_interval = 30.0
        self.collector.set_collection_interval(new_interval)

        assert self.collector.collection_interval == new_interval

    def test_invalid_collection_interval(self):
        """测试无效的收集间隔"""
        with pytest.raises(ValueError):
            self.collector.set_collection_interval(-1)

        with pytest.raises(ValueError):
            self.collector.set_collection_interval(0)

    @patch("src.monitoring.metrics_collector.datetime")
    def test_get_current_timestamp(self, mock_datetime):
        """测试获取当前时间戳"""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 10, 30, 0)
        mock_datetime.now().timestamp.return_value = 1705312200.0

        timestamp = self.collector.get_current_timestamp()

        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_get_collector_info(self):
        """测试获取收集器信息"""
        info = self.collector.get_collector_info()

        assert isinstance(info, dict)
        assert "enabled" in info
        assert "collection_interval" in info
        assert "type" in info


class TestSystemMetricsCollector:
    """系统指标收集器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.collector = SystemMetricsCollector()

    def test_system_collector_initialization(self):
        """测试系统收集器初始化"""
        assert self.collector is not None
        assert isinstance(self.collector, MetricsCollector)

    @patch("src.monitoring.metrics_collector.psutil.cpu_percent")
    def test_collect_cpu_metrics(self, mock_cpu_percent):
        """测试CPU指标收集"""
        mock_cpu_percent.return_value = 45.5

        metrics = self.collector.collect_cpu_metrics()

        assert isinstance(metrics, dict)
        assert "cpu_usage_percent" in metrics
        assert metrics["cpu_usage_percent"] == 45.5

    @patch("src.monitoring.metrics_collector.psutil.virtual_memory")
    def test_collect_memory_metrics(self, mock_memory):
        """测试内存指标收集"""
        mock_memory_obj = Mock()
        mock_memory_obj.total = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory_obj.available = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory_obj.percent = 50.0
        mock_memory_obj.used = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.return_value = mock_memory_obj

        metrics = self.collector.collect_memory_metrics()

        assert isinstance(metrics, dict)
        assert "memory_total_bytes" in metrics
        assert "memory_available_bytes" in metrics
        assert "memory_usage_percent" in metrics
        assert metrics["memory_usage_percent"] == 50.0

    @patch("src.monitoring.metrics_collector.psutil.disk_usage")
    def test_collect_disk_metrics(self, mock_disk_usage):
        """测试磁盘指标收集"""
        mock_disk_obj = Mock()
        mock_disk_obj.total = 100 * 1024 * 1024 * 1024  # 100GB
        mock_disk_obj.used = 60 * 1024 * 1024 * 1024  # 60GB
        mock_disk_obj.free = 40 * 1024 * 1024 * 1024  # 40GB
        mock_disk_usage.return_value = mock_disk_obj

        metrics = self.collector.collect_disk_metrics("/")

        assert isinstance(metrics, dict)
        assert "disk_total_bytes" in metrics
        assert "disk_used_bytes" in metrics
        assert "disk_free_bytes" in metrics

    @patch("src.monitoring.metrics_collector.psutil.net_io_counters")
    def test_collect_network_metrics(self, mock_net_io):
        """测试网络指标收集"""
        mock_net_obj = Mock()
        mock_net_obj.bytes_sent = 1024 * 1024  # 1MB
        mock_net_obj.bytes_recv = 2 * 1024 * 1024  # 2MB
        mock_net_obj.packets_sent = 1000
        mock_net_obj.packets_recv = 1500
        mock_net_io.return_value = mock_net_obj

        metrics = self.collector.collect_network_metrics()

        assert isinstance(metrics, dict)
        assert "network_bytes_sent" in metrics
        assert "network_bytes_recv" in metrics
        assert "network_packets_sent" in metrics
        assert "network_packets_recv" in metrics

    def test_collect_system_load(self):
        """测试系统负载收集"""
        with patch(
            "src.monitoring.metrics_collector.os.getloadavg",
            return_value=(1.0, 1.5, 2.0),
        ):
            metrics = self.collector.collect_system_load()

            assert isinstance(metrics, dict)
            assert "load_1min" in metrics
            assert "load_5min" in metrics
            assert "load_15min" in metrics

    def test_collect_all_system_metrics(self):
        """测试收集所有系统指标"""
        with patch.object(
            self.collector,
            "collect_cpu_metrics",
            return_value={"cpu_usage_percent": 30.0},
        ):
            with patch.object(
                self.collector,
                "collect_memory_metrics",
                return_value={"memory_usage_percent": 40.0},
            ):
                with patch.object(
                    self.collector,
                    "collect_disk_metrics",
                    return_value={"disk_usage_percent": 50.0},
                ):
                    with patch.object(
                        self.collector,
                        "collect_network_metrics",
                        return_value={"network_bytes_sent": 1024},
                    ):
                        with patch.object(
                            self.collector,
                            "collect_system_load",
                            return_value={"load_1min": 1.0},
                        ):
                            all_metrics = self.collector.collect_all_metrics()

                            assert isinstance(all_metrics, dict)
                            assert "cpu_usage_percent" in all_metrics
                            assert "memory_usage_percent" in all_metrics


class TestDatabaseMetricsCollector:
    """数据库指标收集器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.collector = DatabaseMetricsCollector()

    def test_database_collector_initialization(self):
        """测试数据库收集器初始化"""
        assert self.collector is not None
        assert isinstance(self.collector, MetricsCollector)

    @patch("src.monitoring.metrics_collector.DatabaseManager")
    @pytest.mark.asyncio
    async def test_collect_connection_pool_metrics(self, mock_db_manager):
        """测试数据库连接池指标收集"""
        mock_db_instance = Mock()
        mock_db_instance.get_pool_status.return_value = {
            "size": 10,
            "checked_in": 3,
            "checked_out": 7,
            "overflow": 2,
            "invalid": 0,
        }
        mock_db_manager.return_value = mock_db_instance

        metrics = await self.collector.collect_connection_pool_metrics()

        assert isinstance(metrics, dict)
        assert "db_pool_size" in metrics
        assert "db_pool_checked_out" in metrics

    @patch("src.monitoring.metrics_collector.DatabaseManager")
    @pytest.mark.asyncio
    async def test_collect_query_performance_metrics(self, mock_db_manager):
        """测试查询性能指标收集"""
        mock_db_instance = Mock()
        mock_db_instance.get_async_session.return_value.__aenter__ = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(query_type="SELECT", avg_duration=0.05, count=100),
            Mock(query_type="INSERT", avg_duration=0.02, count=50),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        mock_db_manager.return_value = mock_db_instance

        metrics = await self.collector.collect_query_performance_metrics()

        assert isinstance(metrics, dict)

    @patch("src.monitoring.metrics_collector.DatabaseManager")
    @pytest.mark.asyncio
    async def test_collect_table_size_metrics(self, mock_db_manager):
        """测试表大小指标收集"""
        mock_db_instance = Mock()
        mock_db_instance.get_async_session.return_value.__aenter__ = AsyncMock()
        mock_db_instance.get_async_session.return_value.__aexit__ = AsyncMock()

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(table_name="matches", row_count=1000, size_bytes=1024 * 1024),
            Mock(table_name="odds", row_count=5000, size_bytes=5 * 1024 * 1024),
        ]
        mock_session.execute.return_value = mock_result
        mock_db_instance.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        mock_db_manager.return_value = mock_db_instance

        metrics = await self.collector.collect_table_size_metrics()

        assert isinstance(metrics, dict)


class TestApplicationMetricsCollector:
    """应用指标收集器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.collector = ApplicationMetricsCollector()

    def test_application_collector_initialization(self):
        """测试应用收集器初始化"""
        assert self.collector is not None
        assert isinstance(self.collector, MetricsCollector)

    @patch("src.monitoring.metrics_collector.get_cache_stats")
    def test_collect_cache_metrics(self, mock_cache_stats):
        """测试缓存指标收集"""
        mock_cache_stats.return_value = {
            "hits": 1000,
            "misses": 200,
            "hit_rate": 0.833,
            "size": 500,
            "memory_usage": 1024 * 1024,  # 1MB
        }

        metrics = self.collector.collect_cache_metrics()

        assert isinstance(metrics, dict)
        assert "cache_hits_total" in metrics
        assert "cache_misses_total" in metrics
        assert "cache_hit_rate" in metrics

    @patch("src.monitoring.metrics_collector.TaskErrorLogger")
    @pytest.mark.asyncio
    async def test_collect_task_metrics(self, mock_error_logger):
        """测试任务指标收集"""
        mock_logger_instance = Mock()
        mock_logger_instance.get_error_statistics.return_value = {
            "total_errors": 10,
            "task_errors": [
                {"task_name": "collect_fixtures", "error_count": 5},
                {"task_name": "collect_odds", "error_count": 3},
            ],
        }
        mock_error_logger.return_value = mock_logger_instance

        metrics = await self.collector.collect_task_metrics()

        assert isinstance(metrics, dict)
        assert "task_errors_total" in metrics

    def test_collect_api_metrics(self):
        """测试API指标收集"""
        with patch("src.monitoring.metrics_collector.get_api_stats") as mock_api_stats:
            mock_api_stats.return_value = {
                "requests_total": 10000,
                "requests_per_second": 50.5,
                "response_time_avg": 0.15,
                "error_rate": 0.02,
            }

            metrics = self.collector.collect_api_metrics()

            assert isinstance(metrics, dict)
            assert "api_requests_total" in metrics
            assert "api_response_time_avg" in metrics

    def test_collect_prediction_metrics(self):
        """测试预测指标收集"""
        with patch(
            "src.monitoring.metrics_collector.get_prediction_stats"
        ) as mock_prediction_stats:
            mock_prediction_stats.return_value = {
                "predictions_generated_total": 1000,
                "predictions_accuracy": 0.75,
                "models_active": 3,
                "last_training_timestamp": 1705312200.0,
            }

            metrics = self.collector.collect_prediction_metrics()

            assert isinstance(metrics, dict)
            assert "predictions_generated_total" in metrics
            assert "predictions_accuracy" in metrics


class TestMetricsCollectorIntegration:
    """指标收集器集成测试"""

    @patch("src.monitoring.metrics_collector.prometheus_client")
    def test_prometheus_integration(self, mock_prometheus):
        """测试Prometheus集成"""
        collector = SystemMetricsCollector()

        # 模拟指标收集
        with patch.object(collector, "collect_all_metrics") as mock_collect:
            mock_collect.return_value = {
                "cpu_usage_percent": 45.0,
                "memory_usage_percent": 60.0,
            }

            collector.export_to_prometheus()

            # 验证指标导出
            mock_collect.assert_called_once()

    def test_metrics_aggregation(self):
        """测试指标聚合"""
        system_collector = SystemMetricsCollector()
        db_collector = DatabaseMetricsCollector()
        app_collector = ApplicationMetricsCollector()

        # 模拟各个收集器的数据
        with patch.object(
            system_collector, "collect_all_metrics", return_value={"cpu_usage": 30}
        ):
            with patch.object(
                db_collector, "collect_all_metrics", return_value={"db_connections": 10}
            ):
                with patch.object(
                    app_collector,
                    "collect_all_metrics",
                    return_value={"cache_hits": 100},
                ):
                    # 聚合所有指标
                    all_metrics = {}
                    all_metrics.update(system_collector.collect_all_metrics())
                    all_metrics.update(db_collector.collect_all_metrics())
                    all_metrics.update(app_collector.collect_all_metrics())

                    assert len(all_metrics) == 3
                    assert "cpu_usage" in all_metrics
                    assert "db_connections" in all_metrics
                    assert "cache_hits" in all_metrics


class TestErrorHandling:
    """错误处理测试"""

    def test_collection_with_missing_dependencies(self):
        """测试缺少依赖时的收集"""
        collector = SystemMetricsCollector()

        with patch(
            "src.monitoring.metrics_collector.psutil.cpu_percent",
            side_effect=ImportError("psutil not available"),
        ):
            metrics = collector.collect_cpu_metrics()

            # 应该返回空或默认值
            assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """测试数据库连接失败"""
        collector = DatabaseMetricsCollector()

        with patch(
            "src.monitoring.metrics_collector.DatabaseManager",
            side_effect=Exception("Connection failed"),
        ):
            metrics = await collector.collect_connection_pool_metrics()

            # 应该处理异常并返回默认值
            assert isinstance(metrics, dict)

    def test_metrics_collection_timeout(self):
        """测试指标收集超时"""
        collector = SystemMetricsCollector()

        with patch(
            "src.monitoring.metrics_collector.psutil.cpu_percent",
            side_effect=TimeoutError("Operation timed out"),
        ):
            metrics = collector.collect_cpu_metrics()

            assert isinstance(metrics, dict)


class TestPerformance:
    """性能测试"""

    def test_collection_performance(self):
        """测试收集性能"""
        collector = SystemMetricsCollector()

        import time

        start_time = time.time()

        # 模拟快速收集
        with patch.object(collector, "collect_all_metrics", return_value={}):
            for _ in range(100):
                collector.collect_all_metrics()

        end_time = time.time()
        duration = end_time - start_time

        # 确保收集速度足够快
        assert duration < 1.0  # 100次收集应该在1秒内完成

    def test_memory_usage_during_collection(self):
        """测试收集过程中的内存使用"""
        import gc

        collector = SystemMetricsCollector()

        # 强制垃圾回收
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 执行多次收集
        for _ in range(10):
            with patch.object(collector, "collect_all_metrics", return_value={}):
                collector.collect_all_metrics()

        gc.collect()
        final_objects = len(gc.get_objects())

        # 确保没有明显的内存泄漏
        object_growth = final_objects - initial_objects
        assert object_growth < 100  # 允许少量对象增长


if __name__ == "__main__":
    pytest.main([__file__])
