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
        adapter = await registry.register_adapter(config)

        assert adapter is not None
        assert "test_adapter" in registry.adapters
        mock_adapter.initialize.assert_called_once()

        # 清理
        await registry.shutdown()

    async def test_register_adapter_not_active(self, registry):
        """测试：在非活跃状态下注册适配器"""
        _config = AdapterConfig(name="test", adapter_type="test")

        with pytest.raises(RuntimeError, match="Registry not active"):
            await registry.register_adapter(config)

    async def test_register_adapter_already_exists(self, registry):
        """测试：注册已存在的适配器"""
        await registry.initialize()

        # 创建配置
        _config = AdapterConfig(name="test_adapter", adapter_type="test")
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock()
        registry.factory.create_adapter.return_value = mock_adapter

        # 第一次注册
        await registry.register_adapter(config)

        # 第二次注册应该失败
        with pytest.raises(ValueError, match="already registered"):
            await registry.register_adapter(config)

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

        await registry.register_adapter(config)
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
        assert result is True
        mock_adapter.initialize.assert_called_once()

    async def test_enable_adapter_not_found(self, registry):
        """测试：启用不存在的适配器"""
        _result = await registry.enable_adapter("nonexistent")
        assert result is False

    async def test_enable_adapter_failure(self, registry):
        """测试：启用适配器失败"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.initialize = AsyncMock(side_effect=ValueError("Failed"))
        registry.adapters["test_adapter"] = mock_adapter

        # 启用应该失败
        _result = await registry.enable_adapter("test_adapter")
        assert result is False

    async def test_disable_adapter(self, registry):
        """测试：禁用适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        registry.adapters["test_adapter"] = mock_adapter

        # 禁用适配器
        _result = await registry.disable_adapter("test_adapter")
        assert result is True
        mock_adapter.cleanup.assert_called_once()
        assert mock_adapter.status == AdapterStatus.INACTIVE

    async def test_disable_adapter_not_found(self, registry):
        """测试：禁用不存在的适配器"""
        _result = await registry.disable_adapter("nonexistent")
        assert result is False

    async def test_restart_adapter(self, registry):
        """测试：重启适配器"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        mock_adapter.initialize = AsyncMock()
        registry.adapters["test_adapter"] = mock_adapter

        # 重启适配器
        _result = await registry.restart_adapter("test_adapter")
        assert result is True
        mock_adapter.cleanup.assert_called_once()
        mock_adapter.initialize.assert_called_once()

    async def test_restart_adapter_not_found(self, registry):
        """测试：重启不存在的适配器"""
        _result = await registry.restart_adapter("nonexistent")
        assert result is False

    async def test_restart_adapter_failure(self, registry):
        """测试：重启适配器失败"""
        # 创建模拟适配器
        mock_adapter = Mock(spec=Adapter)
        mock_adapter.cleanup = AsyncMock()
        mock_adapter.initialize = AsyncMock(side_effect=ValueError("Failed"))
        registry.adapters["test_adapter"] = mock_adapter

        # 重启应该失败
        _result = await registry.restart_adapter("test_adapter")
        assert result is False

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
