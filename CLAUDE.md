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

## 🏗️ Tech Stack Architecture

### 后端技术栈
- **Web框架**: FastAPI 0.104+ (现代化异步Web框架)
- **数据库**: PostgreSQL 15 (主数据库) + Redis 7.0+ (缓存)
- **ORM**: SQLAlchemy 2.0+ (完全异步支持)
- **机器学习**: XGBoost 2.0+ + TensorFlow 2.18.0 + MLflow
- **任务调度**: Prefect 2.x + Celery Beat (混合调度架构)
- **容器化**: Docker 27.0+ + 多环境Docker Compose

### 前端技术栈
- **框架**: Vue.js 3 + Composition API
- **语言**: TypeScript 5.0+ (完全类型安全)
- **构建工具**: Vite 5.0 (快速开发和构建)
- **状态管理**: Pinia (Vuex现代替代品)
- **路由**: Vue Router 4
- **UI框架**: Tailwind CSS (实用优先的CSS框架)
- **图表**: Chart.js + vue-chartjs

## 🚀 Core Development Commands

### Environment Management
```bash
make dev              # Start full development environment (app + db + redis + nginx)
make dev-rebuild      # Rebuild images and start development environment
make dev-stop         # Stop development environment
make dev-logs         # View development environment logs
make status           # Check all service status
make clean            # Cleanup containers and cache
make shell            # Enter backend container
make shell-db         # Enter database container
make install          # Install dependencies in virtual environment
make help             # Show all available commands with descriptions ⭐
```

### Testing Commands
```bash
# 🔥 Test Golden Rule - Never run pytest directly! Always use Makefile commands
make test.fast        # Quick core tests (API/Utils/Cache/Events only)
make test-fast        # 快速单元测试（开发日常使用）
make test.unit        # Unit tests (278+ test files)
make test.unit.ci     # CI verification (ultimate stable solution)
make test.integration # Integration tests
make test.all         # Run all tests including slow ones
make coverage         # Generate coverage report
make test-coverage-local # Run tests with coverage locally
```

### Running Single Tests (Correct Way)
```bash
# IMPORTANT: Services must be running first (make dev)

# Run specific test module (use path relative to project root)
docker-compose exec app bash -c "cd /app && pytest tests/test_api_health.py -v"

# Run tests with specific pattern
docker-compose exec app bash -c "cd /app && pytest tests/test_utils/ -v"

# Run with coverage for specific file
docker-compose exec app bash -c "cd /app && pytest tests/test_collectors/test_fotmob_adapter.py --cov=src.collectors.fotmob -v"

# Run tests in CI mode (mock external dependencies)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
docker-compose exec app bash -c "cd /app && pytest tests/unit/ -v"
```

### Code Quality
```bash
make lint             # Code checking with ruff
make fix-code         # Auto-fix code issues with ruff
make format           # Code formatting with ruff
make security-check   # Security scanning with bandit
make ci               # Complete CI verification
make type-check       # MyPy type checking
make prepush          # Complete pre-push validation
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

### 前端开发服务器配置
- **开发端口**: 5173
- **生产端口**: 80 (通过Nginx代理)
- **API代理**: /api -> http://localhost:8000
- **构建工具**: Vite 5.0
- **路径别名**: @/* -> ./src/*

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
services:
  app:                 # FastAPI主应用 (8000)
  db:                  # PostgreSQL 15 (5432)
  redis:               # Redis缓存 (6379)
  frontend:            # Vue.js前端应用 (3000)
  nginx:               # 反向代理 (80)
  worker:              # Celery异步任务处理
  beat:                # Celery定时任务调度
  data-collector:      # 专用数据采集服务
  data-collector-l2:   # L2深度数据采集器
```

### Multi-Environment Support
- **开发环境**: `docker-compose.yml`
- **生产环境**: `docker-compose.prod.yml`
- **前端服务**: `docker-compose.frontend.yml`
- **调度系统**: `docker-compose.scheduler.yml`

## 🔄 Monitoring & Observability (v2.5+)

### Enterprise Monitoring UIs
```bash
http://localhost:4200  # Prefect UI - Workflow orchestration
http://localhost:5555  # Flower UI - Celery task monitoring
http://localhost:5000  # MLflow UI - ML experiment tracking
```

### 调度系统管理 (v2.5+)
```bash
# 启动包含调度器的完整服务栈
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
curl http://localhost:8000/api/v1/metrics   # Prometheus metrics
```

### 服务状态验证
```bash
# 后端服务验证
curl http://localhost:8000/health           # 基础健康检查
curl http://localhost:8000/health/system    # 系统资源检查
curl http://localhost:8000/api/v1/metrics   # Prometheus指标

# 前端服务验证
curl http://localhost:5173                  # 前端开发服务器
curl http://localhost:80                    # 前端生产服务器 (通过Nginx)
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

### 测试覆盖率要求
- **最低覆盖率**: 29.0%+ (CI将在此阈值以下失败)
- **测试分层**: 单元测试 (85%) + 集成测试 (12%) + 端到端测试 (2%) + 性能测试 (1%)
- **异步测试支持**: asyncio_mode = auto
- **超时设置**: 300秒
- **ML Mock模式**: 强制启用（除非TEST_REAL_ML=true）

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

### Vue.js 3 + TypeScript Development
```bash
# 1️⃣ Initialize frontend development environment
cd frontend
npm install

# 2️⃣ Start development with real-time validation
npm run dev           # Terminal 1: Development server
npm run type-check -- --watch  # Terminal 2: Real-time type checking

# 3️⃣ Development cycle
npm run lint -- --fix          # Auto-fix linting issues
npm run type-check             # Check TypeScript types
# Make changes to components...

# 4️⃣ Pre-build validation
npm run lint && npm run type-check && npm run build

# 5️⃣ Production deployment
npm run build       # Build for production
npm run preview     # Test production build locally
```

### Frontend Project Structure
```
frontend/
├── src/
│   ├── api/                    # API客户端
│   │   └── client.ts          # Axios HTTP客户端配置
│   ├── components/            # Vue组件
│   │   ├── auth/              # 认证相关组件
│   │   ├── charts/            # 图表组件 (Chart.js + vue-chartjs)
│   │   ├── match/             # 比赛相关组件
│   │   └── profile/           # 用户资料组件
│   ├── composables/           # Vue 3 Composition API
│   │   └── useApi.ts          # API调用组合式函数
│   ├── layouts/               # 页面布局
│   ├── router/                # 路由配置
│   │   └── index.ts           # Vue Router 4配置
│   ├── stores/                # Pinia状态管理
│   │   └── auth.ts            # 认证状态管理
│   ├── types/                 # TypeScript类型定义
│   ├── views/                 # 页面视图
│   │   ├── auth/              # 认证页面
│   │   ├── admin/             # 管理页面
│   │   └── match/             # 比赛页面
│   ├── App.vue                # 根组件
│   └── main.ts                # 应用入口
├── package.json               # 依赖配置
├── vite.config.ts            # Vite构建配置
├── tsconfig.json             # TypeScript配置
├── tailwind.config.js        # Tailwind CSS配置
└── scripts/                  # 前端工具脚本
```

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
- **🎨 Use Vue 3 Composition API** - Prefer Composition API over Options API
- **📝 TypeScript mandatory** - All new code must have proper type definitions
- **📦 Follow component structure** - Use `<script setup lang="ts">` syntax
- **🎯 Pinia for state management** - Use Pinia stores for application state
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
git clone <repository-url>
cd FootballPrediction

# 3. 启动开发环境
make dev && make status

# 4. 验证后端服务
curl http://localhost:8000/health
```

### 第二步：前端开发环境
```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器 (新终端)
npm run dev

# 4. 验证前端服务
curl http://localhost:5173
```

### 第三步：开发工作流
```bash
# 1. 运行测试确保环境正常
make test-fast

# 2. 代码质量检查
make lint && make fix-code

# 3. 提交前验证 (必须执行)
make test.unit.ci && make security-check

# 4. 查看所有可用命令
make help  # ⭐ 最有用的命令
```

## 📝 Development Workflow Summary

### Daily Development Process
```bash
# 1. 启动环境并验证服务
make dev && make status

# 2. 验证API可访问性
curl http://localhost:8000/health

# 3. 运行核心测试确保环境正常
make test-fast

# 4. 开发过程中
make lint && make fix-code  # 代码质量检查和修复

# 5. 提交前验证 (必须执行)
make test.unit.ci && make security-check
```

This system represents modern full-stack application development best practices, integrating machine learning, real-time data processing, and enterprise-grade architecture patterns. It's a mature, production-ready football prediction system.