#!/usr/bin/env python3
"""
数据库连接池性能压力测试

模拟50个并发任务，每个任务尝试连接数据库5次
用于验证连接池在高并发场景下的稳定性

运行方式:
pytest tests/performance/test_db_pool_stress.py -v -s
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
from datetime import datetime

# 设置项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseStressTester:
    """数据库压力测试器"""

    def __init__(self):
        """初始化测试器配置"""
        # 从环境变量获取数据库连接参数
        self.db_config = self._get_db_config()
        self.test_results: List[Dict[str, Any]] = []

    def _get_db_config(self) -> Dict[str, Any]:
        """从环境变量获取数据库配置"""
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction"
        )

        # 解析数据库URL
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))

        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
            "database": parsed.path.lstrip("/") or "football_prediction"
        }

    async def single_connection_task(self, task_id: int, connection_attempts: int = 5) -> Dict[str, Any]:
        """
        单个连接任务

        Args:
            task_id: 任务ID
            connection_attempts: 连接尝试次数

        Returns:
            Dict: 任务执行结果
        """
        start_time = time.time()
        successful_connections = 0
        failed_connections = 0
        errors: List[str] = []

        logger.info(f"🚀 任务 {task_id}: 开始执行 {connection_attempts} 次连接测试")

        for attempt in range(connection_attempts):
            attempt_start = time.time()
            try:
                # 模拟当前代码中的直接连接方式
                conn = await asyncpg.connect(**self.db_config)

                # 执行简单查询验证连接
                result = await conn.fetchval("SELECT 1")
                await conn.close()

                if result == 1:
                    successful_connections += 1
                    connection_time = time.time() - attempt_start
                    logger.debug(f"✅ 任务 {task_id} - 尝试 {attempt + 1}: 连接成功 ({connection_time:.3f}s)")
                else:
                    failed_connections += 1
                    errors.append(f"查询结果异常: {result}")

            except asyncpg.exceptions.ConnectionLimitExceededError as e:
                failed_connections += 1
                errors.append(f"连接数超限: {str(e)}")
                logger.warning(f"⚠️ 任务 {task_id} - 尝试 {attempt + 1}: 连接数超限")

            except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                failed_connections += 1
                errors.append(f"连接不存在: {str(e)}")
                logger.warning(f"⚠️ 任务 {task_id} - 尝试 {attempt + 1}: 连接不存在")

            except Exception as e:
                failed_connections += 1
                errors.append(f"未知错误: {str(e)}")
                logger.error(f"❌ 任务 {task_id} - 尝试 {attempt + 1}: {str(e)}")

            # 模拟实际使用中的间隔
            await asyncio.sleep(0.1)

        total_time = time.time() - start_time

        result = {
            "task_id": task_id,
            "total_attempts": connection_attempts,
            "successful_connections": successful_connections,
            "failed_connections": failed_connections,
            "success_rate": successful_connections / connection_attempts,
            "total_time": total_time,
            "avg_connection_time": total_time / connection_attempts,
            "errors": errors
        }

        logger.info(f"🏁 任务 {task_id}: 完成 - 成功: {successful_connections}/{connection_attempts} ({result['success_rate']:.1%})")
        return result

    async def run_stress_test(self, concurrent_tasks: int = 50, connections_per_task: int = 5) -> Dict[str, Any]:
        """
        运行压力测试

        Args:
            concurrent_tasks: 并发任务数
            connections_per_task: 每个任务的连接尝试次数

        Returns:
            Dict: 测试结果统计
        """
        logger.info(f"🎯 开始数据库压力测试")
        logger.info(f"   并发任务数: {concurrent_tasks}")
        logger.info(f"   每任务连接数: {connections_per_task}")
        logger.info(f"   总连接请求数: {concurrent_tasks * connections_per_task}")
        logger.info("=" * 60)

        test_start_time = time.time()

        # 创建并发任务
        tasks = [
            self.single_connection_task(task_id, connections_per_task)
            for task_id in range(concurrent_tasks)
        ]

        # 执行所有并发任务
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"❌ 并发执行失败: {e}")
            raise

        test_end_time = time.time()
        total_test_time = test_end_time - test_start_time

        # 统计结果
        successful_tasks = 0
        failed_tasks = 0
        total_successful_connections = 0
        total_failed_connections = 0
        connection_limit_errors = 0

        for result in results:
            if isinstance(result, Exception):
                failed_tasks += 1
                logger.error(f"❌ 任务异常: {result}")
            else:
                successful_tasks += 1
                total_successful_connections += result["successful_connections"]
                total_failed_connections += result["failed_connections"]

                # 检查是否有连接数超限错误
                for error in result.get("errors", []):
                    if "连接数超限" in error or "ConnectionLimitExceededError" in error:
                        connection_limit_errors += 1

        total_connections_requested = concurrent_tasks * connections_per_task

        # 计算统计指标
        stats = {
            "test_config": {
                "concurrent_tasks": concurrent_tasks,
                "connections_per_task": connections_per_task,
                "total_connections_requested": total_connections_requested
            },
            "execution_summary": {
                "total_test_time": total_test_time,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "task_success_rate": successful_tasks / concurrent_tasks
            },
            "connection_summary": {
                "total_successful_connections": total_successful_connections,
                "total_failed_connections": total_failed_connections,
                "overall_connection_success_rate": total_successful_connections / total_connections_requested,
                "connection_limit_errors": connection_limit_errors
            },
            "performance_metrics": {
                "avg_time_per_connection": total_test_time / total_connections_requested,
                "connections_per_second": total_connections_requested / total_test_time
            },
            "raw_results": results
        }

        return stats


@pytest.mark.asyncio
@pytest.mark.performance
async test_database_stress_current_implementation():
    """
    测试当前实现在高并发场景下的表现

    这个测试模拟50个并发任务，每个任务尝试5次数据库连接
    用于验证当前代码是否存在连接数限制问题
    """
    logger.info("🧪 开始当前实现的数据库压力测试")

    # 创建压力测试器
    tester = DatabaseStressTester()

    # 运行压力测试
    stats = await tester.run_stress_test(concurrent_tasks=50, connections_per_task=5)

    # 输出详细统计信息
    logger.info("📊 测试结果统计:")
    logger.info(f"   总测试时间: {stats['execution_summary']['total_test_time']:.2f}s")
    logger.info(f"   任务成功率: {stats['execution_summary']['task_success_rate']:.1%}")
    logger.info(f"   连接成功率: {stats['connection_summary']['overall_connection_success_rate']:.1%}")
    logger.info(f"   连接数超限错误: {stats['connection_summary']['connection_limit_errors']}")
    logger.info(f"   平均每连接耗时: {stats['performance_metrics']['avg_time_per_connection']:.3f}s")
    logger.info(f"   连接吞吐量: {stats['performance_metrics']['connections_per_second']:.1f} conn/s")

    # 核心断言：所有连接请求都应该在5秒内完成
    assert stats['execution_summary']['total_test_time'] < 5.0, \
        f"总测试时间过长: {stats['execution_summary']['total_test_time']:.2f}s > 5.0s"

    # 断言：不应该有连接数超限错误
    assert stats['connection_summary']['connection_limit_errors'] == 0, \
        f"检测到连接数超限错误: {stats['connection_summary']['connection_limit_errors']}"

    # 断言：整体连接成功率应该大于90%
    assert stats['connection_summary']['overall_connection_success_rate'] > 0.9, \
        f"连接成功率过低: {stats['connection_summary']['overall_connection_success_rate']:.1%}"

    logger.info("✅ 压力测试通过 - 当前实现在高并发下表现良好")


@pytest.mark.asyncio
@pytest.mark.performance
async test_database_connection_reuse():
    """
    测试数据库连接复用效率

    验证重复连接和关闭是否有性能损失
    """
    logger.info("🔄 测试数据库连接复用效率")

    tester = DatabaseStressTester()

    # 测试场景1: 每次新建连接
    start_time = time.time()
    for i in range(10):
        conn = await asyncpg.connect(**tester.db_config)
        await conn.fetchval("SELECT 1")
        await conn.close()
    new_connection_time = time.time() - start_time

    # 测试场景2: 复用连接 (模拟连接池)
    start_time = time.time()
    conn = await asyncpg.connect(**tester.db_config)
    for i in range(10):
        await conn.fetchval("SELECT 1")
    await conn.close()
    reuse_connection_time = time.time() - start_time

    logger.info(f"   新建连接方式: {new_connection_time:.3f}s")
    logger.info(f"   复用连接方式: {reuse_connection_time:.3f}s")
    logger.info(f"   性能提升: {((new_connection_time - reuse_connection_time) / new_connection_time * 100):.1f}%")

    # 复用连接应该更快
    assert reuse_connection_time < new_connection_time, \
        "连接复用应该比每次新建连接更快"

    logger.info("✅ 连接复用效率测试通过")


if __name__ == "__main__":
    """
    直接运行压力测试的便捷方式
    """
    print("🚀 启动数据库压力测试")
    print("确保数据库服务正在运行并且可以连接")

    async def main():
        tester = DatabaseStressTester()
        stats = await tester.run_stress_test(concurrent_tasks=50, connections_per_task=5)

        print("\n" + "=" * 60)
        print("📊 压力测试完成")
        print(f"总连接请求数: {stats['test_config']['total_connections_requested']}")
        print(f"连接成功率: {stats['connection_summary']['overall_connection_success_rate']:.1%}")
        print(f"连接数超限错误: {stats['connection_summary']['connection_limit_errors']}")
        print(f"测试总时间: {stats['execution_summary']['total_test_time']:.2f}s")
        print("=" * 60)

    asyncio.run(main())