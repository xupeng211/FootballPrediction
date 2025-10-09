"""
数据API模型
Data API Models
"""


from .common import TeamInfo, LeagueInfo, MatchInfo, OddsInfo
from .league_models import LeagueQueryParams, LeagueCreateRequest
from .match_models import MatchQueryParams, MatchCreateRequest, MatchUpdateRequest
from .odds_models import OddsQueryParams
from .team_models import TeamQueryParams, TeamCreateRequest, TeamUpdateRequest

__all__ = [
    # 基础模型
    "TeamInfo",
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
    # 查询参数模型
    "MatchQueryParams",
    "TeamQueryParams",
    "LeagueQueryParams",
    "OddsQueryParams",
    # 请求模型
    "MatchCreateRequest",
    "MatchUpdateRequest",
    "TeamCreateRequest",
    "TeamUpdateRequest",
    "LeagueCreateRequest",
]
