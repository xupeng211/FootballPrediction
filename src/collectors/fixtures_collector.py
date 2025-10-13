# mypy: ignore-errors
"""
比赛赛程收集器
从各种数据源收集比赛赛程信息
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager
from src.database.connection import DatabaseManager
from src.database.models.match import Match
from src.database.models.team import Team
from src.core.logging_system import get_logger

logger = get_logger(__name__)


class FixturesCollector:
    """比赛赛程收集器"""

    def __init__(self, db_session: AsyncSession, redis_client: RedisManager):
        self.db_session = db_session
        self.redis_client = redis_client
        self.cache_timeout = 3600  # 1小时缓存
        self.api_endpoints = {
            "football-api": "https://api.football-data.org/v4",
            "api-sports": "https://v3.football.api-sports.io",
        }
        # 从环境变量读取 API Token
        api_token = os.getenv("FOOTBALL_API_TOKEN")
        if not api_token:
            logger.warning("未设置 FOOTBALL_API_TOKEN 环境变量")
        self.headers = {"X-Auth-Token": api_token} if api_token else {}

    async def collect_team_fixtures(
        self, team_id: int, days_ahead: int = 30, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        收集指定球队的未来比赛

        Args:
            team_id: 球队ID
            days_ahead: 向前搜索的天数
            force_refresh: 是否强制刷新缓存

        Returns:
            比赛信息列表
        """
        cache_key = f"fixtures:team:{team_id}:{days_ahead}"

        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取球队 {team_id} 的赛程")
                return cached_data

        try:
            # 从数据库查询
            fixtures = await self._get_fixtures_from_db(team_id, days_ahead)

            if not fixtures:
                # 如果数据库没有，从API获取
                fixtures = await self._fetch_fixtures_from_api(team_id, days_ahead)

                # 保存到数据库
                if fixtures:
                    await self._save_fixtures_to_db(fixtures)

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, fixtures, expire=self.cache_timeout
            )

            logger.info(f"收集到球队 {team_id} 的 {len(fixtures)} 场比赛")
            return fixtures

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"收集球队 {team_id} 赛程失败: {e}")
            return []

    async def collect_league_fixtures(
        self,
        league_id: int,
        matchday: Optional[int] = None,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        收集联赛的比赛赛程

        Args:
            league_id: 联赛ID
            matchday: 轮次（可选）
            force_refresh: 是否强制刷新缓存

        Returns:
            比赛信息列表
        """
        cache_key = f"fixtures:league:{league_id}:{matchday or 'all'}"

        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                return cached_data

        try:
            # 从API获取联赛赛程
            fixtures = await self._fetch_league_fixtures_from_api(league_id, matchday)

            # 缓存结果
            if fixtures:
                await self.redis_client.set_cache_value(
                    cache_key, fixtures, expire=self.cache_timeout
                )

            return fixtures

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"收集联赛 {league_id} 赛程失败: {e}")
            return []

    async def _get_fixtures_from_db(
        self, team_id: int, days_ahead: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取比赛信息"""
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=days_ahead)

        query = (
            select(Match)
            .where(
                Match.start_time >= start_date,
                Match.start_time <= end_date,
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
            )
            .order_by(Match.start_time)
        )

        result = await self.db_session.execute(query)
        matches = result.scalars().all()

        fixtures = []
        for match in matches:
            fixtures.append(
                {
                    "id": match.id,
                    "home_team_id": match.home_team_id,
                    "away_team_id": match.away_team_id,
                    "league_id": match.league_id,
                    "start_time": match.start_time,
                    "venue": match.venue,
                    "match_status": match.match_status,
                }
            )

        return fixtures

    async def _fetch_fixtures_from_api(
        self, team_id: int, days_ahead: int
    ) -> List[Dict[str, Any]]:
        """从API获取比赛信息"""
        # 模拟数据，实际使用时替换为真实API调用
        return await self._get_mock_fixtures(team_id, days_ahead)

    async def _fetch_league_fixtures_from_api(
        self, league_id: int, matchday: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """从API获取联赛比赛信息"""
        # 模拟API调用
        return await self._get_mock_league_fixtures(league_id, matchday)

    async def _save_fixtures_to_db(self, fixtures: List[Dict[str, Any]]) -> None:
        """保存比赛信息到数据库"""
        for fixture_data in fixtures:
            # 检查是否已存在
            existing_match = await self.db_session.execute(
                select(Match).where(Match.id == fixture_data["id"])
            ).scalar_one_or_none()

            if not existing_match:
                # 创建新的比赛记录
                match = Match(
                    id=fixture_data["id"],
                    home_team_id=fixture_data["home_team_id"],
                    away_team_id=fixture_data["away_team_id"],
                    league_id=fixture_data["league_id"],
                    start_time=fixture_data["start_time"],
                    venue=fixture_data.get("venue", "Unknown"),
                    match_status=fixture_data.get("match_status", "scheduled"),
                )
                self.db_session.add(match)

        await self.db_session.commit()

    def _transform_api_data(self, api_data: Dict) -> List[Dict[str, Any]]:
        """转换API数据格式"""
        fixtures = []

        for match_data in api_data.get("matches", []):
            fixture = {
                "id": match_data.get("id"),
                "home_team_id": match_data.get("homeTeam", {}).get("id"),
                "away_team_id": match_data.get("awayTeam", {}).get("id"),
                "league_id": match_data.get("competition", {}).get("id"),
                "start_time": datetime.fromisoformat(match_data.get("utcDate")),
                "venue": match_data.get("venue", {}).get("name"),
                "match_status": match_data.get("status", "scheduled"),
            }
            fixtures.append(fixture)

        return fixtures

    async def _get_mock_fixtures(
        self, team_id: int, days_ahead: int
    ) -> List[Dict[str, Any]]:
        """生成模拟数据（仅用于测试）"""
        fixtures = []
        base_date = datetime.now()

        for i in range(min(5, days_ahead // 6)):  # 生成5场模拟比赛
            match_date = base_date + timedelta(days=i * 7)
            fixture = {
                "id": 1000 + team_id * 100 + i,
                "home_team_id": team_id if i % 2 == 0 else team_id + 1,
                "away_team_id": team_id + 1 if i % 2 == 0 else team_id,
                "league_id": 2021,  # Premier League
                "start_time": match_date,
                "venue": "Test Stadium",
                "match_status": "scheduled",
            }
            fixtures.append(fixture)

        return fixtures

    async def _get_mock_league_fixtures(
        self, league_id: int, matchday: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """生成联赛模拟数据（仅用于测试）"""
        fixtures = []

        # 生成10场模拟比赛
        for i in range(10):
            match_date = datetime.now() + timedelta(days=i)
            fixture = {
                "id": 5000 + league_id * 100 + i,
                "home_team_id": 10 + i,
                "away_team_id": 20 + i,
                "league_id": league_id,
                "start_time": match_date,
                "venue": f"Stadium {i + 1}",
                "match_status": "scheduled",
            }
            fixtures.append(fixture)

        return fixtures

    async def refresh_all_fixtures(self) -> Dict[str, int]:
        """
        刷新所有比赛的赛程信息

        Returns:
            收集统计信息
        """
        stats = {
            "total_fixtures": 0,
            "new_fixtures": 0,
            "updated_fixtures": 0,
            "errors": 0,
        }

        try:
            # 获取所有活跃的球队
            result = await self.db_session.execute(
                select(Team).where(Team.is_active is True)
            )
            teams = result.scalars().all()

            # 为每个球队收集赛程
            for team in teams:
                fixtures = await self.collect_team_fixtures(
                    team.id,
                    days_ahead=90,
                    force_refresh=True,
                )

                stats["total_fixtures"] += len(fixtures)
                # 这里可以根据实际情况统计新增和更新的比赛

            logger.info(f"刷新完成，总共收集 {stats['total_fixtures']} 场比赛")

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"刷新所有赛程失败: {e}")
            stats["errors"] += 1

        return stats


class FixturesCollectorFactory:
    """赛程收集器工厂类"""

    @staticmethod
    def create() -> FixturesCollector:
        """创建赛程收集器实例"""
        db_session = DatabaseManager()
        redis_client = RedisManager()
        return FixturesCollector(db_session, redis_client)
