"""
统一基础服务测试
Base Unified Service Tests

测试BaseService的核心功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.services.base_unified import BaseService


class TestBaseService:
    """测试基础服务"""

    def setup_method(self):
        """设置测试环境"""

        # 创建一个具体的实现类
        class TestService(BaseService):
            def __init__(self):
                super().__init__(name="test_service")

            async def _get_service_info(self):
                return {
                    "name": self.name,
                    "type": "test",
                    "initialized": self._initialized,
                    "running": self._running,
                }

        self.service = TestService()

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service.name == "test_service"
        assert self.service._initialized is False
        assert self.service._running is False
        assert self.service._created_at is not None

    @pytest.mark.asyncio
    async def test_initialize_service(self):
        """测试初始化服务"""
        result = await self.service.initialize()
        assert result is True
        assert self.service._initialized is True

    @pytest.mark.asyncio
    async def test_start_service(self):
        """测试启动服务"""
        # 先初始化
        await self.service.initialize()

        # 启动服务
        result = self.service.start()
        assert result is True
        assert self.service._running is True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        """测试停止服务"""
        # 先初始化并启动
        await self.service.initialize()
        self.service.start()

        # 停止服务
        await self.service.stop()
        assert self.service._running is False

    @pytest.mark.asyncio
    async def test_shutdown_service(self):
        """测试关闭服务"""
        # 先初始化并启动
        await self.service.initialize()
        self.service.start()

        # 关闭服务
        await self.service.shutdown()
        assert self.service._initialized is False
        assert self.service._running is False

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        """测试重复初始化"""
        await self.service.initialize()

        # 第二次初始化应该返回True
        result = await self.service.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_start_without_init(self):
        """测试未初始化时启动"""
        result = self.service.start()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_service_info(self):
        """测试获取服务信息"""
        await self.service.initialize()
        info = await self.service._get_service_info()

        assert info["name"] == "test_service"
        assert info["type"] == "test"
        assert info["initialized"] is True

    def test_get_status(self):
        """测试获取服务状态"""
        # 未初始化状态
        status = self.service.get_status()
        assert status == "uninitialized"

        # 已初始化但未运行
        self.service._initialized = True
        status = self.service.get_status()
        assert status == "stopped"

        # 运行中
        self.service._running = True
        status = self.service.get_status()
        assert status == "running"

    def test_is_healthy(self):
        """测试健康检查"""
        # 默认情况下不健康
        assert self.service.is_healthy() is False

        # 初始化并运行后健康
        self.service._initialized = True
        self.service._running = True
        assert self.service.is_healthy() is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试详细健康检查"""
        health = await self.service.health_check()

        assert "service" in health
        assert "status" in health
        assert "healthy" in health
        assert "initialized" in health
        assert "running" in health
        assert "uptime" in health
        assert "database_connected" in health

        assert health["service"] == "test_service"
        assert health["status"] == "uninitialized"
        assert health["healthy"] is False

    def test_log_operation(self):
        """测试记录操作日志"""
        with pytest.mock.patch.object(self.service.logger, "info") as mock_info:
            self.service.log_operation(operation="test_op", details={"key": "value"})
            mock_info.assert_called_once()

    def test_log_error(self):
        """测试记录错误日志"""
        with pytest.mock.patch.object(self.service.logger, "error") as mock_error:
            error = Exception("Test error")
            self.service.log_error(
                operation="test_op", error=error, details={"key": "value"}
            )
            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_session(self):
        """测试获取异步会话"""
        with pytest.mock.patch.object(
            self.service.db_manager, "get_async_session"
        ) as mock_session:
            await self.service.get_async_session()
            mock_session.assert_called_once()

    def test_get_sync_session(self):
        """测试获取同步会话"""
        with pytest.mock.patch.object(
            self.service.db_manager, "get_session"
        ) as mock_session:
            self.service.get_sync_session()
            mock_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_methods(self):
        """测试生命周期方法"""
        # 测试默认实现
        result = await self.service._on_initialize()
        assert result is True

        await self.service._on_start()
        await self.service._on_stop()
        await self.service._on_shutdown()

        # 这些方法应该不会抛出异常
        assert True
