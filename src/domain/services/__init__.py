"""
领域服务
Domain Services

包含跨多个聚合的业务逻辑.
Contains business logic that spans multiple aggregates.
"""

from .match_service import MatchDomainService
from .prediction_service import PredictionDomainService
from .scoring_service import ScoringService
from .team_service import TeamDomainService

__all__ = [
    "MatchDomainService",
    "PredictionDomainService",
    "ScoringService",
    "TeamDomainService",
]
