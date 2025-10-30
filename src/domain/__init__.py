"""
领域层
Domain Layer

实现领域驱动设计（DDD）的核心概念,包含:
- 领域模型（Entities, Value Objects）
- 领域服务（Domain Services）
- 领域事件（Domain Events）

Implements core concepts of Domain-Driven Design (DDD), including:
- Domain models (Entities, Value Objects)
- Domain services
- Domain events
"""

from .events import (
    MatchCancelledEvent,
    MatchFinishedEvent,
    MatchPostponedEvent,
    MatchStartedEvent,
    PredictionCancelledEvent,
    PredictionCreatedEvent,
    PredictionEvaluatedEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
    PredictionUpdatedEvent,
)
from .models import (
    ConfidenceScore,
    League,
    LeagueSeason,
    LeagueSettings,
    Match,
    MatchResult,
    MatchScore,
    MatchStatus,
    Prediction,
    PredictionPoints,
    PredictionScore,
    PredictionStatus,
    Team,
    TeamForm,
    TeamStats,
)
from .services import MatchDomainService, PredictionDomainService, ScoringService
from .strategies import (
    EnsembleStrategy,
    HistoricalStrategy,
    MLModelStrategy,
    PredictionContext,
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    PredictionStrategyFactory,
    StatisticalStrategy,
    StrategyConfig,
    StrategyMetrics,
    StrategyType,
)

__all__ = [
    # 领域模型
    "Match",
    "MatchStatus",
    "MatchResult",
    "MatchScore",
    "Prediction",
    "PredictionStatus",
    "ConfidenceScore",
    "PredictionScore",
    "PredictionPoints",
    "Team",
    "TeamStats",
    "TeamForm",
    "League",
    "LeagueSeason",
    "LeagueSettings",
    # 领域服务
    "MatchDomainService",
    "PredictionDomainService",
    "ScoringService",
    # 领域事件
    "MatchStartedEvent",
    "MatchFinishedEvent",
    "MatchCancelledEvent",
    "MatchPostponedEvent",
    "PredictionCreatedEvent",
    "PredictionUpdatedEvent",
    "PredictionEvaluatedEvent",
    "PredictionCancelledEvent",
    "PredictionExpiredEvent",
    "PredictionPointsAdjustedEvent",
    # 预测策略
    "PredictionStrategy",
    "PredictionContext",
    "PredictionInput",
    "PredictionOutput",
    "StrategyType",
    "StrategyMetrics",
    "MLModelStrategy",
    "StatisticalStrategy",
    "HistoricalStrategy",
    "EnsembleStrategy",
    "PredictionStrategyFactory",
    "StrategyConfig",
]
