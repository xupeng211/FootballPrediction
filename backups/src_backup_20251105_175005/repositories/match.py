"""
比赛仓储模块 - 重写版本

实现比赛相关的数据访问逻辑
Match Repository - Rewritten Version
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Match
from .base import BaseRepository, QuerySpec


class MatchRepositoryInterface:
    """比赛仓储接口"""

    async def get_match_by_id(self, match_id: int) -> Optional["Match"]:
        raise NotImplementedError

    async def get_matches_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list["Match"]:
        raise NotImplementedError


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class MatchRepository(BaseRepository):
    """比赛仓储实现 - 简化版本"""

    def __init__(self, session: AsyncSession):
        """初始化比赛仓储"""
        super().__init__(session, Match)

    async def get_by_id(self, match_id: int) -> Optional["Match"]:
        """根据ID获取比赛"""
        query = select(self.model_class).where(self.model_class.id == match_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, query_spec: QuerySpec | None = None) -> list["Match"]:
        """获取所有比赛"""
        query = select(self.model_class)

        if query_spec:
            query = self._build_query(query_spec)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, match_data: dict[str, Any]) -> "Match":
        """创建比赛"""
        match = self.model_class(
            home_team_id=match_data["home_team_id"],
            away_team_id=match_data["away_team_id"],
            match_time=match_data.get("match_time", datetime.utcnow()),
            venue=match_data.get("venue", ""),
            status=match_data.get("status", MatchStatus.SCHEDULED),
            home_score=match_data.get("home_score", 0),
            away_score=match_data.get("away_score", 0),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

    async def update(
        self, match_id: int, update_data: dict[str, Any]
    ) -> Optional["Match"]:
        """更新比赛"""
        update_data["updated_at"] = datetime.utcnow()

        query = (
            update(self.model_class)
            .where(self.model_class.id == match_id)
            .values(**update_data)
        )

        await self.session.execute(query)
        await self.session.commit()

        return await self.get_by_id(match_id)

    async def delete(self, match_id: int) -> bool:
        """删除比赛"""
        match = await self.get_by_id(match_id)
        if match:
            await self.session.delete(match)
            await self.session.commit()
            return True
        return False

    async def find_by_team(
        self, team_id: int, limit: int | None = None
    ) -> list["Match"]:
        """根据球队ID查找比赛"""
        filters = {"$or": [{"home_team_id": team_id}, {"away_team_id": team_id}]}
        return await self.find_by_filters(filters, limit)

    async def find_by_status(
        self, status: MatchStatus, limit: int | None = None
    ) -> list["Match"]:
        """根据状态查找比赛"""
        filters = {"status": status}
        return await self.find_by_filters(filters, limit)

    async def find_upcoming_matches(
        self, days: int = 7, limit: int = 50
    ) -> list["Match"]:
        """查找即将到来的比赛"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(days=days)

        filters = {
            "match_time": {"$gte": start_time, "$lte": end_time},
            "status": MatchStatus.SCHEDULED,
        }
        order_by = ["match_time"]

        query_spec = QuerySpec(filters=filters, order_by=order_by, limit=limit)

        return await self.get_all(query_spec)

    async def find_live_matches(self) -> list["Match"]:
        """查找正在进行的比赛"""
        filters = {"status": MatchStatus.LIVE}
        return await self.find_by_filters(filters)

    async def find_recent_finished_matches(
        self, days: int = 7, limit: int = 50
    ) -> list["Match"]:
        """查找最近结束的比赛"""
        start_time = datetime.utcnow() - timedelta(days=days)

        filters = {"match_time": {"$gte": start_time}, "status": MatchStatus.FINISHED}
        order_by = ["-match_time"]

        query_spec = QuerySpec(filters=filters, order_by=order_by, limit=limit)

        return await self.get_all(query_spec)

    async def update_match_score(
        self, match_id: int, home_score: int, away_score: int
    ) -> bool:
        """更新比赛比分"""
        update_data = {
            "home_score": home_score,
            "away_score": away_score,
            "updated_at": datetime.utcnow(),
        }

        result = await self.update(match_id, update_data)
        return result is not None

    async def start_match(self, match_id: int) -> bool:
        """开始比赛"""
        update_data = {"status": MatchStatus.LIVE, "updated_at": datetime.utcnow()}

        result = await self.update(match_id, update_data)
        return result is not None

    async def finish_match(
        self, match_id: int, home_score: int, away_score: int
    ) -> bool:
        """结束比赛"""
        update_data = {
            "status": MatchStatus.FINISHED,
            "home_score": home_score,
            "away_score": away_score,
            "updated_at": datetime.utcnow(),
        }

        result = await self.update(match_id, update_data)
        return result is not None

    async def postpone_match(self, match_id: int, reason: str = "") -> bool:
        """推迟比赛"""
        update_data = {
            "status": MatchStatus.POSTPONED,
            "postponed_reason": reason,
            "updated_at": datetime.utcnow(),
        }

        result = await self.update(match_id, update_data)
        return result is not None

    async def cancel_match(self, match_id: int, reason: str = "") -> bool:
        """取消比赛"""
        update_data = {
            "status": MatchStatus.CANCELLED,
            "cancelled_reason": reason,
            "updated_at": datetime.utcnow(),
        }

        result = await self.update(match_id, update_data)
        return result is not None

    async def get_matches_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: MatchStatus | None = None,
    ) -> list["Match"]:
        """根据日期范围获取比赛"""
        filters = {"match_time": {"$gte": start_date, "$lte": end_date}}

        if status:
            filters["status"] = status

        return await self.find_by_filters(filters)

    async def get_head_to_head_matches(
        self, team1_id: int, team2_id: int, limit: int = 10
    ) -> list["Match"]:
        """获取两支球队的历史交锋记录"""
        filters = {
            "$or": [
                {"home_team_id": team1_id, "away_team_id": team2_id},
                {"home_team_id": team2_id, "away_team_id": team1_id},
            ]
        }
        order_by = ["-match_time"]

        query_spec = QuerySpec(filters=filters, order_by=order_by, limit=limit)

        return await self.get_all(query_spec)

    async def count_matches_by_status(self) -> dict[str, int]:
        """统计各种状态的比赛数量"""
        result = {}
        for status in MatchStatus:
            count = await self.count(QuerySpec(filters={"status": status}))
            result[status.value] = count
        return result

    async def bulk_create(self, matches_data: list[dict[str, Any]]) -> list["Match"]:
        """批量创建比赛"""
        matches = []
        for match_data in matches_data:
            match = self.model_class(
                home_team_id=match_data["home_team_id"],
                away_team_id=match_data["away_team_id"],
                match_time=match_data.get("match_time", datetime.utcnow()),
                venue=match_data.get("venue", ""),
                status=match_data.get("status", MatchStatus.SCHEDULED),
                home_score=match_data.get("home_score", 0),
                away_score=match_data.get("away_score", 0),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            matches.append(match)

        self.session.add_all(matches)
        await self.session.commit()

        # 刷新所有实体
        for match in matches:
            await self.session.refresh(match)


class ReadOnlyMatchRepository(BaseRepository):
    """只读比赛仓储"""

    def __init__(self, session: AsyncSession):
        """初始化只读比赛仓储"""
        super().__init__(session, Match)

    async def get_match_by_id(self, match_id: int) -> Optional["Match"]:
        """根据ID获取比赛"""
        return await self.get_by_id(match_id)

    async def get_matches_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: MatchStatus | None = None,
    ) -> list["Match"]:
        """获取日期范围内的比赛"""
        conditions = {
            "match_date__gte": start_date,
            "match_date__lte": end_date,
        }
        if status:
            conditions["status"] = status

        return await self.get_by_conditions(conditions)
