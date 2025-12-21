"""
数据库连接池优化测试
第二层优化：专注数据库连接池模块 (52% → 80%)
基于实际数据库连接池结构的测试，确保高价值覆盖
"""

import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, Mock, MagicMock
from contextlib import asynccontextmanager


class TestDatabasePoolConfigCore:
    """数据库连接池配置核心测试"""

    def test_database_pool_config_default_values(self):
        """测试数据库连接池配置默认值"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        # 验证基本连接配置
        assert hasattr(config, "host")
        assert hasattr(config, "port")
        assert hasattr(config, "user")
        assert hasattr(config, "password")
        assert hasattr(config, "database")

        # 验证连接池配置
        assert hasattr(config, "min_size")
        assert hasattr(config, "max_size")
        assert hasattr(config, "timeout")
        assert hasattr(config, "command_timeout")

        # 验证默认值在合理范围内
        assert 1 <= config.min_size <= 100
        assert 1 <= config.max_size <= 1000
        assert config.max_size >= config.min_size
        assert config.timeout > 0
        assert config.command_timeout > 0

    @patch.dict(
        "os.environ",
        {
            "DB_HOST": "test-host",
            "DB_PORT": "5433",
            "DB_USER": "test-user",
            "DB_PASSWORD": "test-pass",
            "DB_NAME": "test-db",
            "DB_POOL_MIN_SIZE": "10",
            "DB_POOL_MAX_SIZE": "50",
        },
    )
    def test_database_pool_config_from_environment(self):
        """测试从环境变量加载配置"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        assert config.host == "test-host"
        assert config.port == 5433
        assert config.user == "test-user"
        assert config.password == "test-pass"
        assert config.database == "test-db"
        assert config.min_size == 10
        assert config.max_size == 50

    def test_database_pool_config_from_url(self):
        """测试从URL创建配置"""
        from src.database.db_pool import DatabasePoolConfig

        # 测试完整URL解析
        test_url = "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
        config = DatabasePoolConfig.from_url(test_url)

        assert config.host == "localhost"
        assert config.port == 5433
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.database == "testdb"

    def test_database_pool_config_validation(self):
        """测试配置验证"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        # 验证健康检查配置
        assert hasattr(config, "health_check_interval")
        assert hasattr(config, "health_check_timeout")
        assert config.health_check_interval > 0
        assert config.health_check_timeout > 0

        # 验证重连配置
        assert hasattr(config, "max_retries")
        assert hasattr(config, "retry_delay")
        assert config.max_retries >= 0
        assert config.retry_delay >= 0


class TestDatabasePoolCore:
    """数据库连接池核心功能测试"""

    def test_database_pool_initialization(self):
        """测试数据库连接池初始化"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        assert pool.config == config
        assert pool._pool is None
        assert pool._is_initialized is False
        assert hasattr(pool, "_stats")

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_init_pool_success(self, mock_create_pool):
        """测试连接池初始化成功"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        # Mock asyncpg连接池
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        await pool.init_pool()

        assert pool._is_initialized is True
        assert pool._pool == mock_pool
        mock_create_pool.assert_called_once()

        # 验证统计信息
        stats = pool.get_stats()
        assert "pool_creation_time" in stats
        assert stats["pool_creation_time"] > 0

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_init_pool_already_initialized(self, mock_create_pool):
        """测试连接池重复初始化"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 第一次初始化
        await pool.init_pool()
        first_call_count = mock_create_pool.call_count

        # 第二次初始化应该跳过
        await pool.init_pool()

        assert mock_create_pool.call_count == first_call_count

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_connection_context_manager(self, mock_create_pool):
        """测试连接上下文管理器"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        # 测试连接上下文管理器
        async with pool.connection() as conn:
            assert conn == mock_conn

        # 验证acquire被调用
        mock_pool.acquire.assert_called()

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_execute_query(self, mock_create_pool):
        """测试执行查询"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "INSERT 0 1"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        result = await pool.execute("INSERT INTO test VALUES (1)")

        assert result == "INSERT 0 1"
        mock_conn.execute.assert_called_once_with("INSERT INTO test VALUES (1)")

        # 验证统计信息
        stats = pool.get_stats()
        assert stats["total_queries_executed"] == 1

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_fetch_query(self, mock_create_pool):
        """测试查询获取数据"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_records = [Mock(id=1), Mock(id=2)]
        mock_conn.fetch.return_value = mock_records
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        result = await pool.fetch("SELECT * FROM test")

        assert result == mock_records
        mock_conn.fetch.assert_called_once_with("SELECT * FROM test")

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_fetchrow_query(self, mock_create_pool):
        """测试查询单行数据"""
        from src.database.db_pool import DatabasePoolConfig, DatabasePool

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_record = Mock(id=1, name="test")
        mock_conn.fetchrow.return_value = mock_record
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        result = await pool.fetchrow("SELECT * FROM test WHERE id = 1")

        assert result == mock_record
        mock_conn.fetchrow.assert_called_once_with("SELECT * FROM test WHERE id = 1")

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_fetchval_query(self, mock_create_pool):
        """测试查询单个值"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 42
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        result = await pool.fetchval("SELECT COUNT(*) FROM test")

        assert result == 42
        mock_conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_executemany(self, mock_create_pool):
        """测试批量执行"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.executemany.return_value = "INSERT 0 3"
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        args_list = [(1,), (2,), (3,)]
        result = await pool.executemany("INSERT INTO test VALUES ($1)", args_list)

        assert result == "INSERT 0 3"
        mock_conn.executemany.assert_called_once_with("INSERT INTO test VALUES ($1)", args_list)

        # 验证统计信息
        stats = pool.get_stats()
        assert stats["total_queries_executed"] == 3  # 批量查询算作3个


class TestDatabasePoolErrorHandling:
    """数据库连接池错误处理测试"""

    async def test_database_pool_not_initialized_error(self):
        """测试未初始化错误"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 尝试在未初始化时使用连接池
        with pytest.raises(RuntimeError, match="连接池未初始化"):
            async with pool.connection():
                pass

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_connection_error_handling(self, mock_create_pool):
        """测试连接错误处理"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncpg

        # 模拟连接错误
        mock_create_pool.side_effect = asyncpg.PostgresError("Connection failed")

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with pytest.raises(asyncpg.PostgresError):
            await pool.init_pool()

        assert pool._is_initialized is False

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_query_error_handling(self, mock_create_pool):
        """测试查询错误处理"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncpg

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = asyncpg.PostgresError("Query failed")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        with pytest.raises(asyncpg.PostgresError):
            await pool.execute("INVALID SQL")

        # 验证错误统计
        stats = pool.get_stats()
        assert stats["total_errors"] == 1

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_query_timeout(self, mock_create_pool):
        """测试查询超时"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncio

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        # 模拟超时
        mock_conn.execute.side_effect = asyncio.TimeoutError("Query timeout")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        with pytest.raises(asyncio.TimeoutError):
            await pool.execute("SELECT * FROM large_table", timeout=0.1)


class TestDatabasePoolPerformance:
    """数据库连接池性能测试"""

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_concurrent_connections(self, mock_create_pool):
        """测试并发连接"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [Mock(id=1)]

        # 创建多个模拟连接
        async def mock_acquire():
            return mock_conn

        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        # 并发执行多个查询
        tasks = [pool.fetch("SELECT * FROM test") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert result == [Mock(id=1)]

        # 验证连接统计
        stats = pool.get_stats()
        assert stats["total_connections_acquired"] == 10
        assert stats["total_connections_released"] == 10

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_performance_stats(self, mock_create_pool):
        """测试性能统计"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.get_size.return_value = 5
        mock_pool.get_min_size.return_value = 2
        mock_pool.get_max_size.return_value = 20
        mock_pool.get_idle_size.return_value = 3
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)
        await pool.init_pool()

        # 执行一些查询
        await pool.fetch("SELECT * FROM test")
        await pool.execute("INSERT INTO test VALUES (1)")

        stats = pool.get_stats()

        # 验证查询统计
        assert stats["total_queries_executed"] == 2
        assert stats["total_connections_acquired"] == 2
        assert stats["total_connections_released"] == 2

        # 验证连接池统计
        assert "pool_size" in stats
        assert stats["pool_size"] == 5
        assert stats["pool_idle_connections"] == 3

    def test_database_pool_get_pool_info(self):
        """测试获取连接池信息"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        config.host = "test-host"
        config.port = 5433
        config.database = "test-db"
        config.min_size = 5
        config.max_size = 20

        pool = DatabasePool(config)

        info = pool.get_pool_info()

        # 验证基本信息
        assert info["is_initialized"] is False
        assert "config" in info
        assert "stats" in info

        # 验证配置信息
        assert info["config"]["host"] == "test-host"
        assert info["config"]["port"] == 5433
        assert info["config"]["database"] == "test-db"
        assert info["config"]["min_size"] == 5
        assert info["config"]["max_size"] == 20

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_async_context_manager(self, mock_create_pool):
        """测试异步上下文管理器"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 测试异步上下文管理器
        async with pool as p:
            assert p == pool
            assert p._is_initialized is True

        # 验证关闭被调用
        mock_pool.close.assert_called_once()


class TestDatabasePoolHealthCheck:
    """数据库连接池健康检查测试"""

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_health_check_success(self, mock_create_pool):
        """测试健康检查成功"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        config.health_check_interval = 0.1  # 快速健康检查
        pool = DatabasePool(config)
        await pool.init_pool()

        # 等待健康检查执行
        await asyncio.sleep(0.2)

        # 验证健康检查统计
        stats = pool.get_stats()
        assert "last_health_check" in stats
        assert "health_check_count" in stats
        assert stats["health_check_count"] > 0

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_health_check_failure(self, mock_create_pool):
        """测试健康检查失败"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncpg

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = asyncpg.PostgresError("Health check failed")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        config = DatabasePoolConfig()
        config.health_check_interval = 0.1
        pool = DatabasePool(config)
        await pool.init_pool()

        # 等待健康检查执行
        await asyncio.sleep(0.2)

        # 健康检查失败不应该停止池的工作
        assert pool._is_initialized is True


class TestDatabasePoolSingleton:
    """数据库连接池单例测试"""

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_singleton_instance(self, mock_create_pool):
        """测试单例模式"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_create_pool.return_value = AsyncMock()

        # 获取两个实例
        pool1 = await DatabasePool.get_instance()
        pool2 = await DatabasePool.get_instance()

        # 验证是同一个实例
        assert pool1 is pool2

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_database_pool_singleton_config_only_first(self, mock_create_pool):
        """测试单例只在首次使用配置"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        mock_create_pool.return_value = AsyncMock()

        config1 = DatabasePoolConfig()
        config1.host = "host1"

        config2 = DatabasePoolConfig()
        config2.host = "host2"

        # 第一次获取使用配置
        pool1 = await DatabasePool.get_instance(config1)
        assert pool1.config.host == "host1"

        # 第二次获取应该忽略配置，使用同一个实例
        pool2 = await DatabasePool.get_instance(config2)
        assert pool2 is pool1
        assert pool2.config.host == "host1"  # 仍然是第一次的配置


class TestDatabasePoolGlobalFunctions:
    """数据库连接池全局函数测试"""

    @patch("src.database.db_pool.DatabasePool.get_instance")
    async def test_get_db_pool_function(self, mock_get_instance):
        """测试全局get_db_pool函数"""
        from src.database.db_pool import get_db_pool, DatabasePool

        mock_pool = AsyncMock(spec=DatabasePool)
        mock_instance = AsyncMock()
        mock_instance.get_instance.return_value = mock_pool
        mock_get_instance.return_value = mock_instance

        result = await get_db_pool()

        assert result == mock_pool
        mock_get_instance.assert_called_once()

    @patch("src.database.db_pool.asyncpg.create_pool")
    async def test_convenience_functions(self, mock_create_pool):
        """测试便捷函数"""
        from src.database.db_pool import (
            execute_query,
            fetch_query,
            fetchrow_query,
            fetchval_query,
            DatabasePoolConfig,
        )

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock各种查询方法
        mock_conn.execute.return_value = "EXECUTED"
        mock_conn.fetch.return_value = [{"id": 1}]
        mock_conn.fetchrow.return_value = {"id": 1}
        mock_conn.fetchval.return_value = 42

        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        # 初始化全局池
        from src.database.db_pool import init_global_db_pool

        await init_global_db_pool(DatabasePoolConfig())

        # 测试便捷函数
        result1 = await execute_query("INSERT INTO test VALUES (1)")
        assert result1 == "EXECUTED"

        result2 = await fetch_query("SELECT * FROM test")
        assert result2 == [{"id": 1}]

        result3 = await fetchrow_query("SELECT * FROM test LIMIT 1")
        assert result3 == {"id": 1}

        result4 = await fetchval_query("SELECT COUNT(*) FROM test")
        assert result4 == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
