# Makefile 使用指南

## 📋 概述

项目现在有两个 Makefile：

- **`Makefile`** (主文件) - 包含核心的30个常用命令
- **`Makefile.full`** - 包含所有86个命令（完整版）

## 🚀 快速开始

### 日常开发
```bash
# 首次使用
make install      # 安装依赖
make env-check    # 检查环境
make up           # 启动Docker服务

# 日常开发
make dev          # 启动开发服务器
make test-quick   # 快速测试
make fmt          # 格式化代码
make lint         # 代码检查

# 提交前
make prepush      # 完整检查（格式化+检查+测试）
```

### 快捷命令
```bash
make quickstart   # 一键启动开发环境
make health       # 项目健康检查
make test-all     # 完整测试流程
make clean        # 清理项目
```

## 📊 对比

| 项目 | Makefile.core | Makefile.full |
|------|---------------|---------------|
| 命令数 | 30 | 86 |
| 行数 | ~200 | 794 |
| 适用场景 | 日常开发 | 特殊需求 |

## 🔧 使用完整版

需要使用完整版时：
```bash
# 查看所有命令
make -f Makefile.full help

# 使用特定命令
make -f Makefile.full mutation-test
make -f Makefile.full performance-report
```

## 📝 命令分类

### 环境管理 (3个)
- `install` - 安装依赖
- `env-check` - 环境检查
- `venv` - 创建虚拟环境

### 开发日常 (6个)
- `dev` - 启动开发服务器
- `test` - 运行测试
- `test-quick` - 快速测试
- `lint` - 代码检查
- `fmt` - 代码格式化
- `clean` - 清理项目

### 质量保证 (4个)
- `coverage` - 生成覆盖率报告
- `prepush` - 提交前检查
- `ci` - 完整CI检查
- `health` - 项目健康检查

### Docker (3个)
- `up` - 启动服务
- `down` - 停止服务
- `docker-build` - 构建镜像

### 数据库 (2个)
- `db-init` - 初始化数据库
- `db-migrate` - 运行迁移

### 其他 (2个)
- `docs` - 生成文档
- `help` - 显示帮助

## 💡 最佳实践

1. **日常开发**使用核心命令
2. **特殊需求**才使用完整版
3. **提交前**必须运行 `make prepush`
4. **定期清理**运行 `make clean`

## 🔄 迁移建议

如果你习惯使用某些完整版命令：
```bash
# 创建个人别名（在 ~/.bashrc 或 ~/.zshrc）
alias makefull='make -f Makefile.full'

# 或者创建符号链接
ln -s Makefile.full Makefile.advanced
```

## ❓ 常见问题

**Q: 某个命令找不到了？**
A: 使用 `make -f Makefile.full <command>`

**Q: 如何查看所有可用命令？**
A: 运行 `make help` 或 `make -f Makefile.full help`

**Q: 可以添加新命令吗？**
A: 建议先添加到 Makefile.full，确认常用后再移到 Makefile.core