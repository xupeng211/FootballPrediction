"""
import typing
from datetime import datetime, timedelta
import asyncio
测试监控指标导出器
"""

from datetime import datetime, timedelta

import pytest
from prometheus_client import CollectorRegistry

from src.monitoring.metrics_exporter import MetricsExporter

pytestmark = pytest.mark.unit


class TestMetricsExporter:
    """
    MetricsExporter 基础测试

    每个测试使用独立的 CollectorRegistry 实例，确保测试间的隔离，
    避免 Prometheus 指标的全局状态污染问题。
    """

    def setup_method(self):
        """
        每个测试方法前的设置

        创建独立的 CollectorRegistry 实例用于测试，避免与全局注册表冲突。
        这确保每个测试都有干净的指标环境。
        """
        # 使用独立的注册表实例，避免全局状态污染
        self.test_registry = CollectorRegistry()
        self.exporter = MetricsExporter(registry=self.test_registry)

    def test_init_creates_all_metrics(self):
        """测试初始化时创建所有指标"""
        assert self.exporter.data_collection_total is not None
        assert self.exporter.data_collection_errors is not None
        assert self.exporter.data_cleaning_total is not None
        assert self.exporter.scheduler_task_delay is not None
        assert self.exporter.table_row_count is not None  # 修正属性名

    def test_record_data_collection_success(self):
        """测试记录数据采集成功"""
        # 记录一次成功的数据采集
        self.exporter.record_data_collection(
            data_source="test_api",
            collection_type="fixtures",
            success=True,
            duration=10.5,
        )

        # 获取指标数据
        headers, data = self.exporter.get_metrics()
        metrics_data = data  # data 已经是字符串类型，不需要decode

        # 验证指标被正确设置
        assert "football_data_collection_total" in metrics_data
        assert "test_api" in metrics_data  # 修正：应该检查实际使用的data_source

    def test_record_data_collection_failure(self):
        """测试记录数据采集失败"""
        self.exporter.record_data_collection(
            data_source="api_football",
            collection_type="fixtures",
            success=False,
            duration=10.0,
            error_type="API限制",  # 修正参数名
        )

        metrics_data = self.exporter.get_metrics()[1]
        assert "football_data_collection_errors_total" in metrics_data

    def test_record_data_cleaning_success(self):
        """测试记录数据清洗成功"""
        self.exporter.record_data_cleaning(
            data_type="fixtures", success=True, duration=8.2, records_processed=100
        )

        headers, data = self.exporter.get_metrics()
        metrics_data = data  # data 已经是字符串类型，不需要decode
        assert "football_data_cleaning_total" in metrics_data

    def test_record_scheduler_task(self):
        """测试记录调度任务"""
        # 记录调度任务
        scheduled_time = datetime.now()
        actual_start_time = scheduled_time + timedelta(seconds=2)

        self.exporter.record_scheduler_task(
            task_name="test_task",
            scheduled_time=scheduled_time,
            actual_start_time=actual_start_time,
            duration=30.0,
            success=True,
        )

        headers, data = self.exporter.get_metrics()
        metrics_data = data  # data 已经是字符串类型，不需要decode
        assert "football_scheduler_task_delay_seconds" in metrics_data

    def test_update_table_row_counts(self):
        """
        测试更新表行数统计

        使用独立的 CollectorRegistry 确保测试隔离，避免全局状态污染。
        这个测试验证指标能够正确设置到mock注册表中。
        """
        # 提供测试数据，避免异步数据库调用
        test_counts = {"matches": 1000, "teams": 50, "odds": 2000}

        # 调用同步方法，使用提供的测试数据
        self.exporter.update_table_row_counts(test_counts)

        # 验证指标被正确记录到我们的独立注册表中
        content_type, metrics_data = self.exporter.get_metrics()
        assert "football_table_row_count" in metrics_data
        assert "matches" in metrics_data

    def test_get_metrics_returns_prometheus_format(self):
        """测试获取Prometheus格式指标"""
        headers, data = self.exporter.get_metrics()

        # 验证Content-Type
        assert headers == "text/plain; version=0.0.4; charset=utf-8"

        # 验证数据格式
        metrics_text = data  # data 已经是字符串类型，不需要decode
        assert isinstance(metrics_text, str)
        assert "football_system_info_info" in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
