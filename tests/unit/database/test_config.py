from unittest.mock import patch, MagicMock
"""
数据库配置测试
Tests for Database Config

测试src.database.config模块的功能
"""

import pytest
import tempfile
import os

from src.database.config import (
    DatabaseConfig,
    get_database_config,
    get_test_database_config,
    get_production_database_config,
    _get_env_bool,
    _parse_int,
)


@pytest.mark.unit
@pytest.mark.database

class TestDatabaseConfig:
    """数据库配置测试"""

    def test_config_creation_minimal(self):
        """测试：最小配置创建"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password=None,
        )

        assert _config.host == "localhost"
        assert _config.port == 5432
        assert _config.database == "testdb"
        assert _config.username == "user"
        assert _config.password is None
        assert _config.pool_size == 10  # 默认值
        assert _config.echo is False  # 默认值

    def test_config_creation_full(self):
        """测试：完整配置创建"""
        _config = DatabaseConfig(
            host="custom-host",
            port=5433,
            database="custom_db",
            username="custom_user",
            password="custom_pass",
            pool_size=20,
            max_overflow=30,
            pool_timeout=60,
            pool_recycle=3600,
            echo=True,
        )

        assert _config.host == "custom-host"
        assert _config.port == 5433
        assert _config.database == "custom_db"
        assert _config.username == "custom_user"
        assert _config.password == "custom_pass"
        assert _config.pool_size == 20
        assert _config.max_overflow == 30
        assert _config.pool_timeout == 60
        assert _config.pool_recycle == 3600
        assert _config.echo is True

    def test_is_sqlite_memory(self):
        """测试：SQLite内存数据库检测"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database=":memory:",
            username="user",
            password=None,
        )
        assert _config._is_sqlite() is True

    def test_is_sqlite_file(self):
        """测试：SQLite文件数据库检测"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password=None,
        )
        assert _config._is_sqlite() is True

    def test_is_not_sqlite(self):
        """测试：非SQLite数据库检测"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="postgresdb",
            username="user",
            password=None,
        )
        assert _config._is_sqlite() is False

    def test_sync_url_postgresql(self):
        """测试：PostgreSQL同步URL生成"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )
        expected = "postgresql+psycopg2://user:pass@localhost:5432/testdb"
        assert _config.sync_url == expected

    def test_sync_url_postgresql_no_password(self):
        """测试：PostgreSQL同步URL生成（无密码）"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password=None,
        )
        expected = "postgresql+psycopg2://user@localhost:5432/testdb"
        assert _config.sync_url == expected

    def test_sync_url_sqlite_memory(self):
        """测试：SQLite内存数据库同步URL"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database=":memory:",
            username="user",
            password=None,
        )
        assert _config.sync_url == "sqlite:///:memory:"

    def test_sync_url_sqlite_file(self):
        """测试：SQLite文件数据库同步URL"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password=None,
        )
        assert _config.sync_url == "sqlite:///test.db"

    def test_async_url_postgresql(self):
        """测试：PostgreSQL异步URL生成"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )
        expected = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        assert _config.async_url == expected

    def test_async_url_postgresql_no_password(self):
        """测试：PostgreSQL异步URL生成（无密码）"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password=None,
        )
        expected = "postgresql+asyncpg://user@localhost:5432/testdb"
        assert _config.async_url == expected

    def test_async_url_sqlite_memory(self):
        """测试：SQLite内存数据库异步URL"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database=":memory:",
            username="user",
            password=None,
        )
        assert _config.async_url == "sqlite+aiosqlite:///:memory:"

    def test_async_url_sqlite_file(self):
        """测试：SQLite文件数据库异步URL"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password=None,
        )
        assert _config.async_url == "sqlite+aiosqlite:///test.db"

    def test_alembic_url(self):
        """测试：Alembic URL生成"""
        _config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )
        assert _config.alembic_url == _config.sync_url


class TestEnvironmentHelpers:
    """环境变量辅助函数测试"""

    def test_get_env_bool_true(self):
        """测试：环境变量布尔值解析（真）"""
        with patch.dict("os.environ", {"TEST_BOOL": "true"}):
            pass
        with patch.dict("os.environ", {"TEST_BOOL": "true"}):
            pass
        with patch.dict("os.environ", {"TEST_BOOL": "true"}):
            assert _get_env_bool("TEST_BOOL") is True

        with patch.dict("os.environ", {"TEST_BOOL": "1"}):
            assert _get_env_bool("TEST_BOOL") is True

        with patch.dict("os.environ", {"TEST_BOOL": "YES"}):
            assert _get_env_bool("TEST_BOOL") is True

    def test_get_env_bool_false(self):
        """测试：环境变量布尔值解析（假）"""
        with patch.dict("os.environ", {"TEST_BOOL": "false"}):
            assert _get_env_bool("TEST_BOOL") is False

        with patch.dict("os.environ", {"TEST_BOOL": "0"}):
            assert _get_env_bool("TEST_BOOL") is False

        with patch.dict("os.environ", {"TEST_BOOL": "no"}):
            assert _get_env_bool("TEST_BOOL") is False

    def test_get_env_bool_default(self):
        """测试：环境变量布尔值解析（默认值）"""
        assert _get_env_bool("NONEXISTENT") is False
        assert _get_env_bool("NONEXISTENT", True) is True

    def test_parse_int_valid(self):
        """测试：环境变量整数解析（有效）"""
        with patch.dict("os.environ", {"TEST_INT": "123"}):
            pass
        with patch.dict("os.environ", {"TEST_INT": "123"}):
            pass
        with patch.dict("os.environ", {"TEST_INT": "123"}):
            pass
        with patch.dict("os.environ", {"TEST_INT": "123"}):
            pass
        with patch.dict("os.environ", {"TEST_INT": "123"}):
            assert _parse_int("TEST_INT", 0) == 123

    def test_parse_int_invalid(self):
        """测试：环境变量整数解析（无效）"""
        with patch.dict("os.environ", {"TEST_INT": "not_a_number"}):
            assert _parse_int("TEST_INT", 42) == 42

    def test_parse_int_default(self):
        """测试：环境变量整数解析（默认值）"""
        assert _parse_int("NONEXISTENT", 99) == 99


class TestDatabaseConfigFactory:
    """数据库配置工厂函数测试"""

    def test_get_database_config_development(self):
        """测试：获取开发环境配置"""
        with patch.dict("os.environ", {"DB_PASSWORD": "dev-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "dev-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "dev-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "dev-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "dev-pass"}, clear=True):
            _config = get_database_config("development")

            assert _config.host == "localhost"
            assert _config.port == 5432
            assert _config.database == "football_prediction_dev"
            assert _config.username == "football_user"
            assert _config.password == "dev-pass"

    def test_get_database_config_test(self):
        """测试：获取测试环境配置"""
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            _config = get_database_config("test")

            assert _config.host == "localhost"
            assert _config.port == 5432
            assert _config.database == ":memory:"
            assert _config.username == "football_user"
            assert _config.password is None  # 测试环境不需要密码

    def test_get_database_config_production_with_password(self):
        """测试：获取生产环境配置（有密码）"""
        env_vars = {
            "PROD_DB_HOST": "prod-host",
            "PROD_DB_PORT": "5433",
            "PROD_DB_NAME": "prod_db",
            "PROD_DB_USER": "prod_user",
            "PROD_DB_PASSWORD": "secret_pass",
            "PROD_DB_POOL_SIZE": "20",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_database_config("production")

            assert _config.host == "prod-host"
            assert _config.port == 5433
            assert _config.database == "prod_db"
            assert _config.username == "prod_user"
            assert _config.password == "secret_pass"
            assert _config.pool_size == 20

    def test_get_database_config_production_missing_password(self):
        """测试：获取生产环境配置（缺少密码）"""
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_database_config("production")

            assert "数据库密码未配置" in str(exc_info.value)
            assert "PROD_DB_PASSWORD" in str(exc_info.value)

    def test_get_database_config_from_env(self):
        """测试：从环境变量获取配置"""
        env_vars = {
            "ENVIRONMENT": "development",
            "DB_HOST": "env-host",
            "DB_PORT": "55432",
            "DB_NAME": "env-db",
            "DB_USER": "env-user",
            "DB_PASSWORD": "env-pass",
            "DB_POOL_SIZE": "15",
            "DB_ECHO": "true",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_database_config()

            assert _config.host == "env-host"
            assert _config.port == 55432
            assert _config.database == "env-db"
            assert _config.username == "env-user"
            assert _config.password == "env-pass"
            assert _config.pool_size == 15
            assert _config.echo is True

    def test_get_database_config_dev_environment_alias(self):
        """测试：开发环境别名"""
        with patch.dict(
            "os.environ", {"DB_HOST": "dev-host", "DB_PASSWORD": "dev-pass"}, clear=True
        ):
            _config = get_database_config("dev")
            assert _config.host == "dev-host"

    def test_get_database_config_prod_environment_alias(self):
        """测试：生产环境别名"""
        env_vars = {"PROD_DB_HOST": "prod-host-alias", "PROD_DB_PASSWORD": "secret"}

        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_database_config("prod")
            assert _config.host == "prod-host-alias"

    def test_get_database_config_unknown_environment(self):
        """测试：未知环境"""
        with patch.dict("os.environ", {"DB_PASSWORD": "unknown-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "unknown-pass"}, clear=True):
            pass
        with patch.dict("os.environ", {"DB_PASSWORD": "unknown-pass"}, clear=True):
            _config = get_database_config("unknown")
            # 应该使用开发环境的默认值
            assert _config.host == "localhost"
            assert _config.database == "football_prediction_dev"

    def test_get_test_database_config(self):
        """测试：获取测试数据库配置快捷函数"""
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            _config = get_test_database_config()

            assert _config.database == ":memory:"
            assert _config.username == "football_user"

    def test_get_production_database_config_with_password(self):
        """测试：获取生产数据库配置快捷函数（有密码）"""
        env_vars = {"PROD_DB_HOST": "prod-host", "PROD_DB_PASSWORD": "secret"}

        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_production_database_config()

            assert _config.host == "prod-host"
            assert _config.password == "secret"

    def test_get_production_database_config_missing_password(self):
        """测试：获取生产数据库配置快捷函数（缺少密码）"""
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            pass
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError):
                get_production_database_config()

    def test_config_with_all_pool_parameters(self):
        """测试：完整的连接池配置"""
        env_vars = {
            "DB_HOST": "localhost",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_POOL_SIZE": "15",
            "DB_MAX_OVERFLOW": "25",
            "DB_POOL_TIMEOUT": "45",
            "DB_POOL_RECYCLE": "2700",
            "DB_ASYNC_POOL_SIZE": "20",
            "DB_ASYNC_MAX_OVERFLOW": "30",
            "DB_ECHO": "true",
            "DB_ECHO_POOL": "true",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_database_config()

            assert _config.pool_size == 15
            assert _config.max_overflow == 25
            assert _config.pool_timeout == 45
            assert _config.pool_recycle == 2700
            assert _config.async_pool_size == 20
            assert _config.async_max_overflow == 30
            assert _config.echo is True
            assert _config.echo_pool is True

    def test_config_async_pool_defaults(self):
        """测试：异步连接池默认值"""
        env_vars = {
            "DB_HOST": "localhost",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_POOL_SIZE": "12",
            "DB_MAX_OVERFLOW": "18",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            pass
        with patch.dict("os.environ", env_vars, clear=True):
            _config = get_database_config()

            # 异步池默认使用同步池的值
            assert _config.async_pool_size == 12
            assert _config.async_max_overflow == 18
