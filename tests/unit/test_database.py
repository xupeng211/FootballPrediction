"""
数据库模块测试
测试数据库连接、配置和连接池功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

# 正确的异步数据库导入
from src.database.connection import DatabaseManager, initialize_database, get_db_manager
from src.database.config import DatabaseConfig
from src.database.base import BaseModel, TimestampMixin


class TestDatabaseConfig:
    """数据库配置测试"""

    def test_database_config_creation(self):
        """测试数据库配置创建"""
        config_data = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",  # 修复参数名
            "password": "test_password",
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }

        config = DatabaseConfig(**config_data)

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"
        assert config.username == "test_user"  # 修复属性名
        assert config.password == "test_password"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_database_config_defaults(self):
        """测试数据库配置默认值"""
        config = DatabaseConfig(
            host="localhost",
            database="test_db",
            username="test_user",  # 修复参数名
            password="test_password",
        )

        # 验证默认值
        assert config.port == 5432
        assert config.pool_size == 10  # 修复默认值
        assert config.max_overflow == 20  # 修复默认值
        assert config.async_pool_size == 20
        assert config.async_max_overflow == 30
        assert config.echo == False

    def test_database_config_properties(self):
        """测试配置属性"""
        config = DatabaseConfig(
            host="localhost",
            database="test_db",
            username="test_user",
            password="test_password",
            pool_size=15,
        )

        # 测试URL生成
        sync_url = config.sync_url
        async_url = config.async_url
        alembic_url = config.alembic_url

        assert "postgresql+psycopg2://" in sync_url
        assert "postgresql+asyncpg://" in async_url
        assert sync_url == alembic_url
        assert "test_user" in sync_url
        assert "localhost:5432" in sync_url
        assert "test_db" in sync_url

    def test_database_config_url_encoding(self):
        """测试URL编码"""
        config = DatabaseConfig(
            host="localhost",
            database="test_db",
            username="user@name",  # 特殊字符
            password="pass@word",  # 特殊字符
            port=5432,
        )

        sync_url = config.sync_url
        # 用户名和密码应该被编码
        assert "user%40name" in sync_url
        assert "pass%40word" in sync_url


class TestDatabaseManager:
    """数据库管理器测试"""

    @pytest.fixture
    def mock_config(self):
        """Mock数据库配置"""
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",  # 修复参数名
            password="test_password",
            pool_size=5,
            max_overflow=10,
        )

    @patch("src.database.connection.create_async_engine")
    @patch("src.database.connection.async_sessionmaker")
    def test_manager_initialization(self, mock_sessionmaker, mock_create_engine, mock_config):
        """测试管理器初始化"""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        mock_sessionmaker.return_value = Mock()

        manager = DatabaseManager()
        manager.initialize(mock_config)

        assert manager._config == mock_config
        assert manager._async_engine == mock_engine

    @patch("src.database.connection.create_async_engine")
    def test_get_async_url(self, mock_create_engine, mock_config):
        """测试获取异步连接URL"""
        manager = DatabaseManager()
        manager.initialize(mock_config)

        async_url = mock_config.async_url

        assert "postgresql+asyncpg://" in async_url
        assert "test_user" in async_url
        assert "localhost:5432" in async_url
        assert "test_db" in async_url

    @patch("src.database.connection.create_async_engine")
    def test_engine_creation_config(self, mock_create_engine, mock_config):
        """测试引擎创建配置"""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseManager()
        manager.initialize(mock_config)

        # 验证引擎创建参数
        call_args = mock_create_engine.call_args
        assert call_args is not None

        url = call_args[0][0]
        assert "postgresql+asyncpg://" in url
        assert "localhost:5432" in url
        assert "test_db" in url

        kwargs = call_args[1]
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 10
        assert kwargs["pool_timeout"] == 30
        assert kwargs["pool_recycle"] == 3600

    @pytest.mark.asyncio
    async def test_get_async_session(self, mock_config):
        """测试获取异步会话"""
        with (
            patch("src.database.connection.create_async_engine") as mock_create_engine,
            patch("src.database.connection.async_sessionmaker") as mock_sessionmaker,
        ):

            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            mock_session_factory = Mock()
            mock_sessionmaker.return_value = mock_session_factory
            mock_session_factory.configure.return_value = AsyncMock()

            manager = DatabaseManager()
            manager.initialize(mock_config)

            async with manager.get_async_session() as session:
                mock_session_factory.assert_called_once()
                mock_session.__aenter__.assert_called_once()
                mock_session.__aexit__.assert_called_once()

    def test_close_connection(self):
        """测试关闭连接"""
        mock_engine = AsyncMock()

        manager = DatabaseManager()
        manager._async_engine = mock_engine  # 直接设置引擎

        manager.close()

        mock_engine.dispose.assert_called_once()
        assert not manager.is_initialized()

    def test_is_initialized(self):
        """测试初始化状态"""
        manager = DatabaseManager()

        # 未初始化状态
        assert not manager.is_initialized()

        # 设置引擎模拟初始化
        manager._async_engine = AsyncMock()
        assert manager.is_initialized()

    def test_sync_engine_disabled(self):
        """测试同步引擎被禁用"""
        manager = DatabaseManager()

        # sync_engine应该返回None
        assert manager.sync_engine is None

    def test_create_session_disabled(self):
        """测试同步会话被禁用"""
        manager = DatabaseManager()

        # create_session应该返回None
        assert manager.create_session() is None

    @patch("src.database.connection.get_db_session")
    def test_sync_session_disabled(self, mock_get_session):
        """测试同步会话被禁用"""
        from src.database.connection import get_db_session

        # get_db_session应该返回None
        result = get_db_session()
        assert result is None

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        assert manager1 is manager2

    def test_database_manager_initialization_with_defaults(self):
        """测试使用默认配置初始化"""
        with patch("src.database.connection.get_database_config") as mock_get_config:
            mock_config = DatabaseConfig(
                host="default_host",
                database="default_db",
                username="default_user",
                password="default_pass",
            )
            mock_get_config.return_value = mock_config

            manager = DatabaseManager()
            manager.initialize()  # 不传入配置

            assert manager._config == mock_config
            mock_get_config.assert_called_once()

    def test_database_config_environment_variables(self, monkeypatch):
        """测试从环境变量加载配置"""
        # 设置环境变量
        monkeypatch.setenv("DB_HOST", "env_host")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "env_db")
        monkeypatch.setenv("DB_USER", "env_user")
        monkeypatch.setenv("DB_PASSWORD", "env_password")

        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "env_host"
        assert config.port == 5433
        assert config.database == "env_db"
        assert config.username == "env_user"
        assert config.password == "env_password"


class TestBaseModel:
    """基础模型测试"""

    @pytest.fixture
    def sample_model_instance(self):
        """示例模型实例"""

        # 使用独立的模型类避免冲突
        class TestModel(BaseModel):
            __tablename__ = "test_models_unique"

            name = Mock()
            value = Mock()

        # 模拟数据库表结构
        TestModel.__table__ = Mock()
        TestModel.__table__.columns = [
            Mock(name="id"),
            Mock(name="name"),
            Mock(name="value"),
            Mock(name="created_at"),
            Mock(name="updated_at"),
        ]

        instance = TestModel()
        instance.id = 1
        instance.name = "test"
        instance.value = 100

        return instance

    def test_base_model_to_dict(self, sample_model_instance):
        """测试模型转换为字典"""

        # 模拟getattr行为
        def mock_getattr(obj, attr):
            if attr == "id":
                return 1
            elif attr == "name":
                return "test"
            elif attr == "value":
                return 100
            elif attr in ["created_at", "updated_at"]:
                return None
            return Mock()

        with patch("builtins.getattr", side_effect=mock_getattr):
            result = sample_model_instance.to_dict()

            assert isinstance(result, dict)
            # 应该包含所有字段
            assert "id" in result
            assert "name" in result
            assert "value" in result

    def test_base_model_to_dict_with_exclude(self, sample_model_instance):
        """测试模型转换为字典（排除字段）"""

        def mock_getattr(obj, attr):
            if attr == "id":
                return 1
            elif attr == "name":
                return "test"
            elif attr == "value":
                return 100
            elif attr in ["created_at", "updated_at"]:
                return None
            return Mock()

        with patch("builtins.getattr", side_effect=mock_getattr):
            result = sample_model_instance.to_dict(exclude_fields={"id", "created_at"})

            assert "id" not in result
            assert "created_at" not in result
            assert "name" in result
            assert "value" in result

    def test_base_model_from_dict(self):
        """测试从字典创建模型"""

        class TestModel(BaseModel):
            __tablename__ = "test_models_from_dict"

        # 模拟表结构
        TestModel.__table__ = Mock()
        TestModel.__table__.columns = [
            Mock(name="id"),
            Mock(name="name"),
            Mock(name="value"),
        ]

        data = {"id": 1, "name": "test", "value": 100, "extra": "ignored"}

        with patch.object(TestModel, "__init__", return_value=None):
            instance = TestModel.from_dict(data)

            # 应该过滤掉不属于模型的字段
            TestModel.__init__.assert_called_once_with(id=1, name="test", value=100)

    def test_base_model_update_from_dict(self):
        """测试从字典更新模型"""

        class TestModel(BaseModel):
            __tablename__ = "test_models_update"

        # 模拟表结构
        TestModel.__table__ = Mock()
        TestModel.__table__.columns = [
            Mock(name="id"),
            Mock(name="name"),
            Mock(name="value"),
            Mock(name="created_at"),
            Mock(name="updated_at"),
        ]

        instance = TestModel()
        data = {"name": "updated", "value": 200, "id": 999}

        with patch("builtins.setattr") as mock_setattr:
            instance.update_from_dict(data)

            # 应该排除id和created_at
            mock_setattr.assert_any_call(instance, "name", "updated")
            mock_setattr.assert_any_call(instance, "value", 200)
            # 不应该调用id
            setattr_calls = [call[0][1] for call in mock_setattr.call_args_list]
            assert "id" not in setattr_calls

    def test_base_model_repr(self, sample_model_instance):
        """测试模型字符串表示"""
        result = repr(sample_model_instance)
        assert "TestModel" in result
        assert "id=1" in result

    def test_timestamp_mixin(self):
        """测试时间戳混入"""
        from datetime import datetime

        mixin = TimestampMixin()

        # 验证字段存在
        assert hasattr(mixin, "created_at")
        assert hasattr(mixin, "updated_at")

        # 验证Column对象
        assert hasattr(mixin.created_at, "default")
        assert hasattr(mixin.updated_at, "onupdate")


class TestDatabaseIntegration:
    """数据库集成测试"""

    @patch("src.database.connection.create_async_engine")
    def test_database_lifecycle(self, mock_create_engine):
        """测试数据库生命周期"""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(
            host="localhost",
            database="test_db",
            username="test_user",  # 修复参数名
            password="test_password",
        )

        # 创建连接
        manager = DatabaseManager()
        manager.initialize(config)

        assert manager._async_engine == mock_engine
        assert manager.is_initialized() is True

        # 关闭连接
        manager.close()
        mock_engine.dispose.assert_called_once()

    @patch("src.database.connection.create_async_engine")
    def test_connection_pool_behavior(self, mock_create_engine):
        """测试连接池行为"""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(
            host="localhost",
            database="test_db",
            username="test_user",  # 修复参数名
            password="test_password",
            pool_size=3,
            max_overflow=5,
        )

        manager = DatabaseManager()
        manager.initialize(config)

        # 验证连接池配置
        call_args = mock_create_engine.call_args
        kwargs = call_args[1]
        assert kwargs["pool_size"] == 3
        assert kwargs["max_overflow"] == 5

    def test_database_config_environment_variables(self, monkeypatch):
        """测试从环境变量加载配置"""
        # 设置环境变量
        monkeypatch.setenv("DB_HOST", "env_host")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "env_db")
        monkeypatch.setenv("DB_USER", "env_user")
        monkeypatch.setenv("DB_PASSWORD", "env_password")

        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "env_host"
        assert config.port == 5433
        assert config.database == "env_db"
        assert config.user == "env_user"
        assert config.password == "env_password"

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """测试异步会话上下文管理器"""
        with (
            patch("src.database.connection.create_async_engine") as mock_create_engine,
            patch("src.database.connection.async_sessionmaker") as mock_sessionmaker,
        ):

            # 设置mock
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session_factory = Mock()
            mock_session_factory.return_value = mock_session
            mock_sessionmaker.return_value = mock_session_factory

            # 设置上下文管理器行为
            mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.__aexit__ = AsyncMock(return_value=None)

            config = DatabaseConfig(
                host="localhost",
                database="test_db",
                username="test_user",
                password="test_password",
            )

            manager = DatabaseManager()
            manager.initialize(config)

            # 测试异步会话上下文管理器
            async with manager.get_async_session() as session:
                assert session == mock_session

            mock_session_factory.assert_called_once()

    def test_global_functions(self):
        """测试全局便捷函数"""
        with patch("src.database.connection._db_manager") as mock_manager:
            # 测试get_db_manager
            from src.database.connection import get_db_manager

            result = get_db_manager()
            assert result == mock_manager


if __name__ == "__main__":
    # 运行数据库测试
    pytest.main([__file__, "-v", "-s"])
