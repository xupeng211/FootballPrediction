# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📖 重要提示

**请先阅读 [.claude-preferences.md](/.claude-preferences.md)**
- 该文件记录了用户的核心偏好和已选择的最佳实践
- 包含用户的开发哲学和当前项目状态
- 了解用户的渐进式改进理念

**核心理念**：先让 CI 绿灯亮起，再逐步提高标准！

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
make coverage-local   # 本地覆盖率检查（要求60%）
```

### 代码质量
```bash
make lint             # 运行 ruff 和 mypy 检查
make fmt              # 使用 ruff 格式化代码（已替换 black 和 isort）
make prepush          # 完整的提交前验证（ruff + mypy + pytest）
make ci               # 模拟 GitHub Actions CI 流程
```

### 本地 CI 验证
```bash
./ci-verify.sh        # 在本地运行完整的 CI 验证
make test-phase1      # 运行第一阶段核心 API 测试
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

### 关键模式
- 使用支持异步的 SQLAlchemy
- 数据访问使用仓库模式
- 通过 FastAPI 的依赖系统进行依赖注入
- 测试数据使用工厂模式（见 `tests/factories/`）
- 全面使用 Pydantic 模型进行数据验证

## 测试指南

### 测试组织
- 单元测试：`tests/unit/` - 测试单个函数/类
- 集成测试：`tests/integration/` - 测试模块交互
- 测试夹具：`tests/factories/` - 使用工厂模式生成测试数据
- 共享夹具：`tests/conftest.py` - pytest 配置

### 测试执行
- 始终使用 Makefile 命令进行测试（不要直接运行 pytest）
- 开发时使用 `make test-quick` 获得快速反馈（带超时和失败限制）
- 使用 `make coverage-fast` 生成不包含慢测试的覆盖率报告
- 覆盖率要求：CI 环境 >=80%，本地开发 >=60%（使用 coverage-local）
- 运行单个测试：`pytest tests/unit/test_specific.py::test_function`

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
   - 代码覆盖率 >= 80%
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

- 项目使用 pip-tools 进行依赖管理（requirements/ 目录）
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

## 常见问题

- 如果测试运行缓慢，使用 `make test-quick` 或 `make coverage-fast`
- 对于数据库相关的测试失败，确保 Docker 服务正在运行：`docker-compose up -d`
- 如果导入失败，确保虚拟环境已激活：`source .venv/bin/activate`
- ruff 同时处理代码检查和格式化，使用 `make fmt` 会自动运行 `ruff format` 和 `ruff check --fix`
- 本地开发建议使用 `make coverage-local`（60%阈值）而不是 `make coverage`（80%阈值）
