"""异步数据服务模块
Async Data Service Module.

提供比赛数据管理的核心业务逻辑，支持异步操作。
Provides core business logic for match data management with async support.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session

logger = logging.getLogger(__name__)


class AsyncDataService:
    """异步数据服务类 - 统一的数据管理服务."""

    def __init__(self):
        """初始化异步数据服务."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_matches_list(
        self, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """获取比赛列表 (异步版本)
        Get matches list (async version).

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            比赛列表数据
        """
        try:
            # 尝试从数据库获取数据
            async with get_async_session() as session:
                # 获取总数
                count_query = text("SELECT COUNT(*) FROM matches")
                count_result = await session.execute(count_query)
                total = count_result.scalar()

                # 获取分页数据
                query = text(
                    """
                    SELECT
                        m.id,
                        m.home_team_id,
                        m.away_team_id,
                        m.scheduled_at,
                        m.status,
                        m.venue,
                        ht.name as home_team_name,
                        ht.short_name as home_team_short_name,
                        at.name as away_team_name,
                        at.short_name as away_team_short_name,
                        l.name as league_name,
                        l.country as league_country
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    JOIN leagues l ON m.league_id = l.id
                    ORDER BY m.scheduled_at DESC
                    LIMIT :limit OFFSET :offset
                """
                )

                result = await session.execute(
                    query, {"limit": limit, "offset": offset}
                )
                rows = result.fetchall()

                # 格式化数据
                matches = []
                for row in rows:
                    matches.append(
                        {
                            "id": row[0],
                            "home_team": {
                                "id": row[1],
                                "name": row[6],
                                "short_name": row[7],
                            },
                            "away_team": {
                                "id": row[2],
                                "name": row[8],
                                "short_name": row[9],
                            },
                            "date": row[3].isoformat() if row[3] else None,
                            "status": row[4],
                            "venue": row[5],
                            "league": {
                                "id": 0,  # 可以从查询中添加
                                "name": row[10],
                                "country": row[11],
                            },
                        }
                    )

                self.logger.info(f"从数据库获取 {len(matches)} 条比赛记录")
                return {
                    "matches": matches,
                    "total": total or len(matches),
                    "limit": limit,
                    "offset": offset,
                    "source": "database",
                }

        except Exception as e:
            self.logger.warning(f"从数据库获取比赛失败，使用模拟数据: {e}")
            # 降级到模拟数据
            return await self._get_mock_matches_list(limit, offset)

    async def _get_mock_matches_list(
        self, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """获取模拟比赛数据
        Get mock matches data.
        """
        # 模拟异步操作延迟
        await asyncio.sleep(0.001)  # 1ms延迟模拟数据库查询

        sample_matches = [
            {
                "id": 12345,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
            },
            {
                "id": 12346,
                "home_team": {"id": 3, "name": "Chelsea", "short_name": "CHE"},
                "away_team": {"id": 4, "name": "Arsenal", "short_name": "ARS"},
                "date": "2025-11-11T17:30:00.000Z",
                "status": "SCHEDULED",
                "venue": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
            },
            {
                "id": 12347,
                "home_team": {"id": 5, "name": "Barcelona", "short_name": "BAR"},
                "away_team": {"id": 6, "name": "Real Madrid", "short_name": "RMA"},
                "date": "2025-11-12T20:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Camp Nou",
                "league": {"id": 140, "name": "La Liga", "country": "Spain"},
            },
        ]

        start = offset
        end = start + limit
        paginated_matches = sample_matches[start:end]

        return {
            "matches": paginated_matches,
            "total": len(sample_matches),
            "limit": limit,
            "offset": offset,
            "source": "mock",
        }

    async def get_match_by_id(self, match_id: int) -> Optional[dict[str, Any]]:
        """根据ID获取比赛信息 (异步版本)
        Get match information by ID (async version).

        Args:
            match_id: 比赛ID

        Returns:
            比赛信息
        """
        try:
            # 尝试从数据库获取数据
            async with get_async_session() as session:
                query = text(
                    """
                    SELECT
                        m.id,
                        m.home_team_id,
                        m.away_team_id,
                        m.scheduled_at,
                        m.status,
                        m.venue,
                        m.home_score,
                        m.away_score,
                        ht.name as home_team_name,
                        ht.short_name as home_team_short_name,
                        at.name as away_team_name,
                        at.short_name as away_team_short_name,
                        l.name as league_name,
                        l.country as league_country
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    JOIN leagues l ON m.league_id = l.id
                    WHERE m.id = :match_id
                """
                )

                result = await session.execute(query, {"match_id": match_id})
                row = result.first()

                if row:
                    self.logger.info(f"从数据库获取比赛 {match_id} 信息")
                    return {
                        "id": row[0],
                        "home_team": {
                            "id": row[1],
                            "name": row[7],
                            "short_name": row[8],
                        },
                        "away_team": {
                            "id": row[2],
                            "name": row[9],
                            "short_name": row[10],
                        },
                        "date": row[3].isoformat() if row[3] else None,
                        "status": row[4],
                        "venue": row[5],
                        "score": (
                            {"home": row[6], "away": row[7]}
                            if row[6] is not None and row[7] is not None
                            else None
                        ),
                        "league": {"name": row[11], "country": row[12]},
                        "source": "database",
                    }
                else:
                    return await self._get_mock_match_by_id(match_id)

        except Exception as e:
            self.logger.warning(f"从数据库获取比赛 {match_id} 失败，使用模拟数据: {e}")
            return await self._get_mock_match_by_id(match_id)

    async def _get_mock_match_by_id(self, match_id: int) -> Optional[dict[str, Any]]:
        """获取模拟比赛信息
        Get mock match information.
        """
        # 模拟异步操作延迟
        await asyncio.sleep(0.001)

        sample_matches = {
            12345: {
                "id": 12345,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
                "statistics": {
                    "possession": {"home": 52, "away": 48},
                    "shots": {"home": 12, "away": 8},
                    "corners": {"home": 6, "away": 4},
                },
                "source": "mock",
            },
            12346: {
                "id": 12346,
                "home_team": {"id": 3, "name": "Chelsea", "short_name": "CHE"},
                "away_team": {"id": 4, "name": "Arsenal", "short_name": "ARS"},
                "date": "2025-11-11T17:30:00.000Z",
                "status": "SCHEDULED",
                "venue": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
                "statistics": {
                    "possession": {"home": 48, "away": 52},
                    "shots": {"home": 9, "away": 11},
                    "corners": {"home": 5, "away": 7},
                },
                "source": "mock",
            },
        }

        return sample_matches.get(match_id)

    async def get_teams_list(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """获取球队列表 (异步版本)
        Get teams list (async version).

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            球队列表数据
        """
        try:
            # 尝试从数据库获取数据
            async with get_async_session() as session:
                # 获取总数
                count_query = text("SELECT COUNT(*) FROM teams")
                count_result = await session.execute(count_query)
                total = count_result.scalar()

                # 获取分页数据
                query = text(
                    """
                    SELECT
                        t.id,
                        t.name,
                        t.short_name,
                        t.country,
                        t.founded,
                        t.stadium,
                        l.name as league_name
                    FROM teams t
                    LEFT JOIN leagues l ON t.league_id = l.id
                    ORDER BY t.name
                    LIMIT :limit OFFSET :offset
                """
                )

                result = await session.execute(
                    query, {"limit": limit, "offset": offset}
                )
                rows = result.fetchall()

                # 格式化数据
                teams = []
                for row in rows:
                    teams.append(
                        {
                            "id": row[0],
                            "name": row[1],
                            "short_name": row[2],
                            "country": row[3],
                            "founded": row[4],
                            "stadium": row[5],
                            "league": {"name": row[6]} if row[6] else None,
                        }
                    )

                self.logger.info(f"从数据库获取 {len(teams)} 支球队记录")
                return {
                    "teams": teams,
                    "total": total or len(teams),
                    "limit": limit,
                    "offset": offset,
                    "source": "database",
                }

        except Exception as e:
            self.logger.warning(f"从数据库获取球队失败，使用模拟数据: {e}")
            return await self._get_mock_teams_list(limit, offset)

    async def _get_mock_teams_list(
        self, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """获取模拟球队数据
        Get mock teams data.
        """
        await asyncio.sleep(0.001)

        sample_teams = [
            {
                "id": 1,
                "name": "Manchester United",
                "short_name": "MU",
                "country": "England",
                "founded": 1878,
                "stadium": "Old Trafford",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 2,
                "name": "Liverpool",
                "short_name": "LIV",
                "country": "England",
                "founded": 1892,
                "stadium": "Anfield",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 3,
                "name": "Chelsea",
                "short_name": "CHE",
                "country": "England",
                "founded": 1905,
                "stadium": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 4,
                "name": "Arsenal",
                "short_name": "ARS",
                "country": "England",
                "founded": 1886,
                "stadium": "Emirates Stadium",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 5,
                "name": "Barcelona",
                "short_name": "BAR",
                "country": "Spain",
                "founded": 1899,
                "stadium": "Camp Nou",
                "league": {"id": 140, "name": "La Liga"},
            },
            {
                "id": 6,
                "name": "Real Madrid",
                "short_name": "RMA",
                "country": "Spain",
                "founded": 1902,
                "stadium": "Santiago Bernabéu",
                "league": {"id": 140, "name": "La Liga"},
            },
        ]

        start = offset
        end = start + limit
        paginated_teams = sample_teams[start:end]

        return {
            "teams": paginated_teams,
            "total": len(sample_teams),
            "limit": limit,
            "offset": offset,
            "source": "mock",
        }

    async def get_team_by_id(self, team_id: int) -> Optional[dict[str, Any]]:
        """根据ID获取球队信息 (异步版本)
        Get team information by ID (async version).

        Args:
            team_id: 球队ID

        Returns:
            球队信息
        """
        try:
            async with get_async_session() as session:
                query = text(
                    """
                    SELECT
                        t.id,
                        t.name,
                        t.short_name,
                        t.country,
                        t.founded,
                        t.stadium,
                        l.name as league_name
                    FROM teams t
                    LEFT JOIN leagues l ON t.league_id = l.id
                    WHERE t.id = :team_id
                """
                )

                result = await session.execute(query, {"team_id": team_id})
                row = result.first()

                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "short_name": row[2],
                        "country": row[3],
                        "founded": row[4],
                        "stadium": row[5],
                        "league": {"name": row[6]} if row[6] else None,
                        "source": "database",
                    }
                else:
                    return await self._get_mock_team_by_id(team_id)

        except Exception as e:
            self.logger.warning(f"从数据库获取球队 {team_id} 失败，使用模拟数据: {e}")
            return await self._get_mock_team_by_id(team_id)

    async def _get_mock_team_by_id(self, team_id: int) -> Optional[dict[str, Any]]:
        """获取模拟球队信息
        Get mock team information.
        """
        await asyncio.sleep(0.001)

        sample_teams = {
            1: {
                "id": 1,
                "name": "Manchester United",
                "short_name": "MU",
                "country": "England",
                "founded": 1878,
                "stadium": "Old Trafford",
                "league": {"id": 39, "name": "Premier League"},
                "statistics": {
                    "matches_played": 38,
                    "wins": 21,
                    "draws": 8,
                    "losses": 9,
                    "goals_for": 62,
                    "goals_against": 38,
                },
                "source": "mock",
            },
            2: {
                "id": 2,
                "name": "Liverpool",
                "short_name": "LIV",
                "country": "England",
                "founded": 1892,
                "stadium": "Anfield",
                "league": {"id": 39, "name": "Premier League"},
                "statistics": {
                    "matches_played": 38,
                    "wins": 25,
                    "draws": 7,
                    "losses": 6,
                    "goals_for": 68,
                    "goals_against": 33,
                },
                "source": "mock",
            },
        }

        return sample_teams.get(team_id)

    async def batch_get_matches(
        self, match_ids: list[int]
    ) -> list[Optional[dict[str, Any]]]:
        """批量获取比赛信息 (异步版本)
        Batch get matches information (async version).

        Args:
            match_ids: 比赛ID列表

        Returns:
            比赛信息列表
        """
        # 使用 asyncio.gather 并发获取比赛信息
        tasks = [self.get_match_by_id(match_id) for match_id in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        matches = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"获取比赛 {match_ids[i]} 信息失败: {result}")
                matches.append(None)
            else:
                matches.append(result)

        return matches

    async def get_upcoming_matches(self, limit: int = 20) -> dict[str, Any]:
        """获取即将开始的比赛 (异步版本)
        Get upcoming matches (async version).

        Args:
            limit: 返回数量限制

        Returns:
            即将开始的比赛数据
        """
        try:
            async with get_async_session() as session:
                query = text(
                    """
                    SELECT
                        m.id,
                        m.home_team_id,
                        m.away_team_id,
                        m.scheduled_at,
                        m.status,
                        m.venue,
                        ht.name as home_team_name,
                        ht.short_name as home_team_short_name,
                        at.name as away_team_name,
                        at.short_name as away_team_short_name,
                        l.name as league_name
                    FROM matches m
                    JOIN teams ht ON m.home_team_id = ht.id
                    JOIN teams at ON m.away_team_id = at.id
                    JOIN leagues l ON m.league_id = l.id
                    WHERE m.status IN ('SCHEDULED', 'TIMED')
                    AND m.scheduled_at >= NOW()
                    ORDER BY m.scheduled_at ASC
                    LIMIT :limit
                """
                )

                result = await session.execute(query, {"limit": limit})
                rows = result.fetchall()

                matches = []
                for row in rows:
                    matches.append(
                        {
                            "id": row[0],
                            "home_team": {
                                "id": row[1],
                                "name": row[6],
                                "short_name": row[7],
                            },
                            "away_team": {
                                "id": row[2],
                                "name": row[8],
                                "short_name": row[9],
                            },
                            "date": row[3].isoformat() if row[3] else None,
                            "status": row[4],
                            "venue": row[5],
                            "league": {"name": row[10]},
                            "source": "database",
                        }
                    )

                return {
                    "matches": matches,
                    "total": len(matches),
                    "limit": limit,
                    "source": "database",
                }

        except Exception as e:
            self.logger.warning(f"从数据库获取即将开始的比赛失败，使用模拟数据: {e}")
            return await self._get_mock_upcoming_matches(limit)

    async def _get_mock_upcoming_matches(self, limit: int = 20) -> dict[str, Any]:
        """获取模拟即将开始的比赛数据
        Get mock upcoming matches data.
        """
        await asyncio.sleep(0.001)

        from datetime import datetime, timedelta
        import random

        teams = [
            {"id": 1, "name": "Manchester United", "short_name": "MU"},
            {"id": 2, "name": "Liverpool", "short_name": "LIV"},
            {"id": 3, "name": "Chelsea", "short_name": "CHE"},
            {"id": 4, "name": "Arsenal", "short_name": "ARS"},
            {"id": 5, "name": "Barcelona", "short_name": "BAR"},
            {"id": 6, "name": "Real Madrid", "short_name": "RMA"},
        ]

        matches = []
        for i in range(min(limit, 10)):
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t["id"] != home_team["id"]])

            scheduled_at = datetime.utcnow() + timedelta(hours=i * 6)

            matches.append(
                {
                    "id": 10000 + i,
                    "home_team": home_team,
                    "away_team": away_team,
                    "date": scheduled_at.isoformat() + "Z",
                    "status": "SCHEDULED",
                    "venue": f"Stadium {i+1}",
                    "league": {"name": "Premier League"},
                    "source": "mock",
                }
            )

        return {
            "matches": matches,
            "total": len(matches),
            "limit": limit,
            "source": "mock",
        }


# 全局异步数据服务实例
_async_data_service: Optional[AsyncDataService] = None


def get_async_data_service() -> AsyncDataService:
    """获取异步数据服务实例."""
    global _async_data_service
    if _async_data_service is None:
        _async_data_service = AsyncDataService()
    return _async_data_service


# 向后兼容的便捷函数
async def get_matches_async(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """便捷的异步获取比赛列表函数."""
    service = get_async_data_service()
    return await service.get_matches_list(limit, offset)


async def get_match_async(match_id: int) -> Optional[dict[str, Any]]:
    """便捷的异步获取比赛信息函数."""
    service = get_async_data_service()
    return await service.get_match_by_id(match_id)


async def get_teams_async(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """便捷的异步获取球队列表函数."""
    service = get_async_data_service()
    return await service.get_teams_list(limit, offset)


async def get_team_async(team_id: int) -> Optional[dict[str, Any]]:
    """便捷的异步获取球队信息函数."""
    service = get_async_data_service()
    return await service.get_team_by_id(team_id)
