"""
用户仓储
User Repository

提供用户数据的访问操作,实现Repository模式.
Provides user data access operations, implementing the Repository pattern.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    用户仓储类
    User Repository Class

    提供用户数据的CRUD操作和复杂查询方法.
    Provides CRUD operations and complex query methods for user data.
    """

    def __init__(self, db_manager=None):
        """函数文档字符串"""
        # 添加pass语句
        super().__init__(User, db_manager)

    # ========================================
    # 用户特定的查询方法
    # ========================================

    async def get_by_username(
        self, username: str, session: AsyncSession | None = None
    ) -> User | None:
        """
        根据用户名获取用户

        Args:
            username: 用户名
            session: 数据库会话

        Returns:
            用户对象或None
        """
        return await self.find_one_by(filters={"username": username}, session=session)

    async def get_by_email(
        self, email: str, session: AsyncSession | None = None
    ) -> User | None:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱地址
            session: 数据库会话

        Returns:
            用户对象或None
        """
        return await self.find_one_by(filters={"email": email}, session=session)

    async def username_exists(
        self,
        username: str,
        exclude_id: int | str | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        检查用户名是否存在

        Args:
            username: 用户名
            exclude_id: 排除的用户ID（用于更新时检查）
            session: 数据库会话

        Returns:
            是否存在
        """
        filters = {"username": username}
        if exclude_id:
            filters["id"] = {"ne": exclude_id}

        return await self.exists(filters=filters, session=session)

    async def email_exists(
        self,
        email: str,
        exclude_id: int | str | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        检查邮箱是否存在

        Args:
            email: 邮箱地址
            exclude_id: 排除的用户ID（用于更新时检查）
            session: 数据库会话

        Returns:
            是否存在
        """
        filters = {"email": email}
        if exclude_id:
            filters["id"] = {"ne": exclude_id}

        return await self.exists(filters=filters, session=session)

    async def get_active_users(
        self, limit: int | None = None, session: AsyncSession | None = None
    ) -> list[User]:
        """
        获取活跃用户

        Args:
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            活跃用户列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 定义活跃用户:最近30天内有登录
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            stmt = (
                select(User)
                .where(
                    and_(User.is_active is True, User.last_login_at >= thirty_days_ago)
                )
                .order_by(desc(User.last_login_at))
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def get_inactive_users(
        self,
        days: int = 90,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[User]:
        """
        获取非活跃用户

        Args:
            days: 多少天未登录
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            非活跃用户列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            stmt = (
                select(User)
                .where(
                    or_(User.last_login_at < cutoff_date, User.last_login_at.is_(None))
                )
                .order_by(asc(User.last_login_at))
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def search_users(
        self,
        query: str,
        search_fields: list[str] | None = None,
        limit: int | None = None,
        session: AsyncSession | None = None,
    ) -> list[User]:
        """
        搜索用户

        Args:
            query: 搜索关键词
            search_fields: 搜索字段列表（默认搜索用户名,邮箱,显示名）
            limit: 限制返回数量
            session: 数据库会话

        Returns:
            匹配的用户列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            if not search_fields:
                search_fields = ["username", "email", "display_name"]

            # 构建搜索条件
            search_conditions = []
            for field in search_fields:
                if hasattr(User, field):
                    search_conditions.append(getattr(User, field).ilike(f"%{query}%"))

            stmt = select(User).where(or_(*search_conditions))

            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return result.scalars().all()

    async def update_last_login(
        self, user_id: int | str, session: AsyncSession | None = None
    ) -> User | None:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID
            session: 数据库会话

        Returns:
            更新后的用户对象
        """
        return await self.update(
            obj_id=user_id,
            obj_data={"last_login_at": datetime.utcnow()},
            session=session,
        )

    async def change_password(
        self,
        user_id: int | str,
        hashed_password: str,
        session: AsyncSession | None = None,
    ) -> User | None:
        """
        修改用户密码

        Args:
            user_id: 用户ID
            hashed_password: 加密后的密码
            session: 数据库会话

        Returns:
            更新后的用户对象
        """
        return await self.update(
            obj_id=user_id,
            obj_data={
                "password_hash": hashed_password,
                "password_changed_at": datetime.utcnow(),
            },
            session=session,
        )

    async def activate_user(
        self, user_id: int | str, session: AsyncSession | None = None
    ) -> User | None:
        """
        激活用户

        Args:
            user_id: 用户ID
            session: 数据库会话

        Returns:
            更新后的用户对象
        """
        return await self.update(
            obj_id=user_id,
            obj_data={"is_active": True, "activated_at": datetime.utcnow()},
            session=session,
        )

    async def deactivate_user(
        self,
        user_id: int | str,
        reason: str | None = None,
        session: AsyncSession | None = None,
    ) -> User | None:
        """
        停用用户

        Args:
            user_id: 用户ID
            reason: 停用原因
            session: 数据库会话

        Returns:
            更新后的用户对象
        """
        update_data = {"is_active": False, "deactivated_at": datetime.utcnow()}

        if reason:
            update_data["deactivation_reason"] = reason

        return await self.update(obj_id=user_id, obj_data=update_data, session=session)

    # ========================================
    # 统计方法
    # ========================================

    async def get_user_stats(
        self, days: int | None = None, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        获取用户统计信息

        Args:
            days: 统计天数（可选）
            session: 数据库会话

        Returns:
            统计数据字典
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 基础查询
            base_query = select(User)

            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                base_query = base_query.where(User.created_at >= start_date)

            # 总用户数
            total_stmt = select(func.count(User.id))
            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                total_stmt = total_stmt.where(User.created_at >= start_date)

            total_result = await sess.execute(total_stmt)
            total_users = total_result.scalar()

            # 活跃用户数（最近30天登录）
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_stmt = select(func.count(User.id)).where(
                and_(User.is_active is True, User.last_login_at >= thirty_days_ago)
            )
            if days:
                active_stmt = active_stmt.where(User.created_at >= start_date)

            active_result = await sess.execute(active_stmt)
            active_users = active_result.scalar()

            # 新注册用户数（今天）
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            new_stmt = select(func.count(User.id)).where(User.created_at >= today_start)
            new_result = await sess.execute(new_stmt)
            new_users_today = new_result.scalar()

            # 计算比率
            activity_rate = 0.0
            if total_users > 0:
                activity_rate = active_users / total_users

            return {
                "total_users": total_users,
                "active_users": active_users,
                "new_users_today": new_users_today,
                "activity_rate": activity_rate,
                "inactive_users": total_users - active_users,
            }

    async def get_user_growth_stats(
        self, days: int = 30, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """
        获取用户增长统计

        Args:
            days: 统计天数
            session: 数据库会话

        Returns:
            每日增长数据列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 计算日期范围
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)

            # 查询每天的用户注册数
            stmt = (
                select(
                    func.date(User.created_at).label("date"),
                    func.count(User.id).label("new_users"),
                )
                .where(
                    and_(
                        func.date(User.created_at) >= start_date,
                        func.date(User.created_at) <= end_date,
                    )
                )
                .group_by(func.date(User.created_at))
                .order_by(func.date(User.created_at))
            )

            result = await sess.execute(stmt)
            rows = result.all()

            # 转换为字典列表
            growth_stats = []
            for row in rows:
                growth_stats.append(
                    {"date": row.date.isoformat(), "new_users": row.new_users}
                )

            return growth_stats

    # ========================================
    # 实现抽象方法
    # ========================================

    async def get_related_data(
        self,
        obj_id: int | str,
        relation_name: str,
        session: AsyncSession | None = None,
    ) -> Any:
        """
        获取用户的关联数据

        Args:
            obj_id: 用户ID
            relation_name: 关联名称（如 'predictions', 'profile'）
            session: 数据库会话

        Returns:
            关联数据
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            # 根据关联名称加载不同的关联数据
            if relation_name == "predictions":
                stmt = (
                    select(User)
                    .options(selectinload(User.predictions))
                    .where(User.id == obj_id)
                )
            elif relation_name == "profile":
                stmt = (
                    select(User)
                    .options(selectinload(User.profile))
                    .where(User.id == obj_id)
                )
            elif relation_name == "roles":
                stmt = (
                    select(User)
                    .options(selectinload(User.roles))
                    .where(User.id == obj_id)
                )
            else:
                return None

            result = await sess.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                return getattr(user, relation_name, None)
            return None
