# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📋 Latest Updates (2025-12-04)

### v2.1.0 Improvements Applied
- **Updated Quality Metrics**: Real coverage increased from 6.5% to 29.0% (target achieved)
- **Enhanced FotMob Guidelines**: Added critical HTTP-only policy and authentication requirements
- **Database Interface Clarification**: Stronger emphasis on async_manager.py usage
- **Critical Development Rules**: Added non-negotiable protocol section
- **Architecture Pattern Updates**: Refined DDD+CQRS+Event-Driven guidance

### P0-2 FeatureStore Complete (2025-12-05)
- **Production Feature Store**: Async PostgreSQL+JSONB implementation with 121.2% test coverage
- **Data Quality System**: Modern async quality monitor with protocol-based rule system
- **Feature Engineering**: Protocol-based interfaces for extensibility and maintainability
- **Enterprise-grade Storage**: 6 optimized indexes, <100ms batch operations, full async support

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

```bash
# 1️⃣ 启动完整开发环境
make dev && make status

# 2️⃣ 验证环境 (必须执行)
curl http://localhost:8000/health && make test.fast

# 3️⃣ 开始开发
make shell  # 进入容器开始编码
```

### Alternative Quick Start (For New Developers)

```bash
# Clone and initialize
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
make install      # Install dependencies
make context      # Load project context (⭐ Most Important)
make test.fast    # Verify environment (385 test cases)
```

### ✅ Verification Checklist
After running the quick start commands, verify:

```bash
# Service health check
curl http://localhost:8000/health/system       # System resources
curl http://localhost:8000/health/database     # Database connectivity
curl http://localhost:8000/api/v1/metrics       # Prometheus metrics

# Test environment verification (385+ tests should pass)
make test.fast                    # Core functionality (2-3 min)
make test.unit.ci                 # CI verification (fastest)
```

**Expected Results**:
- ✅ All services healthy (app, db, redis)
- ✅ API accessible at http://localhost:8000
- ✅ Documentation at http://localhost:8000/docs
- ✅ Test coverage: 29.0% total (target achieved)

## 🎯 Project Overview

**FootballPrediction** is an enterprise-grade football prediction system based on modern async architecture, integrating machine learning, data collection, real-time prediction, and event-driven architecture.

### Quality Baseline (v2.1.0)
| Metric | Current Status | Target |
|--------|---------------|--------|
| Build Status | ✅ Stable (Green Baseline) | Maintain |
| Test Coverage | 29.0% total (measured) | 18%+ (✅ Achieved) |
| Test Cases | 385+ passing tests | 400+ |
| Quality Gates | 6.0% minimum (enforced) | Maintain |
| Test Files | 270+ test files | 300+ |
| Code Quality | A+ (ruff) | Maintain |
| Python Version | 3.10/3.11/3.12 | Recommend 3.11 |
| Security Status | ✅ Bandit Passed | Continuous Monitoring |
| CI Environment | GitHub Actions + Docker | Consistent Local/CI |

### Project Badges
[![CI Pipeline](https://github.com/xupeng211/FootballPrediction/actions/workflows/ci_pipeline_v2.yml/badge.svg)](https://github.com/xupeng211/FootballPrediction/actions/workflows/ci_pipeline_v2.yml)
[![Test Improvement Guide](https://img.shields.io/badge/📊%20Test%20Improvement%20Guide-blue?style=flat-square)](docs/TEST_IMPROVEMENT_GUIDE.md)
[![Testing Guide](https://img.shields.io/badge/🛡️%20Testing%20Guide-green?style=flat-square)](docs/TESTING_GUIDE.md)
[![Kanban Check](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml/badge.svg)](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml)

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

### Smart Cold Start System
The application implements intelligent startup logic:

1. **Database Health Check**: Verifies PostgreSQL connectivity
2. **Migration Status**: Automatically runs pending Alembic migrations
3. **Data State Detection**: Checks if initial data collection needed
4. **Background Tasks**: Starts Celery workers for async processing
5. **Event System**: Initializes event-driven communication
6. **Performance Monitoring**: Sets up Prometheus metrics collection

This ensures the application starts gracefully in any environment and automatically handles initialization tasks.

### Directory Structure
```
FootballPrediction/         # Project root directory
├── src/                   # Main source code
│   ├── api/              # API layer (CQRS implementation)
│   │   ├── predictions/  # Prediction APIs (optimized version included)
│   │   ├── data/         # Data management APIs
│   │   ├── analytics/    # Analytics APIs
│   │   ├── health/       # Health check APIs
│   │   ├── auth/         # Auth & authorization APIs
│   │   ├── optimization/ # Performance optimization APIs
│   │   └── models/       # API data models
│   ├── domain/           # Domain layer (DDD core logic)
│   ├── features/         # Feature store and data engineering (P0-2 Complete)
│   │   ├── feature_store.py           # Production-ready async feature store
│   │   ├── feature_store_interface.py # Protocol-based feature store interface
│   │   └── feature_definitions.py     # Feature data definitions and validation
│   ├── quality/          # Data quality monitoring system (P0-3 Complete)
│   │   ├── data_quality_monitor.py    # Modern async quality monitor
│   │   ├── quality_protocol.py        # Quality rule protocols
│   │   └── rules/                     # Quality rule implementations
│   ├── ml/               # Machine learning modules
│   │   ├── xgboost_hyperparameter_optimization.py  # XGBoost hyperparameter optimization
│   │   ├── lstm_predictor.py        # LSTM deep learning prediction
│   │   ├── football_prediction_pipeline.py  # Complete prediction pipeline
│   │   └── experiment_tracking.py   # MLflow experiment tracking
│   ├── tasks/            # Celery task scheduling
│   ├── database/         # Async SQLAlchemy 2.0 (includes async_manager.py unified interface)
│   ├── cache/            # Cache layer (Redis)
│   ├── cqrs/             # CQRS pattern implementation
│   ├── events/           # Event system
│   ├── core/             # Core infrastructure
│   ├── services/         # Business service layer
│   ├── utils/            # Utility functions
│   ├── monitoring/       # Monitoring system (Prometheus integration)
│   ├── adapters/         # External data source adapters (FotMob, etc.)
│   ├── collectors/       # Data collectors
│   ├── config/           # Configuration management
│   ├── middleware/       # Middleware
│   ├── performance/      # Performance monitoring
│   └── streaming/        # Real-time data streaming
├── tests/                # Test suites (250+ test files)
├── models/               # Trained ML models
├── scripts/              # Utility scripts
├── docker-compose*.yml   # Multiple Docker configurations (20+ files)
├── requirements*.txt     # Dependency management
└── config/               # Configuration files including quality gates
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
make help             # Show all available commands with descriptions ⭐
```

### Docker Compose Variants (9 Available)
The project includes 9 specialized Docker configurations:

```bash
# Development Environments
docker-compose.yml              # Standard development (default)
docker-compose.dev.yml          # Extended development with debug tools
docker-compose.lightweight.yml  # Minimal setup for low-resource machines

# CI/CD Environments
docker-compose.ci.yml           # Full CI environment with testing
docker-compose.ci.simple.yml    # Simplified CI for fast builds

# Production & Deployment
docker-compose.prod.yml         # Production-ready configuration
docker-compose.deploy.yml       # Deployment-specific settings

# Specialized Services
docker-compose.crawler.yml      # Web scraping focused setup
docker-compose.monitoring.yml   # Monitoring stack (Prometheus, Grafana)

# Usage Examples:
docker-compose -f docker-compose.lightweight.yml up    # Minimal dev
docker-compose -f docker-compose.monitoring.yml up     # With monitoring
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
make help             # Show all available commands ⭐
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

# Anti-Scraping Configuration (FotMob API)
PROXY_LIST=proxy1.example.com:8080,username:password@proxy2.example.com:8080
PROXY_HEALTH_CHECK_INTERVAL=300
PROXY_BAN_THRESHOLD=5
PROXY_COOLDOWN_TIME=3600
RATE_LIMIT_STRATEGY=adaptive  # conservative, normal, aggressive, adaptive
RATE_LIMIT_MIN_DELAY=1.0
RATE_LIMIT_MAX_DELAY=10.0
RATE_LIMIT_BASE_DELAY=2.0
USER_AGENT_ROTATION=true
MOBILE_USER_AGENT_RATIO=0.2  # 20% mobile, 80% desktop
ANTI_SCRAPING_LEVEL=medium  # low, medium, high

# Authentication (for development/testing)
ADMIN_PASSWORD_HASH=240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
TEST_PASSWORD_HASH=ffc121a2210958bf74e5a874668f3d978d24b6a8241496ccff3c0ea245e4f126

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
./ci-verify.sh        # Local CI verification script (recommended before commits)
```

### ⚠️ Important: Coverage Information (v2.1.0)
- **Current Coverage**: 29.0% total (measured) - ✅ Target Achieved
- **Quality Gates**: 6.0% minimum enforced (config/quality_baseline.json)
- **Test Cases**: 385+ passing tests
- **Domain Coverage**: Improved from 0.0% baseline
- **Utils Coverage**: 73.0% (strong foundation)
- **Monthly Target**: 18.0% (✅ Achieved - 11% above target)
- **Next Target**: 35.0% (stretch goal for next quarter)
- **Use `make ci`** for complete local verification before pushing

### Quality Gates Configuration (Enforced)
The project enforces strict quality standards via `config/quality_baseline.json`:

```json
{
  "quality_gates": {
    "minimum_total_coverage": 6.0,    // CI will fail below this
    "minimum_domain_coverage": 0.0,
    "minimum_utils_coverage": 70.0,    // Strong foundation requirement
    "minimum_pass_rate": 100.0,        // All tests must pass
    "maximum_regression": 0.5          // Limited regression allowed
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
# docker-compose.deploy.yml       - Deployment configuration
# docker-compose.monitoring.yml   # Monitoring stack

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

### Pytest Configuration (pytest.ini)
The project uses comprehensive pytest configuration with test markers:

```ini
# Test markers defined in pytest.ini
markers =
    unit:           # Fast isolated component tests
    integration:    # Database, cache, external API tests
    performance:    # Load and stress testing
    e2e:           # Complete user flow tests
    api:          # HTTP interface tests
    database:     # SQLAlchemy operation tests
    ml:           # Machine learning model tests
    slow:         # Time-intensive tests (>10s)
    skip_ci:      # Skip in CI environment
    unstable:     # Known flaky tests
```

### Running Specific Test Categories
```bash
# Run only unit tests
pytest -m unit

# Run integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run specific test file (use container!)
docker-compose exec app pytest tests/unit/api/test_predictions.py -v
```

### Environment Configuration Matrix
| Variable | Development | CI | Production | Purpose |
|----------|-------------|----|------------|---------|
| `FOOTBALL_PREDICTION_ML_MODE` | real | mock | real | ML model loading mode |
| `SKIP_ML_MODEL_LOADING` | false | true | false | Skip model loading for speed |
| `INFERENCE_SERVICE_MOCK` | false | true | false | Mock ML inference service |
| `XGBOOST_MOCK` | false | true | false | Mock XGBoost models |
| `JOBLIB_MOCK` | false | true | false | Mock joblib model loading |
| `ENV` | development | ci | production | Environment identifier |

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

### Feature Store Development
1. **Use Protocol-based Interface**: `src/features/feature_store_interface.py`
2. **Implement Features**: Add new feature definitions in `src/features/feature_definitions.py`
3. **Data Quality**: Apply quality rules from `src/quality/rules/`
4. **Storage**: Features automatically stored via async feature store
5. **Testing**: Feature store has 121.2% test coverage (P0-2 Complete)

### Data Quality Monitoring
1. **Built-in Rules**: Use existing rules in `src/quality/rules/`
2. **Custom Rules**: Implement `DataQualityRule` protocol for custom validation
3. **Batch Processing**: Use `DataQualityMonitor` for async batch checks
4. **Integration**: Quality monitor integrates with FeatureStore automatically
5. **Error Reporting**: JSON-safe error reports for downstream systems

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

## 🤖 AI-Assisted Development Workflow

### 📋 AI Development Guidelines
This section provides specific guidance for AI tools (Claude Code, Cursor, GitHub Copilot) working in this codebase.

### 🎯 AI Development Process

#### **Phase 1: Context Understanding**
```bash
# Always start by loading project context
make context              # Load project configuration
make status               # Check service status
make test.fast            # Verify environment health
```

#### **Phase 2: Task Analysis**
1. **Read Task Sources**:
   - `docs/_reports/TEST_COVERAGE_KANBAN.md` - Current priorities
   - `docs/_reports/BUGFIX_REPORT_*.md` - Latest issues
   - `docs/_reports/COVERAGE_FIX_PLAN.md` - Coverage gaps

2. **Analyze Test Failures**:
   ```bash
   # Run tests and capture output
   make test.fast --no-color 2>&1 | tee test_output.log

   # Identify error patterns
   grep -E "(FAILED|ERROR|ERROR:)" test_output.log
   ```

#### **Phase 3: Code Analysis**
```bash
# Find specific functionality using search patterns
grep -r "class.*Prediction" src/           # Find prediction classes
grep -r "@router" src/api/predictions/     # Find prediction endpoints
grep -r "async def.*predict" src/          # Find prediction functions
```

#### **Phase 4: Implementation & Testing**
1. **Make Targeted Changes**:
   - Focus on specific modules identified in Phase 2
   - Follow existing patterns in the codebase
   - Maintain architectural integrity

2. **Verify Changes**:
   ```bash
   # Quick verification
   make test.unit.ci              # Fast CI verification

   # Full verification if time permits
   make ci                        # Complete validation
   ```

### 🛠️ AI Coding Standards

#### **Code Quality Rules**
```python
# ✅ Always use complete type annotations
async def process_prediction_request(
    request: PredictionRequest,
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session)
) -> PredictionResponse:

# ✅ Follow async patterns consistently
async def get_match_by_id(match_id: str) -> Optional[Match]:
    async with get_db_session() as session:
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        return result.scalar_one_or_none()

# ✅ Use proper error handling
try:
    prediction = await generate_prediction(match_id)
except DataNotFoundError as e:
    logger.error(f"Match not found: {match_id}")
    raise HTTPException(status_code=404, detail="Match not found")
```

#### **Database Pattern Standards**
```python
# ✅ Always use unified async manager
from src.database.async_manager import get_db_session

# FastAPI dependency injection
@router.get("/matches/{match_id}")
async def get_match(
    match_id: str,
    session: AsyncSession = Depends(get_db_session)
) -> MatchResponse:
    match = await match_repository.get_by_id(session, match_id)
    return MatchResponse.model_validate(match)

# ❌ NEVER use deprecated connection.py
# from src.database.connection import get_session  # DEPRECATED
```

#### **API Development Standards**
```python
# ✅ Use CQRS pattern for API endpoints
@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    command: CreatePredictionCommand,
    handler: PredictionCommandHandler = Depends()
) -> PredictionResponse:
    return await handler.handle(command)

# ✅ Proper error responses
@router.get("/predictions/{prediction_id}")
async def get_prediction(
    prediction_id: str,
    handler: PredictionQueryHandler = Depends()
) -> PredictionResponse:
    try:
        return await handler.handle(GetPredictionQuery(prediction_id))
    except PredictionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Prediction {prediction_id} not found"
        )
```

### 🧪 AI Testing Guidelines

#### **Test Structure Standards**
```python
# ✅ Use proper test markers
@pytest.mark.unit
@pytest.mark.asyncio
async def test_prediction_service_success():
    # Arrange
    mock_match = create_mock_match()
    service = PredictionService()

    # Act
    result = await service.generate_prediction(mock_match.id)

    # Assert
    assert result.confidence > 0.5
    assert result.prediction_type == PredictionType.WINNER

# ✅ Mock external dependencies
@pytest.fixture
def mock_fotmob_client():
    with patch('src.adapters.fotmob_adapter.FotMobClient') as mock:
        mock.return_value.get_match_data.return_value = MOCK_MATCH_DATA
        yield mock
```

#### **Test Data Management**
```python
# ✅ Use factories for test data
@pytest.fixture
def sample_match():
    return MatchFactory.create(
        home_team="Team A",
        away_team="Team B",
        scheduled_at=datetime.now(timezone.utc)
    )

# ✅ Clean database state
@pytest.fixture(autouse=True)
async def cleanup_db(test_db_session):
    yield
    await test_db_session.execute(text("TRUNCATE TABLE matches RESTART IDENTITY CASCADE"))
    await test_db_session.commit()
```

### 🔍 AI Code Review Checklist

Before suggesting or committing changes, AI should verify:

#### **Architecture Compliance**
- [ ] Follows DDD patterns (domain purity)
- [ ] Implements CQRS separation (commands vs queries)
- [ ] Uses async/await consistently
- [ ] Maintains event-driven communication

#### **Code Quality Standards**
- [ ] Complete type annotations
- [ ] Proper error handling
- [ ] Consistent naming conventions
- [ ] No deprecated patterns (e.g., connection.py)

#### **Testing Requirements**
- [ ] Tests cover new functionality
- [ ] External dependencies are mocked
- [ ] Test coverage doesn't regress
- [ ] Tests run successfully in CI environment

#### **Security & Performance**
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] Database queries are optimized
- [ ] Rate limiting considered for external APIs

### 📊 AI Task Prioritization

Based on current project metrics:

#### **High Priority** (P0 - Critical)
1. **Test Coverage Improvement**: Target 35.0% (current: 29.0%)
2. **Domain Module Testing**: Currently low coverage
3. **Critical Bug Fixes**: Any failing tests in CI
4. **Security Issues**: Bandit scan failures

#### **Medium Priority** (P1 - Important)
1. **Performance Optimization**: API response times
2. **ML Pipeline Enhancements**: Model accuracy improvements
3. **Documentation Updates**: API documentation completeness
4. **Code Quality**: Ruff violations and type errors

#### **Low Priority** (P2 - Nice to Have)
1. **Feature Enhancements**: New prediction models
2. **UI/UX Improvements**: Frontend enhancements
3. **Monitoring**: Additional metrics and dashboards
4. **Refactoring**: Code cleanup and optimization

### 💡 AI Best Practices

1. **Always verify environment** before making changes
2. **Use existing patterns** rather than introducing new ones
3. **Test in isolation** before integration
4. **Document architectural decisions** when deviating from patterns
5. **Prioritize CI health** over feature development
6. **Communicate blockers** immediately when encountered

---

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

#### **Domain Layer (Pure Business Logic)**
```python
# src/domain/prediction.py - Pure domain logic, no external dependencies
from dataclasses import dataclass
from typing import List
from datetime import datetime
from enum import Enum

class PredictionType(Enum):
    WINNER = "winner"
    SCORE = "score"
    OVER_UNDER = "over_under"

@dataclass
class Match:
    id: str
    home_team: str
    away_team: str
    scheduled_at: datetime
    league_id: str

@dataclass
class PredictionResult:
    match_id: str
    prediction_type: PredictionType
    predicted_value: str
    confidence: float
    created_at: datetime

class MatchPrediction:
    """Domain entity for football match predictions"""

    def __init__(self, match: Match, result: PredictionResult):
        self.match = match
        self.result = result
        self._validate_prediction()

    def _validate_prediction(self) -> None:
        """Business rule: Prediction confidence must be >= 0.5"""
        if self.result.confidence < 0.5:
            raise ValueError("Prediction confidence must be at least 0.5")

    def is_high_confidence(self) -> bool:
        """Business rule: High confidence = >= 0.8"""
        return self.result.confidence >= 0.8

    def calculate_risk_score(self) -> float:
        """Business logic: Risk score calculation"""
        return 1.0 - self.result.confidence
```

#### **API Layer (CQRS Command Query Separation)**
```python
# src/api/predictions/commands.py - CQRS Commands
from pydantic import BaseModel, Field
from typing import Optional

class CreatePredictionCommand(BaseModel):
    match_id: str = Field(..., min_length=1, max_length=50)
    prediction_type: PredictionType
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class GetPredictionQuery(BaseModel):
    prediction_id: str
    include_details: bool = False

# src/api/predictions/handlers.py - CQRS Handlers
class PredictionCommandHandler:
    def __init__(self, prediction_service: PredictionService):
        self.prediction_service = prediction_service

    async def handle(self, command: CreatePredictionCommand) -> PredictionResponse:
        # Command handling logic
        prediction = await self.prediction_service.create_prediction(
            match_id=command.match_id,
            prediction_type=command.prediction_type,
            confidence_threshold=command.confidence_threshold
        )
        return PredictionResponse.from_domain(prediction)

class PredictionQueryHandler:
    def __init__(self, prediction_repository: PredictionRepository):
        self.prediction_repository = prediction_repository

    async def handle(self, query: GetPredictionQuery) -> PredictionResponse:
        # Query handling logic
        prediction = await self.prediction_repository.get_by_id(query.prediction_id)
        if not prediction:
            raise PredictionNotFoundError(f"Prediction {query.prediction_id} not found")

        return PredictionResponse.from_domain(prediction, query.include_details)

# src/api/predictions/router.py - API Routes
@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    command: CreatePredictionCommand,
    handler: PredictionCommandHandler = Depends()
) -> PredictionResponse:
    return await handler.handle(command)

@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    include_details: bool = False,
    handler: PredictionQueryHandler = Depends()
) -> PredictionResponse:
    query = GetPredictionQuery(prediction_id=prediction_id, include_details=include_details)
    return await handler.handle(query)
```

#### **Services Layer (Application Service Orchestration)**
```python
# src/services/prediction_service.py - Application services
class PredictionService:
    def __init__(
        self,
        match_repository: MatchRepository,
        ml_service: MLInferenceService,
        event_bus: EventBus
    ):
        self.match_repository = match_repository
        self.ml_service = ml_service
        self.event_bus = event_bus

    async def create_prediction(
        self,
        match_id: str,
        prediction_type: PredictionType,
        confidence_threshold: float
    ) -> MatchPrediction:
        # Orchestrate multiple domain operations

        # 1. Load aggregate
        match = await self.match_repository.get_by_id(match_id)
        if not match:
            raise MatchNotFoundError(f"Match {match_id} not found")

        # 2. Generate prediction using ML service
        ml_result = await self.ml_service.predict(match, prediction_type)

        # 3. Apply business rules
        if ml_result.confidence < confidence_threshold:
            raise LowConfidenceError(
                f"Prediction confidence {ml_result.confidence} below threshold {confidence_threshold}"
            )

        # 4. Create domain entity
        prediction = MatchPrediction(
            match=match,
            result=PredictionResult(
                match_id=match_id,
                prediction_type=prediction_type,
                predicted_value=ml_result.value,
                confidence=ml_result.confidence,
                created_at=datetime.utcnow()
            )
        )

        # 5. Save to repository
        await self.prediction_repository.save(prediction)

        # 6. Publish domain event
        await self.event_bus.publish(
            PredictionCreatedEvent(
                prediction_id=prediction.result.match_id,
                match_id=match_id,
                prediction_type=prediction_type
            )
        )

        return prediction
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

#### Proxy Configuration (WSL/Windows)
If running in WSL or Windows with proxy software (Clash, etc.):

```bash
# Set proxy for Docker containers
export HTTP_PROXY=http://host.docker.internal:7890
export HTTPS_PROXY=http://host.docker.internal:7890

# Test proxy connectivity
python scripts/proxy_check.py

# Restart services with proxy
make clean-all && make dev
```

#### Rate Limiting & Anti-Scraping
- **Rate Limiter**: `src/collectors/rate_limiter.py` - Adaptive delay strategies
- **Proxy Pool**: `src/collectors/proxy_pool.py` - Rotating proxy management
- **User-Agent Rotation**: `src/collectors/user_agent.py` - Mobile/desktop mixing

## 🔄 Microservices Architecture

### Service Overview
While the application follows a modular monolith structure in `src/`, it implements microservice patterns for scalability:

```
Service Communication Patterns:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Predictions    │    │   Data          │    │   Analytics     │
│  Service        │◄──►│   Collection    │◄──►│   Service       │
│  (src/api/)     │    │   (src/collectors/) │ │  (src/api/analytics/) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Core Events   │
                    │   (src/events/) │
                    └─────────────────┘
```

### Service Communication
- **Event-Driven**: Services communicate via `src/events/` system
- **CQRS Separation**: Command/Query separation in `src/cqrs/`
- **Async Processing**: Celery tasks in `src/tasks/` for background operations
- **Database Sharing**: PostgreSQL with unified async interface in `src/database/async_manager.py`

### Service Boundaries
- **Predictions Service**: `src/api/predictions/` + ML models in `src/ml/`
- **Data Collection Service**: `src/collectors/` + `src/adapters/` for external APIs
- **Analytics Service**: `src/api/analytics/` + metrics in `src/monitoring/`
- **User Management**: `src/api/auth/` + user domain logic
- **Real-time Streaming**: `src/streaming/` for WebSocket communications

## 📊 API Endpoints

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws
- **Prometheus Metrics**: http://localhost:8000/api/v1/metrics

## 📈 Performance Monitoring & Debugging

### Built-in Monitoring Stack
The application includes comprehensive monitoring:

```bash
# Health Check Endpoints
curl http://localhost:8000/health              # Basic health
curl http://localhost:8000/health/system       # System resources (CPU, RAM)
curl http://localhost:8000/health/database     # Database connectivity
curl http://localhost:8000/api/v1/metrics       # Prometheus metrics

# External Monitoring Services
http://localhost:5555                           # Flower - Celery task monitoring
mlflow ui                                       # MLflow - ML experiment tracking
docker-compose -f docker-compose.monitoring.yml up  # Full monitoring stack
```

### Performance Monitoring Commands
```bash
# Real-time performance metrics
curl http://localhost:8000/api/v1/metrics                    # Prometheus metrics
curl http://localhost:8000/health/system                   # System resource usage
curl http://localhost:8000/health/database                 # Database performance

# Application performance profiling
export DEBUG=true                                          # Enable debug mode
make dev                                                   # Start with debugging
make logs | grep "performance"                            # Filter performance logs

# ML model performance
python src/ml/model_performance_monitor.py                 # Model performance dashboard
mlflow ui                                                  # MLflow experiment tracking
```

### Full Monitoring Stack (Optional)
```bash
# Start with Grafana, Prometheus, and Jaeger
docker-compose -f docker-compose.monitoring.yml up

# Access dashboards
http://localhost:3000              # Grafana (admin/admin)
http://localhost:9090              # Prometheus
http://localhost:16686             # Jaeger tracing
```

### Debugging Tools & Techniques
```bash
# Container debugging
make shell                                                 # Enter app container
docker-compose exec app python -m pdb src/main.py         # Debug with pdb
docker-compose logs app --tail=100                        # Recent app logs

# Database debugging
make db-shell                                              # PostgreSQL debugging
\dt                                                       # List all tables
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 10;           # Query performance

# Redis debugging
make redis-shell                                           # Redis CLI
MONITOR                                                   # Real-time Redis commands
INFO memory                                               # Memory usage analysis

# Background task debugging
curl http://localhost:5555                                 # Flower dashboard
docker-compose exec worker celery -A src.tasks.celery_app inspect active  # Active tasks
```

### Performance Benchmarks
- **API Response Time**: < 200ms for 95th percentile
- **Database Query Time**: < 100ms average
- **ML Model Inference**: < 500ms per prediction
- **Memory Usage**: < 2GB per container
- **CPU Usage**: < 80% under normal load

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

### 🎯 Critical File Reference (For AI Development)

#### Core Application Files
```
src/main.py                    # Application lifecycle + smart cold start
src/config/                    # Configuration management
├── openapi_config.py         # API documentation setup
├── swagger_ui_config.py      # Enhanced Swagger UI
└── settings.py               # Application settings
```

#### Database Layer (DDD)
```
src/database/
├── async_manager.py          # ⭐ Unified async interface (USE THIS)
├── models/                   # SQLAlchemy models (DDD entities)
│   ├── match.py             # Match entity
│   ├── team.py              # Team entity
│   ├── prediction.py        # Prediction entity
│   └── user.py              # User entity
└── connection.py             # ❌ Deprecated (DO NOT USE)
```

#### API Layer (CQRS)
```
src/api/
├── predictions/              # Prediction APIs (optimized)
│   ├── router.py            # Main prediction routes
│   └── optimized_router.py  # Performance-optimized routes
├── data_management.py        # ETL data import/export
├── health/                   # Health check endpoints
├── auth/                     # Authentication & authorization
├── analytics/                # Analytics and metrics
└── models/                   # Pydantic request/response models
```

#### Feature Store & Data Quality (P0-2 Complete)
```
src/features/
├── feature_store.py                   # Production-ready async feature store
├── feature_store_interface.py         # Protocol-based interface
└── feature_definitions.py             # Feature data definitions

src/quality/
├── data_quality_monitor.py            # Modern async quality monitor
├── quality_protocol.py                # Quality rule protocols
└── rules/                             # Quality rule implementations
    ├── logical_relation_rule.py       # Logical relationship validation
    ├── missing_value_rule.py          # Missing value detection
    ├── range_rule.py                  # Range validation
    ├── type_rule.py                   # Type checking
    └── __init__.py                    # Rule registry
```

#### Machine Learning Pipeline
```
src/ml/
├── enhanced_feature_engineering.py    # Feature extraction
├── enhanced_xgboost_trainer.py        # XGBoost model training
├── lstm_predictor.py                  # Deep learning LSTM
├── football_prediction_pipeline.py    # Complete pipeline
├── experiment_tracking.py             # MLflow integration
└── xgboost_hyperparameter_optimization.py  # Optuna tuning
```

#### External Data Collection
```
src/collectors/               # Data collectors (FotMob focus)
├── fotmob_details_collector.py  # ⭐ Primary data engine
├── rate_limiter.py             # Anti-scraping rate limiting
├── proxy_pool.py               # Proxy rotation
└── user_agent.py               # User-Agent rotation

src/adapters/
├── factory.py                  # Data source factory pattern
└── fotmob_adapter.py           # FotMob API adapter
```

#### Event System (CQRS Events)
```
src/events/                   # Domain events
├── base_event.py             # Base event class
├── match_events.py           # Match-related events
└── prediction_events.py      # Prediction-related events

src/cqrs/                     # Command Query Responsibility Segregation
├── commands/                 # Command handlers
├── queries/                  # Query handlers
└── application.py            # CQRS application setup
```

#### Background Tasks
```
src/tasks/
├── celery_app.py             # Celery configuration
├── data_collection_tasks.py  # Background data collection
└── prediction_tasks.py       # Async prediction processing
```

#### Testing Structure
```
tests/
├── conftest.py               # Global test configuration
├── unit/                     # Unit tests (85%)
│   ├── api/                  # API endpoint tests
│   ├── database/             # Database tests
│   ├── ml/                   # ML model tests
│   └── utils/                # Utility tests
├── integration/              # Integration tests (12%)
└── e2e/                      # End-to-end tests (2%)
```

### 🔍 Search Patterns for Quick Navigation
```bash
# Find API endpoints
grep -r "@router\." src/api/
grep -r "@app\." src/

# Find database models
grep -r "class.*Base" src/database/models/

# Find event handlers
grep -r "@event_handler" src/

# Find CQRS handlers
grep -r "class.*CommandHandler" src/cqrs/
grep -r "class.*QueryHandler" src/cqrs/

# Find Feature Store implementations
grep -r "FeatureStoreProtocol" src/features/
grep -r "class.*FeatureStore" src/features/

# Find Data Quality rules
grep -r "DataQualityRule" src/quality/rules/
grep -r "class.*Rule" src/quality/rules/

# Find test markers
grep -r "@pytest.mark" tests/
```

## 🚨 Troubleshooting Guide

### Quick Reference Table
| Issue Type | Primary Command | Secondary Checks |
|-----------|----------------|------------------|
| **Test Failures** | `make test.fast` | `make logs`, `export FOOTBALL_PREDICTION_ML_MODE=mock` |
| **CI Timeout** | `make test.unit.ci` | Check memory usage, reduce parallel jobs |
| **Port Conflicts** | `lsof -i :8000` | `kill -9 <PID>`, modify docker-compose.yml |
| **Database Issues** | `make db-migrate` | `make status`, `make db-shell` |
| **Redis Connection** | `make redis-shell` | `make logs-redis`, check docker-compose.yml |
| **Memory Issues** | `make test.fast` | `docker stats`, reduce ML model loading |
| **Type Errors** | `make type-check` | Check imports, add type annotations |
| **Dependency Issues** | `make clean-all && make dev` | Verify requirements*.txt files |
| **ML Model Loading** | Check `models/trained/` | `mlflow experiments list`, model paths |
| **Celery Task Failures** | `make logs` | `curl http://localhost:5555`, Redis status |
| **Coverage < 6.0%** | `make coverage` | Check specific test files coverage gaps |
| **Docker Build Failures** | Check `Dockerfile` | Verify requirements, build context |
| **FotMob 403 Errors** | Check `.env` auth | `python scripts/manual_token_test.py` |
| **Container Permissions** | `sudo chown -R $USER:$USER ./` | Check Docker user mapping |

### Error-Specific Solutions

#### 🔥 FotMob API Authentication Failures
```bash
# Symptom: HTTP 403 errors from FotMob API
# Diagnosis:
python scripts/manual_token_test.py

# Solution:
python scripts/refresh_fotmob_tokens.py
# Verify environment variables:
cat .env | grep FOTMOB

# Common fixes:
# 1. Update FOTMOB_CLIENT_VERSION in .env
# 2. Refresh FOTMOB_KNOWN_SIGNATURE
# 3. Check network connectivity
# 4. Verify proxy configuration (if using Clash)
# 5. Check rate limiting settings

# Proxy Configuration (WSL/Windows)
export HTTP_PROXY=http://host.docker.internal:7890
export HTTPS_PROXY=http://host.docker.internal:7890
```

#### 🐳 Docker Port Conflicts
```bash
# Symptom: "port already allocated" errors
# Diagnosis:
lsof -i :8000  # Backend API
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :5555  # Flower (Celery)

# Solution 1: Kill conflicting processes
kill -9 <PID>  # Force kill process

# Solution 2: Modify ports in docker-compose.yml
services:
  app:
    ports:
      - "8001:8000"  # Change external port to 8001
  db:
    ports:
      - "5433:5432"  # Change external port to 5433

# Solution 3: Clean reset
make clean-all && make dev
```

#### 🧠 ML Model Loading Problems
```bash
# Symptom: Model loading failures during startup
# Diagnosis:
ls -la models/trained/
mlflow experiments list

# Solution 1: Re-train models
python src/ml/enhanced_xgboost_trainer.py

# Solution 2: Use mock mode for development
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true
make dev

# Solution 3: Check model paths
echo $ML_MODEL_PATH
find /app -name "*.pkl" -o -name "*.joblib"
```

#### 📊 Database Connection Issues
```bash
# Symptom: Database connection timeouts
# Diagnosis:
make db-shell
# Check connection string in .env:
echo $DATABASE_URL

# Solution 1: Run pending migrations
make db-migrate

# Solution 2: Reset database (dev only)
make db-reset

# Solution 3: Check PostgreSQL status
docker-compose exec db pg_isready
docker-compose logs db --tail=20

# Solution 4: Verify database health
curl http://localhost:8000/health/database
```

#### ⚡ Performance Issues
```bash
# Symptom: Slow API responses, high memory usage
# Monitoring:
curl http://localhost:8000/health/system
docker stats

# Solution 1: Enable mock mode to skip ML models
export FOOTBALL_PREDICTION_ML_MODE=mock
make dev

# Solution 2: Check for memory leaks
make logs | grep "memory"
docker-compose exec app ps aux

# Solution 3: Optimize database queries
make db-shell
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 10;

# Solution 4: Clear cache
make redis-shell
FLUSHALL
```

#### 🧪 Test Failures
```bash
# Symptom: Tests failing unexpectedly
# Diagnosis:
make test.fast --no-color 2>&1 | tee test_failures.log

# Solution 1: Check environment variables
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
export INFERENCE_SERVICE_MOCK=true

# Solution 2: Run specific test category
make test.unit.ci
make test.integration

# Solution 3: Check database state
make db-shell
SELECT COUNT(*) FROM matches;

# Solution 4: Clean test environment
make clean-all && make dev && make test.fast
```

#### 🔐 Authentication Issues
```bash
# Symptom: JWT token errors, authentication failures
# Diagnosis:
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}'

# Solution 1: Check password hashes
cat .env | grep PASSWORD_HASH

# Solution 2: Generate new password hash
python -c "
import hashlib
print(hashlib.sha256('your-password'.encode()).hexdigest())
"

# Solution 3: Verify JWT secret
echo $SECRET_KEY
# Should be at least 32 characters
```

#### 🔄 Redis Connection Issues
```bash
# Symptom: Cache failures, Celery task issues
# Diagnosis:
make redis-shell
PING  # Should return PONG

# Solution 1: Restart Redis service
docker-compose restart redis

# Solution 2: Check Redis logs
make logs-redis

# Solution 3: Clear corrupted data
make redis-shell
FLUSHDB  # Clear current database
# OR
FLUSHALL # Clear all databases

# Solution 4: Verify Celery connection
curl http://localhost:5555  # Flower UI
docker-compose exec worker celery -A src.tasks.celery_app inspect active
```

#### 🧠 ML Model Loading Problems
```bash
# Symptom: Model loading failures during startup
# Diagnosis:
ls -la models/trained/
mlflow experiments list

# Solution:
# Re-train models:
python src/ml/enhanced_xgboost_trainer.py

# Or use mock mode for development:
export FOOTBALL_PREDICTION_ML_MODE=mock
export SKIP_ML_MODEL_LOADING=true
make dev
```

#### 📊 Database Connection Issues
```bash
# Symptom: Database connection timeouts
# Diagnosis:
make db-shell
# Check connection string in .env:
echo $DATABASE_URL

# Common solutions:
make db-migrate      # Run pending migrations
make db-reset        # Reset database (dev only)
# Check PostgreSQL status:
docker-compose exec db pg_isready
```

#### ⚡ Performance Issues
```bash
# Symptom: Slow API responses, high memory usage
# Monitoring:
curl http://localhost:8000/health/system
docker stats

# Common fixes:
# 1. Enable mock mode to skip ML models:
export FOOTBALL_PREDICTION_ML_MODE=mock

# 2. Check for memory leaks:
make logs | grep "memory"

# 3. Optimize database queries:
make db-shell
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 10;
```

## 📜 Essential Scripts Guide

### Critical Data Collection Scripts
```bash
# Primary FotMob Data Engine (HTTP-based, NO browser automation)
python scripts/backfill_details_fotmob_v2.py      # Main data collection engine

# Token Management (REQUIRED for FotMob API access)
python scripts/manual_token_test.py               # Test authentication headers
python scripts/refresh_fotmob_tokens.py           # Update expired tokens

# Data Pipeline Operations
python scripts/explore_fotmob_urls.py             # Discover API endpoints
make run-l1                                        # L1: Fixtures collection
make run-l2                                        # L2: Match details collection

# Database Operations
python scripts/init_db.py                         # Initialize database schema
python scripts/seed_data.py                       # Load initial data
```

### ML Training Scripts
```bash
# Model Training Pipeline
python src/ml/enhanced_xgboost_trainer.py        # XGBoost model training
python src/ml/lstm_predictor.py                  # Deep learning LSTM
python src/ml/football_prediction_pipeline.py    # Complete ML pipeline

# Hyperparameter Optimization
python src/ml/xgboost_hyperparameter_optimization.py  # Optuna tuning
python scripts/tune_model_optuna.py                     # Advanced tuning

# Model Performance
python src/ml/model_performance_monitor.py       # Performance dashboard
```

### Development & Debugging Scripts
```bash
# Environment Testing
python scripts/auth_integration_test.py          # Test authentication system
python scripts/proxy_check.py                    # Verify proxy configuration
python scripts/collectors_dry_run.py             # Test data collectors without DB writes

# Data Analysis
python scripts/deep_data_analysis.py             # Analyze data quality
python scripts/inspect_real_data_depth.py        # Check data coverage
python scripts/fotmob_data_analysis.py           # FotMob-specific analysis
```

## ⚡ Quick Command Reference

### Most Used Commands (90% of Daily Tasks)
```bash
# Environment Management
make dev && make status          # Start and check all services
make shell                       # Enter app container
make logs                        # View application logs

# Testing (Always use Makefile commands!)
make test.fast                   # Quick core tests (2-3 min)
make test.unit.ci                # CI verification (fastest)
make ci                          # Complete validation (if time permits)

# Code Quality
make lint && make fix-code       # Check and fix code issues
make security-check              # Security scanning

# Database Operations
make db-migrate                  # Run database migrations
make db-shell                    # PostgreSQL terminal
```

### Development Workflow Commands
```bash
# Daily Development
make dev && make status          # 1. Start environment
curl http://localhost:8000/health  # 2. Verify API
make test.fast                   # 3. Run core tests
# 4. Development work...
make lint && make fix-code       # 5. Code quality
make test.unit.ci                # 6. Pre-commit verification

# Environment Switching
export FOOTBALL_PREDICTION_ML_MODE=mock     # Fast development
export FOOTBALL_PREDICTION_ML_MODE=real     # Full ML features
make clean-all && make dev                  # Fresh environment
```

### Troubleshooting Commands
```bash
# Service Health
make status                      # Check all services
curl http://localhost:8000/health/system   # System resources
curl http://localhost:8000/health/database  # DB connectivity

# Debug Information
make logs | grep -i error       # Find errors in logs
docker-compose ps               # Check container status
docker stats                    # Resource usage

# Reset & Recovery
make clean-all && make dev      # Complete rebuild
make db-reset                   # Reset database (dev only)
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
12. **Use `make help`** - Shows all available commands with descriptions - most useful command for newcomers

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