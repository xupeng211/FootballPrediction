"""
ID映射器模块

负责处理球队和联赛的ID映射功能。
"""

import hashlib
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ....database.connection import DatabaseManager
from ....database.models.league import League
from ....database.models.team import Team


class IDMapper:
    """ID映射器"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化ID映射器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

        # 球队ID映射缓存
        self._team_id_cache: Dict[str, int] = {}
        # 联赛ID映射缓存
        self._league_id_cache: Dict[str, int] = {}

    async def map_team_id(
        self, team_data: Dict[str, Any], *, league_id: Optional[int] = None
    ) -> Optional[int]:
        """
        球队ID映射到标准ID

        Args:
            team_data: 球队数据
            league_id: 联赛ID（可选）

        Returns:
            Optional[int]: 标准球队ID，未找到则返回None
        """
        if not team_data:
            return None

        external_id = team_data.get("id")
        team_name = team_data.get("name") or team_data.get("shortName") or ""
        team_code = team_data.get("tla")

        cache_key = f"{external_id}:{team_name}:{team_code}:{league_id}"
        if cache_key in self._team_id_cache:
            return self._team_id_cache[cache_key]

        api_team_id: Optional[int] = None
        if external_id not in (None, ""):
            try:
                api_team_id = int(external_id)
            except (TypeError, ValueError):
                api_team_id = None

        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(Team.id)
                if api_team_id is not None:
                    stmt = stmt.where(Team.api_team_id == api_team_id)
                elif team_code:
                    stmt = stmt.where(Team.team_code == team_code)
                else:
                    stmt = stmt.where(Team.team_name == team_name)

                result = await session.execute(stmt)
                team_id = result.scalar_one_or_none()

                if team_id is None:
                    team_record = Team(
                        team_name=team_name or team_code or f"Team-{external_id}",
                        team_code=team_code,
                        api_team_id=api_team_id,
                        league_id=league_id,
                    )
                    session.add(team_record)
                    try:
                        await session.flush()
                    except IntegrityError:
                        await session.rollback()
                        lookup_stmt = select(Team.id)
                        if api_team_id is not None:
                            lookup_stmt = lookup_stmt.where(
                                Team.api_team_id == api_team_id
                            )
                        elif team_code:
                            lookup_stmt = lookup_stmt.where(Team.team_code == team_code)
                        else:
                            lookup_stmt = lookup_stmt.where(Team.team_name == team_name)
                        result = await session.execute(lookup_stmt)
                        team_id = result.scalar_one_or_none()
                    else:
                        team_id = team_record.id

                if team_id is not None:
                    self._team_id_cache[cache_key] = team_id
                    return team_id

        except (RuntimeError, SQLAlchemyError) as e:
            self.logger.warning(
                "Team ID lookup failed for %s (%s), falling back to deterministic mapping: %s",
                team_name,
                external_id,
                e,
            )

        deterministic_id = self._deterministic_id(cache_key, modulus=100000)
        self._team_id_cache[cache_key] = deterministic_id
        return deterministic_id

    async def map_league_id(self, league_data: Dict[str, Any]) -> Optional[int]:
        """
        联赛ID映射到标准ID

        Args:
            league_data: 联赛数据

        Returns:
            Optional[int]: 标准联赛ID，未找到则返回None
        """
        if not league_data:
            return None

        external_id = league_data.get("id")
        league_name = league_data.get("name") or ""
        league_code = league_data.get("code") or league_data.get("codeName")
        country = None
        area = league_data.get("area")
        if isinstance(area, dict):
            country = area.get("name")

        cache_key = f"{external_id}:{league_name}:{league_code}"
        if cache_key in self._league_id_cache:
            return self._league_id_cache[cache_key]

        api_league_id: Optional[int] = None
        if external_id not in (None, ""):
            try:
                api_league_id = int(external_id)
            except (TypeError, ValueError):
                api_league_id = None

        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(League.id)
                if api_league_id is not None:
                    stmt = stmt.where(League.api_league_id == api_league_id)
                elif league_code:
                    stmt = stmt.where(League.league_code == league_code)
                else:
                    stmt = stmt.where(League.league_name == league_name)

                result = await session.execute(stmt)
                league_id = result.scalar_one_or_none()

                if league_id is None:
                    league_record = League(
                        league_name=league_name
                        or league_code
                        or f"League-{external_id}",
                        league_code=league_code,
                        api_league_id=api_league_id,
                        country=country,
                    )
                    session.add(league_record)
                    try:
                        await session.flush()
                    except IntegrityError:
                        await session.rollback()
                        lookup_stmt = select(League.id)
                        if api_league_id is not None:
                            lookup_stmt = lookup_stmt.where(
                                League.api_league_id == api_league_id
                            )
                        elif league_code:
                            lookup_stmt = lookup_stmt.where(
                                League.league_code == league_code
                            )
                        else:
                            lookup_stmt = lookup_stmt.where(
                                League.league_name == league_name
                            )
                        result = await session.execute(lookup_stmt)
                        league_id = result.scalar_one_or_none()
                    else:
                        league_id = league_record.id

                if league_id is not None:
                    self._league_id_cache[cache_key] = league_id
                    return league_id

        except (RuntimeError, SQLAlchemyError) as e:
            self.logger.warning(
                "League ID lookup failed for %s (%s), falling back to deterministic mapping: %s",
                league_name,
                external_id,
                e,
            )

        deterministic_id = self._deterministic_id(cache_key, modulus=1000)
        self._league_id_cache[cache_key] = deterministic_id
        return deterministic_id

    def _deterministic_id(self, value: str, *, modulus: int) -> int:
        """
        基于稳定哈希生成确定性ID

        Args:
            value: 用于生成ID的值
            modulus: 模数

        Returns:
            int: 确定性ID
        """
        digest = hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()
        return int(digest[:12], 16) % modulus
