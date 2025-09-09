"""
FootballPrediction - 基于机器学习的足球比赛结果预测系统

覆盖全球主要赛事的足球比赛结果预测，提供数据分析、特征工程、
模型训练和预测等核心功能模块。
"""

__version__ = "0.1.0"
__author__ = "FootballPrediction Team"
__email__ = "football@prediction.com"

# 导入核心模块
from . import core, models, services, utils

__all__ = [
    "core",
    "models",
    "services",
    "utils",
]
