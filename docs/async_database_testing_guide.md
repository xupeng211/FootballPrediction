# 异步数据库测试指南

## 🎯 概述

本指南解决项目中异步数据库测试的常见问题，特别是 `AttributeError: 'async_generator' object has no attribute 'execute'` 错误。

## ❌ 常见问题

### 问题1：错误的Fixture定义

```python
# ❌ 错误写法
@pytest.fixture  # 错误：应该用 @pytest_asyncio.fixture
async def async_session():
    async with get_async_session() as session:
        yield session
```

### 问题2：缺失装饰器

```python
# ❌ 错误写法
async def test_something(async_session):  # 缺少 @pytest.mark.asyncio
    result = await async_session.execute(text("SELECT 1"))
```

### 问题3：同步/异步混用

```python
# ❌ 错误写法
def test_mixed_usage(async_session):  # 同步函数使用异步fixture
    result = async_session.execute(text("SELECT 1"))  # 缺少 await
```

## ✅ 正确的解决方案

### 1. 标准异步数据库测试模板

```python
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from src.database.connection import DatabaseManager

class AsyncDatabaseTestTemplate:
    """标准异步数据库测试模板"""

    @pytest_asyncio.fixture
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """标准异步数据库会话 fixture"""
        db_manager = DatabaseManager()

        # 确保数据库连接已初始化
        if not db_manager.is_initialized():
            await db_manager.initialize()

        try:
            async with db_manager.get_async_session() as session:
                yield session
        finally:
            # 清理工作由 async with 自动处理
            pass

    @pytest.mark.asyncio
    async def test_example(self, async_session: AsyncSession):
        """测试示例"""
        result = await async_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

### 2. 关键修复点

#### A. Fixture装饰器
```python
# ✅ 正确
@pytest_asyncio.fixture  # 必须使用 pytest_asyncio.fixture
async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
    ...
```

#### B. 测试函数装饰器
```python
# ✅ 正确
@pytest.mark.asyncio  # 必须添加此装饰器
async def test_function(self, async_session: AsyncSession):
    ...
```

#### C. 数据库操作
```python
# ✅ 正确
result = await async_session.execute(text("SELECT 1"))
await async_session.commit()
```

#### D. Session管理
```python
# ✅ 正确
async with db_manager.get_async_session() as session:
    yield session  # 会话自动管理
```

## 🔧 实际应用步骤

### 步骤1：修复Fixture定义

在 `tests/test_database_performance_optimization.py` 第556行：

```python
# 原始代码（错误）
@pytest.fixture
async def async_session():
    async with get_async_session() as session:
        yield session

# 修复后
@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    db_manager = DatabaseManager()
    if not db_manager.is_initialized():
        await db_manager.initialize()
    async with db_manager.get_async_session() as session:
        yield session
```

### 步骤2：继承标准模板

```python
from templates.async_database_test_template import AsyncDatabaseTestTemplate

class TestDatabaseIndexes(AsyncDatabaseTestTemplate):
    """继承模板类，获得标准的异步测试能力"""

    @pytest.mark.asyncio
    async def test_index_existence(self, async_session: AsyncSession):
        # 你的测试代码
        pass
```

### 步骤3：验证修复

```bash
pytest tests/test_database_performance_optimization.py::TestDatabaseIndexes::test_index_existence -v
```

## 📁 文件结构

```
FootballPrediction/
├── templates/
│   └── async_database_test_template.py  # 标准模板
├── examples/
│   └── refactored_test_index_existence.py  # 重构示例
├── docs/
│   └── async_database_testing_guide.md  # 本指南
└── tests/
    └── test_database_performance_optimization.py  # 需要修复的文件
```

## 🚀 使用模板的好处

1. **统一性**: 所有异步数据库测试使用相同的模式
2. **可维护性**: 统一的错误处理和资源管理
3. **可读性**: 清晰的代码结构和注释
4. **可靠性**: 经过验证的异步模式，避免常见错误
5. **扩展性**: 容易添加新的测试方法和fixture

## 🛡️ 最佳实践

### 1. Fixture设计原则

```python
@pytest_asyncio.fixture
async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
    """
    原则：
    1. 使用 @pytest_asyncio.fixture
    2. 添加正确的类型注解
    3. 使用 async with 管理资源
    4. 确保数据库初始化
    """
    db_manager = DatabaseManager()
    if not db_manager.is_initialized():
        await db_manager.initialize()
    async with db_manager.get_async_session() as session:
        yield session
```

### 2. 测试函数设计

```python
@pytest.mark.asyncio
async def test_something(self, async_session: AsyncSession):
    """
    原则：
    1. 必须添加 @pytest.mark.asyncio
    2. 函数必须是 async def
    3. 所有数据库操作前加 await
    4. 使用类型注解提高代码质量
    """
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
```

### 3. 错误处理

```python
@pytest.mark.asyncio
async def test_with_error_handling(self, async_session: AsyncSession):
    """正确的错误处理模式"""
    from sqlalchemy.exc import SQLAlchemyError

    try:
        result = await async_session.execute(text("SELECT * FROM non_existent"))
        assert False, "应该抛出异常"
    except SQLAlchemyError as e:
        # 验证预期的异常
        assert "non_existent" in str(e).lower()
```

## 📊 性能考虑

### 1. 连接池管理

```python
# ✅ 推荐：复用连接管理器
@pytest_asyncio.fixture
async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
    db_manager = DatabaseManager()  # 复用现有管理器
    async with db_manager.get_async_session() as session:
        yield session
```

### 2. 事务管理

```python
# ✅ 推荐：测试专用事务回滚fixture
@pytest_asyncio.fixture
async def async_transaction_session(self) -> AsyncGenerator[AsyncSession, None]:
    """带事务回滚的session，测试数据不会持久化"""
    db_manager = DatabaseManager()
    async with db_manager.get_async_session() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()
```

## 🔄 迁移清单

- [ ] 识别所有使用 `@pytest.fixture` + `async def` 的fixture
- [ ] 替换为 `@pytest_asyncio.fixture`
- [ ] 检查所有异步测试函数是否有 `@pytest.mark.asyncio`
- [ ] 验证所有 `session.execute()` 调用都有 `await`
- [ ] 更新类型注解
- [ ] 继承标准模板类（可选）
- [ ] 运行测试验证修复效果

## 🎯 验证命令

```bash
# 运行特定测试
pytest tests/test_database_performance_optimization.py::TestDatabasePartitioning::test_matches_partition_insertion -v

# 运行整个测试类
pytest tests/test_database_performance_optimization.py::TestDatabaseIndexes -v

# 运行所有数据库测试
pytest tests/test_database_*.py -v

# 显示详细错误信息
pytest tests/test_database_performance_optimization.py -v --tb=short
```

完成这些步骤后，您的异步数据库测试将完全兼容 SQLAlchemy 2.0 + asyncio，不再出现 `AttributeError` 错误。
