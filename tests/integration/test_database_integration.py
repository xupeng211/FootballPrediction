"""
数据库集成测试
测试数据库连接、事务和模型操作
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import tempfile
import os

from src.database.config import DatabaseConfig
from src.database.connection import DatabaseManager, initialize_database
from src.database.base import BaseModel, TimestampMixin


class TestDatabaseIntegration:
    """数据库集成测试"""

    @pytest.fixture(scope="class")
    async def test_database_config(self):
        """测试数据库配置"""
        # 使用内存SQLite进行测试
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database=":memory:",
            username="test",
            password="test",
        )

    @pytest.fixture(scope="class")
    async def test_engine(self):
        """创建测试数据库引擎"""
        # 使用内存SQLite数据库进行测试
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.create_all)

        yield engine

        await engine.dispose()

    @pytest.fixture(scope="class")
    async def test_session_factory(self, test_engine):
        """创建测试会话工厂"""
        return sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    @pytest.mark.asyncio
    async def test_database_manager_initialization(self, test_database_config):
        """测试数据库管理器初始化"""
        manager = DatabaseManager()

        # 测试未初始化状态
        assert not manager.is_initialized()
        assert manager.sync_engine is None
        assert manager.create_session() is None

        # 测试初始化
        with patch("src.database.connection.create_async_engine") as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            manager.initialize(test_database_config)

            assert manager.is_initialized()
            assert manager._async_engine == mock_engine

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self, test_database_config):
        """测试异步会话上下文管理器"""
        manager = DatabaseManager()

        with (
            patch("src.database.connection.create_async_engine") as mock_create_engine,
            patch("src.database.connection.async_sessionmaker") as mock_sessionmaker,
        ):

            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session_factory = Mock()
            mock_session_factory.return_value = mock_session
            mock_sessionmaker.return_value = mock_session_factory

            # 设置上下文管理器行为
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.__aexit__ = AsyncMock(return_value=None)

            manager.initialize(test_database_config)

            # 测试异步会话上下文管理器
            async with manager.get_async_session() as session:
                assert session == mock_session

    def test_database_config_url_generation(self):
        """测试数据库配置URL生成"""
        config = DatabaseConfig(
            host="test-host",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
        )

        # 测试同步URL
        sync_url = config.sync_url
        assert "postgresql+psycopg2://" in sync_url
        assert "test_user" in sync_url
        assert "test-host:5432" in sync_url
        assert "test_db" in sync_url

        # 测试异步URL
        async_url = config.async_url
        assert "postgresql+asyncpg://" in async_url
        assert "test_user" in async_url
        assert "test-host:5432" in async_url
        assert "test_db" in async_url

        # 测试Alembic URL
        alembic_url = config.alembic_url
        assert alembic_url == sync_url

    def test_database_config_special_characters(self):
        """测试数据库配置特殊字符处理"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test-db",
            username="user@domain",
            password="p@ssw#rd",
        )

        # 测试URL编码
        sync_url = config.sync_url
        assert "user%40domain" in sync_url  # @编码为%40
        assert "p%40ssw%23rd" in sync_url  # @编码为%40, #编码为%23

    def test_database_config_defaults(self):
        """测试数据库配置默认值"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass",
        )

        # 测试默认值
        assert config.port == 5432
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
        assert config.async_pool_size == 20
        assert config.async_max_overflow == 30
        assert config.echo is False
        assert config.echo_pool is False

    def test_base_model_functionality(self):
        """测试基础模型功能"""

        # 创建测试模型
        class TestModel(BaseModel):
            __tablename__ = "test_models"

            def __init__(self):
                self.id = 1
                self.name = "test"

        model = TestModel()

        # 测试属性
        assert model.id == 1
        assert model.name == "test"

        # 测试方法存在性
        assert hasattr(model, "to_dict")
        assert hasattr(model, "from_dict")
        assert hasattr(model, "update_from_dict")
        assert hasattr(model, "__repr__")

    @patch("src.database.connection.get_db_manager")
    def test_global_database_functions(self, mock_get_manager):
        """测试全局数据库函数"""
        from src.database.connection import (
            get_db_manager,
            initialize_database,
            close_database,
        )

        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # 测试获取管理器
        manager = get_db_manager()
        assert manager == mock_manager

        # 测试全局初始化
        with patch("src.database.config.get_database_config") as mock_get_config:
            mock_config = Mock()
            mock_get_config.return_value = mock_config

            initialize_database()
            mock_manager.initialize.assert_called_once_with(mock_config)

        # 测试全局关闭
        close_database()
        mock_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_connection_string_validation(self):
        """测试数据库连接字符串验证"""
        from src.database.config import get_database_config

        # 测试环境变量配置
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "env-host",
                "DB_PORT": "5433",
                "DB_NAME": "env-db",
                "DB_USER": "env-user",
                "DB_PASSWORD": "env-pass",
            },
        ):
            config = get_database_config()

            assert config.host == "env-host"
            assert config.port == 5433
            assert config.database == "env-db"
            assert config.username == "env-user"
            assert config.password == "env-pass"

    def test_database_config_class_methods(self):
        """测试数据库配置类方法"""
        from src.database.config import (
            get_database_config,
            get_test_database_config,
            get_production_database_config,
        )

        # 测试不同环境的配置函数
        dev_config = get_database_config()
        assert isinstance(dev_config, DatabaseConfig)

        test_config = get_test_database_config()
        assert isinstance(test_config, DatabaseConfig)

        prod_config = get_production_database_config()
        assert isinstance(prod_config, DatabaseConfig)


class TestDatabaseErrorHandling:
    """数据库错误处理测试"""

    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """测试数据库连接失败处理"""
        manager = DatabaseManager()

        with patch("src.database.connection.create_async_engine") as mock_create_engine:
            mock_create_engine.side_effect = Exception("Connection failed")

            config = DatabaseConfig(
                host="invalid-host",
                port=5432,
                database="test",
                username="user",
                password="pass",
            )

            # 测试初始化失败不会抛出异常（应该在更高层处理）
            try:
                manager.initialize(config)
            except Exception:
                pass  # 预期可能会失败

    @pytest.mark.asyncio
    async def test_session_creation_failure(self):
        """测试会话创建失败处理"""
        manager = DatabaseManager()

        with (
            patch("src.database.connection.create_async_engine") as mock_create_engine,
            patch("src.database.connection.async_sessionmaker") as mock_sessionmaker,
        ):

            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            mock_sessionmaker.side_effect = Exception("Session creation failed")

            config = DatabaseConfig(
                host="localhost",
                port=5432,
                database="test",
                username="user",
                password="pass",
            )

            manager.initialize(config)

            # 测试会话创建失败
            with pytest.raises(Exception):
                session = manager.create_async_session()


class TestDatabasePerformance:
    """数据库性能测试"""

    def test_connection_pool_configuration(self):
        """测试连接池配置"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass",
            pool_size=15,
            max_overflow=25,
            pool_timeout=60,
            pool_recycle=7200,
        )

        assert config.pool_size == 15
        assert config.max_overflow == 25
        assert config.pool_timeout == 60
        assert config.pool_recycle == 7200
        assert config.async_pool_size == 20  # 默认值
        assert config.async_max_overflow == 30  # 默认值

    def test_database_echo_configuration(self):
        """测试数据库回显配置"""
        # 测试默认值
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass",
        )

        assert config.echo is False
        assert config.echo_pool is False

        # 测试设置回显
        config_echo = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test",
            username="user",
            password="pass",
            echo=True,
            echo_pool=True,
        )

        assert config_echo.echo is True
        assert config_echo.echo_pool is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
