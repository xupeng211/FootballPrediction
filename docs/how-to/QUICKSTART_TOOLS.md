# 🚀 项目工具快速启动指南

**新的 AI 助手？** 这里是您需要知道的一切！

## ⚡ 立即可用的命令

```bash
make help                 # 🎯 显示所有命令
make context             # 🤖 加载项目上下文 (AI开发必备)
make sync-issues         # 🔄 GitHub Issues 同步
source github_sync_config.sh  # 🔑 加载环境变量
```

## 🤖 AI 开发 - 首要功能

```bash
# 1. 加载项目上下文（AI开发第一步）
make context

# 2. 查看上下文信息
cat logs/project_context.json
```

## 📋 Issues 同步 - 常用功能

```bash
# 1. 设置环境（一次性）
source github_sync_config.sh

# 2. 同步 Issues
make sync-issues
```

## 📚 完整文档位置

- **[TOOLS.md](./TOOLS.md)** - 完整工具文档
- **[scripts/README_sync_issues.md](./scripts/README_sync_issues.md)** - Issues 同步详细说明
- **[github_sync_config.sh](./github_sync_config.sh)** - 环境配置脚本

## 🎯 关键文件

- `issues.yaml` - 本地 Issues 文件
- `Makefile` - 所有命令入口
- `scripts/sync_issues.py` - Issues 同步脚本

**问题？** 运行 `make help` 或查看 [TOOLS.md](./TOOLS.md)

## 🔗 相关文档链接

### 📚 快速开始指南
- **[完整系统演示](COMPLETE_DEMO.md)** - 系统功能完整演示
- **[部署指南](DEPLOYMENT.md)** - 系统部署配置指南
- **[故障排除指南](TROUBLESHOOTING_GUIDE.md)** - 常见问题解决方案
- **[迁移指南](MIGRATION_GUIDE.md)** - 版本迁移和升级指导

### 🛠️ 开发工具和规范
- **[开发指南](../reference/DEVELOPMENT_GUIDE.md)** - 完整的开发环境搭建和编码规范
- **[Makefile工具指南](MAKEFILE_GUIDE.md)** - 120+开发命令详解
- **[CLAUDE.md](../../CLAUDE.md)** - AI辅助开发指导和工作流程
- **[系统架构文档](../architecture/ARCHITECTURE.md)** - 完整的系统架构设计

### 🚀 部署和环境
- **[Staging环境配置](STAGING_ENVIRONMENT.md)** - 测试环境配置和管理
- **[生产部署指南](../ops/PRODUCTION_READINESS_PLAN.md)** - 生产环境部署和运维
- **[运维手册](../ops/runbooks/README.md)** - 运维操作指南和故障排除

### 🧪 测试和质量
- **[测试策略文档](../testing/TEST_IMPROVEMENT_GUIDE.md)** - 完整的测试策略和质量保证体系
- **[API文档](../reference/API_REFERENCE.md)** - REST API接口规范
- **[术语表](../reference/glossary.md)** - 项目专业术语和概念定义

### 📊 项目资源
- **[项目索引](../INDEX.md)** - 完整的文档导航和入口
- **[数据库架构](../reference/DATABASE_SCHEMA.md)** - 数据库设计和表结构详情
- **[监控系统](../ops/MONITORING.md)** - 监控系统配置和告警设置

### 📋 管理和协作
- **[项目贡献指南](../project/CONTRIBUTING.md)** - 贡献流程和规范
- **[变更日志](../project/CHANGELOG.md)** - 项目版本变更记录
- **[项目管理](../project/README.md)** - 项目管理相关信息

---

**文档维护**: 本快速启动指南与项目工具同步更新，帮助新用户快速上手项目开发。
