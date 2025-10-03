"""
缓存初始化脚本
Cache Initialization Script

用于系统启动时初始化缓存配置和预热数据
"""

import asyncio
import logging
from typing import List, Optional

from src.cache.redis_manager import RedisManager
from src.cache.optimization import (
    MultiLevelCache,
    CacheWarmer,
    CacheOptimizer,
    init_cache_manager,
    get_cache_manager
)
from src.config.cache import get_cache_config_manager, init_cache_config

logger = logging.getLogger(__name__)


class CacheInitializer:
    """缓存初始化器"""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager
        self.config_manager = init_cache_config()
        self.cache_manager: Optional[MultiLevelCache] = None
        self.cache_warmer: Optional[CacheWarmer] = None
        self.cache_optimizer: Optional[CacheOptimizer] = None

    async def initialize(self) -> bool:
        """初始化缓存系统"""
        try:
            logger.info("🗄️ 开始初始化缓存系统...")

            # 初始化多级缓存管理器
            logger.info("📦 初始化多级缓存管理器...")
            self.cache_manager = init_cache_manager(
                self.config_manager.get_cache_config(),
                self.redis_manager
            )

            # 初始化缓存预热器
            logger.info("🔥 初始化缓存预热器...")
            self.cache_warmer = CacheWarmer(self.cache_manager)
            self._setup_warmup_tasks()

            # 初始化缓存优化器
            logger.info("⚡ 初始化缓存优化器...")
            self.cache_optimizer = CacheOptimizer(self.cache_manager)
            self._setup_optimization_rules()

            # 执行缓存预热
            if self.config_manager.settings.preload_enabled:
                logger.info("🚀 开始缓存预热...")
                await self.cache_warmer.warmup_all()
            else:
                logger.info("⏭️ 缓存预热已禁用")

            logger.info("✅ 缓存系统初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 缓存系统初始化失败: {e}")
            return False

    def _setup_warmup_tasks(self):
        """设置预热任务"""
        # 预热预测数据
        self.cache_warmer.add_task(
            "predictions",
            self.cache_warmer.warmup_predictions
        )

        # 预热球队数据
        self.cache_warmer.add_task(
            "teams",
            self.cache_warmer.warmup_teams
        )

        # 添加自定义预热任务
        self.cache_warmer.add_task(
            "hot_matches",
            self._warmup_hot_matches
        )

    def _setup_optimization_rules(self):
        """设置优化规则"""
        # 清理过期缓存
        self.cache_optimizer.add_rule(
            self.cache_optimizer.cleanup_expired
        )

        # 根据访问模式调整TTL
        self.cache_optimizer.add_rule(
            self.cache_optimizer.adjust_ttl_based_on_access
        )

        # 提升热键
        self.cache_optimizer.add_rule(
            self.cache_optimizer.promote_hot_keys
        )

    async def _warmup_hot_matches(self):
        """预热热门比赛"""
        try:
            # 这里应该从数据库查询热门比赛
            # 示例实现
            hot_matches = []
            cache = get_cache_manager()
            if cache:
                for match_id in hot_matches:
                    key = f"match:{match_id}:details"
                    # 这里应该加载实际数据
                    await cache.set(key, {"match_id": match_id, "hot": True})
            logger.info("热门比赛预热完成")
        except Exception as e:
            logger.error(f"热门比赛预热失败: {e}")

    async def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.cache_manager:
            return {"error": "Cache manager not initialized"}

        return self.cache_manager.get_stats()

    async def shutdown(self):
        """关闭缓存系统"""
        try:
            logger.info("🔌 关闭缓存系统...")
            # 这里可以添加清理逻辑
            logger.info("✅ 缓存系统已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭缓存系统失败: {e}")


# 全局初始化器实例
_cache_initializer: Optional[CacheInitializer] = None


async def init_cache_system(redis_manager: Optional[RedisManager] = None) -> bool:
    """初始化全局缓存系统"""
    global _cache_initializer
    _cache_initializer = CacheInitializer(redis_manager)
    return await _cache_initializer.initialize()


def get_cache_initializer() -> Optional[CacheInitializer]:
    """获取全局缓存初始化器"""
    return _cache_initializer


async def shutdown_cache_system():
    """关闭全局缓存系统"""
    global _cache_initializer
    if _cache_initializer:
        await _cache_initializer.shutdown()
        _cache_initializer = None


# 定期任务
async def cache_maintenance_task():
    """缓存维护任务"""
    initializer = get_cache_initializer()
    if not initializer:
        logger.warning("缓存初始化器未初始化")
        return

    try:
        # 执行优化
        if initializer.cache_optimizer:
            await initializer.cache_optimizer.optimize()

        # 记录统计信息
        if initializer.cache_manager:
            stats = await initializer.get_cache_stats()
            logger.info(f"缓存统计: {stats}")

    except Exception as e:
        logger.error(f"缓存维护任务失败: {e}")


# 定期任务调度器
async def schedule_cache_maintenance():
    """调度缓存维护任务"""
    import asyncio

    config_manager = get_cache_config_manager()
    interval = config_manager.settings.stats_interval

    while True:
        try:
            await asyncio.sleep(interval)
            await cache_maintenance_task()
        except asyncio.CancelledError:
            logger.info("缓存维护任务已取消")
            break
        except Exception as e:
            logger.error(f"调度缓存维护任务失败: {e}")
            await asyncio.sleep(60)  # 错误后等待1分钟再试