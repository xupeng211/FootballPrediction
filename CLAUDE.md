# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**当前分支状态**：recovery/restore-from-safe-point - 正在从安全点恢复代码到稳定状态。

**重要提示**：当前处于恢复状态，不要进行大规模重构。优先运行测试确保系统稳定性。

## 🌏 语言设置

**重要规则：在与用户交流时，请使用简体中文回复。** 用户不懂英文，所以所有解释和说明都应该用中文。

- 与用户的所有对话都使用简体中文
- 代码注释可以使用英文，但解释要用中文
- 错误信息和技术术语的解释也要用中文

## 项目简介

这是一个足球预测系统，使用 FastAPI、SQLAlchemy、Redis 和 PostgreSQL 构建。项目采用现代 Python 架构，具有完整的测试、CI/CD 和 MLOps 功能。

**核心理念**：先让 CI 绿灯亮起，再逐步提高标准！采用渐进式改进策略。

**当前项目状态**（2025-01-17）：
- 分支：recovery/restore-from-safe-point（从安全点恢复）
- 测试覆盖率：28.21%（已从6%大幅提升）
- CI 覆盖率门槛：30%（已从 20% 提升）
- 代码质量评分：8.5/10 ✅ 已达成最佳实践目标
- 测试优化：已完成并行测试基础设施，config_loader和dict_utils达到100%覆盖率
- 采用渐进式改进策略，确保持续集成保持绿灯

### 开发命令

#### ⚠️ 恢复模式特别说明
**当前处于恢复分支**，请遵循以下原则：
- ❌ 不要进行大规模重构
- ✅ 可以修复明显的错误
- ✅ 可以添加缺失的测试
- ✅ 必须运行测试确保稳定性

#### 环境设置
```bash
make install          # 从锁文件安装依赖
make install-locked   # 从锁定文件安装（可重现构建）
make env-check        # 检查开发环境是否健康
make context          # 加载项目上下文供 AI 开发使用
make dev-setup        # 一键设置开发环境
make clean            # 清理缓存和虚拟环境
make clean-env        # 清理虚拟环境和旧依赖文件
make lock-deps        # 锁定依赖以保证可重现构建
make verify-deps      # 验证依赖是否与锁定文件匹配
make smart-deps       # 智能依赖检查（AI指导）
make audit-vulnerabilities  # 运行依赖漏洞审计
```

**重要提示**：
- 不要直接运行 `pytest`，必须使用 Makefile 命令
- 推荐使用 `./scripts/ci-verify.sh` 进行完整的 CI 验证
- 日常开发使用 `make test-quick`（60秒超时）
- 推送前必须运行 `./scripts/ci-verify.sh` 确保 CI 能够通过
- **恢复期间**：每次修改后立即运行 `make test-quick` 验证

#### 测试
```bash
make test             # 运行所有单元测试
make test-quick       # 快速单元测试（60秒超时，最多5个失败）【恢复期间推荐】
make test-unit        # 只运行单元测试（标记为 'unit' 的）
make test-phase1      # 运行第一阶段核心 API 测试
make test-api         # 运行所有 API 测试
make test.containers  # 运行需要 Docker 容器的测试
make coverage         # 运行测试并检查覆盖率（CI默认22%）
make coverage-fast    # 快速覆盖率检查（仅单元测试）
make coverage-local   # 本地覆盖率检查（18%阈值）
make coverage-optimized # 优化的快速测试（仅快速测试）
make coverage-targeted MODULE=xxx  # 针对特定模块的测试
make coverage-parallel # 并行测试（实验性）
make prepush          # 完整的提交前验证（ruff + mypy + pytest）【恢复期间必须】
```

#### 单个测试运行（基于 Cursor 测试规范）
```bash
# 运行特定测试文件
pytest tests/unit/test_specific.py -v

# 运行特定测试函数
pytest tests/unit/test_specific.py::test_function -v

# 运行带特定标记的测试
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "not slow" -v
pytest -m "fast or unit" -v  # 优化测试组合

# 调试模式
pytest tests/unit/test_specific.py -v -s --pdb

# 只运行失败的测试
pytest --lf -v

# 在第一个失败时停止
pytest -x -v

# 限制失败次数
pytest --maxfail=5 -v

# 运行性能基准测试
pytest tests/performance/ --benchmark-only

# 运行容器测试
pytest -m "integration" -v  # 需要 Docker 运行
pytest tests/unit/test_database_with_containers.py  # TestContainers

# 快速测试（日常开发）
make test-quick          # 快速单元测试（60秒超时，最多5个失败）
make test.unit           # 只运行单元测试（标记为'unit'）
make coverage-optimized  # 优化的快速测试（仅fast或unit测试）

# 覆盖率测试
make coverage-local      # 本地覆盖率检查（20%阈值）
make coverage-ci         # CI覆盖率检查（22%阈值）
make coverage-parallel   # 并行测试（使用所有CPU核心）
make coverage-targeted MODULE=src.utils.config_loader  # 模块特定测试

# 测试环境管理
make test-env-start      # 启动集成测试环境
make test-env-stop       # 停止测试环境
make test-env-status     # 检查测试环境状态
```

#### 代码质量
```bash
make lint             # 运行 ruff 和 mypy 检查
make fmt              # 使用 ruff 格式化代码（已替换 black 和 isort）
make quality          # 完整质量检查（lint + format + test）
make prepush          # 完整的提交前验证（ruff + mypy + pytest）
make ci               # 模拟 GitHub Actions CI 流程
make ruff-check       # 仅运行 ruff 检查
make ruff-format      # 仅运行 ruff 格式化
make mypy-check       # 仅运行 mypy 类型检查
./scripts/quality-check.sh  # 推荐的快速质量检查（5-10秒）
./scripts/ci-verify.sh     # 完整的 CI 验证（推荐推送前运行）
```

#### 性能和高级测试
```bash
make benchmark-full       # 运行完整的性能基准测试
make mutation-test        # 运行突变测试（mutmut）
make test-debt-analysis   # 分析测试债务
make coverage-dashboard   # 生成实时覆盖率仪表板
make test-quick           # 快速单元测试（60秒超时）
make test-unit            # 只运行单元测试（标记为 'unit'）
make test-phase1          # 运行第一阶段核心 API 测试
```

#### Docker 容器管理
```bash
make up               # 启动所有 Docker 服务
docker-compose up -d  # 后台启动服务
docker-compose ps     # 查看服务状态
make down             # 停止所有 Docker 服务
make logs             # 查看 Docker 日志
docker-compose logs -f app  # 查看特定服务日志
make deploy           # 部署应用（使用 git SHA 标签）
make rollback TAG=xxx # 回滚到指定版本

# 测试环境管理（使用管理脚本）
make test-env-start   # 启动测试环境
make test-env-stop    # 停止测试环境
make test-env-restart # 重启测试环境
make test-env-shell   # 进入测试容器
make test-env-reset   # 重置测试环境（删除所有数据）
```

#### 技术债务管理
```bash
make debt-plan        # 查看每日技术债务清理计划
make debt-today       # 一键开始今天的工作（默认4小时）
make debt-start TASK=1.1.1    # 开始执行特定任务
make debt-done        # 完成当前任务
make debt-status      # 查看当前状态
make debt-check       # 运行代码健康检查
make debt-progress    # 查看整体清理进度
make debt-summary     # 生成清理总结报告
```

#### 最佳实践优化
```bash
make best-practices-plan        # 查看今天的优化任务
make best-practices-today       # 一键开始今天的工作
make best-practices-start TASK=1.1  # 开始特定任务
make best-practices-done        # 完成当前任务
make best-practices-check       # 运行代码质量检查
make best-practices-progress    # 查看整体进度
make best-practices-summary     # 生成优化总结报告
make best-practices-status      # 查看当前状态
./scripts/check_best_practices.sh  # 运行最佳实践检查脚本
```

## 架构说明

### 核心目录结构

> 📖 **详细架构文档**：查看 [docs/architecture.md](docs/architecture.md) 获取完整的系统架构说明

```
src/
├── api/              # FastAPI 路由和端点
│   ├── app.py       # 主应用入口
│   ├── dependencies.py # 依赖注入
│   ├── cqrs.py      # CQRS 模式实现
│   ├── events.py    # 事件系统
│   └── observers.py # 观察者模式
├── domain/           # 领域层（DDD）
│   ├── models/      # 领域模型
│   └── services/    # 领域服务
├── database/         # 数据层
│   ├── models/      # SQLAlchemy 模型
│   ├── migrations/  # Alembic 迁移
│   ├── repositories/ # 仓储模式
│   └── connection*.py # 数据库连接
├── services/         # 服务层
│   ├── base_unified.py # 统一基础服务
│   └── *.py         # 业务服务
├── cache/            # 缓存层
│   ├── redis_manager.py # Redis 管理
│   └── decorators.py # 缓存装饰器
├── monitoring/       # 监控系统
│   ├── system_monitor.py
│   ├── metrics_collector.py
│   └── health_checker.py
├── streaming/        # 流处理（Kafka）
├── scheduler/        # 任务调度（Celery）
├── core/            # 核心组件
│   ├── exceptions.py # 异常定义
│   ├── logger.py    # 日志系统
│   └── di.py        # 依赖注入容器
└── utils/           # 工具类
```

### 关键架构模式

#### 设计模式
- **工厂模式**：测试数据生成（`tests/factories/`）
- **依赖注入**：使用内置 DI 容器（`src/core/di.py`）
- **仓储模式**：数据访问抽象（`src/database/repositories/`）
- **领域驱动设计**：领域模型和业务规则分离（`src/domain/`）
- **事件驱动架构**：系统事件和观察者模式（`src/api/events.py`, `src/api/observers.py`）
- **CQRS 模式**：命令查询责任分离（`src/api/cqrs.py`）

#### 技术选型
- **异步 SQLAlchemy**：使用 asyncpg 驱动，支持高并发
- **统一基础服务**：所有服务继承 `BaseService`（`src/services/base_unified.py`）
- **Pydantic 数据验证**：API 请求/响应验证
- **KeyManager 密钥管理**：禁止硬编码密钥
- **结构化日志**：JSON 格式日志记录
- **TestContainers**：集成测试支持

### 当前架构状态（2025-01-13）
- **代码质量评分**：8.5/10 ✅ 已达成最佳实践目标
- **测试覆盖率**：28.21%（持续优化中）
- **CI 覆盖率门槛**：22%（实际值，30%为目标）
- **测试优化成就**：
  - config_loader.py: 100%覆盖率
  - dict_utils.py: 100%覆盖率
  - retry.py: 100%覆盖率
- **架构亮点**：
  - ✅ 统一基础服务类（`src/services/base_unified.py`）
  - ✅ 仓储模式实现完成（`src/database/repositories/`）
  - ✅ 领域模型引入（`src/domain/models/`）
  - ✅ 依赖注入系统（`src/core/di.py`）
  - ✅ 事件驱动架构（`src/api/events.py`）
  - ✅ CQRS 模式（`src/api/cqrs.py`）
  - ✅ 多种设计模式应用（工厂、DI、仓储、事件等）
  - ✅ 模块化架构，易于扩展和维护

### 关键配置文件
- `pyproject.toml`：Ruff配置和项目元数据
- `pytest.ini`：测试配置和标记定义
- `mypy.ini`：类型检查配置
- `coverage_local.ini`：本地覆盖率配置
- `docker-compose.yml`：容器编排配置

## 测试优化指南

### 测试基础设施（2025-01-13新增）

#### 新的测试命令
```bash
# 日常开发优化测试
make coverage-optimized    # 仅运行快速测试

# 针对特定模块测试
make coverage-targeted MODULE=src.utils.config_loader

# 并行测试（实验性）
make coverage-parallel     # 使用所有CPU核心

# 单模块快速测试
pytest tests/unit/utils/test_config_loader_comprehensive.py --cov=src.utils.config_loader
```

#### 已达到100%覆盖率的模块
- `config_loader.py`: 配置文件加载（JSON/YAML）
- `dict_utils.py`: 字典深度操作工具
- `retry.py`: 重试机制工具

#### 测试标记系统
- `unit`: 单元测试（快速）
- `integration`: 集成测试（较慢）
- `fast`: 快速测试（<1秒）
- `slow`: 慢速测试（>1秒）
- `e2e`: 端到端测试（最慢）

> 📖 **详细测试指南**：查看 [TESTING_GUIDE.md](TESTING_GUIDE.md) 获取完整的测试选择策略

## 测试指南

### 测试组织结构
```
tests/
├── unit/            # 单元测试（标记为 'unit'）
│   ├── core/       # 核心业务逻辑测试
│   ├── api/        # API 路由和端点测试
│   ├── services/   # 服务层测试
│   ├── database/   # 数据库模型和查询测试
│   ├── repositories/ # 仓储模式测试
│   ├── domain/     # 领域模型测试
│   └── utils/      # 工具函数测试
├── integration/     # 集成测试（标记为 'integration'）
│   ├── api/        # API 集成测试
│   ├── database/   # 数据库集成测试
│   └── services/   # 服务集成测试
├── e2e/            # 端到端测试（标记为 'e2e'）
├── performance/    # 性能基准测试
├── factories/      # 测试数据工厂
├── conftest.py     # pytest 配置和共享夹具
└── debt/          # 测试债务分析
```

> 📖 **详细测试指南**：查看 [docs/test_guidelines.md](docs/test_guidelines.md) 获取完整的测试编写指南和最佳实践

### 测试标记系统
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.api` - API 测试
- `@pytest.mark.database` - 数据库测试

### 测试执行策略
- **日常开发**：使用 `make test-quick` 快速反馈（60秒超时）
- **提交前**：运行 `make prepush` 完整验证
- **CI 模拟**：使用 `make ci` 本地模拟
- **覆盖率检查**：
  - 本地开发：`make coverage-local`（18%阈值）
  - CI 环境：`make coverage`（22%实际，30%目标）
  - 快速检查：`make coverage-optimized`
- **容器测试**：`pytest -m "integration"` 需要 Docker 运行
- **模块测试**：`make coverage-targeted MODULE=xxx`
- **分阶段测试**：
  - Phase 1: `make test-phase1`（核心API测试）
  - API测试: `make test-api`（所有API端点）
  - 单元测试: `make test-unit`（仅单元测试）

## 恢复模式指南

### 当前状态
- 分支：recovery/restore-from-safe-point
- 目标：恢复代码到稳定状态
- 策略：保守修复，避免引入新问题

### 恢复期间的最佳实践
1. **最小化修改**：只修复必要的错误
2. **频繁测试**：每次修改后立即运行 `make test-quick`
3. **小步提交**：完成一个小修复就提交一次
4. **保留日志**：记录所有修改和测试结果

### 恢复完成后
1. 运行完整的测试套件：`make test && make coverage`
2. 执行代码质量检查：`make lint && make fmt`
3. 生成恢复报告：记录所有修复的问题
4. 创建 PR 到 develop 或 main 分支

## 新开发者快速上手

### 🎯 必读文档（按优先级）
1. **本文档**：了解开发命令和架构
2. **[.claude-preferences.md](/.claude-preferences.md)**：理解用户开发哲学和渐进式改进理念
3. **[测试运行指南](TEST_RUN_GUIDE.md)**：学习正确的测试方法
4. **[架构文档](docs/architecture.md)**：深入理解系统架构

### 🚀 5分钟快速设置（恢复模式）
```bash
# 1. 环境检查
make env-check        # 确认 Python 环境健康

# 2. 安装依赖
make install          # 从锁文件安装依赖

# 3. 加载上下文
make context          # 加载项目上下文到 AI 助手

# 4. 验证环境（恢复期间必须）
make test-quick       # 快速测试（60秒内完成）
```

### 📋 日常开发流程（恢复模式）
1. **开发前**：`make context && make env-check`
2. **开发中**：每 5-10 分钟运行 `make test-quick`（比平时更频繁）
3. **修改后**：立即运行 `make test-quick` 验证
4. **提交前**：`make fmt && make lint && make prepush`
5. **推送前**：`./scripts/ci-verify.sh`（完整 CI 验证）

### 日常开发流程
1. **开始开发前**
   ```bash
   make context        # 加载项目上下文到 AI 助手
   make env-check      # 确认环境健康
   ```

2. **开发过程中**
   ```bash
   # 每 10-15 分钟
   make test-quick     # 快速测试反馈

   # 功能完成后
   make test-unit      # 运行单元测试
   make coverage-local # 检查覆盖率（16%）
   ```

3. **提交前检查**
   ```bash
   make fmt            # 格式化代码
   make lint           # 代码质量检查
   make prepush        # 完整预推送验证
   ```

4. **推送前验证**（推荐）
   ```bash
   ./scripts/ci-verify.sh  # 完整 CI 验证
   # 或
   make ci             # 快速 CI 模拟
   ```

### 分支管理策略
- **main**: 生产环境代码，只接受 PR
- **develop**: 开发主分支，功能集成
- **recovery/***: 恢复分支（如当前 recovery/restore-from-safe-point）
- **feature/***: 功能开发分支
- **hotfix/***: 紧急修复分支
- **wip/***: 工作进行中分支（如技术债务清理）

**重要提示**：
- 当前在恢复分支，需要先恢复代码到稳定状态
- 恢复完成后，应创建 PR 到 develop 或 main 分支

### CI/CD 工作流理解
1. **触发条件**
   - Push 到 main/develop/hotfix 分支
   - 创建 Pull Request
   - 手动触发

2. **CI 阶段**
   ```mermaid
   graph LR
   A[基础检查] --> B[代码质量]
   B --> C[单元测试]
   C --> D[集成测试]
   D --> E[构建镜像]
   E --> F[安全扫描]
   F --> G[部署/通知]
   ```

3. **质量门禁**
   - 代码覆盖率 >= 30%（已从 20% 提升）
   - 所有 Ruff/MyPy 检查通过
   - 安全扫描无高危漏洞

### MLOps 工作流
1. **模型训练流程**
   - 数据收集 → 特征工程 → 模型训练 → 模型评估
   - 自动触发：每日 8:00 UTC（通过 Celery）
   - 手动触发：`make mlops-pipeline`

2. **模型部署流程**
   - 模型验证 → 创建 PR → 人工审核 → 合并部署
   - 需要 2 人审核才能部署到生产环境

3. **反馈循环**
   - 收集预测结果 → 更新模型性能 → 触发重训练
   - 使用 MLflow 跟踪模型版本

### 代码审查流程
1. **创建 Pull Request**
   - 使用清晰的标题和描述
   - 关联相关 Issue
   - 添加适当的标签

2. **审查要求**
   - 至少一人审查批准
   - 所有 CI 检查通过
   - 解决所有审查意见

3. **合并规范**
   - 使用 squash merge
   - 删除功能分支
   - 更新版本号（如需要）

### 发布流程
1. **版本管理**
   ```bash
   # 查看当前版本
   git tag -l

   # 创建新版本
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **发布检查清单**
   - [ ] 所有测试通过
   - [ ] 文档已更新
   - [ ] CHANGELOG 已更新
   - [ ] 版本号已更新
   - [ ] 性能测试通过

## 近期项目改进（2025-01-13）

### 测试优化成果
- **覆盖率提升**：从6% → 28.21%（增长370%）
- **三个模块达到100%覆盖率**：
  - config_loader.py（18% → 100%）
  - dict_utils.py（27% → 100%）
  - retry.py（保持100%）
- **新增测试基础设施**：
  - 并行测试支持（pytest-xdist）
  - 针对性模块测试
  - 快速测试优化

### 已修复的问题
- 9个语法错误修复
- 1个导入问题修复（AsyncSession）
- 3个pytest标记问题
- 2个收集错误修复（重复文件）
- AsyncClient导入错误修复

## 技术债务清理

### 当前状态
- 技术债务分支：`wip/technical-debt-and-refactoring`
- 测试覆盖率：28.21%（已超出目标）
- 代码质量：8.5/10（优秀）

### 技术债务清理命令
```bash
# 查看每日清理计划
make debt-plan         # 显示今天的技术债务清理任务
make debt-today        # 一键开始今天的工作（默认4小时）

# 任务管理
make debt-start TASK=1.1.1    # 开始执行特定任务
make debt-done               # 完成当前任务
make debt-status             # 查看当前状态

# 监控和报告
make debt-check              # 运行代码健康检查
make debt-progress           # 查看整体清理进度
make debt-summary            # 生成清理总结报告
```

### 清理阶段概览
1. **Phase 1**: 紧急问题修复（语法错误、编码问题）
2. **Phase 2**: 核心模块重构（API、监控、缓存系统）
3. **Phase 3**: 测试覆盖率提升（16.51% → 21.78%）✅ 已完成
4. **Phase 4**: 代码质量优化（类型注解、文档、性能）

详细信息请查看：[TECHNICAL_DEBT_KANBAN.md](TECHNICAL_DEBT_KANBAN.md)

## 最佳实践优化

### 当前状态（2025-01-12）
- ✅ **已完成 Phase 4**：代码质量评分达到 8.5/10
- **主要成就**：
  - 统一基础服务类实现
  - 仓储模式完整实现
  - 领域模型引入
  - 依赖注入系统建立
  - 事件驱动架构
  - CQRS 模式应用
- 详情请查看：[BEST_PRACTICES_KANBAN.md](BEST_PRACTICES_KANBAN.md)

## 重要说明

### 技术栈
- **Python**: 3.11+
- **FastAPI**: 0.115.6
- **SQLAlchemy**: 2.0.36（异步支持）
- **Pydantic**: 2.10.4
- **PostgreSQL**: 15
- **Redis**: 7
- **Celery**: 5.4.0（异步任务）
- **Ruff**: 代码格式化和检查（替代 black/flake8/isort）
- **MyPy**: 静态类型检查
- **pytest**: 测试框架，支持标记和覆盖率

### 依赖管理
- 项目使用 pip-tools 进行依赖管理（requirements/ 目录）
- **requirements/base.txt** - 基础依赖
- **requirements/dev.lock** - 开发依赖锁定
- **requirements/requirements.lock** - 完整依赖锁定

### 代码质量工具
- **代码格式化和检查**：已完全迁移到 Ruff（替代 flake8、black、isort）
- **静态类型检查**：MyPy 配置完整，新代码必须包含类型注解
- **测试框架**：pytest，支持标记系统和覆盖率报告
- **容器化**：Docker Compose 提供本地开发的 PostgreSQL、Redis 和 Nginx
- **MLOps**：完整的模型训练、部署和反馈循环流程

## 项目特定规则

### 代码风格（基于 Cursor 规则）
- **修改优先**：优先修改已有文件，避免不必要的文件创建
- **模块化设计**：保持文件功能单一，避免过度复杂的模块
- **依赖注入**：使用 `src/core/di.py` 容器管理依赖
- **统一基础服务**：所有服务继承 `BaseService`（`src/services/base_unified.py`）
- **命名规范**：
  - 变量和函数：snake_case
  - 类名：PascalCase
  - 常量：UPPER_SNAKE_CASE
  - 私有成员：前缀下划线
- **类型注解**：所有公共接口必须有完整类型注解
- **文档字符串**：使用 Google 风格 docstring，函数和类使用清晰的中文说明
- **格式化工具**：使用 Ruff（已替代 black/flake8/isort）
  - 运行 `make fmt` 进行格式化
  - 运行 `make ruff-check` 进行检查
- **异步优先**：全栈使用 async/await 模式

### 数据库相关
- 使用异步 SQLAlchemy 2.0 操作（asyncpg 驱动）
- 所有数据库操作必须在 service 层，不要在 API 层直接操作
- 使用 Alembic 进行数据库迁移
- 使用仓储模式（`src/database/repositories/`）进行数据访问
- 测试使用 TestContainers 进行集成测试
- 配置文件：`config/alembic.ini`

### 错误处理
- 使用项目定义的异常类（见 `src/core/exceptions.py`）
- API 错误返回统一的错误格式
- 敏感信息不得记录到日志中

### 绝对禁止的行为
- ❌ 硬编码密钥、密码、令牌（必须使用 KeyManager）
- ❌ 直接运行 pytest（必须使用 Makefile 命令）
- ❌ 提交前不运行任何检查
- ❌ 在 API 层直接操作数据库
- ❌ 跳过测试覆盖率要求（除非是文档提交）
- ❌ 使用 black/flake8/isort（项目已完全迁移到 Ruff）
- ❌ 推送前不运行完整测试验证
- ❌ **在恢复分支进行大规模重构**（先恢复到稳定状态）
- ❌ **恢复期间跳过快速测试**（必须运行 make test-quick）

### 代码风格（基于 Cursor 规则）
- **修改优先**：优先修改已有文件，避免不必要的文件创建
- **模块化设计**：保持文件功能单一，避免过度复杂的模块
- **依赖注入**：使用 `src/core/di.py` 容器管理依赖
- **统一基础服务**：所有服务继承 `BaseService`（`src/services/base_unified.py`）

## 故障排除指南

### 常见问题解决

#### 1. 测试失败
```bash
# 运行特定测试并显示详细输出
pytest tests/unit/test_specific.py -v -s

# 只运行失败的测试
pytest --lf

# 在第一个失败时停止
pytest -x

# 调试模式（进入 pdb）
pytest --pdb
```

#### 2. 端口冲突
- PostgreSQL: 5432
- Redis: 6379
- FastAPI: 8000
- 检查占用：`lsof -i :5432`

#### 3. 依赖问题
```bash
# 重新安装依赖
make clean-env
make install

# 检查虚拟环境
source .venv/bin/activate
python --version
```

#### 4. 数据库连接失败
```bash
# 启动数据库服务
docker-compose up -d db

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs db
```

## 环境配置

### 环境变量管理
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量（必需）
# DATABASE_URL=postgresql+asyncpg://...
# REDIS_URL=redis://...
# SECRET_KEY=your-secret-key

# 检查环境变量
make check-env
```

### Docker 服务管理
```bash
# 启动所有服务
make up

# 仅启动数据库服务
docker-compose up -d db redis

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止服务
make down
```

### 服务端口说明
- PostgreSQL: 5432
- Redis: 6379
- FastAPI: 8000
- Nginx: 80/443
- MLflow: 5000

### 性能优化建议
- 测试运行缓慢？使用 `make test-quick` 或 `make coverage-fast`
- Ruff 同时处理格式化和检查，使用 `make fmt` 一键完成
- 本地开发使用 `make coverage-local`（16%阈值）
- CI 环境使用 `make coverage-ci`（30%阈值）
- 使用 `make context` 加载项目上下文到 AI 助手

### 调试技巧

#### 测试调试
```bash
# 运行特定测试并显示详细输出
pytest tests/unit/test_specific.py -v -s

# 只运行失败的测试
pytest --lf

# 在测试失败时停止
pytest -x

# 调试模式（进入 pdb）
pytest --pdb
```

#### 常见错误解决
- **端口被占用**：检查是否有其他服务运行，使用 `lsof -i :5432` 查看端口占用
- **权限问题**：确保 `.env` 文件权限正确，`chmod 600 .env`
- **依赖问题**：删除 `.venv` 重新创建，或使用 `make install` 重新安装
- **数据库连接失败**：检查 PostgreSQL 是否运行，`docker-compose ps db`

### 质量改进工作流

#### 使用 --no-verify 的原则
```bash
# 仅在以下情况使用：
git commit --no-verify -m "fix: 修复小问题"

# 正常情况应先运行检查：
make fmt && make lint && make test-quick
git commit -m "feat: 添加新功能"
```

#### 渐进式改进策略
1. **第1周**：覆盖率 16.5%→18%，减少 --no-verify 使用
2. **第2周**：覆盖率 18%→20%，极少使用 --no-verify
3. **第3周**：覆盖率 20%→25%，完全不用 --no-verify
4. **第4周**：覆盖率 25%→30%，养成良好习惯

### 快速健康检查
```bash
# 一键检查项目状态
make env-check                    # 环境健康
make test-quick                   # 快速测试
make lint                        # 代码质量
./scripts/quick-health-check.sh  # 5秒快速检查
./scripts/quality-check.sh       # 推荐的快速质量检查（5-10秒）
./scripts/ci-verify.sh          # 完整的CI验证（推送前必跑）
```

## MyPy 类型检查

### 配置说明
- 配置文件：`mypy.ini`
- 已忽略第三方库导入（见配置文件）
- 新代码必须包含完整的类型注解

### 运行类型检查
```bash
make mypy-check       # 仅运行 MyPy
make lint             # Ruff + MyPy
mypy src/api          # 检查特定模块
```

### 类型注解规范
- 公共函数必须有类型注解
- 使用 Python 3.11+ 联合类型：`int | str` 而非 `Union[int, str]`
- 复杂类型使用 `typing` 模块
- 必要时使用 `# type: ignore`

## 架构模式详解

### 已实现的设计模式（2025-01-12）
✅ **统一基础服务类**：`src/services/base_unified.py` - 所有服务继承的基类
✅ **仓储模式**：`src/database/repositories/` - 数据访问抽象层
✅ **领域驱动设计**：`src/domain/models/` - 业务领域模型和服务
✅ **依赖注入**：`src/core/di.py` - IoC容器实现
✅ **事件驱动架构**：`src/api/events.py` + `src/api/observers.py` - 系统事件和观察者
✅ **CQRS 模式**：`src/api/cqrs.py` - 命令查询责任分离
✅ **工厂模式**：`tests/factories/` - 测试数据生成
✅ **适配器模式**：`src/adapters/` - 外部系统集成
✅ **异步优先**：全栈使用 async/await

### 架构特点
- **高度模块化**：清晰的分层架构（API→Service→Domain→Database）
- **异步优先**：FastAPI + SQLAlchemy 2.0 + asyncpg
- **类型安全**：完整的 MyPy 配置和类型注解
- **测试友好**：工厂模式 + TestContainers + pytest标记
- **生产就绪**：完整的监控、日志和健康检查

### 技术栈详情
- **Python 3.11+**：使用现代Python特性
- **FastAPI 0.115.6**：现代异步Web框架
- **SQLAlchemy 2.0.36**：异步ORM，支持asyncpg驱动
- **Pydantic 2.10.4**：数据验证和序列化
- **PostgreSQL 15**：主数据库
- **Redis 7**：缓存和会话存储
- **Ruff**：代码格式化和检查（替代black/flake8/isort）
- **MyPy**：静态类型检查
- **pytest**：测试框架，支持标记和覆盖率

### CI/CD 质量门禁
- **覆盖率要求**：
  - CI环境：30%（目标）
  - 开发环境：22%（当前实际）
  - 最低门槛：18%
  - 当前实际：28.21%（持续提升中）
- **质量检查**：Ruff + MyPy + 测试覆盖率 + 安全扫描
- **验证脚本**：
  - `./scripts/ci-verify.sh` 提供完整的本地CI模拟
  - `./scripts/quality-check.sh` 快速质量检查（5-10秒）
  - `./scripts/quick-health-check.sh` 5秒快速健康检查
- **触发条件**：Push 到 main/develop/hotfix 分支、创建 PR、手动触发

### 关键配置文件
- `pyproject.toml`：Ruff配置和项目元数据
- `pytest.ini`：测试配置和标记定义
- `mypy.ini`：类型检查配置
- `coverage_local.ini`：本地覆盖率配置
- `coverage_ci.ini`：CI覆盖率配置
- `docker-compose.yml`：容器编排配置
- `.cursor/rules/`：Cursor AI 编码规范和最佳实践
- `TESTING_GUIDE.md`：测试选择和优化指南
- `config/`：配置文件目录（alembic.ini, monitoring/等）

### 重要文档文件
- `TESTING_GUIDE.md`：测试选择和优化指南
- `COVERAGE_IMPROVEMENT_FINAL_REPORT_UPDATED.md`：覆盖率提升历程
- `TEST_OPTIMIZATION_FINAL_SUMMARY.md`：测试优化总结

---

## 📝 快速参考摘要

### 核心命令
```bash
# 日常开发
make test-quick           # 快速测试（60秒）【恢复期间必用】
make test.unit           # 单元测试
make coverage-optimized  # 优化的快速测试
make fmt                 # 代码格式化
make lint                # 代码质量检查

# 模块特定测试
make coverage-targeted MODULE=src.utils.config_loader

# 完整验证
make prepush            # 提交前验证【恢复期间必须】
make coverage-local      # 本地覆盖率检查
./scripts/ci-verify.sh   # 完整CI验证【推送前必跑】
./scripts/quality-check.sh  # 快速质量检查

# 测试环境管理
make test-env-start      # 启动测试环境
make test-env-status     # 查看环境状态

# 恢复期间额外命令
make test-local          # 运行本地测试（无外部依赖）
make test-core-modules    # 测试核心模块
```

### 关键架构组件
- **BaseService** (`src/services/base_unified.py`) - 所有服务的基类
- **DI Container** (`src/core/di.py`) - 依赖注入容器
- **Repository Pattern** (`src/database/repositories/`) - 数据访问层
- **Event System** (`src/api/events.py`) - 事件驱动架构
- **CQRS Pattern** (`src/api/cqrs.py`) - 命令查询分离

### 测试覆盖率现状
- **总体**: 28.21%（目标30%）
- **100%覆盖**: config_loader, dict_utils, retry
- **高覆盖**: i18n (87%), warning_filters (71%), formatters (64%)
- **需要提升**: validators (23%), file_utils (31%), crypto_utils (25%)

### 开发理念
- **渐进式改进**：先让CI通过，再逐步提升
- **快速反馈**：使用 `make test-quick` 获取即时反馈
- **质量优先**：代码质量评分8.5/10
