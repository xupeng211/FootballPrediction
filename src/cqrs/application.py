"""
CQRS应用服务
CQRS Application Services

提供高级的CQRS操作接口。
Provides high-level CQRS operation interfaces.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .bus import get_command_bus, get_query_bus
from .commands import (
    CreatePredictionCommand,
    UpdatePredictionCommand,
    DeletePredictionCommand,
    CreateUserCommand,
    UpdateUserCommand,
    CreateMatchCommand,
    UpdateMatchCommand,
)
from .queries import (
    GetPredictionByIdQuery,
    GetPredictionsByUserQuery,
    GetUserStatsQuery,
    GetMatchByIdQuery,
    GetUpcomingMatchesQuery,
    GetPredictionAnalyticsQuery,
    GetLeaderboardQuery,
)
from .dto import (
    PredictionDTO,
    MatchDTO,
    PredictionStatsDTO,
    CommandResult,
)
from .handlers import (
    PredictionCommandHandlers,
    PredictionQueryHandlers,
    UserCommandHandlers,
)

logger = logging.getLogger(__name__)

class PredictionCQRSService:
    """预测CQRS服务

    提供预测相关的命令和查询操作。
    Provides command and query operations for predictions.
    """

    def __init__(self):
        self.command_bus = get_command_bus()
        self.query_bus = get_query_bus()

    # 命令操作
    async def create_prediction(
        self,
        match_id: int,
        user_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: float,
        strategy_used: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> CommandResult:
        """创建预测"""
        command = CreatePredictionCommand(
            match_id=match_id,
            user_id=user_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            strategy_used=strategy_used,
            notes=notes,
        )
        return await self.command_bus.dispatch(command)

    async def update_prediction(
        self,
        prediction_id: int,
        predicted_home: Optional[int] = None,
        predicted_away: Optional[int] = None,
        confidence: Optional[float] = None,
        strategy_used: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> CommandResult:
        """更新预测"""
        command = UpdatePredictionCommand(
            prediction_id=prediction_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            strategy_used=strategy_used,
            notes=notes,
        )
        return await self.command_bus.dispatch(command)

    async def delete_prediction(self, prediction_id: int) -> CommandResult:
        """删除预测"""
        command = DeletePredictionCommand(prediction_id=prediction_id)
        return await self.command_bus.dispatch(command)

    # 查询操作
    async def get_prediction_by_id(self, prediction_id: int) -> Optional[PredictionDTO]:
        """根据ID获取预测"""
        query = GetPredictionByIdQuery(prediction_id=prediction_id)
        return await self.query_bus.dispatch(query)

    async def get_predictions_by_user(
        self,
        user_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[PredictionDTO]:
        """获取用户的所有预测"""
        query = GetPredictionsByUserQuery(
            user_id=user_id,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )
        return await self.query_bus.dispatch(query)

    async def get_user_stats(
        self, user_id: int, include_predictions: bool = False
    ) -> Optional[PredictionStatsDTO]:
        """获取用户统计"""
        query = GetUserStatsQuery(
            user_id=user_id, include_predictions=include_predictions
        )
        return await self.query_bus.dispatch(query)

class MatchCQRSService:
    """比赛CQRS服务

    提供比赛相关的命令和查询操作。
    Provides command and query operations for matches.
    """

    def __init__(self):
        self.command_bus = get_command_bus()
        self.query_bus = get_query_bus()

    # 命令操作
    async def create_match(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> CommandResult:
        """创建比赛"""
        command = CreateMatchCommand(
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            competition=competition,
            venue=venue,
        )
        return await self.command_bus.dispatch(command)

    async def update_match(
        self,
        match_id: int,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None,
        status: Optional[str] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> CommandResult:
        """更新比赛"""
        command = UpdateMatchCommand(
            match_id=match_id,
            home_score=home_score,
            away_score=away_score,
            status=status,
            competition=competition,
            venue=venue,
        )
        return await self.command_bus.dispatch(command)

    # 查询操作
    async def get_match_by_id(
        self, match_id: int, include_predictions: bool = False
    ) -> Optional[MatchDTO]:
        """根据ID获取比赛"""
        query = GetMatchByIdQuery(
            match_id=match_id, include_predictions=include_predictions
        )
        return await self.query_bus.dispatch(query)

    async def get_upcoming_matches(
        self,
        days_ahead: int = 7,
        competition: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[MatchDTO]:
        """获取即将到来的比赛"""
        query = GetUpcomingMatchesQuery(
            days_ahead=days_ahead, competition=competition, limit=limit, offset=offset
        )
        return await self.query_bus.dispatch(query)

class UserCQRSService:
    """用户CQRS服务

    提供用户相关的命令和查询操作。
    Provides command and query operations for users.
    """

    def __init__(self):
        self.command_bus = get_command_bus()
        self.query_bus = get_query_bus()

    # 命令操作
    async def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
    ) -> CommandResult:
        """创建用户"""
        command = CreateUserCommand(
            username=username, email=email, password_hash=password_hash
        )
        return await self.command_bus.dispatch(command)

    async def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> CommandResult:
        """更新用户"""
        command = UpdateUserCommand(
            user_id=user_id, username=username, email=email, is_active=is_active
        )
        return await self.command_bus.dispatch(command)

class AnalyticsCQRSService:
    """分析CQRS服务

    提供分析相关的查询操作。
    Provides analytics-related query operations.
    """

    def __init__(self):
        self.query_bus = get_query_bus()

    async def get_prediction_analytics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        strategy_filter: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取预测分析"""
        query = GetPredictionAnalyticsQuery(
            start_date=start_date,
            end_date=end_date,
            strategy_filter=strategy_filter,
            user_id=user_id,
        )
        return await self.query_bus.dispatch(query)

    async def get_leaderboard(
        self,
        period: str = "all_time",
        limit: Optional[int] = 10,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取排行榜"""
        query = GetLeaderboardQuery(period=period, limit=limit, offset=offset)
        return await self.query_bus.dispatch(query)

# CQRS服务工厂
class CQRSServiceFactory:
    """CQRS服务工厂"""

    @staticmethod
    def create_prediction_service() -> PredictionCQRSService:
        """创建预测服务"""
        return PredictionCQRSService()

    @staticmethod
    def create_match_service() -> MatchCQRSService:
        """创建比赛服务"""
        return MatchCQRSService()

    @staticmethod
    def create_user_service() -> UserCQRSService:
        """创建用户服务"""
        return UserCQRSService()

    @staticmethod
    def create_analytics_service() -> AnalyticsCQRSService:
        """创建分析服务"""
        return AnalyticsCQRSService()

# 便捷函数
async def initialize_cqrs():
    """初始化CQRS系统"""
    command_bus = get_command_bus()
    query_bus = get_query_bus()

    # 注册命令处理器
    prediction_command_handlers = PredictionCommandHandlers()
    command_bus.register_handler(
        CreatePredictionCommand, prediction_command_handlers.create
    )
    command_bus.register_handler(
        UpdatePredictionCommand, prediction_command_handlers.update
    )
    command_bus.register_handler(
        DeletePredictionCommand, prediction_command_handlers.delete
    )

    user_command_handlers = UserCommandHandlers()
    command_bus.register_handler(CreateUserCommand, user_command_handlers.create)

    # 注册查询处理器
    prediction_query_handlers = PredictionQueryHandlers()
    query_bus.register_handler(
        GetPredictionByIdQuery, prediction_query_handlers.get_by_id
    )
    query_bus.register_handler(
        GetPredictionsByUserQuery, prediction_query_handlers.get_by_user
    )
    query_bus.register_handler(GetUserStatsQuery, prediction_query_handlers.get_stats)
    query_bus.register_handler(
        GetUpcomingMatchesQuery, prediction_query_handlers.get_upcoming_matches
    )

    # 注册中间件
    from .bus import LoggingMiddleware, ValidationMiddleware

    command_bus.register_middleware(LoggingMiddleware())
    command_bus.register_middleware(ValidationMiddleware())
    query_bus.register_middleware(LoggingMiddleware())
    query_bus.register_middleware(ValidationMiddleware())

    logger.info("CQRS系统初始化完成")
