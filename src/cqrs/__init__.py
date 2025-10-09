"""
CQRS模式实现
CQRS Pattern Implementation

实现命令查询职责分离模式。
Implements Command Query Responsibility Segregation pattern.
"""

from .base import Command, Query, CommandHandler, QueryHandler
from .bus import CommandBus, QueryBus, get_command_bus, get_query_bus
from .commands import *
from .queries import *
from .handlers import *
from .dto import *

__all__ = [
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
]
