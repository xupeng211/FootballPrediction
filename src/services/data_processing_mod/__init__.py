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

# 从新的模块结构导入
from ..data_processing.pipeline_mod.stages import (
    BronzeToSilverProcessor,
    # SilverToGoldProcessor,  # 未使用
)
# from ..data_processing.pipeline_mod.pipeline import DataPipeline  # 未使用


# 创建兼容的类别名
class DataQualityValidator:
    """数据质量验证器（兼容类）"""

    def __init__(self):
        self.logger = __import__(
            "src.core.logging", fromlist=["get_logger"]
        ).get_logger(__name__)

    def validate(self, data):
        """验证数据质量"""
        return isinstance(data, dict) and bool(data)


class AnomalyDetector:
    """异常检测器（兼容类）"""

    def __init__(self):
        self.logger = __import__(
            "src.core.logging", fromlist=["get_logger"]
        ).get_logger(__name__)

    def detect(self, data):
        """检测异常"""
        return False  # 简单实现


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
