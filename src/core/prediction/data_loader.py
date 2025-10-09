"""
预测数据加载器
Prediction Data Loader

加载预测所需的数据。
"""

import logging
from typing import Any, Dict, List, Optional

from src.database.connection import DatabaseManager
from src.database.models import League, Match, Odds, Team
from src.collectors.fixtures_collector import FixturesCollector
from src.collectors.odds_collector import OddsCollector
from src.collectors.scores_collector import ScoresCollector

logger = logging.getLogger(__name__)


class PredictionDataLoader:
    """预测数据加载器"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        fixtures_collector: Optional[FixturesCollector] = None,
        odds_collector: Optional[OddsCollector] = None,
        scores_collector: Optional[ScoresCollector] = None,
    ):
        """
        初始化数据加载器

        Args:
            db_manager: 数据库管理器
            fixtures_collector: 赛程收集器
            odds_collector: 赔率收集器
            scores_collector: 比分收集器
        """
        self.db_manager = db_manager
        self.fixtures_collector = fixtures_collector
        self.odds_collector = odds_collector
        self.scores_collector = scores_collector

    async def get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛信息

        Args:
            match_id: 比赛ID

        Returns:
            比赛信息字典或None
        """
        async with self.db_manager.get_async_session() as session:
            try:
                # 查询比赛信息
                query = """
                SELECT
                    m.id,
                    m.home_team_id,
                    m.away_team_id,
                    m.league_id,
                    m.match_date,
                    m.status,
                    m.home_score,
                    m.away_score,
                    ht.name as home_team_name,
                    ht.short_name as home_team_short,
                    at.name as away_team_name,
                    at.short_name as away_team_short,
                    l.name as league_name,
                    l.country as league_country,
                    l.season as league_season
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                JOIN leagues l ON m.league_id = l.id
                WHERE m.id = :match_id
                """
                result = await session.execute(query, {"match_id": match_id})
                row = result.first()

                if row:
                    return {
                        "id": row.id,
                        "home_team": {
                            "id": row.home_team_id,
                            "name": row.home_team_name,
                            "short_name": row.home_team_short,
                        },
                        "away_team": {
                            "id": row.away_team_id,
                            "name": row.away_team_name,
                            "short_name": row.away_team_short,
                        },
                        "league": {
                            "id": row.league_id,
                            "name": row.league_name,
                            "country": row.league_country,
                            "season": row.league_season,
                        },
                        "match_date": row.match_date.isoformat() if row.match_date else None,
                        "status": row.status,
                        "score": {
                            "home": row.home_score,
                            "away": row.away_score,
                        } if row.home_score is not None else None,
                    }
                return None
            except Exception as e:
                logger.error(f"获取比赛信息失败: {e}")
                return None

    async def get_match_odds(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛赔率

        Args:
            match_id: 比赛ID

        Returns:
            赔率信息字典或None
        """
        async with self.db_manager.get_async_session() as session:
            try:
                # 查询最新赔率
                query = """
                SELECT
                    bookmaker,
                    home_win,
                    draw,
                    away_win,
                    created_at
                FROM odds
                WHERE match_id = :match_id
                ORDER BY created_at DESC
                LIMIT 1
                """
                result = await session.execute(query, {"match_id": match_id})
                row = result.first()

                if row:
                    return {
                        "bookmaker": row.bookmaker,
                        "odds": {
                            "home_win": float(row.home_win),
                            "draw": float(row.draw),
                            "away_win": float(row.away_win),
                        },
                        "created_at": row.created_at.isoformat(),
                    }
                return None
            except Exception as e:
                logger.error(f"获取比赛赔率失败: {e}")
                return None

    async def get_team_history(
        self, team_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取球队历史比赛

        Args:
            team_id: 球队ID
            limit: 返回数量限制

        Returns:
            历史比赛列表
        """
        async with self.db_manager.get_async_session() as session:
            try:
                query = """
                SELECT
                    m.id,
                    m.match_date,
                    m.home_team_id,
                    m.away_team_id,
                    m.home_score,
                    m.away_score,
                    m.status,
                    ht.name as opponent_name,
                    CASE
                        WHEN m.home_team_id = :team_id THEN 'home'
                        ELSE 'away'
                    END as position,
                    CASE
                        WHEN m.home_team_id = :team_id AND m.home_score > m.away_score THEN 'win'
                        WHEN m.away_team_id = :team_id AND m.away_score > m.home_score THEN 'win'
                        WHEN m.home_score = m.away_score THEN 'draw'
                        ELSE 'lose'
                    END as result
                FROM matches m
                JOIN teams ht ON (
                    (m.home_team_id = :team_id AND m.away_team_id = ht.id) OR
                    (m.away_team_id = :team_id AND m.home_team_id = ht.id)
                )
                WHERE (m.home_team_id = :team_id OR m.away_team_id = :team_id)
                  AND m.status = 'finished'
                  AND m.match_date < NOW()
                ORDER BY m.match_date DESC
                LIMIT :limit
                """
                result = await session.execute(
                    query, {"team_id": team_id, "limit": limit}
                )
                rows = result.fetchall()

                history = []
                for row in rows:
                    history.append(
                        {
                            "match_id": row.id,
                            "date": row.match_date.isoformat() if row.match_date else None,
                            "opponent": row.opponent_name,
                            "position": row.position,
                            "result": row.result,
                            "score": {
                                "home": row.home_score,
                                "away": row.away_score,
                            } if row.home_score is not None else None,
                        }
                    )
                return history
            except Exception as e:
                logger.error(f"获取球队历史失败: {e}")
                return []

    async def collect_latest_data(self, match_id: int, match_info: Dict[str, Any]):
        """
        收集最新数据

        Args:
            match_id: 比赛ID
            match_info: 比赛信息
        """
        try:
            # 初始化收集器（如果需要）
            if not self.fixtures_collector:
                # 延迟初始化
                from src.cache.redis_manager import RedisManager
                redis_manager = RedisManager()
                async with self.db_manager.get_async_session() as session:
                    self.fixtures_collector = FixturesCollector(session, redis_manager)
                    self.odds_collector = OddsCollector(session, redis_manager)
                    self.scores_collector = ScoresCollector(session, redis_manager)

            # 根据比赛状态决定收集哪些数据
            if match_info.get("status") in ["scheduled", "live"]:
                # 收集最新赔率
                if self.odds_collector:
                    await self.odds_collector.collect_match_odds(match_id)
                    logger.debug(f"收集赔率数据: 比赛 {match_id}")

            if match_info.get("status") == "live":
                # 收集实时比分
                if self.scores_collector:
                    await self.scores_collector.collect_live_score(match_id)
                    logger.debug(f"收集比分数据: 比赛 {match_id}")

        except Exception as e:
            logger.error(f"收集最新数据失败: {e}")

    async def get_upcoming_matches(
        self, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取即将到来的比赛

        Args:
            hours: 未来多少小时
            limit: 返回数量限制

        Returns:
            比赛列表
        """
        async with self.db_manager.get_async_session() as session:
            try:
                query = """
                SELECT
                    m.id,
                    m.match_date,
                    ht.name as home_team_name,
                    at.name as away_team_name,
                    l.name as league_name
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                JOIN leagues l ON m.league_id = l.id
                WHERE m.status = 'scheduled'
                  AND m.match_date BETWEEN NOW() AND NOW() + INTERVAL ':hours hours'
                ORDER BY m.match_date ASC
                LIMIT :limit
                """
                result = await session.execute(
                    query, {"hours": hours, "limit": limit}
                )
                rows = result.fetchall()

                matches = []
                for row in rows:
                    matches.append(
                        {
                            "id": row.id,
                            "match_date": row.match_date.isoformat(),
                            "home_team": row.home_team_name,
                            "away_team": row.away_team_name,
                            "league": row.league_name,
                        }
                    )
                return matches
            except Exception as e:
                logger.error(f"获取即将到来的比赛失败: {e}")
                return []