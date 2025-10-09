"""
数据API端点（向后兼容）
Data API Endpoints (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化API。

Provides complete data management API endpoints, including:
- 比赛数据查询
- 球队数据查询
- 联赛数据查询
- 比分和赔率数据
- 数据统计和分析
"""

from .data import router
from .data.models import TeamInfo, LeagueInfo, MatchInfo, OddsInfo

# 重新导出所有路由和模型以保持向后兼容

# 导出所有必要的符号以保持兼容性
__all__ = [
    "router",
    "TeamInfo",
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
]
