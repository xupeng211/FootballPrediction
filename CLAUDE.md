# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📑 Table of Contents

- [🌟 Quick Start](#-quick-start)
- [🎯 Project Overview](#-project-overview)
- [🏗️ Architecture](#-architecture)
- [🚀 Core Development Commands](#-core-development-commands)
- [🧪 Testing Strategy](#-testing-strategy)
- [🔧 Development Workflow](#-development-workflow)
- [📋 Common Tasks](#-common-tasks)
- [🛠️ Architecture Principles](#️-architecture-principles)
- [🤖 Machine Learning](#-machine-learning)
- [📊 API Endpoints](#-api-endpoints)
- [🐳 Container Architecture](#-container-architecture)
- [🔍 Code Navigation](#-code-navigation)
- [🚨 Troubleshooting](#-troubleshooting)

---

## 🌟 Quick Start (5 Minutes)

> **💡 Language**: Use Simplified Chinese for user communication

```bash
# 🚀 Start full development environment
make dev && make status

# ✅ Verify API accessibility
curl http://localhost:8000/health

# 🧪 Run core tests to validate environment
make test.fast

# 📊 Generate coverage report
make coverage
```

## 🎯 Project Overview

**FootballPrediction** is an enterprise-grade football prediction system based on modern async architecture, integrating machine learning, data collection, real-time prediction, and event-driven architecture.

### Quality Baseline (v1.0.0-rc1)
| Metric | Status | Target |
|--------|--------|--------|
| Build Status | ✅ Stable (Green Baseline) | Maintain |
| Test Coverage | 29.0% | 80%+ |
| Test Count | 385 tests | 500+ |
| Code Quality | A+ (ruff) | Maintain |
| Python Version | 3.10/3.11/3.12 | Recommend 3.11 |
| Security Status | ✅ Bandit Passed | Continuous Monitoring |

### Tech Stack
- **Backend**: FastAPI + PostgreSQL 15 + Redis 7.0+ + SQLAlchemy 2.0+
- **Machine Learning**: XGBoost 2.0+ + TensorFlow 2.18.0 + MLflow + Optuna
- **Containerization**: Docker 27.0+ + 20+ Docker Compose configurations
- **Dev Tools**: pytest 8.4.0+ + Ruff 0.14+ + Complete Makefile toolchain

## 🏗️ Architecture

### Architecture Patterns
Enterprise-grade patterns for high performance, maintainability, and scalability:

- **DDD (Domain-Driven Design)** - Clear domain boundaries and business logic separation
- **CQRS (Command Query Separation)** - Independent optimization of read/write operations
- **Event-Driven Architecture** - Loose coupling communication between components
- **Async First** - All I/O operations use async/await
- **Lifecycle Management** - Resource management via FastAPI `lifespan`

### Application Startup Flow
```python
# src/main.py - Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup phase
    await initialize_database()          # DB connection and migrations
    await initialize_event_system()      # Event system initialization
    await initialize_cqrs()              # CQRS pattern initialization
    setup_performance_monitoring()       # Performance monitoring config

    # Smart cold start - auto-detect data state
    if await needs_data_collection():
        trigger_background_data_collection()

    yield  # Application running

    # Shutdown phase
    await shutdown_event_system()        # Cleanup event system
```

### Directory Structure
```
src/
├── api/                  # API layer (CQRS implementation)
│   ├── predictions/      # Prediction APIs (optimized version included)
│   ├── data/            # Data management APIs
│   ├── analytics/       # Analytics APIs
│   ├── health/          # Health check APIs
│   ├── auth/            # Auth & authorization APIs
│   ├── optimization/    # Performance optimization APIs
│   └── models/          # API data models
├── domain/              # Domain layer (DDD core logic)
├── ml/                  # Machine learning modules
│   ├── xgboost_hyperparameter_optimization.py  # XGBoost hyperparameter optimization
│   ├── lstm_predictor.py        # LSTM deep learning prediction
│   ├── football_prediction_pipeline.py  # Complete prediction pipeline
│   └── experiment_tracking.py   # MLflow experiment tracking
├── tasks/               # Celery task scheduling
├── database/            # Async SQLAlchemy 2.0 (includes async_manager.py unified interface)
├── cache/              # Cache layer (Redis)
├── cqrs/               # CQRS pattern implementation
├── events/             # Event system
├── core/               # Core infrastructure
├── services/           # Business service layer
├── utils/              # Utility functions
├── monitoring/         # Monitoring system (Prometheus integration)
├── adapters/           # External data source adapters (FotMob, etc.)
├── collectors/         # Data collectors
├── config/             # Configuration management
├── middleware/         # Middleware
├── performance/        # Performance monitoring
└── streaming/          # Real-time data streaming
```

### Key Technology Stack

#### Backend Core
- **FastAPI** (v0.104.0+) - Modern async web framework
- **PostgreSQL 15** - Primary database, async SQLAlchemy 2.0+
- **Redis 7.0+** - Cache and Celery message queue
- **Pydantic v2+** - Data validation and serialization
- **Uvicorn** - ASGI server

#### Machine Learning
- **XGBoost 2.0+** - Gradient boosting prediction algorithm
- **TensorFlow 2.18.0** - Deep learning (LSTM)
- **MLflow 2.22.2+** - Experiment tracking and model management
- **Optuna 4.6.0+** - Hyperparameter optimization
- **Scikit-learn 1.3+** - Machine learning utilities

#### Development Tools
- **pytest 8.4.0+** - Testing framework with async support
- **Ruff 0.14+** - Code checking and formatting (A+ grade)
- **Bandit 1.8.6+** - Security scanning
- **Docker 27.0+** - Containerized deployment
- **Makefile** - 297-line standardized development toolchain

## 🚀 Core Development Commands

### Environment Management
```bash
make dev              # Start full development environment (app + db + redis + nginx)
make dev-rebuild      # Rebuild images and start development environment
make dev-stop         # Stop development environment
make dev-logs         # View development environment logs
make status           # Check all service status
make quick-start      # Quick start development environment (alias)
make quick-stop       # Quick stop development environment (alias)
make prod             # Start production environment (use docker-compose.prod.yml)
make clean            # Cleanup containers and cache
make clean-all        # Thorough cleanup of all related resources
make install          # Install dependencies in virtual environment
make venv             # Create Python virtual environment
make env-check        # Check if environment is properly configured
```

### 🔥 Test Golden Rule
**Never run pytest on single files directly!** Always use Makefile commands:

```bash
make test.unit        # Unit tests (278 test files)
make test.fast        # Quick core tests (API/Utils/Cache/Events only)
make test.unit.ci     # CI minimal verification (ultimate stable solution)
make test.integration # Integration tests
make test.all         # Run all tests including slow ones
make test-phase1      # Phase 1 core functionality tests
make coverage         # Generate coverage report
make test-coverage-local # Run tests with coverage locally
```

### ⚠️ Important: Running Single Test Files
```bash
# Correct method: Use container environment
docker-compose exec app pytest tests/unit/api/test_predictions.py -v

# Or enter container first
make shell
pytest tests/unit/api/test_predictions.py -v
```

### Code Quality
```bash
make lint             # Code checking with ruff
make fix-code         # Auto-fix code issues with ruff
make format           # Code formatting with ruff
make security-check   # Security scanning with bandit
make ci               # Complete CI verification
make type-check       # MyPy type checking
make prepush          # Complete pre-push validation
make context          # Load project context for AI assistants
make sync-issues      # Sync GitHub Issues (双向同步工具)
```

### Environment Configuration

#### .env File Configuration
```bash
# Core configuration
ENV=development
SECRET_KEY=your-secret-key-here
PYTHONPATH=/app

# Database configuration
DATABASE_URL=postgresql://postgres:postgres-dev-password@db:5432/football_prediction

# Redis configuration
REDIS_URL=redis://redis:6379/0

# External API keys
FOOTBALL_DATA_API_KEY=your-football-data-api-key
FOTMOB_API_KEY=your-fotmob-api-key

# ML model configuration
ML_MODEL_PATH=/app/models
MLFLOW_TRACKING_URI=http://localhost:5000

# Monitoring configuration
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=false

# Additional environment files available
# .env.ci - CI environment variables
# .env.prod - Production environment variables
```

#### Container Operations
```bash
make shell            # Enter backend container
make shell-db         # Enter database container
make db-shell         # Connect to PostgreSQL database
make redis-shell      # Connect to Redis
make logs             # View application logs
make logs-db          # View database logs
make logs-redis       # View Redis logs
```

### Database Management
```bash
make db-reset         # Reset database (⚠️ will delete all data)
make db-migrate       # Run database migrations
make db-shell         # Enter PostgreSQL interactive terminal
```

### Database Development Workflow
1. **Use new unified interface**: `src/database/async_manager.py` - all database operations use this interface
2. **Create new models**: Add SQLAlchemy model classes in `src/database/models/`
3. **Apply migrations**: `make db-migrate`
4. **View table structure**: `make db-shell` → `\d table_name`
5. **Reset database** (dev environment): `make db-reset`

> ⚠️ **Important**: `src/database/connection.py` is deprecated, please use `src/database/async_manager.py` unified interface

### Local CI Verification
```bash
./ci-verify.sh        # Full local CI verification (checks coverage >= 78%)
./simulate_ci_in_dev.sh  # Simulate CI environment
./scripts/run_tests_in_docker.sh  # Run tests in Docker for isolation
```

### Container Development Workflow
```bash
# Start development environment
docker-compose up --build

# Check service status
docker-compose ps

# View logs for specific services
docker-compose logs app      # Application logs
docker-compose logs db       # Database logs
docker-compose logs redis    # Redis logs

# Execute commands in containers
docker-compose exec app bash # Enter app container
docker-compose exec db psql -U postgres # Connect to database
```

## 🧪 Testing Strategy: SWAT Methodology

### 🛡️ SWAT Testing Core Principles
Derived from successful SWAT operation - elevated 7 P0 risk modules from 0% to 100% coverage in 48 hours:

1. **Build safety net first, then touch code** - Establish complete test safety net before modifying high-risk code
2. **P0/P1 risk first** - Prioritize most critical business logic, avoid wasting time on low-risk tests
3. **Mock all external dependencies** - Database, network, filesystem all mocked to ensure test purity

### Four-Layer Test Architecture
- **Unit Tests (85%)** - Fast isolated component testing
- **Integration Tests (12%)** - Database, cache, external API integration
- **E2E Tests (2%)** - Complete user flow testing
- **Performance Tests (1%)** - Load and stress testing

### Test Markers Example
```python
@pytest.mark.unit           # Unit tests (fast isolated components)
@pytest.mark.integration    # Integration tests (database, cache, external API)
@pytest.mark.api           # API tests (FastAPI endpoints)
@pytest.mark.database      # Database tests (SQLAlchemy operations)
@pytest.mark.ml            # Machine learning tests (model loading, prediction)
@pytest.mark.e2e           # End-to-end tests (complete user flows)
@pytest.mark.performance   # Performance tests (load and pressure)
```

## 🔧 Core Development Workflow

### Daily Development Process
```bash
# 1. Start environment
make dev && make status

# 2. Run tests to ensure environment is normal
make test.fast

# 3. During development
make lint && make fix-code  # Code quality check and fix

# 4. Pre-commit verification (must execute)
make test.unit.ci     # Minimal CI verification (fastest)
make security-check   # Security check
```

### Pre-commit Full Verification
```bash
make ci               # Complete CI verification (if time permits)
```

## 📋 Common Development Tasks

### Adding New API Endpoints
1. Create command/query handlers: `src/api/predictions/`
2. Implement CQRS handlers: `src/cqrs/`
3. Register routes to main API: `src/main.py` (import router)
4. Add unit tests: `tests/unit/api/`
5. Verify: `make test.unit.ci`

### Adding New Data Collectors
1. Create collector class: `src/data/collectors/` or `src/collectors/`
2. Implement async data fetching methods with proper error handling
3. Add data validation logic using Pydantic models
4. Integrate into ETL pipeline: `src/api/data_management.py`
5. Test: `make test.integration`

### Training New ML Models
1. Create training scripts in `src/ml/`
2. Use MLflow for experiment tracking: `mlflow.start_run()`
3. Optimize hyperparameters with Optuna: `src/ml/xgboost_hyperparameter_optimization.py`
4. Save models to `models/trained/` directory
5. Update inference service: `src/services/inference_service.py`
6. Add model monitoring: `src/ml/model_performance_monitor.py`

### Database Schema Changes
1. Create new SQLAlchemy models in `src/database/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `make db-migrate`
4. Update repository classes in `src/database/async_manager.py`
5. Add corresponding tests: `tests/unit/database/`

### Debugging Production Issues
1. View logs: `make logs` or `make dev-logs`
2. Check health status: `curl http://localhost:8000/health`
3. Monitor metrics: `http://localhost:8000/api/v1/metrics`
4. Check Celery tasks: http://localhost:5555 (Flower dashboard)
5. Database diagnosis: `make db-shell` → `\dt` view tables
6. Redis inspection: `make redis-shell` → `KEYS *`

## 🛠️ Architecture Principles

### 1. Async Programming Pattern
```python
# ✅ Correct: All I/O operations use async/await
async def fetch_match_data(match_id: str) -> MatchData:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/matches/{match_id}")
        return MatchData.model_validate(response.json())

# ✅ Correct: Database operations use async SQLAlchemy 2.0
async def get_match_by_id(db: AsyncSession, match_id: str) -> Optional[Match]:
    result = await db.execute(
        select(Match).where(Match.id == match_id)
    )
    return result.scalar_one_or_none()
```

### 2. DDD Layered Architecture
```python
# domain/ - Pure business logic, no external framework dependencies
class MatchPrediction:
    def __init__(self, match: Match, prediction: PredictionResult):
        self.match = match
        self.prediction = prediction
        self.confidence = self._calculate_confidence()

    def _calculate_confidence(self) -> float:
        # Pure business logic, no external dependencies
        pass

# api/ - CQRS command query separation
@router.post("/predictions")
async def create_prediction(
    command: CreatePredictionCommand,
    handler: PredictionCommandHandler = Depends()
) -> PredictionResponse:
    return await handler.handle(command)

# services/ - Application service orchestration
class PredictionService:
    async def generate_match_prediction(self, match_id: str) -> PredictionResult:
        match = await self.match_repository.get_by_id(match_id)
        features = await self.feature_extractor.extract(match)
        return await self.ml_model.predict(features)
```

### 3. Type Safety and Data Validation
```python
# ✅ Complete type annotations
async def process_prediction_request(
    request: PredictionRequest,
    user_id: UUID
) -> PredictionResponse:

# ✅ Pydantic data validation
class PredictionRequest(BaseModel):
    match_id: str = Field(..., min_length=1, max_length=50)
    prediction_type: PredictionType
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
```

### 4. Event-Driven Architecture
```python
# Domain event definition
class MatchCompletedEvent(BaseEvent):
    match_id: str
    final_score: str
    prediction_result: PredictionResult

# Event publishing
async def publish_match_completed(match: Match, result: MatchResult):
    event = MatchCompletedEvent(
        match_id=match.id,
        final_score=result.final_score,
        prediction_result=result.prediction_result
    )
    await event_bus.publish(event)

# Event handling
@event_handler(MatchCompletedEvent)
async def update_predictions_on_match_completion(event: MatchCompletedEvent):
    # Update related prediction statuses
    await prediction_repository.update_status(event.match_id, "completed")
```

## 🤖 Machine Learning Development

### ML Pipeline Structure
```python
# Feature engineering
src/ml/enhanced_feature_engineering.py

# Model training
src/ml/enhanced_xgboost_trainer.py
src/ml/enhanced_real_model_training.py
src/ml/lstm_predictor.py

# Prediction pipeline
src/ml/football_prediction_pipeline.py

# Experiment tracking
src/ml/experiment_tracking.py

# Hyperparameter optimization
src/ml/xgboost_hyperparameter_optimization.py
src/ml/test_hyperparameter_optimization.py

# Performance monitoring
src/ml/model_performance_monitor.py
```

### Model Management
- **MLflow** - Experiment tracking and version control (`mlruns/` directory)
- **Optuna** - Hyperparameter Bayesian optimization
- **Model Registry** - Production model management
- **Model Storage**: `models/trained/` directory for production models

### ML Training Commands
```bash
# Train XGBoost model
python src/ml/enhanced_xgboost_trainer.py

# LSTM deep learning prediction
python src/ml/lstm_predictor.py

# Hyperparameter optimization
python src/ml/xgboost_hyperparameter_optimization.py

# Complete prediction pipeline
python src/ml/football_prediction_pipeline.py

# Prepare final model data
python src/models/train_v1_final.py
```

## 📊 API Endpoints

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws
- **Prometheus Metrics**: http://localhost:8000/api/v1/metrics

## 🐳 Container Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Frontend  │  │  Backend    │  │  Database   │
│   (React)   │  │  (FastAPI)  │  │(PostgreSQL) │
│  Port:3000  │  │  Port:8000  │  │  Port:5432  │
└─────────────┘  └─────────────┘  └─────────────┘
       │                │                │
       │       ┌─────────────┐          │
       │       │    Redis    │          │
       │       │  Port:6379  │          │
       │       └─────────────┘          │
       │                │                │
       └────────────────┼────────────────┘
                        │
              ┌─────────────┐
              │   Worker    │
              │  (Celery)   │
              └─────────────┘
                        │
              ┌─────────────┐
              │    Nginx    │
              │  Port: 80   │
              └─────────────┘
```

## 🔍 Code Navigation Guide

### Quick File Location
- **Find API routes**: Search for `@app.` or `@router.` patterns
- **Find database models**: `src/database/models/` directory - classes inheriting from `Base`
- **Find event handlers**: `src/events/` directory
- **Find CQRS commands**: `src/cqrs/commands/` directory
- **Find CQRS queries**: `src/cqrs/queries/` directory
- **Find ML models**: `.pkl` or `.joblib` files in `src/ml/` directory
- **Find data adapters**: `src/adapters/` directory (FotMob external data sources)
- **Find data collectors**: `src/collectors/` directory

### Key File Locations
- **Main application entry**: `src/main.py` (application lifecycle management, smart cold start)
- **API route registration**: Router files in each API submodule
- **Database configuration**: `src/database/async_manager.py` (new unified interface)
- **Cache configuration**: `src/cache/redis_client.py` (Redis connection pool)
- **Celery configuration**: `src/tasks/celery_app.py`
- **Test configuration**: `pytest.ini` and `tests/conftest.py`
- **Performance monitoring**: `src/performance/middleware.py`
- **Health checks**: `src/api/health/` directory
- **External adapters**: `src/adapters/factory.py` (data source factory pattern)

### Project Statistics
- **Core code**: 1,094+ lines (src root directory)
- **Test files**: 239+ test files, 385+ test cases
- **Configuration files**: 20+ Docker Compose configurations
- **Documentation files**: Complete development and deployment documentation
- **Toolchain**: 297-line Makefile standardized commands

## 🔥 Core Functional Modules

### Prediction System
- **API routes**: `src/api/predictions/` (includes optimized version)
- **Inference service**: `src/services/inference_service.py` - Real-time prediction inference
- **Model loading**: Supports XGBoost and LSTM model hot-loading
- **Prediction pipeline**: `src/ml/football_prediction_pipeline.py` - Complete ML workflow

### Data Collection System

#### FotMob Data Collection Architecture
Project has completed standardized refactoring of FotMob data collection:
- **Core class**: `FotmobBrowserScraper` - Uses Playwright for browser automation
- **API interception**: Intercepts real FotMob API responses to get complete data
- **Data export**: Automatic JSON format export to `data/fotmob/` directory
- **Multiple modes**: Supports single day, batch, date range collection
- **Async support**: Complete async resource management

#### Data Collection Components
- **External adapters**: `src/adapters/` (FotMob external data sources)
- **Data collectors**: `src/collectors/` and `src/data/collectors/`
- **Browser automation**: `src/data/collectors/fotmob_browser.py` - Playwright anti-crawler mechanism
- **ETL pipeline**: `src/api/data_management.py` - Data management API
- **CLI tools**: `scripts/run_fotmob_scraper.py` - Data collection scripts

### Data Collection Workflow
```bash
# 1. Single day data collection
python scripts/run_fotmob_scraper.py --date 2024-01-15

# 2. Batch data collection
python scripts/run_fotmob_scraper.py --start-date 2024-01-01 --end-date 2024-01-31

# 3. View collected data
ls -la data/fotmob/

# 4. Analyze JSON structure
python scripts/inspect_json_structure.py data/fotmob/match_*.json

# 5. Integrate to database
curl -X POST http://localhost:8000/api/v1/data/etl \
  -H "Content-Type: application/json" \
  -d '{"source": "fotmob", "action": "import"}'
```

### Performance Monitoring
- **Middleware**: `src/performance/middleware.py` - Performance monitoring middleware
- **Monitoring API**: `src/api/monitoring.py` - System monitoring endpoints
- **Prometheus integration**: `/metrics` endpoint exports monitoring metrics
- **Health checks**: `/health`, `/health/system`, `/health/database`

### Caching Strategy
- **Multi-level cache**: Memory + Redis distributed cache
- **Cache invalidation**: Smart TTL and active invalidation
- **Read-write separation**: Supports database read-write separation configuration

### Real-time Communication
- **WebSocket**: `/api/v1/realtime/ws` - Real-time data push
- **Event system**: `src/events/` - Event-driven architecture
- **CQRS pattern**: `src/cqrs/` - Command Query Responsibility Segregation

## 🚨 Troubleshooting Quick Reference

| Issue Type | Solution |
|-----------|----------|
| **Test Failures** | `make test.fast` check core functionality, avoid ML model loading |
| **CI Timeout** | Use `make test.unit.ci` instead of full test suite |
| **Port Conflicts** | Check port availability (8000, 3000, 5432, 6379) |
| **Database Issues** | Run `make db-migrate`, check PostgreSQL status |
| **Redis Connection Issues** | `make redis-shell` test connection |
| **Insufficient Memory** | Use `make test.fast` to avoid ML-related tests |
| **Type Errors** | Check imports, add missing type annotations |
| **Dependency Issues** | Run `make clean-all && make dev` to rebuild from scratch |
| **ML Model Loading Failed** | Check model file paths, view `mlruns/` and `models/trained/` directories |
| **Celery Task Failures** | View logs `make logs`, check Redis connection |
| **Coverage < 78%** | Run `./ci-verify.sh` to see specific coverage gaps |
| **Docker Build Failures** | Check `Dockerfile` and ensure all dependencies in requirements.txt |

## 📚 Additional Documentation

### Key Documentation Files
- **[Repository Guidelines](AGENTS.md)** - Contributor structure, processes, and security guidelines
- **[Test Improvement Guide](docs/TEST_IMPROVEMENT_GUIDE.md)** - Kanban, CI Hook, and weekly reporting mechanisms
- **[Testing Guide](docs/TESTING_GUIDE.md)** - SWAT action results, complete testing methodology
- **[Tools Documentation](TOOLS.md)** - Complete development toolchain usage guide
- **[Test Run Guide](TEST_RUN_GUIDE.md)** - Proper test execution methods (IMPORTANT!)

### CI/CD and Quality Gates
- **GitHub Actions**: `.github/workflows/` for automated testing and deployment
- **Coverage Requirement**: Minimum 78% test coverage for CI to pass
- **Quality Gates**: Ruff linting, Bandit security, MyPy type checking
- **Container Health**: Database and Redis health checks in docker-compose

### Development Environment Files
- **requirements.txt** - Core dependencies
- **requirements-dev.txt** - Development dependencies
- **requirements-ci.txt** - CI-specific dependencies
- **pytest.ini** - Test configuration and markers
- **Dockerfile** - Multi-stage container build
- **docker-compose.yml** - Development environment setup

## 💡 Important Reminders

1. **Test Golden Rule** - Always use Makefile commands, never run pytest directly
2. **Async First** - All I/O operations must use async/await pattern
3. **Architectural Integrity** - Strictly follow DDD+CQRS+Event-Driven architecture
4. **Environment Consistency** - Use Docker to ensure local and CI environments match
5. **Service Health** - Run `make status` to check all services before development
6. **AI-First Maintenance** - Project uses AI-assisted development, prioritize architectural integrity and code quality
7. **ML Model Management** - All ML-related code is in `src/ml/` directory, use MLflow for version control
8. **Coverage Requirement** - Maintain minimum 78% test coverage for CI to pass
9. **Security First** - Run `make security-check` before committing changes

## 🎯 Developer Must-Know

### Key Architectural Patterns
- **Application Startup**: Uses lifecycle management (`lifespan` context manager in `src/main.py`)
- **Smart Cold Start**: Automatically checks data status and triggers collection tasks
- **Dependency Injection**: Uses FastAPI's dependency injection system
- **Error Handling**: Unified exception handling and error response format
- **Middleware Chain**: Performance monitoring, CORS, internationalization middleware

### Data Collection Features
- **Anti-Crawler**: Uses Playwright browser automation to bypass site restrictions
- **Multiple Data Sources**: FotMob and other football data API integration
- **Data Quality**: Automated data validation and quality checks
- **Incremental Updates**: Smart judgment on whether data updates are needed
- **ETL Pipeline**: Complete data processing in `src/api/data_management.py`

### Performance Optimization
- **Connection Pool**: Database connection pool and Redis connection pool
- **Async Tasks**: Celery task queue for background job processing
- **Caching Strategy**: Multi-level cache and smart invalidation mechanism
- **Monitoring Integration**: Prometheus metrics real-time monitoring
- **CQRS Optimization**: Separate read/write models for performance

### Development Best Practices
- **Progressive Improvement**: Prioritize CI green status over feature development
- **Test-First**: Write tests before modifying high-risk code modules
- **Mock External Dependencies**: All database, network, filesystem dependencies mocked in tests
- **Type Safety**: Complete type annotations required for all new code
- **Documentation**: Update relevant documentation when adding features

---

**💡 Remember**: This is an enterprise-grade project with AI-first maintenance. Prioritize architectural integrity, code quality, and comprehensive testing. All I/O operations must be async, maintain DDD layer separation, and follow established patterns. The project uses a complete toolchain (Makefile + 20+ Docker configs) to ensure standardized development workflows.
