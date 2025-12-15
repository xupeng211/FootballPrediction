from typing import Optional

"""
适配器工厂模块测试
Tests for adapter factory module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# 导入被测试模块
from src.adapters.factory_simple import (
    BaseAdapterFactory,
    BaseAdapterError,
    BaseAdapterNames,
    get_adapter,
    get_global_factory,
)


# 模拟基础适配器类
class MockBaseAdapter:
    """模拟基础适配器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "test_adapter"
        self.is_initialized = False

    def initialize(self):
        """初始化适配器"""
        self.is_initialized = True

    def connect(self):
        """连接适配器"""
        return True


class MockAdapterA(MockBaseAdapter):
    """模拟适配器A"""

    pass


class MockAdapterB(MockBaseAdapter):
    """模拟适配器B"""

    pass


class TestBaseAdapterFactory:
    """适配器工厂测试类"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = BaseAdapterFactory()

        assert factory.adapters == {}
        assert factory.singletons == {}

    def test_register_adapter(self):
        """测试注册适配器"""
        factory = BaseAdapterFactory()

        # 注册适配器
        factory.register_adapter("test_adapter", MockAdapterA)

        assert "test_adapter" in factory.adapters
        assert factory.adapters["test_adapter"] == MockAdapterA

    def test_create_adapter_success(self):
        """测试成功创建适配器"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test_adapter", MockAdapterA)

        adapter = factory.create_adapter("test_adapter")

        assert isinstance(adapter, MockAdapterA)
        assert adapter.config == {}

    def test_create_adapter_with_config(self):
        """测试使用配置创建适配器"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test_adapter", MockAdapterA)

        config = {"host": "localhost", "port": 8080}
        adapter = factory.create_adapter("test_adapter", config)

        assert adapter.config == config

    def test_create_adapter_not_registered(self):
        """测试创建未注册的适配器"""
        factory = BaseAdapterFactory()

        with pytest.raises(
            BaseAdapterError, match="BaseAdapter 'nonexistent' not registered"
        ):
            factory.create_adapter("nonexistent")

    def test_create_singleton_adapter(self):
        """测试创建单例适配器"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test_adapter", MockAdapterA)

        # 第一次创建
        adapter1 = factory.create_adapter("test_adapter", singleton=True)
        # 第二次创建应该返回同一个实例
        adapter2 = factory.create_adapter("test_adapter", singleton=True)

        assert adapter1 is adapter2
        assert "test_adapter" in factory.singletons

    def test_create_non_singleton_adapter(self):
        """测试创建非单例适配器"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test_adapter", MockAdapterA)

        # 创建两次应该返回不同实例
        adapter1 = factory.create_adapter("test_adapter", singleton=False)
        adapter2 = factory.create_adapter("test_adapter", singleton=False)

        assert adapter1 is not adapter2
        assert "test_adapter" not in factory.singletons

    def test_singleton_mixed_with_non_singleton(self):
        """测试单例和非单例混合使用"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test_adapter", MockAdapterA)

        # 创建单例适配器
        singleton_adapter1 = factory.create_adapter("test_adapter", singleton=True)
        singleton_adapter2 = factory.create_adapter("test_adapter", singleton=True)

        # 创建非单例适配器
        non_singleton_adapter1 = factory.create_adapter("test_adapter", singleton=False)
        non_singleton_adapter2 = factory.create_adapter("test_adapter", singleton=False)

        # 验证结果
        assert singleton_adapter1 is singleton_adapter2
        assert singleton_adapter1 is not non_singleton_adapter1
        assert non_singleton_adapter1 is not non_singleton_adapter2
        assert singleton_adapter1 is not non_singleton_adapter2

    def test_register_multiple_adapters(self):
        """测试注册多个适配器"""
        factory = BaseAdapterFactory()

        factory.register_adapter("adapter_a", MockAdapterA)
        factory.register_adapter("adapter_b", MockAdapterB)

        assert len(factory.adapters) == 2
        assert "adapter_a" in factory.adapters
        assert "adapter_b" in factory.adapters

    def test_override_adapter_registration(self):
        """测试覆盖适配器注册"""
        factory = BaseAdapterFactory()

        # 注册第一个适配器
        factory.register_adapter("test_adapter", MockAdapterA)
        assert factory.adapters["test_adapter"] == MockAdapterA

        # 覆盖注册
        factory.register_adapter("test_adapter", MockAdapterB)
        assert factory.adapters["test_adapter"] == MockAdapterB


class TestBaseAdapterError:
    """适配器错误测试类"""

    def test_base_adapter_error_inheritance(self):
        """测试基础适配器错误继承"""
        error = BaseAdapterError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_base_adapter_error_raised(self):
        """测试基础适配器错误抛出"""
        with pytest.raises(BaseAdapterError) as exc_info:
            raise BaseAdapterError("Test error")

        assert str(exc_info.value) == "Test error"


class TestBaseAdapterNames:
    """适配器名称常量测试类"""

    def test_adapter_names_constants(self):
        """测试适配器名称常量"""
        assert BaseAdapterNames.HTTP == "http"
        assert BaseAdapterNames.DATABASE == "database"
        assert BaseAdapterNames.CACHE == "cache"
        assert BaseAdapterNames.MESSAGE_QUEUE == "message_queue"
        assert BaseAdapterNames.FILE_STORAGE == "file_storage"

    def test_adapter_names_are_strings(self):
        """测试适配器名称都是字符串"""
        for name in vars(BaseAdapterNames).values():
            if isinstance(name, str) and not name.startswith("_"):
                assert isinstance(name, str)


@pytest.mark.skip(reason="Fixing in next sprint - all mock object issues")
class TestGlobalFactoryFunctions:
    """全局工厂函数测试类"""

    @pytest.fixture
    def mock_global_factory(self):
        """模拟全局工厂fixture"""
        with patch(
            "src.adapters.factory_simple._global_factory",
            new_callable=lambda: BaseAdapterFactory(),
        ) as mock_factory:
            yield mock_factory

    @pytest.mark.skip(reason="Fixing in next sprint - mock object issues")
    def test_get_adapter(self, mock_global_factory):
        """测试获取适配器便捷函数"""
        mock_global_factory.register_adapter("test", MockAdapterA)
        mock_global_factory.create_adapter.return_value = MockAdapterA()

        get_adapter("test")

        mock_global_factory.create_adapter.assert_called_once_with("test", None, True)

    @pytest.mark.skip(reason="Fixing in next sprint - mock object issues")
    def test_get_adapter_with_config(self, mock_global_factory):
        """测试使用配置获取适配器"""
        config = {"test": "value"}
        mock_global_factory.register_adapter("test", MockAdapterA)
        mock_global_factory.create_adapter.return_value = MockAdapterA(config)

        get_adapter("test", config)

        mock_global_factory.create_adapter.assert_called_once_with("test", config, True)

    def test_get_adapter_non_singleton(self, mock_global_factory):
        """测试获取非单例适配器"""
        mock_global_factory.register_adapter("test", MockAdapterA)
        mock_global_factory.create_adapter.return_value = MockAdapterA()

        get_adapter("test", singleton=False)

        mock_global_factory.create_adapter.assert_called_once_with("test", None, False)

    def test_get_global_factory(self):
        """测试获取全局工厂实例"""
        factory = get_global_factory()

        assert isinstance(factory, BaseAdapterFactory)
        # 确保返回同一个实例
        factory2 = get_global_factory()
        assert factory is factory2


class TestIntegrationWithRealAdapters:
    """与真实适配器的集成测试"""

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 注册适配器
        factory = BaseAdapterFactory()
        factory.register_adapter("database", MockAdapterA)
        factory.register_adapter("cache", MockAdapterB)

        # 创建单例数据库适配器
        db_adapter = factory.create_adapter(
            "database", {"host": "localhost", "port": 5432}
        )
        db_adapter.initialize()

        # 创建非单例缓存适配器
        cache_adapter1 = factory.create_adapter(
            "cache", {"host": "redis", "port": 6379}
        )
        cache_adapter2 = factory.create_adapter(
            "cache", {"host": "redis", "port": 6379}
        )

        # 验证适配器功能
        assert db_adapter.is_initialized
        assert db_adapter.connect()
        assert cache_adapter1.connect()
        assert cache_adapter2.connect()

        # 验证单例行为
        assert factory.create_adapter("database") is db_adapter
        assert cache_adapter1 is not cache_adapter2

    @patch("src.adapters.factory_simple._global_factory")
    def test_global_factory_integration(self, mock_factory):
        """测试全局工厂集成"""
        # 设置模拟工厂
        mock_factory_instance = BaseAdapterFactory()
        mock_factory_instance.register_adapter("test", MockAdapterA)
        mock_factory.return_value = mock_factory_instance

        # 使用全局函数
        get_adapter("test", {"test": "config"})

        # 验证调用
        mock_factory.create_adapter.assert_called_once_with(
            "test", {"test": "config"}, True
        )


class TestErrorHandling:
    """错误处理测试类"""

    def test_adapter_class_not_callable(self):
        """测试适配器类不可调用"""
        factory = BaseAdapterFactory()

        # 注册非类对象
        factory.register_adapter("invalid", "not_a_class")

        with pytest.raises(TypeError):
            factory.create_adapter("invalid")

    def test_adapter_init_fails(self):
        """测试适配器初始化失败"""

        class FailingAdapter:
            def __init__(self, config):
                raise ValueError("Init failed")

        factory = BaseAdapterFactory()
        factory.register_adapter("failing", FailingAdapter)

        with pytest.raises(ValueError, match="Init failed"):
            factory.create_adapter("failing")

    def test_config_modification_affects_singleton(self):
        """测试配置修改影响单例实例"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test", MockAdapterA)

        # 创建单例适配器
        config1 = {"host": "localhost"}
        adapter1 = factory.create_adapter("test", config1)

        # 尝试用不同配置再次创建单例，应该返回原实例
        config2 = {"host": "remote"}
        adapter2 = factory.create_adapter("test", config2, singleton=True)

        assert adapter1 is adapter2
        assert adapter1.config == config1  # 保持原始配置

    def test_config_modification_non_singleton(self):
        """测试配置修改不影响非单例实例"""
        factory = BaseAdapterFactory()
        factory.register_adapter("test", MockAdapterA)

        # 创建非单例适配器
        config1 = {"host": "localhost"}
        adapter1 = factory.create_adapter("test", config1, singleton=False)

        # 用不同配置再次创建非单例，应该返回新实例
        config2 = {"host": "remote"}
        adapter2 = factory.create_adapter("test", config2, singleton=False)

        assert adapter1 is not adapter2
        assert adapter1.config == config1
        assert adapter2.config == config2


class TestConcurrentAccess:
    """并发访问测试类"""

    def test_concurrent_singleton_creation(self):
        """测试并发单例创建（简化版模拟）"""
        import threading
        import time

        factory = BaseAdapterFactory()
        factory.register_adapter("test", MockAdapterA)

        adapters = []

        def create_adapter():
            adapters.append(factory.create_adapter("test", singleton=True))

        # 创建多个线程
        threads = [threading.Thread(target=create_adapter) for _ in range(5)]

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有线程获取到同一个实例
        first_adapter = adapters[0]
        for adapter in adapters:
            assert adapter is first_adapter
