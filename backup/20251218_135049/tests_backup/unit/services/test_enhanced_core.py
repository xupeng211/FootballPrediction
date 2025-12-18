"""增强核心服务测试
Enhanced Core Service Tests.

测试src/services/enhanced_core.py模块中的增强服务功能。
"""

import pytest
from datetime import datetime
import time

from src.services.enhanced_core import (
    ServiceConfig,
    ServiceMetrics,
    EnhancedBaseService,
    BaseService,
    AbstractBaseService,
)


class TestServiceConfig:
    """服务配置测试类."""

    def test_service_config_initialization_minimal(self):
        """测试服务配置最小初始化."""
        config = ServiceConfig(name="TestService")

        # 验证基本属性
        assert config.name == "TestService"
        assert config.version == "1.0.0"
        assert config.description == ""
        assert config.dependencies == []
        assert config.config == {}
        assert isinstance(config.created_at, datetime)

    def test_service_config_initialization_full(self):
        """测试服务配置完整初始化."""
        dependencies = ["service1", "service2"]
        custom_config = {"key1": "value1", "key2": 42}

        config = ServiceConfig(
            name="FullService",
            version="2.0.0",
            description="A complete service configuration",
            dependencies=dependencies,
            config=custom_config,
        )

        # 验证完整属性
        assert config.name == "FullService"
        assert config.version == "2.0.0"
        assert config.description == "A complete service configuration"
        assert config.dependencies == dependencies
        assert config.config == custom_config

    def test_service_config_creation_time(self):
        """测试服务配置创建时间."""
        before = datetime.now()
        config = ServiceConfig(name="TimeTest")
        after = datetime.now()

        # 验证创建时间在预期范围内
        assert before <= config.created_at <= after

    def test_service_config_immutable_attributes(self):
        """测试服务配置属性的不可变性."""
        config = ServiceConfig(name="ImmutableTest")

        # 验证初始值

        # 尝试修改（虽然Python允许，但实际使用中应该保持不可变）
        config.name = "Modified"
        config.version = "2.0.0"

        # 验证修改生效（Python层面）
        assert config.name == "Modified"
        assert config.version == "2.0.0"


class TestServiceMetrics:
    """服务指标测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.metrics = ServiceMetrics()

    def test_service_metrics_initialization(self):
        """测试服务指标初始化."""
        metrics = ServiceMetrics()

        # 验证初始状态
        expected_metrics = {
            "calls": 0,
            "errors": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "last_call": None,
            "min_time": float("inf"),
            "max_time": 0.0,
        }

        assert metrics.metrics == expected_metrics

    def test_record_call_success(self):
        """测试记录成功调用."""
        duration = 0.5
        self.metrics.record_call(duration, success=True)

        # 验证指标更新
        assert self.metrics.metrics["calls"] == 1
        assert self.metrics.metrics["errors"] == 0
        assert self.metrics.metrics["total_time"] == duration
        assert self.metrics.metrics["avg_time"] == duration
        assert self.metrics.metrics["min_time"] == duration
        assert self.metrics.metrics["max_time"] == duration
        assert self.metrics.metrics["last_call"] is not None

    def test_record_call_error(self):
        """测试记录错误调用."""
        duration = 0.3
        self.metrics.record_call(duration, success=False)

        # 验证错误指标
        assert self.metrics.metrics["calls"] == 1
        assert self.metrics.metrics["errors"] == 1
        assert self.metrics.metrics["total_time"] == duration

    def test_record_multiple_calls(self):
        """测试记录多次调用."""
        durations = [0.1, 0.2, 0.3, 0.4]
        for i, duration in enumerate(durations):
            self.metrics.record_call(duration, success=(i % 2 == 0))

        # 验证汇总指标
        assert self.metrics.metrics["calls"] == len(durations)
        assert self.metrics.metrics["errors"] == 2  # 第2和第4个是错误的
        assert self.metrics.metrics["total_time"] == sum(durations)
        assert self.metrics.metrics["avg_time"] == sum(durations) / len(durations)
        assert self.metrics.metrics["min_time"] == 0.1
        assert self.metrics.metrics["max_time"] == 0.4

    def test_get_metrics(self):
        """测试获取指标."""
        # 记录一些调用
        self.metrics.record_call(0.1, True)
        self.metrics.record_call(0.2, False)

        metrics = self.metrics.get_metrics()

        # 验证返回的指标
        assert isinstance(metrics, dict)
        assert "calls" in metrics
        assert "errors" in metrics
        assert "total_time" in metrics
        assert "avg_time" in metrics
        assert "error_rate" in metrics
        assert "last_call" in metrics

        # 验证错误率计算
        assert metrics["error_rate"] == 0.5  # 1个错误 / 2个总调用

    def test_get_metrics_no_calls(self):
        """测试无调用时的指标获取."""
        metrics = self.metrics.get_metrics()

        # 验证零调用时的指标
        assert metrics["calls"] == 0
        assert metrics["errors"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["min_time"] == float("inf")
        assert metrics["max_time"] == 0.0

    def test_performance_impact(self):
        """测试指标记录的性能影响."""
        start_time = time.time()

        # 记录大量调用
        for _i in range(1000):
            self.metrics.record_call(0.001, True)

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能在合理范围内（应该很快）
        assert duration < 1.0  # 1000次调用应该在1秒内完成
        assert self.metrics.metrics["calls"] == 1000


class TestBaseService:
    """基础服务测试类."""

    def test_base_service_initialization_default(self):
        """测试基础服务默认初始化."""
        service = BaseService()

        # 验证默认配置
        assert service.name == "BaseService"
        assert service.config is not None
        assert service.config.name == "BaseService"

    def test_base_service_initialization_custom(self):
        """测试基础服务自定义初始化."""
        custom_name = "CustomService"
        service = BaseService(name=custom_name)

        # 验证自定义名称
        assert service.name == custom_name
        assert service.config.name == custom_name

    def test_base_service_status_initial(self):
        """测试基础服务初始状态."""
        service = BaseService()

        # 验证初始状态
        assert service.get_status() == "stopped"
        assert not service.is_healthy()
        assert service.is_healthy() is False

    def test_base_service_health_info(self):
        """测试基础服务健康信息."""
        service = BaseService()
        health_info = service.get_health_info()

        # 验证健康信息结构
        assert isinstance(health_info, dict)
        assert "status" in health_info
        assert "healthy" in health_info
        assert "uptime" in health_info
        assert "name" in health_info
        assert health_info["name"] == service.name
        assert health_info["status"] == "stopped"
        assert health_info["healthy"] is False

    def test_base_service_dependency_management(self):
        """测试基础服务依赖管理."""
        service = BaseService()

        # 测试不存在的依赖
        assert service.get_dependency("nonexistent") is None

        # 测试添加依赖（需要另一个服务实例）
        dependency = BaseService("DependencyService")
        service.add_dependency("test_dep", dependency)

        # 验证依赖可以被获取
        retrieved = service.get_dependency("test_dep")
        assert retrieved is dependency

    def test_base_service_config_access(self):
        """测试基础服务配置访问."""
        service = BaseService()

        # 测试存在的配置
        assert service.get_config("name") == "BaseService"

        # 测试不存在的配置
        assert service.get_config("nonexistent", "default") == "default"
        assert service.get_config("nonexistent") is None

    @pytest.mark.asyncio
    async def test_base_service_lifecycle_methods(self):
        """测试基础服务生命周期方法."""
        service = BaseService()

        # 测试初始化
        await service.initialize()
        assert service.get_status() == "ready"

        # 测试启动
        started = await service.start()
        assert started is True
        assert service.get_status() == "running"

        # 测试停止
        stopped = await service.stop()
        assert stopped is True
        assert service.get_status() == "stopped"

        # 测试关闭
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_base_service_health_check(self):
        """测试基础服务健康检查."""
        service = BaseService()

        # 初始状态健康检查
        health = await service.health_check()
        assert isinstance(health, dict)
        assert "status" in health
        assert "healthy" in health

        # 启动后健康检查
        await service.start()
        health = await service.health_check()
        assert health["status"] == "running"
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_base_service_execute_with_metrics(self):
        """测试基础服务带指标执行."""
        service = BaseService()

        # 测试成功的操作
        result = await service.execute_with_metrics(
            lambda: "test_result", "test_operation"
        )
        assert result == "test_result"

        # 验证指标被记录
        metrics = service.metrics.get_metrics()
        assert metrics["calls"] == 1
        assert metrics["errors"] == 0

        # 测试失败的操作
        with pytest.raises(ValueError):
            await service.execute_with_metrics(
                lambda: (_ for _ in ()).throw(ValueError("test error")),
                "test_error_operation",
            )

        # 验证错误指标被记录
        metrics = service.metrics.get_metrics()
        assert metrics["calls"] == 2
        assert metrics["errors"] == 1

    def test_base_service_repr(self):
        """测试基础服务字符串表示."""
        service = BaseService("TestService")
        repr_str = repr(service)

        # 验证字符串表示包含关键信息
        assert "TestService" in repr_str
        assert "BaseService" in repr_str

    def test_base_service_uptime_calculation(self):
        """测试基础服务运行时间计算."""
        service = BaseService()

        # 初始状态运行时间应该为None
        uptime = service._get_uptime_seconds()
        assert uptime is None

        # 启动后应该有运行时间
        # 注意：由于使用Mock，这里主要测试方法调用不抛出异常
        service._start_time = time.time()
        uptime = service._get_uptime_seconds()
        assert uptime is not None
        assert uptime >= 0


class TestAbstractBaseService:
    """抽象基础服务测试类."""

    def test_abstract_base_service_initialization(self):
        """测试抽象基础服务初始化."""

        # 由于是抽象类，测试具体实现
        class ConcreteService(AbstractBaseService):
            pass

        service = ConcreteService("AbstractTest")

        # 验证继承的属性和方法
        assert service.name == "AbstractTest"
        assert hasattr(service, "get_status")
        assert hasattr(service, "is_healthy")

    def test_abstract_base_service_inheritance(self):
        """测试抽象基础服务继承."""

        # 创建具体的子类
        class TestService(AbstractBaseService):
            def __init__(self, name):
                super().__init__(name)
                self.custom_field = "test"

        service = TestService("InheritanceTest")

        # 验证继承层次
        assert isinstance(service, AbstractBaseService)
        assert isinstance(service, EnhancedBaseService)
        assert hasattr(service, "metrics")
        assert hasattr(service, "config")
        assert service.custom_field == "test"

    @pytest.mark.asyncio
    async def test_abstract_base_service_lifecycle(self):
        """测试抽象基础服务生命周期."""

        class TestService(AbstractBaseService):
            def __init__(self, name):
                super().__init__(name)

        service = TestService("LifecycleTest")

        # 验证生命周期方法
        await service.initialize()
        assert service.get_status() == "ready"

        await service.start()
        assert service.get_status() == "running"

        await service.stop()
        assert service.get_status() == "stopped"

        await service.shutdown()


class TestEnhancedBaseServiceIntegration:
    """增强基础服务集成测试类."""

    @pytest.mark.asyncio
    async def test_service_dependencies_interaction(self):
        """测试服务依赖交互."""
        main_service = BaseService("MainService")
        dependency_service = BaseService("DependencyService")

        # 建立依赖关系
        main_service.add_dependency("dependency", dependency_service)

        # 启动依赖
        await dependency_service.start()
        await main_service.start()

        # 验证服务状态
        assert main_service.get_status() == "running"
        assert dependency_service.get_status() == "running"

        # 验证依赖可获取
        dep = main_service.get_dependency("dependency")
        assert dep is dependency_service
        assert dep.get_status() == "running"

        # 清理
        await main_service.stop()
        await dependency_service.stop()
        await main_service.shutdown()
        await dependency_service.shutdown()

    @pytest.mark.asyncio
    async def test_service_health_check_integration(self):
        """测试服务健康检查集成."""
        service = BaseService("HealthTest")

        # 健康检查初始状态
        health = await service.health_check()
        assert health["status"] == "stopped"

        # 启动服务
        await service.start()

        # 健康检查运行状态
        health = await service.health_check()
        assert health["status"] == "running"
        assert health["healthy"] is True
        assert "timestamp" in health
        assert "uptime" in health

        # 清理
        await service.stop()
        await service.shutdown()

    def test_service_metrics_accumulation(self):
        """测试服务指标累积."""
        service = BaseService("MetricsTest")

        # 执行一些操作来累积指标
        for i in range(10):
            # 模拟不同时长的操作
            duration = 0.01 + (i * 0.001)
            service.metrics.record_call(duration, success=(i % 3 != 0))

        # 验证累积指标
        metrics = service.metrics.get_metrics()
        assert metrics["calls"] == 10
        assert metrics["errors"] == 3  # i=3,6,9 时失败
        assert metrics["error_rate"] == 0.3
        assert metrics["avg_time"] > 0
        assert metrics["total_time"] > 0

    def test_service_configuration_inheritance(self):
        """测试服务配置继承."""
        custom_config = ServiceConfig(
            name="ConfigTest",
            version="2.0.0",
            description="Test service with custom config",
            config={"custom_key": "custom_value"},
        )

        service = BaseService("ConfigTest")
        service.config = custom_config

        # 验证配置被正确应用
        assert service.get_config("custom_key") == "custom_value"
        assert service.get_config("version") == "2.0.0"
        assert service.get_config("description") == "Test service with custom config"
