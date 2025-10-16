""" 领域服务
Domain Services

包含跨多个聚合的业务逻辑.
Contains business logic that spans multiple aggregates.
"" from .match_service import MatchDomainServicefrom .prediction_service import PredictionDomainService

from .scoring_service import ScoringServicefrom .team_service import TeamDomainService


__all__ = [)
    "MatchDomainService",
    "PredictionDomainService",
    "ScoringService",
    "TeamDomainService",

