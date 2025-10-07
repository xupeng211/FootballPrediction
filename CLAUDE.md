# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

1. 使用 `make dev-setup` 快速设置环境
2. 开发前用 `make context` 加载上下文
3. 开发过程中使用 `make test-quick` 获得快速反馈
4. 提交前运行 `make prepush`
5. 推送前执行 `./ci-verify.sh` 确保 CI 通过

## 重要说明

- 项目使用 pip-tools 进行依赖管理（requirements/ 目录）
- 代码格式化和检查已迁移到 ruff（替代 flake8、black、isort）
- 所有 Python 代码必须通过 ruff 和 mypy 检查
- 测试使用 pytest 并生成覆盖率报告
- Docker Compose 提供本地开发的 PostgreSQL、Redis 和 Nginx
- MLOps 流程包括模型重训练和反馈循环

## 常见问题

- 如果测试运行缓慢，使用 `make test-quick` 或 `make coverage-fast`
- 对于数据库相关的测试失败，确保 Docker 服务正在运行：`docker-compose up -d`
- 如果导入失败，确保虚拟环境已激活：`source .venv/bin/activate`
- ruff 同时处理代码检查和格式化，使用 `make fmt` 会自动运行 `ruff format` 和 `ruff check --fix`
- 本地开发建议使用 `make coverage-local`（60%阈值）而不是 `make coverage`（80%阈值）
