"""
赔率收集模块
Odds Collection Module

提供高性能的赔率数据收集功能
"""


from .analyzer import OddsAnalyzer
from .collector import OddsCollector
from .manager import OddsCollectorManager
from .manager import get_odds_manager
from .processor import OddsProcessor
from .sources import OddsSourceManager
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
