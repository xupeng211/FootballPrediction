# CI/CD Pipeline Setup Instructions

## Environment Variables Required

Add the following secrets to your GitHub repository settings:

### Docker Registry
- `DOCKER_USERNAME`: Docker Hub username
- `DOCKER_PASSWORD`: Docker Hub password or access token

### Database Configuration
- `DB_USER`: PostgreSQL username (default: `test_user`)
- `DB_PASSWORD`: PostgreSQL password (default: `test_password`)

### Optional Notifications
- `SLACK_WEBHOOK_URL`: Slack webhook for notifications

## Pre-commit Setup

```bash
# Install pre-commit hooks
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

## Pipeline Overview

### Jobs Overview
1. **quality**: Code formatting, linting, and type checking
2. **security**: Security scanning with Bandit, Safety, and Trivy
3. **test**: Unit, integration, and E2E tests with coverage
4. **build**: Docker build and push (main branch only)
5. **deploy**: Production deployment (releases only)
6. **notify-failure**: Failure notifications

### Coverage Requirements
- Unit tests: 85% minimum
- Integration tests: 80% minimum
- E2E tests: 75% minimum

### Service Containers
- PostgreSQL 15 on port 5432
- Redis 7 on port 6379

## Local Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run quality checks
make quality

# Run tests with coverage
make test

# Run security scan
make security
```