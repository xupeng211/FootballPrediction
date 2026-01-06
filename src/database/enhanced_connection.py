"""
增强的数据库连接管理模块
集成了性能优化器的生产级数据库连接
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import DatabaseManager

logger = logging.getLogger(__name__)

# 尝试导入数据工程优化组件
try:
    # 暂时禁用，模块不存在
    # from database_connection_optimizer import DatabaseConnectionOptimizer
    DATA_ENGINEERING_ENABLED = False
    DatabaseConnectionOptimizer = None
except ImportError as e:
    logger.warning(f"数据工程组件导入失败: {e}")
    DATA_ENGINEERING_ENABLED = False


class EnhancedDatabaseManager(DatabaseManager):
    """
    增强的数据库连接管理器
    集成了性能优化和监控功能
    """

    def __init__(self):
        super().__init__()
        self.db_optimizer: DatabaseConnectionOptimizer | None = None
        self.query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "slow_queries": 0,
        }

    def initialize(self, config=None):
        """初始化增强的数据库连接"""
        # 先调用父类初始化
        super().initialize(config)

        # 初始化数据工程优化器
        if DATA_ENGINEERING_ENABLED:
            try:
                logger.info("🔧 初始化数据库连接优化器...")
                self.db_optimizer = DatabaseConnectionOptimizer(
                    database_url=self._config.async_url,
                    pool_size=self._config.async_pool_size,
                    max_overflow=self._config.async_max_overflow,
                )
                # 这里不能使用await，需要在异步环境中调用
                logger.info("✅ 数据库连接优化器配置完成")
            except Exception as e:
                logger.warning(f"数据库优化器初始化失败: {e}")
                self.db_optimizer = None

    async def initialize_async(self):
        """异步初始化方法"""
        if self.db_optimizer:
            await self.db_optimizer.initialize()

    @asynccontextmanager
    async def get_async_session_with_stats(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取带有统计功能的异步数据库会话
        """
        if self._async_session_factory is None:
            raise RuntimeError("数据库连接未初始化")

        session = self._async_session_factory()
        start_time = time.time()

        try:
            yield session
            self.query_stats["successful_queries"] += 1
        except Exception as e:
            self.query_stats["failed_queries"] += 1
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            self._update_query_stats(execution_time)

            # 记录慢查询
            if execution_time > 1.0:  # 超过1秒
                self.query_stats["slow_queries"] += 1
                logger.warning(f"慢查询检测: 执行时间 {execution_time:.3f}s")

            await session.close()

    async def execute_query_with_stats(self, query: str, params: dict = None, use_cache: bool = True):
        """
        执行带有统计和缓存的查询
        """
        if self.db_optimizer:
            return await self.db_optimizer.execute_query(query, params, use_cache=use_cache)
        # 降级到标准查询
        async with self.get_async_session_with_stats() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    async def get_connection_stats(self) -> dict[str, Any]:
        """获取连接统计信息"""
        stats = {"query_stats": self.query_stats, "engine_stats": {}}

        # 获取SQLAlchemy连接池统计
        if self._async_engine:
            pool = self._async_engine.pool
            stats["engine_stats"] = {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }

        # 获取数据库优化器统计
        if self.db_optimizer:
            optimizer_stats = await self.db_optimizer.get_connection_pool_stats()
            stats["optimizer_stats"] = optimizer_stats

        return stats

    async def health_check(self) -> dict[str, Any]:
        """增强的健康检查"""
        health = {"status": "healthy", "timestamp": time.time(), "database": "unknown"}

        try:
            # 执行简单查询测试连接
            async with self.get_async_session_with_stats() as session:
                result = await session.execute(text("SELECT 1"))
                await result.fetchone()

            health["database"] = "healthy"

            # 添加连接统计
            health["connection_stats"] = await self.get_connection_stats()

        except Exception as e:
            health["database"] = "unhealthy"
            health["error"] = str(e)

        return health

    async def optimize_database(self):
        """数据库优化操作"""
        if not self.db_optimizer:
            logger.warning("数据库优化器未可用")
            return

        try:
            # 创建性能索引
            logger.info("📊 创建性能索引...")
            await self.db_optimizer.create_performance_indexes()

            # 更新表统计信息
            logger.info("📈 更新表统计信息...")
            await self.db_optimizer.update_table_statistics()

            logger.info("✅ 数据库优化完成")

        except Exception as e:
            logger.error(f"数据库优化失败: {e}")

    def _update_query_stats(self, execution_time: float):
        """更新查询统计信息"""
        self.query_stats["total_queries"] += 1
        self.query_stats["total_time"] += execution_time
        self.query_stats["avg_time"] = self.query_stats["total_time"] / self.query_stats["total_queries"]

    async def cleanup(self):
        """清理资源"""
        if self.db_optimizer:
            await self.db_optimizer.cleanup()


# 全局增强数据库管理器实例
enhanced_db_manager: EnhancedDatabaseManager | None = None


def get_enhanced_database_manager() -> EnhancedDatabaseManager:
    """获取增强的数据库管理器实例"""
    global enhanced_db_manager
    if enhanced_db_manager is None:
        enhanced_db_manager = EnhancedDatabaseManager()
    return enhanced_db_manager


# 便捷函数
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取标准异步数据库会话"""
    manager = get_enhanced_database_manager()
    async with manager.get_async_session_with_stats() as session:
        yield session


@asynccontextmanager
async def get_optimized_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取优化的异步数据库会话"""
    manager = get_enhanced_database_manager()
    async with manager.get_async_session_with_stats() as session:
        yield session


async def initialize_enhanced_database():
    """初始化增强的数据库连接"""
    manager = get_enhanced_database_manager()
    manager.initialize()
    await manager.initialize_async()

    # 自动优化数据库
    if DATA_ENGINEERING_ENABLED:
        await manager.optimize_database()

    logger.info("✅ 增强数据库连接初始化完成")


async def get_database_health():
    """获取数据库健康状态"""
    manager = get_enhanced_database_manager()
    return await manager.health_check()


async def get_database_performance_stats():
    """获取数据库性能统计"""
    manager = get_enhanced_database_manager()
    return await manager.get_connection_stats()
