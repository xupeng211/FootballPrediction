"""
适配器工厂测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional, Type
from src.core.exceptions import AdapterError
# from src.adapters.factory_simple import AdapterFactory, get_adapter


class TestAdapterFactory:
    """适配器工厂测试"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = AdapterFactory()
        assert factory._adapters == {}
        assert factory._instances == {}

    def test_register_adapter(self):
        """测试注册适配器"""
        factory = AdapterFactory()

        class TestAdapter:
            def __init__(self, config):
                self.config = config

        # 注册适配器
        factory.register_adapter("test", TestAdapter)
        assert "test" in factory._adapters
        assert factory._adapters["test"]["class"] == TestAdapter

    def test_register_duplicate_adapter(self):
        """测试注册重复适配器"""
        factory = AdapterFactory()

        class TestAdapter:
            pass

        # 第一次注册
        factory.register_adapter("test", TestAdapter)

        # 第二次注册应该失败
        with pytest.raises(AdapterError, match="Adapter 'test' already registered"):
            factory.register_adapter("test", TestAdapter)

    def test_create_adapter_without_config(self):
        """测试创建适配器（无配置）"""
        factory = AdapterFactory()

        class TestAdapter:
            def __init__(self, config=None):
                self.created = True
                self.config = config

        factory.register_adapter("test", TestAdapter)

        # 创建实例
        adapter = factory.create_adapter("test")
        assert adapter.created is True
        assert isinstance(adapter, TestAdapter)

    def test_create_adapter_with_config(self):
        """测试创建适配器（带配置）"""
        factory = AdapterFactory()

        class TestAdapter:
            def __init__(self, config):
                self.config = config

        factory.register_adapter("test", TestAdapter)

        config = {"host": "localhost", "port": 5432}
        adapter = factory.create_adapter("test", config)

        assert adapter.config == config

    def test_create_unregistered_adapter(self):
        """测试创建未注册的适配器"""
        factory = AdapterFactory()

        with pytest.raises(AdapterError, match="No adapter registered for 'unknown'"):
            factory.create_adapter("unknown")

    def test_singleton_behavior(self):
        """测试单例行为"""
        factory = AdapterFactory()

        class TestAdapter:
            def __init__(self, config=None):
                self.instance_id = id(self)

        factory.register_adapter("test", TestAdapter)

        # 创建两个实例
        adapter1 = factory.create_adapter("test", singleton=True)
        adapter2 = factory.create_adapter("test", singleton=True)

        # 应该是同一个实例
        assert adapter1 is adapter2
        assert adapter1.instance_id == adapter2.instance_id

    def test_non_singleton_behavior(self):
        """测试非单例行为"""
        factory = AdapterFactory()

        class TestAdapter:
            def __init__(self, config=None):
                self.instance_id = id(self)

        factory.register_adapter("test", TestAdapter)

        # 创建两个实例（非单例）
        adapter1 = factory.create_adapter("test", singleton=False)
        adapter2 = factory.create_adapter("test", singleton=False)

        # 应该是不同的实例
        assert adapter1 is not adapter2
        assert adapter1.instance_id != adapter2.instance_id

    def test_create_adapter_with_error(self):
        """测试创建适配器时发生错误"""
        factory = AdapterFactory()

        class FailingAdapter:
            def __init__(self, config):
                raise ValueError("Configuration error")

        factory.register_adapter("failing", FailingAdapter)

        with pytest.raises(AdapterError, match="Failed to create adapter 'failing'"):
            factory.create_adapter("failing", {"invalid": "config"})

    def test_list_registered_adapters(self):
        """测试列出已注册的适配器"""
        factory = AdapterFactory()

        class Adapter1:
            pass

        class Adapter2:
            pass

        factory.register_adapter("adapter1", Adapter1)
        factory.register_adapter("adapter2", Adapter2)

        adapters = factory.list_adapters()
        adapter_names = [name for name, _ in adapters]
        assert set(adapter_names) == {"adapter1", "adapter2"}

    def test_unregister_adapter(self):
        """测试注销适配器"""
        factory = AdapterFactory()

        class TestAdapter:
            pass

        # 注册适配器
        factory.register_adapter("test", TestAdapter)
        assert "test" in factory._adapters

        # 注销适配器
        factory.unregister_adapter("test")
        assert "test" not in factory._adapters

    def test_unregister_nonexistent_adapter(self):
        """测试注销不存在的适配器"""
        factory = AdapterFactory()

        with pytest.raises(
            AdapterError, match="No adapter registered for 'nonexistent'"
        ):
            factory.unregister_adapter("nonexistent")

    def test_get_adapter_type(self):
        """测试获取适配器类型"""
        factory = AdapterFactory()

        class TestAdapter:
            pass

        factory.register_adapter("test", TestAdapter)

        adapter_type = factory.get_adapter_type("test")
        assert adapter_type is TestAdapter

    def test_create_adapter_with_lifecycle(self):
        """测试创建带生命周期的适配器"""
        factory = AdapterFactory()

        class LifecycleAdapter:
            def __init__(self, config):
                self.config = config
                self.initialized = False

            async def initialize(self):
                self.initialized = True

            async def close(self):
                self.initialized = False

        factory.register_adapter("lifecycle", LifecycleAdapter)

        config = {"timeout": 30}
        adapter = factory.create_adapter("lifecycle", config)

        import asyncio

        asyncio.run(adapter.initialize())
        assert adapter.initialized is True

    def test_factory_with_multiple_configurations(self):
        """测试工厂使用多种配置"""
        factory = AdapterFactory()

        class ConfigurableAdapter:
            def __init__(self, config):
                self.config = config

        factory.register_adapter("configurable", ConfigurableAdapter)

        # 创建不同配置的适配器
        config1 = {"env": "dev", "debug": True}
        config2 = {"env": "prod", "debug": False}

        adapter1 = factory.create_adapter("configurable", config1)
        adapter2 = factory.create_adapter("configurable", config2)

        assert adapter1.config == config1
        assert adapter2.config == config2
        assert adapter1 is not adapter2

    def test_adapter_factory_context_manager(self):
        """测试适配器工厂上下文管理器"""
        factory = AdapterFactory()

        class ContextAdapter:
            def __init__(self, config):
                self.config = config
                self.open = False

            def __enter__(self):
                self.open = True
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.open = False

        factory.register_adapter("context", ContextAdapter)

        # 使用上下文管理器
        with factory.create_adapter("context", {"test": True}) as adapter:
            assert adapter.open is True
            assert adapter.config == {"test": True}

        assert adapter.open is False

    def test_factory_global_instance(self):
        """测试全局工厂实例"""
        # 获取全局实例
        factory1 = AdapterFactory.get_instance()
        factory2 = AdapterFactory.get_instance()

        # 应该是同一个实例
        assert factory1 is factory2


class TestGetAdapterFunction:
    """测试get_adapter函数"""

    def test_get_adapter_function(self):
        """测试get_adapter便捷函数"""
        # 模拟全局工厂
        with patch(
            "src.adapters.factory.AdapterFactory.get_instance"
        ) as mock_get_factory:
            mock_factory = MagicMock()
            mock_adapter = MagicMock()
            mock_factory.create_adapter.return_value = mock_adapter
            mock_get_factory.return_value = mock_factory

            # 调用便捷函数
            result = get_adapter("test_type", {"config": "value"})

            # 验证调用
            mock_factory.create_adapter.assert_called_once_with(
                "test_type", {"config": "value"}
            )
            assert result is mock_adapter

    def test_get_adapter_with_no_config(self):
        """测试get_adapter无配置"""
        with patch(
            "src.adapters.factory.AdapterFactory.get_instance"
        ) as mock_get_factory:
            mock_factory = MagicMock()
            mock_adapter = MagicMock()
            mock_factory.create_adapter.return_value = mock_adapter
            mock_get_factory.return_value = mock_factory

            # 调用无配置
            result = get_adapter("simple")

            mock_factory.create_adapter.assert_called_once_with("simple", None)
            assert result is mock_adapter

    def test_get_adapter_preserves_singleton(self):
        """测试get_adapter保持单例设置"""
        with patch(
            "src.adapters.factory.AdapterFactory.get_instance"
        ) as mock_get_factory:
            mock_factory = MagicMock()
            mock_adapter = MagicMock()
            mock_factory.create_adapter.return_value = mock_adapter
            mock_get_factory.return_value = mock_factory

            # 调用带单例参数
            get_adapter("test", {"config": "value"}, singleton=True)

            mock_factory.create_adapter.assert_called_once_with(
                "test", {"config": "value"}, singleton=True
            )
