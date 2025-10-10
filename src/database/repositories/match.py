"""
比赛仓储

提供比赛数据的访问操作。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from .base import BaseRepository, RepositoryConfig
from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team


class MatchRepository(BaseRepository[Match]):
    """比赛仓储类"""

    def __init__(self, session, config: Optional[RepositoryConfig] = None):
        super().__init__(session, Match, config or RepositoryConfig())

    # ==================== 基础查询 ====================

    async def get_by_fixture_id(self, fixture_id: int) -> Optional[Match]:
        """根据比赛ID获取比赛"""
        return await self.find_one({"fixture_id": fixture_id})

    async def get_by_teams(
        self, home_team_id: int, away_team_id: int, date: Optional[datetime] = None
    ) -> Optional[Match]:
        """根据主客队获取比赛"""
        filters = {"home_team_id": home_team_id, "away_team_id": away_team_id}

        if date:
            # 查找指定日期的比赛（前后1天范围）
            start_date = date - timedelta(days=1)
            end_date = date + timedelta(days=1)

            stmt = select(self.model_class).where(
                and_(
                    self.model_class.home_team_id == home_team_id,
                    self.model_class.away_team_id == away_team_id,
                    self.model_class.match_time >= start_date,
                    self.model_class.match_time <= end_date,
                )
            )

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        return await self.find_one(filters)

    # ==================== 状态相关查询 ====================

    async def get_by_status(self, status: MatchStatus) -> List[Match]:
        """根据状态获取比赛列表"""
        return await self.find({"status": status})

    async def get_upcoming_matches(
        self, days: int = 7, limit: Optional[int] = None
    ) -> List[Match]:
        """获取即将到来的比赛"""
        start_time = datetime.now()
        end_time = start_time + timedelta(days=days)

        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.match_time >= start_time,
                    self.model_class.match_time <= end_time,
                    self.model_class.status == MatchStatus.SCHEDULED,
                )
            )
            .order_by(self.model_class.match_time)
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_live_matches(self) -> List[Match]:
        """获取正在进行的比赛"""
        return await self.find({"status": MatchStatus.LIVE})

    async def get_finished_matches(
        self, days: int = 7, limit: Optional[int] = None
    ) -> List[Match]:
        """获取已结束的比赛"""
        start_time = datetime.now() - timedelta(days=days)

        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.match_time >= start_time,
                    self.model_class.status.in_(
                        [
                            MatchStatus.FINISHED,
                            MatchStatus.POSTPONED,
                            MatchStatus.CANCELLED,
                        ]
                    ),
                )
            )
            .order_by(desc(self.model_class.match_time))
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 球队相关查询 ====================

    async def get_team_matches(
        self, team_id: int, limit: int = 10, status: Optional[MatchStatus] = None
    ) -> List[Match]:
        """获取指定球队的比赛"""
        filters = []
        filters.append(
            or_(
                self.model_class.home_team_id == team_id,
                self.model_class.away_team_id == team_id,
            )
        )

        if status:
            filters.append(self.model_class.status == status)

        stmt = (
            select(self.model_class)
            .where(and_(*filters))
            .order_by(desc(self.model_class.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_home_matches(self, team_id: int, limit: int = 10) -> List[Match]:
        """获取球队的主场比赛"""
        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.home_team_id == team_id,
                    self.model_class.status != MatchStatus.CANCELLED,
                )
            )
            .order_by(desc(self.model_class.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_away_matches(self, team_id: int, limit: int = 10) -> List[Match]:
        """获取球队的客场比赛"""
        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.away_team_id == team_id,
                    self.model_class.status != MatchStatus.CANCELLED,
                )
            )
            .order_by(desc(self.model_class.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 联赛相关查询 ====================

    async def get_league_matches(
        self, league_id: int, season: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Match]:
        """获取联赛的比赛"""
        filters = {"league_id": league_id}

        if season:
            filters["season"] = season

        stmt = (
            select(self.model_class)
            .where(self.model_class.league_id == league_id)
            .order_by(self.model_class.match_time)
        )

        if season:
            stmt = stmt.where(self.model_class.season == season)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_league_standings_data(
        self, league_id: int, season: str
    ) -> List[Dict[str, Any]]:
        """获取联赛积分榜数据"""
        # 只计算已完成的比赛
        stmt = select(self.model_class).where(
            and_(
                self.model_class.league_id == league_id,
                self.model_class.season == season,
                self.model_class.status == MatchStatus.FINISHED,
                self.model_class.home_score.is_not(None),
                self.model_class.away_score.is_not(None),
            )
        )

        result = await self.session.execute(stmt)
        matches = result.scalars().all()

        # 计算积分榜（这里简化处理，实际可能需要更复杂的逻辑）
        standings = {}
        for match in matches:
            home_team_id = match.home_team_id
            away_team_id = match.away_team_id
            home_score = match.home_score or 0
            away_score = match.away_score or 0

            # 初始化
            if home_team_id not in standings:
                standings[home_team_id] = {
                    "team_id": home_team_id,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                }

            if away_team_id not in standings:
                standings[away_team_id] = {
                    "team_id": away_team_id,
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                }

            # 更新统计
            standings[home_team_id]["played"] += 1
            standings[away_team_id]["played"] += 1
            standings[home_team_id]["goals_for"] += home_score
            standings[home_team_id]["goals_against"] += away_score
            standings[away_team_id]["goals_for"] += away_score
            standings[away_team_id]["goals_against"] += home_score

            # 判断胜负
            if home_score > away_score:
                standings[home_team_id]["won"] += 1
                standings[home_team_id]["points"] += 3
                standings[away_team_id]["lost"] += 1
            elif home_score < away_score:
                standings[away_team_id]["won"] += 1
                standings[away_team_id]["points"] += 3
                standings[home_team_id]["lost"] += 1
            else:
                standings[home_team_id]["drawn"] += 1
                standings[home_team_id]["points"] += 1
                standings[away_team_id]["drawn"] += 1
                standings[away_team_id]["points"] += 1

        # 计算净胜球
        for team_stats in standings.values():
            team_stats["goal_difference"] = (
                team_stats["goals_for"] - team_stats["goals_against"]
            )

        # 按积分、净胜球、进球数排序
        sorted_standings = sorted(
            standings.values(),
            key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
            reverse=True,
        )

        return sorted_standings

    # ==================== 统计相关查询 ====================

    async def get_match_count_by_status(self) -> Dict[str, int]:
        """获取各种状态的比赛数量"""
        stmt = select(
            self.model_class.status, func.count(self.model_class.id).label("count")
        ).group_by(self.model_class.status)

        result = await self.session.execute(stmt)
        return {status.value: count for status, count in result.all()}

    async def get_daily_match_count(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取每日比赛数量统计"""
        start_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(
                func.date(self.model_class.match_time).label("date"),
                func.count(self.model_class.id).label("count"),
            )
            .where(self.model_class.match_time >= start_date)
            .group_by(func.date(self.model_class.match_time))
            .order_by("date")
        )

        result = await self.session.execute(stmt)
        return [{"date": str(date), "count": count} for date, count in result.all()]

    # ==================== 高级查询 ====================

    async def search_matches(self, query: str, limit: int = 20) -> List[Match]:
        """搜索比赛（按球队名称）"""
        # 使用JOIN查询球队名称
        stmt = (
            select(self.model_class)
            .options(
                selectinload(self.model_class.home_team),
                selectinload(self.model_class.away_team),
            )
            .join(
                Team,
                or_(
                    self.model_class.home_team_id == Team.id,
                    self.model_class.away_team_id == Team.id,
                ),
            )
            .where(
                or_(Team.name.ilike(f"%{query}%"), Team.short_name.ilike(f"%{query}%"))
            )
            .order_by(desc(self.model_class.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_matches_with_predictions(self, limit: int = 10) -> List[Match]:
        """获取有预测的比赛"""
        # 这里假设有prediction关联
        stmt = (
            select(self.model_class)
            .where(
                self.model_class.predictions.any()  # 如果有relationship定义
            )
            .order_by(desc(self.model_class.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 批量操作 ====================

    async def update_match_scores(
        self,
        match_id: int,
        home_score: int,
        away_score: int,
        status: MatchStatus = MatchStatus.FINISHED,
    ) -> bool:
        """更新比赛比分"""
        updates = {
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "updated_at": datetime.now(),
        }

        updated_count = await self.update_batch({"id": match_id}, updates)

        return updated_count > 0

    async def finish_matches_by_time(self) -> int:
        """结束过期的比赛（自动标记为结束）"""
        # 超过24小时还未结束的比赛，自动标记为结束
        cutoff_time = datetime.now() - timedelta(hours=24)

        updates = {"status": MatchStatus.FINISHED, "updated_at": datetime.now()}

        updated_count = await self.update_batch(
            {"match_time": cutoff_time, "status": MatchStatus.LIVE}, updates
        )

        if updated_count > 0:
            self.logger.info(f"Auto-finished {updated_count} expired matches")

        return updated_count
