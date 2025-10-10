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


# 为了向后兼容，保持models包
__all__ = ["LeagueInfo", "MatchInfo", "OddsInfo", "TeamInfo"]
