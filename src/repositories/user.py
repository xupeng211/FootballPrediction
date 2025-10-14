"""
用户仓储
User Repository

实现用户相关的数据访问逻辑。
Implements data access logic for users.
"""

from typing import Any, Dict[str, Any], List[Any], Optional
from datetime import datetime, date

from sqlalchemy import select, func, update

from .base import Repository, ReadOnlyRepository, QuerySpec
from ..database.models import User


class UserRepositoryInterface(Repository[User, int]):
    """用户仓储接口"""

    pass


class ReadOnlyUserRepository(ReadOnlyRepository[User, int]):
    """只读用户仓储"""

    async def find_one(self, query_spec: QuerySpec) -> Optional[User]:
        """查找单个用户"""
        query = select(User)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def find_many(self, query_spec: QuerySpec) -> List[User]:
        """查找多个用户"""
        query = select(User)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.order_by:
                query = self._apply_order_by(query, query_spec.order_by)
            if query_spec.limit or query_spec.offset:
                query = self._apply_pagination(
                    query, query_spec.limit or 100, query_spec.offset or 0
                )
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().all()  # type: ignore  # type: ignore

    async def get_by_id(self, id: int) -> Optional[User]:
        """根据ID获取用户"""
        query = select(User).where(User.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def get_all(self, query_spec: Optional[QuerySpec] ] = None) -> List[User]:
        """获取所有用户"""
        return await self.find_many(query_spec or QuerySpec())

    async def save(self, entity: User) -> User:
        """保存用户"""
        raise NotImplementedError("This is a read-only repository")

    async def delete(self, entity: User) -> bool:
        """删除用户"""
        raise NotImplementedError("This is a read-only repository")

    async def exists(self, id: int) -> bool:
        """检查用户是否存在"""
        query = select(func.count(User.id)).where(User.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0  # type: ignore

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def search_users(self, keyword: str) -> List[User]:
        """搜索用户"""
        filters = {
            "$or": [
                {"username": {"$ilike": f"%{keyword}%"}},
                {"email": {"$ilike": f"%{keyword}%"}},
                {"display_name": {"$ilike": f"%{keyword}%"}},
            ]
        }
        query_spec = QuerySpec(filters=filters, order_by=["username"])
        return await self.find_many(query_spec)

    async def get_active_users(self, limit: int = 100) -> List[User]:
        """获取活跃用户"""
        filters = {"is_active": True}
        query_spec = QuerySpec(
            filters=filters, order_by=["-last_login_at"], limit=limit
        )
        return await self.find_many(query_spec)

    async def get_users_created_in_range(
        self, start_date: date, end_date: date, limit: int = 100
    ) -> List[User]:
        """获取指定时间范围内创建的用户"""
        filters = {"created_at": {"$gte": start_date, "$lte": end_date}}
        query_spec = QuerySpec(filters=filters, order_by=["-created_at"], limit=limit)
        return await self.find_many(query_spec)


class UserRepository(UserRepositoryInterface):
    """用户仓储实现"""

    async def get_by_id(self, id: int) -> Optional[User]:
        """根据ID获取用户"""
        query = select(User).where(User.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def get_all(self, query_spec: Optional[QuerySpec] ] = None) -> List[User]:
        """获取所有用户"""
        query = select(User)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.order_by:
                query = self._apply_order_by(query, query_spec.order_by)
            if query_spec.limit or query_spec.offset:
                query = self._apply_pagination(
                    query, query_spec.limit or 100, query_spec.offset or 0
                )
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().all()  # type: ignore  # type: ignore

    async def find_one(self, query_spec: QuerySpec) -> Optional[User]:
        """查找单个用户"""
        query = select(User)

        if query_spec:
            if query_spec.filters:
                query = self._apply_filters(query, query_spec.filters)
            if query_spec.include:
                query = self._apply_includes(query, query_spec.include)

        result = await self.session.execute(query)
        return result.scalars().first()  # type: ignore

    async def find_many(self, query_spec: QuerySpec) -> List[User]:
        """查找多个用户"""
        return await self.get_all(query_spec)

    async def save(self, entity: User) -> User:
        """保存用户"""
        if entity.id is None:
            self.session.add(entity)  # type: ignore
        else:
            entity.updated_at = datetime.utcnow()  # type: ignore

        await self.session.commit()
        await self.session.refresh(entity)  # type: ignore
        return entity

    async def delete(self, entity: User) -> bool:
        """删除用户"""
        try:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            await self.session.rollback()
            return False

    async def exists(self, id: int) -> bool:
        """检查用户是否存在"""
        query = select(func.count(User.id)).where(User.id == id)
        result = await self.session.execute(query)
        return result.scalar() > 0  # type: ignore

    async def create(self, entity_data: Dict[str, Any]) -> User:
        """创建新用户"""
        user = User(
            username=entity_data["username"],
            email=entity_data["email"],
            password_hash=entity_data["password_hash"],
            display_name=entity_data.get("display_name"),
            role=entity_data.get("role", "user"),
            is_active=entity_data.get("is_active", True),
            created_at=datetime.utcnow(),
        )

        self.session.add(user)  # type: ignore
        await self.session.commit()
        await self.session.refresh(user)  # type: ignore
        return user

    async def update_by_id(
        self, id: int, update_data: Dict[str, Any]
    ) -> Optional[User]:
        """根据ID更新用户"""
        query = update(User).where(User.id == id)

        # 更新时间戳
        update_data["updated_at"] = datetime.utcnow()

        # 处理特殊字段
        if "last_login_at" in update_data and isinstance(
            update_data["last_login_at"], str
        ):
            update_data["last_login_at"] = datetime.fromisoformat(
                update_data["last_login_at"]
            )

        # 构建更新语句
        for key, value in update_data.items():
            query = query.values({getattr(User, key): value})

        result = await self.session.execute(query)
        await self.session.commit()

        if result.rowcount > 0:  # type: ignore
            return await self.get_by_id(id)
        return None

    async def delete_by_id(self, id: int) -> bool:
        """根据ID删除用户"""
        query = update(User).where(User.id == id).values(is_active=False)
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0  # type: ignore

    async def bulk_create(self, entities_data: List[Dict[str, Any]) -> List[User]:
        """批量创建用户"""
        users = []
        for data in entities_data:
            user = User(
                username=data["username"],
                email=data["email"],
                password_hash=data["password_hash"],
                display_name=data.get("display_name"),
                role=data.get("role", "user"),
                is_active=data.get("is_active", True),
                created_at=datetime.utcnow(),
            )
            users.append(user)

        self.session.add_all(users)
        await self.session.commit()

        # 刷新所有实体
        for user in users:
            await self.session.refresh(user)  # type: ignore

        return users

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""
        from ..database.models import Prediction

        # 获取预测统计
        prediction_query = select(
            func.count(Prediction.id).label("total_predictions"),
            func.sum(Prediction.points_earned).label("total_points"),
            func.avg(Prediction.confidence).label("avg_confidence"),
            func.max(Prediction.created_at).label("last_prediction_at"),
        ).where(Prediction.user_id == user_id)

        prediction_result = await self.session.execute(prediction_query)
        prediction_stats = prediction_result.first()  # type: ignore

        # 获取用户信息
        _user = await self.get_by_id(user_id)
        if not _user:
            return {}

        # 计算活跃天数
        if _user.created_at:
            active_days = (datetime.utcnow().date() - _user.created_at.date()).days + 1
        else:
            active_days = 0

        return {
            "user_id": user_id,
            "username": user.username,
            "total_predictions": prediction_stats.total_predictions or 0,
            "total_points": float(prediction_stats.total_points or 0),
            "average_confidence": float(prediction_stats.avg_confidence or 0),
            "last_prediction_at": prediction_stats.last_prediction_at,
            "member_since": user.created_at,
            "active_days": active_days,
            "predictions_per_day": (
                (prediction_stats.total_predictions or 0) / active_days
                if active_days > 0
                else 0
            ),
        }

    async def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0  # type: ignore

    async def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0  # type: ignore

    async def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=True, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0  # type: ignore

    def get_read_only_repository(self) -> ReadOnlyUserRepository:
        """获取只读仓储"""
        return ReadOnlyUserRepository(self.session, self.model_class)
