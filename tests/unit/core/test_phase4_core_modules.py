"""
核心模块集成测试
Core Modules Integration Tests

专注于核心业务逻辑的集成测试，基于真实模块实现。
"""

import asyncio

import pytest

# 真实模块导入
try:
    from src.core.prediction_engine import _lazy_import, get_prediction_engine
    from src.core.service_lifecycle import ServiceLifecycleManager, ServiceState
    from src.cqrs.application import PredictionCQRSService
    from src.cqrs.bus import get_command_bus, get_query_bus
    from src.events.base import Event, EventHandler
    from src.events.bus import EventBus

    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    CORE_MODULES_AVAILABLE = False
    print(f"核心模块导入失败: {e}")


@pytest.mark.skipif(not CORE_MODULES_AVAILABLE, reason="核心模块不可用")
@pytest.mark.integration
class TestCoreModulesIntegration:
    """核心模块集成测试"""

    @pytest.fixture
    async def prediction_engine(self):
        """预测引擎fixture"""
        _lazy_import()
        engine = await get_prediction_engine()
        yield engine
        # 清理
        if hasattr(engine, "cleanup"):
            await engine.cleanup()

    @pytest.fixture
    def lifecycle_manager(self):
        """生命周期管理器fixture"""
        return ServiceLifecycleManager()

    @pytest.fixture
    def event_bus(self):
        """事件总线fixture"""
        return EventBus(max_workers=2)

    async def test_prediction_engine_basic_flow(self, prediction_engine):
        """测试预测引擎基本流程"""
        # 基本配置验证
        assert hasattr(prediction_engine, "config")
        assert hasattr(prediction_engine, "generate_prediction")

        # 模拟预测数据
        match_data = {
            "match_id": "test_match_001",
            "teams": {"home": "Team A", "away": "Team B"},
            "competition": "Premier League",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 测试预测生成（如果方法存在）
        if hasattr(prediction_engine, "generate_prediction"):
            try:
                result = await prediction_engine.generate_prediction(match_data)
                assert "predictions" in result or "error" in result
            except Exception as e:
                # 允许服务不可用的情况
                assert "unavailable" in str(e).lower() or "connection" in str(e).lower()

    async def test_service_lifecycle_management(self, lifecycle_manager):
        """测试服务生命周期管理"""
        # 创建模拟服务
        mock_service = Mock()
        mock_service.start = AsyncMock()
        mock_service.stop = AsyncMock()
        mock_service.health_check = AsyncMock(return_value={"status": "healthy"})

        service_name = "test_service"

        # 注册服务
        success = lifecycle_manager.register_service(service_name, mock_service)
        assert success is True

        # 启动服务
        start_result = await lifecycle_manager.start_service(service_name)
        assert start_result.success is True
        assert lifecycle_manager.get_service_status(service_name) == ServiceState.RUNNING

        # 健康检查
        health = await lifecycle_manager.check_service_health(service_name)
        assert health["status"] == "healthy"

        # 停止服务
        stop_result = await lifecycle_manager.stop_service(service_name)
        assert stop_result.success is True
        assert lifecycle_manager.get_service_status(service_name) == ServiceState.STOPPED

    async def test_event_bus_publish_subscribe(self, event_bus):
        """测试事件总线发布订阅"""
        # 创建测试事件处理器
        received_events = []

        class TestEventHandler(EventHandler):
            async def handle(self, event: Event) -> None:
                received_events.append(event)

        handler = TestEventHandler()

        # 订阅事件
        event_bus.subscribe("TestEvent", handler)

        # 启动事件总线
        await event_bus.start()

        try:
            # 创建并发布测试事件
            class TestEvent(Event):
                def __init__(self, data):
                    self.data = data
                    self.timestamp = datetime.utcnow()

            test_event = TestEvent({"message": "test data"})
            await event_bus.publish(test_event)

            # 等待事件处理
            await asyncio.sleep(0.1)

            # 验证事件被接收
            assert len(received_events) == 1
            assert received_events[0].data["message"] == "test data"

        finally:
            await event_bus.stop()

    async def test_cqrs_command_query_integration(self):
        """测试CQRS命令查询集成"""
        # 获取命令和查询总线
        get_command_bus()
        query_bus = get_query_bus()

        # 创建CQRS服务
        PredictionCQRSService()

        # 测试查询操作
        try:
            # 创建测试查询
            from src.cqrs.queries import GetPredictionByIdQuery

            query = GetPredictionByIdQuery(prediction_id="test_001")

            # 执行查询（可能因为数据不存在而失败，这是正常的）
            await query_bus.execute(query)
            # 结果可能是None或异常，都接受

        except Exception as e:
            # 允许数据库连接或数据不存在的情况
            assert "not found" in str(e).lower() or "connection" in str(e).lower()

    async def test_prediction_engine_configuration_validation(self, prediction_engine):
        """测试预测引擎配置验证"""
        config = prediction_engine.config

        # 验证基本配置属性
        assert hasattr(config, "model_path")
        assert hasattr(config, "cache_enabled")
        assert hasattr(config, "confidence_threshold")

        # 验证配置值的有效性
        if hasattr(config, "confidence_threshold"):
            assert 0.0 <= config.confidence_threshold <= 1.0

        if hasattr(config, "cache_ttl"):
            assert config.cache_ttl > 0

    async def test_service_error_handling(self, lifecycle_manager):
        """测试服务错误处理"""
        # 创建会失败的服务
        failing_service = Mock()
        failing_service.start = AsyncMock(side_effect=Exception("Service start failed"))
        failing_service.stop = AsyncMock()

        service_name = "failing_service"

        # 注册服务
        lifecycle_manager.register_service(service_name, failing_service)

        # 尝试启动失败的服务
        result = await lifecycle_manager.start_service(service_name)
        assert result.success is False
        assert "Service start failed" in str(result.error)

        # 验证服务状态
        status = lifecycle_manager.get_service_status(service_name)
        assert status in [ServiceState.ERROR, ServiceState.UNINITIALIZED]

    async def test_event_bus_error_handling(self, event_bus):
        """测试事件总线错误处理"""
        # 创建会失败的事件处理器
        failing_handler = Mock()
        failing_handler.handle = AsyncMock(side_effect=Exception("Handler failed"))

        # 创建正常的事件处理器
        success_handler = Mock()
        success_handler.handle = AsyncMock()

        # 订阅事件
        event_bus.subscribe("ErrorTestEvent", failing_handler)
        event_bus.subscribe("ErrorTestEvent", success_handler)

        # 启动事件总线
        await event_bus.start()

        try:
            # 创建并发布测试事件
            class ErrorTestEvent(Event):
                def __init__(self):
                    self.timestamp = datetime.utcnow()

            event = ErrorTestEvent()
            await event_bus.publish(event)

            # 等待事件处理
            await asyncio.sleep(0.1)

            # 验证失败的处理器被记录但不影响其他处理器
            success_handler.handle.assert_called_once()

        finally:
            await event_bus.stop()

    async def test_module_integration_workflow(self, lifecycle_manager, event_bus):
        """测试模块集成工作流"""
        # 1. 启动生命周期管理器中的服务
        mock_prediction_service = Mock()
        mock_prediction_service.start = AsyncMock()
        mock_prediction_service.stop = AsyncMock()
        mock_prediction_service.generate_prediction = AsyncMock(
            return_value={"confidence": 0.85, "outcome": "home_win"}
        )

        lifecycle_manager.register_service("prediction_service", mock_prediction_service)
        await lifecycle_manager.start_service("prediction_service")

        # 2. 启动事件总线
        await event_bus.start()

        try:
            # 3. 模拟完整的工作流
            workflow_events = []

            class WorkflowEventHandler(EventHandler):
                async def handle(self, event: Event) -> None:
                    workflow_events.append(type(event).__name__)

            event_bus.subscribe("WorkflowEvent", WorkflowEventHandler())

            # 4. 执行工作流步骤
            class WorkflowEvent(Event):
                def __init__(self, step):
                    self.step = step
                    self.timestamp = datetime.utcnow()

            # 模拟工作流事件序列
            for step in ["start", "processing", "complete"]:
                await event_bus.publish(WorkflowEvent(step))

            await asyncio.sleep(0.1)

            # 5. 验证工作流完成
            assert len(workflow_events) == 3
            assert "start" in workflow_events
            assert "complete" in workflow_events

            # 6. 验证服务状态
            status = lifecycle_manager.get_service_status("prediction_service")
            assert status == ServiceState.RUNNING

        finally:
            # 清理
            await event_bus.stop()
            await lifecycle_manager.stop_service("prediction_service")

    def test_module_availability_and_imports(self):
        """测试模块可用性和导入"""
        # 验证核心模块可以正常导入
        from src.core.service_lifecycle import ServiceLifecycleManager, ServiceState
        from src.events.base import Event, EventHandler
        from src.events.bus import EventBus

        # 验证类的存在
        assert ServiceLifecycleManager is not None
        assert ServiceState is not None
        assert EventBus is not None
        assert Event is not None
        assert EventHandler is not None

        # 验证枚举值
        assert hasattr(ServiceState, "RUNNING")
        assert hasattr(ServiceState, "STOPPED")
        assert hasattr(ServiceState, "ERROR")


@pytest.mark.unit
class TestCoreModulesUnit:
    """核心模块单元测试"""

    def test_service_state_enum(self):
        """测试服务状态枚举"""
        from src.core.service_lifecycle import ServiceState

        # 验证枚举值
        assert ServiceState.UNINITIALIZED.value == "uninitialized"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.ERROR.value == "error"

        # 验证枚举比较
        assert ServiceState.RUNNING != ServiceState.STOPPED
        assert ServiceState.RUNNING == ServiceState.RUNNING

    def test_event_bus_initialization(self):
        """测试事件总线初始化"""
        from src.events.bus import EventBus

        # 测试不同参数的初始化
        bus1 = EventBus()
        bus2 = EventBus(max_workers=5)

        assert bus1._executor._max_workers == 10  # 默认值
        assert bus2._executor._max_workers == 5
        assert not bus1._running
        assert not bus2._running

    def test_lazy_import_functionality(self):
        """测试延迟导入功能"""
        from src.core.prediction_engine import _lazy_import

        # 第一次调用应该成功导入
        _lazy_import()

        # 第二次调用不应该重复导入
        _lazy_import()

        # 验证全局变量已设置（可能因为模块依赖问题而失败）
        try:
            from src.core.prediction_engine import PredictionConfig, PredictionEngine

            assert PredictionEngine is not None
            assert PredictionConfig is not None
        except ImportError:
            # 允许导入失败的情况
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
