"""
预测仓储
Prediction Repository

实现预测相关的数据访问逻辑.
Implements data access logic for predictions.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from ..database.models import Prediction
from .base import QuerySpec, ReadOnlyRepository, Repository


class PredictionRepositoryInterface(Repository[Prediction, int]):
    """预测仓储接口"""

    pass


class ReadOnlyPredictionRepository(ReadOnlyRepository[Prediction, int]):
    """只读预测仓储"""

    async def find_one(self, query_spec: QuerySpec) -> Optional[Prediction]:
        """查找单个预测"""
        query = select(Prediction)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_many(self, query_spec: QuerySpec) -> List[Prediction]:
        """查找多个预测"""
        query = select(Prediction)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.order_by:
                query = self._apply_order_by(query, query_spec.order_by)
            if query_spec.limit or query_spec.offset:
                query = self._apply_pagination(
                    query, query_spec.limit or 100, query_spec.offset or 0
                )
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, id: int) -> Optional[Prediction]:
        """根据ID获取预测"""
        query = select(Prediction).where(Prediction.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self, query_spec: Optional[QuerySpec] = None) -> List[Prediction]:
        """获取所有预测"""
        return await self.find_many(query_spec or QuerySpec())

    async def save(self, entity: Prediction) -> Prediction:
        """保存预测"""
        raise NotImplementedError("This is a read-only repository")

    async def delete(self, entity: Prediction) -> bool:
        """删除预测"""
        raise NotImplementedError("This is a read-only repository")

    async def exists(self, id: int) -> bool:
        """检查预测是否存在"""
        query = select(func.count(Prediction.id)).where(Prediction.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0

    async def get_predictions_by_user(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Prediction]:
        """获取用户的所有预测"""
        filters = {"user_id": user_id}
        if start_date:
            filters["match"] = {"match_date": {"$gte": start_date}}
        if end_date:
            filters["match"] = {"match_date": {"$lte": end_date}}

        query_spec = QuerySpec(
            filters=filters,
            order_by=["-created_at"],
            limit=limit,
            offset=offset,
            include=["match"],
        )

        return await self.find_many(query_spec)

    async def get_predictions_by_match(
        self, match_id: int, include_user_details: bool = False
    ) -> List[Prediction]:
        """获取比赛的所有预测"""
        filters = {"match_id": match_id}
        includes = ["match"]
        if include_user_details:
            includes.append("user")

        query_spec = QuerySpec(filters=filters, include=includes, order_by=["created_at"])

        return await self.find_many(query_spec)

    async def get_user_statistics(
        self, user_id: int, period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取用户统计信息"""
        query = select(
            func.count(Prediction.id).label("total_predictions"),
            func.avg(Prediction.confidence).label("avg_confidence"),
            func.sum(func.case((Prediction.is_correct, 1), else_=0)).label(
                "successful_predictions"
            ),
        ).where(Prediction.user_id == user_id)

        if period_days:
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=period_days)
            query = query.where(Prediction.created_at >= cutoff_date)

        result = await self.session.execute(query)
        stats = result.first()

        if not stats or stats.total_predictions == 0:
            return {
                "total_predictions": 0,
                "successful_predictions": 0,
                "success_rate": 0.0,
                "total_points": 0,
                "average_confidence": 0.0,
            }

        return {
            "total_predictions": stats.total_predictions,
            "successful_predictions": stats.successful_predictions or 0,
            "success_rate": (
                (stats.successful_predictions / stats.total_predictions)
                if stats.total_predictions > 0
                else 0.0
            ),
            "total_points": stats.successful_predictions or 0,  # 用成功预测数作为积分
            "average_confidence": float(stats.avg_confidence or 0),
        }

    async def get_match_statistics(self, match_id: int) -> Dict[str, Any]:
        """获取比赛统计信息"""
        query = select(
            func.count(Prediction.id).label("total_predictions"),
            func.avg(Prediction.confidence).label("avg_confidence"),
        ).where(Prediction.match_id == match_id)

        result = await self.session.execute(query)
        stats = result.first()

        # 获取预测分布
        distribution_query = (
            select(
                Prediction.predicted_home,
                Prediction.predicted_away,
                func.count(Prediction.id).label("count"),
            )
            .where(Prediction.match_id == match_id)
            .group_by(Prediction.predicted_home, Prediction.predicted_away)
        )

        distribution_result = await self.session.execute(distribution_query)
        distribution = [
            {
                "predicted_home": row.predicted_home,
                "predicted_away": row.predicted_away,
                "count": row.count,
            }
            for row in distribution_result.fetchall()
        ]

        return {
            "total_predictions": stats.total_predictions or 0,
            "average_confidence": float(stats.avg_confidence or 0),
            "prediction_distribution": distribution,
        }


class PredictionRepository(PredictionRepositoryInterface):
    """预测仓储实现"""

    async def get_by_id(self, id: int) -> Optional[Prediction]:
        """根据ID获取预测"""
        query = select(Prediction).where(Prediction.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self, query_spec: Optional[QuerySpec] = None) -> List[Prediction]:
        """获取所有预测"""
        query = select(Prediction)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.order_by:
                query = self._apply_order_by(query, query_spec.order_by)
            if query_spec.limit or query_spec.offset:
                query = self._apply_pagination(
                    query, query_spec.limit or 100, query_spec.offset or 0
                )
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one(self, query_spec: QuerySpec) -> Optional[Prediction]:
        """查找单个预测"""
        query = select(Prediction)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_many(self, query_spec: QuerySpec) -> List[Prediction]:
        """查找多个预测"""
        return await self.get_all(query_spec)

    async def save(self, entity: Prediction) -> Prediction:
        """保存预测"""
        if entity.id is None:
            self.session.add(entity)
        else:
            entity.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Prediction) -> bool:
        """删除预测"""
        try:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            await self.session.rollback()
            return False

    async def exists(self, id: int) -> bool:
        """检查预测是否存在"""
        query = select(func.count(Prediction.id)).where(Prediction.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0

    async def create(self, entity_data: Dict[str, Any]) -> Prediction:
        """创建新预测"""
        _prediction = Prediction(
            match_id=entity_data["match_id"],
            user_id=entity_data["user_id"],
            predicted_home=entity_data["predicted_home"],
            predicted_away=entity_data["predicted_away"],
            confidence=Decimal(str(entity_data["confidence"])),
            strategy_used=entity_data.get("strategy_used"),
            notes=entity_data.get("notes"),
            created_at=datetime.utcnow(),
        )

        self.session.add(prediction)
        await self.session.commit()
        await self.session.refresh(prediction)
        return prediction

    async def update_by_id(self, id: int, update_data: Dict[str, Any]) -> Optional[Prediction]:
        """根据ID更新预测"""
        query = update(Prediction).where(Prediction.id == id)

        # 更新时间戳
        update_data["updated_at"] = datetime.utcnow()

        # 处理特殊字段
        if "confidence" in update_data:
            update_data["confidence"] = Decimal(str(update_data["confidence"]))

        # 构建更新语句
        for key, value in update_data.items():
            query = query.values({getattr(Prediction, key): value})

        result = await self.session.execute(query)
        await self.session.commit()

        if result.rowcount > 0:
            return await self.get_by_id(id)
        return None

    async def delete_by_id(self, id: int) -> bool:
        """根据ID删除预测"""
        query = delete(Prediction).where(Prediction.id == id)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def bulk_create(self, entities_data: List[Dict[str, Any]]) -> List[Prediction]:
        """批量创建预测"""
        predictions = []
        for data in entities_data:
            _prediction = Prediction(
                match_id=data["match_id"],
                user_id=data["user_id"],
                predicted_home=data["predicted_home"],
                predicted_away=data["predicted_away"],
                confidence=Decimal(str(data["confidence"])),
                strategy_used=data.get("strategy_used"),
                notes=data.get("notes"),
                created_at=datetime.utcnow(),
            )
            predictions.append(prediction)

        self.session.add_all(predictions)
        await self.session.commit()

        # 刷新所有实体
        for prediction in predictions:
            await self.session.refresh(prediction)

        return predictions

    def get_read_only_repository(self) -> ReadOnlyPredictionRepository:
        """获取只读仓储"""
        return ReadOnlyPredictionRepository(self.session, self.model_class)
