# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Commands
- `make help` - Show all available commands with categorized help
- `make install` - Install dependencies from requirements.txt and requirements-dev.txt
- `make venv` - Create virtual environment (.venv)
- `make env-check` - Check development environment health
- `make context` - Load project context for AI development (important for understanding codebase)

### Code Quality
- `make lint` - Run flake8 and mypy checks
- `make fmt` - Format code with black and isort
- `make type-check` - Run mypy type checking
- `make quality` - Complete quality check (lint + format + test)
- `make prepush` - Complete pre-push validation (format + lint + type-check + test)

### Testing
- `make test` - Run pytest unit tests
- `make coverage` - Run tests with coverage report (70% threshold)
- `make coverage-fast` - Run fast coverage (unit tests only, 70% threshold)
- `make coverage-unit` - Unit test coverage only (with HTML report)
- `make test-quick` - Quick test run (unit tests with timeout)
- `pytest tests/unit/` - Run only unit tests
- `pytest tests/integration/` - Run only integration tests
- `pytest tests/unit/test_specific.py::test_function` - Run specific test
- `./venv/bin/pytest tests/unit/ --cov=src --cov-report=term-missing --disable-warnings` - Run unit tests with coverage

#### Test Markers
- `pytest -m unit` - Run only unit tests (no external dependencies)
- `pytest -m integration` - Run integration tests (with external dependencies)
- `pytest -m slow` - Run slow tests (>5 seconds)
- `pytest -m "not slow"` - Skip slow tests
- `pytest -m asyncio` - Run async tests only

### CI/CD Simulation
- `make ci` - Simulate GitHub Actions CI pipeline
- `./ci-verify.sh` - Full CI verification with Docker environment (run before pushing)

### Container Management
- `make up` - Start docker-compose services
- `make down` - Stop docker-compose services
- `make logs` - Show docker-compose logs
- `make deploy` - Build & start containers with git-sha tag
- `make rollback TAG=<sha>` - Rollback to previous image tag

### MLOps Pipeline
- `make feedback-update` - Update prediction results with actual outcomes
- `make feedback-report` - Generate accuracy trends and feedback analysis
- `make performance-report` - Generate model performance reports with charts
- `make retrain-check` - Check models and trigger retraining if needed
- `make retrain-dry` - Dry run retrain check (evaluation only)
- `make model-monitor` - Run enhanced model monitoring cycle
- `make feedback-test` - Run feedback loop unit tests
- `make mlops-pipeline` - Run complete MLOps feedback pipeline
- `make mlops-status` - Show MLOps pipeline status

### Development Environment
- `make check-deps` - Verify required Python dependencies are installed
- `make sync-issues` - Sync issues between local and GitHub
- `make clean` - Remove cache and virtual environment

## Architecture Overview

This is a production-ready football prediction system built with modern Python technologies:

### Core Technology Stack
- **FastAPI** - Web framework with automatic API documentation
- **SQLAlchemy 2.0** - Modern ORM with async support
- **PostgreSQL** - Primary database with async drivers (asyncpg)
- **Redis** - Caching and session storage
- **Celery** - Task queue for background processing
- **MLflow** - Model lifecycle management
- **Feast** - Feature store for ML features
- **Kafka** - Streaming data processing

### Project Structure
```
src/
├── api/           # FastAPI routes and schemas
├── cache/         # Caching implementations (Redis, TTL cache)
├── core/          # Core utilities (logging, exceptions)
├── database/      # Database models and migrations
├── data/          # Data collection, processing, and quality
├── features/      # Feature engineering and store
├── lineage/       # Data lineage and metadata tracking
├── models/        # ML models and prediction services
├── monitoring/    # Metrics collection and alerting
├── scheduler/     # Task scheduling and management
├── services/      # Business logic services
├── streaming/     # Kafka stream processing
├── tasks/         # Celery background tasks
├── utils/         # Utility functions
└── main.py        # FastAPI application entry point
```

### Key Components

#### Data Layer
- **Data Collectors** (`src/data/collectors/`) - Football data collection from APIs
- **Data Processing** (`src/data/processing/`) - Data cleaning and transformation
- **Data Quality** (`src/data/quality/`) - Great Expectations integration for data validation
- **Feature Store** (`src/features/`) - Feast-based feature management
- **Caching Layer** (`src/cache/`) - Redis and TTL cache implementations
- **Data Lineage** (`src/lineage/`) - Metadata tracking and data flow monitoring

#### ML Pipeline
- **Models** (`src/models/`) - XGBoost-based prediction models
- **MLOps** - Complete feedback loop with performance monitoring and auto-retraining
- **Monitoring** (`src/monitoring/`) - Prometheus metrics and alerting

#### Infrastructure
- **Database Migrations** - Alembic-managed database schema evolution
- **Async Architecture** - Full async/await support throughout the stack
- **Task Scheduling** (`src/scheduler/`) - Background job scheduling and management
- **Docker Environment** - Production-ready containerization
- **CI/CD** - GitHub Actions with local simulation capabilities

#### Full Stack Services
- **FastAPI Application** (`src/main.py`) - Main application with lifespan management
- **Celery Workers** (`src/tasks/`) - Background task processing
- **Kafka Streaming** (`src/streaming/`) - Real-time data processing
- **Business Services** (`src/services/`) - Core business logic services

### Development Workflow

1. **Environment Setup**: Run `make install` to set up development environment
2. **Context Loading**: Always run `make context` to understand current project state
3. **Code Quality**: Use `make prepush` before committing to ensure all checks pass
4. **Testing**: Maintain 70%+ test coverage (enforced by `make coverage`)
5. **Local CI**: Use `./ci-verify.sh` to simulate full CI environment locally

### Important Notes

- **Test Coverage**: Currently configured with 70% minimum threshold via pytest-cov
- **Type Safety**: Full mypy type checking required for all code
- **Code Formatting**: Black and isort automatically applied
- **Database**: Uses both SQLite (testing) and PostgreSQL (production) with compatibility layer
- **MLOps**: Automated model performance monitoring and retraining pipeline
- **Async**: All database operations and external API calls use async/await patterns

### Configuration Files

- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development and testing tools
- `alembic.ini` - Database migration configuration
- `mypy.ini` - Type checking configuration
- `setup.cfg` - Flake8 and other tool configurations
- `feature_store.yaml` - Feast feature store configuration
- `docker-compose.yml` - Full development environment with 15+ services

### AI Development Rules

The project includes comprehensive AI development guidelines in `.cursor/rules/` directory:
- `coding-standards.mdc` - Python coding standards
- `testing-workflow.mdc` - Testing requirements and patterns
- `ci-pipeline.mdc` - CI/CD pipeline standards
- `git-workflow.mdc` - Git workflow and commit message standards
- `ai.mdc` - AI development guidelines

#### Key AI Development Principles
- **Tools-First Approach**: All operations must go through Makefile commands
- **Environment Requirements**: All operations must use activated virtual environment
- **Context Loading**: Always run `make context` before starting development work
- **Quality Standards**: 70%+ test coverage, complete type annotations, comprehensive error handling
- **Prohibited Actions**: Bypassing Makefile, skipping CI checks, direct script execution

Always refer to these rules and run `make context` to load project-specific AI development guidance.

### Docker Environment Services

The project includes a comprehensive Docker environment with:
- **PostgreSQL** - Primary database with health checks
- **Redis** - Caching and message broker with password protection
- **Kafka/Zookeeper** - Streaming data processing
- **MinIO** - S3-compatible object storage for data lake
- **MLflow** - Model tracking and registry
- **Prometheus/Grafana** - Monitoring and visualization
- **Celery** - Task queue with worker, beat, and flower monitoring
- **Marquez** - Data lineage tracking
- **Nginx** - Reverse proxy

### Critical Development Notes

- **Mandatory Context Loading**: Before any development work, always run `make context` to load project-specific guidance
- **Chinese Comments**: All generated code must include detailed Chinese comments
- **No Direct Script Execution**: Never bypass Makefile - all operations must go through `make` commands
- **Virtual Environment Required**: All operations must be performed in the activated virtual environment
- **No `any` Types**: Strict type annotations required - `any` type is prohibited
- **80% Test Coverage**: Current threshold is 70% but project aims for 80%+ coverage
- **Pre-Push Validation**: Always run `make prepush` and `./ci-verify.sh` before committing changes
- **Docker Environment**: The system includes 15+ services in docker-compose.yml for production-like development
