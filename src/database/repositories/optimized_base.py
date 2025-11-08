#!/usr/bin/env python3
"""
优化版基础仓储
集成异步I/O优化和查询优化功能
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager
from src.database.repositories.base import BaseRepository
from src.performance.async_optimizer import get_batch_processor, get_connection_pool
from src.performance.db_query_optimizer import get_query_optimizer

T = TypeVar("T")


class OptimizedRepository(BaseRepository[T], ABC, Generic[T]):
    """
    优化版基础仓储
    集成异步I/O优化和查询优化功能，提供高性能的数据访问
    """

    def __init__(self, model_class: type[T], db_manager: DatabaseManager | None = None):
        super().__init__(model_class, db_manager)
        self.query_optimizer = get_query_optimizer()
        self.connection_pool = get_connection_pool()
        self.batch_processor = get_batch_processor()

    # ========================================
    # 优化的CRUD操作
    # ========================================

    async def create_optimized(
        self, obj_data: dict[str, Any], session: AsyncSession | None = None
    ) -> T:
        """
        优化的创建操作
        使用连接池和查询优化
        """
        if session:
            # 如果提供了会话，直接使用
            db_obj = self.model_class(**obj_data)
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)
            return db_obj
        else:
            # 使用优化的连接池
            async with self.connection_pool.get_connection() as sess:
                return await self._execute_create(sess, obj_data)

    async def _execute_create(
        self, session: AsyncSession, obj_data: dict[str, Any]
    ) -> T:
        """内部创建执行方法"""
        db_obj = self.model_class(**obj_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get_by_id_optimized(
        self, obj_id: int | str, session: AsyncSession | None = None
    ) -> T | None:
        """
        优化的根据ID获取记录
        使用查询优化和缓存
        """
        query = f"SELECT * FROM {self._model_name.lower()} WHERE id = :id"
        params = {"id": obj_id}

        return await self.query_optimizer.execute_optimized_query(
            query, params, analyze=True, auto_explain=False
        )

    async def find_by_optimized(
        self,
        filters: dict[str, Any],
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
        session: AsyncSession | None = None,
    ) -> list[T]:
        """
        优化的条件查询
        使用查询分析和执行计划优化
        """
        # 构建优化查询
        query = f"SELECT * FROM {self._model_name.lower()} WHERE 1=1"
        params = {}

        # 添加过滤条件
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query += f" AND {key} = :{key}"
                params[key] = value

        # 添加排序
        if order_by and hasattr(self.model_class, order_by):
            query += f" ORDER BY {order_by}"

        # 添加分页
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        return await self.query_optimizer.execute_optimized_query(query, params)

    async def find_by_with_index_hint(
        self,
        filters: dict[str, Any],
        index_hint: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """
        使用索引提示的查询
        """
        query = f"SELECT * FROM {self._model_name.lower()}"
        if index_hint:
            query += f" USE INDEX ({index_hint})"

        query += " WHERE 1=1"
        params = {}

        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query += f" AND {key} = :{key}"
                params[key] = value

        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        return await self.query_optimizer.execute_optimized_query(query, params)

    # ========================================
    # 批量操作优化
    # ========================================

    async def bulk_create_optimized(
        self, objects_data: list[dict[str, Any]]
    ) -> list[T]:
        """
        优化的批量创建
        使用异步批量处理器
        """

        async def process_batch(batch_data: list[dict[str, Any]]) -> list[T]:
            async with self.connection_pool.get_connection() as session:
                db_objects = [self.model_class(**data) for data in batch_data]
                session.add_all(db_objects)
                await session.commit()

                # 刷新对象以获取ID
                for obj in db_objects:
                    await session.refresh(obj)

                return db_objects

        # 使用批量处理器
        results = await self.batch_processor.process_batch(objects_data, process_batch)
        # 扁平化结果
        return [item for sublist in results if sublist for item in sublist]

    async def bulk_update_optimized(self, updates: list[dict[str, Any]]) -> int:
        """
        优化的批量更新
        使用CASE WHEN语句优化
        """
        if not updates:
            return 0

        # 构建批量更新查询
        ids = [update["id"] for update in updates if "id" in update]
        if not ids:
            return 0

        # 获取第一个更新的字段作为模板
        first_update = next(u for u in updates if "id" in u and len(u) > 1)
        update_fields = [k for k in first_update.keys() if k != "id"]

        if not update_fields:
            return 0

        # 构建CASE WHEN语句
        query = f"UPDATE {self._model_name.lower()} SET "
        params = {}

        for i, field in enumerate(update_fields):
            query += f"{field} = CASE id "
            for update in updates:
                if "id" in update and field in update:
                    query += (
                        f"WHEN :id_{i}_{update['id']} THEN :{field}_{i}_{update['id']} "
                    )
                    params[f"id_{i}_{update['id']}"] = update["id"]
                    params[f"{field}_{i}_{update['id']}"] = update[field]
            query += "END"
            if i < len(update_fields) - 1:
                query += ", "

        query += " WHERE id IN :ids"
        params["ids"] = ids

        async with self.connection_pool.get_connection() as session:
            stmt = update(self.model_class).where(self.model_class.id.in_(ids))

            # 执行更新
            for update_data in updates:
                if "id" in update_data:
                    obj_id = update_data.pop("id")
                    stmt = stmt.where(self.model_class.id == obj_id).values(
                        **update_data
                    )

            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def bulk_delete_optimized(self, ids: list[int | str]) -> int:
        """
        优化的批量删除
        """
        if not ids:
            return 0

        query = f"DELETE FROM {self._model_name.lower()} WHERE id = ANY(:ids)"
        params = {"ids": ids}

        async with self.connection_pool.get_connection() as session:
            stmt = delete(self.model_class).where(self.model_class.id.in_(ids))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    # ========================================
    # 高级查询功能
    # ========================================

    async def find_with_joins(
        self,
        filters: dict[str, Any] | None = None,
        joins: list[dict[str, Any]] | None = None,
        select_fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        带连接的复杂查询

        Args:
            filters: 过滤条件
            joins: 连接配置 [{"table": "related_table", "local_key": "id", "foreign_key": "related_id"}, ...]
            select_fields: 选择的字段
            limit: 限制数量
            offset: 偏移量

        Returns:
            查询结果字典列表
        """
        # 构建基础查询
        query = "SELECT"
        params = {}

        # 选择字段
        if select_fields:
            query += ", ".join(select_fields)
        else:
            query += f"{self._model_name.lower()}.*"

        query += f" FROM {self._model_name.lower()}"

        # 添加连接
        if joins:
            for join_config in joins:
                join_table = join_config["table"]
                local_key = join_config["local_key"]
                foreign_key = join_config["foreign_key"]
                join_type = join_config.get("type", "INNER JOIN")

                query += f" {join_type} {join_table} ON {self._model_name.lower()}.{local_key} = {join_table}.{foreign_key}"

        # 添加过滤条件
        if filters:
            query += " WHERE 1=1"
            for key, value in filters.items():
                query += f" AND {key} = :{key}"
                params[key] = value

        # 添加分页
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        return await self.query_optimizer.execute_optimized_query(query, params)

    async def find_aggregated(
        self,
        group_by: list[str],
        aggregates: dict[str, str],
        filters: dict[str, Any] | None = None,
        having: dict[str, Any] | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        聚合查询

        Args:
            group_by: 分组字段
            aggregates: 聚合函数 {"total": "SUM(amount)", "count": "COUNT(*)"}
            filters: 过滤条件
            having: HAVING条件
            order_by: 排序字段

        Returns:
            聚合结果列表
        """
        # 构建SELECT子句
        select_fields = group_by.copy()
        for alias, func in aggregates.items():
            select_fields.append(f"{func} as {alias}")

        query = f"SELECT {', '.join(select_fields)} FROM {self._model_name.lower()}"
        params = {}

        # WHERE条件
        if filters:
            query += " WHERE 1=1"
            for key, value in filters.items():
                query += f" AND {key} = :{key}"
                params[key] = value

        # GROUP BY
        query += f" GROUP BY {', '.join(group_by)}"

        # HAVING条件
        if having:
            query += " HAVING 1=1"
            for key, value in having.items():
                query += f" AND {key} = :having_{key}"
                params[f"having_{key}"] = value

        # ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"

        return await self.query_optimizer.execute_optimized_query(query, params)

    async def exists_with_cache(
        self, filters: dict[str, Any], cache_ttl: int = 300
    ) -> bool:
        """
        带缓存的存在性检查
        """
        cache_key = f"exists_{self._model_name}_{str(filters)}"

        # 这里可以集成Redis缓存
        # 暂时直接查询数据库
        query = f"SELECT EXISTS(SELECT 1 FROM {self._model_name.lower()} WHERE 1=1"
        params = {}

        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query += f" AND {key} = :{key}"
                params[key] = value

        query += ")"

        result = await self.query_optimizer.execute_optimized_query(
            query, params, use_cache=True
        )
        return bool(result)

    # ========================================
    # 性能监控和分析
    # ========================================

    async def analyze_query_performance(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        分析查询性能
        """
        # 构建测试查询
        query = f"SELECT * FROM {self._model_name.lower()}"
        params = {}

        if filters:
            query += " WHERE 1=1"
            for key, value in filters.items():
                query += f" AND {key} = :{key}"
                params[key] = value

        # 获取查询分析
        analysis = self.query_optimizer.analyzer.analyze_query(query)

        # 添加表特定信息
        analysis["table_name"] = self._model_name.lower()
        analysis["repository_type"] = "optimized"

        return analysis

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        获取仓储性能指标
        """
        return {
            "query_optimizer_metrics": self.query_optimizer.get_performance_report(),
            "connection_pool_stats": self.connection_pool.get_pool_stats(),
            "batch_processor_metrics": self.batch_processor.metrics.__dict__,
        }

    # ========================================
    # 事务优化
    # ========================================

    async def execute_transaction_optimized(
        self, operations: list[Callable[[AsyncSession], Any]]
    ) -> list[Any]:
        """
        优化的事务执行
        使用连接池和错误处理
        """
        async with self.connection_pool.get_connection() as session:
            try:
                results = []
                for operation in operations:
                    result = await operation(session)
                    results.append(result)

                await session.commit()
                return results

            except Exception as e:
                await session.rollback()
                logger.error(f"优化事务执行失败: {e}")
                raise

    # ========================================
    # 抽象方法实现
    # ========================================

    @abstractmethod
    async def get_related_data(
        self,
        obj_id: int | str,
        relation_name: str,
        session: AsyncSession | None = None,
    ) -> Any:
        """
        获取关联数据（子类需要实现）
        """
        pass


# 便捷函数
async def create_optimized_repository(
    model_class: type[T], db_manager: DatabaseManager | None = None
) -> OptimizedRepository[T]:
    """
    创建优化仓储实例
    """
    # 这里需要具体的子类实现
    # 返回基类实例用于演示
    return OptimizedRepository(model_class, db_manager)


if __name__ == "__main__":

    async def demo_optimized_repository():
        """演示优化仓储功能"""
        print("🚀 演示优化仓储功能")

        # 这里需要实际的模型类
        # from src.domain.entities import Match
        # repo = OptimizedRepository(Match)

        print("✅ 优化仓储功能演示完成")

    import asyncio

    asyncio.run(demo_optimized_repository())
