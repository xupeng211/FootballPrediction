"""
适配器注册表测试
Tests for Adapter Registry

测试src.adapters.registry模块的适配器注册表功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

# 测试导入
try:
    from src.adapters.registry import AdapterRegistry, RegistryStatus, adapter_registry
    from src.adapters.base import Adapter, AdapterStatus
    from src.adapters.factory import AdapterFactory, AdapterConfig, AdapterGroupConfig

    REGISTRY_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    REGISTRY_AVAILABLE = False
    AdapterRegistry = None
    RegistryStatus = None
    adapter_registry = None
    Adapter = None
    AdapterStatus = None
    AdapterFactory = None
    AdapterConfig = None
    AdapterGroupConfig = None


@pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry module not available")
@pytest.mark.asyncio
class TestAdapterRegistry:
    """适配器注册表测试"""

    @pytest.fixture
    def mock_factory(self):
        """创建模拟工厂"""
        factory = Mock(spec=AdapterFactory)
        return factory

    @pytest.fixture
    def registry(self, mock_factory):
        """创建注册表实例"""
        return AdapterRegistry(factory=mock_factory)

    async def test_registry_creation(self, registry):
        """测试：注册表创建"""
        assert registry is not None
        assert registry.status == RegistryStatus.INACTIVE
        assert registry.adapters == {}
        assert registry.groups == {}
        assert registry.health_check_interval == 60.0

    async def test_registry_creation_with_default_factory(self):
        """测试：使用默认工厂创建注册表"""
        registry = AdapterRegistry()
        assert registry.factory is not None
        assert isinstance(registry.factory, AdapterFactory)

    async def test_initialize(self, registry):
        """测试：初始化注册表"""
        assert registry.status == RegistryStatus.INACTIVE

        await registry.initialize()

        assert registry.status == RegistryStatus.ACTIVE
        assert registry._health_check_task is not None

        # 清理
        await registry.shutdown()

    async def test_initialize_already_initialized(self, registry):
        """测试：初始化已初始化的注册表"""
        await registry.initialize()

        with pytest.raises(RuntimeError, match="Registry already initialized"):
            await registry.initialize()

        # 清理
        await registry.shutdown()

    async def test_shutdown(self, registry):
        """测试：关闭注册表"""
        await registry.initialize()
        assert registry.status == RegistryStatus.ACTIVE

        await registry.shutdown()

        assert registry.status == RegistryStatus.INACTIVE

    async def test_shutdown_when_shutting_down(self, registry):
        """测试：关闭正在关闭的注册表"""
        await registry.initialize()
        registry.status = RegistryStatus.SHUTTING_DOWN

        # 应该不会抛出异常
        await registry.shutdown()

    async def test_shutdown_with_adapters(self, registry):
        """测试：关闭注册表时清理适配器"""
        # 创建模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.cleanup = AsyncMock()
        adapter2 = Mock(spec=Adapter)
        adapter2.cleanup = AsyncMock()

        registry.adapters["test1"] = adapter1
        registry.adapters["test2"] = adapter2

        await registry.initialize()
        await registry.shutdown()

        # 验证cleanup被调用
        adapter1.cleanup.assert_called_once()
        adapter2.cleanup.assert_called_once()

    async def test_register_adapter(self, registry):
        """测试：注册适配器"""
        await registry.initialize()

        # 创建配置和模拟适配器
        _config = AdapterConfig(name="test_adapter", adapter_type="test")
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock()
        registry.factory.create_adapter.return_value = mock_adapter

        # 注册适配器
        adapter = await registry.register_adapter(_config)

        assert adapter is not None
        assert "test_adapter" in registry.adapters
        mock_adapter.initialize.assert_called_once()

        # 清理
        await registry.shutdown()

    async def test_register_adapter_not_active(self, registry):
        """测试：在非活跃状态下注册适配器"""
        _config = AdapterConfig(name="test", adapter_type="test")

        with pytest.raises(RuntimeError, match="Registry not active"):
            await registry.register_adapter(_config)

    async def test_register_adapter_already_exists(self, registry):
        """测试：注册已存在的适配器"""
        await registry.initialize()

        # 创建配置
        _config = AdapterConfig(name="test_adapter", adapter_type="test")
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock()
        registry.factory.create_adapter.return_value = mock_adapter

        # 第一次注册
        await registry.register_adapter(_config)

        # 第二次注册应该失败
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_adapter(_config)

        # 清理
        await registry.shutdown()

    async def test_unregister_adapter(self, registry):
        """测试：注销适配器"""
        await registry.initialize()

        # 创建并注册适配器
        _config = AdapterConfig(name="test_adapter", adapter_type="test")
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock()
        mock_adapter.cleanup = AsyncMock()
        registry.factory.create_adapter.return_value = mock_adapter

        await registry.register_adapter(_config)
        assert "test_adapter" in registry.adapters

        # 注销适配器
        await registry.unregister_adapter("test_adapter")
        assert "test_adapter" not in registry.adapters
        mock_adapter.cleanup.assert_called_once()

        # 清理
        await registry.shutdown()

    async def test_register_group(self, registry):
        """测试：注册适配器组"""
        await registry.initialize()

        # 创建组配置
        group_config = AdapterGroupConfig(name="test_group", adapters=[])
        mock_group = Mock(spec=Adapter)
        mock_group.initialize = AsyncMock()
        registry.factory.create_adapter_group.return_value = mock_group

        # 注册组
        group = await registry.register_group(group_config)

        assert group is not None
        assert "test_group" in registry.groups
        mock_group.initialize.assert_called_once()

        # 清理
        await registry.shutdown()

    async def test_register_group_already_exists(self, registry):
        """测试：注册已存在的组"""
        await registry.initialize()

        group_config = AdapterGroupConfig(name="test_group", adapters=[])
        mock_group = Mock(spec=Adapter)
        mock_group.initialize = AsyncMock()
        registry.factory.create_adapter_group.return_value = mock_group

        # 第一次注册
        await registry.register_group(group_config)

        # 第二次注册应该失败
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_group(group_config)

        # 清理
        await registry.shutdown()

    async def test_unregister_group(self, registry):
        """测试：注销适配器组"""
        await registry.initialize()

        # 创建并注册组
        group_config = AdapterGroupConfig(name="test_group", adapters=[])
        mock_group = Mock(spec=Adapter)
        mock_group.initialize = AsyncMock()
        mock_group.cleanup = AsyncMock()
        registry.factory.create_adapter_group.return_value = mock_group

        await registry.register_group(group_config)
        assert "test_group" in registry.groups

        # 注销组
        await registry.unregister_group("test_group")
        assert "test_group" not in registry.groups
        mock_group.cleanup.assert_called_once()

        # 清理
        await registry.shutdown()

    def test_get_adapter(self, registry):
        """测试：获取适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        registry.adapters["test_adapter"] = mock_adapter

        # 获取适配器
        adapter = registry.get_adapter("test_adapter")
        assert adapter is mock_adapter

        # 获取不存在的适配器
        adapter = registry.get_adapter("nonexistent")
        assert adapter is None

    def test_get_group(self, registry):
        """测试：获取适配器组"""
        # 创建模拟组
        mock_group = Mock(spec=Adapter)
        registry.groups["test_group"] = mock_group

        # 获取组
        group = registry.get_group("test_group")
        assert group is mock_group

        # 获取不存在的组
        group = registry.get_group("nonexistent")
        assert group is None

    def test_list_adapters(self, registry):
        """测试：列出所有适配器"""
        registry.adapters["adapter1"] = Mock()
        registry.adapters["adapter2"] = Mock()

        adapters = registry.list_adapters()
        assert set(adapters) == {"adapter1", "adapter2"}

    def test_list_groups(self, registry):
        """测试：列出所有组"""
        registry.groups["group1"] = Mock()
        registry.groups["group2"] = Mock()

        groups = registry.list_groups()
        assert set(groups) == {"group1", "group2"}

    def test_get_adapters_by_type(self, registry):
        """测试：按类型获取适配器"""
        # 创建不同类型的模拟适配器
        adapter1 = Mock()
        adapter1.__class__.__name__ = "TestAdapter"
        adapter2 = Mock()
        adapter2.__class__.__name__ = "OtherAdapter"
        adapter3 = Mock()
        adapter3.__class__.__name__ = "TestAdapter"

        registry.adapters["test1"] = adapter1
        registry.adapters["other"] = adapter2
        registry.adapters["test2"] = adapter3

        # 按类型获取
        test_adapters = registry.get_adapters_by_type("TestAdapter")
        assert len(test_adapters) == 2
        assert adapter1 in test_adapters
        assert adapter3 in test_adapters

    def test_get_active_adapters(self, registry):
        """测试：获取活跃的适配器"""
        # 创建不同状态的模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.status = AdapterStatus.ACTIVE
        adapter2 = Mock(spec=Adapter)
        adapter2.status = AdapterStatus.INACTIVE
        adapter3 = Mock(spec=Adapter)
        adapter3.status = AdapterStatus.ACTIVE

        registry.adapters["active1"] = adapter1
        registry.adapters["inactive"] = adapter2
        registry.adapters["active2"] = adapter3

        # 获取活跃适配器
        active_adapters = registry.get_active_adapters()
        assert len(active_adapters) == 2
        assert adapter1 in active_adapters
        assert adapter3 in active_adapters

    def test_get_inactive_adapters(self, registry):
        """测试：获取非活跃的适配器"""
        # 创建不同状态的模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.status = AdapterStatus.ACTIVE
        adapter2 = Mock(spec=Adapter)
        adapter2.status = AdapterStatus.INACTIVE
        adapter3 = Mock(spec=Adapter)
        adapter3.status = AdapterStatus.ERROR

        registry.adapters["active"] = adapter1
        registry.adapters["inactive"] = adapter2
        registry.adapters["error"] = adapter3

        # 获取非活跃适配器
        inactive_adapters = registry.get_inactive_adapters()
        assert len(inactive_adapters) == 2
        assert adapter2 in inactive_adapters
        assert adapter3 in inactive_adapters

    async def test_enable_adapter(self, registry):
        """测试：启用适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock()
        registry.adapters["test_adapter"] = mock_adapter

        # 启用适配器
        _result = await registry.enable_adapter("test_adapter")
        assert _result is True
        mock_adapter.initialize.assert_called_once()

    async def test_enable_adapter_not_found(self, registry):
        """测试：启用不存在的适配器"""
        _result = await registry.enable_adapter("nonexistent")
        assert _result is False

    async def test_enable_adapter_failure(self, registry):
        """测试：启用适配器失败"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock(side_effect=ValueError("Failed"))
        registry.adapters["test_adapter"] = mock_adapter

        # 启用应该失败
        _result = await registry.enable_adapter("test_adapter")
        assert _result is False

    async def test_disable_adapter(self, registry):
        """测试：禁用适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        registry.adapters["test_adapter"] = mock_adapter

        # 禁用适配器
        _result = await registry.disable_adapter("test_adapter")
        assert _result is True
        mock_adapter.cleanup.assert_called_once()
        assert mock_adapter.status == AdapterStatus.INACTIVE

    async def test_disable_adapter_not_found(self, registry):
        """测试：禁用不存在的适配器"""
        _result = await registry.disable_adapter("nonexistent")
        assert _result is False

    async def test_restart_adapter(self, registry):
        """测试：重启适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        mock_adapter.initialize = AsyncMock()
        registry.adapters["test_adapter"] = mock_adapter

        # 重启适配器
        _result = await registry.restart_adapter("test_adapter")
        assert _result is True
        mock_adapter.cleanup.assert_called_once()
        mock_adapter.initialize.assert_called_once()

    async def test_restart_adapter_not_found(self, registry):
        """测试：重启不存在的适配器"""
        _result = await registry.restart_adapter("nonexistent")
        assert _result is False

    async def test_restart_adapter_failure(self, registry):
        """测试：重启适配器失败"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        mock_adapter.initialize = AsyncMock(side_effect=ValueError("Failed"))
        registry.adapters["test_adapter"] = mock_adapter

        # 重启应该失败
        _result = await registry.restart_adapter("test_adapter")
        assert _result is False

    @patch("asyncio.sleep")
    async def test_health_check_loop(self, mock_sleep, registry):
        """测试：健康检查循环"""
        await registry.initialize()

        # 模拟健康检查任务被取消
        registry._health_check_task.cancel()

        # 等待任务被取消
        with pytest.raises(asyncio.CancelledError):
            await registry._health_check_task

        await registry.shutdown()


@pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry module not available")
class TestRegistryStatus:
    """注册表状态测试"""

    def test_registry_status_values(self):
        """测试：注册表状态值"""
        assert RegistryStatus.ACTIVE.value == "active"
        assert RegistryStatus.INACTIVE.value == "inactive"
        assert RegistryStatus.SHUTTING_DOWN.value == "shutting_down"


@pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry module not available")
class TestGlobalRegistry:
    """全局注册表测试"""

    def test_global_registry_exists(self):
        """测试：全局注册表实例存在"""
        assert adapter_registry is not None
        assert isinstance(adapter_registry, AdapterRegistry)


@pytest.mark.skipif(REGISTRY_AVAILABLE, reason="Registry module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not REGISTRY_AVAILABLE
        assert True  # Basic assertion - consider enhancing


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if REGISTRY_AVAILABLE:
        from src.adapters.registry import AdapterRegistry, RegistryStatus

        assert AdapterRegistry is not None
        assert RegistryStatus is not None


def test_enum_values():
    """测试：枚举值"""
    if REGISTRY_AVAILABLE:
        # 验证RegistryStatus是枚举
        assert hasattr(RegistryStatus, "__members__")
        members = RegistryStatus.__members__
        assert "ACTIVE" in members
        assert "INACTIVE" in members
        assert "SHUTTING_DOWN" in members


# 补充测试以达到更高覆盖率
@pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry module not available")
@pytest.mark.asyncio
class TestRegistryAdditionalCoverage:
    """补充注册表测试以达到更高覆盖率"""

    @pytest.fixture
    def mock_factory(self):
        """创建模拟工厂"""
        factory = Mock(spec=AdapterFactory)
        return factory

    @pytest.fixture
    def registry(self, mock_factory):
        """创建注册表实例"""
        return AdapterRegistry(factory=mock_factory)

    async def test_health_check_loop_with_error(self, registry):
        """测试健康检查循环中遇到错误"""
        await registry.initialize()

        # 模拟健康检查抛出异常
        with patch.object(registry, '_perform_health_checks', side_effect=ValueError("Health check failed")):
            with patch('asyncio.sleep') as mock_sleep:
                # 取消任务以避免无限循环
                registry._health_check_task.cancel()

                try:
                    await registry._health_check_task
                except asyncio.CancelledError:
                    pass  # 预期的取消异常

                await registry.shutdown()

    async def test_perform_health_checks_success(self, registry):
        """测试执行健康检查成功"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.health_check = AsyncMock(return_value=True)
        registry.adapters["test_adapter"] = mock_adapter

        # 执行健康检查
        await registry._perform_health_checks()

        # 验证健康检查被调用
        mock_adapter.health_check.assert_called_once()

    async def test_perform_health_checks_with_failure(self, registry):
        """测试执行健康检查时适配器失败"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.health_check = AsyncMock(side_effect=ValueError("Health check failed"))
        registry.adapters["test_adapter"] = mock_adapter

        # 执行健康检查
        await registry._perform_health_checks()

        # 验证健康检查被调用
        mock_adapter.health_check.assert_called_once()

    async def test_perform_health_checks_group_failure(self, registry):
        """测试执行健康检查时组适配器失败"""
        # 创建模拟组适配器
        mock_group = Mock(spec=Adapter)
        mock_group.health_check = AsyncMock(side_effect=TypeError("Group check failed"))
        registry.groups["test_group"] = mock_group

        # 执行健康检查
        await registry._perform_health_checks()

        # 验证健康检查被调用
        mock_group.health_check.assert_called_once()

    async def test_get_health_status_empty(self, registry):
        """测试获取空注册表的健康状态"""
        await registry.initialize()

        status = await registry.get_health_status()

        assert isinstance(status, dict)
        assert "registry_status" in status
        assert "total_adapters" in status
        assert "active_adapters" in status
        assert "inactive_adapters" in status
        assert "total_groups" in status
        assert "last_health_check" in status
        assert "adapters" in status
        assert "groups" in status
        assert status["total_adapters"] == 0
        assert status["active_adapters"] == 0
        assert status["inactive_adapters"] == 0
        assert status["total_groups"] == 0
        assert len(status["adapters"]) == 0
        assert len(status["groups"]) == 0

        await registry.shutdown()

    async def test_get_health_status_with_adapters(self, registry):
        """测试获取包含适配器的注册表健康状态"""
        await registry.initialize()

        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.status = AdapterStatus.ACTIVE
        mock_adapter.get_metrics.return_value = {"requests": 10, "success_rate": 0.95}
        registry.adapters["test_adapter"] = mock_adapter

        status = await registry.get_health_status()

        assert "test_adapter" in status["adapters"]
        assert status["adapters"]["test_adapter"]["status"] == "active"
        assert "metrics" in status["adapters"]["test_adapter"]

        await registry.shutdown()

    async def test_get_metrics_summary_empty(self, registry):
        """测试获取空注册表的指标摘要"""
        summary = registry.get_metrics_summary()

        assert isinstance(summary, dict)
        assert "total_requests" in summary
        assert "total_successful" in summary
        assert "total_failed" in summary
        assert "adapter_types" in summary
        assert summary["total_requests"] == 0
        assert summary["total_successful"] == 0
        assert summary["total_failed"] == 0

    async def test_find_best_adapter_no_candidates(self, registry):
        """测试查找最佳适配器没有候选"""
        await registry.initialize()

        best_adapter = await registry.find_best_adapter("nonexistent-type")

        assert best_adapter is None

        await registry.shutdown()

    def test_registry_properties(self, registry):
        """测试注册表属性"""
        assert hasattr(registry, 'health_check_interval')
        assert isinstance(registry.health_check_interval, float)
        assert registry.health_check_interval > 0

        assert hasattr(registry, 'adapters')
        assert isinstance(registry.adapters, dict)

        assert hasattr(registry, 'groups')
        assert isinstance(registry.groups, dict)

        assert hasattr(registry, 'factory')
        assert registry.factory is not None

        assert hasattr(registry, '_metrics_collector')
        assert registry._metrics_collector is None

        assert hasattr(registry, '_health_check_task')
        assert registry._health_check_task is None

    def test_enable_metrics_collection(self, registry):
        """测试启用指标收集"""
        registry.enable_metrics_collection()

        assert registry._metrics_collector is not None
        assert "start_time" in registry._metrics_collector
        assert "health_checks" in registry._metrics_collector
        assert "adapter_failures" in registry._metrics_collector

    def test_disable_metrics_collection(self, registry):
        """测试禁用指标收集"""
        # 先启用
        registry.enable_metrics_collection()
        assert registry._metrics_collector is not None

        # 再禁用
        registry.disable_metrics_collection()
        assert registry._metrics_collector is None

    async def test_get_adapters_by_type(self, registry):
        """测试按类型获取适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.name = "test_adapter"
        mock_adapter.status = AdapterStatus.ACTIVE
        # 设置类名以匹配get_adapters_by_type的逻辑（它比较__class__.__name__）
        mock_adapter.__class__.__name__ = "api-football"

        registry.factory.create_adapter.return_value = mock_adapter

        # 注册适配器
        mock_config = Mock(spec=AdapterConfig)
        mock_config.name = "test_adapter"
        mock_config.adapter_type = "api-football"

        registry.factory.create_adapter.return_value = mock_adapter
        registry.adapters["test_adapter"] = mock_adapter

        # 获取特定类型的适配器（使用类名而不是adapter_type）
        adapters = registry.get_adapters_by_type("api-football")
        assert len(adapters) == 1
        assert "test_adapter" in [a.name for a in adapters]

    def test_registry_properties(self, registry):
        """测试注册表属性"""
        assert hasattr(registry, 'health_check_interval')
        assert isinstance(registry.health_check_interval, float)
        assert registry.health_check_interval > 0

        assert hasattr(registry, 'adapters')
        assert isinstance(registry.adapters, dict)

        assert hasattr(registry, 'groups')
        assert isinstance(registry.groups, dict)

        assert hasattr(registry, 'factory')
        assert registry.factory is not None

        assert hasattr(registry, '_metrics_collector')
        assert registry._metrics_collector is None

        assert hasattr(registry, '_health_check_task')
        assert registry._health_check_task is None

    def test_registry_status_transitions(self, registry):
        """测试注册表状态转换"""
        # 初始状态
        assert registry.status == RegistryStatus.INACTIVE

        # 这些操作需要在异步环境中测试，但我们可以验证状态枚举
        assert hasattr(registry, 'status')
        assert isinstance(registry.status, RegistryStatus)

    def test_health_check_interval_property(self, registry):
        """测试健康检查间隔属性"""
        assert hasattr(registry, 'health_check_interval')
        assert isinstance(registry.health_check_interval, float)
        assert registry.health_check_interval > 0

    def test_adapters_and_groups_properties(self, registry):
        """测试适配器和组属性"""
        assert hasattr(registry, 'adapters')
        assert hasattr(registry, 'groups')
        assert isinstance(registry.adapters, dict)
        assert isinstance(registry.groups, dict)
        assert len(registry.adapters) == 0
        assert len(registry.groups) == 0

    def test_factory_property(self, registry):
        """测试工厂属性"""
        assert hasattr(registry, 'factory')
        assert registry.factory is not None

    def test_metrics_collector_initial_state(self, registry):
        """测试指标收集器初始状态"""
        assert hasattr(registry, '_metrics_collector')
        assert registry._metrics_collector is None

    def test_health_check_task_initial_state(self, registry):
        """测试健康检查任务初始状态"""
        assert hasattr(registry, '_health_check_task')
        assert registry._health_check_task is None
