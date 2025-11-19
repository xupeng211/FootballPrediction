"""足球数据缓存策略
Football Data Cache Strategy.

专门针对足球数据API的缓存管理，包括联赛、球队、比赛等数据的缓存策略和失效机制。
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .mock_redis import CacheKeyManager
from .redis_manager import get_redis_manager

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置."""

    # 联赛数据缓存时间（小时）
    league_cache_hours: int = 24
    # 球队数据缓存时间（小时）
    team_cache_hours: int = 48
    # 比赛数据缓存时间（分钟）
    match_cache_minutes: int = 15
    # 积分榜数据缓存时间（分钟）
    standings_cache_minutes: int = 30
    # API响应缓存时间（分钟）
    api_response_cache_minutes: int = 10
    # 统计数据缓存时间（小时）
    statistics_cache_hours: int = 6


class FootballDataCacheManager:
    """足球数据缓存管理器."""

    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()
        self.redis = get_redis_manager()
        self.key_manager = CacheKeyManager()

        # 缓存键前缀
        self.prefixes = {
            "league": "football:league",
            "team": "football:team",
            "match": "football:match",
            "standings": "football:standings",
            "api_response": "football:api",
            "statistics": "football:stats",
            "sync_status": "football:sync",
        }

    # ==================== 键管理方法 ====================

    def _make_key(self, prefix: str, identifier: str, suffix: str = "") -> str:
        """生成缓存键."""
        key = f"{prefix}:{identifier}"
        if suffix:
            key += f":{suffix}"
        return key

    def _make_list_key(self, prefix: str, filters: dict[str, Any] = None) -> str:
        """生成列表缓存键."""
        filter_str = ""
        if filters:
            sorted_items = sorted(filters.items())
            filter_str = ":" + ":".join(f"{k}={v}" for k, v in sorted_items)
        return f"{prefix}:list{filter_str}"

    # ==================== 联赛数据缓存 ====================

    async def cache_league(self, league_data: dict[str, Any]) -> bool:
        """缓存联赛数据."""
        try:
            league_id = league_data.get("external_id") or league_data.get("id")
            if not league_id:
                return False

            key = self._make_key(self.prefixes["league"], str(league_id))
            ttl = self.config.league_cache_hours * 3600

            success = await self.redis.aset(key, json.dumps(league_data), ex=ttl)

            # 同时添加到联赛列表
            list_key = self._make_list_key(self.prefixes["league"])
            await self.redis.asadd(list_key, str(league_id))

            if success:
                logger.debug(f"Cached league data: {league_id}")
            return success

        except Exception as e:
            logger.error(f"Error caching league data: {e}")
            return False

    async def get_cached_league(self, league_id: str) -> dict[str, Any] | None:
        """获取缓存的联赛数据."""
        try:
            key = self._make_key(self.prefixes["league"], league_id)
            data = await self.redis.aget(key)

            if data:
                logger.debug(f"Cache hit for league: {league_id}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for league: {league_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached league data: {e}")
            return None

    async def cache_league_list(
        self, leagues: list[dict[str, Any]], filters: dict[str, Any] = None
    ) -> bool:
        """缓存联赛列表."""
        try:
            list_key = self._make_list_key(self.prefixes["league"], filters)
            ttl = self.config.league_cache_hours * 3600

            # 序列化联赛数据
            serialized_data = json.dumps(leagues)
            success = await self.redis.aset(list_key, serialized_data, ex=ttl)

            if success:
                logger.debug(f"Cached league list with {len(leagues)} items")
            return success

        except Exception as e:
            logger.error(f"Error caching league list: {e}")
            return False

    async def get_cached_league_list(
        self, filters: dict[str, Any] = None
    ) -> list[dict[str, Any]] | None:
        """获取缓存的联赛列表."""
        try:
            list_key = self._make_list_key(self.prefixes["league"], filters)
            data = await self.redis.aget(list_key)

            if data:
                logger.debug("Cache hit for league list")
                return json.loads(data)
            else:
                logger.debug("Cache miss for league list")
                return None

        except Exception as e:
            logger.error(f"Error getting cached league list: {e}")
            return None

    # ==================== 球队数据缓存 ====================

    async def cache_team(self, team_data: dict[str, Any]) -> bool:
        """缓存球队数据."""
        try:
            team_id = team_data.get("external_id") or team_data.get("id")
            if not team_id:
                return False

            key = self._make_key(self.prefixes["team"], str(team_id))
            ttl = self.config.team_cache_hours * 3600

            success = await self.redis.aset(key, json.dumps(team_data), ex=ttl)

            # 如果有关联的联赛，添加到联赛的球队列表
            competition_id = team_data.get("competition_id")
            if competition_id:
                team_list_key = self._make_key(
                    self.prefixes["team"], f"competition:{competition_id}"
                )
                await self.redis.asadd(team_list_key, str(team_id))

            if success:
                logger.debug(f"Cached team data: {team_id}")
            return success

        except Exception as e:
            logger.error(f"Error caching team data: {e}")
            return False

    async def get_cached_team(self, team_id: str) -> dict[str, Any] | None:
        """获取缓存的球队数据."""
        try:
            key = self._make_key(self.prefixes["team"], team_id)
            data = await self.redis.aget(key)

            if data:
                logger.debug(f"Cache hit for team: {team_id}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for team: {team_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached team data: {e}")
            return None

    async def cache_competition_teams(
        self, competition_id: str, teams: list[dict[str, Any]]
    ) -> bool:
        """缓存联赛球队列表."""
        try:
            key = self._make_key(self.prefixes["team"], f"competition:{competition_id}")
            ttl = self.config.team_cache_hours * 3600

            serialized_data = json.dumps(teams)
            success = await self.redis.aset(key, serialized_data, ex=ttl)

            if success:
                logger.debug(
                    f"Cached competition teams: {competition_id}, {len(teams)} teams"
                )
            return success

        except Exception as e:
            logger.error(f"Error caching competition teams: {e}")
            return False

    async def get_cached_competition_teams(
        self, competition_id: str
    ) -> list[dict[str, Any]] | None:
        """获取缓存的联赛球队列表."""
        try:
            key = self._make_key(self.prefixes["team"], f"competition:{competition_id}")
            data = await self.redis.aget(key)

            if data:
                logger.debug(f"Cache hit for competition teams: {competition_id}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for competition teams: {competition_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached competition teams: {e}")
            return None

    # ==================== 比赛数据缓存 ====================

    async def cache_match(self, match_data: dict[str, Any]) -> bool:
        """缓存比赛数据."""
        try:
            match_id = match_data.get("external_id") or match_data.get("id")
            if not match_id:
                return False

            key = self._make_key(self.prefixes["match"], str(match_id))
            ttl = self.config.match_cache_minutes * 60

            success = await self.redis.aset(key, json.dumps(match_data), ex=ttl)

            if success:
                logger.debug(f"Cached match data: {match_id}")
            return success

        except Exception as e:
            logger.error(f"Error caching match data: {e}")
            return False

    async def get_cached_match(self, match_id: str) -> dict[str, Any] | None:
        """获取缓存的比赛数据."""
        try:
            key = self._make_key(self.prefixes["match"], match_id)
            data = await self.redis.aget(key)

            if data:
                logger.debug(f"Cache hit for match: {match_id}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for match: {match_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached match data: {e}")
            return None

    async def cache_team_matches(
        self, team_id: str, matches: list[dict[str, Any]]
    ) -> bool:
        """缓存球队比赛列表."""
        try:
            key = self._make_key(self.prefixes["match"], f"team:{team_id}")
            ttl = self.config.match_cache_minutes * 60

            serialized_data = json.dumps(matches)
            success = await self.redis.aset(key, serialized_data, ex=ttl)

            if success:
                logger.debug(f"Cached team matches: {team_id}, {len(matches)} matches")
            return success

        except Exception as e:
            logger.error(f"Error caching team matches: {e}")
            return False

    # ==================== 积分榜数据缓存 ====================

    async def cache_standings(
        self, competition_id: str, standings: list[dict[str, Any]]
    ) -> bool:
        """缓存积分榜数据."""
        try:
            key = self._make_key(self.prefixes["standings"], competition_id)
            ttl = self.config.standings_cache_minutes * 60

            serialized_data = json.dumps(standings)
            success = await self.redis.aset(key, serialized_data, ex=ttl)

            if success:
                logger.debug(
                    f"Cached standings: {competition_id}, {len(standings)} teams"
                )
            return success

        except Exception as e:
            logger.error(f"Error caching standings: {e}")
            return False

    async def get_cached_standings(
        self, competition_id: str
    ) -> list[dict[str, Any]] | None:
        """获取缓存的积分榜数据."""
        try:
            key = self._make_key(self.prefixes["standings"], competition_id)
            data = await self.redis.aget(key)

            if data:
                logger.debug(f"Cache hit for standings: {competition_id}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for standings: {competition_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached standings: {e}")
            return None

    # ==================== API响应缓存 ====================

    async def cache_api_response(
        self, endpoint: str, params: dict[str, Any], response_data: dict[str, Any]
    ) -> bool:
        """缓存API响应."""
        try:
            # 生成唯一的缓存键
            params_str = json.dumps(params, sort_keys=True) if params else ""
            cache_key = self._make_key(
                self.prefixes["api_response"], f"{endpoint}:{hash(params_str)}"
            )
            ttl = self.config.api_response_cache_minutes * 60

            # 添加缓存时间戳
            cache_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": response_data,
            }

            success = await self.redis.aset(cache_key, json.dumps(cache_data), ex=ttl)

            if success:
                logger.debug(f"Cached API response: {endpoint}")
            return success

        except Exception as e:
            logger.error(f"Error caching API response: {e}")
            return False

    async def get_cached_api_response(
        self, endpoint: str, params: dict[str, Any] = None
    ) -> dict[str, Any] | None:
        """获取缓存的API响应."""
        try:
            params_str = json.dumps(params, sort_keys=True) if params else ""
            cache_key = self._make_key(
                self.prefixes["api_response"], f"{endpoint}:{hash(params_str)}"
            )
            data = await self.redis.aget(cache_key)

            if data:
                cache_data = json.loads(data)
                logger.debug(f"Cache hit for API response: {endpoint}")
                return cache_data.get("data")
            else:
                logger.debug(f"Cache miss for API response: {endpoint}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached API response: {e}")
            return None

    # ==================== 统计数据缓存 ====================

    async def cache_statistics(self, key: str, statistics: dict[str, Any]) -> bool:
        """缓存统计数据."""
        try:
            cache_key = self._make_key(self.prefixes["statistics"], key)
            ttl = self.config.statistics_cache_hours * 3600

            success = await self.redis.aset(cache_key, json.dumps(statistics), ex=ttl)

            if success:
                logger.debug(f"Cached statistics: {key}")
            return success

        except Exception as e:
            logger.error(f"Error caching statistics: {e}")
            return False

    async def get_cached_statistics(self, key: str) -> dict[str, Any] | None:
        """获取缓存的统计数据."""
        try:
            cache_key = self._make_key(self.prefixes["statistics"], key)
            data = await self.redis.aget(cache_key)

            if data:
                logger.debug(f"Cache hit for statistics: {key}")
                return json.loads(data)
            else:
                logger.debug(f"Cache miss for statistics: {key}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached statistics: {e}")
            return None

    # ==================== 同步状态缓存 ====================

    async def set_sync_status(self, sync_type: str, status: dict[str, Any]) -> bool:
        """设置同步状态."""
        try:
            key = self._make_key(self.prefixes["sync_status"], sync_type)
            # 同步状态较短TTL，避免状态过期
            ttl = 3600  # 1小时

            status_data = {"timestamp": datetime.utcnow().isoformat(), "status": status}

            success = await self.redis.aset(key, json.dumps(status_data), ex=ttl)

            if success:
                logger.debug(f"Set sync status: {sync_type}")
            return success

        except Exception as e:
            logger.error(f"Error setting sync status: {e}")
            return False

    async def get_sync_status(self, sync_type: str) -> dict[str, Any] | None:
        """获取同步状态."""
        try:
            key = self._make_key(self.prefixes["sync_status"], sync_type)
            data = await self.redis.aget(key)

            if data:
                status_data = json.loads(data)
                logger.debug(f"Got sync status: {sync_type}")
                return status_data
            else:
                logger.debug(f"No sync status found: {sync_type}")
                return None

        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return None

    # ==================== 缓存管理方法 ====================

    async def invalidate_league_cache(self, league_id: str = None) -> int:
        """失效联赛缓存."""
        try:
            if league_id:
                # 失效特定联赛
                key = self._make_key(self.prefixes["league"], league_id)
                return await self.redis.adelete(key)
            else:
                # 失效所有联赛缓存
                pattern = f"{self.prefixes['league']}:*"
                return await self.redis.adelete_pattern(pattern)

        except Exception as e:
            logger.error(f"Error invalidating league cache: {e}")
            return 0

    async def invalidate_team_cache(self, team_id: str = None) -> int:
        """失效球队缓存."""
        try:
            if team_id:
                key = self._make_key(self.prefixes["team"], team_id)
                return await self.redis.adelete(key)
            else:
                pattern = f"{self.prefixes['team']}:*"
                return await self.redis.adelete_pattern(pattern)

        except Exception as e:
            logger.error(f"Error invalidating team cache: {e}")
            return 0

    async def invalidate_match_cache(self, match_id: str = None) -> int:
        """失效比赛缓存."""
        try:
            if match_id:
                key = self._make_key(self.prefixes["match"], match_id)
                return await self.redis.adelete(key)
            else:
                pattern = f"{self.prefixes['match']}:*"
                return await self.redis.adelete_pattern(pattern)

        except Exception as e:
            logger.error(f"Error invalidating match cache: {e}")
            return 0

    async def invalidate_competition_cache(self, competition_id: str) -> int:
        """失效联赛相关的所有缓存."""
        try:
            keys_to_delete = []

            # 联赛数据
            keys_to_delete.append(
                self._make_key(self.prefixes["league"], competition_id)
            )
            # 积分榜数据
            keys_to_delete.append(
                self._make_key(self.prefixes["standings"], competition_id)
            )
            # 球队列表
            keys_to_delete.append(
                self._make_key(self.prefixes["team"], f"competition:{competition_id}")
            )

            # 批量删除
            deleted_count = 0
            for key in keys_to_delete:
                if await self.redis.adelete(key):
                    deleted_count += 1

            logger.debug(
                f"Invalidated {deleted_count} keys for competition: {competition_id}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Error invalidating competition cache: {e}")
            return 0

    async def get_cache_info(self) -> dict[str, Any]:
        """获取缓存信息统计."""
        try:
            info = {}

            for prefix_name, prefix in self.prefixes.items():
                pattern = f"{prefix}:*"
                keys = await self.redis.akeys(pattern)
                info[prefix_name] = {"key_count": len(keys), "prefix": prefix}

            return info

        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {}

    async def clear_all_football_cache(self) -> bool:
        """清空所有足球数据缓存."""
        try:
            total_deleted = 0
            for prefix in self.prefixes.values():
                pattern = f"{prefix}:*"
                deleted = await self.redis.adelete_pattern(pattern)
                total_deleted += deleted

            logger.info(f"Cleared {total_deleted} football cache keys")
            return True

        except Exception as e:
            logger.error(f"Error clearing football cache: {e}")
            return False


# 全局缓存管理器实例
_football_cache_manager = None


def get_football_cache_manager() -> FootballDataCacheManager:
    """获取足球数据缓存管理器实例."""
    global _football_cache_manager
    if _football_cache_manager is None:
        _football_cache_manager = FootballDataCacheManager()
    return _football_cache_manager


# 便捷函数
async def cache_league_data(league_data: dict[str, Any]) -> bool:
    """缓存联赛数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.cache_league(league_data)


async def get_cached_league_data(league_id: str) -> dict[str, Any] | None:
    """获取缓存的联赛数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.get_cached_league(league_id)


async def cache_team_data(team_data: dict[str, Any]) -> bool:
    """缓存球队数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.cache_team(team_data)


async def get_cached_team_data(team_id: str) -> dict[str, Any] | None:
    """获取缓存的球队数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.get_cached_team(team_id)


async def cache_standings_data(
    competition_id: str, standings: list[dict[str, Any]]
) -> bool:
    """缓存积分榜数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.cache_standings(competition_id, standings)


async def get_cached_standings_data(
    competition_id: str,
) -> list[dict[str, Any]] | None:
    """获取缓存的积分榜数据 - 便捷函数."""
    manager = get_football_cache_manager()
    return await manager.get_cached_standings(competition_id)
