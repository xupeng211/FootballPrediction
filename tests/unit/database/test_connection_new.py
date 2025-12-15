from typing import Optional

"""
数据库连接管理器测试
Enhanced database connection manager tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# 导入被测试模块
from src.database.connection import (
    DatabaseManager,
    MultiUserDatabaseManager,
    DatabaseRole,
    get_database_manager,
    get_session,
    get_async_session,
    initialize_database,
)


class MockDatabaseManager:
    """模拟数据库管理器（用于无依赖环境）"""

    def __init__(self, database_url=None):
        self.database_url = database_url
        self.initialized = False

    def initialize(self, database_url=None):
        """初始化数据库连接"""
        if database_url:
            self.database_url = database_url
        self.initialized = True

    def get_session(self):
        """获取同步会话"""
        if not self.initialized:
            raise RuntimeError(
                "DatabaseManager is not initialized. Call initialize() first."
            )
        return Mock()

    def get_async_session(self):
        """获取异步会话"""
        if not self.initialized:
            raise RuntimeError(
                "DatabaseManager is not initialized. Call initialize() first."
            )
        return AsyncMock()


class TestDatabaseManager:
    """数据库管理器测试类"""

    def test_manager_initialization_with_url(self):
        """测试使用URL初始化管理器"""
        url = "postgresql://test:pass@localhost/test"
        manager = MockDatabaseManager(url)

        assert manager.database_url == url
        assert manager.initialized is False

    def test_manager_initialization_without_url(self):
        """测试不使用URL初始化管理器"""
        manager = MockDatabaseManager()

        assert manager.database_url is None
        assert manager.initialized is False

    def test_initialize(self):
        """测试初始化"""
        manager = MockDatabaseManager()
        assert manager.initialized is False

        manager.initialize("postgresql://test:pass@localhost/test")

        assert manager.initialized is True
        assert manager.database_url == "postgresql://test:pass@localhost/test"

    def test_initialize_with_default_url(self):
        """测试使用默认URL初始化"""
        manager = MockDatabaseManager()
        manager.initialize()

        assert manager.initialized is True

    def test_get_session_success(self):
        """测试成功获取同步会话"""
        manager = MockDatabaseManager()
        manager.initialize()

        session = manager.get_session()
        assert session is not None

    def test_get_session_before_initialization(self):
        """测试未初始化时获取会话应该失败"""
        manager = MockDatabaseManager()

        with pytest.raises(RuntimeError, match="DatabaseManager is not initialized"):
            manager.get_session()

    def test_get_async_session_success(self):
        """测试成功获取异步会话"""
        manager = MockDatabaseManager()
        manager.initialize()

        session = manager.get_async_session()
        assert session is not None

    def test_get_async_session_before_initialization(self):
        """测试未初始化时获取异步会话应该失败"""
        manager = MockDatabaseManager()

        with pytest.raises(RuntimeError, match="DatabaseManager is not initialized"):
            manager.get_async_session()


class TestRealDatabaseManager:
    """真实数据库管理器测试类"""

    @pytest.fixture
    def mock_sqlalchemy(self):
        """模拟SQLAlchemy fixture"""
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch(
                "src.database.definitions.create_async_engine"
            ) as mock_create_async_engine,
            patch("src.database.definitions.sessionmaker") as mock_sessionmaker,
            patch(
                "src.database.definitions.async_sessionmaker"
            ) as mock_async_sessionmaker,
        ):
            mock_engine = Mock()
            mock_async_engine = AsyncMock()
            mock_session_factory = Mock()
            mock_async_session_factory = Mock()

            mock_create_engine.return_value = mock_engine
            mock_create_async_engine.return_value = mock_async_engine
            mock_sessionmaker.return_value = mock_session_factory
            mock_async_sessionmaker.return_value = mock_async_session_factory

            yield {
                "create_engine": mock_create_engine,
                "create_async_engine": mock_create_async_engine,
                "sessionmaker": mock_sessionmaker,
                "async_sessionmaker": mock_async_sessionmaker,
                "engine": mock_engine,
                "async_engine": mock_async_engine,
                "session_factory": mock_session_factory,
                "async_session_factory": mock_async_session_factory,
            }

    def test_real_manager_initialization(self, mock_sqlalchemy):
        """测试真实管理器初始化"""
        manager = DatabaseManager()

        # 测试单例模式
        manager2 = DatabaseManager()
        assert manager is manager2

        # 测试初始化
        url = "postgresql://test:pass@localhost/test"
        manager.initialize(url)

        assert manager.initialized is True

        # 验证SQLAlchemy调用
        mock_sqlalchemy["create_engine"].assert_called_once()
        mock_sqlalchemy["create_async_engine"].assert_called_once()
        mock_sqlalchemy["sessionmaker"].assert_called_once()
        mock_sqlalchemy["async_sessionmaker"].assert_called_once()

    def test_database_url_from_env(self, mock_sqlalchemy):
        """测试从环境变量获取数据库URL"""
        with patch.dict(
            "os.environ", {"DATABASE_URL": "postgresql://env:pass@localhost/envdb"}
        ):
            manager = DatabaseManager()
            manager.initialize()

            # 验证URL构造
            mock_sqlalchemy["create_engine"].assert_called_once_with(
                "postgresql://env:pass@localhost/envdb",
                pool_pre_ping=True,
                pool_recycle=300,
            )
            mock_sqlalchemy["create_async_engine"].assert_called_once_with(
                "postgresql+asyncpg://env:pass@localhost/envdb",
                pool_pre_ping=True,
                pool_recycle=300,
            )

    def test_database_url_default(self, mock_sqlalchemy):
        """测试默认数据库URL"""
        with patch.dict("os.environ", {}, clear=True):
            manager = DatabaseManager()
            manager.initialize()

            # 验证默认URL
            mock_sqlalchemy["create_engine"].assert_called_once_with(
                "postgresql://localhost/football_prediction",
                pool_pre_ping=True,
                pool_recycle=300,
            )

    def test_double_initialization(self, mock_sqlalchemy):
        """测试重复初始化"""
        manager = DatabaseManager()
        manager.initialize("postgresql://test:pass@localhost/test")

        # 第二次初始化应该被忽略
        manager.initialize("postgresql://other:pass@localhost/other")

        # 验证只调用了一次初始化
        assert mock_sqlalchemy["create_engine"].call_count == 1
        assert mock_sqlalchemy["create_async_engine"].call_count == 1

    def test_get_session_real_manager(self, mock_sqlalchemy):
        """测试真实管理器获取同步会话"""
        manager = DatabaseManager()
        manager.initialize()

        mock_session = Mock()
        mock_sqlalchemy["session_factory"].return_value = mock_session

        session = manager.get_session()

        assert session is mock_session
        mock_sqlalchemy["session_factory"].assert_called_once()

    def test_get_async_session_real_manager(self, mock_sqlalchemy):
        """测试真实管理器获取异步会话"""
        manager = DatabaseManager()
        manager.initialize()

        mock_async_session = AsyncMock()
        mock_sqlalchemy["async_session_factory"].return_value = mock_async_session

        session = manager.get_async_session()

        assert session is mock_async_session
        mock_sqlalchemy["async_session_factory"].assert_called_once()

    def test_get_session_without_initialization_real_manager(self):
        """测试未初始化时获取会话失败"""
        manager = DatabaseManager()

        with pytest.raises(RuntimeError, match="DatabaseManager is not initialized"):
            manager.get_session()

    def test_get_async_session_without_initialization_real_manager(self):
        """测试未初始化时获取异步会话失败"""
        manager = DatabaseManager()

        with pytest.raises(RuntimeError, match="DatabaseManager is not initialized"):
            manager.get_async_session()


class TestDatabaseRole:
    """数据库角色测试类"""

    def test_database_role_values(self):
        """测试数据库角色枚举值"""
        assert DatabaseRole.READER.value == "reader"
        assert DatabaseRole.WRITER.value == "writer"
        assert DatabaseRole.ADMIN.value == "admin"

    def test_database_role_creation(self):
        """测试数据库角色创建"""
        reader_role = DatabaseRole.READER
        writer_role = DatabaseRole.WRITER
        admin_role = DatabaseRole.ADMIN

        assert reader_role != writer_role
        assert writer_role != admin_role
        assert reader_role != admin_role

    def test_database_role_comparison(self):
        """测试数据库角色比较"""
        role1 = DatabaseRole.READER
        role2 = DatabaseRole.READER
        role3 = DatabaseRole.WRITER

        assert role1 == role2
        assert role1 != role3


class TestMultiUserDatabaseManager:
    """多用户数据库管理器测试类"""

    def test_multi_user_inheritance(self):
        """测试多用户管理器继承"""
        multi_manager = MultiUserDatabaseManager()

        # 验证继承关系
        assert isinstance(multi_manager, DatabaseManager)
        assert hasattr(multi_manager, "readers")
        assert hasattr(multi_manager, "writers")
        assert hasattr(multi_manager, "admins")

    def test_multi_user_initialization(self, mock_sqlalchemy):
        """测试多用户管理器初始化"""
        multi_manager = MultiUserDatabaseManager()
        multi_manager.initialize("postgresql://test:pass@localhost/test")

        assert multi_manager.initialized is True
        assert multi_manager.readers == []
        assert multi_manager.writers == []
        assert multi_manager.admins == []

    def test_multi_user_singleton_behavior(self):
        """测试多用户管理器单例行为"""
        manager1 = MultiUserDatabaseManager()
        manager2 = MultiUserDatabaseManager()

        # 应该是同一个实例（因为继承自DatabaseManager的单例）
        assert manager1 is manager2


class TestFactoryFunctions:
    """工厂函数测试类"""

    def test_get_database_manager(self):
        """测试获取数据库管理器单例"""
        manager1 = get_database_manager()
        manager2 = get_database_manager()

        assert isinstance(manager1, DatabaseManager)
        assert manager1 is manager2

    def test_initialize_database(self, mock_sqlalchemy):
        """测试初始化数据库函数"""
        result = initialize_database("postgresql://test:pass@localhost/test")

        # 验证返回数据库管理器实例
        assert isinstance(result, DatabaseManager)
        assert result.initialized is True

        # 验证SQLAlchemy调用
        mock_sqlalchemy["create_engine"].assert_called_once()
        mock_sqlalchemy["create_async_engine"].assert_called_once()

    @patch("src.database.connection.get_database_manager")
    def test_get_session_function(self, mock_get_manager):
        """测试获取会话便捷函数"""
        mock_manager = Mock()
        mock_session = Mock()
        mock_manager.get_session.return_value = mock_session
        mock_get_manager.return_value = mock_manager

        session = get_session()

        assert session is mock_session
        mock_manager.get_session.assert_called_once()

    @patch("src.database.connection.get_database_manager")
    def test_get_async_session_function(self, mock_get_manager):
        """测试获取异步会话便捷函数"""
        mock_manager = Mock()
        mock_async_session = AsyncMock()
        mock_manager.get_async_session.return_value = mock_async_session
        mock_get_manager.return_value = mock_manager

        session = get_async_session()

        assert session is mock_async_session
        mock_manager.get_async_session.assert_called_once()


class TestErrorHandling:
    """错误处理测试类"""

    def test_invalid_database_url(self):
        """测试无效的数据库URL"""
        manager = DatabaseManager()

        # 测试None URL
        with pytest.raises(ValueError, match="Database URL is required"):
            manager.initialize(None)

        with pytest.raises(ValueError, match="Database URL is required"):
            manager.initialize("")

    def test_database_connection_failure(self, mock_sqlalchemy):
        """测试数据库连接失败"""
        mock_sqlalchemy["create_engine"].side_effect = Exception("Connection failed")

        manager = DatabaseManager()

        with pytest.raises(Exception, match="Connection failed"):
            manager.initialize("postgresql://test:pass@localhost/test")

    def test_async_connection_failure(self, mock_sqlalchemy):
        """测试异步数据库连接失败"""
        mock_sqlalchemy["create_engine"].return_value = Mock()
        mock_sqlalchemy["create_async_engine"].side_effect = Exception(
            "Async connection failed"
        )

        manager = DatabaseManager()

        with pytest.raises(Exception, match="Async connection failed"):
            manager.initialize("postgresql://test:pass@localhost/test")


class TestConfigurationOptions:
    """配置选项测试类"""

    def test_pool_configuration(self, mock_sqlalchemy):
        """测试连接池配置"""
        manager = DatabaseManager()
        manager.initialize("postgresql://test:pass@localhost/test")

        # 验证连接池配置
        mock_sqlalchemy["create_engine"].assert_called_once_with(
            "postgresql://test:pass@localhost/test",
            pool_pre_ping=True,
            pool_recycle=300,
        )

        mock_sqlalchemy["create_async_engine"].assert_called_once_with(
            "postgresql+asyncpg://test:pass@localhost/test",
            pool_pre_ping=True,
            pool_recycle=300,
        )

    def test_async_url_conversion(self, mock_sqlalchemy):
        """测试异步URL转换"""
        manager = DatabaseManager()
        manager.initialize("postgresql://user:pass@host:5432/dbname")

        # 验证URL转换
        sync_call = mock_sqlalchemy["create_engine"].call_args[0][0]
        async_call = mock_sqlalchemy["create_async_engine"].call_args[0][0]

        assert sync_call == "postgresql://user:pass@host:5432/dbname"
        assert async_call == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_session_factory_configuration(self, mock_sqlalchemy):
        """测试会话工厂配置"""
        manager = DatabaseManager()
        manager.initialize("postgresql://test:pass@localhost/test")

        # 验证同步会话工厂配置
        mock_sqlalchemy["sessionmaker"].assert_called_once_with(
            bind=mock_sqlalchemy["engine"]
        )

        # 验证异步会话工厂配置
        mock_sqlalchemy["async_sessionmaker"].assert_called_once_with(
            bind=mock_sqlalchemy["async_engine"],
            class_=AsyncSession,
        )


class TestIntegrationScenarios:
    """集成场景测试类"""

    def test_full_workflow_simulation(self, mock_sqlalchemy):
        """测试完整工作流模拟"""
        # 创建管理器
        manager = get_database_manager()

        # 初始化
        initialize_database("postgresql://test:pass@localhost/test")

        # 验证管理器状态
        assert manager.initialized is True

        # 模拟获取会话
        mock_session = Mock()
        mock_sqlalchemy["session_factory"].return_value = mock_session

        session = manager.get_session()
        assert session is mock_session

        # 模拟获取异步会话
        mock_async_session = AsyncMock()
        mock_sqlalchemy["async_session_factory"].return_value = mock_async_session

        async_session = manager.get_async_session()
        assert async_session is mock_async_session

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self, mock_sqlalchemy):
        """测试异步会话上下文管理器"""
        manager = DatabaseManager()
        manager.initialize()

        mock_async_session = AsyncMock()
        mock_sqlalchemy["async_session_factory"].return_value = mock_async_session

        # 模拟异步上下文管理器
        async with manager.get_async_session() as session:
            assert session is mock_async_session

    def test_multiple_session_creation(self, mock_sqlalchemy):
        """测试创建多个会话"""
        manager = DatabaseManager()
        manager.initialize()

        # 创建多个会话
        sessions = []
        for _i in range(3):
            mock_session = Mock()
            mock_sqlalchemy["session_factory"].return_value = mock_session
            session = manager.get_session()
            sessions.append(session)

        assert len(sessions) == 3
        assert mock_sqlalchemy["session_factory"].call_count == 3
