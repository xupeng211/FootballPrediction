# TODO: Consider creating a fixture for 54 repeated Mock creations

# TODO: Consider creating a fixture for 54 repeated Mock creations

from unittest.mock import Mock, patch, MagicMock
"""
简化适配器注册表模块测试
Simple Adapter Registry Module Tests

测试src/adapters/registry_simple.py中定义的简化适配器注册表功能，专注于实现100%覆盖率。
Tests simple adapter registry functionality defined in src/adapters/registry_simple.py, focused on achieving 100% coverage.
"""

import pytest
from typing import Any, Dict, Optional

# 导入要测试的模块
try:
    from src.adapters.registry_simple import (
        AdapterRegistry,
        get_global_registry,
        register_adapter,
        _global_registry,
    )
    from src.core.exceptions import AdapterError

    REGISTRY_SIMPLE_AVAILABLE = True
except ImportError:
    REGISTRY_SIMPLE_AVAILABLE = False


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
@pytest.mark.unit

class TestAdapterRegistry:
    """AdapterRegistry类测试"""

    def test_adapter_registry_initialization(self):
        """测试适配器注册表初始化"""
        registry = AdapterRegistry()

        assert hasattr(registry, "_registry")
        assert hasattr(registry, "_instances")
        assert isinstance(registry._registry, dict)
        assert isinstance(registry._instances, dict)
        assert len(registry._registry) == 0
        assert len(registry._instances) == 0

    def test_register_success(self):
        """测试成功注册适配器"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("test_adapter", mock_class, version="1.0", singleton=True)

        assert "test_adapter" in registry._registry
        assert registry._registry["test_adapter"]["class"] is mock_class
        assert registry._registry["test_adapter"]["version"] == "1.0"
        assert registry._registry["test_adapter"]["singleton"] is True

    def test_register_without_kwargs(self):
        """测试不使用额外参数注册适配器"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("simple_adapter", mock_class)

        assert "simple_adapter" in registry._registry
        assert registry._registry["simple_adapter"]["class"] is mock_class
        assert len(registry._registry["simple_adapter"]) == 1  # 只有class

    def test_register_overwrite(self):
        """测试覆盖注册适配器"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("overwrite", mock_class1, version="1.0")
        registry.register("overwrite", mock_class2, version="2.0")

        # 应该被覆盖
        assert registry._registry["overwrite"]["class"] is mock_class2
        assert registry._registry["overwrite"]["version"] == "2.0"

    def test_unregister_existing(self):
        """测试注销已存在的适配器"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("to_remove", mock_class)
        registry._instances["to_remove"] = Mock()  # 添加实例

        # 确认适配器已注册
        assert "to_remove" in registry._registry
        assert "to_remove" in registry._instances

        registry.unregister("to_remove")

        assert "to_remove" not in registry._registry
        assert "to_remove" not in registry._instances

    def test_unregister_nonexistent(self):
        """测试注销不存在的适配器"""
        registry = AdapterRegistry()

        with pytest.raises(AdapterError) as exc_info:
            registry.unregister("nonexistent")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_unregister_without_instance(self):
        """测试注销没有实例的适配器"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("no_instance", mock_class)

        # 不应该抛出异常
        registry.unregister("no_instance")
        assert "no_instance" not in registry._registry

    def test_create_success_without_config(self):
        """测试成功创建适配器（无配置）"""
        registry = AdapterRegistry()
        mock_adapter_class = Mock(return_value="mock_instance")

        registry.register("test", mock_adapter_class)

        result = registry.create("test")

        assert result == "mock_instance"
        mock_adapter_class.assert_called_once_with()

    def test_create_success_with_config(self):
        """测试成功创建适配器（带配置）"""
        registry = AdapterRegistry()
        mock_adapter_class = Mock(return_value="configured_instance")
        config = {"setting1": "value1", "setting2": 42}

        registry.register("configurable", mock_adapter_class)

        result = registry.create("configurable", config)

        assert result == "configured_instance"
        mock_adapter_class.assert_called_once_with(config)

    def test_create_with_config_none(self):
        """测试创建适配器（config=None）"""
        registry = AdapterRegistry()
        mock_adapter_class = Mock(return_value="instance")

        registry.register("test", mock_adapter_class)

        result = registry.create("test", None)

        assert result == "instance"
        mock_adapter_class.assert_called_once_with()

    def test_create_with_config_empty_dict(self):
        """测试创建适配器（config为空字典）"""
        registry = AdapterRegistry()
        mock_adapter_class = Mock(return_value="instance")

        registry.register("test", mock_adapter_class)

        result = registry.create("test", {})

        assert result == "instance"
        # 源代码使用if config:检查，空字典{}在Python中是False，所以调用无参构造函数
        mock_adapter_class.assert_called_once_with()

    def test_create_not_registered(self):
        """测试创建未注册的适配器"""
        registry = AdapterRegistry()

        with pytest.raises(AdapterError) as exc_info:
            registry.create("nonexistent")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_create_with_value_error(self):
        """测试创建适配器时遇到ValueError"""
        registry = AdapterRegistry()
        failing_adapter_class = Mock(side_effect=ValueError("Invalid configuration"))

        registry.register("failing", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            registry.create("failing")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "failing" in str(exc_info.value)
        assert "Invalid configuration" in str(exc_info.value)

    def test_create_with_type_error(self):
        """测试创建适配器时遇到TypeError"""
        registry = AdapterRegistry()
        failing_adapter_class = Mock(side_effect=TypeError("Wrong type"))

        registry.register("type_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            registry.create("type_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "type_error" in str(exc_info.value)
        assert "Wrong type" in str(exc_info.value)

    def test_create_with_attribute_error(self):
        """测试创建适配器时遇到AttributeError"""
        registry = AdapterRegistry()
        failing_adapter_class = Mock(side_effect=AttributeError("Missing attribute"))

        registry.register("attr_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            registry.create("attr_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "attr_error" in str(exc_info.value)
        assert "Missing attribute" in str(exc_info.value)

    def test_create_with_key_error(self):
        """测试创建适配器时遇到KeyError"""
        registry = AdapterRegistry()
        failing_adapter_class = Mock(side_effect=KeyError("Missing key"))

        registry.register("key_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            registry.create("key_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "key_error" in str(exc_info.value)
        assert "'Missing key'" in str(exc_info.value)

    def test_create_with_runtime_error(self):
        """测试创建适配器时遇到RuntimeError"""
        registry = AdapterRegistry()
        failing_adapter_class = Mock(side_effect=RuntimeError("Runtime failure"))

        registry.register("runtime_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            registry.create("runtime_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "runtime_error" in str(exc_info.value)
        assert "Runtime failure" in str(exc_info.value)

    def test_get_info_existing(self):
        """测试获取已存在适配器的信息"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("info_test", mock_class, version="1.0", singleton=True)

        result = registry.get_info("info_test")

        assert isinstance(result, dict)
        assert result["class"] is mock_class
        assert result["version"] == "1.0"
        assert result["singleton"] is True

        # 验证返回的是副本，不是原始引用
        result["new_field"] = "test"
        assert "new_field" not in registry._registry["info_test"]

    def test_get_info_nonexistent(self):
        """测试获取不存在适配器的信息"""
        registry = AdapterRegistry()

        with pytest.raises(AdapterError) as exc_info:
            registry.get_info("nonexistent")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_list_no_filters(self):
        """测试不带过滤条件的列表功能"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("adapter1", mock_class1, version="1.0")
        registry.register("adapter2", mock_class2, version="2.0")

        result = registry.list()

        assert isinstance(result, list)
        assert len(result) == 2

        # 转换为字典便于验证
        result_dict = dict(result)
        assert "adapter1" in result_dict
        assert "adapter2" in result_dict
        assert result_dict["adapter1"]["version"] == "1.0"
        assert result_dict["adapter2"]["version"] == "2.0"

    def test_list_with_matching_filters(self):
        """测试使用匹配过滤条件列表"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("adapter1", mock_class1, version="1.0", singleton=True)
        registry.register("adapter2", mock_class2, version="2.0", singleton=False)

        # 过滤singleton=True的适配器
        result = registry.list(singleton=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "adapter1"
        assert result[0][1]["singleton"] is True

    def test_list_with_non_matching_filters(self):
        """测试使用不匹配过滤条件列表"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("test", mock_class, version="1.0")

        # 过滤不存在的版本
        result = registry.list(version="2.0")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_with_multiple_filters(self):
        """测试使用多个过滤条件列表"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()
        mock_class3 = Mock()

        registry.register(
            "adapter1", mock_class1, version="1.0", singleton=True, priority=1
        )
        registry.register(
            "adapter2", mock_class2, version="1.0", singleton=False, priority=2
        )
        registry.register(
            "adapter3", mock_class3, version="2.0", singleton=True, priority=1
        )

        # 使用多个过滤条件
        result = registry.list(version="1.0", priority=1)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "adapter1"

    def test_list_filter_on_nonexistent_key(self):
        """测试过滤不存在的键"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("test", mock_class, version="1.0")

        # 过滤不存在的键，应该匹配所有项（源代码逻辑）
        result = registry.list(nonexistent_key="value")

        assert isinstance(result, list)
        assert len(result) == 1  # 应该匹配，因为键不存在

    def test_get_singleton_existing_first_time(self):
        """测试获取已存在单例（首次）"""
        registry = AdapterRegistry()
        mock_adapter_class = Mock(return_value="singleton_instance")

        registry.register("singleton", mock_adapter_class)

        result = registry.get_singleton("singleton")

        assert result == "singleton_instance"
        mock_adapter_class.assert_called_once_with()
        assert "singleton" in registry._instances
        assert registry._instances["singleton"] == "singleton_instance"

    def test_get_singleton_existing_subsequent(self):
        """测试获取已存在单例（后续）"""
        registry = AdapterRegistry()
        instance = Mock()
        mock_adapter_class = Mock(return_value=instance)

        registry.register("singleton", mock_adapter_class)

        # 第一次获取
        result1 = registry.get_singleton("singleton")
        # 第二次获取
        result2 = registry.get_singleton("singleton")

        assert result1 is instance
        assert result2 is instance
        assert result1 is result2  # 应该是同一个实例
        mock_adapter_class.assert_called_once_with()  # 只应该调用一次

    def test_get_singleton_nonexistent(self):
        """测试获取不存在单例"""
        registry = AdapterRegistry()

        with pytest.raises(AdapterError) as exc_info:
            registry.get_singleton("nonexistent")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_clear(self):
        """测试清空注册表"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("adapter1", mock_class1)
        registry.register("adapter2", mock_class2)
        registry._instances["adapter1"] = Mock()
        registry._instances["adapter2"] = Mock()

        assert len(registry._registry) == 2
        assert len(registry._instances) == 2

        registry.clear()

        assert len(registry._registry) == 0
        assert len(registry._instances) == 0

    def test_clear_empty(self):
        """测试清空空注册表"""
        registry = AdapterRegistry()

        registry.clear()

        assert len(registry._registry) == 0
        assert len(registry._instances) == 0

    def test_validate_config(self):
        """测试配置验证"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("test", mock_class)

        config = {"some": "config"}
        result = registry.validate_config("test", config)

        # 简化实现，总是返回True
        assert result is True

    def test_validate_config_nonexistent(self):
        """测试验证不存在适配器的配置"""
        registry = AdapterRegistry()

        config = {"some": "config"}
        result = registry.validate_config("nonexistent", config)

        # 简化实现，总是返回True
        assert result is True

    def test_get_dependencies_existing(self):
        """测试获取已存在适配器的依赖"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("with_deps", mock_class, dependencies=["dep1", "dep2"])

        result = registry.get_dependencies("with_deps")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "dep1" in result
        assert "dep2" in result

    def test_get_dependencies_no_dependencies(self):
        """测试获取没有依赖的适配器"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("no_deps", mock_class)

        result = registry.get_dependencies("no_deps")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_dependencies_nonexistent(self):
        """测试获取不存在适配器的依赖"""
        registry = AdapterRegistry()

        result = registry.get_dependencies("nonexistent")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_resolve_dependencies_existing(self):
        """测试解析已存在适配器的依赖"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("test", mock_class)

        result = registry.resolve_dependencies("test")

        # 简化实现，返回包含名称的列表
        assert isinstance(result, list)
        assert len(result) == 1
        assert "test" in result

    def test_resolve_dependencies_nonexistent(self):
        """测试解析不存在适配器的依赖"""
        registry = AdapterRegistry()

        result = registry.resolve_dependencies("nonexistent")

        # 源代码实现：return [name]，即使不存在也返回名称
        assert isinstance(result, list)
        assert len(result) == 1
        assert "nonexistent" in result

    def test_get_statistics_empty(self):
        """测试获取空注册表的统计信息"""
        registry = AdapterRegistry()

        result = registry.get_statistics()

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert result["singletons"] == 0

    def test_get_statistics_with_adapters(self):
        """测试获取包含适配器的注册表统计信息"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()
        mock_class3 = Mock()

        registry.register("normal1", mock_class1)
        registry.register("singleton1", mock_class2, singleton=True)
        registry.register("singleton2", mock_class3, singleton=True)

        result = registry.get_statistics()

        assert isinstance(result, dict)
        assert result["total"] == 3
        assert result["singletons"] == 2

    def test_get_statistics_with_explicit_false(self):
        """测试统计信息处理显式singleton=False"""
        registry = AdapterRegistry()
        mock_class = Mock()

        registry.register("explicit_false", mock_class, singleton=False)

        result = registry.get_statistics()

        assert result["total"] == 1
        assert result["singletons"] == 0

    def test_export(self):
        """测试导出注册表"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        registry.register("export1", mock_class1, version="1.0")
        registry.register("export2", mock_class2, version="2.0")

        result = registry.export()

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "export1" in result
        assert "export2" in result
        assert result["export1"]["version"] == "1.0"
        assert result["export2"]["version"] == "2.0"

        # 验证返回的是副本，不是原始引用
        result["new_adapter"] = {"class": Mock()}
        assert "new_adapter" not in registry._registry

    def test_export_empty(self):
        """测试导出空注册表"""
        registry = AdapterRegistry()

        result = registry.export()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_import_data(self):
        """测试导入数据"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        import_data = {
            "import1": {"class": mock_class1, "version": "1.0"},
            "import2": {"class": mock_class2, "version": "2.0"},
        }

        registry.import_data(import_data)

        assert len(registry._registry) == 2
        assert "import1" in registry._registry
        assert "import2" in registry._registry
        assert registry._registry["import1"]["version"] == "1.0"
        assert registry._registry["import2"]["version"] == "2.0"

    def test_import_data_merge(self):
        """测试导入数据合并"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()
        mock_class3 = Mock()

        # 先注册一个适配器
        registry.register("existing", mock_class1, version="1.0")

        # 导入更多数据
        import_data = {
            "import1": {"class": mock_class2, "version": "2.0"},
            "import2": {"class": mock_class3, "version": "3.0"},
        }

        registry.import_data(import_data)

        assert len(registry._registry) == 3
        assert "existing" in registry._registry
        assert "import1" in registry._registry
        assert "import2" in registry._registry
        assert registry._registry["existing"]["version"] == "1.0"

    def test_import_data_override(self):
        """测试导入数据覆盖"""
        registry = AdapterRegistry()
        mock_class1 = Mock()
        mock_class2 = Mock()

        # 先注册一个适配器
        registry.register("override", mock_class1, version="1.0")

        # 导入同名数据
        import_data = {"override": {"class": mock_class2, "version": "2.0"}}

        registry.import_data(import_data)

        assert len(registry._registry) == 1
        assert "override" in registry._registry
        assert registry._registry["override"]["class"] is mock_class2
        assert registry._registry["override"]["version"] == "2.0"

    def test_adapter_decorator_with_name(self):
        """测试适配器装饰器（指定名称）"""
        registry = AdapterRegistry()

        @registry.adapter("decorated_adapter", version="1.0", singleton=True)
        class TestAdapter:
            def __init__(self):
                self.name = "test"

        # 验证适配器被注册
        assert "decorated_adapter" in registry._registry
        assert registry._registry["decorated_adapter"]["class"] is TestAdapter
        assert registry._registry["decorated_adapter"]["version"] == "1.0"
        assert registry._registry["decorated_adapter"]["singleton"] is True

        # 验证装饰器返回原类
        assert TestAdapter.__name__ == "TestAdapter"

    def test_adapter_decorator_without_name(self):
        """测试适配器装饰器（使用类名）"""
        registry = AdapterRegistry()

        @registry.adapter(version="2.0")
        class AutoNamedAdapter:
            def __init__(self):
                self.name = "auto"

        # 验证适配器以类名注册
        assert "AutoNamedAdapter" in registry._registry
        assert registry._registry["AutoNamedAdapter"]["class"] is AutoNamedAdapter
        assert registry._registry["AutoNamedAdapter"]["version"] == "2.0"

    def test_adapter_decorator_no_kwargs(self):
        """测试适配器装饰器（无额外参数）"""
        registry = AdapterRegistry()

        @registry.adapter()
        class SimpleAdapter:
            def __init__(self):
                self.name = "simple"

        # 验证适配器以类名注册
        assert "SimpleAdapter" in registry._registry
        assert registry._registry["SimpleAdapter"]["class"] is SimpleAdapter
        assert len(registry._registry["SimpleAdapter"]) == 1  # 只有class

    def test_adapter_decorator_called_directly(self):
        """测试适配器装饰器直接调用"""
        registry = AdapterRegistry()

        @registry.adapter()
        class DirectAdapter:
            def __init__(self):
                self.name = "direct"

        # 验证适配器以类名注册
        assert "DirectAdapter" in registry._registry
        assert registry._registry["DirectAdapter"]["class"] is DirectAdapter

    def test_adapter_decorator_nested_registration(self):
        """测试适配器装饰器嵌套注册"""
        registry = AdapterRegistry()

        @registry.adapter("nested1", version="1.0")
        @registry.adapter("nested2", version="2.0")  # 应该覆盖前一个
        class NestedAdapter:
            def __init__(self):
                self.name = "nested"

        # 验证两个名称都被注册了（装饰器嵌套的行为）
        assert "nested1" in registry._registry
        assert "nested2" in registry._registry
        assert registry._registry["nested1"]["version"] == "1.0"
        assert registry._registry["nested2"]["version"] == "2.0"
        # 两个名称指向同一个类
        assert registry._registry["nested1"]["class"] is NestedAdapter
        assert registry._registry["nested2"]["class"] is NestedAdapter

    def test_complete_workflow(self):
        """测试完整工作流程"""
        registry = AdapterRegistry()

        # 1. 注册适配器
        mock_class = Mock(return_value="workflow_instance")
        registry.register("workflow", mock_class, version="1.0", singleton=True)

        # 2. 创建实例
        instance1 = registry.create("workflow", {"config": "value"})
        instance2 = registry.get_singleton("workflow")

        # 3. 获取信息
        info = registry.get_info("workflow")

        # 4. 列出适配器
        adapters = registry.list(version="1.0")

        # 5. 获取统计信息
        stats = registry.get_statistics()

        # 验证结果
        assert instance1 == "workflow_instance"
        assert instance2 == "workflow_instance"
        assert info["version"] == "1.0"
        assert len(adapters) == 1
        assert adapters[0][0] == "workflow"
        assert stats["total"] == 1
        assert stats["singletons"] == 1

        # 6. 导出和导入
        exported = registry.export()
        new_registry = AdapterRegistry()
        new_registry.import_data(exported)

        assert len(new_registry._registry) == 1
        assert "workflow" in new_registry._registry


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
class TestGlobalRegistryFunctions:
    """全局注册表函数测试"""

    def test_get_global_registry_returns_instance(self):
        """测试获取全局注册表返回实例"""
        registry = get_global_registry()

        assert isinstance(registry, AdapterRegistry)

    def test_get_global_registry_singleton(self):
        """测试全局注册表是单例"""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert registry1 is registry2  # 应该是同一个实例

    @patch("src.adapters.registry_simple._global_registry", None)
    def test_get_global_registry_creates_new_instance(self):
        """测试全局注册表创建新实例"""
        # 重置全局变量
        import src.adapters.registry_simple

        original_registry = src.adapters.registry_simple._global_registry
        src.adapters.registry_simple._global_registry = None

        try:
            registry = get_global_registry()

            assert isinstance(registry, AdapterRegistry)
            # 验证全局变量被设置
            assert src.adapters.registry_simple._global_registry is registry
        finally:
            # 恢复原始状态
            src.adapters.registry_simple._global_registry = original_registry

    def test_register_adapter_decorator(self):
        """测试注册适配器装饰器"""
        # 清除全局注册表
        import src.adapters.registry_simple

        src.adapters.registry_simple._global_registry = None

        @register_adapter("decorated_global", version="1.0")
        class GlobalAdapter:
            def __init__(self):
                self.name = "global"

        # 验证适配器被注册到全局注册表
        registry = get_global_registry()
        assert "decorated_global" in registry._registry
        assert registry._registry["decorated_global"]["class"] is GlobalAdapter
        assert registry._registry["decorated_global"]["version"] == "1.0"

    def test_register_adapter_decorator_without_name(self):
        """测试注册适配器装饰器（使用类名）"""
        # 清除全局注册表
        import src.adapters.registry_simple

        src.adapters.registry_simple._global_registry = None

        @register_adapter(version="2.0")
        class AutoGlobalAdapter:
            def __init__(self):
                self.name = "auto_global"

        # 验证适配器以类名注册到全局注册表
        registry = get_global_registry()
        assert "AutoGlobalAdapter" in registry._registry
        assert registry._registry["AutoGlobalAdapter"]["class"] is AutoGlobalAdapter
        assert registry._registry["AutoGlobalAdapter"]["version"] == "2.0"

    def test_global_registry_isolation(self):
        """测试全局注册表隔离"""
        # 重置全局注册表
        import src.adapters.registry_simple

        src.adapters.registry_simple._global_registry = None

        # 注册适配器到全局注册表
        registry1 = get_global_registry()
        mock_class = Mock(return_value="global_instance")
        registry1.register("global_test", mock_class)

        # 再次获取全局注册表应该是同一个实例
        registry2 = get_global_registry()
        assert registry1 is registry2

        # 应该能够创建适配器
        result = registry2.create("global_test")
        assert result == "global_instance"
        mock_class.assert_called_once_with()


@pytest.mark.skipif(
    not REGISTRY_SIMPLE_AVAILABLE, reason="Simple registry module not available"
)
class TestModuleIntegration:
    """模块集成测试"""

    def test_module_exports(self):
        """测试模块导出"""
        from src.adapters import registry_simple

        # 验证所有预期的导出都存在
        assert hasattr(registry_simple, "AdapterRegistry")
        assert hasattr(registry_simple, "get_global_registry")
        assert hasattr(registry_simple, "register_adapter")
        assert hasattr(registry_simple, "_global_registry")

    def test_adapter_registry_class_attributes(self):
        """测试AdapterRegistry类属性"""
        # 验证类有预期的属性
        assert hasattr(AdapterRegistry, "register")
        assert hasattr(AdapterRegistry, "unregister")
        assert hasattr(AdapterRegistry, "create")
        assert hasattr(AdapterRegistry, "get_info")
        assert hasattr(AdapterRegistry, "list")
        assert hasattr(AdapterRegistry, "get_singleton")
        assert hasattr(AdapterRegistry, "clear")
        assert hasattr(AdapterRegistry, "validate_config")
        assert hasattr(AdapterRegistry, "get_dependencies")
        assert hasattr(AdapterRegistry, "resolve_dependencies")
        assert hasattr(AdapterRegistry, "get_statistics")
        assert hasattr(AdapterRegistry, "export")
        assert hasattr(AdapterRegistry, "import_data")
        assert hasattr(AdapterRegistry, "adapter")

    def test_global_registry_variable(self):
        """测试全局注册表变量"""
        import src.adapters.registry_simple

        # 验证全局变量存在
        assert hasattr(src.adapters.registry_simple, "_global_registry")

        # 初始状态应该是None
        original_value = src.adapters.registry_simple._global_registry

        # 测试后恢复原始值
        try:
            # 验证可以设置为None
            src.adapters.registry_simple._global_registry = None
            assert src.adapters.registry_simple._global_registry is None
        finally:
            # 恢复原始值
            src.adapters.registry_simple._global_registry = original_value

    def test_function_signatures(self):
        """测试函数签名"""
        import inspect

        # 测试get_global_registry签名
        sig = inspect.signature(get_global_registry)
        assert len(sig.parameters) == 0

        # 测试register_adapter签名
        sig = inspect.signature(register_adapter)
        expected_params = ["name"]
        actual_params = list(sig.parameters.keys())
        for param in expected_params:
            assert param in actual_params

    def test_concurrent_access_to_global_registry(self):
        """测试并发访问全局注册表"""
        import threading
        import time

        # 重置全局注册表
        import src.adapters.registry_simple

        src.adapters.registry_simple._global_registry = None

        results = []
        errors = []

        def worker():
            try:
                registry = get_global_registry()
                time.sleep(0.01)  # 短暂延迟
                # 验证所有线程得到的是同一个实例
                results.append(registry)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时访问全局注册表
        threads = [threading.Thread(target=worker) for _ in range(5)]

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

        # 所有结果应该是同一个实例
        first_result = results[0]
        for result in results[1:]:
            assert result is first_result

    def test_global_registry_state_persistence(self):
        """测试全局注册表状态持久性"""
        import src.adapters.registry_simple

        # 重置全局注册表
        src.adapters.registry_simple._global_registry = None

        # 获取全局注册表并注册适配器
        registry1 = get_global_registry()
        mock_class = Mock(return_value="persistent_instance")
        registry1.register("persistent_test", mock_class)

        # 再次获取全局注册表
        registry2 = get_global_registry()

        # 状态应该保持
        assert registry2._registry["persistent_test"]["class"] is mock_class

        # 应该能够创建适配器
        result = registry2.create("persistent_test")
        assert result == "persistent_instance"

    def test_module_import_integrity(self):
        """测试模块导入完整性"""
        # 测试可以正常导入所有必要的组件
        from src.adapters.registry_simple import AdapterRegistry
        from src.adapters.registry_simple import get_global_registry
        from src.adapters.registry_simple import register_adapter
        from src.core.exceptions import AdapterError

        # 验证导入的对象是可用的
        assert callable(AdapterRegistry)
        assert callable(get_global_registry)
        assert callable(register_adapter)
        assert issubclass(AdapterError, Exception)

        # 验证可以正常使用
        registry = AdapterRegistry()
        assert hasattr(registry, "register")
        assert hasattr(registry, "create")
