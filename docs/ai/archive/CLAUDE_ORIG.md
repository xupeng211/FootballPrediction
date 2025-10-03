# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌏 语言设置 (Language Settings)

**请始终使用中文回复！** (Always reply in Chinese!)

- 语言偏好: 中文 (简体)
- 回复语言: 中文
- 注释语言: 中文
- 文档语言: 中文

当与用户交流时，请：
1. 始终使用中文回复
2. 用中文编写代码注释
3. 用中文编写文档
4. 保持对话的一致性，不要切换到英文

## 🚀 Quick Start

**Essential first steps when starting work:**
```bash
make install      # Install dependencies and create virtual environment
make context      # Load project context (most important)
make env-check    # Verify environment health
make help         # Show all available commands
```

### AI Development Guidelines
The project includes comprehensive AI development guidelines in `.cursor/rules/` directory:
- **Tool Priority**: Use Makefile commands for consistency
- **Quality Standards**: 80%+ test coverage (CI), 20-60% (local)
- **Code Style**: Black formatting, mypy type checking, flake8 linting
- **Modify Over Create**: Prioritize modifying existing files over creating new ones
- **Context Loading**: Always run `make context` first to understand project state
- **Docker CI**: Validate with `./ci-verify.sh` before pushing
- **Documentation First**: 创建/修改功能前必须更新相关文档（见 docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md）

### 🤖 AI Documentation Automation Rules
根据 `docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md`，AI开发工具必须遵守：

#### 文档维护强制规则
- **新功能开发**：先检查并更新文档，再编写代码
- **文档同步**：代码变更时同步更新所有相关文档
- **报告管理**：临时报告自动按月归档到 `docs/_reports/archive/YYYY-MM/`
- **命名规范**：文档使用英文文件名，内容可用中文

#### 自动触发条件
- 创建 API 端点 → 更新 `docs/reference/API_REFERENCE.md`
- 修改数据库 → 更新 `docs/reference/DATABASE_SCHEMA.md`
- 完成阶段任务 → 生成完成报告
- 修复重大 bug → 创建 bugfix 报告

#### 文档目录维护
```
docs/
├── _reports/archive/  # 按月归档的历史报告
├── architecture/     # 架构设计文档
├── how-to/          # 操作指南
├── reference/       # API、数据库等参考资料
├── testing/         # 测试策略
├── ops/            # 运维手册
├── ml/             # 机器学习文档
├── release/        # 发布管理
└── legacy/         # 废弃文档（保留3个月）
```

## 📋 Common Commands

### Environment Setup
- `make help` - Show all available commands with categorized help
- `make install` - Install dependencies from requirements.txt and requirements-dev.txt
- `make venv` - Create virtual environment (.venv)
- `make env-check` - Check development environment health
- `make clean` - Remove cache and virtual environment

### Code Quality
- `make lint` - Run flake8 and mypy checks
- `make fmt` - Format code with black and isort
- `make type-check` - Run mypy type checking
- `make quality` - Complete quality check (lint + format + test)

### Testing
- `make test` - Run pytest unit tests
- `make coverage` - Run tests with coverage report (80% threshold enforced in CI, 20-60% for local development)
- `make coverage-fast` - Run fast coverage (unit tests only, 20% threshold for development)
- `make coverage-ci` - CI coverage validation with 80% threshold
- `make coverage-local` - Local development coverage with 60% threshold
- `make coverage-critical` - Critical path coverage with 100% threshold requirement
- `make test-quick` - Quick test run (unit tests with timeout)
- `make coverage-unit` - Unit test coverage with HTML report
- `./ci-verify.sh` - Complete CI verification with Docker environment (⭐ Critical before pushing)

**Note**: Many integration tests were deleted during cleanup and need to be recreated. Focus on unit tests for reliable development.

### CI/CD Simulation
- `make ci` - Simulate GitHub Actions CI pipeline
- `make prepush` - Complete pre-push validation (format + lint + type-check + test)
- `./ci-verify.sh` - Full CI verification with Docker environment (⭐ Required before pushing)

### Container Management
- `make up` - Start docker-compose services
- `make down` - Stop docker-compose services
- `make logs` - Show docker-compose logs
- `make deploy` - Build & start containers with git-sha tag
- `make rollback` - Rollback to previous image (TAG=<sha>)

### MLOps Pipeline
- `make feedback-update` - Update prediction results with actual outcomes
- `make performance-report` - Generate model performance reports
- `make retrain-check` - Check models and trigger retraining if needed
- `make model-monitor` - Run enhanced model monitoring cycle
- `make mlops-pipeline` - Run complete MLOps feedback pipeline
- `make mlops-status` - Show MLOps pipeline status and generated reports
- `make feedback-test` - Run feedback loop unit tests

### Performance & Quality Testing
- `make benchmark` - Run performance benchmarks using pytest-benchmark
- `make profile-app` - Profile application performance
- `make profile-tests` - Profile test execution performance
- `make profile-memory` - Analyze memory usage patterns
- `make flamegraph` - Generate performance visualization flame graphs
- `make mutation-test` - Run mutation testing with mutmut
- `make performance-regression-check` - Check for performance regressions

### Project Context
- `make context` - Load project context for AI development (⭐ Most important)
- `make sync-issues` - Sync GitHub issues between local and GitHub (bidirectional sync with kanban workflow)

### Single Test Execution
- `pytest tests/unit/test_specific_module.py` - Run specific test file
- `pytest tests/unit/test_module.py::TestClass::test_method` - Run specific test method
- `pytest -x` - Stop on first failure
- `pytest -m "not slow"` - Exclude slow tests
- `pytest tests/unit/` - Run only unit tests

## Architecture Overview

**Production-ready enterprise football prediction system** with async-first architecture and comprehensive MLOps pipeline:

### Core Technology Stack
- **FastAPI** - Modern async web framework with automatic API documentation
- **SQLAlchemy 2.0** - Modern ORM with async support (PostgreSQL + SQLite)
- **PostgreSQL** - Production database with multi-user role architecture
- **SQLite** - Testing database with seamless switching capability
- **Redis** - Caching, session storage, and Celery broker
- **Celery** - Distributed task queue with Beat scheduler
- **MLflow** - Model lifecycle management with PostgreSQL backend
- **Feast** - Feature store for ML features
- **Kafka** - Streaming data processing with Confluent Platform
- **Great Expectations** - Data quality validation
- **Prometheus/Grafana** - Metrics collection and visualization
- **MinIO** - Object storage for data lake and ML artifacts

### Key Architecture Patterns

#### Async-First Design
- **129+ Python source files** with comprehensive async/await patterns
- **Dual database support**: PostgreSQL (production) + SQLite (testing)
- **Background processing**: Celery with Redis for async task queue
- **Connection pooling**: Advanced database connection management

#### Data-Centric ML Pipeline
```
Data Collection → Processing → Feature Store → ML Models → Predictions
     ↓                    ↓            ↓           ↓           ↓
  Live APIs        Data Quality    Feast      MLflow     Real-time API
                   Great Expect             Monitoring
                   Prometheus
```

#### Multi-Layer Caching
- **Redis**: Application-level caching with TTL
- **Feature Store**: Feast-based feature caching
- **Model Cache**: MLflow model versioning with local caching
- **Database**: Connection pooling and query caching

## 🔄 Development Workflow

### Essential Start Sequence
1. **Environment Setup**: `make install` to set up development environment
2. **Context Loading**: `make context` to understand current project state (⭐ Critical)
3. **Environment Check**: `make env-check` to verify environment health

### AI Development Principles
- **Tool Priority**: Use Makefile commands for consistency
- **Modify Over Create**: Prioritize modifying existing files over creating new ones
- **Quality First**: All changes must pass `make ci` checks
- **Docker CI**: Validate with `./ci-verify.sh` before pushing

### Quality Requirements
- **Test Coverage**: CI enforces 80%+ minimum coverage; local development uses 20-60% for faster iteration
- **Type Safety**: Full mypy type checking required for all code
- **Code Formatting**: Black and isort automatically applied with flake8 linting
- **Database**: Dual support for SQLite (testing) and PostgreSQL (production)
- **Async Architecture**: All database operations and external API calls use async/await
- **Performance Testing**: pytest-benchmark integration with regression detection

**Note**: Many integration tests were deleted during cleanup and need to be recreated. Focus on unit tests for reliable development.

### Key Configuration Files
- `requirements.txt` - Production dependencies (FastAPI, SQLAlchemy, MLflow, Feast, Great Expectations)
- `requirements-dev.txt` - Development tools with conflict resolution (pytest, black, mypy, bandit)
- `docker-compose.yml` - Complete development environment (15+ services)
- `docker-compose.test.yml` - CI testing environment
- `pytest.ini` - pytest configuration with 80% coverage threshold and comprehensive test markers
- `.coveragerc` - Coverage configuration with exclusions for fast development
- `coverage_ci.ini` - CI environment coverage configuration (80% threshold)
- `coverage_local.ini` - Local development coverage configuration (60% threshold)
- `mutmut.ini` - Mutation testing configuration for code quality validation
- `ci-verify.sh` - Complete CI verification script with Docker environment
- `Makefile` - Comprehensive build automation with 50+ commands
- `.cursor/rules/` - AI development guidelines and project standards

### pytest Configuration
- **Coverage threshold**: 80% minimum (CI), 20-60% for local development
- **Test markers**: unit, integration, slow, asyncio, e2e, docker, performance, timeout, edge_case, failure_scenario, mlflow, db, kafka, celery, ml, factory, mock, pipeline, api, model, data, cache, feature, validation, monitoring
- **Async mode**: auto with function fixture loop scope
- **Test discovery**: test_*.py files, Test* classes, test_* functions
- **Current status**: Many unit tests available; integration tests largely deleted and need recreation

### Coverage Configuration
- **Source paths**: src/ directory
- **Exclusions**: Tests, migrations, scripts, main.py, and heavy integration layers
- **Fast coverage**: Excludes API, data, services, utils, cache, monitoring layers for speed
- **Report settings**: Shows missing lines, generates HTML reports in htmlcov/
- **Branch coverage**: Enabled for comprehensive test coverage analysis

### Testing Tips & Troubleshooting

#### Test Organization
- **Unit Tests**: `tests/unit/` - Fast, isolated tests - **Use these for reliable development**
- **Integration Tests**: `tests/integration/` - Component interaction tests - **Note: Largely deleted, need recreation**
- **E2E Tests**: `tests/e2e/` - End-to-end testing scenarios
- **Feature Tests**: `tests/test_features/` - Feature-specific testing

**Note**: Many integration tests were deleted during cleanup and need to be recreated. Focus on unit tests for reliable development.

#### Common Testing Commands
- **Single test file**: `pytest tests/unit/test_specific_module.py -v`
- **Stop on first failure**: `pytest -x` or `pytest --maxfail=3`
- **Verbose output**: `pytest -v --tb=long`
- **Run specific test**: `pytest tests/unit/test_module.py::TestClass::test_method`
- **Run with markers**: `pytest -m "not slow"` to exclude slow tests
- **Run unit tests only**: `pytest tests/unit/`

#### Performance Testing
- **Benchmarks**: `make benchmark` - Run performance benchmarks with pytest-benchmark
- **Profiling**: `make profile-app` - Profile application performance
- **Regression Detection**: `make performance-regression-check` - Check for performance regressions
- **Mutation Testing**: `make mutation-test` - Run mutation testing with mutmut

#### Performance Tips
- Use `make coverage-fast` for quick feedback during development
- Use `make test-quick` for rapid iteration with timeout protection
- Integration tests may require external services - ensure Docker containers are running
- CI uses 80% coverage threshold, local development uses 20-60% for faster iteration

#### Common Issues
- **Database connection errors**: Ensure Docker services are running with `docker-compose up -d`
- **Import errors**: Run with proper PYTHONPATH: `export PYTHONPATH="$(pwd):${PYTHONPATH}"`
- **Test timeouts**: Use `make test-quick` for timeout protection
- **Coverage reporting slow**: Use `make coverage-fast` for unit tests only

## 🔧 Development Environment Setup

### Technology Stack
- **Language**: Python 3.11+ with async/await throughout
- **Web Framework**: FastAPI with automatic API documentation and Chinese language support
- **Database**: PostgreSQL (production) + SQLite (testing) with async drivers and role-based access
- **ORM**: SQLAlchemy 2.0 with modern async/await patterns and connection pooling
- **Caching**: Redis with async Redis client for application caching and Celery broker
- **Task Queue**: Celery with Beat scheduler for background processing
- **Message Queue**: Apache Kafka via Confluent Platform for streaming data
- **Model Management**: MLflow with PostgreSQL backend and MinIO artifact storage
- **Feature Store**: Feast with Redis/PostgreSQL backend for ML features
- **Data Quality**: Great Expectations for data validation with automated checks
- **Monitoring**: Prometheus/Grafana metrics stack with comprehensive alerting

### Key Dependencies
- **Core**: FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, Alembic
- **ML**: MLflow, XGBoost, scikit-learn, pandas, numpy, PyArrow
- **Data Processing**: Apache Kafka, Great Expectations, Feast, Prefect
- **Testing**: pytest (385+ tests), pytest-cov, pytest-asyncio, factory-boy
- **Code Quality**: black, flake8, mypy, bandit, safety, ruff
- **Infrastructure**: Docker, docker-compose (15+ services), nginx

### Database Architecture
- **Multi-role connection management**: Single `DatabaseManager` with admin/writer/reader roles
- **Migration system**: Alembic with 10+ migration files for schema evolution
- **Dual database support**: Seamless switching between PostgreSQL (production) and SQLite (testing)
- **Connection pooling**: Advanced connection management for high performance with asyncpg

### Project Structure
```
src/
├── api/              # FastAPI API endpoints (health, predictions, monitoring)
├── config/           # Configuration management and FastAPI Chinese setup
├── core/             # Core business logic and services
├── database/         # Database models, migrations, and connection management
├── middleware/       # FastAPI middleware (i18n, CORS, etc.)
├── utils/            # Utility functions (crypto, data, time, validation)
├── ai/               # AI and machine learning components
├── cache/            # Redis caching layer
├── data/             # Data collection, processing, and quality
└── monitoring/       # Metrics collection and monitoring

tests/ (290+ test files, 96.35% coverage)
├── unit/             # Fast unit tests - use for reliable development
├── integration/      # Component integration tests (largely deleted, needs recreation)
└── e2e/              # End-to-end testing scenarios
```

### MLOps Pipeline Features
- **End-to-end MLOps**: Data collection → processing → feature store → ML models → predictions → monitoring
- **Feature store**: Feast-based feature management with Redis/PostgreSQL backends
- **Model versioning**: MLflow integration with PostgreSQL backend and MinIO artifact storage
- **Performance tracking**: Automated model performance monitoring with Prometheus/Grafana
- **Feedback loop**: Automated retraining pipeline with performance-based triggers
- **Quality Assurance**: Multi-layered testing with mutation testing and performance benchmarks

### Chinese Localization
- **I18N Support**: Complete internationalization with Chinese as primary language
- **API Documentation**: Chinese API docs via FastAPI automatic documentation
- **Error Messages**: Localized error messages and responses
- **Config**: Chinese configuration in `src/config/fastapi_config.py`
- **Middleware**: I18n middleware for request-based language detection

### Environment Configuration
- **CI Environment**: Complete environment defined in `.env.ci` (228 variables)
- **Docker Compose**: Multiple compose files for different environments (dev, test, prod, staging)
- **Database Roles**: Multi-user PostgreSQL setup with admin/writer/reader roles
- **Service Integration**: Pre-configured for MLflow, Feast, Kafka, Redis, PostgreSQL

### Database Management Commands
- **Database Initialization**: `make db-init` - Initialize database with migrations
- **Database Migration**: `make db-migrate` - Run database migrations
- **Database Seeding**: `make db-seed` - Seed database with initial data
- **Database Backup**: `make db-backup` - Create database backup
- **Database Restore**: `make db-restore BACKUP=filename.sql` - Restore from backup
- **Database Reset**: `make db-reset` - Reset database (WARNING: deletes all data)
- **Database Shell**: `make db-shell` - Open database shell for queries

### Security and Audit Commands
- **Security Scan**: `make security-check` - Run vulnerability scan (safety + bandit)
- **License Check**: `make license-check` - Check open source licenses
- **Dependency Check**: `make dependency-check` - Check for outdated dependencies
- **Secret Scan**: `make secret-scan` - Scan for secrets and sensitive data
- **Complete Audit**: `make audit` - Run complete security audit (all checks above)

### Testing and Quality Assurance Infrastructure
- **Mutation Testing**: `make mutation-test` - Run mutmut for code quality validation
- **Performance Benchmarks**: `make benchmark` - Execute pytest-benchmark performance tests
- **Coverage Analysis**: Multi-environment coverage with CI gating (80% CI, 60% local)
- **Regression Detection**: Automated performance and quality regression detection
- **Test Factories**: Comprehensive test data factories in `tests/factories/`
- **Mock Services**: Complete mock infrastructure in `tests/mocks/`
- **Performance Baselines**: `tests/performance/baseline_metrics.json` for comparison

### CI/CD Pipeline
- **Local CI Simulation**: `./ci-verify.sh` - Complete CI verification with Docker
- **GitHub Actions**: Automated CI with 80% coverage enforcement
- **Pre-push Checks**: `make prepush` - Complete validation before pushing
- **Docker Integration**: Multi-service container orchestration
- **Environment Parity**: CI environment matches production exactly

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.