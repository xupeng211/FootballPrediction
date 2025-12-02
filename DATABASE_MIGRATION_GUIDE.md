# 数据库连接层重构指南
# Database Connection Layer Refactoring Guide

## 📋 概述 (Overview)

本次重构实现了 **"One Way to do it"** 原则，统一了数据库会话管理接口，解决了 `definitions.py` 和 `base.py` 混用导致的 Session 管理风险。

## ✨ 新架构优势

- ✅ **单一入口**: 统一的 `get_db_session()` 上下文管理器
- ✅ **完全异步**: 所有操作使用 async/await，无同步阻塞
- ✅ **类型安全**: 完整的类型注解和 IDE 支持
- ✅ **健康检查**: 内置连接健康监控
- ✅ **向后兼容**: 保留旧接口但标记为弃用

---

## 🚀 快速开始

### Step 1: 安装依赖

```bash
# 在容器内执行
pip install curl_cffi>=0.5.10 asyncpg sqlalchemy[asyncio] --upgrade
```

### Step 2: 初始化数据库管理器

在应用启动时（如 `main.py`）初始化一次：

```python
# src/main.py
from src.database.async_manager import initialize_database

# 应用启动时调用
initialize_database()
```

### Step 3: 使用新的会话接口

#### 在 FastAPI 路由中使用（推荐）

```python
# src/api/predictions/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.async_manager import get_async_db_session
from src.database.models.match import Match

router = APIRouter()

@router.get("/matches/")
async def get_matches(
    session: AsyncSession = Depends(get_async_db_session)
):
    """获取比赛列表"""
    result = await session.execute(select(Match))
    matches = result.scalars().all()
    return matches
```

#### 在爬虫脚本中使用

```python
# scripts/crawl_fotmob.py
import asyncio
from src.database.async_manager import get_db_session
from src.database.models.match import Match

async def crawl_and_save():
    """爬取数据并保存到数据库"""
    async with get_db_session() as session:
        # 1. 爬取数据
        from src.data.collectors.fotmob_collector import FotmobCollector
        collector = FotmobCollector()
        data = await collector.collect()

        # 2. 保存到数据库
        # ... 使用 session 进行 ORM 操作 ...

        await session.commit()

if __name__ == "__main__":
    asyncio.run(crawl_and_save())
```

#### 在脚本和工具中使用

```python
# scripts/my_script.py
import asyncio
from src.database.async_manager import get_db_session

async def my_script():
    """脚本示例"""
    async with get_db_session() as session:
        # 执行 SQL
        from sqlalchemy import text
        result = await session.execute(text("SELECT COUNT(*) FROM matches"))
        count = result.scalar()
        print(f"数据库中有 {count} 条比赛记录")

asyncio.run(my_script())
```

---

## 📚 API 参考

### 核心函数

#### `initialize_database(database_url=None, **kwargs)`

初始化数据库管理器（应用启动时调用一次）

**参数**:
- `database_url`: 数据库连接URL，如果为None则从环境变量读取
- `**kwargs`: 额外的引擎配置参数

**示例**:
```python
# 使用自定义配置
initialize_database(
    database_url="postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,
    max_overflow=30,
)
```

#### `get_db_session() -> AsyncGenerator[AsyncSession, None]`

获取异步数据库会话（上下文管理器）

**推荐用于**: 脚本、爬虫、工具等

**示例**:
```python
async with get_db_session() as session:
    result = await session.execute(select(Match))
    matches = result.scalars().all()
```

#### `get_async_db_session() -> AsyncGenerator[AsyncSession, None]`

FastAPI 依赖注入函数

**推荐用于**: FastAPI 路由

**示例**:
```python
@router.get("/")
async def handler(
    session: AsyncSession = Depends(get_async_db_session)
):
    result = await session.execute(select(Match))
    return result.scalars().all()
```

### 健康检查

```python
from src.database.async_manager import get_database_manager

manager = get_database_manager()
health = await manager.check_connection()

print(health)
# 输出:
# {
#     "status": "healthy",
#     "message": "连接正常",
#     "response_time_ms": 12,
#     "database_url": "postgresql+asyncpg://..."
# }
```

---

## 🔄 迁移指南

### 从旧接口迁移

#### 旧代码（已弃用）:

```python
# ❌ 旧方式 - 不要使用
from src.database.connection import get_async_db

async def old_handler(session: AsyncSession = Depends(get_async_db)):
    pass
```

#### 新代码:

```python
# ✅ 新方式 - 推荐使用
from src.database.async_manager import get_async_db_session

async def new_handler(session: AsyncSession = Depends(get_async_db_session)):
    pass
```

### 逐步迁移策略

1. **第一步**: 在 `main.py` 中添加 `initialize_database()` 调用
2. **第二步**: 更新 FastAPI 路由使用 `get_async_db_session`
3. **第三步**: 更新脚本使用 `get_db_session()`
4. **第四步**: 移除旧的 `from src.database.connection import`

---

## ⚠️ 弃用警告

以下接口已标记为弃用，但仍可用于向后兼容：

| 旧接口 | 新接口 | 状态 |
|--------|--------|------|
| `from src.database.connection import get_async_db` | `from src.database.async_manager import get_async_db_session` | ⚠️ 弃用 |
| `from src.database.base import get_async_db` | `from src.database.async_manager import get_async_db_session` | ⚠️ 弃用 |

使用弃用接口会收到 `DeprecationWarning`，建议尽快迁移。

---

## 🐛 故障排除

### 问题 1: "AsyncDatabaseManager 未初始化"

**错误**:
```
RuntimeError: AsyncDatabaseManager 未初始化！请在应用启动时调用 initialize_database()
```

**解决方案**: 在 `main.py` 中添加：
```python
from src.database.async_manager import initialize_database

initialize_database()
```

### 问题 2: "ModuleNotFoundError: No module named 'asyncpg'"

**错误**:
```
ModuleNotFoundError: No module named 'asyncpg'
```

**解决方案**: 安装依赖：
```bash
pip install asyncpg sqlalchemy[asyncio] --upgrade
```

### 问题 3: "curl_cffi not found"

**错误**:
```
ImportError: curl_cffi is required
```

**解决方案**: 安装依赖：
```bash
pip install curl_cffi>=0.5.10 --upgrade
```

### 问题 4: 数据库连接失败

**错误**:
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**解决方案**:
1. 检查数据库是否启动: `docker-compose ps`
2. 检查连接URL: `echo $DATABASE_URL`
3. 运行健康检查: `python scripts/smoke_test_db_crawler.py`

---

## 🧪 测试

运行冒烟测试验证重构是否成功：

```bash
# 进入容器
make shell

# 运行测试
python scripts/smoke_test_db_crawler.py
```

预期输出：
```
🚀 冒烟测试开始 - Database & Crawler Integration
==========================================
✅ Test 1: 检查模块导入 - PASS
✅ Test 2: 测试 AsyncDatabaseManager - PASS
✅ Test 3: 测试数据库会话获取 - PASS
✅ Test 4: 测试 FotMobCollector - PASS
✅ Test 5: 测试 FotMob详情收集器 - PASS

🎉 所有测试通过！数据库和爬虫系统已准备就绪。
```

---

## 📁 文件结构

重构后的文件结构：

```
src/database/
├── async_manager.py       # ⭐ 新的统一接口（推荐使用）
├── base.py               # ⚠️ 基础模型，保留但标记弃用
├── connection.py         # ⚠️ 向后兼容层，标记弃用
├── definitions.py        # ⚠️ 旧管理器，标记弃用
└── models/               # ✅ 数据模型（无需修改）
    ├── match.py
    ├── team.py
    └── ...
```

---

## 📞 支持

如果在迁移过程中遇到问题：

1. 查看错误日志
2. 运行 `python scripts/smoke_test_db_crawler.py` 诊断
3. 检查 [故障排除](#-故障排除) 部分
4. 查看 [SQLAlchemy 文档](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

## ✅ 检查清单

- [ ] 安装所有依赖: `pip install curl_cffi asyncpg sqlalchemy[asyncio]`
- [ ] 在 `main.py` 中调用 `initialize_database()`
- [ ] 更新 FastAPI 路由使用 `get_async_db_session`
- [ ] 更新脚本使用 `get_db_session()`
- [ ] 运行冒烟测试验证
- [ ] 收到0个弃用警告

---

**🎉 恭喜！数据库连接层重构完成！**
