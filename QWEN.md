# FootballPrediction Project - Qwen Code Context

## Project Overview

This is a **Football Prediction System** built with a modern Python technology stack. It's an enterprise-grade application using FastAPI as the web framework, with a complete development infrastructure and best practices configuration.

### Core Features
- High test coverage (96.35%)
- Security validation with bandit scanning
- Full type safety with Python type annotations
- Modern architecture with FastAPI, SQLAlchemy, Redis, and PostgreSQL
- Containerized deployment with Docker and docker-compose
- Automated CI/CD with GitHub Actions
- Complete development toolchain driven by a 613-line Makefile
- AI-assisted development workflow
- Comprehensive documentation

## Project Structure
```
FootballPrediction/
├── src/                  # Source code
├── tests/                # Test files
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── .github/workflows/    # CI/CD configuration
├── config/               # Configuration files
├── data/                 # Data files
├── models/               # ML models
├── monitoring/           # Monitoring configurations
├── nginx/                # Nginx configuration
├── reports/              # Generated reports
├── venv/                 # Virtual environment (git-ignored)
├── Makefile              # Development toolchain
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # Docker image definition
├── README.md             # Project documentation
└── ...                   # Other configuration and documentation files
```

## Key Technologies
- **Backend Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis
- **Streaming**: Kafka (via confluent-kafka)
- **Monitoring**: Prometheus, Grafana, AlertManager
- **Data Lineage**: Marquez
- **ML Platform**: MLflow
- **Task Queue**: Celery with Redis backend
- **Feature Store**: Feast
- **Data Validation**: Great Expectations
- **Containerization**: Docker, docker-compose

## Development Workflow

### Environment Setup
1. Clone the repository
2. Run `make install` to create virtual environment and install dependencies
3. Run `make context` to load project context (important for AI-assisted development)

### Code Quality
- `make lint`: Run flake8 and mypy checks
- `make fmt`: Format code with black and isort
- `make quality` or `make check`: Complete quality check (lint + format + test)

### Testing
- `make test`: Run pytest unit tests
- `make coverage`: Run tests with coverage report (requires 80% minimum)
- `make ci`: Simulate CI environment locally

### GitHub Issues Synchronization
- The project includes a custom tool for synchronizing GitHub Issues with a local `issues.yaml` file
- `make sync-issues`: Sync issues between GitHub and local file
- This enables offline issue management and team collaboration

### AI-Assisted Development
The project is designed to work with AI coding assistants:
1. `make env-check`: Check environment health
2. `make context`: Load comprehensive project context
3. Development and testing
4. `make ci`: Quality checks
5. `make prepush`: Full validation before pushing

## Building and Running

### Local Development
1. `make install`: Set up environment
2. `make context`: Load context for AI tools
3. `make test`: Run tests
4. `make coverage`: Check code coverage

### Containerized Deployment
1. Configure environment variables in `.env.ci` or similar files
2. `docker-compose up --build`: Start all services
   - This includes the app, database, Redis, Kafka, monitoring tools (Prometheus, Grafana), MLflow, and task workers
3. Access services:
   - Main app: http://localhost:8000
   - Grafana: http://localhost:3000
   - MLflow: http://localhost:5002
   - Flower (Celery monitoring): http://localhost:5555/flower

### CI Simulation
- Run `./ci-verify.sh` to execute a complete CI validation locally
- This script rebuilds the virtual environment, starts Docker services, and runs all tests with coverage checks

## Development Conventions
- Follow the toolchain defined in the Makefile
- Maintain high test coverage (>80%)
- Use type hints throughout the codebase
- Follow code formatting standards (black, isort)
- Write comprehensive docstrings for public APIs
- Use the GitHub issues sync tool for task management

## Key Files and Directories
- `src/main.py`: Main FastAPI application entry point
- `Makefile`: Primary development toolchain
- `requirements.txt`/`requirements-dev.txt`: Dependencies
- `docker-compose.yml`: Full service orchestration
- `scripts/sync_issues.py`: GitHub issues synchronization tool
- `issues.yaml`: Local issue tracking file
- `TOOLS.md`: Detailed documentation of development tools

## Architecture Overview

### Core Components
1. **API Layer**: FastAPI-based REST API with endpoints for predictions, data, features, monitoring, and health checks
2. **Database Layer**: PostgreSQL with SQLAlchemy ORM for data persistence
3. **Caching Layer**: Redis for caching frequently accessed data
4. **Streaming Layer**: Kafka for real-time data processing
5. **ML Pipeline**: MLflow for model management and training
6. **Task Queue**: Celery for background task processing
7. **Feature Store**: Feast for feature management
8. **Monitoring**: Prometheus and Grafana for system monitoring

### Data Models
- **Match**: Football match information including teams, scores, and status
- **Team**: Team information including name, country, and league
- **Prediction**: Model predictions with probabilities for match outcomes
- **Features**: Feature data used for machine learning models
- **Odds**: Betting odds from various bookmakers
- **League**: League information

### Services
- **Prediction Service**: Core service for generating football match predictions using ML models
- **Data Collection**: Automated data collection from various sources
- **Feature Engineering**: Feature extraction and processing for ML models
- **Model Training**: ML model training and evaluation
- **Monitoring**: System and business metrics collection and reporting

## Development Tools
- **Makefile**: Complete development toolchain with 60+ commands
- **GitHub Issues Sync**: Bidirectional synchronization between local file and GitHub
- **Quality Checks**: Automated code quality tools (black, isort, flake8, mypy)
- **Testing**: Pytest with coverage reporting
- **CI Simulation**: Local CI environment using Docker Compose
- **Context Loading**: AI context loading for development assistance

## Key Environment Variables
- `DATABASE_URL`: PostgreSQL database connection string
- `REDIS_URL`: Redis connection URL
- `MLFLOW_TRACKING_URI`: MLflow tracking server URI
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers
- `API_KEY`: API key for external data sources
- Various Docker-specific variables in `.env.ci`

## Testing Strategy
- Unit tests for individual components
- Integration tests for service interactions
- End-to-end tests for complete workflows
- High test coverage target (96.35% currently achieved)
- Automated testing in CI pipeline

## Deployment Architecture
- Docker containers for all services
- Docker Compose for local development and testing
- Kubernetes-ready configurations
- Health checks and monitoring
- Automated scaling capabilities
- CI/CD pipeline with GitHub Actions

## Monitoring and Observability
- Prometheus metrics collection
- Grafana dashboards for visualization
- Health check endpoints
- Performance metrics
- Business metrics tracking
- Alerting mechanisms

## ML Pipeline
- Feature store with Feast
- Model training with scikit-learn/XGBoost
- Model registry with MLflow
- Model serving for predictions
- Model performance tracking
- Automated retraining capabilities
