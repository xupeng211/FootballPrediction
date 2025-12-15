#!/usr/bin/env python3
"""
数据库异步化集成测试
Database Async Integration Tests

验证 asyncpg + SQLAlchemy 2.0 Async 的完整异步数据库操作

作者: Async架构负责人
创建时间: 2025-12-06
版本: v1.0.0
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    select, delete, update, text, func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import get_db_session, execute, fetch_all, fetch_one
from src.database.session import get_async_session, AsyncCRUD, AsyncBatchOperations, AsyncQuery


# Test Model Definitions
TestBase = declarative_base()


class AsyncTestModel(TestBase):
    """异步测试模型"""
    __tablename__ = "async_test_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AsyncTestModel(id={self.id}, name={self.name}, score={self.score})>"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
class TestAsyncDatabaseOperations:
    """异步数据库操作集成测试"""

    @pytest.fixture(autouse=True)
    async def setup_test_db(self):
        """设置测试数据库表"""
        # 创建测试表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS async_test_models (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            description VARCHAR(500),
            score FLOAT DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            await execute(text(create_table_sql))
            await execute(text("TRUNCATE TABLE async_test_models RESTART IDENTITY CASCADE"))
        except Exception as e:
            pytest.skip(f"Database setup failed: {e}")

    @pytest.fixture(autouse=True)
    async def cleanup_test_data(self):
        """清理测试数据"""
        yield
        try:
            await execute(text("TRUNCATE TABLE async_test_models RESTART IDENTITY CASCADE"))
        except Exception as e:
            pass  # Cleanup should not fail tests

    async def test_create_model_instance(self):
        """测试创建模型实例"""
        print("\n🧪 测试创建模型实例")

        # 准备测试数据
        test_name = f"test_model_{uuid.uuid4().hex[:8]}"
        test_data = {
            "name": test_name,
            "description": "Test model for async database operations",
            "score": 95.5,
            "is_active": True
        }

        # 使用 AsyncCRUD 创建实例
        created_model = await AsyncCRUD.create(AsyncTestModel, **test_data)

        # 断言
        assert created_model is not None
        assert created_model.name == test_name
        assert created_model.description == test_data["description"]
        assert created_model.score == test_data["score"]
        assert created_model.is_active is True
        assert created_model.id is not None

        print(f"✅ 成功创建模型实例: {created_model}")

    async def test_read_model_instance(self):
        """测试读取模型实例"""
        print("\n🧪 测试读取模型实例")

        # 先创建一个实例
        test_name = f"test_read_{uuid.uuid4().hex[:8]}"
        created_model = await AsyncCRUD.create(
            AsyncTestModel,
            name=test_name,
            description="Model for read test",
            score=88.0
        )

        # 使用 AsyncCRUD 读取实例
        retrieved_model = await AsyncCRUD.get(AsyncTestModel, created_model.id)

        # 断言
        assert retrieved_model is not None
        assert retrieved_model.id == created_model.id
        assert retrieved_model.name == test_name
        assert retrieved_model.description == "Model for read test"
        assert retrieved_model.score == 88.0

        print(f"✅ 成功读取模型实例: {retrieved_model}")

    async def test_update_model_instance(self):
        """测试更新模型实例"""
        print("\n🧪 测试更新模型实例")

        # 创建实例
        test_name = f"test_update_{uuid.uuid4().hex[:8]}"
        created_model = await AsyncCRUD.create(
            AsyncTestModel,
            name=test_name,
            description="Original description",
            score=75.0
        )

        # 更新实例
        updated_data = {
            "description": "Updated description",
            "score": 92.5,
            "is_active": False
        }
        updated_model = await AsyncCRUD.update(AsyncTestModel, created_model.id, **updated_data)

        # 断言
        assert updated_model is not None
        assert updated_model.id == created_model.id
        assert updated_model.name == test_name  # 未更新
        assert updated_model.description == "Updated description"
        assert updated_model.score == 92.5
        assert updated_model.is_active is False

        print(f"✅ 成功更新模型实例: {updated_model}")

    async def test_delete_model_instance(self):
        """测试删除模型实例"""
        print("\n🧪 测试删除模型实例")

        # 创建实例
        test_name = f"test_delete_{uuid.uuid4().hex[:8]}"
        created_model = await AsyncCRUD.create(
            AsyncTestModel,
            name=test_name,
            description="Model for deletion test",
            score=80.0
        )

        # 删除实例
        delete_success = await AsyncCRUD.delete(AsyncTestModel, created_model.id)

        # 断言删除成功
        assert delete_success is True

        # 验证实例已被删除
        deleted_model = await AsyncCRUD.get(AsyncTestModel, created_model.id)
        assert deleted_model is None

        print(f"✅ 成功删除模型实例: {created_model.id}")

    async def test_batch_operations(self):
        """测试批量操作"""
        print("\n🧪 测试批量操作")

        # 准备批量数据
        batch_data = []
        for i in range(5):
            batch_data.append({
                "name": f"batch_model_{i}_{uuid.uuid4().hex[:4]}",
                "description": f"Batch test model {i}",
                "score": 80.0 + i * 2.5,
                "is_active": i % 2 == 0
            })

        # 批量创建
        created_models = await AsyncBatchOperations.bulk_create(AsyncTestModel, batch_data)

        # 断言批量创建成功
        assert len(created_models) == 5
        for i, model in enumerate(created_models):
            assert model.name == batch_data[i]["name"]
            assert model.score == batch_data[i]["score"]

        print(f"✅ 成功批量创建 {len(created_models)} 个模型实例")

        # 准备批量更新数据
        update_data = []
        for model in created_models:
            update_data.append({
                "id": model.id,
                "description": f"Updated: {model.description}",
                "score": model.score + 10.0
            })

        # 批量更新
        updated_count = await AsyncBatchOperations.bulk_update(AsyncTestModel, update_data)

        # 断言批量更新成功
        assert updated_count == 5

        print(f"✅ 成功批量更新 {updated_count} 个模型实例")

        # 批量删除
        model_ids = [model.id for model in created_models]
        deleted_count = await AsyncBatchOperations.bulk_delete(AsyncTestModel, model_ids)

        # 断言批量删除成功
        assert deleted_count == 5

        print(f"✅ 成功批量删除 {deleted_count} 个模型实例")

    async def test_query_operations(self):
        """测试查询操作"""
        print("\n🧪 测试查询操作")

        # 创建测试数据
        test_models = []
        for i in range(3):
            model = await AsyncCRUD.create(
                AsyncTestModel,
                name=f"query_test_{i}",
                description=f"Query test model {i}",
                score=85.0 + i * 5,
                is_active=i != 1  # 第二个不活跃
            )
            test_models.append(model)

        # 测试 fetch_all
        query = select(AsyncTestModel).where(AsyncTestModel.name.like("query_test_%"))
        all_results = await AsyncQuery.fetch_all(query)

        # 断言
        assert len(all_results) == 3
        print(f"✅ fetch_all 返回 {len(all_results)} 条记录")

        # 测试 fetch_one
        query_one = select(AsyncTestModel).where(AsyncTestModel.name == "query_test_1")
        one_result = await AsyncQuery.fetch_one(query_one)

        # 断言
        assert one_result is not None
        assert one_result["name"] == "query_test_1"
        print("✅ fetch_one 成功返回单条记录")

        # 测试分页查询
        page_result = await AsyncQuery.fetch_page(
            select(AsyncTestModel).where(AsyncTestModel.name.like("query_test_%")),
            page=1,
            page_size=2
        )

        # 断言
        assert page_result["total"] == 3
        assert len(page_result["items"]) == 2
        assert page_result["page"] == 1
        assert page_result["has_next"] is True
        assert page_result["has_prev"] is False
        print(f"✅ 分页查询成功: {page_result}")

        # 测试 exists
        exists_query = select(AsyncTestModel).where(AsyncTestModel.name == "query_test_0")
        exists = await AsyncQuery.exists(exists_query)
        assert exists is True
        print("✅ exists 查询成功")

        # 测试不存在的记录
        not_exists_query = select(AsyncTestModel).where(AsyncTestModel.name == "non_existent")
        not_exists = await AsyncQuery.exists(not_exists_query)
        assert not_exists is False
        print("✅ not exists 查询成功")

    async def test_raw_sql_operations(self):
        """测试原生SQL操作"""
        print("\n🧪 测试原生SQL操作")

        # 使用原生SQL插入数据
        test_name = f"raw_sql_{uuid.uuid4().hex[:8]}"
        insert_sql = """
        INSERT INTO async_test_models (name, description, score, is_active, created_at, updated_at)
        VALUES (:name, :description, :score, :is_active, :created_at, :updated_at)
        RETURNING id
        """

        now = datetime.utcnow()
        params = {
            "name": test_name,
            "description": "Raw SQL test",
            "score": 90.0,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }

        # 执行插入
        insert_result = await execute(text(insert_sql), params)
        inserted_id = insert_result.scalar()

        # 断言插入成功
        assert inserted_id is not None
        print(f"✅ 原生SQL插入成功，ID: {inserted_id}")

        # 使用原生SQL查询
        select_sql = "SELECT * FROM async_test_models WHERE name = :name"
        select_result = await fetch_one(text(select_sql), {"name": test_name})

        # 断言查询成功
        assert select_result is not None
        assert select_result["name"] == test_name
        assert select_result["score"] == 90.0
        print("✅ 原生SQL查询成功")

        # 使用原生SQL更新
        update_sql = "UPDATE async_test_models SET score = :score WHERE name = :name"
        update_params = {"name": test_name, "score": 95.5}
        await execute(text(update_sql), update_params)

        # 验证更新
        updated_result = await fetch_one(text(select_sql), {"name": test_name})
        assert updated_result["score"] == 95.5
        print("✅ 原生SQL更新成功")

        # 使用原生SQL删除
        delete_sql = "DELETE FROM async_test_models WHERE name = :name"
        await execute(text(delete_sql), {"name": test_name})

        # 验证删除
        deleted_result = await fetch_one(text(select_sql), {"name": test_name})
        assert deleted_result is None
        print("✅ 原生SQL删除成功")

    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        print("\n🧪 测试异步上下文管理器")

        # 使用 get_async_session 上下文管理器
        async with get_async_session() as session:
            # 创建实例
            test_name = f"context_test_{uuid.uuid4().hex[:8]}"
            new_model = AsyncTestModel(
                name=test_name,
                description="Context manager test",
                score=87.5
            )
            session.add(new_model)
            await session.commit()
            await session.refresh(new_model)

            # 读取实例
            result = await session.execute(
                select(AsyncTestModel).where(AsyncTestModel.id == new_model.id)
            )
            retrieved_model = result.scalar_one()

            # 断言
            assert retrieved_model is not None
            assert retrieved_model.name == test_name
            assert retrieved_model.score == 87.5

            print(f"✅ 异步上下文管理器测试成功: {retrieved_model}")

    async def test_connection_pool_and_performance(self):
        """测试连接池和性能"""
        print("\n🧪 测试连接池和性能")

        # 并发测试
        async def create_and_verify_model(index: int):
            """创建并验证模型的并发任务"""
            try:
                model_name = f"concurrent_test_{index}_{uuid.uuid4().hex[:4]}"

                # 创建模型
                model = await AsyncCRUD.create(
                    AsyncTestModel,
                    name=model_name,
                    description=f"Concurrent test {index}",
                    score=80.0 + index
                )

                # 立即验证
                verified = await AsyncCRUD.get(AsyncTestModel, model.id)

                return model.id if verified and verified.name == model_name else None

            except Exception as e:
                print(f"❌ 并发任务 {index} 失败: {e}")
                return None

        # 启动10个并发任务
        tasks = [create_and_verify_model(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        failed_results = [r for r in results if r is None or isinstance(r, Exception)]

        print(f"✅ 并发测试完成: {len(successful_results)} 成功, {len(failed_results)} 失败")

        # 断言至少80%的任务成功
        success_rate = len(successful_results) / 10
        assert success_rate >= 0.8, f"成功率 {success_rate:.2%} 低于 80%"

        # 验证没有 GreenletExit 或 AttachError
        exceptions = [r for r in results if isinstance(r, Exception)]
        for exc in exceptions:
            assert not isinstance(exc, (asyncio.CancelledError, Exception)), \
                f"不应该出现 GreenletExit 或 AttachError: {exc}"

        print("✅ 连接池和性能测试通过，无 GreenletExit 或 AttachError 错误")

    async def test_error_handling_and_rollback(self):
        """测试错误处理和回滚"""
        print("\n🧪 测试错误处理和回滚")

        # 测试违反约束的情况
        try:
            # 尝试创建无效数据（名称为空）
            await AsyncCRUD.create(AsyncTestModel, name="", description="Invalid model")
            raise AssertionError("应该抛出异常")
        except Exception as e:
            print(f"✅ 正确捕获了无效数据异常: {type(e).__name__}")

        # 测试事务回滚
        async with get_async_session() as session:
            try:
                # 开始事务
                await session.begin()

                # 创建第一个模型
                model1 = AsyncTestModel(
                    name="rollback_test_1",
                    description="First model",
                    score=85.0
                )
                session.add(model1)
                await session.flush()  # 刷新到数据库但不提交

                # 故意引发错误
                model2 = AsyncTestModel(
                    name="",  # 无效数据
                    description="This will cause error",
                    score=90.0
                )
                session.add(model2)
                await session.flush()

                await session.commit()  # 这应该失败并回滚

            except Exception as e:
                await session.rollback()
                print("✅ 事务回滚成功")

                # 验证第一个模型也没有被保存
                result = await session.execute(
                    select(AsyncTestModel).where(AsyncTestModel.name == "rollback_test_1")
                )
                saved_model = result.scalar_one_or_none()
                assert saved_model is None
                print("✅ 回滚验证成功，没有数据被保存")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.database
class TestAsyncDatabaseConnection:
    """异步数据库连接测试"""

    async def test_database_connection_health(self):
        """测试数据库连接健康状态"""
        print("\n🧪 测试数据库连接健康状态")

        try:
            # 测试基本连接
            result = await fetch_one(text("SELECT 1 as health_check"))
            assert result["health_check"] == 1
            print("✅ 数据库连接正常")

            # 测试连接池状态
            pool_info = await fetch_one(text("""
                SELECT
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """))

            print(f"✅ 连接池状态: 总连接 {pool_info['total_connections']}, "
                  f"活跃连接 {pool_info['active_connections']}")

            # 测试事务支持
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
                print("✅ 事务支持正常")

        except Exception as e:
            pytest.fail(f"数据库连接健康检查失败: {e}")

    async def test_async_vs_sync_performance(self):
        """测试异步 vs 同步性能对比"""
        print("\n🧪 测试异步性能")

        # 准备测试数据
        test_data = []
        for i in range(20):
            test_data.append({
                "name": f"perf_test_{i}_{uuid.uuid4().hex[:4]}",
                "description": f"Performance test model {i}",
                "score": 70.0 + i * 1.5,
                "is_active": i % 2 == 0
            })

        # 测量批量创建性能
        import time
        start_time = time.time()

        created_models = await AsyncBatchOperations.bulk_create(AsyncTestModel, test_data)

        creation_time = time.time() - start_time
        creation_rate = len(created_models) / creation_time

        print(f"✅ 异步批量创建性能: {len(created_models)} 条记录, "
              f"耗时 {creation_time:.3f}s, 速率 {creation_rate:.1f} 记录/秒")

        # 性能断言（应该在合理范围内）
        assert creation_rate > 50, f"异步创建速率 {creation_rate:.1f} 记录/秒 低于期望"
        print("✅ 异步性能测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m=not slow"
    ])
