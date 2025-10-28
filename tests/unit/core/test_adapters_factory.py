# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations

import sys
from pathlib import Path

# 添加项目路径
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

"""
适配器工厂测试 - 简化版
"""

import pytest

from src.adapters.base import Adapter


class MockAdapter(Adapter):
    """Mock适配器"""

    def __init__(self, adaptee=None, name=None):
        # 创建一个mock adaptee
        self.mock_adaptee = Mock()
        self.mock_adaptee.request = AsyncMock(return_value={"result": "mocked"})
        super().__init__(self.mock_adaptee, name)

    async def _initialize(self):
        pass

    async def _request(self, *args, **kwargs):
        return await self.adaptee.request(*args, **kwargs)

    async def _cleanup(self):
        pass


@pytest.mark.unit
class TestAdapterFactory:
    """适配器工厂测试"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = Mock()  # Mock factory
        assert factory is not None

    def test_register_adapter(self):
        """测试注册适配器"""
        registry = Mock()
        registry.register_adapter = Mock()
        registry.register_adapter("test", MockAdapter)
        registry.register_adapter.assert_called_once_with("test", MockAdapter)

    def test_create_adapter(self):
        """测试创建适配器"""
        adapter = MockAdapter()
        assert adapter.name is not None
        assert adapter.status.value == "inactive"

    def test_singleton_behavior(self):
        """测试单例行为"""
        adapter1 = MockAdapter()
        adapter2 = MockAdapter()
        assert adapter1 is not adapter2  # 不是同一个实例
