"""
数据库连接池扩展测试
基于实际API的全面测试，专注于连接池管理功能
"""

import pytest
import asyncio
import time
import os
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import asyncpg
from urllib.parse import urlparse


class TestDatabasePoolConfig:
    """数据库连接池配置测试"""

    def test_database_pool_config_creation(self):
        """测试数据库连接池配置创建"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb",
            min_size=5,
            max_size=20,
            timeout=60.0,
            command_timeout=30.0,
        )

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.database == "testdb"
        assert config.min_size == 5
        assert config.max_size == 20
        assert config.timeout == 60.0
        assert config.command_timeout == 30.0

    def test_database_pool_config_from_env(self):
        """测试从环境变量加载连接池配置"""
        from src.database.db_pool import DatabasePoolConfig

        with patch.dict(
            os.environ,
            {
                "DB_HOST": "envhost",
                "DB_PORT": "9999",
                "DB_USER": "envuser",
                "DB_PASSWORD": "envpass",
                "DB_DATABASE": "envdb",
                "DB_POOL_MIN_SIZE": "10",
                "DB_POOL_MAX_SIZE": "50",
                "DB_TIMEOUT": "120.0",
                "DB_COMMAND_TIMEOUT": "60.0",
                "DB_HEALTH_CHECK_INTERVAL": "45.0",
                "DB_MAX_RETRIES": "5",
            },
        ):
            config = DatabasePoolConfig()

            assert config.host == "envhost"
            assert config.port == 9999
            assert config.user == "envuser"
            assert config.password == "envpass"
            assert config.database == "envdb"
            assert config.min_size == 10
            assert config.max_size == 50
            assert config.timeout == 120.0
            assert config.command_timeout == 60.0
            assert config.health_check_interval == 45.0
            assert config.max_retries == 5

    def test_database_pool_config_from_url(self):
        """测试从数据库URL创建配置"""
        from src.database.db_pool import DatabasePoolConfig

        # 测试完整URL解析
        url = "postgresql://user:pass@host:1234/database"
        config = DatabasePoolConfig.from_url(url)

        assert config.host == "host"
        assert config.port == 1234
        assert config.user == "user"
        assert config.password == "pass"
        assert config.database == "database"

    def test_database_pool_config_from_url_with_default(self):
        """测试从默认URL创建配置"""
        from src.database.db_pool import DatabasePoolConfig

        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://defaultuser:defaultpass@defaulthost:5433/defaultdb"
            },
        ):
            config = DatabasePoolConfig.from_url()

            assert config.host == "defaulthost"
            assert config.port == 5433
            assert config.user == "defaultuser"
            assert config.password == "defaultpass"
            assert config.database == "defaultdb"

    def test_database_pool_config_url_edge_cases(self):
        """测试URL解析边界情况"""
        from src.database.db_pool import DatabasePoolConfig

        # 测试缺少端口的URL
        url = "postgresql://user:pass@host/database"
        config = DatabasePoolConfig.from_url(url)

        assert config.host == "host"
        assert config.port == 5432  # 默认端口

        # 测试缺少用户名的URL
        url = "postgresql://:pass@host/database"
        config = DatabasePoolConfig.from_url(url)

        assert config.user == "postgres"  # 默认用户名

        # 测试空数据库名的URL
        url = "postgresql://user:pass@host/"
        config = DatabasePoolConfig.from_url(url)

        assert config.database == "football_prediction"  # 默认数据库

    def test_database_pool_config_field_defaults(self):
        """测试配置字段默认值"""
        from src.database.db_pool import DatabasePoolConfig

        config = DatabasePoolConfig()

        # 验证所有默认值
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.user == "postgres"
        assert config.password == "postgres"
        assert config.database == "football_prediction"
        assert config.min_size == 5
        assert config.max_size == 20
        assert config.max_queries == 50000
        assert config.max_inactive_connection_lifetime == 300.0
        assert config.timeout == 60.0
        assert config.command_timeout == 30.0
        assert config.health_check_interval == 30.0
        assert config.health_check_timeout == 5.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0


class TestDatabasePoolSingleton:
    """数据库连接池单例测试"""

    @pytest.mark.asyncio
    async def test_database_pool_singleton_pattern(self):
        """测试数据库连接池单例模式"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config1 = DatabasePoolConfig(host="test1")
        config2 = DatabasePoolConfig(host="test2")

        # 第一次创建实例
        pool1 = await DatabasePool.get_instance(config1)

        # 第二次获取实例（应该返回同一个）
        pool2 = await DatabasePool.get_instance(config2)

        assert pool1 is pool2
        assert pool1.config.host == "test1"  # 配置应该是第一次的

    @pytest.mark.asyncio
    async def test_database_pool_singleton_thread_safety(self):
        """测试数据库连接池单例线程安全"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig(host="threadtest")

        # 并发获取单例实例
        tasks = [DatabasePool.get_instance(config) for _ in range(10)]
        pools = await asyncio.gather(*tasks)

        # 所有任务应该获得同一个实例
        assert len(set(pools)) == 1
        assert all(pool.config.host == "threadtest" for pool in pools)


class TestDatabasePoolOperations:
    """数据库连接池操作测试"""

    @pytest.mark.asyncio
    async def test_database_pool_initialization(self):
        """测试数据库连接池初始化"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig(
            host="localhost",
            port=5432,
            user="test",
            password="test",
            database="test",
            min_size=5,
            max_size=20,
        )

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.size = 5
            mock_pool.min_size = 5
            mock_pool.max_size = 20
            mock_create_pool.return_value = mock_pool

            pool = DatabasePool(config)

            # 测试初始化
            await pool.init_pool()

            # 验证初始化状态
            assert pool._is_initialized is True
            assert pool._pool == mock_pool

            # 验证统计信息
            assert pool._stats["pool_creation_time"] is not None

            # 验证asyncpg.create_pool调用
            mock_create_pool.assert_called_once()
            call_args = mock_create_pool.call_args
            assert call_args[1]["min_size"] == 5
            assert call_args[1]["max_size"] == 20

    @pytest.mark.asyncio
    async def test_database_pool_double_initialization(self):
        """测试数据库连接池重复初始化"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # 第一次初始化
            await pool.init_pool()
            assert pool._is_initialized is True

            # 第二次初始化应该被跳过
            await pool.init_pool()

            # 只应该调用一次create_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_pool_initialization_failure(self):
        """测试数据库连接池初始化失败"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncpg

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_create_pool.side_effect = asyncpg.PostgresError("Connection failed")

            with pytest.raises(asyncpg.PostgresError):
                await pool.init_pool()

            # 初始化失败后状态应该保持为未初始化
            assert pool._is_initialized is False

    @pytest.mark.asyncio
    async def test_database_pool_acquire_connection(self):
        """测试数据库连接获取"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试连接获取
            conn = await pool.acquire()

            assert conn == mock_conn
            assert pool._stats["total_connections_acquired"] == 1
            mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_pool_release_connection(self):
        """测试数据库连接释放"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 模拟连接获取和释放
            await pool.release(mock_conn)

            assert pool._stats["total_connections_released"] == 1

    @pytest.mark.asyncio
    async def test_database_pool_execute_query(self):
        """测试数据库查询执行"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = "INSERT 1"
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试查询执行
            result = await pool.execute("INSERT INTO test VALUES (1)", 1)

            assert result == "INSERT 1"
            assert pool._stats["total_queries_executed"] == 1
            mock_conn.execute.assert_called_once_with("INSERT INTO test VALUES (1)", 1)

    @pytest.mark.asyncio
    async def test_database_pool_fetch_query(self):
        """测试数据库查询获取"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [
                {"id": 1, "name": "test1"},
                {"id": 2, "name": "test2"},
            ]
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试查询获取
            results = await pool.fetch("SELECT * FROM test WHERE id = $1", 1)

            assert len(results) == 2
            assert results[0]["id"] == 1
            assert results[1]["name"] == "test2"
            assert pool._stats["total_queries_executed"] == 1
            mock_conn.fetch.assert_called_once_with(
                "SELECT * FROM test WHERE id = $1", 1
            )

    @pytest.mark.asyncio
    async def test_database_pool_fetchrow_query(self):
        """测试数据库单行查询获取"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchrow.return_value = {"id": 1, "name": "test"}
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试单行查询
            result = await pool.fetchrow("SELECT * FROM test WHERE id = $1", 1)

            assert result["id"] == 1
            assert result["name"] == "test"
            assert pool._stats["total_queries_executed"] == 1
            mock_conn.fetchrow.assert_called_once_with(
                "SELECT * FROM test WHERE id = $1", 1
            )

    @pytest.mark.asyncio
    async def test_database_pool_fetchval_query(self):
        """测试数据库单值查询获取"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 42
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试单值查询
            result = await pool.fetchval("SELECT COUNT(*) FROM test")

            assert result == 42
            assert pool._stats["total_queries_executed"] == 1
            mock_conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")

    @pytest.mark.asyncio
    async def test_database_pool_connection_context_manager(self):
        """测试数据库连接上下文管理器"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试上下文管理器
            async with pool.acquire() as conn:
                assert conn == mock_conn

            # 验证连接获取和释放统计
            assert pool._stats["total_connections_acquired"] == 1
            mock_pool.acquire.assert_called_once()


class TestDatabasePoolHealth:
    """数据库连接池健康检查测试"""

    @pytest.mark.asyncio
    async def test_database_pool_health_check(self):
        """测试数据库连接池健康检查"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig(health_check_interval=1.0)
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = True
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试健康检查
            health = await pool.check_health()

            assert health["status"] == "healthy"
            assert "timestamp" in health
            assert pool._stats["health_check_count"] >= 1

    @pytest.mark.asyncio
    async def test_database_pool_health_check_failure(self):
        """测试数据库连接池健康检查失败"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig
        import asyncpg

        config = DatabasePoolConfig(health_check_interval=1.0)
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval.side_effect = asyncpg.PostgresError("Connection lost")
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 测试健康检查失败
            health = await pool.check_health()

            assert health["status"] == "unhealthy"
            assert "error" in health

    @pytest.mark.asyncio
    async def test_database_pool_close(self):
        """测试数据库连接池关闭"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()
            await pool.close()

            # 验证关闭操作
            assert pool._is_initialized is False
            mock_pool.close.assert_called_once()


class TestDatabasePoolStats:
    """数据库连接池统计测试"""

    @pytest.mark.asyncio
    async def test_database_pool_get_stats(self):
        """测试数据库连接池统计信息"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.size = 10
            mock_pool.min_size = 5
            mock_pool.max_size = 20
            mock_create_pool.return_value = mock_pool

            await pool.init_pool()

            # 模拟一些操作
            await pool.execute("SELECT 1")
            await pool.fetch("SELECT 1")

            # 获取统计信息
            stats = pool.get_stats()

            assert "total_connections_created" in stats
            assert "total_connections_acquired" in stats
            assert "total_queries_executed" in stats
            assert "pool_creation_time" in stats
            assert "health_check_count" in stats
            assert stats["total_queries_executed"] >= 2

    def test_database_pool_reset_stats(self):
        """测试数据库连接池统计信息重置"""
        from src.database.db_pool import DatabasePool, DatabasePoolConfig

        config = DatabasePoolConfig()
        pool = DatabasePool(config)

        # 模拟一些统计数据
        pool._stats["total_connections_acquired"] = 10
        pool._stats["total_queries_executed"] = 20

        # 重置统计信息
        pool.reset_stats()

        # 验证统计信息被重置（保留某些字段）
        assert pool._stats["total_connections_acquired"] == 0
        assert pool._stats["total_queries_executed"] == 0
        assert pool._stats["total_errors"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
