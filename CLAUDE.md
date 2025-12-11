# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌐 Language Preference

**IMPORTANT**: Please reply in Chinese (中文) for all communications in this repository. The user prefers Chinese responses for all interactions, including code explanations, documentation updates, and general discussions.

## 📋 Project Overview

**FootballPrediction** 是一个企业级足球预测系统，采用现代化全栈架构，集成了机器学习、数据采集、实时预测和事件驱动架构。

### 核心质量指标
- **测试覆盖率**: 29.0% (385+ 通过测试)
- **代码质量**: A+ (ruff评分)
- **安全等级**: 企业级
- **版本**: v4.0.1-hotfix (生产就绪)

### 关键项目定位
- **架构模式**: DDD (领域驱动设计) + CQRS (命令查询分离) + 事件驱动架构 + 异步优先
- **开发理念**: AI辅助维护优先，工具驱动开发，渐进式改进
- **质量标准**: 29.0%测试覆盖率硬性门槛，零容忍CI失败

## 🏗️ Tech Stack Architecture

### 后端技术栈
- **Web框架**: FastAPI 0.104+ (现代化异步Web框架)
- **数据库**: PostgreSQL 15 (主数据库) + Redis 7.0+ (缓存)
- **ORM**: SQLAlchemy 2.0+ (完全异步支持)
- **机器学习**: XGBoost 2.0+ + TensorFlow 2.18.0 + MLflow
- **任务调度**: Prefect 2.x + Celery Beat (混合调度架构)
- **容器化**: Docker 27.0+ + 多环境Docker Compose

### 前端技术栈
- **框架**: Vue.js 3.4.0 + Composition API
- **语言**: TypeScript 5.7.2 (完全类型安全)
- **构建工具**: Vite 5.0 (快速开发和构建)
- **状态管理**: Pinia 2.1.7 (Vuex现代替代品)
- **路由**: Vue Router 4.2.5
- **UI框架**: Tailwind CSS 3.3.6 (实用优先的CSS框架)
- **图表**: Chart.js 4.5.1 + vue-chartjs 5.3.3
- **HTTP客户端**: Axios 1.6.0 + vue-axios 3.5.2

## 🚀 Core Development Commands

### Environment Management
```bash
# 📍 重要提示：有两个CLAUDE.md文件：
# - /CLAUDE.md (根目录，AI维护的完整文档)
# - /FootballPrediction/CLAUDE.md (Docker开发环境文档)

# 📍 重要提示：Makefile位于 FootballPrediction/ 子目录中
cd FootballPrediction  # 首先进入包含Makefile的目录

# 完整Docker开发环境 (主要开发方式)
make dev              # 启动完整开发环境 (app + db + redis + frontend + nginx + worker + beat)
make dev-rebuild      # 重新构建镜像并启动开发环境
make dev-logs         # 查看开发环境日志
make dev-stop         # 停止开发环境
make status           # 检查所有服务状态
make clean            # 清理Docker资源和缓存
make quick-start      # 快速启动开发环境 (别名: dev)
make quick-stop       # 快速停止开发环境 (别名: dev-stop)

# 生产环境
make prod             # 启动生产环境 (使用 docker-compose.prod.yml)
make prod-rebuild     # 重新构建生产环境

# 容器管理和访问
make shell            # 进入后端容器终端
make shell-db         # 进入数据库容器
make db-shell         # 连接PostgreSQL数据库
make redis-shell      # 连接Redis
make logs             # 查看应用日志
make logs-db          # 查看数据库日志
make logs-redis       # 查看Redis日志

# 传统虚拟环境开发 (可选方式)
make install          # 在虚拟环境中安装依赖
make help             # 显示所有可用命令 ⭐
```

### Testing Commands (Docker环境优先)
```bash
# 🔥 Test Golden Rule - 在Docker容器中运行测试，本地开发可使用FootballPrediction/Makefile
# 重要提示：默认在Docker容器中运行测试，确保环境一致性

# Docker容器测试 (推荐方式)
make test             # 在容器中运行所有测试
make test.unit        # 在容器中运行单元测试
make test.integration # 在容器中运行集成测试
make test.all         # 在容器中运行所有测试
make coverage         # 在容器中生成覆盖率报告

# 传统测试命令 (需要本地环境)
make test.fast        # 快速核心测试 (API/Utils/Cache/Events only)
make test-fast        # 快速单元测试（开发日常使用）
make test.unit.ci     # CI验证 (极致稳定方案)
make test-coverage-local # 本地运行测试并生成覆盖率
make test-check-unit  # 检查单元测试状态（无输出，仅返回成功/失败）

# Running Single Tests (Docker方式 - 推荐)
# IMPORTANT: 服务必须先运行 (make dev)

# 在容器中运行特定测试模块
docker-compose exec app bash -c "cd /app && pytest tests/test_api_health.py -v"

# 在容器中运行特定模式测试
docker-compose exec app bash -c "cd /app && pytest tests/test_utils/ -v"

# 在容器中运行特定文件的覆盖率测试
docker-compose exec app bash -c "cd /app && pytest tests/test_collectors/test_fotmob_adapter.py --cov=src.collectors.fotmob -v"

# CI模式测试 (Mock外部依赖)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
docker-compose exec app bash -c "cd /app && pytest tests/unit/ -v"
```

### Code Quality (Docker环境优先)
```bash
# Docker容器代码质量检查 (推荐方式)
make lint             # 在容器中运行代码检查 (Ruff + MyPy)
make fix-code         # 在容器中运行代码自动修复
make format           # 在容器中运行代码格式化 (ruff format)
make type-check       # 在容器中运行类型检查
make security-check   # 在容器中运行安全扫描

# 传统代码质量检查 (需要本地环境)
make ci               # 完整CI验证
make prepush          # 完整提交前验证

# 快速优化脚本
./quick_optimize.sh   # 快速优化代码质量 (一键修复所有问题)
```

### Database Management
```bash
make db-reset         # Reset database (⚠️ will delete all data)
make db-migrate       # Run database migrations
make db-shell         # Enter PostgreSQL interactive terminal
make redis-shell      # Enter Redis CLI (for cache debugging)
```

### Frontend Development
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Test production build locally
npm run lint         # ESLint code checking
npm run type-check   # TypeScript type checking
```

### 前端冒烟测试
```bash
cd frontend
node scripts/frontend_smoke_test.cjs  # 前端冒烟测试
```

### 前端开发最佳实践
```bash
# 推荐的开发工作流 (双终端)
# 终端1: 启动开发服务器
npm run dev

# 终端2: 实时类型检查
npm run type-check -- --watch  # 实时TypeScript类型检查和错误提示

# 开发循环
npm run lint -- --fix          # 自动修复ESLint问题
npm run type-check             # 检查TypeScript类型
# 进行代码修改...

# 提交前验证
npm run lint && npm run type-check && npm run build
```

### 前端开发服务器配置
- **开发端口**: 5173
- **生产端口**: 80 (通过Nginx代理)
- **API代理**: /api -> http://localhost:8000
- **构建工具**: Vite 5.0
- **路径别名**: @/* -> ./src/*
- **TypeScript**: 严格模式，完整类型安全

### Data Collection Commands
```bash
# L1/L2 数据采集系统 (核心业务功能)
make run-l1              # L1赛季数据采集
make run-l2              # L2详情数据采集 (HTML解析)
make run-l2-api          # L2 API详情数据采集

# 调度系统管理 (v2.5+)
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d
curl http://localhost:4200  # Prefect UI
curl http://localhost:5555  # Flower UI
curl http://localhost:5000  # MLflow UI
```

## 🏗️ Architecture Patterns

### 1. DDD (Domain-Driven Design) 领域驱动设计
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

### 2. CQRS (Command Query Responsibility Segregation)
**位置**: `/src/cqrs/`

核心组件：
- **Commands**: 写操作命令定义
- **Queries**: 读操作查询定义
- **Handlers**: 命令和查询处理器
- **Event Bus**: 事件驱动通信
- **DTOs**: 数据传输对象

### 3. Event-Driven Architecture
**位置**: `/src/events/`

- **Event Bus**: 事件总线实现
- **Event Handlers**: 事件处理器
- **Domain Events**: 领域事件定义
- **Integration Events**: 集成事件

### 4. Async First Architecture
```python
# 所有I/O操作使用async/await
async def fetch_match_data(match_id: str) -> MatchData:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/matches/{match_id}")
        return MatchData.model_validate(response.json())
```

## 📊 Data Collection Architecture

### L1/L2/L3 Data Pipeline
```
L1: 赛程数据采集 (基础数据)
├── 比赛时间、对阵双方
├── 联赛信息
└── 基础比赛数据

L2: 详情数据采集 (深度数据)
├── xG期望进球数据
├── 射门分布图
├── 裁判和天气信息
└── 实时赔率数据

L3: 特征工程 (ML特征)
├── 历史战绩统计
├── 球队状态指标
├── 球员表现数据
└── 14个核心ML特征
```

### 数据采集关键规则
- **🚫 严禁Playwright**: 禁止任何浏览器自动化
- **✅ HTTP-Only**: 必须使用HTTP API
- **🔐 认证必需**: x-mas和x-foo头部认证
- **🔄 限流保护**: RateLimiter + 指数退避
- **🎭 UA轮换**: 移动端/桌面端User-Agent混合

## 🗄️ Database Architecture

### 核心表结构
```sql
-- 比赛表 (核心实体)
matches (
    id UUID PRIMARY KEY,
    fotmob_id VARCHAR UNIQUE,
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),
    match_date TIMESTAMP,
    home_xg FLOAT,              -- 主队期望进球
    away_xg FLOAT,              -- 客队期望进球
    data_completeness VARCHAR,  -- 'partial'|'complete'
    created_at TIMESTAMP DEFAULT NOW()
)

-- 球队表
teams (
    id UUID PRIMARY KEY,
    name VARCHAR UNIQUE,
    fotmob_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### 数据库访问模式
- **统一异步管理器**: `src/database/async_manager.py`
- **Repository模式**: 数据访问抽象
- **连接池管理**: PostgreSQL连接池优化
- **事务管理**: 自动事务回滚

## 🧠 Machine Learning Architecture

### ML Pipeline Components
**位置**: `/src/inference/`, `/src/ml/`

```python
# 核心推理服务
class InferenceService:
    async def predict_match(self, match_id: str) -> PredictionResult:
        features = await self.feature_builder.build_features(match_id)
        prediction = await self.model.predict(features)
        return prediction
```

### Feature Store
- **实时特征**: 当前赛季数据
- **历史特征**: 多赛季统计
- **派生特征**: 14个核心特征
- **数据质量监控**: 异常检测和数据验证

## 🐳 Containerization & Services

### Docker Services Architecture
```yaml
# 开发环境完整服务栈 (docker-compose.yml)
services:
  app:                 # FastAPI主应用 (8000)
  frontend:            # React/Vue.js前端应用 (3000, 3001)
  db:                  # PostgreSQL 15 (5432)
  redis:               # Redis缓存 (6379)
  nginx:               # 反向代理 (80)
  worker:              # Celery异步任务处理
  beat:                # Celery定时任务调度
  data-collector:      # 专用数据采集服务
  data-collector-l2:   # L2深度数据采集器

# 生产环境扩展服务 (docker-compose.prod.yml)
  prometheus:          # 指标收集和存储 (9090)
  grafana:             # 可视化仪表板 (3000)
  loki:                # 日志聚合 (3100)
```

### Multi-Environment Support
```bash
# 开发环境 (主要开发方式)
docker-compose.yml                    # 完整开发栈 - app + db + redis + frontend + nginx + worker + beat

# 生产环境
docker-compose.prod.yml               # 生产优化栈 - app + db + redis + nginx + monitoring + logging

# 其他环境配置文件 (在FootballPrediction/目录中)
docker-compose.dev.yml                # 开发环境配置
docker-compose.lightweight.yml        # 轻量级开发环境
docker-compose.microservices.yml     # 微服务架构
docker-compose.full-test.yml         # 完整测试环境
docker-compose.staging.yml           # 预发环境
docker-compose.verify.yml            # 本地验证环境
docker-compose.optimized.yml         # 优化配置
docker-compose.scheduler.yml         # 调度系统 (如启用)
```

## 🔄 Monitoring & Observability (v2.5+)

### Enterprise Monitoring UIs
```bash
# ML and Task Monitoring
http://localhost:4200  # Prefect UI - Workflow orchestration
http://localhost:5555  # Flower UI - Celery task monitoring
http://localhost:5000  # MLflow UI - ML experiment tracking

# Production Monitoring (when running production environment)
http://localhost:9090  # Prometheus - 指标收集和存储
http://localhost:3000  # Grafana - 可视化仪表板 (生产模式下)
http://localhost:3100  # Loki - 日志聚合
```

### 调度系统管理 (v2.5+)
```bash
# 启动包含调度器的完整服务栈
cd FootballPrediction  # 进入包含docker-compose的目录
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d

# 验证调度服务
curl http://localhost:4200  # Prefect UI
curl http://localhost:5555  # Flower UI
curl http://localhost:5000  # MLflow UI

# 检查调度状态
docker-compose ps
```

### Health Checks
```bash
curl http://localhost:8000/health           # Basic health check
curl http://localhost:8000/health/system    # System resources check
curl http://localhost:8000/health/database  # Database connectivity
curl http://localhost:8000/api/v1/metrics   # Prometheus metrics
curl http://localhost:8000/api/v1/health/inference # Inference service health
```

### 服务状态验证
```bash
# 后端服务验证
curl http://localhost:8000/health           # 基础健康检查
curl http://localhost:8000/health/system    # 系统资源检查
curl http://localhost:8000/api/v1/metrics   # Prometheus指标

# 前端服务验证 (React)
curl http://localhost:3000                  # 前端开发服务器 (React)
curl http://localhost:3001                  # 前端开发服务器 (备用端口)
curl http://localhost:80                    # 前端生产服务器 (通过Nginx)

# Docker容器监控
make monitor            # 实时监控应用资源使用
make monitor-all        # 监控所有容器资源使用
```

## 🧪 Testing Strategy

### Test Environment Configuration
```bash
# Development testing (default)
make test.fast        # Core functionality only

# CI Environment Testing (Required for CI)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true
make test.unit.ci     # Minimal verification for CI (fastest)
```

### 测试覆盖率要求 (v4.0.1-hotfix)
- **当前覆盖率**: 29.0% (385+ 通过测试，已达生产标准)
- **最低覆盖率**: 29.0%+ (CI将在此阈值以下失败)
- **测试分层**: 单元测试 (85%) + 集成测试 (12%) + 端到端测试 (2%) + 性能测试 (1%)
- **异步测试支持**: asyncio_mode = auto
- **超时设置**: 300秒
- **ML Mock模式**: 强制启用（除非TEST_REAL_ML=true）
- **CI优化**: test.unit.ci 使用极致内存优化，确保CI稳定性

### 详细测试标记体系 (config/pytest.ini)
```python
# 核心测试类型标记
@pytest.mark.unit           # 单元测试 - 测试单个函数或类 (85% of tests)
@pytest.mark.integration    # 集成测试 - 测试多个组件的交互 (12% of tests)
@pytest.mark.e2e           # 端到端测试 - 完整的用户流程测试 (2% of tests)
@pytest.mark.performance   # 性能测试 - 基准测试和性能分析 (1% of tests)

# 功能域标记
@pytest.mark.api           # API测试 - 测试HTTP端点和接口
@pytest.mark.domain        # 领域层测试 - 业务逻辑和算法测试
@pytest.mark.business      # 业务规则测试 - 业务逻辑和规则引擎
@pytest.mark.services      # 服务层测试 - 业务服务和数据处理
@pytest.mark.database      # 数据库测试 - 需要数据库连接
@pytest.mark.cache         # 缓存相关测试 - Redis和缓存逻辑
@pytest.mark.auth          # 认证相关测试 - JWT和权限验证
@pytest.mark.monitoring    # 监控相关测试 - 指标和健康检查
@pytest.mark.streaming     # 流处理测试 - Kafka和实时数据
@pytest.mark.collectors    # 收集器测试 - 数据收集和抓取模块
@pytest.mark.middleware    # 中间件测试 - 请求处理和管道组件
@pytest.mark.utils         # 工具类测试 - 通用工具和辅助函数
@pytest.mark.core          # 核心模块测试 - 配置、依赖注入、基础设施
@pytest.mark.decorators    # 装饰器测试 - 各种装饰器功能和性能测试
@pytest.mark.ml            # 机器学习测试 - ML模型训练、预测和评估测试

# 执行特征标记
@pytest.mark.slow          # 慢速测试 - 运行时间较长的测试 (>30s)
@pytest.mark.smoke         # 冒烟测试 - 基本功能验证
@pytest.mark.critical      # 关键测试 - 必须通过的核心功能测试
@pytest.mark.regression    # 回归测试 - 验证修复的问题不会重现
@pytest.mark.metrics       # 指标和度量测试 - 性能指标和进展验证
@pytest.mark.external_api  # 需要外部API调用
@pytest.mark.docker        # 需要Docker容器环境
@pytest.mark.network       # 需要网络连接
```

### Smart Tests 优化配置
- **核心稳定测试模块**: tests/unit/utils, tests/unit/cache, tests/unit/core
- **排除的问题测试文件**: 自动识别并排除不稳定的测试
- **性能优化配置**: 排除慢速测试，设置合理的最大失败数
- **覆盖率报告**: 生成HTML和XML格式的覆盖率报告

### CI环境变量配置
```bash
# 必需的环境变量
export FOOTBALL_PREDICTION_ML_MODE=mock      # ML模型Mock模式
export SKIP_ML_MODEL_LOADING=true            # 跳过ML模型加载
export INFERENCE_SERVICE_MOCK=true           # 推理服务Mock
export TEST_REAL_ML=false                    # 禁用真实ML测试
```

### Test Layers
- **单元测试 (85%)**: 快速、隔离、无外部依赖
- **集成测试 (12%)**: 数据库、Redis、API集成
- **端到端测试 (2%)**: 完整业务流程
- **性能测试 (1%)**: 负载、压力测试

## 🎨 Frontend Development Workflow

### React + TypeScript Development (现代前端技术栈)
```bash
# 1️⃣ Initialize frontend development environment
cd frontend
npm install

# 2️⃣ Start development with real-time validation
npm run dev           # Terminal 1: Development server (http://localhost:3000)
npm run type-check -- --watch  # Terminal 2: Real-time type checking

# 3️⃣ Development cycle
npm run lint -- --fix          # Auto-fix ESLint issues
npm run type-check             # Check TypeScript types
# Make changes to components...

# 4️⃣ Pre-build validation
npm run lint && npm run type-check && npm run build

# 5️⃣ Production deployment
npm run build       # Build for production
npm run preview     # Test production build locally
```

### Frontend Project Structure (React架构)
```
frontend/
├── src/
│   ├── components/            # React组件
│   │   ├── auth/              # 认证相关组件
│   │   ├── charts/            # 图表组件 (Chart.js + React-Chartjs)
│   │   ├── match/             # 比赛相关组件
│   │   └── profile/           # 用户资料组件
│   ├── pages/                 # 页面组件
│   │   ├── auth/              # 认证页面
│   │   ├── admin/             # 管理页面
│   │   └── match/             # 比赛页面
│   ├── hooks/                 # 自定义React hooks
│   ├── store/                 # Redux Toolkit配置
│   │   └── index.ts           # Redux store配置
│   ├── services/              # API服务函数
│   ├── types/                 # TypeScript类型定义
│   ├── utils/                 # 前端工具函数
│   ├── styles/                # CSS和样式
│   ├── App.tsx                # 根组件
│   └── main.tsx               # 应用入口
├── public/                    # 静态资源
├── tests/                     # 前端测试文件
├── package.json               # 依赖配置
├── vite.config.ts            # Vite构建配置
├── tsconfig.json             # TypeScript配置
└── scripts/                  # 前端工具脚本
```

### 前端技术栈详情
- **React 19.2.0**: 现代React，支持并发特性
- **TypeScript 4.9.5**: 完整类型安全，严格模式
- **Ant Design 5.27.6**: 企业级组件库
- **Redux Toolkit 2.9.2**: 状态管理，包含RTK Query
- **React Query**: 服务端状态管理和缓存
- **Vite**: 快速构建工具，支持HMR

## 🔧 Critical Development Rules

### 1. FotMob Data Collection (Critical)
- **🚫 NEVER use Playwright or browser automation** - HTTP requests only
- **✅ Always use rate limiting** - `src/collectors/rate_limiter.py`
- **🔐 Proper authentication required** - x-mas and x-foo headers mandatory
- **🔄 Rotate User-Agents** - Mix mobile/desktop patterns
- **🌐 Proxy configuration** - WSL environments use Clash proxy at `host.docker.internal:7890`

### 2. Database Operations (Mandatory)
- **📌 Always use `src/database/async_manager.py`** - "One Way to do it" principle
- **🚫 NEVER use `src/database/connection.py`** - Deprecated interface
- **⚡ All operations must be async** - Use `async/await` consistently
- **🔒 Use proper session management** - Context managers or dependency injection
- **🏗️ Database roles** - READER/WRITER roles for access control

### 3. Testing Protocol (Non-negotiable)
- **🛡️ ALWAYS use Makefile commands** - Never pytest directly on files
- **🎯 Mock all external dependencies** - Database, network, filesystem
- **📊 Maintain 29.0%+ coverage** - CI will fail below this threshold
- **⚡ Use mock ML mode in CI** - Set `FOOTBALL_PREDICTION_ML_MODE=mock`
- **🔧 Test environment setup** - Docker required for consistent testing
- **📋 Test layers** - Unit (85%) + Integration (12%) + E2E (2%) + Performance (1%)

### 4. Architecture Integrity (Enterprise Standards)
- **🏗️ Follow DDD patterns** - Domain layer purity essential
- **📡 Implement CQRS separation** - Commands vs queries distinct
- **🔄 Event-driven communication** - Use event system for loose coupling
- **🎯 Type safety mandatory** - Complete type annotations required
- **🏛️ Clean Architecture** - Layer separation with dependency inversion

### 5. Frontend Development Standards
- **🎨 Use React with TypeScript** - Modern React with functional components and hooks
- **📝 TypeScript mandatory** - All new code must have proper type definitions
- **📦 Follow React patterns** - Use functional components with hooks, avoid class components
- **🎯 Redux Toolkit for state management** - Use Redux Toolkit with RTK Query for server state
- **🔧 Development workflow** - Separate terminal for `npm run dev` and `npm run type-check -- --watch`

## 🔍 Code Navigation Guide

### Quick File Location
- **Find API routes**: Search for `@app.` or `@router.` patterns
- **Find database models**: `src/database/models/` directory - classes inheriting from `Base`
- **Find event handlers**: `src/events/` directory
- **Find CQRS commands**: `src/cqrs/commands/` directory
- **Find CQRS queries**: `src/cqrs/queries/` directory
- **Find ML models**: `.pkl` or `.joblib` files in `src/ml/` directory
- **Find data adapters**: `src/adapters/` directory (FotMob external data sources)
- **Find data collectors**: `src/collectors/` directory

### Key File Locations
- **Main application entry**: `src/main.py` (application lifecycle management, smart cold start)
- **API route registration**: Router files in each API submodule
- **Database configuration**: `src/database/async_manager.py` (new unified interface)
- **Cache configuration**: `src/cache/redis_client.py` (Redis connection pool)
- **Celery configuration**: `src/tasks/celery_app.py`
- **Test configuration**: `pytest.ini` and `tests/conftest.py`
- **Performance monitoring**: `src/performance/middleware.py`
- **Health checks**: `src/api/health/` directory
- **External adapters**: `src/adapters/factory.py` (data source factory pattern)
- **Inference service**: `src/inference/` (ML inference service)
- **Quality monitoring**: `src/quality_dashboard/` (data quality monitoring)
- **System monitoring**: `src/monitoring/` (performance monitoring)
- **Internationalization**: `src/locales/` (i18n configuration)

## 🚨 Troubleshooting

### Common Issues and Solutions

#### FotMob API Authentication Failures
```bash
# Symptom: HTTP 403 errors from FotMob API
# Solution:
python scripts/refresh_fotmob_tokens.py
# Verify environment variables:
cat .env | grep FOTMOB
```

#### Docker Port Conflicts
```bash
# Symptom: "port already allocated" errors
# Solution:
lsof -i :8000  # Check port usage
kill -9 <PID>  # Kill conflicting processes
# Or modify ports in docker-compose.yml
```

#### Test Failures in CI
```bash
# Use mock mode for CI testing
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
make test.unit.ci     # Fastest CI verification
```

#### Database Connection Issues
```bash
make db-migrate      # Run pending migrations
make db-shell        # Check PostgreSQL status
docker-compose exec db pg_isready
```

#### Frontend Development Issues
```bash
cd frontend
npm install          # Reinstall dependencies
rm -rf node_modules package-lock.json && npm install  # Clean install
npm run type-check   # Check TypeScript errors
```

## 📈 Performance Optimization

### Key Optimization Strategies
- **异步I/O**: 全链路异步处理
- **连接池**: 数据库和Redis连接复用
- **缓存策略**: 多层缓存(Redis + 应用缓存)
- **数据库优化**: 索引优化和查询优化
- **CDN集成**: 静态资源加速

## 💡 Important Reminders

1. **Test Golden Rule** - Always use Makefile commands, never run pytest directly
2. **Async First** - All I/O operations must use async/await pattern
3. **Architectural Integrity** - Strictly follow DDD+CQRS+Event-Driven architecture
4. **Environment Consistency** - Use Docker to ensure local and CI environments match
5. **Service Health** - Run `make status` to check all services before development
6. **Frontend Development** - Use separate terminal for frontend dev server
7. **AI-Assisted Maintenance** - Project uses AI-assisted development workflows
8. **Coverage Requirement** - Maintain minimum 29.0% test coverage for CI to pass
9. **Security First** - Run `make security-check` before committing changes
10. **Use `make help`** - Shows all available commands with descriptions - most useful command for newcomers

## 🔒 Security Best Practices

### Enterprise Security Measures
- **HTTP安全头**: CSP、HSTS、XSS防护
- **认证授权**: JWT + 基于角色的访问控制
- **输入验证**: Pydantic数据验证
- **SQL注入防护**: SQLAlchemy ORM保护
- **安全审计**: bandit自动化扫描
- **密钥管理**: 环境变量化配置

### Security Commands
```bash
make security-check                             # Run bandit security scan
pip-audit                                       # Check for vulnerable Python packages
cd frontend && npm audit                       # Check frontend vulnerabilities
grep -r -i "password\|secret\|token\|key" src/ --include="*.py" | grep -v "test"
```

---

## 🚀 Quick Start for New Developers

### 第一步：环境验证 (5分钟)
```bash
# 1. 确保Docker运行
docker --version && docker-compose --version

# 2. 克隆并进入项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 3. 进入包含Makefile的子目录
cd FootballPrediction  # 📍 重要：Makefile在此目录中

# 4. 启动完整开发环境 (Docker方式)
make dev && make status

# 5. 验证后端服务
curl http://localhost:8000/health
```

### 第二步：前端开发环境 (React)
```bash
# 1. 进入前端目录 (从项目根目录)
cd frontend  # 直接从根目录进入frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器 (新终端)
npm run dev

# 4. 验证前端服务 (React开发服务器)
curl http://localhost:3000
```

### 第三步：开发工作流
```bash
# 1. Docker容器测试验证环境正常
cd FootballPrediction
make test && make lint

# 2. 代码质量快速修复
make fix-code && make format

# 3. 提交前验证 (必须执行)
make security-check && make coverage

# 4. 查看所有可用命令
make help  # ⭐ 最有用的命令

# 5. 高级开发 (可选)
make test.unit          # 单元测试
make monitor            # 监控容器资源使用
./quick_optimize.sh     # 快速优化代码质量
```

## 📝 Development Workflow Summary

### Daily Development Process (Docker优先)
```bash
# 1. 进入项目目录并启动完整Docker环境
cd FootballPrediction  # 📍 重要：进入包含Makefile的目录
make dev && make status

# 2. 验证服务可访问性
curl http://localhost:8000/health           # 后端API
curl http://localhost:3000                  # 前端React

# 3. 运行Docker容器测试确保环境正常
make test && make lint

# 4. 开发过程中 (Docker容器中)
make fix-code              # 代码质量自动修复
make format                # 代码格式化

# 5. 提交前验证 (必须执行)
make security-check && make coverage

# 6. 前端开发 (并行进行，新终端)
cd frontend
npm run dev               # 启动React开发服务器
npm run type-check -- --watch  # 实时TypeScript类型检查
```

### 关键服务访问地址
```bash
# 开发环境访问
http://localhost:8000          # FastAPI后端服务
http://localhost:8000/docs     # API交互式文档
http://localhost:3000          # React前端开发服务器
http://localhost:80            # 生产前端 (通过Nginx代理)

# 监控和管理界面
http://localhost:4200          # Prefect UI - 工作流编排
http://localhost:5555          # Flower UI - Celery任务监控
http://localhost:5000          # MLflow UI - ML实验跟踪

# 生产环境监控 (启动生产环境时可用)
http://localhost:9090          # Prometheus - 指标存储
http://localhost:3000          # Grafana - 监控仪表板
```

### 项目核心特性总结
- ✅ **Docker优先开发**: 完整容器化开发环境，确保一致性
- ✅ **React现代前端**: React 19.2.0 + TypeScript + Redux Toolkit
- ✅ **企业级后端**: FastAPI + SQLAlchemy + Redis + PostgreSQL
- ✅ **机器学习流水线**: XGBoost预测模型，MLflow实验跟踪
- ✅ **完整测试体系**: 385+ 测试用例，29.0%+ 覆盖率
- ✅ **生产级监控**: Prometheus + Grafana + 结构化日志
- ✅ **自动化CI/CD**: GitHub Actions，代码质量自动检查

This system represents modern full-stack application development best practices, integrating machine learning, real-time data processing, and enterprise-grade architecture patterns. It's a mature, production-ready football prediction system with Docker-first development workflow.