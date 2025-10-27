"""
比赛仓储
Match Repository

实现比赛相关的数据访问逻辑。
Implements data access logic for matches.
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import func, select, update

from ..database.models import Match
from .base import QuerySpec, ReadOnlyRepository, Repository


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class MatchRepositoryInterface(Repository[Match, int]):
    """比赛仓储接口"""

    pass


class ReadOnlyMatchRepository(ReadOnlyRepository[Match, int]):
    """只读比赛仓储"""

    async def find_one(self, query_spec: QuerySpec) -> Optional[Match]:
        """查找单个比赛"""
        query = select(Match)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_many(self, query_spec: QuerySpec) -> List[Match]:
        """查找多个比赛"""
        query = select(Match)

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

    async def get_by_id(self, id: int) -> Optional[Match]:
        """根据ID获取比赛"""
        query = select(Match).where(Match.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self, query_spec: Optional[QuerySpec] = None) -> List[Match]:
        """获取所有比赛"""
        return await self.find_many(query_spec or QuerySpec())

    async def save(self, entity: Match) -> Match:
        """保存比赛"""
        raise NotImplementedError("This is a read-only repository")

    async def delete(self, entity: Match) -> bool:
        """删除比赛"""
        raise NotImplementedError("This is a read-only repository")

    async def exists(self, id: int) -> bool:
        """检查比赛是否存在"""
        query = select(func.count(Match.id)).where(Match.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0

    async def get_matches_by_date_range(
        self,
        start_date: date,
        end_date: date,
        status: Optional[MatchStatus] = None,
        limit: int = 100,
    ) -> List[Match]:
        """获取指定日期范围内的比赛"""
        filters = {"match_date": {"$gte": start_date, "$lte": end_date}}
        if status:
            filters["status"] = status.value

        query_spec = QuerySpec(filters=filters, order_by=["match_date"], limit=limit)
        return await self.find_many(query_spec)

    async def get_upcoming_matches(self, days: int = 7, limit: int = 50) -> List[Match]:
        """获取即将到来的比赛"""
        start_date = date.today()
        end_date = start_date + timedelta(days=days)

        filters = {
            "match_date": {"$gte": start_date, "$lte": end_date},
            "status": MatchStatus.SCHEDULED.value,
        }

        query_spec = QuerySpec(filters=filters, order_by=["match_date"], limit=limit)
        return await self.find_many(query_spec)

    async def get_live_matches(self) -> List[Match]:
        """获取正在进行的比赛"""
        filters = {"status": MatchStatus.LIVE.value}
        query_spec = QuerySpec(filters=filters, order_by=["match_date"])
        return await self.find_many(query_spec)

    async def get_finished_matches(
        self, days: int = 30, limit: int = 100
    ) -> List[Match]:
        """获取已结束的比赛"""
        start_date = date.today() - timedelta(days=days)

        filters = {
            "match_date": {"$gte": start_date},
            "status": MatchStatus.FINISHED.value,
        }

        query_spec = QuerySpec(filters=filters, order_by=["-match_date"], limit=limit)
        return await self.find_many(query_spec)

    async def get_matches_by_team(self, team_id: int, limit: int = 50) -> List[Match]:
        """获取指定队伍的比赛"""
        filters = {"$or": [{"home_team_id": team_id}, {"away_team_id": team_id}]}

        query_spec = QuerySpec(filters=filters, order_by=["-match_date"], limit=limit)
        return await self.find_many(query_spec)

    async def get_matches_by_competition(
        self, competition_id: int, season: Optional[str] = None, limit: int = 100
    ) -> List[Match]:
        """获取指定联赛的比赛"""
        filters = {"competition_id": competition_id}
        if season:
            filters["season"] = season

        query_spec = QuerySpec(filters=filters, order_by=["-match_date"], limit=limit)
        return await self.find_many(query_spec)

    async def search_matches(self, keyword: str) -> List[Match]:
        """搜索比赛"""
        filters = {
            "$or": [
                {"home_team_name": {"$ilike": f"%{keyword}%"}},
                {"away_team_name": {"$ilike": f"%{keyword}%"}},
                {"competition_name": {"$ilike": f"%{keyword}%"}},
            ]
        }
        query_spec = QuerySpec(filters=filters, order_by=["-match_date"], limit=50)
        return await self.find_many(query_spec)

    async def get_match_head_to_head(
        self, home_team_id: int, away_team_id: int, limit: int = 10
    ) -> List[Match]:
        """获取两队历史交锋记录"""
        filters = {
            "$or": [
                {
                    "$and": [
                        {"home_team_id": home_team_id},
                        {"away_team_id": away_team_id},
                    ]
                },
                {
                    "$and": [
                        {"home_team_id": away_team_id},
                        {"away_team_id": home_team_id},
                    ]
                },
            ],
            "status": MatchStatus.FINISHED.value,
        }

        query_spec = QuerySpec(filters=filters, order_by=["-match_date"], limit=limit)
        return await self.find_many(query_spec)


class MatchRepository(MatchRepositoryInterface):
    """比赛仓储实现"""

    async def get_by_id(self, id: int) -> Optional[Match]:
        """根据ID获取比赛"""
        query = select(Match).where(Match.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self, query_spec: Optional[QuerySpec] = None) -> List[Match]:
        """获取所有比赛"""
        query = select(Match)

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

    async def find_one(self, query_spec: QuerySpec) -> Optional[Match]:
        """查找单个比赛"""
        query = select(Match)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_many(self, query_spec: QuerySpec) -> List[Match]:
        """查找多个比赛"""
        return await self.get_all(query_spec)

    async def save(self, entity: Match) -> Match:
        """保存比赛"""
        if entity.id is None:
            self.session.add(entity)
        else:
            entity.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Match) -> bool:
        """删除比赛"""
        try:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            await self.session.rollback()
            return False

    async def exists(self, id: int) -> bool:
        """检查比赛是否存在"""
        query = select(func.count(Match.id)).where(Match.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0

    async def create(self, entity_data: Dict[str, Any]) -> Match:
        """创建新比赛"""
        match = Match(
            home_team_id=entity_data["home_team_id"],
            away_team_id=entity_data["away_team_id"],
            home_team_name=entity_data["home_team_name"],
            away_team_name=entity_data["away_team_name"],
            competition_id=entity_data["competition_id"],
            competition_name=entity_data.get("competition_name"),
            season=entity_data.get("season"),
            match_date=entity_data["match_date"],
            status=entity_data.get("status", MatchStatus.SCHEDULED.value),
            created_at=datetime.utcnow(),
        )

        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

    async def update_by_id(
        self, id: int, update_data: Dict[str, Any]
    ) -> Optional[Match]:
        """根据ID更新比赛"""
        query = update(Match).where(Match.id == id)

        # 更新时间戳
        update_data["updated_at"] = datetime.utcnow()

        # 处理特殊字段
        if "match_date" in update_data and isinstance(update_data["match_date"], str):
            update_data["match_date"] = datetime.fromisoformat(
                update_data["match_date"]
            )

        if "status" in update_data:
            # 更新状态时，记录状态变更时间
            if update_data["status"] == MatchStatus.LIVE.value:
                update_data["started_at"] = datetime.utcnow()
            elif update_data["status"] == MatchStatus.FINISHED.value:
                update_data["finished_at"] = datetime.utcnow()

        # 构建更新语句
        for key, value in update_data.items():
            query = query.values({getattr(Match, key): value})

        result = await self.session.execute(query)
        await self.session.commit()

        if result.rowcount > 0:
            return await self.get_by_id(id)
        return None

    async def delete_by_id(self, id: int) -> bool:
        """根据ID删除比赛"""
        query = (
            update(Match)
            .where(Match.id == id)
            .values(status=MatchStatus.CANCELLED.value, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0

    async def bulk_create(self, entities_data: List[Dict[str, Any]]) -> List[Match]:
        """批量创建比赛"""
        _matches = []
        for data in entities_data:
            match = Match(
                home_team_id=data["home_team_id"],
                away_team_id=data["away_team_id"],
                home_team_name=data["home_team_name"],
                away_team_name=data["away_team_name"],
                competition_id=data["competition_id"],
                competition_name=data.get("competition_name"),
                season=data.get("season"),
                match_date=data["match_date"],
                status=data.get("status", MatchStatus.SCHEDULED.value),
                created_at=datetime.utcnow(),
            )
            matches.append(match)

        self.session.add_all(matches)
        await self.session.commit()

        # 刷新所有实体
        for match in matches:
            await self.session.refresh(match)

        return matches

    async def update_match_score(
        self,
        match_id: int,
        home_score: int,
        away_score: int,
        status: Optional[MatchStatus] = None,
    ) -> Optional[Match]:
        """更新比赛比分"""
        update_data = {
            "home_score": home_score,
            "away_score": away_score,
            "updated_at": datetime.utcnow(),
        }

        if status:
            update_data["status"] = status.value
            if status == MatchStatus.FINISHED.value:
                update_data["finished_at"] = datetime.utcnow()

        return await self.update_by_id(match_id, update_data)

    async def start_match(self, match_id: int) -> Optional[Match]:
        """开始比赛"""
        update_data = {
            "status": MatchStatus.LIVE.value,
            "started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.update_by_id(match_id, update_data)

    async def finish_match(
        self, match_id: int, home_score: int, away_score: int
    ) -> Optional[Match]:
        """结束比赛"""
        update_data = {
            "status": MatchStatus.FINISHED.value,
            "home_score": home_score,
            "away_score": away_score,
            "finished_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return await self.update_by_id(match_id, update_data)

    async def postpone_match(
        self, match_id: int, reason: Optional[str] = None
    ) -> Optional[Match]:
        """推迟比赛"""
        update_data = {
            "status": MatchStatus.POSTPONED.value,
            "updated_at": datetime.utcnow(),
        }
        if reason:
            update_data["notes"] = reason
        return await self.update_by_id(match_id, update_data)

    async def cancel_match(
        self, match_id: int, reason: Optional[str] = None
    ) -> Optional[Match]:
        """取消比赛"""
        update_data = {
            "status": MatchStatus.CANCELLED.value,
            "updated_at": datetime.utcnow(),
        }
        if reason:
            update_data["notes"] = reason
        return await self.update_by_id(match_id, update_data)

    async def get_match_statistics(self, match_id: int) -> Dict[str, Any]:
        """获取比赛统计信息"""
        from ..database.models import Prediction

        # 获取比赛信息
        match = await self.get_by_id(match_id)
        if not match:
            return {}

        # 获取预测统计
        prediction_query = select(
            func.count(Prediction.id).label("total_predictions"),
            func.avg(Prediction.confidence).label("avg_confidence"),
            func.sum(
                func.case(
                    (
                        Prediction.predicted_home_score
                        > Prediction.predicted_away_score,
                        1,
                    ),
                    else_=0,
                )
            ).label("home_win_predictions"),
            func.sum(
                func.case(
                    (
                        Prediction.predicted_home_score
                        < Prediction.predicted_away_score,
                        1,
                    ),
                    else_=0,
                )
            ).label("away_win_predictions"),
            func.sum(
                func.case(
                    (
                        Prediction.predicted_home_score
                        == Prediction.predicted_away_score,
                        1,
                    ),
                    else_=0,
                )
            ).label("draw_predictions"),
        ).where(Prediction.match_id == match_id)

        prediction_result = await self.session.execute(prediction_query)
        prediction_stats = prediction_result.first()

        # 获取实际结果分布
        actual_result = None
        if match.status == MatchStatus.FINISHED.value and match.home_score is not None:
            if match.home_score > match.away_score:
                actual_result = "home_win"
            elif match.home_score < match.away_score:
                actual_result = "away_win"
            else:
                actual_result = "draw"

        return {
            "match_id": match_id,
            "match_info": {
                "home_team": match.home_team_name,
                "away_team": match.away_team_name,
                "competition": match.competition_name,
                "match_date": match.match_date,
                "status": match.status,
                "score": (
                    {"home": match.home_score, "away": match.away_score}
                    if match.home_score is not None
                    else None
                ),
            },
            "predictions": {
                "total": prediction_stats.total_predictions or 0,
                "average_confidence": float(prediction_stats.avg_confidence or 0),
                "distribution": {
                    "home_win": prediction_stats.home_win_predictions or 0,
                    "away_win": prediction_stats.away_win_predictions or 0,
                    "draw": prediction_stats.draw_predictions or 0,
                },
            },
            "actual_result": actual_result,
        }

    def get_read_only_repository(self) -> ReadOnlyMatchRepository:
        """获取只读仓储"""
        return ReadOnlyMatchRepository(self.session, self.model_class)
