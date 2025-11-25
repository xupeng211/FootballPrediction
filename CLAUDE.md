# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**请使用简体中文回复用户** - Please respond in Simplified Chinese when interacting with the user. The project team primarily communicates in Chinese, so all responses should be in Simplified Chinese unless specifically requested otherwise.

## Project Overview

This is an enterprise-level football prediction system built with Python FastAPI, following Domain-Driven Design (DDD), CQRS, and Event-Driven architecture patterns. The system uses modern async/await patterns throughout and includes machine learning capabilities for match predictions.

**Current Status**: Production-ready with CI/CD pipeline established, 29.0% test coverage, and comprehensive quality assurance measures.

**Project Scale**:
- **385 test cases** covering unit, integration, and end-to-end scenarios
- **613-line Makefile** with comprehensive development workflow automation
- **40+ API endpoints** across multiple domains (predictions, data management, system monitoring)
- **Multiple task queues** for data collection, ETL processing, and system maintenance

## Key Development Commands

### Environment Management
```bash
# Start development environment (Docker-based)
make dev

# Start production environment
make prod

# Stop services
make down

# Clean resources
make clean
make clean-all

# Check service status
make status

# Build and deployment
make build              # Build application image
make build-no-cache     # Build without cache
make dev-rebuild        # Rebuild and start development
make prod-rebuild       # Rebuild and start production
```

### Code Quality & Testing
```bash
# Run tests
make test
make test.unit          # Unit tests only
make test.integration   # Integration tests only
make test.phase1        # Phase 1 core functionality tests
make test.all           # All tests

# Test execution in isolation
./scripts/run_tests_in_docker.sh  # Run tests in Docker container

# Code quality checks
make lint               # Ruff + MyPy checks
make format             # Code formatting
make fix-code           # Auto-fix issues
make type-check         # Type checking
make security-check     # Security scanning

# Coverage analysis
make coverage           # Generate coverage report
open htmlcov/index.html # View coverage report (macOS)
xdg-open htmlcov/index.html # View coverage report (Linux)

# CI validation
./ci-verify.sh          # Local CI verification
make ci                 # Complete quality check pipeline
```

### Celery 任务管理与开发工具
```bash
# Celery 服务管理
celery -A src.tasks.celery_app worker --loglevel=info       # 启动 worker 进程
celery -A src.tasks.celery_app beat --loglevel=info         # 启动定时任务调度器
celery -A src.tasks.celery_app flower                       # 启动 Flower 监控界面

# 任务执行与监控
celery -A src.tasks.celery_app call tasks.data_collection_tasks.collect_fotmob_data  # 手动触发数据采集
docker-compose exec app celery -A src.tasks.celery_app inspect active    # 检查活跃任务
docker-compose exec app celery -A src.tasks.celery_app inspect stats     # 查看任务统计
docker-compose exec app celery -A src.tasks.celery_app inspect scheduled  # 查看定时任务
docker-compose exec app celery -A src.tasks.celery_app purge             # 清空任务队列

# 任务调试
docker-compose exec app celery -A src.tasks.celery_app report           # 查看工作节点信息
docker-compose exec app celery -A src.tasks.celery_app events           # 实时任务事件监控

# FotMob 数据采集专项
docker-compose exec app python scripts/fotmob_authenticated_client.py   # FotMob 认证客户端测试
docker-compose exec app python scripts/probe_fotmob_advanced.py         # 高级 FotMob API 探测
docker-compose exec app python scripts/probe_fotmob_advanced_v2.py     # FotMob API 探测 v2
```

### ETL 数据处理工具
```bash
# ETL 数据处理管道
docker-compose exec app python scripts/run_etl_silver.py                # 运行 Silver 层 ETL 处理
docker-compose exec app python scripts/daily_pipeline.py               # 运行日常数据管道
docker-compose exec app python scripts/collect_and_save_data.py        # 采集并保存数据到数据库

# 数据质量审计
docker-compose exec app python scripts/audit_data_quality.py           # 数据质量审计脚本
```

### Container Management
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

# Container status and monitoring
make status             # View all service status
make monitor            # Monitor app container resources
make monitor-all        # Monitor all container resources

# Database management
make db-reset           # Reset database (WARNING: destroys data)
make db-migrate         # Run database migrations
```

## Architecture

### Core Structure
- **FastAPI Application**: `src/main.py` - Main application with 40+ API endpoints
- **Domain Layer**: `src/domain/` - Business logic and entities (pure Python)
- **API Layer**: `src/api/` - HTTP routers and API concerns
- **Services**: `src/services/` - Application services and orchestration
- **Database**: `src/database/` - SQLAlchemy models and repositories
- **ML Engine**: `src/ml/` - Machine learning models and pipelines
- **Cache Layer**: `src/cache/` - Redis-based caching
- **Adapters**: `src/adapters/` - External API integrations
- **Data Collectors**: `src/data/collectors/` - Data collection components (FotMob, Fixtures, Scores, Odds)
- **Tasks Layer**: `src/tasks/` - Celery async tasks for data collection and processing
  - `data_collection_tasks.py` - Main data collection tasks
  - `pipeline_tasks.py` - ETL and feature calculation tasks
  - `maintenance_tasks.py` - System maintenance and cleanup tasks
  - `backup_tasks.py` - Database backup and archival tasks
  - `streaming_tasks.py` - Real-time data streaming tasks
- **CQRS Layer**: `src/cqrs/` - Command Query Responsibility Segregation implementation
- **Config Layer**: `src/config/` - Configuration management and OpenAPI setup
- **Core Infrastructure**: `src/core/` - Event system and shared utilities

### Technology Stack
- **Backend**: FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic v2+, Redis 7.0+, PostgreSQL 15
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+, numpy 1.25+, MLflow 2.22.2+
- **Frontend**: React 19.2.0, TypeScript 4.9.5, Ant Design 5.27.6
- **Testing**: pytest 8.4+ with asyncio support, pytest-cov 7.0+, pytest-mock 3.14+
- **Code Quality**: Ruff 0.14+, MyPy 1.18+, Bandit 1.8.6+
- **Development Tools**: pre-commit 4.0.1, pip-audit 2.6.0, ipython 8.31+
- **Task Queue**: Celery with Redis broker for async data collection and processing

### Database & Caching
- **Primary Database**: PostgreSQL 15 with async SQLAlchemy 2.0
- **Cache**: Redis 7.0+ for performance optimization
- **Task Queue**: Celery with Redis broker for async data collection
- **Migrations**: Alembic for database schema management
- **Connection Pooling**: Async connection management

## Development Standards

### Code Requirements
- **Type Hints**: All functions must have complete type annotations
- **Async/Await**: All I/O operations must be async (database, external APIs)
- **Logging**: Use structured logging with `logger` (never use `print()`)
- **Error Handling**: Comprehensive exception handling with proper logging

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

## Testing

### Test Structure
- **Unit Tests**: 85% - Fast, isolated component testing
- **Integration Tests**: 12% - Real dependency testing
- **E2E Tests**: 2% - Complete user workflow testing
- **Performance Tests**: 1% - Load and stress testing

### Test Markers
```python
# Core test type markers
@pytest.mark.unit           # Unit tests - 85% of test suite
@pytest.mark.integration    # Integration tests - 12% of test suite
@pytest.mark.e2e           # End-to-end tests - 2% of test suite
@pytest.mark.performance   # Performance tests - 1% of test suite

# Functional domain markers
@pytest.mark.api           # HTTP endpoint testing
@pytest.mark.domain        # Domain layer business logic
@pytest.mark.business      # Business rules and validation
@pytest.mark.services      # Service layer testing
@pytest.mark.database      # Database connection tests
@pytest.mark.cache         # Redis and caching logic
@pytest.mark.auth          # Authentication and authorization
@pytest.mark.monitoring    # Metrics and health checks
@pytest.mark.ml            # Machine learning tests
@pytest.mark.utils         # Utility functions and helpers

# Data collection and processing markers
@pytest.mark.fotmob        # FotMob data collection tests
@pytest.mark.etl           # ETL pipeline processing tests
@pytest.mark.batch         # Batch processing tests
@pytest.mark.data_quality  # Data quality validation tests

# Execution characteristics
@pytest.mark.critical       # Must-pass core functionality
@pytest.mark.slow          # Long-running tests (>30s)
@pytest.mark.smoke         # Basic functionality verification
@pytest.mark.regression    # Verify fixes don't regress
@pytest.mark.external_api  # Tests requiring external API calls
@pytest.mark.docker        # Tests requiring Docker environment
@pytest.mark.network       # Tests requiring network connection
```

### Running Tests
```bash
# Run specific test file
pytest tests/unit/test_specific.py::test_function -v

# Run tests by keyword
pytest tests/unit/ -k "test_keyword" -v

# Run tests by marker
pytest tests/unit/ -m "unit and not slow" -v

# Fast failure for debugging
pytest tests/unit/ --maxfail=3 -x

# Run single test with detailed output
pytest tests/unit/test_specific.py::test_function -v -s --tb=short

# Coverage analysis
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run tests in Docker (isolated environment)
./scripts/run_tests_in_docker.sh

# CI-style test execution with reporting
pytest tests/ --cov=src --cov-report=xml --cov-report=term-missing --junit-xml=test-results.xml --maxfail=5 -x

# Run tests with specific Python version
docker-compose exec app python -m pytest tests/unit/ -v
```

### Test Configuration (pyproject.toml)
- **Async mode**: `asyncio_mode = "auto"` - Automatic async detection
- **Test paths**: `tests/` directory with recursive discovery
- **Coverage source**: `src/` directory
- **Log level**: INFO with structured logging format
- **Warning filters**: Comprehensive filtering for clean output
- **Timeout**: 10-second test duration reporting

## Docker Development

### Services
- **app**: FastAPI application (port: 8000)
- **frontend**: React application (ports: 3000, 3001)
- **db**: PostgreSQL 15 (port: 5432)
- **redis**: Redis 7.0 (port: 6379) - acts as both cache and Celery broker
- **nginx**: Reverse proxy (port: 80)
- **worker**: Celery worker (async task processing)
- **beat**: Celery beat (scheduled task scheduling)

### Container Features
- Hot reload with volume mounting
- Health checks for all services
- Environment-specific configurations
- Multi-stage builds for optimized images

## Machine Learning Pipeline

### ML Architecture
- **Prediction Engine**: XGBoost 2.0+ gradient boosting models
- **Feature Engineering**: Automated data preprocessing pipelines
- **Model Training**: scikit-learn 1.3+ with cross-validation
- **Model Management**: MLflow 2.22.2+ version control and experiment tracking

### ML Integration
```python
from src.services.inference_service import inference_service

prediction_result = await inference_service.predict_match(match_id)
batch_results = await inference_service.batch_predict_match(match_ids)
```

## API Usage

### Key Endpoints
- **Health Checks**: `/health`, `/health/system`, `/health/database`
- **Predictions**: `/api/v1/predictions/`, `/api/v2/predictions/`
- **Data Management**: `/api/v1/data_management/`
- **System**: `/api/v1/system/`
- **Adapters**: `/api/v1/adapters/`
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

# Initial development setup (5-minute quick start)
make install            # Install dependencies
make context            # Load project context ⭐ Most important
make env-check          # Verify environment configuration

# Additional useful shortcuts
make quick-start        # Alias for make dev
make quick-stop         # Alias for make dev-stop
make quick-clean        # Alias for make clean

# Verify test environment
make test-phase1        # Phase 1 core functionality tests
make coverage           # View coverage report

# Edit with actual values
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
FOTMOB_CLIENT_VERSION=production:208a8f87c2cc13343f1dd8671471cf5a039dced3
FOTMOB_KNOWN_SIGNATURE=eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0

# Local CI validation before commits
./ci-verify.sh          # Complete local CI verification
```

### Development Workflow
```bash
# Standard development cycle
1. make dev             # Start development environment
2. make context         # Load project context
3. Write code           # Follow DDD + CQRS patterns
4. make test            # Run tests (385 test cases)
5. make lint && make fix-code  # Code quality checks
6. ./ci-verify.sh       # Pre-commit validation
7. make ci              # Full quality pipeline

# 数据采集与处理开发流程
1. docker-compose exec app python scripts/fotmob_authenticated_client.py  # 测试 API 连接
2. celery -A src.tasks.celery_app call tasks.data_collection_tasks.collect_fotmob_data  # 手动采集数据
3. docker-compose exec app python scripts/run_etl_silver.py                # 处理采集的数据
4. docker-compose exec app python scripts/audit_data_quality.py           # 验证数据质量

# Celery 调试流程
1. docker-compose exec app celery -A src.tasks.celery_app inspect active   # 检查活跃任务
2. docker-compose logs -f worker                                         # 查看 worker 日志
3. docker-compose exec app celery -A src.tasks.celery_app purge           # 清空卡住的任务队列

# FotMob 高级 API 探测工具
docker-compose exec app python scripts/probe_fotmob_advanced.py           # 高级 API 探测
docker-compose exec app python scripts/probe_fotmob_advanced_v2.py         # API 探测 v2
docker-compose exec app python scripts/trigger_historical_backfill.py      # 历史数据回填

# Quick test validation
make test-phase1        # Core functionality tests
./scripts/run_tests_in_docker.sh  # Isolated test execution
```

## Important Reminders for Developers

### Critical Development Notes
- **⚠️ Test Running**: Always use Makefile commands for testing, never run pytest directly on individual files. See [TEST_RUN_GUIDE.md](TEST_RUN_GUIDE.md) for proper testing methodology.
- **📋 Context Loading**: Always run `make context` before starting development work to load project context.
- **🐳 Docker Environment**: Use Docker Compose for local development to ensure consistency with CI environment.
- **🔄 CI Validation**: Run `./ci-verify.sh` before commits to simulate the complete CI pipeline locally.

### Project Documentation Structure
- **[TEST_IMPROVEMENT_GUIDE.md](docs/TEST_IMPROVEMENT_GUIDE.md)** - Kanban, CI Hook, and weekly reporting mechanisms for test optimization
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Comprehensive testing methodology and best practices from SWAT operations
- **[TOOLS.md](./TOOLS.md)** - Complete tool usage guide including GitHub Issues sync and development workflows
- **[AGENTS.md](AGENTS.md)** - Repository guidelines for contributors covering structure, processes, and security baselines

## Quality Assurance

### Code Quality Tools
- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Bandit**: Security scanning
- **pytest**: Testing framework with asyncio support
- **pip-audit**: Dependency vulnerability scanning

### Pre-commit Checklist
- [ ] Tests pass: `make test`
- [ ] Code quality: `make fix-code`
- [ ] Type checking: `make type-check`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Full validation: `make lint && make test`

### Code Quality Standards
- **Type Coverage**: All functions must have complete type annotations
- **Async Pattern**: All I/O operations must use async/await
- **Error Handling**: Comprehensive exception handling with structured logging
- **Documentation**: Public APIs must have docstrings with examples

## Troubleshooting

### Common Issues
1. **Test Failures**: Run `make test` to identify issues
2. **Type Errors**: Check imports and add missing type hints
3. **Database Issues**: Verify connection string and PostgreSQL status
4. **Redis Issues**: Check Redis service status and connection
5. **Port Conflicts**: Check if ports 8000, 3000, 5432, 6379 are available
6. **FotMob API Issues**: Test connection with `docker-compose exec app python scripts/fotmob_authenticated_client.py`
7. **Data Collection Failures**: Check Celery worker status and logs with `docker-compose logs -f app | grep -i fotmob`

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
SELECT COUNT(*) FROM raw_match_data WHERE source='fotmob';

# Redis debugging
make redis-shell
KEYS *
INFO memory

# Celery 任务调试
docker-compose exec app celery -A src.tasks.celery_app inspect active    # 检查活跃任务
docker-compose exec app celery -A src.tasks.celery_app inspect stats     # 查看任务统计
docker-compose logs -f worker | grep -E "(ERROR|WARNING|task)"           # 查看任务相关日志
docker-compose exec app python scripts/verify_api_connection.py         # 验证 API 连接

# FotMob 专项调试
docker-compose logs -f app | grep -i fotmob                               # 查看 FotMob 相关日志
docker-compose exec app celery -A src.tasks.celery_app inspect scheduled  # 查看定时任务状态

# ETL pipeline debugging
docker-compose exec app python scripts/run_etl_silver.py                          # 手动运行 ETL
docker-compose exec app python scripts/audit_data_quality.py                     # 数据质量审计

# Performance monitoring
docker-compose exec app python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%'); print(f'Memory: {psutil.virtual_memory().percent}%%')"  # 系统资源监控
docker-compose stats                                                              # 容器资源使用情况
docker-compose exec app python scripts/monitor_system_health.py                  # 系统健康检查（如果存在）

# Application debugging
docker-compose exec app python -c "from src.core.cache import cache_manager; print('Cache connection:', cache_manager.redis.ping())"  # 测试缓存连接
docker-compose exec app python -c "from src.database.session import get_async_session; print('Database connection test')"  # 测试数据库连接
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
chore(security): upgrade MLflow to 2.22.2 for security patches
```

### Development Workflow
1. Environment setup: `make dev`
2. Write code following DDD + CQRS patterns
3. Quality validation: `make lint && make test`
4. Security check: `make security-check`
5. Pre-commit: `make fix-code && make format`

## Special Features

### Intelligent Cold Start
The system automatically detects database state and data freshness, triggering intelligent data collection:
- Empty database: Triggers complete data collection
- Stale data: Triggers incremental data updates
- Fresh data: Skips collection to optimize performance

### Real-time Monitoring
- System health: CPU, memory, disk usage monitoring
- Performance metrics: API response times, database connection pool status
- Business metrics: Prediction accuracy, data update frequency

### Smart Development Workflow
- AI-first maintained project with comprehensive tooling
- Automated test recovery and flaky test isolation
- Green CI baseline with quality gates
- Complete documentation and development guides

### Celery 任务调度系统
- **多队列支持**: fixtures、odds、scores、maintenance、backup、streaming 等专用队列
- **定时任务调度**: 通过 Celery Beat 管理定期数据采集和处理任务
- **任务重试机制**: 可配置的重试策略，支持退避和抖动
- **监控集成**: 任务状态监控、性能指标收集和错误追踪
- **任务路由**: 智能任务分发到不同工作节点

### FotMob 数据采集系统
- **智能降级机制**: API 失败时自动降级到 Mock 模式
- **数据持久化**: 自动保存采集数据到 `raw_match_data` 表
- **批量处理**: 支持分块处理，优化 ETL 性能
- **定时任务**: 通过 Celery Beat 自动执行数据采集（凌晨 2:00）
- **开发工具**: 专门的 API 探测和调试工具集

### ETL 数据处理管道
- **分块处理**: 大数据集分批处理，避免内存溢出
- **Silver 层处理**: 从原始数据到清洗数据的转换管道
- **数据质量审计**: 自动化数据质量检查和报告
- **批量插入**: 优化的数据库批量插入操作
- **特征计算**: 自动化为新比赛数据计算 ML 特征

### 任务调度与监控
- **多任务队列**: 支持数据采集、ETL处理、备份维护等专用队列
- **定时调度**: 基于 Celery Beat 的灵活定时任务配置
- **任务重试**: 智能重试机制，支持退避策略和错误阈值
- **实时监控**: 任务执行状态、性能指标和错误追踪
- **资源管理**: 工作进程配置、超时限制和连接池优化

## 重要脚本和工具

### 开发辅助脚本
```bash
# 项目管理和设置
./verify-docker-setup.sh           # 验证 Docker 环境配置
./generate_secure_keys.sh          # 生成安全密钥
./quality_status.sh                # 项目质量状态检查

# 测试相关脚本
./scripts/run_tests_with_report.py # 运行测试并生成报告
./scripts/harvest_passing_tests.py # 收集通过的测试用例

# 数据处理脚本
./scripts/daily_pipeline.py        # 日常数据处理管道
./scripts/collect_and_save_data.py # 数据采集和存储
./scripts/seed_data.py            # 数据库种子数据

# Celery 任务相关脚本
src/tasks/celery_app.py           # Celery 应用配置和任务调度
src/tasks/data_collection_tasks.py # 数据采集任务实现
src/tasks/pipeline_tasks.py       # ETL 和特征计算任务
src/tasks/maintenance_tasks.py    # 系统维护任务
src/tasks/backup_tasks.py         # 数据库备份任务
src/tasks/streaming_tasks.py      # 实时流处理任务
```

### CI/CD 和质量保证
- **CI 配置**: GitHub Actions 自动化流水线
- **本地验证**: `./ci-verify.sh` 脚本模拟 CI 环境
- **代码质量**: Ruff + MyPy + Bandit 全套检查工具
- **测试隔离**: Docker 容器化测试环境确保一致性

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. All I/O operations must be async, maintain DDD layer separation, and follow established patterns.