"""
赔率收集模块
Odds Collection Module

提供高性能的赔率数据收集功能
"""

from .collector import OddsCollector
from .manager import OddsCollectorManager
from .sources import OddsSourceManager
from .processor import OddsProcessor
from .analyzer import OddsAnalyzer
from .storage import OddsStorage

# 导出主要接口
__all__ = [
    "OddsCollector",
    "OddsCollectorManager",
    "OddsSourceManager",
    "OddsProcessor",
    "OddsAnalyzer",
    "OddsStorage",
    "get_odds_manager",
]

# 导入全局管理器
from .manager import get_odds_manager