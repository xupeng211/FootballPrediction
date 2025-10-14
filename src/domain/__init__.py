from typing import Any, Dict, List, Optional, Union
"""
领域层
Domain Layer

实现领域驱动设计（DDD）的核心概念，包含：
- 领域模型（Entities, Value Objects）
- 领域服务（Domain Services）
- 领域事件（Domain Events）

Implements core concepts of Domain-Driven Design (DDD), including:
- Domain models (Entities, Value Objects)
- Domain services
- Domain events
"""

from .models import (
    Match,
    MatchStatus,
    MatchResult,
    MatchScore,
    Prediction,
    PredictionStatus,
    ConfidenceScore,
    PredictionScore,
    PredictionPoints,
    Team,
    TeamStats,
    TeamForm,
    League,
    LeagueSeason,
    LeagueSettings,
)
from .services import (
    MatchDomainService,
    PredictionDomainService,
    ScoringService,
)
from .events import (
    MatchStartedEvent,
    MatchFinishedEvent,
    MatchCancelledEvent,
    MatchPostponedEvent,
    PredictionCreatedEvent,
    PredictionUpdatedEvent,
    PredictionEvaluatedEvent,
    PredictionCancelledEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
)
from .strategies import (
    PredictionStrategy,
    PredictionContext,
    PredictionInput,
    PredictionOutput,
    StrategyType,
    StrategyMetrics,
    MLModelStrategy,
    StatisticalStrategy,
    HistoricalStrategy,
    EnsembleStrategy,
    PredictionStrategyFactory,
    StrategyConfig,
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
