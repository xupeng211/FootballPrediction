# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌟 重要提醒

**请始终使用简体中文回复用户，用户看不懂英文。**

---

## 📑 快速导航

- [🎯 核心必知](#-核心必知) - 首次打开必读
- [🏗️ 架构概览](#️-架构概览) - 技术栈和结构
- [📚 详细文档](#-详细文档) - 深入学习和故障排除

---

## 🎯 核心必知

### 🔥 首次打开项目必做（3步启动）

```bash
# 1️⃣ 环境准备
make install && make env-check

# 2️⃣ 智能修复（解决80%常见问题）
make fix-code

# 3️⃣ 快速验证
make test.smart
```

### ⚡ 25个核心开发命令

```bash
# 🔧 环境管理
make install          # 安装项目依赖
make env-check        # 检查环境健康
make create-env       # 创建环境文件
make venv             # 创建虚拟环境

# 🧪 测试相关
make test             # 运行单元测试（默认）
make test.smart       # 快速测试（<2分钟）
make test.unit        # 完整单元测试
make test.phase1      # Phase 1核心功能测试
make coverage         # 覆盖率报告
make cov.html         # HTML覆盖率报告
make solve-test-crisis # 测试危机解决方案

# 🔍 质量工具
make fix-code         # 一键修复代码质量
make check-quality    # 质量检查
make ci-check         # CI/CD验证
make prepush          # 提交前验证
make security-check   # 安全扫描

# 🚀 渐进式改进系列
make improve-start    # 开始改进会话
make improve-status   # 查看改进状态
make improve-all      # 执行完整改进

# 🤖 MLOps 系列
make feedback-update  # 更新预测反馈循环
make model-monitor    # 监控模型健康状况
make performance-report # 生成性能分析报告

# 🐳 部署相关
make up               # 启动服务
make down             # 停止服务
make deploy           # 部署容器
make ci               # 本地CI完整验证
```

### ⚠️ 关键规则

- **永远不要**对单个文件使用 `--cov-fail-under`
- **优先使用** Makefile命令而非直接调用工具
- **覆盖率阈值**: 当前29.0%，目标40%（渐进式提升）
- **中文沟通**: 始终用简体中文回复用户

### 🔍 常用测试命令

```bash
# 按类型运行测试
pytest -m "unit" -v              # 单元测试
pytest -m "integration" -v       # 集成测试
pytest -m "critical" --maxfail=5 # 关键功能测试
pytest -m "not slow"             # 排除慢速测试

# Smart Tests 快速验证
make test.smart                  # 运行稳定的核心测试组合
pytest -m "not slow" --maxfail=5 -x  # 快速失败模式

# 覆盖率相关
make cov.html                     # HTML覆盖率报告
pytest --cov=src --cov-report=term-missing

# 单个测试文件
pytest tests/unit/utils/test_date_utils.py -v
pytest tests/unit/cache/test_redis_manager.py::TestRedisManager::test_set_get -v

# 按模块运行测试
pytest tests/unit/api/ -v
pytest tests/unit/domain/ -v
pytest tests/unit/database/ -v

# 运行特定标记的测试
pytest -m "critical" -v
pytest -m "not slow" --maxfail=5
```

### 🛠️ 开发环境设置

```bash
# 环境配置文件
cp .env.example .env
# 编辑 .env 文件设置数据库和Redis连接

# 数据库迁移
make migrate-up

# 启动开发环境
make up
```

### 🔧 关键环境变量

```bash
# 必需的生产环境变量
DATABASE_URL=postgresql://user:pass@host:5432/football_prediction
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-production-secret-key-change-this

# 开发配置
ENV=development
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# 安全配置
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 外部服务配置
EXTERNAL_API_TIMEOUT=30
EXTERNAL_API_RETRIES=3

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
```

---

## 🏗️ 架构概览

### 💻 技术栈
- **后端**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动
- **机器学习**: LSTM、Poisson分布、Elo评分、集成学习
- **测试**: 完整测试体系，40个标准化测试标记
- **工具**: Ruff + MyPy + pytest + Docker + CI/CD

### 📁 核心结构

```
src/
├── domain/           # 业务实体和领域逻辑
│   ├── models/       # 领域模型 (Match, Team, League, Prediction)
│   ├── services/     # 领域服务 (业务逻辑核心)
│   ├── strategies/   # 预测策略 (ML模型、统计分析)
│   └── events/       # 领域事件 (事件驱动架构)
├── api/             # FastAPI路由层
│   ├── models/       # API请求/响应模型
│   ├── predictions/  # 预测API路由
│   └── health/       # 健康检查端点
├── services/        # 应用服务层
├── database/        # 数据访问层 (SQLAlchemy 2.0)
├── cache/           # 多级缓存 (Redis + TTL)
├── core/            # 核心基础设施 (DI、配置、日志)
├── cqrs/            # CQRS模式实现
├── ml/              # 机器学习模型训练和预测
├── adapters/        # 适配器模式 (数据源统一)
└── utils/           # 工具函数
```

### 🔧 关键设计模式

**领域驱动设计 (DDD)**: 四层架构，清晰的领域边界
**CQRS模式**: 命令查询职责分离，读写优化
**策略工厂模式**: 动态选择预测策略，支持多模型集成
**依赖注入容器**: 轻量级DI容器，生命周期管理
**事件驱动架构**: 异步事件处理，松耦合组件通信
**适配器模式**: 统一不同数据源接口，便于扩展

### 🧪 测试体系

**57个标准化测试标记**：
- **类型标记**: unit, integration, e2e, performance
- **功能域标记**: api, domain, database, cache, auth, monitoring, streaming, collectors, middleware, utils, core, decorators, business, services, health, validation
- **执行特征标记**: slow, smoke, critical, regression, metrics, edge_cases
- **技术特定标记**: ml, asyncio, external_api, docker, network
- **问题特定标记**: issue94

**Smart Tests配置**：
- 核心稳定模块：`tests/unit/utils`, `tests/unit/cache`, `tests/unit/core`
- 执行时间：<2分钟，通过率>90%
- 排除不稳定测试文件：
  - `tests/unit/services/test_prediction_service.py`
  - `tests/unit/core/test_di.py`
  - `tests/unit/core/test_path_manager_enhanced.py`
  - `tests/unit/core/test_config_new.py`
  - `tests/unit/scripts/test_create_service_tests.py`
  - `tests/unit/test_core_logger_enhanced.py`

### 🤖 机器学习架构

**预测策略**:
- **LSTM模型**: 时序数据预测，处理比赛历史数据
- **Poisson分布**: 进球数概率建模
- **Elo评分**: 球队实力评分系统
- **集成策略**: 多模型加权组合预测

**特征工程**:
- 自动化特征计算和存储
- 比赛统计数据、历史对战记录
- 球队状态、球员伤病情况

**MLOps工具链**:
```bash
# ML相关命令
make feedback-update    # 更新预测反馈循环
make model-monitor      # 监控模型健康状况
make retrain-check      # 检查模型是否需要重新训练
make retrain-dry        # 干运行重新训练检查（仅评估）
make mlops-pipeline     # 运行完整的MLOps反馈管道
make mlops-status       # 显示MLOps管道状态

# ML模型测试
make feedback-test      # 运行反馈循环单元测试
```

### 🐳 服务栈

**开发环境（4个核心服务）**：
```bash
make up          # 启动所有服务
```

- **app** (FastAPI应用) - 主要API服务
- **db** (PostgreSQL 15) - 主数据库
- **redis** (Redis 7-alpine) - 缓存和会话存储
- **nginx** (反向代理) - 负载均衡和静态文件服务

**完整生产环境（7个服务）**：
- app (FastAPI应用)
- db (PostgreSQL)
- redis (Redis缓存)
- nginx (反向代理)
- prometheus (监控)
- grafana (可视化)
- loki (日志聚合)

**服务访问地址**：
- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **交互式API**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **数据库**: localhost:5432 (PostgreSQL 15)
- **Redis缓存**: localhost:6379 (Redis 7-alpine)
- **Nginx代理**: http://localhost:80 (生产环境)

**监控服务栈（生产环境）**：
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **日志聚合**: http://localhost:3100 (Loki)

**实时功能栈**：
- **WebSocket**: 实时比赛数据推送和预测更新
- **流处理**: Kafka消息队列处理实时数据流
- **事件驱动**: 异步事件处理和通知系统

**实时功能测试**：
```bash
# WebSocket连接测试
curl http://localhost:8000/realtime/matches

# 流数据测试
curl http://localhost:8000/streaming/predictions

# 事件处理测试
curl http://localhost:8000/realtime/events
```

**Docker 开发环境管理**：
```bash
# 服务状态检查
docker-compose ps                # 查看所有服务状态
docker-compose logs app          # 查看应用日志
docker-compose exec app bash     # 进入应用容器

# 端口冲突解决
docker-compose down              # 停止所有服务
make up                          # 重新启动服务
```

---

## 📚 详细文档

### 📋 核心配置文件
- `pyproject.toml`: 依赖管理和工具配置，包含完整的pytest和coverage设置
- `pytest.ini`: 测试配置和57个标记定义，Smart Tests优化
- `Makefile`: 76KB企业级开发工作流，25个核心命令
- `docker-compose.yml`: 容器编排配置，4个开发环境核心服务
- `.env.example`: 环境变量模板，包含必需的生产环境配置

### 🔧 重要配置细节

**pytest配置 (pyproject.toml)**:
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
coverage_threshold = 40
```

**覆盖率配置**:
```toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

### 🔄 CI/CD 集成说明

**本地 CI 验证**：
```bash
./ci-verify.sh                    # 完整本地CI验证脚本
# 自动执行：环境重建 → Docker启动 → 测试验证 → 覆盖率检查
```

**CI 环境一致性保证**：
- **容器化测试**: `./scripts/run_tests_in_docker.sh` - 隔离本地依赖
- **环境变量**: `.env.ci` - CI专用配置
- **依赖锁定**: `requirements.lock` - 确保版本一致性
- **Docker Compose**: 本地完整模拟CI环境

**GitHub Actions 集成**：
- **Kanban检查**: 自动同步项目状态
- **质量门禁**: 代码覆盖率、安全扫描、测试通过率
- **自动化部署**: 容器镜像构建和推送

**质量验证流程**：
1. `make env-check` - 环境健康检查
2. `make test.smart` - 快速功能验证
3. `make security-check` - 安全漏洞扫描
4. `make coverage` - 覆盖率验证
5. `make prepush` - 完整提交前验证

### 🔧 高级主题
- **完整的代码示例**: [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md#代码示例)
- **性能优化配置**: [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md#性能优化)
- **故障排除指南**: [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md#故障排除)
- **质量修复工具**: [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md#质量修复)

### 🚨 常见问题快速解决

**测试大量失败 >30%**：
```bash
make solve-test-crisis
make fix-code
make test.unit
```

**代码质量问题**：
```bash
make fix-code
make check-quality
ruff check src/ tests/ --fix
```

**环境问题**：
```bash
make env-check
make create-env
make check-deps
```

**Docker问题**：
```bash
make down && make up
docker-compose exec app make test.unit
```

**数据库连接问题**：
```bash
# 检查数据库服务状态
docker-compose ps db
# 重启数据库
docker-compose restart db
# 运行迁移
make migrate-up
```

**本地开发环境故障排除**：
```bash
# 端口冲突解决
make down && make up

# 服务状态检查
docker-compose ps
docker-compose logs app

# 进入容器调试
docker-compose exec app bash

# 环境变量问题
make env-check
make create-env
```

**覆盖率问题**：
```bash
# 查看详细覆盖率报告
make cov.html
open htmlcov/index.html  # macOS 或
xdg-open htmlcov/index.html  # Linux

# 单个模块覆盖率检查
pytest --cov=src.domain --cov-report=term-missing tests/unit/domain/
```

### 🛡️ 企业级安全扫描工具链

**多层安全审计体系**：
```bash
# 代码安全扫描
make security-check    # 运行完整安全扫描
bandit -r src/         # 代码漏洞扫描
safety check           # 依赖漏洞检查
pip-audit              # 依赖审计
trufflehog git .       # 密钥扫描
gitleaks detect        # 密钥泄露检测
pip-licenses --from=mixed --format=table  # 许可证检查
```

**安全工具集成**：
- **Bandit**: Python代码安全漏洞扫描
- **Safety**: PyPI依赖包漏洞检查
- **pip-audit**: 依赖审计和漏洞数据库
- **TruffleHog**: Git历史密钥扫描
- **Gitleaks**: 密钥泄露检测
- **pip-licenses**: 开源许可证合规检查

### 📋 提交前检查

- [ ] `make test.smart` 快速验证通过
- [ ] `make test.unit` 完整单元测试通过
- [ ] `make security-check` 安全扫描通过
- [ ] `make ci-check` 无严重问题
- [ ] `make coverage` 达到当前29.0%覆盖率
- [ ] `make prepush` 完整验证通过

---

## 🏆 项目状态

- **🏗️ 架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动
- **📏 规模**: 企业级代码库，完整测试体系
- **🧪 测试**: 57个标准化测试标记，40%覆盖率目标
- **🛡️ 质量**: 现代化工具链（Ruff + MyPy + 安全扫描）
- **🤖 工具**: 自动化脚本 + 完整CI/CD工作流
- **🎯 方法**: 渐进式改进策略，Docker容器化部署

### 🚀 核心优势

- **智能修复**: 完整的代码质量修复工具链
- **渐进改进**: 不破坏现有功能的持续优化
- **完整工具链**: 从开发到部署的全流程自动化
- **企业级就绪**: 完整的CI/CD、监控、安全体系
- **ML驱动**: 多模型集成的智能预测引擎

---

*文档版本: v28.0 (企业级增强版) | 维护者: Claude Code | 更新时间: 2025-11-17*

📖 **需要更详细的信息？** 查看 [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md) 获取完整的代码示例、配置参数和故障排除指南。