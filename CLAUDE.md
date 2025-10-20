# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Guidelines
This project follows structured development practices. See [AGENTS.md](AGENTS.md) for repository structure, workflow, and security guidelines for contributors.

## Chinese Language Support
**重要：始终使用简体中文回复用户** - 与用户交流时必须使用简体中文，不要使用英文或其他语言。

## Project Overview

FootballPrediction is an enterprise-grade football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows Domain-Driven Design (DDD) principles with a layered architecture including API, Application, Domain, and Infrastructure layers.

## Development Commands

### Environment Setup
```bash
make dev-setup        # Complete development setup (install + env-check + context)
make env-check          # Check development environment health
make venv              # Create virtual environment
make install           # Install dependencies from lock file
make install-locked    # Install from locked dependencies (reproducible)
make context           # Load project context (⭐ most important)
make check-env         # Verify required environment variables
make create-env        # Create .env file from example
```

### Testing Commands
```bash
make test              # Run all tests (385 test cases)
make test-phase1       # Phase 1 core functionality tests (data, features, predictions)
make test-quick        # Quick unit tests (unit tests only, no slow tests)
make test-unit         # Run unit tests only (marked with 'unit')
make test-int          # Run integration tests only
make test-e2e          # Run end-to-end tests only
make test-api          # All API tests (marked with 'api')
make test-core-modules # Test high-value modules (config, utils, database)
make test-with-db      # Run tests with PostgreSQL
make test-with-redis   # Run tests with Redis
make test-all-services # Run tests with all external services
make coverage          # View coverage report (96.35% actual)
make coverage-fast     # Fast coverage (unit tests only, no slow tests)
make coverage-unit     # Unit test coverage only
make coverage-local    # Local coverage with development threshold
make cov.html          # Generate HTML coverage report
make cov.enforce       # Run coverage with strict 80% threshold
```

### Code Quality
```bash
make lint              # Run ruff and mypy checks
make fmt               # Format code with ruff (not black)
make type-check        # Run layered MyPy type checking
make typecheck-core    # Run type checking on core modules only (strict)
make typecheck-aux     # Run type checking on auxiliary modules (relaxed)
make ci                # Complete quality verification
make prepush           # Full validation before push (ruff + mypy core + pytest)
make quality           # Complete quality check (lint + format + test)
make check             # Alias for quality command
make security-check    # Run security vulnerability scan
make audit             # Complete security audit (security + license + secrets)
```

### Containerized Development
```bash
docker-compose up --build  # Start full environment (app, db, redis, nginx)
docker-compose exec app pytest  # Run tests in container

# Test environment management
make test-env-start     # Start integration test environment
make test-env-stop      # Stop test environment
make test-env-restart   # Restart test environment
make test-env-status    # Check test environment status
make test-env-shell     # Enter test container shell
make staging-start      # Start staging for E2E tests

# E2E Testing
make e2e-setup         # Setup E2E test environment
make e2e-run            # Quick E2E test run
make e2e-smoke          # Run smoke tests
make e2e-critical       # Run critical path tests
make e2e-performance    # Run performance tests
make e2e-full           # Run full test suite
```

## Architecture & Design Patterns

### Domain-Driven Design (DDD)
The project follows DDD principles with clear separation of concerns:
- **Domain Layer**: Business logic and rules (src/domain/)
- **Application Layer**: Use cases and orchestration (src/services/)
- **Infrastructure Layer**: External concerns (src/database/, src/cache/)
- **API Layer**: HTTP endpoints and routing (src/api/)

### Key Design Patterns Implemented
- **Repository Pattern**: Data access abstraction in src/repositories/
- **Factory Pattern**: For creating adapters and services
- **Strategy Pattern**: For different prediction algorithms
- **CQRS**: Command Query Responsibility Segregation
- **Event-Driven Architecture**: Domain events with observers
- **Decorator Pattern**: For cross-cutting concerns
- **Adapter Pattern**: For integrating external services

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
- **src/cqrs/**: CQRS pattern implementation with command/query separation
- **src/events/**: Event system and observers (domain events, integration events)
- **src/tasks/**: Celery task definitions and background job processing
- **src/utils/**: Utility functions and helpers
- **src/patterns/**: Design pattern implementations (Adapter, Decorator, Facade, Observer)

### Key Architecture Files
- `src/api/app.py`: Main FastAPI application with middleware and startup
- `src/core/prediction_engine.py`: Core prediction logic
- `src/database/session.py`: Database session management
- `src/cache/redis/`: Redis connection and key management
- `src/domain/strategies/`: Prediction algorithm strategies

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
- MyPy for type checking (strict mode for core modules, relaxed for aux)
- pytest with coverage reporting (80% threshold)
- Security scanning with bandit
- Pre-commit hooks with `make setup-hooks`

### Type Checking Strategy
The project uses layered MyPy type checking:
- **Core modules** (src/core, src/services, src/api, src/domain, src/repositories): strict mode
- **Auxiliary modules** (src/utils, src/monitoring, src/tasks, src/cache, src/collectors, src/data, src/features, src/ml, src/scheduler, src/security): relaxed mode
- Run `make type-check` for full layered check
- Use `make typecheck-core` for core modules only
- Use `make typecheck-aux` for auxiliary modules only

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

## Local Development Workflow

### Recommended Daily Workflow
1. **Morning Setup**: `make env-check && make context`
2. **During Development**: Use `make test-quick` for fast feedback
3. **Before Commit**: `make prepush` for quality validation
4. **End of Day**: `make coverage` to track metrics

### Local CI Validation

Before pushing code:
1. Run `make test` to ensure all tests pass
2. Run `make coverage` to verify coverage ≥80%
3. Run `make lint` and `make type-check` for code quality
4. Run `make ci` for complete validation
5. Use `./ci-verify.sh` for full CI simulation

### Technical Debt Management
The project includes automated technical debt tracking:
- `make debt-plan`: View daily cleanup plan
- `make debt-start TASK=1.1`: Start specific task
- `make best-practices-today`: Start optimization work

## Advanced Testing Features

### Test Categories & Markers
The project uses comprehensive pytest markers:
- `unit`: Unit tests for individual components
- `integration`: Multi-component interaction tests
- `api`: HTTP endpoint tests
- `database`: Tests requiring database connection
- `slow`: Long-running tests
- `smoke`: Basic functionality validation
- `e2e`: End-to-end workflow tests
- `performance`: Performance benchmarks
- `critical`: Must-pass core functionality tests

### Running Single Tests

While the project emphasizes using Makefile commands, you can run specific tests:
```bash
# Run a specific test file
pytest tests/unit/api/test_predictions.py -v

# Run tests by marker
pytest -m "unit and not slow" -v
pytest -m "integration" -v
pytest -m "api" -v
pytest -m "database" -v
pytest -m "requires_db" -v
pytest -m "requires_redis" -v

# Run with coverage for specific module
pytest tests/unit/api/test_predictions.py --cov=src.api.predictions --cov-report=term-missing

# Run tests in Docker for isolation
./scripts/run_tests_in_docker.sh

# Run with different thresholds
pytest --cov=src --cov-fail-under=80  # 80% threshold
pytest --cov=src --cov-fail-under=60  # 60% threshold (CI)
```

### Key Testing Files
- `pytest.ini`: Comprehensive test markers and configuration
- `tests/conftest.py`: Shared fixtures and test configuration
- `tests/factories/`: Test data factories for unit tests
- `tests/fixtures/`: Mock data and fixtures

## Docker & Container Development

### Test Containers
The project supports test-driven development with Docker containers:
```bash
# Start test environment
make test-env-start

# Run tests with containers
make test.containers

# Stop test environment
make test-env-stop
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

## Special Notes

### Coverage Discrepancy
There's a known discrepancy between coverage reports:
- README badge shows 16.5% (from CI runs)
- Actual coverage is 96.35% (check with `make coverage-unit`)
- CI uses lower threshold (60%) for reliability
- Local development shows actual coverage

### Dependency Management
- Use `make lock-deps` to update locked dependencies
- Use `make verify-deps` to ensure reproducible builds
- Never edit requirements/requirements.lock manually
- Use `make smart-deps` for AI-guided dependency checks

### Performance Monitoring
- The project includes comprehensive performance tracking
- Use `make benchmark-full` for performance benchmarks
- Memory profiling available with `make profile-memory`
- Flame graphs for performance visualization with `make flamegraph`

### Debugging Tools
- `make debug-shell`: Open debug shell in container
- `make logs`: View application logs
- `make db-shell`: Open database shell
- `make redis-shell`: Open Redis CLI

### AI-Assisted Development
The project is optimized for AI assistance:
- Comprehensive .cursorrules for Cursor IDE users
- GitHub Copilot instructions available in .github/copilot-instructions.md
- Context loading with `make context` for AI assistants
- All code follows consistent patterns for easy AI comprehension

### Security & Compliance
- Run `make audit` for complete security audit
- Vulnerability scanning with `make security-check`
- License compliance with `make license-check`
- Secret scanning with `make secret-scan`

## MLOps & Model Management

The system includes a complete MLOps pipeline:
```bash
# Update predictions with actual outcomes
make feedback-update

# Generate performance reports
make performance-report

# Check if models need retraining
make retrain-check

# Run full MLOps pipeline
make mlops-pipeline
```

### Model Lifecycle
- Models are automatically monitored for accuracy degradation
- Retraining is triggered when accuracy falls below 45%
- All predictions are tracked with actual outcomes for learning
- Performance trends are analyzed and reported

## Documentation & Resources

- **Test Improvement Guide**: docs/TEST_IMPROVEMENT_GUIDE.md
- **Tools Documentation**: TOOLS.md
- **Kanban Management**: See Kanban Check workflow in GitHub Actions
- **Architecture Overview**: docs/architecture/ (generate with `make docs-architecture`)
- **API Documentation**: Available at http://localhost:8000/docs when running
- **Test Run Guide**: TEST_RUN_GUIDE.md (essential reading for testing)

## Getting Help

- Run `make help` to see all available commands
- Check .cursorrules for development rules
- Review .github/copilot-instructions.md for AI assistance guidelines
- Use `make context` to load project state before starting work

## Repository Best Practices

### Daily Development Workflow
1. **Start**: `make dev-setup` (first time only)
2. **Daily**: `make env-check && make context`
3. **During Development**: `make test-quick` for fast feedback
4. **Before Commit**: `make prepush` for quality validation
5. **End of Day**: `make coverage-unit` to track metrics

### Critical Reminders
- **NEVER** run pytest directly on individual files - always use Makefile commands
- **ALWAYS** run `make env-check` before starting work
- **ALWAYS** activate virtual environment before development
- **NEVER** commit secrets or API keys
- **ALWAYS** use Ruff for formatting (NOT Black)
- **Python 3.11+ is required**

## Architecture Deep Dive

### Async/Await Patterns
The project extensively uses async/await patterns:
- Database operations with SQLAlchemy 2.0 async
- Redis caching with async Redis client
- FastAPI endpoints with async route handlers
- Background tasks with Celery

### Database Architecture
- PostgreSQL as primary database
- Connection pooling with asyncpg
- Migration management with Alembic
- Repository pattern for data access

### Caching Strategy
- Redis as distributed cache
- TTL-based cache invalidation
- Cache warming strategies
- Consistency management patterns

### Event-Driven Architecture
- Domain events for business logic
- Integration events for system communication
- Observer pattern for decoupled components
- Event sourcing for audit trails
