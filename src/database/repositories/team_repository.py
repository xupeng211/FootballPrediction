from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

"""
队伍数据仓库
Team Repository
"""


class TeamRepository(ABC):
    """队伍数据仓库接口"""

    @abstractmethod
    async def get_by_id(self, team_id: int, db: AsyncSession) -> dict[str, Any] | None:
        """根据ID获取队伍"""

    @abstractmethod
    async def get_by_name(self, name: str, db: AsyncSession) -> dict[str, Any] | None:
        """根据名称获取队伍"""

    @abstractmethod
    async def get_all(self, db: AsyncSession, limit: int = 100) -> list[dict[str, Any]]:
        """获取所有队伍"""

    @abstractmethod
    async def create(
        self, team_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        """创建队伍"""

    @abstractmethod
    async def update(
        self, team_id: int, team_data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any] | None:
        """更新队伍"""

    @abstractmethod
    async def delete(self, team_id: int, db: AsyncSession) -> bool:
        """删除队伍"""
