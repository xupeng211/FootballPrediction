# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**请使用简体中文回复用户** - Please respond in Simplified Chinese when interacting with the user. The project team primarily communicates in Chinese, so all responses should be in Simplified Chinese unless specifically requested otherwise.

## Project Overview

This is an enterprise-level football prediction system built with Python FastAPI, following Domain-Driven Design (DDD), CQRS, and Event-Driven architecture patterns. The system uses modern async/await patterns throughout and includes machine learning capabilities for match predictions.

**Project Scale**:
- **Large-scale Python project** - Enterprise-grade application architecture
- **Comprehensive testing** - Four-layer testing architecture (Unit: 85%, Integration: 12%, E2E: 2%, Performance: 1%)
- **613-line Makefile** - Complete development workflow automation
- **40+ API endpoints** - Supporting both v1 and v2 versions
- **7 dedicated queues** - Celery distributed task scheduling

## Key Development Commands

### Environment Management
```bash
# Start development environment
make dev

# Start production environment
make prod

# Stop services
make down

# Clean resources
make clean

# Check service status
make status

# Build and deployment
make build
make dev-rebuild
make prod-rebuild

# Complete CI validation
make ci
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

### Technology Stack

#### Backend Core
- **FastAPI**: Modern async web framework with 40+ API endpoints
- **Database**: PostgreSQL 15 with async SQLAlchemy 2.0+
- **Cache**: Redis 7.0+ for caching and Celery broker
- **ORM**: SQLAlchemy 2.0+ with async connection pooling
- **Serialization**: Pydantic v2+ for data validation

#### Machine Learning
- **ML Framework**: XGBoost 2.0+, scikit-learn 1.3+, TensorFlow/Keras
- **ML Management**: MLflow 2.22.2+ for experiment tracking
- **Feature Engineering**: pandas 2.1+, numpy 1.25+
- **Optimization**: Optuna 4.6.0+ for hyperparameter tuning

#### Frontend
- **Framework**: React 19.2.0, TypeScript 4.9.5
- **UI Library**: Ant Design 5.27.6
- **Build Tools**: Vite for modern bundling

#### Development Tools
- **Code Quality**: Ruff 0.14+ (linting/formatting), Bandit 1.8.6+ (security)
- **Testing**: pytest 8.4.0+ with asyncio support, pytest-cov 7.0+
- **Type Checking**: MyPy 1.18+ (temporarily disabled for CI stability)
- **Dependencies**: pip-tools 7.4.1+, pre-commit 4.0.1+

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
- **app**: FastAPI application (port: 8000)
- **db**: PostgreSQL 15 (port: 5432)
- **redis**: Redis 7.0 (port: 6379)
- **frontend**: React application (ports: 3000, 3001)
- **nginx**: Reverse proxy (port: 80)
- **worker**: Celery worker for async tasks
- **beat**: Celery beat for scheduled tasks

#### Container Features
- **Health Checks**: All services have comprehensive health monitoring
- **Hot Reload**: Volume mounting for development
- **Environment Isolation**: Separate configurations for dev/prod
- **Multi-stage Builds**: Optimized Docker images

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
- **Coverage Target**: 29.0% baseline (Unit: 85%, Integration: 12%, E2E: 2%, Performance: 1%)
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

### Running Tests
```bash
# ✅ Correct: Always use Makefile commands (ensures CI consistency)
make test.unit          # Unit tests only
make test.integration   # Integration tests only
make test.all           # All tests with full reporting
make coverage           # Generate coverage report

# ❌ Wrong: Never run pytest directly on individual files
pytest tests/unit/specific.py  # This causes environment inconsistency

# Advanced testing (use with caution)
pytest tests/unit/test_specific.py::test_function -v     # Only for debugging
pytest tests/unit/ -k "test_keyword" -v                   # Keyword filtering
pytest tests/unit/ -m "unit and not slow" -v              # Marker filtering
pytest tests/unit/ --maxfail=3 -x                         # Fast failure
pytest tests/ -n auto                                     # Parallel execution
pytest --cov=src --cov-report=html --cov-report=term-missing  # Coverage
```

### Critical Testing Rules
- **Environment Consistency**: Always use Makefile commands to ensure CI/localhost consistency
- **Isolation**: Each test must be independent and not rely on other tests' state
- **Async Testing**: All async functions must use proper pytest-asyncio patterns
- **Database Tests**: Use transaction rollback or test databases to avoid data pollution
- **External APIs**: Mock external API calls in unit tests, use integration tests for real API testing

### Test Configuration
- **Async Mode**: `asyncio_mode = "auto"` for automatic async detection
- **Test Paths**: `tests/` directory with recursive discovery
- **Coverage Source**: `src/` directory
- **Log Level**: INFO with structured logging format
- **Timeout**: 10-second test duration reporting

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

## CI/CD Pipeline & Validation

### GitHub Actions Integration
- **Smart CI System**: Automated CI pipeline with Python 3.10/3.11/3.12 matrix testing
- **Local CI Simulation**: `./ci-verify.sh` - Complete local CI validation before commits
- **Multi-environment Support**: Development, staging, and production deployment configurations
- **Automated Recovery**: Smart CI with automatic test failure detection and recovery suggestions

### Pre-commit Workflow
```bash
# Standard development sequence
make env-check      # Verify environment health
make context        # Load project context and dependencies
make dev           # Start development environment
make test          # Run test suite (385 tests)
make ci            # Run complete quality validation
make prepush       # Final validation before commit
```

### Docker Compose Environments
The project includes **10 specialized Docker Compose configurations**:
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production deployment
- `docker-compose.staging.yml` - Staging environment
- `docker-compose.microservices.yml` - Microservices architecture
- `docker-compose.full-test.yml` - Comprehensive testing environment
- `docker-compose.optimized.yml` - Performance-optimized configuration

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
- **Code Coverage**: Maintain 29.0% baseline coverage with continuous improvement
- **Security**: Regular security audits and dependency scanning
- **Performance**: Monitor and optimize API response times
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
2. Write code following DDD + CQRS patterns
3. Quality validation: `make lint && make test`
4. Security check: `make security-check`
5. Pre-commit: `make fix-code && make format`

### Monitoring & Observability Stack
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization dashboards and alerts
- **InfluxDB**: Time-series database for production metrics
- **Loki**: Log aggregation and analysis
- **Alert Manager**: Intelligent alerting with multi-channel notifications

### Data Collection Architecture
- **Multi-Source Collectors**: `src/collectors/` - Specialized data采集器
- **Async HTTP Processing**: `curl_cffi` for high-performance async requests
- **Data Adapters**: `src/adapters/` - Unified data interface layer
- **Quality Assurance**: `src/data/quality/` - Advanced anomaly detection and data validation

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. All I/O operations must be async, maintain DDD layer separation, and follow established patterns.