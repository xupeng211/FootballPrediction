# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

## Project Overview

This is a football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows enterprise-grade architecture patterns with Domain-Driven Design (DDD), CQRS, and microservices principles.

**Key Metrics:**
- Test Coverage: 96.35% (target: >=80%)
- Code Quality: A+ (Ruff + MyPy compliant)
- Python 3.11+ required
- 385 test cases

## Development Environment Setup

### Quick Start (5 minutes)
```bash
make install      # Install dependencies and create venv
make context      # Load project context (⭐ most important)
make test         # Run all tests (385 tests)
make coverage     # View coverage report (96.35%)
```

### Essential Commands
```bash
make help         # Show all available commands
make env-check    # Check development environment health
make lint         # Run ruff and mypy checks
make fmt          # Format code with ruff
make ci           # Simulate complete CI pipeline
make prepush      # Complete pre-push validation
```

## Testing Strategy

### Test Execution Rules
- **ALWAYS use Makefile commands** - never run pytest directly on single files
- Test environment is isolated with Docker containers
- Coverage threshold is enforced (80% minimum, currently 96.35%)

### Test Categories
```bash
make test-phase1      # Core API tests (data, features, predictions)
make test.unit        # Unit tests only
make test.int         # Integration tests
make test.e2e         # End-to-end tests
make coverage-fast    # Quick coverage (unit tests only)
```

### Test Environment Management
```bash
make test-env-start   # Start test environment with Docker
make test-env-stop    # Stop test environment
make test-all         # Run all tests in isolated environment
```

## Architecture

### Core Layers
1. **API Layer** (`src/api/`): FastAPI routes, dependencies, CQRS implementation
2. **Domain Layer** (`src/domain/`): Business models, services, value objects
3. **Infrastructure Layer** (`src/database/`, `src/cache/`): PostgreSQL, Redis, repositories
4. **Service Layer** (`src/services/`): Business logic implementation

### Key Patterns
- **Repository Pattern**: Data access abstraction in `src/database/repositories/`
- **CQRS**: Command/Query separation in `src/api/cqrs.py`
- **Dependency Injection**: Container-based DI in `src/core/di.py`
- **Observer Pattern**: Event system in `src/observers/`

### Database Architecture
- **PostgreSQL**: Primary database with SQLAlchemy 2.0 async ORM
- **Redis**: Caching and session storage
- **Connection Pooling**: Efficient connection management
- **Migrations**: Alembic for schema management

## Code Quality Standards

### Style Guide
- **Ruff**: Primary linter and formatter (line length: 88)
- **MyPy**: Type checking (zero tolerance for type errors)
- **Double quotes**: Standard string quoting
- **Type annotations**: Required for all public functions

### Quality Gates
```bash
make lint           # Must pass without errors
make type-check     # MyPy must be clean
make coverage       # >=80% threshold enforced
make prepush        # All quality checks combined
```

## Container Management

### Development Environment
```bash
make up             # Start docker-compose services
make down           # Stop services
make logs           # View logs
make deploy         # Build with immutable git-sha tag
make rollback TAG=<sha>  # Rollback to previous tag
```

### Services Architecture
- **app**: Main FastAPI application
- **db**: PostgreSQL database with health checks
- **redis**: Redis cache service
- **nginx**: Reverse proxy and load balancer

## CI/CD Pipeline

### Local Validation
```bash
./ci-verify.sh      # Complete local CI validation
make ci             # Simulate GitHub Actions CI
```

### Quality Checks
1. **Security**: bandit vulnerability scan
2. **Dependencies**: pip-audit for vulnerable packages
3. **Code**: Ruff + MyPy strict checking
4. **Tests**: 385 test cases with coverage enforcement
5. **Build**: Docker image building and testing

## MLOps and Model Management

### Prediction Feedback Loop
```bash
make feedback-update    # Update predictions with actual outcomes
make feedback-report    # Generate accuracy trends
make retrain-check      # Check models for retraining
make model-monitor      # Run enhanced model monitoring
```

### Complete Pipeline
```bash
make mlops-pipeline     # Run full MLOps feedback loop
make mlops-status       # Show pipeline status
```

## Documentation Standards

### Quality Requirements
- All docs must pass `make docs.check` (Docs Guard validation)
- Allowed directories: `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
- No orphaned documents - everything must be linked from INDEX.md

### Documentation Commands
```bash
make docs.check      # Validate documentation quality
make docs.fix        # Auto-fix documentation issues
make docs-all        # Generate all documentation
```

## Database Operations

### Management Commands
```bash
make db-init         # Initialize database with migrations
make db-migrate      # Run database migrations
make db-seed         # Seed initial data
make db-backup       # Create database backup
make db-reset        # Reset database (WARNING: deletes all data)
```

### Connection Management
- Uses async SQLAlchemy 2.0 with connection pooling
- Repository pattern for data access abstraction
- Automatic transaction management

## Security and Compliance

### Security Scanning
```bash
make security-check  # Run vulnerability scan
make audit           # Complete security audit
make secret-scan     # Scan for hardcoded secrets
```

### Security Features
- JWT token authentication
- RBAC permission control
- SQL injection protection
- XSS and CSRF protection
- HTTPS enforcement

## Performance Monitoring

### Performance Commands
```bash
make profile-app     # Profile application performance
make benchmark       # Run performance benchmarks
make flamegraph      # Generate performance flamegraph
```

### Monitoring Features
- Structured JSON logging
- Performance metrics collection
- Health check endpoints
- Real-time monitoring dashboard

## Development Workflow

### AI-Assisted Development
1. `make env-check` - Verify environment health
2. `make context` - Load project context for AI
3. Development and testing
4. `make ci` - Quality validation
5. `make prepush` - Final validation before push

### Best Practices
- Use dependency injection container
- Follow repository pattern for data access
- Implement proper error handling with custom exceptions
- Use async/await for I/O operations
- Write comprehensive unit and integration tests
- Use type annotations throughout

## Key Configuration Files

- `pyproject.toml`: Ruff configuration, tool settings
- `pytest.ini`: Test configuration and markers
- `requirements/requirements.lock`: Locked dependencies
- `Makefile`: Complete development toolchain (613 lines)
- `.env.example`: Environment variable template

## Troubleshooting

### Common Issues
- **Port conflicts**: Ensure ports 5432, 6379, 80 are available
- **Docker issues**: Check Docker daemon and docker-compose version
- **Test failures**: Verify test environment is properly set up
- **Coverage drops**: Run `make coverage-targeted MODULE=<module>`

### Debug Commands
```bash
make test-env-status    # Check test environment health
make env-check          # Verify development environment
make logs               # View service logs
```

## Project Status

- **Maturity**: Production-ready ⭐⭐⭐⭐⭐
- **Architecture**: Modern microservices with DDD
- **Testing**: 96.35% coverage with comprehensive test suite
- **CI/CD**: Full automation with quality gates
- **Documentation**: Complete with AI assistance

This system demonstrates enterprise-grade Python development with modern tools, practices, and comprehensive automation.
