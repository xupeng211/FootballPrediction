# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒**: 请始终使用简体中文回复用户问题和交流。

**项目类型**: 企业级足球预测系统 (Enterprise Football Prediction System)
**架构模式**: DDD + CQRS + Event-Driven + Async-First
**技术栈**: FastAPI 0.104+ + SQLAlchemy 2.0+ + Redis 5.0+ + PostgreSQL 15 + React 19.2.0 + TypeScript 4.9.5 + XGBoost 2.0+

## 🛠️ Core Development Commands

### Environment Setup
```bash
# Docker开发环境 (主要开发方式)
make dev                # 启动完整开发环境 (app + db + redis + frontend + nginx + worker + beat)
make dev-rebuild        # 重新构建镜像并启动开发环境
make dev-logs           # 查看开发环境日志
make dev-stop           # 停止开发环境
make down               # 停止所有服务

# 生产环境
make prod               # 启动生产环境 (使用 docker-compose.prod.yml)
make prod-rebuild       # 重新构建生产环境

# 环境管理
make clean              # 清理Docker资源和缓存
make clean-all          # 彻底清理所有相关资源
make status             # 查看所有服务状态

# 快捷命令
make quick-start        # 快速启动开发环境 (别名: dev)
make quick-stop         # 快速停止开发环境 (别名: dev-stop)
```

### Code Quality & Testing
```bash
# 代码质量检查和修复 (在Docker容器中运行)
make test               # 在容器中运行所有测试
make lint               # 在容器中运行代码检查 (Ruff + MyPy)
make format             # 在容器中运行代码格式化 (ruff format)
make fix-code           # 在容器中运行代码自动修复
make type-check         # 在容器中运行类型检查
make security-check     # 在容器中运行安全扫描
make coverage           # 在容器中生成覆盖率报告

# 测试分类执行
make test.unit          # 在容器中运行单元测试
make test.integration   # 在容器中运行集成测试
make test.all           # 在容器中运行所有测试

# 快速优化脚本
./quick_optimize.sh     # 快速优化代码质量 (一键修复所有问题)

# 本地测试执行 (可选，需要本地环境)
pytest tests/unit/test_specific.py::test_function -v        # 运行单个测试
pytest tests/unit/test_module.py -k "test_keyword" -v        # 关键词过滤测试
pytest tests/unit/ -m "unit and not slow" -v                # 标记组合测试
pytest tests/unit/ --maxfail=3 -x                           # 失败时快速停止

# 覆盖率分析
pytest --cov=src --cov-report=html --cov-report=term-missing

# CI 覆盖率门槛验证 (要求31%)
pytest --cov=src --cov-fail-under=31 --cov-report=term-missing
```

### Container Management & Access
```bash
# 容器管理和访问
make shell              # 进入后端容器终端
make shell-db           # 进入数据库容器
make db-shell           # 连接PostgreSQL数据库
make redis-shell        # 连接Redis
make logs               # 查看应用日志
make logs-db            # 查看数据库日志
make logs-redis         # 查看Redis日志
make status             # 查看所有服务状态

# Docker 容器管理 (原生命令)
docker-compose up -d            # 启动完整开发环境
docker-compose down             # 停止开发环境
docker-compose logs -f app      # 查看应用日志
docker-compose exec app bash     # 进入应用容器
docker-compose exec db psql      # 连接PostgreSQL数据库

# 监控和调试
make monitor            # 实时监控应用资源使用
make monitor-all        # 监控所有容器资源使用

# 数据库管理
make db-reset           # 重置数据库
make db-migrate         # 运行数据库迁移
```

### Security & Validation
```bash
make security-check     # Bandit安全扫描
make audit              # 依赖安全审计
make ci-check          # 完整CI验证
```

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic v2+, Redis 5.0+, PostgreSQL 15
- **Frontend**: React 19.2.0, TypeScript 4.9.5, Ant Design 5.27.6, Redux Toolkit 2.9.2
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+, MLflow 2.22.2+
- **Testing**: pytest 8.4+ with asyncio support (4597 test functions across 274 test files)
- **Code Quality**: Ruff 0.14+, MyPy 1.18+, Bandit 1.8.6+

### Clean Architecture Pattern
```
src/
├── api/           # FastAPI routers, HTTP concerns only
├── domain/        # Business logic, entities (pure Python)
├── services/      # Application services, orchestration
├── database/      # SQLAlchemy models, repositories
├── adapters/      # External API integrations
├── ml/           # Machine learning models and pipelines
├── cache/        # Redis caching layer
└── utils/        # Shared utilities
```

### Key Integration Points
- **Main Application**: `src/main.py` with 40+ API endpoints
- **ML Prediction Engine**: XGBoost models for match predictions
- **Real-time Features**: WebSocket support at `/api/v1/realtime/ws`
- **Caching**: Redis-based performance optimization
- **Database**: Async PostgreSQL with SQLAlchemy 2.0

### API Endpoints Structure
- **Health Checks**: `/health`, `/health/system`, `/health/database`
- **Predictions**: `/api/v1/predictions/`, `/api/v2/predictions/`
- **Data Management**: `/api/v1/data_management/`
- **System**: `/api/v1/system/`
- **Adapters**: `/api/v1/adapters/`
- **Monitoring**: `/metrics`

## 🧪 Testing Architecture

### Test Structure (4597 test functions across 274 test files)
- **Unit Tests** (85%): Fast, isolated component testing
- **Integration Tests** (12%): Real dependency testing
- **E2E Tests** (2%): Complete user workflow testing
- **Performance Tests** (1%): Load and stress testing

### Standardized Test Markers
```python
# Core test types
@pytest.mark.unit           # Unit tests (85% of tests)
@pytest.mark.integration    # Integration tests (12% of tests)
@pytest.mark.e2e           # End-to-end tests (2% of tests)
@pytest.mark.performance   # Performance tests (1% of tests)

# Execution characteristics
@pytest.mark.critical       # Must-pass core functionality
@pytest.mark.smoke         # Basic functionality validation
@pytest.mark.slow          # Long-running tests (>30s)
@pytest.mark.regression    # Regression testing

# Functional domain
@pytest.mark.api           # HTTP endpoint testing
@pytest.mark.database      # Database connection tests
@pytest.mark.ml            # Machine learning tests
@pytest.mark.cache         # Redis and caching logic
@pytest.mark.auth          # Authentication and authorization
@pytest.mark.monitoring    # Metrics and health checks

# Development dependencies
@pytest.mark.external_api  # Requires external API calls
@pytest.mark.docker        # Requires Docker container environment
@pytest.mark.network       # Requires network connection
```

### Recommended Testing Workflow
```bash
# 日常开发 - 快速验证
make test              # Run all tests with fast feedback

# 功能开发完成 - 完整测试
make test.unit          # Full unit test suite with coverage
make coverage           # Generate HTML coverage report

# 发布前验证 - 全面检查
make test.all           # Complete test suite (unit + integration + e2e)
make lint && make test  # Code quality + full testing
```

## 🔧 Development Standards

### Code Style Requirements
- **Type Hints**: All functions must have complete type annotations
- **Async/Await**: All I/O operations must be async (database, external APIs)
- **Logging**: Use structured logging with `logger` (never use `print()`)
- **Error Handling**: Comprehensive exception handling with proper logging

### Function Template
```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_data(
    input_data: Dict[str, Any],
    *,
    timeout: Optional[int] = None,
    retry_count: int = 3
) -> ResultModel:
    """Process input data with async operations.

    Args:
        input_data: Dictionary containing input parameters
        timeout: Optional timeout in seconds
        retry_count: Number of retry attempts

    Returns:
        ResultModel: Processed result

    Raises:
        ValueError: When input data is invalid
        TimeoutError: When operation exceeds timeout
    """
    logger.info(f"Processing data: {len(input_data)} items")

    try:
        result = await database_service.fetch_data(input_data, timeout)
        logger.debug(f"Successfully processed {len(result)} items")
        return result
    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        raise
```

## 🐳 Docker Development

### Multi-Environment Support
- **Development**: `docker-compose.yml` (完整开发栈 - app + db + redis + frontend + nginx + worker + beat)
- **Production**: `docker-compose.prod.yml` (生产优化栈 - app + db + redis + nginx + monitoring + logging)

### Service Stack
#### Development Environment
- **app**: FastAPI application (port: 8000)
- **frontend**: React application (ports: 3000, 3001)
- **db**: PostgreSQL 15 (port: 5432)
- **redis**: Redis 7.0 (port: 6379)
- **nginx**: Reverse proxy (port: 80)
- **worker**: Celery worker (异步任务处理)
- **beat**: Celery beat (定时任务调度)

#### Production Environment (Additional Services)
- **prometheus**: 指标收集和存储 (port: 9090)
- **grafana**: 可视化仪表板 (port: 3000)
- **loki**: 日志聚合 (port: 3100)

### Container Development Features
- Hot reload with volume mounting
- Health checks for all services
- Environment-specific configurations
- Multi-stage builds for optimized images
- Development vs production targets

## 🤖 Machine Learning Pipeline

### ML Architecture
- **Prediction Engine**: XGBoost 2.0+ gradient boosting models with hyperparameter optimization
- **Feature Engineering**: pandas 2.1+ and numpy 1.25+ data preprocessing with automated pipelines
- **Model Training**: scikit-learn 1.3+ training pipelines with cross-validation
- **Model Management**: MLflow 2.22.2+ version control with security patches and experiment tracking
- **Model Ensemble**: Multiple prediction strategies (LSTM, Poisson, Ensemble) with performance comparison

### ML Service Integration
```python
# Inference service usage
from src.services.inference_service import inference_service

prediction_result = await inference_service.predict_match(match_id)
# Returns: PredictionResult with confidence scores and probabilities

# Batch prediction
batch_results = await inference_service.batch_predict_match(match_ids)
```

### Model Lifecycle
- **Training**: `src/ml/train_model.py` - Automated model training with hyperparameter tuning
- **Validation**: `src/ml/model_validation.py` - Cross-validation and performance evaluation
- **Deployment**: `src/ml/model_deployment.py` - Model packaging and API deployment
- **Monitoring**: `src/ml/model_monitoring.py` - Real-time performance tracking and drift detection
- **Feature Store**: `src/ml/feature_store.py` - Centralized feature management
- **Experiments**: `src/ml/experiments/` - A/B testing and model comparison

### ML Model Management
```bash
# ML model operations
python -m src.ml.train_model --config configs/ml/xgboost_v2.yaml
python -m src.ml.model_validation --model-version latest
python -m src.ml.batch_predict --date-range 2024-01-01:2024-01-31

# MLflow UI (when running)
mlflow ui --port 5000  # Access experiment tracking
```

## 🚨 Crisis Management Tools

### Test Crisis Recovery
```bash
# When tests are failing (>30%)
make test               # Run tests to identify issues
make fix-code           # Auto-fix code quality issues
make lint              # Run full code quality check
make coverage          # Check coverage impact

# Manual test recovery
pytest tests/unit/ --maxfail=5 -x  # Run tests with fast failure
pytest tests/unit/ -k "not slow"   # Exclude slow tests
pytest --cov=src --cov-report=term-missing  # Identify uncovered code
```

### Environment Recovery
```bash
# Environment issues
make clean                    # Clean Docker resources
make status                   # Check project status

# Docker environment recovery
docker-compose down -v        # Stop and remove volumes
docker-compose up -d          # Fresh start
docker-compose logs -f app    # Check startup issues
```

### Code Quality Recovery
```bash
# Quality issues
make fix-code               # Auto-fix most issues
make format                 # Format all code
make lint                  # Identify remaining issues

# Import and dependency issues
pip install --upgrade pip   # Update pip
pip install -e ".[dev]"     # Reinstall development dependencies
```

## 🤖 自动化脚本工具

### 快速优化脚本
```bash
./quick_optimize.sh     # 快速优化代码质量 (一键修复所有问题)
```

### 维护脚本 (scripts/)
```bash
# 数据库管理
scripts/backup_db.sh     # 备份数据库
scripts/restore_db.sh    # 恢复数据库
scripts/db-migrate.sh    # 运行数据库迁移

# 质量保证
scripts/quality/intelligent_quality_analyzer.py        # 智能质量分析
scripts/quality/continuous_improvement_engine.py      # 持续改进引擎
scripts/maintenance/scheduled_maintenance.py         # 定期维护
scripts/maintenance/coverage_trend_analyzer.py        # 覆盖率趋势分析

# 部署和验证
scripts/deploy.sh         # 部署脚本
scripts/deploy_verify.sh  # 部署验证
scripts/security_check.sh # 安全检查

# 监控和日志
scripts/start_monitoring.sh # 启动监控系统
```

### GitHub Actions CI/CD 工作流
```yaml
# .github/workflows/
├── ci_pipeline_v2.yml         # CI/CD流水线
├── production-deploy.yml      # 生产部署
├── smart-fixer-ci.yml          # 智能修复CI
├── docs.yml                    # 文档构建
├── branch-protection.yml       # 分支保护
├── issues-cleanup.yml         # Issue清理
├── ai-feedback.yml            # AI反馈
└── deploy.yml                  # 部署流程
```

### CI/CD 流水线特性
- **自动化测试**: 4597个测试函数自动执行
- **代码质量检查**: Ruff + MyPy + Bandit 三重检查
- **安全扫描**: 依赖漏洞检测和代码安全审计
- **覆盖率门槛**: 31%覆盖率刚性要求
- **智能修复**: 自动修复常见代码问题
- **部署验证**: 生产部署前完整性检查
- **环境清理**: 定期清理临时资源和过期数据

## 🔄 Git Workflow

### Commit Message Format
```bash
# Features
feat(api): add user authentication endpoint
feat(ml): implement XGBoost prediction model

# Fixes
fix(database): resolve async connection timeout issue
fix(tests): restore 100+ core test functionality

# Quality
refactor(api): extract validation logic to service layer
style(core): apply ruff formatting to all files

# Maintenance
chore(deps): update FastAPI to 0.121.2
chore(security): upgrade MLflow to 2.22.2 for security patches
```

### Pre-Commit Checklist
- [ ] Tests pass: `make test`
- [ ] Code quality: `make fix-code`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Full validation: `make lint && make test`

## 📊 Current Project Status

### Quality Metrics
- **Test Coverage**: Use `make test.unit --cov=src --cov-report=term-missing`
- **Test Cases**: 4597 test functions across 274 test files (unit/integration/e2e)
- **Code Quality**: Ruff + Black + Bandit validation passing
- **Security**: No critical vulnerabilities, ECDSA vulnerability patched
- **CI/CD**: Green pipeline with automated recovery

### Health Score
```
Overall Health: 85/100 ✅
├── Code Quality: 90/100 ✅
├── Testing: 70/100 ⚠️
├── Documentation: 95/100 ✅
├── Security: 95/100 ✅
├── CI/CD: 90/100 ✅
└── Dependencies: 90/100 ✅
```

## 🎨 Frontend Architecture

### React + TypeScript Stack
- **React 19.2.0**: Modern React with concurrent features
- **TypeScript 4.9.5**: Full type safety with strict mode
- **Ant Design 5.27.6**: Enterprise-grade component library
- **Redux Toolkit 2.9.2**: State management with RTK Query
- **React Query**: Server state management and caching
- **Vite**: Fast build tool with HMR

### Frontend Development Commands
```bash
# Frontend development (在 frontend/ 目录中)
cd frontend
npm install              # 安装依赖
npm start               # 启动开发服务器 (port 3000)
npm run build           # 生产构建
npm test                # 运行前端测试
```

### Frontend Project Structure
```
frontend/
├── src/
│   ├── components/     # 可重用UI组件
│   ├── pages/         # 页面组件
│   ├── hooks/         # 自定义React hooks
│   ├── store/         # Redux store配置
│   ├── services/      # API服务函数
│   ├── types/         # TypeScript类型定义
│   ├── utils/         # 前端工具函数
│   └── styles/        # CSS和样式
├── public/            # 静态资源
└── tests/             # 前端测试文件
```

### Frontend State Management
```typescript
// Redux Toolkit store configuration
import { configureStore } from '@reduxjs/toolkit'
import { predictionApi } from './services/predictionApi'

export const store = configureStore({
  reducer: {
    [predictionApi.reducerPath]: predictionApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(predictionApi.middleware),
})
```

### 前端开发环境访问
- **Frontend Dev Server**: http://localhost:3000 (Vite开发服务器)
- **Backend API**: http://localhost:8000 (FastAPI应用)
- **API Documentation**: http://localhost:8000/docs (交互式OpenAPI)
- **Frontend in Production**: http://localhost (通过nginx反向代理)

## 🤖 AI Assistant Configuration

### Claude Code Integration
This project is AI-first maintained with these configurations:

#### Development Workflow
1. **Environment Setup**: `make dev` - Start development environment
2. **Development**: Write code following DDD + CQRS patterns
3. **Quality Validation**: `make lint && make test` - Code quality and testing
4. **Security Check**: `make security-check` - Security scanning
5. **Pre-commit**: `make fix-code && make format` - Code cleanup and validation

#### AI Tool Guidelines
- **Architecture Priority**: Maintain DDD layer separation and CQRS patterns
- **Testing First**: Write tests before implementation (TDD approach)
- **Async Everywhere**: All I/O operations must be async (database, APIs)
- **Type Safety**: Complete type annotations required for all functions
- **Error Handling**: Comprehensive exception handling with proper logging
- **Security First**: Never expose secrets, validate all inputs

#### Preferred Patterns
```python
# ✅ Preferred: Service layer with dependency injection
async def get_prediction_use_case(
    match_id: int,
    prediction_service: PredictionService,
    prediction_repo: PredictionRepository
) -> Dict[str, Any]:
    prediction = await prediction_service.generate_prediction(match_id)
    await prediction_repo.save_prediction(prediction)
    return prediction

# ❌ Avoid: Direct database access in API layer
@app.get("/predictions/{match_id}")
async def get_prediction(match_id: int, db: AsyncSession):
    # Business logic should be in service layer
    result = await db.execute(select(Prediction).where(Prediction.match_id == match_id))
    return result.scalar_one_or_none()
```

## 📊 监控和运维

### 生产环境监控栈
- **Prometheus**: 指标收集和存储 (port: 9090)
- **Grafana**: 可视化仪表板 (port: 3000)
- **Loki**: 日志聚合 (port: 3100)
- **健康检查**: 多层次健康监测

### 监控命令
```bash
# 容器监控
make monitor              # 实时监控应用资源使用
make monitor-all          # 监控所有容器资源使用

# 日志查看
make logs                 # 查看应用日志
make logs-db             # 查看数据库日志
make logs-redis          # 查看Redis日志

# 健康检查
curl http://localhost:8000/health               # 应用健康检查
curl http://localhost:8000/health/system          # 系统健康检查
curl http://localhost:8000/health/database       # 数据库健康检查
curl http://localhost:8000/api/v1/health/inference # 推理服务健康检查
```

### 性能监控
```bash
# Prometheus 指标访问
curl http://localhost:9090/metrics              # Prometheus指标
curl http://localhost:8000/metrics               # 应用指标

# 系统资源监控
docker stats                                     # 查看容器资源使用
docker-compose ps                               # 检查服务状态
```

### 质量保证
- **测试覆盖率**: 31% CI门槛要求
- **代码质量**: Ruff + MyPy + Bandit 三重检查
- **安全扫描**: 定期安全审计和漏洞修复
- **性能监控**: 实时性能指标和趋势分析

## 🌐 Application URLs

### Development Access
- **Frontend**: http://localhost:3000 (React development server)
- **Backend API**: http://localhost:8000 (FastAPI application)
- **API Documentation**: http://localhost:8000/docs (Interactive OpenAPI)
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/system/status
- **Inference Service**: http://localhost:8000/api/v1/health/inference
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws
- **MLflow UI**: http://localhost:5000 (ML experiment tracking)

### Production Monitoring Access
- **Grafana Dashboard**: http://localhost:3000 (监控仪表板)
- **Prometheus**: http://localhost:9090 (指标存储)
- **Loki**: http://localhost:3100 (日志聚合)
- **Frontend Production**: http://localhost (nginx反向代理)

### Quality Dashboard
- **Quality Monitor**: http://localhost:3001 (Independent quality monitoring)

## 🚀 Quick Start for New Development

### Environment Prerequisites
```bash
# 确保以下工具已安装
docker --version
docker-compose --version
python3 --version  # Python 3.10+
make --version
```

### 5-Minute Setup
```bash
# 1. Environment initialization
make dev                    # 启动完整开发环境

# 2. Validate setup
make test && make lint      # 验证环境和代码质量

# 3. Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Database: make db-shell
```

### Quick Development Commands
```bash
# 快速启动完整开发环境 (推荐)
make dev

# 启动生产环境 (带监控)
make prod

# 代码质量快速修复
./quick_optimize.sh

# 查看所有服务状态
make status

# 停止所有服务
make down
```

### First Development Tasks
1. Read `src/main.py` to understand the application structure
2. Review `pyproject.toml` for dependencies and tool configurations
3. Check `Makefile` for available development commands
4. Run `make test.smart` to verify the testing environment
5. Access API documentation at http://localhost:8000/docs

## 🔍 Common Development Patterns

### Database Operations (Async Only)
```python
# ✅ Correct: Async database operations
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ❌ Wrong: Sync database operations
user = db.query(User).filter(User.id == user_id).first()
```

### API Response Patterns
```python
from src.api.schemas import PredictionResponse

@app.get("/api/v1/predictions/{match_id}")
async def get_prediction(match_id: int) -> PredictionResponse:
    try:
        prediction = await inference_service.predict_match(match_id)
        return PredictionResponse(success=True, data=prediction)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction service unavailable")
```

### Service Layer Integration
```python
# Service injection pattern
from src.services.prediction import PredictionService
from src.database.repositories import PredictionRepository

async def get_prediction_use_case(
    match_id: int,
    prediction_service: PredictionService,
    prediction_repo: PredictionRepository
) -> Dict[str, Any]:
    # Use case orchestration
    prediction = await prediction_service.generate_prediction(match_id)
    await prediction_repo.save_prediction(prediction)
    return prediction
```

## 🔗 API Usage Patterns

### Standard API Response Format
```python
from src.api.schemas import PredictionResponse

# Standard success response
{
    "success": True,
    "data": {...},
    "message": "Operation completed successfully",
    "timestamp": "2025-01-01T00:00:00Z"
}

# Error response format
{
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input parameters",
        "details": {...}
    },
    "timestamp": "2025-01-01T00:00:00Z"
}
```

### Common API Endpoints Usage
```python
# Health checks
GET /health                    # Basic health check
GET /health/system             # System health (CPU, memory)
GET /health/database           # Database connectivity

# Predictions API (v1 and v2)
GET /api/v1/predictions/{match_id}              # Single match prediction
POST /api/v1/predictions/batch                  # Batch predictions
GET /api/v2/predictions/{match_id}/analysis      # Enhanced prediction with analysis
GET /predictions/{match_id}                     # Direct prediction endpoint

# Data management
GET /api/v1/data_management/teams               # Get all teams
POST /api/v1/data_management/matches/sync       # Sync match data
GET /api/v1/data_management/leagues/{id}/table  # League table

# System management
GET /api/v1/system/status                       # System status
POST /api/v1/system/cache/clear                 # Clear cache
GET /api/v1/system/metrics                      # Performance metrics

# Adapters and external integrations
GET /api/v1/adapters/{service}/status           # External service status
POST /api/v1/adapters/{service}/sync            # Sync external data

# Monitoring and metrics
GET /metrics                                    # Prometheus metrics
GET /api/v1/monitoring/health                   # Application health monitoring
```

### WebSocket Real-time Communication
```python
# WebSocket connection for real-time updates
import asyncio
import json
import websockets

async def handle_realtime_updates():
    uri = "ws://localhost:8000/api/v1/realtime/ws"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            data = json.loads(message)

            if data['type'] == 'prediction_update':
                # Handle real-time prediction updates
                await handle_prediction_update(data['payload'])
            elif data['type'] == 'match_status':
                # Handle match status changes
                await handle_match_status_change(data['payload'])
            elif data['type'] == 'system_metrics':
                # Handle system monitoring data
                await handle_system_metrics(data['payload'])

# Client usage example
import websocket

def on_message(ws, message):
    data = json.loads(message)
    if data['type'] == 'prediction_update':
        handle_prediction_update(data['payload'])

ws = websocket.WebSocketApp(
    "ws://localhost:8000/api/v1/realtime/ws",
    on_message=on_message
)
ws.run_forever()
```

## 📞 Troubleshooting Guide

### Common Issues
1. **Test Failures**: Run `make solve-test-crisis` immediately
2. **Type Errors**: Check imports and add missing type hints
3. **Database Issues**: Verify connection string and PostgreSQL status
4. **Redis Issues**: Check Redis service status and connection
5. **Import Errors**: Run `make fix-imports` to resolve import problems
6. **Port Conflicts**: Check if ports 8000, 3000, 5432, 6379 are available

### Environment Debugging
```bash
# Check service status
docker-compose ps                    # All containers status
docker-compose logs app              # Application logs
docker-compose logs db               # Database logs
docker-compose logs redis            # Redis logs

# Database debugging
make db-shell                        # Connect to PostgreSQL
\dt                                  # List tables
SELECT COUNT(*) FROM matches;        # Verify data

# Redis debugging
make redis-shell                     # Connect to Redis
KEYS *                               # List all keys
INFO memory                          # Memory usage
```

### Performance Issues
```bash
# Performance monitoring
curl http://localhost:8000/metrics   # Prometheus metrics
curl http://localhost:8000/system/status  # System status

# Load testing (if installed)
ab -n 100 -c 10 http://localhost:8000/health  # Apache bench
```

### Emergency Commands
```bash
# Complete environment reset
make clean && make test

# Health check all services
make status

# Code quality emergency
make fix-code && make format && make lint

# Database recovery
docker-compose down -v && docker-compose up -d

# Dependency issues
pip install --upgrade pip

# Test failures - quick diagnosis
pytest tests/unit/ --tb=short --maxfail=3
pytest tests/unit/ -k "critical or smoke"

# Performance issues
docker stats                    # Check container resource usage
curl http://localhost:8000/metrics  # Check application metrics
```

## 📚 Additional Resources

### Documentation
- **API Documentation**: http://localhost:8000/docs (Interactive OpenAPI)
- **ReDoc**: http://localhost:8000/redoc (Alternative API docs)
- **MLflow Tracking**: http://localhost:5000 (ML experiments)
- **Coverage Report**: `htmlcov/index.html` (Test coverage visualization)

### Development Tools
- **Adminer**: http://localhost:8080 (Database admin, if enabled)
- **Redis Commander**: http://localhost:8081 (Redis admin, if enabled)
- **Prometheus**: http://localhost:9090 (Metrics, if configured)

### Key Configuration Files
- `pyproject.toml` - Python dependencies and tool configuration
- `docker-compose.*.yml` - Container orchestration
- `Makefile` - Development workflow commands
- `.env.*` - Environment configurations

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. When in doubt, choose the conservative approach that preserves existing patterns and maintains the green CI pipeline.

## 📋 Development Environment Reference

### Minimum Requirements
- **Python**: 3.10+ (recommended: 3.11)
- **Docker**: 20.0+ with docker-compose
- **Memory**: 4GB+ RAM for development
- **Storage**: 10GB+ free disk space

### Service Ports
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **API Docs**: http://localhost:8000/docs

### Key File Locations
- **Main App**: `src/main.py` - FastAPI application entry point
- **Config**: `pyproject.toml` - Dependencies and tool configuration
- **Docker**: `docker-compose.yml` - Development environment
- **Makefile**: Development commands and workflows
- **Tests**: `tests/` - 4597 test functions across 274 test files (unit/integration/e2e)

*Last Updated: 2025-11-25 | AI Maintainer: Claude Code | Version: 1.3*