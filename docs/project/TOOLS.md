# 🛠️ 项目开发工具

本项目提供了一套完整的开发工具，旨在提高开发效率和项目管理质量。

## 📋 工具总览

### 🔧 Makefile 命令

使用 `make help` 查看所有可用命令：

```bash
make help                    # 显示所有可用命令
```

### 🎯 核心开发工具

#### 1. **GitHub Issues 同步工具** 🔄

**位置**: `scripts/sync_issues.py`
**文档**: `scripts/README_sync_issues.md`

快速开始：

```bash
# 设置环境变量
source github_sync_config.sh

# 双向同步 Issues
make sync-issues
# 或
python scripts/sync_issues.py sync
```

**功能**：

- 📥 从 GitHub 拉取 Issues 到本地 `issues.yaml`
- 📤 推送本地 Issues 到 GitHub
- 🔄 双向同步，保持数据一致性
- 📝 支持批量管理和团队协作

**常用命令**：

```bash
python scripts/sync_issues.py pull   # 拉取
python scripts/sync_issues.py push   # 推送
python scripts/sync_issues.py sync   # 双向同步
```

#### 2. **代码质量工具** ✨

```bash
make lint        # 代码风格检查 (flake8 + mypy)
make fmt         # 代码格式化 (black + isort)
make check       # 完整质量检查
```

#### 3. **测试工具** 🧪

```bash
make test        # 运行单元测试
make coverage    # 覆盖率测试 (阈值: 80%)
make ci          # CI 模拟 (lint + test + coverage)
```

#### 4. **环境管理** 🌍

```bash
make venv        # 创建虚拟环境
make install     # 安装依赖
make clean       # 清理环境
```

#### 5. **容器管理** 🐳

```bash
make up          # 启动 docker-compose 服务
make down        # 停止服务
make logs        # 查看日志
```

#### 6. **AI 上下文加载** 🤖

```bash
make context     # 加载项目上下文 (为AI提供完整项目信息)
```

**功能**：

- 📁 扫描项目目录结构
- 🌿 获取 Git 信息和提交历史
- 📦 分析 Python 模块和依赖
- 🧪 统计测试文件
- 📊 生成项目统计信息
- 💾 保存到 `logs/project_context.json`

## 🚀 AI 助手使用指南

### 对于新的 AI 助手

1. **发现工具的方法**：

   ```bash
   make help                    # 查看所有命令
   ls scripts/                  # 查看脚本目录
   cat TOOLS.md                 # 阅读本文档
   ```

2. **Issues 同步的完整流程**：

   ```bash
   # 1. 加载环境变量
   source github_sync_config.sh

   # 2. 执行同步
   make sync-issues

   # 3. 查看结果
   cat issues.yaml
   ```

3. **AI 开发的完整流程**：

   ```bash
   # 1. 加载项目上下文
   make context

   # 2. 查看上下文文件
   cat logs/project_context.json

   # 3. 开始开发工作
   make venv && make install
   ```

3. **环境配置检查**：

   ```bash
   # 检查环境变量
   echo $GITHUB_TOKEN $GITHUB_REPO

   # 检查依赖
   pip list | grep -E "(PyGithub|pyyaml)"
   ```

## 📁 重要文件路径

```
project/
├── Makefile                          # 主命令入口
├── github_sync_config.sh             # GitHub 环境配置
├── issues.yaml                       # 本地 Issues 文件
├── scripts/
│   ├── sync_issues.py                # Issues 同步脚本
│   └── README_sync_issues.md         # 详细使用文档
└── TOOLS.md                          # 本文档
```

## 🎯 最佳实践

### Issues 管理工作流

1. **日常同步**: `make sync-issues`
2. **本地编辑**: 修改 `issues.yaml`
3. **推送更新**: `python scripts/sync_issues.py push`

### 开发工作流

1. **环境准备**: `make venv && make install`
2. **开发编码**: 遵循 `.cursor/rules/` 规范
3. **质量检查**: `make check`
4. **提交前验证**: `make ci`

## 🆘 故障排除

### Issues 同步问题

```bash
# 检查环境配置
source github_sync_config.sh

# 检查网络连接
python scripts/sync_issues.py --help

# 查看详细文档
cat scripts/README_sync_issues.md
```

### 开发环境问题

```bash
# 重建环境
make clean && make venv && make install

# 检查依赖
pip check
```

---

**更新时间**: 2024年9月
**维护者**: DevOps Engineer

💡 **提示**: 新加入项目的 AI 助手，建议首先阅读本文档了解可用工具！
