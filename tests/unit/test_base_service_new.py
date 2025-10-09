"""基础服务测试"""

import pytest
from unittest.mock import MagicMock, patch
from src.services.base import BaseService


class TestBaseService:
    """基础服务测试"""

    @pytest.fixture
    def base_service(self):
        """创建基础服务实例"""
        return BaseService()

    def test_service_initialization(self, base_service):
        """测试服务初始化"""
        assert base_service.name == "BaseService"
        assert base_service.logger is not None
        assert base_service._running is True

    def test_service_start_stop(self, base_service):
        """测试服务启动和停止"""
        # 测试启动服务
        result = base_service.start()
        assert result is True
        assert base_service.get_status() == "running"

        # 测试停止服务
        result = base_service.stop()
        assert result is True
        assert base_service.get_status() == "stopped"

    async def test_async_initialization(self, base_service):
        """测试异步初始化"""
        result = await base_service.initialize()
        assert result is True

    async def test_async_shutdown(self, base_service):
        """测试异步关闭"""
        await base_service.shutdown()
        assert base_service._running is False

    def test_get_status(self, base_service):
        """测试获取服务状态"""
        # 初始状态是运行中
        assert base_service.get_status() == "running"

        # 停止后状态改变
        base_service._running = False
        assert base_service.get_status() == "stopped"

    def test_service_with_custom_name(self):
        """测试自定义服务名称"""
        service = BaseService("TestService")
        assert service.name == "TestService"
        assert service.logger is not None
