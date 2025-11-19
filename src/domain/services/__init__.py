from typing import Optional

"""领域服务
Domain Services.

包含跨多个聚合的业务逻辑.
Contains business logic that spans multiple aggregates.
"""

from src.domain.services.match_service import MatchDomainService
from src.domain.services.prediction_service import PredictionDomainService
from src.domain.services.scoring_service import ScoringService
from src.domain.services.team_service import TeamDomainService
from src.domain.services.user_service import UserService

__all__ = [
    "MatchDomainService",
    "PredictionDomainService",
    "ScoringService",
    "TeamDomainService",
    "UserService",
    "user_service",
]

# 为了兼容性，提供user_service作为UserService的实例
user_service = UserService()
