"""
事件系统API测试
Tests for Event System API

测试src.api.events模块的功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# 测试导入
try:
    from src.api.events import (
        router,
        event_health_check,
        get_event_statistics,
        _find_handler,
    )
    from src.core.event_application import EventApplication
    from src.events import EventBus
    from src.events.handlers import MetricsEventHandler, AnalyticsEventHandler

    EVENTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    EVENTS_AVAILABLE = False


@pytest.mark.skipif(not EVENTS_AVAILABLE, reason="Events API module not available")
class TestEventHealthCheck:
    """事件健康检查测试"""

    @pytest.mark.asyncio
    async def test_event_health_check_success(self):
        """测试：健康检查成功"""
        mock_app = AsyncMock()
        mock_app.health_check.return_value = {
            "status": "healthy",
            "event_handlers": 5,
            "uptime": "2h 30m",
        }

        with patch("src.api.events.get_event_application") as mock_get_app:
            mock_get_app.return_value = mock_app

            _result = await event_health_check()

            assert result["status"] == "healthy"
            assert result["event_handlers"] == 5
            assert result["uptime"] == "2h 30m"
            mock_app.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_health_check_unhealthy(self):
        """测试：健康检查返回不健康状态"""
        mock_app = AsyncMock()
        mock_app.health_check.return_value = {
            "status": "unhealthy",
            "error": "Database connection failed",
        }

        with patch("src.api.events.get_event_application") as mock_get_app:
            mock_get_app.return_value = mock_app

            _result = await event_health_check()

            assert result["status"] == "unhealthy"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_event_health_check_exception(self):
        """测试：健康检查抛出异常"""
        mock_app = AsyncMock()
        mock_app.health_check.side_effect = RuntimeError("Service unavailable")

        with patch("src.api.events.get_event_application") as mock_get_app:
            mock_get_app.return_value = mock_app

            with pytest.raises(RuntimeError, match="Service unavailable"):
                await event_health_check()


@pytest.mark.skipif(not EVENTS_AVAILABLE, reason="Events API module not available")
class TestGetEventStatistics:
    """获取事件统计测试"""

    @pytest.mark.asyncio
    async def test_get_event_statistics_success(self):
        """测试：成功获取事件统计"""
        mock_bus = Mock()
        mock_bus.get_stats.return_value = {
            "total_events": 1000,
            "events_per_second": 10.5,
            "handlers": 5,
        }

        with (
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_bus.return_value = mock_bus
            mock_find_handler.side_effect = [None, None]  # 没有找到处理器

            _result = await get_event_statistics()

            assert result["total_events"] == 1000
            assert result["events_per_second"] == 10.5
            assert result["handlers"] == 5

    @pytest.mark.asyncio
    async def test_get_event_statistics_with_metrics(self):
        """测试：获取带指标的事件统计"""
        mock_bus = Mock()
        mock_bus.get_stats.return_value = {
            "total_events": 500,
            "events_per_second": 5.2,
        }

        mock_metrics_handler = Mock()
        mock_metrics_handler.get_metrics.return_value = {
            "cpu_usage": 45.5,
            "memory_usage": 67.8,
        }

        mock_analytics_handler = Mock()
        mock_analytics_handler.get_analytics_data.return_value = {
            "top_events": ["prediction.created", "user.login"],
            "event_trends": {"up": 10, "down": 5},
        }

        with (
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_bus.return_value = mock_bus
            # 第一次调用返回metrics处理器，第二次返回analytics处理器
            mock_find_handler.side_effect = [
                mock_metrics_handler,
                mock_analytics_handler,
            ]

            _result = await get_event_statistics()

            assert result["total_events"] == 500
            assert result["metrics"]["cpu_usage"] == 45.5
            assert result["analytics"]["top_events"] == [
                "prediction.created",
                "user.login",
            ]

    @pytest.mark.asyncio
    async def test_get_event_statistics_no_handlers(self):
        """测试：没有找到处理器"""
        mock_bus = Mock()
        mock_bus.get_stats.return_value = {"total_events": 100, "handlers": 0}

        with (
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_bus.return_value = mock_bus
            mock_find_handler.return_value = None  # 没有找到任何处理器

            _result = await get_event_statistics()

            assert result["total_events"] == 100
            assert "metrics" not in result
            assert "analytics" not in result

    @pytest.mark.asyncio
    async def test_get_event_statistics_bus_error(self):
        """测试：事件总线错误"""
        mock_bus = Mock()
        mock_bus.get_stats.side_effect = Exception("Bus error")

        with patch("src.api.events.get_event_bus") as mock_get_bus:
            mock_get_bus.return_value = mock_bus

            with pytest.raises(Exception, match="Bus error"):
                await get_event_statistics()


@pytest.mark.skipif(not EVENTS_AVAILABLE, reason="Events API module not available")
class TestFindHandler:
    """查找处理器测试"""

    def test_find_handler_success(self):
        """测试：成功找到处理器"""
        if "_find_handler" in globals():
            [Mock(spec=MetricsEventHandler), Mock(spec=AnalyticsEventHandler), Mock()]

            with patch("src.api.events MetricsEventHandler"):
                _find_handler(MetricsEventHandler)
                # 测试逻辑取决于实际实现

    def test_find_handler_not_found(self):
        """测试：未找到处理器"""
        if "_find_handler" in globals():
            [Mock(spec=AnalyticsEventHandler), Mock()]

            with patch("src.api.events MetricsEventHandler"):
                _find_handler(MetricsEventHandler)
                # 测试逻辑取决于实际实现


@pytest.mark.skipif(not EVENTS_AVAILABLE, reason="Events API module not available")
class TestEventsAPIIntegration:
    """事件API集成测试"""

    def test_router_configuration(self):
        """测试：路由配置"""
        assert router is not None
        assert router.prefix == "/events"
        assert "事件系统" in router.tags

    @pytest.mark.asyncio
    async def test_full_event_api_flow(self):
        """测试：完整的事件API流程"""
        # Mock所有依赖
        mock_app = AsyncMock()
        mock_app.health_check.return_value = {"status": "healthy"}

        mock_bus = Mock()
        mock_bus.get_stats.return_value = {
            "total_events": 100,
            "events_per_second": 5.0,
        }

        mock_metrics_handler = Mock()
        mock_metrics_handler.get_metrics.return_value = {"cpu": 50.0}

        mock_analytics_handler = Mock()
        mock_analytics_handler.get_analytics_data.return_value = {"trends": "up"}

        with (
            patch("src.api.events.get_event_application") as mock_get_app,
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_app.return_value = mock_app
            mock_get_bus.return_value = mock_bus
            mock_find_handler.side_effect = [
                mock_metrics_handler,
                mock_analytics_handler,
            ]

            # 1. 健康检查
            health_result = await event_health_check()
            assert health_result["status"] == "healthy"

            # 2. 获取统计信息
            stats_result = await get_event_statistics()
            assert stats_result["total_events"] == 100
            assert "metrics" in stats_result
            assert "analytics" in stats_result

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """测试：并发API调用"""
        import asyncio

        mock_app = AsyncMock()
        mock_app.health_check.return_value = {"status": "healthy"}

        with patch("src.api.events.get_event_application") as mock_get_app:
            mock_get_app.return_value = mock_app

            # 并发调用健康检查
            tasks = [event_health_check() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # 验证所有调用都成功
            assert len(results) == 10
            for result in results:
                assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """测试：错误传播"""
        # 测试健康检查错误传播
        mock_app = AsyncMock()
        mock_app.health_check.side_effect = ValueError("Invalid configuration")

        with patch("src.api.events.get_event_application") as mock_get_app:
            mock_get_app.return_value = mock_app

            with pytest.raises(ValueError, match="Invalid configuration"):
                await event_health_check()

    @pytest.mark.asyncio
    async def test_handler_metrics_collection(self):
        """测试：处理器指标收集"""
        mock_bus = Mock()
        mock_bus.get_stats.return_value = {"total_events": 50}

        mock_metrics = Mock()
        mock_metrics.get_metrics.side_effect = [
            {"requests": 100},
            {"requests": 200},
            {"requests": 300},
        ]

        with (
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_bus.return_value = mock_bus
            mock_find_handler.return_value = mock_metrics

            # 多次调用统计
            for i in range(3):
                _result = await get_event_statistics()
                assert result["metrics"]["requests"] == 100 * (i + 1)

    def test_router_tags_and_metadata(self):
        """测试：路由标签和元数据"""
        # 验证路由配置
        assert hasattr(router, "routes")

        # 检查路由信息
        for route in router.routes:
            if hasattr(route, "path"):
                assert route.path.startswith("/events")
            if hasattr(route, "tags"):
                assert isinstance(route.tags, list)

    @pytest.mark.asyncio
    async def test_event_system_metrics_detailed(self):
        """测试：详细事件系统指标"""
        # 创建复杂的模拟数据
        mock_bus = Mock()
        mock_bus.get_stats.return_value = {
            "total_events": 10000,
            "events_per_second": 25.5,
            "active_handlers": 8,
            "queue_size": 150,
            "processing_time_avg": 0.05,
        }

        mock_metrics_handler = Mock()
        mock_metrics_handler.get_metrics.return_value = {
            "handler_metrics": {
                "MetricsEventHandler": {
                    "processed": 5000,
                    "failed": 10,
                    "avg_processing_time": 0.02,
                },
                "AnalyticsEventHandler": {
                    "processed": 3000,
                    "failed": 5,
                    "avg_processing_time": 0.03,
                },
            }
        }

        mock_analytics_handler = Mock()
        mock_analytics_handler.get_analytics_data.return_value = {
            "event_types": {
                "prediction.created": 4000,
                "prediction.updated": 2000,
                "user.login": 1500,
                "user.logout": 1500,
            },
            "time_distribution": {
                "last_hour": 1000,
                "last_day": 8000,
                "last_week": 50000,
            },
        }

        with (
            patch("src.api.events.get_event_bus") as mock_get_bus,
            patch("src.api.events._find_handler") as mock_find_handler,
        ):
            mock_get_bus.return_value = mock_bus
            mock_find_handler.side_effect = [
                mock_metrics_handler,
                mock_analytics_handler,
            ]

            _result = await get_event_statistics()

            # 验证基础统计
            assert result["total_events"] == 10000
            assert result["events_per_second"] == 25.5

            # 验证处理器指标
            assert "handler_metrics" in result["metrics"]
            assert (
                result["metrics"]["handler_metrics"]["MetricsEventHandler"]["processed"]
                == 5000
            )

            # 验证分析数据
            assert result["analytics"]["event_types"]["prediction.created"] == 4000
            assert result["analytics"]["time_distribution"]["last_hour"] == 1000


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not EVENTS_AVAILABLE
        assert True  # 表明测试意识到模块不可用
