"""
赔率收集器管理器
Odds Collector Manager

管理多个收集器实例
"""




logger = logging.getLogger(__name__)


class OddsCollectorManager:
    """赔率收集器管理器"""

    def __init__(self):
        """初始化管理器"""
        self.collectors: Dict[int, OddsCollector] = {}
        self.redis_manager = RedisManager()

    async def get_collector(self, session_id: int) -> OddsCollector:
        """
        获取或创建收集器实例

        Args:
            session_id: 会话ID

        Returns:
            赔率收集器实例
        """
        if session_id not in self.collectors:
            from src.database.connection import get_async_session

            async with get_async_session() as session:
                collector = OddsCollector(session, self.redis_manager)
                self.collectors[session_id] = collector
        return self.collectors[session_id]

    async def start_all(self):
        """启动所有收集器"""
        for collector in self.collectors.values():
            await collector.start_collection()

    async def stop_all(self):
        """停止所有收集器"""
        for collector in self.collectors.values():
            await collector.stop_collection()

    def remove_collector(self, session_id: int):
        """
        移除收集器

        Args:
            session_id: 会话ID
        """
        if session_id in self.collectors:
            del self.collectors[session_id]

    async def get_global_stats(self) -> Dict:
        """
        获取所有收集器的全局统计

        Returns:
            统计信息
        """
        total_stats = {
            "total_collectors": len(self.collectors),
            "running_collectors": 0,
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "unique_matches": 0,
            "average_processing_time": 0.0,
            "collectors": [],
        }

        for session_id, collector in self.collectors.items():
            stats = collector.get_stats()
            total_stats["collectors"].append({
                "session_id": session_id,
                **stats
            })

            if stats.get("running"):
                total_stats["running_collectors"] += 1

            total_stats["total_updates"] += stats.get("total_updates", 0)
            total_stats["successful_updates"] += stats.get("successful_updates", 0)
            total_stats["failed_updates"] += stats.get("failed_updates", 0)
            total_stats["unique_matches"] += stats.get("unique_matches", 0)

        # 计算平均处理时间
        if total_stats["collectors"]:
            total_processing_time = sum(
                c.get("average_processing_time", 0)
                for c in total_stats["collectors"]
            )
            total_stats["average_processing_time"] = (
                total_processing_time / len(total_stats["collectors"])
            )

        return total_stats


# 全局管理器实例
_odds_manager: Optional[OddsCollectorManager] = None


def get_odds_manager() -> OddsCollectorManager:
    """
    获取全局赔率收集器管理器

    Returns:
        管理器实例
    """
    global _odds_manager
    if _odds_manager is None:
        _odds_manager = OddsCollectorManager()
    return _odds_manager
from typing import Dict

from .collector import OddsCollector
from src.cache.redis_manager import RedisManager

