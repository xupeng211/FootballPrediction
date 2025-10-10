"""
monitor
管道监控

此模块从原始文件拆分而来。
This module was split from the original file.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.core.logging import get_logger

logger = get_logger(__name__)


class PipelineMonitor:
    """管道监控器"""

    def __init__(self):
        """初始化监控器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = {
            "total_processed": 0,
            "total_failed": 0,
            "total_time": 0.0,
            "start_time": None,
            "end_time": None,
        }

    def start_monitoring(self):
        """开始监控"""
        self.metrics["start_time"] = time.time()
        self.logger.info("Pipeline monitoring started")

    def stop_monitoring(self):
        """停止监控"""
        self.metrics["end_time"] = time.time()
        if self.metrics["start_time"]:
            duration = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_time"] = duration
        self.logger.info("Pipeline monitoring stopped")

    def record_success(self, execution_time: float):
        """记录成功执行"""
        self.metrics["total_processed"] += 1
        self.logger.debug(f"Pipeline executed successfully in {execution_time:.2f}s")

    def record_failure(self, error: str):
        """记录失败执行"""
        self.metrics["total_failed"] += 1
        self.logger.error(f"Pipeline execution failed: {error}")

    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        total = self.metrics["total_processed"] + self.metrics["total_failed"]
        success_rate = (
            (self.metrics["total_processed"] / total * 100) if total > 0 else 0
        )
        avg_time = (
            (self.metrics["total_time"] / self.metrics["total_processed"])
            if self.metrics["total_processed"] > 0
            else 0
        )

        return {
            "total_processed": self.metrics["total_processed"],
            "total_failed": self.metrics["total_failed"],
            "success_rate": f"{success_rate:.2f}%",
            "average_execution_time": f"{avg_time:.2f}s",
            "total_duration": f"{self.metrics['total_time']:.2f}s",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset(self):
        """重置监控指标"""
        self.metrics = {
            "total_processed": 0,
            "total_failed": 0,
            "total_time": 0.0,
            "start_time": None,
            "end_time": None,
        }
