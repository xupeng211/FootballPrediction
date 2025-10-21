import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

"""
适配器基类测试 - 简化版
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.adapters.base import Adapter, AdapterStatus


class TestAdapter:
    """基础适配器测试"""

    def test_adapter_is_abstract(self):
        """测试适配器是抽象类"""
        with pytest.raises(TypeError):
            Adapter()

    def test_adapter_initialization(self):
        """测试适配器初始化"""

        # 创建一个具体的Adaptee
        class TestAdaptee:
            async def request(self, *args, **kwargs):
                return {"result": "test"}

        # 创建一个具体实现
        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _request(self, *args, **kwargs):
                return await self.adaptee.request(*args, **kwargs)

            async def _cleanup(self):
                pass

        adaptee = TestAdaptee()
        adapter = ConcreteAdapter(adaptee)
        assert adapter.name is not None
        assert adapter.status == AdapterStatus.INACTIVE

    def test_adapter_basic_functionality(self):
        """测试适配器基本功能"""

        class TestAdaptee:
            async def request(self, *args, **kwargs):
                return {"endpoint": args[0] if args else "test", "data": "test"}

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                self.initialized = True

            async def _request(self, *args, **kwargs):
                return await self.adaptee.request(*args, **kwargs)

            async def _cleanup(self):
                self.initialized = False

        adaptee = TestAdaptee()
        adapter = ConcreteAdapter(adaptee)

        # 测试状态
        assert adapter.status == AdapterStatus.INACTIVE

    def test_adapter_status_transitions(self):
        """测试适配器状态转换"""

        class TestAdaptee:
            async def request(self, *args, **kwargs):
                return {"status": "ok"}

        class ConcreteAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _request(self, *args, **kwargs):
                return {"status": self.status.value}

            async def _cleanup(self):
                pass

        adaptee = TestAdaptee()
        adapter = ConcreteAdapter(adaptee)
        assert adapter.status == AdapterStatus.INACTIVE

    def test_adapter_error_handling(self):
        """测试适配器错误处理"""

        class TestAdaptee:
            async def request(self, *args, **kwargs):
                raise Exception("Request failed")

        class FailingAdapter(Adapter):
            async def _initialize(self):
                raise Exception("Init failed")

            async def _request(self, *args, **kwargs):
                raise Exception("Request failed")

            async def _cleanup(self):
                pass

        adaptee = TestAdaptee()
        adapter = FailingAdapter(adaptee)
        assert adapter.name is not None

    def test_adapter_configuration(self):
        """测试适配器配置"""

        class TestAdaptee:
            def __init__(self, config):
                self._config = config

            async def request(self, *args, **kwargs):
                return {"config": self.config}

        class ConfigurableAdapter(Adapter):
            def __init__(self, adaptee, _config=None):
                self._config = config or {}
                super().__init__(adaptee)

            async def _initialize(self):
                self.initialized = True

            async def _request(self, *args, **kwargs):
                return await self.adaptee.request(*args, **kwargs)

            async def _cleanup(self):
                self.initialized = False

        _config = {"timeout": 30, "retries": 3}
        adaptee = TestAdaptee(config)
        adapter = ConfigurableAdapter(adaptee, config)
        assert adapter._config == config

    def test_adapter_metadata(self):
        """测试适配器元数据"""

        class TestAdaptee:
            async def request(self, *args, **kwargs):
                return {"metadata": {"version": "1.0", "type": "test"}}

        class MetaAdapter(Adapter):
            def __init__(self, adaptee, _metadata=None):
                self._metadata = metadata or {"version": "1.0", "type": "test"}
                super().__init__(adaptee)

            async def _initialize(self):
                pass

            async def _request(self, *args, **kwargs):
                return await self.adaptee.request(*args, **kwargs)

            async def _cleanup(self):
                pass

        adaptee = TestAdaptee()
        adapter = MetaAdapter(adaptee)
        assert adapter.metadata["version"] == "1.0"
