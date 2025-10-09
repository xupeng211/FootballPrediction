"""
缓存预热管理器

负责在系统启动和运行时预热高频访问的缓存数据
"""

import logging
from datetime import datetime, timedelta
from typing import Dict

from ..core.key_manager import CacheKeyManager


logger = logging.getLogger(__name__)


class CacheWarmupManager:
    """
    缓存预热管理器

    负责在系统启动和运行时预热高频访问的缓存数据
    """

    def __init__(self, redis_manager):
        self.redis_manager = redis_manager
        self.key_manager = CacheKeyManager()

    async def warmup_match_cache(self, match_id: int) -> bool:
        """
        预热比赛相关缓存

        Args:
            match_id: 比赛ID

        Returns:
            bool: 预热是否成功
        """
        try:
            from sqlalchemy import select

            from src.database.connection import get_async_session
            from src.database.models import Match

            async with get_async_session() as session:
                # 获取比赛基本信息
                result = await session.execute(
                    select(Match).where(Match.id == match_id)
                )
                match = result.scalar_one_or_none()

                if not match:
                    return False

                # 缓存比赛信息
                match_info_key = self.key_manager.build_key("match", match_id, "info")
                match_data = {
                    "id": match.id,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "match_time": match.match_time.isoformat(),
                    "league_id": match.league_id,
                    "status": match.match_status.value,
                    "venue": match.venue,
                }
                await self.redis_manager.aset(
                    match_info_key, match_data, self.key_manager.get_ttl("match_info")
                )

                # 缓存比赛特征
                features_key = self.key_manager.build_key("match", match_id, "features")
                await self.redis_manager.aset(
                    features_key,
                    {"match_id": match_id, "features_ready": True},
                    self.key_manager.get_ttl("match_features"),
                )

                logger.info(f"预热比赛缓存成功: match_id={match_id}")
                return True

        except Exception as e:
            logger.error(f"预热比赛缓存失败: {e}")
            return False

    async def warmup_team_cache(self, team_id: int) -> bool:
        """
        预热球队相关缓存

        Args:
            team_id: 球队ID

        Returns:
            bool: 预热是否成功
        """
        try:
            from sqlalchemy import select

            from src.database.connection import get_async_session
            from src.database.models import Team

            async with get_async_session() as session:
                # 获取球队基本信息
                result = await session.execute(select(Team).where(Team.id == team_id))
                team = result.scalar_one_or_none()

                if not team:
                    return False

                # 缓存球队信息
                team_info_key = self.key_manager.build_key("team", team_id, "info")
                team_data = {
                    "id": team.id,
                    "name": team.team_name,
                    "country": team.country,
                    "founded": team.founded_year,
                    "stadium": team.stadium,
                }
                await self.redis_manager.aset(
                    team_info_key, team_data, self.key_manager.get_ttl("team_stats")
                )

                # 缓存球队特征
                features_key = self.key_manager.build_key("team", team_id, "features")
                await self.redis_manager.aset(
                    features_key,
                    {"team_id": team_id, "features_ready": True},
                    self.key_manager.get_ttl("team_features"),
                )

                logger.info(f"预热球队缓存成功: team_id={team_id}")
                return True

        except Exception as e:
            logger.error(f"预热球队缓存失败: {e}")
            return False

    async def warmup_upcoming_matches(self, hours_ahead: int = 24) -> int:
        """
        预热即将开始比赛的缓存

        Args:
            hours_ahead: 预热未来多少小时内的比赛

        Returns:
            int: 成功预热的比赛数量
        """
        try:
            from sqlalchemy import select

            from src.database.connection import get_async_session
            from src.database.models import Match

            async with get_async_session() as session:
                # 查询未来N小时内的比赛
                cutoff_time = datetime.now() + timedelta(hours=hours_ahead)
                result = await session.execute(
                    select(Match).where(
                        Match.match_time <= cutoff_time,
                        Match.match_time >= datetime.now(),
                        Match.match_status == "scheduled",
                    )
                )
                matches = result.scalars().all()

                success_count = 0
                for match in matches:
                    if await self.warmup_match_cache(int(match.id)):
                        success_count += 1
                        # 预热主客队缓存
                        await self.warmup_team_cache(match.home_team_id)
                        await self.warmup_team_cache(match.away_team_id)

                logger.info(f"预热即将开始比赛缓存完成: {success_count}/{len(matches)}")
                return success_count

        except Exception as e:
            logger.error(f"预热即将开始比赛缓存失败: {e}")
            return 0

    async def warmup_historical_stats(self, days: int = 7) -> bool:
        """
        预热历史统计数据缓存

        Args:
            days: 统计最近多少天的数据

        Returns:
            bool: 预热是否成功
        """
        try:
            stats_key = self.key_manager.build_key("stats", "historical", "summary")
            stats_data = {
                "period_days": days,
                "total_matches": 0,  # 这里可以填充实际统计数据
                "avg_goals": 0.0,
                "prediction_accuracy": 0.0,
                "last_updated": datetime.now().isoformat(),
            }

            await self.redis_manager.aset(
                stats_key, stats_data, self.key_manager.get_ttl("historical_stats")
            )

            logger.info(f"预热历史统计缓存成功: days={days}")
            return True

        except Exception as e:
            logger.error(f"预热历史统计缓存失败: {e}")
            return False

    async def full_warmup(self) -> Dict[str, int]:
        """
        执行完整的缓存预热

        Returns:
            Dict[str, int]: 各类缓存预热结果统计
        """
        logger.info("开始执行完整缓存预热...")

        results = {"upcoming_matches": 0, "historical_stats": 0, "total": 0}

        try:
            # 预热即将开始的比赛
            matches_count = await self.warmup_upcoming_matches()
            results["upcoming_matches"] = matches_count

            # 预热历史统计
            stats_success = await self.warmup_historical_stats()
            results["historical_stats"] = 1 if stats_success else 0

            results["total"] = results["upcoming_matches"] + results["historical_stats"]

            logger.info(f"缓存预热完成: {results}")
            return results

        except Exception as e:
            logger.error(f"完整缓存预热失败: {e}")
            return results


async def warmup_cache_on_startup(redis_manager) -> Dict[str, int]:
    """
    系统启动时的缓存预热函数

    Args:
        redis_manager: Redis管理器实例

    Returns:
        Dict[str, int]: 预热结果统计
    """
    warmup_manager = CacheWarmupManager(redis_manager)
    return await warmup_manager.full_warmup()