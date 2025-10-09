"""
特征计算器模块

提供模块化的特征计算功能，包括：
- 近期战绩特征计算
- 历史对战特征计算
- 赔率特征计算
- 批量计算和缓存优化
- 统计工具函数
"""

# 导入核心类
from .core import FeatureCalculator

# 导入子模块计算器
from .recent_performance import RecentPerformanceCalculator
from .historical_matchup import HistoricalMatchupCalculator
from .odds_features import OddsFeaturesCalculator
from .batch_calculator import BatchCalculator

# 导入工具类
from .statistics_utils import StatisticsUtils

# 为了向后兼容，重新导出统计工具函数
stats_utils = StatisticsUtils()

# 导出所有公共接口
__all__ = [
    # 核心类
    "FeatureCalculator",
    # 子模块计算器
    "RecentPerformanceCalculator",
    "HistoricalMatchupCalculator",
    "OddsFeaturesCalculator",
    "BatchCalculator",
    # 工具类
    "StatisticsUtils",
    # 向后兼容的统计函数
    "stats_utils",
]


# 为了向后兼容，添加统计函数的别名
def calculate_mean(data):
    """计算均值（向后兼容函数）"""
    return stats_utils.calculate_mean(data)


def calculate_std(data):
    """计算标准差（向后兼容函数）"""
    return stats_utils.calculate_std(data)


def calculate_min(data):
    """计算最小值（向后兼容函数）"""
    return stats_utils.calculate_min(data)


def calculate_max(data):
    """计算最大值（向后兼容函数）"""
    return stats_utils.calculate_max(data)


def calculate_rolling_mean(data, window: int = 3):
    """计算滚动均值（向后兼容函数）"""
    return stats_utils.calculate_rolling_mean(data, window)


# 添加到导出列表
__all__.extend(
    [
        "calculate_mean",
        "calculate_std",
        "calculate_min",
        "calculate_max",
        "calculate_rolling_mean",
    ]
)
