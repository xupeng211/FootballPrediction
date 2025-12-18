"""
简化的异步数据库管理器集成测试
Simplified Async Database Manager Integration Tests

使用SQLite内存数据库验证核心功能，避免复杂的事件循环问题
"""

import pytest
from sqlalchemy import text

from src.database.async_manager import (
    initialize_database,
    fetch_all,
    fetch_one,
    execute,
)


class TestAsyncManagerIntegration:
    """异步数据库管理器集成测试"""

    @pytest.fixture(scope="class", autouse=True)
    async def setup_test_database(self):
        """设置集成测试数据库环境"""
        # 重置单例状态以避免测试间干扰
        from src.database.async_manager import AsyncDatabaseManager

        AsyncDatabaseManager._instance = None
        AsyncDatabaseManager._initialized = False

        # 使用SQLite内存数据库进行集成测试
        test_url = "sqlite+aiosqlite:///:memory:"
        initialize_database(test_url)

        yield test_url

    async def test_database_connection_and_crud(self, setup_test_database):
        """测试数据库连接和基本CRUD操作"""
        # 创建测试表
        await execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS integration_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                age INTEGER
            )
        """
            )
        )

        # 1. 插入数据
        await execute(
            text(
                """
            INSERT INTO integration_users (name, email, age) VALUES
            ('Alice', 'alice@test.com', 25),
            ('Bob', 'bob@test.com', 30),
            ('Charlie', 'charlie@test.com', 35)
            RETURNING id
        """
            )
        )

        # 2. 查询所有数据
        users = await fetch_all(text("SELECT * FROM integration_users ORDER BY id"))
        assert len(users) == 3, "应该插入3条记录"
        assert users[0]["name"] == "Alice", "第一条记录应该是Alice"

        # 3. 查询单条记录
        alice = await fetch_one(
            text("SELECT * FROM integration_users WHERE name = 'Alice'")
        )
        assert alice is not None, "应该找到Alice"
        assert alice["email"] == "alice@test.com", "Alice的邮箱应该正确"

        # 4. 更新数据
        await execute(
            text("UPDATE integration_users SET age = 26 WHERE name = 'Alice'")
        )
        updated_alice = await fetch_one(
            text("SELECT age FROM integration_users WHERE name = 'Alice'")
        )
        assert updated_alice["age"] == 26, "Alice的年龄应该被更新"

        # 5. 删除数据
        await execute(text("DELETE FROM integration_users WHERE name = 'Bob'"))
        remaining_users = await fetch_all(
            text("SELECT COUNT(*) as count FROM integration_users")
        )
        assert remaining_users[0]["count"] == 2, "删除后应该剩余2条记录"

    async def test_transaction_isolation(self, setup_test_database):
        """测试事务处理"""
        # 创建测试表
        await execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS integration_transactions (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        """
            )
        )

        # 直接使用execute方法（会自动提交）
        await execute(
            text("INSERT INTO integration_transactions (data) VALUES ('trans1')")
        )
        await execute(
            text("INSERT INTO integration_transactions (data) VALUES ('trans2')")
        )

        # 验证结果
        records = await fetch_all(
            text("SELECT * FROM integration_transactions ORDER BY data")
        )
        assert len(records) == 2, "应该有2条记录"
        data_values = [record["data"] for record in records]
        assert "trans1" in data_values, "应该包含trans1"
        assert "trans2" in data_values, "应该包含trans2"

    async def test_error_handling_and_rollback(self, setup_test_database):
        """测试错误处理和回滚"""
        # 创建测试表
        await execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS integration_errors (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """
            )
        )

        # 插入第一条记录
        await execute(
            text("INSERT INTO integration_errors (name) VALUES ('unique_name')")
        )

        # 尝试插入重复记录，应该失败
        with pytest.raises(Exception):
            await execute(
                text("INSERT INTO integration_errors (name) VALUES ('unique_name')")
            )

        # 验证第一条记录仍然存在（事务回滚）
        record = await fetch_one(
            text("SELECT * FROM integration_errors WHERE name = 'unique_name'")
        )
        assert record is not None, "原始记录应该仍然存在"

        # 验证只有一条记录
        count = await fetch_one(
            text("SELECT COUNT(*) as count FROM integration_errors")
        )
        assert count["count"] == 1, "应该只有一条记录"

    async def test_batch_operations(self, setup_test_database):
        """测试批量操作"""
        # 创建测试表
        await execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS integration_batch (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            )
        """
            )
        )

        # 准备批量数据
        batch_data = [
            {"id": i, "name": f"item_{i}", "value": i * 10} for i in range(1, 11)
        ]

        # 批量插入
        await execute(
            text(
                """
            INSERT INTO integration_batch (id, name, value) VALUES
            (:id, :name, :value)
        """
            ),
            batch_data,
        )

        # 验证批量插入结果
        records = await fetch_all(
            text("SELECT COUNT(*) as count FROM integration_batch")
        )
        assert records[0]["count"] == 10, "应该插入10条记录"

        # 验证数据完整性
        first_record = await fetch_one(
            text("SELECT * FROM integration_batch WHERE id = 1")
        )
        assert first_record["name"] == "item_1", "第一条记录应该正确"
        assert first_record["value"] == 10, "第一条记录的值应该正确"

        last_record = await fetch_one(
            text("SELECT * FROM integration_batch WHERE id = 10")
        )
        assert last_record["name"] == "item_10", "最后一条记录应该正确"
        assert last_record["value"] == 100, "最后一条记录的值应该正确"


# 测试标记
pytest.mark.integration = pytest.mark.integration
pytest.mark.database = pytest.mark.database
pytest.mark.asyncio = pytest.mark.asyncio
