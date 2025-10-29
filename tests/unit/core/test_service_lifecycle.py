from datetime import datetime


from unittest.mock import AsyncMock, Mock, patch

# TODO: Consider creating a fixture for 62 repeated Mock creations
# TODO: Consider creating a fixture for 62 repeated Mock creations
"""
服务生命周期管理测试
Service Lifecycle Management Tests

测试src/core/service_lifecycle.py中定义的服务生命周期管理功能。
Tests service lifecycle management functionality defined in src/core/service_lifecycle.py.
"""


import pytest

# 导入要测试的模块
try:
    from src.core.service_lifecycle import (
        IServiceLifecycle,
        ServiceInfo,
        ServiceLifecycleError,
        ServiceLifecycleManager,
        ServiceState,
        get_lifecycle_manager,
        lifecycle_service,
    )

    SERVICE_LIFECYCLE_AVAILABLE = True
except ImportError:
    SERVICE_LIFECYCLE_AVAILABLE = False


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
@pytest.mark.unit
class TestServiceState:
    """服务状态枚举测试"""

    def test_service_state_values(self):
        """测试服务状态枚举值"""
        assert ServiceState.UNINITIALIZED.value == "uninitialized"
        assert ServiceState.INITIALIZING.value == "initializing"
        assert ServiceState.READY.value == "ready"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPING.value == "stopping"
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.ERROR.value == "error"
        assert ServiceState.DISPOSED.value == "disposed"

    def test_service_state_comparison(self):
        """测试服务状态比较"""
        state1 = ServiceState.RUNNING
        state2 = ServiceState.RUNNING
        state3 = ServiceState.STOPPED

        assert state1 == state2
        assert state1 != state3
        assert hash(state1) == hash(state2)
        assert hash(state1) != hash(state3)


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
class TestServiceInfo:
    """服务信息测试"""

    def test_service_info_creation(self):
        """测试服务信息创建"""
        instance = Mock()
        service_info = ServiceInfo(
            name="test_service", instance=instance, dependencies=["dep1", "dep2"]
        )

        assert service_info.name == "test_service"
        assert service_info.instance == instance
        assert service_info.state == ServiceState.UNINITIALIZED
        assert service_info.dependencies == ["dep1", "dep2"]
        assert service_info.dependents == []
        assert service_info.error_count == 0
        assert service_info.last_error is None
        assert isinstance(service_info.created_at, datetime)

    def test_service_info_with_string_dependency(self):
        """测试字符串依赖自动转换"""
        instance = Mock()
        service_info = ServiceInfo(
            name="test_service",
            instance=instance,
            dependencies="single_dep",  # 字符串而不是列表
        )

        assert service_info.dependencies == ["single_dep"]

    def test_service_info_timestamps(self):
        """测试服务信息时间戳"""
        instance = Mock()
        before_creation = datetime.utcnow()

        service_info = ServiceInfo(name="test_service", instance=instance)

        after_creation = datetime.utcnow()

        assert before_creation <= service_info.created_at <= after_creation
        assert service_info.started_at is None
        assert service_info.stopped_at is None

    def test_service_info_str_representation(self):
        """测试服务信息字符串表示"""
        instance = Mock()
        service_info = ServiceInfo(
            name="test_service", instance=instance, state=ServiceState.RUNNING
        )

        str_repr = str(service_info)
        assert "test_service" in str_repr
        assert "RUNNING" in str_repr


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
class TestIServiceLifecycle:
    """服务生命周期接口测试"""

    def test_interface_methods(self):
        """测试接口方法定义"""

        # 创建一个实现接口的测试类
        class TestService(IServiceLifecycle):
            def __init__(self):
                self.initialized = False
                self.started = False
                self.stopped = False
                self.cleaned = False
                self.healthy = True

            async def initialize(self) -> None:
                self.initialized = True

            async def start(self) -> None:
                self.started = True

            async def stop(self) -> None:
                self.stopped = True

            async def cleanup(self) -> None:
                self.cleaned = True

            def health_check(self) -> bool:
                return self.healthy

        service = TestService()

        assert isinstance(service, IServiceLifecycle)
        assert not service.initialized
        assert not service.started
        assert not service.stopped
        assert not service.cleaned
        assert service.healthy


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
class TestServiceLifecycleManager:
    """服务生命周期管理器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ServiceLifecycleManager()

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理管理器资源
        if hasattr(self.manager, "_shutdown_event"):
            self.manager._shutdown_event.set()
        if hasattr(self.manager, "_monitor_task") and self.manager._monitor_task:
            self.manager._monitor_task.cancel()

    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager._services == {}
        assert self.manager._start_order == []
        assert self.manager._stop_order == []
        assert hasattr(self.manager, "_lock")
        assert not self.manager._shutdown_event.is_set()
        assert self.manager._monitor_task is None

    def test_register_service_success(self):
        """测试成功注册服务"""
        instance = Mock()

        self.manager.register_service("test_service", instance, ["dep1"])

        assert "test_service" in self.manager._services
        service_info = self.manager._services["test_service"]
        assert service_info.name == "test_service"
        assert service_info.instance == instance
        assert service_info.dependencies == ["dep1"]

    def test_register_service_duplicate(self):
        """测试注册重复服务"""
        instance = Mock()

        self.manager.register_service("test_service", instance)

        with pytest.raises(ServiceLifecycleError, match="服务已注册: test_service"):
            self.manager.register_service("test_service", Mock())

    def test_register_service_with_circular_dependency(self):
        """测试注册循环依赖服务"""
        # 先注册服务A，并让它依赖服务B（B还未注册）
        Mock()
        # 手动设置A依赖B
        self.manager._services["service_a"] = Mock(dependencies=["service_b"])

        # 现在注册服务B，让它依赖A，形成循环依赖
        instance_b = Mock()
        with pytest.raises(ServiceLifecycleError, match="检测到循环依赖"):
            self.manager.register_service("service_b", instance_b, ["service_a"])

    def test_unregister_service_success(self):
        """测试成功注销服务"""
        instance = Mock()
        self.manager.register_service("test_service", instance)

        self.manager.unregister_service("test_service")

        assert "test_service" not in self.manager._services

    def test_unregister_nonexistent_service(self):
        """测试注销不存在的服务"""
        with pytest.raises(ServiceLifecycleError, match="服务未注册: nonexistent"):
            self.manager.unregister_service("nonexistent")

    def test_unregister_service_with_running_dependents(self):
        """测试注销有运行依赖的服务"""
        # 创建两个服务，service_b 依赖 service_a
        instance_a = Mock()
        instance_b = Mock()

        self.manager.register_service("service_a", instance_a)
        self.manager.register_service("service_b", instance_b, ["service_a"])

        # 设置service_b为运行状态
        self.manager._services["service_b"].state = ServiceState.RUNNING

        # 尝试注销service_a应该失败
        with pytest.raises(ServiceLifecycleError, match="无法注销服务 service_a"):
            self.manager.unregister_service("service_a")

    def test_get_service_state(self):
        """测试获取服务状态"""
        instance = Mock()
        self.manager.register_service("test_service", instance)

        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.UNINITIALIZED

    def test_get_state_nonexistent_service(self):
        """测试获取不存在服务的状态"""
        with pytest.raises(ServiceLifecycleError, match="服务未注册: nonexistent"):
            self.manager.get_service_state("nonexistent")

    def test_get_service_info(self):
        """测试获取服务信息"""
        instance = Mock()
        self.manager.register_service("test_service", instance)

        info = self.manager.get_service_info("test_service")
        assert info.name == "test_service"
        assert info.instance == instance

    def test_get_info_nonexistent_service(self):
        """测试获取不存在服务的信息"""
        with pytest.raises(ServiceLifecycleError, match="服务未注册: nonexistent"):
            self.manager.get_service_info("nonexistent")

    def test_get_all_services(self):
        """测试获取所有服务信息"""
        instance1 = Mock()
        instance2 = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2)

        all_services = self.manager.get_all_services()
        assert len(all_services) == 2
        assert "service1" in all_services
        assert "service2" in all_services

    def test_get_running_services(self):
        """测试获取正在运行的服务"""
        instance1 = Mock()
        instance2 = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2)

        # 设置service1为运行状态
        self.manager._services["service1"].state = ServiceState.RUNNING

        running_services = self.manager.get_running_services()
        assert running_services == ["service1"]

    @pytest.mark.asyncio
    async def test_initialize_service_success(self):
        """测试成功初始化服务"""
        # 创建一个有initialize方法的模拟服务
        instance = Mock()
        instance.initialize = Mock()

        self.manager.register_service("test_service", instance)
        await self.manager.initialize_service("test_service")

        assert instance.initialize.called
        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.READY

    @pytest.mark.asyncio
    async def test_initialize_service_with_lifecycle_interface(self):
        """测试实现生命周期接口的服务初始化"""

        class TestService(IServiceLifecycle):
            def __init__(self):
                self.initialized = False

            async def initialize(self) -> None:
                self.initialized = True

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

            def health_check(self) -> bool:
                return True

        service = TestService()
        self.manager.register_service("test_service", service)

        await self.manager.initialize_service("test_service")

        assert service.initialized
        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.READY

    @pytest.mark.asyncio
    async def test_initialize_service_with_dependencies(self):
        """测试有依赖的服务初始化"""
        # 创建依赖服务
        dep_instance = Mock()
        dep_instance.initialize = Mock()

        # 创建主服务
        main_instance = Mock()
        main_instance.initialize = Mock()

        self.manager.register_service("dependency", dep_instance)
        self.manager.register_service("main", main_instance, ["dependency"])

        await self.manager.initialize_service("main")

        # 依赖服务应该先被初始化
        dep_instance.initialize.assert_called_once()
        main_instance.initialize.assert_called_once()

        assert self.manager.get_service_state("dependency") == ServiceState.READY
        assert self.manager.get_service_state("main") == ServiceState.READY

    @pytest.mark.asyncio
    async def test_initialize_service_failure(self):
        """测试服务初始化失败"""
        instance = Mock()
        instance.initialize = Mock(side_effect=ValueError("初始化失败"))

        self.manager.register_service("test_service", instance)

        with pytest.raises(ServiceLifecycleError, match="服务初始化失败"):
            await self.manager.initialize_service("test_service")

        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.ERROR

        service_info = self.manager.get_service_info("test_service")
        assert service_info.error_count == 1
        assert isinstance(service_info.last_error, ValueError)

    @pytest.mark.asyncio
    async def test_start_service_success(self):
        """测试成功启动服务"""
        instance = Mock()
        instance.start = Mock()

        self.manager.register_service("test_service", instance)
        await self.manager.start_service("test_service")

        assert instance.start.called
        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.RUNNING
        assert self.manager.get_service_info("test_service").started_at is not None

    @pytest.mark.asyncio
    async def test_start_already_running_service(self):
        """测试启动已在运行的服务"""
        instance = Mock()

        self.manager.register_service("test_service", instance)
        # 手动设置为运行状态
        self.manager._services["test_service"].state = ServiceState.RUNNING

        await self.manager.start_service("test_service")

        # 应该跳过启动
        instance.start.assert_not_called()
        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_service_success(self):
        """测试成功停止服务"""
        instance = Mock()
        instance.stop = Mock()

        self.manager.register_service("test_service", instance)
        # 先设置为运行状态
        self.manager._services["test_service"].state = ServiceState.RUNNING

        await self.manager.stop_service("test_service")

        assert instance.stop.called
        state = self.manager.get_service_state("test_service")
        assert state == ServiceState.STOPPED
        assert self.manager.get_service_info("test_service").stopped_at is not None

    @pytest.mark.asyncio
    async def test_stop_not_running_service(self):
        """测试停止未运行的服务"""
        instance = Mock()

        self.manager.register_service("test_service", instance)

        await self.manager.stop_service("test_service")

        # 应该跳过停止
        instance.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_all_services(self):
        """测试启动所有服务"""
        # 创建有依赖关系的服务
        instance1 = Mock()
        instance1.start = Mock()

        instance2 = Mock()
        instance2.start = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2, ["service1"])

        await self.manager.start_all_services()

        # 验证两个服务都被启动
        instance1.start.assert_called_once()
        instance2.start.assert_called_once()

        # 验证状态
        assert self.manager.get_service_state("service1") == ServiceState.RUNNING
        assert self.manager.get_service_state("service2") == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_all_services(self):
        """测试停止所有服务"""
        # 创建两个运行中的服务
        instance1 = Mock()
        instance1.stop = Mock()

        instance2 = Mock()
        instance2.stop = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2)

        # 设置为运行状态
        self.manager._services["service1"].state = ServiceState.RUNNING
        self.manager._services["service2"].state = ServiceState.RUNNING

        # 首先计算启动顺序，这样停止顺序才会被设置
        self.manager._calculate_startup_order()
        self.manager._calculate_stop_order()

        await self.manager.stop_all_services()

        # 验证都被停止
        instance1.stop.assert_called_once()
        instance2.stop.assert_called_once()

        # 验证状态更新为STOPPED
        assert self.manager.get_service_state("service1") == ServiceState.STOPPED
        assert self.manager.get_service_state("service2") == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_health_check_single_service(self):
        """测试单个服务健康检查"""
        instance = Mock()
        instance.health_check = Mock(return_value=True)

        self.manager.register_service("test_service", instance)
        self.manager._services["test_service"].state = ServiceState.RUNNING

        results = await self.manager.health_check("test_service")

        assert results == {"test_service": True}
        instance.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_async(self):
        """测试异步健康检查"""
        instance = Mock()
        instance.health_check = AsyncMock(return_value=True)

        self.manager.register_service("test_service", instance)
        self.manager._services["test_service"].state = ServiceState.RUNNING

        results = await self.manager.health_check("test_service")

        assert results == {"test_service": True}
        instance.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_not_running(self):
        """测试未运行服务的健康检查"""
        instance = Mock()

        self.manager.register_service("test_service", instance)
        # 服务未运行

        results = await self.manager.health_check("test_service")

        assert results == {"test_service": False}

    @pytest.mark.asyncio
    async def test_health_check_all_services(self):
        """测试所有服务健康检查"""
        instance1 = Mock()
        instance1.health_check = Mock(return_value=True)

        instance2 = Mock()
        instance2.health_check = Mock(return_value=False)

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2)

        # 设置为运行状态
        self.manager._services["service1"].state = ServiceState.RUNNING
        self.manager._services["service2"].state = ServiceState.RUNNING

        results = await self.manager.health_check()

        assert results == {"service1": True, "service2": False}

    def test_start_monitoring(self):
        """测试启动监控"""
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = Mock()
            mock_create_task.return_value = mock_task

            self.manager.start_monitoring(interval=10.0)

            assert mock_create_task.called
            assert self.manager._monitor_task == mock_task

    def test_start_monitoring_already_running(self):
        """测试启动已在运行的监控"""
        # 创建一个模拟的任务
        mock_task = Mock()
        mock_task.done.return_value = False
        self.manager._monitor_task = mock_task

        self.manager.start_monitoring()

        # 应该不创建新任务
        assert self.manager._monitor_task == mock_task

    def test_stop_monitoring(self):
        """测试停止监控"""
        # 创建一个模拟的任务
        mock_task = Mock()
        self.manager._monitor_task = mock_task

        self.manager.stop_monitoring()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """测试关闭管理器"""
        # 创建一些模拟服务
        instance = Mock()
        instance.stop = Mock()
        instance.cleanup = Mock()

        self.manager.register_service("test_service", instance)
        self.manager._services["test_service"].state = ServiceState.RUNNING

        # 计算停止顺序
        self.manager._calculate_startup_order()
        self.manager._calculate_stop_order()

        # 启动监控
        mock_task = Mock()
        self.manager._monitor_task = mock_task

        await self.manager.shutdown()

        # 验证清理调用
        mock_task.cancel.assert_called_once()
        assert self.manager._shutdown_event.is_set()
        instance.stop.assert_called_once()
        instance.cleanup.assert_called_once()

        # 验证服务状态
        assert self.manager.get_service_state("test_service") == ServiceState.STOPPED

    def test_calculate_startup_order(self):
        """测试计算启动顺序（拓扑排序）"""
        # 创建有依赖关系的服务
        # service3 依赖 service1 和 service2
        # service2 依赖 service1
        instance1 = Mock()
        instance2 = Mock()
        instance3 = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2, ["service1"])
        self.manager.register_service("service3", instance3, ["service1", "service2"])

        self.manager._calculate_startup_order()

        # 验证启动顺序正确
        assert self.manager._start_order == ["service1", "service2", "service3"]

    def test_calculate_startup_order_with_circular_dependency(self):
        """测试计算启动顺序时的循环依赖检测"""
        # 创建循环依赖
        instance1 = Mock()
        instance2 = Mock()

        self.manager.register_service("service1", instance1)
        self.manager.register_service("service2", instance2, ["service1"])

        # 手动创建循环依赖
        self.manager._services["service1"].dependencies = ["service2"]

        with pytest.raises(ServiceLifecycleError, match="检测到循环依赖"):
            self.manager._calculate_startup_order()

    def test_calculate_stop_order(self):
        """测试计算停止顺序"""
        # 设置启动顺序
        self.manager._start_order = ["service1", "service2", "service3"]

        self.manager._calculate_stop_order()

        # 停止顺序应该是启动顺序的逆序
        assert self.manager._stop_order == ["service3", "service2", "service1"]


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
class TestGlobalLifecycleManager:
    """全局生命周期管理器测试"""

    def test_get_lifecycle_manager_singleton(self):
        """测试获取全局生命周期管理器（单例模式）"""
        manager1 = get_lifecycle_manager()
        manager2 = get_lifecycle_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ServiceLifecycleManager)

    @patch("src.core.service_lifecycle._default_lifecycle_manager", None)
    def test_get_lifecycle_manager_creates_new(self):
        """测试获取生命周期管理器时创建新实例"""
        # 模拟全局变量为None的情况
        import src.core.service_lifecycle

        original_manager = src.core.service_lifecycle._default_lifecycle_manager
        src.core.service_lifecycle._default_lifecycle_manager = None

        try:
            manager = get_lifecycle_manager()
            assert isinstance(manager, ServiceLifecycleManager)
            assert src.core.service_lifecycle._default_lifecycle_manager is manager
        finally:
            # 恢复原始状态
            src.core.service_lifecycle._default_lifecycle_manager = original_manager


@pytest.mark.skipif(
    not SERVICE_LIFECYCLE_AVAILABLE, reason="Service lifecycle module not available"
)
class TestLifecycleDecorator:
    """生命周期装饰器测试"""

    def test_lifecycle_decorator_with_name(self):
        """测试带名称的生命周期装饰器"""

        @lifecycle_service(name="decorated_service", dependencies=["dep1"])
        class TestService:
            def __init__(self):
                self.value = 42

        # 创建实例应该自动注册到管理器
        manager = get_lifecycle_manager()
        service = TestService()

        # 验证服务已注册
        assert "decorated_service" in manager._services
        service_info = manager.get_service_info("decorated_service")
        assert service_info.instance is service
        assert service_info.dependencies == ["dep1"]
        assert service.value == 42

    def test_lifecycle_decorator_without_name(self):
        """测试不带名称的生命周期装饰器"""

        @lifecycle_service()
        class TestService:
            def __init__(self):
                self.value = 42

        manager = get_lifecycle_manager()
        service = TestService()

        # 验证使用类名作为服务名
        assert "TestService" in manager._services
        service_info = manager.get_service_info("TestService")
        assert service_info.instance is service

    def test_lifecycle_decorator_without_dependencies(self):
        """测试不带依赖的生命周期装饰器"""

        @lifecycle_service(name="simple_service")
        class TestService:
            def __init__(self):
                self.value = 42

        manager = get_lifecycle_manager()
        TestService()

        service_info = manager.get_service_info("simple_service")
        assert service_info.dependencies == []

    def test_lifecycle_decorator_preserves_init(self):
        """测试装饰器保持原始初始化方法"""

        @lifecycle_service(name="preserved_service")
        class TestService:
            def __init__(self, custom_arg):
                self.custom_arg = custom_arg

        service = TestService("test_value")

        assert service.custom_arg == "test_value"

        manager = get_lifecycle_manager()
        service_info = manager.get_service_info("preserved_service")
        assert service_info.instance is service
