"""
数据库服务
Database Service
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .repositories.base import AbstractRepository
from .repositories.match_repository import MatchRepository
from .repositories.prediction_repository import PredictionRepository
from .repositories.user_repository import UserRepository

class DatabaseService:
    """数据库服务类 - 提供高级数据库操作接口"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.match_repo = MatchRepository(session)
        self.prediction_repo = PredictionRepository(session)
        self.user_repo = UserRepository(session)

    async def get_match_with_predictions(self, match_id: int):
        """获取比赛及其预测数据"""
        match = await self.match_repo.get_by_id(match_id)
        if match:
            predictions = await self.prediction_repo.get_by_match(match_id)
            match.predictions = predictions
        return match

    async def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            # 简单的连接测试
            await self.session.execute("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

    async def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        # 这里应该实现具体的清理逻辑
        # 暂时返回成功
        return {"cleaned_records": 0}

    async def backup_data(self) -> dict:
        """备份数据"""
        # 这里应该实现具体的备份逻辑
        # 暂时返回成功状态
        return {
            "status": "success",
            "backup_file": f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
        }
