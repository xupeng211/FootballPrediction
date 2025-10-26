"""
API data models package
"""

# 路由器在 data.py 文件中定义，这里不导入以避免循环依赖

# 数据模型现在位于 models 子目录中
try:
    from .models.league_models import LeagueQueryParams
    from .models.match_models import MatchQueryParams
    from .models.odds_models import OddsQueryParams
    from .models.team_models import TeamQueryParams

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

    class OddsInfo(BaseModel):
        #         id: int  # 重复定义已注释
        home_odds: float
        away_odds: float

    class TeamInfo(BaseModel):
        #         id: int  # 重复定义已注释
        #         name: str  # 重复定义已注释
        match_id: int
        home_win: float

#     class TeamInfo(BaseModel):
#         id: int  # 重复定义已注释
#         name: str  # 重复定义已注释

__all__ = ["LeagueInfo", "MatchInfo", "OddsInfo", "TeamInfo"]
