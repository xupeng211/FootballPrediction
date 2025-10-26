"""
football 主模块

此文件由长文件拆分工具自动生成

拆分策略: complexity_split
"""

# 导入拆分的模块
from .adapters.football_models import *

# 导出所有公共接口
__all__ = [
    "MatchStatus",
    "FootballMatch",
    "FootballTeam",
    "FootballPlayer",
    "FootballApiAdaptee",
    "ApiFootballAdaptee",
    "OptaDataAdaptee",
    "FootballDataTransformer",
    "FootballApiAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    "CompositeFootballAdapter",
    "FootballDataAdapter"
]