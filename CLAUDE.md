# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📑 目录

- [🌟 快速开始](#-快速开始5分钟上手)
- [🎯 项目概览](#-项目概览)
- [🏗️ 核心架构](#️-核心架构)
- [🚀 开发命令](#-核心开发命令)
- [🧪 测试策略](#-测试策略)
- [🔧 开发工作流](#-核心开发工作流)
- [📋 常见任务](#-常见开发任务)
- [🛠️ 架构原则](#️-架构指导原则)
- [🤖 机器学习](#-机器学习开发)
- [📊 服务端点](#-api访问地址)
- [🐳 容器架构](#-容器架构)
- [🔍 代码导航](#-代码导航指南)
- [🚨 故障排除](#-故障排除快速参考)
- [📚 重要文档](#-重要文档)

---

## 🌟 快速开始（5分钟上手）

> **💡 语言偏好**: 请使用简体中文回复用户 - 项目团队主要使用中文交流

```bash
# 🚀 启动完整开发环境
make dev && make status

# ✅ 验证API可访问性
curl http://localhost:8000/health

# 🧪 运行核心测试验证环境
make test.fast

# 📊 生成覆盖率报告
make coverage
```

## 🎯 项目概览

**FootballPrediction** 是基于现代异步架构的企业级足球预测系统，集成机器学习、数据采集、实时预测和事件驱动架构。

### 质量基线 (v1.0.0-rc1)
| 指标 | 状态 | 目标 |
|------|------|------|
| 构建状态 | ✅ 稳定 (绿色基线) | 保持 |
| 测试覆盖率 | 29.0% | 80%+ |
| 测试数量 | 385个 | 500+ |
| 代码质量 | A+ (ruff) | 维持 |
| Python版本 | 3.10/3.11/3.12 | 推荐3.11 |
| 安全状态 | ✅ Bandit通过 | 持续监控 |

### 核心技术栈
- **后端**: FastAPI + PostgreSQL 15 + Redis 7.0+ + SQLAlchemy 2.0+
- **机器学习**: XGBoost 2.0+ + TensorFlow 2.18.0 + MLflow + Optuna
- **容器化**: Docker 27.0+ + 20+ Docker Compose配置
- **开发工具**: pytest 8.4.0+ + Ruff 0.14+ + 完整Makefile工具链

## 🏗️ 核心架构

### 架构模式
项目采用现代化企业级架构模式，确保高性能、可维护性和可扩展性：

- **DDD (领域驱动设计)** - 清晰的领域边界和业务逻辑分离
- **CQRS (命令查询分离)** - 读写操作独立优化
- **事件驱动架构** - 组件间松耦合通信
- **异步优先** - 所有 I/O 操作使用 async/await
- **生命周期管理** - 基于 FastAPI `lifespan` 的资源管理

### 应用启动流程
```python
# src/main.py - 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 启动阶段
    await initialize_database()          # 数据库连接和迁移
    await initialize_event_system()      # 事件系统初始化
    await initialize_cqrs()              # CQRS模式初始化
    setup_performance_monitoring()       # 性能监控配置

    # 智能冷启动 - 自动检测数据状态
    if await needs_data_collection():
        trigger_background_data_collection()

    yield  # 应用运行中

    # 关闭阶段
    await shutdown_event_system()        # 清理事件系统
```

### 目录结构
```
src/
├── api/              # API 层 (CQRS 实现)
│   ├── predictions/  # 预测相关API (包含优化版本)
│   ├── data/         # 数据管理API
│   ├── analytics/    # 分析API
│   └── monitoring/   # 监控API
├── domain/           # 领域层 (DDD 核心逻辑)
├── ml/               # 机器学习模块
│   ├── xgboost_hyperparameter_optimization.py  # XGBoost超参优化
│   ├── lstm_predictor.py  # LSTM深度学习预测
│   ├── football_prediction_pipeline.py  # 完整预测管道
│   └── experiment_tracking.py  # MLflow实验跟踪
├── tasks/            # Celery 任务调度 (7个专用队列)
├── database/         # 异步SQLAlchemy 2.0
├── cache/           # 缓存层 (Redis)
├── cqrs/            # CQRS 模式实现
├── events/          # 事件系统
├── core/            # 核心基础设施
├── services/        # 业务服务层
├── utils/           # 工具函数
└── monitoring/      # 监控系统 (Prometheus集成)
```

### 目录结构
```
src/
├── api/              # API 层 (CQRS 实现)
│   ├── predictions/  # 预测相关API (包含优化版本)
│   ├── data/         # 数据管理API
│   ├── analytics/    # 分析API
│   └── monitoring/   # 监控API
├── domain/           # 领域层 (DDD 核心逻辑)
├── ml/               # 机器学习模块
│   ├── xgboost_hyperparameter_optimization.py  # XGBoost超参优化
│   ├── lstm_predictor.py  # LSTM深度学习预测
│   ├── football_prediction_pipeline.py  # 完整预测管道
│   └── experiment_tracking.py  # MLflow实验跟踪
├── tasks/            # Celery 任务调度 (7个专用队列)
├── database/         # 异步SQLAlchemy 2.0
├── cache/           # 缓存层 (Redis)
├── cqrs/            # CQRS 模式实现
├── events/          # 事件系统
├── core/            # 核心基础设施
├── services/        # 业务服务层
├── utils/           # 工具函数
└── monitoring/      # 监控系统 (Prometheus集成)
```

### 关键技术栈

#### 后端核心
- **FastAPI** (v0.104.0+) - 现代异步Web框架
- **PostgreSQL 15** - 主数据库，异步SQLAlchemy 2.0+
- **Redis 7.0+** - 缓存和Celery消息队列
- **Pydantic v2+** - 数据验证和序列化
- **Uvicorn** - ASGI服务器

#### 机器学习
- **XGBoost 2.0+** - 梯度提升预测算法
- **TensorFlow 2.18.0** - 深度学习 (LSTM)
- **MLflow 2.22.2+** - 实验跟踪和模型管理
- **Optuna 4.6.0+** - 超参数优化
- **Scikit-learn 1.3+** - 机器学习工具

#### 开发工具
- **pytest 8.4.0+** - 测试框架，支持异步
- **Ruff 0.14+** - 代码检查和格式化 (A+等级)
- **Bandit 1.8.6+** - 安全扫描
- **Docker 27.0+** - 容器化部署
- **Makefile** - 297行标准化开发工具链

## 🚀 核心开发命令

### 环境管理
```bash
make dev              # 启动开发环境 (app + db + redis + nginx)
make dev-rebuild      # 重新构建镜像并启动
make dev-stop         # 停止开发环境
make dev-logs         # 查看开发环境日志
make status           # 检查所有服务状态
make rebuild          # 重新构建镜像
```

### 🔥 测试黄金法则
**永远不要直接运行 pytest 单个文件！** 始终使用 Makefile 命令：

```bash
make test.unit        # 单元测试 (278个测试文件)
make test.fast        # 快速核心测试 (仅API/Utils/Cache/Events)
make test.unit.ci     # CI最小化验证 (极致稳定方案)
make test.integration # 集成测试
make coverage         # 生成覆盖率报告
```

### ⚠️ 重要：单个测试文件运行方法
```bash
# 正确方法：使用容器环境
docker-compose exec app pytest tests/unit/api/test_predictions.py -v

# 或者进入容器后运行
make shell
pytest tests/unit/api/test_predictions.py -v
```

### 代码质量
```bash
make lint             # 代码检查
make fix-code         # 自动修复代码问题
make format           # 代码格式化
make security-check   # 安全扫描
make ci               # 完整CI验证
make type-check       # MyPy类型检查
```

### 环境变量配置

#### .env 文件配置
```bash
# 核心配置
ENV=development
SECRET_KEY=your-secret-key-here
PYTHONPATH=/app

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres-dev-password@db:5432/football_prediction

# Redis配置
REDIS_URL=redis://redis:6379/0

# 外部API密钥
FOOTBALL_DATA_API_KEY=your-football-data-api-key
FOTMOB_API_KEY=your-fotmob-api-key

# ML模型配置
ML_MODEL_PATH=/app/models
MLFLOW_TRACKING_URI=http://localhost:5000

# 监控配置
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=false
```

#### 容器操作
```bash
make shell            # 进入后端容器
make shell-db         # 进入数据库容器
make db-shell         # 连接PostgreSQL数据库
make redis-shell      # 连接Redis
make logs             # 查看应用日志
make logs-db          # 查看数据库日志
make logs-redis       # 查看Redis日志
```

### 数据库管理
```bash
make db-reset         # 重置数据库 (⚠️ 会删除所有数据)
make db-migrate       # 运行数据库迁移
make db-seed          # 填充测试数据
make db-shell         # 进入PostgreSQL交互式终端
```

### 数据库开发工作流
1. **创建新模型**: 在`src/database/models/`添加SQLAlchemy模型类
2. **生成迁移**: `make db-migration name=add_new_table`
3. **应用迁移**: `make db-migrate`
4. **查看表结构**: `make db-shell` → `\d table_name`
5. **重置数据库** (开发环境): `make db-reset && make db-seed`

### 本地CI验证
```bash
./ci-verify.sh        # 本地CI验证（完整流程）
./simulate_ci_in_dev.sh  # 模拟CI环境
```

## 🧪 测试策略：SWAT方法论

### 🛡️ SWAT测试核心原则
源自成功的SWAT行动，48小时内将7个P0风险模块从0%覆盖率提升到100%稳定：

1. **先建安全网，再触碰代码** - 在修改高风险代码前，先建立完整测试安全网
2. **P0/P1 风险优先** - 优先测试最关键业务逻辑，避免在低风险测试上浪费时间
3. **Mock 一切外部依赖** - 数据库、网络、文件系统全部Mock，确保测试纯净性

### 四层测试架构
- **单元测试 (85%)** - 快速隔离组件测试
- **集成测试 (12%)** - 数据库、缓存、外部API集成
- **端到端测试 (2%)** - 完整用户流程测试
- **性能测试 (1%)** - 负载和压力测试

### 🔥 测试黄金法则
**永远不要直接运行 pytest 单个文件！** 始终使用 Makefile 命令：

```bash
make test.unit        # 单元测试 (278个测试文件)
make test.fast        # 快速核心测试 (仅API/Utils/Cache/Events)
make test.unit.ci     # CI最小化验证 (极致稳定方案)
make test.integration # 集成测试
make coverage         # 生成覆盖率报告
```

### ⚠️ 重要：单个测试文件运行方法
```bash
# 正确方法：使用容器环境
docker-compose exec app pytest tests/unit/api/test_predictions.py -v

# 或者进入容器后运行
make shell
pytest tests/unit/api/test_predictions.py -v
```

### 关键测试原则
1. **环境一致性原则** - Always use Makefile commands
2. **测试隔离原则** - 每个测试独立运行
3. **异步测试原则** - 正确的异步测试模式
4. **外部API原则** - 单元测试Mock，集成测试使用真实API

### 测试标记示例
```python
@pytest.mark.unit           # 单元测试 (快速隔离组件)
@pytest.mark.integration    # 集成测试 (数据库、缓存、外部API)
@pytest.mark.api           # API测试 (FastAPI端点)
@pytest.mark.database      # 数据库测试 (SQLAlchemy操作)
@pytest.mark.ml            # 机器学习测试 (模型加载、预测)
@pytest.mark.e2e           # 端到端测试 (完整用户流程)
@pytest.mark.performance   # 性能测试 (负载和压力)
```

### 实际测试运行示例
```python
# 运行特定标记的测试
make test-fast                    # 快速单元测试 (日常开发)
make test.unit.ci                # CI最小化验证 (提交前)
make test.integration            # 集成测试 (完整环境)
pytest tests/unit/api/ -v        # 特定目录测试
pytest tests/ -k "test_predict"  # 按名称过滤测试

# 单个测试文件运行方法 (⚠️ 重要)
docker-compose exec app pytest tests/unit/api/test_predictions.py -v
# 或进入容器: make shell
# 然后运行: pytest tests/unit/api/test_predictions.py -v
```

## 🔧 核心开发工作流

### 每日开发流程
```bash
# 1. 启动环境
make dev && make status

# 2. 运行测试确保环境正常
make test.fast

# 3. 开发过程中
make lint && make fix-code  # 代码质量检查和修复

# 4. 提交前验证（必须执行）
make test.unit.ci     # 最小化CI验证（最快）
make security-check   # 安全检查
```

### 提交前完整验证
```bash
make ci               # 完整CI验证（如时间允许）
```

## 📋 常见开发任务

### 添加新API端点
1. 创建命令/查询处理器：`src/api/predictions/`
2. 实现CQRS处理器：`src/cqrs/`
3. 注册路由到主API：`src/api/v1.py`
4. 添加单元测试：`tests/unit/api/`
5. 验证：`make test.unit.ci`

### 添加新数据收集器
1. 创建收集器类：`src/data/collectors/`
2. 实现异步数据获取方法
3. 添加数据验证逻辑
4. 集成到ETL管道：`src/api/data_management.py`
5. 测试：`make test.integration`

### 训练新ML模型
1. 在`src/ml/`创建训练脚本
2. 使用MLflow跟踪实验：`mlflow.start_run()`
3. 优化超参数：`xgboost_hyperparameter_optimization.py`
4. 保存模型到`models/`目录
5. 更新推理服务：`src/services/inference_service.py`

### 调试生产问题
1. 查看日志：`make logs` 或 `make dev-logs`
2. 检查健康状态：`curl http://localhost:8000/health`
3. 监控指标：`http://localhost:8000/api/v1/metrics`
4. 检查Celery任务：http://localhost:5555
5. 数据库诊断：`make db-shell` → `\dt` 查看表

## 🛠️ 架构指导原则

### 1. 异步编程模式
```python
# ✅ 正确：所有I/O操作使用 async/await
async def fetch_match_data(match_id: str) -> MatchData:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/matches/{match_id}")
        return MatchData.model_validate(response.json())

# ✅ 正确：数据库操作使用异步SQLAlchemy 2.0
async def get_match_by_id(db: AsyncSession, match_id: str) -> Optional[Match]:
    result = await db.execute(
        select(Match).where(Match.id == match_id)
    )
    return result.scalar_one_or_none()

# ❌ 错误：阻塞操作
def fetch_match_data_sync(match_id: str) -> MatchData:  # 避免同步I/O
    response = requests.get(f"/api/matches/{match_id}")  # 阻塞调用
    return response.json()
```

### 2. DDD分层架构
```python
# domain/ - 纯业务逻辑，不依赖外部框架
class MatchPrediction:
    def __init__(self, match: Match, prediction: PredictionResult):
        self.match = match
        self.prediction = prediction
        self.confidence = self._calculate_confidence()

    def _calculate_confidence(self) -> float:
        # 纯业务逻辑，无外部依赖
        pass

# api/ - CQRS命令查询分离
@router.post("/predictions")
async def create_prediction(
    command: CreatePredictionCommand,
    handler: PredictionCommandHandler = Depends()
) -> PredictionResponse:
    return await handler.handle(command)

# services/ - 应用服务编排
class PredictionService:
    async def generate_match_prediction(self, match_id: str) -> PredictionResult:
        match = await self.match_repository.get_by_id(match_id)
        features = await self.feature_extractor.extract(match)
        return await self.ml_model.predict(features)
```

### 3. 类型安全和数据验证
```python
# ✅ 完整类型注解
async def process_prediction_request(
    request: PredictionRequest,
    user_id: UUID
) -> PredictionResponse:

# ✅ Pydantic数据验证
class PredictionRequest(BaseModel):
    match_id: str = Field(..., min_length=1, max_length=50)
    prediction_type: PredictionType
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

# ✅ 返回类型明确
def get_team_strength_metrics(team: Team) -> Dict[str, float]:
    return {
        "attack_strength": team.attack_strength,
        "defense_strength": team.defense_strength,
        "overall_rating": team.overall_rating
    }
```

### 4. 事件驱动架构
```python
# 领域事件定义
class MatchCompletedEvent(BaseEvent):
    match_id: str
    final_score: str
    prediction_result: PredictionResult

# 事件发布
async def publish_match_completed(match: Match, result: MatchResult):
    event = MatchCompletedEvent(
        match_id=match.id,
        final_score=result.final_score,
        prediction_result=result.prediction_result
    )
    await event_bus.publish(event)

# 事件处理
@event_handler(MatchCompletedEvent)
async def update_predictions_on_match_completion(event: MatchCompletedEvent):
    # 更新相关预测的状态
    await prediction_repository.update_status(event.match_id, "completed")
```

## 🤖 机器学习开发

### ML Pipeline结构
```python
# 特征工程
src/ml/enhanced_feature_engineering.py

# 模型训练
src/ml/enhanced_xgboost_trainer.py
src/ml/enhanced_real_model_training.py
src/ml/lstm_predictor.py

# 预测管道
src/ml/football_prediction_pipeline.py

# 实验跟踪
src/ml/experiment_tracking.py

# 超参数优化
src/ml/xgboost_hyperparameter_optimization.py
src/ml/test_hyperparameter_optimization.py

# 性能监控
src/ml/model_performance_monitor.py
```

### 模型管理
- **MLflow** - 实验跟踪和版本控制
- **Optuna** - 超参数贝叶斯优化
- **模型注册** - 生产模型管理

### ML训练命令
```bash
# 训练XGBoost模型
python src/ml/enhanced_xgboost_trainer.py

# LSTM深度学习预测
python src/ml/lstm_predictor.py

# 超参数优化
python src/ml/xgboost_hyperparameter_optimization.py

# 完整预测管道
python src/ml/football_prediction_pipeline.py
```

## 📊 API访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws
- **Prometheus指标**: http://localhost:8000/api/v1/metrics

## 🐳 容器架构

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Frontend  │  │  Backend    │  │  Database   │
│   (React)   │  │  (FastAPI)  │  │(PostgreSQL) │
│  Port:3000  │  │  Port:8000  │  │  Port:5432  │
└─────────────┘  └─────────────┘  └─────────────┘
       │                │                │
       │       ┌─────────────┐          │
       │       │    Redis    │          │
       │       │  Port:6379  │          │
       │       └─────────────┘          │
       │                │                │
       └────────────────┼────────────────┘
                        │
              ┌─────────────┐
              │   Worker    │
              │  (Celery)   │
              └─────────────┘
                        │
              ┌─────────────┐
              │    Nginx    │
              │  Port: 80   │
              └─────────────┘
```

## 🔍 代码导航指南

### 快速定位文件
- **查找API路由**: 使用`Grep`搜索`@app.`或`@router.`模式
- **查找数据库模型**: `src/database/models/` 目录下的`Base`继承类
- **查找事件处理器**: `src/events/` 目录
- **查找CQRS命令**: `src/cqrs/commands/` 目录
- **查找CQRS查询**: `src/cqrs/queries/` 目录
- **查找ML模型**: `src/ml/` 目录下的`.pkl`或`.joblib`文件

### 关键文件位置
- **主应用入口**: `src/main.py` (27,349字节，应用生命周期管理)
- **API路由注册**: `src/api/v1.py` (路由和中间件注册)
- **数据库配置**: `src/database/connection.py` (异步SQLAlchemy 2.0+)
- **缓存配置**: `src/cache/redis_client.py` (Redis连接池)
- **Celery配置**: `src/tasks/celery_app.py` (7个专用队列)
- **测试配置**: `pytest.ini` 和 `tests/conftest.py`

### 项目统计信息
- **核心代码**: 1,094+ 行 (src根目录)
- **测试文件**: 239+ 个测试文件，385+ 个测试用例
- **配置文件**: 20+ Docker Compose配置
- **文档文件**: 完整的开发和部署文档
- **工具链**: 297行Makefile标准化命令

## 🔥 核心功能模块

### 预测系统
- **API路由**: `src/api/predictions/` (包含优化版本)
- **推理服务**: `src/services/inference_service.py` - 实时预测推理
- **模型加载**: 支持XGBoost和LSTM模型热加载
- **预测管道**: `src/ml/football_prediction_pipeline.py` - 完整ML流程

### 数据采集系统

#### 容器依赖关系
```yaml
# docker-compose.yml - 服务依赖管理
services:
  app:
    depends_on:
      db:
        condition: service_healthy    # 等待数据库健康检查
      redis:
        condition: service_started    # 等待Redis启动
    volumes:
      - ./src:/app/src                # 源码热重载
      - ./data:/app/data              # 数据目录挂载
      - ./models:/app/models          # ML模型文件挂载
```

#### FotMob数据采集架构
项目已完成FotMob数据采集的标准化重构：
- **核心类**: `FotmobBrowserScraper` - 使用Playwright进行浏览器自动化
- **API拦截**: 拦截真实的FotMob API响应，获取完整数据
- **数据导出**: 自动JSON格式导出到 `data/fotmob/` 目录
- **多种模式**: 支持单日、批量、日期范围采集
- **异步支持**: 完整的异步资源管理

#### 数据采集组件
- **外部适配器**: `src/adapters/` (FotMob等数据源)
- **数据收集器**: `src/collectors/` 和 `src/data/collectors/`
- **浏览器自动化**: `src/data/collectors/fotmob_browser.py` - Playwright反反爬虫机制
- **ETL管道**: `src/api/data_management.py` - 数据管理API
- **CLI工具**: `scripts/run_fotmob_scraper.py` - 数据采集脚本

### 数据采集工作流
```bash
# 1. 单日数据采集
python scripts/run_fotmob_scraper.py --date 2024-01-15

# 2. 批量数据采集
python scripts/run_fotmob_scraper.py --start-date 2024-01-01 --end-date 2024-01-31

# 3. 查看采集数据
ls -la data/fotmob/

# 4. 分析JSON结构
python scripts/inspect_json_structure.py data/fotmob/match_*.json

# 5. 集成到数据库
curl -X POST http://localhost:8000/api/v1/data/etl \
  -H "Content-Type: application/json" \
  -d '{"source": "fotmob", "action": "import"}'
```

### 性能监控
- **中间件**: `src/performance/middleware.py` - 性能监控中间件
- **监控API**: `src/api/monitoring.py` - 系统监控端点
- **Prometheus集成**: `/metrics` 端点导出监控指标
- **健康检查**: `/health`, `/health/system`, `/health/database`

### 缓存策略
- **多级缓存**: 内存 + Redis分布式缓存
- **缓存失效**: 智能TTL和主动失效
- **读写分离**: 支持数据库读写分离配置

### 实时通信
- **WebSocket**: `/api/v1/realtime/ws` - 实时数据推送
- **事件系统**: `src/events/` - 事件驱动架构
- **CQRS模式**: `src/cqrs/` - 命令查询责任分离

## 🚨 故障排除快速参考

| 问题类型 | 解决方案 |
|---------|---------|
| **测试失败** | `make test.fast` 查看核心功能，避免ML模型加载 |
| **CI超时** | 使用 `make test.unit.ci` 替代完整测试套件 |
| **端口冲突** | 检查 8000、3000、5432、6379 端口可用性 |
| **数据库问题** | 运行 `make db-migrate`，检查PostgreSQL状态 |
| **Redis连接问题** | `make redis-shell` 测试连接 |
| **内存不足** | 使用 `make test.fast` 避免ML相关测试 |
| **类型错误** | 检查导入，添加缺失类型注解 |
| **依赖问题** | 运行 `make rebuild` 重新构建镜像 |
| **ML模型加载失败** | 检查模型文件路径，查看`mlruns/`目录 |
| **Celery任务失败** | 查看日志`make logs`，检查Redis连接 |

## 🐳 Docker配置说明

### 可用Docker Compose配置
项目包含20+个Docker Compose配置文件，支持不同场景：

```bash
# 主要配置文件
docker-compose.yml              # 默认开发环境
docker-compose.dev.yml          # 纯开发环境
docker-compose.prod.yml         # 生产环境
docker-compose.ci.yml           # CI/CD环境
docker-compose.test.yml         # 测试环境
docker-compose.staging.yml      # 预发布环境

# 专用配置
config/docker-compose.microservices.yml  # 微服务架构
config/docker-compose.optimized.yml      # 性能优化版本
config/docker-compose.full-test.yml      # 完整测试环境
monitoring/docker-compose.monitoring.yml # 监控服务栈
```

### 服务端口映射
- **Frontend (React)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Nginx Proxy**: http://localhost:80
- **Flower (Celery监控)**: http://localhost:5555

## 🔄 CI/CD流程

### GitHub Actions工作流
- **ci_pipeline_v2.yml**: 主要CI流水线，支持Python 3.10/3.11/3.12
- **deploy.yml**: 部署流程
- **production-deploy.yml**: 生产环境部署
- **smart-fixer-ci.yml**: 智能修复和代码质量检查

### 本地CI验证
```bash
./ci-verify.sh              # 完整本地CI验证
./simulate_ci_in_dev.sh     # 模拟CI环境测试
```

## 📑 快速导航

### 核心命令速查
```bash
# 🚀 启动环境
make dev && make status          # 完整开发环境
make test.fast                   # 核心功能测试

# 🧪 测试命令
make test.unit.ci               # CI最小化验证
make coverage                   # 覆盖率报告

# 🔧 开发工具
make lint && make fix-code      # 代码质量
make shell                      # 进入容器
```

### 端口和服务
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **系统资源监控**: http://localhost:8000/health/system
- **数据库状态**: http://localhost:8000/health/database
- **推理服务状态**: http://localhost:8000/api/v1/health/inference
- **前端应用**: http://localhost:3000
- **Prometheus指标**: http://localhost:8000/api/v1/metrics
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws
- **Flower监控**: http://localhost:5555

### 应用启动流程
1. **容器启动**: `docker-compose up`
2. **数据库初始化**: 自动执行 Alembic 迁移
3. **智能冷启动**: 检查数据状态，自动触发数据采集
4. **服务注册**: API路由、事件系统、CQRS初始化
5. **健康检查**: 所有组件状态监控

## 📚 重要文档

### 核心文档
- **测试指南**: `docs/TESTING_GUIDE.md` - SWAT行动成果，完整测试方法论
- **覆盖率报告**: `TEST_COVERAGE_BASELINE_REPORT.md` - 29.0%基线提升路线图
- **Docker配置**: `DOCKER_README.md` - 容器化部署指南
- **CI流程**: `LOCAL_CI_GUIDE.md` - 本地CI验证指南
- **架构设计**: `docs/ARCHITECTURE_FOR_AI.md` - AI优先维护架构指南

### 专项指南
- **ML Ops部署**: `ML_OPS_DEPLOYMENT_GUIDE.md` - 机器学习运维指南
- **爬虫部署**: `CRAWLER_DEPLOYMENT_GUIDE.md` - FotMob数据采集指南
- **全栈升级**: `FULL_STACK_UPGRAGE_GUIDE.md` - 前端+后端集成
- **系统审计**: `SYSTEM_ROBUSTNESS_AUDIT_FINAL_REPORT.md` - 系统健壮性报告

### GitHub配置
- **代码评审**: `.github/CODEOWNERS` - 默认评审者 @xupeng211
- **PR模板**: `.github/pull_request_template.md` - 标准化提交流程
- **工作流**: `.github/workflows/` - CI/CD自动化 (支持Python 3.10/3.11/3.12)

## 💡 重要提醒

1. **测试黄金法则** - 始终使用 Makefile 命令，永远不要直接运行pytest
2. **异步优先** - 所有I/O操作必须使用async/await模式
3. **架构完整性** - 严格遵循DDD+CQRS+事件驱动架构
4. **环境一致性** - 使用Docker确保本地与CI环境一致
5. **服务健康** - 开发前先运行 `make status` 检查所有服务
6. **AI优先维护** - 项目采用AI辅助开发，优先考虑架构完整性和代码质量
7. **ML模型管理** - 所有机器学习相关代码位于`src/ml/`目录，使用MLflow进行版本控制

## 🎯 开发者必知

### 关键架构模式
- **应用启动**: 采用生命周期管理 (`lifespan` context manager)
- **智能冷启动**: 自动检查数据状态并触发采集任务
- **依赖注入**: 使用FastAPI的依赖注入系统
- **错误处理**: 统一异常处理和错误响应格式
- **中间件链**: 性能监控、CORS、国际化等中间件

### 数据采集特性
- **反反爬虫**: 使用浏览器自动化绕过网站限制
- **多数据源**: FotMob等足球数据API集成
- **数据质量**: 自动化数据验证和质量检查
- **增量更新**: 智能判断是否需要数据更新

### 性能优化
- **连接池**: 数据库连接池和Redis连接池
- **异步任务**: Celery任务队列处理后台作业
- **缓存策略**: 多级缓存和智能失效机制
- **监控集成**: Prometheus指标实时监控

---

**💡 记住**: 这是一个AI优先维护的企业级项目。优先考虑架构完整性、代码质量和全面测试。所有I/O操作必须是异步的，保持DDD层分离，并遵循既定模式。项目使用完整的工具链（297行Makefile + 20+ Docker配置）来确保开发流程标准化。

## 🔐 Git与代码管理

### 关键忽略规则 (来自 .gitignore)
```gitignore
# 字节码和缓存
__pycache__/
*.py[cod]
*$py.class

# 测试和覆盖率
.coverage
.htmlcov/
.pytest_cache/
.mypy_cache/

# 临时文件和报告
*TEMP*.md
*_REPORT_*.md
bandit*.json
coverage*.json
scripts/temp/

# AI生成文件
CLAUDE_*.md.bak
*_ANALYSIS.md
*_SUMMARY.md
```

### 代码评审流程
- **默认评审者**: @xupeng211 (所有路径)
- **专项评审**: 源码、测试、文档、CI流程分别指定
- **PR模板**: 标准化提交信息，包含测试验证清单
- **保护分支**: main分支受保护，需要评审通过

### 文件组织规范
- **报告文件**: 统一存储在 `reports/` 目录
- **临时脚本**: 存储在 `scripts/temp/` 目录
- **配置文件**: 集中管理，支持多环境 (dev/prod/ci/test)
- **文档目录**: 3368个文档文件，分类清晰

## 📈 项目健康度指标

| 指标 | 当前状态 | 目标状态 |
|------|---------|---------|
| 测试覆盖率 | 29.0% | 80%+ |
| 代码质量 | A+ (Ruff) | A+ 维持 |
| CI通过率 | 绿色基线 | 100%维持 |
| 测试数量 | 385个 | 500+ |
| 安全扫描 | Bandit通过 | 持续监控 |
| 文档覆盖 | 完整 | 持续更新 |

---

## 🎯 AI优先开发指南

### 核心开发理念
- **架构完整性优先** - 严格遵循DDD+CQRS+事件驱动架构
- **代码质量至上** - A+等级代码质量，29.0%测试覆盖率基线
- **异步编程强制** - 所有I/O操作必须使用async/await模式
- **环境一致性保障** - 使用Docker确保本地与CI环境完全一致
- **智能自动化** - AI辅助开发，优先考虑长期维护性

### 开发前必做检查
```bash
# 1. 检查服务健康状态
make status

# 2. 运行核心功能测试
make test.fast

# 3. 验证代码质量
make lint && make security-check

# 4. 提交前CI验证
make test.unit.ci
```

---

**📝 版本**: v1.0.0-rc1 (生产就绪) | **架构**: DDD+CQRS+Events | **质量**: A+ 等级 | **维护**: AI优先开发
