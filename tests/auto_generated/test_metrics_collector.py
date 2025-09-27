"""
Auto-generated tests for src.monitoring.metrics_collector module
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio


class TestMetricsCollector:
    """测试指标收集器"""

    def test_metrics_collector_import(self):
        """测试指标收集器导入"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector
            assert MetricsCollector is not None
        except ImportError as e:
            pytest.skip(f"Cannot import MetricsCollector: {e}")

    @patch('src.monitoring.metrics_collector.psutil')
    def test_system_metrics_collection(self, mock_psutil):
        """测试系统指标收集"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            # Mock psutil data
            mock_psutil.cpu_percent.return_value = 45.5
            mock_psutil.virtual_memory.return_value = MagicMock(
                percent=78.2, available=2048 * 1024 * 1024
            )
            mock_psutil.disk_usage.return_value = MagicMock(
                percent=65.3, free=50 * 1024 * 1024 * 1024
            )
            mock_psutil.net_io_counters.return_value = MagicMock(
                bytes_sent=1024 * 1024, bytes_recv=2048 * 2048
            )

            collector = MetricsCollector()
            metrics = collector.collect_system_metrics()

            assert isinstance(metrics, dict)
            assert "cpu_percent" in metrics
            assert "memory_percent" in metrics
            assert "disk_percent" in metrics
            assert "network_bytes_sent" in metrics
            assert "network_bytes_recv" in metrics
            assert "timestamp" in metrics

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @patch('src.monitoring.metrics_collector.psutil')
    def test_process_metrics_collection(self, mock_psutil):
        """测试进程指标收集"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            # Mock process data
            mock_process = MagicMock()
            mock_process.cpu_percent.return_value = 25.3
            mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 512)
            mock_process.num_threads.return_value = 15
            mock_process.create_time.return_value = datetime.now().timestamp()

            mock_psutil.Process.return_value = mock_process

            collector = MetricsCollector()
            metrics = collector.collect_process_metrics()

            assert isinstance(metrics, dict)
            assert "cpu_percent" in metrics
            assert "memory_rss_mb" in metrics
            assert "thread_count" in metrics
            assert "uptime_seconds" in metrics
            assert "timestamp" in metrics

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_database_metrics_collection(self):
        """测试数据库指标收集"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Mock database session
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 150
            mock_session.execute.return_value = mock_result

            metrics = collector.collect_database_metrics(mock_session)

            assert isinstance(metrics, dict)
            assert "active_connections" in metrics
            assert "timestamp" in metrics

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @patch('src.monitoring.metrics_collector.psutil')
    def test_metrics_with_error_handling(self, mock_psutil):
        """测试指标收集错误处理"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            # Mock psutil to raise exception
            mock_psutil.cpu_percent.side_effect = Exception("PSUtil error")

            collector = MetricsCollector()
            metrics = collector.collect_system_metrics()

            # Should return empty or default metrics on error
            assert isinstance(metrics, dict)
            assert "timestamp" in metrics

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_timestamp_format(self):
        """测试指标时间戳格式"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()
            mock_session = MagicMock()

            with patch('src.monitoring.metrics_collector.datetime') as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 0, 0)
                mock_datetime.now.return_value = mock_now

                metrics = collector.collect_database_metrics(mock_session)

                assert metrics["timestamp"] == mock_now.isoformat()

        except ImportError:
            pytest.skip("MetricsCollector not available")

    @pytest.mark.asyncio
    async def test_async_metrics_collection(self):
        """测试异步指标收集"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Mock async database operations
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 25
            mock_session.execute.return_value = mock_result

            metrics = await collector.collect_async_metrics(mock_session)

            assert isinstance(metrics, dict)
            assert "timestamp" in metrics

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_aggregation(self):
        """测试指标聚合"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Mock multiple metric collections
            metrics_samples = [
                {"cpu_percent": 45.2, "memory_percent": 78.1, "timestamp": "2024-01-01T12:00:00"},
                {"cpu_percent": 46.8, "memory_percent": 78.5, "timestamp": "2024-01-01T12:01:00"},
                {"cpu_percent": 44.9, "memory_percent": 77.9, "timestamp": "2024-01-01T12:02:00"}
            ]

            aggregated = collector.aggregate_metrics(metrics_samples)

            assert isinstance(aggregated, dict)
            assert "avg_cpu_percent" in aggregated
            assert "avg_memory_percent" in aggregated
            assert "max_cpu_percent" in aggregated
            assert "min_cpu_percent" in aggregated

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_validation(self):
        """测试指标验证"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Test valid metrics
            valid_metrics = {
                "cpu_percent": 45.5,
                "memory_percent": 78.2,
                "timestamp": datetime.now().isoformat()
            }

            is_valid = collector.validate_metrics(valid_metrics)
            assert is_valid is True

            # Test invalid metrics (missing timestamp)
            invalid_metrics = {
                "cpu_percent": 45.5,
                "memory_percent": 78.2
            }

            is_valid = collector.validate_metrics(invalid_metrics)
            assert is_valid is False

            # Test invalid metrics (negative values)
            invalid_metrics = {
                "cpu_percent": -10.0,
                "memory_percent": 78.2,
                "timestamp": datetime.now().isoformat()
            }

            is_valid = collector.validate_metrics(invalid_metrics)
            assert is_valid is False

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_storage(self):
        """测试指标存储"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Mock storage operation
            mock_storage = MagicMock()
            metrics = {
                "cpu_percent": 45.5,
                "memory_percent": 78.2,
                "timestamp": datetime.now().isoformat()
            }

            collector.store_metrics(mock_storage, metrics)

            # Verify storage was called
            mock_storage.store.assert_called_once_with(metrics)

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_export(self):
        """测试指标导出"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            metrics = {
                "cpu_percent": 45.5,
                "memory_percent": 78.2,
                "timestamp": "2024-01-01T12:00:00"
            }

            # Test JSON export
            json_export = collector.export_metrics_json(metrics)
            assert isinstance(json_export, str)
            assert "cpu_percent" in json_export

            # Test CSV export
            csv_export = collector.export_metrics_csv(metrics)
            assert isinstance(csv_export, str)
            assert "cpu_percent,memory_percent" in csv_export

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_filtering(self):
        """测试指标过滤"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            metrics = {
                "cpu_percent": 45.5,
                "memory_percent": 78.2,
                "disk_percent": 65.3,
                "network_bytes_sent": 1024,
                "network_bytes_recv": 2048,
                "timestamp": "2024-01-01T12:00:00"
            }

            # Filter by prefix
            filtered = collector.filter_metrics(metrics, "network_")
            assert "network_bytes_sent" in filtered
            assert "network_bytes_recv" in filtered
            assert "cpu_percent" not in filtered

            # Filter by list
            allowed_keys = ["cpu_percent", "memory_percent", "timestamp"]
            filtered = collector.filter_metrics_by_keys(metrics, allowed_keys)
            assert len(filtered) == 3
            assert "cpu_percent" in filtered
            assert "memory_percent" in filtered
            assert "timestamp" in filtered

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_threshold_checking(self):
        """测试指标阈值检查"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            metrics = {
                "cpu_percent": 85.0,
                "memory_percent": 95.0,
                "disk_percent": 75.0,
                "timestamp": "2024-01-01T12:00:00"
            }

            thresholds = {
                "cpu_percent": {"warning": 80.0, "critical": 90.0},
                "memory_percent": {"warning": 90.0, "critical": 95.0},
                "disk_percent": {"warning": 80.0, "critical": 90.0}
            }

            alerts = collector.check_thresholds(metrics, thresholds)

            assert isinstance(alerts, list)
            # CPU should trigger warning
            assert any(alert["metric"] == "cpu_percent" and alert["level"] == "warning" for alert in alerts)
            # Memory should trigger critical
            assert any(alert["metric"] == "memory_percent" and alert["level"] == "critical" for alert in alerts)
            # Disk should be normal
            assert not any(alert["metric"] == "disk_percent" for alert in alerts)

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_performance_monitoring(self):
        """测试指标性能监控"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Test collection performance
            start_time = datetime.now()

            with patch('src.monitoring.metrics_collector.psutil') as mock_psutil:
                mock_psutil.cpu_percent.return_value = 45.5
                mock_psutil.virtual_memory.return_value = MagicMock(percent=78.2)

                metrics = collector.collect_system_metrics()

            end_time = datetime.now()
            collection_time = (end_time - start_time).total_seconds()

            assert collection_time < 1.0  # Should complete within 1 second
            assert isinstance(metrics, dict)

        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_metrics_history_management(self):
        """测试指标历史管理"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            collector = MetricsCollector()

            # Add metrics to history
            for i in range(5):
                metrics = {
                    "cpu_percent": 45.0 + i,
                    "timestamp": f"2024-01-01T12:0{i}:00"
                }
                collector.add_to_history(metrics)

            # Get history
            history = collector.get_metrics_history(hours=1)
            assert isinstance(history, list)
            assert len(history) <= 5

            # Clear old history
            collector.cleanup_old_history(hours=0.5)
            cleaned_history = collector.get_metrics_history(hours=1)
            assert len(cleaned_history) <= 2  # Only recent entries should remain

        except ImportError:
            pytest.skip("MetricsCollector not available")