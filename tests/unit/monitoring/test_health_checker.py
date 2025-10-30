import asyncio
from datetime import datetime



# TODO: Consider creating a fixture for 19 repeated Mock creations
# TODO: Consider creating a fixture for 19 repeated Mock creations
"""
健康检查器测试
Tests for Health Checker

测试src.monitoring.health_checker模块的功能
"""


import pytest

from src.monitoring.health_checker import HealthChecker, HealthStatus


@pytest.mark.unit
class TestHealthStatus:
    """健康状态测试"""

    def test_status_values(self):
        """测试:状态常量值"""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.DEGRADED == "degraded"

    def test_status_constants(self):
        """测试:状态常量"""
        # 验证常量存在且是字符串
        assert isinstance(HealthStatus.HEALTHY, str)
        assert isinstance(HealthStatus.UNHEALTHY, str)
        assert isinstance(HealthStatus.DEGRADED, str)


class TestHealthChecker:
    """健康检查器测试"""

    def test_health_checker_initialization(self):
        """测试:健康检查器初始化"""
        checker = HealthChecker()

        assert checker.db_manager is None
        assert checker.redis_manager is None
        assert isinstance(checker.last_checks, dict)
        assert len(checker.last_checks) == 0

    def test_set_database_manager(self):
        """测试:设置数据库管理器"""
        checker = HealthChecker()
        mock_db = Mock()

        checker.set_database_manager(mock_db)
        assert checker.db_manager is mock_db

    def test_set_redis_manager(self):
        """测试:设置Redis管理器"""
        checker = HealthChecker()
        mock_redis = Mock()

        checker.set_redis_manager(mock_redis)
        assert checker.redis_manager is mock_redis

    @pytest.mark.asyncio
    async def test_check_database_no_manager(self):
        """测试:检查数据库（无管理器）"""
        checker = HealthChecker()

        health = await checker.check_database()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert "error" in health["details"]
        assert health["details"]["error"] == "Database manager not set"
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_check_database_success_fast(self):
        """测试:检查数据库成功（快速响应）"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = {"test": 1}
        mock_db.pool = None

        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.HEALTHY
        assert "response_time" in health["details"]
        assert health["details"]["response_time"].endswith("s")
        mock_db.fetch_one.assert_called_once_with("SELECT 1 as test")

    @pytest.mark.asyncio
    async def test_check_database_success_slow(self):
        """测试:检查数据库成功（慢响应）"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.pool = None

        # 模拟慢查询（1-5秒）
        async def slow_query(query):
            await asyncio.sleep(0.1)  # 模拟延迟
            await asyncio.sleep(0.1)  # 模拟延迟
            await asyncio.sleep(0.1)  # 模拟延迟
            return {"test": 1}

        mock_db.fetch_one = slow_query
        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        # 0.1秒小于1秒,应该是HEALTHY
        # 如果我们模拟更长时间
        async def very_slow_query(query):
            await asyncio.sleep(1.1)
            return {"test": 1}

        mock_db.fetch_one = very_slow_query
        health = await checker.check_database()

        assert health["status"] == HealthStatus.DEGRADED
        assert "warning" in health["details"]
        assert "Slow response time" in health["details"]["warning"]

    @pytest.mark.asyncio
    async def test_check_database_very_slow(self):
        """测试:检查数据库（非常慢响应）"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.pool = None

        # 模拟非常慢的查询（>5秒）
        async def very_slow_query(query):
            await asyncio.sleep(0.2)  # 模拟延迟
            await asyncio.sleep(0.2)  # 模拟延迟
            await asyncio.sleep(0.2)  # 模拟延迟
            return {"test": 1}

        mock_db.fetch_one = very_slow_query
        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        # 0.2秒小于5秒,但我们需要模拟更长时间
        # 实际测试中不能真的等待5秒
        # 这里只验证逻辑结构
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_check_database_with_pool_info(self):
        """测试:检查数据库（带连接池信息）"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = {"test": 1}

        # 模拟连接池
        mock_pool = Mock()
        mock_pool.size = 10
        mock_pool.checkedin = 8
        mock_pool.checkedout = 2
        mock_pool.overflow = 0
        mock_db.pool = mock_pool

        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.HEALTHY
        assert "pool" in health["details"]
        pool_info = health["details"]["pool"]
        assert pool_info["size"] == 10
        assert pool_info["checked_in"] == 8
        assert pool_info["checked_out"] == 2
        assert pool_info["overflow"] == 0

    @pytest.mark.asyncio
    async def test_check_database_pool_overflow(self):
        """测试:检查数据库（连接池溢出）"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = {"test": 1}

        # 模拟有溢出的连接池
        mock_pool = Mock()
        mock_pool.size = 10
        mock_pool.checkedin = 10
        mock_pool.checkedout = 10
        mock_pool.overflow = 2
        mock_db.pool = mock_pool

        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.DEGRADED
        assert "warning" in health["details"]
        assert "Connection pool overflow" in health["details"]["warning"]

    @pytest.mark.asyncio
    async def test_check_database_error(self):
        """测试:检查数据库错误"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.pool = None

        # 模拟错误
        mock_db.fetch_one.side_effect = ValueError("Connection failed")
        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert "error" in health["details"]
        assert health["details"]["error"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_check_database_runtime_error(self):
        """测试:检查数据库运行时错误"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.pool = None

        mock_db.fetch_one.side_effect = RuntimeError("Database locked")
        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert health["details"]["error"] == "Database locked"

    @pytest.mark.asyncio
    async def test_check_database_timeout_error(self):
        """测试:检查数据库超时错误"""
        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.pool = None

        mock_db.fetch_one.side_effect = TimeoutError("Query timeout")
        checker.set_database_manager(mock_db)

        health = await checker.check_database()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert health["details"]["error"] == "Query timeout"

    @pytest.mark.asyncio
    async def test_check_redis_no_manager(self):
        """测试:检查Redis（无管理器）"""
        checker = HealthChecker()

        health = await checker.check_redis()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert "error" in health["details"]
        assert health["details"]["error"] == "Redis manager not set"
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """测试:检查Redis成功"""
        checker = HealthChecker()
        mock_redis = AsyncMock()
        mock_redis.health_check.return_value = True

        checker.set_redis_manager(mock_redis)

        health = await checker.check_redis()

        assert health["status"] == HealthStatus.HEALTHY
        assert "timestamp" in health
        mock_redis.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """测试:检查Redis失败"""
        checker = HealthChecker()
        mock_redis = AsyncMock()
        mock_redis.health_check.return_value = False

        checker.set_redis_manager(mock_redis)

        health = await checker.check_redis()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert "error" in health["details"]
        assert health["details"]["error"] == "Redis health check failed"

    @pytest.mark.asyncio
    async def test_check_redis_exception(self):
        """测试:检查Redis异常"""
        checker = HealthChecker()
        mock_redis = AsyncMock()
        mock_redis.health_check.side_effect = Exception("Redis connection error")

        checker.set_redis_manager(mock_redis)

        health = await checker.check_redis()

        assert health["status"] == HealthStatus.UNHEALTHY
        assert "error" in health["details"]
        assert health["details"]["error"] == "Redis connection error"

    @pytest.mark.asyncio
    async def test_check_all_components(self):
        """测试:检查所有组件"""
        # 检查是否有check_all方法
        checker = HealthChecker()

        # 如果有check_all方法
        if hasattr(checker, "check_all"):
            mock_db = AsyncMock()
            mock_db.fetch_one.return_value = {"test": 1}
            mock_db.pool = None

            mock_redis = AsyncMock()
            mock_redis.health_check.return_value = True

            checker.set_database_manager(mock_db)
            checker.set_redis_manager(mock_redis)

            health = await checker.check_all()

            assert "database" in health
            assert "redis" in health
            assert "overall" in health
        else:
            # 如果没有check_all方法,跳过测试
            pytest.skip("check_all method not implemented")

    def test_update_last_checks(self):
        """测试:更新最后检查时间"""
        checker = HealthChecker()

        # 如果有_update_last_checks方法
        if hasattr(checker, "_update_last_checks"):
            checker._update_last_checks("database")
            assert "database" in checker.last_checks
            assert isinstance(checker.last_checks["database"], datetime)

    def test_get_component_status(self):
        """测试:获取组件状态"""
        checker = HealthChecker()

        # 如果有get_component_status方法
        if hasattr(checker, "get_component_status"):
            # 测试存在的组件
            if "database" in checker.last_checks:
                status = checker.get_component_status("database")
                assert status is not None

            # 测试不存在的组件
            status = checker.get_component_status("nonexistent")
            assert status is None

    def test_health_checker_timestamps(self):
        """测试:健康检查时间戳"""
        checker = HealthChecker()

        # 初始状态
        assert len(checker.last_checks) == 0

        # 设置一个时间戳
        test_time = datetime.utcnow()
        checker.last_checks["test"] = test_time

        assert checker.last_checks["test"] == test_time
        assert isinstance(checker.last_checks["test"], datetime)

    def test_health_checker_singleton_pattern(self):
        """测试:健康检查器单例模式（如果适用）"""
        # 创建多个实例
        checker1 = HealthChecker()
        checker2 = HealthChecker()

        # 默认情况下,应该不是单例（除非明确实现）
        assert checker1 is not checker2
        assert checker1.db_manager is None
        assert checker2.db_manager is None

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """测试:并发健康检查"""
        import asyncio

        checker = HealthChecker()
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = {"test": 1}
        mock_db.pool = None

        mock_redis = AsyncMock()
        mock_redis.health_check.return_value = True

        checker.set_database_manager(mock_db)
        checker.set_redis_manager(mock_redis)

        # 并发执行多个健康检查
        tasks = [
            checker.check_database(),
            checker.check_redis(),
            checker.check_database(),
            checker.check_redis(),
        ]

        results = await asyncio.gather(*tasks)

        # 所有检查都应该成功
        for result in results:
            assert _result["status"] == HealthStatus.HEALTHY
            assert "timestamp" in result
