from typing import Optional

"""数据收集器模块
负责从各种数据源收集足球相关数据，包含反爬对抗技术.
"""

# 传统采集器
from .base_collector import BaseCollector, CollectionResult, CollectorError
from .football_data_collector import FootballDataCollector
from .match_collector import MatchCollector

# 简化版FotMob采集器
from .enhanced_fotmob_collector import EnhancedFotMobCollector, create_fotmob_collector

__all__ = [
    # 传统采集器
    "BaseCollector",
    "CollectionResult",
    "CollectorError",
    "FootballDataCollector",
    "MatchCollector",

    # 简化版采集器
    "EnhancedFotMobCollector",
    "create_fotmob_collector",
]
