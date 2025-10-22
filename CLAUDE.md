# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

## Project Overview

This is a football prediction system built with FastAPI, PostgreSQL, Redis, and modern Python technologies. The project follows enterprise-grade architecture patterns with Domain-Driven Design (DDD), CQRS, and microservices principles.

**Key Metrics:**
- Test Coverage: 16.5% (target: >=80%, currently improving)
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
make help         # Show all available commands (120+ commands)
make env-check    # Check development environment health
make lint         # Run ruff and mypy checks
make fmt          # Format code with ruff
make ci           # Simulate complete CI pipeline
make prepush      # Complete pre-push validation
```

### Complete Makefile Toolchain

#### 环境管理
```bash
make env-check          # 检查开发环境健康
make venv               # 创建和激活虚拟环境
make install            # 从锁文件安装依赖
make install-locked     # 从锁文件安装可重现依赖
make lock-deps          # 锁定当前依赖用于可重现构建
make verify-deps        # 验证依赖与锁文件匹配
make smart-deps         # AI指导的智能依赖检查
make clean-env          # 清理虚拟环境和旧依赖文件
```

#### 测试工具
```bash
make test               # 运行pytest单元测试
make test-api           # 运行所有API测试
make test-full          # 运行完整单元测试套件
make coverage           # 运行覆盖率测试（阈值：80%）
make test-integration   # 运行集成测试
make test-all           # 在测试环境中运行所有测试
make test-env-start     # 启动集成/E2E测试环境
make test-env-stop      # 停止测试环境
make test-env-status    # 检查测试环境状态
make test-debt-analysis # 运行全面的测试债务分析
```

#### 高级测试功能
```bash
make coverage-parallel     # 并行执行覆盖率测试
make coverage-targeted     # 运行特定模块的覆盖率测试
make coverage-critical      # 关键路径模块100%覆盖率测试
make mutation-test          # 运行mutmut变异测试
make mutation-html          # 生成HTML变异测试报告
```

#### 夜间测试
```bash
make nightly-test           # 本地运行夜间测试套件
make nightly-schedule       # 启动夜间测试调度器
make nightly-monitor        # 监控和报告夜间测试结果
make nightly-report         # 生成夜间测试报告
```

#### 性能分析
```bash
make benchmark-full         # 运行全面的性能基准测试
make benchmark-regression   # 运行性能回归检测
make flamegraph             # 生成性能可视化火焰图
make profile-app            # 分析主应用程序性能
make profile-tests          # 分析测试执行性能
```

#### Staging环境
```bash
make staging-start          # 启动staging环境用于E2E测试
make staging-stop           # 停止staging环境
make staging-migrate        # 运行数据库迁移
make staging-test           # 运行E2E测试
make staging-health         # 检查staging环境健康
```

#### 技术债务管理
```bash
make debt-plan              # 显示每日技术债务清理计划
make debt-today             # 快速开始今日债务清理工作
make debt-status            # 显示当前任务和状态
make debt-progress          # 查看整体清理进度
```

#### 最佳实践优化
```bash
make best-practices-today   # 快速开始今日最佳实践工作
make best-practices-check   # 运行代码质量和最佳实践检查
make best-practices-progress # 查看整体最佳实践优化进度
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
项目使用19种测试标记来分类测试：

- `unit`: 单元测试 - 测试单个函数或类
- `integration`: 集成测试 - 测试多个组件的交互
- `api`: API测试 - 测试HTTP端点
- `database`: 数据库测试 - 需要数据库连接
- `slow`: 慢速测试 - 运行时间较长的测试
- `smoke`: 冒烟测试 - 基本功能验证
- `auth`: 认证相关测试
- `cache`: 缓存相关测试
- `monitoring`: 监控相关测试
- `e2e`: 端到端测试 - 完整的用户流程测试
- `performance`: 性能测试 - 基准测试和性能分析
- `asyncio`: 异步测试 - 基于asyncio的协程用例
- `regression`: 回归测试 - 验证修复的问题不会重现
- `critical`: 关键测试 - 必须通过的核心功能测试

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

**⚠️ 关键测试规则**
**永远不要**对单个测试文件添加 `--cov-fail-under` - 这会破坏CI流水线集成。项目有复杂的覆盖率跟踪系统，仅在集中管理时覆盖率阈值才正常工作。

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

### Ruff Configuration Details
From `pyproject.toml`:
- **Python Target**: 3.11+
- **Line Length**: 88 characters
- **Test File Exceptions**: More relaxed rules for test files:
  - `F401`: Unused imports (common in test files)
  - `F811`: Redefinition (common in test files)
  - `F821`: Undefined names (common with mocks)
  - `E402`: Module level imports not at top (test file specific)

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

### Docker Multi-Environment Configuration
项目支持通过环境变量切换不同环境：

#### 开发环境
```bash
docker-compose up  # 自动加载override配置
```

#### 生产环境
```bash
ENV=production docker-compose --profile production up -d
```

#### 测试环境
```bash
ENV=test docker-compose --profile test run --rm app pytest
```

#### 可选服务配置
- **nginx**: 反向代理（production、staging）
- **prometheus**: 监控（monitoring、production）
- **grafana**: 监控面板（monitoring、production）
- **loki**: 日志收集（logging、production）
- **celery-worker**: Celery工作进程（celery、production）
- **celery-beat**: Celery定时任务（celery、production）

#### 开发工具（tools profile）
- **adminer**: 数据库管理工具 (http://localhost:8080)
- **redis-commander**: Redis管理工具 (http://localhost:8081)
- **mailhog**: 邮件模拟器 (http://localhost:8025)
- **pyroscope**: 性能分析 (http://localhost:4040)

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

### 质量要求
- **质量要求**: 所有文档必须通过 `make docs.check`（Docs Guard验证）
- **目录限制**: 允许的目录包括 `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
- **无孤立文档**: 一切都必须从INDEX.md链接
- **持续验证**: 自动化文档健康检查

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
make security-check      # Run vulnerability scan
make audit               # Complete security audit
make secret-scan         # Scan for hardcoded secrets
make license-check       # Check open source licenses
make dependency-check    # Check for outdated dependencies
make audit-vulnerabilities # Run dependency vulnerability audit
```

### Security and Compliance Features
- **JWT Token Authentication**: 基于令牌的认证机制
- **RBAC Permission Control**: 角色基础访问控制
- **SQL Injection Protection**: ORM层保护机制
- **XSS and CSRF Protection**: 跨站脚本和请求伪造防护
- **HTTPS Enforcement**: 生产环境强制HTTPS
- **Environment Variable Encryption**: 敏感配置加密存储
- **Audit Logging**: 操作记录和追踪
- **Database Security**: 连接池和权限管理

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

### Monitoring and Observability
项目具备完整的监控和可观测性体系：

#### 监控生态系统
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化监控面板
- **Loki**: 日志聚合和查询
- **Health Checks**: 服务状态监控
- **APM Integration**: 应用性能监控
- **Performance Profiling**: 性能分析和优化

#### 监控工具
```bash
make coverage-dashboard     # 生成实时覆盖率监控面板
make coverage-trends        # 显示覆盖率趋势和历史
make coverage-live          # 启动实时覆盖率监控（自动刷新）
```

#### 日志管理
- **Structured Logging**: 结构化JSON日志格式
- **Log Level Management**: 环境驱动的日志级别
- **Log Aggregation**: 分布式日志收集
- **Audit Logs**: 操作审计日志

#### 性能分析
- **Performance Metrics**: 应用性能指标收集
- **Flame Graphs**: 性能可视化火焰图
- **Memory Profiling**: 内存使用分析
- **Benchmark Testing**: 性能基准测试
- **Regression Detection**: 性能回归检测

#### Health Check Endpoints
- **Application Health**: `/health` - 应用程序健康状态
- **Database Health**: 数据库连接和性能检查
- **Redis Health**: 缓存服务状态检查
- **Service Dependencies**: 外部依赖服务检查

## Development Workflow

### AI-Assisted Development
遵循工具优先原则的开发流程：

1. **环境检查** - `make env-check` 检查开发环境健康
2. **加载上下文** - `make context` 为AI加载项目上下文
3. **开发和测试** - 使用适当的测试策略
4. **质量验证** - `make ci` 运行完整质量检查
5. **预提交验证** - `make prepush` 完整的预推送验证

### 本地CI验证
在提交代码前运行完整的本地CI验证：

```bash
./ci-verify.sh
```

该脚本会执行完整的CI验证流程：
1. **虚拟环境重建** - 清理并重新创建虚拟环境，确保依赖一致性
2. **Docker环境启动** - 启动完整的服务栈（应用、数据库、Redis、Nginx）
3. **测试执行** - 运行所有测试并验证代码覆盖率 >= 78%

如果脚本输出 "🎉 CI 绿灯验证成功！" 则可以安全推送到远程。

### 文档验证
所有文档必须通过 `make docs.check`（Docs Guard验证）

#### 文档质量要求
- **允许的目录**: `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
- **无孤立文档** - 一切都必须从INDEX.md链接
- **质量门禁** - 所有文档必须通过验证系统

### GitHub Issues 双向同步
项目包含完整的GitHub Issues同步工具：

```bash
# 设置环境变量
source github_sync_config.sh

# 双向同步 Issues
make sync-issues
# 或
python scripts/sync_issues.py sync
```

功能特性：
- 📥 从 GitHub 拉取 Issues 到本地 `issues.yaml`
- 📤 推送本地 Issues 到 GitHub
- 🔄 双向同步，保持数据一致性
- 📝 支持批量管理和团队协作

### Best Practices
- Use dependency injection container
- Follow repository pattern for data access
- Implement proper error handling with custom exceptions
- Use async/await for I/O operations
- Write comprehensive unit and integration tests
- Use type annotations throughout
- **CRITICAL**: Never use `--cov-fail-under` with single files - it breaks CI integration
- Use markers wisely: `-m "unit"` for unit tests only, `-m "not slow"` to skip slow tests

### 高级开发模式

#### 事件驱动架构
系统实现了完整的事件驱动架构：
- **事件总线**: 统一事件分发机制
- **事件处理器**: 各种业务事件处理
- **观察者模式**: 监听器系统
- **领域事件**: 匹配事件、预测事件等业务事件

#### CQRS模式
实现了Command Query Responsibility Segregation：
- **命令处理**: 写操作处理
- **查询处理**: 读操作优化
- **DTO模式**: 数据传输对象
- **领域模型隔离**: 读写模型分离

#### 依赖注入容器
`src/core/di.py` 实现了完整的依赖注入系统：
- **自动绑定**: 自动组件注册
- **生命周期管理**: 服务生命周期控制
- **环境感知**: 环境特定配置

#### 优雅关闭机制
系统实现了完整的优雅关闭流程：
- **资源清理**: 连接和资源释放
- **任务完成**: 等待中任务完成
- **状态保存**: 应用状态持久化

### 故障排除指南

#### 常见问题
- **端口冲突**: 确保端口5432、6379、80可用
- **Docker问题**: 检查Docker守护进程和docker-compose版本
- **测试失败**: 验证测试环境是否正确设置
- **覆盖率下降**: 运行 `make coverage-targeted MODULE=<module>`

#### 调试命令
```bash
make test-env-status    # 检查测试环境健康
make env-check          # 验证开发环境
make logs               # 查看服务日志
```

### 环境特定配置

#### 开发环境特性
- **热重载**: 开发环境自动重启
- **调试模式**: 调试信息和详细日志
- **测试隔离**: 测试环境独立
- **代码分析**: 实时代码质量检查

#### 团队协作功能
- **Git Hooks**: 提交前检查
- **代码审查**: 质量门禁
- **分支策略**: Git Flow模式
- **发布管理**: 版本控制和发布流程

## Key Configuration Files

- `pyproject.toml`: Ruff configuration, tool settings
- `pytest.ini`: Test configuration and markers
- `requirements/requirements.lock`: Locked dependencies
- `Makefile`: Complete development toolchain (613 lines)
- `.env.example`: Environment variable template

## Important Development Notes

### ⚠️ 关键测试规则
**永远不要**对单个测试文件添加 `--cov-fail-under` - 这会破坏CI流水线集成。项目有复杂的覆盖率跟踪系统，仅在集中管理时覆盖率阈值才正常工作。

### 🎯 何时打破规则
虽然首选Makefile命令，但以下情况允许直接使用pytest：
- **调试特定测试失败**
- **处理隔离的功能**
- **开发期间的快速反馈**

始终使用适当的标记，避免在单文件命令中使用覆盖率阈值。

### 📂 文档标准
- **质量要求**: 所有文档必须通过 `make docs.check`（Docs Guard验证）
- **目录限制**: 允许的目录包括 `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
- **无孤立文档**: 一切都必须从INDEX.md链接
- **持续验证**: 自动化文档健康检查

### 🔒 安全要求
- **JWT认证**: 基于令牌的身份验证
- **RBAC权限**: 角色基础访问控制
- **注入防护**: SQL注入、XSS、CSRF保护
- **HTTPS强制**: 生产环境安全连接
- **敏感信息**: 环境变量加密存储
- **审计日志**: 操作记录和追踪

### 🐳 容器化最佳实践
- **多阶段构建**: 开发、测试、生产环境分离
- **健康检查**: 所有服务的健康状态监控
- **优雅关闭**: 正确处理信号和资源清理
- **环境隔离**: 通过环境变量管理不同配置
- **服务发现**: 基于Docker Compose的服务协调

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