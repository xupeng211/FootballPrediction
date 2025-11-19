"""数据收集器模块
负责从各种数据源收集足球相关数据.
"""

from .base_collector import BaseCollector, CollectionResult, CollectorError
from .football_data_collector import FootballDataCollector
from .match_collector import MatchCollector

__all__ = [
    "BaseCollector",
    "CollectionResult",
    "CollectorError",
    "FootballDataCollector",
    "MatchCollector",
]
