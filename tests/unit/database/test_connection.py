"""
数据库连接测试
Tests for Database Connection

测试src.database.connection模块的功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from src.database.connection import (
    DatabaseRole,
    DatabaseManager,
    MultiUserDatabaseManager,
    get_database_manager,
    get_multi_user_database_manager,
    initialize_database,
    initialize_multi_user_database,
    initialize_test_database,
    get_db_session,
    get_async_session,
    get_reader_session,
    get_writer_session,
    get_admin_session,
    get_session,
    get_async_reader_session,
    get_async_writer_session,
    get_async_admin_session,
)


class TestDatabaseRole:
    """数据库角色测试"""

    def test_role_values(self):
        """测试：角色枚举值"""
        assert DatabaseRole.READER.value == "reader"
        assert DatabaseRole.WRITER.value == "writer"
        assert DatabaseRole.ADMIN.value == "admin"

    def test_role_comparison(self):
        """测试：角色比较"""
        assert DatabaseRole.READER == DatabaseRole.READER
        assert DatabaseRole.READER != DatabaseRole.WRITER

    def test_role_string_representation(self):
        """测试：角色字符串表示"""
        assert str(DatabaseRole.READER) == "DatabaseRole.READER"
        assert repr(DatabaseRole.READER) == "<DatabaseRole.READER: 'reader'>"


class TestDatabaseManager:
    """数据库管理器测试"""

    def test_singleton_pattern(self):
        """测试：单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_initialization_default(self):
        """测试：默认初始化"""
        with (
            patch("src.database.connection.create_engine") as mock_create_engine,
            patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_create_engine,
            patch("src.database.connection.sessionmaker") as mock_sessionmaker,
            patch(
                "src.database.connection.async_sessionmaker"
            ) as mock_async_sessionmaker,
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test/test"}, clear=True
            ),
        ):
            manager = DatabaseManager()
            manager.initialize()

            assert manager.initialized is True
            mock_create_engine.assert_called_once()
            mock_async_create_engine.assert_called_once()
            mock_sessionmaker.assert_called_once()
            mock_async_sessionmaker.assert_called_once()

    def test_initialization_with_custom_url(self):
        """测试：使用自定义URL初始化"""
        with (
            patch("src.database.connection.create_engine") as mock_create_engine,
            patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_create_engine,
        ):
            manager = DatabaseManager()
            custom_url = "postgresql://custom:pass@host:5432/db"
            manager.initialize(custom_url)

            assert manager.initialized is True
            # 检查调用参数
            sync_call_args = mock_create_engine.call_args
            async_call_args = mock_async_create_engine.call_args
            assert custom_url in str(sync_call_args)
            assert "postgresql+asyncpg://custom:pass@host:5432/db" in str(
                async_call_args
            )

    def test_initialization_no_url(self):
        """测试：没有URL时的初始化"""
        with patch.dict("os.environ", {}, clear=True):
            manager = DatabaseManager()
            with pytest.raises(ValueError) as exc_info:
                manager.initialize()
            assert "Database URL is required" in str(exc_info.value)

    def test_double_initialization(self):
        """测试：重复初始化"""
        with patch("src.database.connection.create_engine") as mock_create_engine:
            manager = DatabaseManager()
            manager.initialize("postgresql://test/test")
            manager.initialize("postgresql://test/test2")  # 第二次调用应该被忽略

            # 只应该调用一次
            assert mock_create_engine.call_count == 1

    def test_get_sync_session(self):
        """测试：获取同步会话"""
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)

        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch(
                "src.database.connection.sessionmaker",
                return_value=mock_session_factory,
            ),
        ):
            manager = DatabaseManager()
            manager.initialize("postgresql://test/test")

            session = manager.get_session()
            assert session == mock_session
            mock_session_factory.assert_called_once()

    def test_get_sync_session_auto_initialize(self):
        """测试：获取同步会话时自动初始化"""
        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)

        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch(
                "src.database.connection.sessionmaker",
                return_value=mock_session_factory,
            ),
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test/test"}, clear=True
            ),
        ):
            manager = DatabaseManager()
            # 不手动初始化

            session = manager.get_session()
            assert session == mock_session
            assert manager.initialized is True

    def test_get_async_session(self):
        """测试：获取异步会话"""
        mock_async_session = Mock()
        mock_async_session_factory = Mock(return_value=mock_async_session)

        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch(
                "src.database.connection.async_sessionmaker",
                return_value=mock_async_session_factory,
            ),
        ):
            manager = DatabaseManager()
            manager.initialize("postgresql://test/test")

            async_session = manager.get_async_session()
            assert async_session == mock_async_session
            mock_async_session_factory.assert_called_once()

    def test_get_async_session_auto_initialize(self):
        """测试：获取异步会话时自动初始化"""
        mock_async_session = Mock()
        mock_async_session_factory = Mock(return_value=mock_async_session)

        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch(
                "src.database.connection.async_sessionmaker",
                return_value=mock_async_session_factory,
            ),
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test/test"}, clear=True
            ),
        ):
            manager = DatabaseManager()
            # 不手动初始化

            async_session = manager.get_async_session()
            assert async_session == mock_async_session
            assert manager.initialized is True


class TestMultiUserDatabaseManager:
    """多用户数据库管理器测试"""

    def test_inheritance(self):
        """测试：继承关系"""
        manager = MultiUserDatabaseManager()
        assert isinstance(manager, DatabaseManager)

    def test_initialization(self):
        """测试：多用户管理器初始化"""
        manager = MultiUserDatabaseManager()
        assert hasattr(manager, "readers")
        assert hasattr(manager, "writers")
        assert hasattr(manager, "admins")
        assert manager.readers == []
        assert manager.writers == []
        assert manager.admins == []


class TestFactoryFunctions:
    """工厂函数测试"""

    def test_get_database_manager(self):
        """测试：获取数据库管理器"""
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        assert isinstance(manager1, DatabaseManager)
        assert manager1 is manager2  # 单例

    def test_get_multi_user_database_manager(self):
        """测试：获取多用户数据库管理器"""
        manager1 = get_multi_user_database_manager()
        manager2 = get_multi_user_database_manager()
        assert isinstance(manager1, MultiUserDatabaseManager)
        # 多用户管理器不是单例（每次返回新实例）
        assert manager1 is not manager2

    def test_initialize_database(self):
        """测试：初始化数据库函数"""
        with patch("src.database.connection.get_database_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            initialize_database("postgresql://test/test")

            mock_manager.initialize.assert_called_once_with("postgresql://test/test")

    def test_initialize_multi_user_database(self):
        """测试：初始化多用户数据库函数"""
        with patch(
            "src.database.connection.get_multi_user_database_manager"
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            initialize_multi_user_database("postgresql://test/test")

            mock_manager.initialize.assert_called_once_with("postgresql://test/test")

    def test_initialize_test_database(self):
        """测试：初始化测试数据库函数"""
        # 这个函数目前是空的，只是确保它不会抛出异常
        initialize_test_database()


class TestSessionFunctions:
    """会话获取函数测试"""

    def test_get_db_session(self):
        """测试：获取数据库会话"""
        mock_session = Mock()
        mock_manager = Mock()
        mock_manager.get_session.return_value = mock_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            session = get_db_session()
            assert session == mock_session
            mock_manager.get_session.assert_called_once()

    def test_get_async_session(self):
        """测试：获取异步会话"""
        mock_async_session = Mock()
        mock_manager = Mock()
        mock_manager.get_async_session.return_value = mock_async_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            async_session = get_async_session()
            assert async_session == mock_async_session
            mock_manager.get_async_session.assert_called_once()

    def test_get_reader_session(self):
        """测试：获取读会话"""
        mock_session = Mock()
        mock_manager = Mock()
        mock_manager.get_session.return_value = mock_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            session = get_reader_session()
            assert session == mock_session

    def test_get_writer_session(self):
        """测试：获取写会话"""
        mock_session = Mock()
        mock_manager = Mock()
        mock_manager.get_session.return_value = mock_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            session = get_writer_session()
            assert session == mock_session

    def test_get_admin_session(self):
        """测试：获取管理会话"""
        mock_session = Mock()
        mock_manager = Mock()
        mock_manager.get_session.return_value = mock_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            session = get_admin_session()
            assert session == mock_session

    def test_get_session_alias(self):
        """测试：会话获取别名"""
        mock_session = Mock()
        mock_manager = Mock()
        mock_manager.get_session.return_value = mock_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            session = get_session()
            assert session == mock_session

    def test_get_async_reader_session(self):
        """测试：获取异步读会话"""
        mock_async_session = Mock()
        mock_manager = Mock()
        mock_manager.get_async_session.return_value = mock_async_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            async_session = get_async_reader_session()
            assert async_session == mock_async_session

    def test_get_async_writer_session(self):
        """测试：获取异步写会话"""
        mock_async_session = Mock()
        mock_manager = Mock()
        mock_manager.get_async_session.return_value = mock_async_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            async_session = get_async_writer_session()
            assert async_session == mock_async_session

    def test_get_async_admin_session(self):
        """测试：获取异步管理会话"""
        mock_async_session = Mock()
        mock_manager = Mock()
        mock_manager.get_async_session.return_value = mock_async_session

        with patch(
            "src.database.connection.get_database_manager", return_value=mock_manager
        ):
            async_session = get_async_admin_session()
            assert async_session == mock_async_session


class TestDatabaseManagerIntegration:
    """数据库管理器集成测试"""

    def test_engine_configuration(self):
        """测试：引擎配置"""
        with (
            patch("src.database.connection.create_engine") as mock_create_engine,
            patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_create_engine,
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test/test"}, clear=True
            ),
        ):
            manager = DatabaseManager()
            manager.initialize()

            # 检查同步引擎配置
            sync_call_kwargs = mock_create_engine.call_args[1]
            assert sync_call_kwargs["pool_pre_ping"] is True
            assert sync_call_kwargs["pool_recycle"] == 300

            # 检查异步引擎配置
            async_call_kwargs = mock_async_create_engine.call_args[1]
            assert async_call_kwargs["pool_pre_ping"] is True
            assert async_call_kwargs["pool_recycle"] == 300

    def test_url_conversion(self):
        """测试：URL转换"""
        with (
            patch("src.database.connection.create_engine"),
            patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_create_engine,
        ):
            manager = DatabaseManager()
            postgresql_url = "postgresql://user:pass@host:5432/db"
            manager.initialize(postgresql_url)

            # 检查异步URL转换
            async_call_args = mock_async_create_engine.call_args[0][0]
            expected_async_url = "postgresql+asyncpg://user:pass@host:5432/db"
            assert async_call_args == expected_async_url

    def test_session_factory_configuration(self):
        """测试：会话工厂配置"""
        with (
            patch("src.database.connection.create_engine") as mock_create_engine,
            patch(
                "src.database.connection.create_async_engine"
            ) as mock_async_create_engine,
            patch("src.database.connection.sessionmaker") as mock_sessionmaker,
            patch(
                "src.database.connection.async_sessionmaker"
            ) as mock_async_sessionmaker,
        ):
            mock_engine = Mock()
            mock_async_engine = Mock()
            mock_create_engine.return_value = mock_engine
            mock_async_create_engine.return_value = mock_async_engine

            manager = DatabaseManager()
            manager.initialize("postgresql://test/test")

            # 检查同步会话工厂配置
            mock_sessionmaker.assert_called_once_with(bind=mock_engine)

            # 检查异步会话工厂配置
            mock_async_sessionmaker.assert_called_once_with(
                bind=mock_async_engine,
                class_=MagicMock(),  # AsyncSession类
            )

    def test_manager_state_persistence(self):
        """测试：管理器状态持久化"""
        manager1 = DatabaseManager()

        with (
            patch("src.database.connection.create_engine"),
            patch("src.database.connection.create_async_engine"),
            patch("src.database.connection.sessionmaker"),
            patch("src.database.connection.async_sessionmaker"),
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test/test"}, clear=True
            ),
        ):
            manager1.initialize()
            assert manager1.initialized is True

            # 获取同一个实例
            manager2 = DatabaseManager()
            assert manager2.initialized is True
            assert manager1 is manager2
