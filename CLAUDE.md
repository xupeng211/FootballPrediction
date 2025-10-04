# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📑 目录
- [语言设置](#语言设置)
- [快速开始](#快速开始)
- [核心命令](#核心命令)
- [开发原则](#开发原则)
- [工作流系统](#工作流系统)
- [项目架构](#项目架构)
- [重要文档](#重要文档)
- [故障排除](#故障排除)

## 🌏 语言设置

**请始终使用中文回复！**

- 语言偏好: 中文 (简体)
- 回复语言: 中文
- 注释语言: 中文
- 文档语言: 中文

## 🚀 快速开始

### 首次使用
```bash
make install      # 安装依赖
make context      # 加载项目上下文 ⭐最重要
make test         # 验证环境
```

### 日常开发
```bash
make env-check    # 检查环境
make test-quick   # 快速测试
make fmt && make lint  # 代码格式化和检查
make prepush      # 提交前检查
```

## 📋 核心命令

### 必须知道的命令
| 命令 | 说明 | 何时使用 |
|------|------|----------|
| `make help` | 查看所有命令 | 不确定时 |
| `make context` | 加载项目上下文 | 开始工作前 |
| `make install` | 安装依赖 | 首次使用 |
| `make test-quick` | 快速测试（不包含coverage） | 开发中 |
| `make test.unit` | 只运行单元测试 | 主要测试方式 |
| `make coverage` | 运行覆盖率测试（80%阈值） | CI要求 |
| `make ci` | 完整CI检查 | 推送前 |
| `./ci-verify.sh` | Docker CI验证 | 发布前 |
| `make prepush` | 提交前检查 | 必须运行 |

### 快速参考
- 完整命令列表：[CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- 故障排除：[CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)

## 🤖 AI开发原则

### 核心原则
1. **文档优先**：修改代码前先更新文档
2. **使用Makefile**：保持命令一致性
3. **测试驱动**：确保测试覆盖率
4. **修改优于创建**：优先修改现有文件

### 文档自动化规则
根据 `docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md`：

- **API变更** → 更新 `docs/reference/API_REFERENCE.md`
- **数据库变更** → 更新 `docs/reference/DATABASE_SCHEMA.md`
- **完成阶段** → 生成完成报告
- **修复Bug** → 创建bugfix报告

## 🏗️ 项目架构

### 技术栈
- **框架**: FastAPI + SQLAlchemy 2.0
- **数据库**: PostgreSQL (生产) + SQLite (测试)
- **缓存**: Redis
- **任务队列**: Celery
- **MLOps**: MLflow + Feast
- **监控**: Prometheus/Grafana

### 项目结构
```
src/
├── api/           # API端点（health等）
├── config/        # 配置管理（fastapi_config等）
├── database/      # 数据库相关（models、connections）
├── utils/         # 工具函数（i18n等）
├── middleware/    # 中间件（i18n、auth等）
└── monitoring/    # 监控组件

tests/ (96.35%覆盖率)
├── unit/          # 单元测试 ⭐主要使用
│   ├── api/       # API单元测试
│   ├── database/  # 数据库测试
│   ├── services/  # 服务测试
│   └── utils/     # 工具测试
├── integration/   # 集成测试（待重建）
├── e2e/          # 端到端测试
└── legacy/       # 遗留测试（默认排除）

scripts/          # 辅助脚本
├── dependency/   # 依赖管理
├── testing/      # 测试工具
└── security/     # 安全工具
```

## 📚 重要文档

### 文档索引
- [文档首页](docs/INDEX.md) - 完整文档列表
- [AI开发规则](docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md) - 必读
- [测试指南](docs/testing/) - 测试策略
- [架构文档](docs/architecture/) - 系统设计
- [运维手册](docs/ops/) - 部署运维

### API和参考
- [API文档](docs/reference/API_REFERENCE.md)
- [数据库架构](docs/reference/DATABASE_SCHEMA.md)
- [开发指南](docs/reference/DEVELOPMENT_GUIDE.md)

## 🔄 工作流系统

### ⚠️ 重要：理解工作流
这个项目有6个自动化工作流，请务必阅读：
- **[Claude工作流指南](docs/ai/CLAUDE_WORKFLOW_GUIDE.md)** - 必读！
- **[工作流文档](.github/workflows/README.md)** - 完整说明

### 核心工作流（中文命名）
1. **CI流水线.yml** - 代码质量检查（push/PR触发）
2. **部署流水线.yml** - 自动部署到staging/production
3. **MLOps机器学习流水线.yml** - 模型自动管理（每日8:00）
4. **问题跟踪流水线.yml** - 问题自动跟踪（CI失败触发）
5. **项目同步流水线.yml** - 看板状态同步（PR关闭触发）
6. **项目维护流水线.yml** - 项目维护（每周一触发）

### 必须遵守的规则
```bash
# 提交前必须运行
make prepush
# 或
./ci-verify.sh
```

### Docker服务
```bash
# 启动所需服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

### CI失败处理
- Issue Tracker会自动创建Issue
- Issue包含详细错误信息
- 修复后自动关闭Issue

## 🔧 开发工作流

### 新功能开发
1. `make context` - 了解项目状态
2. 更新相关文档（重要！）
3. 编写代码
4. `make test-quick` - 测试
5. `make fmt && make lint` - 代码规范
6. `make coverage` - 覆盖率检查
7. `make prepush` - 提交前检查（触发CI）

### 运行单个测试
```bash
# 运行特定测试文件
pytest tests/unit/api/test_health.py -v

# 运行特定测试函数
pytest tests/unit/api/test_health.py::test_health_endpoint -v

# 运行带标记的测试
pytest -m "unit and not slow" --cov=src
```

### Bug修复
1. 查看Issue Tracker的Issue
2. 理解失败原因
3. 修复代码
4. 添加测试
5. 推送修复（CI自动运行）

## ⚠️ 重要注意事项

### 测试策略
- **主要使用单元测试**：`tests/unit/` 目录包含96.35%覆盖率的测试
- **测试标记系统**：
  - `unit` - 单元测试（主要）
  - `integration` - 集成测试（待重建）
  - `e2e` - 端到端测试
  - `slow` - 慢速测试
  - `legacy` - 遗留测试（默认排除）
- **覆盖率要求**：CI要求80%，本地开发20-60%即可

### 环境管理
- **虚拟环境**：使用 `.venv` 目录，通过 Makefile 管理
- **Docker服务**：需要先启动 `docker-compose up -d`
- **环境配置**：
  - 开发：`.env`
  - 生产：`.env.production`
  - 示例：`.env.example`

### 依赖管理
- **锁定文件**：`requirements/requirements.lock`
- **命令**：
  - `make lock-deps` - 锁定依赖
  - `make install-locked` - 安装锁定版本
  - `make verify-deps` - 验证依赖一致性

## 🆘 故障排除

### 快速诊断
```bash
# 环境问题
make env-check

# 查看所有命令
make help

# 测试失败
cat htmlcov/index.html  # 查看覆盖率报告

# CI问题
./ci-verify.sh  # 本地验证
```

### 常见问题
- **测试失败**：查看 [故障排除指南](CLAUDE_TROUBLESHOOTING.md)
- **命令不工作**：运行 `make help`
- **环境问题**：运行 `make env-check`
- **依赖问题**：检查 `requirements/requirements.lock`
- **Docker问题**：确保 `docker-compose up -d`

## 📞 支持

- 快速参考：[CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- 故障排除：[CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)
- 完整文档：[docs/](docs/)

---

# 重要指令提醒
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files unless explicitly requested.