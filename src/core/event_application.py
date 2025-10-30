"""
事件驱动应用程序初始化
Event-Driven Application Initialization

提供事件系统的初始化和生命周期管理.
Provides event system initialization and lifecycle management.
"""

import logging
from typing import Optional

from ..events import get_event_bus, start_event_bus, stop_event_bus
from ..events.handlers import register_default_handlers
from .config import get_settings

logger = logging.getLogger(__name__)


class EventDrivenApplication:
    """事件驱动应用程序

    管理事件系统的生命周期.
    Manages the event system lifecycle.
    """

    def __init__(self):
        """初始化应用程序"""
        self._event_bus = get_event_bus()
        self._settings = get_settings()
        self._initialized = False

    async def initialize(self) -> None:
        """初始化事件系统"""
        if self._initialized:
            return

        try:
            logger.info("初始化事件驱动应用程序...")

            # 启动事件总线
            await start_event_bus()

            # 注册默认事件处理器
            await register_default_handlers()

            # 注册自定义事件处理器（如果需要）
            await self._register_custom_handlers()

            self._initialized = True
            logger.info("事件驱动应用程序初始化完成")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"事件系统初始化失败: {e}")
            raise

    async def shutdown(self) -> None:
        """关闭事件系统"""
        if not self._initialized:
            return

        try:
            logger.info("关闭事件驱动应用程序...")

            # 停止事件总线
            await stop_event_bus()

            self._initialized = False
            logger.info("事件驱动应用程序已关闭")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"事件系统关闭失败: {e}")

    async def _register_custom_handlers(self) -> None:
        """注册自定义事件处理器"""
        # 这里可以注册特定于应用程序的事件处理器
        # 例如:邮件发送处理器,WebSocket推送处理器等

        # 示例:注册一个简单的统计处理器
        from ..events.base import Event, EventHandler

        class SimpleStatsHandler(EventHandler):
            """简单统计处理器"""

            def __init__(self):
                super().__init__("SimpleStats")
                self.stats = {}

            async def handle(self, event: Event) -> None:
                """处理事件并更新统计"""
                event_type = event.get_event_type()
                self.stats[event_type] = self.stats.get(event_type, 0) + 1

            def get_handled_events(self) -> list[str]:
                return [
                    "prediction.made",
                    "prediction.updated",
                    "match.created",
                    "match.updated",
                    "user.registered",
                ]

        # 注册处理器
        stats_handler = SimpleStatsHandler()
        for event_type in stats_handler.get_handled_events():
            await self._event_bus.subscribe(event_type, stats_handler)

        logger.info("自定义事件处理器注册完成")

    def get_event_stats(self) -> dict:
        """获取事件统计信息"""
        return self._event_bus.get_stats()

    async def health_check(self) -> dict:
        """事件系统健康检查"""
        stats = self.get_event_stats()

        return {
            "status": ("healthy" if self._initialized and stats["running"] else "unhealthy"),
            "initialized": self._initialized,
            "event_bus_stats": stats,
            "handlers_count": stats["total_subscribers"],
            "active_tasks": stats["active_tasks"],
        }


# 全局应用程序实例
_app_instance: Optional[EventDrivenApplication] = None


def get_event_application() -> EventDrivenApplication:
    """获取全局事件应用程序实例"""
    global _app_instance
    if _app_instance is None:
        _app_instance = EventDrivenApplication()
    return _app_instance


# 便捷函数
async def initialize_event_system() -> None:
    """初始化事件系统"""
    app = get_event_application()
    await app.initialize()


async def shutdown_event_system() -> None:
    """关闭事件系统"""
    app = get_event_application()
    await app.shutdown()


async def get_event_system_health() -> dict:
    """获取事件系统健康状态"""
    app = get_event_application()
    return await app.health_check()
