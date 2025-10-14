from typing import Any, Dict, List, Optional, Union
"""
仓储基类
Repository Base Classes

定义仓储模式的基础接口和实现。
Defines base interfaces and implementations for repository pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_
from sqlalchemy.orm import selectinload

# 泛型类型
T = TypeVar("T")
ID = TypeVar("ID")


@dataclass
class QuerySpec:
    """查询规范"""

    filters: Optional[Dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    include: Optional[List[str]] = None
class BaseRepository(Generic[T, ID], ABC):
    """仓储基类

    提供基本的数据访问功能。
    Provides basic data access functionality.
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        self.session = session
        self.model_class = model_class

    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass

    @abstractmethod
    async def get_all(self, query_spec: Optional[QuerySpec] ] = None) -> List[T]:
        """获取所有实体"""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """保存实体"""
        pass

    @abstractmethod
    async def delete(self, entity: T) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    async def exists(self, id: ID) -> bool:
        """检查实体是否存在"""
        pass

    async def count(self, query_spec: Optional[QuerySpec] ] = None) -> int:
        """计算实体数量"""
        query = select(self.model_class)

        if query_spec and query_spec.filters:
            query = self._apply_filters(query, query_spec.filters)

        result = await self.session.execute(query)
        return len(result.fetchall())

    def _apply_filters(self, query, filters: Dict[str, Any]) -> None:
        """应用过滤器"""
        for key, value in filters.items():
            if isinstance(value, dict[str, Any]):
                # 支持嵌套条件
                for operator, val in value.items():
                    if operator == "$gt":
                        query = query.where(getattr(self.model_class, key) > val)
                    elif operator == "$lt":
                        query = query.where(getattr(self.model_class, key) < val)
                    elif operator == "$gte":
                        query = query.where(getattr(self.model_class, key) >= val)
                    elif operator == "$lte":
                        query = query.where(getattr(self.model_class, key) <= val)
                    elif operator == "$ne":
                        query = query.where(getattr(self.model_class, key) != val)
                    elif operator == "$in":
                        query = query.where(getattr(self.model_class, key).in_(val))
                    elif operator == "$nin":
                        query = query.where(getattr(self.model_class, key).notin_(val))
            else:
                query = query.where(getattr(self.model_class, key) == value)
        return query

    def _apply_order_by(self, query, order_by: List[str]) -> None:
        """应用排序"""
        for order in order_by:
            if order.startswith("-"):
                field = order[1:]
                query = query.order_by(getattr(self.model_class, field).desc())
            else:
                query = query.order_by(getattr(self.model_class, order))
        return query

    def _apply_pagination(self, query, limit: int, offset: int) -> None:
        """应用分页"""
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query

    def _apply_includes(self, query, includes: List[str]) -> None:
        """应用预加载"""
        for include in includes:
            if hasattr(self.model_class, include):
                query = query.options(selectinload(getattr(self.model_class, include)))
        return query


class ReadOnlyRepository(BaseRepository[T, ID], ABC):
    """只读仓储基类"""

    @abstractmethod
    async def find_one(self, query_spec: QuerySpec) -> Optional[T]:
        """查找单个实体"""
        pass

    @abstractmethod
    async def find_many(self, query_spec: QuerySpec) -> List[T]:
        """查找多个实体"""
        pass

    async def search(self, keyword: str, fields: List[str]) -> List[T]:
        """搜索实体"""
        conditions = []
        for field in fields:
            if hasattr(self.model_class, field):
                conditions.append(
                    getattr(self.model_class, field).ilike(f"%{keyword}%")
                )

        if conditions:
            query = select(self.model_class).where(or_(*conditions))
            result = await self.session.execute(query)
            return result.scalars().all()  # type: ignore  # type: ignore
        return []


class WriteOnlyRepository(BaseRepository[T, ID], ABC):
    """只写仓储基类"""

    @abstractmethod
    async def create(self, entity_data: Dict[str, Any]) -> T:
        """创建新实体"""
        pass

    @abstractmethod
    async def update_by_id(self, id: ID, update_data: Dict[str, Any]) -> Optional[T]:
        """根据ID更新实体"""
        pass

    @abstractmethod
    async def delete_by_id(self, id: ID) -> bool:
        """根据ID删除实体"""
        pass

    @abstractmethod
    async def bulk_create(self, entities_data: List[Dict[str, Any]) -> List[T]:
        """批量创建实体"""
        pass

    async def bulk_update(self, updates: List[Dict[str, Any]) -> List[T]:
        """批量更新实体"""
        updated_entities = []
        for update_data in updates:
            if "id" in update_data:
                entity = await self.update_by_id(update_data.pop("id"), update_data)
                if entity:
                    updated_entities.append(entity)
        return updated_entities

    async def bulk_delete(self, ids: List[ID]) -> int:
        """批量删除实体"""
        query = delete(self.model_class).where(self.model_class.id.in_(ids))  # type: ignore
        result = await self.session.execute(query)
        return result.rowcount  # type: ignore


class Repository(ReadOnlyRepository[T, ID], WriteOnlyRepository[T, ID], ABC):
    """完整仓储接口

    组合只读和只写接口。
    Combines read-only and write-only interfaces.
    """

    async def find_or_create(
        self, find_spec: QuerySpec, create_data: Dict[str, Any]
    ) -> tuple[T, bool]:
        """查找或创建实体"""
        entity = await self.find_one(find_spec)
        if entity:
            return entity, False

        new_entity = await self.create(create_data)
        return new_entity, True

    async def update_or_create(
        self,
        find_spec: QuerySpec,
        update_data: Dict[str, Any],
        create_data: Optional[Dict[str, Any] ] ] = None,
    ) -> tuple[T, bool]:
        """更新或创建实体"""
        entity = await self.find_one(find_spec)
        if entity:
            updated_entity = await self.update_by_id(entity.id, update_data)  # type: ignore
            return updated_entity, False  # type: ignore

        final_create_data = create_data or update_data
        new_entity = await self.create(final_create_data)
        return new_entity, True
