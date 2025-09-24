# 🏈 FootballPrediction Project Context for Qwen

This document provides essential context about the FootballPrediction project to help you understand and work effectively with this codebase.

## 📋 Project Overview

FootballPrediction is an enterprise-grade football prediction system built with modern Python technologies. It uses FastAPI as the core web framework with a complete development infrastructure and best practices configuration.

### Key Features:

- **High Test Coverage** - 96.35% code coverage with 385+ test cases
- **Security Validation** - Passed bandit security scanning with dependency vulnerabilities fixed
- **Type Safety** - Full Python type annotations and static checking
- **Modern Architecture** - FastAPI + SQLAlchemy + Redis + PostgreSQL
- **Containerized Deployment** - Docker + docker-compose production-ready configuration
- **Automated CI/CD** - GitHub Actions + local CI simulation
- **Complete Toolchain** - 613-line Makefile-driven development workflow
- **AI-Assisted Development** - Built-in Cursor rules and AI workflow guidance

## 🏗️ Architecture & Technologies

### Core Stack:
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis
- **Streaming**: Kafka for real-time data processing
- **ML Platform**: MLflow for experiment tracking and model management
- **Feature Store**: Feast for feature management
- **Monitoring**: Prometheus + Grafana for metrics and visualization
- **Data Quality**: Great Expectations for data validation
- **Task Queue**: Celery with Redis backend
- **Containerization**: Docker + docker-compose

### Project Structure:
```
FootballPrediction/
├── src/                    # Source code
│   ├── api/               # API endpoints
│   ├── core/              # Core business logic
│   ├── database/          # Database models and connections
│   ├── models/            # ML models and prediction logic
│   ├── services/          # Business services
│   ├── cache/             # Cache management
│   ├── streaming/         # Kafka streaming components
│   ├── monitoring/        # Monitoring and metrics
│   ├── tasks/             # Background tasks
│   ├── utils/             # Utility functions
│   └── main.py            # Application entry point
├── tests/                 # Test suite (unit, integration, e2e)
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── .github/workflows/     # CI/CD configuration
├── docker-compose.yml     # Docker services configuration
├── Dockerfile             # Application container definition
├── Makefile               # Development toolchain
├── requirements.txt       # Production dependencies
└── requirements-dev.txt   # Development dependencies
```

## 🚀 Getting Started

### Quick Start Commands:
```bash
# Clone and setup
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# Install dependencies and setup environment
make install      # Install dependencies
make context      # Load project context (⭐ Most important)
make test         # Run tests (385+ test cases)
make coverage     # View 96.35% coverage report

# Local CI verification
./ci-verify.sh    # Full local CI validation
make ci           # Complete quality checks
```

## 🛠️ Development Workflow

### Essential Makefile Commands:
```bash
make help         # Show all available commands ⭐
make venv         # Create virtual environment
make install      # Install dependencies
make lint         # Code quality checks
make test         # Run tests
make ci           # Local CI checks
make sync-issues  # GitHub Issues synchronization 🔄
make context      # Load project context for AI development
```

### Development Process:
1. `make env-check` - Check environment
2. `make context` - Load context
3. Develop and test
4. `make ci` - Quality checks
5. `make prepush` - Complete validation

## 🧪 Testing Framework

The project has a comprehensive layered testing architecture:

### Test Structure:
```
tests/
├── unit/         # Unit tests (fast, isolated)
├── integration/  # Integration tests (with real services)
├── e2e/          # End-to-end tests (full workflows)
├── slow/         # Slow-running tests
└── fixtures/     # Test data and factories
```

### Running Tests:
```bash
# Run all tests
pytest tests/

# Run specific test types
pytest tests/unit/              # Unit tests
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Requirements:
- **Coverage**: Minimum 80% required (currently at 96.35%)
- **Markers**: unit, integration, e2e, slow, docker
- **Async Support**: Built-in pytest-asyncio support

## 🐳 Containerization & Deployment

### Docker Services:
The project uses docker-compose to manage a complete service stack:
- **app**: Main FastAPI application
- **db**: PostgreSQL database
- **redis**: Redis cache
- **kafka**: Kafka streaming platform
- **nginx**: Reverse proxy
- **minio**: Object storage (S3-compatible)
- **prometheus**: Metrics collection
- **grafana**: Metrics visualization
- **mlflow**: ML experiment tracking
- **celery**: Background task processing

### Deployment Commands:
```bash
# Start full environment
docker-compose up --build

# Deploy with immutable git-sha tag
make deploy

# Rollback to previous version
make rollback TAG=<git-sha>
```

## 📊 Monitoring & Observability

The system includes comprehensive monitoring:
- **Metrics**: Prometheus metrics collector
- **Visualization**: Grafana dashboards
- **Health Checks**: Built-in health endpoints
- **Alerting**: Prometheus AlertManager
- **Data Lineage**: Marquez for data governance
- **Logging**: Structured logging with structlog

## 🔧 Configuration Management

Environment configuration is managed through:
- `.env.ci` - CI environment variables
- `env.example` - Example environment file
- Environment-specific Docker configurations

Key configuration areas:
- Database connections
- Redis caching
- Kafka streaming
- MLflow tracking
- MinIO storage
- External API keys

## 🤖 AI-Assisted Development

The project is designed for AI-assisted development:
1. `make context` - Load comprehensive project context
2. Follow tool-first principles
3. Use structured documentation for AI understanding
4. Leverage Cursor rules and AI workflow guides

## 📈 MLOps Pipeline

The system includes a complete MLOps feedback loop:
```bash
make feedback-update    # Update prediction results
make performance-report # Generate model reports
make retrain-check      # Check models for retraining
make model-monitor      # Run model monitoring
make mlops-pipeline     # Complete MLOps cycle
```

## 🔒 Security & Compliance

- Security scanning with bandit
- Dependency vulnerability checks
- Type safety with mypy
- Code quality enforcement
- Test coverage requirements

## 🎯 Quality Standards

- **Code Coverage**: ≥ 80% (currently 96.35%)
- **Security**: Validated with no known vulnerabilities
- **Code Quality**: A+ rating with full linting
- **Testing**: 385+ passing tests
- **Documentation**: Comprehensive inline and external docs

## 🔄 CI/CD Integration

Local CI simulation with `./ci-verify.sh` ensures consistency with remote CI environments:
1. Virtual environment rebuild
2. Docker environment startup
3. Test execution with coverage validation
4. Quality checks (linting, type checking)

## 📚 Documentation

Key documentation files:
- `README.md` - Project overview and quick start
- `TOOLS.md` - Development tools guide
- `tests/README.md` - Testing framework documentation
- `AI_WORK_GUIDE.md` - AI development workflow
- Various other specialized guides in the docs/ directory

This project follows enterprise best practices for Python development with a focus on maintainability, testability, and scalability.