# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start

**Always run this first when starting work:**
```bash
make install      # Install dependencies and create virtual environment
make context      # Load project context (most important)
make env-check    # Verify environment health
```

### AI Development Guidelines
The project includes comprehensive AI development guidelines in `.cursor/rules/` directory that work with both Cursor and Claude Code:
- **Tool Priority**: Use Makefile commands for consistency
- **Quality Standards**: 80%+ test coverage (CI), 20%+ (local)
- **Code Style**: Black formatting, mypy type checking, flake8 linting
- **Documentation**: Clear comments and structured output
- **Docker CI**: Validate with `./ci-verify.sh` before pushing
- **Modify Over Create**: Prioritize modifying existing files over creating new ones
- **Context Loading**: Always run `make context` first to understand project state

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
- `make test` - Run pytest unit tests (385+ tests, 96.35% coverage)
- `make coverage` - Run tests with coverage report (80% threshold enforced in CI, 20% for local development)
- `make coverage-fast` - Run fast coverage (unit tests only, 20% threshold for development)
- `make test-quick` - Quick test run (unit tests with timeout)
- `make coverage-unit` - Unit test coverage with HTML report
- `./ci-verify.sh` - Complete CI verification with Docker environment (⭐ Critical before pushing)

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

This is a **production-ready enterprise football prediction system** built with modern Python technologies, featuring **asynchronous-first architecture** and comprehensive **MLOps pipeline**:

### Core Technology Stack
- **FastAPI** - Modern async web framework with automatic API documentation
- **SQLAlchemy 2.0** - Modern ORM with async support and aiosqlite/asyncpg compatibility
- **PostgreSQL** - Primary database with multi-user role architecture (READER, WRITER, ADMIN)
- **SQLite** - Testing database with seamless switching capability
- **Redis** - Caching, session storage, and Celery broker
- **Celery** - Distributed task queue with Beat scheduler for background processing
- **MLflow** - Model lifecycle management with PostgreSQL backend and MinIO artifact storage
- **Feast** - Feature store for ML features with Redis/PostgreSQL backend
- **Kafka** - Streaming data processing with Confluent Platform
- **Great Expectations** - Data quality validation and monitoring
- **Prometheus/Grafana** - Metrics collection and visualization
- **MinIO** - Object storage for data lake and ML artifacts
- **OpenLineage** - Data lineage tracking and governance

### Project Structure
```
src/
├── api/           # FastAPI REST API Layer (health, predictions, features, data, monitoring)
├── cache/         # Redis caching layer with TTL support
├── core/          # Core utilities (logging, exceptions, configuration)
├── database/      # Database abstraction layer with multi-role connection management
│   ├── models/          # 11+ SQLAlchemy ORM models
│   ├── migrations/      # Alembic-managed schema migrations (10+ files)
│   ├── connection.py    # Advanced async/sync DB connection manager
│   └── config.py        # Database configuration
├── data/          # Data processing pipeline
│   ├── collectors/      # Live football data collection (WebSocket, HTTP APIs)
│   ├── processing/      # Data cleaning and transformation pipelines
│   ├── quality/         # Great Expectations data validation
│   ├── storage/         # Data lake storage interfaces
│   └── features/        # Feature engineering pipelines
├── features/      # Feature store integration (Feast)
├── lineage/       # OpenLineage data governance
├── models/        # Machine Learning layer
│   ├── prediction_service.py  # Core XGBoost prediction service
│   ├── model_training.py      # Model training pipeline
│   └── common_models.py      # ML model utilities
├── monitoring/    # Prometheus metrics and model performance monitoring
├── scheduler/     # Task scheduling with Celery Beat
├── services/      # Business logic services
├── streaming/     # Kafka stream processing
├── tasks/         # Celery background tasks
├── utils/         # Shared utility functions
└── main.py        # FastAPI application entry point
```

### Key Architectural Patterns

#### Async-First Architecture
- **129+ async Python files** with comprehensive async/await patterns
- **Dual database support**: PostgreSQL (production) + SQLite (testing) via aiosqlite/asyncpg
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

#### Multi-Layer Caching Strategy
- **Redis**: Application-level caching with TTL
- **Feature Store**: Feast-based feature caching
- **Model Cache**: MLflow model versioning with local caching
- **Database**: Connection pooling and query caching

#### Sophisticated Data Management
- **Multi-user database architecture**: READER, WRITER, ADMIN roles
- **Data lineage**: OpenLineage integration for governance
- **Data quality**: Great Expectations validation
- **Streaming**: Kafka for real-time data processing

## 🔄 Development Workflow

### Essential Start Sequence
1. **Environment Setup**: `make install` to set up development environment
2. **Context Loading**: `make context` to understand current project state (⭐ Critical)
3. **Environment Check**: `make env-check` to verify environment health

### AI Development Principles
- **Tool Priority**: Use Makefile commands for consistency and reliability
- **Modify Over Create**: Prioritize modifying existing files over creating new ones
- **Modular Design**: Keep files focused on single responsibilities
- **Quality First**: All changes should pass `make ci` checks
- **Docker CI**: Validate with `./ci-verify.sh` before pushing

### Quality Assurance
1. **Code Quality**: Use `make prepush` before committing to ensure all checks pass
2. **Testing**: CI requires 80%+ coverage, local development uses 20-50% thresholds for speed
3. **Local CI**: Use `./ci-verify.sh` to simulate full CI environment locally (⭐ Required before pushing)

### Critical Requirements
- **Test Coverage**: Currently 96.35% coverage with 385+ tests; CI enforces 80%+ minimum (local dev uses 20-50% for faster iteration)
- **Type Safety**: Full mypy type checking required for all code (with some module exclusions)
- **Code Formatting**: Black and isort automatically applied with flake8 linting
- **Database**: Uses both SQLite (testing) and PostgreSQL (production) with compatibility layer
- **Async Architecture**: 128+ Python files with comprehensive async/await patterns
- **Security**: Multi-user database roles, input validation, audit logging
- **Dependency Management**: Uses strict version constraints and conflict resolution
- **Container Management**: Docker Compose with multiple environment configurations

### Configuration Files

- `requirements.txt` - Production dependencies (FastAPI, SQLAlchemy, MLflow, Feast, Great Expectations)
- `requirements-dev.txt` - Development tools with conflict resolution (pytest, black, mypy, bandit)
- `alembic.ini` - Database migration configuration
- `mypy.ini` - Type checking with module-specific exclusions
- `setup.cfg` - Flake8 and tool configurations
- `feature_store.yaml` - Feast feature store configuration
- `docker-compose.yml` - Complete development environment (15+ services)
- `docker-compose.test.yml` - CI testing environment
- `docker-compose.grafana.yml` - Monitoring stack (Grafana, Prometheus)
- `docker-compose.override.yml` - Development environment overrides
- `docker-compose.dev.yml` - Development-specific configuration
- `docker-compose.staging.yml` - Staging environment configuration
- `docker-compose.prometheus.yml` - Prometheus monitoring configuration
- `pytest.ini` - pytest configuration with 80% coverage threshold and comprehensive test markers
- `.coveragerc` - Coverage configuration with exclusions for fast development
- `ci-verify.sh` - Complete CI verification script with Docker environment
- `Makefile` - Comprehensive build automation with 50+ commands
- `.cursor/rules/` - AI development guidelines and project standards

### Development Guidelines

The project follows established development patterns with comprehensive tooling and automation. Key guidelines include:
- **Code Quality**: Black formatting, flake8 linting, mypy type checking
- **Testing**: pytest with coverage requirements (80% CI, 20-50% local development)
- **CI/CD**: GitHub Actions with local simulation via `./ci-verify.sh`
- **Documentation**: Comprehensive project documentation in `docs/` directory
- **MLOps**: Complete machine learning operations pipeline with automated retraining

#### Key AI Development Principles:
- **Modify over Create**: Prioritize modifying existing files over creating new ones
- **Structured Output**: Use tables, directories, and organized formats
- **Test Coverage**: New code should achieve 80%+ test coverage where feasible
- **Async Architecture**: All database operations and external API calls use async/await
- **Quality Gates**: Must pass all CI checks including type safety, linting, and security scanning
- **Docker Testing**: Test in local Docker environment using `./ci-verify.sh` before pushing
- **Context Awareness**: Always run `make context` first to understand project state and patterns

### pytest Configuration
- **Coverage threshold**: 80% minimum (enforced in CI), 20-50% for local development
- **Test markers**: unit, integration, slow, asyncio, e2e, docker, performance, timeout, edge_case, failure_scenario, mlflow, db, kafka, celery, ml
- **Async mode**: auto with function fixture loop scope
- **Test discovery**: test_*.py files, Test* classes, test_* functions
- **Warning filters**: Handles deprecation warnings and third-party compatibility issues
- **Test paths**: tests/ directory with comprehensive organization

### Coverage Configuration (.coveragerc)
- **Source paths**: src/ directory
- **Exclusions**: Tests, migrations, scripts, main.py, and heavy integration layers
- **Fast coverage**: Excludes API, data, services, utils, cache, monitoring layers for speed
- **Report settings**: Shows missing lines, generates HTML reports in htmlcov/
- **Branch coverage**: Enabled for comprehensive test coverage analysis

### Testing Tips & Troubleshooting

#### Test Organization (385+ tests)
- **Unit Tests**: `tests/unit/` - Fast, isolated tests for individual components (300+ tests)
- **Integration Tests**: `tests/integration/` - Tests for component interactions (30+ tests)
- **E2E Tests**: `tests/e2e/` - End-to-end testing scenarios
- **Demo Tests**: `tests/demo/` - Example and demonstration tests
- **Feature Tests**: `tests/test_features/` - Feature-specific testing

#### MLOps Pipeline Testing
- **Feedback Loop Tests**: `make feedback-test` - Test prediction feedback and retraining logic
- **Model Monitoring Tests**: Tests for model performance tracking and automated retraining
- **Data Quality Tests**: Great Expectations validation and data pipeline testing

#### Performance Testing Commands
- **Application Profiling**: `make profile-app` - Profile main application performance
- **Test Profiling**: `make profile-tests` - Profile test execution performance
- **Memory Analysis**: `make profile-memory` - Analyze memory usage patterns
- **Performance Benchmarks**: `make benchmark` - Run performance benchmarks
- **Flame Graphs**: `make flamegraph` - Generate performance visualization flame graphs

#### Common Testing Commands
- **Single test file**: `pytest tests/unit/test_specific_module.py -v`
- **Stop on first failure**: `pytest -x` or `pytest --maxfail=3`
- **Verbose output with tracebacks**: `pytest -v --tb=long`
- **Run specific test**: `pytest tests/unit/test_module.py::TestClass::test_method`
- **Run with markers**: `pytest -m "not slow"` to exclude slow tests
- **Run specific test categories**: `pytest tests/unit/` (unit tests only)

#### Performance Tips
- Use `make coverage-fast` instead of `make coverage` for quicker feedback during development
- Use `make test-quick` for rapid iteration with timeout protection
- Integration tests may require external services - ensure Docker containers are running with `docker-compose up -d`
- CI uses different coverage thresholds (70%) than local development (60%)
- For fast iteration during development, run `make test-quick` to focus on unit tests only

#### Docker Environment Testing
- The project uses multiple `docker-compose*.yml` files for different environments
- Use `./ci-verify.sh` to test in complete CI environment before pushing
- Ensure PostgreSQL and Redis services are running when running integration tests
- Database migrations are automatically applied in CI environments

#### Common Issues and Solutions
- **Coverage reporting slow**: Use `make coverage-fast` for unit tests only (20% threshold) or `make test-quick` for quick feedback
- **Database connection errors**: Ensure Docker services are running with `docker-compose up -d` and use `./ci-verify.sh` for full CI environment
- **Import errors**: Run with proper PYTHONPATH: `export PYTHONPATH="$(pwd):${PYTHONPATH}"`
- **Test timeouts**: Use `make test-quick` for timeout protection or `pytest -x` to stop on first failure
- **Large test suite**: Use `pytest tests/unit/` for unit tests only, or `pytest tests/unit/test_specific_module.py` for specific modules

## 🔧 Development Environment Setup

### Technology Stack
- **Language**: Python 3.11+
- **Web Framework**: FastAPI with automatic API documentation
- **Database**: PostgreSQL (production) + SQLite (testing) with async drivers
- **ORM**: SQLAlchemy 2.0 with modern async/await patterns
- **Caching**: Redis with async Redis client
- **Task Queue**: Celery with Beat scheduler
- **Message Queue**: Apache Kafka via Confluent Platform
- **Model Management**: MLflow with PostgreSQL backend and MinIO artifact storage
- **Feature Store**: Feast with Redis/PostgreSQL backend
- **Data Quality**: Great Expectations for data validation
- **Monitoring**: Prometheus/Grafana metrics stack
- **Object Storage**: MinIO for data lake and ML artifacts

### Key Dependencies
- **Core**: FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery
- **ML**: MLflow, XGBoost, scikit-learn, pandas, numpy
- **Data Processing**: Apache Kafka, Great Expectations, Feast
- **Testing**: pytest, pytest-cov, pytest-asyncio, factory-boy
- **Code Quality**: black, flake8, mypy, bandit, safety
- **Infrastructure**: Docker, docker-compose, nginx

### Database Architecture
- **Multi-role connection management**: Single `DatabaseManager` with role-based access
- **Migration system**: Alembic with 10+ migration files
- **Dual database support**: Seamless switching between PostgreSQL and SQLite
- **Connection pooling**: Advanced connection management for high performance

### MLOps Pipeline Features
- **End-to-end MLOps**: Data collection → model training → predictions → monitoring
- **Feature store**: Proper feature management with Feast
- **Model versioning**: MLflow integration for model lifecycle
- **Performance tracking**: Automated model performance monitoring
- **Feedback loop**: Automated retraining based on model performance

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
- **Development Stats**: `make dev-stats` - Show development statistics
- **Code Quality Report**: `make code-quality-report` - Generate code quality metrics