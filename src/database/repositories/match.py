from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.match import Match, MatchResult, MatchStatus

from .base import BaseRepository

"""
比赛仓储
Match Repository

提供比赛数据的访问操作,实现Repository模式.
Provides match data access operations, implementing the Repository pattern.
"""


class MatchRepository(BaseRepository[Match]):
    """
    比赛仓储类
    Match Repository Class

    提供比赛数据的CRUD操作和复杂查询方法.
    Provides CRUD operations and complex query methods for match data.
    """

    def __init__(self, db_manager=None):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(Match, db_manager)

    # ========================================
    # 比赛特定的查询方法
    # ========================================

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        获取指定日期范围内的比赛

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            比赛列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                select(Match)
                .where(
                    and_(Match.match_date >= start_date, Match.match_date <= end_date)
                )
                .order_by(Match.match_date)
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_by_status(
        self,
        status: MatchStatus,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        根据状态获取比赛

        Args:
            status: 比赛状态
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            比赛列表
        """
        return await self.find_by(
            filters={"status": status.value}, limit=limit, session=session
        )

    async def get_upcoming_matches(
        self,
        days: int = 7,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        获取即将到来的比赛

        Args:
            days: 未来多少天
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            比赛列表
        """
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)

        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                select(Match)
                .where(
                    and_(
                        Match.match_date >= now,
                        Match.match_date <= end_date,
                        Match.status == MatchStatus.SCHEDULED.value,
                    )
                )
                .order_by(Match.match_date)
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_live_matches(
        self, session: AsyncSession | None = None
    ) -> list[Match] | None:
        """
        获取正在进行的比赛

        Args:
            session: 数据库会话

        Returns:
            正在进行的比赛列表
        """
        return await self.get_by_status(status=MatchStatus.LIVE, session=session)

    async def get_finished_matches(
        self,
        days: int = 7,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        获取已结束的比赛

        Args:
            days: 过去多少天
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            已结束的比赛列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                select(Match)
                .where(
                    and_(
                        Match.match_date >= start_date,
                        Match.status == MatchStatus.FINISHED.value,
                    )
                )
                .order_by(desc(Match.match_date))
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_by_team(
        self,
        team_id: int | str,
        home_or_away: str | None = None,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        根据球队获取比赛

        Args:
            team_id: 球队ID
            home_or_away: 'home','away' 或 None（全部）
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            比赛列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            if home_or_away == "home":
                stmt = select(Match).where(Match.home_team_id == team_id)
            elif home_or_away == "away":
                stmt = select(Match).where(Match.away_team_id == team_id)
            else:
                stmt = select(Match).where(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
                )

            stmt = stmt.order_by(desc(Match.match_date))

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_head_to_head(
        self,
        team1_id: int | str,
        team2_id: int | str,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        获取两支球队的历史对战记录

        Args:
            team1_id: 第一支球队ID
            team2_id: 第二支球队ID
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            历史对战比赛列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                select(Match)
                .where(
                    or_(
                        and_(
                            Match.home_team_id == team1_id,
                            Match.away_team_id == team2_id,
                        ),
                        and_(
                            Match.home_team_id == team2_id,
                            Match.away_team_id == team1_id,
                        ),
                    )
                )
                .order_by(desc(Match.match_date))
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_matches_by_league(
        self,
        league_id: int | str,
        season: str | None = None,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[Match] | None:
        """
        根据联赛获取比赛

        Args:
            league_id: 联赛ID
            season: 赛季（可选）
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            比赛列表
        """
        filters = {"league_id": league_id}
        if season:
            filters["season"] = season

        return await self.find_by(
            filters=filters, limit=limit, order_by="match_date", session=session
        )

    async def update_match_status(
        self,
        match_id: int | str,
        status: MatchStatus,
        session: AsyncSession | None = None,
    ) -> Match | None:
        """
        更新比赛状态

        Args:
            match_id: 比赛ID
            status: 新状态
            session: 数据库会话

        Returns:
            更新后的比赛对象
        """
        return await self.update(
            obj_id=match_id, obj_data={"status": status.value}, session=session
        )

    async def update_match_score(
        self,
        match_id: int | str,
        home_score: int | None,
        away_score: int | None,
        session: AsyncSession | None = None,
    ) -> Match | None:
        """
        更新比赛比分

        Args:
            match_id: 比赛ID
            home_score: 主队得分
            away_score: 客队得分
            session: 数据库会话

        Returns:
            更新后的比赛对象
        """
        update_data = {}
        if home_score is not None:
            update_data["home_score"] = home_score
        if away_score is not None:
            update_data["away_score"] = away_score

        # 如果比赛有比分,设置状态为进行中或已结束
        if home_score is not None and away_score is not None:
            update_data["status"] = MatchStatus.LIVE.value

        return await self.update(obj_id=match_id, obj_data=update_data, session=session)

    async def finish_match(
        self,
        match_id: int | str,
        home_score: int,
        away_score: int,
        result: MatchResult | None = None,
        session: AsyncSession | None = None,
    ) -> Match | None:
        """
        结束比赛

        Args:
            match_id: 比赛ID
            home_score: 主队最终得分
            away_score: 客队最终得分
            result: 比赛结果（可选,可根据比分自动判断）
            session: 数据库会话

        Returns:
            更新后的比赛对象
        """
        update_data = {
            "home_score": home_score,
            "away_score": away_score,
            "status": MatchStatus.FINISHED.value,
            "finished_at": datetime.utcnow(),
        }

        # 自动判断比赛结果
        if not result:
            if home_score > away_score:
                result = MatchResult.HOME_WIN
            elif away_score > home_score:
                result = MatchResult.AWAY_WIN
            else:
                result = MatchResult.DRAW

        update_data["result"] = result.value

        return await self.update(obj_id=match_id, obj_data=update_data, session=session)

    # ========================================
    # 实现抽象方法
    # ========================================

    async def get_related_data(
        self,
        obj_id: int | str,
        relation_name: str,
        session: AsyncSession | None = None,
    ) -> Any:
        """
        获取比赛的关联数据

        Args:
            obj_id: 比赛ID
            relation_name: 关联名称（如 'predictions', 'odds'）
            session: 数据库会话

        Returns:
            关联数据
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 根据关联名称加载不同的关联数据
            if relation_name == "predictions":
                stmt = (
                    select(Match)
                    .options(selectinload(Match.predictions))
                    .where(Match.id == obj_id)
                )
            elif relation_name == "odds":
                stmt = (
                    select(Match)
                    .options(selectinload(Match.odds))
                    .where(Match.id == obj_id)
                )
            elif relation_name == "home_team":
                stmt = (
                    select(Match)
                    .options(selectinload(Match.home_team))
                    .where(Match.id == obj_id)
                )
            elif relation_name == "away_team":
                stmt = (
                    select(Match)
                    .options(selectinload(Match.away_team))
                    .where(Match.id == obj_id)
                )
            else:
                return None

            result = await sess.execute(stmt)
            match = result.scalar_one_or_none()

            if match:
                return getattr(match, relation_name, None)
            return None

    # ========================================
    # 统计方法
    # ========================================

    async def get_team_form(
        self,
        team_id: int | str,
        last_matches: int = 5,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        获取球队近期状态

        Args:
            team_id: 球队ID
            last_matches: 最近多少场比赛
            session: 数据库会话

        Returns:
            包含胜负平统计的字典
        """
        _matches = await self.get_by_team(
            team_id=team_id, limit=last_matches, session=session
        )

        stats = {
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "form": [],  # 最近比赛结果列表
        }

        for match in _matches:
            if match.status != MatchStatus.FINISHED.value:
                continue

            stats["played"] += 1

            # 判断是主队还是客队
            is_home = match.home_team_id == team_id
            home_score = match.home_score or 0
            away_score = match.away_score or 0

            # 计算进球数
            if is_home:
                stats["goals_for"] += home_score
                stats["goals_against"] += away_score
                team_score = home_score
                opponent_score = away_score
            else:
                stats["goals_for"] += away_score
                stats["goals_against"] += home_score
                team_score = away_score
                opponent_score = home_score

            # 判断胜负平
            if team_score > opponent_score:
                stats["wins"] += 1
                stats["form"].append("W")
            elif team_score < opponent_score:
                stats["losses"] += 1
                stats["form"].append("L")
            else:
                stats["draws"] += 1
                stats["form"].append("D")

        return stats
