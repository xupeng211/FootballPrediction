"""
足球预测系统异常定义模块

定义系统中使用的所有自定义异常类。
"""


class FootballPredictionError(Exception):
    """足球预测系统基础异常类"""

    pass


class ConfigError(FootballPredictionError):
    """配置相关异常"""

    pass


class DataError(FootballPredictionError):
    """数据处理异常"""

    pass


class ModelError(FootballPredictionError):
    """模型相关异常"""

    pass


class PredictionError(FootballPredictionError):
    """预测相关异常"""

    pass
