# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
make install          # Install dependencies and create virtual environment
make env-check        # Verify environment is properly configured
make dev              # Quick development environment setup
```

### Testing and Quality
```bash
make test             # Run unit tests (385 tests, requires 80%+ coverage)
make coverage         # Run tests with coverage report
make ci               # Complete CI simulation (env-check, quality, test, coverage)
make ci-local         # Local CI matching remote GitHub Actions
./ci-verify.sh        # Local CI verification script
```

### Code Quality
```bash
make format           # Format code with black
make lint             # Run flake8 linting
make typecheck        # Run mypy type checking
make security         # Run bandit security scan
make quality          # Run all quality checks (format, lint, typecheck, security)
```

### Local Development
```bash
docker-compose up --build    # Start full development stack
docker-compose ps            # Check service status
docker-compose logs app      # View application logs
make status                  # View project overview and statistics
```

## Architecture Overview

### Core Architecture Pattern
**Domain-Driven Design + CQRS + Event-Driven + Async-First**

The system implements clean architecture with strict separation of concerns:
- **Domain Layer**: Pure business logic (entities, events, repositories interfaces)
- **Application Layer**: Services orchestration and use cases
- **Infrastructure Layer**: Database, cache, external API implementations
- **Presentation Layer**: FastAPI routers and HTTP handling

### Key Architectural Components

#### CQRS System
- **Command Bus**: Handles write operations (create, update, delete)
- **Query Bus**: Handles read operations with optimization
- **Event Bus**: Manages domain events and notifications
- Located in `src/cqrs/` with handlers in `src/cqrs/handlers/`

#### Database Architecture
- **ORM**: SQLAlchemy 2.0+ with async support
- **Connection**: Read-write separation with connection pooling
- **Migrations**: Alembic-based schema management in `src/database/migrations/`
- **Repositories**: Implementation of domain repository interfaces in `src/database/repositories/`

#### Machine Learning Pipeline
- **Inference Service**: Singleton pattern in `src/core/prediction_engine.py`
- **Models**: XGBoost 2.0+ with ensemble strategies in `src/ml/`
- **Feature Store**: Real-time feature extraction and caching
- **Model Management**: Versioned model files with health monitoring

#### Caching Strategy
- **Redis Manager**: Enhanced connection management in `src/cache/redis_manager.py`
- **Multi-layer**: Application, database, and HTTP-level caching
- **TTL Management**: Intelligent cache expiration strategies
- **Cluster Support**: Redis clustering for high availability

#### Streaming Infrastructure
- **Kafka Integration**: Producer/consumer implementations in `src/streaming/`
- **WebSocket Support**: Real-time API communication
- **Event Sourcing**: CQRS event storage and replay capabilities

## Project Structure

```
FootballPrediction/
├── src/
│   ├── api/              # FastAPI routers and HTTP endpoints
│   ├── domain/           # Domain entities, events, repository interfaces
│   ├── services/         # Application services and use cases
│   ├── database/         # SQLAlchemy models, migrations, repositories
│   ├── cqrs/            # Command Query Responsibility Segregation
│   ├── ml/              # Machine learning models and inference
│   ├── cache/           # Caching layer and Redis management
│   ├── streaming/       # Kafka and real-time processing
│   ├── adapters/        # External API integrations
│   ├── core/            # DI container, logging, exceptions
│   └── utils/           # Shared utilities
├── tests/               # Comprehensive test suite (385 tests)
├── microservices/       # Microservice implementations
├── config/              # Configuration management
├── monitoring/          # Health checks and metrics
└── scripts/             # Development and CI scripts
```

## Development Guidelines

### Code Organization
- All code must follow async-first design patterns
- Use dependency injection through `src/core/di.py`
- Repository interfaces defined in domain, implemented in database layer
- All database operations must be async
- External API calls should use the adapter pattern

### Testing Strategy
- Unit tests for all business logic in `tests/unit/`
- Integration tests for database and external APIs in `tests/integration/`
- End-to-end tests for complete workflows in `tests/e2e/`
- Performance tests in `tests/performance/`
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

### Configuration Management
- Environment-specific configs in `.env.ci`, `.env.production`
- Database connection settings in `config/database_pool_config.py`
- Cache strategy configuration in `config/cache_strategy_config.py`
- API optimization settings in `config/api_optimization_config.py`

### Error Handling
- Custom exceptions defined in `src/core/exceptions.py`
- Comprehensive error logging with structured logging
- Fallback strategies for external dependencies
- Circuit breaker pattern for external API calls

## Key Technologies

- **FastAPI 0.104+**: High-performance async web framework
- **SQLAlchemy 2.0+**: Modern async ORM with advanced features
- **PostgreSQL 15**: Primary database with JSON support
- **Redis 5.0+**: Caching and session management
- **XGBoost 2.0+**: Machine learning models
- **Kafka**: Event streaming platform
- **Docker**: Containerization and orchestration

## Performance Considerations

### Database Optimization
- Read-write separation with dedicated connection pools
- Optimized queries with proper indexing
- Batch operations for bulk data processing
- Connection pooling with health checks

### Caching Strategy
- Multi-level caching (application, database, HTTP)
- Intelligent cache warming on startup
- Cache invalidation strategies for data consistency
- Redis clustering for high availability

### API Performance
- Async request handling throughout
- Rate limiting with Redis backend
- Response compression and optimization
- Prometheus metrics for monitoring

## Security Practices

- Input validation through Pydantic models
- SQL injection prevention via ORM
- Authentication and authorization middleware
- Security scanning with bandit
- Dependency vulnerability checks with safety

## Monitoring and Observability

- Structured logging with correlation IDs
- Health checks at multiple levels (`/health`, `/health/database`)
- Prometheus metrics exposure
- Performance monitoring with response time tracking
- Error tracking and alerting

## Working with the Codebase

### Adding New Features
1. Define domain entities in `src/domain/entities.py`
2. Create repository interfaces in domain layer
3. Implement repositories in `src/database/repositories/`
4. Add application services in `src/services/`
5. Create API endpoints in `src/api/`
6. Write comprehensive tests
7. Run `make ci` before submitting

### Database Changes
1. Create Alembic migration in `src/database/migrations/`
2. Update SQLAlchemy models in `src/database/models/`
3. Run `docker-compose exec app alembic upgrade head`
4. Update repository implementations as needed

### Machine Learning Updates
1. Update models in `src/ml/models/`
2. Modify inference service in `src/core/prediction_engine.py`
3. Update feature engineering pipeline
4. Run performance validation tests

### Adding External APIs
1. Create adapter in `src/adapters/`
2. Define interface in domain layer
3. Implement configuration management
4. Add error handling and retry logic
5. Write integration tests