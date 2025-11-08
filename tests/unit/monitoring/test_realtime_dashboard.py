"""
实时监控仪表板测试
Real-time Monitoring Dashboard Tests

测试监控仪表板的核心功能。
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.monitoring.realtime_dashboard import (
    MockPerformanceOptimizer,
    MonitoringDataManager,
    monitoring_manager,
)


class TestMonitoringDataManager:
    """监控数据管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = MonitoringDataManager()

        assert manager.connected_clients == []
        assert manager.performance_optimizer is None
        assert manager.monitoring_active is False
        assert manager.update_interval == 2.0
        assert manager.max_history_points == 100
        assert manager.metrics_history == []

    @pytest.mark.asyncio
    async def test_initialize_with_mock_optimizer(self):
        """测试使用模拟优化器初始化"""
        manager = MonitoringDataManager()

        with patch(
            "src.monitoring.realtime_dashboard.EnhancedPerformanceOptimizer",
            side_effect=Exception("导入失败"),
        ):
            await manager.initialize()

        assert manager.performance_optimizer is not None
        assert isinstance(manager.performance_optimizer, MockPerformanceOptimizer)

    @pytest.mark.asyncio
    async def test_register_unregister_client(self):
        """测试客户端注册和注销"""
        manager = MonitoringDataManager()
        mock_websocket = AsyncMock()

        await manager.register_client(mock_websocket)
        assert len(manager.connected_clients) == 1
        assert mock_websocket in manager.connected_clients

        await manager.unregister_client(mock_websocket)
        assert len(manager.connected_clients) == 0
        assert mock_websocket not in manager.connected_clients

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """测试启动和停止监控"""
        manager = MonitoringDataManager()

        await manager.start_monitoring()
        assert manager.monitoring_active is True

        await manager.stop_monitoring()
        assert manager.monitoring_active is False

    @pytest.mark.asyncio
    async def test_collect_metrics_with_mock(self):
        """测试收集指标（使用模拟数据）"""
        manager = MonitoringDataManager()
        manager.performance_optimizer = MockPerformanceOptimizer()

        metrics = await manager._collect_metrics()

        assert "timestamp" in metrics
        assert "system" in metrics
        assert "database" in metrics
        assert "cache" in metrics
        assert "concurrency" in metrics
        assert "system_info" in metrics
        assert "alerts" in metrics

        # 验证数据结构
        assert isinstance(metrics["system"], dict)
        assert isinstance(metrics["alerts"], list)

    @pytest.mark.asyncio
    async def test_get_system_info_without_psutil(self):
        """测试获取系统信息（没有psutil时）"""
        manager = MonitoringDataManager()

        with patch.dict("sys.modules", {"psutil": None}):
            system_info = await manager._get_system_info()

        assert "cpu_percent" in system_info
        assert "memory_percent" in system_info
        assert "disk_usage" in system_info
        assert "load_average" in system_info

        # 验证默认值
        assert isinstance(system_info["cpu_percent"], (int, float))
        assert 0 <= system_info["cpu_percent"] <= 100

    @pytest.mark.asyncio
    async def test_check_alerts(self):
        """测试告警检查"""
        manager = MonitoringDataManager()

        # 测试正常指标（无告警）
        normal_metrics = {
            "system": {"avg_response_time": 0.5, "error_rate": 1.0},
            "database": {"active_connections": 10},
            "cache": {"hit_rate": 85.0},
        }

        alerts = await manager._check_alerts(normal_metrics)
        assert len(alerts) == 0

        # 测试告警条件
        alert_metrics = {
            "system": {"avg_response_time": 1.5, "error_rate": 6.0},
            "database": {"active_connections": 60},
            "cache": {"hit_rate": 65.0},
        }

        alerts = await manager._check_alerts(alert_metrics)
        assert len(alerts) > 0

        # 验证告警结构
        for alert in alerts:
            assert "level" in alert
            assert "message" in alert
            assert "timestamp" in alert
            assert alert["level"] in ["warning", "critical"]

    @pytest.mark.asyncio
    async def test_broadcast_metrics_with_no_clients(self):
        """测试广播指标（无客户端）"""
        manager = MonitoringDataManager()
        metrics = {"test": "data"}

        # 不应该抛出异常
        await manager._broadcast_metrics(metrics)

    @pytest.mark.asyncio
    async def test_broadcast_metrics_with_clients(self):
        """测试广播指标（有客户端）"""
        manager = MonitoringDataManager()
        mock_websocket = AsyncMock()
        mock_websocket.client_state = "CONNECTED"

        manager.connected_clients.append(mock_websocket)

        metrics = {"test": "data"}
        await manager._broadcast_metrics(metrics)

        # 验证发送消息被调用
        mock_websocket.send_text.assert_called_once()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert "test" in sent_data

    @pytest.mark.asyncio
    async def test_broadcast_metrics_cleanup_disconnected(self):
        """测试广播时清理断开的客户端"""
        manager = MonitoringDataManager()
        mock_websocket_connected = AsyncMock()
        mock_websocket_connected.client_state = "CONNECTED"

        mock_websocket_disconnected = AsyncMock()
        mock_websocket_disconnected.client_state = "DISCONNECTED"

        manager.connected_clients.extend(
            [
                mock_websocket_connected,
                mock_websocket_disconnected,
            ]
        )

        metrics = {"test": "data"}
        await manager._broadcast_metrics(metrics)

        # 验证只有连接的客户端收到消息
        assert mock_websocket_connected.send_text.called
        assert not mock_websocket_disconnected.send_text.called

        # 验证断开的客户端被清理
        assert len(manager.connected_clients) == 1
        assert mock_websocket_connected in manager.connected_clients
        assert mock_websocket_disconnected not in manager.connected_clients

    def test_get_metrics_history(self):
        """测试获取历史指标"""
        manager = MonitoringDataManager()
        from datetime import datetime, timedelta

        # 添加一些历史数据
        now = datetime.now()
        old_time = now - timedelta(minutes=10)

        old_metrics = {"timestamp": old_time.isoformat(), "value": 1}
        new_metrics = {"timestamp": now.isoformat(), "value": 2}

        manager.metrics_history.extend([old_metrics, new_metrics])

        # 获取最近5分钟的数据
        recent_history = manager.get_metrics_history(5)
        assert len(recent_history) == 1
        assert recent_history[0]["value"] == 2

        # 获取最近15分钟的数据
        full_history = manager.get_metrics_history(15)
        assert len(full_history) == 2

    def test_metrics_history_limit(self):
        """测试历史数据限制"""
        manager = MonitoringDataManager()

        # 添加超过限制的数据
        for i in range(manager.max_history_points + 10):
            manager.metrics_history.append({"timestamp": f"time_{i}", "value": i})

        # 验证历史数据被限制
        assert len(manager.metrics_history) == manager.max_history_points

    @pytest.mark.asyncio
    async def test_monitoring_loop_error_handling(self):
        """测试监控循环错误处理"""
        manager = MonitoringDataManager()
        manager.performance_optimizer = MockPerformanceOptimizer()

        # 模拟收集指标时出错
        with patch.object(
            manager, "_collect_metrics", side_effect=Exception("收集失败")
        ):
            # 启动监控循环
            manager.monitoring_active = True

            # 运行一次循环
            await manager._monitoring_loop()

            # 验证监控仍然活跃（错误不应该停止循环）
            assert manager.monitoring_active is True


class TestMockPerformanceOptimizer:
    """模拟性能优化器测试"""

    @pytest.mark.asyncio
    async def test_mock_optimizer_initialization(self):
        """测试模拟优化器初始化"""
        optimizer = MockPerformanceOptimizer()

        await optimizer.initialize("test_db", 50)
        assert optimizer.initialized is True

    @pytest.mark.asyncio
    async def test_mock_comprehensive_metrics(self):
        """测试模拟综合指标"""
        optimizer = MockPerformanceOptimizer()

        metrics = await optimizer.get_comprehensive_metrics()

        assert "system" in metrics
        assert "database" in metrics
        assert "cache" in metrics
        assert "concurrency" in metrics

        # 验证指标数据类型
        for category in metrics.values():
            assert isinstance(category, dict)


class TestGlobalMonitoringManager:
    """全局监控管理器测试"""

    def test_global_manager_instance(self):
        """测试全局管理器实例"""
        from src.monitoring.realtime_dashboard import monitoring_manager

        assert monitoring_manager is not None
        assert isinstance(monitoring_manager, MonitoringDataManager)

    @pytest.mark.asyncio
    async def test_global_manager_functionality(self):
        """测试全局管理器功能"""
        # 测试全局管理器可以正常工作
        await monitoring_manager.initialize()
        assert monitoring_manager.performance_optimizer is not None

        metrics = await monitoring_manager._collect_metrics()
        assert "system" in metrics
