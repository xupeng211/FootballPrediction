"""
基础仓储接口
Base Repository Interface

定义Repository模式的基础接口，提供CRUD操作的标准方法。
Defines the base interface for the Repository pattern, providing standard CRUD operations.
"""

from abc import ABC, abstractmethod
from typing import (Any, Callable, Dict, Generic, List, Optional, Type,
                    TypeVar, Union)

from sqlalchemy import delete
from sqlalchemy import exc as SQLAlchemyExc
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager

# 类型变量
T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    基础仓储抽象类
    Base Repository Abstract Class

    提供标准的CRUD操作，所有具体仓储都应继承此类。
    Provides standard CRUD operations, all concrete repositories should inherit from this class.
    """

    def __init__(
        self, model_class: Type[T], db_manager: Optional[DatabaseManager] = None
    ):
        """
        初始化仓储

        Args:
            model_class: SQLAlchemy模型类
            db_manager: 数据库管理器实例
        """
        self.model_class = model_class
        self.db_manager = db_manager or DatabaseManager()
        self._model_name = model_class.__name__

    # ========================================
    # CRUD 基础操作
    # ========================================

    async def create(
        self, obj_data: Dict[str, Any], session: Optional[AsyncSession] = None
    ) -> T:
        """
        创建新记录

        Args:
            obj_data: 创建对象的数据字典
            session: 数据库会话（可选）

        Returns:
            创建的模型实例
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            db_obj = self.model_class(**obj_data)
            sess.add(db_obj)
            await sess.commit()
            await sess.refresh(db_obj)
            return db_obj

    async def get_by_id(
        self, obj_id: Union[int, str], session: Optional[AsyncSession] = None
    ) -> Optional[T]:
        """
        根据ID获取记录

        Args:
            obj_id: 记录ID
            session: 数据库会话（可选）

        Returns:
            模型实例或None
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = select(self.model_class).where(
                getattr(self.model_class, "id") == obj_id
            )
            result = await sess.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[T]:
        """
        获取所有记录

        Args:
            limit: 限制返回数量
            offset: 偏移量
            session: 数据库会话（可选）

        Returns:
            模型实例列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = select(self.model_class)

            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        obj_id: Union[int, str],
        obj_data: Dict[str, Any],
        session: Optional[AsyncSession] = None,
    ) -> Optional[T]:
        """
        更新记录

        Args:
            obj_id: 记录ID
            obj_data: 更新的数据字典
            session: 数据库会话（可选）

        Returns:
            更新后的模型实例或None
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = (
                update(self.model_class)
                .where(getattr(self.model_class, "id") == obj_id)
                .values(**obj_data)
                .returning(self.model_class)
            )

            result = await sess.execute(stmt)
            await sess.commit()

            return result.scalar_one_or_none()

    async def delete(
        self, obj_id: Union[int, str], session: Optional[AsyncSession] = None
    ) -> bool:
        """
        删除记录

        Args:
            obj_id: 记录ID
            session: 数据库会话（可选）

        Returns:
            是否删除成功
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = delete(self.model_class).where(
                getattr(self.model_class, "id") == obj_id
            )
            result = await sess.execute(stmt)
            await sess.commit()

            return result.rowcount > 0

    # ========================================
    # 查询方法
    # ========================================

    async def find_by(
        self,
        filters: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[T]:
        """
        根据条件查找记录

        Args:
            filters: 过滤条件字典
            limit: 限制返回数量
            offset: 偏移量
            order_by: 排序字段
            session: 数据库会话（可选）

        Returns:
            模型实例列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = select(self.model_class)

            # 应用过滤条件
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            # 应用排序
            if order_by and hasattr(self.model_class, order_by):
                stmt = stmt.order_by(getattr(self.model_class, order_by))

            # 应用分页
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)

            result = await sess.execute(stmt)
            return list(result.scalars().all())

    async def find_one_by(
        self, filters: Dict[str, Any], session: Optional[AsyncSession] = None
    ) -> Optional[T]:
        """
        根据条件查找单个记录

        Args:
            filters: 过滤条件字典
            session: 数据库会话（可选）

        Returns:
            模型实例或None
        """
        results = await self.find_by(filters, limit=1, session=session)
        return results[0] if results else None

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> int:
        """
        统计记录数量

        Args:
            filters: 过滤条件字典（可选）
            session: 数据库会话（可选）

        Returns:
            记录数量
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = select(self.model_class)

            # 应用过滤条件
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        stmt = stmt.where(getattr(self.model_class, key) == value)

            result = await sess.execute(stmt)
            return len(result.scalars().all())

    async def exists(
        self, filters: Dict[str, Any], session: Optional[AsyncSession] = None
    ) -> bool:
        """
        检查记录是否存在

        Args:
            filters: 过滤条件字典
            session: 数据库会话（可选）

        Returns:
            是否存在
        """
        count = await self.count(filters, session=session)
        return count > 0

    # ========================================
    # 批量操作
    # ========================================

    async def bulk_create(
        self, objects_data: List[Dict[str, Any]], session: Optional[AsyncSession] = None
    ) -> List[T]:
        """
        批量创建记录

        Args:
            objects_data: 创建对象的数据字典列表
            session: 数据库会话（可选）

        Returns:
            创建的模型实例列表
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            db_objects = [self.model_class(**data) for data in objects_data]
            sess.add_all(db_objects)
            await sess.commit()

            # 刷新所有对象以获取生成的ID
            for obj in db_objects:
                await sess.refresh(obj)

            return db_objects

    async def bulk_update(
        self, updates: List[Dict[str, Any]], session: Optional[AsyncSession] = None
    ) -> int:
        """
        批量更新记录

        Args:
            updates: 更新列表，每个元素包含id和更新数据
            session: 数据库会话（可选）

        Returns:
            更新的记录数量
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            updated_count = 0

            for update_data in updates:
                if "id" in update_data:
                    obj_id = update_data.pop("id")
                    stmt = (
                        update(self.model_class)
                        .where(getattr(self.model_class, "id") == obj_id)
                        .values(**update_data)
                    )
                    result = await sess.execute(stmt)
                    updated_count += result.rowcount

            await sess.commit()
            return updated_count

    async def bulk_delete(
        self, ids: List[Union[int, str]], session: Optional[AsyncSession] = None
    ) -> int:
        """
        批量删除记录

        Args:
            ids: ID列表
            session: 数据库会话（可选）

        Returns:
            删除的记录数量
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            stmt = delete(self.model_class).where(
                getattr(self.model_class, "id").in_(ids)
            )
            result = await sess.execute(stmt)
            await sess.commit()

            return result.rowcount

    # ========================================
    # 事务方法
    # ========================================

    async def execute_in_transaction(
        self,
        operations: List[Callable],
        session: Optional[AsyncSession] = None,
    ) -> Any:
        """
        在事务中执行多个操作

        Args:
            operations: 操作函数列表
            session: 数据库会话（可选）

        Returns:
            操作结果
        """
        async with self.db_manager.get_async_session() as sess:
            if session:
                sess = session

            try:
                results = []
                for operation in operations:
                    result = await operation(sess)
                    results.append(result)

                await sess.commit()
                return results
            except (
                SQLAlchemyExc.SQLAlchemyError,
                SQLAlchemyExc.DatabaseError,
                ConnectionError,
                TimeoutError,
            ):
                await sess.rollback()
                raise

    # ========================================
    # 抽象方法（子类可以重写）
    # ========================================

    @abstractmethod
    async def get_related_data(
        self,
        obj_id: Union[int, str],
        relation_name: str,
        session: Optional[AsyncSession] = None,
    ) -> Any:
        """
        获取关联数据

        Args:
            obj_id: 主记录ID
            relation_name: 关联名称
            session: 数据库会话（可选）

        Returns:
            关联数据
        """
        pass

    def get_model_class(self) -> Type[T]:
        """获取模型类"""
        return self.model_class

    def get_model_name(self) -> str:
        """获取模型名称"""
        return self._model_name
