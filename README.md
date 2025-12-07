[![CI Pipeline](https://github.com/xupeng211/FootballPrediction/actions/workflows/ci_pipeline_v2.yml/badge.svg)](https://github.com/xupeng211/FootballPrediction/actions/workflows/ci_pipeline_v2.yml)
![Docs Guard Status](https://img.shields.io/badge/Docs%20Guard-Passing-brightgreen?style=flat-square)
[![Test Improvement Guide](https://img.shields.io/badge/📊%20Test%20Improvement%20Guide-blue?style=flat-square)](docs/TEST_IMPROVEMENT_GUIDE.md)
[![Testing Guide](https://img.shields.io/badge/🛡️%20Testing%20Guide-green?style=flat-square)](docs/TESTING_GUIDE.md)
[![Kanban Check](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml/badge.svg)](https://github.com/xupeng211/FootballPrediction/actions/workflows/kanban-check.yml)
[![Security Audit](https://img.shields.io/badge/Security%20Audit-Passed-brightgreen?style=flat-square)](reports/security_audit.md)

> ✅ **Build Status: Stable (Green Baseline Established)** - CI/CD pipeline maintained with automated test recovery and flaky test isolation

# ⚽ FootballPrediction - 足球预测系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.0+-green?style=flat-square&logo=vue.js)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?style=flat-square&logo=typescript)](https://typescriptlang.org)
[![Code Coverage](https://img.shields.io/badge/Coverage-29.0%25-yellow?style=flat-square&logo=codecov)](https://github.com/xupeng211/FootballPrediction)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-A+-green?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Tests](https://img.shields.io/badge/Tests-385%20passed-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Security](https://img.shields.io/badge/Security-Enterprise%20Grade-green?style=flat-square)](reports/security_audit.md)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)](https://docker.com)
[![Version](https://img.shields.io/badge/Version-v4.0.1-hotfix-green?style=flat-square)](RELEASE_NOTES.md)
[![Lint Status](https://img.shields.io/badge/Lint-Passing-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)

基于现代技术栈的**企业级足球预测系统**，采用 Python FastAPI + Vue.js 3 全栈架构，具备完整的开发基础设施和最佳实践配置。

> 🎯 **项目成熟度：⭐⭐⭐⭐⭐** - 已达到生产就绪标准
>
> 💡 **开发理念**：采用渐进式改进方法，优先确保 CI 绿灯，持续提升代码质量。详情请见 [.claude-preferences.md](/.claude-preferences.md)

## ✨ 核心特性

### 🏆 质量保证

- 📊 **测试覆盖率29.0%** - 已建立企业级测试体系，支持utils和domain模块 (实际测量数据)

- 🔧 **测试环境修复完成** - 解决了270个语法错误，恢复了100+核心测试运行能力

- 🛡️ **安全性验证** - 通过bandit安全扫描，依赖漏洞已修复
- 📏 **代码质量** - 通过ruff、mypy等全套质量检查
- 🎯 **类型安全** - 完整的Python类型注解和静态检查

### 🌟 前端 MVP 完成 (P3)

- 🎨 **现代化前端架构** - Vue 3 + TypeScript + Vite + Pinia + Tailwind CSS
- 📱 **响应式设计** - 完美适配移动端、平板和桌面设备
- 🎯 **完整用户旅程** - 从注册认证到数据分析的全流程体验
- 📊 **数据可视化** - Chart.js 图表组件，直观展示预测分析
- 🔐 **用户中心** - 个人信息管理、历史记录、统计分析、账户设置
- 🚀 **高性能优化** - 代码分割、懒加载、状态管理优化


### 🚀 技术架构 (v2.5)

- 🏗️ **现代化架构** - FastAPI + SQLAlchemy + Redis + PostgreSQL
- 🔧 **标准化项目结构** - 严格遵循Python最佳实践
- 🐳 **容器化部署** - Docker + docker-compose生产就绪配置
- ⚡ **自动化CI/CD** - GitHub Actions + 本地CI模拟
- 🔄 **混合调度架构** - Prefect 2.x + Celery Beat 企业级工作流编排


### 🎯 P2 新增功能

#### 🤖 机器学习流水线 (v2.5)
- **📈 真实模型推理** - 生产级XGBoost模型，v3.0智能降级系统
- **🧠 自动模型训练** - P2-5完整训练流水线，超参数优化，MLflow跟踪
- **🔍 特征工程** - P0-2生产级Feature Store，14个核心特征，数据质量监控
- **⚡ 模型热更新** - 无停机推理服务更新，自动性能验证

#### 📊 自动化调度 (v2.5)
- **🔄 日常数据采集** - 并行FotMob和FBref数据采集，智能重试机制
- **🧠 每周模型重训** - 定时模型优化，质量门控，实验对比
- **🚨 紧急重训练** - 性能监控，自动触发，降级策略
- **📈 回测系统** - 历史数据验证，策略评估，风险管理

#### 🛡️ 生产级监控 (v2.5)
- **📊 Prefect UI** - 工作流编排和监控 (http://localhost:4200)
- **🌼 Flower UI** - Celery任务监控 (http://localhost:5555)
- **🧪 MLflow UI** - 实验跟踪和模型管理 (http://localhost:5000)
- **📈 实时质量监控** - 数据质量规则，性能指标，告警系统

### 🔒 系统稳定性与安全加固 (v4.0)

#### 📊 企业级监控与日志
- **📈 Prometheus + Grafana** - 生产级监控仪表板，实时性能指标收集
- **📋 结构化日志** - JSON格式日志，请求追踪ID，分布式日志聚合
- **🚨 智能告警** - 基于阈值的自动告警，多渠道通知支持
- **📊 健康检查** - 全面的系统健康端点，资源监控，依赖检查

#### 🛡️ 企业级安全防护
- **🔒 HTTP安全头** - CSP、HSTS、XSS防护、点击劫持防护完整实施
- **🔍 安全审计** - 自动化漏洞扫描，47项安全问题识别与修复
- **🔐 加密升级** - MD5算法全面升级至SHA256，SSL证书验证强化
- **🚨 敏感信息保护** - 838个文件扫描，防止硬编码凭证泄露

#### ⚡ 生产化部署优化
- **🐳 容器编排** - 多环境Docker配置，服务发现，负载均衡
- **🔄 配置管理** - 环境变量化配置，密钥管理，配置热更新
- **📊 性能优化** - 数据库连接池，缓存策略，API响应优化
- **🛠️ 运维工具** - 自动化部署脚本，故障恢复，备份策略


### 🤖 开发体验

- 🛠️ **完整工具链** - 613行Makefile驱动的开发流程
- 🔍 **AI辅助开发** - 内置Cursor规则和AI工作流程指引
- 📚 **完善文档** - 20+个文档文件，覆盖开发到部署全流程
- 🔄 **实时监控** - CI状态监控、代码质量分析、生产级运维仪表板


## 🚀 快速开始

### 📋 新开发者必读（5分钟上手）

> ⚠️ **重要提醒**：请务必阅读 [测试运行指南](TEST_RUN_GUIDE.md) 了解正确的测试方法！
>
> 🔒 **安全配置**：生产部署前请配置环境变量，详见 [安全审计报告](reports/security_audit.md)

### 1. 克隆项目

```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

### 2. 选择启动方式

#### 🌐 完整全栈应用（推荐）
```bash
# 启动后端服务
make dev && make status

# 启动前端服务（新终端）
cd frontend
npm install
npm run dev
```

#### 🐳 Docker 一键启动
```bash
# 启动完整服务栈（包括前后端）
docker-compose -f docker-compose.yml -f docker-compose.frontend.yml up
```

### 3. 后端环境初始化

```bash
make install      # 安装后端依赖
make context      # 加载项目上下文 (⭐ 最重要)
make test         # 运行测试 (385个测试用例)
make coverage     # 查看当前覆盖率报告
```

### 4. 前端环境初始化

```bash
cd frontend
npm install       # 安装前端依赖
npm run dev       # 启动开发服务器
```

### 5. 验证服务状态 🧪

#### 后端服务验证
```bash
# Phase 1 核心功能测试（最重要）
make test-phase1

# 查看实际覆盖率
open htmlcov/index.html  # macOS 或
xdg-open htmlcov/index.html  # Linux

# 验证后端API
curl http://localhost:8000/health
```

#### 前端服务验证
```bash
# 检查前端开发服务器
curl http://localhost:5173

# 前端冒烟测试
cd frontend
node scripts/frontend_smoke_test.cjs
```

> 📌 **提示**：运行测试时**请使用 Makefile 命令**，不要直接运行 pytest 单个文件！详见 [测试运行指南](TEST_RUN_GUIDE.md)

### 6. 访问应用

- **前端应用**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 7. 验证部署就绪

```bash
./ci-verify.sh    # 本地CI验证（后端）
make ci           # 完整质量检查（后端）
```

### 4. 启动完整调度系统 (v2.5新功能)

```bash
# 启动包含调度器的完整服务栈
docker-compose -f docker-compose.yml -f docker-compose.scheduler.yml up -d

# 验证调度服务
curl http://localhost:4200  # Prefect UI
curl http://localhost:5555  # Flower UI
curl http://localhost:5000  # MLflow UI

# 检查调度状态
docker-compose ps
```

## 📁 项目结构

```text
FootballPrediction/                     # 项目根目录
├── src/                                # 后端源代码 (Python FastAPI)
│   ├── api/                           # API 层
│   ├── domain/                        # 领域层
│   ├── features/                      # 特征存储
│   ├── ml/                            # 机器学习
│   ├── database/                      # 数据库层
│   ├── services/                      # 业务服务
│   └── ...                           # 其他后端模块
├── frontend/                           # 前端源代码 (Vue.js 3)
│   ├── src/                           # 前端源码
│   │   ├── api/                       # API 客户端
│   │   ├── components/                # Vue 组件
│   │   │   ├── auth/                  # 认证组件
│   │   │   ├── charts/                # 图表组件
│   │   │   ├── match/                 # 比赛组件
│   │   │   └── profile/               # 用户中心组件
│   │   ├── layouts/                   # 页面布局
│   │   ├── router/                    # 路由配置
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── types/                     # TypeScript 类型定义
│   │   ├── views/                     # 页面视图
│   │   ├── App.vue                    # 根组件
│   │   └── main.ts                    # 应用入口
│   ├── package.json                   # 前端依赖配置
│   ├── vite.config.ts                 # Vite 构建配置
│   ├── tsconfig.json                  # TypeScript 配置
│   ├── tailwind.config.js             # Tailwind CSS 配置
│   └── scripts/                       # 前端工具脚本
├── tests/                             # 测试文件
├── docs/                              # 文档
├── .github/workflows/                 # CI/CD配置
├── Makefile                          # 后端开发工具链
├── docker-compose*.yml               # Docker 配置文件
└── requirements*.txt                 # Python 依赖定义
```

## 🔧 开发工具链

### 📋 快速命令

#### 后端开发工具
```bash
make help         # 显示所有可用后端命令 ⭐
make venv         # 创建虚拟环境
make install      # 安装后端依赖
make lint         # 后端代码检查
make test         # 运行后端测试
make ci           # 后端本地CI检查
make sync-issues  # GitHub Issues 同步 🔄
./scripts/run_tests_in_docker.sh  # 在容器中执行后端测试，隔离本地依赖
```

#### 前端开发工具
```bash
cd frontend
npm install          # 安装前端依赖
npm run dev          # 启动开发服务器
npm run build        # 构建生产版本
npm run preview      # 预览生产构建
npm run lint         # 前端代码检查
npm run type-check   # TypeScript 类型检查
```

#### 完整服务栈工具
```bash
# 启动完整服务（后端 + 前端）
make dev && cd frontend && npm run dev

# Docker 完整服务栈
docker-compose -f docker-compose.yml -f docker-compose.frontend.yml up

# 服务状态检查
make status                    # 后端服务状态
curl http://localhost:5173     # 前端服务状态
```

### 🛠️ 完整工具文档

**后端工具使用指南**: 📖 [TOOLS.md](./TOOLS.md)

**前端架构文档**: 📖 [docs/architecture/v3_0_frontend_summary.md](./docs/architecture/v3_0_frontend_summary.md)

包含：

- GitHub Issues 双向同步工具 🔄
- 代码质量和测试工具 ✨
- 环境管理和容器工具 🐳
- AI 助手使用指南 🤖
- Vue.js 前端开发最佳实践 🎨
- TypeScript 和组件化开发指南 📦


## 📚 文档入口

### 后端开发文档
- [Repository Guidelines](AGENTS.md) — 面向贡献者的结构、流程与安全基线快速上手手册。
- [测试改进机制指南](docs/TEST_IMPROVEMENT_GUIDE.md) — 了解 Kanban、CI Hook 与周报机制，快速上手测试优化流程。
- [🛡️ 测试实战指南](docs/TESTING_GUIDE.md) — SWAT行动成果，完整的测试方法论和最佳实践，涵盖Mock模式、CI/CD集成和安全网建设。

### 前端开发文档
- [🎨 P3 前端架构总览](docs/architecture/v3_0_frontend_summary.md) — 完整的前端 MVP 架构文档，包括技术栈、组件设计和最佳实践。
- [📱 前端快速开发指南](frontend/README.md) — Vue.js 3 + TypeScript 开发环境搭建和组件开发指南。

### 项目管理文档
- [🚀 项目路线图](docs/ROADMAP.md) — 项目发展规划和里程碑计划。
- [🔧 开发工具链](TOOLS.md) — 完整的开发工具使用指南和自动化脚本说明。


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
# 触发新的GitHub Actions检查

