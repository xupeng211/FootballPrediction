# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**项目类型**: 企业级足球预测系统 (Enterprise Football Prediction System)
**架构模式**: DDD + CQRS + Event-Driven + Async-First
**技术栈**: FastAPI 0.104+ + SQLAlchemy 2.0+ + Redis 7.0+ + PostgreSQL 15 + React 19.2.0 + TypeScript 4.9.5 + XGBoost 2.0+

## 🛠️ Core Development Commands

### Environment Setup
```bash
# 初始化开发环境 (首次使用必须)
make venv               # 创建虚拟环境
make install            # 安装所有依赖
make env-check          # 检查环境健康状态
make context            # 加载项目上下文到AI工作内存
```

### Code Quality & Testing
```bash
# 代码质量检查和修复
make lint               # Ruff代码检查
make fmt                # 代码格式化
make fix-code           # 一键修复代码质量问题
make type-check         # MyPy类型检查

# 测试执行 (关键命令)
make test.smart         # 快速冒烟测试 (<2分钟)
make test.unit          # 完整单元测试
make test.integration   # 集成测试
make test.all           # 所有测试
make coverage           # 覆盖率检查
make cov.html           # 生成HTML覆盖率报告
```

### Docker Development
```bash
# 轻量级全栈开发 (推荐)
make docker.up.lightweight    # 启动前端+后端+数据库+Redis
make docker.down.lightweight  # 停止轻量级环境

# 标准开发环境
make docker.up.dev      # 启动完整开发环境
make docker.logs.dev    # 查看应用日志
make docker.down.dev    # 停止开发环境
```

### Security & Validation
```bash
make security-check     # Bandit安全扫描
make audit              # 依赖安全审计
make ci-check          # 完整CI验证
```

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: FastAPI 0.121.2, SQLAlchemy 2.0.44, Pydantic v2+, Redis 7.0.1, PostgreSQL 15
- **Frontend**: React 19.2.0, TypeScript 4.9.5, Ant Design 5.27.6, Redux Toolkit 2.9.2
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+, MLflow 2.22.2+
- **Testing**: pytest 9.0.1+ with asyncio support (385 test cases)
- **Code Quality**: Ruff, MyPy, Bandit

### Clean Architecture Pattern
```
src/
├── api/           # FastAPI routers, HTTP concerns only
├── domain/        # Business logic, entities (pure Python)
├── services/      # Application services, orchestration
├── database/      # SQLAlchemy models, repositories
├── adapters/      # External API integrations
├── ml/           # Machine learning models and pipelines
├── cache/        # Redis caching layer
└── utils/        # Shared utilities
```

### Key Integration Points
- **Main Application**: `src/main.py` with 40+ API endpoints
- **ML Prediction Engine**: XGBoost models for match predictions
- **Real-time Features**: WebSocket support at `/api/v1/realtime/ws`
- **Caching**: Redis-based performance optimization
- **Database**: Async PostgreSQL with SQLAlchemy 2.0

### API Endpoints Structure
- **Health Checks**: `/health`, `/health/system`, `/health/database`
- **Predictions**: `/api/v1/predictions/`, `/api/v2/predictions/`
- **Data Management**: `/api/v1/data_management/`
- **System**: `/api/v1/system/`
- **Adapters**: `/api/v1/adapters/`
- **Monitoring**: `/metrics`

## 🧪 Testing Architecture

### Test Structure (385 test cases)
- **Unit Tests** (85%): Fast, isolated component testing
- **Integration Tests** (12%): Real dependency testing
- **E2E Tests** (2%): Complete user workflow testing
- **Performance Tests** (1%): Load and stress testing

### Standardized Test Markers
```python
@pytest.mark.unit           # Unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.critical       # Must-pass core functionality
@pytest.mark.smoke         # Basic functionality validation
@pytest.mark.slow          # Long-running tests (>30s)
@pytest.mark.api           # HTTP endpoint testing
@pytest.mark.database      # Database connection tests
@pytest.mark.ml            # Machine learning tests
```

### Recommended Testing Workflow
```bash
# 日常开发
make test.smart         # Quick validation (<2 minutes)

# 功能开发完成
make test.unit          # Full unit test suite
make coverage           # Coverage report generation

# 发布前验证
make test.all           # Complete test suite
make ci-check          # Full pipeline validation
```

## 🔧 Development Standards

### Code Style Requirements
- **Type Hints**: All functions must have complete type annotations
- **Async/Await**: All I/O operations must be async (database, external APIs)
- **Logging**: Use structured logging with `logger` (never use `print()`)
- **Error Handling**: Comprehensive exception handling with proper logging

### Function Template
```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_data(
    input_data: Dict[str, Any],
    *,
    timeout: Optional[int] = None,
    retry_count: int = 3
) -> ResultModel:
    """Process input data with async operations.

    Args:
        input_data: Dictionary containing input parameters
        timeout: Optional timeout in seconds
        retry_count: Number of retry attempts

    Returns:
        ResultModel: Processed result

    Raises:
        ValueError: When input data is invalid
        TimeoutError: When operation exceeds timeout
    """
    logger.info(f"Processing data: {len(input_data)} items")

    try:
        result = await database_service.fetch_data(input_data, timeout)
        logger.debug(f"Successfully processed {len(result)} items")
        return result
    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        raise
```

## 🐳 Docker Development

### Multi-Environment Support
- **Development**: `docker-compose.yml` (hot reload, debugging)
- **Lightweight**: `docker-compose.lightweight.yml` (full-stack minimal)
- **Production**: `docker-compose.prod.yml` (optimized, secure)

### Service Stack
- **app**: FastAPI application (ports: 8000)
- **frontend**: React application (ports: 3000, 3001)
- **db**: PostgreSQL 15 (port: 5432)
- **redis**: Redis 7.0 (port: 6379)
- **nginx**: Reverse proxy (production only)

### Container Development Features
- Hot reload with volume mounting
- Health checks for all services
- Environment-specific configurations
- Development vs production targets

## 🤖 Machine Learning Pipeline

### ML Architecture
- **Prediction Engine**: XGBoost 2.0+ gradient boosting models
- **Feature Engineering**: pandas 2.1+ and numpy 1.25+ data preprocessing
- **Model Training**: scikit-learn 1.3+ training pipelines
- **Model Management**: MLflow 2.22.2+ version control with security patches

### ML Service Integration
```python
# Inference service usage
from src.services.inference_service import inference_service

prediction_result = await inference_service.predict_match(match_id)
```

### Model Lifecycle
- Training: `src/ml/train_model.py`
- Validation: `src/ml/model_validation.py`
- Deployment: `src/ml/model_deployment.py`
- Monitoring: `src/ml/model_monitoring.py`

## 🚨 Crisis Management Tools

### Test Crisis Recovery
```bash
# When tests are failing (>30%)
make solve-test-crisis      # Automated test recovery
make emergency-fix          # Emergency code quality fixes
make syntax-fix            # Batch syntax error correction
```

### Environment Recovery
```bash
make env-restore           # Environment restoration
make create-env            # Create fresh environment files
make env-check             # Environment health check
```

### Code Quality Recovery
```bash
make smart-fix            # AI-driven quality improvements
make quality-guardian     # Continuous quality monitoring
make daily-quality        # Daily progressive optimization
```

## 🔄 Git Workflow

### Commit Message Format
```bash
# Features
feat(api): add user authentication endpoint
feat(ml): implement XGBoost prediction model

# Fixes
fix(database): resolve async connection timeout issue
fix(tests): restore 100+ core test functionality

# Quality
refactor(api): extract validation logic to service layer
style(core): apply ruff formatting to all files

# Maintenance
chore(deps): update FastAPI to 0.121.2
chore(security): upgrade MLflow to 2.22.2 for security patches
```

### Pre-Commit Checklist
- [ ] Tests pass: `make test.smart`
- [ ] Code quality: `make fix-code`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Full validation: `make ci-check`

## 📊 Current Project Status

### Quality Metrics
- **Test Coverage**: Use `make test.unit --cov=src --cov-report=term-missing`
- **Test Cases**: 385 active test cases across unit/integration/e2e
- **Code Quality**: Ruff + Black + Bandit validation passing
- **Security**: No critical vulnerabilities, ECDSA vulnerability patched
- **CI/CD**: Green pipeline with automated recovery

### Health Score
```
Overall Health: 85/100 ✅
├── Code Quality: 90/100 ✅
├── Testing: 70/100 ⚠️
├── Documentation: 95/100 ✅
├── Security: 95/100 ✅
├── CI/CD: 90/100 ✅
└── Dependencies: 90/100 ✅
```

## 🌐 Application URLs

### Development Access
- **Frontend**: http://localhost:3000 (React development server)
- **Backend API**: http://localhost:8000 (FastAPI application)
- **API Documentation**: http://localhost:8000/docs (Interactive OpenAPI)
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/system/status
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws

### Quality Dashboard
- **Quality Monitor**: http://localhost:3001 (Independent quality monitoring)

## 🚀 Quick Start for New Development

### 5-Minute Setup
```bash
# 1. Environment initialization
make venv && make install && make env-check

# 2. Load project context
make context

# 3. Validate setup
make test.smart && make lint

# 4. Start development
make docker.up.lightweight  # Full stack development
# OR
uvicorn src.main:app --reload  # Backend only
```

### First Development Tasks
1. Read `src/main.py` to understand the application structure
2. Review `pyproject.toml` for dependencies and tool configurations
3. Check `Makefile` for available development commands
4. Run `make test.smart` to verify the testing environment
5. Access API documentation at http://localhost:8000/docs

## 🔍 Common Development Patterns

### Database Operations (Async Only)
```python
# ✅ Correct: Async database operations
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ❌ Wrong: Sync database operations
user = db.query(User).filter(User.id == user_id).first()
```

### API Response Patterns
```python
from src.api.schemas import PredictionResponse

@app.get("/api/v1/predictions/{match_id}")
async def get_prediction(match_id: int) -> PredictionResponse:
    try:
        prediction = await inference_service.predict_match(match_id)
        return PredictionResponse(success=True, data=prediction)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Prediction service unavailable")
```

### Service Layer Integration
```python
# Service injection pattern
from src.services.prediction import PredictionService
from src.database.repositories import PredictionRepository

async def get_prediction_use_case(
    match_id: int,
    prediction_service: PredictionService,
    prediction_repo: PredictionRepository
) -> Dict[str, Any]:
    # Use case orchestration
    prediction = await prediction_service.generate_prediction(match_id)
    await prediction_repo.save_prediction(prediction)
    return prediction
```

## 📞 Troubleshooting Guide

### Common Issues
1. **Test Failures**: Run `make solve-test-crisis` immediately
2. **Type Errors**: Check imports and add missing type hints
3. **Database Issues**: Verify connection string and PostgreSQL status
4. **Redis Issues**: Check Redis service status and connection
5. **Import Errors**: Run `make fix-imports` to resolve import problems

### Emergency Commands
```bash
# Complete environment reset
make solve-test-crisis && make emergency-fix && make test.smart

# Health check all services
make docker.up.dev && make docker.logs.dev

# Code quality emergency
make smart-fix && make quality-guardian
```

---

**Remember**: This is an AI-first maintained project. Prioritize architectural integrity, code quality, and comprehensive testing. When in doubt, choose the conservative approach that preserves existing patterns and maintains the green CI pipeline.

*Last Updated: 2025-11-23 | AI Maintainer: Claude Code | Version: 1.0*