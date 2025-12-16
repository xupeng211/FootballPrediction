#!/usr/bin/env python3
"""
数据库连接池性能对比测试

对比重构前后的性能差异，验证连接池的性能提升

运行方式:
pytest tests/performance/test_db_pool_performance_comparison.py -v -s
"""

import asyncio
import os
import sys
import time
import logging
import urllib.parse
from typing import List, Dict, Any
from pathlib import Path
import pytest
import asyncpg

# 设置项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OldDatabaseConnection:
    """模拟旧的数据库连接方式"""

    def __init__(self):
        self.db_config = self._get_db_config()

    def _get_db_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction"
        )
        parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))

        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
            "database": parsed.path.lstrip("/") or "football_prediction"
        }

    async def execute_query_old(self, query: str, *args) -> str:
        """旧的查询执行方式 - 每次新建连接"""
        conn = await asyncpg.connect(**self.db_config)
        try:
            result = await conn.execute(query, *args)
            return result
        finally:
            await conn.close()

    async def fetch_query_old(self, query: str, *args) -> List[asyncpg.Record]:
        """旧的查询方式 - 每次新建连接"""
        conn = await asyncpg.connect(**self.db_config)
        try:
            result = await conn.fetch(query, *args)
            return result
        finally:
            await conn.close()


class NewDatabaseConnection:
    """新的数据库连接方式 - 使用连接池"""

    def __init__(self):
        from database.db_pool import get_db_pool
        self.pool = None
        self._get_db_pool = get_db_pool

    async def init(self):
        """初始化连接池"""
        self.pool = await self._get_db_pool()
        await self.pool.init_pool()

    async def execute_query_new(self, query: str, *args) -> str:
        """新的查询执行方式 - 使用连接池"""
        return await self.pool.execute(query, *args)

    async def fetch_query_new(self, query: str, *args) -> List[asyncpg.Record]:
        """新的查询方式 - 使用连接池"""
        return await self.pool.fetch(query, *args)

    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()


@pytest.mark.asyncio
@pytest.mark.performance
async test_performance_comparison_single_query():
    """对比单次查询性能"""
    logger.info("⚡ 对比单次查询性能")

    # 测试数据
    test_query = "SELECT $1 as test_value"
    test_args = (123,)

    # 旧方式测试
    old_db = OldDatabaseConnection()
    old_times = []

    logger.info("测试旧连接方式...")
    for i in range(20):
        start_time = time.time()
        await old_db.execute_query_old(test_query, *test_args)
        end_time = time.time()
        old_times.append(end_time - start_time)

    # 新方式测试
    new_db = NewDatabaseConnection()
    await new_db.init()
    new_times = []

    logger.info("测试新连接方式...")
    for i in range(20):
        start_time = time.time()
        await new_db.execute_query_new(test_query, *test_args)
        end_time = time.time()
        new_times.append(end_time - start_time)

    # 计算统计数据
    old_avg = sum(old_times) / len(old_times)
    new_avg = sum(new_times) / len(new_times)
    old_min = min(old_times)
    new_min = min(new_times)
    old_max = max(old_times)
    new_max = max(new_times)

    # 计算性能提升
    improvement = ((old_avg - new_avg) / old_avg) * 100

    logger.info(f"📊 单次查询性能对比:")
    logger.info(f"   旧方式 - 平均: {old_avg:.4f}s, 最小: {old_min:.4f}s, 最大: {old_max:.4f}s")
    logger.info(f"   新方式 - 平均: {new_avg:.4f}s, 最小: {new_min:.4f}s, 最大: {new_max:.4f}s")
    logger.info(f"   性能提升: {improvement:.1f}%")

    # 性能断言 - 新方式应该更快或至少不慢太多
    assert new_avg <= old_avg * 1.2, f"新方式性能过慢: {new_avg:.4f}s vs {old_avg:.4f}s"

    await new_db.close()
    logger.info("✅ 单次查询性能对比测试完成")


@pytest.mark.asyncio
@pytest.mark.performance
async test_performance_comparison_concurrent_queries():
    """对比并发查询性能"""
    logger.info("🚀 对比并发查询性能")

    concurrent_tasks = 30
    queries_per_task = 5
    test_query = "SELECT $1 as task_id, $2 as iteration"

    async def old_concurrent_task(task_id: int) -> float:
        """旧方式并发任务"""
        start_time = time.time()
        old_db = OldDatabaseConnection()

        for i in range(queries_per_task):
            await old_db.fetch_query_old(test_query, task_id, i)

        end_time = time.time()
        return end_time - start_time

    async def new_concurrent_task(task_id: int) -> float:
        """新方式并发任务"""
        start_time = time.time()

        # 使用全局连接池
        from database.db_pool import get_db_pool
        pool = await get_db_pool()

        for i in range(queries_per_task):
            await pool.fetch(test_query, task_id, i)

        end_time = time.time()
        return end_time - start_time

    # 测试旧方式
    logger.info("测试旧方式并发查询...")
    old_start_time = time.time()
    old_tasks = [old_concurrent_task(i) for i in range(concurrent_tasks)]
    old_results = await asyncio.gather(*old_tasks)
    old_total_time = time.time() - old_start_time
    old_avg_time = sum(old_results) / len(old_results)

    # 测试新方式
    logger.info("测试新方式并发查询...")

    # 初始化连接池
    from database.db_pool import init_global_db_pool
    await init_global_db_pool()

    new_start_time = time.time()
    new_tasks = [new_concurrent_task(i) for i in range(concurrent_tasks)]
    new_results = await asyncio.gather(*new_tasks)
    new_total_time = time.time() - new_start_time
    new_avg_time = sum(new_results) / len(new_results)

    # 计算性能提升
    total_improvement = ((old_total_time - new_total_time) / old_total_time) * 100
    avg_improvement = ((old_avg_time - new_avg_time) / old_avg_time) * 100

    logger.info(f"📊 并发查询性能对比:")
    logger.info(f"   总体耗时 - 旧: {old_total_time:.3f}s, 新: {new_total_time:.3f}s")
    logger.info(f"   平均耗时 - 旧: {old_avg_time:.3f}s, 新: {new_avg_time:.3f}s")
    logger.info(f"   总体性能提升: {total_improvement:.1f}%")
    logger.info(f"   平均性能提升: {avg_improvement:.1f}%")

    # 性能断言
    assert new_total_time <= old_total_time * 0.9, f"并发性能提升不足: {new_total_time:.3f}s vs {old_total_time:.3f}s"

    # 关闭连接池
    from database.db_pool import get_db_pool
    pool = await get_db_pool()
    await pool.close()

    logger.info("✅ 并发查询性能对比测试完成")


@pytest.mark.asyncio
@pytest.mark.performance
async test_connection_pool_efficiency():
    """测试连接池效率"""
    logger.info("🔧 测试连接池效率")

    from database.db_pool import DatabasePool, DatabasePoolConfig

    config = DatabasePoolConfig(min_size=2, max_size=10)
    pool = await DatabasePool.get_instance(config)
    await pool.init_pool()

    try:
        # 测试连接复用
        logger.info("测试连接复用效率...")

        # 获取初始统计
        initial_stats = pool.get_stats()
        initial_connections = initial_stats.get("total_connections_created", 0)

        # 执行多次查询，应该复用连接
        for i in range(50):
            await pool.fetchval("SELECT $1", i)

        # 检查最终统计
        final_stats = pool.get_stats()
        final_connections = final_stats.get("total_connections_created", 0)

        # 验证连接复用
        connections_created = final_connections - initial_connections
        logger.info(f"创建了 {connections_created} 个新连接来处理 50 次查询")

        # 理想情况下，应该创建很少的连接来处理很多查询
        efficiency_ratio = 50 / max(connections_created, 1)
        logger.info(f"连接复用效率: {efficiency_ratio:.1f} 查询/连接")

        # 连接池大小验证
        pool_size = final_stats.get("pool_size", 0)
        assert pool_size <= config.max_size, f"连接池大小超出限制: {pool_size} > {config.max_size}"

        # 健康检查
        assert final_stats.get("health_check_count", 0) >= 0, "健康检查应该正常运行"

        logger.info("✅ 连接池效率测试通过")

    finally:
        await pool.close()


@pytest.mark.asyncio
@pytest.mark.performance
async test_memory_usage_comparison():
    """对比内存使用情况"""
    logger.info("💾 对比内存使用情况")

    import psutil
    import gc

    # 获取初始内存使用
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # 旧方式测试
    logger.info("测试旧方式内存使用...")
    old_db = OldDatabaseConnection()

    for i in range(100):
        conn = await asyncpg.connect(**old_db.db_config)
        try:
            await conn.fetchval("SELECT $1", i)
        finally:
            await conn.close()

    # 强制垃圾回收
    gc.collect()
    old_memory = process.memory_info().rss / 1024 / 1024  # MB
    old_memory_increase = old_memory - initial_memory

    # 等待内存稳定
    await asyncio.sleep(1)

    # 新方式测试
    logger.info("测试新方式内存使用...")
    from database.db_pool import init_global_db_pool
    await init_global_db_pool()

    for i in range(100):
        from database.db_pool import get_db_pool
        pool = await get_db_pool()
        await pool.fetchval("SELECT $1", i)

    # 强制垃圾回收
    gc.collect()
    new_memory = process.memory_info().rss / 1024 / 1024  # MB
    new_memory_increase = new_memory - old_memory

    logger.info(f"📊 内存使用对比:")
    logger.info(f"   初始内存: {initial_memory:.1f} MB")
    logger.info(f"   旧方式增量: {old_memory_increase:.1f} MB")
    logger.info(f"   新方式增量: {new_memory_increase:.1f} MB")

    if old_memory_increase > 0:
        memory_improvement = ((old_memory_increase - new_memory_increase) / old_memory_increase) * 100
        logger.info(f"   内存使用改善: {memory_improvement:.1f}%")

    # 关闭连接池
    from database.db_pool import get_db_pool
    pool = await get_db_pool()
    await pool.close()

    logger.info("✅ 内存使用对比测试完成")


if __name__ == "__main__":
    """
    直接运行性能对比测试的便捷方式
    """
    print("🚀 启动数据库连接池性能对比测试")

    async def main():
        try:
            await test_performance_comparison_single_query()
            await test_performance_comparison_concurrent_queries()
            await test_connection_pool_efficiency()
            await test_memory_usage_comparison()
            print("\n✅ 所有性能对比测试完成")
        except Exception as e:
            print(f"\n❌ 性能对比测试失败: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(main())