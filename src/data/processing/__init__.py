
"""
数据处理模块

提供足球数据的清洗、标准化和缺失值处理功能。
基于 DATA_DESIGN.md 的设计实现数据质量保证。

主要组件：
- FootballDataCleaner: 足球数据清洗器
- MissingDataHandler: 缺失数据处理器
"""


from typing import cast, Any, Optional, Union

from .football_data_cleaner import FootballDataCleaner
from .missing_data_handler import MissingDataHandler

__all__ = ["FootballDataCleaner", "MissingDataHandler"]
