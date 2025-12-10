"""
数据库会话管理 - 统一异步接口
Database Session Management - Unified Async Interface

这是FootballPrediction项目的标准数据库会话管理文件。
所有数据库操作都应该使用这里提供的异步接口。

作者: Async架构负责人
创建时间: 2025-12-06
版本: v2.0.0
"""

import logging
# Empty typing importAny, Optional, , , AsyncGenerator
from sqlalchemy import text
from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import (
    get_db_session,
    fetch_all,
    fetch_one,
    execute,
)

logger = logging.getLogger(__name__)

# ============================================================================
# 标准异步会话接口 - 推荐使用
# ============================================================================

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（推荐方式）

    这是标准的数据库会话获取方式，适用于所有异步应用代码。

    使用示例:
        async with get_async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()

    Yields:
        AsyncSession: 异步数据库会话
    """
    # 直接委托给已实现的异步管理器
    async with get_db_session() as session:
        yield session


# ============================================================================
# CRUD 操作接口
# ============================================================================

class AsyncCRUD:
    """异步CRUD操作基类"""

    @staticmethod
    async def create(model, **kwargs) -> Any:
        """
        创建记录

        Args:
            model: SQLAlchemy模型类
            **kwargs: 字段值

        Returns:
            创建的记录实例
        """
        async with get_async_session() as session:
            db_instance = model(**kwargs)
            session.add(db_instance)
            await session.commit()
            await session.refresh(db_instance)
            return db_instance

    @staticmethod
    async def get(model, pk: Any) -> Optional[Any]:
        """
        根据主键获取记录

        Args:
            model: SQLAlchemy模型类
            pk: 主键值

        Returns:
            记录实例或None
        """
        async with get_async_session() as session:
            result = await session.execute(
                model.__table__.select().where(model.id == pk)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_all(model) -> list[Any]:
        """
        获取所有记录

        Args:
            model: SQLAlchemy模型类

        Returns:
            记录列表
        """
        async with get_async_session() as session:
            result = await session.execute(model.__table__.select())
            return result.scalars().all()

    @staticmethod
    async def update(model, pk: Any, **kwargs) -> Optional[Any]:
        """
        更新记录

        Args:
            model: SQLAlchemy模型类
            pk: 主键值
            **kwargs: 要更新的字段值

        Returns:
            更新后的记录实例或None
        """
        async with get_async_session() as session:
            result = await session.execute(
                model.__table__.update().where(model.id == pk).values(**kwargs)
            )
            await session.commit()

            # 返回更新后的记录
            if result.rowcount > 0:
                return await AsyncCRUD.get(model, pk)
            return None

    @staticmethod
    async def delete(model, pk: Any) -> bool:
        """
        删除记录

        Args:
            model: SQLAlchemy模型类
            pk: 主键值

        Returns:
            是否删除成功
        """
        async with get_async_session() as session:
            result = await session.execute(
                model.__table__.delete().where(model.id == pk)
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def execute_query(query, params: Optional[dict] = None) -> Any:
        """
        执行自定义查询

        Args:
            query: SQLAlchemy查询对象或SQL字符串
            params: 查询参数

        Returns:
            查询结果
        """
        return await execute(query, params)


# ============================================================================
# 批量操作接口
# ============================================================================

class AsyncBatchOperations:
    """异步批量操作接口"""

    @staticmethod
    async def bulk_create(model_class, instances: list[dict]) -> list[Any]:
        """
        批量创建记录

        Args:
            model_class: SQLAlchemy模型类
            instances: 数据字典列表

        Returns:
            创建的记录列表
        """
        async with get_async_session() as session:
            db_instances = [model_class(**data) for data in instances]
            session.add_all(db_instances)
            await session.commit()

            # 刷新所有实例以获取生成的主键等
            for instance in db_instances:
                await session.refresh(instance)

            return db_instances

    @staticmethod
    async def bulk_update(model_class, updates: list[dict]) -> int:
        """
        批量更新记录

        Args:
            model_class: SQLAlchemy模型类
            updates: 更新数据列表，每个字典应包含主键和要更新的字段

        Returns:
            更新的记录数量
        """
        updated_count = 0

        async with get_async_session() as session:
            for update_data in updates:
                pk = update_data.pop('id', None) or update_data.pop('uuid', None)
                if pk is not None:
                    result = await session.execute(
                        model_class.__table__.update()
                        .where(model_class.id == pk)
                        .values(**update_data)
                    )
                    if result.rowcount > 0:
                        updated_count += 1
                        await session.commit()

            return updated_count

    @staticmethod
    async def bulk_delete(model_class, pks: list[Any]) -> int:
        """
        批量删除记录

        Args:
            model_class: SQLAlchemy模型类
            pks: 主键列表

        Returns:
            删除的记录数量
        """
        deleted_count = 0

        async with get_async_session() as session:
            for pk in pks:
                result = await session.execute(
                    model_class.__table__.delete().where(model_class.id == pk)
                )
                if result.rowcount > 0:
                    deleted_count += 1
                    await session.commit()

            return deleted_count


# ============================================================================
# 便捷查询接口
# ============================================================================

class AsyncQuery:
    """异步查询接口"""

    @staticmethod
    async def fetch_all(query, params: Optional[dict] = None) -> list[dict]:
        """
        执行查询并返回所有结果

        Args:
            query: SQLAlchemy查询对象或SQL字符串
            params: 查询参数

        Returns:
            查询结果列表
        """
        return await fetch_all(query, params)

    @staticmethod
    async def fetch_one(query, params: Optional[dict] = None) -> Optional[dict]:
        """
        执行查询并返回单个结果

        Args:
            query: SQLAlchemy查询对象或SQL字符串
            params: 查询参数

        Returns:
            单个查询结果字典，如果没有结果则返回None
        """
        return await fetch_one(query, params)

    @staticmethod
    async def fetch_page(
        query,
        page: int = 1,
        page_size: int = 20,
        params: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        分页查询

        Args:
            query: SQLAlchemy查询对象
            page: 页码（从1开始）
            page_size: 每页记录数
            params: 查询参数

        Returns:
            分页结果字典
        """
        offset = (page - 1) * page_size

        # 计算总数
        async with get_async_session() as session:
            count_result = await session.execute(query)
            total = count_result.scalar()

            # 获取分页数据
            paginated_query = query.offset(offset).limit(page_size)
            result = await session.execute(paginated_query)
            items = [dict(row._mapping) for row in result.fetchall()]

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'has_next': page * page_size < total,
                'has_prev': page > 1
            }

    @staticmethod
    async def exists(query, params: Optional[dict] = None) -> bool:
        """
        检查记录是否存在

        Args:
            query: SQLAlchemy查询对象或SQL字符串
            params: 查询参数

        Returns:
            是否存在记录
        """
        async with get_async_session() as session:
            result = await session.execute(query.limit(1), params)
            return result.first() is not None


# ============================================================================
# 导出统一接口
# ============================================================================

__all__ = [
    # 标准会话接口
    "get_async_session",

    # CRUD操作
    "AsyncCRUD",

    # 批量操作
    "AsyncBatchOperations",

    # 查询接口
    "AsyncQuery",

    # 向后兼容性别名
    "get_session",  # 指向 get_async_session
]
