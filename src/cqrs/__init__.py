"""
CQRS模式实现
CQRS Pattern Implementation

实现命令查询职责分离模式.
Implements Command Query Responsibility Segregation pattern.
"""

from .base import Command, CommandHandler, Query, QueryHandler
from .bus import CommandBus, QueryBus, get_command_bus, get_query_bus
from .commands import ()
    CreateMatchCommand,
    CreatePredictionCommand,
    CreateUserCommand,
    DeletePredictionCommand,
    UpdateMatchCommand,
    UpdatePredictionCommand,
    UpdateUserCommand,

from .dto import ()
    MatchDTO,
    MatchStatsDTO,
    PredictionDTO,
    PredictionStatsDTO,
    UserDTO,


# GetPredictionAnalyticsQuery,  # 未使用
# GetLeaderboardQuery,  # 未使用
from .handlers import ()
    MatchCommandHandlers,
    MatchQueryHandlers,
    PredictionCommandHandlers,
    PredictionQueryHandlers,
    UserCommandHandlers,
    UserQueryHandlers,

from .queries import ()
    GetMatchByIdQuery,
    GetMatchPredictionsQuery,
    GetPredictionByIdQuery,
    GetPredictionsByUserQuery,
    GetUpcomingMatchesQuery,
    GetUserStatsQuery,


__all__ = [)
    # Base classes
    "Command",
    "Query",
    "CommandHandler",
    "QueryHandler",
    # Bus implementations
    "CommandBus",
    "QueryBus",
    "get_command_bus",
    "get_query_bus",
    # Commands
    "CreatePredictionCommand",
    "UpdatePredictionCommand",
    "DeletePredictionCommand",
    "CreateUserCommand",
    "UpdateUserCommand",
    "CreateMatchCommand",
    "UpdateMatchCommand",
    # Queries
    "GetPredictionByIdQuery",
    "GetPredictionsByUserQuery",
    "GetMatchPredictionsQuery",
    "GetUserStatsQuery",
    "GetMatchByIdQuery",
    "GetUpcomingMatchesQuery",
    # Handlers
    "PredictionCommandHandlers",
    "PredictionQueryHandlers",
    "UserCommandHandlers",
    "UserQueryHandlers",
    "MatchCommandHandlers",
    "MatchQueryHandlers",
    # DTOs
    "PredictionDTO",
    "UserDTO",
    "MatchDTO",
    "PredictionStatsDTO",
    "MatchStatsDTO",

