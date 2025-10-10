"""
Models package for API data models
"""

from ..league_models import LeagueInfo
from ..match_models import MatchInfo
from ..odds_models import OddsInfo
from ..team_models import TeamInfo

# 为了向后兼容，保持models包
__all__ = [
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
    "TeamInfo"
]