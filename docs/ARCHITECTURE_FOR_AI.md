# AI Architecture Map

**Purpose**: AI 维护者的导航指南 - 快速理解项目结构和职责边界

---

## 🎯 Project Architecture Overview

### 🏗️ Core Architecture Pattern
```
📦 Football Prediction System
├── 🎨 Presentation Layer (API)
├── 🔧 Application Layer (Services)
├── 🧠 Domain Layer (Business Logic)
├── 💾 Infrastructure Layer (Database/Cache/External)
└── 🔌 Adapters (Third-party Integrations)
```

### 🏛️ Architecture Principles
- **DDD + CQRS**: 领域驱动设计，命令查询职责分离
- **Async First**: 所有 I/O 操作必须是异步的
- **Dependency Injection**: 通过依赖注入实现松耦合
- **Event-Driven**: 事件驱动架构，领域事件解耦组件

---

## 📁 Directory Structure & Responsibilities

### 🎨 `src/api/` - HTTP Layer (仅关注HTTP协议)
```
src/api/
├── models/           # ✅ API请求/响应模型 (Pydantic)
│   ├── requests/     # 📥 请求数据结构
│   └── responses/    # 📤 响应数据结构
├── routers/          # ✅ FastAPI路由定义
│   ├── predictions/  # ⚽ 预测相关API
│   ├── health/       # 💊 健康检查API
│   └── system/       # ⚙️ 系统管理API
├── middleware/       # 🔧 HTTP中间件 (CORS, Auth, etc.)
└── dependencies/     # 🔌 FastAPI依赖注入
```

**职责边界**:
- ✅ **允许**: HTTP请求处理、参数验证、响应格式化
- ✅ **允许**: 调用应用服务
- ❌ **禁止**: 业务逻辑实现
- ❌ **禁止**: 直接数据库操作
- ❌ **禁止**: 外部API调用

---

### 🔧 `src/services/` - Application Layer (业务流程编排)
```
src/services/
├── prediction/       # ⚽ 预测服务
│   ├── prediction_service.py    # 🔮 核心预测逻辑
│   ├── model_selector.py        # 🤖 模型选择器
│   └── result_processor.py      # 📊 结果处理
├── user/             # 👤 用户服务
├── match/            # 🏆 比赛服务
└── analytics/        # 📈 分析服务
```

**职责边界**:
- ✅ **允许**: 编排业务流程
- ✅ **允许**: 调用领域服务和基础设施
- ✅ **允许**: 事务管理
- ❌ **禁止**: HTTP协议相关逻辑
- ❌ **禁止**: 具体的业务规则实现

---

### 🧠 `src/domain/` - Business Logic Layer (纯粹的业务逻辑)
```
src/domain/
├── models/           # 📋 领域实体 (纯Python对象)
│   ├── match.py      # ⚽ 比赛实体
│   ├── team.py       # 👥 球队实体
│   ├── prediction.py # 🔮 预测实体
│   └── league.py     # 🏆 联赛实体
├── services/         # 💼 领域服务 (无外部依赖)
│   ├── prediction/   # 🔮 预测领域服务
│   ├── validation/   # ✅ 数据验证服务
│   └── calculation/  # 🧮 计算服务
├── strategies/       # 🎯 策略模式实现
│   ├── lstm_strategy.py      # 📊 LSTM预测策略
│   ├── poisson_strategy.py   # 📈 Poisson分布策略
│   └── ensemble_strategy.py  # 🔄 集成策略
└── events/           # 📡 领域事件
    ├── prediction_created.py # 🔮 预测创建事件
    └── match_completed.py   # 🏁 比赛完成事件
```

**职责边界**:
- ✅ **允许**: 业务规则实现
- ✅ **允许**: 领域实体操作
- ✅ **允许**: 策略模式实现
- ❌ **禁止**: 数据库访问
- ❌ **禁止**: 外部服务调用
- ❌ **禁止**: 文件系统操作

---

### 💾 `src/database/` - Data Access Layer (数据持久化)
```
src/database/
├── models/           # 🗄️ SQLAlchemy ORM模型
│   ├── match.py      # ⚽ 比赛数据模型
│   ├── team.py       # 👥 球队数据模型
│   ├── prediction.py # 🔮 预测数据模型
│   └── user.py       # 👤 用户数据模型
├── repositories/     # 📚 数据访问层 (Repository模式)
│   ├── base_repository.py    # 🔧 基础Repository
│   ├── match_repository.py   # ⚽ 比赛Repository
│   └── prediction_repository.py # 🔮 预测Repository
├── migrations/       # 🔄 数据库迁移 (Alembic)
└── session.py        # 🔗 数据库会话管理
```

**职责边界**:
- ✅ **允许**: 数据库操作 (CRUD)
- ✅ **允许**: 查询优化
- ✅ **允许**: 事务处理
- ❌ **禁止**: 业务逻辑
- ❌ **禁止**: HTTP协议处理
- ❌ **禁止**: 外部API调用

---

### 🔌 `src/adapters/` - External Integrations (外部适配器)
```
src/adapters/
├── data_sources/     # 📊 数据源适配器
│   ├── football_api.py       # ⚽ 足球数据API
│   ├── betting_api.py        # 💰 博彩数据API
│   └── news_api.py          # 📰 新闻数据API
├── cache/            # 💾 缓存适配器
│   ├── redis_adapter.py      # 🔴 Redis适配器
│   └── memory_cache.py       # 🧠 内存缓存适配器
└── notifications/    # 📢 通知适配器
    ├── email_adapter.py      # 📧 邮件通知
    └── webhook_adapter.py    # 🎣 Webhook通知
```

**职责边界**:
- ✅ **允许**: 第三方API集成
- ✅ **允许**: 数据格式转换
- ✅ **允许**: 错误处理和重试
- ❌ **禁止**: 业务逻辑实现
- ❌ **禁止**: 数据库操作

---

### ⚙️ `src/core/` - Infrastructure Core (基础设施)
```
src/core/
├── config/           # ⚙️ 配置管理
│   ├── settings.py           # 📋 应用配置
│   └── database.py           # 🗄️ 数据库配置
├── logging/          # 📝 日志系统
│   ├── logger.py            # 📊 日志配置
│   └── formatters.py        # 🎨 日志格式化
├── exceptions/       # ⚠️ 异常定义
│   └── custom_exceptions.py # 🚨 自定义异常
└── security/         # 🔒 安全相关
    ├── auth.py              # 🔐 认证逻辑
    └── encryption.py        # 🔒 加密工具
```

---

### 🤖 `src/ml/` - Machine Learning Layer (机器学习)
```
src/ml/
├── models/           # 🤖 ML模型定义
│   ├── lstm_model.py         # 📊 LSTM时序模型
│   ├── poisson_model.py      # 📈 Poisson分布模型
│   └── ensemble_model.py     # 🔄 集成模型
├── features/         # 🔧 特征工程
│   ├── match_features.py     # ⚽ 比赛特征
│   ├── team_features.py      # 👥 球队特征
│   └── historical_features.py # 📚 历史特征
├── training/         # 🎯 模型训练
│   ├── trainer.py           # 🏋️ 模型训练器
│   └── evaluator.py         # 📊 模型评估
└── inference/        # 🔮 模型推理
    ├── predictor.py         # 🔮 预测器
    └── model_loader.py      # 📂 模型加载器
```

---

## 🎯 AI Development Guidelines

### 🚀 How to Add New Features

#### 1. 添加新的预测模型
```
📁 文件位置:
- 模型实现: src/ml/models/new_model.py
- 策略实现: src/domain/strategies/new_model_strategy.py
- 服务集成: src/services/prediction/strategy_selector.py
- API端点: src/api/routers/predictions.py

🔄 开发流程:
1. 在 src/ml/models/ 实现ML模型
2. 在 src/domain/strategies/ 创建策略
3. 在 src/services/prediction/ 集成策略
4. 在 src/api/routers/predictions/ 暴露API
5. 在 tests/unit/ 对应目录添加测试
```

#### 2. 添加新的API端点
```
📁 文件位置:
- 路由定义: src/api/routers/feature_name.py
- 请求模型: src/api/models/requests/feature_name.py
- 响应模型: src/api/models/responses/feature_name.py
- 业务逻辑: src/services/feature_name/
- 数据模型: src/domain/models/feature_name.py

🔄 开发流程:
1. 在 src/api/routers/ 定义路由
2. 在 src/api/models/ 定义请求/响应模型
3. 在 src/services/ 实现业务逻辑
4. 在 src/domain/ 定义领域模型
5. 在 src/database/ 实现数据访问 (如需要)
6. 在 tests/unit/ 添加完整测试
```

#### 3. 添加新的数据源
```
📁 文件位置:
- 适配器实现: src/adapters/data_sources/new_source.py
- 数据转换: src/adapters/transformers/new_source_transformer.py
- 配置管理: src/core/config/new_source.py
- 测试: tests/unit/adapters/test_new_source.py

🔄 开发流程:
1. 在 src/adapters/data_sources/ 实现适配器
2. 在 src/adapters/transformers/ 实现数据转换
3. 在 src/core/config/ 添加配置
4. 在 src/services/ 集成数据源
5. 在 tests/ 添加集成测试
```

### 🚨 Architecture Violations (必须避免)

#### ❌ 禁止的跨层调用
```
❌ API Layer → Database Layer
   # 错误示例
   @app.get("/users/{user_id}")
   async def get_user(user_id: int):
       user = db.query(User).filter(User.id == user_id).first()  # ❌ 直接数据库访问
       return user

   # 正确做法
   @app.get("/users/{user_id}")
   async def get_user(user_id: int, user_service: UserService = Depends()):
       return await user_service.get_user_by_id(user_id)  # ✅ 通过服务层

❌ Domain Layer → External APIs
   # 错误示例
   class MatchService:
       def get_match_data(self, match_id: int):
           response = requests.get(f"https://api.football.com/matches/{match_id}")  # ❌ 外部API调用
           return response.json()

   # 正确做法
   class MatchService:
       def __init__(self, data_adapter: FootballDataAdapter):
           self.data_adapter = data_adapter  # ✅ 注入适配器

       def get_match_data(self, match_id: int):
           return self.data_adapter.get_match_data(match_id)  # ✅ 通过适配器
```

#### ❌ 禁止的反模式
```python
# 1. 同步数据库操作
def get_user(user_id: int):
    user = db.query(User).filter(User.id == user_id).first()  # ❌ 同步操作

# 2. 业务逻辑在API层
@app.post("/predictions")
async def create_prediction(data: PredictionRequest):
    # 复杂的业务逻辑不应该在这里
    if data.home_team_strength > 0.8 and data.away_team_strength < 0.3:
        home_win_prob = 0.85  # ❌ 业务规则在API层

    prediction = Prediction(home_win_prob=home_win_prob)
    db.add(prediction)  # ❌ 直接数据库操作
    return prediction

# 3. 缺少类型注解
def process_data(data):  # ❌ 缺少类型注解
    return data.process()

# 4. 使用print()而非logger
def process_items(items):
    print(f"Processing {len(items)} items")  # ❌ 使用print
    return items
```

### ✅ 推荐的模式

#### ✅ 正确的层间调用
```python
# 1. API层调用服务层
@router.post("/predictions")
async def create_prediction(
    request: PredictionRequest,
    prediction_service: PredictionService = Depends()
) -> PredictionResponse:
    """创建预测的API端点."""
    prediction = await prediction_service.create_prediction(request)
    return PredictionResponse.from_domain(prediction)

# 2. 服务层编排业务逻辑
class PredictionService:
    async def create_prediction(self, request: PredictionRequest) -> Prediction:
        """创建预测."""
        # 数据验证
        validated_data = await self.validation_service.validate(request)

        # 领域逻辑
        prediction = await self.prediction_domain_service.predict(validated_data)

        # 持久化
        saved_prediction = await self.prediction_repository.save(prediction)

        # 事件发布
        await self.event_bus.publish(PredictionCreatedEvent(saved_prediction))

        return saved_prediction

# 3. 异步数据库操作
class PredictionRepository:
    async def save(self, prediction: Prediction) -> Prediction:
        """保存预测."""
        db_prediction = PredictionModel.from_domain(prediction)
        self.db.add(db_prediction)
        await self.db.commit()
        await self.db.refresh(db_prediction)
        return db_prediction.to_domain()
```

---

## 🔄 Data Flow Patterns

### 📊 预测流程数据流
```
API Request → API Layer → Service Layer → Domain Layer
    ↓               ↓              ↓              ↓
HTTP Valid. → Service Orch. → Business Logic → ML Models
    ↓               ↓              ↓              ↓
API Response ← Response DTO ← Result Entity ← Prediction Result
```

### 🏆 比赛数据更新流程
```
External API → Adapter Layer → Service Layer → Domain Layer
      ↓              ↓              ↓              ↓
Data Fetch → Data Transform → Validation → Domain Events
      ↓              ↓              ↓              ↓
Database ← Repository ← Service Orchestration ← Event Handlers
```

---

## 🎯 Quick Reference

### 📋 常见开发任务的文件位置
```
🔍 添加新API端点:
   - 路由: src/api/routers/
   - 模型: src/api/models/
   - 服务: src/services/

🤖 实现新ML模型:
   - 模型: src/ml/models/
   - 特征: src/ml/features/
   - 策略: src/domain/strategies/

🗄️ 添加新数据表:
   - 模型: src/database/models/
   - Repository: src/database/repositories/
   - 迁移: src/database/migrations/

🔌 集成新外部API:
   - 适配器: src/adapters/data_sources/
   - 转换器: src/adapters/transformers/
   - 配置: src/core/config/

📢 添加新领域事件:
   - 事件定义: src/domain/events/
   - 事件处理: src/services/handlers/
   - 事件发布: src/core/event_bus.py
```

### 🧪 测试文件对应关系
```
src/api/routers/predictions.py     → tests/unit/api/test_predictions.py
src/services/prediction/           → tests/unit/services/test_prediction.py
src/domain/models/prediction.py    → tests/unit/domain/test_prediction.py
src/database/models/prediction.py  → tests/unit/database/test_prediction.py
src/ml/models/lstm_model.py        → tests/unit/ml/test_lstm_model.py
src/adapters/data_sources/         → tests/unit/adapters/test_data_sources.py
```

---

**记住**: 架构的完整性是AI维护系统的基石。当不确定时，选择保守的方案，保持现有模式。

*Last Updated: 2025-11-20 | AI Architect: Claude Code*