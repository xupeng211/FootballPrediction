# 数据库接口统一代码示例
# Database Interface Unification Code Examples

本文档展示如何将旧的同步数据库接口迁移到新的异步接口。

---

## 🔄 基本模式转换

### 示例 1: 简单查询操作

#### 旧版本（同步）:
```python
# src/services/user_service.py
from src.database.connection import DatabaseManager

def get_user(user_id: int):
    """获取用户信息 - 同步版本"""
    db_manager = DatabaseManager()
    with db_manager.get_session() as session:
        # 同步查询
        user = session.execute(
            "SELECT * FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
    return user
```

#### 新版本（异步）:
```python
# src/services/user_service.py
from src.database.async_manager import get_db_session
from sqlalchemy import text

async def get_user(user_id: int):
    """获取用户信息 - 异步版本"""
    async with get_db_session() as session:
        # 异步查询
        result = await session.execute(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user = result.fetchone()
    return user
```

#### 更简洁的异步版本（使用便捷方法）:
```python
# src/services/user_service.py
from src.database.async_manager import fetch_one
from sqlalchemy import text

async def get_user(user_id: int):
    """获取用户信息 - 简洁异步版本"""
    return await fetch_one(
        text("SELECT * FROM users WHERE id = :user_id"),
        {"user_id": user_id}
    )
```

---

### 示例 2: FastAPI 路由处理

#### 旧版本（同步）:
```python
# src/api/matches.py
from fastapi import APIRouter, Depends, HTTPException
from src.database.connection import get_async_session
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/matches/{match_id}")
def get_match(match_id: int, session: Session = Depends(get_async_session)):
    """获取比赛信息 - 同步版本（不推荐）"""
    match = session.execute(
        "SELECT * FROM matches WHERE id = :match_id",
        {"match_id": match_id}
    ).fetchone()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return match
```

#### 新版本（异步）:
```python
# src/api/matches.py
from fastapi import APIRouter, Depends, HTTPException
from src.database.async_manager import get_async_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

router = APIRouter()

@router.get("/matches/{match_id}")
async def get_match(match_id: int, session: AsyncSession = Depends(get_async_db_session)):
    """获取比赛信息 - 异步版本"""
    result = await session.execute(
        text("SELECT * FROM matches WHERE id = :match_id"),
        {"match_id": match_id}
    )
    match = result.fetchone()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return dict(match._mapping)
```

#### 最佳实践版本（使用ORM）:
```python
# src/api/matches.py
from fastapi import APIRouter, Depends, HTTPException
from src.database.async_manager import get_async_db_session
from src.database.models import Match
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()

@router.get("/matches/{match_id}")
async def get_match(match_id: int, session: AsyncSession = Depends(get_async_db_session)):
    """获取比赛信息 - ORM异步版本（推荐）"""
    result = await session.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return match
```

---

### 示例 3: 数据收集器

#### 旧版本（同步）:
```python
# src/collectors/data_collector.py
from src.database.connection import DatabaseManager

class DataCollector:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def save_match_data(self, match_data: dict):
        """保存比赛数据 - 同步版本"""
        with self.db_manager.get_session() as session:
            session.execute(
                "INSERT INTO matches (id, home_team, away_team, date) "
                "VALUES (:id, :home_team, :away_team, :date)",
                match_data
            )
            session.commit()
```

#### 新版本（异步）:
```python
# src/collectors/data_collector.py
from src.database.async_manager import get_db_session, execute
from sqlalchemy import text

class DataCollector:
    async def save_match_data(self, match_data: dict):
        """保存比赛数据 - 异步版本"""
        await execute(
            text("""
                INSERT INTO matches (id, home_team, away_team, date)
                VALUES (:id, :home_team, :away_team, :date)
            """),
            match_data
        )

    async def save_match_data_with_session(self, match_data: dict):
        """保存比赛数据 - 使用会话管理器"""
        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO matches (id, home_team, away_team, date)
                    VALUES (:id, :home_team, :away_team, :date)
                """),
                match_data
            )
            # 自动提交（会话管理器处理）
```

---

### 示例 4: CQRS 命令处理器

#### 旧版本（同步）:
```python
# src/cqrs/commands.py
from src.database.connection import get_session

class CreatePredictionCommand:
    def __init__(self, match_id: int, prediction_data: dict):
        self.match_id = match_id
        self.prediction_data = prediction_data

def execute_create_prediction(command: CreatePredictionCommand):
    """执行创建预测命令 - 同步版本"""
    with get_session() as session:
        # 创建预测记录
        session.execute(
            "INSERT INTO predictions (match_id, prediction, confidence) "
            "VALUES (:match_id, :prediction, :confidence)",
            {
                "match_id": command.match_id,
                "prediction": command.prediction_data["prediction"],
                "confidence": command.prediction_data["confidence"]
            }
        )
        session.commit()
```

#### 新版本（异步）:
```python
# src/cqrs/commands.py
from src.database.async_manager import get_db_session, execute
from sqlalchemy import text

class CreatePredictionCommand:
    def __init__(self, match_id: int, prediction_data: dict):
        self.match_id = match_id
        self.prediction_data = prediction_data

async def execute_create_prediction(command: CreatePredictionCommand):
    """执行创建预测命令 - 异步版本"""
    await execute(
        text("""
            INSERT INTO predictions (match_id, prediction, confidence)
            VALUES (:match_id, :prediction, :confidence)
        """),
        {
            "match_id": command.match_id,
            "prediction": command.prediction_data["prediction"],
            "confidence": command.prediction_data["confidence"]
        }
    )

async def execute_create_prediction_with_session(command: CreatePredictionCommand):
    """执行创建预测命令 - 使用会话管理器"""
    async with get_db_session() as session:
        await session.execute(
            text("""
                INSERT INTO predictions (match_id, prediction, confidence)
                VALUES (:match_id, :prediction, :confidence)
            """),
            {
                "match_id": command.match_id,
                "prediction": command.prediction_data["prediction"],
                "confidence": command.prediction_data["confidence"]
            }
        )
        # 自动提交
```

---

### 示例 5: 批量操作

#### 旧版本（同步）:
```python
# src/services/batch_service.py
from src.database.connection import DatabaseManager

class BatchService:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def save_multiple_predictions(self, predictions: list[dict]):
        """批量保存预测 - 同步版本"""
        with self.db_manager.get_session() as session:
            for prediction in predictions:
                session.execute(
                    "INSERT INTO predictions (match_id, prediction, confidence) "
                    "VALUES (:match_id, :prediction, :confidence)",
                    prediction
                )
            session.commit()
```

#### 新版本（异步）:
```python
# src/services/batch_service.py
from src.database.async_manager import get_db_session
from sqlalchemy import text

class BatchService:
    async def save_multiple_predictions(self, predictions: list[dict]):
        """批量保存预测 - 异步版本"""
        async with get_db_session() as session:
            # 使用 executemany 进行批量插入
            await session.execute(
                text("""
                    INSERT INTO predictions (match_id, prediction, confidence)
                    VALUES (:match_id, :prediction, :confidence)
                """),
                predictions
            )
            # 自动提交

    async def save_multiple_predictions_transactional(self, predictions: list[dict]):
        """事务性批量保存预测"""
        async with get_db_session() as session:
            try:
                # 开始事务
                for prediction in predictions:
                    await session.execute(
                        text("""
                            INSERT INTO predictions (match_id, prediction, confidence)
                            VALUES (:match_id, :prediction, :confidence)
                        """),
                        prediction
                    )
                # 提交事务
                await session.commit()
            except Exception as e:
                # 回滚事务
                await session.rollback()
                raise
```

---

### 示例 6: 使用兼容适配器（临时迁移）

如果暂时无法完全转换为异步，可以使用兼容适配器：

```python
# src/services/legacy_service.py
from src.database.compat import fetch_all_sync, fetch_one_sync, execute_sync
from sqlalchemy import text

class LegacyService:
    """遗留服务 - 使用同步适配器逐步迁移"""

    def get_user_sync(self, user_id: int):
        """获取用户信息 - 使用同步适配器"""
        return fetch_one_sync(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )

    def save_prediction_sync(self, prediction_data: dict):
        """保存预测 - 使用同步适配器"""
        execute_sync(
            text("""
                INSERT INTO predictions (match_id, prediction, confidence)
                VALUES (:match_id, :prediction, :confidence)
            """),
            prediction_data
        )

    async def get_user_async(self, user_id: int):
        """获取用户信息 - 异步版本（推荐）"""
        from src.database.async_manager import fetch_one
        return await fetch_one(
            text("SELECT * FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
```

---

## 🔧 迁移检查清单

### 迁移前的准备:
- [ ] 确保函数是 `async def`
- [ ] 检查调用者是否支持 `await`
- [ ] 备份原始文件
- [ ] 运行测试确保功能正常

### 迁移步骤:
1. **替换导入语句**:
   ```python
   # 旧版本
   from src.database.connection import get_async_session, DatabaseManager

   # 新版本
   from src.database.async_manager import get_db_session, AsyncDatabaseManager
   ```

2. **更新函数签名**:
   ```python
   # 旧版本
   def my_function():

   # 新版本
   async def my_function():
   ```

3. **替换数据库操作**:
   ```python
   # 旧版本
   with db_manager.get_session() as session:
       result = session.execute(query, params)

   # 新版本
   async with get_db_session() as session:
       result = await session.execute(query, params)
   ```

4. **添加 await 关键字**:
   ```python
   # 旧版本
   result = session.execute(query)

   # 新版本
   result = await session.execute(query)
   ```

### 迁移后的验证:
- [ ] 语法检查: `python -m py_compile file.py`
- [ ] 类型检查: `mypy file.py`
- [ ] 单元测试: `pytest tests/unit/test_file.py`
- [ ] 集成测试: `pytest tests/integration/test_feature.py`

---

## ⚠️ 常见陷阱和注意事项

### 1. 事务处理
```python
# ✅ 正确的事务处理
async def complex_operation():
    async with get_db_session() as session:
        try:
            await session.execute(text("INSERT INTO ..."))
            await session.execute(text("UPDATE ..."))
            await session.commit()  # 手动提交
        except Exception:
            await session.rollback()  # 手动回滚
            raise

# ✅ 简化的事务处理（推荐）
async def simple_operation():
    async with get_db_session() as session:
        await session.execute(text("INSERT INTO ..."))
        await session.execute(text("UPDATE ..."))
        # 自动提交和回滚
```

### 2. 错误处理
```python
# ✅ 完善的错误处理
async def safe_operation():
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT ..."))
            return result.fetchall()
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        raise
```

### 3. 性能考虑
```python
# ✅ 批量操作优化
async def batch_insert(items: list[dict]):
    async with get_db_session() as session:
        # 使用 executemany 而不是循环 execute
        await session.execute(text("INSERT INTO ... VALUES ..."), items)

# ✅ 连接池优化
# 在应用启动时初始化数据库
from src.database.async_manager import initialize_database
initialize_database(pool_size=20, max_overflow=30)
```

---

## 📚 相关资源

- [SQLAlchemy 2.0 Async 支持](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI 异步数据库集成](https://fastapi.tiangolo.com/tutorial/dependencies/#async-dependencies)
- [Python asyncio 最佳实践](https://docs.python.org/3/library/asyncio-dev.html)

---

*最后更新: 2025-12-05*
*维护者: Claude Code Refactoring Team*