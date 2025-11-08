from src.domain.services.match_service import MatchDomainService
from src.domain.services.prediction_service import PredictionDomainService
from src.domain.services.scoring_service import ScoringService
from src.domain.services.team_service import TeamDomainService

"""
领域服务
Domain Services

包含跨多个聚合的业务逻辑.
Contains business logic that spans multiple aggregates.
"""

__all__ = [
    "MatchDomainService",
    "PredictionDomainService",
    "ScoringService",
    "TeamDomainService",
]
