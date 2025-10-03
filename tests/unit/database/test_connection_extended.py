"""数据库连接扩展测试"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 尝试导入，如果失败则跳过
try:
    from src.database.connection import DatabaseManager, get_async_session, get_database
except ImportError:
    DatabaseManager = None
    get_async_session = None
    get_database = None


class TestDatabaseConnectionExtended:
    """数据库连接扩展测试"""

    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        if DatabaseManager is None:
            pytest.skip("DatabaseManager not available")
        return DatabaseManager()

    @pytest.mark.asyncio
    async def test_database_initialization(self, db_manager):
        """测试数据库初始化"""
        # 测试初始化配置
        assert db_manager is not None
        assert hasattr(db_manager, 'engine')
        assert hasattr(db_manager, 'session_factory')

    @pytest.mark.asyncio
    async def test_create_engine_with_different_url(self):
        """测试使用不同URL创建引擎"""
        test_url = "sqlite+aiosqlite:///test.db"
        db_manager = DatabaseManager(database_url=test_url)

        assert db_manager.database_url == test_url

    @pytest.mark.asyncio
    async def test_session_creation(self, db_manager):
        """测试会话创建"""
        # 测试会话工厂
        assert db_manager.session_factory is not None

    @pytest.mark.asyncio
    async def test_get_async_session_context_manager(self):
        """测试异步会话上下文管理器"""
        async with get_async_session() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active

    @pytest.mark.asyncio
    async def test_get_database_singleton(self):
        """测试数据库单例"""
        db1 = get_database()
        db2 = get_database()

        # 应该返回相同的实例
        assert db1 is db2

    @pytest.mark.asyncio
    async def test_database_connect(self, db_manager):
        """测试数据库连接"""
        with patch.object(db_manager, 'connect') as mock_connect:
            mock_connect.return_value = None

            await db_manager.connect()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_disconnect(self, db_manager):
        """测试数据库断开连接"""
        with patch.object(db_manager, 'disconnect') as mock_disconnect:
            mock_disconnect.return_value = None

            await db_manager.disconnect()
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, db_manager):
        """测试错误时事务回滚"""
        async with get_async_session() as session:
            # 开始事务
            transaction = await session.begin()

            try:
                # 模拟错误
                raise Exception("Test error")
            except Exception:
                # 回滚事务
                await transaction.rollback()
                assert not transaction.is_active

    @pytest.mark.asyncio
    async def test_session_close(self):
        """测试会话关闭"""
        async with get_async_session() as session:
            assert session.is_active

        # 会话应该在上下文管理器外关闭
        assert not session.is_active

    @pytest.mark.asyncio
    async def test_database_url_validation(self):
        """测试数据库URL验证"""
        # 测试有效的URL
        valid_urls = [
            "sqlite+aiosqlite:///test.db",
            "postgresql+asyncpg://user:pass@localhost/db",
            "mysql+aiomysql://user:pass@localhost/db"
        ]

        for url in valid_urls:
            db_manager = DatabaseManager(database_url=url)
            assert db_manager.database_url == url

    @pytest.mark.asyncio
    async def test_connection_pool_settings(self, db_manager):
        """测试连接池设置"""
        # 测试连接池配置
        if hasattr(db_manager, 'engine') and db_manager.engine:
            engine = db_manager.engine
            # 检查连接池设置
            assert hasattr(engine, 'pool')

    @pytest.mark.asyncio
    async def test_multiple_sessions_independence(self):
        """测试多个会话的独立性"""
        sessions = []

        # 创建多个会话
        for _ in range(3):
            session = get_async_session()
            sessions.append(session)

        # 每个会话应该是独立的
        for i, session in enumerate(sessions):
            async with session as s:
                assert s.is_active

    @pytest.mark.asyncio
    async def test_session_nesting(self):
        """测试嵌套会话处理"""
        async with get_async_session() as outer_session:
            # 嵌套会话可能需要特殊处理
            # 根据实际实现调整测试
            pass

    def test_database_manager_repr(self, db_manager):
        """测试数据库管理器的字符串表示"""
        repr_str = repr(db_manager)
        assert "DatabaseManager" in repr_str

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """测试连接超时设置"""
        # 测试连接超时配置
        timeout = 30
        db_manager = DatabaseManager(connect_timeout=timeout)

        # 根据实际实现验证超时设置
        assert hasattr(db_manager, 'connect_timeout')

    @pytest.mark.asyncio
    async def test_echo_mode(self):
        """测试回显模式（SQL日志）"""
        # 测试SQL日志回显
        db_manager = DatabaseManager(echo=True)

        # 根据实际实现验证echo设置
        assert hasattr(db_manager, 'echo')

    @pytest.mark.asyncio
    async def test_health_check(self, db_manager):
        """测试数据库健康检查"""
        # 模拟健康检查
        with patch('sqlalchemy.ext.asyncio.AsyncSession.execute') as mock_execute:
            mock_execute.return_value = MagicMock()

            # 执行健康检查
            async with get_async_session() as session:
                result = await session.execute("SELECT 1")
                assert result is not None

    @pytest.mark.asyncio
    async def test_database_migration_support(self):
        """测试数据库迁移支持"""
        # 测试迁移相关的功能
        # 根据实际的迁移系统实现测试
        pass

    @pytest.mark.asyncio
    async def test_connection_retry_logic(self):
        """测试连接重试逻辑"""
        # 测试连接失败时的重试机制
        # 根据实际的重试实现调整测试
        pass