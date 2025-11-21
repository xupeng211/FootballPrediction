# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**项目类型**: 企业级足球预测系统 (Enterprise Football Prediction System)
**架构模式**: DDD + CQRS + Event-Driven + Async-First
**技术栈**: FastAPI + SQLAlchemy 2.0 + Redis 7.0 + PostgreSQL 15 + React 19.2.0 + TypeScript 4.9.5 + XGBoost 2.0+

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
-看到这些代码模式，立即停止并修复：
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
make fix-code           # 一键修复代码质量 (Black + Ruff + MyPy)
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
```

### 🐳 Docker Development Environment
```bash
# 开发环境管理 (热重载、调试支持)
make docker.up.dev      # 启动开发环境 (app + db + redis)
make docker.up.admin    # 启动开发环境 + 管理工具 (pgAdmin, Redis-Commander)
make docker.logs.dev    # 查看应用日志
make docker.down.dev    # 停止开发环境
make docker.build.dev   # 重新构建开发镜像

# 生产环境部署
make docker.build.prod  # 构建生产镜像
make docker.push.prod   # 推送生产镜像
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

# 语法错误批量修复 (Issue #84)
make syntax-fix              # 自动修复语法错误
make syntax-validate         # 验证测试文件可执行性
```

---

## 🏗️ Tech Stack & Standards

### 📋 Technology Requirements

#### 后端技术栈
- **Python**: 3.10+ (支持现代类型注解)
- **Web Framework**: FastAPI 0.104+ (async-first)
- **ORM**: SQLAlchemy 2.0+ (async operations only)
- **Data Validation**: Pydantic v2+ (strict mode)
- **Testing**: pytest 8.4+ (with asyncio support)
- **Database**: PostgreSQL 15 (async driver)
- **Cache**: Redis 7.0+ (async operations)
- **Machine Learning**: XGBoost 2.0+, scikit-learn 1.3+, pandas 2.1+

#### 前端技术栈
- **Framework**: React 19.2.0 + TypeScript 4.9.5
- **UI Library**: Ant Design 5.27.6
- **Charts**: ECharts 5.4.3 + Ant Design Charts 2.6.6
- **State Management**: Redux Toolkit 2.9.2
- **Routing**: React Router DOM 7.9.4
- **Testing**: Jest + React Testing Library
- **Build Tool**: Create React App 5.0.1

### 📏 Code Standards

#### Function Signature Template
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

#### Database Operation Pattern
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_by_id(
    db: AsyncSession,
    user_id: int
) -> Optional[UserModel]:
    """Get user by ID using async SQLAlchemy."""
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            logger.debug(f"Found user: {user_id}")
        else:
            logger.warning(f"User not found: {user_id}")

        return user

    except Exception as e:
        logger.error(f"Database error fetching user {user_id}: {e}")
        raise
```

---

## 📁 Architecture Boundaries (架构职责边界)

### 🎯 Layer Responsibilities (DDD + CQRS Pattern)
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

### 🏗️ Application Architecture
- **Pattern**: Domain-Driven Design (DDD) + Command Query Responsibility Segregation (CQRS)
- **Database**: Async SQLAlchemy 2.0+ with PostgreSQL 15
- **Caching**: Redis 7.0+ with async operations
- **API**: FastAPI with automatic OpenAPI documentation
- **Containerization**: Multi-stage Docker builds (dev/prod targets)

### 🚫 Forbidden Cross-layer Calls

```text
❌ API Layer → Database Layer (must go through Services)
❌ Domain Layer → External APIs (must go through Adapters)
❌ Services → FastAPI dependencies (inject from API layer)
✅ API → Services → Domain/Database/Adapters
```

### ⚡ Async/Concurrency Patterns
- **Database**: All operations must use `await` with `AsyncSession`
- **External APIs**: Use `asynchttp` or `httpx` async clients
- **Caching**: Redis async client (`redis-py` async)
- **File I/O**: Use `aiofiles` for async file operations

---

## 🔄 Git Commit Standards

### 📝 Commit Message Format
```bash
# 新功能
feat(api): add user authentication endpoint
feat(ml): implement LSTM prediction model

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
```

### 🎯 Commit Quality Checklist
- [ ] Tests pass: `make test.smart`
- [ ] Code quality: `make fix-code`
- [ ] Security check: `make security-check`
- [ ] Coverage maintained: `make coverage`
- [ ] Type checking passes: `mypy src/`
- [ ] Full validation: `make ci-check`

---

## 🧪 Testing Standards

### 📋 Test Structure
```
tests/
├── unit/           # 单元测试 (快速，隔离)
├── integration/    # 集成测试 (真实依赖)
├── e2e/           # 端到端测试 (完整流程)
└── conftest.py    # pytest配置和fixtures
```

### 🎯 Test Writing Guidelines
```python
import pytest
from unittest.mock import AsyncMock
from src.services.prediction import PredictionService

class TestPredictionService:
    """Prediction service unit tests."""

    @pytest.fixture
    def prediction_service(self):
        """Create prediction service fixture."""
        return PredictionService()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_predict_match_success(self, prediction_service):
        """Test successful match prediction."""
        # Arrange
        match_data = {
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01"
        }

        # Act
        result = await prediction_service.predict(match_data)

        # Assert
        assert result is not None
        assert result.home_win_probability >= 0.0
        assert result.home_win_probability <= 1.0
        assert result.away_win_probability >= 0.0
        assert result.away_win_probability <= 1.0

        logger.info(f"Prediction test passed: {result}")
```

### 🏷️ Test Markers & Configuration
```bash
# 核心测试组合 (AI日常使用)
pytest -m "unit and not slow" -v              # 单元测试 (快速)
pytest -m "critical and not slow" --maxfail=5 # 关键功能测试
pytest -m "smoke or critical" -v              # 冒烟测试

# 统一测试接口 (推荐使用Makefile)
make test.smart         # 快速冒烟测试 (推荐)
make test.unit          # 单元测试 (默认)
make test.integration   # 集成测试
make test.all           # 完整测试套件

# 高级测试功能
make test-crisis-fix    # 紧急修复测试问题
make test-enhanced-coverage # 增强覆盖率分析
make test-report-generate   # 生成综合测试报告

# 运行单个测试文件（当需要调试时）
pytest tests/unit/test_specific_file.py::test_function_name -v
pytest tests/unit/test_specific_file.py -k "test_keyword" -v
```

#### Test Configuration (pytest.ini + conftest.py)
- **Test Files**: 269 test files organized by type
- **Markers**: 57 standardized markers (unit, integration, critical, smoke, etc.)
- **Fixtures**: Global fixtures for client, access_token, training_data
- **Auto-Skip**: Tests listed in `tests/skipped_tests.txt` auto-skipped for CI stability
- **Coverage Target**: 40% (current: 29.0%)

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

## 🔍 Quick Diagnostics & Health Checks

### 🩺 全面环境健康检查 (5分钟诊断)
```bash
# 1. 完整环境检查 (最重要)
make full-health-check     # 检查所有关键指标

# 2. 分项检查
make env-check             # Python环境和依赖
make test-status           # 测试状态和覆盖率
make code-quality-check    # 代码质量指标
make security-scan         # 安全漏洞扫描
make docker-health         # Docker环境检查
```

### 🚨 问题快速定位
```bash
# 测试问题诊断
make test-diagnostic       # 识别测试失败的根本原因
make coverage-gap          # 覆盖率缺口分析
make flaky-test-detect     # 不稳定测试检测

# 代码质量问题诊断
make quality-report        # 详细代码质量报告
make dependency-check      # 依赖冲突和安全检查
make type-scan            # 类型错误扫描

# 环境问题诊断
make environment-scan     # 环境配置完整性检查
make port-conflict-check  # 端口冲突检测
make service-health       # 服务状态检查
```

### 📊 性能和资源监控
```bash
# 应用性能
make performance-check     # API响应时间和资源使用
make database-health       # 数据库连接和性能
make cache-status          # Redis缓存状态

# 开发环境性能
make dev-resources         # 开发环境资源使用情况
make docker-stats          # Docker容器资源监控
```

### 🔧 一键修复命令
```bash
# 常见问题自动修复
make auto-fix-tests        # 自动修复常见测试问题
make auto-fix-quality      # 自动修复代码质量问题
make auto-fix-deps         # 自动解决依赖冲突
make env-repair           # 修复环境配置问题

# 深度修复 (需要谨慎使用)
make full-system-repair    # 系统级修复 (破坏性)
make test-crisis-solve     # 解决测试危机
```

### 📋 诊断报告生成
```bash
# 生成综合报告
make diagnostic-report     # 完整的诊断报告
make quality-dashboard     # 代码质量仪表板
make test-analytics        # 测试分析报告
make project-status        # 项目状态总览
```

---

## 📊 Quality Metrics & Tooling

### 🎯 Current Benchmarks
- **Test Coverage**: 29.0% (Target: 40%, Gap: 11%)
- **Test Files**: 269 files with 57 standardized markers
- **Test Cases**: 385 active test cases across unit/integration/e2e
- **Source Files**: 622 files across multiple layers
- **CI Pipeline**: ✅ Green baseline established with automated recovery
- **Flaky Test Management**: Automated isolation system in place
- **Quality Gates**: Ruff ✅, MyPy (temporarily disabled for CI stability), Bandit ✅
- **Security**: ✅ No critical vulnerabilities, all dependencies patched
- **Docker**: ✅ Multi-stage builds optimized for dev/prod workflows

### 🔧 Development Toolchain
```bash
# Code Quality (Ruff + Black + MyPy)
make lint               # 运行 Ruff linter
make fmt                # Ruff 代码格式化
make type-check         # MyPy 类型检查
make fix-code           # 一键修复所有问题

# Testing & Coverage
make test.smart         # 快速冒烟测试 (<2分钟)
make coverage           # 生成覆盖率报告
make cov.html           # 生成HTML覆盖率报告

# Dependency Management
make install            # 安装依赖 (pyproject.toml + pip-tools)
make lock               # 锁定依赖版本
make lock-dev           # 锁定开发依赖
```

### 📦 Dependency Management (pyproject.toml)
- **Format**: Modern Python pyproject.toml with optional dependencies
- **Tools**: pip-tools for lock file generation (requirements/prod.txt, requirements/dev.txt)
- **Resolution**: Backtracking resolver for complex dependency trees
- **Dev Dependencies**: pytest, ruff, mypy, bandit, pre-commit
- **Production Dependencies**: FastAPI, SQLAlchemy, Redis, PostgreSQL drivers

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

### 🌐 Application Endpoints
- **API Documentation**: `http://localhost:8000/docs` (Interactive OpenAPI)
- **Health Check**: `http://localhost:8000/health` (基础 + 详细健康检查)
- **System Status**: `http://localhost:8000/system/status`
- **Application Root**: `http://localhost:8000/`

#### 📡 API路由架构
```
├── /health                    # 健康检查 (基础 + 详细)
├── /api/v1/predictions        # 预测API (核心业务)
├── /api/v2/predictions        # 优化版预测API
├── /api/v1/data_management    # 数据管理API
├── /api/v1/system            # 系统管理API
├── /api/v1/adapters          # 外部适配器API
├── /api/v1/auth              # 认证授权API
├── /api/v1/optimization      # 性能优化API
├── /metrics                  # Prometheus监控指标
└── /docs                     # API文档 (OpenAPI + ReDoc)
```

#### 🔑 核心API端点
- **预测服务**: `/api/v1/predictions/match`, `/api/v1/predictions/batch`
- **数据管理**: `/api/v1/data_management/sync`, `/api/v1/data_management/quality`
- **系统监控**: `/api/v1/system/status`, `/api/v1/system/metrics`
- **外部适配器**: `/api/v1/adapters/data_collectors`, `/api/v1/adapters/odds`

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
- **Database**: Connection pooling configured for both environments

### 🐳 Development vs Production Targets
- **Development**: `target: development` - includes dev dependencies, debugging tools
- **Production**: `target: production` - optimized image, minimal layers, security hardening

---

## 🎨 Frontend Development (React + TypeScript)

### 🏗️ 前端架构
- **Framework**: React 19.2.0 with TypeScript 4.9.5
- **UI Components**: Ant Design 5.27.6 with custom theming
- **State Management**: Redux Toolkit 2.9.2 for global state
- **Charts & Visualization**: ECharts 5.4.3 + Ant Design Charts
- **Routing**: React Router DOM 7.9.4 for SPA navigation

### 🔧 Frontend Development Workflow
```bash
# 前端开发环境设置
cd frontend/
npm install                    # 安装依赖
npm start                      # 启动开发服务器 (http://localhost:3000)
npm test                       # 运行Jest单元测试
npm run build                  # 生产构建验证

# 代码质量检查
npm run lint                   # ESLint检查 (如果配置)
npm run type-check             # TypeScript类型检查
```

### 📁 Frontend Project Structure
```
frontend/
├── public/                     # 静态资源
├── src/
│   ├── components/            # React组件
│   │   ├── Dashboard.tsx      # 主仪表板
│   │   ├── PredictionChart.tsx # 预测图表组件
│   │   └── ...                # 其他业务组件
│   ├── services/              # API服务层
│   │   └── api.ts            # 后端API客户端
│   ├── store/                 # Redux状态管理
│   │   └── slices/           # Redux Toolkit切片
│   ├── types/                 # TypeScript类型定义
│   └── utils/                 # 工具函数
├── package.json               # 依赖配置
└── tsconfig.json             # TypeScript配置
```

### 🎨 UI/UX Development Standards
- **组件设计**: 遵循Ant Design设计规范
- **响应式设计**: 移动端优先的响应式布局
- **国际化**: 支持中英文双语界面
- **主题定制**: 可配置的颜色主题和品牌化
- **无障碍**: WCAG 2.1 AA级无障碍支持

### 🔗 前后端集成
- **API客户端**: Axios HTTP客户端与自动重试
- **类型安全**: 共享的TypeScript类型定义
- **错误处理**: 统一的错误处理和用户反馈
- **认证集成**: JWT token自动管理和刷新

---

## 🤖 Machine Learning Model Management

### 🧠 ML架构概览
- **Prediction Engine**: XGBoost 2.0+ 梯度提升树模型
- **Feature Engineering**: pandas 2.1+ + numpy 1.25+ 数据预处理
- **Model Training**: scikit-learn 1.3+ 训练管道
- **Model Validation**: 交叉验证 + 性能监控
- **Model Storage**: MLflow 2.15+ 模型版本管理

### 📊 ML模型生命周期
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

### 🎯 预测系统架构
- **实时预测**: 单场比赛结果预测
- **批量预测**: 多场比赛批量处理
- **特征存储**: Redis缓存的实时特征数据
- **模型版本**: A/B测试和渐进式模型更新
- **预测解释**: SHAP值分析和特征重要性

### 📈 模型性能指标
- **准确率目标**: >85% 比赛结果预测准确率
- **响应时间**: <100ms 单次预测延迟
- **模型更新**: 每周自动重训练和验证
- **数据质量**: 实时数据质量监控和清洗

---

## 🏗️ 高级架构概念 (Advanced Architecture Concepts)

### 🧠 DDD + CQRS 实现细节

#### 领域驱动设计 (DDD) 关键概念
- **聚合根 (Aggregate Root)**: `Match`、`Prediction` 等核心实体
- **值对象 (Value Object)**: `TeamId`、`Score`、`Odds` 等不可变对象
- **领域服务 (Domain Service)**: 纯业务逻辑，无外部依赖
- **领域事件 (Domain Events)**: `PredictionCreated`、`MatchCompleted` 等事件

#### 命令查询职责分离 (CQRS)
```python
# Command Side - 写操作
class CreatePredictionCommand:
    """创建预测命令"""
    def __init__(self, match_id: int, prediction_data: PredictionData):
        self.match_id = match_id
        self.prediction_data = prediction_data

# Query Side - 读操作
class GetPredictionQuery:
    """获取预测查询"""
    def __init__(self, prediction_id: int):
        self.prediction_id = prediction_id
```

### ⚡ 异步架构模式

#### 异步数据库操作模式
```python
# ✅ 正确的异步数据库操作
async def get_predictions(db: AsyncSession, limit: int = 100) -> List[Prediction]:
    """异步获取预测列表"""
    stmt = select(Prediction).limit(limit).order_by(Prediction.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

# ❌ 错误的同步操作
def get_predictions_sync(db: Session, limit: int = 100) -> List[Prediction]:
    """禁止使用同步数据库操作"""
    return db.query(Prediction).limit(limit).all()
```

#### 异步外部API调用
```python
async def fetch_external_data(url: str) -> Dict[str, Any]:
    """异步获取外部数据"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.json()
```

### 🔄 事件驱动架构

#### 领域事件发布
```python
class PredictionCreated:
    """预测创建事件"""
    def __init__(self, prediction_id: int, match_id: int):
        self.prediction_id = prediction_id
        self.match_id = match_id
        self.timestamp = datetime.utcnow()

# 事件发布
async def create_prediction(db: AsyncSession, data: PredictionData) -> Prediction:
    prediction = Prediction(**data.dict())
    db.add(prediction)
    await db.commit()

    # 发布领域事件
    await event_bus.publish(PredictionCreated(prediction.id, prediction.match_id))
    return prediction
```

### 🎯 机器学习架构

#### XGBoost模型集成
- **模型存储**: MLflow模型注册表管理版本
- **特征工程**: 实时特征计算和缓存
- **模型推理**: 异步推理服务，支持批量预测
- **模型监控**: 性能指标追踪和自动重训练

#### 预测服务架构
```python
class PredictionService:
    """预测服务 - 协调领域模型和ML推理"""

    async def predict_match(self, match_data: MatchData) -> PredictionResult:
        # 1. 数据验证 (领域层)
        validated_match = await self.validation_service.validate(match_data)

        # 2. 特征计算 (领域层)
        features = await self.feature_calculator.calculate(validated_match)

        # 3. 模型推理 (ML层)
        prediction = await self.ml_model.predict(features)

        # 4. 结果处理 (领域层)
        return await self.result_processor.process(prediction, validated_match)
```

---

## 🎯 关键开发模式 (Key Development Patterns)

### 📝 常见代码模式

#### 1. 服务层模式 (Service Layer Pattern)
```python
# ✅ 推荐的服务层实现
class PredictionService:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def create_prediction(self, data: CreatePredictionRequest) -> PredictionResponse:
        # 1. 验证输入 (领域逻辑)
        validated_data = await self._validate_prediction_data(data)

        # 2. 业务处理 (领域服务)
        prediction = await self._process_prediction(validated_data)

        # 3. 持久化 (基础设施)
        saved_prediction = await self._save_prediction(prediction)

        # 4. 发布事件 (领域事件)
        await self.event_bus.publish(PredictionCreated(saved_prediction.id))

        return PredictionResponse.from_model(saved_prediction)
```

#### 2. 仓储模式 (Repository Pattern)
```python
# ✅ 异步仓储实现
class PredictionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, prediction_id: int) -> Optional[Prediction]:
        """根据ID查找预测"""
        stmt = select(Prediction).where(Prediction.id == prediction_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_match(self, match_id: int) -> List[Prediction]:
        """根据比赛查找所有预测"""
        stmt = select(Prediction).where(Prediction.match_id == match_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

#### 3. 工厂模式 (Factory Pattern)
```python
# ✅ 预测对象工厂
class PredictionFactory:
    @staticmethod
    def create_from_data(match_data: MatchData, user_id: int) -> Prediction:
        """从比赛数据创建预测对象"""
        return Prediction(
            match_id=match_data.id,
            user_id=user_id,
            home_win_prob=match_data.home_win_probability,
            away_win_prob=match_data.away_win_probability,
            draw_prob=match_data.draw_probability,
            created_at=datetime.utcnow()
        )
```

### 🧪 测试模式

#### 1. 异步单元测试模式
```python
@pytest.mark.asyncio
@pytest.mark.unit
class TestPredictionService:
    async def test_create_prediction_success(self):
        # Arrange
        mock_db = AsyncMock()
        mock_event_bus = AsyncMock()
        service = PredictionService(mock_db, mock_event_bus)

        request_data = CreatePredictionRequest(
            match_id=123,
            predicted_result="home_win"
        )

        # Act
        result = await service.create_prediction(request_data)

        # Assert
        assert result is not None
        assert result.match_id == 123
        mock_event_bus.publish.assert_called_once()
```

#### 2. 数据库集成测试模式
```python
@pytest.mark.integration
@pytest.mark.database
class TestPredictionRepositoryIntegration:
    async def test_save_and_retrieve_prediction(self, db_session: AsyncSession):
        # Arrange
        repo = PredictionRepository(db_session)
        prediction = PredictionFactory.create_from_data(mock_match_data, 1)

        # Act
        await repo.save(prediction)
        retrieved = await repo.find_by_id(prediction.id)

        # Assert
        assert retrieved is not None
        assert retrieved.match_id == prediction.match_id
```

### 🔧 配置管理模式

#### 1. 环境配置
```python
# ✅ 环境配置管理
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    url: str
    pool_size: int = 10
    max_overflow: int = 20

    class Config:
        env_prefix = "DATABASE_"

class AppSettings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    redis_url: str
    secret_key: str
    debug: bool = False

    class Config:
        env_file = ".env"
```

#### 2. 依赖注入模式
```python
# ✅ FastAPI依赖注入
async def get_prediction_service(db: AsyncSession = Depends(get_db)) -> PredictionService:
    event_bus = get_event_bus()
    return PredictionService(db, event_bus)

@app.post("/predictions")
async def create_prediction(
    request: CreatePredictionRequest,
    service: PredictionService = Depends(get_prediction_service)
) -> PredictionResponse:
    return await service.create_prediction(request)
```

### 🚨 反模式检测 (Anti-Patterns to Avoid)

#### ❌ 常见错误模式
```python
# 1. 在API层直接操作数据库
@app.post("/predictions")
async def create_prediction(request: CreatePredictionRequest, db: AsyncSession):
    # ❌ 错误：违反分层架构
    prediction = Prediction(**request.dict())
    db.add(prediction)
    await db.commit()

# 2. 同步数据库操作
def get_predictions_sync(db: Session):
    # ❌ 错误：应该使用异步操作
    return db.query(Prediction).all()

# 3. 硬编码配置
async def fetch_external_data():
    # ❌ 错误：应该使用环境变量
    api_key = "hardcoded_api_key_123"
    # ...
```

#### ✅ 正确的重构方式
```python
# ✅ 正确：分层架构 + 异步操作 + 配置管理
@app.post("/predictions")
async def create_prediction(
    request: CreatePredictionRequest,
    service: PredictionService = Depends(get_prediction_service)
):
    return await service.create_prediction(request)

async def get_predictions(db: AsyncSession):
    # ✅ 正确：异步操作
    stmt = select(Prediction)
    result = await db.execute(stmt)
    return result.scalars().all()

async def fetch_external_data(config: AppConfig = Depends(get_config)):
    # ✅ 正确：依赖注入配置
    api_key = config.external_api_key
    # ...
```

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

## 📞 Emergency Contacts

### 🆘 Critical Situations
- **Test Failures**: Run crisis solver → `make solve-test-crisis`
- **Code Quality**: Emergency fix → `make emergency-fix`
- **Environment Issues**: Create environment → `make create-env`
- **CI/CD Issues**: Full pipeline check → `make ci-check`

### 📚 Reference Documentation
- **Detailed Architecture**: `docs/ARCHITECTURE_FOR_AI.md`
- **Testing Guidelines**: `docs/TESTING_GUIDE.md`
- **API Documentation**: `http://localhost:8000/docs`
- **Project Status**: `make test-status-report`

---

**Remember**: As an AI maintainer, your priority is maintaining architectural integrity and code quality. When in doubt, choose the conservative approach that preserves existing patterns.

*Last Updated: 2025-11-21 | AI Maintainer: Claude Code | Version: 2.2 (Architecture Enhancement + Development Patterns)*

---

## 📝 CLAUDE.md 改进历史

### v2.2 - 当前版本 (2025-11-21)
**新增功能**:
- ✅ **高级架构概念** - DDD + CQRS实现细节和代码示例
- ✅ **关键开发模式** - 服务层、仓储、工厂等设计模式的最佳实践
- ✅ **异步架构模式** - 完整的异步操作模式和反模式检测
- ✅ **事件驱动架构** - 领域事件发布和事件驱动实现指南
- ✅ **测试模式增强** - 异步单元测试和集成测试的标准模式

**改进内容**:
- 添加项目类型和技术栈的快速识别标识
- 增强DDD + CQRS架构模式的详细实现指导
- 补充完整的代码模式和反模式检测指南
- 完善异步架构和事件驱动的设计模式
- 增加配置管理和依赖注入的最佳实践

### v2.1 - 前一版本 (2025-11-21)
**新增功能**:
- ✅ **前端开发指南** - 完整的React + TypeScript + Ant Design开发工作流
- ✅ **机器学习管理** - XGBoost模型生命周期管理和性能监控
- ✅ **API路由图谱** - 详细的40+个API端点架构和导航
- ✅ **技术栈增强** - 前后端完整技术栈说明和集成指导

**改进内容**:
- 添加前端React开发环境和项目结构说明
- 补充机器学习模型训练、部署和监控流程
- 完善API端点分类和核心业务接口说明
- 增强前后端集成和类型安全指导
- 更新开发工作流以支持全栈开发

### v2.0 - 前一版本 (2025-11-20)
**新增功能**:
- ✅ **项目状态快照** - 详细的项目健康评分和质量指标
- ✅ **快速诊断命令** - 5分钟环境健康检查和问题定位
- ✅ **外部文档链接** - 完整的文档和技术资源快速访问
- ✅ **增强指标显示** - 更详细的质量指标和状态标识

**改进内容**:
- 添加项目健康评分系统 (总分: 85/100)
- 新增快速诊断和自动化修复命令
- 完善外部文档链接体系
- 更新质量指标数据，增加更多状态信息
- 添加开发活跃区域和技术债务雷达

### v1.0 - 原始版本
- 基础的 AI 维护者指导框架
- 核心开发命令和架构指导
- 测试标准和代码规范
- Git 提交标准和危机处理方案

---

---

## 📈 Project Status & Metrics

### 🎯 Current Quality Indicators
- **CI Status**: ✅ Green baseline established
- **Test Coverage**: 29.0% (Target: 40%)
- **Test Suite**: 385 test cases, 269 test files
- **Code Quality**: Ruff + Bandit validation passing
- **Type Safety**: MyPy temporarily disabled for CI stability
- **Security**: Bandit scans passing, vulnerabilities addressed
- **Docker Status**: ✅ Multi-stage builds ready (dev/prod targets)
- **Dependencies**: ✅ All critical dependencies up-to-date

### 📊 Technical Debt Radar
- **High Priority**: Test coverage improvement (11% gap)
- **Medium Priority**: MyPy type checking re-enablement
- **Low Priority**: Documentation completeness (D series rules in Ruff)

### 🚀 Active Development Areas
- **Environment Setup**: Docker development environment optimization
- **Test Enhancement**: Coverage improvement towards 40% target
- **CI Pipeline**: Stability enhancements and automated recovery
- **Code Quality**: Baseline establishment and gradual improvement

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

---

## 🔄 Current Session Context

### 📝 Recent Changes (Git Status)
- Modified `.dockerignore`: Allow development dependencies for dev builds
- Modified `docker-compose.yml`: Use development build target for local development

### 🎯 Active Development Areas
- Docker development environment optimization
- Test coverage improvement (target: 40% from current 29.0%)
- CI/CD pipeline stability enhancements
- Code quality baseline establishment

### 🚀 Quick Start for New AI Instances
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

# 5. Frontend Development (optional)
cd frontend && npm install && npm start  # React开发服务器 (http://localhost:3000)
```

### 📁 Essential Project Files for AI Context
When starting work, always read these files first:
- **`pyproject.toml`**: Project dependencies, tool configurations, and build settings
- **`README.md`**: Project overview, status, and basic setup instructions
- **`docs/ARCHITECTURE_FOR_AI.md`**: Detailed AI-specific architecture guide
- **`Makefile`**: Complete development command reference (first 100 lines for overview)
- **`docker-compose.yml`**: Local development environment setup
- **`frontend/package.json`**: React frontend dependencies and scripts
- **`src/main.py`**: FastAPI application entry point and router configuration

### 📚 Essential Documentation
- **Project README**: Quick overview and installation guide
- **Testing Guide**: `docs/TESTING_GUIDE.md` - Comprehensive testing methodology
- **Architecture**: Understanding DDD+CQRS implementation
- **API Docs**: Interactive OpenAPI at `http://localhost:8000/docs`

### 🔗 Quick Access Links
#### 📖 核心文档
- **[Architecture Guide](docs/ARCHITECTURE_FOR_AI.md)** - AI架构导航指南
- **[Testing Guide](docs/TESTING_GUIDE.md)** - 完整测试方法论
- **[Test Improvement Guide](docs/TEST_IMPROVEMENT_GUIDE.md)** - 测试改进机制
- **[Project Handover](docs/PROJECT_HANDOVER.md)** - 项目交接文档
- **[Tools Documentation](./TOOLS.md)** - 完整工具使用指南

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
- **[Docker Compose](https://docs.docker.com/compose/)** - 容器编排文档

#### 📊 质量和监控
- **[Coverage Report](htmlcov/index.html)** - 测试覆盖率HTML报告
- **[Bandit Security Report](reports/security/bandit-report.html)** - 安全扫描报告
- **[Ruff Report](reports/quality/ruff-report.html)** - 代码质量报告
- **[Type Check Report](reports/quality/mypy-report.html)** - 类型检查报告

#### 🔧 开发工具
- **[Makefile Commands](#-core-commands-ai必须掌握的命令)** - 核心开发命令参考
- **[Docker Commands](#-docker-development-environment)** - Docker开发环境
- **[Testing Commands](#-ai-testing-protocol)** - 测试协议和命令
- **[Crisis Recovery](#-crisis-recovery-紧急情况处理)** - 紧急情况处理
