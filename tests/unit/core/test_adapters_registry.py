import sys
from pathlib import Path

# 添加项目路径
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

"""
适配器注册表测试 - 简化版
"""

import pytest

from src.adapters.base import Adapter


class MockAdapter(Adapter):
    """Mock适配器"""

    def __init__(self, adaptee=None, name=None):
        self.mock_adaptee = Mock()
        self.mock_adaptee.request = AsyncMock(return_value={"result": "mocked"})
        super().__init__(self.mock_adaptee, name)

    async def _initialize(self):
        pass

    async def _request(self, *args, **kwargs):
        return await self.adaptee.request(*args, **kwargs)

    async def _cleanup(self):
        pass


class MockAdapterRegistry:
    """Mock适配器注册表"""

    def __init__(self):
        self._adapters = {}
        self._instances = {}

    def register_adapter(self, name, adapter_class, _metadata=None):
        self._adapters[name] = {"class": adapter_class, "metadata": metadata or {}}

    def unregister_adapter(self, name):
        self._adapters.pop(name, None)
        self._instances.pop(name, None)

    def create_adapter(self, name, _config=None):
        if name not in self._adapters:
            raise ValueError(f"Unknown adapter: {name}")
        if name not in self._instances:
            self._instances[name] = MockAdapter()
        return self._instances[name]

    def list_adapters(self):
        return list(self._adapters.keys())

    def get_adapter_info(self, name):
        if name in self._adapters:
            return self._adapters[name]["metadata"]
        return None


@pytest.mark.unit
class TestAdapterRegistry:
    """适配器注册表测试"""

    def test_registry_initialization(self):
        """测试注册表初始化"""
        registry = MockAdapterRegistry()
        assert len(registry._adapters) == 0
        assert len(registry._instances) == 0

    def test_register_adapter(self):
        """测试注册适配器"""
        registry = MockAdapterRegistry()
        registry.register_adapter("test", MockAdapter, {"version": "1.0"})

        assert "test" in registry._adapters
        assert registry._adapters["test"]["metadata"]["version"] == "1.0"

    def test_unregister_adapter(self):
        """测试注销适配器"""
        registry = MockAdapterRegistry()
        registry.register_adapter("test", MockAdapter)
        registry.unregister_adapter("test")

        assert "test" not in registry._adapters

    def test_create_adapter(self):
        """测试创建适配器"""
        registry = MockAdapterRegistry()
        registry.register_adapter("test", MockAdapter)

        adapter = registry.create_adapter("test")
        assert isinstance(adapter, MockAdapter)

    def test_create_unregistered_adapter(self):
        """测试创建未注册的适配器"""
        registry = MockAdapterRegistry()

        with pytest.raises(ValueError, match="Unknown adapter"):
            registry.create_adapter("nonexistent")

    def test_list_adapters(self):
        """测试列出适配器"""
        registry = MockAdapterRegistry()
        registry.register_adapter("test1", MockAdapter)
        registry.register_adapter("test2", MockAdapter)

        adapters = registry.list_adapters()
        assert len(adapters) == 2
        assert "test1" in adapters
        assert "test2" in adapters

    def test_get_adapter_info(self):
        """测试获取适配器信息"""
        registry = MockAdapterRegistry()
        _metadata = {"version": "1.0", "author": "test"}
        registry.register_adapter("test", MockAdapter, metadata)

        info = registry.get_adapter_info("test")
        assert info["version"] == "1.0"
        assert info["author"] == "test"
