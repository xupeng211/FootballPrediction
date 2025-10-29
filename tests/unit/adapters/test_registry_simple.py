"""
简化适配器注册表模块测试
Tests simple adapter registry functionality defined in src/adapters/registry_simple.py
"""


import pytest

# 导入要测试的模块
try:
        AdapterRegistry,
        _global_registry,
        get_global_registry,
        register_adapter,
    )
    from src.core.exceptions import AdapterError

    REGISTRY_SIMPLE_AVAILABLE = True
except ImportError:
    REGISTRY_SIMPLE_AVAILABLE = False


@pytest.fixture
def registry():
    """创建干净的适配器注册表实例"""
    return AdapterRegistry()


@pytest.fixture
def mock_adapter_class():
    """创建模拟适配器类"""
    return Mock(return_value="mock_instance")


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    return {"setting1": "value1", "setting2": 42}


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
@pytest.mark.unit
class TestAdapterRegistry:
    """AdapterRegistry类核心功能测试"""

    def test_initialization(self, registry):
        """测试注册表初始化"""
        assert isinstance(registry._registry, dict)
        assert isinstance(registry._instances, dict)
        assert len(registry._registry) == 0
        assert len(registry._instances) == 0

    def test_register_and_unregister_workflow(self, registry, mock_adapter_class):
        """测试完整的注册和注销工作流程"""
        # 注册适配器
        registry.register(
            "test_adapter", mock_adapter_class, version="1.0", singleton=True
        )
        assert "test_adapter" in registry._registry
        assert registry._registry["test_adapter"]["class"] is mock_adapter_class
        assert registry._registry["test_adapter"]["version"] == "1.0"

        # 注销适配器
        registry.unregister("test_adapter")
        assert "test_adapter" not in registry._registry
        assert "test_adapter" not in registry._instances

    def test_register_overwrite(self, registry):
        """测试注册覆盖功能"""
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("overwrite", mock_class1, version="1.0")
        registry.register("overwrite", mock_class2, version="2.0")

        assert registry._registry["overwrite"]["class"] is mock_class2
        assert registry._registry["overwrite"]["version"] == "2.0"

    def test_unregister_errors(self, registry):
        """测试注销错误情况"""
        with pytest.raises(AdapterError, match="No adapter registered"):
            registry.unregister("nonexistent")

    def test_create_success_scenarios(self, registry, mock_adapter_class, mock_config):
        """测试创建适配器的各种成功场景"""
        registry.register("test", mock_adapter_class)

        # 无配置创建
        instance1 = registry.create("test")
        assert instance1 == "mock_instance"
        mock_adapter_class.assert_called_with()

        # 有配置创建
        mock_adapter_class.reset_mock()
        instance2 = registry.create("test", mock_config)
        assert instance2 == "mock_instance"
        mock_adapter_class.assert_called_with(mock_config)

        # None配置创建
        mock_adapter_class.reset_mock()
        instance3 = registry.create("test", None)
        assert instance3 == "mock_instance"
        mock_adapter_class.assert_called_with()

    def test_create_errors(self, registry):
        """测试创建适配器的错误情况"""
        # 未注册适配器
        with pytest.raises(AdapterError, match="No adapter registered"):
            registry.create("nonexistent")

        # 各种异常类型传播
        error_cases = [
            (ValueError("Invalid config"), "Invalid config"),
            (TypeError("Wrong type"), "Wrong type"),
            (AttributeError("Missing attr"), "Missing attr"),
            (KeyError("Missing key"), "'Missing key'"),
            (RuntimeError("Runtime error"), "Runtime error"),
        ]

        for exception, expected_msg in error_cases:
            failing_class = Mock(side_effect=exception)
            registry.register(f"failing_{type(exception).__name__}", failing_class)

            with pytest.raises(AdapterError, match=f"Failed to create.*{expected_msg}"):
                registry.create(f"failing_{type(exception).__name__}")

    def test_info_and_list_operations(self, registry, mock_adapter_class):
        """测试信息获取和列表操作"""
        registry.register(
            "info_test", mock_adapter_class, version="1.0", singleton=True
        )

        # 获取信息
        info = registry.get_info("info_test")
        assert info["class"] is mock_adapter_class
        assert info["version"] == "1.0"
        assert info["singleton"] is True

        # 验证返回副本
        info["new_field"] = "test"
        assert "new_field" not in registry._registry["info_test"]

        # 列表操作
        adapters = registry.list()
        assert len(adapters) == 1
        assert adapters[0][0] == "info_test"

        # 过滤列表
        filtered = registry.list(version="1.0")
        assert len(filtered) == 1

        no_match = registry.list(version="2.0")
        assert len(no_match) == 0

    def test_singleton_management(self, registry, mock_adapter_class):
        """测试单例管理"""
        registry.register("singleton", mock_adapter_class)

        # 首次获取
        instance1 = registry.get_singleton("singleton")
        assert instance1 == "mock_instance"
        mock_adapter_class.assert_called_once()

        # 后续获取应返回同一实例
        instance2 = registry.get_singleton("singleton")
        assert instance1 is instance2
        mock_adapter_class.assert_called_once()  # 仍然只调用一次

    def test_advanced_operations(self, registry, mock_adapter_class):
        """测试高级操作"""
        # 注册带依赖的适配器
        registry.register(
            "with_deps", mock_adapter_class, dependencies=["dep1", "dep2"]
        )

        # 依赖相关操作
        deps = registry.get_dependencies("with_deps")
        assert deps == ["dep1", "dep2"]

        resolved = registry.resolve_dependencies("with_deps")
        assert resolved == ["with_deps"]

        # 配置验证
        assert registry.validate_config("with_deps", {}) is True
        assert registry.validate_config("nonexistent", {}) is True

    def test_statistics_and_import_export(self, registry):
        """测试统计信息和导入导出"""
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("normal", mock_class1)
        registry.register("singleton", mock_class2, singleton=True)

        # 统计信息
        stats = registry.get_statistics()
        assert stats["total"] == 2
        assert stats["singletons"] == 1

        # 导出和导入
        exported = registry.export()
        assert len(exported) == 2
        assert "normal" in exported
        assert "singleton" in exported

        new_registry = AdapterRegistry()
        new_registry.import_data(exported)
        assert len(new_registry._registry) == 2

    def test_decorator_registration(self, registry):
        """测试装饰器注册"""

        @registry.adapter("decorated", version="1.0", singleton=True)
        class TestAdapter:
            def __init__(self):
                self.name = "test"

        assert "decorated" in registry._registry
        assert registry._registry["decorated"]["class"] is TestAdapter
        assert registry._registry["decorated"]["version"] == "1.0"

        # 自动命名
        @registry.adapter(version="2.0")
        class AutoAdapter:
            pass

        assert "AutoAdapter" in registry._registry
        assert registry._registry["AutoAdapter"]["version"] == "2.0"

    def test_comprehensive_workflow(self, registry, mock_adapter_class, mock_config):
        """测试完整工作流程"""
        # 1. 注册
        registry.register("workflow", mock_adapter_class, version="1.0", singleton=True)

        # 2. 创建和获取
        instance = registry.create("workflow", mock_config)
        _ = registry.get_singleton("workflow")  # 验证单例获取

        # 3. 信息和列表
        info = registry.get_info("workflow")
        adapters = registry.list(version="1.0")
        stats = registry.get_statistics()

        # 4. 验证
        assert instance == "mock_instance"
        assert info["version"] == "1.0"
        assert len(adapters) == 1
        assert stats["total"] == 1
        assert stats["singletons"] == 1


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
class TestGlobalRegistryFunctions:
    """全局注册表函数测试"""

    @pytest.fixture(autouse=True)
    def reset_global_registry(self):
        """重置全局注册表"""
        import src.adapters.registry_simple

        original = src.adapters.registry_simple._global_registry
        src.adapters.registry_simple._global_registry = None
        yield
        src.adapters.registry_simple._global_registry = original

    def test_global_registry_singleton(self):
        """测试全局注册表单例特性"""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert isinstance(registry1, AdapterRegistry)
        assert registry1 is registry2

    def test_global_adapter_decorator(self):
        """测试全局适配器装饰器"""

        @register_adapter("global_test", version="1.0")
        class GlobalAdapter:
            def __init__(self):
                self.name = "global"

        registry = get_global_registry()
        assert "global_test" in registry._registry
        assert registry._registry["global_test"]["class"] is GlobalAdapter

    def test_global_registry_state_persistence(self):
        """测试全局注册表状态持久性"""
        registry1 = get_global_registry()
        mock_class = Mock(return_value="persistent")
        registry1.register("persistent", mock_class)

        registry2 = get_global_registry()
        assert registry1 is registry2
        result = registry2.create("persistent")
        assert result == "persistent"


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
class TestModuleIntegration:
    """模块集成测试"""

    def test_module_exports(self):
        """测试模块导出完整性"""
from src.adapters import registry_simple

        expected_exports = [
            "AdapterRegistry",
            "get_global_registry",
            "register_adapter",
            "_global_registry",
        ]

        for export in expected_exports:
            assert hasattr(registry_simple, export)

    def test_class_interface_completeness(self):
        """测试类接口完整性"""
        required_methods = [
            "register",
            "unregister",
            "create",
            "get_info",
            "list",
            "get_singleton",
            "clear",
            "validate_config",
            "get_dependencies",
            "resolve_dependencies",
            "get_statistics",
            "export",
            "import_data",
            "adapter",
        ]

        for method in required_methods:
            assert hasattr(AdapterRegistry, method)

    def test_concurrent_global_access(self):
        """测试并发访问全局注册表"""
        import threading
        import time

        results = []

        def worker():
            registry = get_global_registry()
            time.sleep(0.01)
            results.append(registry)

        threads = [threading.Thread(target=worker) for _ in range(5)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 所有结果应该是同一个实例
        first = results[0]
        for result in results[1:]:
            assert result is first
