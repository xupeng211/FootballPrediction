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

# 避免循环导入，直接创建路由器
from fastapi import APIRouter

router = APIRouter(prefix="/data", tags=["data"])
# 从 models 子目录导入数据模型
try:
    from .data.models.league_models import LeagueQueryParams
    from .data.models.match_models import MatchQueryParams
    from .data.models.odds_models import OddsQueryParams
    from .data.models.team_models import TeamQueryParams

    # 为了向后兼容，提供简化的别名
    LeagueInfo = LeagueQueryParams
    MatchInfo = MatchQueryParams
    OddsInfo = OddsQueryParams
    TeamInfo = TeamQueryParams
except ImportError:
    # 如果模型文件不存在，创建基本的占位符类
    from pydantic import BaseModel

    class LeagueInfo(BaseModel):  # type: ignore
        id: int
        name: str
        country: str

    class MatchInfo(BaseModel):  # type: ignore
        id: int
        home_team: str
        away_team: str

    class OddsInfo(BaseModel):  # type: ignore
        id: int
        match_id: int
        home_win: float

    class TeamInfo(BaseModel):  # type: ignore
        id: int
        name: str

# 重新导出所有路由和模型以保持向后兼容

# 导出所有必要的符号以保持兼容性
__all__ = [
    "router",
    "TeamInfo",
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
]
