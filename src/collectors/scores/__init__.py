"""
比分收集模块
Scores Collection Module

提供实时比分数据收集功能，支持多数据源集成和WebSocket实时推送。
"""

from .collector import ScoresCollector
from .manager import ScoresCollectorManager, get_scores_manager
from .data_sources import (
    FootballAPISource,
    ApiSportsSource,
    ScorebatSource,
)
from .processor import ScoreDataProcessor
from .publisher import ScoreUpdatePublisher

__all__ = [
    "ScoresCollector",
    "ScoresCollectorManager",
    "get_scores_manager",
    "FootballAPISource",
    "ApiSportsSource",
    "ScorebatSource",
    "ScoreDataProcessor",
    "ScoreUpdatePublisher",
]