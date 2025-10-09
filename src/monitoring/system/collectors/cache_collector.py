"""
缓存监控收集器

收集Redis和其他缓存系统的指标。
"""

import logging
from typing import Dict, Optional

from src.cache.redis_manager import get_redis_manager
from ..metrics.system_metrics import SystemMetrics

logger = logging.getLogger(__name__)


class CacheCollector:
    """缓存监控收集器"""

    def __init__(self, metrics: SystemMetrics):
        """
        初始化缓存收集器

        Args:
            metrics: 系统指标实例
        """
        self.metrics = metrics
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "operations": {
                "get": {"hit": 0, "miss": 0},
                "set": {"hit": 0, "miss": 0},
                "delete": {"hit": 0, "miss": 0},
            },
        }

    async def collect(self) -> Dict[str, any]:
        """
        收集缓存指标

        Returns:
            收集到的指标值
        """
        try:
            metrics_data = {}

            # 获取Redis指标
            redis_info = await self._get_redis_info()
            if redis_info:
                metrics_data["redis"] = redis_info

                # 更新Redis指标
                self.metrics.cache_size_bytes.labels(
                    cache_type="redis"
                ).set(redis_info.get("used_memory", 0))

                # 计算命中率
                hits = redis_info.get("keyspace_hits", 0)
                misses = redis_info.get("keyspace_misses", 0)
                total = hits + misses
                if total > 0:
                    hit_ratio = hits / total
                    self.metrics.cache_hit_ratio.labels(
                        cache_type="redis"
                    ).set(hit_ratio)
                    metrics_data["redis_hit_ratio"] = hit_ratio

            # 更新操作计数
            self._update_operation_metrics()

            logger.debug(f"缓存指标收集完成: {metrics_data}")
            return metrics_data

        except Exception as e:
            logger.error(f"收集缓存指标失败: {e}")
            return {}

    async def _get_redis_info(self) -> Optional[Dict[str, any]]:
        """
        获取Redis信息

        Returns:
            Redis信息字典
        """
        try:
            redis_manager = get_redis_manager()
            if not redis_manager:
                return None

            info = await redis_manager.info()
            return info

        except Exception as e:
            logger.debug(f"无法获取Redis信息: {e}")
            return None

    def _update_operation_metrics(self):
        """更新缓存操作指标"""
        # 更新总操作数
        for operation, results in self.cache_stats["operations"].items():
            for result, count in results.items():
                if count > 0:
                    self.metrics.cache_operations_total.labels(
                        operation=operation,
                        cache_type="redis",
                        result=result,
                    ).inc(count)

    def record_operation(self, operation: str, cache_type: str, result: str):
        """
        记录缓存操作

        Args:
            operation: 操作类型
            cache_type: 缓存类型
            result: 操作结果（hit/miss）
        """
        # 更新统计
        if operation not in self.cache_stats["operations"]:
            self.cache_stats["operations"][operation] = {"hit": 0, "miss": 0}

        if result in ["hit", "miss"]:
            self.cache_stats["operations"][operation][result] += 1

        if result == "hit":
            self.cache_stats["hits"] += 1
        else:
            self.cache_stats["misses"] += 1

        # 立即更新指标
        self.metrics.cache_operations_total.labels(
            operation=operation,
            cache_type=cache_type,
            result=result,
        ).inc()

    def get_cache_stats(self) -> Dict[str, any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        total_hits = self.cache_stats["hits"]
        total_misses = self.cache_stats["misses"]
        total_operations = total_hits + total_misses

        stats = {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_operations": total_operations,
            "operations_by_type": self.cache_stats["operations"],
        }

        if total_operations > 0:
            stats["overall_hit_ratio"] = total_hits / total_operations

        return stats

    async def test_connection(self) -> bool:
        """
        测试缓存连接

        Returns:
            连接是否正常
        """
        try:
            redis_manager = get_redis_manager()
            if not redis_manager:
                return False

            # 执行ping命令
            result = await redis_manager.ping()
            if result:
                self.record_operation("ping", "redis", "hit")
            return result

        except Exception as e:
            logger.error(f"缓存连接测试失败: {e}")
            self.record_operation("ping", "redis", "miss")
            return False