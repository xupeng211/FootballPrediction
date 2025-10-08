"""扩展的数据库配置测试 - 提升覆盖率"""

import os
import pytest
from src.database.config import (
    DatabaseConfig,
    get_database_config,
    get_test_database_config,
    get_production_database_config,
    _parse_int,
    _get_env_bool,
    _ENV_PREFIX,
)


class TestDatabaseConfigExtended:
    """扩展的数据库配置测试，覆盖未测试的代码路径"""

    def test_config_with_memory_database(self):
        """测试内存数据库配置"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database=":memory:",
            username="user",
            password="pass",
        )
        assert config.sync_url == "sqlite:///:memory:"
        assert config.async_url == "sqlite+aiosqlite:///:memory:"
        assert config.alembic_url == config.sync_url

    def test_config_with_file_database(self):
        """测试文件数据库配置"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password="pass",
        )
        assert config.sync_url == "sqlite:///test.db"
        assert config.async_url == "sqlite+aiosqlite:///test.db"
        assert config.alembic_url == config.sync_url

    def test_config_with_postgresql(self):
        """测试PostgreSQL配置"""
        config = DatabaseConfig(
            host="db.example.com",
            port=5432,
            database="mydb",
            username="myuser",
            password="mypass",
        )
        expected = "postgresql+psycopg2://myuser:mypass@db.example.com:5432/mydb"
        assert config.sync_url == expected
        expected_async = "postgresql+asyncpg://myuser:mypass@db.example.com:5432/mydb"
        assert config.async_url == expected_async
        assert config.alembic_url == expected

    def test_parse_int_with_valid_value(self):
        """测试整数解析功能 - 有效值"""
        os.environ["TEST_INT"] = "42"
        result = _parse_int("TEST_INT", 10)
        assert result == 42
        del os.environ["TEST_INT"]

    def test_parse_int_with_invalid_value(self):
        """测试整数解析功能 - 无效值"""
        os.environ["TEST_INT_INVALID"] = "not_a_number"
        result = _parse_int("TEST_INT_INVALID", 10)
        assert result == 10  # 应该返回默认值
        del os.environ["TEST_INT_INVALID"]

    def test_parse_int_with_missing_env(self):
        """测试整数解析功能 - 缺失环境变量"""
        result = _parse_int("NON_EXISTENT_VAR", 99)
        assert result == 99

    def test_get_env_bool_true_values(self):
        """测试布尔环境变量解析 - 真值"""
        true_values = ["1", "true", "yes", "on"]
        for i, value in enumerate(true_values):
            env_key = f"TEST_BOOL_{i}"
            os.environ[env_key] = value
            assert _get_env_bool(env_key) is True
            del os.environ[env_key]

    def test_get_env_bool_false_values(self):
        """测试布尔环境变量解析 - 假值"""
        false_values = ["0", "false", "no", "off", "anything_else"]
        for i, value in enumerate(false_values):
            env_key = f"TEST_BOOL_FALSE_{i}"
            os.environ[env_key] = value
            assert _get_env_bool(env_key) is False
            del os.environ[env_key]

    def test_get_env_bool_default(self):
        """测试布尔环境变量解析 - 默认值"""
        result = _get_env_bool("NON_EXISTENT_BOOL", True)
        assert result is True
        result = _get_env_bool("NON_EXISTENT_BOOL", False)
        assert result is False

    def test_get_database_config_dev_environment(self):
        """测试开发环境配置"""
        # 开发环境需要密码（根据实际代码逻辑）
        os.environ["DB_PASSWORD"] = "dev_pass"

        config = get_database_config("development")
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "football_prediction_dev"
        assert config.username == "football_user"
        assert config.password == "dev_pass"

        # 清理
        del os.environ["DB_PASSWORD"]

    def test_get_database_config_test_environment(self):
        """测试测试环境配置"""
        # 清理环境变量
        for key in list(os.environ.keys()):
            if key.startswith("TEST_DB_"):
                del os.environ[key]

        config = get_database_config("test")
        assert config.database == ":memory:"
        assert config.username == "football_user"

    def test_get_database_config_production_without_password(self):
        """测试生产环境配置 - 无密码应该抛出异常"""
        # 清理环境变量
        for key in list(os.environ.keys()):
            if key.startswith("PROD_DB_"):
                del os.environ[key]

        with pytest.raises(ValueError, match="数据库密码未配置"):
            get_database_config("production")

    def test_get_database_config_production_with_password(self):
        """测试生产环境配置 - 有密码"""
        # 设置密码
        os.environ["PROD_DB_PASSWORD"] = "secret123"

        config = get_database_config("production")
        assert config.password == "secret123"
        assert config.database == "football_prediction_dev"

        # 清理
        del os.environ["PROD_DB_PASSWORD"]

    def test_get_database_config_with_custom_env_values(self):
        """测试使用自定义环境变量值"""
        # 先设置ENVIRONMENT为development，确保使用正确的前缀
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DB_HOST"] = "custom.host.com"
        os.environ["DB_PORT"] = "3306"
        os.environ["DB_NAME"] = "custom_db"
        os.environ["DB_USER"] = "custom_user"
        os.environ["DB_PASSWORD"] = "custom_pass"
        os.environ["DB_POOL_SIZE"] = "20"
        os.environ["DB_ECHO"] = "1"

        config = get_database_config()
        assert config.host == "custom.host.com"
        assert config.port == 3306
        assert config.database == "custom_db"
        assert config.username == "custom_user"
        assert config.password == "custom_pass"
        assert config.pool_size == 20
        assert config.echo is True

        # 清理
        for key in [
            "ENVIRONMENT",
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "DB_POOL_SIZE",
            "DB_ECHO",
        ]:
            if key in os.environ:
                del os.environ[key]

    def test_env_prefix_mapping(self):
        """测试环境前缀映射"""
        assert _ENV_PREFIX["development"] == ""
        assert _ENV_PREFIX["dev"] == ""
        assert _ENV_PREFIX["test"] == "TEST_"
        assert _ENV_PREFIX["production"] == "PROD_"
        assert _ENV_PREFIX["prod"] == "PROD_"
        assert _ENV_PREFIX.get("unknown", "") == ""  # dict.get 返回 None 如果没有默认值

    def test_get_test_database_config_function(self):
        """测试获取测试数据库配置函数"""
        config = get_test_database_config()
        assert isinstance(config, DatabaseConfig)
        # 测试环境应该使用内存数据库
        assert config.database == ":memory:" or config.database.endswith(".db")

    def test_get_production_database_config_function(self):
        """测试获取生产数据库配置函数"""
        # 设置密码以避免异常
        os.environ["PROD_DB_PASSWORD"] = "test_pass"

        config = get_production_database_config()
        assert isinstance(config, DatabaseConfig)
        # 生产环境不应该使用内存数据库
        assert config.database != ":memory:"

        # 清理
        del os.environ["PROD_DB_PASSWORD"]

    def test_config_with_async_pool_settings(self):
        """测试异步连接池设置"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password="pass",
            async_pool_size=5,
            async_max_overflow=10,
        )
        assert config.async_pool_size == 5
        assert config.async_max_overflow == 10

    def test_config_all_boolean_options(self):
        """测试所有布尔选项"""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test.db",
            username="user",
            password="pass",
            echo=True,
            echo_pool=True,
        )
        assert config.echo is True
        assert config.echo_pool is True
