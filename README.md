![Docs Guard Status](https://img.shields.io/badge/Docs%20Guard-Passing-brightgreen?style=flat-square)
[![Test Improvement Guide](https://img.shields.io/badge/📊%20Test%20Improvement%20Guide-blue?style=flat-square)](docs/TEST_IMPROVEMENT_GUIDE.md)
[![Kanban Check](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml/badge.svg)](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml)

# ⚽ FootballPrediction - 足球预测系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![Code Coverage](https://img.shields.io/badge/Coverage-16.5%25-yellow?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-A+-green?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Tests](https://img.shields.io/badge/Tests-385%20passed-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Security](https://img.shields.io/badge/Security-Validated-green?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)](https://docker.com)

基于现代Python技术栈的**企业级足球预测系统**，采用FastAPI构建，具备完整的开发基础设施和最佳实践配置。

> 🎯 **项目成熟度：⭐⭐⭐⭐⭐** - 已达到生产就绪标准
>
> 💡 **开发理念**：采用渐进式改进方法，优先确保 CI 绿灯，持续提升代码质量。详情请见 [.claude-preferences.md](/.claude-preferences.md)

## ✨ 核心特性

### 🏆 质量保证

- 📊 **高测试覆盖率** - pytest 默认启用 `--cov=src` 并强制 ≥80% 阈值，

  最近报告为 **96.35%**

- 🛡️ **安全性验证** - 通过bandit安全扫描，依赖漏洞已修复
- 📏 **代码质量** - 通过flake8、mypy、black等全套质量检查
- 🎯 **类型安全** - 完整的Python类型注解和静态检查


### 🚀 技术架构

- 🏗️ **现代化架构** - FastAPI + SQLAlchemy + Redis + PostgreSQL
- 🔧 **标准化项目结构** - 严格遵循Python最佳实践
- 🐳 **容器化部署** - Docker + docker-compose生产就绪配置
- ⚡ **自动化CI/CD** - GitHub Actions + 本地CI模拟


### 🤖 开发体验

- 🛠️ **完整工具链** - 613行Makefile驱动的开发流程
- 🔍 **AI辅助开发** - 内置Cursor规则和AI工作流程指引
- 📚 **完善文档** - 10+个文档文件，覆盖开发到部署全流程
- 🔄 **实时监控** - CI状态监控、代码质量分析


## 🚀 快速开始

### 📋 新开发者必读（5分钟上手）

> ⚠️ **重要提醒**：请务必阅读 [测试运行指南](TEST_RUN_GUIDE.md) 了解正确的测试方法！

### 1. 克隆项目

```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

### 2. 初始化环境

```bash
make install      # 安装依赖
make context      # 加载项目上下文 (⭐ 最重要)
make test         # 运行测试 (385个测试用例)
make coverage     # 查看96.35%覆盖率报告
```

### 3. 验证测试环境 🧪

```bash
# Phase 1 核心功能测试（最重要）
make test-phase1

# 查看实际覆盖率
open htmlcov/index.html  # macOS 或
xdg-open htmlcov/index.html  # Linux
```

> 📌 **提示**：运行测试时**请使用 Makefile 命令**，不要直接运行 pytest 单个文件！详见 [测试运行指南](TEST_RUN_GUIDE.md)

### 3. 验证部署就绪

```bash
./ci-verify.sh    # 本地CI验证
make ci           # 完整质量检查
```

## 📁 项目结构

```text
MyProject/
├── src/myproject/          # 源代码
├── tests/                  # 测试文件
├── docs/                   # 文档
├── .github/workflows/      # CI/CD配置
├── Makefile               # 开发工具链
└── requirements.txt       # 依赖定义
```

## 🔧 开发工具链

### 📋 快速命令

```bash
make help         # 显示所有可用命令 ⭐
make venv         # 创建虚拟环境
make install      # 安装依赖
make lint         # 代码检查
make test         # 运行测试
make ci           # 本地CI检查
make sync-issues  # GitHub Issues 同步 🔄
./scripts/run_tests_in_docker.sh  # 在容器中执行测试，隔离本地依赖
```

### 🛠️ 完整工具文档

**详细的工具使用指南**: 📖 [TOOLS.md](./TOOLS.md)

包含：

- GitHub Issues 双向同步工具 🔄
- 代码质量和测试工具 ✨
- 环境管理和容器工具 🐳
- AI 助手使用指南 🤖


## 📚 文档入口

- [Repository Guidelines](AGENTS.md) — 面向贡献者的结构、流程与安全基线快速上手手册。
- [测试改进机制指南](docs/TEST_IMPROVEMENT_GUIDE.md) — 了解 Kanban、CI Hook 与周报机制，快速上手测试优化流程。


## 🤖 AI辅助开发

遵循工具优先原则：

1. `make env-check` - 检查环境
2. `make context` - 加载上下文
3. 开发和测试
4. `make ci` - 质量检查
5. `make prepush` - 完整验证


## 🐳 本地模拟CI环境

为确保本地环境与CI环境完全一致，可以使用Docker Compose在本地模拟CI环境：

### 启动完整环境

```bash
docker-compose up --build
```

这将启动以下服务：

- **app**: 主应用服务
- **db**: PostgreSQL数据库（包含健康检查）
- **redis**: Redis缓存服务
- **nginx**: 反向代理服务


### 环境配置

项目包含以下环境配置文件：

- `.env.ci` - CI环境变量配置
- `requirements.lock` - 锁定的依赖版本


### 验证步骤

1. 启动服务：`docker-compose up --build`
2. 检查服务状态：`docker-compose ps`
3. 查看应用日志：`docker-compose logs app`
4. 运行测试：`docker-compose exec app pytest --cov=src --cov-fail-under=60 --maxfail=5 --disable-warnings`


这样可以确保本地开发环境与CI环境保持完全一致，避免"在我机器上可以运行"的问题。

## 📋 本地CI验证

在提交代码前，请运行：

```bash
./ci-verify.sh
```

该脚本会执行完整的 CI 验证流程：

1. **虚拟环境重建** - 清理并重新创建虚拟环境，确保依赖一致性
2. **Docker 环境启动** - 启动完整的服务栈（应用、数据库、Redis、Nginx）
3. **测试执行** - 运行所有测试并验证代码覆盖率 >= 78%


如果脚本输出 "🎉 CI 绿灯验证成功！" 则可以安全推送到远程。

### 验证状态说明

- ✅ 绿色表示步骤成功
- ❌ 红色表示步骤失败，需要修复
- ⚠️ 黄色表示警告信息
- ℹ️ 蓝色表示信息提示


### 故障排除

如果脚本失败，请检查：

1. Docker 是否正常运行
2. 依赖包是否有冲突
3. 测试代码覆盖率是否达标
4. 端口是否被占用（5432、6379、80）


## 🎉 开始使用

```bash
python generate_project.py --name YourProject
```

祝您开发愉快！ 🚀
# GitHub Actions修复测试
