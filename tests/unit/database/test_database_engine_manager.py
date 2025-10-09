"""
数据库引擎管理器测试
"""

import pytest
from unittest.mock import MagicMock, patch

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from src.database.config import DatabaseConfig
from src.database.connection.pools.engine_manager import DatabaseEngineManager


@pytest.fixture
def engine_manager():
    """创建引擎管理器实例"""
    return DatabaseEngineManager()


@pytest.fixture
def database_config():
    """创建数据库配置"""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="test_user",
        password="test_password",
        echo=False
    )


class TestDatabaseEngineManager:
    """测试数据库引擎管理器"""

    def test_init(self, engine_manager):
        """测试初始化"""
        assert engine_manager._sync_engine is None
        assert engine_manager._async_engine is None
        assert engine_manager._session_factory is None
        assert engine_manager._async_session_factory is None
        assert engine_manager._config is None

    @patch('src.database.connection.pools.engine_manager.create_engine')
    @patch('src.database.connection.pools.engine_manager.create_async_engine')
    @patch('src.database.connection.pools.engine_manager.sessionmaker')
    @patch('src.database.connection.pools.engine_manager.async_sessionmaker')
    def test_initialize_engines_postgresql(
        self,
        mock_async_sessionmaker,
        mock_sessionmaker,
        mock_create_async_engine,
        mock_create_engine,
        engine_manager,
        database_config
    ):
        """测试初始化PostgreSQL引擎"""
        # 设置模拟
        mock_sync_engine = MagicMock(spec=Engine)
        mock_async_engine = MagicMock(spec=AsyncEngine)
        mock_session_factory = MagicMock()
        mock_async_session_factory_instance = MagicMock()

        mock_create_engine.return_value = mock_sync_engine
        mock_create_async_engine.return_value = mock_async_engine
        mock_sessionmaker.return_value = mock_session_factory
        mock_async_sessionmaker.return_value = mock_async_session_factory_instance

        # 初始化引擎
        engine_manager.initialize_engines(database_config)

        # 验证
        assert engine_manager._sync_engine == mock_sync_engine
        assert engine_manager._async_engine == mock_async_engine
        assert engine_manager._session_factory == mock_session_factory
        assert engine_manager._async_session_factory == mock_async_session_factory_instance
        assert engine_manager._config == database_config

        # 验证调用
        mock_create_engine.assert_called_once()
        mock_create_async_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()
        mock_async_sessionmaker.assert_called_once()

    @patch('src.database.connection.pools.engine_manager.create_engine')
    @patch('src.database.connection.pools.engine_manager.create_async_engine')
    def test_initialize_engines_sqlite(
        self,
        mock_create_async_engine,
        mock_create_engine,
        engine_manager
    ):
        """测试初始化SQLite引擎"""
        # SQLite配置
        sqlite_config = DatabaseConfig(
            database="test.db",
            echo=False
        )

        # 设置模拟
        mock_sync_engine = MagicMock()
        mock_async_engine = MagicMock()

        mock_create_engine.return_value = mock_sync_engine
        mock_create_async_engine.return_value = mock_async_engine

        # 初始化引擎
        engine_manager.initialize_engines(sqlite_config)

        # 验证调用（SQLite不应该使用连接池参数）
        mock_create_engine.assert_called_once()
        call_kwargs = mock_create_engine.call_args[1]
        assert "poolclass" not in call_kwargs
        assert "pool_size" not in call_kwargs

    def test_sync_engine_property(self, engine_manager):
        """测试同步引擎属性"""
        # 未初始化时应该抛出异常
        with pytest.raises(RuntimeError, match="数据库引擎未初始化"):
            _ = engine_manager.sync_engine

        # 初始化后应该正常返回
        mock_engine = MagicMock(spec=Engine)
        engine_manager._sync_engine = mock_engine
        assert engine_manager.sync_engine == mock_engine

    def test_async_engine_property(self, engine_manager):
        """测试异步引擎属性"""
        # 未初始化时应该抛出异常
        with pytest.raises(RuntimeError, match="数据库引擎未初始化"):
            _ = engine_manager.async_engine

        # 初始化后应该正常返回
        mock_engine = MagicMock(spec=AsyncEngine)
        engine_manager._async_engine = mock_engine
        assert engine_manager.async_engine == mock_engine

    def test_create_session(self, engine_manager):
        """测试创建会话"""
        # 设置会话工厂
        mock_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        engine_manager._session_factory = mock_session_factory

        # 创建会话
        session = engine_manager.create_session()

        # 验证
        assert session == mock_session
        mock_session_factory.assert_called_once()

    def test_create_async_session(self, engine_manager):
        """测试创建异步会话"""
        # 设置会话工厂
        mock_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        engine_manager._async_session_factory = mock_session_factory

        # 创建会话
        session = engine_manager.create_async_session()

        # 验证
        assert session == mock_session
        mock_session_factory.assert_called_once()

    def test_get_config(self, engine_manager, database_config):
        """测试获取配置"""
        # 未设置时返回None
        assert engine_manager.get_config() is None

        # 设置后返回配置
        engine_manager._config = database_config
        assert engine_manager.get_config() == database_config

    def test_close_engines(self, engine_manager):
        """测试关闭引擎"""
        # 设置模拟引擎
        mock_sync_engine = MagicMock()
        mock_async_engine = MagicMock()
        engine_manager._sync_engine = mock_sync_engine
        engine_manager._async_engine = mock_async_engine

        # 关闭引擎
        engine_manager.close_engines()

        # 验证
        mock_sync_engine.dispose.assert_called_once()

    def test_is_initialized(self, engine_manager):
        """测试是否已初始化"""
        # 未初始化
        assert not engine_manager.is_initialized

        # 部分初始化
        engine_manager._sync_engine = MagicMock()
        assert not engine_manager.is_initialized

        # 完全初始化
        engine_manager._async_engine = MagicMock()
        assert engine_manager.is_initialized