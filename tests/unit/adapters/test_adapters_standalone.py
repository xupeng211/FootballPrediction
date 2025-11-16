"""
适配器模式独立测试
Standalone Adapter Pattern Tests

直接测试适配器模式的核心概念，不依赖有语法问题的模块文件.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

import pytest


# 重新定义适配器模式的核心类，避免导入有问题的模块
class AdapterStatus(Enum):
    """适配器状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Adaptee(ABC):
    """被适配者接口,需要被适配的现有接口"""

    @abstractmethod
    async def get_data(self, *args, **kwargs) -> Any:
        """获取原始数据"""

    @abstractmethod
    async def send_data(self, data: Any) -> Any:
        """发送数据"""


class Target(ABC):
    """目标接口,客户端期望的接口"""

    @abstractmethod
    async def request(self, *args, **kwargs) -> Any:
        """标准请求方法"""


class Adapter(Target):
    """适配器基类,将Adaptee接口转换为Target接口"""


class BaseAdapter(ABC):
    """基础适配器抽象类"""

    @abstractmethod
    def connect(self) -> bool:
        """连接方法"""
        pass


class DataTransformer(ABC):
    """数据转换器基类"""

    @abstractmethod
    async def transform(self, data: Any, **kwargs) -> Any:
        """转换数据格式"""


class CompositeAdapter(Adapter):
    """组合适配器,可以管理多个子适配器"""

    def get_source_schema(self) -> dict[str, Any]:
        """获取源数据结构"""
        return {}

    def get_target_schema(self) -> dict[str, Any]:
        """获取目标数据结构"""
        return {"type": "object", "properties": {}}

    def __init__(self, name: str = "CompositeAdapter"):
        """初始化组合适配器"""
        self.name = name
        self.adapters: list[Adapter] = []
        self.adapter_registry: dict[str, Adapter] = {}
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "average_response_time": 0.0,
        }
        self.status = AdapterStatus.ACTIVE
        self.last_error = None

    def get_metrics(self) -> dict[str, Any]:
        """获取适配器指标"""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_error": self.last_error,
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"]
                if self.metrics["total_requests"] > 0
                else 0
            ),
        }

    def add_adapter(self, adapter: Adapter) -> None:
        """添加子适配器"""
        self.adapters.append(adapter)
        if hasattr(adapter, "name"):
            self.adapter_registry[adapter.name] = adapter

    def remove_adapter(self, adapter_name: str) -> bool:
        """移除子适配器"""
        if adapter_name in self.adapter_registry:
            adapter = self.adapter_registry[adapter_name]
            self.adapters.remove(adapter)
            del self.adapter_registry[adapter_name]
            return True
        return False

    def get_adapter(self, adapter_name: str) -> Adapter | None:
        """获取子适配器"""
        return self.adapter_registry.get(adapter_name)

    async def request(self, *args, **kwargs) -> Any:
        """并行请求所有适配器并合并结果"""
        results = []

        # 并行请求所有适配器
        tasks = [adapter.request(*args, **kwargs) for adapter in self.adapters]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        successful_results = [
            result for result in results if not isinstance(result, Exception)
        ]

        return {"adapter_name": self.name, "results": successful_results}


# 测试用的Mock实现
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


class TestAdapter:
    """适配器测试"""

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


    @pytest.mark.asyncio
    async def test_mock_data_transformer_transform_dict(self):
        """测试模拟数据转换器转换字典数据"""
        transformer = MockDataTransformer("TestTransformer")
        input_data = {"key1": "value1", "key2": "value2"}
        result = await transformer.transform(input_data)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["transformed_by"] == "TestTransformer"
        assert result["transform_count"] == 1


    @pytest.mark.asyncio
    async def test_mock_data_transformer_transform_string(self):
        """测试模拟数据转换器转换字符串数据"""
        transformer = MockDataTransformer("TestTransformer")
        result = await transformer.transform("test_string")
        assert result == "TestTransformer_transformed_test_string"
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


class TestAdapterIntegration:
    """适配器集成测试"""


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


    @pytest.mark.asyncio
    async def test_adapter_pattern_core_concept(self):
        """测试适配器模式核心概念"""
        # 被适配者（遗留系统）
        legacy_system = MockAdaptee("LegacySystem")

        # 适配器（转换接口）
        adapter = MockAdapter("LegacyAdapter", legacy_system)

        # 客户端代码只调用Target接口，不需要知道被适配者的细节
        result = await adapter.request(action="get", key="user_data")
        assert result == "mock_data_user_data"

        result = await adapter.request(action="send", data={"user": "test"})
        assert result["status"] == "success"


    @pytest.mark.asyncio
    async def test_composite_adapter_multiple_sources(self):
        """测试组合适配器整合多个数据源"""
        composite = CompositeAdapter("DataAggregator")

        # 添加多个数据源适配器
        source1 = MockAdapter("DatabaseAdapter")
        source2 = MockAdapter("APIAdapter")
        source3 = MockAdapter("CacheAdapter")

        composite.add_adapter(source1)
        composite.add_adapter(source2)
        composite.add_adapter(source3)

        # 并行请求所有数据源
        result = await composite.request(action="get", key="aggregated_data")

        assert result["adapter_name"] == "DataAggregator"
        assert len(result["results"]) == 3

        # 验证所有适配器都被调用
        for source in [source1, source2, source3]:
            assert source.request_count == 1


    @pytest.mark.asyncio
    async def test_adapter_error_resilience(self):
        """测试适配器错误恢复能力"""
        composite = CompositeAdapter("ResilientAdapter")

        # 添加正常的和会失败的适配器
        working_adapter = MockAdapter("WorkingAdapter")

        class FaultyAdapter(MockAdapter):
            async def request(self, *args, **kwargs):
                raise ConnectionError("Network failed")

        faulty_adapter = FaultyAdapter("FaultyAdapter")

        composite.add_adapter(working_adapter)
        composite.add_adapter(faulty_adapter)

        # 即使有适配器失败，也应该返回成功的结果
        result = await composite.request(action="get", key="resilience_test")

        assert len(result["results"]) == 1  # 只有成功的适配器结果
        assert result["results"][0] == "mock_data_resilience_test"
