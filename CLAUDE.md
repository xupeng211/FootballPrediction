# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📑 目录

- [Language Settings](#language-settings)
- [Quick Start](#quick-start)
- [Essential Commands](#essential-commands)
- [Development Principles](#development-principles)
- [Project Architecture](#project-architecture)
- [Important Documents](#important-documents)
- [Environment Management](#environment-management)
- [CI/CD System](#cicd-system)
- [Troubleshooting](#troubleshooting)

## Language Settings

**Please always reply in Chinese!**

- Language: Chinese (Simplified)
- Reply Language: Chinese
- Comment Language: Chinese
- Documentation Language: Chinese

## Quick Start

### For AI Tools - Essential Checklist

**Must execute on first entry**:
```bash
make install      # Install dependencies
make context      # Load project context ⭐most important
make env-check    # Verify environment health
make test-phase1  # Verify test environment (71 tests)
```

**After each code modification**:
```bash
make test-quick   # Quick test verification
make fmt && make lint  # Code formatting and quality check
make prepush      # Complete pre-push check
```

**If adding new dependencies**:
```bash
make smart-deps   # Smart dependency check and guidance
```

### 日常开发

```bash
make env-check    # 检查环境
make test-quick   # 快速测试
make fmt && make lint  # 代码格式化和检查
make prepush      # 提交前检查
```

## Essential Commands

### Must-Know Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `make help` | View all commands | When unsure |
| `make context` | Load project context | Before starting work |
| `make install` | Install dependencies | First time use |
| `make test-quick` | Quick tests (no coverage) | During development |
| `make test.unit` | Run only unit tests | Main testing method |
| `make coverage` | Run coverage tests (80% threshold) | CI requirement |
| `make ci` | Complete CI check | Before pushing |
| `./ci-verify.sh` | Docker CI verification | Before release |
| `make prepush` | Pre-push checks | Must run |
| `make fmt` | Code formatting | Before commit |
| `make lint` | Code quality check | Before commit |
| `make type-check` | Type checking | Before commit |
| `make lock-deps` | Lock dependency versions | After dependency updates |
| `make verify-deps` | Verify dependency consistency | Environment check |
| `make smart-deps` | Smart dependency check (with AI reminder) | After dependency changes |
| `make ai-deps-reminder` | Show dependency management reminder | When guidance needed |
| `make env-check` | Check development environment | Environment troubleshooting |
| `make coverage-local` | Local coverage check (60% threshold) | Daily development |
| `make coverage-ci` | CI coverage check (80% threshold) | Pre-push verification |

### Quick Reference

- Complete command list: [CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- Troubleshooting: [CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)

### Important Reminders

- **CI Verification**: Must run `./ci-verify.sh` before pushing to simulate complete CI environment
- **Docker Services**: Integration tests require `docker-compose up -d postgres redis`
- **Phase 1 Testing**: Use `make test-phase1` (not `make test.phase1`)
- **Coverage Warning**: Do NOT use `--cov=src` with single test files - shows misleading 0% coverage

## Development Principles

### Core Principles

1. **Documentation First**: Update documentation before modifying code
   - API changes → Update `docs/reference/API_REFERENCE.md`
   - Database changes → Update `docs/reference/DATABASE_SCHEMA.md`
   - Feature completion → Generate completion report
2. **Use Makefile**: Maintain command consistency
3. **Test-Driven**: Ensure test coverage (target ≥80%)
4. **Modify Over Create**: Prioritize modifying existing files

### Critical Testing Reminders

**AI Programming Tools Pay Special Attention**:

1. **DO NOT use `--cov=src` with single test files** - This shows misleading 0% coverage
2. **Phase 1 Testing is Complete**:
   - data.py: 17 tests, 90% coverage
   - features.py: 27 tests, 88% coverage
   - predictions.py: 27 tests, 88% coverage
   - **Total**: 71 test cases
3. **Use Correct Commands**:
   ```bash
   make test-phase1    # Phase 1 core tests
   make test-quick     # Quick tests
   make coverage       # Complete coverage
   ```

### Documentation Automation Rules

According to `docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md`:

- **API changes** → Update `docs/reference/API_REFERENCE.md`
- **Database changes** → Update `docs/reference/DATABASE_SCHEMA.md`
- **Stage completion** → Generate completion report
- **Bug fixes** → Create bugfix report

## Project Architecture

### Tech Stack

- **Python Version**: 3.11+ (project requirement)
- **Framework**: FastAPI + SQLAlchemy 2.0
- **Database**: PostgreSQL (production) + SQLite (testing)
- **Cache**: Redis
- **Task Queue**: Celery
- **MLOps**: MLflow + Feast
- **Monitoring**: Prometheus/Grafana
- **Testing**: pytest (96.35% coverage)
- **Code Quality**: black, flake8, mypy, bandit

### 项目结构

```
src/
├── api/           # FastAPI路由和端点
├── cache/         # Redis缓存管理
├── config/        # 配置管理（环境变量、设置）
├── core/          # 核心业务逻辑
├── data/          # 数据处理和ETL
├── database/      # SQLAlchemy模型和数据库连接
├── features/      # 特征工程
├── lineage/       # 数据血缘追踪
├── locales/       # 国际化支持
├── middleware/    # FastAPI中间件（认证、CORS等）
├── models/        # 预测模型
├── monitoring/    # 监控和指标
├── scheduler/     # 任务调度
├── services/      # 业务服务层
├── streaming/     # 实时数据流
├── stubs/         # 类型存根
├── tasks/         # 异步任务
└── utils/         # 通用工具函数

tests/ (96.35%覆盖率)
├── unit/          # 单元测试 ⭐主要使用
│   ├── api/       # API单元测试
│   ├── database/  # 数据库测试
│   ├── services/  # 服务测试
│   └── utils/     # 工具测试
├── integration/   # 集成测试
├── e2e/          # 端到端测试
├── factories/    # 测试数据工厂
├── fixtures/     # 测试夹具
├── helpers/      # 测试辅助函数
└── legacy/       # 遗留测试（默认排除）

scripts/          # 辅助脚本（自动化工具）
├── dependency/   # 依赖管理（lock、verify、audit）
├── testing/      # 测试工具（performance、optimization）
├── security/     # 安全工具（漏洞扫描、审计）
├── welcome.sh    # 新开发者自动引导
└── check-test-usage.sh  # 测试命令检查
```

### Core Module Description

- **api/**: FastAPI routes and endpoint definitions
  - `data.py` - Data API endpoints (17 tests)
  - `features.py` - Feature engineering API (27 tests)
  - `predictions.py` - Prediction API (27 tests)
  - `health.py` - Health check endpoints

- **config/**: Configuration management, including environment variables and settings
  - Uses Pydantic for configuration validation
  - Supports multi-environment configuration (dev/prod/ci)

- **database/**: SQLAlchemy models, database connections, and session management
  - Uses PostgreSQL (production) and SQLite (testing)
  - Supports database migrations

- **utils/**: Common utility functions (internationalization, dictionary operations, etc.)
  - `time_utils.py` - Time processing utilities
  - `crypto_utils.py` - Encryption utilities
  - `dict_utils.py` - Dictionary operation utilities

- **middleware/**: FastAPI middleware (authentication, CORS, logging, etc.)
  - Authentication middleware
  - CORS middleware
  - Request logging middleware

### 5-Minute Architecture Understanding

For AI tools needing to quickly understand project architecture:

1. **Entry Point**: `src/main.py` - FastAPI application startup
2. **Route Registration**: `src/api/` - All API endpoints
3. **Data Layer**: `src/database/models/` - SQLAlchemy models
4. **Business Logic**: `src/services/` - Core business services
5. **Configuration Center**: `src/core/config.py` - Environment configuration

**Data Flow**:
```
Request → API Routes → Business Service → Database → Response
    ↓
   Logging/Monitoring
```

## Important Documents

### Document Index

- [Document Home](docs/INDEX.md) - Complete document list
- [AI Development Rules](docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md) - Must read
- [Testing Guide](docs/testing/) - Testing strategy
- [Architecture Documentation](docs/architecture/) - System design
- [Operations Manual](docs/ops/) - Deployment and operations

### API and Reference

- [API Documentation](docs/reference/API_REFERENCE.md)
- [Database Schema](docs/reference/DATABASE_SCHEMA.md)
- [Development Guide](docs/reference/DEVELOPMENT_GUIDE.md)

## Development Workflow

### New Feature Development

1. `make context` - Understand project status
2. Update relevant documentation (important!)
3. Write code
4. `make test-quick` - Test
5. `make fmt && make lint` - Code formatting and standards
6. `make coverage-local` - Local coverage check
7. `make prepush` - Pre-push check (triggers CI)

### Running Single Tests

⚠️ **Important Warning**: DO NOT use `--cov=src` with single test files - this shows misleading 0% coverage!

```bash
# ✅ Correct: Run specific test file (without coverage)
pytest tests/unit/api/test_health.py -v

# ✅ Correct: Run specific test function
pytest tests/unit/api/test_health.py::test_health_endpoint -v

# ✅ Correct: Run tests with markers
pytest -m "unit and not slow" --cov=src

# ❌ Wrong: Single file + coverage (will show 0%!)
# pytest tests/unit/api/test_health.py --cov=src  # Don't do this!

# Debug mode tests
pytest tests/unit/api/test_health.py -v -s --tb=long

# Run only last failed tests
pytest --lf

# Parallel tests (requires pytest-xdist)
pytest tests/ -n auto

# Generate HTML coverage report
make cov.html
# View report: open htmlcov/index.html
```

### Bug Fixes

1. Check Issue Tracker issues
2. Understand failure reasons
3. Fix code
4. Add tests
5. Push fix (CI runs automatically)

## Important Notes

### Testing Strategy

- **Primarily use unit tests**: `tests/unit/` directory contains 96.35% coverage tests
- **Test marking system**:
  - `unit` - Unit tests (primary)
  - `integration` - Integration tests (to be rebuilt)
  - `e2e` - End-to-end tests
  - `slow` - Slow tests
  - `legacy` - Legacy tests (excluded by default)
- **Coverage requirements**: CI requires 80%, local development 20-60% is acceptable

### Environment Management

#### Virtual Environment
- **Directory**: `.venv/` (automatically managed via Makefile)
- **Python Version**: 3.11+
- **Activation**: `source .venv/bin/activate` or use Makefile commands for automatic activation

#### Service Dependencies
```bash
# Core services (must start)
docker-compose up -d postgres redis  # Database and cache

# Optional services (start on demand)
docker-compose --profile mlflow up    # MLflow model management
docker-compose --profile celery up    # Celery task queue
docker-compose up nginx               # Nginx reverse proxy (no profile)
```

#### Environment Configuration
- **Development Environment**: `.env` (contains debugging and development settings)
- **Production Environment**: `.env.production` (security settings)
- **CI Environment**: `.env.ci` (CI-specific configuration)
- **Example Configuration**: `.env.example` (template file)

#### Environment Check Commands
```bash
make env-check      # Complete environment health check
make check-services # Check Docker service status
make check-ports    # Check port usage
```

### Database Operations

```bash
# Start database services
docker-compose up -d postgres redis

# Check service status
docker-compose ps

# View service logs
docker-compose logs -f

# Stop services
docker-compose down

# Use profiles to start additional services
docker-compose --profile mlflow up   # Start MLflow
docker-compose --profile celery up   # Start Celery task queue
```

### Dependency Management

Adopts a **layered dependency management** approach to ensure environment isolation and production stability:

#### Dependency Hierarchy

```
requirements/
├── base.in/.lock      # Python base version (3.11+)
├── core.txt           # Core runtime dependencies (FastAPI, SQLAlchemy, etc.)
├── ml.txt             # Machine learning dependencies (scikit-learn, pandas, etc.)
├── api.txt            # API service dependencies (uvicorn, pydantic, etc.)
├── dev.in/.lock       # Development tool dependencies (pytest, black, mypy, etc.)
├── production.txt     # Production environment (core + ml + api)
├── development.txt     # Development environment (production + dev)
└── requirements.lock  # Complete lock file (all dependencies)
```

#### Core Commands

```bash
# Install dependencies (first time use)
make install           # Install from requirements.lock

# Lock dependency versions (after dependency changes)
make lock-deps         # Generate all .lock files

# Verify dependency consistency
make verify-deps       # Check if current environment matches lock files

# Reproducible builds
make install-locked    # Force reinstall from lock files

# Dependency analysis and audit
make audit-deps        # Scan for security vulnerabilities
make analyze-deps      # Analyze dependency conflicts
```

#### Environment Management Principles

1. **Development Environment**: Includes all dependencies (dev + test + lint)
2. **Production Environment**: Only includes runtime dependencies (core + ml + api)
3. **Version Locking**: All dependency versions precisely locked
4. **Security Auditing**: Regularly scan for dependency vulnerabilities

## CI/CD System

### Must-Follow Rules

```bash
# Must run before committing
make prepush
# or
./ci-verify.sh
```

### Docker CI Verification

- **Before pushing**: Must execute `./ci-verify.sh` to verify CI compatibility
- **Environment Consistency**: Exactly matches GitHub Actions CI environment
- **Dependency Verification**: Ensure `requirements.lock` works properly in CI environment
- **Service Testing**: Run complete tests under PostgreSQL and Redis services

### CI Failure Handling

- Issue Tracker automatically creates issues
- Issues contain detailed error information
- Automatically closes after fixes

## Troubleshooting

### Quick Diagnostics

```bash
# Environment issues
make env-check

# View all commands
make help

# Test failures
cat htmlcov/index.html  # View coverage report

# CI issues
./ci-verify.sh  # Local verification

# Check mypy errors
make type-check  # or mypy src --ignore-missing-imports

# Check Docker service status
docker-compose ps

# Check port usage
netstat -tulpn | grep :5432  # PostgreSQL
netstat -tulpn | grep :6379  # Redis
netstat -tulpn | grep :8000  # FastAPI application
```

### Common Issues

- **Test failures**: See [Troubleshooting Guide](CLAUDE_TROUBLESHOOTING.md)
- **Commands not working**: Run `make help`
- **Environment issues**: Run `make env-check`
- **Dependency issues**: Check `requirements.lock.txt` or run `make verify-deps`
- **Docker issues**: Ensure `docker-compose up -d`
- **Insufficient coverage**: Run `make cov.html` for detailed report
- **Type check failures**: Run `make type-check` for specific errors
- **Code formatting issues**: Run `make fmt` for automatic fixes
- **CI failures**: Check GitHub Actions logs, run `./ci-verify.sh` locally
- **Port conflicts**: Modify port configuration in `.env` file

## AI Tool Usage Tips

### Efficient Workflow

1. **Before starting work**:
   ```bash
   make context      # Load project context
   make env-check    # Verify environment health
   ```

2. **Testing Strategy**:
   - Use `make test-phase1` instead of single file testing
   - When running single tests, DO NOT add `--cov=src`
   - Prioritize using `make test-quick` for quick verification

3. **Before code generation**:
   - First review existing code patterns
   - Use same imports and structure
   - Follow existing naming conventions

4. **Dependency operations**:
   - Never directly modify `.lock` files
   - **Recommended**: `python scripts/dependency/add_dependency.py <package>`
   - Manual operation: Edit `.in` files then run `make lock-deps`
   - Use `make verify-deps` to verify consistency
   - **Absolutely not**: Directly run `pip install <package>`

   > 💡 **AI Tool Special Reminder**: After introducing new dependencies, run `make smart-deps` for intelligent guidance

### Common Pattern Recognition

1. **Test file pattern**:
   ```python
   # Correct import pattern
   from unittest.mock import Mock, patch
   import pytest
   from src.api.module import function_to_test

   class TestModuleName:
       @pytest.mark.unit
       def test_function_name(self, mock_fixture):
           # Test logic
           pass
   ```

2. **API route pattern**:
   ```python
   # FastAPI route standard pattern
   from fastapi import APIRouter, Depends
   from src.core.logger import logger

   router = APIRouter(prefix="/api/v1", tags=["module"])

   @router.get("/endpoint")
   async def get_endpoint():
       logger.info("Getting endpoint")
       return {"status": "ok"}
   ```

3. **Database operation pattern**:
   ```python
   # SQLAlchemy standard pattern
   from sqlalchemy.orm import Session
   from src.database.models import Model

   def get_items(db: Session):
       return db.query(Model).all()
   ```

### Quick Diagnostic Commands

```bash
# Check why tests failed
pytest tests/unit/api/test_xxx.py -v -s --tb=long

# See which code lacks tests
make cov.html && open htmlcov/index.html

# Check type errors
make type-check

# Verify all environment configuration
make env-check
```

### Pre-push Checklist

Before pushing code, AI tools should:
1. ✅ Run `make test-quick` to verify tests
2. ✅ Run `make fmt` to format code
3. ✅ Run `make lint` to check quality
4. ✅ Run `make type-check` for type checking
5. ✅ Run `make verify-deps` to verify dependencies
6. ✅ Run `make prepush` for complete check

### Performance Tips

- Use `pytest -x` to stop at first failure
- Use `pytest --lf` to run only last failed tests
- Use `pytest -k "keyword"` to filter tests
- Avoid running slow tests in CI (use `-m "not slow"`)

## Support

- Quick reference: [CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- Troubleshooting: [CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)
- Complete documentation: [docs/](docs/)

---

# Important Instruction Reminder

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files unless explicitly requested.