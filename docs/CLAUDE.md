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

## 🤖 AI工具指南

**重要：在使用项目工具前，请先阅读AI工具文档**

- 📖 [AI工具参考指南](docs/ai/TOOLS_REFERENCE_GUIDE.md) - 完整工具使用说明
- 🌳 [工具选择决策树](docs/ai/DECISION_TREE_FOR_TOOLS.md) - 问题解决流程
- 📄 [工具速查表](docs/ai/QUICK_TOOL_CHEAT_SHEET.md) - 一页纸快速参考

**必须记住的三个命令**：
1. `make context` - 了解项目状态（开始工作前必运行）
2. `make test-quick` - 快速验证功能
3. `make prepush` - 提交前完整检查

**环境问题解决顺序**：
1. 遇到导入错误 → `source scripts/setup_pythonpath.sh`
2. 仍有问题 → `python scripts/dependency_manager/verify_core_functionality.py`
3. 依赖冲突 → 使用 `venv_clean` 干净环境

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
make prepush      # 提交前检查
```

## 📋 核心命令

### 必须知道的命令
| 命令 | 说明 | 何时使用 |
|------|------|----------|
| `make help` | 查看所有命令 | 不确定时 |
| `make context` | 加载项目上下文 | 开始工作前 |
| `make test` | 运行测试 | 开发完成后 |
| `make test-quick` | 快速测试（仅单元测试） | 开发中 |
| `make test-unit` | 只运行单元测试 | 调试时 |
| `make test-integration` | 运行集成测试 | 验证集成 |
| `make test-e2e` | 运行端到端测试 | 完整验证 |
| `make ci` | 完整CI检查 | 推送前 |
| `make prepush` | 提交前检查 | 提交前 |
| `./ci-verify.sh` | Docker CI验证 | 发布前 |

### 代码质量命令
| 命令 | 说明 |
|------|------|
| `make fmt` | 代码格式化 (black, isort) |
| `make lint` | 代码检查 (flake8, ruff) |
| `make typecheck` | 类型检查 (mypy) |
| `make security` | 安全检查 (bandit) |
| `make coverage` | 生成覆盖率报告 |

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
- **缓存**: Redis + TTL缓存
- **任务队列**: Celery
- **消息流**: Kafka
- **MLOps**: MLflow + Feast
- **监控**: Prometheus/Grafana
- **数据质量**: Great Expectations

### 项目结构
```
src/
├── api/           # API端点（predictions, health, monitoring）
├── config/        # 配置管理（缓存、环境验证、热重载）
├── core/          # 核心组件（日志、异常处理）
├── database/      # 数据库相关（模型、迁移、连接）
│   └── models/    # SQLAlchemy模型（team, match, predictions等）
├── utils/         # 工具函数（字符串、时间、重试等）
├── middleware/    # 中间件（i18n、安全、性能、缓存）
├── cache/         # 缓存系统（Redis、TTL、一致性管理）
├── data/          # 数据层（收集、处理、质量、特征）
├── features/      # 特征工程（定义、计算、实体）
├── lineage/       # 数据血缘（元数据管理）
├── models/        # ML模型（训练、预测、指标导出）
├── monitoring/    # 监控组件（质量监控、异常检测）
├── scheduler/     # 任务调度（依赖解析、作业管理）
├── streaming/     # 流处理（Kafka、流处理器）
└── tasks/         # 异步任务（Celery、数据收集、维护）

tests/ (385+ 测试用例，96.35%覆盖率)
├── unit/          # 单元测试 ⭐主要使用
├── integration/   # 集成测试（API、数据库、缓存集成）
└── e2e/          # 端到端测试（完整流程验证）
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
这个项目有10个自动化工作流，请务必阅读：
- **[Claude工作流指南](docs/ai/CLAUDE_WORKFLOW_GUIDE.md)** - 必读！
- **[工作流文档](.github/workflows/README.md)** - 完整说明

### 核心工作流
1. **CI Pipeline** - 代码质量检查（自动触发）
2. **Deploy** - 自动部署到staging
3. **MLOps** - 模型自动管理（每日8:00）
4. **Issue Tracker** - 问题自动跟踪
5. **Project Sync** - 看板状态同步
6. **Project Maintenance** - 项目维护（每周一）
7. **Dependency Security** - 依赖漏洞扫描
8. **License Check** - 许可证合规检查
9. **Security Scan** - 代码安全扫描
10. **Production Readiness** - 生产就绪检查

### 必须遵守的规则
```bash
# 提交前必须运行
make prepush
# 或
./ci-verify.sh
```

### CI验证脚本说明
`ci-verify.sh` 执行完整验证流程：
1. **虚拟环境重建** - 清理并重建，确保依赖一致性
2. **Docker环境启动** - 完整服务栈（应用、PostgreSQL、Redis、Nginx）
3. **测试执行** - 验证覆盖率≥78%
4. **代码质量检查** - 格式化、lint、类型检查、安全扫描

### CI失败处理
- Issue Tracker会自动创建Issue
- Issue包含详细错误信息
- 修复后自动关闭Issue

## 🔧 开发工作流

### 新功能开发
1. `make context` - 了解项目状态
2. 更新相关文档（API_REFERENCE.md或DATABASE_SCHEMA.md）
3. 编写代码
4. `make test-quick` - 快速测试
5. `make fmt && make lint` - 代码规范
6. `make coverage` - 覆盖率检查
7. `make prepush` - 提交前检查（触发CI）

### Bug修复
1. 查看Issue Tracker自动创建的Issue
2. 理解失败原因（包含详细错误信息）
3. 修复代码
4. 添加测试用例
5. 推送修复（CI自动运行并关闭Issue）

## ⚠️ 注意事项

### 测试相关
- CI要求80%覆盖率，当前96.35%
- 主要使用单元测试（tests/unit/）
- 集成测试和端到端测试可用于完整验证
- 单个测试运行：`pytest tests/unit/test_file.py::test_function`
- 调试模式：`pytest -s -v tests/unit/test_file.py`

### 环境问题
- Docker服务启动：`docker-compose up -d`
- 数据库连接问题：`make env-check`
- 完整环境验证：`./ci-verify.sh`
- 查看Docker日志：`docker-compose logs app`

## 🆘 常见问题

**测试失败**？→ 查看 [故障排除指南](CLAUDE_TROUBLESHOOTING.md)

**命令不工作**？→ 运行 `make help`

**环境问题**？→ 运行 `make env-check`

**需要帮助**？→ 查看快速参考或文档索引

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

# 关键提醒
- 始终使用中文回复！
- 优先运行单元测试：`pytest tests/unit/`
- 提交前必须运行：`make prepush` 或 `./ci-verify.sh`
- 查看命令帮助：`make help`