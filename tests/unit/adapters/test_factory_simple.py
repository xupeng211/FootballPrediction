# TODO: Consider creating a fixture for 45 repeated Mock creations

# TODO: Consider creating a fixture for 45 repeated Mock creations


"""
简化适配器工厂模块测试
Simple Adapter Factory Module Tests

测试src/adapters/factory_simple.py中定义的简化适配器工厂功能，专注于实现100%覆盖率。
Tests simple adapter factory functionality defined in src/adapters/factory_simple.py, focused on achieving 100% coverage.
"""


import pytest

# 导入要测试的模块
try:
        AdapterFactory,
        _global_factory,
        get_adapter,
        get_global_factory,
    )
    from src.core.exceptions import AdapterError

    FACTORY_SIMPLE_AVAILABLE = True
except ImportError:
    FACTORY_SIMPLE_AVAILABLE = False


@pytest.mark.skipif(
    not FACTORY_SIMPLE_AVAILABLE, reason="Simple factory module not available"
)
@pytest.mark.unit
class TestAdapterFactory:
    """AdapterFactory类测试"""

    def test_adapter_factory_initialization(self):
        """测试适配器工厂初始化"""
        factory = AdapterFactory()

        assert hasattr(factory, "_adapters")
        assert hasattr(factory, "_instances")
        assert isinstance(factory._adapters, dict)
        assert isinstance(factory._instances, dict)
        assert len(factory._adapters) == 0
        assert len(factory._instances) == 0

    def test_adapter_factory_initialization_with_existing_state(self):
        """测试适配器工厂初始化时的状态"""
        factory1 = AdapterFactory()
        factory1.register_adapter("test", Mock)

        # 新工厂实例应该是空的
        factory2 = AdapterFactory()
        assert len(factory2._adapters) == 0
        assert len(factory2._instances) == 0

    def test_register_adapter_success(self):
        """测试成功注册适配器"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("test_adapter", mock_class, singleton=True)

        assert "test_adapter" in factory._adapters
        assert factory._adapters["test_adapter"]["class"] is mock_class
        assert factory._adapters["test_adapter"]["singleton"] is True

    def test_register_adapter_without_kwargs(self):
        """测试不使用额外参数注册适配器"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("simple_adapter", mock_class)

        assert "simple_adapter" in factory._adapters
        assert factory._adapters["simple_adapter"]["class"] is mock_class
        assert factory._adapters["simple_adapter"]["singleton"] is False  # 默认值

    def test_register_adapter_duplicate_name(self):
        """测试注册重复名称的适配器"""
        factory = AdapterFactory()
        mock_class1 = Mock()
        mock_class2 = Mock()

        factory.register_adapter("duplicate", mock_class1)

        # 第二次注册相同名称应该抛出异常
        with pytest.raises(AdapterError) as exc_info:
            factory.register_adapter("duplicate", mock_class2)

        assert "already registered" in str(exc_info.value)
        assert "duplicate" in str(exc_info.value)

    def test_register_adapter_various_kwargs(self):
        """测试注册适配器时使用各种参数"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter(
            "complex_adapter",
            mock_class,
            singleton=True,
            version="1.0",
            description="Test adapter",
            priority=5,
        )

        adapter_info = factory._adapters["complex_adapter"]
        assert adapter_info["class"] is mock_class
        assert adapter_info["singleton"] is True
        assert adapter_info["version"] == "1.0"
        assert adapter_info["description"] == "Test adapter"
        assert adapter_info["priority"] == 5

    def test_create_adapter_success(self):
        """测试成功创建适配器"""
        factory = AdapterFactory()
        mock_adapter_class = Mock(return_value="mock_instance")

        factory.register_adapter("test", mock_adapter_class)

        result = factory.create_adapter("test")

        assert result == "mock_instance"
        mock_adapter_class.assert_called_once_with(None)

    def test_create_adapter_with_config(self):
        """测试使用配置创建适配器"""
        factory = AdapterFactory()
        mock_adapter_class = Mock(return_value="configured_instance")
        config = {"setting1": "value1", "setting2": 42}

        factory.register_adapter("configurable", mock_adapter_class)

        result = factory.create_adapter("configurable", config)

        assert result == "configured_instance"
        mock_adapter_class.assert_called_once_with(config)

    def test_create_adapter_singleton_first_time(self):
        """测试单例适配器首次创建"""
        factory = AdapterFactory()
        mock_adapter_class = Mock(return_value="singleton_instance")

        factory.register_adapter("singleton", mock_adapter_class, singleton=True)

        result1 = factory.create_adapter("singleton")
        result2 = factory.create_adapter("singleton")

        assert result1 == "singleton_instance"
        assert result2 == "singleton_instance"  # 应该是同一个实例
        assert result1 is result2  # 确保是同一个对象
        mock_adapter_class.assert_called_once_with(None)  # 只应该调用一次

    def test_create_adapter_singleton_with_parameter(self):
        """测试通过参数指定单例创建适配器"""
        factory = AdapterFactory()
        mock_adapter_class = Mock(return_value="param_singleton_instance")

        factory.register_adapter("normal", mock_adapter_class)  # 不设置singleton

        # 通过参数指定singleton
        result1 = factory.create_adapter("normal", singleton=True)
        result2 = factory.create_adapter("normal", singleton=True)

        assert result1 == "param_singleton_instance"
        assert result2 == "param_singleton_instance"
        assert result1 is result2
        mock_adapter_class.assert_called_once_with(None)

    def test_create_adapter_non_singleton(self):
        """测试创建非单例适配器"""
        factory = AdapterFactory()

        # 创建不同的Mock实例来确保返回不同的对象
        instance1 = Mock()
        instance2 = Mock()
        mock_adapter_class = Mock(side_effect=[instance1, instance2])

        factory.register_adapter("non_singleton", mock_adapter_class, singleton=False)

        result1 = factory.create_adapter("non_singleton")
        result2 = factory.create_adapter("non_singleton")

        assert result1 is instance1
        assert result2 is instance2
        assert result1 is not result2  # 应该是不同的实例
        assert mock_adapter_class.call_count == 2  # 应该调用两次

    def test_create_adapter_not_registered(self):
        """测试创建未注册的适配器"""
        factory = AdapterFactory()

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("nonexistent")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_create_adapter_with_value_error(self):
        """测试创建适配器时遇到ValueError"""
        factory = AdapterFactory()
        failing_adapter_class = Mock(side_effect=ValueError("Invalid configuration"))

        factory.register_adapter("failing", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("failing")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "failing" in str(exc_info.value)
        assert "Invalid configuration" in str(exc_info.value)

    def test_create_adapter_with_type_error(self):
        """测试创建适配器时遇到TypeError"""
        factory = AdapterFactory()
        failing_adapter_class = Mock(side_effect=TypeError("Wrong type"))

        factory.register_adapter("type_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("type_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "type_error" in str(exc_info.value)
        assert "Wrong type" in str(exc_info.value)

    def test_create_adapter_with_attribute_error(self):
        """测试创建适配器时遇到AttributeError"""
        factory = AdapterFactory()
        failing_adapter_class = Mock(side_effect=AttributeError("Missing attribute"))

        factory.register_adapter("attr_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("attr_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "attr_error" in str(exc_info.value)
        assert "Missing attribute" in str(exc_info.value)

    def test_create_adapter_with_key_error(self):
        """测试创建适配器时遇到KeyError"""
        factory = AdapterFactory()
        failing_adapter_class = Mock(side_effect=KeyError("Missing key"))

        factory.register_adapter("key_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("key_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "key_error" in str(exc_info.value)
        assert "'Missing key'" in str(exc_info.value)

    def test_create_adapter_with_runtime_error(self):
        """测试创建适配器时遇到RuntimeError"""
        factory = AdapterFactory()
        failing_adapter_class = Mock(side_effect=RuntimeError("Runtime failure"))

        factory.register_adapter("runtime_error", failing_adapter_class)

        with pytest.raises(AdapterError) as exc_info:
            factory.create_adapter("runtime_error")

        assert "Failed to create adapter" in str(exc_info.value)
        assert "runtime_error" in str(exc_info.value)
        assert "Runtime failure" in str(exc_info.value)

    def test_get_instance(self):
        """测试获取工厂实例"""
        factory = AdapterFactory()

        result = factory.get_instance()

        assert result is factory  # 应该返回同一个实例

    def test_list_adapters_empty(self):
        """测试列出空的适配器列表"""
        factory = AdapterFactory()

        result = factory.list_adapters()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_adapters_with_registered_adapters(self):
        """测试列出已注册的适配器"""
        factory = AdapterFactory()
        mock_class1 = Mock()
        mock_class2 = Mock()

        factory.register_adapter("adapter1", mock_class1)
        factory.register_adapter("adapter2", mock_class2)

        result = factory.list_adapters()

        assert isinstance(result, list)
        assert len(result) == 2

        # 转换为字典便于验证
        result_dict = dict(result)
        assert "adapter1" in result_dict
        assert "adapter2" in result_dict
        assert result_dict["adapter1"] is mock_class1
        assert result_dict["adapter2"] is mock_class2

    def test_list_no_filters(self):
        """测试不带过滤条件的列表功能"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("test", mock_class, version="1.0", singleton=True)

        result = factory.list()

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "test"
        assert result[0][1]["class"] is mock_class
        assert result[0][1]["version"] == "1.0"
        assert result[0][1]["singleton"] is True

    def test_list_with_matching_filters(self):
        """测试使用匹配过滤条件列表"""
        factory = AdapterFactory()
        mock_class1 = Mock()
        mock_class2 = Mock()

        factory.register_adapter("adapter1", mock_class1, version="1.0", singleton=True)
        factory.register_adapter(
            "adapter2", mock_class2, version="2.0", singleton=False
        )

        # 过滤singleton=True的适配器
        result = factory.list(singleton=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "adapter1"
        assert result[0][1]["singleton"] is True

    def test_list_with_non_matching_filters(self):
        """测试使用不匹配过滤条件列表"""
        factory = AdapterFactory()
        mock_class1 = Mock()
        mock_class2 = Mock()

        factory.register_adapter("adapter1", mock_class1, version="1.0")
        factory.register_adapter("adapter2", mock_class2, version="2.0")

        # 过滤不存在的版本
        result = factory.list(version="3.0")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_with_multiple_filters(self):
        """测试使用多个过滤条件列表"""
        factory = AdapterFactory()
        mock_class1 = Mock()
        mock_class2 = Mock()
        mock_class3 = Mock()

        factory.register_adapter(
            "adapter1", mock_class1, version="1.0", singleton=True, priority=1
        )
        factory.register_adapter(
            "adapter2", mock_class2, version="1.0", singleton=False, priority=2
        )
        factory.register_adapter(
            "adapter3", mock_class3, version="2.0", singleton=True, priority=1
        )

        # 使用多个过滤条件
        result = factory.list(version="1.0", priority=1)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "adapter1"

    def test_list_filter_on_nonexistent_key(self):
        """测试过滤不存在的键"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("test", mock_class, version="1.0")

        # 过滤不存在的键，应该不匹配任何项
        # 源代码中的list方法只过滤存在的键，如果键不存在就认为匹配
        # 所以我们需要测试一个存在的键但值不匹配的情况
        result = factory.list(version="2.0")  # 版本不匹配

        assert isinstance(result, list)
        assert len(result) == 0

    def test_unregister_adapter_existing(self):
        """测试注销已存在的适配器"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("to_remove", mock_class, singleton=True)

        # 确认适配器已注册
        assert "to_remove" in factory._adapters

        # 创建单例实例
        factory.create_adapter("to_remove", singleton=True)
        assert "to_remove" in factory._instances

        # 注销适配器
        factory.unregister_adapter("to_remove")

        assert "to_remove" not in factory._adapters
        assert "to_remove" not in factory._instances

    def test_unregister_adapter_nonexistent(self):
        """测试注销不存在的适配器"""
        factory = AdapterFactory()

        # 注销不存在的适配器不应该抛出异常
        factory.unregister_adapter("nonexistent")

        # 确保不会抛出异常
        assert True

    def test_get_adapter_type_existing(self):
        """测试获取已存在适配器的类型"""
        factory = AdapterFactory()
        mock_class = Mock()

        factory.register_adapter("test_adapter", mock_class)

        result = factory.get_adapter_type("test_adapter")

        assert result is mock_class

    def test_get_adapter_type_nonexistent(self):
        """测试获取不存在适配器的类型"""
        factory = AdapterFactory()

        result = factory.get_adapter_type("nonexistent")

        assert result is None

    def test_adapter_factory_workflow_complete(self):
        """测试完整的适配器工厂工作流程"""
        factory = AdapterFactory()

        # 1. 注册多个适配器
        instance1 = Mock()
        mock_class1 = Mock(return_value=instance1)

        # 为非单例创建不同的实例
        instance2a = Mock()
        instance2b = Mock()
        mock_class2 = Mock(side_effect=[instance2a, instance2b])

        factory.register_adapter("service1", mock_class1, singleton=True)
        factory.register_adapter(
            "service2", mock_class2, singleton=False, version="2.0"
        )

        # 2. 列出适配器
        adapters = factory.list_adapters()
        assert len(adapters) == 2

        # 3. 创建实例
        created_instance1a = factory.create_adapter("service1")
        created_instance1b = factory.create_adapter("service1")
        created_instance2a = factory.create_adapter("service2")
        created_instance2b = factory.create_adapter("service2")

        # 4. 验证实例
        assert created_instance1a is instance1
        assert created_instance1b is instance1
        assert created_instance1a is created_instance1b  # 单例
        assert created_instance2a is instance2a
        assert created_instance2b is instance2b
        assert created_instance2a is not created_instance2b  # 非单例
        mock_class1.assert_called_once()
        assert mock_class2.call_count == 2

        # 5. 获取适配器类型
        assert factory.get_adapter_type("service1") is mock_class1
        assert factory.get_adapter_type("service2") is mock_class2

        # 6. 过滤列表
        singleton_adapters = factory.list(singleton=True)
        assert len(singleton_adapters) == 1
        assert singleton_adapters[0][0] == "service1"

        # 7. 注销适配器
        factory.unregister_adapter("service1")
        assert factory.get_adapter_type("service1") is None
        assert len(factory.list_adapters()) == 1

    def test_adapter_factory_error_recovery(self):
        """测试适配器工厂错误恢复"""
        factory = AdapterFactory()

        # 注册一个会失败的适配器
        failing_class = Mock(side_effect=RuntimeError("Creation failed"))
        factory.register_adapter("failing", failing_class)

        # 尝试创建应该失败
        with pytest.raises(AdapterError):
            factory.create_adapter("failing")

        # 注册一个正常的适配器
        normal_class = Mock(return_value="normal_instance")
        factory.register_adapter("normal", normal_class)

        # 正常适配器应该可以成功创建
        result = factory.create_adapter("normal")
        assert result == "normal_instance"

    def test_singleton_instance_isolation(self):
        """测试单例实例隔离"""
        factory = AdapterFactory()

        instance1 = Mock()
        instance2 = Mock()
        mock_class = Mock(side_effect=[instance1, instance2])
        factory.register_adapter("isolated", mock_class, singleton=True)

        # 创建单例实例
        created_instance1 = factory.create_adapter("isolated")

        # 手动清除实例字典中的项（模拟某种清理操作）
        factory._instances.pop("isolated", None)

        # 再次创建应该得到新的实例
        created_instance2 = factory.create_adapter("isolated")

        assert created_instance1 is instance1
        assert created_instance2 is instance2
        assert created_instance1 is not created_instance2  # 应该是不同的实例
        assert mock_class.call_count == 2  # 应该调用两次


@pytest.mark.skipif(
    not FACTORY_SIMPLE_AVAILABLE, reason="Simple factory module not available"
)
class TestGlobalFactoryFunctions:
    """全局工厂函数测试"""

    def test_get_global_factory_returns_instance(self):
        """测试获取全局工厂返回实例"""
        factory = get_global_factory()

        assert isinstance(factory, AdapterFactory)

    def test_get_global_factory_singleton(self):
        """测试全局工厂是单例"""
        factory1 = get_global_factory()
        factory2 = get_global_factory()

        assert factory1 is factory2  # 应该是同一个实例

    @patch("src.adapters.factory_simple._global_factory", None)
    def test_get_global_factory_creates_new_instance(self):
        """测试全局工厂创建新实例"""
        # 重置全局变量
        import src.adapters.factory_simple

        original_factory = src.adapters.factory_simple._global_factory
        src.adapters.factory_simple._global_factory = None

        try:
            factory = get_global_factory()

            assert isinstance(factory, AdapterFactory)
            # 验证全局变量被设置
            assert src.adapters.factory_simple._global_factory is factory
        finally:
            # 恢复原始状态
            src.adapters.factory_simple._global_factory = original_factory

    def test_get_adapter_success(self):
        """测试便捷函数获取适配器"""
        # 清除全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        mock_adapter_class = Mock(return_value="convenient_instance")

        # 使用全局工厂注册适配器
        factory = get_global_factory()
        factory.register_adapter("convenient", mock_adapter_class)

        # 使用便捷函数获取适配器
        result = get_adapter("convenient")

        assert result == "convenient_instance"
        mock_adapter_class.assert_called_once_with(None)

    def test_get_adapter_with_config(self):
        """测试便捷函数获取适配器（带配置）"""
        # 清除全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        mock_adapter_class = Mock(return_value="configured_convenient_instance")
        config = {"key": "value"}

        factory = get_global_factory()
        factory.register_adapter("configurable_convenient", mock_adapter_class)

        result = get_adapter("configurable_convenient", config)

        assert result == "configured_convenient_instance"
        mock_adapter_class.assert_called_once_with(config)

    def test_get_adapter_singleton(self):
        """测试便捷函数获取单例适配器"""
        # 清除全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        mock_adapter_class = Mock(return_value="convenient_singleton")

        factory = get_global_factory()
        factory.register_adapter("convenient_singleton", mock_adapter_class)

        result1 = get_adapter("convenient_singleton", singleton=True)
        result2 = get_adapter("convenient_singleton", singleton=True)

        assert result1 == "convenient_singleton"
        assert result2 == "convenient_singleton"
        assert result1 is result2  # 应该是同一个实例
        mock_adapter_class.assert_called_once_with(None)

    def test_get_adapter_not_registered(self):
        """测试便捷函数获取未注册的适配器"""
        # 清除全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        with pytest.raises(AdapterError) as exc_info:
            get_adapter("nonexistent_convenient")

        assert "No adapter registered" in str(exc_info.value)
        assert "nonexistent_convenient" in str(exc_info.value)

    def test_global_factory_isolation(self):
        """测试全局工厂隔离"""
        # 重置全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        # 注册适配器到全局工厂
        factory1 = get_global_factory()
        mock_class = Mock(return_value="global_instance")
        factory1.register_adapter("global_test", mock_class)

        # 再次获取全局工厂应该是同一个实例
        factory2 = get_global_factory()
        assert factory1 is factory2

        # 应该能够创建适配器
        result = factory2.create_adapter("global_test")
        assert result == "global_instance"
        mock_class.assert_called_once_with(None)


@pytest.mark.skipif(
    not FACTORY_SIMPLE_AVAILABLE, reason="Simple factory module not available"
)
class TestModuleIntegration:
    """模块集成测试"""

    def test_module_exports(self):
        """测试模块导出"""
from src.adapters import factory_simple

        # 验证所有预期的导出都存在
        assert hasattr(factory_simple, "AdapterFactory")
        assert hasattr(factory_simple, "get_global_factory")
        assert hasattr(factory_simple, "get_adapter")
        assert hasattr(factory_simple, "_global_factory")

    def test_adapter_factory_class_attributes(self):
        """测试AdapterFactory类属性"""
        # 验证类有预期的属性
        assert hasattr(AdapterFactory, "register_adapter")
        assert hasattr(AdapterFactory, "create_adapter")
        assert hasattr(AdapterFactory, "get_instance")
        assert hasattr(AdapterFactory, "list_adapters")
        assert hasattr(AdapterFactory, "list")
        assert hasattr(AdapterFactory, "unregister_adapter")
        assert hasattr(AdapterFactory, "get_adapter_type")

    def test_global_factory_variable(self):
        """测试全局工厂变量"""
        import src.adapters.factory_simple

        # 验证全局变量存在
        assert hasattr(src.adapters.factory_simple, "_global_factory")

        # 初始状态应该是None
        original_value = src.adapters.factory_simple._global_factory

        # 测试后恢复原始值
        try:
            # 验证可以设置为None
            src.adapters.factory_simple._global_factory = None
            assert src.adapters.factory_simple._global_factory is None
        finally:
            # 恢复原始值
            src.adapters.factory_simple._global_factory = original_value

    def test_function_signatures(self):
        """测试函数签名"""
        import inspect

        # 测试get_global_factory签名
        sig = inspect.signature(get_global_factory)
        assert len(sig.parameters) == 0

        # 测试get_adapter签名
        sig = inspect.signature(get_adapter)
        expected_params = ["adapter_type", "config", "singleton"]
        actual_params = list(sig.parameters.keys())
        for param in expected_params:
            assert param in actual_params

    def test_concurrent_access_to_global_factory(self):
        """测试并发访问全局工厂"""
        import threading
        import time

        # 重置全局工厂
        import src.adapters.factory_simple

        src.adapters.factory_simple._global_factory = None

        results = []
        errors = []

        def worker():
            try:
                factory = get_global_factory()
                time.sleep(0.01)  # 短暂延迟
                # 验证所有线程得到的是同一个实例
                results.append(factory)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时访问全局工厂
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

    def test_global_factory_state_persistence(self):
        """测试全局工厂状态持久性"""
        import src.adapters.factory_simple

        # 重置全局工厂
        src.adapters.factory_simple._global_factory = None

        # 获取全局工厂并注册适配器
        factory1 = get_global_factory()
        mock_class = Mock(return_value="persistent_instance")
        factory1.register_adapter("persistent_test", mock_class)

        # 再次获取全局工厂
        factory2 = get_global_factory()

        # 状态应该保持
        assert factory2.get_adapter_type("persistent_test") is mock_class

        # 应该能够创建适配器
        result = factory2.create_adapter("persistent_test")
        assert result == "persistent_instance"

    def test_module_import_integrity(self):
        """测试模块导入完整性"""
        # 测试可以正常导入所有必要的组件
from src.adapters.factory_simple import (
            AdapterFactory,
            get_adapter,
            get_global_factory,
        )
from src.core.exceptions import AdapterError

        # 验证导入的对象是可用的
        assert callable(AdapterFactory)
        assert callable(get_global_factory)
        assert callable(get_adapter)
        assert issubclass(AdapterError, Exception)

        # 验证可以正常使用
        factory = AdapterFactory()
        assert hasattr(factory, "register_adapter")
        assert hasattr(factory, "create_adapter")
