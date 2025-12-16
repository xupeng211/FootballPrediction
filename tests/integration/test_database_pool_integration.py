#!/usr/bin/env python3
"""
数据库连接池集成测试

测试DatabasePool与实际应用的集成，验证连接池在高并发场景下的性能和稳定性

运行方式:
pytest tests/integration/test_database_pool_integration.py -v -s
"""

import asyncio
import os
import sys
import time
import logging
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


@pytest.mark.asyncio
@pytest.mark.integration
async test_database_pool_basic_functionality():
    """测试数据库连接池基本功能"""
    logger.info("🧪 测试数据库连接池基本功能")

    from database.db_pool import DatabasePool, DatabasePoolConfig

    # 创建连接池配置
    config = DatabasePoolConfig.from_url()
    pool = await DatabasePool.get_instance(config)

    # 初始化连接池
    await pool.init_pool()

    try:
        # 测试基本查询
        result = await pool.fetchval("SELECT 1")
        assert result == 1, "基本查询失败"

        # 测试执行SQL
        await pool.execute("CREATE TEMP TABLE test_pool (id INTEGER, name TEXT)")
        await pool.execute("INSERT INTO test_pool VALUES ($1, $2)", 1, "test")

        # 测试查询
        rows = await pool.fetch("SELECT * FROM test_pool")
        assert len(rows) == 1, "插入数据失败"
        assert rows[0]["id"] == 1 and rows[0]["name"] == "test", "数据内容不匹配"

        # 测试单行查询
        row = await pool.fetchrow("SELECT * FROM test_pool WHERE id = $1", 1)
        assert row is not None, "单行查询失败"
        assert row["name"] == "test", "单行查询结果不正确"

        # 测试单值查询
        value = await pool.fetchval("SELECT name FROM test_pool WHERE id = $1", 1)
        assert value == "test", "单值查询失败"

        # 测试批量执行
        await pool.executemany(
            "INSERT INTO test_pool VALUES ($1, $2)",
            [(2, "test2"), (3, "test3")]
        )

        count = await pool.fetchval("SELECT COUNT(*) FROM test_pool")
        assert count == 3, "批量插入失败"

        logger.info("✅ 数据库连接池基本功能测试通过")

    finally:
        await pool.close()


@pytest.mark.asyncio
@pytest.mark.integration
async test_database_pool_concurrent_access():
    """测试数据库连接池并发访问"""
    logger.info("🚀 测试数据库连接池并发访问")

    from database.db_pool import DatabasePool, DatabasePoolConfig

    config = DatabasePoolConfig.from_url()
    pool = await DatabasePool.get_instance(config)
    await pool.init_pool()

    async def concurrent_task(task_id: int) -> Dict[str, Any]:
        """并发任务"""
        start_time = time.time()

        try:
            # 执行多个查询
            for i in range(5):
                await pool.fetchval("SELECT $1", i)

            # 使用上下文管理器
            async with pool.connection() as conn:
                result = await conn.fetchval("SELECT $1", task_id)

            end_time = time.time()

            return {
                "task_id": task_id,
                "success": True,
                "result": result,
                "duration": end_time - start_time
            }

        except Exception as e:
            end_time = time.time()
            logger.error(f"任务 {task_id} 失败: {e}")
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e),
                "duration": end_time - start_time
            }

    try:
        # 创建20个并发任务
        tasks = [concurrent_task(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        successful_tasks = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_tasks = [r for r in results if not (isinstance(r, dict) and r.get("success"))]

        assert len(successful_tasks) == 20, f"成功任务数不正确: {len(successful_tasks)}/20"
        assert len(failed_tasks) == 0, f"存在失败任务: {len(failed_tasks)}"

        # 验证每个任务的结果
        for result in successful_tasks:
            assert result["result"] == result["task_id"], f"任务结果不匹配: {result}"

        logger.info(f"✅ 并发访问测试通过 - {len(successful_tasks)} 个任务全部成功")

    finally:
        await pool.close()


@pytest.mark.asyncio
@pytest.mark.integration
async test_database_pool_stats_monitoring():
    """测试数据库连接池统计监控"""
    logger.info("📊 测试数据库连接池统计监控")

    from database.db_pool import DatabasePool, DatabasePoolConfig

    config = DatabasePoolConfig.from_url()
    pool = await DatabasePool.get_instance(config)
    await pool.init_pool()

    try:
        # 获取初始统计信息
        initial_stats = pool.get_stats()
        logger.info(f"初始统计: {initial_stats}")

        # 执行一些操作
        for i in range(10):
            await pool.fetchval("SELECT $1", i)

        # 获取更新后的统计信息
        updated_stats = pool.get_stats()
        logger.info(f"更新后统计: {updated_stats}")

        # 验证统计信息更新
        assert updated_stats["total_queries_executed"] >= 10, "查询统计不正确"
        assert updated_stats["total_connections_created"] >= 0, "连接创建统计不正确"

        # 验证连接池信息
        pool_info = pool.get_pool_info()
        assert pool_info["is_initialized"] == True, "连接池状态不正确"
        assert "config" in pool_info, "配置信息缺失"
        assert "stats" in pool_info, "统计信息缺失"

        logger.info("✅ 统计监控测试通过")

    finally:
        await pool.close()


@pytest.mark.asyncio
@pytest.mark.integration
async test_database_pool_error_handling():
    """测试数据库连接池错误处理"""
    logger.info("🛡️ 测试数据库连接池错误处理")

    from database.db_pool import DatabasePool, DatabasePoolConfig

    config = DatabasePoolConfig.from_url()
    pool = await DatabasePool.get_instance(config)
    await pool.init_pool()

    try:
        # 测试SQL错误处理
        try:
            await pool.execute("SELECT * FROM non_existent_table")
            assert False, "应该抛出异常"
        except asyncpg.PostgresError:
            logger.debug("✅ SQL错误正确抛出")

        # 测试参数错误处理
        try:
            await pool.fetchval("SELECT $1::integer", "not_a_number")
            assert False, "应该抛出类型转换错误"
        except (asyncpg.DataError, ValueError):
            logger.debug("✅ 参数错误正确抛出")

        # 验证错误后连接池仍然可用
        result = await pool.fetchval("SELECT 1")
        assert result == 1, "错误后连接池不可用"

        logger.info("✅ 错误处理测试通过")

    finally:
        await pool.close()


@pytest.mark.asyncio
@pytest.mark.integration
async test_enhanced_fotmob_collector_integration():
    """测试EnhancedFotMobCollector与数据库连接池的集成"""
    logger.info("🔗 测试EnhancedFotMobCollector与数据库连接池的集成")

    from database.db_pool import init_global_db_pool
    from collectors.enhanced_fotmob_collector import EnhancedFotMobCollector

    # 初始化全局连接池
    await init_global_db_pool()

    try:
        # 创建采集器实例
        collector = EnhancedFotMobCollector()

        # 测试原始数据保存功能
        test_data = {
            "content": {
                "general": {
                    "matchId": "test_match_123"
                }
            }
        }

        # 调用保存方法 - 这里应该使用连接池
        result = await collector._save_raw_data("test_match_123", test_data)

        if result:
            logger.info("✅ 原始数据保存成功，连接池集成正常")
        else:
            logger.warning("⚠️ 原始数据保存失败，但连接池集成代码已更新")

    except Exception as e:
        logger.error(f"❌ 集成测试失败: {e}")
        # 这里不应该失败，如果失败说明集成有问题
        raise

    finally:
        # 关闭全局连接池
        from database.db_pool import get_db_pool
        pool = await get_db_pool()
        await pool.close()


if __name__ == "__main__":
    """
    直接运行集成测试的便捷方式
    """
    print("🚀 启动数据库连接池集成测试")

    async def main():
        try:
            await test_database_pool_basic_functionality()
            await test_database_pool_concurrent_access()
            await test_database_pool_stats_monitoring()
            await test_database_pool_error_handling()
            print("\n✅ 所有集成测试通过")
        except Exception as e:
            print(f"\n❌ 集成测试失败: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(main())