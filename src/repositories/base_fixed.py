"""仓储基类模块 - 重写版本.

定义仓储模式的基础接口和实现
Repository Base Classes - Rewritten Version
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

# 泛型类型
T = TypeVar("T")
ID = TypeVar("ID")


@dataclass
class QuerySpec:
    """查询规范 - 简化版本."""

    filters: dict[str, Any] | None = None
    order_by: list[str] | None = None
    limit: int | None = None
    offset: int | None = None
    include: list[str] | None = None


class BaseRepository(Generic[T, ID], ABC):
    """仓储基类 - 简化版本.

    提供基本的数据访问功能
    Provides basic data access functionality
    """

    def __init__(self, session: AsyncSession, model_class: typing.Type[T]):
        """初始化仓储实例."""
        self.session = session
        self.model_class = model_class

    @abstractmethod
    async def get_by_id(self, entity_entity_id: ID) -> T | None:
        """根据ID获取实体."""
        pass

    @abstractmethod
    async def get_all(self, query_spec: QuerySpec | None = None) -> list[T]:
        """获取所有实体."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体."""
        pass

    @abstractmethod
    async def update(
        self, entity_entity_id: ID, update_data: dict[str, Any]
    ) -> T | None:
        """更新实体."""
        pass

    @abstractmethod
    async def delete(self, entity_entity_id: ID) -> bool:
        """删除实体."""
        pass

    async def exists(self, entity_entity_id: ID) -> bool:
        """检查实体是否存在."""
        query = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def count(self, query_spec: QuerySpec | None = None) -> int:
        """计算实体数量."""
        query = select(self.model_class)

        if query_spec and query_spec.filters:
            for key, value in query_spec.filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
                elif isinstance(value, dict):
                    # 支持嵌套条件
                    for operator, val in value.items():
                        if operator == "$gt":
                            query = query.where(getattr(self.model_class, key) > val)
                        elif operator == "$lt":
                            query = query.where(getattr(self.model_class, key) < val)
                        elif operator == "$ne":
                            query = query.where(getattr(self.model_class, key) != val)
                        elif operator == "$like":
                            query = query.where(
                                getattr(self.model_class, key).like(val)
                            )

        result = await self.session.execute(query)
        return len(result.scalars().all())

    def _build_query(self, query_spec: QuerySpec | None) -> Select:
        """构建查询."""
        query = select(self.model_class)

        if query_spec:
            # 添加过滤条件
            if query_spec.filters:
                for key, value in query_spec.filters.items():
                    if hasattr(self.model_class, key):
                        query = query.where(getattr(self.model_class, key) == value)

            # 添加排序
            if query_spec.order_by:
                for order_field in query_spec.order_by:
                    if order_field.startswith("-"):
                        field = order_field[1:]
                        query = query.order_by(getattr(self.model_class, field).desc())
                    else:
                        query = query.order_by(
                            getattr(self.model_class, order_field).asc()
                        )

            # 添加分页
            if query_spec.limit:
                query = query.limit(query_spec.limit)
            if query_spec.offset:
                query = query.offset(query_spec.offset)

            # 添加预加载
            if query_spec.include:
                for include_field in query_spec.include:
                    if hasattr(self.model_class, include_field):
                        query = query.options(
                            selectinload(getattr(self.model_class, include_field))
                        )

        return query

    def _apply_filters(self, query: Select, filters: dict[str, Any]) -> Select:
        """应用过滤条件."""
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                if isinstance(value, list | tuple):
                    # 支持IN操作
                    query = query.where(getattr(self.model_class, key).in_(value))
                elif isinstance(value, dict):
                    # 支持复杂条件
                    for operator, val in value.items():
                        if operator == "$gt":
                            query = query.where(getattr(self.model_class, key) > val)
                        elif operator == "$lt":
                            query = query.where(getattr(self.model_class, key) < val)
                        elif operator == "$ne":
                            query = query.where(getattr(self.model_class, key) != val)
                        elif operator == "$like":
                            query = query.where(
                                getattr(self.model_class, key).like(val)
                            )
                        elif operator == "$in":
                            query = query.where(getattr(self.model_class, key).in_(val))
                        elif operator == "$nin":
                            query = query.where(
                                getattr(self.model_class, key).notin_(val)
                            )
                else:
                    query = query.where(getattr(self.model_class, key) == value)
        return query

    async def find_by_filters(
        self, filters: dict[str, Any], limit: int | None = None
    ) -> list[T]:
        """根据过滤条件查找实体."""
        query = select(self.model_class)
        query = self._apply_filters(query, filters)

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def find_one_by_filters(self, filters: dict[str, Any]) -> T | None:
        """根据过滤条件查找单个实体."""
        query = select(self.model_class)
        query = self._apply_filters(query, filters)
        query = query.limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
