"""
足球预测系统数据处理服务模块
Football Prediction System Data Processing Service Module

提供数据清洗、处理和特征提取功能。
集成了足球数据清洗器和缺失值处理器。

Provides data cleaning, processing, and feature extraction functionality.
Integrates football data cleaner and missing data handler.

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.services.data_processing_mod import <class_name>

主要类 / Main Classes:
    DataProcessingService: 数据处理服务 / Data processing service

主要方法 / Main Methods:
    DataProcessingService.process_raw_match_data(): 处理原始比赛数据 / Process raw match data
    DataProcessingService.process_bronze_to_silver(): 处理青铜到银层数据 / Process bronze to silver layer data

使用示例 / Usage Example:
    ```python
    from src.services.data_processing_mod import DataProcessingService

    # 创建服务实例
    service = DataProcessingService()
    await service.initialize()

    # 处理数据
    result = await service.process_raw_match_data(raw_data)
    ```

依赖 / Dependencies:
    - src.data.processing.football_data_cleaner: 足球数据清洗器 / Football data cleaner
    - src.data.processing.missing_data_handler: 缺失值处理器 / Missing data handler
    - src.database.connection: 数据库连接管理 / Database connection management

重构历史 / Refactoring History:
    - 原始文件：972行，包含所有数据处理功能
    - 重构为模块化结构：
      - processors.py: 数据处理器（比赛、赔率、比分、特征）
      - pipeline.py: 数据处理管道（青铜到银层、质量验证、异常检测）
      - handlers.py: 特殊数据处理器（缺失数据、缺失比分、缺失队伍）
      - service.py: 核心数据处理服务
"""

from .data_processing_mod import (
    # 为了向后兼容性，从新的模块化结构中导入所有内容
    # 核心服务
    DataProcessingService,
    # 数据处理器
    MatchDataProcessor,
    OddsDataProcessor,
    ScoresDataProcessor,
    FeaturesDataProcessor,
    # 数据管道
    BronzeToSilverProcessor,
    DataQualityValidator,
    AnomalyDetector,
    # 处理器
    MissingDataHandler,
    MissingScoresHandler,
    MissingTeamDataHandler,
)

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
    "MissingTeamDataHandler",
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
