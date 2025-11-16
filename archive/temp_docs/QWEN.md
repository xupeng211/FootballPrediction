# Qwen Code - Football Prediction Project

## Project Overview

The Football Prediction project is an enterprise-level football match result prediction system built with modern Python technologies. It's built on FastAPI and incorporates a comprehensive development infrastructure with best practices for code quality, testing, and deployment.

**Key Technologies:**
- **Web Framework:** FastAPI
- **Database:** PostgreSQL with SQLAlchemy
- **Caching:** Redis
- **ML Framework:** Custom machine learning components
- **Containerization:** Docker + docker-compose
- **Testing:** pytest with extensive coverage
- **Code Quality:** ruff, mypy, black, pre-commit hooks

**Project Maturity:** Production-ready with continuous improvement methodology.

## Architecture

The project follows a clean architecture with a clear separation of concerns:

```
src/
├── adapters/           # External service adapters
├── api/               # API endpoints and routers
├── cache/             # Caching implementations
├── collectors/        # Data collection services
├── common/            # Shared utilities
├── config/            # Configuration modules
├── core/              # Core business logic
├── cqrs/              # CQRS pattern implementation
├── data/              # Data access and processing
├── database/          # Database connection and models
├── decorators/        # Custom decorators
├── dependencies/      # Dependency injection
├── domain/            # Domain models and services
├── events/            # Event-driven architecture
├── facades/           # Facade pattern implementations
├── features/          # Feature-specific modules
├── ml/                # Machine learning components
├── models/            # Data models
├── monitoring/        # Monitoring and metrics
├── patterns/          # Design pattern implementations
├── performance/       # Performance monitoring
├── realtime/          # Real-time processing
├── repositories/      # Repository pattern implementations
├── scheduler/         # Task scheduling
├── security/          # Security implementations
├── services/          # Business services
├── streaming/         # Data streaming
├── tasks/             # Background tasks
├── utils/             # Utility functions
└── main.py            # Application entry point
```

## Building and Running

### Prerequisites
- Python 3.11+
- Docker and docker-compose
- Make

### Quick Start

1. **Clone the project:**
   ```bash
   git clone https://github.com/xupeng211/FootballPrediction.git
   cd FootballPrediction
   ```

2. **Initialize environment:**
   ```bash
   make install      # Install dependencies
   make dev-setup    # Complete development setup
   make context      # Load project context
   ```

3. **Run tests:**
   ```bash
   make test         # Run all tests
   make coverage     # Run tests with coverage report
   ```

4. **Run the application:**
   ```bash
   # Using Make (recommended):
   make up           # Start with docker-compose

   # Or directly with Python:
   python -m src.main
   ```

### Development Commands

- `make help` - Show all available commands
- `make install` - Install dependencies
- `make lint` - Run code quality checks
- `make test` - Run all tests
- `make coverage` - Run tests with coverage
- `make ci` - Run local CI simulation
- `make sync-issues` - Sync GitHub issues
- `make prepush` - Run pre-push quality gate

### Docker Commands

- `make up` - Start services with docker-compose
- `make down` - Stop services
- `make logs` - View service logs
- `make build` - Build Docker image

## Testing

The project has extensive test coverage with 385+ passing tests achieving ~96.35% coverage:

- **Unit tests** - Testing individual functions and classes
- **Integration tests** - Testing component interactions
- **API tests** - Testing HTTP endpoints
- **End-to-end tests** - Full user flow validation
- **Performance tests** - Benchmarking and load testing

### Test Commands

- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-phase1` - Run core API tests
- `make coverage-fast` - Run fast coverage tests
- `make test-containers` - Run tests with TestContainers

## Development Conventions

### Code Quality
- Follow PEP 8 style guidelines (enforced by ruff)
- Type annotations required (enforced by mypy)
- Pre-commit hooks run on every commit
- Test coverage threshold of 80% for CI

### Git Workflow
- Use feature branches for new functionality
- Run `make prepush` before pushing changes
- Follow conventional commit messages
- Pre-commit hooks ensure code quality

### Documentation
- Code should be self-documenting with clear function names
- API endpoints have OpenAPI documentation
- Configuration options are documented

### Architecture Principles
- Follow SOLID principles
- Use design patterns where appropriate (Repository, CQRS, Observer, etc.)
- Separate domain logic from infrastructure concerns
- Implement proper error handling and logging

## Infrastructure and Services

- **Database:** PostgreSQL with Alembic for migrations
- **Cache:** Redis for caching and session storage
- **API Gateway:** Nginx reverse proxy
- **Monitoring:** Prometheus metrics collection
- **Security:** JWT authentication, rate limiting, input validation
- **Background Tasks:** Celery for async job processing

## Project Reports and Status

The project includes comprehensive documentation of its status:
- Deployment readiness assessment reports
- Test coverage analysis
- Technical debt cleanup plans
- Security audit reports
- Performance monitoring reports

## MLOps Pipeline

The project includes an MLOps pipeline with:
- Model performance monitoring
- Prediction feedback loop
- Automated retraining triggers
- Performance reporting

## Best Practices

- Comprehensive type checking with mypy
- Code formatting with ruff
- Security scanning with bandit and safety
- Dependency vulnerability checks
- Automated testing with pytest
- Container-based deployment
- CI/CD pipeline simulation

## Communication Protocol

All responses from Qwen Code should be in **简体中文 (Simplified Chinese)** when communicating with the user.
