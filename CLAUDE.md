# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📋 Latest Updates (2025-12-04)

### v2.1.0 Improvements Applied
- **Updated Quality Metrics**: Real coverage increased from 6.5% to 29.0% (target achieved)
- **Enhanced FotMob Guidelines**: Added critical HTTP-only policy and authentication requirements
- **Database Interface Clarification**: Stronger emphasis on async_manager.py usage
- **Critical Development Rules**: Added non-negotiable protocol section
- **Architecture Pattern Updates**: Refined DDD+CQRS+Event-Driven guidance

## 📑 Table of Contents

- [🌟 Quick Start](#-quick-start)
- [🎯 Project Overview](#-project-overview)
- [🏗️ Architecture](#-architecture)
- [🚀 Core Development Commands](#-core-development-commands)
- [🧪 Testing Strategy](#-testing-strategy)
- [🔧 Development Workflow](#-development-workflow)
- [📋 Common Tasks](#-common-tasks)
- [🛠️ Architecture Principles](️-architecture-principles)
- [🤖 Machine Learning](#-machine-learning)
- [📊 API Endpoints](#-api-endpoints)
- [🐳 Container Architecture](#-container-architecture)
- [🔍 Code Navigation](#-code-navigation)
- [🚨 Troubleshooting](#-troubleshooting)

---

## 🌟 Quick Start (3 Minutes)

> **💡 Language**: Use Simplified Chinese for user communication

```bash
# 1️⃣ 启动完整开发环境
make dev && make status

# 2️⃣ 验证环境 (必须执行)
curl http://localhost:8000/health && make test.fast

# 3️⃣ 开始开发
make shell  # 进入容器开始编码
```

## 🎯 Project Overview

**FootballPrediction** is an enterprise-grade football prediction system based on modern async architecture, integrating machine learning, data collection, real-time prediction, and event-driven architecture.

### Quality Baseline (v2.1.0)
| Metric | Current Status | Target |
|--------|---------------|--------|
| Build Status | ✅ Stable (Green Baseline) | Maintain |
| Test Coverage | 29.0% (README.md measured) | 18%+ (Achieved) |
| Test Files | 250+ test files | 300+ |
| Code Quality | A+ (ruff) | Maintain |
| Python Version | 3.10/3.11/3.12 | Recommend 3.11 |
| Security Status | ✅ Bandit Passed | Continuous Monitoring |
| CI Environment | GitHub Actions + Docker | Consistent Local/CI |

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
- **pytest 8.0.0+** - Testing framework with async support
- **Ruff** - Code checking and formatting (A+ grade)
- **Bandit** - Security scanning
- **Docker** - Containerized deployment with Playwright
- **Makefile** - 613-line standardized development toolchain

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

### Data Collection Commands
```bash
make run-l1           # L1: Fixtures data collection from FotMob
make run-l2           # L2: Match details collection from FotMob
python scripts/backfill_details_fotmob_v2.py  # Primary FotMob data engine
python scripts/refresh_fotmob_tokens.py       # Update API authentication tokens
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
make test-quality     # Advanced quality checks
make monitor-all      # Monitor all containers
make prod-rebuild     # Production rebuild
```

### Environment Configuration

#### .env File Configuration
Use `.env.example` as template:
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
FOTMOB_CLIENT_VERSION=production:208a8f87c2cc13343f1dd8671471cf5a039dced3
FOTMOB_KNOWN_SIGNATURE=eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9hdWRpby1tYXRjaGVzIiwiY29kZSI6MTc2NDA1NTcxMjgyOCwiZm9vIjoicHJvZHVjdGlvbjoyMDhhOGY4N2MyY2MxMzM0M2YxZGQ4NjcxNDcxY2Y1YTAzOWRjZWQzIn0sInNpZ25hdHVyZSI6IkMyMkI0MUQ5Njk2NUJBREM1NjMyNzcwRDgyNzVFRTQ4In0=

# ML model configuration
ML_MODEL_PATH=/app/models
MLFLOW_TRACKING_URI=http://localhost:5000

# ML Mode Configuration (Critical for Development)
FOOTBALL_PREDICTION_ML_MODE=real|mock          # Set to 'mock' in CI/development
INFERENCE_SERVICE_MOCK=true|false              # Mock ML inference service
SKIP_ML_MODEL_LOADING=true|false               # Skip model loading for faster tests
XGBOOST_MOCK=true|false                        # Mock XGBoost models
JOBLIB_MOCK=true|false                         # Mock joblib loading

# Monitoring configuration
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=false

# Available environment files:
# .env.example - Template (copy to .env)
# .env.docker - Docker-specific configuration
# .env.ci - CI environment variables (auto-generated)
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
1. **Use unified interface**: `src/database/async_manager.py` - **"One Way to do it"** principle
2. **Create new models**: Add SQLAlchemy model classes in `src/database/models/`
3. **Apply migrations**: `make db-migrate`
4. **View table structure**: `make db-shell` → `\d table_name`
5. **Reset database** (dev environment): `make db-reset`

> ⚠️ **Critical**: Always use `src/database/async_manager.py` - `src/database/connection.py` is deprecated

### Async Database Pattern Examples
```python
# ✅ Correct: Use unified async manager
from src.database.async_manager import get_db_session

# FastAPI dependency injection
async def get_matches(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(Match))
    return result.scalars().all()

# Context manager usage
async with get_db_session() as session:
    # Database operations here
    await session.commit()
```

### Local CI Verification
```bash
make ci               # Complete local CI verification (checks coverage >= 6.0%)
./scripts/run_tests_in_docker.sh  # Run tests in Docker for isolation
```

### ⚠️ Important: Coverage Information
- **Current Coverage**: 29.0% total (README.md measured)
- **Monthly Target**: 18.0% (✅ Achieved)
- **Domain Coverage**: Improved from 0.0% baseline
- **Utils Coverage**: 73.0% (strong foundation)
- **Quality Gates**: Minimum 6.0% total coverage enforced
- **Use `make ci`** for complete local verification before pushing

### Container Development Workflow
```bash
# Start development environment
make dev              # Recommended: uses docker-compose.yml
# OR: docker-compose up --build

# Choose specific environment:
# docker-compose.yml              - Standard development
# docker-compose.dev.yml          - Extended development
# docker-compose.ci.yml           - CI environment
# docker-compose.ci.simple.yml    - Simplified CI
# docker-compose.prod.yml         - Production
# docker-compose.lightweight.yml  - Minimal setup
# docker-compose.crawler.yml      - Web scraping focused

# Check service status
docker-compose ps
make status           # Makefile equivalent

# View logs for specific services
docker-compose logs app      # Application logs
docker-compose logs db       # Database logs
docker-compose logs redis    # Redis logs
make logs                    # Makefile equivalent

# Execute commands in containers
docker-compose exec app bash # Enter app container
docker-compose exec db psql -U postgres # Connect to database
make shell                   # Makefile equivalent
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
@pytest.mark.skip_ci       # Skip these tests in CI environment
@pytest.mark.unstable      # Known flaky tests (run separately)
@pytest.mark.slow          # Time-intensive tests (>10 seconds)
```

### Test Environment Configuration
```bash
# Development testing (default)
make test.fast        # Core functionality only
make test.unit        # All unit tests

# CI Environment Testing (Required for CI)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true
export XGBOOST_MOCK=true
make test.unit.ci     # Minimal verification for CI (fastest, no ML models)

# Local testing with real ML models
export FOOTBALL_PREDICTION_ML_MODE=real
export SKIP_ML_MODEL_LOADING=false
export INFERENCE_SERVICE_MOCK=false
make test.integration # Full integration with real models

# Quick development without ML dependency
export FOOTBALL_PREDICTION_ML_MODE=mock
make test.fast        # Skip ML model loading for faster development
```

### Quality Gates Configuration
The project enforces quality gates via `config/quality_baseline.json`:

```json
{
  "quality_gates": {
    "minimum_total_coverage": 6.0,
    "minimum_utils_coverage": 70.0,
    "minimum_pass_rate": 100.0,
    "maximum_regression": 0.5
  },
  "protection_rules": {
    "pre_commit_checks": [
      "syntax_check",
      "type_check",
      "unit_tests",
      "coverage_check"
    ]
  }
}
```

## 🔧 Core Development Workflow

### Daily Development Process
```bash
# 1. Start environment and verify services
make dev && make status

# 2. Verify API accessibility
curl http://localhost:8000/health

# 3. Run core tests to ensure environment is normal
make test.fast

# 4. During development
make lint && make fix-code  # Code quality check and fix

# 5. Pre-commit verification (must execute)
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
make test.unit.ci     # Minimal CI verification (fastest)
make security-check   # Security check

# 6. Optional: Full verification if time permits
make ci               # Complete CI verification including coverage
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
1. Create collector class: `src/collectors/`
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
```bash
# 1. View application logs
make logs              # All service logs
make logs-app          # Application logs only
make logs-db           # Database logs only
make logs-redis        # Redis logs only

# 2. Check service health
curl http://localhost:8000/health              # Basic health check
curl http://localhost:8000/health/system       # System resources
curl http://localhost:8000/health/database     # Database connectivity

# 3. Monitor metrics and performance
curl http://localhost:8000/api/v1/metrics       # Prometheus metrics
http://localhost:8000/docs                      # API documentation

# 4. Check background tasks
http://localhost:5555                           # Flower dashboard (Celery tasks)

# 5. Database diagnosis
make db-shell                                   # PostgreSQL terminal
\dt                                            # List all tables
SELECT COUNT(*) FROM matches;                   # Check data volume

# 6. Cache and queue inspection
make redis-shell                                 # Redis CLI
KEYS *                                          # View all keys
INFO memory                                     # Memory usage
```

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

# Hyperparameter optimization with Optuna
python src/ml/xgboost_hyperparameter_optimization.py

# Advanced hyperparameter tuning
python scripts/tune_model_optuna.py

# Complete prediction pipeline
python src/ml/football_prediction_pipeline.py

# Prepare final model data
python src/models/train_v1_final.py

# MLflow experiment tracking
mlflow ui  # Start MLflow UI at http://localhost:5000
mlflow experiments list  # List all experiments
```

### Data Collection System

#### ⚠️ FotMob HTTP-Only Policy (Critical)
**Strict prohibition of Playwright/browser automation** - All data collection uses HTTP requests only:

```bash
# FotMob data collection (HTTP-based, no browser automation)
python scripts/backfill_details_fotmob_v2.py      # Primary FotMob engine
python scripts/refresh_fotmob_tokens.py           # Update authentication tokens

# L1-L3 Data Pipeline (Makefile commands)
make run-l1              # L1: Fixtures data collection
make run-l2              # L2: Match details collection

# Token management for FotMob API (IMPORTANT!)
python scripts/manual_token_test.py               # Test API authentication
python scripts/explore_fotmob_urls.py             # Explore API endpoints

# Integrate to database via ETL API
curl -X POST http://localhost:8000/api/v1/data/etl \
  -H "Content-Type: application/json" \
  -d '{"source": "fotmob", "action": "import"}'
```

#### FotMob Authentication Requirements (Critical)
FotMob requires specific headers for API access. **Missing these headers will result in 403 errors**:

- **x-mas**: Authentication token (from .env.example)
- **x-foo**: Request signature (from .env.example)
- **User-Agent**: Proper browser headers (automatically rotated)

**获取认证信息**：
1. 从 `.env.example` 复制 `FOTMOB_CLIENT_VERSION` 和 `FOTMOB_KNOWN_SIGNATURE`
2. 运行 `python scripts/manual_token_test.py` 验证认证
3. 如需更新token，运行 `python scripts/refresh_fotmob_tokens.py`

#### Rate Limiting & Anti-Scraping
- **Rate Limiter**: `src/collectors/rate_limiter.py` - Adaptive delay strategies
- **Proxy Pool**: `src/collectors/proxy_pool.py` - Rotating proxy management
- **User-Agent Rotation**: `src/collectors/user_agent.py` - Mobile/desktop mixing

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

## 🚨 Troubleshooting Quick Reference

| Issue Type | Solution |
|-----------|----------|
| **Test Failures** | `make test.fast` check core functionality, avoid ML model loading |
| **CI Timeout** | Use `make test.unit.ci` instead of full test suite |
| **Port Conflicts** | `lsof -i :8000` to check, then `kill -9 PID` or change ports |
| **Database Issues** | `make db-migrate`, check PostgreSQL status with `make status` |
| **Redis Connection Issues** | `make redis-shell` test connection, check if Redis is running |
| **Insufficient Memory** | Use `make test.fast` to avoid ML-related tests |
| **Type Errors** | Check imports, add missing type annotations, run `make type-check` |
| **Dependency Issues** | Run `make clean-all && make dev` to rebuild from scratch |
| **ML Model Loading Failed** | Check model file paths in `models/trained/`, verify MLflow registry |
| **Celery Task Failures** | View logs `make logs`, check Redis connection, use Flower UI |
| **Coverage < 6.0%** | Run `make coverage` to see specific coverage gaps |
| **Docker Build Failures** | Check `Dockerfile`, verify all dependencies in requirements*.txt |
| **FotMob 403 Errors** | Check `.env` for FOTMOB_CLIENT_VERSION and FOTMOB_KNOWN_SIGNATURE |
| **Container Permission Issues** | Use `sudo chown -R $USER:$USER ./` for local file permissions |

### 常见问题详细解决方案

#### 🔥 FotMob API 认证失败 (403 Error)
```bash
# 1. 验证认证配置
python scripts/manual_token_test.py

# 2. 更新认证token
python scripts/refresh_fotmob_tokens.py

# 3. 检查环境变量
cat .env | grep FOTMOB
```

#### 🐳 Docker 端口冲突
```bash
# 查看端口占用
lsof -i :8000  # Backend API
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 强制结束占用进程
kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口映射
```

#### 🧠 ML 模型加载问题
```bash
# 检查模型文件
ls -la models/trained/

# 检查 MLflow 实验记录
mlflow experiments list

# 重新训练模型
python src/ml/enhanced_xgboost_trainer.py
```

## 💡 Important Reminders

1. **Test Golden Rule** - Always use Makefile commands, never run pytest directly
2. **Async First** - All I/O operations must use async/await pattern
3. **Architectural Integrity** - Strictly follow DDD+CQRS+Event-Driven architecture
4. **Environment Consistency** - Use Docker to ensure local and CI environments match
5. **Service Health** - Run `make status` to check all services before development
6. **AI-First Maintenance** - Project uses AI-assisted development, prioritize architectural integrity and code quality
7. **ML Model Management** - All ML-related code is in `src/ml/` directory, use MLflow for version control
8. **Coverage Requirement** - Maintain minimum 6.0% test coverage for CI to pass (config/quality_baseline.json)
9. **Security First** - Run `make security-check` before committing changes
10. **Celery Task Management** - Use Flower UI at http://localhost:5555 to monitor background tasks
11. **FotMob Authentication** - Always verify x-mas and x-foo headers before data collection

---

## 🔑 Critical Development Rules

### 1. FotMob Data Collection (Critical)
- **🚫 NEVER use Playwright or browser automation** - HTTP requests only
- **✅ Always use rate limiting** - `src/collectors/rate_limiter.py`
- **🔐 Proper authentication required** - x-mas and x-foo headers mandatory
- **🔄 Rotate User-Agents** - Mix mobile/desktop patterns

### 2. Database Operations (Mandatory)
- **📌 Always use `src/database/async_manager.py`** - "One Way to do it" principle
- **🚫 NEVER use `src/database/connection.py`** - Deprecated interface
- **⚡ All operations must be async** - Use `async/await` consistently
- **🔒 Use proper session management** - Context managers or dependency injection

### 3. Testing Protocol (Non-negotiable)
- **🛡️ ALWAYS use Makefile commands** - Never pytest directly on files
- **🎯 Mock all external dependencies** - Database, network, filesystem
- **📊 Maintain 6.0%+ coverage** - CI will fail below this threshold
- **⚡ Use mock ML mode in CI** - Set `FOOTBALL_PREDICTION_ML_MODE=mock`

### 4. Architecture Integrity (Enterprise Standards)
- **🏗️ Follow DDD patterns** - Domain layer purity essential
- **📡 Implement CQRS separation** - Commands vs queries distinct
- **🔄 Event-driven communication** - Use event system for loose coupling
- **🎯 Type safety mandatory** - Complete type annotations required

**💡 Remember**: This is an enterprise-grade project with AI-first maintenance. Violating these critical rules will break the system's architectural integrity and quality standards.