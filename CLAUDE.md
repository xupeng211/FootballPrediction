# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**请使用简体中文回复用户** - Please respond in Simplified Chinese when interacting with the user. The project team primarily communicates in Chinese, so all responses should be in Simplified Chinese unless specifically requested otherwise.

## Project Overview

This is an enterprise-level football prediction system built with Python FastAPI, following Domain-Driven Design (DDD), CQRS, and Event-Driven architecture patterns. The system uses modern async/await patterns throughout and includes machine learning capabilities for match predictions.

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

### Technology Stack
- **Backend**: FastAPI 0.104+, SQLAlchemy 2.0+, Pydantic v2+, Redis 5.0+, PostgreSQL 15
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+, numpy 1.25+, MLflow 2.22.2+
- **Frontend**: React 19.2.0, TypeScript 4.9.5, Ant Design 5.27.6
- **Testing**: pytest 8.4+ with asyncio support, pytest-cov 7.0+, pytest-mock 3.14+
- **Code Quality**: Ruff 0.14+, MyPy 1.18+, Bandit 1.8.6+
- **Development Tools**: pre-commit 4.0.1, pip-audit 2.6.0, ipython 8.31+

### Database & Caching
- **Primary Database**: PostgreSQL 15 with async SQLAlchemy 2.0
- **Cache**: Redis 5.0+ for performance optimization
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

# Coverage analysis
pytest --cov=src --cov-report=html --cov-report=term-missing
```

## Docker Development

### Services
- **app**: FastAPI application (port: 8000)
- **frontend**: React application (ports: 3000, 3001)
- **db**: PostgreSQL 15 (port: 5432)
- **redis**: Redis 7.0 (port: 6379)
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

# Initial development setup
make install            # Install dependencies
make context            # Load project context
make env-check          # Verify environment configuration

# Edit with actual values
FOOTBALL_DATA_API_KEY=your_actual_api_key_here
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
4. make test            # Run tests
5. make lint && make fix-code  # Code quality checks
6. ./ci-verify.sh       # Pre-commit validation
7. make ci              # Full quality pipeline
```

## Quality Assurance

### Code Quality Tools
- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Bandit**: Security scanning
- **pytest**: Testing framework with asyncio support

### Pre-commit Checklist
- [ ] Tests pass: `make test`
- [ ] Code quality: `make fix-code`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Full validation: `make lint && make test`

## Troubleshooting

### Common Issues
1. **Test Failures**: Run `make test` to identify issues
2. **Type Errors**: Check imports and add missing type hints
3. **Database Issues**: Verify connection string and PostgreSQL status
4. **Redis Issues**: Check Redis service status and connection
5. **Port Conflicts**: Check if ports 8000, 3000, 5432, 6379 are available

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

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. All I/O operations must be async, maintain DDD layer separation, and follow established patterns.