# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌐 Language Preference

**IMPORTANT**: Please reply in Chinese (中文) for all communications in this repository. The user prefers Chinese responses for all interactions, including code explanations, documentation updates, and general discussions.

## 📋 Latest Updates (2025-12-07)

### v2.5.0 Backend Complete
- **Complete Backend Architecture v2.5**: 16 services, 29.0% test coverage achieved
- **Prefect + Celery Scheduler**: Enterprise-grade task orchestration with MLflow integration
- **Vue.js 3 Frontend Migration**: Complete migration from React to Vue.js + Vite
- **Enhanced Monitoring**: Prefect UI, MLflow tracking, and quality dashboard

### v2.1.0 Quality Improvements
- **Updated Quality Metrics**: Real coverage increased from 6.5% to 29.0% (target achieved)
- **Enhanced FotMob Guidelines**: Added critical HTTP-only policy and authentication requirements
- **Database Interface Clarification**: Stronger emphasis on async_manager.py usage
- **Critical Development Rules**: Added non-negotiable protocol section
- **Architecture Pattern Updates**: Refined DDD+CQRS+Event-Driven guidance

## 📑 Table of Contents

- [🌟 Quick Start](#-quick-start)
- [🎯 Project Overview](#-project-overview)
- [🏗️ Architecture](#-architecture)
- [🚀 Core Development Commands](#-core-development-commands)
- [🧪 Testing Strategy](#-testing-strategy)
- [🎨 Frontend Development](#-frontend-development)
- [🔧 Development Workflow](#-development-workflow)
- [🛠️ Architecture Principles](#-architecture-principles)
- [🔍 Code Navigation](#-code-navigation)
- [🚨 Troubleshooting](#-troubleshooting)

---

## 🌟 Quick Start (3 Minutes)

```bash
# 1️⃣ 启动完整开发环境
make dev && make status

# 2️⃣ 验证环境 (必须执行)
curl http://localhost:8000/health && make test.fast

# 3️⃣ 开始开发
make shell  # 进入容器开始编码
```

### Frontend Quick Start

```bash
# 启动前端开发服务器 (新终端)
cd frontend
npm install
npm run dev    # 访问 http://localhost:5173
```

### ✅ Verification Checklist

```bash
# 后端服务验证
curl http://localhost:8000/health/system       # 系统资源
curl http://localhost:8000/health/database     # 数据库连接
curl http://localhost:8000/api/v1/metrics       # Prometheus指标

# 前端服务验证
curl http://localhost:5173                      # Vite开发服务器

# 测试环境验证 (385+ tests should pass)
make test.fast                    # 核心功能 (2-3 min)
make test.unit.ci                 # CI验证 (最快)
```

**Expected Results**:
- ✅ All services healthy (app, db, redis)
- ✅ Backend API at http://localhost:8000
- ✅ Frontend dev server at http://localhost:5173
- ✅ API docs at http://localhost:8000/docs
- ✅ Test coverage: 29.0% total (target achieved)

## 🎯 Project Overview

**FootballPrediction** is an enterprise-grade football prediction system based on modern async architecture, integrating machine learning, data collection, real-time prediction, and event-driven architecture.

### Quality Baseline
| Metric | Current Status | Target |
|--------|---------------|--------|
| Build Status | ✅ Stable (Green Baseline) | Maintain |
| Test Coverage | 29.0% total (measured) | 18%+ (✅ Achieved) |
| Test Cases | 385+ passing tests | 400+ |
| Code Quality | A+ (ruff) | Maintain |
| Python Version | 3.10/3.11/3.12 | Recommend 3.11 |

### Tech Stack
- **Backend**: FastAPI + PostgreSQL 15 + Redis 7.0+ + SQLAlchemy 2.0+
- **Frontend**: Vue.js 3 + Vite + Pinia + Vue Router 4 + Tailwind CSS + TypeScript
- **Machine Learning**: XGBoost 2.0+ + TensorFlow 2.18.0 + MLflow + Optuna
- **Task Orchestration**: Prefect + Celery hybrid system
- **Containerization**: Docker 27.0+ + 10+ Docker Compose configurations

## 🏗️ Architecture

### Architecture Patterns
Enterprise-grade patterns for high performance, maintainability, and scalability:

- **DDD (Domain-Driven Design)** - Clear domain boundaries and business logic separation
- **CQRS (Command Query Separation)** - Independent optimization of read/write operations
- **Event-Driven Architecture** - Loose coupling communication between components
- **Async First** - All I/O operations use async/await
- **Lifecycle Management** - Resource management via FastAPI `lifespan`

### Application Startup Flow
```python
# src/main.py - Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup phase
    await initialize_database()          # DB connection and migrations
    await initialize_event_system()      # Event system initialization
    await initialize_cqrs()              # CQRS pattern initialization
    setup_performance_monitoring()       # Performance monitoring config

    # Smart cold start - auto-detect data state
    if await needs_data_collection():
        trigger_background_data_collection()

    yield  # Application running

    # Shutdown phase
    await shutdown_event_system()        # Cleanup event system
```

### Smart Cold Start System
The application implements intelligent startup logic:

1. **Database Health Check**: Verifies PostgreSQL connectivity
2. **Migration Status**: Automatically runs pending Alembic migrations
3. **Data State Detection**: Checks if initial data collection needed
4. **Background Tasks**: Starts Celery workers for async processing
5. **Event System**: Initializes event-driven communication
6. **Performance Monitoring**: Sets up Prometheus metrics collection

This ensures the application starts gracefully in any environment and automatically handles initialization tasks.

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
make install          # Install dependencies in virtual environment
make help             # Show all available commands with descriptions ⭐
```

### 🔥 Test Golden Rule
**Never run pytest on single files directly!** Always use Makefile commands:

```bash
make test.unit        # Unit tests (278 test files)
make test.fast        # Quick core tests (API/Utils/Cache/Events only)
make test.unit.ci     # CI verification (ultimate stable solution)
make test.integration # Integration tests
make test.all         # Run all tests including slow ones
make coverage         # Generate coverage report
make test-coverage-local # Run tests with coverage locally
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
```

### 🔧 Essential Scripts & Tools
```bash
# Data collection scripts
python scripts/refresh_fotmob_tokens.py    # Refresh FotMob API tokens
python scripts/daily_pipeline.py          # Run daily data collection
python scripts/backfill_details_fotmob_v2.py  # Backfill missing match data

# ML model scripts
python scripts/train_model_v2.py          # Train ML models
python scripts/tune_model_optuna.py       # Hyperparameter optimization
python scripts/generate_predictions.py    # Generate match predictions

# System maintenance
python scripts/ops_monitor.py             # Operations monitoring dashboard
python scripts/deploy_verify.py           # Deployment verification
```

### 📊 Monitoring Tools Access
```bash
# v2.5+ Enterprise Monitoring UIs
http://localhost:4200  # Prefect UI - Workflow orchestration
http://localhost:5555  # Flower UI - Celery task monitoring
http://localhost:5000  # MLflow UI - ML experiment tracking
```

## 🧪 Testing Strategy

### SWAT Testing Core Principles
1. **Build safety net first, then touch code** - Establish complete test safety net before modifying high-risk code
2. **P0/P1 risk first** - Prioritize most critical business logic, avoid wasting time on low-risk tests
3. **Mock all external dependencies** - Database, network, filesystem all mocked to ensure test purity

### Test Environment Configuration
```bash
# Development testing (default)
make test.fast        # Core functionality only

# CI Environment Testing (Required for CI)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true
make test.unit.ci     # Minimal verification for CI (fastest, no ML models)

# Local testing with real ML models
export FOOTBALL_PREDICTION_ML_MODE=real
export SKIP_ML_MODEL_LOADING=false
make test.integration # Full integration with real models
```

## 🎨 Frontend Development

### Frontend Tech Stack
- **Vue.js 3** - Progressive JavaScript framework with Composition API
- **TypeScript** - Static type checking for better code quality
- **Vite** - Fast build tool and development server
- **Pinia** - Modern state management (Vuex successor)
- **Vue Router 4** - Official routing solution
- **Tailwind CSS** - Utility-first CSS framework
- **Chart.js + vue-chartjs** - Data visualization components

### Frontend Development Commands
```bash
cd frontend  # 进入前端目录

# 开发环境
npm install          # 安装依赖
npm run dev          # 启动开发服务器 (http://localhost:5173)
npm run build        # 构建生产版本
npm run preview      # 预览生产构建

# 代码质量
npm run lint         # ESLint代码检查
npm run type-check   # TypeScript类型检查
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

### Key Frontend Architecture Components
- **Vue 3 Composition API**: Use `<script setup lang="ts">` syntax
- **Pinia State Management**: Replace Vuex, use stores for global state
- **TypeScript Integration**: Strong typing for all components and API calls
- **Chart.js Integration**: Use vue-chartjs for data visualization
- **Tailwind CSS**: Utility-first styling with responsive design
- **Axios HTTP Client**: Configured in `src/api/client.ts` for API communication

### Frontend Development Workflow
```bash
# 1. 启动前端开发环境
cd frontend && npm run dev

# 2. 实时类型检查 (在另一个终端)
cd frontend && npm run type-check -- --watch

# 3. 开发过程中
npm run lint -- --fix          # 自动修复linting问题
npm run type-check             # 检查TypeScript类型

# 4. 构建前验证
npm run lint && npm run type-check && npm run build
```

## 🔧 Development Workflow

### Daily Development Process
```bash
# 1. 启动环境并验证服务
make dev && make status

# 2. 验证API可访问性
curl http://localhost:8000/health

# 3. 运行核心测试确保环境正常
make test.fast

# 4. 开发过程中
make lint && make fix-code  # 代码质量检查和修复

# 5. 提交前验证 (必须执行)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
make test.unit.ci     # 最小CI验证 (最快)
make security-check   # 安全检查

# 6. 可选: 如果时间允许进行完整验证
make ci               # 完整CI验证包括覆盖率
```

### Pre-commit Full Verification
```bash
make ci               # 完整CI验证 (如果时间允许)
```

## 🛠️ Architecture Principles

### 1. Async Programming Pattern
```python
# ✅ Correct: All I/O operations use async/await
async def fetch_match_data(match_id: str) -> MatchData:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/matches/{match_id}")
        return MatchData.model_validate(response.json())

# ✅ Correct: Database operations use async SQLAlchemy 2.0
async def get_match_by_id(db: AsyncSession, match_id: str) -> Optional[Match]:
    result = await db.execute(
        select(Match).where(Match.id == match_id)
    )
    return result.scalar_one_or_none()
```

### 2. Database Operations (Mandatory)
- **📌 Always use `src/database/async_manager.py`** - "One Way to do it" principle
- **🚫 NEVER use `src/database/connection.py`** - Deprecated interface
- **⚡ All operations must be async** - Use `async/await` consistently
- **🔒 Use proper session management** - Context managers or dependency injection

```python
# ✅ Correct: Use unified async manager
from src.database.async_manager import get_db_session

# FastAPI dependency injection
async def get_matches(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Match))
    return result.scalars().all()

# Context manager usage
async with get_db_session() as session:
    # Database operations here
    await session.commit()
```

### 3. Type Safety and Data Validation
```python
# ✅ Complete type annotations
async def process_prediction_request(
    request: PredictionRequest,
    user_id: UUID
) -> PredictionResponse:

# ✅ Pydantic data validation
class PredictionRequest(BaseModel):
    match_id: str = Field(..., min_length=1, max_length=50)
    prediction_type: PredictionType
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
```

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

### 🔍 Search Patterns for Quick Navigation
```bash
# Find API endpoints
grep -r "@router\." src/api/
grep -r "@app\." src/

# Find database models
grep -r "class.*Base" src/database/models/

# Find event handlers
grep -r "@event_handler" src/

# Find CQRS handlers
grep -r "class.*CommandHandler" src/cqrs/
grep -r "class.*QueryHandler" src/cqrs/
```

### Frontend Code Navigation
```bash
# Find Vue components
find frontend/src -name "*.vue"

# Find API calls
grep -r "axios\|fetch" frontend/src/

# Find TypeScript types
find frontend/src -name "*.ts" -name "types*"

# Find Pinia stores
find frontend/src/stores -name "*.ts"
```

## 🚨 Troubleshooting

### Quick Reference Table
| Issue Type | Primary Command | Secondary Checks |
|-----------|----------------|------------------|
| **Test Failures** | `make test.fast` | `make logs`, `export FOOTBALL_PREDICTION_ML_MODE=mock` |
| **CI Timeout** | `make test.unit.ci` | Check memory usage, reduce parallel jobs |
| **Port Conflicts** | `lsof -i :8000` | `kill -9 <PID>`, modify docker-compose.yml |
| **Database Issues** | `make db-migrate` | `make status`, `make db-shell` |
| **Redis Connection** | `make redis-shell` | `make logs-redis`, check docker-compose.yml |
| **Memory Issues** | `make test.fast` | `docker stats`, reduce ML model loading |
| **Type Errors** | `make type-check` | Check imports, add type annotations |
| **Frontend Build** | `cd frontend && npm run build` | Check npm dependencies, TypeScript errors |
| **Frontend Dev Server** | `cd frontend && npm run dev` | Check port 5173 availability |

### Error-Specific Solutions

#### 🔥 FotMob API Authentication Failures
```bash
# Symptom: HTTP 403 errors from FotMob API
# Diagnosis:
python scripts/manual_token_test.py

# Solution:
python scripts/refresh_fotmob_tokens.py
# Verify environment variables:
cat .env | grep FOTMOB
```

#### 🐳 Docker Port Conflicts
```bash
# Symptom: "port already allocated" errors
# Diagnosis:
lsof -i :8000  # Backend API
lsof -i :5173  # Frontend

# Solution 1: Kill conflicting processes
kill -9 <PID>

# Solution 2: Modify ports in docker-compose.yml
services:
  app:
    ports:
      - "8001:8000"  # Change external port to 8001
```

#### 🎨 Frontend Development Issues
```bash
# Symptom: Vite dev server fails to start
# Diagnosis:
cd frontend
npm run dev

# Common solutions:
npm install          # Reinstall dependencies
rm -rf node_modules package-lock.json && npm install  # Clean install
npm run type-check   # Check TypeScript errors
```

#### 🧠 ML Model Loading Problems
```bash
# Symptom: Model loading failures during startup
# Solution: Use mock mode for development
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
make dev
```

#### 📊 Database Connection Issues
```bash
# Symptom: Database connection timeouts
# Common solutions:
make db-migrate      # Run pending migrations
make db-shell        # Check PostgreSQL status
docker-compose exec db pg_isready
```

### Frontend Specific Issues

#### TypeScript Compilation Errors
```bash
cd frontend
npm run type-check   # Identify TypeScript errors
npm run lint         # Check for linting issues

# Common fixes:
# - Add missing type definitions
# - Fix import paths
# - Update vue-tsc version if needed
```

#### Vue.js Development Issues
```bash
# Component not rendering?
# 1. Check Vue DevTools browser extension
# 2. Verify component imports and exports
# 3. Check console for JavaScript errors

# State not updating?
# 1. Check Pinia store mutations
# 2. Verify reactive data usage
# 3. Use Vue DevTools to inspect state
```

#### 📊 Monitoring UI Issues
```bash
# Prefect UI not accessible?
curl http://localhost:4200  # Direct access check
docker-compose logs prefect  # Check Prefect service logs

# Flower UI not showing tasks?
curl http://localhost:5555  # Verify Celery status
# Check worker processes:
docker-compose exec celery celery -A src.tasks.celery_app inspect active

# MLflow UI not loading experiments?
curl http://localhost:5000  # Basic connectivity test
# Check MLflow tracking server:
docker-compose logs mlflow
```

## 💡 Important Reminders

1. **Test Golden Rule** - Always use Makefile commands, never run pytest directly
2. **Async First** - All I/O operations must use async/await pattern
3. **Architectural Integrity** - Strictly follow DDD+CQRS+Event-Driven architecture
4. **Environment Consistency** - Use Docker to ensure local and CI environments match
5. **Service Health** - Run `make status` to check all services before development
6. **Frontend Development** - Use separate terminal for frontend dev server
7. **AI-First Maintenance** - Project uses AI-assisted development, prioritize architectural integrity
8. **Coverage Requirement** - Maintain minimum 6.0% test coverage for CI to pass
9. **Security First** - Run `make security-check` before committing changes
10. **Use `make help`** - Shows all available commands with descriptions - most useful command for newcomers
11. **Monitoring Tools** - v2.5+ provides Prefect (4200), Flower (5555), MLflow (5000) UIs for system observability

---

## 🔑 Critical Development Rules

### 1. FotMob Data Collection (Critical)
- **🚫 NEVER use Playwright or browser automation** - HTTP requests only
- **✅ Always use rate limiting** - `src/collectors/rate_limiter.py`
- **🔐 Proper authentication required** - x-mas and x-foo headers mandatory
- **🔄 Rotate User-Agents** - Mix mobile/desktop patterns

### 2. Database Operations (Mandatory)
- **📌 Always use `src/database/async_manager.py`** - "One Way to do it" principle
- **🚫 NEVER use `src/database/connection.py`** - Deprecated interface
- **⚡ All operations must be async** - Use `async/await` consistently
- **🔒 Use proper session management** - Context managers or dependency injection

### 3. Testing Protocol (Non-negotiable)
- **🛡️ ALWAYS use Makefile commands** - Never pytest directly on files
- **🎯 Mock all external dependencies** - Database, network, filesystem
- **📊 Maintain 6.0%+ coverage** - CI will fail below this threshold
- **⚡ Use mock ML mode in CI** - Set `FOOTBALL_PREDICTION_ML_MODE=mock`

### 4. Architecture Integrity (Enterprise Standards)
- **🏗️ Follow DDD patterns** - Domain layer purity essential
- **📡 Implement CQRS separation** - Commands vs queries distinct
- **🔄 Event-driven communication** - Use event system for loose coupling
- **🎯 Type safety mandatory** - Complete type annotations required

### 5. Frontend Development Standards
- **🎨 Use Vue 3 Composition API** - Prefer Composition API over Options API
- **📝 TypeScript mandatory** - All new code must have proper type definitions
- **📦 Follow component structure** - Use `<script setup lang="ts">` syntax
- **🎯 Pinia for state management** - Use Pinia stores for application state

**💡 Remember**: This is an enterprise-grade project with AI-first maintenance. Violating these critical rules will break the system's architectural integrity and quality standards.