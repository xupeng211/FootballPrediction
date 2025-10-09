"""
系统监控模块化组件测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.monitoring.system_monitor_mod import (
    SystemMonitor,
    PrometheusMetrics,
    get_system_monitor,
    MetricsCollectorManager,
    HealthChecker,
)


class TestPrometheusMetrics:
    """测试Prometheus指标管理器"""

    def test_initialization(self):
        """测试指标初始化"""
        metrics = PrometheusMetrics()

        # 验证所有指标都已创建
        assert hasattr(metrics, 'system_cpu_percent')
        assert hasattr(metrics, 'system_memory_percent')
        assert hasattr(metrics, 'app_requests_total')
        assert hasattr(metrics, 'db_query_duration_seconds')
        assert hasattr(metrics, 'cache_operations_total')
        assert hasattr(metrics, 'business_predictions_total')

    def test_get_all_metrics(self):
        """测试获取所有指标"""
        metrics = PrometheusMetrics()
        all_metrics = metrics.get_all_metrics()

        # 验证返回的指标字典包含所有预期的指标
        expected_keys = [
            'system_cpu_percent',
            'system_memory_percent',
            'app_requests_total',
            'db_query_duration_seconds',
            'cache_operations_total',
            'business_predictions_total',
        ]

        for key in expected_keys:
            assert key in all_metrics


class TestSystemMonitor:
    """测试系统监控器"""

    def test_initialization(self):
        """测试监控器初始化"""
        monitor = SystemMonitor()

        assert monitor.metrics is not None
        assert monitor.collector_manager is not None
        assert monitor.health_checker is not None
        assert monitor.is_monitoring is False
        assert monitor.start_time > 0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        monitor = SystemMonitor()

        # 启动监控
        await monitor.start_monitoring(interval=1)
        assert monitor.is_monitoring is True
        assert monitor.monitor_task is not None

        # 停止监控
        await monitor.stop_monitoring()
        assert monitor.is_monitoring is False

    @pytest.mark.asyncio
    async def test_collect_metrics(self):
        """测试收集指标"""
        monitor = SystemMonitor()

        # 收集指标
        metrics = await monitor.collect_metrics()

        # 验证返回的指标包含预期的组件
        assert 'system' in metrics
        assert 'database' in metrics
        assert 'cache' in metrics
        assert 'application' in metrics

    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """测试获取健康状态"""
        monitor = SystemMonitor()

        # 获取健康状态
        health = await monitor.get_health_status()

        # 验证健康状态结构
        assert 'status' in health
        assert 'timestamp' in health
        assert 'components' in health
        assert 'metrics' in health
        assert 'uptime_seconds' in health
        assert 'version' in health

    def test_record_request(self):
        """测试记录HTTP请求"""
        monitor = SystemMonitor()

        # 记录请求（应该不会抛出异常）
        monitor.record_request('GET', '/api/v1/test', 200, 0.123)

    def test_record_database_query(self):
        """测试记录数据库查询"""
        monitor = SystemMonitor()

        # 记录普通查询
        monitor.record_database_query('SELECT', 'matches', 0.045)

        # 记录慢查询
        monitor.record_database_query('SELECT', 'matches', 2.5, is_slow=True)

    def test_record_cache_operation(self):
        """测试记录缓存操作"""
        monitor = SystemMonitor()

        # 记录缓存命中
        monitor.record_cache_operation('get', 'redis', 'hit')

        # 记录缓存未命中
        monitor.record_cache_operation('get', 'redis', 'miss')

    def test_record_prediction(self):
        """测试记录预测操作"""
        monitor = SystemMonitor()

        monitor.record_prediction('v1.0.0', 'premier_league')

    def test_record_model_inference(self):
        """测试记录模型推理"""
        monitor = SystemMonitor()

        monitor.record_model_inference('football_predictor', 'v2.1.0', 0.234)

    def test_get_monitoring_status(self):
        """测试获取监控状态"""
        monitor = SystemMonitor()

        status = monitor.get_monitoring_status()

        assert 'is_monitoring' in status
        assert 'uptime_seconds' in status
        assert 'collectors' in status
        assert 'health_checkers' in status


class TestGlobalInstance:
    """测试全局实例管理"""

    def test_get_system_monitor(self):
        """测试获取全局监控器实例"""
        monitor1 = get_system_monitor()
        monitor2 = get_system_monitor()

        # 应该返回同一个实例
        assert monitor1 is monitor2


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """测试完整的监控周期"""
        monitor = SystemMonitor()

        # 启动监控
        await monitor.start_monitoring(interval=0.1)

        # 等待一些监控循环
        await asyncio.sleep(0.3)

        # 记录一些指标
        monitor.record_request('POST', '/api/v1/predict', 201, 0.567)
        monitor.record_database_query('INSERT', 'predictions', 0.123)
        monitor.record_cache_operation('set', 'redis', 'success')

        # 收集指标
        metrics = await monitor.collect_metrics()
        assert metrics is not None

        # 获取健康状态
        health = await monitor.get_health_status()
        assert health is not None

        # 停止监控
        await monitor.stop_monitoring()

        assert monitor.is_monitoring is False


@pytest.mark.asyncio
async def test_backward_compatibility():
    """测试向后兼容性"""
    from src.monitoring.system_monitor import SystemMonitor as LegacySystemMonitor

    # 使用旧的导入应该能正常工作
    monitor = LegacySystemMonitor()

    # 所有方法都应该可用
    assert hasattr(monitor, 'start_monitoring')
    assert hasattr(monitor, 'stop_monitoring')
    assert hasattr(monitor, 'record_request')
    assert hasattr(monitor, 'get_health_status')

    # 测试基本功能
    monitor.record_request('GET', '/test', 200, 0.1)
    health = await monitor.get_health_status()
    assert health is not None