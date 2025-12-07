# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌐 Language Preference

**IMPORTANT**: Please reply in Chinese (中文) for all communications in this repository. The user prefers Chinese responses for all interactions, including code explanations, documentation updates, and general discussions.

## 📋 Latest Updates (2025-12-07)

### v4.0.1-hotfix Current Release
- **Production Stable Version**: CI/CD pipeline maintained with automated test recovery
- **Test Coverage**: 29.0% achieved with 385+ passing tests
- **Code Quality**: A+ rating with enterprise-grade security standards
- **Full Stack Modernization**: Vue.js 3 + TypeScript + FastAPI + PostgreSQL 15

### v4.0.2 Documentation Enhancement (2025-12-07)
- **Enhanced Essential Scripts**: Added comprehensive script categorization with 20+ key commands
- **Frontend Troubleshooting**: Detailed Vue.js, TypeScript, Vite, and Tailwind CSS troubleshooting guides
- **Monitoring Tools Guide**: Complete Prefect, Flower, and MLflow UI usage instructions
- **Daily Development Workflow**: Step-by-step checklist with morning, development, and end-of-day procedures
- **Performance Monitoring**: Added system health checks and performance monitoring scripts

### v2.5.0 Backend Complete
- **Complete Backend Architecture v2.5**: Enterprise-grade task orchestration with MLflow integration
- **Prefect + Celery Scheduler**: Hybrid scheduling system for workflow orchestration
- **Enhanced Monitoring**: Prefect UI (4200), Flower UI (5555), MLflow UI (5000)

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

# 可选：启动完整调度系统
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d
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
- ✅ Monitoring UIs: Prefect (4200), Flower (5555), MLflow (5000)

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

### 🎯 Running Single Tests (Correct Way)
When you need to run specific test files, use these container-aware commands:

```bash
# Run specific test module (use path relative to project root)
docker-compose exec app bash -c "cd /app && pytest tests/test_api_health.py -v"

# Run tests with specific pattern
docker-compose exec app bash -c "cd /app && pytest tests/test_utils/ -v"

# Run with coverage for specific file
docker-compose exec app bash -c "cd /app && pytest tests/test_collectors/test_fotmob_adapter.py --cov=src.collectors.fotmob -v"

# Run with debugger
docker-compose exec app bash -c "cd /app && pytest tests/test_ml/test_inference.py -v --pdb"
```

#### CI 环境测试优化
```bash
# CI 环境最小化验证 (终极稳定方案)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true
make test.unit.ci     # 绕过pytest的极简验证，最快通过CI
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

### Monitoring Commands
```bash
make monitor          # 实时监控应用容器资源使用
make monitor-all      # 监控所有容器资源使用
```

### Database Management
```bash
make db-reset         # Reset database (⚠️ will delete all data)
make db-migrate       # Run database migrations
make db-shell         # Enter PostgreSQL interactive terminal
```

### 🔧 Essential Scripts & Tools
```bash
# 数据采集脚本 (核心业务功能)
python scripts/refresh_fotmob_tokens.py        # 刷新 FotMob API 令牌
python scripts/daily_pipeline.py              # 运行每日数据采集
python scripts/backfill_details_fotmob_v2.py   # 回填缺失的比赛数据
python scripts/collect_l1_fixtures.py          # L1 基础数据采集
python scripts/fbref_real_data_collector.py    # FBref 数据采集器

# 机器学习脚本
python scripts/train_model_v2.py               # 训练 ML 模型
python scripts/tune_model_optuna.py            # 超参数优化
python scripts/generate_predictions.py         # 生成比赛预测
python scripts/generate_advanced_features.py   # 生成高级特征
python scripts/backtest_standalone_demo.py     # 回测演示脚本

# 运维与监控脚本
python scripts/ops_monitor.py                  # 运维监控仪表板
python scripts/deploy_verify.py                # 部署验证
python scripts/validate_data_integrity.py      # 数据完整性验证
python scripts/scan_secrets.py                 # 敏感信息扫描

# 数据库管理脚本
python scripts/init_db.py                      # 初始化数据库
python scripts/check_db_content.py             # 检查数据库内容
python scripts/massive_backfill.py             # 大规模数据回填

# 性能与调试脚本
python scripts/proxy_check.py                  # 代理配置检查
python scripts/data_flow_watchdog.py           # 数据流监控
python scripts/fotmob_real_audit.py            # FotMob 数据审计
```

### 📈 Data Collection Commands
```bash
# L1/L2 数据采集系统 (核心业务功能)
make run-l1              # L1赛季数据采集
make run-l2              # L2详情数据采集 (HTML解析)
make run-l2-api          # L2 API详情数据采集
```

### 📊 Monitoring Tools Access
```bash
# v2.5+ Enterprise Monitoring UIs
http://localhost:4200  # Prefect UI - Workflow orchestration
http://localhost:5555  # Flower UI - Celery task monitoring
http://localhost:5000  # MLflow UI - ML experiment tracking

# 启动完整调度系统 (如果未启动)
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d
```

### 🔄 Scheduler Management Commands
```bash
# Prefect Workflow Management
docker-compose exec prefect prefect work-queue ls                    # List work queues
docker-compose exec prefect prefect deployment ls                   # List deployments
docker-compose exec prefect prefect flow-run ls                    # List flow runs
docker-compose exec prefect prefect flow-run get <flow-run-id>      # Get flow run details
docker-compose exec prefect prefect flow-run cancel <flow-run-id>   # Cancel running flow
docker-compose exec prefect prefect flow-run retry <flow-run-id>    # Retry failed flow

# Celery Task Management
docker-compose exec celery celery -A src.tasks.celery_app inspect active    # Active tasks
docker-compose exec celery celery -A src.tasks.celery_app inspect scheduled  # Scheduled tasks
docker-compose exec celery celery -A src.tasks.celery_app inspect stats      # Worker stats
docker-compose exec celery celery -A src.tasks.celery_app inspect reserved   # Reserved tasks
docker-compose exec celery celery -A src.tasks.celery_app purge               # Clear queue
docker-compose exec celery celery -A src.tasks.celery_app control enable      # Enable tasks
docker-compose exec celery celery -A src.tasks.celery_app control disable     # Disable tasks

# MLflow Experiment Tracking
docker-compose exec mlflow mlflow experiments list                    # List experiments
docker-compose exec mlflow mlflow runs list -e <experiment-id>        # List runs in experiment
docker-compose exec mlflow mlflow ui --port 5000                     # Start MLflow UI (if not running)
docker-compose exec mlflow mlflow models list                        # List registered models
docker-compose exec mlflow mlflow model-versions list --name <model>  # List model versions
```

### 📊 监控工具详细使用指南

#### Prefect UI - 工作流编排 (http://localhost:4200)
```bash
# 启动 Prefect 服务
docker-compose -f docker-compose.scheduler.yml up -d prefect

# 检查 Prefect 服务状态
curl http://localhost:4200/health

# 常用 Prefect 命令
docker-compose exec prefect prefect get-work-queue                 # 获取工作队列详情
docker-compose exec prefect prefect schedule ls                    # 列出所有调度
docker-compose exec prefect prefect block ls                      # 列出所有块（存储、认证等）

# 日志查看
docker-compose logs prefect | tail -50                            # 最近50行日志
docker-compose logs prefect | grep -E "ERROR|WARN"               # 只看错误和警告

# 故障排查
# 如果工作流卡住：
docker-compose exec prefect prefect flow-run cancel --force <run-id>

# 如果队列堆积：
docker-compose exec prefect prefect work-queue pause <queue-name>
docker-compose exec prefect prefect work-queue resume <queue-name>
```

#### Flower UI - Celery 任务监控 (http://localhost:5555)
```bash
# 启动 Celery 监控
docker-compose -f docker-compose.scheduler.yml up -d celery flower

# 实时任务监控命令
docker-compose exec celery celery -A src.tasks.celery_app inspect active      # 查看活跃任务
docker-compose exec celery celery -A src.tasks.celery_app inspect reserved    # 查看预留任务
docker-compose exec celery celery -A src.tasks.celery_app inspect scheduled   # 查看计划任务

# 性能监控
docker-compose exec celery celery -A src.tasks.celery_app inspect stats       # 工作进程统计
docker-compose exec celery celery -A src.tasks.celery_app inspect report      # 详细报告

# 任务管理
docker-compose exec celery celery -A src.tasks.celery_app purge -Q <queue>    # 清空特定队列
docker-compose exec celery celery -A src.tasks.celery_app control revoke <task-id>  # 撤销任务

# 工作进程管理
docker-compose exec celery celery -A src.tasks.celery_app control pool_restart  # 重启工作池
docker-compose exec celery celery -A src.tasks.celery_app control pool_restart @worker1  # 重启特定工作器
```

#### MLflow UI - ML 实验跟踪 (http://localhost:5000)
```bash
# 启动 MLflow 服务
docker-compose -f docker-compose.scheduler.yml up -d mlflow

# 实验管理
docker-compose exec mlflow mlflow experiments create --name <experiment-name>  # 创建新实验
docker-compose exec mlflow mlflow experiments delete <experiment-id>          # 删除实验

# 运行管理
docker-compose exec mlflow mlflow runs delete --run-id <run-id>               # 删除运行
docker-compose exec mlflow mlflow runs restore --run-id <run-id>              # 恢复删除的运行

# 模型注册
docker-compose exec mlflow mlflow model-register create --name <model-name>   # 注册新模型
docker-compose exec mlflow mlflow model-transition --name <model> --stage Staging --version <version>  # 模型版本转换

# 数据监控
docker-compose exec mlflow mlflow artifacts download --run-id <run-id> -d ./artifacts  # 下载产物
docker-compose exec mlflow mlflow artifacts list --run-id <run-id>            # 列出产物
```

### 🚨 监控告警设置

#### 健康检查端点监控
```bash
# 系统健康检查脚本
#!/bin/bash
# save as monitor_system.sh

# 检查各个服务状态
echo "🔍 系统健康检查"
echo "================"

# 后端API
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 后端API健康"
else
    echo "❌ 后端API异常"
fi

# 前端开发服务器
if curl -s http://localhost:5173 > /dev/null; then
    echo "✅ 前端服务健康"
else
    echo "⚠️ 前端服务未启动"
fi

# 数据库连接
if docker-compose exec -T db pg_isready -U football_prediction > /dev/null 2>&1; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败"
fi

# Redis连接
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis连接正常"
else
    echo "⚠️ Redis连接失败"
fi

# 调度系统服务
for port in 4200 5555 5000; do
    if curl -s http://localhost:$port > /dev/null; then
        echo "✅ 监控服务 $port 正常"
    else
        echo "⚠️ 监控服务 $port 未启动"
    fi
done

echo "================"
echo "检查完成"
```

#### 性能监控命令
```bash
# 容器资源监控
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# 磁盘使用情况
docker-compose exec df -h /app  # 应用容器内磁盘使用

# 数据库性能监控
docker-compose exec db psql -U football_prediction -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10;"

# Redis性能监控
docker-compose exec redis redis-cli info memory | grep -E "used_memory|maxmemory"
docker-compose exec redis redis-cli info stats | grep -E "total_commands|keyspace"
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

### 🚀 Complete Frontend Workflow
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

### 🔄 Frontend-Backend Integration Testing
```bash
# Start both services for full-stack testing
# Terminal 1: Backend
make dev

# Terminal 2: Frontend (in another window)
cd frontend && npm run dev

# Verify integration
curl http://localhost:8000/health     # Backend health
curl http://localhost:5173            # Frontend dev server
curl http://localhost:5173/api/health # Frontend proxy to backend
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

### 📋 Daily Development Checklist

#### 🌅 早晨环境检查 (5分钟)
```bash
# 1️⃣ 检查服务状态
make status                           # 验证所有容器运行状态
docker-compose ps                    # 详细容器状态

# 2️⃣ 健康检查
curl http://localhost:8000/health     # 后端健康检查
curl http://localhost:8000/health/system    # 系统资源检查
curl http://localhost:5173            # 前端服务检查（如果运行）

# 3️⃣ 快速测试验证
make test.fast                       # 核心功能冒烟测试 (2-3分钟)

# 4️⃣ 环境清理（可选）
make clean                          # 清理Docker缓存和旧容器
```

#### 🚀 开发前准备
```bash
# 1️⃣ 创建功能分支
git checkout -b feature/your-feature-name
git push -u origin feature/your-feature-name

# 2️⃣ 代码质量基线检查
make lint                            # 检查代码风格
make test.fast                       # 确保测试通过
npm run type-check                   # 前端类型检查 (cd frontend)

# 3️⃣ 环境配置验证
make env-check                       # 验证环境变量配置
cat .env | grep -E "DATABASE|REDIS"  # 检查关键配置
```

#### 💻 开发过程中
```bash
# 1️⃣ 持续代码质量（每次保存后）
make lint && make fix-code           # 自动修复代码问题
npm run lint -- --fix               # 前端代码修复 (cd frontend)

# 2️⃣ 实时监控（保持开发环境稳定）
docker-compose logs app --tail=20    # 应用日志监控
docker-compose logs db --tail=10     # 数据库日志
make monitor                         # 系统资源监控

# 3️⃣ 前端开发（如果是全栈开发）
cd frontend && npm run dev           # 启动前端开发服务器
npm run type-check -- --watch        # 实时类型检查

# 4️⃣ 测试驱动开发
# 运行相关测试文件（正确方式）
docker-compose exec app bash -c "cd /app && pytest tests/test_api_health.py -v"
```

#### 🔍 提交前验证 (必须执行)
```bash
# 1️⃣ 设置CI环境变量（加速测试）
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true

# 2️⃣ 快速CI验证
make test.unit.ci                    # 最小CI验证 (30秒)
make security-check                  # 安全漏洞扫描
make lint                            # 最终代码风格检查

# 3️⃣ 前端验证（如果有前端更改）
cd frontend && npm run type-check && npm run lint && npm run build

# 4️⃣ 提交代码
git add .
git commit -m "feat: 描述你的更改

- 更改点1
- 更改点2
- 测试覆盖

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 📊 完整验证（有时间时执行）
```bash
# 1️⃣ 完整CI验证
make ci                              # 完整质量检查 (5-10分钟)
make coverage                        # 生成覆盖率报告
open htmlcov/index.html              # 查看覆盖率详情

# 2️⃣ 集成测试
make test.integration                # 集成测试（需要数据库）
make test-coverage-local             # 本地覆盖率测试

# 3️⃣ 性能测试
make performance-test                # 性能基准测试（如果存在）
```

#### 🌙 日结束清理
```bash
# 1️⃣ 最终验证
make test.fast                       # 确保没有破坏核心功能
make status                          # 检查服务状态

# 2️⃣ 推送工作
git push origin feature/your-feature-name

# 3️⃣ 可选：停止服务（节省资源）
make dev-stop                       # 停止开发环境
docker-compose down                  # 完全关闭所有服务

# 4️⃣ 创建PR（GitHub）
# 在GitHub网站上创建Pull Request
# 标题：feat: 你的功能描述
# 描述：包含更改说明和测试结果
```

#### 🚨 紧急修复清单
```bash
# 如果生产环境出现紧急问题：
# 1️⃣ 快速诊断
make status                         # 检查所有服务状态
docker-compose logs app --tail=100  # 查看最近100行日志

# 2️⃣ 快速修复
make hotfix-branch                  # 创建热修复分支（如果有这个命令）
# 或
git checkout -b hotfix/urgent-fix

# 3️⃣ 最小验证
make test.fast                      # 核心功能验证
git commit -m "fix: 紧急修复"
git push origin hotfix/urgent-fix
```

### 🔍 Environment Verification Script
```bash
#!/bin/bash
# save as verify_env.sh and run with: bash verify_env.sh

echo "🔍 Environment Verification Script"
echo "================================"

# Check Docker services
echo "📊 Checking Docker services..."
docker-compose ps

# Check backend health
echo "🏥 Checking backend health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend API healthy"
else
    echo "❌ Backend API not responding"
fi

# Check database connection
echo "🗄️ Checking database connection..."
if docker-compose exec -T db pg_isready -U football_prediction > /dev/null 2>&1; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
fi

# Check Redis connection
echo "🔴 Checking Redis connection..."
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis connection OK"
else
    echo "⚠️ Redis connection failed (may not be critical)"
fi

# Check test environment
echo "🧪 Running quick test verification..."
make test.fast > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Test environment OK"
else
    echo "❌ Test environment has issues"
fi

echo "================================"
echo "Environment verification complete!"
```

### 📈 Performance Monitoring Commands
```bash
# Real-time resource monitoring
make monitor                      # Monitor app container
make monitor-all                  # Monitor all containers

# System resource usage
docker stats                      # Live container stats
docker stats --no-stream          # Single snapshot

# Application performance metrics
curl http://localhost:8000/api/v1/metrics  # Prometheus metrics
curl http://localhost:8000/health/system    # System resources

# Database performance
docker-compose exec db psql -U football_prediction -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
LIMIT 10;"

# Cache performance
docker-compose exec redis redis-cli info memory
docker-compose exec redis redis-cli info stats
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

### 🎯 Functionality-Based Navigation
```bash
# Find prediction-related code
grep -r "prediction" src/ --include="*.py" | head -10

# Find data collection logic
grep -r "collect\|scrape\|fetch" src/collectors/ --include="*.py"

# Find ML inference code
grep -r "inference\|predict" src/ml/ --include="*.py"

# Find authentication logic
grep -r "auth\|login\|token" src/ --include="*.py"

# Find database operations
grep -r "async def.*\(get\|create\|update\|delete\)" src/ --include="*.py"
```

### 🔧 Advanced Search Patterns
```bash
# Find async database operations
grep -r "await.*session\." src/ --include="*.py"

# Find API response models
grep -r "class.*Response" src/api/ --include="*.py"

# Find dependency injection
grep -r "Depends(" src/ --include="*.py"

# Find error handling
grep -r "raise.*Exception\|HTTPException" src/ --include="*.py"

# Find configuration variables
grep -r "getenv\|environ" src/ --include="*.py"
```

### 🌐 Frontend-Backend API Integration
```bash
# Find API endpoint definitions (backend)
grep -r "@app\.\|@router\." src/api/ -A 2 | grep "def\|async def"

# Find corresponding frontend API calls
grep -r "axios\.\|fetch(" frontend/src/ -A 1 | grep -E "\/api\/|http"

# Find data models mapping between frontend/backend
grep -r "interface.*\|type.*=" frontend/src/types/
grep -r "class.*BaseModel\|class.*Schema" src/api/schemas/
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
# - Add missing type definitions in src/types/
# - Fix import paths and module declarations
# - Update vue-tsc version if needed
# - Check Vue 3 Composition API syntax
# - Verify Pinia store type definitions

# Advanced TypeScript debugging
npx vue-tsc --noEmit --project tsconfig.json --diagnostics  # Detailed diagnostics
```

#### Vue.js Development Issues
```bash
# Component not rendering?
# 1. Check Vue DevTools browser extension
# 2. Verify component imports and exports (case-sensitive)
# 3. Check console for JavaScript errors
# 4. Verify <script setup lang="ts"> syntax
# 5. Check Vue Router configuration

# State not updating?
# 1. Check Pinia store mutations and actions
# 2. Verify reactive data usage (ref/reactive)
# 3. Use Vue DevTools to inspect state
# 4. Check store persistence and hydration

# Props/Emits not working?
# 1. Verify defineProps<T>() and defineEmits<T>() syntax
# 2. Check type definitions match parent component
# 3. Use Vue DevTools component inspector
```

#### Vite Development Server Issues
```bash
# Dev server not starting or hot reload not working?
cd frontend

# Check common issues:
npm run dev -- --host 0.0.0.0  # Bind to all interfaces
npm run dev -- --port 3000     # Use different port

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev

# Check proxy configuration in vite.config.ts
# Verify API proxy to backend is working
```

#### Tailwind CSS Issues
```bash
# Styles not applying?
cd frontend

# Check Tailwind compilation
npx tailwindcss -i ./src/assets/main.css -o ./dist/output.css --watch

# Verify content sources in tailwind.config.js
# Ensure all Vue components are included in content paths

# Common fixes:
# - Check PostCSS configuration
# - Verify Tailwind CSS imports in main.css
# - Ensure @apply directives have correct syntax
```

#### Chart.js Integration Issues
```bash
# Charts not rendering or updating?
# 1. Check Chart.js version compatibility with vue-chartjs
# 2. Verify data reactive updates in component
# 3. Check chart options and type definitions

# Example debugging component:
<script setup lang="ts">
import { ref, watch } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement)

const chartData = ref({
  labels: [],
  datasets: []
})

// Debug: Watch for data changes
watch(chartData, (newData) => {
  console.log('Chart data updated:', newData)
}, { deep: true })
</script>
```

#### Frontend Build and Deployment Issues
```bash
# Production build failing?
cd frontend

# Check build process
npm run build

# Common build errors:
# 1. TypeScript type errors - fix with npm run type-check
# 2. Import resolution issues - check vite.config.ts aliases
# 3. Asset optimization issues - check public/ folder

# Build analysis
npm run build -- --analyze  # Analyze bundle size

# Preview production build
npm run preview
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

## 📊 Data Collection Operations

### L1/L2/L3 Data Collection System
```bash
# L1 - Fixtures Data Collection (基础数据)
make run-l1                           # Collect league fixtures and team data
python scripts/collect_l1_fixtures.py    # Direct L1 collection script

# L2 - Match Details Collection (详细数据)
make run-l2                           # HTML parsing method
make run-l2-api                       # API-based method
python scripts/backfill_details_fotmob_v2.py  # Backfill missing data

# L3 - Feature Engineering (特征工程)
python scripts/compute_features_v2.py      # Compute ML features
python scripts/validate_feature_store.py  # Validate feature data quality
```

### Data Collection Troubleshooting
```bash
# Check FotMob API authentication
python scripts/manual_token_test.py        # Test API tokens
python scripts/refresh_fotmob_tokens.py    # Refresh expired tokens

# Monitor collection progress
docker-compose logs app | grep -E "L1|L2|collect"  # Collection logs
curl http://localhost:8000/api/v1/data/status      # Data collection status

# Fix data collection issues
make db-migrate                         # Ensure DB schema up-to-date
python scripts/validate_data_integrity.py     # Check data consistency
```

### 🤖 Machine Learning Model Management

### Model Training and Deployment
```bash
# Train new models
python scripts/train_model_v2.py            # Training pipeline
python scripts/tune_model_optuna.py         # Hyperparameter optimization

# Model validation and testing
python scripts/validate_model_v2.py         # Model performance validation
python scripts/generate_predictions.py      # Generate predictions

# Model deployment and monitoring
python scripts/deploy_model.py              # Deploy to production
curl http://localhost:8000/api/v1/ml/status # Model service health
```

### MLflow Model Registry
```bash
# Access MLflow UI
http://localhost:5000                       # MLflow experiment tracking

# Command line MLflow operations
docker-compose exec mlflow mlflow experiments list      # List experiments
docker-compose exec mlflow mlflow runs list -e <exp-id> # List experiment runs
docker-compose exec mlflow mlflow models list          # List registered models

# Model version management
docker-compose exec mlflow mlflow models describe --name <model-name>
docker-compose exec mlflow mlflow runs delete <run-id>  # Delete specific run
```

### Feature Store Management
```bash
# Feature computation and validation
python scripts/compute_features_v2.py           # Compute all features
python scripts/validate_feature_store.py        # Validate feature quality

# Feature monitoring
curl http://localhost:8000/api/v1/features/status     # Feature store status
docker-compose logs app | grep -E "feature|Feature"    # Feature computation logs

# Feature backfilling
python scripts/backfill_features.py <date_range>     # Backfill missing features
```

## 🔒 Security Best Practices

### 🔐 Credential Management
```bash
# Environment variable management
cat .env | grep -E "FOTMOB|DATABASE|REDIS"           # Check configured credentials
docker-compose exec app printenv | grep -E "SECRET|KEY|TOKEN"  # Check container env

# Secure credential rotation
python scripts/refresh_fotmob_tokens.py             # Rotate API tokens
make generate-secret                              # Generate new app secret

# Database security
make db-shell                                    # Access database securely
docker-compose exec db psql -U football_prediction -c "\du"  # List database users
```

### 🛡️ API Security Configuration
```bash
# FotMob API authentication (Critical)
# Required headers in all requests:
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-mas": "your-production-token-here",      # Auth token
    "x-foo": "production:your-secret-key",      # API secret
}

# Security headers verification
curl -I http://localhost:8000/api/v1/health     # Check security headers
curl -I http://localhost:5173                   # Frontend security headers
```

### 🔍 Code Security Scanning
```bash
# Automated security checks
make security-check                             # Run bandit security scan
docker run --rm -v "$(pwd)":/app securecodewarrior/python-security-scan:latest  # External scan

# Dependency vulnerability scanning
pip-audit                                       # Check for vulnerable Python packages
cd frontend && npm audit                       # Check frontend vulnerabilities

# Code quality security checks
make lint                                       # Ruff includes some security checks
make type-check                                 # Type safety prevents certain vulnerabilities

# Secrets detection in code
grep -r -i "password\|secret\|token\|key" src/ --include="*.py" | grep -v "test"
git-secrets --scan                             # Detect secrets in git history
```

### 🚨 Security Incident Response
```bash
# If security issues found
1. Immediate actions:
   - make dev-stop                            # Stop all services
   - change passwords/secrets immediately

2. Investigation:
   - docker-compose logs > investigation.log   # Save all logs
   - check unauthorized access patterns
   - run make security-check                  # Full security audit

3. Recovery:
   - rotate all credentials
   - update all API tokens
   - redeploy with clean images
   - monitor for suspicious activity
```