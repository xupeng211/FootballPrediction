"""
比赛仓储实现
Match Repository Implementation
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import Base

from .models.match import Match
from .repositories.base import AbstractRepository


class MatchRepository(AbstractRepository[Match]):
    """比赛数据仓储类"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Match)

    async def create(self, match_data: dict) -> Match:
        """创建比赛记录"""
        match = Match(**match_data)
        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

    async def get_by_id(self, match_id: int) -> Optional[Match]:
        """根据ID获取比赛"""
        return await self.session.get(Match, match_id)

    async def get_by_team(self, team_id: int) -> List[Match]:
        """根据队伍ID获取比赛列表"""
        # 这里应该实现具体的查询逻辑
        # 暂时返回空列表
        return []

    async def update(self, match_id: int, match_data: dict) -> Optional[Match]:
        """更新比赛信息"""
        match = await self.get_by_id(match_id)
        if match:
            for key, value in match_data.items():
                setattr(match, key, value)
            await self.session.commit()
            await self.session.refresh(match)
        return match

    async def delete(self, match_id: int) -> bool:
        """删除比赛记录"""
        match = await self.get_by_id(match_id)
        if match:
            await self.session.delete(match)
            await self.session.commit()
            return True
        return False

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Match]:
        """获取所有比赛列表"""
        result = await self.session.execute(select(Match).offset(offset).limit(limit))
        return result.scalars().all()

    async def get_by_competition(self, competition_id: str) -> List[Match]:
        """根据比赛ID获取比赛列表"""
        # 这里应该实现具体的查询逻辑
        # 暂时返回空列表
        return []
