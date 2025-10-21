# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

## Project Overview

This is a football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows enterprise-grade architecture patterns with Domain-Driven Design (DDD), CQRS, and microservices principles.

**Key Metrics:**
- Test Coverage: 22% (target: >=80%, currently improving)
- Code Quality: A+ (Ruff + MyPy compliant)
- Python 3.11+ required
- 385 test cases

## Development Environment Setup

### Quick Start (5 minutes)
```bash
make install      # Install dependencies and create venv
make context      # Load project context (⭐ most important)
make test         # Run all tests (385 tests)
make coverage     # View coverage report (22%)
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
- Coverage threshold is enforced (80% minimum, currently 22%, improving)

### Test Categories
```bash
make test-phase1      # Core API tests (data, features, predictions)
make test.unit        # Unit tests only
make test.int         # Integration tests
make test.e2e         # End-to-end tests
make coverage-fast    # Quick coverage (unit tests only)
```

### Test Markers (from pytest.ini)
- `unit`: 单元测试 - 测试单个函数或类
- `integration`: 集成测试 - 测试多个组件的交互
- `api`: API测试 - 测试HTTP端点
- `database`: 数据库测试 - 需要数据库连接
- `slow`: 慢速测试 - 运行时间较长的测试
- `critical`: 关键测试 - 必须通过的核心功能测试
- `e2e`: 端到端测试 - 完整的用户流程测试
- `performance`: 性能测试 - 基准测试和性能分析

**Usage Examples:**
```bash
pytest -m "unit"                    # Only unit tests
pytest -m "not slow"                # Skip slow tests
pytest -m "critical"                # Only critical tests
```

### Test Environment Management
```bash
make test-env-start   # Start test environment with Docker
make test-env-stop    # Stop test environment
make test-all         # Run all tests in isolated environment
```

### Running Single Test Files (Advanced)
While Makefile commands are preferred for regular development, you sometimes need to run single files:

```bash
# ✅ ALLOWED: Single file debugging
pytest tests/unit/api/test_health.py -v

# ✅ ALLOWED: With coverage for debugging
pytest tests/unit/api/test_health.py --cov=src --cov-report=term-missing

# ❌ NEVER: Add --cov-fail-under (breaks CI integration)
pytest tests/unit/api/test_health.py --cov=src --cov-fail-under=80

# ✅ RECOMMENDED: Use marker for focused testing
pytest tests/unit/api/test_health.py -v -m "not slow"
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
4. **Tests**: 385 test cases with coverage enforcement (currently 22%, target 80%)
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
- **CRITICAL**: Never use `--cov-fail-under` with single files - it breaks CI integration
- Use markers wisely: `-m "unit"` for unit tests only, `-m "not slow"` to skip slow tests

## Key Configuration Files

- `pyproject.toml`: Ruff configuration, tool settings
- `pytest.ini`: Test configuration and markers
- `requirements/requirements.lock`: Locked dependencies
- `Makefile`: Complete development toolchain (613 lines)
- `.env.example`: Environment variable template

## Important Development Notes

### ⚠️ Critical Test Rule
**NEVER add `--cov-fail-under` to single test file commands** - this breaks the CI pipeline integration. The project has a sophisticated coverage tracking system that only works correctly when coverage thresholds are managed centrally.

### 🎯 When to Break the Rules
While Makefile commands are preferred, these situations allow direct pytest usage:
- **Debugging specific test failures**
- **Working on isolated features**
- **Quick feedback during development**

Always use proper markers and avoid coverage thresholds in single-file commands.

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
- **Testing**: 22% coverage with comprehensive test suite (target: 80%)
- **CI/CD**: Full automation with quality gates
- **Documentation**: Complete with AI assistance

This system demonstrates enterprise-grade Python development with modern tools, practices, and comprehensive automation.
