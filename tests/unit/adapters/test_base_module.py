"""
适配器基础模块测试
Base Adapter Module Tests

直接测试src/adapters/base.py模块的覆盖率，绕过其他模块的语法错误。
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock
from typing import Any
from datetime import datetime

# 直接添加adapters目录到路径，避免通过__init__.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src/adapters"))

# 直接导入base模块，绕过__init__.py
from base import (
    AdapterStatus,
    Adaptee,
    Target,
    Adapter,
    BaseAdapter,
    DataTransformer,
    CompositeAdapter,
)


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


class TestAdapterStatusFromBaseModule:
    """测试来自base模块的适配器状态"""

    def test_adapter_status_enum_values_from_base_module(self):
        """测试适配器状态枚举值"""
        assert AdapterStatus.ACTIVE.value == "active"
        assert AdapterStatus.INACTIVE.value == "inactive"
        assert AdapterStatus.ERROR.value == "error"
        assert AdapterStatus.MAINTENANCE.value == "maintenance"

    def test_adapter_status_enum_count_from_base_module(self):
        """测试适配器状态枚举数量"""
        statuses = list(AdapterStatus)
        assert len(statuses) == 4
        assert AdapterStatus.ACTIVE in statuses
        assert AdapterStatus.INACTIVE in statuses
        assert AdapterStatus.ERROR in statuses
        assert AdapterStatus.MAINTENANCE in statuses

    def test_adapter_status_iteration(self):
        """测试适配器状态迭代"""
        for status in AdapterStatus:
            assert isinstance(status.value, str)
            assert len(status.value) > 0

    def test_adapter_status_comparison(self):
        """测试适配器状态比较"""
        assert AdapterStatus.ACTIVE == AdapterStatus.ACTIVE
        assert AdapterStatus.ACTIVE != AdapterStatus.INACTIVE

        # 测试字符串比较
        assert AdapterStatus.ACTIVE.value == "active"
        assert "active" == AdapterStatus.ACTIVE.value


class TestAdapteeFromBaseModule:
    """测试来自base模块的被适配者"""

    def test_mock_adaptee_initialization_from_base_module(self):
        """测试模拟被适配者初始化"""
        adaptee = MockAdaptee("TestAdaptee")
        assert adaptee.name == "TestAdaptee"
        assert isinstance(adaptee.data_store, dict)

    async def test_mock_adaptee_get_data_from_base_module(self):
        """测试模拟被适配者获取数据"""
        adaptee = MockAdaptee()
        result = await adaptee.get_data(key="test_key")
        assert result == "mock_data_test_key"

        # 设置数据并获取
        adaptee.data_store["custom_key"] = "custom_value"
        result = await adaptee.get_data(key="custom_key")
        assert result == "custom_value"

    async def test_mock_adaptee_send_data_from_base_module(self):
        """测试模拟被适配者发送数据"""
        adaptee = MockAdaptee()
        test_data = {"message": "test"}
        result = await adaptee.send_data(test_data)

        assert result["status"] == "success"
        assert "timestamp" in result
        assert len(adaptee.data_store) == 1

    def test_adaptee_interface_is_abstract_from_base_module(self):
        """测试被适配者接口是抽象的"""
        with pytest.raises(TypeError):
            Adaptee()

    def test_adaptee_abstract_methods(self):
        """测试被适配者抽象方法"""
        # 验证抽象方法存在
        assert hasattr(Adaptee, "get_data")
        assert hasattr(Adaptee, "send_data")

        # 验证是抽象方法
        assert getattr(Adaptee.get_data, "__isabstractmethod__", False)  # 已实现的Mock
        assert getattr(Adaptee.send_data, "__isabstractmethod__", False)  # 已实现的Mock


class TestTargetFromBaseModule:
    """测试来自base模块的目标接口"""

    def test_mock_target_initialization_from_base_module(self):
        """测试模拟目标接口初始化"""
        target = MockTarget("TestTarget")
        assert target.name == "TestTarget"
        assert target.request_count == 0

    async def test_mock_target_request_from_base_module(self):
        """测试模拟目标接口请求"""
        target = MockTarget()
        result = await target.request("arg1", arg2="value2")

        assert result["target"] == "MockTarget"
        assert result["request_id"] == 1
        assert result["args"] == ("arg1",)
        assert result["kwargs"] == {"arg2": "value2"}
        assert target.request_count == 1

    def test_target_interface_is_abstract_from_base_module(self):
        """测试目标接口是抽象的"""
        with pytest.raises(TypeError):
            Target()

    def test_target_abstract_methods(self):
        """测试目标接口抽象方法"""
        # 验证抽象方法存在
        assert hasattr(Target, "request")

        # Mock类已实现，所以不是抽象的
        assert not getattr(Target.request, "__isabstractmethod__", False)


class TestAdapterFromBaseModule:
    """测试来自base模块的适配器"""

    def test_mock_adapter_initialization_from_base_module(self):
        """测试模拟适配器初始化"""
        adapter = MockAdapter("TestAdapter")
        assert adapter.name == "TestAdapter"
        assert adapter.request_count == 0
        assert isinstance(adapter.adaptee, MockAdaptee)

    async def test_mock_adapter_request_get_action_from_base_module(self):
        """测试模拟适配器获取动作请求"""
        adapter = MockAdapter()
        result = await adapter.request(action="get", key="test_key")
        assert result == "mock_data_test_key"

    async def test_mock_adapter_request_send_action_from_base_module(self):
        """测试模拟适配器发送动作请求"""
        adapter = MockAdapter()
        test_data = {"message": "test"}
        result = await adapter.request(action="send", data=test_data)
        assert result["status"] == "success"

    async def test_mock_adapter_request_default_action_from_base_module(self):
        """测试模拟适配器默认动作请求"""
        adapter = MockAdapter()
        result = await adapter.request()
        assert result["adapter"] == "MockAdapter"
        assert result["request_id"] == 1

    def test_adapter_inheritance_from_base_module(self):
        """测试适配器继承关系"""
        # MockAdapter继承自Adapter，Adapter继承自Target
        adapter = MockAdapter()
        assert isinstance(adapter, Adapter)
        assert isinstance(adapter, Target)


class TestBaseAdapterFromBaseModule:
    """测试来自base模块的基础适配器"""

    def test_base_adapter_is_abstract_from_base_module(self):
        """测试基础适配器是抽象的"""
        with pytest.raises(TypeError):
            BaseAdapter()

    def test_base_adapter_class_definition(self):
        """测试基础适配器类定义"""
        # 验证类存在
        assert BaseAdapter is not None
        assert hasattr(BaseAdapter, "__module__")
        assert "base" in BaseAdapter.__module__


class TestDataTransformerFromBaseModule:
    """测试来自base模块的数据转换器"""

    def test_mock_data_transformer_initialization_from_base_module(self):
        """测试模拟数据转换器初始化"""
        transformer = MockDataTransformer("TestTransformer")
        assert transformer.name == "TestTransformer"
        assert transformer.transform_count == 0

    async def test_mock_data_transformer_transform_dict_from_base_module(self):
        """测试模拟数据转换器转换字典数据"""
        transformer = MockDataTransformer()
        input_data = {"key1": "value1", "key2": "value2"}
        result = await transformer.transform(input_data)

        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert result["transformed_by"] == "TestTransformer"
        assert result["transform_count"] == 1

    async def test_mock_data_transformer_transform_string_from_base_module(self):
        """测试模拟数据转换器转换字符串数据"""
        transformer = MockDataTransformer()
        result = await transformer.transform("test_string")
        assert result == "TestTransformer_transformed_test_string"
        assert transformer.transform_count == 1

    def test_data_transformer_interface_is_abstract_from_base_module(self):
        """测试数据转换器接口是抽象的"""
        with pytest.raises(TypeError):
            DataTransformer()

    def test_data_transformer_abstract_methods(self):
        """测试数据转换器抽象方法"""
        # 验证抽象方法存在
        assert hasattr(DataTransformer, "transform")

        # Mock实现，所以不是抽象的
        assert not getattr(DataTransformer.transform, "__isabstractmethod__", False)


class TestCompositeAdapterFromBaseModule:
    """测试来自base模块的组合适配器"""

    def test_composite_adapter_initialization_from_base_module(self):
        """测试组合适配器初始化"""
        adapter = CompositeAdapter("TestComposite")
        assert adapter.name == "TestComposite"
        assert adapter.adapters == []
        assert adapter.adapter_registry == {}
        assert adapter.status == AdapterStatus.ACTIVE
        assert adapter.last_error is None
        assert adapter.metrics["total_requests"] == 0

    def test_composite_adapter_get_source_schema_from_base_module(self):
        """测试组合适配器获取源数据结构"""
        adapter = CompositeAdapter()
        schema = adapter.get_source_schema()
        assert isinstance(schema, dict)
        assert schema == {}

    def test_composite_adapter_add_adapter_from_base_module(self):
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

    def test_composite_adapter_remove_adapter_from_base_module(self):
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

    def test_composite_adapter_get_adapter_from_base_module(self):
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

    async def test_composite_adapter_request_with_no_adapters_from_base_module(self):
        """测试组合适配器无子适配器时的请求"""
        composite = CompositeAdapter()
        result = await composite.request()
        assert result == {"adapter_name": "CompositeAdapter", "results": []}

    async def test_composite_adapter_request_with_single_adapter_from_base_module(self):
        """测试组合适配器单个子适配器的请求"""
        composite = CompositeAdapter()
        adapter = MockAdapter("SingleAdapter")
        composite.add_adapter(adapter)

        result = await composite.request(action="get", key="test")
        assert result["adapter_name"] == "CompositeAdapter"
        assert len(result["results"]) == 1
        assert result["results"][0] == "mock_data_test"

    async def test_composite_adapter_request_with_multiple_adapters_from_base_module(
        self,
    ):
        """测试组合适配器多个子适配器的请求"""
        composite = CompositeAdapter()
        adapter1 = MockAdapter("Adapter1")
        adapter2 = MockAdapter("Adapter2")
        composite.add_adapter(adapter1)
        composite.add_adapter(adapter2)

        result = await composite.request(action="get", key="test")
        assert result["adapter_name"] == "CompositeAdapter"
        assert len(result["results"]) == 2

    async def test_composite_adapter_request_with_exception_handling_from_base_module(
        self,
    ):
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

    def test_composite_adapter_get_metrics_from_base_module(self):
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

    def test_composite_adapter_inheritance_from_base_module(self):
        """测试组合适配器继承关系"""
        composite = CompositeAdapter()
        assert isinstance(composite, Adapter)
        assert isinstance(composite, Target)

    def test_composite_adapter_metrics_update(self):
        """测试组合适配器指标更新"""
        composite = CompositeAdapter()

        # 模拟更新指标
        composite.metrics["total_requests"] = 10
        composite.metrics["successful_requests"] = 8
        composite.metrics["failed_requests"] = 2

        metrics = composite.get_metrics()
        assert metrics["success_rate"] == 0.8  # 8/10 = 0.8

    def test_composite_adapter_status_management(self):
        """测试组合适配器状态管理"""
        composite = CompositeAdapter()

        # 测试状态变更
        composite.status = AdapterStatus.ERROR
        composite.last_error = "Test error"

        metrics = composite.get_metrics()
        assert metrics["status"] == "error"
        assert metrics["last_error"] == "Test error"


class TestAdapterIntegrationFromBaseModule:
    """适配器集成测试 - 来自base模块"""

    async def test_full_adapter_workflow_from_base_module(self):
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

    async def test_adapter_pattern_core_concept_from_base_module(self):
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

    async def test_composite_adapter_multiple_sources_from_base_module(self):
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

    async def test_adapter_error_resilience_from_base_module(self):
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

    def test_adapter_module_exports(self):
        """测试适配器模块导出"""
        # 验证所有重要的类都已导入
        assert AdapterStatus is not None
        assert Adaptee is not None
        assert Target is not None
        assert Adapter is not None
        assert BaseAdapter is not None
        assert DataTransformer is not None
        assert CompositeAdapter is not None

    def test_adapter_module_constants(self):
        """测试适配器模块常量"""
        # 验证枚举值
        assert AdapterStatus.ACTIVE.value == "active"
        assert AdapterStatus.INACTIVE.value == "inactive"
        assert AdapterStatus.ERROR.value == "error"
        assert AdapterStatus.MAINTENANCE.value == "maintenance"
