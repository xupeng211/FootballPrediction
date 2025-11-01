"""
外部数据模型
External Data Models for Football-Data.org API
"""

from .match import ExternalMatch
from .team import ExternalTeam
from .competition import ExternalCompetition

__all__ = ["ExternalMatch", "ExternalTeam", "ExternalCompetition"]
