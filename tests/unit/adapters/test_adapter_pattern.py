"""
适配器模式测试套件
Adapter Pattern Test Suite

测试适配器模式的核心功能，包括基础适配器、组合适配器、注册表等。
"""

from datetime import datetime
from typing import Any
from unittest.mock import Mock

import pytest

# 尝试从src导入，失败则使用本地导入
try:
    from src.adapters.base import (
        Adaptee,
        Adapter,
        AdapterStatus,
        BaseAdapter,
        CompositeAdapter,
        DataTransformer,
        Target,
    )
    from src.adapters.factory import AdapterConfig, AdapterFactory, AdapterGroupConfig
    from src.adapters.registry import AdapterError, AdapterRegistry
except ImportError as e:
    print(f"Warning: Import failed: {e}")
    # 直接导入避免__init__.py的语法错误
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src/adapters"))

    from base import (
        Adaptee,
        Adapter,
        AdapterStatus,
        BaseAdapter,
        CompositeAdapter,
        DataTransformer,
        Target,
    )
    from registry import AdapterError, AdapterRegistry

    # 为factory模块提供Mock实现
    class AdapterConfig:
        pass

    class AdapterGroupConfig:
        pass

    class AdapterFactory:
        def __init__(self):
            self.adapters = {}


class MockAdaptee(Adaptee):
    """模拟被适配者实现"""

    def __init__(self, name: str = "MockAdaptee"):
        self.name = name
        self.data_store = {}

    async def get_data(self, *args, **kwargs) -> Any:
        """获取原始数据"""
        key = kwargs.get("key", "default")
        return self.data_store.get(key, f"mock_data_{key}")

    async def send_data(self, data: Any) -> Any:
        """发送数据"""
        timestamp = datetime.now().isoformat()
        self.data_store[f"sent_{timestamp}"] = data
        return {"status": "success", "timestamp": timestamp}


class MockTarget(Target):
    """模拟目标接口实现"""

    def __init__(self, name: str = "MockTarget"):
        self.name = name
        self.request_count = 0

    async def request(self, *args, **kwargs) -> Any:
        """标准请求方法"""
        self.request_count += 1
        return {
            "target": self.name,
            "request_id": self.request_count,
            "args": args,
            "kwargs": kwargs,
        }


class MockAdapter(Adapter):
    """模拟适配器实现"""

    def __init__(self, name: str = "MockAdapter", adaptee: Adaptee = None):
        self.name = name
        self.adaptee = adaptee or MockAdaptee(f"AdapteeFor_{name}")
        self.request_count = 0

    async def request(self, *args, **kwargs) -> Any:
        """适配请求方法"""
        self.request_count += 1
        # 将目标请求转换为被适配者的操作
        if kwargs.get("action") == "get":
            return await self.adaptee.get_data(*args, **kwargs)
        elif kwargs.get("action") == "send":
            data = kwargs.get("data")
            return await self.adaptee.send_data(data)
        else:
            return {"adapter": self.name, "request_id": self.request_count}


class MockDataTransformer(DataTransformer):
    """模拟数据转换器"""

    def __init__(self, name: str = "MockTransformer"):
        self.name = name
        self.transform_count = 0

    async def transform(self, data: Any, **kwargs) -> Any:
        """转换数据格式"""
        self.transform_count += 1
        # 简单的数据转换逻辑
        if isinstance(data, dict):
            transformed = data.copy()
            transformed["transformed_by"] = self.name
            transformed["transform_count"] = self.transform_count
            return transformed
        else:
            return f"{self.name}_transformed_{data}"


class TestAdapterStatus:
    """适配器状态测试"""

    def test_adapter_status_enum_values(self):
        """测试适配器状态枚举值"""
        assert AdapterStatus.ACTIVE.value == "active"
        assert AdapterStatus.INACTIVE.value == "inactive"
        assert AdapterStatus.ERROR.value == "error"
        assert AdapterStatus.MAINTENANCE.value == "maintenance"

    def test_adapter_status_enum_count(self):
        """测试适配器状态枚举数量"""
        statuses = list(AdapterStatus)
        assert len(statuses) == 4
        assert AdapterStatus.ACTIVE in statuses
        assert AdapterStatus.INACTIVE in statuses
        assert AdapterStatus.ERROR in statuses
        assert AdapterStatus.MAINTENANCE in statuses


class TestAdaptee:
    """被适配者测试"""

    def test_mock_adaptee_initialization(self):
        """测试模拟被适配者初始化"""
        adaptee = MockAdaptee("TestAdaptee")
        assert adaptee.name == "TestAdaptee"
        assert isinstance(adaptee.data_store, dict)

    async def test_mock_adaptee_get_data(self):
        """测试模拟被适配者获取数据"""
        adaptee = MockAdaptee()
        result = await adaptee.get_data(key="test_key")
        assert result == "mock_data_test_key"

        # 设置数据并获取
        adaptee.data_store["custom_key"] = "custom_value"
        result = await adaptee.get_data(key="custom_key")
        assert result == "custom_value"

    async def test_mock_adaptee_send_data(self):
        """测试模拟被适配者发送数据"""
        adaptee = MockAdaptee()
        test_data = {"message": "test"}
        result = await adaptee.send_data(test_data)

        assert result["status"] == "success"
        assert "timestamp" in result
        assert len(adaptee.data_store) == 1

    def test_adaptee_interface_is_abstract(self):
        """测试被适配者接口是抽象的"""
        with pytest.raises(TypeError):
            Adaptee()


class TestTarget:
    """目标接口测试"""

    def test_mock_target_initialization(self):
        """测试模拟目标接口初始化"""
        target = MockTarget("TestTarget")
        assert target.name == "TestTarget"
        assert target.request_count == 0

    async def test_mock_target_request(self):
        """测试模拟目标接口请求"""
        target = MockTarget()
        result = await target.request("arg1", arg2="value2")

        assert result["target"] == "MockTarget"
        assert result["request_id"] == 1
        assert result["args"] == ("arg1",)
        assert result["kwargs"] == {"arg2": "value2"}
        assert target.request_count == 1

    def test_target_interface_is_abstract(self):
        """测试目标接口是抽象的"""
        with pytest.raises(TypeError):
            Target()


class TestAdapter:
    """适配器测试"""

    def test_mock_adapter_initialization(self):
        """测试模拟适配器初始化"""
        adapter = MockAdapter("TestAdapter")
        assert adapter.name == "TestAdapter"
        assert adapter.request_count == 0
        assert isinstance(adapter.adaptee, MockAdaptee)

    async def test_mock_adapter_request_get_action(self):
        """测试模拟适配器获取动作请求"""
        adapter = MockAdapter()
        result = await adapter.request(action="get", key="test_key")
        assert result == "mock_data_test_key"

    async def test_mock_adapter_request_send_action(self):
        """测试模拟适配器发送动作请求"""
        adapter = MockAdapter()
        test_data = {"message": "test"}
        result = await adapter.request(action="send", data=test_data)
        assert result["status"] == "success"

    async def test_mock_adapter_request_default_action(self):
        """测试模拟适配器默认动作请求"""
        adapter = MockAdapter()
        result = await adapter.request()
        assert result["adapter"] == "MockAdapter"
        assert result["request_id"] == 1


class TestBaseAdapter:
    """基础适配器测试"""

    def test_base_adapter_is_abstract(self):
        """测试基础适配器是抽象的"""
        with pytest.raises(TypeError):
            BaseAdapter()


class TestDataTransformer:
    """数据转换器测试"""

    def test_mock_data_transformer_initialization(self):
        """测试模拟数据转换器初始化"""
        transformer = MockDataTransformer("TestTransformer")
        assert transformer.name == "TestTransformer"
        assert transformer.transform_count == 0

    async def test_mock_data_transformer_transform_dict(self):
        """测试模拟数据转换器转换字典数据"""
        transformer = MockDataTransformer()
        input_data = {"key1": "value1", "key2": "value2"}
        result = await transformer.transform(input_data)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["transformed_by"] == "MockTransformer"
        assert result["transform_count"] == 1

    async def test_mock_data_transformer_transform_string(self):
        """测试模拟数据转换器转换字符串数据"""
        transformer = MockDataTransformer()
        result = await transformer.transform("test_string")
        assert result == "MockTransformer_transformed_test_string"
        assert transformer.transform_count == 1

    def test_data_transformer_interface_is_abstract(self):
        """测试数据转换器接口是抽象的"""
        with pytest.raises(TypeError):
            DataTransformer()


class TestCompositeAdapter:
    """组合适配器测试"""

    def test_composite_adapter_initialization(self):
        """测试组合适配器初始化"""
        adapter = CompositeAdapter("TestComposite")
        assert adapter.name == "TestComposite"
        assert adapter.adapters == []
        assert adapter.adapter_registry == {}
        assert adapter.status == AdapterStatus.ACTIVE
        assert adapter.last_error is None
        assert adapter.metrics["total_requests"] == 0

    def test_composite_adapter_initialization_with_custom_name(self):
        """测试组合适配器自定义名称初始化"""
        adapter = CompositeAdapter("CustomName")
        assert adapter.name == "CustomName"

    def test_composite_adapter_get_source_schema(self):
        """测试组合适配器获取源数据结构"""
        adapter = CompositeAdapter()
        schema = adapter.get_source_schema()
        assert isinstance(schema, dict)
        assert schema == {}

    def test_composite_adapter_add_adapter(self):
        """测试组合适配器添加子适配器"""
        composite = CompositeAdapter()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        composite.add_adapter(adapter1)
        assert len(composite.adapters) == 1
        assert "Adapter1" in composite.adapter_registry

        composite.add_adapter(adapter2)
        assert len(composite.adapters) == 2
        assert "Adapter2" in composite.adapter_registry

    def test_composite_adapter_remove_adapter(self):
        """测试组合适配器移除子适配器"""
        composite = CompositeAdapter()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        composite.add_adapter(adapter1)
        composite.add_adapter(adapter2)

        # 移除存在的适配器
        result = composite.remove_adapter("Adapter1")
        assert result is True
        assert len(composite.adapters) == 1
        assert "Adapter1" not in composite.adapter_registry

        # 移除不存在的适配器
        result = composite.remove_adapter("NonExistent")
        assert result is False
        assert len(composite.adapters) == 1

    def test_composite_adapter_get_adapter(self):
        """测试组合适配器获取子适配器"""
        composite = CompositeAdapter()
        adapter1 = MockAdapter("Adapter1")

        composite.add_adapter(adapter1)

        # 获取存在的适配器
        retrieved = composite.get_adapter("Adapter1")
        assert retrieved is adapter1

        # 获取不存在的适配器
        retrieved = composite.get_adapter("NonExistent")
        assert retrieved is None

    async def test_composite_adapter_request_with_no_adapters(self):
        """测试组合适配器无子适配器时的请求"""
        composite = CompositeAdapter()
        result = await composite.request()
        assert result == {"adapter_name": "CompositeAdapter", "results": []}

    async def test_composite_adapter_request_with_single_adapter(self):
        """测试组合适配器单个子适配器的请求"""
        composite = CompositeAdapter()
        adapter = MockAdapter("SingleAdapter")
        composite.add_adapter(adapter)

        result = await composite.request(action="get", key="test")
        assert result["adapter_name"] == "CompositeAdapter"
        assert len(result["results"]) == 1
        assert result["results"][0] == "mock_data_test"

    async def test_composite_adapter_request_with_multiple_adapters(self):
        """测试组合适配器多个子适配器的请求"""
        composite = CompositeAdapter()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")
        composite.add_adapter(adapter1)
        composite.add_adapter(adapter2)

        result = await composite.request(action="get", key="test")
        assert result["adapter_name"] == "CompositeAdapter"
        assert len(result["results"]) == 2

    async def test_composite_adapter_request_with_exception_handling(self):
        """测试组合适配器请求时的异常处理"""
        composite = CompositeAdapter()

        # 创建一个会抛出异常的适配器
        class FailingAdapter(MockAdapter):
            async def request(self, *args, **kwargs):
                raise Exception("Adapter failed")

        failing_adapter = FailingAdapter("FailingAdapter")
        normal_adapter = MockAdapter("NormalAdapter")

        composite.add_adapter(failing_adapter)
        composite.add_adapter(normal_adapter)

        result = await composite.request()
        # 应该只返回成功的结果，过滤掉异常
        assert len(result["results"]) == 1
        assert result["results"][0]["adapter"] == "NormalAdapter"

    def test_composite_adapter_get_metrics(self):
        """测试组合适配器获取指标"""
        adapter = CompositeAdapter("TestAdapter")
        metrics = adapter.get_metrics()

        assert metrics["name"] == "TestAdapter"
        assert metrics["status"] == "active"
        assert metrics["last_error"] is None
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 0


class TestAdapterRegistry:
    """适配器注册表测试"""

    def test_adapter_registry_initialization_with_factory(self):
        """测试适配器注册表带工厂初始化"""
        mock_factory = Mock()
        registry = AdapterRegistry(mock_factory)
        assert registry.factory is mock_factory
        assert registry.adapters == {}
        assert registry.groups == {}

    def test_adapter_registry_initialization_without_factory(self):
        """测试适配器注册表无工厂初始化"""
        registry = AdapterRegistry()
        assert registry.adapters == {}
        assert registry.groups == {}

    def test_adapter_registry_register_adapter(self):
        """测试适配器注册表注册适配器"""
        registry = AdapterRegistry()
        adapter = MockAdapter("TestAdapter")

        registry.register("TestAdapter", adapter)
        assert "TestAdapter" in registry.adapters
        assert registry.adapters["TestAdapter"] is adapter

    def test_adapter_registry_register_adapter_with_group(self):
        """测试适配器注册表注册适配器到组"""
        registry = AdapterRegistry()
        adapter = MockAdapter("TestAdapter")

        registry.register("TestAdapter", adapter, group="test_group")
        assert "TestAdapter" in registry.adapters
        assert "test_group" in registry.groups
        assert adapter in registry.groups["test_group"]

    def test_adapter_registry_register_multiple_adapters_same_group(self):
        """测试适配器注册表注册多个适配器到同一组"""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        registry.register("Adapter1", adapter1, group="test_group")
        registry.register("Adapter2", adapter2, group="test_group")

        assert len(registry.groups["test_group"]) == 2
        assert adapter1 in registry.groups["test_group"]
        assert adapter2 in registry.groups["test_group"]

    def test_adapter_registry_get_adapter_success(self):
        """测试适配器注册表获取适配器成功"""
        registry = AdapterRegistry()
        adapter = MockAdapter("TestAdapter")
        registry.register("TestAdapter", adapter)

        retrieved = registry.get_adapter("TestAdapter")
        assert retrieved is adapter

    def test_adapter_registry_get_adapter_not_found(self):
        """测试适配器注册表获取适配器不存在"""
        registry = AdapterRegistry()

        with pytest.raises(AdapterError, match="Adapter 'NonExistent' not found"):
            registry.get_adapter("NonExistent")

    def test_adapter_registry_get_group_exists(self):
        """测试适配器注册表获取适配器组存在"""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        registry.register("Adapter1", adapter1, group="test_group")
        registry.register("Adapter2", adapter2, group="test_group")

        group_adapters = registry.get_group("test_group")
        assert len(group_adapters) == 2
        assert adapter1 in group_adapters
        assert adapter2 in group_adapters

    def test_adapter_registry_get_group_not_exists(self):
        """测试适配器注册表获取适配器组不存在"""
        registry = AdapterRegistry()

        group_adapters = registry.get_group("non_existent_group")
        assert group_adapters == []

    def test_adapter_registry_list_adapters(self):
        """测试适配器注册表列出所有适配器"""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        registry.register("Adapter1", adapter1)
        registry.register("Adapter2", adapter2)

        adapter_names = registry.list_adapters()
        assert len(adapter_names) == 2
        assert "Adapter1" in adapter_names
        assert "Adapter2" in adapter_names

    def test_adapter_registry_list_adapters_empty(self):
        """测试适配器注册表列出空适配器列表"""
        registry = AdapterRegistry()

        adapter_names = registry.list_adapters()
        assert adapter_names == []

    def test_adapter_registry_unregister_exists(self):
        """测试适配器注册表注销存在的适配器"""
        registry = AdapterRegistry()
        adapter = MockAdapter("TestAdapter")
        registry.register("TestAdapter", adapter, group="test_group")

        registry.unregister("TestAdapter")
        assert "TestAdapter" not in registry.adapters
        assert len(registry.groups["test_group"]) == 0

    def test_adapter_registry_unregister_not_exists(self):
        """测试适配器注册表注销不存在的适配器"""
        registry = AdapterRegistry()

        # 应该不抛出异常
        registry.unregister("NonExistent")

    def test_adapter_registry_clear(self):
        """测试适配器注册表清空"""
        registry = AdapterRegistry()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")

        registry.register("Adapter1", adapter1, group="group1")
        registry.register("Adapter2", adapter2, group="group2")

        registry.clear()
        assert len(registry.adapters) == 0
        assert len(registry.groups) == 0


class TestAdapterConfig:
    """适配器配置测试"""

    def test_adapter_config_initialization_minimal(self):
        """测试适配器配置最小初始化"""
        config = AdapterConfig("TestAdapter", "test_type")

        assert config.name == "TestAdapter"
        assert config.adapter_type == "test_type"
        assert config.enabled is True
        assert config.priority == 0
        assert config.parameters == {}
        assert config.rate_limits is None
        assert config.cache_config is None
        assert config.retry_config is None

    def test_adapter_config_initialization_full(self):
        """测试适配器配置完整初始化"""
        rate_limits = {"requests_per_second": 100}
        cache_config = {"ttl": 300}
        retry_config = {"max_retries": 3}
        parameters = {"api_key": "secret"}

        config = AdapterConfig(
            name="FullAdapter",
            adapter_type="full_type",
            enabled=False,
            priority=5,
            parameters=parameters,
            rate_limits=rate_limits,
            cache_config=cache_config,
            retry_config=retry_config,
        )

        assert config.name == "FullAdapter"
        assert config.adapter_type == "full_type"
        assert config.enabled is False
        assert config.priority == 5
        assert config.parameters is parameters
        assert config.rate_limits is rate_limits
        assert config.cache_config is cache_config
        assert config.retry_config is retry_config


class TestAdapterGroupConfig:
    """适配器组配置测试"""

    def test_adapter_group_config_initialization_minimal(self):
        """测试适配器组配置最小初始化"""
        config = AdapterGroupConfig("TestGroup", ["Adapter1", "Adapter2"])

        assert config.name == "TestGroup"
        assert config.adapters == ["Adapter1", "Adapter2"]
        assert config.primary_adapter is None
        assert config.fallback_strategy == "sequential"

    def test_adapter_group_config_initialization_full(self):
        """测试适配器组配置完整初始化"""
        config = AdapterGroupConfig(
            name="FullGroup",
            adapters=["Adapter1", "Adapter2", "Adapter3"],
            primary_adapter="Adapter1",
            fallback_strategy="parallel",
        )

        assert config.name == "FullGroup"
        assert config.adapters == ["Adapter1", "Adapter2", "Adapter3"]
        assert config.primary_adapter == "Adapter1"
        assert config.fallback_strategy == "parallel"


class TestAdapterFactory:
    """适配器工厂测试"""

    def test_adapter_factory_initialization(self):
        """测试适配器工厂初始化"""
        factory = AdapterFactory()
        assert factory is not None

    def test_global_adapter_factory_exists(self):
        """测试全局适配器工厂存在"""
        from src.adapters.factory import adapter_factory

        assert adapter_factory is not None
        assert isinstance(adapter_factory, AdapterFactory)


class TestAdapterIntegration:
    """适配器集成测试"""

    async def test_adapter_registry_with_composite_adapter(self):
        """测试适配器注册表与组合适配器集成"""
        registry = AdapterRegistry()
        composite = CompositeAdapter("MainComposite")

        # 添加子适配器到组合适配器
        adapter1 = MockAdapter("SubAdapter1")
        adapter2 = MockAdapter("SubAdapter2")
        composite.add_adapter(adapter1)
        composite.add_adapter(adapter2)

        # 注册组合适配器
        registry.register("MainComposite", composite, group="main_group")

        # 验证注册
        retrieved = registry.get_adapter("MainComposite")
        assert retrieved is composite

        # 验证组
        group_adapters = registry.get_group("main_group")
        assert composite in group_adapters

        # 验证功能
        result = await composite.request(action="get", key="integration_test")
        assert result["adapter_name"] == "MainComposite"
        assert len(result["results"]) == 2

    async def test_full_adapter_workflow(self):
        """测试完整的适配器工作流程"""
        # 1. 创建数据转换器
        transformer = MockDataTransformer("IntegrationTransformer")

        # 2. 创建被适配者
        adaptee = MockAdaptee("IntegrationAdaptee")

        # 3. 创建适配器
        adapter = MockAdapter("IntegrationAdapter", adaptee)

        # 4. 创建组合适配器
        composite = CompositeAdapter("IntegrationComposite")
        composite.add_adapter(adapter)

        # 5. 创建注册表
        registry = AdapterRegistry()
        registry.register("IntegrationComposite", composite, group="integration")

        # 6. 测试完整流程
        retrieved_composite = registry.get_adapter("IntegrationComposite")
        result = await retrieved_composite.request(
            action="send", data={"test": "integration"}
        )

        assert result["adapter_name"] == "IntegrationComposite"
        assert len(result["results"]) == 1

        # 7. 测试数据转换
        transformed_data = await transformer.transform(result)
        assert "transformed_by" in transformed_data
        assert transformed_data["transformed_by"] == "IntegrationTransformer"


# 辅助函数
def create_test_adapter(name: str) -> MockAdapter:
    """创建测试适配器"""
    return MockAdapter(name)


def create_test_composite_adapter(
    name: str, adapter_count: int = 2
) -> CompositeAdapter:
    """创建测试组合适配器"""
    composite = CompositeAdapter(name)
    for i in range(adapter_count):
        adapter = create_test_adapter(f"{name}_Sub{i+1}")
        composite.add_adapter(adapter)
    return composite


def create_test_registry() -> AdapterRegistry:
    """创建测试注册表"""
    registry = AdapterRegistry()

    # 添加单个适配器
    single_adapter = create_test_adapter("SingleTestAdapter")
    registry.register("SingleTestAdapter", single_adapter, group="single")

    # 添加组合适配器
    composite_adapter = create_test_composite_adapter("CompositeTestAdapter", 3)
    registry.register("CompositeTestAdapter", composite_adapter, group="composite")

    return registry


async def assert_adapter_request_works(adapter: Adapter, *args, **kwargs):
    """断言适配器请求工作正常"""
    result = await adapter.request(*args, **kwargs)
    assert result is not None
    return result


def assert_metrics_valid(metrics: dict):
    """断言指标数据有效"""
    assert "name" in metrics
    assert "status" in metrics
    assert "total_requests" in metrics
    assert "successful_requests" in metrics
    assert "failed_requests" in metrics
    assert "success_rate" in metrics
    assert isinstance(metrics["total_requests"], int)
    assert isinstance(metrics["success_rate"], (int, float))
    assert 0 <= metrics["success_rate"] <= 1
