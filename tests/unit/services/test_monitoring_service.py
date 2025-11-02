"""监控服务测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import time
from datetime import datetime, timedelta
from src.monitoring.system_monitor import SystemMonitor
from src.monitoring.metrics_collector import MetricsCollector

class TestSystemMonitor:
    """系统监控测试"""

    @pytest.fixture
    def mock_metrics_collector(self):
        """模拟指标收集器"""
        collector = Mock(spec=MetricsCollector)
        collector.collect_cpu_usage.return_value = 45.5
        collector.collect_memory_usage.return_value = 68.2
        collector.collect_disk_usage.return_value = 32.1
        return collector

    @pytest.fixture
    def monitor(self, mock_metrics_collector):
        """创建系统监控器"""
        return SystemMonitor(metrics_collector=mock_metrics_collector)

    def test_get_system_metrics(self, monitor, mock_metrics_collector):
        """测试获取系统指标"""
        # 调用方法
        metrics = monitor.get_system_metrics()

        # 验证
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_usage" in metrics
        assert metrics["cpu_usage"] == 45.5

    def test_health_check(self, monitor):
        """测试健康检查"""
        # 设置模拟返回
        with patch('monitor.database_check') as mock_db,              patch('monitor.redis_check') as mock_redis:
            mock_db.return_value = {"status": "healthy", "response_time": 10}
            mock_redis.return_value = {"status": "healthy", "response_time": 5}

            # 调用方法
            health = monitor.check_health()

            # 验证
            assert health["overall_status"] == "healthy"
            assert "checks" in health
            assert len(health["checks"]) == 2

    def test_performance_monitoring(self, monitor):
        """测试性能监控"""
        # 准备测试数据
        start_time = time.time()
        time.sleep(0.01)  # 模拟操作
        end_time = time.time()

        # 调用方法
        performance = monitor.measure_performance(start_time, end_time)

        # 验证
        assert "duration_ms" in performance
        assert performance["duration_ms"] > 0

    def test_alert_threshold_check(self, monitor):
        """测试告警阈值检查"""
        # 设置高CPU使用率
        monitor.metrics_collector.collect_cpu_usage.return_value = 95.0

        # 调用方法
        alerts = monitor.check_alerts()

        # 验证
        assert len(alerts) > 0
        assert any(alert["type"] == "high_cpu" for alert in alerts)

    def test_log_anomaly_detection(self, monitor):
        """测试日志异常检测"""
        # 准备异常日志
        logs = [
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "ERROR", "message": "Database connection failed"}
        ]

        # 调用方法
        anomalies = monitor.detect_log_anomalies(logs)

        # 验证
        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "repeated_errors"

    def test_api_endpoint_monitoring(self, monitor):
        """测试API端点监控"""
        # 准备API指标
        api_metrics = {
            "/api/predictions": {
                "requests": 1000,
                "errors": 10,
                "avg_response_time": 120
            },
            "/api/matches": {
                "requests": 500,
                "errors": 5,
                "avg_response_time": 80
            }
        }

        # 调用方法
        health = monitor.check_api_health(api_metrics)

        # 验证
        assert "/api/predictions" in health
        assert health["/api/predictions"]["status"] in ["healthy", "degraded", "unhealthy"]

    def test_resource_usage_trend(self, monitor):
        """测试资源使用趋势"""
        # 准备历史数据
        historical_data = [
            {"timestamp": datetime.now() - timedelta(hours=1), "cpu": 30},
            {"timestamp": datetime.now() - timedelta(minutes=30), "cpu": 45},
            {"timestamp": datetime.now(), "cpu": 60}
        ]

        # 调用方法
        trend = monitor.analyze_resource_trend(historical_data)

        # 验证
        assert "direction" in trend  # up/down/stable
        assert "rate" in trend
        assert trend["direction"] == "up"

    def test_generate_monitoring_report(self, monitor):
        """测试生成监控报告"""
        # 设置模拟数据
        with patch.object(monitor, 'get_system_metrics') as mock_metrics,              patch.object(monitor, 'check_health') as mock_health:
            mock_metrics.return_value = {"cpu": 50, "memory": 60}
            mock_health.return_value = {"status": "healthy"}

            # 调用方法
            report = monitor.generate_report()

            # 验证
            assert "system_metrics" in report
            assert "health_status" in report
            assert "timestamp" in report
            assert report["health_status"]["status"] == "healthy"


class TestMetricsCollector:
    """指标收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建指标收集器"""
        return MetricsCollector()

    def test_collect_cpu_usage(self, collector):
        """测试收集CPU使用率"""
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.return_value = 45.5

            # 调用方法
            cpu_usage = collector.collect_cpu_usage()

            # 验证
            assert isinstance(cpu_usage, (int, float))
            assert 0 <= cpu_usage <= 100

    def test_collect_memory_usage(self, collector):
        """测试收集内存使用率"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 68.2
            mock_memory.return_value = mock_memory_obj

            # 调用方法
            memory_usage = collector.collect_memory_usage()

            # 验证
            assert isinstance(memory_usage, (int, float))
            assert 0 <= memory_usage <= 100

    def test_collect_disk_usage(self, collector):
        """测试收集磁盘使用率"""
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk_obj = Mock()
            mock_disk_obj.percent = 32.1
            mock_disk.return_value = mock_disk_obj

            # 调用方法
            disk_usage = collector.collect_disk_usage()

            # 验证
            assert isinstance(disk_usage, (int, float))
            assert 0 <= disk_usage <= 100

    def test_collect_network_stats(self, collector):
        """测试收集网络统计"""
        with patch('psutil.net_io_counters') as mock_net:
            mock_net_obj = Mock()
            mock_net_obj.bytes_sent = 1000000
            mock_net_obj.bytes_recv = 2000000
            mock_net.return_value = mock_net_obj

            # 调用方法
            net_stats = collector.collect_network_stats()

            # 验证
            assert "bytes_sent" in net_stats
            assert "bytes_recv" in net_stats
            assert net_stats["bytes_sent"] == 1000000

    def test_collect_process_count(self, collector):
        """测试收集进程数量"""
        with patch('psutil.pids') as mock_pids:
            mock_pids.return_value = [1, 2, 3, 4, 5]

            # 调用方法
            process_count = collector.collect_process_count()

            # 验证
            assert process_count == 5

    def test_collect_active_connections(self, collector):
        """测试收集活动连接数"""
        with patch('psutil.net_connections') as mock_connections:
            mock_connections.return_value = [Mock() for _ in range(10)]

            # 调用方法
            connections = collector.collect_active_connections()

            # 验证
            assert connections == 10

    def test_collect_system_load(self, collector):
        """测试收集系统负载"""
        with patch('os.getloadavg') as mock_loadavg:
            mock_loadavg.return_value = (1.0, 1.5, 2.0)

            # 调用方法
            load = collector.collect_system_load()

            # 验证
            assert "1min" in load
            assert "5min" in load
            assert "15min" in load
            assert load["1min"] == 1.0

    def test_collect_all_metrics(self, collector):
        """测试收集所有指标"""
        with patch.object(collector, 'collect_cpu_usage', return_value=50),              patch.object(collector, 'collect_memory_usage', return_value=60),              patch.object(collector, 'collect_disk_usage', return_value=30):

            # 调用方法
            metrics = collector.collect_all()

            # 验证
            assert "cpu" in metrics
            assert "memory" in metrics
            assert "disk" in metrics
            assert "timestamp" in metrics
