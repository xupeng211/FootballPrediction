# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**请使用简体中文回复用户** - Please respond in Simplified Chinese when interacting with the user. The project team primarily communicates in Chinese, so all responses should be in Simplified Chinese unless specifically requested otherwise.

## 快速命令查找表

| 任务类型 | 首选命令 | 备选方案 | 说明 |
|---------|----------|----------|------|
| **环境启动** | `make dev` | `make quick-start` | 启动完整开发环境 |
| **运行测试** | `make test.unit` | `make test` | 单元测试 / 全部测试 |
| **代码检查** | `make lint && make fix-code` | `make ci` | 检查并修复 / 完整CI验证 |
| **服务状态** | `make status` | `docker-compose ps` | 检查所有服务健康状态 |
| **进入容器** | `make shell` | `docker-compose exec app bash` | 进入app容器 |
| **查看日志** | `make logs` | `docker-compose logs -f app` | 应用日志 |
| **数据库操作** | `make db-shell` | `docker-compose exec db psql -U postgres` | 连接数据库 |
| **覆盖率报告** | `make coverage` | `open htmlcov/index.html` | 生成/查看覆盖率 |

## 项目质量基线

- **Build Status**: Stable (Green Baseline Established)
- **Test Coverage**: 29.0% baseline (持续改进中)
- **Total Tests**: 385 tests passing
- **Security**: Bandit validated, dependency vulnerabilities fixed
- **Code Quality**: A+ grade through ruff, mypy quality checks
- **Python版本**: 支持 3.10/3.11/3.12 (推荐 3.11)

## Project Overview

This is an enterprise-level football prediction system built with Python FastAPI, following Domain-Driven Design (DDD), CQRS, and Event-Driven architecture patterns. The system uses modern async/await patterns throughout and includes machine learning capabilities for match predictions.

**Project Scale**:
- **Large-scale Python project** - Enterprise-grade application architecture
- **Comprehensive testing** - Four-layer testing architecture (Unit: 85%, Integration: 12%, E2E: 2%, Performance: 1%)
- **Complete workflow automation** - 259-line Makefile with comprehensive development commands
- **40+ API endpoints** - Supporting both v1 and v2 versions
- **7 dedicated queues** - Celery distributed task scheduling
- **Current test coverage**: 29.0% baseline (as measured in latest CI runs)

## Quick Reference (快速参考)

### 5分钟快速上手
```bash
# 完整环境启动
make dev && make status && make test.unit && make coverage

# 开发流程 essentials
make dev              # 启动环境
make test.unit        # 运行单元测试
make lint             # 代码检查
make ci               # 完整CI验证
```

### 常用命令速查
| 任务 | 命令 | 说明 |
|------|------|------|
| 环境管理 | `make dev` / `make dev-stop` | 启动/停止开发环境 |
| 测试 | `make test.unit` / `make coverage` | 单元测试/覆盖率 |
| 代码质量 | `make lint && make fix-code` | 检查并自动修复 |
| 容器操作 | `make shell` / `make logs` | 进入容器/查看日志 |
| 数据库 | `make db-shell` / `make db-reset` | 数据库操作 |
| 状态检查 | `make status` | 检查所有服务状态 |
| 快速启动 | `make quick-start` | 快速启动开发环境 |

## Key Development Commands

### Environment Management
```bash
# Start development environment
make dev

# Start production environment
make prod

# Stop services
make dev-stop

# Clean resources
make clean
make clean-all  # 彻底清理所有资源

# Check service status
make status

# Build and deployment
make build
make dev-rebuild
make prod-rebuild

# Complete CI validation
make ci

# Quick commands
make quick-start  # 快速启动 (别名)
make quick-stop   # 快速停止 (别名)
```

### Code Quality & Testing
```bash
# Run tests (always use Makefile commands, never run pytest directly)
make test               # Run all tests
make test.unit          # Unit tests only
make test.integration   # Integration tests only
make test.all           # All tests with full reporting

# Code quality checks
make lint               # Ruff code checks (MyPy disabled for CI stability)
make format             # Code formatting with ruff
make fix-code           # Auto-fix issues with ruff
make type-check         # MyPy type checking
make security-check     # Security scanning with bandit

# Coverage analysis
make coverage           # Generate coverage report
open htmlcov/index.html # View coverage report (macOS)
xdg-open htmlcov/index.html # View coverage report (Linux)

# CI validation (pre-commit checks)
make lint && make test && make security-check && make type-check
```

### Docker Development
```bash
# Access containers
make shell              # Enter app container
make shell-db           # Enter database container
make db-shell           # Connect to PostgreSQL
make redis-shell        # Connect to Redis

# View logs
make logs               # Application logs
make logs-db            # Database logs
make logs-redis         # Redis logs

# Container monitoring
make monitor            # Monitor app container resources
make monitor-all        # Monitor all container resources

# Performance monitoring
docker-compose exec app python -c "
import psutil
import time
print(f'CPU: {psutil.cpu_percent()}%')
print(f'Memory: {psutil.virtual_memory().percent}%')
print(f'Disk: {psutil.disk_usage(\"/\").percent}%')
"

# Database performance analysis
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Quick health check (under 5 seconds)
docker-compose exec app python -c "
import asyncio
import aiohttp
async def check():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as resp:
                print('✅ API Health:', await resp.text())
    except Exception as e:
        print('❌ API Health Check Failed:', e)
asyncio.run(check())
"
```

### Database Management
```bash
# Database operations
make db-reset           # Reset database (WARNING: destroys data)
make db-migrate         # Run database migrations
```

### Celery Task Management
```bash
# Celery services
celery -A src.tasks.celery_app worker --loglevel=info       # Start worker
celery -A src.tasks.celery_app beat --loglevel=info         # Start scheduler
celery -A src.tasks.celery_app flower                       # Start Flower UI

# Task execution and monitoring
celery -A src.tasks.celery_app call tasks.data_collection_tasks.collect_fotmob_data  # Manual data collection
docker-compose exec app celery -A src.tasks.celery_app inspect active    # Check active tasks
docker-compose exec app celery -A src.tasks.celery_app inspect stats     # Task statistics
docker-compose exec app celery -A src.tasks.celery_app purge             # Clear task queue

# Advanced queue management
docker-compose exec app celery -A src.tasks.celery_app inspect reserved   # Check reserved tasks
docker-compose exec app celery -A src.tasks.celery_app inspect scheduled  # Check scheduled tasks
docker-compose exec app celery -A src.tasks.celery_app inspect revoked    # Check revoked tasks
docker-compose exec app celery -A src.tasks.celery_app -Q fixtures inspect active  # Inspect specific queue
```

### Extended Development Tools

#### Quick Optimization Scripts
```bash
# One-click code optimization
./quick_optimize.sh                           # 快速优化代码质量 (一键修复所有问题)
./verify-docker-setup.sh                     # Docker配置完整性验证脚本

# Environment health check
make doctor                                   # 全面环境健康检查
make env-check                               # Docker、依赖、端口验证
```

#### Data Backfill Tools
```bash
# Safe data backfill operations
scripts/backfill_fotmob_safe.py              # 安全FotMob数据回填 (带保护机制)
scripts/backfill_global.py                   # 全局数据回填 (完整数据集)
scripts/backfill_production.py               # 生产环境数据回填

# Data collection management
python -m src.data.collectors.fotmob_collector --dry-run  # 预览数据收集
python -m src.data.collectors.football_data_collector --validate  # 验证数据完整性
```

#### CI/CD Analysis Tools
```bash
# CI results analysis
ls -la ci_results/                            # CI结果目录查看
cat ci_results/ci_report.md                  # CI报告分析
cat ci_results/ci_results_*.json             # 详细CI结果JSON

# Test failure diagnostics
tail -f ci_*.log                              # 实时CI错误日志分析
grep "ERROR" ci_*.log                        # 错误模式快速定位
grep "FAIL" ci_*.log                         # 失败测试详细信息

# Performance analysis
python -c "import json; data=json.load(open('ci_results/ci_results_performance.json')); print(f'平均响应时间: {data[\"avg_response_time\"]:.2f}ms')"
```

#### Code Quality Enhancement
```bash
# Advanced code fixing
make fix-all                                  # 修复所有可自动修复的问题
make fix-imports                              # 修复导入语句
make fix-formatting                          # 修复代码格式问题

# Dependency management
make deps-update                              # 更新依赖项
make deps-check                               # 检查依赖项安全漏洞
make deps-audit                               # 全面依赖项审计
```

## Architecture

### Core Architecture Patterns

#### Domain-Driven Design (DDD)
- **Domain Layer**: `src/domain/` - Business logic and entities
- **Application Layer**: `src/services/` - Business process coordination
- **Infrastructure Layer**: `src/database/`, `src/cache/` - Technical implementations

#### CQRS (Command Query Responsibility Segregation)
- **Command Handling**: Write operations (Create, Update, Delete)
- **Query Handling**: Read operations (Get, List, Analytics)
- **Separate Optimization**: Independent scaling of reads and writes

#### Event-Driven Architecture
- **Event Bus**: `src/core/event_application.py` - Event publishing/subscription
- **Async Event Processing**: Event handler registration and lifecycle
- **Loose Coupling**: Components communicate through events

### Extended Architecture Components

#### Stream Processing Layer (`src/streaming/`)
- **Real-time Data Streams**: WebSocket-based real-time data processing and updates
- **Message Queue Integration**: Advanced message queuing with event-driven architecture
- **Live Prediction Updates**: Real-time prediction synchronization and status updates
- **Stream Analytics**: Real-time data analysis and pattern detection

#### Data Lineage Management (`src/lineage/`)
- **Data Source Tracking**: Complete data provenance and lineage relationship management
- **Quality Auditing**: Data quality audits and compliance checking
- **Metadata Management**: Centralized metadata management and data catalog
- **Impact Analysis**: Data change impact analysis and dependency tracking

#### Quality Monitoring Dashboard (`src/quality_dashboard/`)
- **Real-time Quality Metrics**: Live quality指标监控 with comprehensive visualization
- **Test Coverage Visualization**: Interactive test coverage and code quality dashboards
- **Performance Benchmarks**: Performance baseline tracking and trend analysis
- **Quality Gates**: Automated quality gate enforcement and reporting

#### Localization & Internationalization (`src/locales/zh_CN/`)
- **Chinese Interface**: Complete Chinese language support and localization
- **Multi-language Resources**: Comprehensive multi-language resource management
- **Cultural Adaptation**: Cultural adaptation and regional configuration support
- **Dynamic Language Switching**: Runtime language switching capabilities

#### Feature Management (`src/features/`)
- **Feature Flags**: Dynamic feature flag management and A/B testing support
- **Progressive Rollout**: Controlled feature rollout with gradual deployment
- **Feature Analytics**: Feature usage analytics and performance monitoring
- **Rollback Capabilities**: Instant feature rollback and recovery mechanisms

### Technology Stack

#### Backend Core
- **FastAPI**: Modern async web framework (v0.121.2) with 40+ API endpoints
- **Database**: PostgreSQL 15 with async SQLAlchemy 2.0+ (v2.0.36)
- **Cache**: Redis 7.0+ for caching and Celery broker (v7.2.5)
- **ORM**: SQLAlchemy 2.0+ with async connection pooling (v2.0.36)
- **Serialization**: Pydantic v2+ for data validation (v2.10.3)
- **HTTP Client**: httpx for async HTTP requests (v0.27.2)
- **Async Support**: aiohttp for high-performance async operations (v3.11.10)

#### Machine Learning
- **ML Framework**: XGBoost 2.0+ (v2.1.1), scikit-learn 1.3+ (v1.5.2), TensorFlow/Keras (v2.18.0)
- **ML Management**: MLflow 2.22.2+ for experiment tracking and model management
- **Feature Engineering**: pandas 2.1+ (v2.2.3), numpy 1.25+ (v1.26.4)
- **Optimization**: Optuna 4.6.0+ (v4.1.1) for hyperparameter tuning
- **ML Extensions**: scikit-learn-extra, shap for model interpretability
- **Deep Learning**: TensorFlow 2.18.0 with Keras integration

#### Frontend
- **Framework**: React 19.2.0, TypeScript 4.9.5 (v5.6.3)
- **UI Library**: Ant Design 5.27+ (v5.21.6)
- **Build Tools**: Vite for modern bundling (v6.0.1)
- **State Management**: Redux Toolkit for state management
- **Styling**: Styled-components and CSS-in-JS support
- **Testing**: Jest and React Testing Library for frontend testing

#### Development Tools
- **Code Quality**: Ruff 0.14+ (v0.8.2) for linting/formatting, Bandit 1.8.6+ (v1.8.0) for security
- **Testing**: pytest 8.4.0+ (v8.3.4) with asyncio support, pytest-cov 7.0+ (v6.0.0)
- **Type Checking**: MyPy 1.18+ (v1.13.0) (temporarily disabled for CI stability)
- **Dependencies**: pip-tools 7.4.1+ (v7.4.1), pre-commit 4.0.1+ (v4.0.1)
- **Documentation**: mkdocs for documentation generation
- **Code Analysis**: sonar-scanner for code quality analysis
- **Performance**: pytest-benchmark for performance testing

#### Additional Infrastructure
- **Message Queue**: Celery 5.3+ (v5.4.0) with Redis broker
- **Containerization**: Docker 27.0+ and Docker Compose 2.29+
- **Process Management**: Supervisor for production process management
- **Logging**: structlog for structured logging (v24.4.0)
- **Monitoring**: psutil for system monitoring (v6.1.1)
- **Cryptography**: cryptography for security operations (v44.0.0)

### Database & Caching

#### Database Architecture
- **Primary Database**: PostgreSQL 15 with async SQLAlchemy 2.0
- **Connection Pooling**: Async connection pool with health checks
- **Migrations**: Alembic for schema management
- **Data Replication**: Support for master-slave replication

#### Caching Strategy
- **Multi-layer Caching**: Redis 7.0+ with intelligent cache invalidation
- **Session Storage**: Redis for user sessions and temporary data
- **Query Caching**: Automatic caching for frequently accessed data
- **Cache Performance**: Optimized cache keys and TTL strategies

### Container Architecture

#### Development Services
- **app**: FastAPI application (port: 8000) - 主应用服务，支持热重载
- **db**: PostgreSQL 15 (port: 5432) - 主数据库，带健康检查
- **redis**: Redis 7.0 (port: 6379) - 缓存和Celery消息队列
- **frontend**: React application (内部80端口，外部映射到3000) - 前端应用
- **nginx**: Reverse proxy (port: 80) - 反向代理，统一入口
- **worker**: Celery worker for async tasks - 异步任务处理器，8个专用队列
- **beat**: Celery beat for scheduled tasks - 定时任务调度器

#### Container Features
- **Health Checks**: 所有服务都有完善的健康监控机制
- **Hot Reload**: 开发环境支持代码热重载 (`./src:/app/src`)
- **Environment Isolation**: 开发和生产环境配置分离
- **Multi-stage Builds**: Docker镜像优化，支持开发和生产阶段
- **Volume Management**: 数据持久化 (postgres_data, redis_data, celerybeat_data)
- **Dependency Management**: 服务间依赖关系和启动顺序管理

### Multi-Environment Docker Configurations

#### Environment Variants
```bash
# Complete development stack
docker-compose.yml                              # 完整开发环境 (所有服务)

# Lightweight environments
docker-compose.lightweight.yml                 # 轻量级开发栈 (核心服务 only)
docker-compose.dev.yml                          # 开发专用配置 (调试工具增强)
docker-compose.local.yml                        # 本地开发配置 (本地优化)

# Production environments
docker-compose.prod.yml                         # 生产环境 (性能优化 + 安全加固)
docker-compose.staging.yml                      # 预发布环境 (生产前验证)
docker-compose.microservices.yml               # 微服务架构 (服务解耦)

# Specialized configurations
docker-compose.full-test.yml                   # 全面测试环境 (测试工具集成)
docker-compose.optimized.yml                   # 性能优化配置 (资源优化)
docker-compose.monitoring.yml                  # 监控专用 (完整监控栈)
config/docker-compose.local.yml               # 本地配置覆盖
```

#### Frontend Docker Configuration
```bash
# Frontend build and deployment
frontend/Dockerfile                            # 多阶段构建 (开发 + 生产)
frontend/docker-compose.dev.yml               # 前端开发环境
frontend/docker-compose.prod.yml              # 前端生产环境

# Build optimization
docker build -t football-frontend:latest ./frontend/
docker build -f frontend/Dockerfile.prod -t football-frontend:prod ./frontend/
```

#### Docker Validation Tools
```bash
# Configuration validation
./verify-docker-setup.sh                      # Docker配置完整性验证
docker-compose config                          # 验证Docker Compose配置
docker-compose config --quiet                  # 静默配置验证

# Service health verification
docker-compose ps                              # 检查所有服务状态
docker-compose exec app python -c "import asyncio; print('✅ App healthy')"  # 应用健康检查

# Resource monitoring
docker stats                                   # 实时资源使用监控
docker-compose exec app python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%')"  # CPU监控
```

#### Environment Management Commands
```bash
# Quick environment switching
make dev-lightweight                          # 启动轻量级开发环境
make dev-full                                  # 启动完整开发环境
make prod-start                               # 启动生产环境

# Environment migration
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.lightweight.yml up -d  # 切换到轻量级环境

# Configuration debugging
docker-compose config --services              # 列出所有服务
docker-compose config --volumes               # 列出所有卷
docker-compose config --networks              # 列出所有网络
```

## Code Requirements

### Development Standards

#### Async-First Architecture
- **Mandatory**: All I/O operations must use async/await patterns
- **Database Operations**: Use async SQLAlchemy sessions
- **External APIs**: Use httpx or aiohttp for async HTTP calls
- **File Operations**: Use aiofiles for async file handling

#### Type Safety
- **Complete Annotations**: All functions must have full type hints
- **Pydantic Models**: Use for data validation and serialization
- **IDE Support**: Full type hints for better development experience
- **Runtime Validation**: Pydantic ensures data integrity

#### Testing Standards
- **Test-Driven**: Write tests before implementation code
- **Coverage Target**: Maintain 29.0% baseline with continuous improvement
- **Async Testing**: Use pytest-asyncio for async function testing
- **Test Isolation**: Each test should be independent and isolated

### Database Pattern
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

### Service Layer Pattern
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
```

## Testing Strategy

### Test Architecture
The project uses a four-layer testing strategy:

- **Unit Tests (85%)**: Fast, isolated component tests
- **Integration Tests (12%)**: Database, cache, and external API integration
- **E2E Tests (2%)**: Complete user flow testing
- **Performance Tests (1%)**: Load and stress testing

### Test Markers
```python
# Core test type markers
@pytest.mark.unit           # Unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.e2e           # End-to-end tests
@pytest.mark.performance   # Performance tests

# Functional domain markers
@pytest.mark.api           # HTTP endpoint testing
@pytest.mark.domain        # Domain layer business logic
@pytest.mark.services      # Service layer testing
@pytest.mark.database      # Database connection tests
@pytest.mark.cache         # Redis and caching logic
@pytest.mark.ml            # Machine learning tests
```

### 测试运行黄金法则 🏆

```bash
# ✅ 正确: 始终使用 Makefile 命令 (确保CI/localhost一致性)
make test.unit          # 仅单元测试
make test.integration   # 仅集成测试
make test.all           # 全部测试 + 完整报告
make coverage           # 生成覆盖率报告

# ❌ 错误: 永远不要直接运行 pytest 单个文件
pytest tests/unit/specific.py  # 这会导致环境不一致问题

# ⚠️ 高级测试命令 (仅在调试时谨慎使用)
pytest tests/unit/test_specific.py::test_function -v     # 调试单个测试
pytest tests/unit/ -k "test_keyword" -v                   # 关键字过滤
pytest tests/unit/ -m "unit and not slow" -v              # 标记过滤
pytest tests/unit/ --maxfail=3 -x                         # 快速失败
pytest tests/ -n auto                                     # 并行执行
pytest --cov=src --cov-report=html --cov-report=term-missing  # 覆盖率
```

### 关键测试原则 (Critical Testing Rules)

1. **环境一致性原则** - **Always use Makefile commands**
   - 确保本地开发环境与CI环境完全一致
   - 避免依赖版本冲突和环境差异
   - 使用容器化测试保证隔离性

2. **测试隔离原则** - Each test must be independent
   - 每个测试必须独立，不能依赖其他测试的状态
   - 使用事务回滚或测试数据库避免数据污染

3. **异步测试原则** - Proper async testing patterns
   - 所有异步函数必须使用正确的 pytest-asyncio 模式
   - 使用适当的异步测试夹具和等待机制

4. **外部API处理原则** - Mock in unit, real in integration
   - 单元测试中模拟外部API调用
   - 集成测试中使用真实API进行验证

**🔥 记住：测试运行的黄金法则是"Always use Makefile commands"，这是确保项目稳定性的核心原则！**

### Enhanced Testing Strategy

#### CI Testing Analysis
```bash
# CI results查看和分析
ls -la ci_results/                            # CI结果目录结构
cat ci_results/ci_report.md                  # CI执行报告分析
cat ci_results/ci_results_*.json             # 详细CI结果数据
jq '.test_summary' ci_results/ci_results_*.json  # JSON格式测试摘要

# Test failure诊断和调试
tail -f ci_*.log                              # 实时跟踪CI错误日志
grep "ERROR\|FAIL\|FAILED" ci_*.log          # 快速定位失败测试
grep -A 5 -B 5 "AssertionError" ci_*.log     # 详细错误上下文
python -c "
import json
with open('ci_results/ci_results_performance.json') as f:
    data = json.load(f)
    print(f'平均响应时间: {data[\"avg_response_time\"]:.2f}ms')
    print(f'成功率: {data[\"success_rate\"]:.1f}%')
"
```

#### Quality Gates Enforcement
```bash
# 三重质量检查流水线
make lint && make test && make security-check  # 代码检查 + 测试 + 安全扫描
make ci-check                                   # 完整CI验证流水线
make pre-push                                   # 提交前完整验证

# 覆盖率质量门禁 (31%门槛)
make coverage                                   # 生成覆盖率报告
pytest --cov=src --cov-fail-under=31 --cov-report=term-missing  # 覆盖率门槛检查

# Performance quality gates
make test.performance                          # 性能基准测试
make benchmark                                 # 性能基准对比
```

#### Smart Testing Commands
```bash
# 智能测试验证 (根据变更自动选择测试)
make test.smart                               # 智能测试：基于Git变更选择相关测试
make test.affected                            # 运行受影响模块的测试
make test.focus                               # 专注测试：排除慢速和不稳定测试

# 危机恢复命令
make solve-test-crisis                        # 解决测试危机 (清理 + 重新运行)
make test.crime-recovery                      # 测试犯罪现场恢复
make test.stability                           # 测试稳定性验证

# 快速验证命令
make test.quick                               # 快速测试 (核心功能 only)
make test.smoke                               # 冒烟测试 (关键路径)
pytest tests/unit/ -k "not slow" --maxfail=3 -x  # 排除慢速测试，快速失败
```

#### Advanced Test Diagnostics
```bash
# 测试性能分析
pytest --durations=10                         # 显示最慢的10个测试
pytest --profile-svg                          # 生成性能分析SVG图
pytest tests/unit/ --benchmark-only          # 基准性能测试

# 测试覆盖率深度分析
make coverage-detailed                        # 详细覆盖率分析 (按模块)
coverage report --show-missing --sort=Cover   # 按覆盖率排序显示缺失行
coverage html                                 # 生成HTML覆盖率报告
open htmlcov/index.html                      # 查看交互式覆盖率报告

# 并行测试执行
pytest tests/ -n auto --dist=loadfile         # 自动并行测试
pytest tests/ -n 4 --maxprocesses=4          # 指定4个进程并行
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -n auto  # 并行覆盖率测试
```

### Test Configuration
- **Async Mode**: `asyncio_mode = "auto"` for automatic async detection
- **Test Paths**: `tests/` directory with recursive discovery
- **Coverage Source**: `src/` directory
- **Coverage Threshold**: 31% minimum baseline (CI enforcement)
- **Log Level**: INFO with structured logging format
- **Timeout**: 10-second test duration reporting
- **Parallel Execution**: Auto-detection for optimal performance
- **Quality Gates**: Automated enforcement via CI pipeline

## Special Features

### Intelligent Cold Start System
**File**: `src/main.py:53+` - `check_and_trigger_initial_data_fill()`

Enterprise-grade intelligent cold start system with automated database state detection:
- **Smart Database Analysis**: Auto-detects `matches` table record count
- **Multi-layer Time Awareness**: Decision-making based on last update timestamps
- **Adaptive Collection Strategy**: Empty database → Full collection, Stale data → Incremental updates
- **Real-time Decision Logging**: Detailed Chinese logging for each decision process
- **Fault Recovery**: Intelligent degradation and retry mechanisms

### Machine Learning Pipeline
**Directory**: `src/ml/` - Enterprise ML ecosystem

- **Prediction Engine**: XGBoost 2.0+ gradient boosting with LSTM deep learning support
- **Advanced Feature Engineering**: `enhanced_feature_engineering.py` - Automated feature extraction
- **Hyperparameter Optimization**: `xgboost_hyperparameter_optimization.py` - Bayesian optimization
- **Model Management**: MLflow 2.22.2+ experiment tracking and version control
- **Production Pipeline**: `football_prediction_pipeline.py` - End-to-end prediction workflow

### Enhanced Task Scheduling System
**File**: `src/tasks/celery_app.py` - Enterprise distributed task scheduling

- **7 Dedicated Queues**: fixtures, odds, scores, maintenance, streaming, features, backup
- **Smart Task Scheduling**: 7 cron jobs + 4 interval tasks with Celery Beat
- **Advanced Retry Mechanism**: Configurable exponential backoff, jitter, and error thresholds
- **Dynamic Task Routing**: Intelligent distribution based on task type and priority
- **Comprehensive Monitoring**: Real-time task status, performance metrics, and error tracking

### Real-time Monitoring & Performance
**Directory**: `src/monitoring/` - Comprehensive system observability

- **Infrastructure Monitoring**: CPU, memory, disk, network I/O with container support
- **Application Performance**: API response times, database connection pool status
- **Business Intelligence**: Prediction accuracy trends, data update frequency
- **Resource Usage Analysis**: psutil integration with container-level resource tracking
- **Structured Logging**: JSON format logs with multi-level filtering
- **Alerting**: Threshold-based intelligent alerting with multi-channel notifications

## API Usage

### Versioning Strategy
- **v1 API**: Traditional REST endpoints, maintaining backward compatibility
- **v2 API**: Optimized prediction API with higher performance and enhanced features
- **Progressive Migration**: Support smooth v1 to v2 migration
- **Version Coexistence**: Multiple API versions available simultaneously

### Key Endpoints
- **Health Checks**: `/health`, `/health/system`, `/health/database`
- **Predictions**: `/api/v1/predictions/`, `/api/v2/predictions/`
- **Data Management**: `/api/v1/data_management/`
- **System**: `/api/v1/system/`
- **Adapters**: `/api/v1/adapters/`
- **Real-time**: `/api/v1/realtime/ws` (WebSocket)
- **Monitoring**: `/metrics`

### Response Format
```python
# Success response
{
    "success": True,
    "data": {...},
    "message": "Operation completed successfully",
    "timestamp": "2025-01-01T00:00:00Z"
}

# Error response
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

## URLs & Access

### Development
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws

### Production Monitoring
- **Grafana Dashboard**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

### Sports Data APIs
- **Football-Data.org**: https://api.football-data.org/v4/
- **FotMob API**: https://www.fotmob.com/api/ (authentication required)
- **The Sports DB**: https://www.thesportsdb.com/api/v1/json/

## Configuration Files

### Key Files
- `pyproject.toml` - Dependencies and tool configuration
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment
- `Makefile` - Development workflow commands
- `.env.example` - Environment variable template

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# 5-minute quick start
make dev && make status && make test.unit && make coverage

# Step-by-step detailed setup
make dev              # Start complete Docker environment
make status           # Verify all services
make test.unit        # Run unit tests
make coverage         # Check coverage report

# Alternative setup for new developers
make install          # Install dependencies
make context          # Load project context and dependencies
make test             # Run test suite (385 tests)
./ci-verify.sh        # Local CI validation

# Configure real API keys
# Edit .env file with actual values:
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
FOTMOB_CLIENT_VERSION=production:208a8f87c2cc13343f1dd8671471cf5a039dced3
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0
```

### Environment Variable Priority
Environment variables are loaded in the following order (higher priority overrides lower):

1. **System Environment Variables** - Highest priority
2. **Docker Compose Environment** - `docker-compose.yml` environment section
3. **`.env` File** - Local environment configuration
4. **Default Values** - Built-in application defaults

### Required Environment Variables
- **FOOTBALL_DATA_API_KEY**: Essential for data collection (get from football-data.org)
- **SECRET_KEY**: JWT token security (use `openssl rand -hex 32` to generate)
- **DATABASE_URL**: PostgreSQL connection string
- **REDIS_URL**: Redis connection for caching and Celery broker

## AI辅助开发标准工作流 🤖

### 工具优先原则 (Tool-first Principle)

遵循经过验证的5步标准开发流程，确保代码质量和项目稳定性：

```bash
# 标准开发序列 (按顺序执行)
make env-check      # 1. 环境健康检查 - 验证Docker、依赖等
make context        # 2. 加载项目上下文和依赖关系
# 3. 开发实现阶段 - 编码、调试、实现功能
make ci             # 4. 质量验证 - 代码检查、测试、安全扫描
make prepush        # 5. 提交前完整验证 - 最终检查
```

### 工作流详解

#### 阶段1: 环境验证 (`make env-check`)
- 验证Docker服务状态
- 检查Python环境和依赖
- 确认端口可用性
- 验证数据库和Redis连接

#### 阶段2: 上下文加载 (`make context`)
- 安装/更新项目依赖
- 加载开发环境配置
- 初始化数据库结构（如需要）
- 准备测试数据和环境

#### 阶段3: 开发实现
- 遵循DDD + CQRS架构模式
- 编写异步优先的代码
- 实现完整的类型注解
- 编写相应的测试用例

#### 阶段4: 质量验证 (`make ci`)
- 代码风格检查 (`make lint`)
- 自动代码修复 (`make fix-code`)
- 安全扫描 (`make security-check`)
- 类型检查 (`make type-check`)
- 测试执行 (`make test`)

#### 阶段5: 提交前验证 (`make prepush`)
- 完整的CI流程模拟
- 覆盖率验证
- 性能基准测试
- 最终质量检查

### AI辅助开发最佳实践

1. **先工具，后编码** - 始终先验证环境，再开始开发
2. **持续验证** - 每个功能完成后立即运行质量检查
3. **测试驱动** - 使用Makefile命令确保测试一致性
4. **渐进式改进** - 小步快跑，频繁验证
5. **文档同步** - 及时更新相关文档和注释

**🎯 核心理念：通过标准化的工具链和流程，实现AI辅助开发的高效和可靠性！**

## CI/CD Pipeline & Validation

### GitHub Actions Integration
- **Smart CI System**: Automated CI pipeline with Python 3.10/3.11/3.12 matrix testing
- **Local CI Simulation**: `./ci-verify.sh` - Complete local CI validation before commits
- **Multi-environment Support**: Development, staging, and production deployment configurations
- **Automated Recovery**: Smart CI with automatic test failure detection and recovery suggestions

### Docker Compose Environments
The project includes **multiple specialized Docker Compose configurations** (52+ configuration files):
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production deployment
- `docker-compose.staging.yml` - Staging environment
- `docker-compose.microservices.yml` - Microservices architecture
- `docker-compose.full-test.yml` - Comprehensive testing environment
- `docker-compose.optimized.yml` - Performance-optimized configuration
- And 46+ specialized configurations for different use cases

## Important Reminders

### Critical Development Notes
- **Test Running**: Always use Makefile commands for testing, never run pytest directly on individual files
- **Docker Environment**: Mandatory use of Docker Compose for local development to ensure CI consistency
- **CI Validation**: Run `make lint && make test && make security-check && make type-check` before commits
- **Environment Check**: Always run `make status` to verify service health before development
- **Architecture Integrity**: Strictly follow DDD + CQRS + Event-Driven architecture patterns
- **Async-First**: All I/O operations must use async/await patterns

### Architecture Integrity
- **DDD Layer Separation**: Maintain clear boundaries between domain, application, and infrastructure layers
- **CQRS Implementation**: Separate command and query responsibilities
- **Event-Driven Design**: Use events for loose coupling between components
- **Type Safety**: Complete type annotations for all functions
- **Error Handling**: Comprehensive exception handling with structured logging

### Quality Assurance
- **Code Coverage**: Current baseline 29.0% with focus on continuous improvement
- **Security**: Regular security audits and dependency scanning via bandit
- **Performance**: Monitor and optimize API response times with dedicated middleware
- **Documentation**: Maintain comprehensive API documentation and system guides

## Troubleshooting

### Common Issues
1. **Test Failures**: Run `make test` to identify issues
2. **Type Errors**: Check imports and add missing type hints
3. **Database Issues**: Verify connection string and PostgreSQL status
4. **Redis Issues**: Check Redis service status and connection
5. **Port Conflicts**: Check if ports 8000, 3000, 5432, 6379 are available
6. **FotMob API Issues**: Test connection with provided scripts
7. **Memory Issues**: Monitor with `docker stats` and check resource consumption
8. **Queue Backlog**: Inspect Celery queues with provided commands
9. **Celery Worker Issues**: Check worker status with `docker-compose logs -f worker`
10. **Task Stuck in Queue**: Use `celery -A src.tasks.celery_app purge` to clear stuck tasks

### Environment Recovery
```bash
# Reset Docker environment
docker-compose down -v && docker-compose up -d

# Check service status
docker-compose ps
docker-compose logs -f app
```

### Debugging Commands
```bash
# Database debugging
make db-shell
\dt  # List tables
SELECT COUNT(*) FROM matches;

# Redis debugging
make redis-shell
KEYS *
INFO memory

# Celery task debugging
docker-compose exec app celery -A src.tasks.celery_app inspect active
docker-compose logs -f worker
```

## Commit Standards

### Format
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
chore(security): upgrade dependencies for security patches
```

### Development Workflow
1. Environment setup: `make dev`
2. Check service health: `make status`
3. Write code following DDD + CQRS patterns
4. Quality validation: `make lint && make test`
5. Security check: `make security-check`
6. Pre-commit: `make fix-code && make format`

### Complete Development Checklist
```bash
# 每日开发流程
make dev              # 启动开发环境
make status           # 确认所有服务健康
make test.unit        # 运行单元测试
make coverage         # 检查覆盖率
make lint && make fix-code  # 代码质量检查和修复

# 提交前验证
make ci               # 完整CI验证
make security-check   # 安全检查
make type-check       # 类型检查
```

### Project Quality Status
- **Build Status**: Stable (Green Baseline Established)
- **Test Coverage**: 29.0% baseline (actual measured data)
- **Tests**: 385 tests passing
- **Security**: Bandit validated, dependency vulnerabilities fixed
- **Code Quality**: A+ grade through ruff, mypy quality checks

### Monitoring & Observability Stack
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization dashboards and alerts
- **InfluxDB**: Time-series database for production metrics
- **Loki**: Log aggregation and analysis
- **Alert Manager**: Intelligent alerting with multi-channel notifications

### CI/CD Pipeline & Deployment Workflows

#### GitHub Actions Configuration
```yaml
# .github/workflows/production-deploy.yml
name: Production Deployment

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}

    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Run comprehensive tests
      run: |
        make lint
        make test
        make security-check
        make coverage

    - name: Build Docker images
      if: matrix.python-version == '3.11'
      run: |
        docker build -t football-prediction:latest .
        docker build -f frontend/Dockerfile -t football-frontend:latest ./frontend/
```

#### Smart CI Auto-Fixer
```yaml
# .github/workflows/smart-fixer-ci.yml
name: Smart CI Auto-Fixer

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  smart-fix:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
    - uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install --upgrade pip
        pip install -r requirements.txt

    - name: Auto-fix code issues
      run: |
        make fix-code
        make fix-imports
        make fix-formatting

    - name: Commit auto-fixes
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add .
        git diff --staged --quiet || git commit -m "🤖 Auto-fix code quality issues"
        git push
```

#### Branch Protection Rules
```yaml
# Branch protection configuration via GitHub API
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": [
        "CI Test (3.10)",
        "CI Test (3.11)",
        "CI Test (3.12)",
        "Code Quality Check",
        "Security Scan"
      ]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "required_approving_review_count": 2,
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": true
    },
    "restrictions": {
      "users": [],
      "teams": ["core-developers"]
    }
  }'
```

#### Environment-Specific Deployment
```bash
# Production deployment workflow
deploy_production() {
    echo "🚀 Starting production deployment..."

    # Pre-deployment checks
    make pre-deploy-check
    make health-check

    # Blue-green deployment
    docker-compose -f docker-compose.prod.yml --project-name football-prod-blue up -d
    sleep 30  # Health check period

    if docker-compose -f docker-compose.prod.yml --project-name football-prod-blue ps | grep -q "Up (healthy)"; then
        echo "✅ Blue deployment healthy, switching traffic..."
        # Switch load balancer to blue
        docker-compose -f docker-compose.prod.yml --project-name football-prod exec nginx nginx -s reload

        # Scale down green environment
        docker-compose -f docker-compose.prod.yml --project-name football-prod-green down
    else
        echo "❌ Blue deployment failed, rolling back..."
        docker-compose -f docker-compose.prod.yml --project-name football-prod-blue down
        exit 1
    fi
}

# Staging deployment
deploy_staging() {
    echo "🧪 Deploying to staging environment..."
    docker-compose -f docker-compose.staging.yml up -d --build
    make test.integration.staging
}
```

#### Issues and Cleanup Automation
```yaml
# .github/workflows/issues-cleanup.yml
name: Issues Cleanup

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  cleanup-stale-issues:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/stale@v8
      with:
        repo-token: ${{ secrets.GITHUB_TOKEN }}
        stale-issue-message: 'This issue has been inactive for 30 days. It will be closed in 7 days if there is no further activity.'
        stale-pr-message: 'This PR has been inactive for 14 days. It will be closed in 7 days if there is no further activity.'
        days-before-stale: 30
        days-before-close: 7
```

#### Quality Gates Automation
```bash
# Pre-push quality gates
make pre-push() {
    echo "🔍 Running pre-push quality gates..."

    # Code quality checks
    if ! make lint; then
        echo "❌ Code quality check failed"
        return 1
    fi

    # Security scan
    if ! make security-check; then
        echo "❌ Security scan failed"
        return 1
    fi

    # Test coverage threshold
    if ! pytest --cov=src --cov-fail-under=31 --cov-report=term-missing; then
        echo "❌ Test coverage below 31% threshold"
        return 1
    fi

    # Performance benchmarks
    if ! make benchmark-check; then
        echo "⚠️ Performance regression detected"
        return 1
    fi

    echo "✅ All quality gates passed"
    return 0
}

# Automated dependency updates
make deps-update() {
    echo "📦 Checking for dependency updates..."

    # Check for security vulnerabilities
    pip-audit --requirement requirements.txt --output-format=json

    # Update outdated packages
    pip-review --interactive

    # Update frontend dependencies
    cd frontend && npm audit fix && npm update

    echo "✅ Dependency update complete"
}
```

### Data Collection Architecture
- **Multi-Source Collectors**: `src/collectors/` - Specialized data采集器
- **Async HTTP Processing**: `curl_cffi` for high-performance async requests
- **Data Adapters**: `src/adapters/` - Unified data interface layer
- **Quality Assurance**: `src/data/quality/` - Advanced anomaly detection and data validation

### Comprehensive Monitoring & Observability Stack

#### Prometheus Metrics Configuration
```yaml
# prometheus.yml configuration example
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'football-prediction-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

#### Grafana Dashboard Configuration
```bash
# Grafana dashboard management
docker-compose exec grafana grafana-cli admin reset-admin-password admin  # 重置管理员密码
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @config/grafana/dashboards/football-prediction.json  # 导入仪表板

# Custom metrics dashboard
open http://localhost:3000/d/football-prediction-overview  # 系统概览仪表板
open http://localhost:3000/d/api-performance-metrics      # API性能仪表板
open http://localhost:3000/d/ml-model-accuracy            # ML模型准确率仪表板
```

#### Loki Log Aggregation Setup
```yaml
# loki-config.yml
server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 1h
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /tmp/loki/boltdb-shipper-active
    cache_location: /tmp/loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /tmp/loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

#### AlertManager Configuration
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@football-prediction.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://127.0.0.1:5001/'
    email_configs:
      - to: 'admin@football-prediction.com'
        subject: '[Football Prediction] Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

#### Custom Prometheus Metrics
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Custom metrics
REQUEST_COUNT = Counter(
    'football_prediction_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'football_prediction_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_PREDICTIONS = Gauge(
    'football_prediction_active_predictions',
    'Number of active predictions'
)

ML_MODEL_ACCURACY = Gauge(
    'football_prediction_ml_model_accuracy',
    'ML model accuracy percentage',
    ['model_name', 'league']
)

# Database connection pool metrics
DB_POOL_SIZE = Gauge(
    'football_prediction_db_pool_size',
    'Database connection pool size'
)

DB_POOL_AVAILABLE = Gauge(
    'football_prediction_db_pool_available',
    'Available database connections'
)
```

#### Advanced Monitoring Commands
```bash
# System health monitoring
make monitoring.status                        # 显示所有监控服务状态
make metrics.export                          # 导出Prometheus指标
make logs.aggregated                         # 聚合日志查看

# Performance monitoring
docker-compose exec prometheus promtool query instant 'rate(football_prediction_requests_total[5m])'
docker-compose exec prometheus promtool query instant 'histogram_quantile(0.95, rate(football_prediction_request_duration_seconds_bucket[5m]))'

# Log analysis with Loki
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode "query={app=\"football-prediction\"} |= \"ERROR\"" \
  --data-urlencode "start=$(date -d '-1 hour' --iso-8601)" \
  --data-urlencode "end=$(date --iso-8601)" | jq

# Alert testing
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"TestAlert","severity":"warning"}}]'
```

#### Monitoring Dashboard URLs
- **Grafana Dashboards**: http://localhost:3000
  - System Overview: http://localhost:3000/d/system-overview
  - API Performance: http://localhost:3000/d/api-performance
  - ML Metrics: http://localhost:3000/d/ml-metrics
  - Database Health: http://localhost:3000/d/database-health

- **Prometheus**: http://localhost:9090
  - Targets: http://localhost:9090/targets
  - Alerts: http://localhost:9090/alerts
  - Graph: http://localhost:9090/graph

- **Loki**: http://localhost:3100
  - Explore: http://localhost:3100/explore
  - Rules: http://localhost:3100/rules

- **AlertManager**: http://localhost:9093
  - Alerts: http://localhost:9093/#/alerts
  - Status: http://localhost:9093/#/status

### Security & Compliance Framework

#### Bandit Security Scanning Configuration
```ini
# .bandit configuration
[bandit]
exclude_dirs = tests,docs,build,dist
skips = B101,B601
tests = B201,B202

[bandit.assert_used]
skips = ['*_test.py', '*/test_*.py']

[bandit.imported_blacklist_list]
blacklist_imports = ['cPickle', 'dill', 'marshal', 'pickle']

[bandit.hardcoded_tmp_directory]
tmp_dirs = ['/tmp', '/var/tmp', '/usr/tmp']
```

#### Security Scanning Commands
```bash
# Comprehensive security audit
make security-check                           # Run complete security suite
make bandit-scan                             # Bandit security scanning
make dependency-audit                       # Dependency vulnerability check
make container-security                     # Container security analysis

# Advanced security tools
bandit -r src/ -f json -o security-report.json    # JSON security report
bandit -r src/ -f html -o security-report.html    # HTML security report
safety check --json --output safety-report.json   # Safety vulnerability report
pip-audit --requirement requirements.txt --format=json  # Full dependency audit

# Container security scanning
docker run --rm -v $(pwd):/app clair-scanner:latest Football-Prediction  # Clair container scan
trivy image football-prediction:latest                 # Trivy image vulnerability scan
```

#### API Security Best Practices
```python
# src/security/api_security.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Optional
import secrets
import hashlib
from datetime import datetime, timedelta

security = HTTPBearer()

class APIKeyManager:
    """API密钥管理和验证"""

    def __init__(self):
        self.api_keys = {
            "production": self._generate_secure_key(),
            "staging": self._generate_secure_key(),
            "development": self._generate_secure_key()
        }

    def _generate_secure_key(self) -> str:
        """生成安全的API密钥"""
        return secrets.token_urlsafe(32)

    def validate_key(self, api_key: str) -> bool:
        """验证API密钥"""
        return api_key in self.api_keys.values()

class RateLimiter:
    """API速率限制"""

    def __init__(self):
        self.requests = {}

    def check_rate_limit(self, client_id: str, limit: int = 100, window: int = 3600) -> bool:
        """检查速率限制"""
        now = datetime.now().timestamp()
        if client_id not in self.requests:
            self.requests[client_id] = []

        # 清理过期请求
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < window
        ]

        if len(self.requests[client_id]) >= limit:
            return False

        self.requests[client_id].append(now)
        return True

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT令牌验证"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

#### Container Security Configuration
```dockerfile
# Multi-stage secure Dockerfile
FROM python:3.11-slim as builder

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置安全的工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖并清理缓存
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# 生产阶段
FROM python:3.11-slim as production

# 复制已安装的包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY src/ ./src/
COPY pyproject.toml ./

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 设置安全的环境变量
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["python", "-m", "src.main"]
```

#### Compliance and Auditing
```bash
# Data privacy and GDPR compliance
make gdpr-compliance-check                   # GDPR合规性检查
make data-privacy-audit                      # 数据隐私审计

# Security compliance frameworks
make iso27001-compliance                     # ISO 27001合规性检查
make soc2-compliance                         # SOC 2合规性验证
make pci-dss-compliance                      # PCI DSS安全标准检查

# Logging and audit trails
make audit-log-setup                         # 审计日志设置
make security-monitoring                     # 安全监控配置

# Compliance reporting
python -c "
import json
from src.security.compliance import ComplianceChecker

checker = ComplianceChecker()
report = checker.generate_compliance_report()

with open('compliance_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f'合规性评分: {report[\"overall_score\"]}/100')
print(f'关键问题: {len(report[\"critical_issues\"])}')
"
```

#### Security Monitoring and Alerting
```yaml
# Security monitoring configuration
security_rules:
  - name: "Brute Force Detection"
    condition: "rate(http_requests_total{status='401'}[5m]) > 10"
    severity: "high"
    action: "block_ip"

  - name: "SQL Injection Attempts"
    condition: 'http_requests_total{path=~".*sql.*"} > 0'
    severity: "critical"
    action: "alert_security_team"

  - name: "Unusual Data Access"
    condition: "rate(data_access_total[10m]) > 1000"
    severity: "medium"
    action: "log_anomaly"

security_alerts:
  webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  email_recipients: ["security@football-prediction.com"]
  slack_channel: "#security-alerts"
```

#### Security Testing Integration
```python
# tests/security/test_api_security.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.mark.security
def test_sql_injection_protection():
    """测试SQL注入防护"""
    malicious_payloads = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "1' UNION SELECT * FROM sensitive_data --"
    ]

    for payload in malicious_payloads:
        response = client.get(f"/api/v1/matches?search={payload}")
        assert response.status_code != 500
        assert "error" not in response.text.lower()

@pytest.mark.security
def test_rate_limiting():
    """测试API速率限制"""
    for i in range(150):  # 超过100次限制
        response = client.get("/api/v1/predictions/")
        if i > 100:
            assert response.status_code == 429

@pytest.mark.security
def test_authentication_required():
    """测试需要认证的端点"""
    response = client.post("/api/v1/admin/users/")
    assert response.status_code == 401
```

#### Security Configuration Management
```bash
# Secure secrets management
make secrets-setup                            # 设置安全密钥管理
make env-var-scan                            # 环境变量安全扫描
make ssl-certificate-setup                   # SSL证书配置

# Infrastructure security
make firewall-configuration                  # 防火墙配置
make intrusion-detection-setup              # 入侵检测设置
make security-hardening                      # 系统安全加固

# Backup and recovery security
make secure-backup-setup                     # 安全备份配置
make disaster-recovery-plan                 # 灾难恢复计划
make data-encryption-setup                   # 数据加密设置
```

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. All I/O operations must be async, maintain DDD layer separation, and follow established patterns.