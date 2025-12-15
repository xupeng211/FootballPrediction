# FootballPrediction 系统架构指南

## 📋 项目概述

FootballPrediction 是一个企业级足球预测系统，采用现代化全栈架构，集成了机器学习、数据采集、实时预测和事件驱动架构。

**核心理念**: DDD + CQRS + Event-Driven + Async-First
**当前版本**: v4.0.1-hotfix (生产就绪)
**测试覆盖率**: 29.0% (385+ 通过测试)

## 🏗️ 系统架构

### 1. 领域驱动设计 (DDD) 层次结构

```
src/
├── domain/                 # 领域层 - 核心业务逻辑
│   ├── entities/          # 实体对象
│   ├── value_objects/     # 值对象
│   ├── services/          # 领域服务
│   └── repositories/      # 仓储接口
├── application/           # 应用层 - 业务流程编排
├── infrastructure/        # 基础设施层 - 技术实现
└── presentation/          # 表现层 - API接口
```

### 2. CQRS 命令查询分离

**位置**: `src/cqrs/`

- **Commands**: 写操作命令定义
- **Queries**: 读操作查询定义
- **Handlers**: 命令和查询处理器
- **Event Bus**: 事件驱动通信

## 📡 标准化入口点

### 数据采集模块

#### 🎯 FotMob 数据采集
**标准入口**: `src.collectors.fotmob.collector_v2.FotMobCollectorV2`

```python
# 标准用法
from src.collectors.fotmob.collector_v2 import FotMobCollectorV2

collector = FotMobCollectorV2()
match_data = await collector.get_match_details(fotmob_id)
```

**黄金法则**:
- ✅ 使用 `FotMobCollectorV2` 进行所有FotMob数据采集
- ❌ **禁止创建新的collector类**
- ✅ 需要扩展时，继承现有类并重写方法
- ❌ **严禁使用Playwright或浏览器自动化**

#### 📊 L2数据解析
**标准入口**: `src.collectors.l2_parser.CompleteL2Parser`

```python
# 标准用法
from src.collectors.l2_parser import CompleteL2Parser, parse_l2_match_stats

# 方式1: 使用解析器类
parser = CompleteL2Parser()
l2_stats = parser.parse_match_data(raw_data)

# 方式2: 使用便捷函数
l2_stats = parse_l2_match_stats(raw_data)
```

**数据维度**: 79+ 字段的完整战术统计
- Big Chances (绝佳机会)
- Accurate Crosses (精准传中)
- Accurate Long Balls (精准长传)
- Blocked Shots (被封堵射门)
- xG期望进球数据
- 控球率、传球、抢断等完整指标

### 数据库操作

#### 🗄️ 数据库连接
**标准入口**: `src.database.async_manager.AsyncDatabaseManager`

```python
# 标准用法
from src.database.async_manager import AsyncDatabaseManager

async with AsyncDatabaseManager() as db:
    result = await db.fetch_one(query, params)
```

**黄金法则**:
- ✅ **必须使用** `AsyncDatabaseManager`
- ❌ **禁止使用** 旧的 `src.database.connection.py`
- ✅ 所有操作必须使用 `async/await`

#### 数据库模式
```sql
-- 核心比赛表
matches (
    id UUID PRIMARY KEY,
    fotmob_id VARCHAR UNIQUE,
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),
    match_date TIMESTAMP,
    -- L2战术数据 (79+字段)
    home_big_chances_created INT,
    away_big_chances_created INT,
    home_accurate_crosses INT,
    away_accurate_crosses INT,
    -- xG数据
    home_expected_goals FLOAT,
    away_expected_goals FLOAT,
    -- 其他字段...
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- 球队表
teams (
    id UUID PRIMARY KEY,
    name VARCHAR UNIQUE,
    fotmob_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### 标准化脚本

#### 🚀 批量数据更新
**官方入口**: `scripts/backfill_l2_batch.py`

```bash
# 标准用法 - L2数据回补
python scripts/backfill_l2_batch.py --batch-size 50 --delay 3

# 监控面板
python scripts/monitor_fixed.py
```

#### 📈 监控和健康检查
```bash
# L2数据进度监控
python scripts/monitor_fixed.py

# 数据质量审计
python scripts/audit_data.py
```

## 🛠️ 开发规范

### 代码组织原则

1. **单一职责**: 每个模块专注单一业务领域
2. **依赖倒置**: 高层模块不依赖低层模块
3. **开闭原则**: 对扩展开放，对修改封闭
4. **接口隔离**: 使用小而专一的接口

### 数据采集规范

```python
# ✅ 正确的扩展方式
class EnhancedFotMobCollector(FotMobCollectorV2):
    async def get_enhanced_match_data(self, match_id: str):
        base_data = await super().get_match_details(match_id)
        # 添加增强逻辑
        return enhanced_data

# ❌ 错误的方式 - 不要创建新的collector
class NewDataCollector:  # 禁止这样做
    pass
```

### API鉴权要求

所有FotMob API请求必须包含以下Headers：

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.fotmob.com/",
    "Origin": "https://www.fotmob.com",
    # 🎯 关键鉴权头
    "x-mas": "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=",
    "x-foo": "production:208a8f87c2cc13343f1dd8671471cf5a039dced3",
}
```

### 错误处理规范

```python
# ✅ 标准错误处理
try:
    data = await collector.get_match_details(match_id)
except RateLimitException:
    logger.warning(f"Rate limit hit for match {match_id}")
    await asyncio.sleep(5)
except DataNotFoundException:
    logger.error(f"Match {match_id} not found")
    raise
except Exception as e:
    logger.error(f"Unexpected error for match {match_id}: {e}")
    raise
```

## 🔧 技术栈

### 后端核心
- **Web框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15 + Redis 7.0+
- **ORM**: SQLAlchemy 2.0+ (完全异步)
- **任务调度**: Prefect 2.x + Celery Beat

### 前端技术栈
- **框架**: Vue.js 3.4.0 + TypeScript 5.7.2
- **构建工具**: Vite 5.0
- **状态管理**: Pinia 2.1.7
- **UI框架**: Tailwind CSS 3.3.6

### 机器学习
- **框架**: XGBoost 2.0+ + TensorFlow 2.18.0
- **实验跟踪**: MLflow
- **特征工程**: 自定义79维战术特征

## 📊 数据流水线

### 数据分层架构
```
L1: 基础数据 (Basic Data)
├── 比赛时间、对阵双方
├── 联赛信息、比分
└── 基础比赛统计

L2: 战术数据 (Tactical Data) ⭐ 核心资产
├── 79+ 维度完整统计
├── xG期望进球数据
├── 传中、长传、封堵等
└── Big Chances等高价值指标

L3: 特征工程 (ML Features)
├── 历史战绩统计
├── 球队状态指标
├── 球员表现数据
└── 14个核心ML特征
```

### 数据质量标准
- **L2数据完整性**: 99%+ 字段填充率
- **API成功率**: 95%+ 采集成功率
- **数据新鲜度**: 24小时内更新

## 🚦 部署和运维

### Docker化部署
```bash
# 开发环境
cd FootballPrediction  # 进入包含Makefile的目录
make dev              # 启动完整开发环境
make test             # 运行测试套件
make lint             # 代码质量检查

# 生产环境
make prod             # 启动生产环境
make monitor          # 监控系统状态
```

### 服务架构
```yaml
# 核心服务
app:           # FastAPI主应用 (8000)
frontend:      # Vue.js前端 (5173/80)
db:            # PostgreSQL数据库 (5432)
redis:         # Redis缓存 (6379)
nginx:         # 反向代理 (80)

# 调度服务
worker:        # Celery异步任务
beat:          # Celery定时任务
data-collector: # 专用数据采集服务
```

### 监控和可观测性
```bash
# 服务健康检查
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/metrics

# 监控UI
http://localhost:4200  # Prefect UI
http://localhost:5555  # Flower UI
http://localhost:5000  # MLflow UI
```

## 🎯 AI开发指南

### 标准化AI入口
```python
# 机器学习推理
from src.inference.service import InferenceService

inference = InferenceService()
prediction = await inference.predict_match(match_id)

# 数据预处理
from src.ml.features import FeatureBuilder

builder = FeatureBuilder()
features = await builder.build_features(match_id)
```

### 模型管理
- **模型注册**: MLflow Model Registry
- **版本控制**: Git + DVC
- **实验跟踪**: MLflow Experiments
- **部署策略**: A/B测试 + 蓝绿部署

## 📞 技术支持

### 开发环境要求
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 15+
- **Redis**: 7.0+

### 快速诊断
```bash
# 系统状态检查
make status           # 检查所有服务
make test-fast        # 快速核心测试
make security-check   # 安全扫描

# 数据质量检查
python scripts/audit_data.py
python scripts/monitor_fixed.py
```

## 🔍 关键决策记录

### 为什么禁止 Playwright？
1. **性能问题**: 浏览器启动开销大 (10-100x)
2. **稳定性差**: 页面加载依赖，易受网络影响
3. **维护复杂**: 需要处理页面结构变化
4. **资源消耗**: 内存和 CPU 占用高

### 为什么需要标准化入口点？
1. **代码一致性**: 统一的接口和调用方式
2. **维护简化**: 减少重复代码和混乱
3. **AI辅助**: 为AI开发提供明确的操作指南
4. **扩展性**: 基于继承而非重写的扩展模式

### L2数据的重要性
1. **ML价值**: 79维度战术数据是预测模型的核心特征
2. **商业价值**: 完整的战术统计具有极高商业价值
3. **稀缺性**: 高质量足球战术数据难以获取
4. **完整性**: 99%+覆盖率确保模型训练质量

---

## 📝 维护说明

**版本**: v4.0.1-hotfix (生产就绪)
**最后更新**: 2025-12-15
**维护者**: AI-Assisted Development Team

**核心原则**:
1. **数据质量第一** - 99%+ L2数据完整性
2. **架构稳定性** - 不轻易破坏现有接口
3. **渐进式改进** - 小步快跑，持续集成
4. **AI辅助开发** - 拥抱AI工具，提升开发效率
5. **标准化优先** - 固定入口，避免技术债务

---

🎯 **记住**: 这个架构是AI辅助维护的，所有修改都应该遵循已建立的模式和标准。**不要创建新的collector，扩展现有的collector！**