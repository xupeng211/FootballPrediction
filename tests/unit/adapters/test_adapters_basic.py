"""
适配器基础测试
Basic Adapter Tests

测试适配器模式的基础功能，避免有语法错误的模块.
"""

import os
import sys
from datetime import datetime
from typing import Any, Optional

import pytest

# 添加adapters路径并直接导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/adapters"))

# 只导入没有语法错误的模块
try:
    from base import (
        Adaptee,
        Adapter,
        AdapterStatus,
        BaseAdapter,
        CompositeAdapter,
        DataTransformer,
        Target,
    )

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

    # 如果导入失败，创建Mock类避免NameError
    Adaptee = object
    Adapter = object
    AdapterStatus = object
    BaseAdapter = object
    CompositeAdapter = object
    DataTransformer = object
    Target = object

try:
    from registry import AdapterError, AdapterRegistry

    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

try:
    from factory import AdapterConfig, AdapterFactory, AdapterGroupConfig

    FACTORY_AVAILABLE = True
except ImportError:
    FACTORY_AVAILABLE = False


# 移除skip条件，允许测试运行


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

    def test_mock_adaptee_initialization(self):
        """测试模拟被适配者初始化"""
        adaptee = MockAdaptee("TestAdaptee")
        assert adaptee.name == "TestAdaptee"
        assert isinstance(adaptee.data_store, dict)

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_mock_adaptee_get_data(self):
        """测试模拟被适配者获取数据"""
        adaptee = MockAdaptee()
        result = await adaptee.get_data(key="test_key")
        assert result == "mock_data_test_key"

        # 设置数据并获取
        adaptee.data_store["custom_key"] = "custom_value"
        result = await adaptee.get_data(key="custom_key")
        assert result == "custom_value"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
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

    def test_mock_target_initialization(self):
        """测试模拟目标接口初始化"""
        target = MockTarget("TestTarget")
        assert target.name == "TestTarget"
        assert target.request_count == 0

    @pytest.mark.asyncio
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

    def test_mock_adapter_initialization(self):
        """测试模拟适配器初始化"""
        adapter = MockAdapter("TestAdapter")
        assert adapter.name == "TestAdapter"
        assert adapter.request_count == 0
        assert isinstance(adapter.adaptee, MockAdaptee)

    @pytest.mark.asyncio
    async def test_mock_adapter_request_get_action(self):
        """测试模拟适配器获取动作请求"""
        adapter = MockAdapter()
        result = await adapter.request(action="get", key="test_key")
        assert result == "mock_data_test_key"

    @pytest.mark.asyncio
    async def test_mock_adapter_request_send_action(self):
        """测试模拟适配器发送动作请求"""
        adapter = MockAdapter()
        test_data = {"message": "test"}
        result = await adapter.request(action="send", data=test_data)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_mock_adapter_request_default_action(self):
        """测试模拟适配器默认动作请求"""
        adapter = MockAdapter()
        result = await adapter.request()
        assert result["adapter"] == "TestAdapter"
        assert result["request_id"] == 1

    def test_base_adapter_is_abstract(self):
        """测试基础适配器是抽象的"""
        with pytest.raises(TypeError):
            BaseAdapter()

    def test_mock_data_transformer_initialization(self):
        """测试模拟数据转换器初始化"""
        transformer = MockDataTransformer("TestTransformer")
        assert transformer.name == "TestTransformer"
        assert transformer.transform_count == 0

    @pytest.mark.asyncio
    async def test_mock_data_transformer_transform_dict(self):
        """测试模拟数据转换器转换字典数据"""
        transformer = MockDataTransformer()
        input_data = {"key1": "value1", "key2": "value2"}
        result = await transformer.transform(input_data)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["transformed_by"] == "TestTransformer"
        assert result["transform_count"] == 1

    @pytest.mark.asyncio
    async def test_mock_data_transformer_transform_string(self):
        """测试模拟数据转换器转换字符串数据"""
        transformer = MockDataTransformer()
        result = await transformer.transform("test_string")
        assert result == "TestTransformer_transformed_test_string"
        assert transformer.transform_count == 1

    def test_data_transformer_interface_is_abstract(self):
        """测试数据转换器接口是抽象的"""
        with pytest.raises(TypeError):
            DataTransformer()

    def test_composite_adapter_initialization(self):
        """测试组合适配器初始化"""
        adapter = CompositeAdapter("TestComposite")
        assert adapter.name == "TestComposite"
        assert adapter.adapters == []
        assert adapter.adapter_registry == {}
        assert adapter.status == AdapterStatus.ACTIVE
        assert adapter.last_error is None
        assert adapter.metrics["total_requests"] == 0

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

    @pytest.mark.asyncio
    async def test_composite_adapter_request_with_no_adapters(self):
        """测试组合适配器无子适配器时的请求"""
        composite = CompositeAdapter()
        result = await composite.request()
        assert result == {"adapter_name": "CompositeAdapter", "results": []}

    @pytest.mark.asyncio
    async def test_composite_adapter_request_with_single_adapter(self):
        """测试组合适配器单个子适配器的请求"""
        composite = CompositeAdapter()
        adapter = MockAdapter("SingleAdapter")
        composite.add_adapter(adapter)

        result = await composite.request(action="get", key="test")
        assert result["adapter_name"] == "CompositeAdapter"
        assert len(result["results"]) == 1
        assert result["results"][0] == "mock_data_test"

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    def test_adapter_registry_initialization(self):
        """测试适配器注册表初始化"""
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

    def test_adapter_factory_initialization(self):
        """测试适配器工厂初始化"""
        factory = AdapterFactory()
        assert factory is not None

    @pytest.mark.asyncio
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

        # 5. 测试完整流程
        result = await composite.request(action="send", data={"test": "integration"})

        assert result["adapter_name"] == "IntegrationComposite"
        assert len(result["results"]) == 1

        # 6. 测试数据转换
        transformed_data = await transformer.transform(result)
        assert "transformed_by" in transformed_data
        assert transformed_data["transformed_by"] == "IntegrationTransformer"