"""
用户仓储模块 - 重写版本

实现用户相关的数据访问逻辑
User Repository - Rewritten Version
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, QuerySpec


class UserRepository(BaseRepository):
    """用户仓储实现 - 简化版本"""

    def __init__(self, session: AsyncSession):
        """初始化用户仓储"""
        # 假设有一个User模型类
        from ..database.models import User
        super().__init__(session, User)

    async def get_by_id(self, user_id: int) -> Optional["User"]:
        """根据ID获取用户"""
        query = select(self.model_class).where(self.model_class.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, query_spec: Optional[QuerySpec] = None) -> List["User"]:
        """获取所有用户"""
        query = select(self.model_class)

        if query_spec:
            query = self._build_query(query_spec)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, user_data: Dict[str, Any]) -> "User":
        """创建用户"""
        user = self.model_class(
            username=user_data["username"],
            email=user_data.get("email", ""),
            role=user_data.get("role", "user"),
            is_active=user_data.get("is_active", True),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user_id: int, update_data: Dict[str, Any]) -> Optional["User"]:
        """更新用户"""
        update_data["updated_at"] = datetime.utcnow()

        query = update(self.model_class).where(
            self.model_class.id == user_id
        ).values(**update_data)

        await self.session.execute(query)
        await self.session.commit()

        return await self.get_by_id(user_id)

    async def delete(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False

    async def find_by_username(self, username: str) -> Optional["User"]:
        """根据用户名查找用户"""
        query = select(self.model_class).where(
            self.model_class.username == username
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional["User"]:
        """根据邮箱查找用户"""
        query = select(self.model_class).where(
            self.model_class.email == email
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_active_users(self, limit: Optional[int] = None) -> List["User"]:
        """查找活跃用户"""
        filters = {"is_active": True}
        return await self.find_by_filters(filters, limit)

    async def count_active_users(self) -> int:
        """统计活跃用户数量"""
        filters = {"is_active": True}
        return await self.count(QuerySpec(filters=filters))

    async def bulk_create(self, users_data: List[Dict[str, Any]]) -> List["User"]:
        """批量创建用户"""
        users = []
        for user_data in users_data:
            user = self.model_class(
                username=user_data["username"],
                email=user_data.get("email", ""),
                role=user_data.get("role", "user"),
                is_active=user_data.get("is_active", True),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            users.append(user)

        self.session.add_all(users)
        await self.session.commit()

        # 刷新所有实体
        for user in users:
            await self.session.refresh(user)

        return users

    async def change_password(self, user_id: int, new_password: str) -> bool:
        """修改密码"""
        update_data = {
            "password_hash": new_password,  # 实际应该哈希处理
            "updated_at": datetime.utcnow()
        }

        result = await self.update(user_id, update_data)
        return result is not None

    async def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow()
        }

        result = await self.update(user_id, update_data)
        return result is not None

    async def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        update_data = {
            "is_active": True,
            "updated_at": datetime.utcnow()
        }

        result = await self.update(user_id, update_data)
        return result is not None

    async def update_last_login(self, user_id: int) -> bool:
        """更新最后登录时间"""
        update_data = {
            "last_login_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await self.update(user_id, update_data)
        return result is not None

    async def search_users(self, keyword: str, limit: int = 50) -> List["User"]:
        """搜索用户"""
        filters = {
            "$or": [
                {"username": {"$like": f"%{keyword}%"}},
                {"email": {"$like": f"%{keyword}%"}}
            ]
        }
        return await self.find_by_filters(filters, limit)

    async def get_users_by_role(self, role: str) -> List["User"]:
        """根据角色获取用户"""
        filters = {"role": role}
        return await self.find_by_filters(filters)