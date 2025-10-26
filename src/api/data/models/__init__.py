"""
Models package for API data models
"""

try:
    from .league_models import LeagueQueryParams
    from .match_models import MatchQueryParams
    from .odds_models import OddsQueryParams
    from .team_models import TeamQueryParams

    # 为了向后兼容，提供简化的别名
    LeagueInfo = LeagueQueryParams
    MatchInfo = MatchQueryParams
    OddsInfo = OddsQueryParams
    TeamInfo = TeamQueryParams
except ImportError:
    # 如果模型文件不存在，创建基本的占位符类
    from pydantic import BaseModel

    class LeagueInfo(BaseModel):
        id: int
        name: str
        country: str

    class MatchInfo(BaseModel):
#         id: int  # 重复定义已注释
        home_team: str
        away_team: str

#     class OddsInfo(BaseModel):
#         id: int  # 重复定义已注释
        match_id: int
        home_win: float

#     class TeamInfo(BaseModel):
#         id: int  # 重复定义已注释
#         name: str  # 重复定义已注释

# 为了向后兼容，保持models包
__all__ = ["LeagueInfo", "MatchInfo", "OddsInfo", "TeamInfo"]
