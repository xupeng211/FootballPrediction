"""

"""



from .collector import ScoresCollector
from .data_sources import (
from .manager import ScoresCollectorManager, get_scores_manager
from .processor import ScoreDataProcessor
from .publisher import ScoreUpdatePublisher

比分收集模块
Scores Collection Module
提供实时比分数据收集功能，支持多数据源集成和WebSocket实时推送。
    FootballAPISource,
    ApiSportsSource,
    ScorebatSource,
)
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