# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
# 环境检查 (开始工作前必做)
make env-check

# 代码质量修复 (发现问题时立即执行)
make fix-code

# 测试 (修改代码前后必须执行)
make test.smart       # 快速测试 (<2分钟)
make test.unit        # 完整单元测试
make test-status      # 查看测试状态报告

# 安全检查 (提交前必须执行)
make security-check
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
- **Python**: 3.10+ (支持现代类型注解)
- **Web Framework**: FastAPI 0.104+ (async-first)
- **ORM**: SQLAlchemy 2.0+ (async operations only)
- **Data Validation**: Pydantic v2+ (strict mode)
- **Testing**: pytest 8.4+ (with asyncio support)
- **Database**: PostgreSQL 15 (async driver)
- **Cache**: Redis 7.0+ (async operations)

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

### 🎯 Layer Responsibilities
- **`src/api/`**: FastAPI routers, request/response models, HTTP concerns only
- **`src/domain/`**: Business logic, entities, domain services (pure Python)
- **`src/services/`**: Application services, orchestration between layers
- **`src/database/`**: Database models, repositories, SQLAlchemy operations
- **`src/adapters/`**: External service integrations, third-party APIs

### 🚫 Forbidden Cross-layer Calls

```text
❌ API Layer → Database Layer (must go through Services)
❌ Domain Layer → External APIs (must go through Adapters)
❌ Services → FastAPI dependencies (inject from API layer)
✅ API → Services → Domain/Database/Adapters
```

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

### 🏷️ Test Markers (57个标准化标记)
```bash
# 核心测试组合 (AI日常使用)
pytest -m "unit and not slow" -v              # 单元测试 (快速)
pytest -m "critical and not slow" --maxfail=5 # 关键功能测试
pytest -m "smoke or critical" -v              # 冒烟测试

# 问题特定测试
pytest -m "regression" --maxfail=3            # 回归测试
pytest -m "issue94" -v                        # 特定问题测试

# CI/CD集成测试
make test-ci-integration                       # CI集成测试
make test-enhanced-coverage                    # 增强覆盖率分析
make test-report-generate                     # 生成综合测试报告
```

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

## 📊 Quality Metrics

### 🎯 Current Benchmarks
- **Test Coverage**: 29.0% (Target: 40%)
- **Test Files**: 269 files
- **Source Files**: 622 files
- **Test Markers**: 57 standardized markers
- **CI Pipeline**: Green baseline established
- **Flaky Test Management**: Automated isolation system in place
- **Quality Gates**: Ruff, MyPy, Bandit integration

### 📈 Quality Commands
```bash
make test-status-report  # 测试状态报告
make quality             # 完整的质量检查 (lint + format + all tests)
make ci-check           # 完整CI流程 (quality + test)
make coverage           # 覆盖率检查
```

---

## 🐳 Docker & Development Environment

### 🏗️ Container Architecture
The project uses multi-stage Docker builds with development and production targets:

```bash
# 开发环境 (热重载、调试支持)
docker-compose up --build                    # 启动完整开发栈
docker-compose up app db redis               # 选择性启动服务

# 生产环境部署
docker-compose -f docker-compose.prod.yml up
```

### 🔧 Service Stack
- **app**: FastAPI application (development target with hot reload)
- **db**: PostgreSQL 15 with persistent data
- **redis**: Redis 7.0 for caching and session management
- **nginx**: Reverse proxy (production only)

### 📁 Development Volumes
```yaml
volumes:
  - ./src:/app/src      # 源代码热重载
  - ./tests:/app/tests  # 测试文件同步
```

### 🌐 Environment Configuration
- Development environment variables in `.env`
- Production overrides in docker-compose.prod.yml
- Database connection pooling configured for both environments

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

*Last Updated: 2025-11-20 | AI Maintainer: Claude Code*

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
