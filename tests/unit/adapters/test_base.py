# TODO: Consider creating a fixture for 12 repeated Mock creations

# TODO: Consider creating a fixture for 12 repeated Mock creations

from unittest.mock import AsyncMock, Mock

"""
适配器基类测试
Tests for Adapter Base Classes

测试src.adapters.base模块的功能
"""

import asyncio
from datetime import datetime

import pytest

from src.adapters.base import Adaptee, Adapter, AdapterStatus, Target


@pytest.mark.unit
class TestAdapterStatus:
    """适配器状态测试"""

    def test_status_values(self):
        """测试：状态枚举值"""
        assert AdapterStatus.ACTIVE.value == "active"
        assert AdapterStatus.INACTIVE.value == "inactive"
        assert AdapterStatus.ERROR.value == "error"
        assert AdapterStatus.MAINTENANCE.value == "maintenance"

    def test_status_comparison(self):
        """测试：状态比较"""
        assert AdapterStatus.ACTIVE == AdapterStatus.ACTIVE
        assert AdapterStatus.ACTIVE != AdapterStatus.INACTIVE

    def test_status_string_representation(self):
        """测试：状态字符串表示"""
        assert str(AdapterStatus.ACTIVE) == "AdapterStatus.ACTIVE"
        assert repr(AdapterStatus.ACTIVE) == "<AdapterStatus.ACTIVE: 'active'>"

    def test_status_iteration(self):
        """测试：状态迭代"""
        statuses = list(AdapterStatus)
        assert AdapterStatus.ACTIVE in statuses
        assert AdapterStatus.INACTIVE in statuses
        assert AdapterStatus.ERROR in statuses
        assert AdapterStatus.MAINTENANCE in statuses


class TestAdaptee:
    """被适配者测试"""

    def test_adaptee_is_abstract(self):
        """测试：被适配者是抽象类"""
        with pytest.raises(TypeError):
            Adaptee()

    def test_adaptee_methods(self):
        """测试：被适配者方法定义"""
        # 检查抽象方法
        assert Adaptee.get_data.__isabstractmethod__
        assert Adaptee.send_data.__isabstractmethod__

    def test_adaptee_implementation(self):
        """测试：被适配者实现"""

        class ConcreteAdaptee(Adaptee):
            async def get_data(self, *args, **kwargs):
                return "data"

            async def send_data(self, data):
                return f"sent: {data}"

        adaptee = ConcreteAdaptee()
        assert isinstance(adaptee, Adaptee)

        # 测试方法调用
        async def test():
            _result = await adaptee.get_data()
            assert _result == "data"

            _result = await adaptee.send_data("test")
            assert _result == "sent: test"

        asyncio.run(test())


class TestTarget:
    """目标接口测试"""

    def test_target_is_abstract(self):
        """测试：目标是抽象类"""
        with pytest.raises(TypeError):
            Target()

    def test_target_methods(self):
        """测试：目标方法定义"""
        # 检查抽象方法
        assert Target.request.__isabstractmethod__

    def test_target_implementation(self):
        """测试：目标实现"""

        class ConcreteTarget(Target):
            async def request(self, *args, **kwargs):
                return "response"

        target = ConcreteTarget()
        assert isinstance(target, Target)

        # 测试方法调用
        async def test():
            _result = await target.request()
            assert _result == "response"

        asyncio.run(test())


class TestAdapter:
    """适配器测试"""

    def test_adapter_inheritance(self):
        """测试：适配器继承"""
        # 测试适配器继承自Target
        assert issubclass(Adapter, Target)

    def test_adapter_is_abstract(self):
        """测试：适配器是抽象类"""
        with pytest.raises(TypeError):
            Adapter(Mock(spec=Adaptee))

    def test_adapter_initialization(self):
        """测试：适配器初始化"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee, name="test_adapter")

        # 检查属性
        assert adapter.adaptee is mock_adaptee
        assert adapter.name == "test_adapter"
        assert adapter.status == AdapterStatus.INACTIVE
        assert adapter.last_error is None
        assert isinstance(adapter.metrics, dict)

    def test_adapter_initialization_default_name(self):
        """测试：适配器默认名称"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        # 应该使用类名作为默认名称
        assert adapter.name == "ConcreteAdapter"

    def test_adapter_metrics_initialization(self):
        """测试：适配器指标初始化"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        # 检查初始指标
        assert adapter.metrics["total_requests"] == 0
        assert adapter.metrics["successful_requests"] == 0
        assert adapter.metrics["failed_requests"] == 0
        assert adapter.metrics["total_response_time"] == 0.0
        assert adapter.metrics["average_response_time"] == 0.0

    @pytest.mark.asyncio
    async def test_adapter_initialize_success(self):
        """测试：适配器初始化成功"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                self.initialized = True

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        await adapter.initialize()

        assert adapter.status == AdapterStatus.ACTIVE
        assert adapter.initialized is True
        assert adapter.last_error is None

    @pytest.mark.asyncio
    async def test_adapter_initialize_failure(self):
        """测试：适配器初始化失败"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                raise ValueError("Initialization failed")

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        with pytest.raises(ValueError):
            await adapter.initialize()

        assert adapter.status == AdapterStatus.ERROR
        assert adapter.last_error == "Initialization failed"

    @pytest.mark.asyncio
    async def test_adapter_cleanup_success(self):
        """测试：适配器清理成功"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                self.cleaned = True

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        await adapter.cleanup()

        assert adapter.status == AdapterStatus.INACTIVE
        assert adapter.cleaned is True

    @pytest.mark.asyncio
    async def test_adapter_cleanup_failure(self):
        """测试：适配器清理失败"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                raise RuntimeError("Cleanup failed")

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)

        with pytest.raises(RuntimeError):
            await adapter.cleanup()

        assert adapter.status == AdapterStatus.ERROR
        assert adapter.last_error == "Cleanup failed"

    @pytest.mark.asyncio
    async def test_adapter_request_active(self):
        """测试：适配器请求（活跃状态）"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def request(self, *args, **kwargs):
                return "response"

            async def _request(self, method, endpoint, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)
        adapter.status = AdapterStatus.ACTIVE

        _result = await adapter.request()
        assert _result == "response"

    @pytest.mark.asyncio
    async def test_adapter_request_inactive(self):
        """测试：适配器请求（非活跃状态）"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)
        # 适配器默认状态是 INACTIVE，不需要手动设置

        with pytest.raises(RuntimeError, match="not active"):
            await adapter.request()

    @pytest.mark.asyncio
    async def test_adapter_request_metrics_update(self):
        """测试：适配器请求指标更新"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                """实现抽象方法"""
                return {"status": "ok", "data": "response"}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)
        adapter.status = AdapterStatus.ACTIVE

        initial_requests = adapter.metrics["total_requests"]
        await adapter.request()

        # 检查指标是否更新
        assert adapter.metrics["total_requests"] == initial_requests + 1

    @pytest.mark.asyncio
    async def test_adapter_request_with_args(self):
        """测试：适配器请求带参数"""

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                """实现抽象方法"""
                return {"args": args, "kwargs": kwargs}

        mock_adaptee = Mock(spec=Adaptee)
        adapter = ConcreteAdapter(mock_adaptee)
        adapter.status = AdapterStatus.ACTIVE

        _result = await adapter.request(1, 2, param="value")
        assert _result["args"] == (1, 2)
        assert _result["kwargs"] == {"param": "value"}


class TestAdapterConcreteImplementation:
    """适配器具体实现测试"""

    @pytest.mark.asyncio
    async def test_full_adapter_lifecycle(self):
        """测试：完整适配器生命周期"""

        class TestAdaptee(Adaptee):
            def __init__(self):
                self._data = "initial"
                self.initialized = False

            async def get_data(self, *args, **kwargs):
                return self._data

            async def send_data(self, data):
                self._data = data
                return f"updated: {data}"

        class TestAdapter(Adapter):
            async def _initialize(self):
                await self.adaptee.send_data("initialized")
                self.initialized = True

            async def _cleanup(self):
                await self.adaptee.send_data("cleaned")
                self.cleaned = True

            async def _request(self, operation="get", _data=None):
                if operation == "get":
                    return await self.adaptee.get_data()
                elif operation == "set":
                    return await self.adaptee.send_data(_data)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

        # 创建适配器和被适配者
        adaptee = TestAdaptee()
        adapter = TestAdapter(adaptee, "lifecycle_test")

        # 初始化
        await adapter.initialize()
        assert adapter.status == AdapterStatus.ACTIVE
        assert adapter.initialized is True
        assert await adaptee.get_data() == "initialized"

        # 请求操作
        _result = await adapter.request("set", "new_data")
        assert _result == "updated: new_data"
        assert await adaptee.get_data() == "new_data"

        _result = await adapter.request("get")
        assert _result == "new_data"

        # 清理
        await adapter.cleanup()
        assert adapter.status == AdapterStatus.INACTIVE
        assert adapter.cleaned is True
        assert await adaptee.get_data() == "cleaned"

    @pytest.mark.asyncio
    async def test_adapter_error_handling(self):
        """测试：适配器错误处理"""

        class TestAdaptee(Adaptee):
            async def get_data(self, *args, **kwargs):
                raise ValueError("Data error")

            async def send_data(self, data):
                if _data == "error":
                    raise RuntimeError("Send error")
                return f"sent: {data}"

        class TestAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                try:
                    return await self.adaptee.get_data(*args, **kwargs)
                except ValueError as e:
                    self.last_error = str(e)
                    self.metrics["failed_requests"] += 1
                    raise

        adaptee = TestAdaptee()
        adapter = TestAdapter(adaptee)
        adapter.status = AdapterStatus.ACTIVE

        # 测试错误传播
        with pytest.raises(ValueError, match="Data error"):
            await adapter.request()

        # 检查错误状态 (父类request方法也会增加failed_requests计数)
        assert adapter.last_error == "Data error"
        assert adapter.metrics["failed_requests"] >= 1

    @pytest.mark.asyncio
    async def test_adapter_composition(self):
        """测试：适配器组合"""

        class SourceAdaptee(Adaptee):
            async def get_data(self, *args, **kwargs):
                return {"raw": "data"}

            async def send_data(self, data):
                return f"received: {data}"

        class IntermediateAdaptee(Adaptee):
            async def get_data(self, *args, **kwargs):
                return {"intermediate": "data"}

            async def send_data(self, data):
                return f"processed: {data}"

        class SourceAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                _data = await self.adaptee.get_data()
                # 转换数据
                return {"converted": True, "source": _data}

        class TargetAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                source_adapter = self.adaptee
                intermediate_data = await source_adapter.request()
                # 进一步转换
                return {"final": True, "data": intermediate_data}

        # 创建适配器链
        source = SourceAdaptee()
        source_adapter = SourceAdapter(source)

        # 这里TargetAdapter的adaptee应该是另一个Adapter
        # 这展示了适配器可以组合使用
        target_adapter = TargetAdapter(source_adapter)

        # 初始化
        await source_adapter.initialize()
        await target_adapter.initialize()

        # 请求
        _result = await target_adapter.request()
        assert _result["final"] is True
        assert _result["data"]["converted"] is True
        assert "source" in _result["data"]
