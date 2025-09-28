# ⚽ FootballPrediction - 足球预测系统

## 📋 Project Overview

The FootballPrediction project is an **enterprise-level football prediction system** built with modern Python technology stack. It's a comprehensive machine learning application that uses FastAPI, SQLAlchemy, PostgreSQL, Redis, and various MLOps tools to predict football match outcomes.

The system is designed with production readiness in mind, featuring:
- High test coverage (96.35%)
- Complete security validation through bandit scans
- Full type safety with Python type annotations
- Docker and docker-compose for containerization
- Complete CI/CD pipeline with GitHub Actions simulation
- Full monitoring stack with Prometheus, Grafana, and MLflow
- Data lake architecture with MinIO and Kafka streaming
- Feature store capabilities with Feast
- Data lineage tracking with Marquez
- Task scheduling with Celery

## 🏗️ Architecture

The system follows a modern, scalable architecture:

### Core Components:
- **FastAPI** - Web framework providing RESTful APIs with automatic OpenAPI documentation
- **SQLAlchemy** - ORM for PostgreSQL database management
- **Redis** - Caching and session storage
- **PostgreSQL** - Primary relational database
- **Kafka** - Stream processing for real-time data
- **MinIO** - Object storage for data lake and model artifacts

### MLOps Stack:
- **MLflow** - Experiment tracking, model registry, and deployment
- **XGBoost** - Primary machine learning algorithm for predictions
- **Scikit-learn** - Feature engineering and preprocessing
- **Pandas/Numpy** - Data manipulation and analysis

### Monitoring & Observability:
- **Prometheus** - Metrics collection
- **Grafana** - Visualization dashboard
- **OpenLineage** - Data lineage tracking
- **Marquez** - Data lineage management

### Task Management:
- **Celery** - Distributed task queue for background processing
- **Celery Beat** - Periodic task scheduler
- **Flower** - Celery web monitoring interface

## 🚀 Building and Running

### Prerequisites:
- Python 3.11+
- Docker and Docker Compose
- Make utility

### Quick Start Commands:
```bash
# Clone the repository
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# Initialize the development environment
make install      # Install dependencies
make context      # Load project context (most important step)
make test         # Run tests (385 test cases)
make coverage     # Check 96.35%+ coverage report
```

### Full Development Setup:
```bash
make dev-setup    # Complete development setup (install + env-check + context)
```

### Docker Compose Environment:
```bash
make up           # Start all services with Docker Compose
make logs         # View service logs
make down         # Stop all services
```

### Local CI Verification:
```bash
./ci-verify.sh    # Run complete CI validation locally (environment reconstruction, testing, coverage)
```

### Production Deployment:
```bash
make deploy       # Build and deploy with git SHA tag
make rollback TAG=<git-sha>  # Rollback to a previous version
```

## 🧪 Testing
The project includes comprehensive testing with various categories:

- **Unit tests**: `make test.unit` or `make test-quick`
- **Integration tests**: `make test.int`
- **End-to-end tests**: `make test.e2e`
- **Slow tests**: `make test.slow`
- **Coverage reports**: `make coverage` (enforces 80% threshold)
- **HTML coverage**: `make cov.html`

## 🔧 Development Conventions

### Code Quality:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **Bandit** for security scanning
- **Pylint** for code analysis

### Quality Commands:
```bash
make fmt        # Format code with black and isort
make lint       # Run linter checks
make type-check # Run type checking
make quality    # Complete quality check (lint + format + test)
```

### Pre-push Validation:
```bash
make prepush    # Complete pre-push validation (format + lint + type-check + test)
make ci         # Simulate full CI pipeline
```

### Project Structure:
```
FootballPrediction/
├── src/                    # Source code
│   ├── api/               # API endpoints
│   ├── database/          # Database connection and models
│   ├── models/            # ML models and prediction logic
│   ├── features/          # Feature engineering
│   ├── services/          # Business logic
│   ├── data/              # Data processing
│   ├── core/              # Core utilities
│   ├── cache/             # Caching layer
│   ├── streaming/         # Kafka streaming
│   ├── tasks/             # Celery tasks
│   ├── monitoring/        # Monitoring logic
│   ├── lineage/           # Data lineage tracking
│   └── main.py            # Main FastAPI application
├── tests/                  # Test suite
├── config/                 # Configuration files
├── models/                 # Trained ML models storage
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── data/                   # Data files
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Container build instructions
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── Makefile               # Development commands
└── README.md              # Project documentation
```

### Environment Management:
- Multiple environment files: `.env.ci`, `.env.integration`, `.env.staging`, `.env.production.example`
- Use `make check-env` to verify required environment variables
- Use `make create-env` to create environment file from example

## 🔒 Security & Monitoring

### Security Features:
- Security scanning with Bandit
- Dependency vulnerability checks with Safety
- Secret scanning capabilities
- License compliance checking
- Complete audit capabilities with `make audit`

### Monitoring & Observability:
- Prometheus metrics collection
- Grafana dashboards
- Application logging with StructLog
- ML model performance tracking
- Data lineage with OpenLineage
- System resource monitoring

### MLOps Pipeline:
The project includes a complete MLOps feedback pipeline:
- `make feedback-update` - Update predictions with actual results
- `make feedback-report` - Generate accuracy trends and feedback analysis
- `make performance-report` - Generate model performance reports
- `make retrain-check` - Check models and trigger retraining if needed
- `make model-monitor` - Run enhanced model monitoring
- `make mlops-pipeline` - Run complete MLOps feedback pipeline

## 📊 Data Processing & Storage

### Data Flow Architecture:
- **Bronze** → **Silver** → **Gold** data lake layers with MinIO
- Kafka streaming for real-time data ingestion
- PostgreSQL for transactional data
- Redis for caching
- MLflow for model artifacts
- Feast for feature store

### Database Management:
```bash
make db-init      # Initialize database
make db-migrate   # Run migrations
make db-seed      # Seed with initial data
make db-backup    # Create backup
make db-reset     # Reset database (WARNING: deletes all data)
```

### AI-Assisted Development:
The project includes AI-assisted development capabilities:
- `make ai-bugfix-analyze` - Run AI bug analysis
- `make ai-bugfix-fix` - Apply AI-recommended fixes
- `make ai-bugfix-report` - Generate AI bugfix report
- `make context` - Load project context for AI development

## 🚀 Key Features

1. **High Test Coverage** - 96.35% coverage with strict enforcement
2. **Production Ready** - Docker containers, health checks, monitoring
3. **MLOps Integration** - MLflow, model versioning, experiment tracking
4. **Security First** - Bandit scanning, dependency checks, secret detection
5. **AI-Assisted Development** - Built-in AI tools for development
6. **Complete Monitoring** - Prometheus, Grafana, application metrics
7. **Data Lineage** - Full tracking of data flow and transformations
8. **Scalable Architecture** - Microservice architecture with containerization
9. **Real-time Processing** - Kafka streaming for real-time data
10. **Feature Store** - Feast integration for feature management