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
| **新开发者** | [快速开始](#-快速开始) → [开发指南](#-开发指南) | 30 分钟 |
| **数据采集工程师** | [QuantHarvester](#-quantharvester-v171001---integrated-harvester) + [NetworkShield](#-networkshield-v110---工业级代理管理) + [Match Engine](#-match-engine---python-基础收割引擎) | 60 分钟 |
| **机器学习工程师** | [ML引擎架构](#ml-引擎架构训练-vs-推理分离) + [核心模块](#-核心模块) | 60 分钟 |
| **运维工程师** | [Docker 部署](#-docker-容器化部署) + [环境检测](#️-环境检测系统) | 30 分钟 |
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

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **QuantHarvester** | V171.001 (Integrated Harvester + Multi-Model Consensus) |
| **NetworkShield** | V1.1.0 (工业级代理管理, 22节点) |
| **命令中心** | V144.9 (Multi-Source Command Center) |
| **核心模型** | V26.8 (联赛专项) |
| **特征提取** | V41.380 (GoldenExtractor) |
| **代码质量** | V106.0 (Ruff - line-length: 100) |
| **基线准确率** | 56% (真赛前) / 62%+ (V171 目标) |
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

### 数据流水线（三层架构）

```
┌─────────────────────────────────────────────────────────────────────┐
│  L1: FotMob API - 基础数据层                                         │
│  • 比赛基础信息: league, season, teams, match_time                   │
│  • 实时统计数据: xG, shots, possession                               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  L2: URL Harvest - 链接收割层 (Python Match Engine)                  │
│  • 自动导航联赛页面，智能提取比赛详情链接                              │
│  • NetworkShield 代理池 + 熔断器模式                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  L3: RPA Extraction - 赔率提取层 (QuantHarvester.js)                 │
│  • 双模提取: 网络拦截（首选）→ DOM 抓取（回退）                        │
│  • MultiModelValidator: 3模型并发 + 2/3一致性验证                     │
│  • FundamentalHarvester: 首发阵容 + 伤停名单 + 球队身价               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PostgreSQL 持久层                                                   │
│  matches 表 + metrics_multi_source_data 表 + match_odds_intelligence │
└─────────────────────────────────────────────────────────────────────┘
```

### ML 引擎架构（训练 vs 推理分离）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ML Engine Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  训练层 (src/ml/training/)          推理层 (src/ml/inference/)       │
│  ┌──────────────────────┐          ┌──────────────────────┐        │
│  │ V17MLEngine          │          │ ModelDispatcher      │        │
│  │ • 数据集生成          │          │ • 联赛专项模型路由     │        │
│  │ • 特征工程            │          │ • XGBoost 预测        │        │
│  │ • 模型训练            │          │ • MultiModelValidator │        │
│  └──────────────────────┘          └──────────────────────┘        │
│           ↓                                   ↓                      │
│  ┌──────────────────────┐          ┌──────────────────────┐        │
│  │ model_zoo/           │◀─────────│ Predictor            │        │
│  │ • league_specific/   │  模型加载 │ • 特征适配            │        │
│  │ • generic/           │          │ • 概率输出            │        │
│  └──────────────────────┘          └──────────────────────┘        │
│                                                                      │
│  特征工程层 (src/ml/feature_engine/)                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ GoldenExtractor V41.380 (6000+维特征)                         │   │
│  │ • 市场价值特征: 球队总身价、身价差值                            │   │
│  │ • 缺阵特征: 伤停球员、身价影响                                  │   │
│  │ • 评分特征: 球队评分、球员评分                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  向后兼容层: src/ml/engine.py - ModelDispatcher (保持旧版API)        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心数据库表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `matches` | 比赛主表 | match_id, home_team, away_team, technical_features, golden_features |
| `metrics_multi_source_data` | 多源数据 | match_id, source_name, odds_data, integrity_score |
| `match_odds_intelligence` | 赔率智能 | match_id, pinnacle_opening, pinnacle_closing |
| `match_lineups` | 首发阵容 | match_id, home_lineup, away_lineup, unavailable_list |

### 核心目录结构

```
FootballPrediction/
├── src/                              # 生产代码
│   ├── api/                          # API 层
│   │   ├── collectors/               # 数据采集器 (base_extractor, fotmob_core, odds_production_extractor)
│   │   ├── models/                   # 数据模型 (schemas.py V105.0 Pydantic)
│   │   └── services/                 # 业务服务层 (harvester_service, 队列驱动)
│   ├── infrastructure/               # 基础设施层
│   │   ├── engines/                  # QuantHarvester.js + match_engine/
│   │   │   └── match_engine/         # Python 基础收割引擎
│   │   │       ├── base/             # BaseHarvestEngine 抽象类
│   │   │       ├── fotmob/           # FotMobEngine 数据采集
│   │   │       ├── discovery/        # DynamicDiscoveryEngine 动态发现
│   │   │       └── shared/           # CircuitBreaker + NetworkGuardian
│   │   └── network/                  # NetworkShield 代理管理
│   ├── ml/                           # 机器学习
│   │   ├── training/                 # 训练引擎 (v17_engine.py)
│   │   ├── inference/                # 推理引擎 (model_dispatcher.py, predictor.py)
│   │   ├── feature_engine/           # 特征工程处理器
│   │   ├── dataset/                  # 数据集生成和标签管理
│   │   └── engine.py                 # 向后兼容层 (ModelDispatcher)
│   └── config/                       # 配置模块 (league/, utils/)
├── config/                           # 配置文件
│   ├── active_registry.json          # NetworkShield 节点配置 (22节点)
│   └── schema_map.yaml               # Schema 韧性配置 (数据源 API 路径映射)
├── model_zoo/                        # 模型存储 (禁止手动修改)
│   ├── league_specific/              # 联赛专项模型
│   └── generic/                      # 通用模型
├── tests/                            # 测试套件
├── scripts/ops/                      # 运维工具
├── main.py                           # V144.7 统一命令入口
├── production_fire.py                # 一键数据采集入口
├── Makefile                          # 统一命令入口
└── ruff.toml                         # 代码质量配置 (line-length: 100)
```

### 关键架构模式

| 模式 | 实现位置 | 用途 |
|------|----------|------|
| **熔断器模式** | `match_engine/shared/circuit_breaker.py` | 连续失败2次后自动屏蔽，15分钟冷却恢复 |
| **队列驱动架构** | `harvester_service.py` | match_search_queue，生产者-消费者模式 |
| **Session 绑定** | `NetworkShield` | 一个会话=一个IP，确保请求一致性 |
| **双模提取** | `QuantHarvester.js` | 网络拦截（首选）→ 20秒超时后DOM抓取（回退） |
| **多模型共识** | `MultiModelValidator` | 3模型并发 + 2/3一致性验证 |
| **PythonBridge** | `src/infrastructure/engines/` | Node.js ↔ Python 无缝桥接 |

---

## 🧬 QuantHarvester V171.001 - Integrated Harvester

**QuantHarvester V171.001** 是最新的 JavaScript 数据收割引擎，集成 **NetworkShield V1.1.0** 工业级代理管理系统和 **MultiModelValidator** 多模型共识验证，专门用于从 OddsPortal 采集高价值赔率数据。

### 核心特性

| 特性 | 说明 |
|------|------|
| **双模提取** | 网络拦截（首选）→ 20秒超时后 DOM 抓取（回退） |
| **NetworkShield 集成** | 22节点工业级代理管理，Session 绑定 |
| **MultiModelValidator** | 3 模型并发 + 2/3 一致性验证 |
| **FundamentalHarvester** | 首发阵容 + 伤停名单 + 球队身价 |
| **PythonBridge** | Node.js ↔ Python 无缝桥接 |
| **GoldenDataMerger** | L1/L2/L3 数据融合 + 异常检测 |

### 使用方式

```bash
# 基本用法（自动使用 NetworkShield）
node src/infrastructure/engines/QuantHarvester.js

# 禁用代理
PROXY_ENABLED=false node src/infrastructure/engines/QuantHarvester.js

# V171 一键部署验证
./scripts/ops/verify_deployment.sh && node scripts/ops/v171_real_fire.js
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

**Match Engine** 是 Python 基础收割引擎架构，位于 `src/infrastructure/engines/match_engine/`，提供统一的数据采集基础框架。

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **BaseHarvestEngine** | `match_engine/base/base_harvest_engine.py` | 基础收割引擎抽象类 |
| **CircuitBreaker** | `match_engine/shared/circuit_breaker.py` | 熔断器模式实现 |
| **NetworkGuardian** | `match_engine/shared/network_guardian.py` | NetworkShield 适配器 |
| **DynamicDiscoveryEngine** | `match_engine/discovery/dynamic_discovery_engine.py` | 动态比赛发现引擎 |
| **FotMobEngine** | `match_engine/fotmob/fotmob_engine.py` | FotMob 数据采集 |

### 使用方式

```python
from src.infrastructure.engines.match_engine.fotmob import FotMobEngine

engine = FotMobEngine()
matches = await engine.discover_matches(league_id=47, season="2324")
```

---

## 🔧 开发指南

### 🚨 核心约束（红线）

| 约束 | 说明 | 违反后果 |
|------|------|----------|
| **单数据库准则** | `DB_NAME=football_db`，禁止创建其他数据库 | 连接失败 |
| **禁止绕过 FotMobCoreCollector** | 所有 FotMob 采集必须走 `src/api/collectors/fotmob_core.py` | 数据不一致 |
| **禁止修改 model_zoo/** | 模型只能通过训练流程更新 | 模型损坏 |
| **禁止版本类文件** | 不创建 `*_v2.py`、`*_new.py`、`*_backup.py`，直接修改原文件 | 代码腐烂 |
| **禁止分支创建** | 除非用户明确要求，所有变更直接提交 main 分支 | 工作流混乱 |
| **禁止创建 Git Tag** | Tag 由用户手动输入指令创建 | 版本混乱 |
| **容器化优先** | 所有开发、测试、依赖安装必须在 Docker 容器内 | 污染宿主机 |

### 配置文件优先级

| 配置文件 | 作用 | 优先级 |
|----------|------|--------|
| `ruff.toml` | 代码质量配置 (**line-length: 100**) | **最高** |
| `config/active_registry.json` | NetworkShield 22 节点配置 | 高 |
| `config/schema_map.yaml` | Schema 韧性配置（数据源 API 路径映射） | 高 |
| `.env` | 环境变量（数据库、Redis 连接） | 高 |
| `pyproject.toml` | 项目元数据和依赖（line-length: 120，被 ruff.toml 覆盖） | 备用 |

### 代码质量规范

**提交前必须运行**: `make verify` (lint + test-unit + security)

**关键规则**: `ruff.toml` (line-length: **100**) 优先级高于 `pyproject.toml` (line-length: 120)

```bash
# 完整质量检查流程
ruff format src/ tests/    # 格式化代码
ruff check src/ tests/     # Lint 检查
mypy src/                  # 类型检查
bandit -r src/             # 安全扫描
make verify                # 提交前完整验证
```

### 测试运行方法

```bash
# 日常快速反馈
make test-unit

# 单文件测试
pytest tests/unit/test_config.py -v

# 单用例测试
pytest tests/unit/test_config.py::TestConfig::test_database_config -v

# 关键词匹配
pytest -k "test_database" -v

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing

# 调试模式（显示打印 + 失败时进入调试器）
pytest tests/unit/test_config.py -v -s --pdb
```

### 环境变量配置

```bash
# 最小配置（复制模板后编辑）
cp .env.example .env

# 关键变量
DB_HOST=db                  # Docker 环境
DB_HOST=172.25.16.1         # WSL2 环境
DB_NAME=football_db         # 必须为 football_db（禁止修改）
DB_PASSWORD=your_password   # 必需设置
```

### Git 工作流

```bash
# 检查当前分支（应为 main）
git status

# 提交流程
make verify                                  # 提交前质量检查
git add <specific_files>                     # 添加指定文件
git commit -m "feat: 添加 XXX 功能"          # 提交 (feat|fix|docs|refactor|test|chore)

# 禁止操作
# ❌ git checkout -b feature/xxx  （除非用户明确要求）
# ❌ git tag v1.0.0               （Tag 由用户手动创建）
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
python production_fire.py    # 一键数据采集入口（GoldenDataMerger + NetworkShield）
```

### ML 预测接口 (V26.8)

```python
# 推理入口（推荐）
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"
)
# 返回: {'home_win_prob': 0.45, 'draw_prob': 0.28, 'away_win_prob': 0.27}
```

### ML 训练工作流

```python
# 训练入口
from src.ml.training.v17_engine import V17MLEngine

engine = V17MLEngine()
# 1. 数据集生成
dataset = engine.generate_dataset(league_filter="Premier League")
# 2. 特征工程
features = engine.extract_features(dataset)
# 3. 模型训练
model = engine.train(features, target="result")
# 4. 模型保存到 model_zoo/league_specific/
```

### 特征工程 - V41.500 自动化特征工厂

```python
from src.processors.feature_factory import get_feature_factory

factory = get_feature_factory()
features = factory.process_match(match_data)
# 输出特征类别：
# - 疲劳度: home_rest_days, away_is_busy_week, diff_rest_days
# - 缺阵: home_unavailable_total_count, home_unavailable_star_count
# - 首发战力: home_starter_avg_rating, home_missing_stars_count
# - 赔率动向: home_drop_ratio, total_movement
# - 联赛等级: is_top_5_league
```

### 配置文件更新（数据源变动时）

当数据源 API 结构变化时，只需更新 `config/schema_map.yaml`，无需修改代码：

```yaml
# 示例：添加新的数据源路径
fotmob:
  match_data:
    path: "data.match"
    home_team: "teams.home.name"
    unavailable: "teams.home.unavailable_list"
```

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

```bash
# 快速反馈（推荐日常使用）
make test-unit

# 提交前验证
make verify

# V41.500 端到端测试
pytest tests/ai/test_v41_500_pipeline.py -v

# JavaScript 测试
cd scripts/ops && npm test
```

---

## 🐛 常见错误速查表

> 💡 **详细故障排除**: [docs/troubleshooting.md](docs/troubleshooting.md)

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `database "football_db" does not exist` | 数据库未初始化 | `make up` |
| `ConnectionRefusedError: 5432` | 数据库未启动 | `make up` |
| `ModuleNotFoundError: No module named 'src'` | Python 路径问题 | 在项目根目录运行 |
| `Timeout 30000ms exceeded` | 网络慢/代理问题 | 检查代理配置或运行 `python main.py --test-proxy` |
| `HTTP 429/403` | IP 限流/封禁 | 等待 6-24h 或启用 NetworkShield 代理轮换 |
| `NetworkShield: No healthy nodes` | 所有代理节点不可用 | 检查 `config/active_registry.json` 或运行健康检查 |
| `Playwright browser not found` | 浏览器未安装 | `playwright install chromium` |
| `WSL2 无法连接 Docker` | 网桥 IP 问题 | `ping 172.25.16.1` 或 `wsl --shutdown` 重启 |

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

本项目采用**多版本号体系**，各组件独立演进，互不影响：

| 版本前缀 | 组件范围 | 当前版本 | 主要职责 |
|----------|----------|----------|----------|
| `V171.x` | QuantHarvester + Multi-Model Consensus | V171.001 | JavaScript 数据收割引擎 + 多模型共识验证 |
| `V144.x` | 多数据源命令中心 | V144.9 | main.py 统一命令入口 |
| `V41.x` | 数据采集运维工具 | V41.832 | GoldenExtractor 特征提取 + 自动化特征工厂 |
| `V26.x` | ML 特征引擎和模型 | V26.8 | ModelDispatcher + XGBoost 预测模型 |
| `V1.x` | NetworkShield 代理管理 | V1.1.0 | 22节点工业级代理池 + 熔断器 |

> **重要**: 各组件版本独立演进，互不影响。修改 ML 模型不会影响 QuantHarvester 版本号。

---

## 📚 延伸阅读

| 文档 | 内容 | 预计阅读时间 |
|------|------|--------------|
| [docs/onboarding.md](docs/onboarding.md) | 新开发者快速上手指南 | 30 分钟 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 故障排除完整指南 | 20 分钟 |
| [docs/CLAUDE_JS_TOOLS.md](docs/CLAUDE_JS_TOOLS.md) | JavaScript 运维工具完整参考 | 45 分钟 |
| [README.md](README.md) | 项目概览和 V171 特性介绍 | 15 分钟 |

---

**生产状态**: ✅ Production Ready | **Python**: 3.11+ | **Node.js**: 18+ | **最后更新**: 2026-02-24
