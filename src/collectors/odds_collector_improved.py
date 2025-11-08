from .odds import (
    OddsAnalyzer,
    OddsCollector,  # 重新导出主要类和函数
    OddsCollectorManager,
    OddsProcessor,
    OddsSourceManager,
    OddsStorage,
    get_odds_manager,
)

"""
改进的赔率收集器（向后兼容）
Improved Odds Collector (Backward Compatible)

为了保持向后兼容性,此文件重新导出新的模块化赔率收集器.

Provides backward compatible exports for the modular odds collector.
"""

__all__ = [
    "OddsCollector",
    "OddsCollectorManager",
    "OddsSourceManager",
    "OddsProcessor",
    "OddsAnalyzer",
    "OddsStorage",
    "get_odds_manager",
]
