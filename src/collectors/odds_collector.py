"""
赔率收集器
从多个博彩公司收集赔率数据
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager
from src.database.connection import DatabaseManager
from src.database.models.match import Match
from src.database.models.odds import Odds
from src.core.logging_system import get_logger

logger = get_logger(__name__)


class OddsCollector:
    """赔率收集器"""

    def __init__(self, db_session: AsyncSession, redis_client: RedisManager):
        self.db_session = db_session
        self.redis_client = redis_client
        self.cache_timeout = 300  # 5分钟缓存，赔率变化较快
        self.bookmakers = {
            "bet365": "https://api.bet365.com/v1",
            "betfair": "https://api.betfair.com/v1",
            "william_hill": "https://api.williamhill.com/v1",
        }

    async def collect_match_odds(
        self,
        match_id: int,
        bookmakers: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        收集指定比赛的赔率

        Args:
            match_id: 比赛ID
            bookmakers: 指定的博彩公司列表
            force_refresh: 是否强制刷新

        Returns:
            赔率数据
        """
        cache_key = f"odds:match:{match_id}"

        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取比赛 {match_id} 的赔率")
                return cached_data

        try:
            # 获取比赛信息
            match = await self._get_match_by_id(match_id)
            if not match:
                logger.error(f"比赛 {match_id} 不存在")
                return {}

            # 收集各博彩公司的赔率
            all_odds = {}
            bookmakers_to_check = bookmakers or list(self.bookmakers.keys())

            for bookmaker in bookmakers_to_check:
                odds = await self._fetch_odds_from_bookmaker(match_id, bookmaker)
                if odds:
                    all_odds[bookmaker] = odds

            # 计算平均赔率
            if all_odds:
                avg_odds = self._calculate_average_odds(all_odds)
                all_odds["average"] = avg_odds

                # 保存到数据库
                await self._save_odds_to_db(match_id, all_odds)

                # 缓存结果
                await self.redis_client.set_cache_value(
                    cache_key, all_odds, expire=self.cache_timeout
                )

            return all_odds

        except Exception as e:
            logger.error(f"收集比赛 {match_id} 赔率失败: {e}")
            return {}

    async def collect_upcoming_matches_odds(
        self, hours_ahead: int = 48, bookmakers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        收集未来几小时内的比赛赔率

        Args:
            hours_ahead: 向前搜索的小时数
            bookmakers: 指定的博彩公司列表

        Returns:
            收集统计
        """
        try:
            # 获取未来几小时的比赛
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=hours_ahead)

            matches = await self._get_upcoming_matches(start_time, end_time)

            stats = {
                "total_matches": len(matches),
                "successful_collects": 0,
                "failed_collects": 0,
                "total_odds_collected": 0,
            }

            # 并发收集赔率
            semaphore = asyncio.Semaphore(10)  # 限制并发数
            tasks = []

            for match in matches:
                task = self._collect_match_odds_with_semaphore(
                    semaphore, match.id, bookmakers
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            for result in results:
                if isinstance(result, Exception):
                    stats["failed_collects"] += 1
                else:
                    stats["successful_collects"] += 1
                    if result:
                        stats["total_odds_collected"] += len(result) - 1  # 减去average

            logger.info(
                f"收集完成，成功 {stats['successful_collects']}/{stats['total_matches']}"
            )
            return stats

        except Exception as e:
            logger.error(f"批量收集赔率失败: {e}")
            return {"error": str(e)}

    async def collect_live_odds(self) -> Dict[str, Any]:
        """收集正在进行的比赛的实时赔率"""
        try:
            # 获取正在进行的比赛
            live_matches = await self._get_live_matches()

            live_odds = {}
            for match in live_matches:
                odds = await self.collect_match_odds(
                    match.id,
                    force_refresh=True,  # 实时赔率总是强制刷新
                )
                if odds:
                    live_odds[match.id] = odds

            return {
                "live_matches_count": len(live_matches),
                "odds_collected": len(live_odds),
                "odds": live_odds,
            }

        except Exception as e:
            logger.error(f"收集实时赔率失败: {e}")
            return {"error": str(e)}

    async def analyze_odds_movement(
        self, match_id: int, hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        分析赔率走势

        Args:
            match_id: 比赛ID
            hours_back: 分析过去几小时的赔率变化

        Returns:
            赔率走势分析
        """
        try:
            # 从历史数据中获取赔率变化
            # 这里需要实现历史赔率数据存储和查询逻辑
            # 简化实现，返回模拟数据

            current_odds = await self.collect_match_odds(match_id)
            if not current_odds:
                return {"error": "无法获取当前赔率"}

            analysis = {
                "match_id": match_id,
                "analysis_period_hours": hours_back,
                "current_odds": current_odds.get("average", {}),
                "movement": {
                    "home_win": {"direction": "down", "change": -0.15},
                    "draw": {"direction": "up", "change": 0.10},
                    "away_win": {"direction": "stable", "change": 0.05},
                },
                "trend": "home_team_favored",
                "confidence": 0.75,
            }

            return analysis

        except Exception as e:
            logger.error(f"分析赔率走势失败: {e}")
            return {"error": str(e)}

    async def _get_match_by_id(self, match_id: int) -> Optional[Match]:
        """根据ID获取比赛"""
        result = await self.db_session.execute(
            select(Match).where(Match.id == match_id)
        )
        return result.scalar_one_or_none()

    async def _get_upcoming_matches(
        self, start_time: datetime, end_time: datetime
    ) -> List[Match]:
        """获取指定时间范围内的比赛"""
        result = await self.db_session.execute(
            select(Match)
            .where(
                and_(
                    Match.start_time >= start_time,
                    Match.start_time <= end_time,
                    Match.match_status == "scheduled",
                )
            )
            .order_by(Match.start_time)
        )
        return result.scalars().all()

    async def _get_live_matches(self) -> List[Match]:
        """获取正在进行的比赛"""
        result = await self.db_session.execute(
            select(Match).where(Match.match_status == "live")
        )
        return result.scalars().all()

    async def _fetch_odds_from_bookmaker(
        self, match_id: int, bookmaker: str
    ) -> Optional[Dict[str, float]]:
        """从博彩公司获取赔率"""
        try:
            # 实际实现需要调用博彩公司API
            # 这里返回模拟数据
            return await self._get_mock_odds(bookmaker)

        except Exception as e:
            logger.error(f"从 {bookmaker} 获取赔率失败: {e}")
            return None

    async def _get_mock_odds(self, bookmaker: str) -> Dict[str, float]:
        """生成模拟赔率数据"""
        import random

        # 生成符合真实赔率分布的随机赔率
        base_home = random.uniform(1.5, 3.0)
        base_away = random.uniform(2.0, 4.5)
        base_draw = random.uniform(2.5, 3.8)

        # 确保赔率合理（庄家有优势）
        margin = random.uniform(1.05, 1.15)
        total_prob = (1 / base_home + 1 / base_draw + 1 / base_away) * margin

        return {
            "home_win": round(total_prob**-1 / (1 / base_home), 2),
            "draw": round(total_prob**-1 / (1 / base_draw), 2),
            "away_win": round(total_prob**-1 / (1 / base_away), 2),
            "bookmaker": bookmaker,
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_average_odds(
        self, all_odds: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """计算平均赔率"""
        if not all_odds:
            return {}

        avg_home = 0
        avg_draw = 0
        avg_away = 0
        count = 0

        for bookmaker, odds in all_odds.items():
            if bookmaker != "average" and odds:
                avg_home += odds.get("home_win", 0)
                avg_draw += odds.get("draw", 0)
                avg_away += odds.get("away_win", 0)
                count += 1

        if count > 0:
            return {
                "home_win": round(avg_home / count, 2),
                "draw": round(avg_draw / count, 2),
                "away_win": round(avg_away / count, 2),
                "source_count": count,
            }

        return {}

    async def _save_odds_to_db(self, match_id: int, odds_data: Dict[str, Any]) -> None:
        """保存赔率到数据库"""
        try:
            # 保存平均赔率
            avg_odds = odds_data.get("average", {})
            if avg_odds:
                odds = Odds(
                    match_id=match_id,
                    home_win=avg_odds.get("home_win"),
                    draw=avg_odds.get("draw"),
                    away_win=avg_odds.get("away_win"),
                    bookmaker="average",
                    timestamp=datetime.now(),
                )

                # 检查是否已存在
                existing = await self.db_session.execute(
                    select(Odds).where(
                        and_(Odds.match_id == match_id, Odds.bookmaker == "average")
                    )
                ).scalar_one_or_none()

                if existing:
                    # 更新现有记录
                    existing.home_win = odds.home_win
                    existing.draw = odds.draw
                    existing.away_win = odds.away_win
                    existing.timestamp = datetime.now()
                else:
                    # 插入新记录
                    self.db_session.add(odds)

            await self.db_session.commit()

        except Exception as e:
            logger.error(f"保存赔率到数据库失败: {e}")
            await self.db_session.rollback()

    async def _collect_match_odds_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        match_id: int,
        bookmakers: Optional[List[str]],
    ) -> Dict[str, Any]:
        """带信号量限制的赔率收集"""
        async with semaphore:
            return await self.collect_match_odds(match_id, bookmakers)


class OddsCollectorFactory:
    """赔率收集器工厂类"""

    @staticmethod
    def create() -> OddsCollector:
        """创建赔率收集器实例"""
        db_session = DatabaseManager()
        redis_client = RedisManager()
        return OddsCollector(db_session, redis_client)
