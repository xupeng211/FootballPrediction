"""
数据API模型
Data API Models
"""

from .common import TeamInfo, LeagueInfo, MatchInfo, OddsInfo
from .match_models import MatchQueryParams, MatchCreateRequest, MatchUpdateRequest
from .team_models import TeamQueryParams, TeamCreateRequest, TeamUpdateRequest
from .league_models import LeagueQueryParams, LeagueCreateRequest
from .odds_models import OddsQueryParams

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