"""
数据处理服务模块
Data Processing Service Module

提供足球数据的清洗、处理和特征提取功能。
"""

from .service import DataProcessingService
from .processors import (
    MatchDataProcessor,
    OddsDataProcessor,
    ScoresDataProcessor,
    FeaturesDataProcessor,
)
from .pipeline import (
    BronzeToSilverProcessor,
    DataQualityValidator,
    AnomalyDetector,
)
from .handlers import (
    MissingDataHandler,
    MissingScoresHandler,
    MissingTeamDataHandler,
)

__all__ = [
    # 核心服务
    "DataProcessingService",

    # 数据处理器
    "MatchDataProcessor",
    "OddsDataProcessor",
    "ScoresDataProcessor",
    "FeaturesDataProcessor",

    # 数据管道
    "BronzeToSilverProcessor",
    "DataQualityValidator",
    "AnomalyDetector",

    # 处理器
    "MissingDataHandler",
    "MissingScoresHandler",
    "MissingTeamDataHandler",
]