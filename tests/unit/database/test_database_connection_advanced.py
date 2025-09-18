"""
数据库连接模块高级测试

专门针对src/database/connection.py中未覆盖的代码路径进行测试，提升覆盖率从75%到95%+
主要覆盖：异步会话管理、close方法、async_health_check等方法
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.exc import DisconnectionError, SQLAlchemyError

from src.database.connection import DatabaseConfig

# 尝试导入 DatabaseManager
try:
    from src.database.connection import DatabaseManager
except ImportError:
    # 如果导入失败，DatabaseManager 将在运行时定义
    pass


class TestDatabaseConnectionAdvanced:
    """测试数据库连接模块的高级功能"""

    def test_get_async_session_success_flow(self):
        """测试异步会话成功流程 (覆盖160-163行)"""
        from src.database.config import DatabaseConfig
        from src.database.connection import DatabaseManager

        # 创建测试配置
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        # 创建新的manager实例并初始化
        manager = DatabaseManager()
        manager.initialize(config)

        # 创建模拟异步会话
        mock_session = AsyncMock()

        with patch.object(manager, "create_async_session", return_value=mock_session):
            # 异步测试需要使用事件循环
            async def test_async():
                async with manager.get_async_session() as session:
                    assert session == mock_session
                    # 模拟一些操作，使用session避免lint错误
                    await session.execute("SELECT 1")

                # 验证commit被调用
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
                mock_session.rollback.assert_not_called()

            # 运行异步测试
            asyncio.run(test_async())

    def test_get_async_session_exception_rollback(self):
        """测试异步会话异常回滚 (覆盖164-168行)"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        mock_session = AsyncMock()
        mock_session.commit.side_effect = SQLAlchemyError("测试异常")

        with patch.object(manager, "create_async_session", return_value=mock_session):

            async def test_async():
                with pytest.raises(SQLAlchemyError):
                    async with manager.get_async_session():
                        # 会话将在这里抛出异常
                        pass

                # 验证rollback和close被调用
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
                mock_session.commit.assert_called_once()

            asyncio.run(test_async())

    def test_close_method_with_engines(self):
        """测试关闭方法 - 有引擎实例 (覆盖173-179行)"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 创建模拟引擎
        mock_sync_engine = Mock()
        mock_async_engine = AsyncMock()

        # 设置引擎
        manager._sync_engine = mock_sync_engine
        manager._async_engine = mock_async_engine

        async def test_async():
            await manager.close()

            # 验证两个引擎都被正确关闭
            mock_async_engine.dispose.assert_called_once()
            mock_sync_engine.dispose.assert_called_once()

        asyncio.run(test_async())

    def test_close_method_with_none_engines(self):
        """测试关闭方法 - 无引擎实例"""

        manager = DatabaseManager()
        # 不初始化，引擎为None

        async def test_async():
            # 不应该抛出异常
            await manager.close()
            # 没有引擎时，方法应该安全执行

        asyncio.run(test_async())

    def test_async_health_check_success(self):
        """测试异步健康检查成功 (覆盖204-209行)"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 创建模拟会话
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        # ✅ 修复：async session 的 close 方法应该是异步的
        mock_session.close = AsyncMock()

        with patch.object(manager, "create_async_session", return_value=mock_session):

            async def test_async():
                result = await manager.async_health_check()

                assert result is True
                mock_session.execute.assert_called_once()
                mock_session.close.assert_called_once()

            asyncio.run(test_async())

    def test_async_health_check_exception(self):
        """测试异步健康检查异常 (覆盖210-211行)"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 模拟create_async_session抛出异常
        with patch.object(
            manager,
            "create_async_session",
            side_effect=DisconnectionError("连接失败", None, None),
        ):

            async def test_async():
                result = await manager.async_health_check()

                assert result is False

            asyncio.run(test_async())

    def test_async_health_check_execute_exception(self):
        """测试异步健康检查执行SQL异常"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 创建模拟会话，execute时抛出异常
        mock_session = AsyncMock()
        mock_session.execute.side_effect = SQLAlchemyError("SQL执行失败")

        with patch.object(manager, "create_async_session", return_value=mock_session):

            async def test_async():
                result = await manager.async_health_check()

                assert result is False
                mock_session.execute.assert_called_once()

            asyncio.run(test_async())

    def test_close_method_dispose_exception(self):
        """测试关闭方法时dispose异常处理"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 创建模拟引擎，dispose时抛出异常
        mock_sync_engine = Mock()
        mock_async_engine = AsyncMock()
        mock_sync_engine.dispose.side_effect = Exception("同步引擎关闭失败")
        mock_async_engine.dispose.side_effect = Exception("异步引擎关闭失败")

        manager._sync_engine = mock_sync_engine
        manager._async_engine = mock_async_engine

        async def test_async():
            # 即使dispose失败，也不应该抛出异常
            await manager.close()

            # 验证两个引擎的dispose都被调用了（即使失败）
            mock_async_engine.dispose.assert_called_once()
            mock_sync_engine.dispose.assert_called_once()

        asyncio.run(test_async())

    def test_get_session_with_manual_commit_rollback(self):
        """测试手动commit和rollback的会话管理 (覆盖更多分支)"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        mock_session = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.close = Mock()

        with patch.object(manager, "create_session", return_value=mock_session):
            # 测试成功提交
            with manager.get_session() as session:
                session.execute("SELECT 1")
                # 不抛出异常

            # 验证正常流程
            mock_session.commit.assert_called()
            mock_session.close.assert_called()
            mock_session.rollback.assert_not_called()

            # 重置mock
            mock_session.reset_mock()

            # 测试异常回滚
            mock_session.execute.side_effect = SQLAlchemyError("测试异常")

            with pytest.raises(SQLAlchemyError):
                with manager.get_session() as session:
                    session.execute("SELECT 1")  # 这里会抛出异常

            # 验证异常处理流程
            mock_session.rollback.assert_called()
            mock_session.close.assert_called()

    def test_manager_properties_after_close(self):
        """测试关闭后管理器属性状态"""

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test",
            password="test",
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 确认初始化后有引擎
        assert manager._sync_engine is not None
        assert manager._async_engine is not None

        async def test_async():
            await manager.close()

            # 关闭后引擎仍然存在（只是dispose了）
            assert manager._sync_engine is not None
            assert manager._async_engine is not None

        asyncio.run(test_async())
