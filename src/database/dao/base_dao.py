"""
数据访问对象(DAO)基础抽象类
Base Data Access Object (DAO) Abstract Class

提供统一、类型安全、高性能的数据库访问接口。
所有具体DAO实现都应该继承此基类。
"""

import logging
from abc import ABC, abstractmethod
from typing import (
    TypeVar,
    Generic,
    Optional,
    Any,
    dict,
    list,
    Union,
    typing.Type,
    cast,
)
from collections.abc import Sequence
from datetime import datetime
from contextlib import asynccontextmanager

from pydantic import BaseModel
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError

# 导入异常定义
try:
    from .exceptions import (
        DAOException,
        RecordNotFoundError,
        DuplicateRecordError,
        ValidationError,
        DatabaseConnectionError,
        handle_sqlalchemy_exception,
    )
except ImportError:
    # 如果异常模块不存在，提供基础定义
    class DAOException(Exception):
        def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
            self.message = message
            self.details = details or {}
            super().__init__(self.message)

    class RecordNotFoundError(DAOException):
        def __init__(self, model: str, identifier: Any):
            super().__init__(f"在{model}中未找到记录: {identifier}")
            self.model = model
            self.identifier = identifier

    class DuplicateRecordError(DAOException):
        def __init__(self, model: str, field: str, value: Any):
            super().__init__(f"{model}中已存在{field}为'{value}'的记录")
            self.model = model
            self.field = field
            self.value = value

    class ValidationError(DAOException):
        def __init__(self, model: str, validation_errors: dict[str, Any]):
            super().__init__(f"{model}数据验证失败")
            self.model = model
            self.validation_errors = validation_errors

    class DatabaseConnectionError(DAOException):
        def __init__(self, message: str):
            super().__init__(f"数据库连接错误: {message}")

    def handle_sqlalchemy_exception(func_name: str, exc: SQLAlchemyError) -> DAOException:
        """SQLAlchemy异常转换工具函数"""
        if "duplicate key" in str(exc).lower():
            return DuplicateRecordError("Unknown", "unknown", "unknown")
        elif "connection" in str(exc).lower():
            return DatabaseConnectionError(str(exc))
        else:
            return DAOException(f"{func_name}执行失败: {str(exc)}")

# 类型定义
ModelType = TypeVar("ModelType")  # SQLAlchemy模型类型
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)  # 创建模式类型
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)  # 更新模式类型

logger = logging.getLogger(__name__)


class BaseDAO(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    数据访问对象基础抽象类

    提供标准的CRUD操作接口和通用功能。
    所有具体的DAO实现都应该继承此类并实现抽象方法。
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        初始化DAO实例

        Args:
            model: SQLAlchemy模型类
            session: 异步数据库会话
        """
        self.model = model
        self.session = session
        self.model_name = model.__name__ if hasattr(model, '__name__') else 'Model'

    @property
    @abstractmethod
    def primary_key_field(self) -> str:
        """
        获取主键字段名

        子类必须实现此方法来指定主键字段。

        Returns:
            str: 主键字段名
        """
        pass

    # ==================== 基础CRUD操作 ====================

    async def get(
        self,
        id: Any,
        *,
        options: Optional[list] = None,
        for_update: bool = False
    ) -> Optional[ModelType]:
        """
        根据主键获取单条记录

        Args:
            id: 主键值
            options: 预加载选项列表
            for_update: 是否加悲观锁

        Returns:
            Optional[ModelType]: 找到的记录或None

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(getattr(self.model, self.primary_key_field) == id)

            # 应用预加载选项
            if options:
                for option in options:
                    query = query.options(option)

            # 应用悲观锁
            if for_update:
                query = query.with_for_update()

            result = await self.session.execute(query)
            record = result.scalar_one_or_none()

            if record:
                logger.debug(f"获取{self.model_name}记录成功: {id}")
            else:
                logger.debug(f"未找到{self.model_name}记录: {id}")

            return record

        except SQLAlchemyError as e:
            logger.error(f"获取{self.model_name}记录失败: {id}")
            raise handle_sqlalchemy_exception(f"{self.model_name}.get", e)

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        options: Optional[list] = None
    ) -> list[ModelType]:
        """
        获取多条记录

        Args:
            skip: 跳过记录数
            limit: 返回记录数限制
            filters: 过滤条件字典
            order_by: 排序字段
            options: 预加载选项

        Returns:
            list[ModelType]: 记录列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model)

            # 应用过滤条件
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            # 应用排序
            if order_by:
                if hasattr(self.model, order_by):
                    query = query.order_by(getattr(self.model, order_by))
                elif order_by.startswith('-'):
                    # 降序处理
                    field = order_by[1:]
                    if hasattr(self.model, field):
                        query = query.order_by(getattr(self.model, field).desc())

            # 应用分页
            query = query.offset(skip).limit(limit)

            # 应用预加载选项
            if options:
                for option in options:
                    query = query.options(option)

            result = await self.session.execute(query)
            records = result.scalars().all()

            logger.debug(f"获取{self.model_name}多条记录成功: {len(records)}条")
            return list(records)

        except SQLAlchemyError as e:
            logger.error(f"获取{self.model_name}多条记录失败")
            raise handle_sqlalchemy_exception(f"{self.model_name}.get_multi", e)

    async def create(
        self,
        *,
        obj_in: CreateSchemaType,
        refresh: bool = True
    ) -> ModelType:
        """
        创建新记录

        Args:
            obj_in: 创建数据模式
            refresh: 是否刷新以获取数据库生成值

        Returns:
            ModelType: 创建的记录

        Raises:
            ValidationError: 数据验证错误
            DuplicateRecordError: 重复记录错误
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 将Pydantic模型转换为字典
            obj_data = obj_in.model_dump(exclude_unset=True)

            # 创建模型实例
            db_obj = self.model(**obj_data)

            # 添加到会话
            self.session.add(db_obj)

            # 刷新以获取生成值（如主键）
            if refresh:
                # 提交到数据库以确保持久化
                await self.session.commit()
                try:
                    await self.session.refresh(db_obj)
                except:
                    # 如果刷新失败，对象已经包含需要的信息
                    pass

            logger.info(f"创建{self.model_name}记录成功: {getattr(db_obj, self.primary_key_field, 'unknown')}")
            return db_obj

        except SQLAlchemyError as e:
            logger.error(f"创建{self.model_name}记录失败: {obj_in}")
            raise handle_sqlalchemy_exception(f"{self.model_name}.create", e)

    async def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
        refresh: bool = True
    ) -> ModelType:
        """
        更新记录

        Args:
            db_obj: 待更新的数据库对象
            obj_in: 更新数据模式
            refresh: 是否刷新

        Returns:
            ModelType: 更新后的记录

        Raises:
            RecordNotFoundError: 记录未找到
            ValidationError: 数据验证错误
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 获取更新数据
            update_data = obj_in.model_dump(exclude_unset=True)

            if not update_data:
                logger.warning(f"没有提供更新数据: {self.model_name}")
                return db_obj

            # 更新字段
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
                else:
                    logger.warning(f"{self.model_name}没有字段: {field}")

            # 标记为已修改
            self.session.add(db_obj)

            # 刷新对象
            if refresh:
                # 提交到数据库
                await self.session.commit()
                try:
                    await self.session.refresh(db_obj)
                except:
                    # 如果刷新失败，对象已经包含更新的信息
                    pass

            logger.info(f"更新{self.model_name}记录成功: {getattr(db_obj, self.primary_key_field, 'unknown')}")
            return db_obj

        except SQLAlchemyError as e:
            logger.error(f"更新{self.model_name}记录失败: {obj_in}")
            raise handle_sqlalchemy_exception(f"{self.model_name}.update", e)

    async def delete(
        self,
        *,
        id: Any,
        soft_delete: bool = False
    ) -> bool:
        """
        删除记录

        Args:
            id: 主键值
            soft_delete: 是否软删除（如果有deleted_at字段）

        Returns:
            bool: 是否删除成功

        Raises:
            RecordNotFoundError: 记录未找到
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 获取记录
            db_obj = await self.get(id)
            if not db_obj:
                raise RecordNotFoundError(self.model_name, id)

            if soft_delete and hasattr(db_obj, 'deleted_at'):
                # 软删除
                db_obj.deleted_at = datetime.utcnow()
                self.session.add(db_obj)
                logger.info(f"软删除{self.model_name}记录成功: {id}")
            else:
                # 硬删除
                await self.session.delete(db_obj)
                logger.info(f"硬删除{self.model_name}记录成功: {id}")

            return True

        except DAOException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"删除{self.model_name}记录失败: {id}")
            raise handle_sqlalchemy_exception(f"{self.model_name}.delete", e)

    # ==================== 高级查询方法 ====================

    async def count(
        self,
        *,
        filters: Optional[dict[str, Any]] = None
    ) -> int:
        """
        统计记录数量

        Args:
            filters: 过滤条件

        Returns:
            int: 记录数量

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(func.count())

            # 应用过滤条件
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            result = await self.session.execute(query)
            count = result.scalar()

            logger.debug(f"统计{self.model_name}记录数量: {count}")
            return count

        except SQLAlchemyError as e:
            logger.error(f"统计{self.model_name}记录数量失败")
            raise handle_sqlalchemy_exception(f"{self.model_name}.count", e)

    async def exists(
        self,
        *,
        filters: dict[str, Any]
    ) -> bool:
        """
        检查记录是否存在

        Args:
            filters: 过滤条件字典

        Returns:
            bool: 是否存在

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).limit(1)

            # 应用过滤条件
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

            result = await self.session.execute(query)
            record = result.scalar_one_or_none()

            exists = record is not None
            logger.debug(f"检查{self.model_name}记录存在性: {exists}")
            return exists

        except SQLAlchemyError as e:
            logger.error(f"检查{self.model_name}记录存在性失败")
            raise handle_sqlalchemy_exception(f"{self.model_name}.exists", e)

    # ==================== 批量操作方法 ====================

    async def bulk_create(
        self,
        *,
        objects_in: list[CreateSchemaType],
        batch_size: int = 1000
    ) -> list[ModelType]:
        """
        批量创建记录

        Args:
            objects_in: 创建数据列表
            batch_size: 批处理大小

        Returns:
            list[ModelType]: 创建的记录列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            db_objects = []

            # 分批处理
            for i in range(0, len(objects_in), batch_size):
                batch = objects_in[i:i + batch_size]

                for obj_in in batch:
                    obj_data = obj_in.model_dump(exclude_unset=True)
                    db_obj = self.model(**obj_data)
                    db_objects.append(db_obj)

                # 批量添加
                self.session.add_all(db_objects)

                # 每批后刷新
                await self.session.flush()

            logger.info(f"批量创建{self.model_name}记录成功: {len(db_objects)}条")
            return db_objects

        except SQLAlchemyError as e:
            logger.error(f"批量创建{self.model_name}记录失败")
            raise handle_sqlalchemy_exception(f"{self.model_name}.bulk_create", e)

    # ==================== 事务支持 ====================

    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器

        Usage:
            async with dao.transaction():
                # 执行多个操作
                await dao.create(obj_in=obj1)
                await dao.update(db_obj=obj2, obj_in=update_data)
                # 如果所有操作成功，事务自动提交
                # 如果有异常，事务自动回滚
        """
        try:
            # 开始事务
            transaction = await self.session.begin()
            logger.debug(f"开始{self.model_name}事务")

            try:
                yield transaction
                # 提交事务
                await transaction.commit()
                logger.debug(f"{self.model_name}事务提交成功")
            except Exception as e:
                # 回滚事务
                await transaction.rollback()
                logger.error(f"{self.model_name}事务回滚: {e}")
                raise

        except Exception as e:
            logger.error(f"{self.model_name}事务管理失败: {e}")
            raise DAOException(f"事务管理失败: {str(e)}")

    # ==================== 调试和监控 ====================

    def get_query_info(self, query: Select) -> dict[str, Any]:
        """
        获取查询信息（用于调试）

        Args:
            query: SQLAlchemy查询对象

        Returns:
            dict[str, Any]: 查询信息
        """
        return {
            "model": self.model_name,
            "query_string": str(query),
            "compiled_query": query.compile(compile_kwargs={"literal_binds": True}),
            "parameters": query.compile().params
        }

    async def execute_query_with_logging(
        self,
        query: Select,
        operation_name: str = "query"
    ) -> Any:
        """
        执行查询并记录日志

        Args:
            query: SQLAlchemy查询
            operation_name: 操作名称

        Returns:
            Any: 查询结果
        """
        start_time = datetime.utcnow()

        try:
            # 记录查询信息
            if logger.isEnabledFor(logging.DEBUG):
                query_info = self.get_query_info(query)
                logger.debug(f"执行{operation_name}查询: {query_info}")

            # 执行查询
            result = await self.session.execute(query)

            # 记录执行时间
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.debug(f"{operation_name}查询完成，耗时: {duration:.3f}s")

            return result

        except SQLAlchemyError as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"{operation_name}查询失败，耗时: {duration:.3f}s, 错误: {e}")
            raise


# 导出主要接口
__all__ = [
    'BaseDAO',
    'DAOException',
    'RecordNotFoundError',
    'DuplicateRecordError',
    'ValidationError',
    'DatabaseConnectionError'
]
