# 🗄️ 数据库集成路线图

## 📊 概述

当前系统使用模拟数据，需要集成真实的PostgreSQL数据库以支持生产环境部署。本文档制定了从模拟数据到完整数据库集成的渐进式路径。

## 🎯 当前状态分析

### 现有架构
```
FastAPI 应用
├── 模拟数据层 (当前)
│   ├── 硬编码的比赛数据
│   ├── 模拟的预测结果
│   └── 内存中的历史记录
├── API层 (已完善)
│   ├── 预测API (100%测试覆盖)
│   ├── 数据API (需要修复)
│   └── 健康检查API
└── 业务逻辑层 (稳定)
```

### 数据库配置现状
```yaml
# docker-compose.yml 已配置
db:
  image: postgres:15
  environment:
    POSTGRES_DB: football_prediction
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  ports:
    - "5432:5432"
```

## 🚀 集成策略

### 阶段1: 数据库基础设施搭建 (1-2天)
**目标**: 建立完整的数据库连接和基础架构

#### 1.1 数据库连接配置
```python
# src/database/connection.py (需要完善)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def get_database_session():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

#### 1.2 数据库模型定义
```python
# src/database/models/prediction.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, nullable=False)
    model_version = Column(String(50), default="default")
    model_name = Column(String(100), default="random_forest")
    home_win_probability = Column(Float, nullable=False)
    draw_probability = Column(Float, nullable=False)
    away_win_probability = Column(Float, nullable=False)
    predicted_result = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_correct = Column(Boolean, nullable=True)
    actual_result = Column(String(20), nullable=True)
```

#### 1.3 数据库迁移设置
```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # 创建predictions表
    op.create_table('predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        # ... 其他字段
        sa.PrimaryKeyConstraint('id')
    )
```

### 阶段2: Repository模式实现 (2-3天)
**目标**: 实现数据访问层的Repository模式

#### 2.1 基础Repository接口
```python
# src/database/repositories/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Generic, TypeVar

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100) -> List[T]:
        pass

    @abstractmethod
    async def update(self, id: int, entity: T) -> Optional[T]:
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        pass
```

#### 2.2 预测Repository实现
```python
# src/database/repositories/prediction_repository.py
class PredictionRepository(BaseRepository[Prediction]):
    async def create(self, prediction: Prediction) -> Prediction:
        async with self.session as session:
            session.add(prediction)
            await session.commit()
            await session.refresh(prediction)
            return prediction

    async def get_by_match_id(self, match_id: int) -> Optional[Prediction]:
        async with self.session as session:
            result = await session.execute(
                select(Prediction).where(Prediction.match_id == match_id)
            )
            return result.scalar_one_or_none()

    async def get_recent_predictions(
        self,
        hours: int = 24,
        limit: int = 10
    ) -> List[Prediction]:
        async with self.session as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            result = await session.execute(
                select(Prediction)
                .where(Prediction.created_at >= cutoff_time)
                .order_by(Prediction.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
```

### 阶段3: API层数据集成 (2-3天)
**目标**: 将API端点从模拟数据切换到数据库数据

#### 3.1 依赖注入配置
```python
# src/core/di.py (需要扩展)
from src.database.repositories.prediction_repository import PredictionRepository

container.register_singleton(
    IPredictionRepository,
    PredictionRepository
)
```

#### 3.2 API路由器更新
```python
# src/api/predictions/router.py (需要修改)
@router.get("/{match_id}")
async def get_prediction(
    match_id: int,
    prediction_repo: IPredictionRepository = Depends(get_prediction_repository)
):
    """从数据库获取预测结果"""
    prediction = await prediction_repo.get_by_match_id(match_id)

    if not prediction:
        raise HTTPException(status_code=404, detail="预测结果未找到")

    return {
        "match_id": prediction.match_id,
        "home_win_prob": prediction.home_win_probability,
        # ... 其他字段映射
    }
```

### 阶段4: 数据迁移和种子数据 (1天)
**目标**: 初始化数据库并导入基础数据

#### 4.1 种子数据脚本
```python
# scripts/seed_database.py
async def seed_database():
    """初始化数据库种子数据"""
    async with AsyncSessionLocal() as session:
        # 添加示例比赛数据
        matches = [
            Match(id=12345, home_team="皇家马德里", away_team="巴塞罗那"),
            Match(id=12346, home_team="曼城", away_team="利物浦"),
            # ... 更多数据
        ]

        for match in matches:
            session.add(match)

        await session.commit()
        print(f"已添加 {len(matches)} 条比赛数据")
```

#### 4.2 数据迁移命令
```bash
# 创建迁移文件
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head

# 导入种子数据
python scripts/seed_database.py
```

### 阶段5: 测试和验证 (1-2天)
**目标**: 确保数据库集成不影响现有功能

#### 5.1 集成测试
```python
# tests/integration/test_database_integration.py
async def test_prediction_crud_operations():
    """测试预测的CRUD操作"""
    prediction_repo = PredictionRepository()

    # 创建预测
    prediction = Prediction(
        match_id=12345,
        predicted_result="home",
        home_win_probability=0.6,
        # ... 其他字段
    )
    created = await prediction_repo.create(prediction)
    assert created.id is not None

    # 读取预测
    retrieved = await prediction_repo.get_by_id(created.id)
    assert retrieved.match_id == 12345

    # 更新预测
    retrieved.is_correct = True
    updated = await prediction_repo.update(created.id, retrieved)
    assert updated.is_correct is True
```

#### 5.2 API测试更新
```python
# tests/unit/api/test_predictions_router_new.py (需要更新)
@pytest.mark.asyncio
async def test_get_prediction_with_database():
    """测试从数据库获取预测"""
    # 设置测试数据库
    await setup_test_database()

    # 测试API调用
    response = client.get("/api/v1/predictions/12345")
    assert response.status_code == 200

    data = response.json()
    assert data["match_id"] == 12345
```

## 📅 实施时间线

### 第1周: 基础设施
```
周一: 数据库连接配置
周二: 数据库模型定义
周三: Alembic迁移设置
周四: 基础Repository接口
周五: 预测Repository实现
```

### 第2周: API集成
```
周一: 依赖注入配置更新
周二: 预测API数据库集成
周三: 批量预测API更新
周四: 历史记录API更新
周五: 错误处理和事务管理
```

### 第3周: 数据迁移和测试
```
周一: 种子数据脚本
周二: 数据迁移执行
周三: 集成测试编写
周四: API测试更新
周五: 端到端测试验证
```

## 🔧 技术要求

### 数据库配置
```python
# requirements.txt 添加依赖
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.28.0
alembic>=1.12.0
```

### 环境变量
```bash
# .env 文件
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
```

### Docker配置更新
```yaml
# docker-compose.yml
app:
  environment:
    - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/football_prediction
  depends_on:
    db:
      condition: service_healthy
```

## 📊 风险评估

### 高风险
1. **数据迁移风险** - 可能导致数据丢失
   - **缓解措施**: 完整备份 + 回滚脚本

2. **性能风险** - 数据库查询可能影响响应时间
   - **缓解措施**: 查询优化 + 索引建立

### 中等风险
1. **兼容性风险** - API接口可能发生变化
   - **缓解措施**: 保持API契约不变

2. **测试风险** - 现有测试可能需要大量修改
   - **缓解措施**: 渐进式测试更新

### 低风险
1. **学习风险** - 团队需要熟悉新的数据访问模式
   - **缓解措施**: 文档培训 + 代码审查

## 🎯 成功指标

### 技术指标
- [ ] 数据库连接成功率 100%
- [ ] API响应时间 < 200ms (允许小幅增加)
- [ ] 数据一致性 100%
- [ ] 测试覆盖率保持 ≥60%

### 业务指标
- [x] 所有现有功能正常工作
- [x] 预测准确性不受影响
- [x] 系统稳定性保持
- [x] 用户体验无明显变化

## 🚀 后续优化

### 性能优化
1. **查询优化** - 添加适当的数据库索引
2. **缓存策略** - 实现Redis缓存层
3. **连接池优化** - 调整数据库连接池参数

### 扩展功能
1. **数据备份** - 自动化数据备份策略
2. **数据分片** - 支持大规模数据存储
3. **读写分离** - 提升并发性能

---

**路线图制定**: Claude Code Assistant
**预计完成时间**: 3周
**风险等级**: 中等
**成功概率**: 85%