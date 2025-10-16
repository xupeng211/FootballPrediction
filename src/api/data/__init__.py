""" API data models package
"" # 路由器在 data.py 文件中定义,这里不导入以避免循环依赖

# 数据模型现在位于 models 子目录中
try:
    .models.league_models import LeagueQueryParams
    .models.match_models import MatchQueryParams
    .models.odds_models import OddsQueryParams
    .models.team_models import TeamQueryParams

    # 为了向后兼容,提供简化的别名
    LeagueInfo = LeagueQueryParams
    MatchInfo = MatchQueryParams
    OddsInfo = OddsQueryParams
    TeamInfo = TeamQueryParamsexcept ImportError:

    # 如果模型文件不存在,创建基本的占位符类
    from pydantic import BaseModel

    class LeagueInfo(BaseModel)
:  # type: ignore
    "id": int
    "name": str
    "country": str

    class MatchInfo(BaseModel)
:  # type: ignore
    "id": int
    "home_team": str
    "away_team": str

    class OddsInfo(BaseModel)
:  # type: ignore
    "id": int
    "match_id": int
    "home_win": float

    class TeamInfo(BaseModel)
:  # type: ignore
    "id": int
    "name": str


__all__ = ["LeagueInfo", "MatchInfo", "OddsInfo", "TeamInfo"]
