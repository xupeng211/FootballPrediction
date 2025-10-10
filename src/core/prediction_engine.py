"""
足球预测引擎核心模块
Football Prediction Engine Core Module

集成了机器学习模型、特征工程、数据收集和缓存管理，
提供高性能的比赛预测服务。

注意：此文件已重构为模块化结构，具体实现请查看 src/core/prediction/ 目录。
"""

# 延迟导入以避免循环导入
PredictionEngine = None
PredictionConfig = None
PredictionStatistics = None


def _lazy_import():
    """延迟导入以避免循环导入"""
    global PredictionEngine, PredictionConfig, PredictionStatistics
    if PredictionEngine is None:
        from .prediction import PredictionEngine as _PE
        from .prediction.config import PredictionConfig as _PC
        from .prediction.statistics import PredictionStatistics as _PS

        PredictionEngine = _PE
        PredictionConfig = _PC
        PredictionStatistics = _PS


# 保持原有的导入方式
__all__ = [
    "PredictionEngine",
    "PredictionConfig",
    "PredictionStatistics",
]
