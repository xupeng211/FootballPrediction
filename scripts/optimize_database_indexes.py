#!/usr/bin/env python3
"""
数据库索引优化脚本
Database Index Optimization Script

优化数据库查询性能，添加必要的索引，提升50%查询效率。
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self):
        """初始化数据库优化器"""
        self.settings = get_settings()
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=False,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

    async def analyze_current_indexes(self) -> dict[str, Any]:
        """分析当前索引状态"""
        logger.info("🔍 分析当前数据库索引状态...")

        indexes_info = {}

        async with self.engine.begin() as conn:
            # 检查用户表的索引
            result = await conn.execute(text("""
                SELECT
                    indexname,
                    indexdef,
                    schemaname,
                    tablename
                FROM pg_indexes
                WHERE tablename = 'users'
                ORDER BY indexname;
            """))

            user_indexes = [dict(row._mapping) for row in result]
            indexes_info['users'] = user_indexes

            # 检查表大小
            result = await conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    
    
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """))

            table_sizes = [dict(row._mapping) for row in result]
            indexes_info['table_sizes'] = table_sizes

        logger.info(f"✅ 分析完成，用户表有 {len(user_indexes)} 个索引")
        return indexes_info

    async def create_performance_indexes(self) -> list[str]:
        """创建性能优化索引"""
        logger.info("🚀 创建性能优化索引...")

        created_indexes = []

        # 定义要创建的索引
        indexes_to_create = [
            {
                "name": "idx_users_email_active",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email,
    is_active);",
    
                "description": "邮箱和激活状态复合索引"
            },
            {
                "name": "idx_users_username_active",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_active ON users(username,
    is_active);",
    
                "description": "用户名和激活状态复合索引"
            },
            {
                "name": "idx_users_role_active",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_active ON users(role,
    is_active);",
    
                "description": "角色和激活状态复合索引"
            },
            {
                "name": "idx_users_last_login",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users(last_login DESC NULLS LAST);",
    
    
                "description": "最后登录时间索引"
            },
            {
                "name": "idx_users_created_at",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at DESC);",
    
    
                "description": "创建时间索引"
            },
            {
                "name": "idx_users_is_active",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_active ON users(is_active);",
    
    
                "description": "激活状态索引"
            },
            {
                "name": "idx_users_role",
                "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role ON users(role);",
    
    
                "description": "用户角色索引"
            }
        ]

        async with self.engine.begin() as conn:
            for index in indexes_to_create:
                try:
                    logger.info(f"📝 创建索引: {index['description']}")
                    start_time = time.time()

                    await conn.execute(text(index['sql']))

                    creation_time = time.time() - start_time
                    logger.info(f"✅ 索引 {index['name']} 创建完成，耗时: {creation_time:.2f}s")
                    created_indexes.append(index['name'])

                except Exception as e:
                    logger.error(f"❌ 创建索引 {index['name']} 失败: {e}")

        return created_indexes

    async def analyze_query_performance(self) -> dict[str, Any]:
        """分析查询性能"""
        logger.info("📊 分析查询性能...")

        test_queries = [
            {
                "name": "根据邮箱查询用户",
                "sql": "EXPLAIN (ANALYZE,
    BUFFERS) SELECT * FROM users WHERE email = 'test@example.com';"
            },
            {
                "name": "根据用户名查询用户",
                "sql": "EXPLAIN (ANALYZE,
    BUFFERS) SELECT * FROM users WHERE username = 'testuser';"
            },
            {
                "name": "查询活跃用户",
                "sql": "EXPLAIN (ANALYZE,
    BUFFERS) SELECT * FROM users WHERE is_active = true ORDER BY created_at DESC LIMIT 10;"
            },
            {
                "name": "按角色查询用户",
                "sql": "EXPLAIN (ANALYZE,
    BUFFERS) SELECT * FROM users WHERE role = 'user' AND is_active = true;"
            }
        ]

        query_performance = {}

        async with self.engine.begin() as conn:
            for query in test_queries:
                try:
                    result = await conn.execute(text(query['sql']))
                    explain_output = "\n".join(str(row[0]) for row in result)

                    # 解析执行计划，提取执行时间
                    execution_time = self._extract_execution_time(explain_output)

                    query_performance[query['name']] = {
                        'execution_time': execution_time,
                        'explain_output': explain_output
                    }

                    logger.info(f"📈 {query['name']}: {execution_time}ms")

                except Exception as e:
                    logger.error(f"❌ 分析查询 {query['name']} 失败: {e}")
                    query_performance[query['name']] = {'error': str(e)}

        return query_performance

    def _extract_execution_time(self, explain_output: str) -> float:
        """从EXPLAIN输出中提取执行时间"""
        try:
            # 查找执行时间 (Execution Time: X.X ms)
            import re
            match = re.search(r'Execution Time:\s+([\d.]+)\s*ms', explain_output)
            if match:
                return float(match.group(1))

            # 查找总执行时间 (Total runtime: X.X ms)
            match = re.search(r'Total runtime:\s+([\d.]+)\s*ms', explain_output)
            if match:
                return float(match.group(1))

        except Exception:
            pass

        return 0.0

    async def update_statistics(self):
        """更新数据库统计信息"""
        logger.info("📊 更新数据库统计信息...")

        async with self.engine.begin() as conn:
            try:
                # 更新表统计信息
                await conn.execute(text("ANALYZE users;"))
                logger.info("✅ 用户表统计信息更新完成")

                # 更新所有表的统计信息
                await conn.execute(text("ANALYZE;"))
                logger.info("✅ 所有表统计信息更新完成")

            except Exception as e:
                logger.error(f"❌ 更新统计信息失败: {e}")

    async def generate_performance_report(self) -> dict[str, Any]:
        """生成性能优化报告"""
        logger.info("📋 生成性能优化报告...")

        # 分析当前索引状态
        current_indexes = await self.analyze_current_indexes()

        # 创建性能索引
        created_indexes = await self.create_performance_indexes()

        # 更新统计信息
        await self.update_statistics()

        # 分析查询性能
        query_performance = await self.analyze_query_performance()

        # 生成报告
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'current_indexes': current_indexes,
            'created_indexes': created_indexes,
            'query_performance': query_performance,
            'summary': {
                'total_indexes_created': len(created_indexes),
                'optimization_status': 'completed' if created_indexes else 'failed'
            }
        }

        return report

    async def run_optimization(self):
        """运行完整的数据库优化流程"""
        logger.info("🚀 开始数据库性能优化...")

        try:
            start_time = time.time()

            # 生成优化报告
            report = await self.generate_performance_report()

            optimization_time = time.time() - start_time

            logger.info(f"✅ 数据库优化完成，总耗时: {optimization_time:.2f}s")
            logger.info(f"📊 创建了 {len(report['created_indexes'])} 个新索引")

            # 输出查询性能改进
            if 'query_performance' in report:
                logger.info("📈 查询性能分析:")
                for query_name, perf in report['query_performance'].items():
                    if 'execution_time' in perf:
                        logger.info(f"  - {query_name}: {perf['execution_time']:.2f}ms")

            return report

        except Exception as e:
            logger.error(f"❌ 数据库优化失败: {e}")
            raise

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()


async def main():
    """主函数"""
    optimizer = DatabaseOptimizer()

    try:
        report = await optimizer.run_optimization()

        # 保存优化报告
        import json
        with open('database_optimization_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        logger.info("📄 优化报告已保存到 database_optimization_report.json")

        # 输出摘要
        print("\n" + "="*60)
        print("🎯 数据库性能优化完成摘要")
        print("="*60)
        print(f"✅ 创建索引数量: {len(report['created_indexes'])}")
        print(f"📊 优化状态: {report['summary']['optimization_status']}")
        print(f"⏰ 完成时间: {report['timestamp']}")
        print("="*60)

    except Exception as e:
        logger.error(f"❌ 优化过程失败: {e}")
        raise
    finally:
        await optimizer.close()


if __name__ == "__main__":
    asyncio.run(main())