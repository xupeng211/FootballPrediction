from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User

"""
认证用户仓储

专门用于认证服务的简化用户数据访问
"""


class AuthUserRepository:
    """类文档字符串"""

    pass  # 添加pass语句
    """认证用户仓储"""

    def __init__(self, db: AsyncSession):
        """函数文档字符串"""
        # 添加pass语句
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户"""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """创建新用户"""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """更新用户"""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
