"""
config 主模块

此文件由长文件拆分工具自动生成

拆分策略: strategy_split
"""

# 导入拆分的模块 - 暂时禁用,避免导入错误
# from .domain.strategies.config_historical import *
# from .domain.strategies.config_ml import *
# from .domain.strategies.config_statistical import *
# from .domain.strategies.config_ensemble import *


# 占位符类定义
class HistoricalConfig:
    """历史配置 - 占位符实现"""

    pass


class MLModelConfig:
    """机器学习模型配置 - 占位符实现"""

    pass


class StatisticalConfig:
    """统计配置 - 占位符实现"""

    pass


class EnsembleConfig:
    """集成配置 - 占位符实现"""

    pass


# 为了保持向后兼容,提供StrategyConfig别名
class StrategyConfig:
    """策略配置 - 占位符实现"""

    pass


# 导出所有公共接口
__all__ = [
    "HistoricalConfig",
    "MLModelConfig",
    "StatisticalConfig",
    "EnsembleConfig",
    "StrategyConfig",
]
