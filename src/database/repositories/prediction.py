"""
预测仓储

提供预测数据的访问操作。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from .base import BaseRepository, RepositoryConfig
from src.database.models.predictions import Prediction, PredictionStatus
from src.database.models.match import Match


class PredictionRepository(BaseRepository[Prediction]):
    """预测仓储类"""

    def __init__(self, session, config: Optional[RepositoryConfig] = None):
        super().__init__(session, Prediction, config or RepositoryConfig())

    # ==================== 基础查询 ====================

    async def get_by_match_id(self, match_id: int) -> List[Prediction]:
        """根据比赛ID获取所有预测"""
        return await self.find({"match_id": match_id})

    async def get_by_user_id(self, user_id: int, limit: int = 50) -> List[Prediction]:
        """根据用户ID获取预测列表"""
        stmt = (
            select(self.model_class)
            .where(self.model_class.user_id == user_id)
            .order_by(desc(self.model_class.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_prediction_for_match(
        self, user_id: int, match_id: int
    ) -> Optional[Prediction]:
        """获取用户对特定比赛的预测"""
        return await self.find_one({"user_id": user_id, "match_id": match_id})

    # ==================== 状态相关查询 ====================

    async def get_by_status(self, status: PredictionStatus) -> List[Prediction]:
        """根据状态获取预测列表"""
        return await self.find({"status": status})

    async def get_pending_predictions(self, limit: int = 100) -> List[Prediction]:
        """获取待处理的预测"""
        return await self.find(
            {"status": PredictionStatus.PENDING}, limit=limit, order_by="created_at"
        )

    async def get_processed_predictions(
        self, hours: int = 24, limit: int = 100
    ) -> List[Prediction]:
        """获取已处理的预测"""
        start_time = datetime.now() - timedelta(hours=hours)

        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.status == PredictionStatus.PROCESSED,
                    self.model_class.processed_at >= start_time,
                )
            )
            .order_by(desc(self.model_class.processed_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_verified_predictions(
        self, days: int = 7, limit: int = 100
    ) -> List[Prediction]:
        """获取已验证的预测"""
        start_time = datetime.now() - timedelta(days=days)

        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.status == PredictionStatus.VERIFIED,
                    self.model_class.verified_at >= start_time,
                )
            )
            .order_by(desc(self.model_class.verified_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 模型相关查询 ====================

    async def get_by_model_name(
        self, model_name: str, limit: int = 50
    ) -> List[Prediction]:
        """根据模型名称获取预测"""
        stmt = (
            select(self.model_class)
            .where(self.model_class.model_name == model_name)
            .order_by(desc(self.model_class.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_model_performance(
        self, model_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """获取模型性能统计"""
        start_date = datetime.now() - timedelta(days=days)

        # 获取已验证的预测
        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.model_name == model_name,
                    self.model_class.status == PredictionStatus.VERIFIED,
                    self.model_class.verified_at >= start_date,
                )
            )
            .options(selectinload(self.model_class.match))
        )

        result = await self.session.execute(stmt)
        predictions = result.scalars().all()

        if not predictions:
            return {
                "model_name": model_name,
                "total_predictions": 0,
                "accuracy": 0.0,
                "correct_predictions": 0,
                "profit_loss": 0.0,
                "roi": 0.0,
            }

        # 计算性能指标
        total = len(predictions)
        correct = 0
        total_stake = 0.0
        total_return = 0.0

        for pred in predictions:
            if pred.is_correct:
                correct += 1

            # 计算盈亏（如果有投注信息）
            if hasattr(pred, "stake") and hasattr(pred, "odds"):
                total_stake += pred.stake or 0
                if pred.is_correct and pred.odds:
                    total_return += (pred.stake or 0) * pred.odds

        accuracy = correct / total if total > 0 else 0.0
        profit_loss = total_return - total_stake
        roi = (profit_loss / total_stake * 100) if total_stake > 0 else 0.0

        return {
            "model_name": model_name,
            "total_predictions": total,
            "accuracy": accuracy,
            "correct_predictions": correct,
            "profit_loss": profit_loss,
            "roi": roi,
            "period_days": days,
        }

    async def get_all_model_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取所有模型的性能统计"""
        # 获取所有唯一的模型名称
        stmt = select(self.model_class.model_name).distinct()
        result = await self.session.execute(stmt)
        model_names = [row[0] for row in result.all()]

        # 获取每个模型的性能
        performances = []
        for model_name in model_names:
            performance = await self.get_model_performance(model_name, days)
            performances.append(performance)

        # 按准确率排序
        performances.sort(key=lambda x: x["accuracy"], reverse=True)
        return performances

    # ==================== 预测类型查询 ====================

    async def get_predictions_by_type(
        self, prediction_type: str, limit: int = 50
    ) -> List[Prediction]:
        """根据预测类型获取预测"""
        stmt = (
            select(self.model_class)
            .where(self.model_class.prediction_type == prediction_type)
            .order_by(desc(self.model_class.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_high_confidence_predictions(
        self, threshold: float = 0.8, limit: int = 20
    ) -> List[Prediction]:
        """获取高置信度预测"""
        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.confidence >= threshold,
                    self.model_class.status == PredictionStatus.PROCESSED,
                )
            )
            .order_by(desc(self.model_class.confidence))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 批量操作 ====================

    async def bulk_create_predictions(
        self, predictions: List[Dict[str, Any]]
    ) -> List[Prediction]:
        """批量创建预测"""
        entities = []
        for pred_data in predictions:
            prediction = self.model_class(**pred_data)
            entities.append(prediction)

        return await self.create_batch(entities)

    async def update_prediction_status(
        self,
        prediction_ids: List[int],
        status: PredictionStatus,
        processed_at: Optional[datetime] = None,
    ) -> int:
        """批量更新预测状态"""
        updates = {"status": status, "updated_at": datetime.now()}

        if processed_at:
            updates["processed_at"] = processed_at

        # 使用IN子句更新多个ID
        stmt = select(self.model_class).where(self.model_class.id.in_(prediction_ids))
        result = await self.session.execute(stmt)
        entities = result.scalars().all()

        for entity in entities:
            for key, value in updates.items():
                setattr(entity, key, value)

        await self.session.commit()
        return len(entities)

    async def verify_predictions(self, match_predictions: List[Dict[str, Any]]) -> int:
        """批量验证预测

        Args:
            match_predictions: 包含预测ID和实际结果的列表

        Returns:
            验证的预测数量
        """
        verified_count = 0
        current_time = datetime.now()

        for pred_data in match_predictions:
            prediction_id = pred_data.get("prediction_id")
            actual_result = pred_data.get("actual_result")
            actual_score = pred_data.get("actual_score")

            if not prediction_id:
                continue

            updates = {
                "status": PredictionStatus.VERIFIED,
                "verified_at": current_time,
                "updated_at": current_time,
            }

            if actual_result:
                updates["actual_result"] = actual_result

            if actual_score:
                updates["actual_score"] = actual_score

            updated = await self.update_batch({"id": prediction_id}, updates)
            if updated > 0:
                verified_count += 1

        return verified_count

    # ==================== 统计查询 ====================

    async def get_prediction_statistics(
        self, user_id: Optional[int] = None, days: int = 30
    ) -> Dict[str, Any]:
        """获取预测统计信息"""
        start_date = datetime.now() - timedelta(days=days)

        # 构建查询条件
        filters = [self.model_class.created_at >= start_date]

        if user_id:
            filters.append(self.model_class.user_id == user_id)

        # 总预测数
        total_stmt = select(func.count(self.model_class.id)).where(and_(*filters))
        total_result = await self.session.execute(total_stmt)
        total_predictions = total_result.scalar() or 0

        # 各状态统计
        status_stmt = (
            select(
                self.model_class.status, func.count(self.model_class.id).label("count")
            )
            .where(and_(*filters))
            .group_by(self.model_class.status)
        )

        status_result = await self.session.execute(status_stmt)
        status_counts = {status.value: count for status, count in status_result.all()}

        # 已验证的预测准确率
        verified_filters = filters + [
            self.model_class.status == PredictionStatus.VERIFIED
        ]

        verified_stmt = select(
            func.count(self.model_class.id).label("total"),
            func.sum(
                func.case((self.model_class.is_correct is True, 1), else_=0)
            ).label("correct"),
        ).where(and_(*verified_filters))

        verified_result = await self.session.execute(verified_stmt)
        verified_data = verified_result.first()

        accuracy = 0.0
        if verified_data and verified_data.total > 0:
            accuracy = verified_data.correct / verified_data.total

        return {
            "period_days": days,
            "user_id": user_id,
            "total_predictions": total_predictions,
            "status_counts": status_counts,
            "verified_predictions": verified_data.total if verified_data else 0,
            "correct_predictions": verified_data.correct if verified_data else 0,
            "accuracy": accuracy,
        }

    async def get_daily_prediction_volume(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取每日预测量统计"""
        start_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(
                func.date(self.model_class.created_at).label("date"),
                func.count(self.model_class.id).label("count"),
            )
            .where(self.model_class.created_at >= start_date)
            .group_by(func.date(self.model_class.created_at))
            .order_by("date")
        )

        result = await self.session.execute(stmt)
        return [{"date": str(date), "count": count} for date, count in result.all()]

    # ==================== 高级查询 ====================

    async def get_predictions_with_analysis(
        self, match_id: int
    ) -> List[Dict[str, Any]]:
        """获取带分析数据的预测"""
        stmt = (
            select(self.model_class)
            .options(
                selectinload(self.model_class.match),
                selectinload(self.model_class.features),
            )
            .where(self.model_class.match_id == match_id)
            .order_by(desc(self.model_class.confidence))
        )

        result = await self.session.execute(stmt)
        predictions = result.scalars().all()

        # 构建详细数据
        detailed_predictions = []
        for pred in predictions:
            pred_data = {
                "id": pred.id,
                "model_name": pred.model_name,
                "prediction_type": pred.prediction_type,
                "predicted_result": pred.predicted_result,
                "confidence": pred.confidence,
                "predicted_odds": pred.predicted_odds,
                "value_bet": pred.value_bet,
                "status": pred.status.value,
                "created_at": pred.created_at,
                "features": pred.features if hasattr(pred, "features") else [],
            }

            # 添加比赛信息
            if pred.match:
                pred_data["match"] = {
                    "id": pred.match.id,
                    "home_team": pred.match.home_team.name
                    if pred.match.home_team
                    else None,
                    "away_team": pred.match.away_team.name
                    if pred.match.away_team
                    else None,
                    "match_time": pred.match.match_time,
                    "status": pred.match.status.value,
                }

            detailed_predictions.append(pred_data)

        return detailed_predictions
