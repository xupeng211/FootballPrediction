"""
监控指标收集器简单测试模块
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.monitoring.metrics_collector import MetricsCollector


class TestMetricsCollectorSimple:
    """MetricsCollector 简单测试"""

    def setup_method(self):
        """测试设置"""
        self.mock_exporter = Mock()
        self.mock_exporter.collect_all_metrics = AsyncMock()

        with patch(
            "src.monitoring.metrics_collector.get_metrics_exporter"
        ) as mock_get_exporter:
            mock_get_exporter.return_value = self.mock_exporter
            self.collector = MetricsCollector()

    def test_init(self):
        """测试初始化"""
        assert self.collector.collection_interval == 30
        assert self.collector.running is False
        assert self.collector._task is None
        assert self.collector.metrics_exporter == self.mock_exporter

    def test_init_custom_interval(self):
        """测试自定义间隔时间初始化"""
        with patch(
            "src.monitoring.metrics_collector.get_metrics_exporter"
        ) as mock_get_exporter:
            mock_get_exporter.return_value = self.mock_exporter
            collector = MetricsCollector(collection_interval=60)
            assert collector.collection_interval == 60

    @pytest.mark.asyncio
    async def test_manual_collection(self):
        """测试手动触发收集"""
        await self.mock_exporter.collect_all_metrics()
        self.mock_exporter.collect_all_metrics.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
