"""数据库连接和配置测试"""

import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration

from src.database.config import DatabaseConfig, get_database_config
from src.database.connection import DatabaseManager, get_database_manager


class TestDatabaseConfig:
    """数据库配置测试类"""

    def test_database_config_initialization(self):
        """测试数据库配置初始化"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass",
        )

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"
        assert config.username == "user"
        assert config.password == "pass"

    def test_sync_url_property(self):
        """测试同步URL属性"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass",
        )

        # 实际的PostgreSQL驱动使用psycopg2
        expected_url = "postgresql+psycopg2://user:pass@localhost:5432/test_db"
        assert config.sync_url == expected_url

    def test_async_url_property(self):
        """测试异步URL属性"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass",
        )

        expected_url = "postgresql+asyncpg://user:pass@localhost:5432/test_db"
        assert config.async_url == expected_url

    def test_alembic_url_property(self):
        """测试Alembic URL属性"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="user",
            password="pass",
        )

        # Alembic也使用psycopg2驱动
        expected_url = "postgresql+psycopg2://user:pass@localhost:5432/test_db"
        assert config.alembic_url == expected_url

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "env_host",
            "DB_PORT": "3306",
            "DB_NAME": "env_db",
            "DB_USER": "env_user",
            "DB_PASSWORD": "env_pass",
        },
        clear=True,
    )
    def test_get_database_config_from_env(self):
        """测试从环境变量获取数据库配置"""
        config = get_database_config()

        assert config.host == "env_host"
        assert config.port == 3306
        assert config.database == "env_db"
        assert config.username == "env_user"
        assert config.password == "env_pass"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_database_config_defaults(self):
        """测试默认数据库配置"""
        config = get_database_config()

        # 应该返回开发环境的默认配置
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "football_prediction_dev"


class TestDatabaseManager:
    """数据库管理器测试类"""

    def test_database_manager_singleton(self):
        """测试数据库管理器单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        assert manager1 is manager2

    def test_get_database_manager(self):
        """测试获取数据库管理器函数"""
        manager = get_database_manager()
        assert isinstance(manager, DatabaseManager)

    @patch("src.database.connection.create_engine")
    def test_sync_engine_creation(self, mock_create_engine):
        """测试同步引擎创建"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseManager()
        manager.initialize()

        engine = manager.sync_engine
        assert engine == mock_engine
        mock_create_engine.assert_called_once()

    @patch("src.database.connection.create_async_engine")
    def test_async_engine_creation(self, mock_create_async_engine):
        """测试异步引擎创建"""
        mock_engine = MagicMock()
        mock_create_async_engine.return_value = mock_engine

        manager = DatabaseManager()
        manager.initialize()

        engine = manager.async_engine
        assert engine == mock_engine
        mock_create_async_engine.assert_called_once()

    @patch("src.database.connection.sessionmaker")
    @patch("src.database.connection.create_engine")
    def test_create_session(self, mock_create_engine, mock_sessionmaker):
        """测试创建数据库会话"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_session_class = MagicMock()
        mock_sessionmaker.return_value = mock_session_class
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        manager = DatabaseManager()
        manager.initialize()

        session = manager.create_session()
        assert session == mock_session
        mock_sessionmaker.assert_called_once_with(
            bind=mock_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    def test_health_check_success(self):
        """测试健康检查成功"""
        manager = DatabaseManager()

        # 使用内存SQLite数据库进行测试
        with patch.object(manager, "create_session") as mock_create_session:
            mock_session = MagicMock()
            mock_create_session.return_value = mock_session
            mock_session.execute.return_value = None

            result = manager.health_check()
            assert result is True
            mock_session.execute.assert_called_once()
            mock_session.close.assert_called_once()

    def test_health_check_failure(self):
        """测试健康检查失败"""
        manager = DatabaseManager()

        with patch.object(manager, "create_session") as mock_create_session:
            mock_create_session.side_effect = Exception("Connection failed")

            result = manager.health_check()
            assert result is False
