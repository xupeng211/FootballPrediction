from typing import Optional, Dict, Any
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine = None
        self._session_factory = None

    async def initialize(self):
        """初始化数据库连接"""
        self._engine = create_async_engine(self.database_url)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        if not self._session_factory:
            await self.initialize()
        return self._session_factory()

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
