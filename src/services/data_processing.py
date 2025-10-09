"""
足球预测系统数据处理服务模块（兼容性垫片）
Football Prediction System Data Processing Service Module (Compatibility Shim)

⚠️ 已弃用：此文件仅用于向后兼容。
Deprecated: This file is for backward compatibility only.

请使用新路径：from src.services.data_processing_mod import DataProcessingService
Please use new path: from src.services.data_processing_mod import DataProcessingService
"""

# 动态导入以避免循环依赖
import warnings
import importlib

warnings.warn(
    "使用src.services.data_processing已弃用，请使用src.services.data_processing_mod",
    DeprecationWarning,
    stacklevel=2
)

# 动态导入模块
_mod = importlib.import_module("src.services.data_processing_mod")

# 重新导出所有内容
DataProcessingService = _mod.DataProcessingService
MatchDataProcessor = _mod.MatchDataProcessor
OddsDataProcessor = _mod.OddsDataProcessor
ScoresDataProcessor = _mod.ScoresDataProcessor
FeaturesDataProcessor = _mod.FeaturesDataProcessor
BronzeToSilverProcessor = _mod.BronzeToSilverProcessor
DataQualityValidator = _mod.DataQualityValidator
AnomalyDetector = _mod.AnomalyDetector
MissingDataHandler = _mod.MissingDataHandler
MissingScoresHandler = _mod.MissingScoresHandler
MissingTeamHandler = _mod.MissingTeamHandler

# 重新导出以保持原始接口
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
    "MissingTeamHandler",
]

# 原始实现已移至 src/services/data_processing_mod/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有功能：
# - DataProcessingService: 核心数据处理服务
#   - process_raw_match_data: 处理原始比赛数据
#   - process_raw_odds_data: 处理原始赔率数据
#   - process_features_data: 处理特征数据
#   - process_batch_matches: 批量处理比赛数据
#   - validate_data_quality: 验证数据质量
#   - detect_anomalies: 检测异常值
#   - process_bronze_to_silver: 处理青铜到银层数据
# - 各类专用处理器：
#   - MatchDataProcessor: 比赛数据处理器
#   - OddsDataProcessor: 赔率数据处理器
#   - ScoresDataProcessor: 比分数据处理器
#   - FeaturesDataProcessor: 特征数据处理器
#   - MissingDataHandler: 缺失数据处理器
#   - MissingScoresHandler: 缺失比分处理器
#   - MissingTeamDataHandler: 缺失队伍数据处理器
# - 数据管道组件：
#   - BronzeToSilverProcessor: 青铜到银层数据处理器
#   - DataQualityValidator: 数据质量验证器
#   - AnomalyDetector: 异常检测器
