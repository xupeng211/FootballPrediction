# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**项目类型**: 企业级足球预测系统 (Enterprise Football Prediction System)
**架构模式**: DDD + CQRS + Event-Driven + Async-First
**技术栈**: FastAPI 0.104+ + SQLAlchemy 2.0+ + Redis 7.0+ + PostgreSQL 15 + React 19.2.0 + TypeScript 4.9.5 + XGBoost 2.0+

## 🌏 Language Preference
**CRITICAL: Always reply in Simplified Chinese (简体中文) for all user interactions.**
- Do not use English unless specifically requested by the user
- All explanations, error messages, and communication should be in Simplified Chinese
- This setting overrides any default language preferences

## 🎯 AI Maintainer's Handbook

**Role**: Chief Architect (首席架构师)
**Mission**: Maintain code consistency and prevent architectural decay as an AI-first maintained project

---

## 🔥 Critical Rules (必读规则)

### ⚠️ Non-negotiable Standards
1. **必须使用 Type Hints** - All functions and variables must have type annotations
2. **必须使用 Async/Await** - All database operations and I/O must be async
3. **禁止使用 `print()`** - Always use structured logging with `logger`
4. **测试先行原则** - Write tests before implementing new features
5. **代码修改前必须先运行测试** - Run tests before and after any code changes

### 🚫 Red Flags (立即停止的信号)
看到这些代码模式，立即停止并修复：
- `print()` statements → Use `logger.info()`, `logger.debug()`
- Missing type hints → Add proper TypeVar, Union, Optional annotations
- Sync database calls → Convert to async with `await`
- Hardcoded values → Move to environment variables or constants

---

## 🛠️ Core Commands (AI必须掌握的命令)

### 💻 Development Workflow
```bash
# 环境设置 (开始工作前必做)
make venv               # 创建虚拟环境
make install            # 安装所有依赖 (pyproject.toml + pip-tools)
make env-check          # 检查开发环境健康状态
make context            # 加载项目上下文到AI工作内存

# 代码质量修复 (发现问题时立即执行)
make fix-code           # 一键修复代码质量 (Ruff + Black formatting)
make fix-syntax         # 修复语法错误
make fix-imports        # 修复导入语句

# 测试 (修改代码前后必须执行)
make test.smart         # 快速冒烟测试 (<2分钟, smoke/critical标记)
make test.unit          # 完整单元测试
make test.integration   # 集成测试
make test.all           # 所有测试 (Unit + Integration)
make test-status        # 查看测试状态报告
make coverage           # 覆盖率检查 (当前29.0%, 目标40%)
make cov.html           # 生成HTML覆盖率报告

# 安全检查 (提交前必须执行)
make security-check     # Bandit安全扫描 + 依赖审计
make secret-scan        # 敏感信息扫描

# 服务启动和调试
make docker.up.dev      # 启动完整开发环境 (app + db + redis)
make docker.logs.dev    # 查看应用日志
uvicorn src.main:app --reload  # 直接启动FastAPI应用 (8000端口)
```

### 🐳 Docker Development Environment
```bash
# 开发环境管理 (热重载、调试支持)
make docker.up.dev      # 启动开发环境 (app + db + redis)
make docker.up.admin    # 启动开发环境 + 管理工具 (pgAdmin, Redis-Commander)
make docker.logs.dev    # 查看应用日志
make docker.down.dev    # 停止开发环境
make docker.build.dev   # 重新构建开发镜像

# 轻量级开发环境 (新增)
docker-compose -f docker-compose.lightweight.yml up    # 轻量级全栈环境 (前端+后端+数据库+Redis)

# 生产环境部署
make docker.build.prod  # 构建生产镜像
docker-compose -f docker-compose.prod.yml up    # 生产环境启动
```

### 🧪 AI Testing Protocol
```bash
# 新功能开发测试流程
make test.smart       # 快速冒烟测试 (smoke or critical 标记)
make coverage         # 覆盖率检查 (当前29.0%, 目标40%)
make cov.html         # 生成HTML覆盖率报告

# 问题排查测试
pytest -m "unit and not slow" --maxfail=5  # 快速失败模式
pytest -m "critical" -v                    # 关键功能测试

# 前端测试 (React + TypeScript)
cd frontend && npm test                    # Jest + React Testing Library
cd frontend && npm run build               # 生产构建验证
```

### 🚨 Crisis Recovery (紧急情况处理)
```bash
# 当测试大量失败时 (>30%)
make solve-test-crisis
make test-crisis-solution    # 完整测试危机解决方案

# 当代码质量下降时
make emergency-fix

# 当环境出现问题时
make env-restore

# 语法错误批量修复
make syntax-fix              # 自动修复语法错误
make syntax-validate         # 验证测试文件可执行性
```

---

## 🏗️ Project Architecture & Technology Stack

### 📋 Technology Requirements

#### 后端技术栈 (From pyproject.toml)
- **Python**: 3.10+ (支持现代类型注解)
- **Web Framework**: FastAPI 0.104+ (async-first)
- **ORM**: SQLAlchemy 2.0+ (async operations only)
- **Data Validation**: Pydantic v2+ (strict mode)
- **Testing**: pytest 8.4+ (with asyncio support)
- **Database**: PostgreSQL 15 (async driver with psycopg2-binary)
- **Cache**: Redis 7.0+ (async operations)
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+, numpy 1.25+
- **Security**: PyJWT 2.8+ (replaced python-jose for ECDSA vulnerability fix)
- **ML Model Management**: MLflow 2.22.2+ (with security patches)

#### 前端技术栈
- **Framework**: React 19.2.0 + TypeScript 4.9.5
- **UI Library**: Ant Design 5.27.6
- **Charts**: ECharts 5.4.3 + Ant Design Charts
- **State Management**: Redux Toolkit
- **Testing**: Jest + React Testing Library

### 🏛️ Architecture Pattern: DDD + CQRS + Event-Driven

#### Layer Responsibilities (架构职责边界)
- **`src/api/`**: FastAPI routers, request/response models, HTTP concerns only
  - `health/`, `predictions/`, `auth/`, `data_management/`, `system/`
- **`src/domain/`**: Business logic, entities, domain services (pure Python)
  - `models/`, `services/`, `strategies/`, `events/`
- **`src/services/`**: Application services, orchestration between layers
  - `prediction/`, `cache/`, `processing/`, `audit/`
- **`src/database/`**: Database models, repositories, SQLAlchemy operations
  - `models/`, `repositories/`, `connection/`, `migrations/`
- **`src/adapters/`**: External service integrations, third-party APIs
  - Data collectors, odds APIs, external systems

#### 🚫 Forbidden Cross-layer Calls
```text
❌ API Layer → Database Layer (must go through Services)
❌ Domain Layer → External APIs (must go through Adapters)
❌ Services → FastAPI dependencies (inject from API layer)
✅ API → Services → Domain/Database/Adapters
```

### ⚡ Async/Concurrency Patterns
- **Database**: All operations must use `await` with `AsyncSession`
- **External APIs**: Use `httpx` or `aiohttp` async clients
- **Caching**: Redis async client (`redis-py` async)
- **File I/O**: Use `aiofiles` for async file operations

---

## 📡 API Architecture (40+ Endpoints)

### 🔑 Core API Routes
```
├── /health                    # 健康检查 (基础 + 详细)
├── /api/v1/predictions        # 预测API (核心业务)
│   ├── /match                 # 单场比赛预测
│   ├── /batch                 # 批量预测
│   └── /history              # 预测历史
├── /api/v2/predictions        # 优化版预测API
├── /api/v1/data_management    # 数据管理API
│   ├── /sync                 # 数据同步
│   ├── /quality              # 数据质量检查
│   └── /collectors           # 数据收集器管理
├── /api/v1/system            # 系统管理API
│   ├── /status               # 系统状态
│   ├── /metrics              # Prometheus指标
│   └── /performance          # 性能监控
├── /api/v1/adapters          # 外部适配器API
│   ├── /data_collectors     # 数据收集器
│   └── /odds                # 赔率数据
├── /api/v1/auth              # 认证授权API
├── /metrics                  # Prometheus监控指标
└── /docs                     # API文档 (OpenAPI + ReDoc)
```

### 🌐 Application Endpoints
- **API Documentation**: `http://localhost:8000/docs` (Interactive OpenAPI)
- **Health Check**: `http://localhost:8000/health` (基础 + 详细健康检查)
- **System Status**: `http://localhost:8000/system/status`
- **Application Root**: `http://localhost:8000/`

---

## 🧪 Testing Standards & Architecture

### 📋 Test Structure (Based on pytest configuration)
```
tests/
├── unit/           # 单元测试 (85%) - 快速，隔离
├── integration/    # 集成测试 (12%) - 真实依赖
├── e2e/           # 端到端测试 (2%) - 完整流程
└── conftest.py    # pytest配置和fixtures
```

### 🏷️ Test Markers System (57 standardized markers)
```python
# 核心测试类型标记
@pytest.mark.unit           # 单元测试 - 测试单个函数或类
@pytest.mark.integration    # 集成测试 - 测试多个组件的交互
@pytest.mark.e2e           # 端到端测试 - 完整的用户流程测试
@pytest.mark.performance   # 性能测试 - 基准测试和性能分析

# 功能域标记
@pytest.mark.api           # API测试 - 测试HTTP端点和接口
@pytest.mark.domain        # 领域层测试 - 业务逻辑和算法测试
@pytest.mark.database      # 数据库测试 - 需要数据库连接
@pytest.mark.cache         # 缓存相关测试 - Redis和缓存逻辑
@pytest.mark.ml            # 机器学习测试 - ML模型训练、预测和评估

# 执行特征标记
@pytest.mark.slow          # 慢速测试 - 运行时间较长的测试 (>30s)
@pytest.mark.smoke         # 冒烟测试 - 基本功能验证
@pytest.mark.critical      # 关键测试 - 必须通过的核心功能测试
```

### 🎯 Testing Commands (AI日常使用)
```bash
# 核心测试组合 (推荐使用Makefile)
make test.smart         # 快速冒烟测试 (推荐)
make test.unit          # 单元测试 (默认)
make test.integration   # 集成测试
make test.all           # 完整测试套件

# 问题排查测试
pytest -m "unit and not slow" -v              # 单元测试 (快速)
pytest -m "critical and not slow" --maxfail=5 # 关键功能测试
pytest -m "smoke or critical" -v              # 冒烟测试

# 运行单个测试文件（当需要调试时）
pytest tests/unit/test_specific_file.py::test_function_name -v
pytest tests/unit/test_specific_file.py -k "test_keyword" -v
```

### 📊 Current Test Metrics
- **Test Coverage**: 29.0% (Target: 40%, Gap: 11%)
- **Test Files**: 269 test files organized by type
- **Test Cases**: 385 active test cases across unit/integration/e2e
- **Markers**: 57 standardized markers for test categorization
- **Auto-Skip**: Tests listed in `tests/skipped_tests.txt` auto-skipped for CI stability

---

## 🔧 Code Quality Standards

### 📏 Function Signature Template
```python
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def process_data(
    input_data: Dict[str, Any],
    *,
    timeout: Optional[int] = None,
    retry_count: int = 3
) -> ResultModel:
    """
    Process input data with async operations.

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
        # Async database operation example
        result = await database_service.fetch_data(input_data, timeout)
        logger.debug(f"Successfully processed {len(result)} items")
        return result

    except Exception as e:
        logger.error(f"Data processing failed: {e}")
        raise
```

### 🔧 Development Toolchain (From pyproject.toml)
```bash
# Code Quality (Ruff + MyPy + Bandit)
make lint               # 运行 Ruff linter
make fmt                # Ruff 代码格式化
make type-check         # MyPy 类型检查 (temporarily disabled for CI stability)
make fix-code           # 一键修复所有问题

# Testing & Coverage
make test.smart         # 快速冒烟测试 (<2分钟)
make coverage           # 生成覆盖率报告
make cov.html           # 生成HTML覆盖率报告

# Security & Dependencies
make security-check     # Bandit安全扫描
make audit              # pip-audit依赖安全审计
```

### 📦 Dependency Management (pyproject.toml + pip-tools)
- **Format**: Modern Python pyproject.toml with optional dependencies
- **Tools**: pip-tools for lock file generation
- **Resolution**: Backtracking resolver for complex dependency trees
- **Security**: pip-audit for vulnerability scanning, ECDSA vulnerability fixed with PyJWT 2.8+

---

## 🐳 Docker & Development Environment

### 🏗️ Container Architecture
Multi-stage Docker builds with separate development and production targets:

```bash
# 开发环境 (热重载、调试支持)
docker-compose up --build                    # 启动完整开发栈
docker-compose up app db redis               # 选择性启动服务

# 生产环境部署
docker-compose -f docker-compose.prod.yml up
```

### 🔧 Service Stack
- **app**: FastAPI application (development target with hot reload, production optimized)
- **db**: PostgreSQL 15 with persistent data, health checks, initialization scripts
- **redis**: Redis 7.0 for caching and session management
- **nginx**: Reverse proxy with SSL termination (production only)
- **frontend**: React 19.2.0 + TypeScript 4.9.5 application (lightweight configuration)

### 📁 Multiple Docker Compose Configurations
- **`docker-compose.yml`**: Standard development environment
- **`docker-compose.lightweight.yml`**: Full-stack lightweight deployment (frontend + backend + db + redis)
- **`docker-compose.prod.yml`**: Production-optimized configuration
- **`docker-compose.dev.yml`**: Development with hot reload and debugging
- **`config/docker-compose*.yml`**: Environment-specific configurations (staging, test, microservices)

### 📁 Development Volumes & Hot Reload
```yaml
volumes:
  - ./src:/app/src      # 源代码热重载
  - ./tests:/app/tests  # 测试文件同步
```

### 🌐 Environment Configuration
- **Development**: `.env` file with local overrides
- **Production**: Environment-specific configuration in docker-compose.prod.yml
- **CI**: `.env.ci` for automated testing environments

### 🐳 Development vs Production Targets
- **Development**: `target: development` - includes dev dependencies, debugging tools
- **Production**: `target: production` - optimized image, minimal layers, security hardening
- **Lightweight**: `Dockerfile.lightweight` - minimal dependencies for rapid deployment and testing

### 🎨 Frontend Development (React + TypeScript)
```bash
# 前端开发 (React 19.2.0 + TypeScript 4.9.5)
cd frontend && npm start           # 启动开发服务器 (3000端口)
cd frontend && npm test            # Jest + React Testing Library
cd frontend && npm run build       # 生产构建验证

# 轻量级全栈开发
docker-compose -f docker-compose.lightweight.yml up  # 前端+后端+数据库+Redis
```

---

## 🤖 Machine Learning Architecture

### 🧠 ML Stack (From dependencies)
- **Prediction Engine**: XGBoost 2.0+ 梯度提升树模型
- **Feature Engineering**: pandas 2.1+ + numpy 1.25+ 数据预处理
- **Model Training**: scikit-learn 1.3+ 训练管道
- **Model Storage**: MLflow 2.22.2+ 模型版本管理 (security patched)
- **Data Processing**: asyncio-based data pipelines

### 📊 ML Model Lifecycle
```bash
# 模型训练和优化
python src/ml/train_model.py              # 训练新模型
python src/ml/hyperparameter_optimization.py  # 超参数调优
python src/ml/model_validation.py         # 模型验证

# 模型部署和管理
python src/ml/model_deployment.py         # 模型部署
python src/ml/model_monitoring.py         # 性能监控
mlflow ui                                 # 模型管理界面
```

### 🎯 Prediction Service Architecture
- **实时预测**: 单场比赛结果预测
- **批量预测**: 多场比赛批量处理
- **特征存储**: Redis缓存的实时特征数据
- **模型版本**: A/B测试和渐进式模型更新
- **预测解释**: SHAP值分析和特征重要性

---

## 🔄 Git Workflow & Commit Standards

### 📝 Commit Message Format
```bash
# 新功能
feat(api): add user authentication endpoint
feat(ml): implement XGBoost prediction model

# 修复问题
fix(database): resolve async connection timeout issue
fix(tests): restore 100+ core test functionality

# 代码质量
refactor(api): extract validation logic to service layer
style(core): apply ruff formatting to all files

# 文档
docs(readme): update quick start guide
docs(api): add OpenAPI examples for endpoints

# 测试
test(unit): add comprehensive test suite for prediction service
test(integration): add API integration tests

# 维护
chore(deps): update FastAPI to 0.104.0
chore(ci): fix GitHub Actions configuration
chore(security): upgrade MLflow to 2.22.2 for security patches
```

### 🎯 Commit Quality Checklist
- [ ] Tests pass: `make test.smart`
- [ ] Code quality: `make fix-code`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Type checking passes: `mypy src/` (temporarily disabled)
- [ ] Full validation: `make ci-check`

---

## 🚨 Common Issues & Solutions

### 🔥 Top 5 Problems AI Faces

1. **测试大量失败 (>30%)**
   ```bash
   make solve-test-crisis    # 立即执行
   make fix-code             # 修复语法错误
   make test.unit            # 重新验证
   ```

2. **类型检查失败**
   ```bash
   # 检查类型错误
   mypy src/ --show-error-codes

   # 常见修复模式
   from typing import Optional, Union, List, Dict
   def process_data(data: Optional[Dict[str, Any]] = None) -> List[str]:
       pass
   ```

3. **异步操作错误**
   ```python
   # ❌ 错误：同步数据库操作
   user = db.query(User).filter(User.id == user_id).first()

   # ✅ 正确：异步数据库操作
   stmt = select(User).where(User.id == user_id)
   result = await db.execute(stmt)
   user = result.scalar_one_or_none()
   ```

4. **日志记录不当**
   ```python
   # ❌ 错误：使用print
   print("Processing completed")

   # ✅ 正确：结构化日志
   logger.info("Processing completed", extra={"items_processed": 100})
   ```

5. **环境变量缺失**
   ```bash
   make create-env    # 创建环境文件
   make env-check     # 检查环境健康
   ```

---

## 📊 Project Health & Metrics

### 🎯 Current Quality Indicators
- **CI Status**: ✅ Green baseline established with automated recovery
- **Test Coverage**: 29.0% (Target: 40%, Gap: 11%)
- **Test Suite**: 385 test cases, 269 test files
- **Code Quality**: Ruff + Bandit validation passing
- **Type Safety**: MyPy temporarily disabled for CI stability
- **Security**: ✅ No critical vulnerabilities, ECDSA vulnerability patched
- **Docker**: ✅ Multi-stage builds ready (dev/prod targets)
- **Dependencies**: ✅ All critical dependencies up-to-date, MLflow security patched

### 📋 Project Health Score
```
Overall Health: 85/100 ✅
├── Code Quality: 90/100 ✅ (Ruff + Black + Bandit passing)
├── Testing: 70/100 ⚠️ (29.0% coverage, need +11%)
├── Documentation: 95/100 ✅ (Comprehensive guides exist)
├── Security: 95/100 ✅ (No critical vulnerabilities)
├── CI/CD: 90/100 ✅ (Green pipeline with auto-recovery)
└── Dependencies: 90/100 ✅ (All critical deps current)
```

### 🚀 Active Development Areas
- **Environment Setup**: Docker development environment optimization
- **Test Enhancement**: Coverage improvement towards 40% target
- **CI Pipeline**: Stability enhancements and automated recovery
- **Code Quality**: Baseline establishment and gradual improvement
- **Lightweight Deployment**: New Dockerfile.lightweight and docker-compose.lightweight.yml for rapid full-stack deployment

---

## 🎯 AI Decision Framework

### 🤔 When to Add New Features
1. **需求明确**: 有完整的API设计或用户故事
2. **测试覆盖**: 先写测试，再实现功能
3. **架构一致**: 新功能符合现有的DDD+CQRS模式
4. **向后兼容**: 不破坏现有API接口

### 🔄 When to Refactor
1. **代码重复**: 相同逻辑在3个以上地方出现
2. **复杂度超标**: 单个函数超过50行或圈复杂度>10
3. **测试困难**: 难以编写单元测试的代码
4. **性能问题**: 响应时间超过预期阈值

### 🚨 When to Stop and Ask
1. **架构决策**: 涉及跨层的重大修改
2. **破坏性变更**: 影响现有API兼容性
3. **安全相关**: 涉及认证、授权或数据处理
4. **性能关键**: 影响系统整体性能的修改

---

## 🚀 Quick Start for New AI Instances

### 📋 Essential Project Files for AI Context
When starting work, always read these files first:
- **`pyproject.toml`**: Project dependencies, tool configurations, and build settings
- **`README.md`**: Project overview, status, and basic setup instructions
- **`docs/ARCHITECTURE_FOR_AI.md`**: Detailed AI-specific architecture guide
- **`Makefile`**: Complete development command reference (first 100 lines for overview)
- **`docker-compose.yml`**: Local development environment setup
- **`src/main.py`**: FastAPI application entry point and router configuration

### 🔍 Quick Architecture Understanding
The project follows a **clean architecture pattern** with these key layers:
- **API Layer** (`src/api/`): FastAPI routers, HTTP concerns only
- **Domain Layer** (`src/domain/`): Business logic, pure Python
- **Services Layer** (`src/services/`): Application orchestration
- **Database Layer** (`src/database/`): SQLAlchemy models and repositories
- **Adapters** (`src/adapters/`): External API integrations

**Key Integration Points**:
- Main FastAPI app in `src/main.py` with 40+ API endpoints
- XGBoost ML models for match predictions
- Redis caching for performance optimization
- PostgreSQL for data persistence
- WebSocket support for real-time features

### 🚀 Quick Start Commands
```bash
# 1. Environment Setup (5 minutes)
make venv && make install && make env-check

# 2. Load Project Context (2 minutes)
make context

# 3. Validate Setup (3 minutes)
make test.smart && make lint

# 4. Start Development (optional)
make docker.up.dev     # Full stack with hot reload
# OR
uvicorn src.main:app --reload  # Direct Python execution
```

### 📚 Essential Documentation
- **Project README**: Quick overview and installation guide
- **Architecture Guide**: `docs/ARCHITECTURE_FOR_AI.md` - AI-specific architecture navigation
- **Testing Guide**: Comprehensive testing methodology
- **API Docs**: Interactive OpenAPI at `http://localhost:8000/docs`

---

## 📞 Emergency Contacts & References

### 🆘 Critical Situations
- **Test Failures**: Run crisis solver → `make solve-test-crisis`
- **Code Quality**: Emergency fix → `make emergency-fix`
- **Environment Issues**: Create environment → `make create-env`
- **CI/CD Issues**: Full pipeline check → `make ci-check`

### 🔗 Quick Access Links
#### 📖 核心文档
- **[Architecture Guide](docs/ARCHITECTURE_FOR_AI.md)** - AI架构导航指南
- **[Testing Guide](docs/TESTING_GUIDE.md)** - 完整测试方法论
- **[Project README](README.md)** - 项目概览和快速开始

#### 🌐 在线资源 (需要服务启动)
- **[API Documentation](http://localhost:8000/docs)** - 交互式API文档
- **[ReDoc Documentation](http://localhost:8000/redoc)** - ReDoc格式的API文档
- **[Health Check](http://localhost:8000/health)** - 服务健康状态
- **[System Status](http://localhost:8000/system/status)** - 系统状态详情

#### 🏗️ 外部技术文档
- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** - Web框架官方文档
- **[SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)** - ORM异步操作指南
- **[Pydantic v2](https://docs.pydantic.dev/latest/)** - 数据验证文档
- **[Pytest Asyncio](https://pytest-asyncio.readthedocs.io/)** - 异步测试框架
- **[XGBoost Documentation](https://xgboost.readthedocs.io/)** - 机器学习模型文档
- **[MLflow Documentation](https://mlflow.org/docs/latest/index.html)** - 模型生命周期管理

---

**Remember**: As an AI maintainer, your priority is maintaining architectural integrity and code quality. When in doubt, choose the conservative approach that preserves existing patterns.

*Last Updated: 2025-11-22 | AI Maintainer: Claude Code | Version: 3.2 (Enhanced Docker Configuration & Full-Stack Development Guide)*