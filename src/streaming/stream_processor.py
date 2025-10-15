from typing import Any, Dict, List, Optional, Union

"""
流数据处理器
Stream Data Processor
"""

import asyncio
import logging

from src.core.logging import get_logger

logger = get_logger(__name__)


class StreamProcessor:
    """流数据处理器"""

    def __init__(self):
        """初始化流处理器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.is_running = False
        self._stats = {"processed_count": 0, "error_count": 0, "last_processed": None}

    async def start(self):
        """启动处理器"""
        self.is_running = True
        self.logger.info("Stream processor started")

    async def stop(self):
        """停止处理器"""
        self.is_running = False
        self.logger.info("Stream processor stopped")

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理消息"""
        try:
            # 简单处理逻辑
            self.stats["processed_count"] += 1
            self.stats["last_processed"] = message
            return {"status": "processed", "data": message}
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.stats["error_count"] += 1
            self.logger.error(f"Error processing message: {str(e)}")
            return {"status": "error", "error": str(e)}


class StreamProcessorManager:
    """流处理器管理器"""

    def __init__(self):
        """初始化管理器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.processors = {}
        self.is_running = False

    async def add_processor(self, name: str, processor: StreamProcessor):
        """添加处理器"""
        self.processors[name] = processor
        self.logger.info(f"Added processor: {name}")

    async def remove_processor(self, name: str):
        """移除处理器"""
        if name in self.processors:
            del self.processors[name]
            self.logger.info(f"Removed processor: {name}")

    async def start_all(self):
        """启动所有处理器"""
        self.is_running = True
        for processor in self.processors.values():
            await processor.start()

    async def stop_all(self):
        """停止所有处理器"""
        for processor in self.processors.values():
            await processor.stop()
        self.is_running = False


class ProcessingStatistics:
    """处理统计"""

    def __init__(self):
        """初始化统计"""
        self.start_time = None
        self.end_time = None
        self.total_processed = 0
        self.total_errors = 0

    def start_timing(self):
        """开始计时"""
        self.start_time = asyncio.get_event_loop().time()

    def stop_timing(self):
        """停止计时"""
        self.end_time = asyncio.get_event_loop().time()

    def record_processed(self):
        """记录处理"""
        self.total_processed += 1

    def record_error(self):
        """记录错误"""
        self.total_errors += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = 0
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time

        return {
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "duration": duration,
            "success_rate": (self.total_processed - self.total_errors)
            / max(self.total_processed, 1)
            * 100,
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        """初始化健康检查器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.last_check = None
        self.is_healthy = True

    async def check_health(self) -> bool:
        """检查健康状态"""
        try:
            # 简单的健康检查
            self.is_healthy = True
            self.last_check = asyncio.get_event_loop().time()
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"Health check failed: {str(e)}")
            self.is_healthy = False
            return False


# 向后兼容的导出
StreamProcessorManager = StreamProcessorManager  # 避免名称冲突
