---
name: code-quality
description: Manage code quality for Football Prediction project using Make commands. Use when running quality checks, formatting code, running tests, or preparing for commits. Supports black, flake8, mypy, bandit, pytest, and coverage tools.
---

# Code Quality Management Skill

## Overview
This skill helps maintain code quality standards for the Football Prediction project through automated quality checks and fixes.

## Quick Commands

### Essential Quality Checks
```bash
make quality          # Run all quality checks
make test            # Run unit tests
make coverage        # Run tests with coverage report
make ci              # Complete CI simulation
```

### Code Formatting
```bash
make format          # Format code with black
make fix             # Quick fix: format + lint
```

### Specific Checks
```bash
make lint           # Run flake8 linting
make typecheck      # Run mypy type checking
make security       # Run bandit security scan
make complexity     # Run code complexity analysis
make deadcode       # Run dead code detection
```

### Pre-commit Workflow
```bash
make prepush        # Complete pre-commit check
./ci-verify.sh      # Local CI verification
```

## Project-Specific Quality Standards

### Architecture Requirements
- **async-first design**: All database operations must be async
- **Service Layer v2.0**: Use the service layer architecture
- **Type safety**: Strict mypy type checking required
- **Test coverage**: Minimum 80% coverage target

### Key Directories
- `src/ml/features/` - ML feature engineering modules
- `src/services/` - Service layer implementation
- `src/api/` - FastAPI routers and endpoints
- `src/ml/inference/` - ML inference layer

### Test Categories
- `tests/v2/` - V2 architecture tests (highest priority)
- `tests/unit/` - Unit tests for business logic
- `tests/integration/` - Database and API integration tests
- `tests/e2e/` - End-to-end workflow tests
- `tests/performance/` - Performance and load tests

## Quality Targets
- **Test Coverage**: 80%+
- **Response Time**: <100ms for predictions
- **Cache Hit Rate**: >80%
- **Code Quality**: Pass all make quality checks
- **Type Checking**: Strict mode with no errors

## Common Workflows

### Before Committing
1. Run `make quality` to check all quality standards
2. Run `make test` to ensure tests pass
3. Run `make coverage` to verify coverage
4. Use `make prepush` for final validation

### CI/CD Integration
- All checks run automatically in GitHub Actions
- Use `./ci-verify.sh` for local pre-CI validation
- Docker-based testing with `./scripts/docker-manager.sh test`

### Troubleshooting
- **V2 Tests Skipping**: Ensure Docker services are running
- **Type Errors**: Check imports and type annotations
- **Test Failures**: Verify database connectivity
- **Coverage Drops**: Add tests for new code paths

## Monitoring and Reporting
- **Coverage Report**: `htmlcov/index.html`
- **Quality Metrics**: Grafana dashboard at http://localhost:3000
- **CI Status**: Real-time monitoring available

## Related Skills
- `docker-devops`: Docker and DevOps best practices
- `fastapi-development`: FastAPI async API development
- `api-testing`: API testing (FastAPI endpoints)

## Integration with Development Environment
This skill integrates with:
- VS Code/Cursor IDE extensions
- Git pre-commit hooks
- GitHub Actions CI/CD
- Docker development environment