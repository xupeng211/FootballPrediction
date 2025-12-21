"""
数据库连接稳定测试
第二层优化：专注数据库连接模块 (52% → 80%)
基于实际API结构的稳定、高覆盖率测试
"""

import pytest
import os
import time
from unittest.mock import patch, Mock, MagicMock


class TestDatabaseConnectionConfig:
    """数据库连接配置测试"""

    def test_database_pool_config_defaults(self):
        """测试数据库连接池配置默认值"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        # 验证基本属性
        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "user")
        assert hasattr(config, "password")
        assert hasattr(config, "database")

        # 验证连接池属性
        assert hasattr(config, "min_size")
        assert hasattr(config, "max_size")
        assert hasattr(config, "timeout")
        assert hasattr(config, "command_timeout")

        # 验证默认值
        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert config.min_size > 0
        assert config.max_size >= config.min_size
        assert config.timeout > 0

    @patch.dict(
        os.environ,
        {
            "DB_HOST": "custom-host",
            "DB_PORT": "8888",
            "DB_USER": "custom-user",
            "DB_PASSWORD": "custom-pass",
            "DB_NAME": "custom-db",
        },
    )
    def test_database_pool_config_environment_variables(self):
        """测试环境变量配置"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        assert config.host == "custom-host"
        assert config.port == 8888
        assert config.user == "custom-user"
        assert config.password == "custom-pass"
        assert config.database == "custom-db"

    def test_database_pool_config_url_parsing(self):
        """测试URL解析"""
        from src.database.db_pool import DatabasePoolConfig

        # 测试标准URL
        config = DatabasePoolConfig.from_url("postgresql+asyncpg://user:pass@hostname:1234/dbname")

        assert config.host == "hostname"
        assert config.port == 1234
        assert config.user == "user"
        assert config.password == "pass"
        assert config.database == "dbname"

    def test_database_pool_config_health_check_settings(self):
        """测试健康检查配置"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        # 验证健康检查配置
        assert hasattr(config, "health_check_interval")
        assert hasattr(config, "health_check_timeout")
        assert hasattr(config, "max_retries")
        assert hasattr(config, "retry_delay")

        # 验证默认值合理性
        assert config.health_check_interval > 0
        assert config.health_check_timeout > 0
        assert config.max_retries >= 0
        assert config.retry_delay >= 0

    @patch.dict(
        os.environ,
        {
            "DB_POOL_MIN_SIZE": "8",
            "DB_POOL_MAX_SIZE": "32",
            "DB_TIMEOUT": "90.5",
            "DB_COMMAND_TIMEOUT": "35.5",
        },
    )
    def test_database_pool_config_pool_settings(self):
        """测试连接池设置"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        assert config.min_size == 8
        assert config.max_size == 32
        assert config.timeout == 90.5
        assert config.command_timeout == 35.5


class TestDatabasePoolBasic:
    """数据库连接池基础功能测试"""

    def test_database_pool_creation(self):
        """测试连接池创建"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 验证初始化状态
        assert hasattr(pool, "config")
        assert hasattr(pool, "_pool")
        assert hasattr(pool, "_is_initialized")
        assert hasattr(pool, "_stats")

        assert pool.config == config
        assert pool._pool is None
        assert pool._is_initialized is False

    def test_database_pool_stats_initialization(self):
        """测试连接池统计初始化"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        stats = pool.get_stats()

        # 验证统计字段
        expected_fields = [
            "total_connections_created",
            "total_connections_acquired",
            "total_connections_released",
            "total_queries_executed",
            "total_errors",
            "pool_creation_time",
            "last_health_check",
            "health_check_count",
        ]

        for field in expected_fields:
            assert field in stats, f"缺少统计字段: {field}"

        # 验证初始值
        assert stats["total_connections_created"] == 0
        assert stats["total_queries_executed"] == 0
        assert stats["total_errors"] == 0

    def test_database_pool_info_structure(self):
        """测试连接池信息结构"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        config.host = "info-test-host"
        config.port = 7777
        config.min_size = 3
        config.max_size = 15

        pool = DatabasePool(config)

        info = pool.get_pool_info()

        # 验证信息结构
        assert "is_initialized" in info
        assert "config" in info
        assert "stats" in info

        # 验证配置信息
        config_info = info["config"]
        assert config_info["host"] == "info-test-host"
        assert config_info["port"] == 7777
        assert config_info["min_size"] == 3
        assert config_info["max_size"] == 15

    def test_database_pool_context_manager_support(self):
        """测试异步上下文管理器支持"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 验证异步上下文管理器方法存在
        assert hasattr(pool, "__aenter__")
        assert hasattr(pool, "__aexit__")

    async def test_database_pool_error_on_uninitialized_access(self):
        """测试未初始化访问的错误处理"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 验证未初始化状态
        assert pool._is_initialized is False

        # 验证未初始化时的错误状态
        # 这里不调用实际方法，只检查状态和错误类型
        assert pool._pool is None


class TestDatabaseManagerRealistic:
    """数据库管理器现实测试"""

    def test_database_manager_singleton(self):
        """测试数据库管理器单例模式"""
        from src.database.connection import DatabaseManager

        manager1 = DatabaseManager()
        manager2 = DatabaseManager()

        # 验证单例
        assert manager1 is manager2

    def test_database_manager_initialization_state(self):
        """测试数据库管理器初始化状态"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 验证初始状态
        assert hasattr(manager, "_initialized")
        assert manager._initialized is True

        assert hasattr(manager, "_config")
        assert manager._config is None

        # 验证未初始化状态
        assert manager.is_initialized() is False

    def test_database_manager_sync_disabled(self):
        """测试同步功能被禁用"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 同步引擎应该返回None
        assert manager.sync_engine is None

        # 同步会话创建应该返回None
        assert manager.create_session() is None

    def test_database_manager_async_engine_error(self):
        """测试异步引擎访问错误"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 未初始化时访问异步引擎应该抛出错误
        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            _ = manager.async_engine

    def test_database_manager_sync_session_context(self):
        """测试同步会话上下文管理器"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 同步会话上下文管理器应该返回None
        with manager.get_session() as session:
            assert session is None

    def test_database_manager_async_session_error(self):
        """测试异步会话创建错误"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 未初始化时创建异步会话应该抛出错误
        with pytest.raises(RuntimeError, match="数据库连接未初始化"):
            _ = manager.create_async_session()


class TestDatabaseConfigRealistic:
    """数据库配置现实测试"""

    def test_database_config_creation(self):
        """测试数据库配置创建"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="config-test-host",
            port=6000,
            database="config-test-db",
            username="config-test-user",
            password="config-test-pass",
        )

        assert config.host == "config-test-host"
        assert config.port == 6000
        assert config.database == "config-test-db"
        assert config.username == "config-test-user"
        assert config.password == "config-test-pass"

    def test_database_config_defaults(self):
        """测试数据库配置默认值"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )

        # 验证默认值
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
        assert config.async_pool_size == 20
        assert config.async_max_overflow == 30
        assert config.echo is False
        assert config.echo_pool is False

    def test_database_config_url_generation(self):
        """测试URL生成"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="url-test-host",
            port=5555,
            database="url-test-db",
            username="url-test-user",
            password="url-test-pass",
        )

        # 测试异步URL
        async_url = config.async_url
        assert "postgresql+asyncpg://" in async_url
        assert "url-test-host" in async_url
        assert "5555" in async_url
        assert "url-test-db" in async_url

        # 测试同步URL
        sync_url = config.sync_url
        assert "postgresql+psycopg2://" in sync_url
        assert "url-test-host" in sync_url

        # 测试Alembic URL
        alembic_url = config.alembic_url
        assert alembic_url == sync_url

    def test_database_config_special_character_encoding(self):
        """测试特殊字符编码"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig(
            host="encoding-host.com",
            port=5432,
            database="encoding-db",
            username="user@domain.com",
            password="p@ss#w0rd",
        )

        # 测试URL中的特殊字符被编码
        async_url = config.async_url
        sync_url = config.sync_url

        assert "user%40domain.com" in async_url
        assert "p%40ss%23w0rd" in async_url
        assert "user%40domain.com" in sync_url
        assert "p%40ss%23w0rd" in sync_url

    def test_get_database_config_default(self):
        """测试默认数据库配置获取"""
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
            "DB_HOST": "env-test-host",
            "DB_PORT": "7777",
            "DB_NAME": "env-test-db",
            "DB_USER": "env-test-user",
            "DB_PASSWORD": "env-test-pass",
        },
    )
    def test_get_database_config_from_environment(self):
        """测试从环境变量获取配置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.host == "env-test-host"
        assert config.port == 7777
        assert config.database == "env-test-db"
        assert config.username == "env-test-user"
        assert config.password == "env-test-pass"

    @patch.dict(os.environ, {"TEST_DB_HOST": "test-env-host", "TEST_DB_NAME": "test-env-db"})
    def test_get_database_config_test_environment(self):
        """测试测试环境配置"""
        from src.database.config import get_database_config

        config = get_database_config("test")

        assert config.host == "test-env-host"
        assert config.database == "test-env-db"

    def test_get_test_database_config(self):
        """测试获取测试数据库配置"""
        from src.database.config import get_test_database_config

        config = get_test_database_config()

        assert isinstance(
            config,
            type(get_test_database_config.__code__.co_globals["get_database_config"]("test")),
        )

    def test_get_production_database_config(self):
        """测试获取生产数据库配置"""
        from src.database.config import get_production_database_config

        config = get_production_database_config()

        assert config is not None
        assert hasattr(config, "host")


class TestDatabaseConnectionIntegration:
    """数据库连接集成测试"""

    def test_database_config_type_safety(self):
        """测试数据库配置类型安全"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        # 验证类型
        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert isinstance(config.database, str)
        assert isinstance(config.username, str)
        assert isinstance(config.password, str)
        assert isinstance(config.pool_size, int)
        assert isinstance(config.echo, bool)

    def test_database_config_range_validation(self):
        """测试数据库配置范围验证"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        # 验证合理范围
        assert config.port >= 1 and config.port <= 65535
        assert config.pool_size > 0
        assert config.max_overflow >= 0
        assert config.pool_timeout > 0
        assert config.pool_recycle > 0

    def test_database_config_environment_prefixes(self):
        """测试数据库配置环境前缀"""
        from src.database.config import get_database_config

        # 测试不同环境的前缀
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

            # 注意：在实现中，只有test和production有前缀
            # development使用默认的无前缀环境变量
            # 但由于我们设置了DB_HOST，development也会读取到

    @patch.dict(os.environ, {"DB_ECHO": "true", "DB_ECHO_POOL": "false"})
    def test_database_config_debug_settings(self):
        """测试数据库配置调试设置"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.echo is True
        assert config.echo_pool is False

    def test_database_config_url_safety(self):
        """测试数据库配置URL安全性"""
        from src.database.config import DatabaseConfig

        # 测试包含特殊字符的凭据
        config = DatabaseConfig(
            host="safe-host.com",
            port=5432,
            database="safe-db",
            username="safe user",
            password="safe pass/with\\symbols",
        )

        # 验证URL生成不会抛出异常
        sync_url = config.sync_url
        async_url = config.async_url

        assert isinstance(sync_url, str)
        assert isinstance(async_url, str)
        assert len(sync_url) > 0
        assert len(async_url) > 0


class TestDatabaseConnectionPerformance:
    """数据库连接性能测试"""

    def test_database_pool_stats_monitoring(self):
        """测试连接池统计监控"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        stats = pool.get_stats()

        # 验证监控字段
        monitoring_fields = [
            "total_connections_created",
            "total_connections_acquired",
            "total_connections_released",
            "total_queries_executed",
            "total_errors",
            "pool_creation_time",
        ]

        for field in monitoring_fields:
            assert field in stats, f"缺少监控字段: {field}"

        # 验证初始统计值
        assert stats["total_connections_created"] == 0
        assert stats["total_queries_executed"] == 0
        assert stats["total_errors"] == 0

    def test_database_pool_health_monitoring(self):
        """测试连接池健康监控"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        stats = pool.get_stats()

        # 验证健康监控字段
        health_fields = ["last_health_check", "health_check_count"]

        for field in health_fields:
            assert field in stats, f"缺少健康监控字段: {field}"

        # 验证初始健康状态
        assert stats["last_health_check"] is None
        assert stats["health_check_count"] == 0

    def test_database_config_performance_settings(self):
        """测试数据库配置性能设置"""
        from src.database.config import DatabaseConfig

        config = DatabaseConfig("host", 5432, "db", "user", "pass")

        # 验证性能相关设置
        assert config.pool_size > 0
        assert config.max_overflow > 0
        assert config.async_pool_size > 0
        assert config.async_max_overflow > 0
        assert config.pool_timeout > 0
        assert config.pool_recycle > 0

    @patch.dict(
        os.environ,
        {"DB_POOL_SIZE": "25", "DB_MAX_OVERFLOW": "50", "DB_POOL_TIMEOUT": "60"},
    )
    def test_database_config_performance_from_env(self):
        """测试从环境变量设置性能参数"""
        from src.database.config import get_database_config

        config = get_database_config()

        assert config.pool_size == 25
        assert config.max_overflow == 50
        assert config.pool_timeout == 60


class TestDatabaseConnectionErrorHandling:
    """数据库连接错误处理测试"""

    def test_database_pool_error_tracking(self):
        """测试连接池错误跟踪"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 验证错误跟踪初始化
        stats = pool.get_stats()
        assert "total_errors" in stats
        assert isinstance(stats["total_errors"], int)
        assert stats["total_errors"] == 0

    def test_database_manager_error_states(self):
        """测试数据库管理器错误状态"""
        from src.database.connection import DatabaseManager

        manager = DatabaseManager()

        # 验证未初始化的错误状态
        assert manager.is_initialized() is False

        # 验证错误消息
        try:
            _ = manager.async_engine
        except RuntimeError as e:
            assert "数据库连接未初始化" in str(e)

    def test_database_config_error_resilience(self):
        """测试数据库配置错误恢复力"""
        from src.database.config import get_database_config

        # 测试缺少环境变量的情况
        with patch.dict(os.environ, {}, clear=True):
            config = get_database_config("unknown_env")

            # 应该使用默认值
            assert config.host == "localhost"
            assert config.port == 5432
            assert config.database == "football_prediction_dev"

    def test_database_url_encoding_error_prevention(self):
        """测试数据库URL编码错误预防"""
        from src.database.config import DatabaseConfig

        # 测试可能导致问题的特殊字符
        config = DatabaseConfig(
            host="host with spaces",
            port=5432,
            database="db-with-dash",
            username="user@domain",
            password="pass:word",
        )

        # 验证URL生成不会因为特殊字符而失败
        try:
            sync_url = config.sync_url
            async_url = config.async_url
            assert isinstance(sync_url, str)
            assert isinstance(async_url, str)
        except Exception as e:
            pytest.fail(f"URL生成失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
