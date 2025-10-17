"""
基础服务测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.base_unified import BaseService


class TestBaseService:
    """测试基础服务类"""

    def test_service_initialization(self):
        """测试服务初始化"""
        # 测试抽象类不能直接实例化
        with pytest.raises(TypeError):
            BaseService()

    def test_concrete_service(self):
        """测试具体服务实现"""
        class ConcreteService(BaseService):
            def __init__(self):
                super().__init__()
                self.name = "test_service"

        service = ConcreteService()
        assert service.name == "test_service"
        assert hasattr(service, 'logger')
        assert hasattr(service, 'metrics')

    @pytest.mark.asyncio
    async def test_async_methods(self):
        """测试异步方法"""
        class AsyncService(BaseService):
            async def test_method(self):
                return "result"

        service = AsyncService()
        result = await service.test_method()
        assert result == "result"
