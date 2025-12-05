"""比赛数据仓库
Match Repository - 提供比赛数据的异步访问接口.

使用 SQLAlchemy 2.0 语法，支持关联数据预加载和性能优化.
"""

from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models.match import Match


class MatchRepository:
    """比赛数据仓库类.

    提供比赛数据的CRUD操作，使用异步SQLAlchemy 2.0语法.
    遵循Repository模式，封装数据访问逻辑.
    """

    def __init__(self, session: AsyncSession) -> None:
        """初始化仓库.

        Args:
            session: 异步数据库会话
        """
        self._session = session

    async def get_matches_with_teams(
        self, limit: int = 50, offset: int = 0
    ) -> list[Match]:
        """获取比赛列表并预加载关联数据.

        使用 joinedload 预加载关联的队伍和联赛信息，避免 N+1 查询问题.

        Args:
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            比赛对象列表，包含已加载的关联数据
        """
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
            )
            .order_by(Match.match_date.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def count_matches(self) -> int:
        """获取比赛总数.

        Returns:
            比赛总数
        """
        stmt = select(func.count(Match.id))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_by_id(self, match_id: int) -> Match | None:
        """根据ID获取比赛详情.

        Args:
            match_id: 比赛ID

        Returns:
            比赛对象或None
        """
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
            )
            .where(Match.id == match_id)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_matches_by_status(
        self, status: str, limit: int = 50, offset: int = 0
    ) -> list[Match]:
        """根据状态获取比赛列表.

        Args:
            status: 比赛状态
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            比赛对象列表
        """
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
            )
            .where(Match.status == status)
            .order_by(Match.match_date.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(stmt)
        return result.scalars().unique().all()