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

### ⚡ 15个核心开发命令

```bash
# 🔧 环境管理
make install          # 安装项目依赖
make env-check        # 检查环境健康
make create-env       # 创建环境文件

# 🧪 测试相关
make test             # 运行单元测试（默认）
make test.smart       # 快速测试（<2分钟）
make test.unit        # 完整单元测试
make coverage         # 覆盖率报告
make solve-test-crisis # 测试危机解决方案

# 🔍 质量工具
make fix-code         # 一键修复代码质量
make check-quality    # 质量检查
make ci-check         # CI/CD验证
make prepush          # 提交前验证

# 🐳 部署相关
make up               # 启动服务
make down             # 停止服务
make deploy           # 部署容器
```

### ⚠️ 关键规则

- **永远不要**对单个文件使用 `--cov-fail-under`
- **优先使用** Makefile命令而非直接调用工具
- **覆盖率阈值**: 40%目标阈值
- **中文沟通**: 始终用简体中文回复用户

### 🔍 常用测试命令

```bash
# 按类型运行测试
pytest -m "unit" -v              # 单元测试
pytest -m "integration" -v       # 集成测试
pytest -m "critical" --maxfail=5 # 关键功能测试
pytest -m "not slow"             # 排除慢速测试

# 覆盖率相关
make cov.html                     # HTML覆盖率报告
pytest --cov=src --cov-report=term-missing

# 单个测试文件
pytest tests/unit/utils/test_date_utils.py -v
pytest tests/unit/cache/test_redis_manager.py::TestRedisManager::test_set_get -v
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
- 排除不稳定测试文件

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
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

---

## 📚 详细文档

### 📋 核心配置文件
- `pyproject.toml`: 依赖管理和工具配置，包含完整的pytest和coverage设置
- `pytest.ini`: 测试配置和57个标记定义，Smart Tests优化
- `Makefile`: 76KB企业级开发工作流，15个核心命令
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

### 📋 提交前检查

- [ ] `make test.smart` 快速验证通过
- [ ] `make test.unit` 完整单元测试通过
- [ ] `make ci-check` 无严重问题
- [ ] `make coverage` 达到40%阈值
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

*文档版本: v27.0 (配置精确化版) | 维护者: Claude Code | 更新时间: 2025-11-17*

📖 **需要更详细的信息？** 查看 [CLAUDE_DETAILED.md](./CLAUDE_DETAILED.md) 获取完整的代码示例、配置参数和故障排除指南。