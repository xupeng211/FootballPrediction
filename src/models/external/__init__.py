"""外部数据模型
External Data Models for Football-Data.org API.
"""

from .competition import ExternalCompetition
from .match import ExternalMatch
from .team import ExternalTeam

__all__ = ["ExternalMatch", "ExternalTeam", "ExternalCompetition"]
