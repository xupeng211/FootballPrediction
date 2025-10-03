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
