"""
测试数据库子系统
"""

import pytest

from src.facades.subsystems.database import DatabaseSubsystem


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseSubsystem:
    """测试数据库子系统"""

    @pytest.fixture
    async def subsystem(self):
        """创建子系统实例"""
        sub = DatabaseSubsystem()
        await sub.initialize()
        yield sub
        await sub.shutdown()

    async def test_initialization(self, subsystem):
        """测试初始化"""
        assert subsystem.name == "database"
        assert subsystem.version == "2.0.0"
        assert subsystem.connection_pool is not None
        assert subsystem.query_count == 0

    async def test_execute_query(self, subsystem):
        """测试执行查询"""
        _result = await subsystem.execute_query("SELECT * FROM test", {"id": 1})
        assert _result["query"] == "SELECT * FROM test"
        assert _result["params"] == {"id": 1}
        assert _result["result"] == "success"
        assert subsystem.query_count == 1

    async def test_execute_query_without_params(self, subsystem):
        """测试无参数查询"""
        _result = await subsystem.execute_query("SELECT NOW()")
        assert _result["query"] == "SELECT NOW()"
        assert _result["params"] is None
        assert subsystem.query_count == 1

    async def test_health_check(self, subsystem):
        """测试健康检查"""
        health = await subsystem.health_check()
        assert "status" in health
        assert "connection_pool" in health
        assert "query_count" in health
        assert health["connection_pool"] is True
        assert health["query_count"] == 0

    async def test_shutdown(self):
        """测试关闭"""
        sub = DatabaseSubsystem()
        await sub.initialize()
        assert sub.connection_pool is not None

        await sub.shutdown()
        assert sub.connection_pool is None

    async def test_execute_query_on_inactive_subsystem(self):
        """测试在未激活的子系统上执行查询"""
        sub = DatabaseSubsystem()
        # 不初始化,直接执行查询
        with pytest.raises(RuntimeError, match="Database subsystem is not active"):
            await sub.execute_query("SELECT 1")
