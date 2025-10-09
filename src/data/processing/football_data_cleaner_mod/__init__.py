"""
足球数据清洗器模块

提供模块化的足球数据清洗功能，包括：
- 时间处理器：时间统一转换
- ID映射器：球队和联赛ID映射
- 数据验证器：数据有效性检查
- 赔率处理器：赔率数据清洗
- 主清洗器：协调各子模块
"""

# 导入核心类
from .cleaner import FootballDataCleaner

# 导入子模块处理器
from .time_processor import TimeProcessor
from .id_mapper import IDMapper
from .data_validator import DataValidator
from .odds_processor import OddsProcessor

# 导出所有公共接口
__all__ = [
    # 核心类
    "FootballDataCleaner",
    # 子模块处理器
    "TimeProcessor",
    "IDMapper",
    "DataValidator",
    "OddsProcessor",
]

# 版本信息
__version__ = "1.0.0"
