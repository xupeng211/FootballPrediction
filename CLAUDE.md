# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FootballPrediction is an enterprise-grade football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows Domain-Driven Design (DDD) principles with a layered architecture including API, Application, Domain, and Infrastructure layers.

## Development Commands

### Environment Setup
```bash
make env-check          # Check development environment health
make venv              # Create virtual environment
make install           # Install dependencies from lock file
make context           # Load project context (⭐ most important)
```

### Testing Commands
```bash
make test              # Run all tests (385 test cases)
make test-phase1       # Phase 1 core functionality tests (data, features, predictions)
make test-unit         # Run unit tests only (marked with 'unit')
make test-int          # Run integration tests only
make test-e2e          # Run end-to-end tests only
make test-api          # All API tests (marked with 'api')
make test-quick        # Quick unit tests (use test-unit for faster feedback)
make coverage          # View coverage report (96.35%)
make coverage-fast     # Fast coverage (unit tests only, no slow tests)
make coverage-unit     # Unit test coverage only
```

### Code Quality
```bash
make lint              # Run ruff and mypy checks
make fmt               # Format code with ruff (not black)
make type-check        # Run mypy type checking
make ci                # Complete quality verification
make prepush           # Full validation before push
make quality           # Complete quality check (lint + format + test)
```

### Containerized Development
```bash
docker-compose up --build  # Start full environment (app, db, redis, nginx)
docker-compose exec app pytest  # Run tests in container
```

## Architecture

### Core Structure
- **src/api/**: FastAPI routes, endpoints, and API models
- **src/core/**: Core business logic and domain services
- **src/domain/**: Domain models and business rules
- **src/database/**: Database connections, models, and migrations (SQLAlchemy 2.0)
- **src/services/**: Business services and application logic
- **src/adapters/**: External service adapters and factory patterns
- **src/cache/**: Redis caching layer
- **src/security/**: Authentication, authorization, and JWT handling
- **src/monitoring/**: Metrics, logging, and health checks
- **src/ml/**: Machine learning components and prediction models
- **src/cqrs/**: CQRS pattern implementation
- **src/events/**: Event system and observers
- **src/tasks/**: Celery task definitions
- **src/utils/**: Utility functions and helpers

### Testing Infrastructure
- **tests/unit/**: Unit tests for individual components
- **tests/integration/**: Multi-component interaction tests
- **tests/e2e/**: End-to-end workflow tests
- **tests/factories/**: Test data factories
- **tests/fixtures/**: Test fixtures and mocks

## Key Development Practices

### Tool-First Approach
Always use existing tools before AI assistance:
1. Run `make env-check` to validate environment
2. Use `make context` to load project state
3. Use Makefile commands, never run pytest directly on individual files
4. Run `make ci` for quality verification before commits

### Testing Standards
- Coverage threshold: 80% (currently at 96.35%)
- 385 test cases across multiple categories
- Phase-based testing with Phase 1 for core functionality
- Comprehensive test markers (see pytest.ini): unit, integration, api, database, slow, smoke, e2e, performance, critical, asyncio, regression, auth, cache, monitoring

### Code Quality Gates
- Ruff for linting AND formatting (configured in pyproject.toml, line length 88)
- MyPy for type checking (strict mode)
- pytest with coverage reporting (80% threshold)
- Security scanning with bandit

## Configuration

### Environment Variables
Key environment variables (see .env.example):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key
- `ENVIRONMENT`: Environment (development/staging/production)

### Dependencies
- Locked dependencies in requirements/requirements.lock
- Use `make install-locked` for reproducible builds
- Python 3.11+ required
- Key dependencies: FastAPI 0.115.6, SQLAlchemy 2.0.36, Redis 5.2.1, Pydantic 2.10.4

## Local CI Validation

Before pushing code:
1. Run `make test` to ensure all tests pass
2. Run `make coverage` to verify coverage ≥80%
3. Run `make lint` and `make type-check` for code quality
4. Run `make ci` for complete validation

## Running Single Tests

While the project emphasizes using Makefile commands, you can run specific tests:
```bash
# Run a specific test file
pytest tests/unit/api/test_predictions.py -v

# Run tests by marker
pytest -m "unit and not slow" -v

# Run with coverage for specific module
pytest tests/unit/api/test_predictions.py --cov=src.api.predictions --cov-report=term-missing
```

## Important Notes

- Always activate virtual environment before development
- Use Docker Compose for consistent local environment
- Follow the existing code patterns and conventions
- Test-driven development approach encouraged
- Never commit secrets or API keys
- Use conventional commit messages
- The project uses Ruff for BOTH linting and formatting (not Black)
- Python 3.11+ is required
