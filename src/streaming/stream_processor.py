"""
流数据处理器（向后兼容）
Stream Data Processor (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化流处理器。

Provides backward compatible exports for the modular stream processor.
"""

from .stream_processor import (

# 重新导出主要类和函数
    StreamProcessor,
    StreamProcessorManager,
    ProcessingStatistics,
    HealthChecker,
)

# 导出所有符号
__all__ = [
    "StreamProcessor",
    "StreamProcessorManager",
    "ProcessingStatistics",
    "HealthChecker",
]
