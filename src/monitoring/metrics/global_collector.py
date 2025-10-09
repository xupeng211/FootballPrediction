"""
全局指标收集器管理
Global Metrics Collector Management

管理全局的指标收集器实例和生命周期。
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, Optional

from src.core.config import get_settings

from .collectors import MetricsCollector

logger = logging.getLogger(__name__)

_settings = get_settings()

# 指标开关
ENABLE_METRICS = bool(_settings.metrics_enabled)
if ENABLE_METRICS and ("PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules):
    ENABLE_METRICS = False

# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器实例

    Returns:
        MetricsCollector: 指标收集器实例
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


async def start_metrics_collection() -> None:
    """
    启动监控指标收集
    """
    if not ENABLE_METRICS:
        logger.info("ENABLE_METRICS=false，跳过指标收集器启动")
        return

    collector = get_metrics_collector()
    await collector.start()


async def stop_metrics_collection() -> None:
    """
    停止监控指标收集
    """
    collector = get_metrics_collector()
    await collector.stop()


async def get_async_session():
    """
    获取异步数据库会话

    在测试环境中返回模拟会话
    """
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    return mock_session


class MetricsCollectorManager:
    """
    指标收集器管理器

    管理多个指标收集器实例的生命周期。
    """

    def __init__(self):
        """初始化管理器"""
        self.collectors: Dict[str, MetricsCollector] = {}
        self.running = False

    def register(self, name: str, collector: MetricsCollector):
        """
        注册指标收集器

        Args:
            name: 收集器名称
            collector: 收集器实例
        """
        self.collectors[name] = collector
        logger.info(f"注册指标收集器: {name}")

    def unregister(self, name: str):
        """
        注销指标收集器

        Args:
            name: 收集器名称
        """
        if name in self.collectors:
            del self.collectors[name]
            logger.info(f"注销指标收集器: {name}")

    async def start_all(self):
        """启动所有收集器"""
        for name, collector in self.collectors.items():
            try:
                await collector.start()
                logger.info(f"启动指标收集器: {name}")
            except Exception as e:
                logger.error(f"启动指标收集器失败 {name}: {e}")

        self.running = True
        logger.info("所有指标收集器已启动")

    async def stop_all(self):
        """停止所有收集器"""
        for name, collector in self.collectors.items():
            try:
                await collector.stop()
                logger.info(f"停止指标收集器: {name}")
            except Exception as e:
                logger.error(f"停止指标收集器失败 {name}: {e}")

        self.running = False
        logger.info("所有指标收集器已停止")

    def get_status(self) -> Dict[str, Any]:
        """
        获取所有收集器状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        status = {
            "manager_running": self.running,
            "collectors_count": len(self.collectors),
            "collectors": {},
        }

        for name, collector in self.collectors.items():
            status["collectors"][name] = collector.get_status()

        return status


# 全局管理器实例
_metrics_manager: Optional[MetricsCollectorManager] = None


def get_metrics_manager() -> MetricsCollectorManager:
    """
    获取全局指标管理器

    Returns:
        MetricsCollectorManager: 管理器实例
    """
    global _metrics_manager
    if _metrics_manager is None:
        _metrics_manager = MetricsCollectorManager()
    return _metrics_manager