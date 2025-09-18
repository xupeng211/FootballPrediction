# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Commands
- `make help` - Show all available commands with categorized help
- `make install` - Install dependencies from requirements.txt and requirements-dev.txt
- `make venv` - Create virtual environment (.venv)
- `make env-check` - Check development environment health

### Code Quality
- `make lint` - Run flake8 and mypy checks
- `make fmt` - Format code with black and isort
- `make type-check` - Run mypy type checking
- `make quality` - Complete quality check (lint + format + test)

### Testing
- `make test` - Run pytest unit tests
- `make coverage` - Run tests with coverage report (80% threshold)
- `make coverage-fast` - Run fast coverage (unit tests only)
- `make test-quick` - Quick test run (unit tests with timeout)

### CI/CD Simulation
- `make ci` - Simulate GitHub Actions CI pipeline
- `make prepush` - Complete pre-push validation (format + lint + type-check + test)
- `./ci-verify.sh` - Full CI verification with Docker environment

### Container Management
- `make up` - Start docker-compose services
- `make down` - Stop docker-compose services
- `make logs` - Show docker-compose logs

### MLOps Pipeline
- `make feedback-update` - Update prediction results with actual outcomes
- `make performance-report` - Generate model performance reports
- `make retrain-check` - Check models and trigger retraining if needed
- `make model-monitor` - Run enhanced model monitoring cycle
- `make mlops-pipeline` - Run complete MLOps feedback pipeline

### Project Context
- `make context` - Load project context for AI development (important for understanding codebase)
- `make sync-issues` - Sync GitHub issues between local and GitHub

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
├── core/          # Core utilities (logging, exceptions)
├── database/      # Database models and migrations
├── data/          # Data collection, processing, and quality
├── features/      # Feature engineering and store
├── models/        # ML models and prediction services
├── monitoring/    # Metrics collection and alerting
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

#### ML Pipeline
- **Models** (`src/models/`) - XGBoost-based prediction models
- **MLOps** - Complete feedback loop with performance monitoring and auto-retraining
- **Monitoring** (`src/monitoring/`) - Prometheus metrics and alerting

#### Infrastructure
- **Database Migrations** - Alembic-managed database schema evolution
- **Async Architecture** - Full async/await support throughout the stack
- **Docker Environment** - Production-ready containerization
- **CI/CD** - GitHub Actions with local simulation capabilities

### Development Workflow

1. **Environment Setup**: Run `make install` to set up development environment
2. **Context Loading**: Always run `make context` to understand current project state
3. **Code Quality**: Use `make prepush` before committing to ensure all checks pass
4. **Testing**: Maintain 80%+ test coverage (enforced by `make coverage`)
5. **Local CI**: Use `./ci-verify.sh` to simulate full CI environment locally

### Important Notes

- **Test Coverage**: Strictly enforced at 80% minimum via pytest-cov
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
- `docker-compose.yml` - Full development environment

### AI Development Rules

The project includes comprehensive AI development guidelines in `.cursor/rules/` directory:
- `coding-standards.mdc` - Python coding standards
- `testing-workflow.mdc` - Testing requirements and patterns
- `ci-pipeline.mdc` - CI/CD pipeline standards
- `git-workflow.mdc` - Git workflow and commit message standards

Always refer to these rules and run `make context` to load project-specific AI development guidance.
