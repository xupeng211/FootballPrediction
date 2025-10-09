"""
足球预测引擎核心模块
Football Prediction Engine Core Module

集成了机器学习模型、特征工程、数据收集和缓存管理，
提供高性能的比赛预测服务。

注意：此文件已重构为模块化结构，具体实现请查看 src/core/prediction/ 目录。
"""

from src.core.prediction import PredictionEngine
from src.core.prediction.config import PredictionConfig
from src.core.prediction.statistics import PredictionStatistics

# 为了向后兼容，从新模块导入所有内容

# 保持原有的导入方式
__all__ = [
    "PredictionEngine",
    "PredictionConfig",
    "PredictionStatistics",
]
