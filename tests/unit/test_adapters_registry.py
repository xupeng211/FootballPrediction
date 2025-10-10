"""
适配器注册表测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Type
from src.core.exceptions import AdapterError
from src.adapters.registry_simple import AdapterRegistry, register_adapter


class TestAdapterRegistry:
    """适配器注册表测试"""

    def test_registry_initialization(self):
        """测试注册表初始化"""
        registry = AdapterRegistry()
        assert registry._registry == {}
        assert registry._instances == {}

    def test_register_adapter_class(self):
        """测试注册适配器类"""
        registry = AdapterRegistry()

        class TestAdapter:
            """测试适配器"""

            pass

        # 注册适配器
        registry.register("test_adapter", TestAdapter)

        # 验证注册
        assert "test_adapter" in registry._registry
        assert registry._registry["test_adapter"]["class"] == TestAdapter
        assert registry._registry["test_adapter"]["singleton"] is False

    def test_register_adapter_with_metadata(self):
        """测试注册带元数据的适配器"""
        registry = AdapterRegistry()

        class TestAdapter:
            """测试适配器"""

            pass

        metadata = {
            "version": "1.0.0",
            "description": "Test adapter",
            "singleton": True,
            "config_schema": {"type": "object"},
        }

        # 注册适配器
        registry.register("test_adapter", TestAdapter, **metadata)

        # 验证元数据
        registered = registry._registry["test_adapter"]
        assert registered["class"] == TestAdapter
        assert registered["version"] == "1.0.0"
        assert registered["description"] == "Test adapter"
        assert registered["singleton"] is True
        assert registered["config_schema"] == {"type": "object"}

    def test_register_duplicate_adapter(self):
        """测试注册重复适配器"""
        registry = AdapterRegistry()

        class TestAdapter:
            pass

        # 第一次注册
        registry.register("test", TestAdapter)

        # 第二次注册应该失败
        with pytest.raises(AdapterError, match="Adapter 'test' already registered"):
            registry.register("test", TestAdapter)

    def test_get_adapter_info(self):
        """测试获取适配器信息"""
        registry = AdapterRegistry()

        class TestAdapter:
            pass

        metadata = {"version": "1.0.0", "description": "Test"}
        registry.register("test", TestAdapter, **metadata)

        # 获取信息
        info = registry.get_info("test")
        assert info["class"] == TestAdapter
        assert info["version"] == "1.0.0"
        assert info["description"] == "Test"

    def test_get_info_for_nonexistent_adapter(self):
        """测试获取不存在适配器的信息"""
        registry = AdapterRegistry()

        with pytest.raises(
            AdapterError, match="No adapter registered with name 'nonexistent'"
        ):
            registry.get_info("nonexistent")

    def test_list_adapters(self):
        """测试列出所有适配器"""
        registry = AdapterRegistry()

        class Adapter1:
            pass

        class Adapter2:
            pass

        # 注册适配器
        registry.register("adapter1", Adapter1, version="1.0")
        registry.register("adapter2", Adapter2, version="2.0")

        # 列出适配器
        adapters = registry.list()
        assert len(adapters) == 2

        # 检查详细信息
        adapter_info = {name: info for name, info in adapters}
        assert adapter_info["adapter1"]["version"] == "1.0"
        assert adapter_info["adapter2"]["version"] == "2.0"

    def test_list_adapters_with_filter(self):
        """测试带过滤条件列出适配器"""
        registry = AdapterRegistry()

        class DatabaseAdapter:
            pass

        class APIAdapter:
            pass

        class CacheAdapter:
            pass

        # 注册适配器
        registry.register("db_adapter", DatabaseAdapter, category="database")
        registry.register("api_adapter", APIAdapter, category="api")
        registry.register("cache_adapter", CacheAdapter, category="cache")

        # 按类别过滤
        api_adapters = registry.list(category="api")
        assert len(api_adapters) == 1
        assert "api_adapter" in dict(api_adapters)

        # 按版本过滤
        v1_adapters = registry.list(version="1.0.0")
        assert len(v1_adapters) == 0

    def test_unregister_adapter(self):
        """测试注销适配器"""
        registry = AdapterRegistry()

        class TestAdapter:
            pass

        # 注册适配器
        registry.register("test", TestAdapter)
        assert "test" in registry._registry

        # 注销适配器
        registry.unregister("test")
        assert "test" not in registry._registry

    def test_unregister_nonexistent_adapter(self):
        """测试注销不存在的适配器"""
        registry = AdapterRegistry()

        with pytest.raises(
            AdapterError, match="No adapter registered with name 'nonexistent'"
        ):
            registry.unregister("nonexistent")

    def test_create_adapter_instance(self):
        """测试创建适配器实例"""
        registry = AdapterRegistry()

        class TestAdapter:
            def __init__(self, config):
                self.config = config

        registry.register("test", TestAdapter)

        # 创建实例
        config = {"host": "localhost"}
        instance = registry.create("test", config)

        assert isinstance(instance, TestAdapter)
        assert instance.config == config

    def test_create_singleton_adapter(self):
        """测试创建单例适配器"""
        registry = AdapterRegistry()

        class SingletonAdapter:
            def __init__(self, config):
                self.instance_id = id(self)

        registry.register("singleton", SingletonAdapter, singleton=True)

        # 创建两个实例
        instance1 = registry.create("singleton")
        instance2 = registry.create("singleton")

        # 应该是同一个实例
        assert instance1 is instance2

    def test_create_nonexistent_adapter(self):
        """测试创建不存在的适配器"""
        registry = AdapterRegistry()

        with pytest.raises(
            AdapterError, match="No adapter registered with name 'nonexistent'"
        ):
            registry.create("nonexistent")

    def test_get_singleton_instance(self):
        """测试获取单例实例"""
        registry = AdapterRegistry()

        class SingletonAdapter:
            def __init__(self):
                self.created = True

        registry.register("singleton", SingletonAdapter, singleton=True)

        # 第一次创建
        instance1 = registry.get_singleton("singleton")
        assert isinstance(instance1, SingletonAdapter)
        assert instance1.created is True

        # 第二次获取
        instance2 = registry.get_singleton("singleton")
        assert instance1 is instance2

    def test_get_non_singleton_as_singleton(self):
        """测试获取非单例适配器作为单例"""
        registry = AdapterRegistry()

        class RegularAdapter:
            def __init__(self):
                self.created = True

        registry.register("regular", RegularAdapter, singleton=False)

        # 尝试获取单例应该失败
        with pytest.raises(
            AdapterError, match="Adapter 'regular' is not registered as singleton"
        ):
            registry.get_singleton("regular")

    def test_clear_registry(self):
        """测试清空注册表"""
        registry = AdapterRegistry()

        class Adapter1:
            pass

        class Adapter2:
            pass

        # 注册适配器
        registry.register("adapter1", Adapter1)
        registry.register("adapter2", Adapter2)

        assert len(registry._registry) == 2

        # 清空注册表
        registry.clear()
        assert len(registry._registry) == 0

    def test_validate_config(self):
        """测试配置验证"""
        registry = AdapterRegistry()

        class ConfigurableAdapter:
            pass

        # 定义配置模式
        schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "timeout": {"type": "number", "default": 30},
            },
            "required": ["host", "port"],
        }

        registry.register("configurable", ConfigurableAdapter, config_schema=schema)

        # 有效配置
        valid_config = {"host": "localhost", "port": 5432}
        assert registry.validate_config("configurable", valid_config) is True

        # 无效配置（缺少必需字段）
        invalid_config = {"host": "localhost"}
        assert registry.validate_config("configurable", invalid_config) is False

        # 无效配置（类型错误）
        invalid_config2 = {"host": "localhost", "port": "invalid"}
        assert registry.validate_config("configurable", invalid_config2) is False

    def test_get_adapter_dependencies(self):
        """测试获取适配器依赖"""
        registry = AdapterRegistry()

        class DependentAdapter:
            dependencies = ["database", "cache"]

        registry.register("dependent", DependentAdapter)

        # 获取依赖
        deps = registry.get_dependencies("dependent")
        assert deps == ["database", "cache"]

    def test_resolve_dependencies(self):
        """测试解析依赖关系"""
        registry = AdapterRegistry()

        class BaseAdapter:
            pass

        class ChildAdapter:
            dependencies = ["base"]

        class GrandChildAdapter:
            dependencies = ["child"]

        # 注册适配器
        registry.register("base", BaseAdapter)
        registry.register("child", ChildAdapter)
        registry.register("grandchild", GrandChildAdapter)

        # 解析依赖
        resolved = registry.resolve_dependencies("grandchild")
        assert "base" in resolved
        assert "child" in resolved
        assert "grandchild" in resolved

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        registry = AdapterRegistry()

        class AdapterA:
            dependencies = ["adapter_b"]

        class AdapterB:
            dependencies = ["adapter_a"]

        registry.register("adapter_a", AdapterA)
        registry.register("adapter_b", AdapterB)

        # 检测循环依赖
        with pytest.raises(AdapterError, match="Circular dependency detected"):
            registry.resolve_dependencies("adapter_a")

    def test_registry_with_decorators(self):
        """测试使用装饰器注册"""
        registry = AdapterRegistry()

        # 使用装饰器注册
        @registry.adapter(name="decorated", version="1.0.0")
        class DecoratedAdapter:
            pass

        # 验证注册
        assert "decorated" in registry._registry
        info = registry.get_info("decorated")
        assert info["version"] == "1.0.0"

    def test_registry_export_import(self):
        """测试注册表导出导入"""
        registry1 = AdapterRegistry()
        registry2 = AdapterRegistry()

        class TestAdapter:
            pass

        # 在第一个注册表注册
        registry1.register("test", TestAdapter, version="1.0.0")

        # 导出注册表
        export_data = registry1.export()

        # 导入到第二个注册表
        registry2.import_data(export_data)

        # 验证导入
        assert "test" in registry2._registry
        info = registry2.get_info("test")
        assert info["version"] == "1.0.0"

    def test_get_adapter_statistics(self):
        """测试获取适配器统计"""
        registry = AdapterRegistry()

        class Adapter1:
            pass

        class Adapter2:
            pass

        registry.register("adapter1", Adapter1, category="database")
        registry.register("adapter2", Adapter2, category="api")

        # 获取统计
        stats = registry.get_statistics()
        assert stats["total"] == 2
        assert stats["by_category"]["database"] == 1
        assert stats["by_category"]["api"] == 1
        assert stats["singletons"] == 0


class TestRegisterDecorator:
    """测试注册装饰器"""

    def test_register_decorator_function(self):
        """测试注册装饰器函数"""
        with patch("src.adapters.registry.get_global_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry

            @register_adapter(name="test_adapter", version="1.0.0")
            class TestAdapter:
                pass

            # 验证注册调用
            mock_registry.register.assert_called_once_with(
                "test_adapter", TestAdapter, version="1.0.0"
            )

    def test_register_decorator_with_no_name(self):
        """测试不带名称的注册装饰器"""
        with patch("src.adapters.registry.get_global_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry

            @register_adapter()
            class TestAdapter:
                pass

            # 验证使用类名注册
            mock_registry.register.assert_called_once_with("TestAdapter", TestAdapter)
