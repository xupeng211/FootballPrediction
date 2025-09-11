"""
监控指标导出器测试模块
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from prometheus_client import CollectorRegistry

from src.monitoring.metrics_exporter import MetricsExporter


class TestMetricsExporter:
    """MetricsExporter 基础测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.test_registry = CollectorRegistry()
        self.exporter = MetricsExporter(registry=self.test_registry)

    def test_init_creates_all_metrics(self):
        """测试初始化时创建所有指标"""
        assert self.exporter.data_collection_total is not None
        assert self.exporter.data_collection_errors is not None
        assert self.exporter.data_cleaning_total is not None
        assert self.exporter.scheduler_task_delay is not None
        assert self.exporter.table_row_counts is not None

    def test_record_data_collection_success(self):
        """测试记录数据采集成功"""
        self.exporter.record_data_collection(
            data_source="api_football",
            collection_type="fixtures",
            success=True,
            duration=30.5,
            records_count=100,
        )

        # 验证指标被正确设置
        metrics_data = self.exporter.get_metrics()[1].decode("utf-8")
        assert "football_data_collection_total" in metrics_data
        assert "api_football" in metrics_data

    def test_record_data_collection_failure(self):
        """测试记录数据采集失败"""
        self.exporter.record_data_collection(
            data_source="api_football",
            collection_type="fixtures",
            success=False,
            duration=10.0,
            failure_reason="API限制",
        )

        metrics_data = self.exporter.get_metrics()[1].decode("utf-8")
        assert "football_data_collection_errors_total" in metrics_data

    def test_record_data_cleaning_success(self):
        """测试记录数据清洗成功"""
        self.exporter.record_data_cleaning(
            data_type="matches", success=True, duration=15.0, records_processed=50
        )

        metrics_data = self.exporter.get_metrics()[1].decode("utf-8")
        assert "football_data_cleaning_total" in metrics_data

    def test_record_scheduler_task(self):
        """测试记录调度任务"""
        scheduled_time = datetime.now()
        actual_start_time = scheduled_time + timedelta(seconds=5)

        self.exporter.record_scheduler_task(
            task_name="collect_fixtures",
            scheduled_time=scheduled_time,
            actual_start_time=actual_start_time,
            duration=30.0,
            success=True,
        )

        metrics_data = self.exporter.get_metrics()[1].decode("utf-8")
        assert "football_scheduler_task_delay_seconds" in metrics_data

    @pytest.mark.asyncio
    async def test_update_table_row_counts(self):
        """测试更新表行数统计"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar.return_value = 1000

        with patch(
            "src.monitoring.metrics_exporter.get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await self.exporter.update_table_row_counts()

            # 验证数据库查询被调用
            assert mock_session.execute.called

    def test_get_metrics_returns_prometheus_format(self):
        """测试获取指标返回Prometheus格式"""
        headers, data = self.exporter.get_metrics()

        assert headers is not None
        assert data is not None
        assert isinstance(data, bytes)

        # 验证包含系统信息
        metrics_text = data.decode("utf-8")
        assert "football_system_info_info" in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
