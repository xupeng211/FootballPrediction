"""
增强版比赛赛程收集器
集成新的数据源管理器，支持多种数据源
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager
from src.core.logging_system import get_logger
from src.database.connection import DatabaseManager
from src.database.models.match import Match
from src.database.models.team import Team

from .data_sources import data_source_manager, MatchData, TeamData

logger = get_logger(__name__)


class EnhancedFixturesCollector:
    """增强版比赛赛程收集器"""

    def __init__(self, db_session: AsyncSession, redis_client: RedisManager):
        self.db_session = db_session
        self.redis_client = redis_client
        self.cache_timeout = 3600  # 1小时缓存
        self.data_source_manager = data_source_manager

    async def collect_all_fixtures(
        self,
        days_ahead: int = 30,
        force_refresh: bool = False,
        preferred_source: str = "mock",
    ) -> List[Dict[str, Any]]:
        """
        收集所有未来比赛

        Args:
            days_ahead: 向前搜索的天数
            force_refresh: 是否强制刷新缓存
            preferred_source: 首选数据源

        Returns:
            比赛信息列表
        """
        cache_key = f"fixtures:all:{days_ahead}:{preferred_source}"

        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.info("从缓存获取所有比赛数据")
                return cached_data

        try:
            # 获取数据源适配器
            adapter = self.data_source_manager.get_adapter(preferred_source)
            if not adapter:
                logger.error(f"数据源 {preferred_source} 不可用")
                return []

            # 收集比赛数据
            date_from = datetime.now()
            date_to = date_from + timedelta(days=days_ahead)

            matches_data = await adapter.get_matches(
                date_from=date_from, date_to=date_to
            )

            # 转换为数据库模型并保存
            fixtures = []
            for match_data in matches_data:
                try:
                    # 转换为字典格式
                    fixture_dict = self._convert_match_data_to_dict(match_data)

                    # 保存到数据库
                    await self._save_fixture_to_db(fixture_dict)

                    fixtures.append(fixture_dict)

                except Exception as e:
                    logger.error(f"处理比赛数据失败 {match_data.id}: {e}")
                    continue

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, fixtures, expire=self.cache_timeout
            )

            logger.info(f"从数据源 {preferred_source} 收集到 {len(fixtures)} 场比赛")
            return fixtures

        except Exception as e:
            logger.error(f"收集所有比赛失败: {e}")
            return []

    async def collect_team_fixtures(
        self,
        team_name: str,
        days_ahead: int = 30,
        force_refresh: bool = False,
        preferred_source: str = "mock",
    ) -> List[Dict[str, Any]]:
        """
        收集指定球队的未来比赛

        Args:
            team_name: 球队名称
            days_ahead: 向前搜索的天数
            force_refresh: 是否强制刷新缓存
            preferred_source: 首选数据源

        Returns:
            比赛信息列表
        """
        cache_key = f"fixtures:team:{team_name}:{days_ahead}:{preferred_source}"

        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取球队 {team_name} 的赛程")
                return cached_data

        try:
            # 获取数据源适配器
            adapter = self.data_source_manager.get_adapter(preferred_source)
            if not adapter:
                logger.error(f"数据源 {preferred_source} 不可用")
                return []

            # 收集比赛数据
            date_from = datetime.now()
            date_to = date_from + timedelta(days=days_ahead)

            matches_data = await adapter.get_matches(
                date_from=date_from, date_to=date_to
            )

            # 过滤指定球队的比赛
            team_fixtures = []
            for match_data in matches_data:
                if (
                    match_data.home_team.lower() == team_name.lower()
                    or match_data.away_team.lower() == team_name.lower()
                ):

                    # 转换为字典格式
                    fixture_dict = self._convert_match_data_to_dict(match_data)

                    # 保存到数据库
                    await self._save_fixture_to_db(fixture_dict)

                    team_fixtures.append(fixture_dict)

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, team_fixtures, expire=self.cache_timeout
            )

            logger.info(f"收集到球队 {team_name} 的 {len(team_fixtures)} 场比赛")
            return team_fixtures

        except Exception as e:
            logger.error(f"收集球队 {team_name} 赛程失败: {e}")
            return []

    async def collect_league_fixtures(
        self,
        league_name: str,
        days_ahead: int = 30,
        force_refresh: bool = False,
        preferred_source: str = "mock",
    ) -> List[Dict[str, Any]]:
        """
        收集联赛的比赛赛程

        Args:
            league_name: 联赛名称
            days_ahead: 向前搜索的天数
            force_refresh: 是否强制刷新缓存
            preferred_source: 首选数据源

        Returns:
            比赛信息列表
        """
        cache_key = f"fixtures:league:{league_name}:{days_ahead}:{preferred_source}"

        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取联赛 {league_name} 的赛程")
                return cached_data

        try:
            # 获取数据源适配器
            adapter = self.data_source_manager.get_adapter(preferred_source)
            if not adapter:
                logger.error(f"数据源 {preferred_source} 不可用")
                return []

            # 收集比赛数据
            date_from = datetime.now()
            date_to = date_from + timedelta(days=days_ahead)

            matches_data = await adapter.get_matches(
                date_from=date_from, date_to=date_to
            )

            # 过滤指定联赛的比赛
            league_fixtures = []
            for match_data in matches_data:
                if match_data.league.lower() == league_name.lower():

                    # 转换为字典格式
                    fixture_dict = self._convert_match_data_to_dict(match_data)

                    # 保存到数据库
                    await self._save_fixture_to_db(fixture_dict)

                    league_fixtures.append(fixture_dict)

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, league_fixtures, expire=self.cache_timeout
            )

            logger.info(f"收集到联赛 {league_name} 的 {len(league_fixtures)} 场比赛")
            return league_fixtures

        except Exception as e:
            logger.error(f"收集联赛 {league_name} 赛程失败: {e}")
            return []

    async def collect_teams(
        self,
        league_name: Optional[str] = None,
        force_refresh: bool = False,
        preferred_source: str = "mock",
    ) -> List[Dict[str, Any]]:
        """
        收集球队信息

        Args:
            league_name: 联赛名称（可选）
            force_refresh: 是否强制刷新缓存
            preferred_source: 首选数据源

        Returns:
            球队信息列表
        """
        cache_key = f"teams:{league_name or 'all'}:{preferred_source}"

        # 尝试从缓存获取
        if not force_refresh:
            cached_data = await self.redis_client.get_cache_value(cache_key)
            if cached_data:
                logger.debug("从缓存获取球队数据")
                return cached_data

        try:
            # 获取数据源适配器
            adapter = self.data_source_manager.get_adapter(preferred_source)
            if not adapter:
                logger.error(f"数据源 {preferred_source} 不可用")
                return []

            # 收集球队数据
            teams_data = await adapter.get_teams()

            # 转换为字典格式
            teams = []
            for team_data in teams_data:
                team_dict = self._convert_team_data_to_dict(team_data)

                # 保存到数据库
                await self._save_team_to_db(team_dict)

                teams.append(team_dict)

            # 缓存结果
            await self.redis_client.set_cache_value(
                cache_key, teams, expire=self.cache_timeout * 2  # 球队数据缓存更久
            )

            logger.info(f"收集到 {len(teams)} 支球队信息")
            return teams

        except Exception as e:
            logger.error(f"收集球队信息失败: {e}")
            return []

    def _convert_match_data_to_dict(self, match_data: MatchData) -> Dict[str, Any]:
        """将MatchData转换为字典格式"""
        return {
            "id": match_data.id,
            "home_team": match_data.home_team,
            "away_team": match_data.away_team,
            "home_team_id": match_data.home_team_id,
            "away_team_id": match_data.away_team_id,
            "match_date": (
                match_data.match_date.isoformat() if match_data.match_date else None
            ),
            "league": match_data.league,
            "league_id": match_data.league_id,
            "status": match_data.status,
            "home_score": match_data.home_score,
            "away_score": match_data.away_score,
            "round": match_data.round,
            "venue": match_data.venue,
            "data_source": "enhanced_collector",
        }

    def _convert_team_data_to_dict(self, team_data: TeamData) -> Dict[str, Any]:
        """将TeamData转换为字典格式"""
        return {
            "id": team_data.id,
            "name": team_data.name,
            "short_name": team_data.short_name,
            "crest": team_data.crest,
            "founded": team_data.founded,
            "venue": team_data.venue,
            "website": team_data.website,
            "data_source": "enhanced_collector",
        }

    async def _save_fixture_to_db(self, fixture_dict: Dict[str, Any]) -> bool:
        """保存比赛到数据库"""
        try:
            # 检查比赛是否已存在
            existing_match = await self.db_session.get(Match, fixture_dict["id"])

            if existing_match:
                # 更新现有比赛
                for key, value in fixture_dict.items():
                    if hasattr(existing_match, key):
                        setattr(existing_match, key, value)
                logger.debug(f"更新比赛 {fixture_dict['id']}")
            else:
                # 创建新比赛
                new_match = Match(**fixture_dict)
                self.db_session.add(new_match)
                logger.debug(f"创建比赛 {fixture_dict['id']}")

            await self.db_session.commit()
            return True

        except Exception as e:
            logger.error(f"保存比赛到数据库失败: {e}")
            await self.db_session.rollback()
            return False

    async def _save_team_to_db(self, team_dict: Dict[str, Any]) -> bool:
        """保存球队到数据库"""
        try:
            # 检查球队是否已存在
            existing_team = await self.db_session.get(Team, team_dict["id"])

            if existing_team:
                # 更新现有球队
                for key, value in team_dict.items():
                    if hasattr(existing_team, key):
                        setattr(existing_team, key, value)
                logger.debug(f"更新球队 {team_dict['id']}")
            else:
                # 创建新球队
                new_team = Team(**team_dict)
                self.db_session.add(new_team)
                logger.debug(f"创建球队 {team_dict['id']}")

            await self.db_session.commit()
            return True

        except Exception as e:
            logger.error(f"保存球队到数据库失败: {e}")
            await self.db_session.rollback()
            return False

    async def get_data_source_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        available_sources = self.data_source_manager.get_available_sources()

        status = {
            "available_sources": available_sources,
            "primary_source": "mock",  # 默认使用mock数据源
            "total_matches": 0,
            "total_teams": 0,
            "last_update": None,
        }

        # 尝试从mock数据源获取一些基本信息
        try:
            adapter = self.data_source_manager.get_adapter("mock")
            if adapter:
                matches = await adapter.get_matches()
                teams = await adapter.get_teams()
                status["total_matches"] = len(matches)
                status["total_teams"] = len(teams)
                status["last_update"] = datetime.now().isoformat()
        except Exception as e:
            logger.error(f"获取数据源状态失败: {e}")

        return status
