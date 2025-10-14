"""
数据库连接池配置优化
"""

import os
import asyncio
from typing import Dict, Optional
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy import event
from sqlalchemy.engine import Engine

from src.core.logging import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


class DatabasePoolConfig:
    """数据库连接池配置管理器"""

    def __init__(self):
        self.settings = get_settings()
        self._engine: Optional[AsyncEngine] = None
    def get_pool_config(self) -> Dict[str, Any]:
        """获取优化的连接池配置"""
        # 基于系统资源动态调整
        cpu_count = os.cpu_count() or 4

        # 根据环境配置不同的池大小
        if self.settings.environment == "production":
            pool_size = min(30, cpu_count * 5)
            max_overflow = min(50, pool_size * 2)
            pool_timeout = 30
            pool_recycle = 3600
        elif self.settings.environment == "staging":
            pool_size = min(20, cpu_count * 3)
            max_overflow = min(30, pool_size * 1.5)
            pool_timeout = 20
            pool_recycle = 1800
        else:  # development
            pool_size = min(10, cpu_count * 2)
            max_overflow = 20
            pool_timeout = 10
            pool_recycle = 600

        return {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": True,
            "poolclass": QueuePool,
            "echo": self.settings.environment == "development",
            "echo_pool": self.settings.environment == "development",
            "future": True,
        }

    async def create_engine(self) -> AsyncEngine:
        """创建优化的数据库引擎"""
        if self._engine is None:
            pool_config = self.get_pool_config()

            logger.info(
                "创建数据库引擎",
                pool_size=pool_config["pool_size"],
                max_overflow=pool_config["max_overflow"],
                pool_timeout=pool_config["pool_timeout"]
            )

            self._engine = create_async_engine(
                self.settings.database_url,
                **pool_config
            )

            # 注册事件监听器
            self._register_event_listeners()

        return self._engine

    def _register_event_listeners(self):
        """注册数据库事件监听器"""

        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """连接建立时的回调"""
            logger.debug("数据库连接已建立")

        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接从池中取出时的回调"""
            # 记录连接池使用情况
            pool_status = connection_proxy.pool.status()
            logger.debug(
                "连接从池中取出",
                size=pool_status.size,
                checked_out=pool_status.checkedout,
                overflow=pool_status.overflow
            )

        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接返回池中时的回调"""
            logger.debug("连接已返回池中")

        @event.listens_for(Engine, "before_execute")
        def receive_before_execute(conn, clauseelement, multiparams, params, execution_options):
            """SQL执行前的回调"""
            if execution_options.get("log_query", False):
                logger.info("执行SQL", sql=str(clauseelement))

        @event.listens_for(Engine, "after_execute")
        def receive_after_execute(conn, clauseelement, multiparams, params, result, execution_options):
            """SQL执行后的回调"""
            if execution_options.get("log_query", False):
                logger.info("SQL执行完成", rows=result.rowcount)

    async def monitor_pool_health(self):
        """监控连接池健康状态"""
        if not self._engine:
            return

        pool = self._engine.pool

        while True:
            try:
                # 获取连接池状态
                status = pool.status()

                # 记录关键指标
                logger.info(
                    "连接池状态",
                    size=status.size,
                    checked_out=status.checkedout,
                    overflow=status.overflow,
                    checked_in=status.checkedin
                )

                # 检查连接池使用率
                usage_rate = status.checkedout / (status.size + status.overflow) if (status.size + status.overflow) > 0 else 0

                if usage_rate > 0.8:
                    logger.warning(
                        "连接池使用率过高",
                        usage_rate=f"{usage_rate:.2%}",
                        checked_out=status.checkedout,
                        total=status.size + status.overflow
                    )

                # 等待下次检查
                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error("监控连接池健康状态失败", error=str(e))
                await asyncio.sleep(60)

    async def create_test_connection(self) -> bool:
        """创建测试连接验证数据库可用性"""
        try:
            engine = await self.create_engine()
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error("数据库连接测试失败", error=str(e))
            return False

    async def close(self):
        """关闭数据库引擎"""
        if self._engine:
            await self._engine.dispose()
            logger.info("数据库引擎已关闭")


class AsyncpgPoolConfig:
    """AsyncPG连接池配置（用于直接使用asyncpg的场景）"""

    def __init__(self):
        self.settings = get_settings()

    def get_pool_config(self) -> Dict[str, Any]:
        """获取AsyncPG连接池配置"""
        return {
            "min_size": 5,
            "max_size": 20,
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300,
            "timeout": 60,
            "command_timeout": 30,
            "server_settings": {
                "application_name": "football_prediction",
                "timezone": "UTC",
                "jit": "of"  # 关闭JIT以提高简单查询性能
            }
        }

    async def create_pool(self):
        """创建AsyncPG连接池"""
        config = self.get_pool_config()

        logger.info(
            "创建AsyncPG连接池",
            min_size=config["min_size"],
            max_size=config["max_size"]
        )

        return await asyncpg.create_pool(
            self.settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
            **config
        )


# 全局配置实例
pool_config = DatabasePoolConfig()
asyncpg_config = AsyncpgPoolConfig()


# 连接池健康检查装饰器
def with_connection_pool_health_check(func):
    """连接池健康检查装饰器"""
    async def wrapper(*args, **kwargs):
        # 在执行前检查连接池健康状态
        if pool_config._engine:
            pool = pool_config._engine.pool
            status = pool.status()

            # 如果连接池已满，记录警告
            if status.checkedout >= (status.size + status.overflow) * 0.9:
                logger.warning(
                    "连接池即将满载",
                    usage=f"{status.checkedout}/{status.size + status.overflow}"
                )

        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error("执行失败", function=func.__name__, error=str(e))
            raise

    return wrapper


# 连接池统计信息收集器
class PoolStatsCollector:
    """连接池统计信息收集器"""

    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_checkout_time": 0,
            "peak_connections": 0
        }

    async def collect_stats(self):
        """收集连接池统计信息"""
        if not pool_config._engine:
            return

        pool = pool_config._engine.pool
        status = pool.status()

        self.stats["peak_connections"] = max(
            self.stats["peak_connections"],
            status.checkedout
        )

        logger.info(
            "连接池统计",
            current_connections=status.checkedout,
            peak_connections=self.stats["peak_connections"],
            pool_size=status.size
        )


# 全局统计收集器
stats_collector = PoolStatsCollector()
