"""
数据仓库模块 - 单一入口点
从 repositories_main.py 导入所有仓库类，避免循环引用和命名冲突
"""

# 单一真理源：从目录内的 repositories_main.py 文件导入所有仓库类
from .repositories_main import (
    BaseRepository,
    TeamRepository,
    LeagueRepository,
    MatchRepository,
)

# 导出所有仓库类，提供统一的导入接口
__all__ = [
    "BaseRepository",
    "TeamRepository",
    "LeagueRepository",
    "MatchRepository",
]