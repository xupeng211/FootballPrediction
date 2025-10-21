"""
门面模式单元测试
Unit Tests for Facade Pattern

测试门面模式的各个组件。
Tests all components of the facade pattern.
"""

import pytest
import asyncio
import os
from typing import Any
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.facades.base import (
    Subsystem,
    SubsystemStatus,
    SubsystemManager,
    SystemFacade,
)
from src.facades.facades import (
    DatabaseSubsystem,
    CacheSubsystem,
    NotificationSubsystem,
    AnalyticsSubsystem,
    PredictionSubsystem,
    MainSystemFacade,
    PredictionFacade,
    DataCollectionFacade,
    AnalyticsFacade,
    NotificationFacade,
)
from src.facades.factory import (
    FacadeFactory,
    FacadeConfig,
    facade_factory,
)


class TestSubsystem:
    """测试子系统"""

    @pytest.mark.asyncio
    async def test_database_subsystem(self):
        """测试数据库子系统"""
        subsystem = DatabaseSubsystem()

        # 测试初始化
        await subsystem.initialize()
        assert subsystem.status == SubsystemStatus.ACTIVE
        assert subsystem.connection_pool is not None

        # 测试查询执行
        _result = await subsystem.execute_query("SELECT * FROM test")
        assert isinstance(result, list)
        assert len(result) > 0
        assert subsystem.query_count > 0

        # 测试事务执行
        success = await subsystem.execute_transaction(
            [{"query": "INSERT INTO test", "params": {}}]
        )
        assert success is True

        # 测试关闭
        await subsystem.shutdown()
        assert subsystem.status == SubsystemStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_cache_subsystem(self):
        """测试缓存子系统"""
        subsystem = CacheSubsystem()

        # 测试初始化
        await subsystem.initialize()
        assert subsystem.status == SubsystemStatus.ACTIVE

        # 测试缓存设置和获取
        await subsystem.set("test_key", {"data": "test_value"}, ttl=300)
        cached_value = await subsystem.get("test_key")
        assert cached_value["data"] == "test_value"

        # 测试缓存未命中
        miss_value = await subsystem.get("nonexistent_key")
        assert miss_value is None

        # 测试缓存指标
        assert subsystem.hit_count == 1
        assert subsystem.miss_count == 1
        assert subsystem.metrics["hit_rate"] == 0.5

        # 测试清空缓存
        await subsystem.clear()
        assert subsystem.metrics["cache_size"] == 0

        await subsystem.shutdown()

    @pytest.mark.asyncio
    async def test_notification_subsystem(self):
        """测试通知子系统"""
        subsystem = NotificationSubsystem()

        # 测试初始化
        await subsystem.initialize()
        assert subsystem.status == SubsystemStatus.ACTIVE

        # 测试发送通知
        success = await subsystem.send_notification(
            "test@example.com", "Test message", channel="email"
        )
        assert success is True
        assert subsystem.metrics["sent_messages"] == 1

        # 测试不支持的通知渠道
        with pytest.raises(ValueError):
            await subsystem.send_notification(
                "test@example.com", "Test message", channel="unsupported"
            )

        # 测试排队通知
        await subsystem.queue_notification(
            {"recipient": "test2@example.com", "message": "Queued message"}
        )
        assert subsystem.metrics["queued_messages"] == 1

        await subsystem.shutdown()

    @pytest.mark.asyncio
    async def test_analytics_subsystem(self):
        """测试分析子系统"""
        subsystem = AnalyticsSubsystem()

        # 测试初始化
        await subsystem.initialize()
        assert subsystem.status == SubsystemStatus.ACTIVE

        # 测试跟踪事件
        await subsystem.track_event("test_event", {"property": "value"})
        assert len(subsystem.events) == 1
        assert subsystem.metrics["events_count"] == 1

        # 测试生成报告
        report = await subsystem.generate_report("summary")
        assert report["type"] == "summary"
        assert "generated_at" in report
        assert "data" in report
        assert subsystem.metrics["reports_count"] == 1

        await subsystem.shutdown()

    @pytest.mark.asyncio
    async def test_prediction_subsystem(self):
        """测试预测子系统"""
        subsystem = PredictionSubsystem()

        # 测试初始化
        await subsystem.initialize()
        assert subsystem.status == SubsystemStatus.ACTIVE

        # 测试预测
        _result = await subsystem.predict(
            "neural_network", {"feature1": 1.0, "feature2": 2.0}
        )
        assert "model" in result
        assert "output" in result
        assert _result["model"] == "neural_network"

        # 测试批量预测
        predictions = await subsystem.batch_predict(
            [
                {"model": "neural_network", "input": {"feature1": 1.0}},
                {"model": "random_forest", "input": {"feature1": 2.0}},
            ]
        )
        assert len(predictions) == 2

        # 测试不存在的模型
        with pytest.raises(ValueError):
            await subsystem.predict("nonexistent_model", {})

        await subsystem.shutdown()


class TestSubsystemManager:
    """测试子系统管理器"""

    def test_register_subsystem(self):
        """测试注册子系统"""
        manager = SubsystemManager()
        subsystem = Mock(spec=Subsystem)
        subsystem.name = "test_subsystem"

        # 注册无依赖的子系统
        manager.register(subsystem)
        assert subsystem.name in manager.list_subsystems()
        assert manager.get_subsystem("test_subsystem") == subsystem

        # 注册有依赖的子系统
        subsystem2 = Mock(spec=Subsystem)
        subsystem2.name = "test_subsystem2"
        manager.register(subsystem2, dependencies=["test_subsystem"])
        assert "test_subsystem" in manager._dependencies["test_subsystem2"]

    def test_unregister_subsystem(self):
        """测试注销子系统"""
        manager = SubsystemManager()
        subsystem = Mock(spec=Subsystem)
        subsystem.name = "test_subsystem"

        manager.register(subsystem)
        manager.unregister("test_subsystem")
        assert "test_subsystem" not in manager.list_subsystems()

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        manager = SubsystemManager()
        subsystem1 = Mock(spec=Subsystem)
        subsystem1.name = "sub1"
        subsystem2 = Mock(spec=Subsystem)
        subsystem2.name = "sub2"

        # 创建循环依赖
        manager.register(subsystem1, dependencies=["sub2"])
        with pytest.raises(ValueError, match="Circular dependency"):
            manager.register(subsystem2, dependencies=["sub1"])

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        """测试初始化所有子系统"""
        manager = SubsystemManager()

        # 创建模拟子系统
        subsystem1 = AsyncMock(spec=Subsystem)
        subsystem1.name = "sub1"
        subsystem1.status = SubsystemStatus.INACTIVE

        subsystem2 = AsyncMock(spec=Subsystem)
        subsystem2.name = "sub2"
        subsystem2.status = SubsystemStatus.INACTIVE

        manager.register(subsystem1)
        manager.register(subsystem2)

        await manager.initialize_all()

        # 验证所有子系统都被初始化
        subsystem1.initialize.assert_called_once()
        subsystem2.initialize.assert_called_once()
        assert subsystem1.status == SubsystemStatus.ACTIVE
        assert subsystem2.status == SubsystemStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """测试关闭所有子系统"""
        manager = SubsystemManager()

        subsystem1 = AsyncMock(spec=Subsystem)
        subsystem1.name = "sub1"
        subsystem2 = AsyncMock(spec=Subsystem)
        subsystem2.name = "sub2"

        manager.register(subsystem1)
        manager.register(subsystem2)

        await manager.shutdown_all()

        # 验证所有子系统都被关闭（逆序）
        subsystem2.shutdown.assert_called_once()
        subsystem1.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """测试所有子系统健康检查"""
        manager = SubsystemManager()

        subsystem1 = AsyncMock(spec=Subsystem)
        subsystem1.name = "sub1"
        subsystem1.health_check.return_value = True

        subsystem2 = AsyncMock(spec=Subsystem)
        subsystem2.name = "sub2"
        subsystem2.health_check.return_value = False

        manager.register(subsystem1)
        manager.register(subsystem2)

        results = await manager.health_check_all()
        assert results == {"sub1": True, "sub2": False}


class TestSystemFacade:
    """测试系统门面"""

    @pytest.mark.asyncio
    async def test_facade_initialization(self):
        """测试门面初始化"""
        facade = MainSystemFacade()

        # 注册子系统
        subsystem = AsyncMock(spec=Subsystem)
        subsystem.name = "test_sub"
        facade.register_subsystem(subsystem)

        # 测试初始化
        await facade.initialize()
        assert facade.initialized is True
        subsystem.initialize.assert_called_once()

        # 测试关闭
        await facade.shutdown()
        assert facade.initialized is False
        subsystem.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_facade_health_check(self):
        """测试门面健康检查"""

        # 使用一个简单的门面类进行测试
        class TestFacade(SystemFacade):
            async def execute(self, operation: str, **kwargs) -> Any:
                return "test_result"

        facade = TestFacade("test_facade")

        subsystem1 = AsyncMock(spec=Subsystem)
        subsystem1.name = "sub1"
        subsystem1.health_check.return_value = True

        subsystem2 = AsyncMock(spec=Subsystem)
        subsystem2.name = "sub2"
        subsystem2.health_check.return_value = True

        facade.register_subsystem(subsystem1)
        facade.register_subsystem(subsystem2)
        await facade.initialize()

        health = await facade.health_check()
        assert health["facade"] == "test_facade"
        assert health["initialized"] is True
        assert health["overall_health"] is True
        assert health["subsystem_count"] == 2
        assert health["healthy_subsystems"] == 2

    def test_facade_metrics(self):
        """测试门面指标"""
        facade = MainSystemFacade()

        # 测试初始指标
        assert facade.metrics["requests_count"] == 0
        assert facade.metrics["errors_count"] == 0

        # 测试重置指标
        facade.metrics["requests_count"] = 10
        facade.reset_metrics()
        assert facade.metrics["requests_count"] == 0

    def test_get_status(self):
        """测试获取门面状态"""
        facade = MainSystemFacade()
        status = facade.get_status()

        assert status["name"] == "main_system"
        assert "description" in status
        assert "initialized" in status
        assert "subsystems" in status
        assert "metrics" in status


class TestConcreteFacades:
    """测试具体门面实现"""

    @pytest.mark.asyncio
    async def test_main_system_facade(self):
        """测试主系统门面"""
        facade = MainSystemFacade()
        await facade.initialize()

        # 测试获取系统状态
        status = await facade.execute("get_system_status")
        assert "system_health" in status
        assert "total_subsystems" in status
        assert status["total_subsystems"] == 5

        # 测试快速预测
        _prediction = await facade.execute(
            "quick_prediction", input_data={"feature1": 1.0}, model="neural_network"
        )
        assert "model" in prediction
        assert "output" in prediction

        # 测试存储并预测
        _result = await facade.execute(
            "store_and_predict",
            _data={"test": "data"},
            cache_key="test_key",
            model="neural_network",
        )
        assert "model" in result

        # 测试批量处理
        items = [
            {"input_data": {"feature1": 1.0}, "cache_key": "key1"},
            {"input_data": {"feature1": 2.0}, "cache_key": "key2"},
        ]
        results = await facade.execute("batch_process", items=items)
        assert len(results) == 2

        # 测试未知操作
        with pytest.raises(ValueError):
            await facade.execute("unknown_operation")

    @pytest.mark.asyncio
    async def test_prediction_facade(self):
        """测试预测门面"""
        facade = PredictionFacade()
        await facade.initialize()

        # 测试预测
        _prediction = await facade.execute(
            "predict",
            model="neural_network",
            input_data={"feature1": 1.0},
            cache_key="test_pred",
        )
        assert "model" in prediction

        # 测试批量预测
        predictions = await facade.execute(
            "batch_predict",
            predictions=[
                {"model": "neural_network", "input": {"feature1": 1.0}},
                {"model": "random_forest", "input": {"feature1": 2.0}},
            ],
        )
        assert len(predictions) == 2

        # 测试获取模型信息
        model_info = await facade.execute("get_model_info")
        assert "available_models" in model_info
        assert "total_predictions" in model_info

    @pytest.mark.asyncio
    async def test_data_collection_facade(self):
        """测试数据收集门面"""
        facade = DataCollectionFacade()
        await facade.initialize()

        # 测试存储数据
        _result = await facade.execute(
            "store_data", _data={"key": "value"}, table="test_table"
        )
        assert _result["status"] == "success"
        assert _result["table"] == "test_table"

        # 测试查询数据
        _result = await facade.execute(
            "query_data", query="SELECT * FROM test_table", use_cache=True
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analytics_facade(self):
        """测试分析门面"""
        facade = AnalyticsFacade()
        await facade.initialize()

        # 测试跟踪事件
        _result = await facade.execute(
            "track_event", event_name="test_event", properties={"key": "value"}
        )
        assert _result["status"] == "tracked"

        # 测试生成报告
        report = await facade.execute("generate_report", report_type="summary")
        assert "type" in report
        assert report["type"] == "summary"

        # 测试获取分析摘要
        summary = await facade.execute("get_analytics_summary")
        assert "total_events" in summary
        assert "reports_count" in summary

    @pytest.mark.asyncio
    async def test_notification_facade(self):
        """测试通知门面"""
        facade = NotificationFacade()
        await facade.initialize()

        # 测试发送通知
        _result = await facade.execute(
            "send_notification",
            recipient="test@example.com",
            message="Test message",
            channel="email",
        )
        assert _result["status"] == "sent"

        # 测试排队通知
        _result = await facade.execute(
            "queue_notification",
            notification={
                "recipient": "test2@example.com",
                "message": "Queued message",
            },
        )
        assert _result["status"] == "queued"

        # 测试获取通知统计
        _stats = await facade.execute("get_notification_stats")
        assert "sent" in stats
        assert "queued" in stats


class TestFacadeFactory:
    """测试门面工厂"""

    def test_create_facade(self):
        """测试创建门面"""
        factory = FacadeFactory()

        # 测试创建主系统门面
        facade = factory.create_facade("main")
        assert isinstance(facade, MainSystemFacade)

        # 测试创建预测门面
        facade = factory.create_facade("prediction")
        assert isinstance(facade, PredictionFacade)

        # 测试未知门面类型
        with pytest.raises(ValueError):
            factory.create_facade("unknown")

    def test_create_from_config(self):
        """测试从配置创建门面"""
        factory = FacadeFactory()
        _config = FacadeConfig(
            name="test_facade",
            facade_type="main",
            enabled=True,
            parameters={"test_param": "test_value"},
        )

        facade = factory.create_from_config(config)
        assert isinstance(facade, MainSystemFacade)

        # 测试禁用的门面
        _config.enabled = False
        with pytest.raises(ValueError):
            factory.create_from_config(config)

    def test_get_or_create_singleton(self):
        """测试获取或创建门面（单例）"""
        factory = FacadeFactory()
        _config = FacadeConfig(name="test_facade", facade_type="main", enabled=True)
        factory.register_config(config)

        # 第一次获取
        facade1 = factory.get_or_create("test_facade")
        # 第二次获取
        facade2 = factory.get_or_create("test_facade")

        assert facade1 is facade2

    def test_load_config_from_dict(self):
        """测试从字典加载配置"""
        factory = FacadeFactory()
        _data = {
            "facades": [
                {
                    "name": "test_facade",
                    "facade_type": "main",
                    "enabled": True,
                    "parameters": {"test": "value"},
                }
            ]
        }

        factory.load_config_from_dict(data)
        _config = factory.get_config("test_facade")
        assert config is not None
        assert _config.facade_type == "main"
        assert _config.parameters["test"] == "value"

    @patch.dict(os.environ, {"TEST_VAR": "environment_value"})
    def test_resolve_environment_variables(self):
        """测试解析环境变量"""
        import os

        factory = FacadeFactory()

        _config = FacadeConfig(
            name="test_env", facade_type="main", parameters={"env_param": "$TEST_VAR"}
        )

        resolved_config = factory._resolve_environment_variables(config)
        assert resolved_config.parameters["env_param"] == "environment_value"

    def test_convert_type(self):
        """测试类型转换"""
        factory = FacadeFactory()

        # 测试布尔值转换
        assert factory._convert_type("true") is True
        assert factory._convert_type("false") is False

        # 测试整数转换
        assert factory._convert_type("123") == 123
        assert isinstance(factory._convert_type("123"), int)

        # 测试浮点数转换
        assert factory._convert_type("123.45") == 123.45
        assert isinstance(factory._convert_type("123.45"), float)

        # 测试字符串保持
        assert factory._convert_type("hello") == "hello"

    def test_facade_type_registration(self):
        """测试门面类型注册"""
        factory = FacadeFactory()

        # 测试列出可用类型
        types = factory.list_facade_types()
        assert "main" in types
        assert "prediction" in types

        # 测试注册新类型
        class CustomFacade(SystemFacade):
            def __init__(self):
                super().__init__("custom", "Custom facade for testing")

            async def execute(self, operation: str, **kwargs):
                return "custom"

        factory.register_facade_type("custom", CustomFacade)
        assert "custom" in factory.list_facade_types()

        # 测试创建自定义门面
        facade = factory.create_facade("custom")
        assert isinstance(facade, CustomFacade)

    def test_save_config_to_file(self, tmp_path):
        """测试保存配置到文件"""
        factory = FacadeFactory()
        factory.create_default_configs()

        # 测试保存为JSON
        json_file = tmp_path / "test_config.json"
        factory.save_config_to_file(json_file)
        assert json_file.exists()

        # 验证文件内容
        import json

        with open(json_file) as f:
            _data = json.load(f)
        assert "facades" in _data

        assert len(_data["facades"]) > 0

    def test_default_configs(self):
        """测试默认配置"""
        factory = FacadeFactory()
        factory.create_default_configs()

        configs = factory.list_configs()
        assert "main_facade" in configs
        assert "prediction_facade" in configs
        assert "data_collection_facade" in configs
        assert "analytics_facade" in configs
        assert "notification_facade" in configs

        # 验证配置内容
        main_config = factory.get_config("main_facade")
        assert main_config.facade_type == "main"
        assert main_config.enabled is True
        assert "timeout" in main_config.parameters
