"""
数据库会话管理器测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.connection.pools.engine_manager import DatabaseEngineManager
from src.database.connection.sessions.session_manager import DatabaseSessionManager


@pytest.fixture
def mock_engine_manager():
    """创建模拟的引擎管理器"""
    manager = MagicMock(spec=DatabaseEngineManager)
    manager.is_initialized = True
    return manager


@pytest.fixture
def session_manager(mock_engine_manager):
    """创建会话管理器实例"""
    return DatabaseSessionManager(mock_engine_manager)


class TestDatabaseSessionManager:
    """测试数据库会话管理器"""

    def test_init(self, session_manager, mock_engine_manager):
        """测试初始化"""
        assert session_manager.engine_manager == mock_engine_manager

    def test_get_session_engine_not_initialized(self, mock_engine_manager):
        """测试引擎未初始化时获取会话"""
        mock_engine_manager.is_initialized = False
        session_manager = DatabaseSessionManager(mock_engine_manager)

        with pytest.raises(RuntimeError, match="数据库引擎未初始化"):
            with session_manager.get_session():
                pass

    @pytest.mark.asyncio
    async def test_get_async_session_engine_not_initialized(self, mock_engine_manager):
        """测试引擎未初始化时获取异步会话"""
        mock_engine_manager.is_initialized = False
        session_manager = DatabaseSessionManager(mock_engine_manager)

        with pytest.raises(RuntimeError, match="数据库引擎未初始化"):
            async with session_manager.get_async_session():
                pass

    def test_get_session_success(self, session_manager, mock_engine_manager):
        """测试成功获取同步会话"""
        # 设置模拟会话
        mock_session = MagicMock(spec=Session)
        mock_engine_manager.create_session.return_value = mock_session

        # 使用会话
        with session_manager.get_session() as session:
            assert session == mock_session

        # 验证调用
        mock_engine_manager.create_session.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_get_session_exception(self, session_manager, mock_engine_manager):
        """测试会话异常处理"""
        # 设置模拟会话
        mock_session = MagicMock(spec=Session)
        mock_session.commit.side_effect = Exception("Database error")
        mock_engine_manager.create_session.return_value = mock_session

        # 使用会话
        with pytest.raises(Exception, match="Database error"):
            with session_manager.get_session():
                pass

        # 验证回滚
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_session_success(
        self, session_manager, mock_engine_manager
    ):
        """测试成功获取异步会话"""
        # 设置模拟会话
        mock_session = AsyncMock(spec=AsyncSession)
        mock_engine_manager.create_async_session.return_value = mock_session

        # 使用会话
        async with session_manager.get_async_session() as session:
            assert session == mock_session

        # 验证调用
        mock_engine_manager.create_async_session.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_session_exception(
        self, session_manager, mock_engine_manager
    ):
        """测试异步会话异常处理"""
        # 设置模拟会话
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit.side_effect = Exception("Database error")
        mock_engine_manager.create_async_session.return_value = mock_session

        # 使用会话
        with pytest.raises(Exception, match="Database error"):
            async with session_manager.get_async_session():
                pass

        # 验证回滚
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_get_sync_session(self, session_manager, mock_engine_manager):
        """测试获取同步会话对象"""
        # 设置模拟会话
        mock_session = MagicMock(spec=Session)
        mock_engine_manager.create_session.return_value = mock_session

        # 获取会话
        session = session_manager.get_sync_session()

        # 验证
        assert session == mock_session
        mock_engine_manager.create_session.assert_called_once()

    def test_get_async_session_obj(self, session_manager, mock_engine_manager):
        """测试获取异步会话对象"""
        # 设置模拟会话
        mock_session = AsyncMock(spec=AsyncSession)
        mock_engine_manager.create_async_session.return_value = mock_session

        # 获取会话
        session = session_manager.get_async_session_obj()

        # 验证
        assert session == mock_session
        mock_engine_manager.create_async_session.assert_called_once()

    @patch("src.utils.retry.retry")
    def test_execute_with_retry_success(
        self, mock_retry, session_manager, mock_engine_manager
    ):
        """测试带重试机制执行操作成功"""
        # 设置模拟
        mock_session = MagicMock()
        mock_operation = MagicMock(return_value="result")
        mock_retry_decorator = MagicMock()
        mock_retry_decorator.return_value = mock_operation
        mock_retry.return_value = mock_retry_decorator

        # 执行操作
        result = session_manager.execute_with_retry(mock_session, mock_operation)

        # 验证
        assert result == "result"
        mock_operation.assert_called_once_with(mock_session)

    @patch("src.utils.retry.retry")
    def test_execute_with_retry_failure(
        self, mock_retry, session_manager, mock_engine_manager
    ):
        """测试带重试机制执行操作失败"""
        # 设置模拟
        mock_session = MagicMock()
        mock_operation = MagicMock(side_effect=Exception("Database error"))
        mock_retry_decorator = MagicMock(side_effect=Exception("Database error"))
        mock_retry.return_value = mock_retry_decorator

        # 执行操作
        with pytest.raises(Exception, match="Database error"):
            session_manager.execute_with_retry(mock_session, mock_operation)

    @pytest.mark.asyncio
    @patch("src.utils.retry.retry")
    async def test_execute_async_with_retry_success(
        self, mock_retry, session_manager, mock_engine_manager
    ):
        """测试异步带重试机制执行操作成功"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_operation = AsyncMock(return_value="result")
        mock_retry_decorator = MagicMock()
        mock_retry_decorator.return_value = mock_operation
        mock_retry.return_value = mock_retry_decorator

        # 执行操作
        result = await session_manager.execute_async_with_retry(
            mock_session, mock_operation
        )

        # 验证
        assert result == "result"
        mock_operation.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    @patch("src.utils.retry.retry")
    async def test_execute_async_with_retry_failure(
        self, mock_retry, session_manager, mock_engine_manager
    ):
        """测试异步带重试机制执行操作失败"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_operation = AsyncMock(side_effect=Exception("Database error"))
        mock_retry_decorator = MagicMock(side_effect=Exception("Database error"))
        mock_retry.return_value = mock_retry_decorator

        # 执行操作
        with pytest.raises(Exception, match="Database error"):
            await session_manager.execute_async_with_retry(mock_session, mock_operation)
