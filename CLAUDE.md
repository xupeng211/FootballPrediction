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
make prepush      # 提交前检查
```

## 📋 核心命令

### 必须知道的命令
| 命令 | 说明 | 何时使用 |
|------|------|----------|
| `make help` | 查看所有命令 | 不确定时 |
| `make context` | 加载项目上下文 | 开始工作前 |
| `make test` | 运行测试 | 开发完成后 |
| `make ci` | 完整CI检查 | 推送前 |
| `./ci-verify.sh` | Docker CI验证 | 发布前 |

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
├── api/           # API端点
├── config/        # 配置管理
├── database/      # 数据库相关
├── utils/         # 工具函数
├── middleware/    # 中间件
└── monitoring/    # 监控组件

tests/ (290+ 测试文件，96.35%覆盖率)
├── unit/          # 单元测试 ⭐主要使用
├── integration/   # 集成测试（待重建）
└── e2e/          # 端到端测试
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

### 核心工作流
1. **CI Pipeline** - 代码质量检查（自动触发）
2. **Deploy** - 自动部署到staging
3. **MLOps** - 模型自动管理（每日8:00）
4. **Issue Tracker** - 问题自动跟踪
5. **Project Sync** - 看板状态同步
6. **Project Maintenance** - 项目维护（每周一）

### 必须遵守的规则
```bash
# 提交前必须运行
make prepush
# 或
./ci-verify.sh
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

### Bug修复
1. 查看Issue Tracker的Issue
2. 理解失败原因
3. 修复代码
4. 添加测试
5. 推送修复（CI自动运行）

## ⚠️ 注意事项

### 测试相关
- CI要求80%覆盖率，本地开发20-60%即可
- 集成测试大多已删除，主要使用单元测试
- 使用 `pytest tests/unit/` 只运行单元测试

### 环境问题
- Docker服务需要先启动：`docker-compose up -d`
- 数据库连接问题检查 `make env-check`
- 使用 `./ci-verify.sh` 进行完整验证

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