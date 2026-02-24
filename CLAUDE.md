# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 🚨 AI 开发准则（最高优先级）

### 🛠️ 环境管理（禁止污染宿主机）
1. **容器化优先**：所有开发、测试、依赖安装必须在 Docker 容器内进行。
2. **严禁修改宿主机**：严禁修改任何宿主机文件（如 `~/.bashrc`, `~/.zshrc`, `/etc/profile` 等）。
3. **环境即代码**：所有环境变更（代理、系统库、环境变量）必须通过修改 `Dockerfile` 或 `docker-compose.dev.yml` 实现，禁止手动在终端执行安装指令而不记录。

### 🌳 Git & 分支规范
1. **主线作战**：除非用户明确要求，否则严禁创建任何新分支。所有代码变更必须直接提交至 `main` 分支。
2. **拒绝自动分支**：严禁为了 bugfix 自动生成类似 `chore/bugfix-xxx` 的分支。
3. **提交规范**：每次 Commit 必须简洁明了，格式为 `feat: xxx` 或 `fix: xxx`。

### 🏷️ 版本与存档
1. **用户主导 Tag**：AI 不得私自创建 Git Tag。Tag 必须由用户手动输入指令创建。
2. **定期同步**：在完成重大逻辑修改并测试通过后，必须提醒用户执行 `git push` 和手动打标签。

### ⚠️ 紧急避险
如果任何操作可能导致宿主机网络或登录异常，必须立即停止并向用户确认风险。

---

## 📑 快速导航

### 🆕 新开发者快速通道

**5 分钟快速上手**（推荐路径 - 容器化开发）：

```
克隆项目 → make dev-up → make dev-shell → 开始开发
```

**传统路径**（本地开发）：

```
克隆项目 → 安装依赖 → make up → python main.py --test-proxy → 开始开发
```

### 按角色查找

| 角色 | 推荐阅读 | 预计时间 |
|------|----------|----------|
| **新开发者** | [docs/onboarding.md](docs/onboarding.md) → [快速开始](#-快速开始) | 30 分钟 |
| **数据采集工程师** | [数据采集系统](#-数据采集系统) + [QuantHarvester](#-quantharvester-v170000) + [NetworkShield](#-networkshield-v110-工业级代理管理) | 60 分钟 |
| **机器学习工程师** | [ML 引擎](#核心模块) + [特征工程](#核心模块) | 60 分钟 |
| **运维工程师** | [Docker 部署](#docker-容器化部署) + [环境检测](#️-环境检测系统) | 30 分钟 |
| **JavaScript 工具** | [JavaScript 运维工具文档](docs/CLAUDE_JS_TOOLS.md) | 45 分钟 |

### 按任务查找

| 我想... | 使用命令 |
|--------|----------|
| 🚀 启动开发容器 | `make dev-up` |
| 🐚 进入开发容器 | `make dev-shell` |
| 📦 启动核心服务 | `make up` |
| 🧪 运行代码质量检查 | `make verify` |
| 📊 采集单场比赛数据 | `python main.py --source fotmob --mode single --limit 1` |
| 🔄 24h 全自动巡航 | `python main.py --mode cruise` |
| 🔍 检查代理连通性 | `python main.py --test-proxy` |
| 🗄️ 进入数据库 | `make db-shell` |
| 📈 查看系统日志 | `make logs` |
| 🌐 JavaScript 收割 | `make dev-harvest` |
| 🛑 停止开发容器 | `make dev-down` |

---

## ⚡ 超快速索引（15 个核心命令）

```bash
# 开发容器（推荐）
make dev-up              # 启动容器化开发环境
make dev-shell           # 进入开发容器
make dev-down            # 停止开发容器
make dev-harvest         # 在容器中运行 QuantHarvester

# 环境管理
make up                  # 启动核心服务 (db + redis)
make verify              # lint + test-unit + security
make ps                  # 查看容器状态

# 数据采集（Python）
python main.py --source fotmob --mode single --limit 10    # FotMob API
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA
python main.py --mode cruise                                # 24h 巡航
python main.py --test-proxy                                 # 测试代理

# 数据采集（一键入口）
python production_fire.py                                   # 一键数据采集

# 数据采集（JavaScript）
node src/infrastructure/engines/QuantHarvester.js           # V170.000 收割

# 开发和测试
make test-unit           # 单元测试
make db-shell            # PostgreSQL Shell
```

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **QuantHarvester** | V170.000 (Genesis.NetworkShield) |
| **NetworkShield** | V1.1.0 (工业级代理管理) |
| **命令中心** | V144.9 (Multi-Source Command Center) |
| **核心模型** | V26.8 (联赛专项) |
| **特征提取** | V41.380 (GoldenExtractor) |
| **代码质量** | V106.0 (Ruff - line-length: 100) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |

### 版本兼容性矩阵

| Python 版本 | 支持状态 | 推荐用途 |
|-------------|----------|----------|
| **3.11** | ✅ 完全支持 | 生产环境 |
| **3.12** | ✅ 完全支持 | 最新特性 |
| **3.10** | ⚠️ 兼容 | 最低版本 |
| **3.13** | 🔄 测试中 | 实验性 |

| Node.js 版本 | 支持状态 | 用途 |
|--------------|----------|------|
| **18.x** | ✅ 完全支持 | JavaScript 运维工具 |
| **20.x** | ✅ 完全支持 | 推荐 |

---

## ⚡ 快速开始

### 3 分钟上手（4 步）

```bash
# 1. 验证 Git 分支（开发前检查）
git status

# 2. 启动核心服务（自动检测环境）
make up

# 3. 验证环境并采集测试数据
python main.py --source fotmob --mode single --limit 1

# 4. 检查代码质量（提交前必需）
make verify
```

### 环境要求

| 软件 | 版本 | 检查命令 |
|------|------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Git | 最新 | `git --version` |

---

## 🐳 容器化开发环境（推荐）

### 一键启动

```bash
make dev-up              # 启动容器化开发环境
```

这条命令会：
1. 构建开发镜像（Python 3.11 + Node.js 20 LTS）
2. 启动 db + redis + dev 容器
3. 安装所有依赖
4. 进入开发就绪状态

### 常用命令

| 命令 | 说明 |
|------|------|
| `make dev-up` | 启动开发容器 |
| `make dev-shell` | 进入开发容器 Shell |
| `make dev-logs` | 查看容器日志 |
| `make dev-down` | 停止开发容器 |
| `make dev-harvest` | 运行 QuantHarvester |

### 核心特性

| 特性 | 说明 |
|------|------|
| **热更新** | Windows 侧改代码 → 容器内立刻生效 |
| **双语言** | Python 3.11 + Node.js 20 LTS |
| **国内加速** | 阿里云镜像源（apt/pip/npm） |
| **完整工具链** | Git, vim, Playwright, pnpm 等 |

### 服务端口

| 服务 | 端口 |
|------|------|
| API Server | 8000 |
| Dashboard | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Python Debug | 5678 |

---

## 🌐 环境检测系统

项目内置**智能环境检测系统**，自动识别运行环境并配置最优参数：

| 环境类型 | DB_HOST | 代理配置 | 启动方式 |
|----------|---------|----------|----------|
| **Docker** (DOCKER_ENV=true) | `db` | 环境变量 | `make up` |
| **WSL2** (/proc/version 包含 "microsoft") | `172.25.16.1` | 自动探测 | `make up` |
| **本地** (默认) | `localhost` | 手动配置 | `make up` |

### 禁用自动检测

如需手动配置，可设置环境变量：
```bash
export DB_HOST=custom_host
export DB_NAME=football_db  # 必须为 football_db
```

---

## 🏗️ 系统架构

### 数据流

```
数据采集层 (FotMob API + OddsPortal RPA + QuantHarvester)
    → 特征工程层 (GoldenExtractor V41.380, 6000+ 维特征)
    → 数据持久层 (PostgreSQL: matches + metrics_multi_source_data)
    → 预测引擎层 (ModelDispatcher V26.8 → XGBoost)
```

### 核心目录结构

```
FootballPrediction/
├── src/                              # 生产代码
│   ├── api/                          # API 层
│   │   ├── collectors/               # 数据采集器 (base_extractor, fotmob_core, odds_production_extractor)
│   │   ├── models/                   # 数据模型
│   │   └── services/                 # 业务服务层 (harvester_service)
│   ├── infrastructure/               # 基础设施层
│   │   ├── engines/                  # QuantHarvester.js + match_engine/
│   │   └── network/                  # NetworkShield 代理管理
│   ├── ml/                           # 机器学习 (engine.py, processors/)
│   └── config/                       # 配置模块 (league/, utils/)
├── config/                           # 配置文件
│   ├── active_registry.json          # NetworkShield 节点配置
│   └── schema_map.yaml               # Schema 韧性配置
├── tests/                            # 测试套件
├── scripts/ops/                      # 运维工具
├── main.py                           # V144.7 统一命令入口
├── production_fire.py                # 一键数据采集入口
├── Makefile                          # 统一命令入口
└── ruff.toml                         # 代码质量配置 (line-length: 100)
```

---

## 🧬 QuantHarvester V170.000 - Genesis.NetworkShield

**QuantHarvester V170.000** 是最新的 JavaScript 数据收割引擎，集成 **NetworkShield V1.1.0** 工业级代理管理系统，专门用于从 OddsPortal 采集高价值赔率数据。

### 核心特性

| 特性 | 说明 |
|------|------|
| **双模提取** | 网络拦截（首选）→ 20秒超时后 DOM 抓取（回退） |
| **NetworkShield 集成** | 22节点工业级代理管理，Session 绑定 |
| **跨语言同步** | Python + Node.js 状态共享 |

### 使用方式

```bash
# 基本用法（自动使用 NetworkShield）
node src/infrastructure/engines/QuantHarvester.js

# 禁用代理
PROXY_ENABLED=false node src/infrastructure/engines/QuantHarvester.js
```

---

## 🛡️ NetworkShield V1.1.0 - 工业级代理管理

**NetworkShield V1.1.0** 是中央代理管理系统，统一管理 Python (L2) 和 Node.js (L3) 的网络出口，深度对接 Windows 端的 Clash Verge (22个节点)。

### 核心特性

- **中央注册制**: 统一节点注册，状态持久化到 `config/active_registry.json`
- **自愈熔断**: 连续失败 2 次后自动屏蔽节点，15 分钟冷却后尝试恢复
- **Session 绑定**: 一个会话 = 一个 IP，确保请求一致性

### 熔断器状态

| 状态 | 触发条件 | 恢复条件 |
|------|----------|----------|
| **active** | 默认状态 | - |
| **circuited** | 连续失败 2 次 | 15 分钟冷却后尝试恢复 |
| **cooldown** | 手动设置冷却 | 冷却时间结束后恢复 |

### 使用方式（Python）

```python
from src.infrastructure.network import get_network_shield

shield = get_network_shield(log_level='info')
await shield.initialize()
proxy = await shield.get_next_healthy_proxy(session_id='my-session')
```

---

## ⚙️ Match Engine - Python 基础收割引擎

**Match Engine** 是 Python 基础收割引擎架构，提供统一的数据采集基础框架。

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **BaseHarvestEngine** | `base/base_harvest_engine.py` | 基础收割引擎抽象类 |
| **CircuitBreaker** | `shared/circuit_breaker.py` | 熔断器模式实现 |
| **NetworkGuardian** | `shared/network_guardian.py` | NetworkShield 适配器 |
| **DynamicDiscoveryEngine** | `discovery/dynamic_discovery_engine.py` | 动态比赛发现引擎 |
| **FotMobEngine** | `fotmob/fotmob_engine.py` | FotMob 数据采集 |

### 使用方式

```python
from src.infrastructure.engines.match_engine.fotmob import FotMobEngine

engine = FotMobEngine()
matches = await engine.discover_matches(league_id=47, season="2324")
```

---

## 🔧 开发指南

### 🚨 核心约束

| 约束 | 说明 |
|------|------|
| **单数据库准则** | `DB_NAME` 必须为 `football_db` |
| **禁止绕过 FotMobCoreCollector** | 所有 FotMob 采集必须使用指定方法 |
| **禁止直接修改 model_zoo/** | 模型文件只能通过重新训练更新 |
| **禁止创建版本类文件** | 不创建 `*_v2.py`, `*_new.py`, `*_backup.py` |

### 代码质量规范

**提交前必须运行**: `make verify` (lint + test-unit + security)

**代码格式化**: `ruff.toml` (line-length: **100**) 优先级高于 `pyproject.toml` (line-length: 120)

**推荐的代码质量工作流**：
```bash
ruff format src/ tests/    # 格式化代码
ruff check src/ tests/     # Lint 检查
mypy src/                  # 类型检查
bandit -r src/             # 安全扫描
```

### 配置文件优先级

| 配置文件 | 作用 | 优先级 |
|----------|------|--------|
| `ruff.toml` | 代码质量配置 (line-length: 100) | **最高** |
| `config/active_registry.json` | NetworkShield 22 节点配置 | 高 |
| `config/schema_map.yaml` | Schema 韧性配置（数据源 API 路径映射） | 高 |
| `.env` | 环境变量（数据库、Redis 连接） | 高 |
| `pyproject.toml` | 项目元数据和依赖 | 备用 |

### Git 工作流

```bash
git checkout -b feature/your-feature-name   # 创建功能分支
make verify                                  # 提交前质量检查
git commit -m "feat: 添加 XXX 功能"          # 提交 (feat|fix|docs|refactor|test|chore)
```

---

## 🧬 核心模块

### main.py - V144.7 统一命令入口

```bash
python main.py --source fotmob --mode single --limit 10    # FotMob API
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA
python main.py --mode cruise                                # 24h 巡航
python main.py --test-proxy                                 # 测试代理
```

### production_fire.py - 一键数据采集

```bash
python production_fire.py    # 一键数据采集入口
```

### ModelDispatcher (V26.8)

```python
from src.ml.engine import ModelDispatcher
dispatcher = ModelDispatcher()
prediction = dispatcher.predict(home_team="Arsenal", away_team="Chelsea", league_name="Premier League")
```

### GoldenExtractor (V41.380) - 三大黄金特征

- **市场价值特征**: 球队总身价、身价差值
- **缺阵特征**: 伤停球员、身价影响
- **评分特征**: 球队评分、球员评分

---

## 📊 系统性能基准

| 指标 | 基准值 | 实际测试值 |
|------|--------|-----------|
| **推理延迟** | <100ms | 平均 45ms |
| **吞吐量** | >100 QPS | 150 QPS |
| **模型准确率** | 56% | 56.3% |
| **特征维度** | 6000+ | 6142 维 |
| **FotMob API** | ~2s/match | 1.8s/match |
| **OddsPortal RPA** | ~5s/match | 4.7s/match |
| **QuantHarvester** | ~20s/match | V170.000 双模提取 (NetworkShield 集成) |

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发 |
| **语言** | Node.js | 18+ | JavaScript 运维工具 |
| **数据库** | PostgreSQL | 15 | 数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器自动化** | Playwright | 1.57+ | 网页自动化 |
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |
| **代码质量** | Ruff | 0.8+ | 格式化 + Lint |

---

## 🧪 测试指南

| 场景 | 命令 |
|------|------|
| **快速反馈** | `make test-unit` (2 个核心测试文件) |
| **完整单元测试** | `pytest tests/unit/ -v` (80+ 文件) |
| **提交前验证** | `make verify` (lint + test-unit + security) |
| **全量测试** | `pytest tests/ -v` |
| **JavaScript 测试** | `cd scripts/ops && npm test` |

---

## 🐛 常见错误速查表

> 💡 **详细故障排除**: [docs/troubleshooting.md](docs/troubleshooting.md)

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `database "football_db" does not exist` | 数据库未初始化 | `make up` |
| `Timeout 30000ms exceeded` | 网络慢 | 检查代理配置 |
| `HTTP 429/403` | IP 限流/封禁 | 等待 6-24h 或启用 Ghost Protocol |
| `ConnectionRefusedError: 5432` | 数据库未启动 | `make up` |
| `ModuleNotFoundError: No module named 'src'` | Python 路径问题 | 在项目根目录运行 |
| `NetworkShield: No healthy nodes` | 所有节点不可用 | 运行健康检查 |

---

## 🐚 Docker 容器化部署

```bash
# 服务管理
make up                  # 启动核心服务 (db + redis)
make up-pipeline         # 启动 + 数据流水线
make up-api              # 启动 + API 服务
make down                # 停止所有服务
make ps                  # 查看状态

# 数据库
make db-shell            # PostgreSQL Shell
make db-backup           # 备份数据库
make redis-shell         # Redis CLI

# 日志和监控
make logs                # 核心服务日志
make logs-api            # API 日志

# 清理和部署
make clean               # 清理缓存
make deploy              # 部署到生产
```

---

## 🌐 版本号体系

本项目采用**多版本号体系**，各组件独立演进：

| 版本前缀 | 组件范围 | 当前版本 |
|----------|----------|----------|
| `V170.x` | QuantHarvester + NetworkShield | V170.000 |
| `V144.x` | 多数据源命令中心 | V144.9 |
| `V26.x` | ML 特征引擎和模型 | V26.8 |
| `V41.x` | 数据采集运维工具 | V41.832 |
| `V1.x` | NetworkShield 代理管理 | V1.1.0 |

> **注意**: 项目版本 (`V26.7.0`) 与组件版本独立。

---

## 📚 延伸阅读

| 文档 | 内容 |
|------|------|
| [docs/onboarding.md](docs/onboarding.md) | 新开发者快速上手 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 故障排除指南 |
| [docs/CLAUDE_JS_TOOLS.md](docs/CLAUDE_JS_TOOLS.md) | JavaScript 运维工具完整参考 |

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**生产状态**: Production Ready | **Python**: 3.11+ | **Node.js**: 18+
