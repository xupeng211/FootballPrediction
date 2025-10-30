"""
预测仓储
Prediction Repository

提供预测数据的访问操作,实现Repository模式.
Provides prediction data access operations, implementing the Repository pattern.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.predictions import Predictions
from .base import BaseRepository 

# 类型别名
Prediction = Predictions


# 预测状态常量
class PredictionStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PredictionRepository(BaseRepository[Predictions]):
    """
    预测仓储类
    Prediction Repository Class

    提供预测数据的CRUD操作和复杂查询方法.
    Provides CRUD operations and complex query methods for prediction data.
    """

    def __init__(self, db_manager=None):
        super().__init__(Predictions, db_manager)

    # ========================================
    # 预测特定的查询方法
    # ========================================

    async def get_by_match(
        self,
        match_id: Union[int, str],
        status: Optional[PredictionStatus] = None,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[Prediction]:
        """
        获取指定比赛的预测

        Args:
            match_id: 比赛ID
            status: 预测状态（可选）
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            预测列表
        """
        filters = {"match_id": match_id}
        if status:
            filters["status"] = status if isinstance(status, str) else str(status)

        return await self.find_by(
            filters=filters, limit=limit
        )

    async def get_by_user(
        self, user_id: str
    ) -> List[Prediction]:
        """
        获取指定用户的预测

        Args:
            user_id: 用户ID
            status: 预测状态（可选）
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            预测列表
        """
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status if isinstance(status, PredictionStatus) else str(status)

        return await self.find_by(
            filters=filters
        )

    async def get_by_status(
        self, status: PredictionStatus
    ) -> List[Prediction]:
        """
        根据状态获取预测

        Args:
            status: 预测状态
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            预测列表
        """
        return await self.find_by(
            filters={"status": status if isinstance(status, PredictionStatus) else str(status)},
            limit=limit
        )

    async def get_pending_predictions(
        self, limit: Optional[int] = None
    ) -> List[Prediction]:
        """
        获取待处理的预测

        Args:
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            待处理预测列表
        """
        return await self.get_by_status(
            status=PredictionStatus.PENDING
        )

    async def get_completed_predictions(
        self, days: int = 7,
        limit: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Prediction]:
        """
        获取已完成的预测

        Args:
            days: 过去多少天
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            已完成预测列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                select(Prediction)
                .where(
                    and_(
                        Prediction.predicted_at >= start_date,
                        Prediction.status == PredictionStatus.COMPLETED,
                    )
                )
                .order_by(desc(Prediction.predicted_at))
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_user_prediction_for_match(
        self,
        user_id: Union[int, str],
        match_id: Union[int, str],
        session: Optional[AsyncSession] = None,
    ) -> Optional[Prediction]:
        """
        获取用户对特定比赛的预测

        Args:
            user_id: 用户ID
            match_id: 比赛ID
            session: 数据库会话

        Returns:
            预测对象或None
        """
        return await self.find_one_by(
            filters={"user_id": user_id, "match_id": match_id}, session=session
        )

    async def create_prediction(
        self,
        user_id: Union[int, str],
        match_id: Union[int, str],
        predicted_home_score: int,
        predicted_away_score: int,
        confidence: Optional[float] = None,
        model_version: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Prediction:
        """
        创建新预测

        Args:
            user_id: 用户ID
            match_id: 比赛ID
            predicted_home_score: 预测主队得分
            predicted_away_score: 预测客队得分
            confidence: 预测置信度（0-1）
            model_version: 模型版本
            session: 数据库会话

        Returns:
            创建的预测对象
        """
        prediction_data = {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home_score": predicted_home_score,
            "predicted_away_score": predicted_away_score,
            "status": PredictionStatus.PENDING,
            "created_at": datetime.utcnow(),
        }

        if confidence is not None:
            prediction_data["confidence"] = float(confidence)
        if model_version:
            prediction_data["model_version"] = model_version

        return await self.create(prediction_data, session=session)

    async def update_prediction_result(
        self,
        prediction_id: Union[int, str],
        actual_home_score: int,
        actual_away_score: int,
        is_correct: bool,
        points_earned: Optional[float] = None,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Prediction]:
        """
        更新预测结果

        Args:
            prediction_id: 预测ID
            actual_home_score: 实际主队得分
            actual_away_score: 实际客队得分
            is_correct: 预测是否正确
            points_earned: 获得积分
            session: 数据库会话

        Returns:
            更新后的预测对象
        """
        update_data = {
            "actual_home_score": actual_home_score,
            "actual_away_score": actual_away_score,
            "is_correct": is_correct,
            "status": PredictionStatus.COMPLETED,
            "evaluated_at": datetime.utcnow(),
        }

        if points_earned is not None:
            update_data["points_earned"] = points_earned

        return await self.update(obj_id=prediction_id, obj_data=update_data, session=session)

    async def cancel_prediction(
        self,
        prediction_id: Union[int, str],
        reason: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Prediction]:
        """
        取消预测

        Args:
            prediction_id: 预测ID
            reason: 取消原因
            session: 数据库会话

        Returns:
            更新后的预测对象
        """
        update_data = {
            "status": PredictionStatus.CANCELLED,
            "cancelled_at": datetime.utcnow(),
        }

        if reason:
            update_data["cancellation_reason"] = reason

        return await self.update(obj_id=prediction_id, obj_data=update_data, session=session)

    # ========================================
    # 统计方法
    # ========================================

    async def get_user_prediction_stats(
        self,
        user_id: Union[int, str],
        days: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        获取用户预测统计

        Args:
            user_id: 用户ID
            days: 统计天数（可选）
            session: 数据库会话

        Returns:
            统计数据字典
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 构建查询
            query = select(Prediction).where(Prediction.user_id == user_id)

            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                query = query.where(Prediction.created_at >= start_date)

            # 执行查询
            result = await sess.execute(query)
            predictions = result.scalars().all()

            # 计算统计数据
            stats = {
                "total": len(predictions),
                "pending": 0,
                "completed": 0,
                "cancelled": 0,
                "correct": 0,
                "wrong": 0,
                "accuracy": 0.0,
                "total_points": 0.0,
                "avg_confidence": 0.0,
            }

            total_confidence = 0
            confidence_count = 0

            for pred in predictions:
                # 状态统计
                if pred.status == PredictionStatus.PENDING:
                    stats["pending"] += 1
                elif pred.status == PredictionStatus.COMPLETED:
                    stats["completed"] += 1
                elif pred.status == PredictionStatus.CANCELLED:
                    stats["cancelled"] += 1

                # 准确性统计
                if pred.is_correct is not None:
                    if pred.is_correct:
                        stats["correct"] += 1
                    else:
                        stats["wrong"] += 1

                # 积分统计
                if pred.points_earned:
                    stats["total_points"] += pred.points_earned

                # 置信度统计
                if pred.confidence is not None:
                    total_confidence += float(pred.confidence)
                    confidence_count += 1

            # 计算准确率
            if stats["completed"] > 0 and (stats["correct"] + stats["wrong"]) > 0:
                stats["accuracy"] = stats["correct"] / (stats["correct"] + stats["wrong"])

            # 计算平均置信度
            if confidence_count > 0:
                stats["avg_confidence"] = total_confidence / confidence_count

            return stats

    async def get_match_prediction_summary(
        self, match_id: Union[int, str], session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        获取比赛预测汇总

        Args:
            match_id: 比赛ID
            session: 数据库会话

        Returns:
            预测汇总数据
        """
        async with self.db_manager.get_async_session():
            if session:
                pass

            # 获取所有预测
            predictions = await self.get_by_match(match_id, session=session)

            # 计算汇总数据
            summary = {
                "total_predictions": len(predictions),
                "pending": 0,
                "completed": 0,
                "avg_predicted_home_score": 0.0,
                "avg_predicted_away_score": 0.0,
                "home_win_predictions": 0,
                "away_win_predictions": 0,
                "draw_predictions": 0,
                "avg_confidence": 0.0,
            }

            total_home_score = 0
            total_away_score = 0
            total_confidence = 0
            confidence_count = 0

            for pred in predictions:
                # 状态统计
                if pred.status == PredictionStatus.PENDING:
                    summary["pending"] += 1
                elif pred.status == PredictionStatus.COMPLETED:
                    summary["completed"] += 1

                # 比分预测统计
                if pred.predicted_home_score is not None:
                    total_home_score += float(pred.predicted_home_score)
                if pred.predicted_away_score is not None:
                    total_away_score += float(pred.predicted_away_score)

                # 结果分布统计
                if pred.predicted_home_score and pred.predicted_away_score:
                    if pred.predicted_home_score > pred.predicted_away_score:
                        summary["home_win_predictions"] += 1
                    elif pred.predicted_home_score < pred.predicted_away_score:
                        summary["away_win_predictions"] += 1
                    else:
                        summary["draw_predictions"] += 1

                # 置信度统计
                if pred.confidence is not None:
                    total_confidence += float(pred.confidence)
                    confidence_count += 1

            # 计算平均值
            if len(predictions) > 0:
                summary["avg_predicted_home_score"] = total_home_score / len(predictions)
                summary["avg_predicted_away_score"] = total_away_score / len(predictions)

            if confidence_count > 0:
                summary["avg_confidence"] = total_confidence / confidence_count

            return summary

    async def get_top_predictors(
        self, days: int = 30, limit: int = 10, session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        获取顶级预测者排行榜

        Args:
            days: 统计天数
            limit: 返回数量限制
            session: 数据库会话

        Returns:
            预测者排行列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            start_date = datetime.utcnow() - timedelta(days=days)

            # 使用SQL查询计算每个用户的统计数据
            stmt = (
                select(
                    Prediction.user_id,
                    func.count(Prediction.id).label("total_predictions"),
                    func.sum(func.case([(Prediction.is_correct is True, 1)], else_=0)).label(
                        "correct_predictions"
                    ),
                    func.sum(Prediction.points_earned).label("total_points"),
                    func.avg(Prediction.confidence).label("avg_confidence"),
                )
                .where(
                    and_(
                        Prediction.predicted_at >= start_date,
                        Prediction.status == PredictionStatus.COMPLETED,
                    )
                )
                .group_by(Prediction.user_id)
                .order_by(desc("total_points"))
                .limit(limit)
            )

            result = await sess.execute(stmt)
            rows = result.all()

            # 转换为字典列表
            predictors = []
            for row in rows:
                accuracy = 0.0
                if row.correct_predictions and row.total_predictions:
                    accuracy = row.correct_predictions / row.total_predictions

                predictors.append(
                    {
                        "user_id": row.user_id,
                        "total_predictions": row.total_predictions,
                        "correct_predictions": row.correct_predictions,
                        "accuracy": accuracy,
                        "total_points": row.total_points or 0.0,
                        "avg_confidence": float(row.avg_confidence or 0.0),
                    }
                )

            return predictors

    # ========================================
    # 实现抽象方法
    # ========================================

    async def get_related_data(
        self,
        obj_id: Union[int, str],
        relation_name: str,
        session: Optional[AsyncSession] = None,
    ) -> Any:
        """
        获取预测的关联数据

        Args:
            obj_id: 预测ID
            relation_name: 关联名称（如 'user', 'match'）
            session: 数据库会话

        Returns:
            关联数据
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 根据关联名称加载不同的关联数据
            if relation_name == "user":
                stmt = (
                    select(Prediction)
                    .options(selectinload(Prediction.user))
                    .where(Prediction.id == obj_id)
                )
            elif relation_name == "match":
                stmt = (
                    select(Prediction)
                    .options(selectinload(Prediction.match))
                    .where(Prediction.id == obj_id)
                )
            else:
                return None

            result = await sess.execute(stmt)
            _prediction = result.scalar_one_or_none()

            if prediction:
                return getattr(prediction, relation_name, None)
            return None
