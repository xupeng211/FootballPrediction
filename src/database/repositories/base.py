"""
基础仓储类

定义Repository模式的基础接口和实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Generic
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger

# 泛型类型变量
T = TypeVar("T")


class RepositoryConfig:
    """仓储配置类"""

    def __init__(
        self,
        default_page_size: int = 20,
        max_page_size: int = 100,
        enable_cache: bool = True,
        cache_ttl: int = 300,
        enable_query_logging: bool = False,
    ):
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.enable_query_logging = enable_query_logging


class QueryResult(Generic[T]):
    """查询结果包装类"""

    def __init__(
        self,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
        has_next: bool,
        has_prev: bool,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.has_next = has_next
        self.has_prev = has_prev

    @property
    def total_pages(self) -> int:
        """总页数"""
        return (self.total + self.page_size - 1) // self.page_size


class BaseRepository(ABC, Generic[T]):
    """基础仓储抽象类

    提供通用的CRUD操作和查询功能。
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[T],
        config: Optional[RepositoryConfig] = None,
    ):
        """初始化仓储

        Args:
            session: 数据库会话
            model_class: 模型类
            config: 仓储配置
        """
        self.session = session
        self.model_class = model_class
        self.config = config or RepositoryConfig()
        self.logger = get_logger(f"repository.{model_class.__name__}")

    # ==================== CRUD操作 ====================

    async def create(self, entity: T) -> T:
        """创建实体

        Args:
            entity: 要创建的实体

        Returns:
            创建后的实体（包含ID等生成字段）
        """
        self.logger.debug(f"Creating {self.model_class.__name__}")

        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)

        self.logger.debug(
            f"Created {self.model_class.__name__} with ID: {getattr(entity, 'id', 'N/A')}"
        )
        return entity

    async def create_batch(self, entities: List[T]) -> List[T]:
        """批量创建实体

        Args:
            entities: 要创建的实体列表

        Returns:
            创建后的实体列表
        """
        if not entities:
            return []

        self.logger.debug(
            f"Creating batch of {len(entities)} {self.model_class.__name__}"
        )

        self.session.add_all(entities)
        await self.session.commit()

        # 刷新所有实体以获取生成的ID
        for entity in entities:
            await self.session.refresh(entity)

        self.logger.debug(
            f"Created batch of {len(entities)} {self.model_class.__name__}"
        )
        return entities

    async def get_by_id(self, entity_id: Union[int, str]) -> Optional[T]:
        """根据ID获取实体

        Args:
            entity_id: 实体ID

        Returns:
            实体或None
        """
        self.logger.debug(f"Getting {self.model_class.__name__} by ID: {entity_id}")

        stmt = select(self.model_class).where(
            getattr(self.model_class, "id") == entity_id
        )

        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            self.logger.debug(f"Found {self.model_class.__name__} with ID: {entity_id}")
        else:
            self.logger.debug(
                f"{self.model_class.__name__} not found with ID: {entity_id}"
            )

        return entity

    async def update(self, entity: T) -> T:
        """更新实体

        Args:
            entity: 包含更新数据的实体

        Returns:
            更新后的实体
        """
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an ID to update")

        self.logger.debug(f"Updating {self.model_class.__name__} with ID: {entity_id}")

        # 将实体附加到会话并标记为脏
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)

        self.logger.debug(f"Updated {self.model_class.__name__} with ID: {entity_id}")
        return entity

    async def delete(self, entity: T) -> bool:
        """删除实体

        Args:
            entity: 要删除的实体

        Returns:
            是否删除成功
        """
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an ID to delete")

        self.logger.debug(f"Deleting {self.model_class.__name__} with ID: {entity_id}")

        await self.session.delete(entity)
        await self.session.commit()

        self.logger.debug(f"Deleted {self.model_class.__name__} with ID: {entity_id}")
        return True

    async def delete_by_id(self, entity_id: Union[int, str]) -> bool:
        """根据ID删除实体

        Args:
            entity_id: 实体ID

        Returns:
            是否删除成功
        """
        entity = await self.get_by_id(entity_id)
        if entity:
            return await self.delete(entity)
        return False

    async def exists(self, entity_id: Union[int, str]) -> bool:
        """检查实体是否存在

        Args:
            entity_id: 实体ID

        Returns:
            是否存在
        """
        stmt = (
            select(self.model_class)
            .where(getattr(self.model_class, "id") == entity_id)
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ==================== 查询操作 ====================

    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[T]:
        """获取所有实体

        Args:
            limit: 限制数量
            offset: 偏移量
            order_by: 排序字段

        Returns:
            实体列表
        """
        stmt = select(self.model_class)

        # 添加排序
        if order_by:
            stmt = stmt.order_by(getattr(self.model_class, order_by))

        # 添加分页
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(min(limit, self.config.max_page_size))

        result = await self.session.execute(stmt)
        entities = result.scalars().all()

        self.logger.debug(
            f"Retrieved {len(entities)} {self.model_class.__name__} entities"
        )
        return list(entities)

    async def find(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[T]:
        """根据条件查找实体

        Args:
            filters: 过滤条件字典
            limit: 限制数量
            offset: 偏移量
            order_by: 排序字段

        Returns:
            匹配的实体列表
        """
        stmt = select(self.model_class)

        # 添加过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)

        # 添加排序
        if order_by:
            stmt = stmt.order_by(getattr(self.model_class, order_by))

        # 添加分页
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(min(limit, self.config.max_page_size))

        result = await self.session.execute(stmt)
        entities = result.scalars().all()

        self.logger.debug(
            f"Found {len(entities)} {self.model_class.__name__} entities with filters: {filters}"
        )
        return list(entities)

    async def find_one(self, filters: Dict[str, Any]) -> Optional[T]:
        """根据条件查找单个实体

        Args:
            filters: 过滤条件字典

        Returns:
            匹配的实体或None
        """
        entities = await self.find(filters, limit=1)
        return entities[0] if entities else None

    async def paginate(
        self,
        page: int = 1,
        page_size: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
    ) -> QueryResult[T]:
        """分页查询

        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            filters: 过滤条件
            order_by: 排序字段

        Returns:
            分页结果
        """
        # 设置默认页大小
        if page_size is None:
            page_size = self.config.default_page_size
        page_size = min(page_size, self.config.max_page_size)

        # 计算偏移量
        offset = (page - 1) * page_size

        # 构建查询
        stmt = select(self.model_class)

        # 添加过滤条件
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

        # 获取总数
        count_stmt = select(self.model_class)
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    count_stmt = count_stmt.where(
                        getattr(self.model_class, key) == value
                    )

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # 添加排序
        if order_by:
            stmt = stmt.order_by(getattr(self.model_class, order_by))

        # 添加分页
        stmt = stmt.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        # 计算分页信息
        has_next = (offset + len(items)) < total
        has_prev = page > 1

        self.logger.debug(
            f"Retrieved page {page} of {self.model_class.__name__}: "
            f"{len(items)} items, total: {total}"
        )

        return QueryResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev,
        )

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计实体数量

        Args:
            filters: 过滤条件

        Returns:
            实体数量
        """
        stmt = select(self.model_class)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ==================== 批量操作 ====================

    async def update_batch(
        self, filters: Dict[str, Any], updates: Dict[str, Any]
    ) -> int:
        """批量更新

        Args:
            filters: 过滤条件
            updates: 更新字段

        Returns:
            更新的记录数
        """
        stmt = update(self.model_class)

        # 添加过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)

        # 设置更新字段
        stmt = stmt.values(**updates)

        result = await self.session.execute(stmt)
        await self.session.commit()

        updated_count = result.rowcount
        self.logger.debug(
            f"Updated {updated_count} {self.model_class.__name__} records"
        )
        return updated_count

    async def delete_batch(self, filters: Dict[str, Any]) -> int:
        """批量删除

        Args:
            filters: 过滤条件

        Returns:
            删除的记录数
        """
        stmt = delete(self.model_class)

        # 添加过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)

        result = await self.session.execute(stmt)
        await self.session.commit()

        deleted_count = result.rowcount
        self.logger.debug(
            f"Deleted {deleted_count} {self.model_class.__name__} records"
        )
        return deleted_count

    # ==================== 辅助方法 ====================

    def _log_query(self, query: str, params: Dict[str, Any] = None):
        """记录查询日志"""
        if self.config.enable_query_logging:
            self.logger.debug(f"Query: {query}")
            if params:
                self.logger.debug(f"Params: {params}")
