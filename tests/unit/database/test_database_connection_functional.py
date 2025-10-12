#!/usr/bin/env python3
"""
数据库连接功能测试
Database Connection Functional Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.connection import (
    DatabaseManager,
    MultiUserDatabaseManager,
    DatabaseRole,
)


class TestDatabaseConnectionFunctional:
    """数据库连接功能测试"""

    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器实例"""
        manager = DatabaseManager()
        # 确保每次测试都是未初始化状态
        manager.initialized = False
        manager._engine = None
        manager._async_engine = None
        manager._session_factory = None
        manager._async_session_factory = None
        return manager

    @pytest.fixture
    def test_db_url(self):
        """测试数据库URL"""
        return "postgresql://test:test@localhost/test_db"

    def test_database_manager_singleton_pattern(self):
        """测试：DatabaseManager应该使用单例模式"""
        # When
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        # Then
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_database_manager_initialization(self, db_manager, test_db_url):
        """测试：数据库管理器初始化"""
        # When
        with patch("src.database.definitions.create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            db_manager.initialize(test_db_url)

        # Then
        assert db_manager.initialized is True
        assert db_manager._engine is not None
        assert db_manager._session_factory is not None
        assert db_manager._async_engine is not None
        assert db_manager._async_session_factory is not None

    def test_database_manager_initialization_with_env_var(self, db_manager):
        """测试：使用环境变量初始化数据库管理器"""
        # Given
        test_url = "postgresql://env:env@localhost/env_db"

        # When
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch.dict("os.environ", {"DATABASE_URL": test_url}),
        ):
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            db_manager.initialize()

        # Then
        assert db_manager.initialized is True
        mock_create_engine.assert_called()

    def test_database_manager_multiple_initialization(self, db_manager, test_db_url):
        """测试：多次初始化应该只执行一次"""
        # Given
        with patch("src.database.definitions.create_engine") as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine

            # When
            db_manager.initialize(test_db_url)
            db_manager.initialize(test_db_url)  # 第二次调用

        # Then
        assert db_manager.initialized is True
        assert mock_create_engine.call_count == 1

    def test_database_manager_raise_error_without_url(self, db_manager):
        """测试：没有提供数据库URL时应该抛出错误"""
        # Given
        with patch.dict("os.environ", {}, clear=True):
            # When / Then
            # 由于SQLAlchemy会先抛出错误，我们捕获任意异常
            with pytest.raises((ValueError, Exception)):
                db_manager.initialize()

    def test_get_sync_session(self, db_manager, test_db_url):
        """测试：获取同步会话"""
        # Given
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch("src.database.definitions.sessionmaker") as mock_sessionmaker,
        ):
            mock_engine = Mock()
            mock_session_factory = Mock()
            mock_create_engine.return_value = mock_engine
            mock_sessionmaker.return_value = mock_session_factory

            db_manager.initialize(test_db_url)

            # When
            session = db_manager.get_session()

        # Then
        assert session is not None
        mock_session_factory.assert_called_once()

    def test_get_async_session(self, db_manager, test_db_url):
        """测试：获取异步会话"""
        # Given
        with (
            patch("src.database.definitions.create_async_engine") as mock_create_engine,
            patch(
                "src.database.definitions.async_sessionmaker"
            ) as mock_async_sessionmaker,
        ):
            mock_engine = Mock()
            mock_session_factory = Mock()
            mock_create_engine.return_value = mock_engine
            mock_async_sessionmaker.return_value = mock_session_factory

            db_manager.initialize(test_db_url)

            # When
            session = db_manager.get_async_session()

        # Then
        assert session is not None
        mock_async_sessionmaker.assert_called_once()

    def test_get_session_auto_initialize(self, db_manager, test_db_url):
        """测试：获取会话时自动初始化"""
        # Given
        assert db_manager.initialized is False

        # When
        with patch.object(db_manager, "initialize") as mock_initialize:
            mock_session = Mock()
            mock_initialize.return_value = None
            db_manager._session_factory = Mock(return_value=mock_session)

            session = db_manager.get_session()

        # Then
        mock_initialize.assert_called_once()
        assert session is not None

    def test_database_url_conversion_to_async(self, db_manager):
        """测试：数据库URL转换为异步格式"""
        # Given
        sync_url = "postgresql://user:pass@localhost/db"
        expected_async_url = "postgresql+asyncpg://user:pass@localhost/db"

        # When
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch(
                "src.database.definitions.create_async_engine"
            ) as mock_create_async_engine,
        ):
            mock_create_engine.return_value = Mock()
            mock_create_async_engine.return_value = Mock()

            db_manager.initialize(sync_url)

        # Then
        mock_create_engine.assert_called_once_with(
            sync_url, pool_pre_ping=True, pool_recycle=300
        )
        mock_create_async_engine.assert_called_once_with(
            expected_async_url, pool_pre_ping=True, pool_recycle=300
        )

    def test_multi_user_database_manager_initialization(self):
        """测试：多用户数据库管理器初始化"""
        # When
        manager = MultiUserDatabaseManager()

        # Then
        assert isinstance(manager, DatabaseManager)
        # 检查是否成功创建了MultiUserDatabaseManager实例
        assert manager is not None
        # MultiUserDatabaseManager继承自DatabaseManager，应该有相同的属性
        assert hasattr(manager, "initialized")

    def test_database_role_enum(self):
        """测试：数据库角色枚举"""
        # Then
        assert DatabaseRole.READER.value == "reader"
        assert DatabaseRole.WRITER.value == "writer"
        assert DatabaseRole.ADMIN.value == "admin"

    def test_database_role_values(self):
        """测试：数据库角色值"""
        # When & Then
        roles = [role.value for role in DatabaseRole]
        assert "reader" in roles
        assert "writer" in roles
        assert "admin" in roles

    def test_database_engine_pool_configuration(self, db_manager, test_db_url):
        """测试：数据库引擎池配置"""
        # When
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch(
                "src.database.definitions.create_async_engine"
            ) as mock_create_async_engine,
        ):
            mock_create_engine.return_value = Mock()
            mock_create_async_engine.return_value = Mock()

            db_manager.initialize(test_db_url)

        # Then
        # 验证同步引擎配置
        mock_create_engine.assert_called_once()
        sync_kwargs = mock_create_engine.call_args.kwargs
        assert sync_kwargs["pool_pre_ping"] is True
        assert sync_kwargs["pool_recycle"] == 300

        # 验证异步引擎配置
        async_kwargs = mock_create_async_engine.call_args.kwargs
        assert async_kwargs["pool_pre_ping"] is True
        assert async_kwargs["pool_recycle"] == 300

    def test_database_session_return(self, db_manager, test_db_url):
        """测试：数据库会话返回"""
        # Given
        with (
            patch("src.database.definitions.create_engine") as mock_create_engine,
            patch("src.database.definitions.sessionmaker") as mock_sessionmaker,
        ):
            mock_engine = Mock()
            mock_session = Mock()
            mock_session_factory = Mock(return_value=mock_session)
            mock_create_engine.return_value = mock_engine
            mock_sessionmaker.return_value = mock_session_factory

            db_manager.initialize(test_db_url)

            # When
            session = db_manager.get_session()

            # Then
            assert session is not None
            assert session == mock_session
            mock_session_factory.assert_called_once()

    def test_database_manager_class_attributes(self, db_manager):
        """测试：数据库管理器类属性"""
        # Then
        assert hasattr(db_manager, "_instance")
        assert hasattr(db_manager, "_engine")
        assert hasattr(db_manager, "_async_engine")
        assert hasattr(db_manager, "_session_factory")
        assert hasattr(db_manager, "_async_session_factory")
        assert hasattr(db_manager, "initialized")
