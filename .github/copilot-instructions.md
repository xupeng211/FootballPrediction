# Football Prediction Project - GitHub Copilot Instructions

## Project Overview
This is an enterprise-grade football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows Domain-Driven Design (DDD) principles.

## Key Technologies
- **Backend**: FastAPI 0.115.6 with async/await
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Cache**: Redis 5.2.1
- **Task Queue**: Celery
- **Python**: 3.11+
- **Quality Tools**: Ruff (linting + formatting), MyPy (strict), pytest

## Development Workflow
1. Always use `make` commands from the Makefile
2. Run `make env-check` to validate environment
3. Use `make context` to load project state
4. Run `make ci` before committing

## Code Style
- Ruff handles both linting and formatting (NOT Black)
- Line length: 88 characters
- Follow existing patterns and conventions

## Testing
- Coverage threshold: 80%
- Use pytest markers appropriately
- 385 test cases across multiple categories

## Architecture
- Layered architecture: API, Application, Domain, Infrastructure
- Async/await patterns throughout
- CQRS pattern with event system
- Domain-driven design principles

## Key Commands
```bash
make install           # Install dependencies
make test              # Run all tests
make lint              # Run ruff + mypy
make fmt               # Format code with ruff
make coverage          # Generate coverage report
```

## Important Notes
- Never run pytest directly on individual files
- Always activate virtual environment
- Use Docker Compose for consistent environment
- Don't commit secrets or API keys
