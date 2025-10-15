from typing import Any, Dict, List, Optional, Union

"""
命令和查询处理器
Command and Query Handlers

实现所有命令和查询的处理器。
Implements handlers for all commands and queries.
"""

import logging
from datetime import datetime
from decimal import Decimal

from ..database.connection import get_session
from ..database.models import User, Prediction
from .base import CommandHandler, QueryHandler
from .commands import (
    CreatePredictionCommand,
    UpdatePredictionCommand,
    DeletePredictionCommand,
    CreateUserCommand,
)
from .queries import (
    GetPredictionByIdQuery,
    GetPredictionsByUserQuery,
    GetUserStatsQuery,
    GetUpcomingMatchesQuery,
)
from .dto import (
    PredictionDTO,
    UserDTO,
    MatchDTO,
    PredictionStatsDTO,
    CommandResult,
)

logger = logging.getLogger(__name__)


# 预测命令处理器
class CreatePredictionHandler(CommandHandler):
    """创建预测处理器"""

    @property
    def command_type(self):
        return CreatePredictionCommand

    async def handle(self, command: CreatePredictionCommand) -> CommandResult:  # type: ignore
        """处理创建预测命令"""
        try:
            async with get_session() as session:  # type: ignore
                # 检查是否已经存在预测
                existing = await session.execute(
                    "SELECT id FROM predictions WHERE match_id = :match_id AND user_id = :user_id",
                    {"match_id": command.match_id, "user_id": command.user_id},
                )
                if existing.scalar():  # type: ignore
                    return CommandResult.failure_result(
                        ["用户已经对该比赛进行了预测"], "预测已存在"
                    )

                # 创建预测
                _prediction = Prediction(
                    match_id=command.match_id,
                    user_id=command.user_id,
                    predicted_home=command.predicted_home,
                    predicted_away=command.predicted_away,
                    confidence=Decimal(str(command.confidence)),
                    strategy_used=command.strategy_used,
                    notes=command.notes,
                    created_at=datetime.utcnow(),
                )

                session.add(prediction)
                await session.commit()
                await session.refresh(prediction)

                logger.info(f"创建预测成功: ID={prediction.id}")

                return CommandResult.success_result(
                    _data=PredictionDTO(
                        id=prediction.id,  # type: ignore
                        match_id=prediction.match_id,
                        user_id=prediction.user_id,  # type: ignore
                        predicted_home=prediction.predicted_home,  # type: ignore
                        predicted_away=prediction.predicted_away,  # type: ignore
                        confidence=float(prediction.confidence),  # type: ignore
                        strategy_used=prediction.strategy_used,  # type: ignore
                        notes=prediction.notes,  # type: ignore
                        created_at=prediction.created_at,  # type: ignore
                    ),
                    message="预测创建成功",
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"创建预测失败: {e}")
            return CommandResult.failure_result([str(e)], "创建预测失败")


class UpdatePredictionHandler(CommandHandler):
    """更新预测处理器"""

    @property
    def command_type(self):
        return UpdatePredictionCommand

    async def handle(self, command: UpdatePredictionCommand) -> CommandResult:  # type: ignore
        """处理更新预测命令"""
        try:
            async with get_session() as session:  # type: ignore
                _prediction = await session.get(Prediction, command.prediction_id)
                if not prediction:
                    return CommandResult.failure_result(["预测不存在"], "预测未找到")

                # 更新字段
                if command.predicted_home is not None:
                    prediction.predicted_home = command.predicted_home
                if command.predicted_away is not None:
                    prediction.predicted_away = command.predicted_away
                if command.confidence is not None:
                    prediction.confidence = Decimal(str(command.confidence))
                if command.strategy_used is not None:
                    prediction.strategy_used = command.strategy_used
                if command.notes is not None:
                    prediction.notes = command.notes

                prediction.updated_at = datetime.utcnow()

                await session.commit()
                await session.refresh(prediction)

                logger.info(f"更新预测成功: ID={prediction.id}")

                return CommandResult.success_result(
                    _data=PredictionDTO(
                        id=prediction.id,
                        match_id=prediction.match_id,
                        user_id=prediction.user_id,
                        predicted_home=prediction.predicted_home,
                        predicted_away=prediction.predicted_away,
                        confidence=float(prediction.confidence),
                        strategy_used=prediction.strategy_used,
                        notes=prediction.notes,
                        created_at=prediction.created_at,
                        updated_at=prediction.updated_at,
                    ),
                    message="预测更新成功",
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"更新预测失败: {e}")
            return CommandResult.failure_result([str(e)], "更新预测失败")


class DeletePredictionHandler(CommandHandler):
    """删除预测处理器"""

    @property
    def command_type(self):
        return DeletePredictionCommand

    async def handle(self, command: DeletePredictionCommand) -> CommandResult:  # type: ignore
        """处理删除预测命令"""
        try:
            async with get_session() as session:  # type: ignore
                _prediction = await session.get(Prediction, command.prediction_id)
                if not prediction:
                    return CommandResult.failure_result(["预测不存在"], "预测未找到")

                await session.delete(prediction)
                await session.commit()

                logger.info(f"删除预测成功: ID={command.prediction_id}")

                return CommandResult.success_result(
                    _data={"deleted_id": command.prediction_id}, message="预测删除成功"
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"删除预测失败: {e}")
            return CommandResult.failure_result([str(e)], "删除预测失败")


# 用户命令处理器
class CreateUserHandler(CommandHandler):
    """创建用户处理器"""

    @property
    def command_type(self):
        return CreateUserCommand

    async def handle(self, command: CreateUserCommand) -> CommandResult:  # type: ignore
        """处理创建用户命令"""
        try:
            async with get_session() as session:  # type: ignore
                _user = User(
                    username=command.username,
                    email=command.email,
                    password_hash=command.password_hash,
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow(),
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                logger.info(f"创建用户成功: ID={user.id}")

                return CommandResult.success_result(
                    _data=UserDTO(
                        id=user.id,  # type: ignore
                        username=user.username,  # type: ignore
                        email=user.email,  # type: ignore
                        is_active=user.is_active,  # type: ignore
                        total_points=0,
                        prediction_count=0,
                        success_rate=0.0,
                        created_at=user.created_at,  # type: ignore
                        last_login=user.last_login,  # type: ignore
                    ),
                    message="用户创建成功",
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"创建用户失败: {e}")
            return CommandResult.failure_result([str(e)], "创建用户失败")


# 查询处理器
class GetPredictionByIdHandler(QueryHandler):
    """根据ID获取预测处理器"""

    @property
    def query_type(self):
        return GetPredictionByIdQuery

    async def handle(self, query: GetPredictionByIdQuery) -> Optional[PredictionDTO]:  # type: ignore
        """处理获取预测查询"""
        try:
            async with get_session() as session:  # type: ignore
                _prediction = await session.get(Prediction, query.prediction_id)
                if not prediction:
                    return None

                return PredictionDTO(
                    id=prediction.id,
                    match_id=prediction.match_id,
                    user_id=prediction.user_id,
                    predicted_home=prediction.predicted_home,
                    predicted_away=prediction.predicted_away,
                    confidence=float(prediction.confidence),
                    strategy_used=prediction.strategy_used,
                    points_earned=prediction.points_earned,
                    accuracy_score=prediction.accuracy_score,
                    notes=prediction.notes,
                    created_at=prediction.created_at,
                    updated_at=prediction.updated_at,
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"获取预测失败: {e}")
            return None


class GetPredictionsByUserHandler(QueryHandler):
    """获取用户预测列表处理器"""

    @property
    def query_type(self):
        return GetPredictionsByUserQuery

    async def handle(self, query: GetPredictionsByUserQuery) -> List[PredictionDTO]:  # type: ignore
        """处理获取用户预测列表查询"""
        try:
            async with get_session() as session:  # type: ignore
                # 构建查询
                sql = """
                SELECT p.* FROM predictions p
                JOIN matches m ON p.match_id = m.id
                WHERE p.user_id = :user_id
                """
                params: Dict[str, Any] = {"user_id": query.user_id}

                if query.start_date:
                    sql += " AND m.match_date >= :start_date"
                    params["start_date"] = query.start_date

                if query.end_date:
                    sql += " AND m.match_date <= :end_date"
                    params["end_date"] = query.end_date

                sql += " ORDER BY p.created_at DESC"

                if query.limit:
                    sql += " LIMIT :limit"
                    params["limit"] = query.limit

                if query.offset:
                    sql += " OFFSET :offset"
                    params["offset"] = query.offset

                _result = await session.execute(sql, params)
                predictions = result.fetchall()

                return [
                    PredictionDTO(
                        id=p.id,
                        match_id=p.match_id,
                        user_id=p.user_id,
                        predicted_home=p.predicted_home,
                        predicted_away=p.predicted_away,
                        confidence=float(p.confidence),
                        strategy_used=p.strategy_used,
                        points_earned=p.points_earned,
                        accuracy_score=p.accuracy_score,
                        notes=p.notes,
                        created_at=p.created_at,
                        updated_at=p.updated_at,
                    )
                    for p in predictions
                ]

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"获取用户预测列表失败: {e}")
            return []


class GetUserStatsHandler(QueryHandler):
    """获取用户统计处理器"""

    @property
    def query_type(self):
        return GetUserStatsQuery

    async def handle(self, query: GetUserStatsQuery) -> Optional[PredictionStatsDTO]:  # type: ignore
        """处理获取用户统计查询"""
        try:
            async with get_session() as session:  # type: ignore
                # 获取基本统计
                stats_sql = """
                SELECT
                    COUNT(*) as total_predictions,
                    COUNT(CASE WHEN p.points_earned > 0 THEN 1 END) as successful_predictions,
                    COALESCE(SUM(p.points_earned), 0) as total_points,
                    COALESCE(AVG(p.confidence), 0) as average_confidence
                FROM predictions p
                WHERE p.user_id = :user_id
                """
                stats_result = await session.execute(
                    stats_sql, {"user_id": query.user_id}
                )
                _stats = stats_result.fetchone()

                if not stats or stats.total_predictions == 0:
                    return PredictionStatsDTO(
                        user_id=query.user_id,
                        total_predictions=0,
                        successful_predictions=0,
                        success_rate=0.0,
                        total_points=0,
                        average_confidence=0.0,
                        strategy_breakdown={},
                        recent_performance=[],
                    )

                success_rate = stats.successful_predictions / stats.total_predictions

                # 获取策略分布
                strategy_sql = """
                SELECT
                    strategy_used,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    SUM(points_earned) as total_points
                FROM predictions
                WHERE user_id = :user_id AND strategy_used IS NOT NULL
                GROUP BY strategy_used
                """
                strategy_result = await session.execute(
                    strategy_sql, {"user_id": query.user_id}
                )
                strategy_rows = strategy_result.fetchall()

                strategy_breakdown: Dict[str, Any] = {}
                for row in strategy_rows:
                    strategy_breakdown[row.strategy_used] = {
                        "count": row.count,
                        "average_confidence": float(row.avg_confidence),
                        "total_points": row.total_points,
                    }

                # 获取最近表现
                recent_sql = """
                SELECT
                    m.match_date,
                    p.predicted_home,
                    p.predicted_away,
                    m.home_score,
                    m.away_score,
                    p.points_earned,
                    p.accuracy_score
                FROM predictions p
                JOIN matches m ON p.match_id = m.id
                WHERE p.user_id = :user_id
                ORDER BY m.match_date DESC
                LIMIT 10
                """
                recent_result = await session.execute(
                    recent_sql, {"user_id": query.user_id}
                )
                recent_rows = recent_result.fetchall()

                recent_performance: List[Any] = []
                for row in recent_rows:
                    recent_performance.append(
                        {
                            "match_date": row.match_date.isoformat(),
                            "predicted_home": row.predicted_home,
                            "predicted_away": row.predicted_away,
                            "actual_home": row.home_score,
                            "actual_away": row.away_score,
                            "points_earned": row.points_earned,
                            "accuracy_score": float(row.accuracy_score)
                            if row.accuracy_score
                            else None,
                        }
                    )

                return PredictionStatsDTO(
                    user_id=query.user_id,
                    total_predictions=stats.total_predictions,
                    successful_predictions=stats.successful_predictions,
                    success_rate=success_rate,
                    total_points=stats.total_points,
                    average_confidence=float(stats.average_confidence),
                    strategy_breakdown=strategy_breakdown,
                    recent_performance=recent_performance,
                )

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"获取用户统计失败: {e}")
            return None


class GetUpcomingMatchesHandler(QueryHandler):
    """获取即将到来的比赛处理器"""

    @property
    def query_type(self):
        return GetUpcomingMatchesQuery

    async def handle(self, query: GetUpcomingMatchesQuery) -> List[MatchDTO]:  # type: ignore
        """处理获取即将到来的比赛查询"""
        try:
            async with get_session() as session:  # type: ignore
                # 构建查询
                sql = """
                SELECT * FROM matches
                WHERE match_date >= NOW()
                AND match_date <= NOW() + INTERVAL ':days_ahead days'
                """
                params: Dict[str, Any] = {"days_ahead": query.days_ahead}

                if query.competition:
                    sql += " AND competition = :competition"
                    params["competition"] = query.competition

                sql += " ORDER BY match_date ASC"

                if query.limit:
                    sql += " LIMIT :limit"
                    params["limit"] = query.limit

                if query.offset:
                    sql += " OFFSET :offset"
                    params["offset"] = query.offset

                _result = await session.execute(sql, params)
                _matches = result.fetchall()

                return [
                    MatchDTO(
                        id=m.id,
                        home_team=m.home_team,
                        away_team=m.away_team,
                        home_score=m.home_score,
                        away_score=m.away_score,
                        match_date=m.match_date,
                        status=m.status,
                        competition=m.competition,
                        venue=m.venue,
                        created_at=m.created_at,
                        updated_at=m.updated_at,
                    )
                    for m in matches
                ]

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"获取即将到来的比赛失败: {e}")
            return []


# 处理器集合类
class PredictionCommandHandlers:
    """预测命令处理器集合"""

    def __init__(self):
        self.create = CreatePredictionHandler()
        self.update = UpdatePredictionHandler()
        self.delete = DeletePredictionHandler()


class PredictionQueryHandlers:
    """预测查询处理器集合"""

    def __init__(self):
        self.get_by_id = GetPredictionByIdHandler()
        self.get_by_user = GetPredictionsByUserHandler()
        self.get_stats = GetUserStatsHandler()
        self.get_upcoming_matches = GetUpcomingMatchesHandler()


class UserCommandHandlers:
    """用户命令处理器集合"""

    def __init__(self):
        self.create = CreateUserHandler()
        self.update = UpdateUserHandler()


class UserQueryHandlers:
    """用户查询处理器集合"""

    def __init__(self):
        self.get_by_id = GetUserByIdHandler()
        self.get_stats = GetUserStatsHandler()


class MatchCommandHandlers:
    """比赛命令处理器集合"""

    def __init__(self):
        self.create = CreateMatchHandler()
        self.update = UpdateMatchHandler()


class MatchQueryHandlers:
    """比赛查询处理器集合"""

    def __init__(self):
        self.get_by_id = GetMatchByIdHandler()
        self.get_upcoming = GetUpcomingMatchesHandler()
        self.get_predictions = GetMatchPredictionsHandler()
