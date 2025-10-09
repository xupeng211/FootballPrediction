"""
管理器
Manager

管理多个比分收集器实例。
"""






class ScoresCollectorManager:
    """比分收集器管理器"""

    def __init__(self):
        """初始化管理器"""
        self.collectors: Dict[int, ScoresCollector] = {}
        self.global_stats = {
            "total_collectors": 0,
            "active_collectors": 0,
            "total_updates": 0,
            "average_processing_time": 0.0,
        }

    async def get_collector(self, session_id: int) -> ScoresCollector:
        """
        获取或创建收集器实例

        Args:
            session_id: 会话ID

        Returns:
            ScoresCollector: 收集器实例
        """
        if session_id not in self.collectors:
            # 创建新的数据库会话
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_session = db_manager.get_async_session()
            redis_manager = RedisManager()

            # 创建收集器
            collector = ScoresCollector(
                db_session=db_session,
                redis_manager=redis_manager,
            )
            self.collectors[session_id] = collector
            self.global_stats["total_collectors"] += 1

        return self.collectors[session_id]

    async def start_all(self):
        """启动所有收集器"""
        active_count = 0
        for collector in self.collectors.values():
            if not collector.running:
                await collector.start_collection()
                active_count += 1

        self.global_stats["active_collectors"] = active_count
        print(f"启动了 {active_count} 个比分收集器")

    async def stop_all(self):
        """停止所有收集器"""
        for collector in self.collectors.values():
            if collector.running:
                await collector.stop_collection()

        self.global_stats["active_collectors"] = 0
        print("已停止所有比分收集器")

    def remove_collector(self, session_id: int):
        """移除收集器"""
        if session_id in self.collectors:
            collector = self.collectors[session_id]
            if collector.running:
                # 停止收集器
                asyncio.create_task(collector.stop_collection())

            # 移除引用
            del self.collectors[session_id]
            self.global_stats["total_collectors"] -= 1
            print(f"移除收集器: {session_id}")

    def get_global_stats(self) -> Dict[str, any]:
        """获取全局统计信息"""
        # 计算聚合统计
        total_updates = sum(
            c.stats["total_updates"] for c in self.collectors.values()
        )
        successful_updates = sum(
            c.stats["successful_updates"] for c in self.collectors.values()
        )
        failed_updates = sum(
            c.stats["failed_updates"] for c in self.collectors.values()
        )

        # 计算平均处理时间
        all_times = [
            c.stats["average_processing_time"]
            for c in self.collectors.values()
            if c.stats["successful_updates"] > 0
        ]
        avg_time = sum(all_times) / len(all_times) if all_times else 0.0

        return {
            **self.global_stats,
            "total_updates": total_updates,
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "success_rate": successful_updates / total_updates * 100
            if total_updates > 0
            else 0.0,
            "average_processing_time": avg_time,
            "collectors": {
                session_id: {
                    "running": collector.running,
                    "stats": collector.stats,
                }
                for session_id, collector in self.collectors.items()
            },
        }

    def get_collector_stats(self, session_id: int) -> Optional[Dict[str, any]]:
        """获取指定收集器的统计信息"""
        collector = self.collectors.get(session_id)
        if collector:
            return collector.get_stats()
        return None

    async def health_check(self) -> Dict[str, any]:
        """健康检查"""
        healthy_collectors = 0
        issues = []

        for session_id, collector in self.collectors.items():
            try:
                # 检查收集器是否响应
                stats = collector.get_stats()
                if stats["running"]:
                    healthy_collectors += 1
                else:
                    issues.append(f"收集器 {session_id} 未运行")
            except Exception as e:
                issues.append(f"收集器 {session_id} 异常: {e}")

        return {
            "status": "healthy" if healthy_collectors > 0 else "unhealthy",
            "total_collectors": len(self.collectors),
            "healthy_collectors": healthy_collectors,
            "issues": issues,
        }


# 全局实例
_scores_manager: Optional[ScoresCollectorManager] = None


def get_scores_manager() -> ScoresCollectorManager:
    """
    获取全局比分收集器管理器

    Returns:
        ScoresCollectorManager: 管理器实例
    """
    global _scores_manager
    if _scores_manager is None:
        _scores_manager = ScoresCollectorManager()
    return _scores_manager
from typing import Dict
import asyncio


from .collector import ScoresCollector
from src.cache.redis_manager import RedisManager

