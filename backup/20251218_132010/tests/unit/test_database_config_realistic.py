"""
基于实际API结构的数据库配置测试
第二层优化：专注数据库配置模块 (52% → 80%)
基于实际数据库配置结构的稳定测试
"""

import pytest
import os
import urllib.parse
from unittest.mock import patch, Mock, MagicMock


class TestDatabaseConfigCore:
    """数据库配置核心功能测试"""

    def test_database_config_creation_with_args(self):
        """测试使用参数创建数据库配置"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="test-host",
            port=5433,
            database="test-db",
            username="test-user",
            password="test-pass",
        )

        assert config.host == "test-host"
        assert config.port == 5433
        assert config.database == "test-db"
        assert config.username == "test-user"
        assert config.password == "test-pass"

    def test_database_config_default_values(self):
        """测试数据库配置默认值"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )

        # 验证连接池默认值
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

        # 验证异步配置默认值
        assert config.async_pool_size == 20
        assert config.async_max_overflow == 30

        # 验证其他默认值
        assert config.echo is False
        assert config.echo_pool is False

    def test_database_config_sync_url_generation(self):
        """测试同步URL生成"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="test-host",
            port=5433,
            database="test-db",
            username="user@name",  # 特殊字符
            password="p@ss#word",  # 特殊字符
        )

        sync_url = config.sync_url

        # 验证URL格式
        assert sync_url.startswith("postgresql+psycopg2://")
        assert "test-host" in sync_url
        assert "5433" in sync_url
        assert "test-db" in sync_url

        # 验证特殊字符被正确编码
        assert "user%40name" in sync_url  # @被编码为%40
        assert "p%40ss%23word" in sync_url  # @和#被编码

    def test_database_config_async_url_generation(self):
        """测试异步URL生成"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="mydb",
            username="myuser",
            password="mypass",
        )

        async_url = config.async_url

        # 验证异步URL格式
        assert async_url.startswith("postgresql+asyncpg://")
        assert "myuser" in async_url
        assert "mypass" in async_url
        assert "localhost" in async_url
        assert "5432" in async_url
        assert "mydb" in async_url

    def test_database_config_alembic_url(self):
        """测试Alembic URL"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="alembic-host",
            port=5434,
            database="alembic-db",
            username="alembic-user",
            password="alembic-pass",
        )

        alembic_url = config.alembic_url

        # Alembic URL应该等于同步URL
        assert alembic_url == config.sync_url
        assert alembic_url.startswith("postgresql+psycopg2://")

    def test_database_config_url_encoding_safety(self):
        """测试URL编码安全性"""
        from src.database.config import DatabaseConfig

        # 测试各种特殊字符
        config = DatabaseConfig(
            host="host with spaces",
            port=5432,
            database="db-with-dash",
            username="user with spaces@symbol",
            password="pass with spaces/slash\\backslash",
        )

        async_url = config.async_url

        # 验证空格和特殊字符被正确编码
        assert "%20" in async_url  # 空格
        assert "%40" in async_url  # @
        assert "%2F" in async_url  # /
        assert "%5C" in async_url  # \


class TestDatabaseConfigEnvironment:
    """数据库配置环境变量测试"""

    def test_get_database_config_development_default(self):
        """测试开发环境默认配置"""
        from src.database.config import get_database_config

        config = get_database_config("development")

        # 验证默认值
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "football_prediction_dev"
        assert config.username == "football_user"
        assert config.password == "football_pass"

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "env-host",
            "DB_PORT": "9999",
            "DB_NAME": "env-db",
            "DB_USER": "env-user",
            "DB_PASSWORD": "env-pass",
            "DB_POOL_SIZE": "15",
            "DB_MAX_OVERFLOW": "25",
        },
    )
    def test_get_database_config_from_environment(self):
        """测试从环境变量获取配置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "env-host"
        assert config.port == 9999
        assert config.database == "env-db"
        assert config.username == "env-user"
        assert config.password == "env-pass"
        assert config.pool_size == 15
        assert config.max_overflow == 25

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "test",
            "TEST_DB_HOST": "test-host",
            "TEST_DB_NAME": "test-db",
            "TEST_DB_USER": "test-user",
        },
    )
    def test_get_database_config_test_environment(self):
        """测试测试环境配置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "test-host"
        assert config.database == "test-db"
        assert config.username == "test-user"

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "PROD_DB_HOST": "prod-host",
            "PROD_DB_NAME": "prod-db",
            "PROD_DB_USER": "prod-user",
        },
    )
    def test_get_database_config_production_environment(self):
        """测试生产环境配置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "prod-host"
        assert config.database == "prod-db"
        assert config.username == "prod-user"

    @patch.dict(os.environ, {"DB_ECHO": "true", "DB_ECHO_POOL": "true"})
    def test_get_database_config_debug_flags(self):
        """测试调试标志配置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.echo is True
        assert config.echo_pool is True

    @patch.dict(os.environ, {"DB_ECHO": "false", "DB_ECHO_POOL": "FALSE"})
    def test_get_database_config_debug_flags_case_insensitive(self):
        """测试调试标志大小写不敏感"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.echo is False
        assert config.echo_pool is False


class TestDatabaseConfigUtility:
    """数据库配置工具函数测试"""

    def test_get_test_database_config(self):
        """测试获取测试数据库配置"""
        from src.database.config import get_test_database_config

        config = get_test_database_config()

        # 验证是DatabaseConfig实例
        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "database")

    def test_get_production_database_config(self):
        """测试获取生产数据库配置"""
        from src.database.config import get_production_database_config

        config = get_production_database_config()

        # 验证是DatabaseConfig实例
        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "database")

    def test_get_database_config_with_none_environment(self):
        """测试None环境参数"""
        from src.database.config import get_database_config

        # 传递None应该使用默认逻辑
        config = get_database_config(None)

        assert config is not None
        assert hasattr(config, "host")

    def test_get_database_config_unknown_environment(self):
        """测试未知环境"""
        from src.database.config import get_database_config

        # 未知环境应该使用无前缀的环境变量
        config = get_database_config("unknown_environment")

        assert config is not None
        # 应该使用默认的环境变量（无前缀）
        assert config.host == "localhost"  # 默认值


class TestDatabaseConfigValidation:
    """数据库配置验证测试"""

    def test_database_config_type_validation(self):
        """测试配置类型验证"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="string-host",
            port=5432,  # int
            database="string-db",
            username="string-user",
            password="string-pass",
        )

        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert isinstance(config.database, str)
        assert isinstance(config.username, str)
        assert isinstance(config.password, str)

    def test_database_config_port_range_validation(self):
        """测试端口范围验证"""
        from src.database.config import DatabaseConfig

        # 测试有效端口
        config1 = DatabaseConfig("host", 1, "db", "user", "pass")
        config2 = DatabaseConfig("host", 65535, "db", "user", "pass")

        assert config1.port == 1
        assert config2.port == 65535

    def test_database_config_pool_size_validation(self):
        """测试连接池大小验证"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        # 验证默认值
        assert config.pool_size > 0
        assert config.max_overflow > 0
        assert config.async_pool_size > 0
        assert config.async_max_overflow > 0

    def test_database_config_timeout_validation(self):
        """测试超时配置验证"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        # 验证超时配置
        assert config.pool_timeout > 0
        assert config.pool_recycle > 0


class TestDatabaseConfigURLProperties:
    """数据库配置URL属性测试"""

    def test_sync_url_special_characters(self):
        """测试同步URL特殊字符处理"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="host.com",
            port=5432,
            database="my-database",
            username="user@domain.com",
            password="p@ss:w0rd#",
        )

        sync_url = config.sync_url

        # 验证URL结构
        assert "postgresql+psycopg2://" in sync_url
        assert "host.com" in sync_url
        assert "5432" in sync_url
        assert "my-database" in sync_url

        # 验证编码
        assert "user%40domain.com" in sync_url
        assert "p%40ss%3Aw0rd%23" in sync_url

    def test_async_url_special_characters(self):
        """测试异步URL特殊字符处理"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            database="example_db",
            username="example_user",
            password="example$pass",
        )

        async_url = config.async_url

        # 验证URL结构
        assert "postgresql+asyncpg://" in async_url
        assert "db.example.com" in async_url
        assert "5433" in async_url
        assert "example_db" in async_url

        # 验证特殊字符编码
        assert "example_user" in async_url  # 无特殊字符
        assert "example%24pass" in async_url  # $被编码

    def test_url_consistency(self):
        """测试URL一致性"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        sync_url = config.sync_url
        alembic_url = config.alembic_url

        # sync_url和alembic_url应该相同
        assert sync_url == alembic_url

        # async_url应该不同（协议不同）
        async_url = config.async_url
        assert sync_url != async_url
        assert sync_url.startswith("postgresql+psycopg2://")
        assert async_url.startswith("postgresql+asyncpg://")

    def test_url_with_complex_credentials(self):
        """测试复杂凭据的URL生成"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="db-host.com",
            port=5432,
            database="my database",
            username="user name",
            password='pass/word\\with"quotes',
        )

        # 验证不会抛出编码异常
        sync_url = config.sync_url
        async_url = config.async_url

        assert isinstance(sync_url, str)
        assert isinstance(async_url, str)
        assert len(sync_url) > 0
        assert len(async_url) > 0


class TestDatabaseConfigIntegration:
    """数据库配置集成测试"""

    def test_config_dataclass_behavior(self):
        """测试配置数据类行为"""
        from src.database.config import DatabaseConfig

        config1 = DatabaseConfig("host", 5432, "db", "user", "pass")
        config2 = DatabaseConfig("host", 5432, "db", "user", "pass")
        config3 = DatabaseConfig("other-host", 5432, "db", "user", "pass")

        # 测试相等性
        assert config1 == config2
        assert config1 != config3

        # 测试哈希
        assert hash(config1) == hash(config2)

        # 测试表示
        repr_str = repr(config1)
        assert "DatabaseConfig" in repr_str
        assert "host" in repr_str

    def test_config_environment_isolation(self):
        """测试配置环境隔离"""
        from src.database.config import get_database_config

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "dev-host",
                "TEST_DB_HOST": "test-host",
                "PROD_DB_HOST": "prod-host",
            },
        ):
            dev_config = get_database_config("development")
            test_config = get_database_config("test")
            prod_config = get_database_config("production")

            assert dev_config.host == "dev-host"
            assert test_config.host == "test-host"
            assert prod_config.host == "prod-host"

    def test_config_fallback_behavior(self):
        """测试配置回退行为"""
        from src.database.config import get_database_config

        with patch.dict(os.environ, {}, clear=True):  # 清除所有环境变量
            config = get_database_config("unknown_env")

            # 应该使用默认值
            assert config.host == "localhost"
            assert config.port == 5432
            assert config.database == "football_prediction_dev"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
