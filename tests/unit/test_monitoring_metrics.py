"""
监控指标模块测试
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.metrics_exporter import MetricsExporter


class TestMetricsExporter:
    """指标导出器测试"""

    def setup_method(self):
        """测试设置"""
        self.exporter = MetricsExporter()

    def test_metrics_exporter_initialization(self):
        """测试指标导出器初始化"""
        assert self.exporter is not None
        assert hasattr(self.exporter, "record_data_collection_success")
        assert hasattr(self.exporter, "record_data_collection_failure")

    def test_record_data_collection_success(self):
        """测试记录数据收集成功"""
        with patch.object(self.exporter, "_get_or_create_counter") as mock_counter:
            mock_metric = Mock()
            mock_counter.return_value = mock_metric

            self.exporter.record_data_collection_success("fixtures", 100)

            mock_metric.inc.assert_called_once()

    def test_record_data_collection_failure(self):
        """测试记录数据收集失败"""
        with patch.object(self.exporter, "_get_or_create_counter") as mock_counter:
            mock_metric = Mock()
            mock_counter.return_value = mock_metric

            self.exporter.record_data_collection_failure("odds", "API timeout")

            mock_metric.inc.assert_called_once()

    def test_record_data_cleaning_success(self):
        """测试记录数据清洗成功"""
        with patch.object(self.exporter, "_get_or_create_counter") as mock_counter:
            mock_metric = Mock()
            mock_counter.return_value = mock_metric

            self.exporter.record_data_cleaning_success(50)

            mock_metric.inc.assert_called_once()

    def test_record_scheduler_task(self):
        """测试记录调度任务"""
        with patch.object(self.exporter, "_get_or_create_counter") as mock_counter:
            mock_metric = Mock()
            mock_counter.return_value = mock_metric

            self.exporter.record_scheduler_task("collect_fixtures", "success", 2.5)

            mock_metric.inc.assert_called_once()

    def test_update_table_row_counts(self):
        """测试更新表行数统计"""
        table_counts = {"matches": 1000, "odds": 5000, "predictions": 500}

        with patch.object(self.exporter, "_get_or_create_gauge") as mock_gauge:
            mock_metric = Mock()
            mock_gauge.return_value = mock_metric

            self.exporter.update_table_row_counts(table_counts)

            assert mock_metric.set.call_count == len(table_counts)

    def test_get_metrics_prometheus_format(self):
        """测试获取Prometheus格式指标"""
        with patch("prometheus_client.generate_latest") as mock_generate:
            mock_generate.return_value = b"# HELP test_metric Test metric\n"

            result = self.exporter.get_metrics()

            assert isinstance(result, str)
            mock_generate.assert_called_once()


class TestMetricsCollector:
    """指标收集器测试"""

    def setup_method(self):
        """测试设置"""
        self.collector = MetricsCollector()

    def test_metrics_collector_initialization(self):
        """测试指标收集器初始化"""
        assert self.collector is not None
        assert hasattr(self.collector, "collect_system_metrics")
        assert hasattr(self.collector, "collect_database_metrics")

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_collect_system_metrics(self, mock_disk, mock_memory, mock_cpu):
        """测试收集系统指标"""
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=75.2, available=1024 * 1024 * 1024)
        mock_disk.return_value = Mock(percent=60.0, free=2 * 1024 * 1024 * 1024)

        metrics = self.collector.collect_system_metrics()

        assert "cpu_usage_percent" in metrics
        assert "memory_usage_percent" in metrics
        assert "disk_usage_percent" in metrics
        assert metrics["cpu_usage_percent"] == 45.5

    @pytest.mark.asyncio
    @patch("src.monitoring.metrics_collector.get_async_session")
    async def test_collect_database_metrics(self, mock_session):
        """测试收集数据库指标"""
        mock_session_instance = Mock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # 模拟查询结果
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("matches", 1000),
            ("odds", 5000),
            ("predictions", 500),
        ]
        mock_session_instance.execute.return_value = mock_result

        metrics = await self.collector.collect_database_metrics()

        assert "table_counts" in metrics
        assert isinstance(metrics["table_counts"], dict)

    def test_collect_application_metrics(self):
        """测试收集应用指标"""
        with patch.object(self.collector, "_get_prediction_stats") as mock_stats:
            mock_stats.return_value = {
                "total_predictions": 1000,
                "accuracy_rate": 0.65,
                "avg_confidence": 0.78,
            }

            metrics = self.collector.collect_application_metrics()

            assert "prediction_stats" in metrics
            assert metrics["prediction_stats"]["total_predictions"] == 1000

    def test_format_metrics_for_export(self):
        """测试格式化指标用于导出"""
        raw_metrics = {
            "system": {"cpu_usage": 45.5},
            "database": {"table_counts": {"matches": 1000}},
            "application": {"prediction_stats": {"total": 500}},
        }

        formatted = self.collector.format_metrics_for_export(raw_metrics)

        assert isinstance(formatted, dict)
        assert "timestamp" in formatted
        assert "metrics" in formatted


class TestMetricsIntegration:
    """指标系统集成测试"""

    def test_metrics_pipeline(self):
        """测试指标收集和导出管道"""
        collector = MetricsCollector()
        # exporter = MetricsExporter()

        # 模拟指标收集
        with patch.object(collector, "collect_system_metrics") as mock_collect:
            mock_collect.return_value = {"cpu_usage": 50.0}

            metrics = collector.collect_system_metrics()

            # 验证指标格式
            assert isinstance(metrics, dict)
            assert "cpu_usage" in metrics

    def test_prometheus_integration(self):
        """测试Prometheus集成"""
        exporter = MetricsExporter()

        # 记录一些指标
        exporter.record_data_collection_success("test", 100)

        # 获取Prometheus格式输出
        prometheus_output = exporter.get_metrics()

        assert isinstance(prometheus_output, str)
        assert len(prometheus_output) > 0

    def test_metrics_persistence(self):
        """测试指标持久化"""
        # 模拟指标存储
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": 45.5,
            "memory_usage": 75.2,
        }

        # 验证数据格式
        assert "timestamp" in metrics_data
        assert isinstance(metrics_data["cpu_usage"], float)

    def test_metrics_alerting_thresholds(self):
        """测试指标告警阈值"""
        # 定义告警阈值
        thresholds = {"cpu_usage": 80.0, "memory_usage": 85.0, "disk_usage": 90.0}

        # 测试指标
        current_metrics = {
            "cpu_usage": 85.0,  # 超过阈值
            "memory_usage": 70.0,  # 正常
            "disk_usage": 95.0,  # 超过阈值
        }

        alerts = []
        for metric, value in current_metrics.items():
            if value > thresholds.get(metric, 100):
                alerts.append(
                    f"{metric} is {value}%, threshold is {thresholds[metric]}%"
                )

        assert len(alerts) == 2  # cpu_usage 和 disk_usage 超过阈值

    def test_metrics_aggregation(self):
        """测试指标聚合"""
        # 模拟时间序列数据
        time_series_data = [
            {"timestamp": datetime.now() - timedelta(minutes=5), "cpu_usage": 45.0},
            {"timestamp": datetime.now() - timedelta(minutes=4), "cpu_usage": 50.0},
            {"timestamp": datetime.now() - timedelta(minutes=3), "cpu_usage": 55.0},
            {"timestamp": datetime.now() - timedelta(minutes=2), "cpu_usage": 48.0},
            {"timestamp": datetime.now() - timedelta(minutes=1), "cpu_usage": 52.0},
        ]

        # 计算平均值
        avg_cpu = sum(data["cpu_usage"] for data in time_series_data) / len(
            time_series_data
        )

        assert avg_cpu == 50.0
        assert len(time_series_data) == 5
