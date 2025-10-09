# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📖 重要提示

**请先阅读 [.claude-preferences.md](/.claude-preferences.md)**
- 该文件记录了用户的核心偏好和已选择的最佳实践
- 包含用户的开发哲学和当前项目状态
- 了解用户的渐进式改进理念

**核心理念**：先让 CI 绿灯亮起，再逐步提高标准！

**当前项目状态**：
- 测试覆盖率：16.51%（技术债务改进阶段）
- CI 覆盖率门槛：20%（将逐步提升至 25%→30%）
- MyPy 类型注解错误：正在进行修复（最近已修复第1批）
- 采用渐进式改进策略，确保持续集成保持绿灯

## 🌏 语言设置

**重要规则：在与用户交流时，请使用简体中文回复。** 用户不懂英文，所以所有解释和说明都应该用中文。

- 与用户的所有对话都使用简体中文
- 代码注释可以使用英文，但解释要用中文
- 错误信息和技术术语的解释也要用中文

## 项目简介

这是一个足球预测系统，使用 FastAPI、SQLAlchemy、Redis 和 PostgreSQL 构建。项目采用现代 Python 架构，具有完整的测试、CI/CD 和 MLOps 功能。

## 开发命令

### 环境设置
```bash
make install          # 从锁文件安装依赖
make env-check        # 检查开发环境是否健康
make context          # 加载项目上下文供 AI 开发使用
make dev-setup        # 一键设置开发环境
make clean            # 清理缓存和虚拟环境
```

### 测试
```bash
make test             # 运行所有单元测试
make test-quick       # 快速单元测试（带超时限制）
make test-unit        # 只运行单元测试（标记为 'unit' 的）
make test-phase1      # 运行第一阶段核心 API 测试
make test-api         # 运行所有 API 测试
make test.containers  # 运行需要 Docker 容器的测试
make coverage         # 运行测试并检查覆盖率（默认80%）
make coverage-fast    # 快速覆盖率检查（仅单元测试）
make coverage-local   # 本地覆盖率检查（16%阈值）
```

### 代码质量
```bash
make lint             # 运行 ruff 和 mypy 检查
make fmt              # 使用 ruff 格式化代码（已替换 black 和 isort）
make quality          # 完整质量检查（lint + format + test）
make prepush          # 完整的提交前验证（ruff + mypy + pytest）
make ci               # 模拟 GitHub Actions CI 流程
```

### 本地 CI 验证
```bash
./ci-verify.sh        # 在本地运行完整的 CI 验证
make test-phase1      # 运行第一阶段核心 API 测试
./scripts/quality-check.sh  # 推荐的快速质量检查
```

## 架构说明

### 核心结构
- **`src/api/`** - FastAPI 端点和模式
- **`src/database/`** - SQLAlchemy 模型、迁移和连接管理
- **`src/services/`** - 业务逻辑层
- **`src/models/`** - 机器学习模型和预测服务
- **`src/cache/`** - Redis 缓存层
- **`src/monitoring/`** - 系统监控和指标
- **`src/utils/`** - 通用工具
- **`src/streaming/`** - 实时数据流处理（Kafka）
- **`src/scheduler/`** - 任务调度系统
- **`src/collectors/`** - 数据收集器
- **`src/core/`** - 核心组件（异常处理、日志等）
- **`src/lineage/`** - 数据血缘管理

### 关键模式
- 使用支持异步的 SQLAlchemy（asyncpg 驱动）
- 数据访问使用仓库模式
- 通过 FastAPI 的依赖系统进行依赖注入
- 测试数据使用工厂模式（见 `tests/factories/`）
- 全面使用 Pydantic 模型进行数据验证
- 服务层继承 `EnhancedBaseService`（统一服务基类）
- 使用项目内置的 `KeyManager` 系统管理密钥（禁止硬编码）
- 使用结构化日志记录（JSON 格式）
- 支持 TestContainers 进行集成测试

## 测试指南

### 测试组织
- 单元测试：`tests/unit/` - 测试单个函数/类（标记为 'unit'）
- 集成测试：`tests/integration/` - 测试模块交互（标记为 'integration'）
- 端到端测试：`tests/e2e/` - 完整工作流测试
- 测试夹具：`tests/factories/` - 使用工厂模式生成测试数据
- 共享夹具：`tests/conftest.py` - pytest 配置
- 测试标记：使用 pytest.mark 区分不同类型的测试

### 测试执行
- 始终使用 Makefile 命令进行测试（不要直接运行 pytest）
- 开发时使用 `make test-quick` 获得快速反馈（带超时和失败限制）
- 使用 `make coverage-fast` 生成不包含慢测试的覆盖率报告
- 覆盖率要求：CI环境 >=20%，本地开发 >=16%（使用 coverage-local）
- 运行单个测试：`pytest tests/unit/test_specific.py::test_function`
- 当前项目处于技术债务改进阶段，采用渐进式提升策略（16%→20%→25%→30%）

### 测试容器
- 对需要真实服务的集成测试使用 TestContainers
- 运行 `make test.containers` 进行基于 Docker 的测试

## 开发工作流程

### 日常开发流程
1. **开始开发前**
   ```bash
   make dev-setup      # 一键设置开发环境
   make context        # 加载项目上下文
   ```

2. **开发过程中**
   ```bash
   # 编码阶段
   # 定期运行快速测试
   make test-quick     # 每10-15分钟运行一次

   # 功能完成后
   make test-unit      # 运行单元测试
   make coverage-local # 检查本地覆盖率
   ```

3. **提交前检查**
   ```bash
   make fmt            # 格式化代码
   make lint           # 代码质量检查
   make prepush        # 完整的预推送验证
   ```

4. **推送前验证**
   ```bash
   ./ci-verify.sh      # 完整的CI验证（推荐）
   # 或
   make ci             # 模拟CI流程
   ```

### 分支管理策略
- **main**: 生产环境代码，只接受 merge request
- **develop**: 开发主分支，功能集成分支
- **feature/***: 功能开发分支
- **hotfix/***: 紧急修复分支

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
   - 代码覆盖率 >= 20%（技术债务阶段，将逐步提升）
   - 所有检查必须通过
   - 安全扫描无高危漏洞

### MLOps 工作流
1. **模型训练流程**
   - 数据收集 → 特征工程 → 模型训练 → 模型评估
   - 自动触发：每日8:00 UTC
   - 手动触发：`make mlops-pipeline`

2. **模型部署流程**
   - 模型验证 → 创建 PR → 人工审核 → 合并部署
   - 需要两人审核才能部署到生产环境

3. **反馈循环**
   - 收集预测结果 → 更新模型性能 → 触发重训练
   - 使用 `make feedback-update` 更新结果

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

## 重要说明

### 技术栈
- **Python**: 3.11+
- **FastAPI**: 0.115.6
- **SQLAlchemy**: 2.0.36（异步支持）
- **Pydantic**: 2.10.4
- **PostgreSQL**: 15
- **Redis**: 7
- **Celery**: 5.4.0（异步任务）

### 依赖管理
- 项目使用 pip-tools 进行依赖管理（requirements/ 目录）
- **requirements/base.txt** - 基础依赖
- **requirements/dev.lock** - 开发依赖锁定
- **requirements/requirements.lock** - 完整依赖锁定

### 代码质量工具
- 代码格式化和检查已迁移到 ruff（替代 flake8、black、isort）
- 所有 Python 代码必须通过 ruff 和 mypy 检查
- 测试使用 pytest 并生成覆盖率报告
- Docker Compose 提供本地开发的 PostgreSQL、Redis 和 Nginx
- MLOps 流程包括模型重训练和反馈循环

## 项目特定规则

### 代码风格
- 优先修改已有文件，避免不必要的文件创建
- 函数和类使用清晰的中文 docstring
- 遵循仓库模式进行数据访问

### 数据库相关
- 使用异步 SQLAlchemy 操作
- 所有数据库操作必须在 service 层，不要在 API 层直接操作
- 使用 Alembic 进行数据库迁移

### 错误处理
- 使用项目定义的异常类（见 `src/core/exceptions.py`）
- API 错误返回统一的错误格式
- 敏感信息不得记录到日志中

### 绝对禁止的行为
- ❌ 硬编码密钥、密码、令牌（必须使用 KeyManager）
- ❌ 直接运行 pytest（必须使用 Makefile 命令）
- ❌ 提交前不运行任何检查
- ❌ 在 API 层直接操作数据库

## 调试和故障排除

### 调试测试
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

### 常见端口冲突
- PostgreSQL: 5432
- Redis: 6379
- FastAPI: 8000
- 如果端口被占用，检查是否有其他服务在运行

### 查看日志
```bash
# 开发环境日志
tail -f logs/app.log

# Docker 容器日志
docker-compose logs -f app
```

## 环境配置和Docker

### 环境变量管理
- 开发环境：`.env.dev`（默认）
- 测试环境：`.env.test`
- 生产环境：`.env.prod`
- 环境变量模板：`.env.example`

### Docker 服务
```bash
# 启动所有服务
make up                # 启动所有服务
docker-compose up -d   # 直接使用 docker-compose

# 仅启动数据库服务
docker-compose up -d db redis

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止服务
make down              # 停止所有服务
```

### 常见端口
- PostgreSQL: 5432
- Redis: 6379
- FastAPI: 8000
- Nginx: 80/443
- MLflow: 5000

### Docker 服务说明
- **app**: 主应用服务（健康检查：/health）
- **db**: PostgreSQL 15 数据库（健康检查：pg_isready）
- **redis**: Redis 7 缓存服务
- **mlflow**: ML 模型管理（可选）
- **nginx**: 反向代理（生产环境）
- **celery**: 异步任务处理（可选）

## 故障排除

### 常见问题

- 如果测试运行缓慢，使用 `make test-quick` 或 `make coverage-fast`
- 对于数据库相关的测试失败，确保 Docker 服务正在运行：`docker-compose up -d`
- 如果导入失败，确保虚拟环境已激活：`source .venv/bin/activate`
- ruff 同时处理代码检查和格式化，使用 `make fmt` 会自动运行 `ruff format` 和 `ruff check --fix`
- 本地开发建议使用 `make coverage-local`（16%阈值）而不是 `make coverage`（20%阈值）

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
make env-check        # 环境健康
make test-quick       # 快速测试
make lint             # 代码质量
./scripts/quick-health-check.sh  # 5秒快速检查
./scripts/quality-check.sh       # 推荐的快速质量检查
```

## MyPy 类型检查

### 当前状态
- 正在进行 MyPy 类型注解错误修复
- 已完成第1批错误修复（提交 7520a03）
- 所有新代码必须包含完整的类型注解

### 运行 MyPy
```bash
mypy src/             # 检查所有源代码
mypy src/api/         # 检查特定模块
make lint             # 包含 MyPy 检查
```

### 类型注解要求
- 所有公共函数必须有类型注解
- 使用 Python 3.11+ 的新类型特性（如 `|` 联合类型）
- 复杂类型使用 `typing` 模块
- 避免 `Any` 类型，必要时添加 `# type: ignore` 注释
