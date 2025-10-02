"""
import asyncio
标准异步数据库测试模板

兼容 SQLAlchemy 2.0 + asyncio
使用 pytest-asyncio 进行异步测试

本模板包含：
1. 正确的异步 fixture 定义
2. 正确的测试函数装饰器
3. 正确的 await 调用方式
4. 正确的 session 管理方式
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager


class AsyncDatabaseTestTemplate:
    """异步数据库测试模板类"""

    # ===============================
    # Fixture 定义 - 标准模式
    # ===============================

    @pytest_asyncio.fixture
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        标准异步数据库会话 fixture

        特点：
        1. 使用 @pytest_asyncio.fixture 而非 @pytest.fixture
        2. 返回类型注解：AsyncGenerator[AsyncSession, None]
        3. 使用 async with 正确管理会话生命周期
        4. 自动处理连接的创建和关闭
        """
        db_manager = DatabaseManager()

        # 确保数据库连接已初始化
        if not db_manager.is_initialized():
            await db_manager.initialize()

        try:
            async with db_manager.get_async_session() as session:
                yield session
        finally:
            # 清理工作会由 async with 自动处理
            pass

    @pytest_asyncio.fixture
    async def async_transaction_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        带事务回滚的异步数据库会话 fixture

        用于测试需要数据库事务但不想持久化更改的场景
        """
        db_manager = DatabaseManager()

        if not db_manager.is_initialized():
            await db_manager.initialize()

        async with db_manager.get_async_session() as session:
            # 开始事务
            transaction = await session.begin()
            try:
                yield session
            finally:
                # 回滚所有更改
                await transaction.rollback()

    # ===============================
    # 测试函数示例 - 各种常见场景
    # ===============================

    @pytest.mark.asyncio
    async def test_simple_query(self, async_session: AsyncSession):
        """
        简单查询测试示例

        展示：
        1. 正确的 @pytest.mark.asyncio 装饰器
        2. 正确的 await session.execute() 调用
        3. 正确的结果处理
        """
        # 执行查询
        result = await async_session.execute(text("SELECT 1 as test_value"))

        # 获取结果
        row = result.fetchone()

        # 验证
        assert row is not None
        assert row.test_value == 1

    @pytest.mark.asyncio
    async def test_parameterized_query(self, async_session: AsyncSession):
        """
        参数化查询测试示例

        展示如何正确传递参数到查询中
        """
        # 带参数的查询
        query = text("SELECT :value as param_value")
        result = await async_session.execute(query, {"value": "test_param"})

        row = result.fetchone()
        assert row.param_value == "test_param"

    @pytest.mark.asyncio
    async def test_multiple_queries(self, async_session: AsyncSession):
        """
        多查询测试示例

        展示在同一个session中执行多个查询
        """
        # 第一个查询
        result1 = await async_session.execute(
            text("SELECT COUNT(*) as total FROM information_schema.tables")
        )
        count = result1.scalar()

        # 第二个查询
        result2 = await async_session.execute(
            text("SELECT current_database() as db_name")
        )
        db_name = result2.scalar()

        # 验证
        assert isinstance(count, int)
        assert count > 0
        assert db_name is not None

    @pytest.mark.asyncio
    async def test_transaction_with_commit(self, async_session: AsyncSession):
        """
        事务提交测试示例

        展示如何正确处理事务提交
        注意：这个会实际修改数据库，谨慎使用
        """
        # 这里通常会插入测试数据
        # 然后提交事务
        await async_session.commit()

        # 验证提交成功
        assert True  # 替换为实际验证逻辑

    @pytest.mark.asyncio
    async def test_transaction_with_rollback(
        self, async_transaction_session: AsyncSession
    ):
        """
        事务回滚测试示例

        展示如何使用会自动回滚的session fixture
        """
        # 执行一些会修改数据的操作
        # 使用 async_transaction_session 确保不会持久化

        # 这里的任何修改都会在测试结束后自动回滚
        result = await async_transaction_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, async_session: AsyncSession):
        """
        错误处理测试示例

        展示如何正确处理数据库异常
        """
        from sqlalchemy.exc import SQLAlchemyError

        try:
            # 故意执行一个错误的查询
            await async_session.execute(text("SELECT * FROM non_existent_table"))
            assert False, "应该抛出异常"

        except SQLAlchemyError as e:
            # 验证捕获到预期的异常
            assert "non_existent_table" in str(e).lower()

    # ===============================
    # 性能测试示例
    # ===============================

    @pytest.mark.asyncio
    async def test_query_performance(self, async_session: AsyncSession):
        """
        查询性能测试示例

        展示如何测量查询执行时间
        """
        import time

        start_time = time.time()

        # 执行查询
        result = await async_session.execute(text("SELECT 1"))
        result.fetchone()

        execution_time = time.time() - start_time

        # 验证性能要求（例如：查询应该在100ms内完成）
        assert execution_time < 0.1, f"查询执行时间 {execution_time:.3f}s 超过预期"

    # ===============================
    # 集成测试示例
    # ===============================

    @pytest.mark.asyncio
    async def test_database_schema_check(self, async_session: AsyncSession):
        """
        数据库模式检查示例

        验证关键表和索引是否存在
        """
        # 检查表是否存在
        table_query = text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        )

        result = await async_session.execute(table_query)
        tables = {row.table_name for row in result.fetchall()}

        # 验证关键表存在
        expected_tables = {"matches", "teams", "leagues", "odds"}
        missing_tables = expected_tables - tables

        assert not missing_tables, f"缺少关键表: {missing_tables}"


# ===============================
# 使用指南和最佳实践
# ===============================

"""
使用指南:

1. **Fixture 使用**:
   - 标准查询使用 `async_session`
   - 需要回滚的测试使用 `async_transaction_session`

2. **装饰器使用**:
   - 测试类不需要特殊装饰器
   - 每个异步测试函数必须使用 `@pytest.mark.asyncio`

3. **查询执行**:
   - 总是使用 `await session.execute(query)`
   - 参数化查询使用字典传递参数
   - 使用 `text()` 包装原生SQL查询

4. **结果处理**:
   - `result.fetchone()` 获取单行
   - `result.fetchall()` 获取所有行
   - `result.scalar()` 获取单个标量值

5. **事务管理**:
   - `await session.commit()` 提交事务
   - `await session.rollback()` 回滚事务
   - 使用 `async_transaction_session` 自动回滚

6. **错误处理**:
   - 捕获 `SQLAlchemyError` 及其子类
   - 使用 try-except 处理预期的数据库错误

7. **性能测试**:
   - 测量执行时间验证性能要求
   - 使用合适的超时限制

示例使用:

```python
class TestMyDatabase(AsyncDatabaseTestTemplate):

    @pytest.mark.asyncio
    async def test_my_feature(self, async_session: AsyncSession):
        # 使用模板中的方法和最佳实践
        result = await async_session.execute(text("SELECT * FROM my_table"))
        rows = result.fetchall()
        assert len(rows) > 0
```
"""
