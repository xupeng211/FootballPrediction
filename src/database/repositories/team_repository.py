"""
队伍数据仓库
Team Repository
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class TeamRepository(ABC):
    """队伍数据仓库接口"""

    @abstractmethod
    async def get_by_id(self, team_id: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """根据ID获取队伍"""
        pass

    @abstractmethod
    async def get_by_name(self, name: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """根据名称获取队伍"""
        pass

    @abstractmethod
    async def get_all(self, db: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有队伍"""
        pass

    @abstractmethod
    async def create(self, team_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """创建队伍"""
        pass

    @abstractmethod
    async def update(
        self, team_id: int, team_data: Dict[str, Any], db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """更新队伍"""
        pass

    @abstractmethod
    async def delete(self, team_id: int, db: AsyncSession) -> bool:
        """删除队伍"""
        pass
