# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📚 文档导航

**推荐阅读顺序**：
1. **docs/onboarding.md** - 新开发者快速上手指南（30分钟）
2. **本文档** (CLAUDE.md) - 完整项目文档和开发指南
3. **docs/troubleshooting.md** - 故障排除指南
4. **README.md** - 项目概览和快速开始
5. **docs/RELEASE_V144_9.md** - 最新版本发布说明

**按角色阅读**：
- **新开发者**: onboarding.md → CLAUDE.md（快速开始章节）
- **数据采集工程师**: CLAUDE.md（数据采集系统章节）
- **机器学习工程师**: CLAUDE.md（ML 引擎章节）
- **运维工程师**: CLAUDE.md（Docker 部署章节）+ troubleshooting.md

---

## 🎯 常见任务快速索引

**我想...** | **使用命令**
---|---
🚀 启动开发环境 | `make up`
🧪 运行代码质量检查 | `make verify`
📊 采集单场比赛数据 | `python main.py --source fotmob --mode single --limit 1`
🔄 24h 全自动巡航 | `python main.py --mode cruise`
🔍 检查代理连通性 | `python main.py --test-proxy`
🗄️ 进入数据库 | `make db-shell`
📈 查看系统日志 | `make logs`
🧹 清理临时文件 | `make clean`
🚢 部署到生产 | `make deploy`
⚡ 运行性能测试 | `pytest -m performance -v --benchmark-only`
🔧 验证 Node.js 环境 | `node --version && npm --version`
🧪 运行 Jest 测试 | `cd scripts/ops && npm test`
🧪 运行 Jest 覆盖率 | `cd scripts/ops && npm run test:coverage`
🚀 运行 Master Pipeline | `node scripts/ops/v87_master_pipeline.js`
⚡ 运行 Turbo Harvest | `node scripts/ops/v86_turbo_harvest.js`

---

## ⚡ 超快速索引（最常用命令）

| 任务 | 命令 |
|------|------|
| 启动服务 | `make up` |
| 质量检查 | `make verify` |
| 采集数据 | `python main.py --source fotmob --mode single --limit 10` |
| 进入数据库 | `make db-shell` |
| 查看日志 | `make logs` |

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **项目版本** | **V26.7.0** (pyproject.toml) |
| **生产版本** | **V69.000** (Pipeline Orchestrator - The Master Switch) |
| **命令中心** | **V144.9** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) |
| **特征提取** | **V41.380** (GoldenExtractor - 市场价值/缺阵/评分) |
| **JavaScript 运维** | **V66.000** (收割引擎) / V69.000 (Pipeline) |
| **Master Pipeline** | **V87.203** (全量收割系统 - Jest 测试) / V86 (Master Harvest) |
| **数据同步** | **V36.3** (auto_sync_and_alchemy_v2.sh) |
| **代码质量** | **V106.0** (Ruff 配置 - line-length: 100) |
| **Docker 版本** | **V51.0** (Industrial Grade Ready) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-27 |

### 版本号体系说明

本项目采用**多版本号体系**，各组件独立演进：

| 版本前缀 | 组件范围 | 当前版本 |
|----------|----------|----------|
| `V26.x` | ML 特征引擎和模型 | V26.8 |
| `V36.x` | 数据同步和自动化 | V36.3 |
| `V41.x` | 数据采集运维工具 | V41.832 |
| `V48.x` | JavaScript 任务调度 | V48.100 |
| `V49.x` | JavaScript 时间同步引擎 | V49.000 |
| `V51.x` | Docker 部署 | V51.0 |
| `V66.x` | JavaScript 数据收割引擎 | V66.000 |
| `V69.x` | Pipeline 编排器 | V69.000 |
| `V70.x` | 数据质量门禁 | V70.200 |
| `V84.x` | JavaScript 诊断和测试工具 | V84.910 |
| `V85.x` | JavaScript 视觉提取引擎 | V85.000 |
| `V106.x` | 代码质量配置 | V106.0 |
| `V144.x` | 多数据源命令中心 | V144.9 |
| `V151.x` | 并发收割和哈希狩猎 | V151.3 |
| `V86.x` | JavaScript Master Harvest | V86 (Master/Turbo Harvest) |
| `V87.x` | JavaScript Master Pipeline | V87.203 (全量收割 + Jest 测试) |

> **注意**: 项目版本 (`V26.7.0`) 与组件版本是独立的，项目版本主要用于 Python 包管理。

---

## 🔑 关键概念

理解以下核心概念对于开发和使用本系统至关重要：

### Ghost Protocol (V141.0)
反爬虫检测基础能力，通过模拟真实用户行为规避检测：
- **30+ 浏览器指纹池**：随机选择 Chrome/Edge/Safari/Firefox 用户代理
- **人类行为模拟**：随机滚动、点击噪声、延迟等待
- **深度拦截检测**：识别 Cloudflare、IP 封禁等反爬措施

### Golden Shield (V41.287)
数据质量评级系统，评估采集数据的完整性：
- **EXCELLENT**：≥100维特征 + 4项核心指标 (xG, Shots, Possession, Corners)
- **GOOD**：≥80维特征 + 3项核心指标
- **FAIR**：≥50维特征 + 2项核心指标
- **POOR**：<50维特征 或 <2项核心指标

### 三位一体样本 (Perfect Samples)
同时具备以下三种数据的高质量样本：
1. **Odds**：赔率数据 (开盘/终盘/时间序列)
2. **Lineups**：阵容数据 (首发/替补/阵型)
3. **Features**：技术特征 (6000+ 维深度特征)

当前系统拥有 **1,770** 个三位一体样本。

### Schema Map (V41.500+)
配置化的数据源适配机制，当数据源 API 结构变化时：
- 只需更新 `config/schema_map.yaml` 配置文件
- 无需修改代码即可适配新的数据结构
- 提供路径解析器 (PathResolver) 安全访问嵌套字段

### Pipeline 状态流转 (V69.000)
全链路自动化数据流转：
```
DISCOVERED → ENRICHED → MAPPED → HARVESTED
   (初始)    (L2采集)   (哈希对齐)  (赔率收割)
```

---

## 📈 版本演进概览

项目采用严格的版本管理体系，各主要组件版本独立演进：

### 最新版本发布：V41.832 工业级归档收割机 (Production Blueprint)

**说明**: V41.832 是一个工业级重构蓝图，将单文件脚本重构为模块化架构

| 特性 | 说明 |
|------|------|
| **物理点击机制** | Playwright 精确定位分页按钮，解决 Vue.js 动态加载问题 |
| **内容锁设计** | 等待页面内容完全填充后再提取，拒绝零场成功 |
| **事务自愈逻辑** | 每场比赛独立 try-except 包裹，execute 报错立即 rollback |
| **模块化架构** | 5 个独立模块 (harvesters, parsers, database_inserter, browser_helper, config) |
| **16/16 测试通过** | 完整的单元测试覆盖，支持英超/西甲/意甲/德甲/法甲 |
| **100% Type Hints** | 完整的类型注解覆盖 |
| **Google Style Docstrings** | 标准化的文档字符串 |

**详细文档**: `docs/MR_V41.832_production_blueprint.md`

**五大联赛总攻计划**:
- ✅ **英超**: 完成 (2024/2025 赛季已收割 380 场)
- 🚀 **西甲**: V41.840 系列 (计划中)
- 🚀 **意甲**: V41.850 系列 (计划中)
- 🚀 **德甲**: V41.860 系列 (计划中)
- 🚀 **法甲**: V41.870 系列 (计划中)

### 核心组件版本系列

| 组件 | 版本系列 | 说明 |
|------|----------|------|
| **数据采集** | V41.x | Python 运维工具和采集器 (V41.832 最新) |
| **JavaScript 运维** | V48.x / V49.x / V85.x | Node.js 时间同步引擎 (V49.000 / V85.000 最新) |
| **JavaScript 诊断** | V84.x | 诊断和测试工具集 (V84.910 最新) |
| **命令中心** | V144.x | 统一入口和数据源路由 (V144.9 最新) |
| **预测模型** | V26.x | 特征引擎和模型训练 (V26.8 最新) |
| **收割服务** | V142.x | 统一收割服务架构 (V142.0 最新) |
| **Ghost Protocol** | V141.x | 反爬检测基础能力 (V141.0 最新) |
| **特征工厂** | V41.500+ | 自动化特征提取引擎 (V41.500 最新) |
| **代码质量** | V106.0 | Ruff 配置 (line-length: 100) |

### 关键里程碑

- **V85.000** (2026-01): Visual-First Extraction - 视觉优先提取引擎（Logo-based detection + 悬停取证）
- **V84.910** (2026-01): Deep Extractor - 深度数据提取工具
- **V84.x 系列** (2026-01): 诊断和测试工具集（金丝雀测试、综合诊断、悬停诊断、API 突击测试）
- **V69.000** (2026-01): Pipeline Orchestrator - The Master Switch (全链路自动化状态流转)
- **V70.200** (2026-01): Data Sentinel - 质量门禁与完整性扫描
- **V66.000** (2026-01): JavaScript Harvest Engine - 5 Providers × 3 Dimensions
- **V49.000** (2026-01): Full-Spectrum Temporal Sync Engine - 全量三维时间序列提取 (Home/Draw/Away)
- **V48.100** (2026-01): URL Reconnaissance - OddsPortal URL 自动化寻址
- **V48.000** (2026-01): The Task Pump - 自动化任务调度与收割
- **V43.200** (2026-01): Interaction/Storage Modules - Playwright 交互与 PostgreSQL 存储
- **V41.832** (2026-01): 工业级归档收割机 - 物理分页、内容锁与事务自愈
- **V41.510** (2026-01): Automated Feature Factory Integration - Production Ready
- **V144.9** (2026-01): Multi-Source Command Center - Final Baseline
- **V36.3** (2026-01): auto_sync_and_alchemy_v2.sh - 数据链路全自动闭环
- **V26.8** (2024-11): 联赛专项模型自动分发器

### 版本文档

详细版本变更记录位于 `docs/V*.md` 文件中，每个版本都有对应的验收报告和技术规范。

---

## ⚡ 快速开始

### 3 分钟上手（4 步）

```bash
# 1. 验证 Git 分支（开发前检查）
git status                    # 确认当前分支和工作区状态

# 2. 启动核心服务
make up

# 3. 验证环境并采集测试数据
python main.py --source fotmob --mode single --limit 1

# 4. 检查代码质量（提交前必需）
make verify
```

### 展开说明

**详细命令列表和更多选项，请参考下方的"核心开发命令速查表"。**

---

### 核心开发命令速查表

| 类别 | 命令 | 说明 |
|------|------|------|
| **环境管理** | `make up` | 启动核心服务 (db + redis) |
| | `make up-pipeline` | 启动核心服务 + 数据流水线 |
| | `make up-api` | 启动核心服务 + API |
| | `make up-dev` | 启动开发环境 (含管理工具) |
| | `make up-all` | 启动所有服务 |
| | `make down` | 停止所有服务 |
| | `make ps` | 查看容器状态 |
| | `make logs` | 查看核心服务日志 |
| | `make logs-api` | 查看 API 日志 |
| | `make logs-all` | 查看所有服务日志 |
| | `make restart` | 重启核心服务 |
| **数据采集** | `python main.py --source fotmob --mode single --limit 10` | FotMob API 数据源 |
| | `python main.py --source oddsportal --mode single --limit 10` | OddsPortal RPA 数据源 |
| | `python main.py --mode cruise` | 24h 全自动巡航 |
| | `python main.py --test-proxy` | 测试代理连通性 |
| **测试** | `make test-unit` | 运行核心测试套件（ML + 运维，2 个文件） |
| | `make test` | 运行完整测试门禁（7 步检查） |
| | `pytest tests/unit/ -v` | 运行单元测试目录（80+ 个文件） |
| | `pytest tests/ -v` | 运行所有测试 |
| | `pytest tests/path/to/test_file.py -v` | 运行单个测试文件 |
| | `pytest tests/ -k "keyword" -v` | 运行匹配关键字的测试 |
| **代码质量** | `make verify` | 快速验证 (lint + test-unit + security) |
| | `make lint` | 运行 Lint 检查 |
| | `make format` | 格式化代码 |
| | `make security` | 运行安全扫描 |
| **数据库** | `make db-shell` | 进入 PostgreSQL Shell |
| | `make db-backup` | 备份数据库到 data/backups/ |
| | `make db-reset` | 重置数据库（危险！） |
| **Redis** | `make redis-shell` | 进入 Redis CLI |
| **构建** | `make build` | 构建生产镜像 |
| | `make build-no-cache` | 无缓存构建 |
| **清理** | `make clean` | 清理垃圾文件、缓存 |
| | `make clean-csv` | 清理临时测试 CSV 文件 |
| | `make clean-logs` | 清理超过 7 天的日志文件 |
| | `make clean-docker` | 清理 Docker 资源 |
| | `make clean-all` | 完全清理（包括临时文件和日志） |
| **部署** | `make deploy` | 部署到生产环境 |
| **监控** | `make health` | 检查服务健康状态 |
| | `make dashboard` | 启动战神仪表盘 |
| **高级测试** | `pytest tests/integration/ -v` | 运行集成测试 |
| | `pytest tests/e2e/ -v` | 运行端到端测试 |
| | `pytest tests/ -k "keyword" -v` | 运行匹配关键字的测试 |

> **注意**: `make verify` 执行 3 步检查（lint + test-unit + security），适合本地开发快速反馈。完整质量门禁（7 步）使用 `./scripts/run_checks.sh`。

### 数据库统计查询

```bash
# 进入数据库 Shell
make db-shell

# 查看数据采集统计
SELECT source_name, COUNT(*) as total_records
FROM metrics_multi_source_data
GROUP BY source_name;

# 查看赛季覆盖情况
SELECT m.season, m.league_name, COUNT(DISTINCT m.match_id) as total_matches
FROM matches m
GROUP BY m.season, m.league_name
ORDER BY m.season DESC;
```

### 命令详解

#### 环境管理
```bash
make up                  # 启动核心服务 (db + redis)
make up-pipeline         # 启动核心服务 + 数据流水线
make up-api              # 启动核心服务 + API
make up-dev              # 启动开发环境 (含管理工具)
make down                # 停止所有服务
make ps                  # 查看容器状态
```

#### 代码质量
```bash
make verify              # 快速验证 (lint + test-unit + security)
./scripts/run_checks.sh  # 完整质量门禁（7 步检查）
ruff format src/ tests/  # 格式化代码
ruff check src/ tests/   # Lint 检查
```

#### 测试
```bash
# 单元测试
pytest tests/unit/test_config.py -v                     # 运行单个测试文件
pytest tests/unit/test_config.py::test_database_config -v  # 运行单个测试函数
pytest tests/ -k "test_database" -v                     # 运行匹配关键字的测试

# 按标记运行测试
pytest -m unit -v           # 只运行单元测试
pytest -m integration -v    # 只运行集成测试
pytest -m "not network" -v  # 排除网络测试

# 覆盖率报告
pytest tests/ --cov=src --cov-report=html              # 生成 HTML 覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing      # 终端显示缺失行
```

#### JavaScript 测试 (Jest)
```bash
# 进入 ops 目录
cd scripts/ops

# 运行 Jest 测试 (V87.203)
npm test                       # 运行所有测试
npm run test:watch             # 监视模式
npm run test:coverage          # 生成覆盖率报告
npm run test:verbose           # 详细输出

# 运行特定测试文件
npx jest tests/interaction_v52.test.js
npx jest tests/orchestrator.test.js

# 安装依赖 (首次运行)
npm install
```

---

## 🏗️ 系统架构

### 简化数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│  数据采集层                                                      │
│  FotMob API (L2数据) + OddsPortal RPA (赔率数据)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  特征工程层                                                      │
│  GoldenExtractor (V41.380) + Feature Factory (V41.500+)        │
│  → 市场价值/缺阵/评分/疲劳度等 6000+ 维特征                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据持久层                                                      │
│  PostgreSQL (matches + metrics_multi_source_data)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  预测引擎层                                                      │
│  ModelDispatcher (V26.8) → XGBoost 预测                        │
└─────────────────────────────────────────────────────────────────┘
```

### V144.7 Multi-Source Command Center 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    main.py - V144.7 统一入口                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  数据源路由 (--source):                                     │ │
│  │  • oddsportal: OddsPortal RPA 采集 (V144.2)               │ │
│  │  • fotmob: FotMob API 采集 (V144.5)                       │ │
│  │                                                            │ │
│  │  运行模式 (--mode):                                        │ │
│  │  • single: 单次收割 (指定联赛/赛季)                        │ │
│  │  • cruise: 24h 全自动巡航                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    HarvesterService (V142.0)                     │
│  队列驱动架构 + Ghost Protocol + 全路径试错匹配                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BaseExtractor (V141.0)                        │
│  Ghost Protocol - 30+ 浏览器指纹池 + 人类行为模拟                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    PostgreSQL 持久层
              matches 表 + metrics_multi_source_data 表
```

### 核心目录结构（简化版）

```
FootballPrediction/
├── src/                              # 生产代码
│   ├── api/                          # API 层
│   │   ├── collectors/               # 数据采集器 (V141.0/V142.0)
│   │   │   ├── base_extractor.py     # V141.0 Ghost Protocol 基类
│   │   │   ├── fotmob_core.py        # FotMob API 采集
│   │   │   └── odds_production_extractor.py  # 赔率提取
│   │   └── services/                 # 业务服务层
│   │       └── harvester_service.py  # V142.0 统一收割服务
│   ├── config_unified.py             # V26.0 统一配置管理
│   ├── core/                         # V105.0 核心基础设施
│   ├── harvesters/                   # V41.832 工业级收割机 ⭐ (蓝图阶段)
│   ├── parsers/                      # V41.832 数据解析器 ⭐ (蓝图阶段)
│   ├── ml/                           # ML 引擎
│   │   └── engine.py                 # XGBoost 引擎 + ModelDispatcher
│   ├── processors/                   # V25.1 特征提取
│   ├── utils/                        # 工具类
│   └── config/                       # 配置模块
├── scripts/                          # 核心脚本
│   ├── ops/                          # V41.x 系列运维工具
│   ├── maintenance/                  # 维护脚本
│   └── run_checks.sh                 # CI 质量门禁
├── tests/                            # 测试套件
│   ├── harvesters/                   # V41.832 收割机测试 ⭐
│   ├── unit/                         # 单元测试
│   └── integration/                  # 集成测试
├── config/                           # 配置文件
├── model_zoo/                        # 模型仓库
├── main.py                           # V144.7 统一命令入口 ⭐
├── Makefile                          # 统一命令入口
├── requirements.txt                  # 生产依赖
├── pyproject.toml                    # Poetry 配置
├── ruff.toml                         # V106.0 Ruff 配置
└── CLAUDE.md                         # 本文件
```

> **提示**: 使用 `tree -L 2 -I '__pycache__|*.pyc'` 查看完整目录结构

---

## 🔧 开发指南

### 核心文件优先级

当需要修改功能时，按以下优先级选择文件：

| 优先级 | 文件类型 | 说明 | 示例 |
|--------|----------|------|------|
| **1** | 配置文件 | 优先修改配置，无需改动代码 | `config/schema_map.yaml`, `config/global_harvest_list.yaml` |
| **2** | 处理器 | 特征提取、数据处理的业务逻辑 | `src/processors/*.py` |
| **3** | 服务层 | 业务服务协调器 | `src/api/services/*.py` |
| **4** | 采集器 | 数据采集逻辑 | `src/api/collectors/*.py` |
| **5** | 核心模块 | 基础设施，修改需谨慎 | `src/core/*.py`, `src/config_unified.py` |

**禁止修改的文件**:
- `model_zoo/` 中的模型文件（使用备份恢复）
- 已废弃的版本类文件（`*_v2.py`, `*_new.py`, `*_backup.py`）

### Git 工作流

**标准提交流程**:
```bash
# 1. 确认当前分支
git status

# 2. 创建功能分支（推荐）
git checkout -b feature/your-feature-name

# 3. 进行代码修改
# ... 编辑文件 ...

# 4. 提交前质量检查
make verify

# 5. 添加变更文件
git add src/path/to/your_file.py
git add tests/path/to/test_file.py

# 6. 提交变更
git commit -m "feat: 添加 XXX 功能

- 实现了 XXX 特性
- 添加了对应的单元测试
- 通过了 make verify 验证"

# 7. 推送到远程
git push origin feature/your-feature-name

# 8. 创建 Pull Request（如果使用 GitHub/GitLab）
```

**提交消息规范**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```bash
git commit -m "feat(processors): 添加疲劳度特征计算"
git commit -m "fix(collectors): 修复 FotMob API 429 错误处理"
git commit -m "docs(claude): 更新 V41.832 蓝图状态说明"
```

### 配置管理

使用 `src.config_unified.get_settings()` 获取配置：

```python
from src.config_unified import get_settings

settings = get_settings()
# 访问配置
db_host = settings.database.host
db_name = settings.database.name
```

#### 配置文件说明 (config/ 目录)

| 文件 | 用途 |
|------|------|
| `.env` | 环境变量配置（数据库、Redis、代理等） |
| `leagues.yaml` | 联赛配置（tier 分级、名称映射） |
| `global_harvest_list.yaml` | 全球联赛注册表 |
| `titan_config.yaml` | 统一代理和联赛配置 |
| `harvester_v2.yaml` | 收割器配置 |
| `schema_map.yaml` | V41.500+ JSON 路径配置（数据源变动适配） |

#### 环境变量配置 (.env)

必需的环境变量（首次运行前需配置）：

```bash
# 数据库配置
DB_HOST=              # 数据库主机 (Docker: db, WSL2: 172.25.16.1, 本地: localhost)
DB_PORT=5432
DB_NAME=football_db   # 唯一合法值 (强制)
DB_USER=football_user
DB_PASSWORD=your_password

# Redis 配置
REDIS_HOST=           # Redis 主机
REDIS_PORT=6379
REDIS_PASSWORD=

# 代理配置（可选）
HTTP_PROXY=           # HTTP 代理 URL
HTTPS_PROXY=          # HTTPS 代理 URL

# API 限流配置
COLLECTION_PAUSE_UNTIL=   # ISO 格式时间戳，API 限流暂停结束时间
```

> **注意**: `DB_NAME` 必须为 `football_db`，系统强制单数据库准则防止环境偏差。

#### 环境智能检测 (V41.59)

系统通过 `src.core.environment_detector` 自动检测运行环境：

| 环境 | `DB_HOST` | 检测方式 |
|------|-----------|----------|
| **Docker** | `db` | 检测 `DOCKER_ENV` 环境变量 |
| **WSL2 本地** | `172.25.16.1` | 检测 `/proc/version` 包含 "microsoft" |
| **本地开发** | `localhost` | 默认环境 |

**数据库连接池配置** (V41.49):
```python
# 支持高并发连接池
pool_size: int = 15           # 基础连接数
max_overflow: int = 20        # 最大溢出数 (理论最大 35)
pool_timeout: int = 10        # 连接超时 (秒)
pool_recycle: int = 600       # 连接回收时间 (10分钟)
```

#### WSL2 代理自动发现

BaseExtractor 支持自动发现 WSL2 环境下的代理配置：
```python
from src.api.collectors.base_extractor import BaseExtractor

extractor = BaseExtractor(auto_proxy=True)
# 自动检测环境变量或 WSL2 桥接网关
proxy_config = extractor.get_proxy_config()
```

#### 单数据库准则 (V41.51)

系统强制只允许连接 `football_db` 数据库，防止环境偏差：
```python
# 违规会抛出 DatabaseConfigurationError
# DB_NAME=football_db  # 唯一合法值
```

### 数据库连接标准

```python
from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor  # 返回字典而非元组
)
```

### 核心数据库表

**matches 表** (Source_F - 比赛基础信息)
```sql
match_id VARCHAR(50) PRIMARY KEY
league_name VARCHAR(255)
season VARCHAR(20)
home_team VARCHAR(255)
away_team VARCHAR(255)
match_time TIMESTAMP
technical_features JSONB      -- 152 维技术特征
l2_raw_json JSONB            -- FotMob L2 原始数据
l3_extraction_status VARCHAR(20) -- V36.1 特征提取状态
```

**matches_mapping 表** (哈希对齐)
```sql
fotmob_id VARCHAR(50) REFERENCES matches(match_id)
oddsportal_hash VARCHAR(8)
oddsportal_url TEXT
match_date TIMESTAMP
mapping_method VARCHAR(50)
confidence FLOAT
review_status VARCHAR(20)
```

**metrics_multi_source_data 表** (赔率数据)
```sql
match_id VARCHAR(50) REFERENCES matches(match_id)
source_name VARCHAR(50)      -- Entity_P (Pinnacle)
init_h/d/a FLOAT             -- 开盘赔率
final_h/d/a FLOAT            -- 终盘赔率
integrity_score FLOAT        -- 完整性分数
```

### 常用 SQL 查询

```sql
-- 查看数据采集统计
SELECT
    source_name,
    COUNT(*) as total_records,
    COUNT(opening_time_h) as with_opening_time,
    ROUND(100.0 * COUNT(opening_time_h) / COUNT(*), 2) as success_rate
FROM metrics_multi_source_data
GROUP BY source_name;

-- 查看赛季覆盖情况
SELECT
    m.season,
    m.league_name,
    COUNT(DISTINCT m.match_id) as total_matches,
    COUNT(DISTINCT CASE WHEN msd.opening_time_h IS NOT NULL THEN m.match_id END) as with_pinnacle_data
FROM matches m
LEFT JOIN metrics_multi_source_data msd
    ON m.match_id = msd.match_id
    AND msd.source_name = 'Entity_P'
GROUP BY m.season, m.league_name
ORDER BY m.season DESC;

-- 检查数据完整性评分分布
SELECT
    CASE
        WHEN integrity_score < 1.02 THEN 'Too Low'
        WHEN integrity_score > 1.08 THEN 'Too High'
        ELSE 'Valid'
    END as score_category,
    COUNT(*) as count,
    ROUND(AVG(integrity_score), 4) as avg_score
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P'
    AND integrity_score IS NOT NULL
GROUP BY score_category;
```

### 代码质量规范

**提交前必须运行**:
```bash
make verify  # 快速验证 (lint + test-unit + security)
```

**工具配置**:
- **Ruff (V106.0)**: `ruff.toml` - **主代码质量工具（优先使用）**
  - `line-length`: **100 字符**（主要配置）
  - `target-version`: Python 3.11
  - 规则集: E, W, F, I, N, UP, B, C4, DTZ, T10, EM, ISC, ICN, G, PIE, T20, PT, Q, RSE, RET, SIM, TID, TCH, ARG, PTH, ERA, PL, TRY, FLY, PERF, RUF
  - McCabe 复杂度阈值: 15
- **pyproject.toml**: 备用配置 (line-length: 120，仅在 ruff.toml 不可用时使用)

> **注意**: 当 ruff.toml 和 pyproject.toml 同时存在时，**ruff.toml 的 100 字符限制优先**。pyproject.toml 的 120 字符配置仅为备用。

**推荐的代码质量工作流**：
```bash
# 1. 格式化代码（主要工具）
ruff format src/ tests/

# 2. Lint 检查（主要工具）
ruff check src/ tests/

# 3. 自动修复
ruff check src/ tests/ --fix

# 4. 类型检查
mypy src/

# 5. 安全扫描
bandit -r src/
```

**工具优先级**：
| 工具 | 优先级 | 用途 |
|------|--------|------|
| **Ruff** | 🔴 主要 | 格式化 + Lint (ruff.toml) |
| **MyPy** | 🟡 推荐 | 类型检查 |
| **Bandit** | 🟡 推荐 | 安全扫描 |

### 测试场景选择指南

根据不同开发场景选择合适的测试命令：

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| **本地开发快速反馈** | `make test-unit` | 只运行核心测试套件（ML + 运维，2 个文件） |
| **单元测试验证** | `pytest tests/unit/ -v` | 运行单元测试目录（80+ 个测试文件） |
| **JavaScript 测试 (Jest)** | `cd scripts/ops && npm test` | 运行 V87.203 Jest 测试套件 |
| **JavaScript 覆盖率 (Jest)** | `cd scripts/ops && npm run test:coverage` | 生成 Jest 覆盖率报告 |
| **提交前完整验证** | `./scripts/run_checks.sh` | 完整质量门禁（7 步检查） |
| **快速验证** | `make verify` | lint + test-unit + security (3 步) |
| **全量测试（CI 环境）** | `pytest tests/ -v` | 运行所有测试 |
| **调试单个测试文件** | `pytest tests/unit/test_config.py -v` | 聚焦特定文件 |
| **生成覆盖率报告** | `pytest tests/ --cov=src --cov-report=html` | 生成 HTML 覆盖率报告 |
| **运行性能测试** | `pytest -m performance -v --benchmark-only` | 运行性能基准测试（需要 pytest-benchmark） |

**测试目录说明**:
- `tests/unit/` - Python 单元测试（80+ 个测试文件，覆盖配置、采集器、特征工程等）
- `tests/integration/` - 集成测试
- `tests/harvesters/` - V41.832 收割机测试（16 个测试用例）
- `tests/ml/` - ML 引擎测试
- `tests/ops/` - 运维脚本测试
- `tests/e2e/` - 端到端测试
- `scripts/ops/tests/` - JavaScript Jest 测试（V87.203 Master Pipeline 测试套件）

**`make verify` vs `./scripts/run_checks.sh` 的区别**:
- **`make verify`** (快速验证): 执行 3 步检查 - lint + test-unit + security，适合本地开发快速反馈
- **`./scripts/run_checks.sh`** (完整质量门禁): 执行 7 步完整检查，包括导入排序、类型检查、模型性能回归测试等，适合 CI/CD 流水线

**按标记运行测试**:
```bash
# 只运行单元测试
pytest -m unit -v

# 只运行集成测试
pytest -m integration -v

# 排除网络测试
pytest -m "not network" -v

# 运行性能测试
pytest -m performance -v --benchmark-only

# 运行性能测试并生成 JSON 报告
pytest -m performance -v --benchmark-only --benchmark-json=benchmark_report.json

# 运行单个性能测试文件
pytest tests/performance/test_inference_speed.py -v --benchmark-only
```

**可用标记 (markers)**:
- `unit`: 单元测试
- `integration`: 集成测试
- `slow`: 慢速测试
- `network`: 需要网络的测试
- `e2e`: 端到端测试
- `performance`: 性能测试

---

## 🚀 典型开发工作流

### 工作流 1: 添加新特征到数据模型

1. **修改数据模型**
   ```bash
   # 编辑特征提取处理器
   src/ml/feature_engine/processors/your_feature.py
   ```

2. **添加单元测试**
   ```bash
   # 创建测试文件
   tests/ml/test_your_feature.py
   ```

3. **运行质量检查**
   ```bash
   make verify
   ```

4. **提交变更**
   ```bash
   git add src/ml/feature_engine/processors/your_feature.py
   git add tests/ml/test_your_feature.py
   git commit -m "feat: 添加新特征 XXX"
   ```

### 工作流 2: 调试数据采集问题

1. **启用详细日志**
   ```bash
   export LOG_LEVEL=DEBUG
   python main.py --source fotmob --mode single --limit 1
   ```

2. **检查代理状态**
   ```bash
   python main.py --test-proxy
   ```

3. **查看数据库记录**
   ```bash
   make db-shell
   # 在 psql 中运行查询
   SELECT match_id, l2_raw_json IS NOT NULL as has_l2_data FROM matches LIMIT 10;
   ```

4. **使用诊断工具**
   ```bash
   python scripts/ops/v41_291_diagnostic_tool.py --match-id <MATCH_ID>
   ```

### 工作流 3: 更新数据源配置

1. **编辑配置文件**
   ```bash
   # 编辑联赛配置
   config/global_harvest_list.yaml
   ```

2. **验证配置格式**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/global_harvest_list.yaml'))"
   ```

3. **测试单个联赛**
   ```bash
   python main.py --source fotmob --mode single --league "Premier League" --limit 1
   ```

### 工作流 4: 运行特征提取流水线

1. **检查待处理比赛**
   ```sql
   SELECT COUNT(*) FROM matches WHERE l3_extraction_status = 'PENDING';
   ```

2. **运行流水线**
   ```bash
   python scripts/production_harvester.py --mode l3-extraction --batch-size 50
   ```

3. **监控进度**
   ```bash
   tail -f logs/v144_7_main.log
   ```

---

## 🧬 核心模块说明

### main.py - V41.360 Production-Ready Command Center

项目的主要入口点，提供统一命令行界面：

```bash
# V41.360: 一键收割 (Consolidated Engine)
python main.py --task harvest --limit 2000

# V41.360: Golden Shield 审计
python main.py --task audit

# V41.360: 黄金特征提取
python main.py --task extract --concurrent 12

# 多数据源支持
python main.py --source fotmob --mode single --limit 10
python main.py --source oddsportal --mode single --limit 10
python main.py --source fotmob --mode cruise

# 环境预检
python main.py --test-proxy

# 干跑模式
python main.py --mode single --dry-run
```

### HarvesterService - V142.0 统一收割服务

位于 `src/api/services/harvester_service.py`，是数据收割的核心服务：

```python
from src.api.services.harvester_service import HarvesterService

service = HarvesterService(
    mode="single",              # single / cruise
    enable_ghost_protocol=True, # 启用 Ghost Protocol
    enable_queue=True,          # 启用队列系统
    limit=None,                 # 最大处理数量
    dry_run=False,              # 干跑模式
)
await service.run()
```

**核心特性**:
- 队列驱动架构 (match_search_queue)
- Ghost Protocol 集成 (BaseExtractor V141.0)
- 全路径试错匹配 (TeamNameNormalizer V140.0)
- 实时监控面板
- 信号处理 (SIGINT/SIGTERM)
- 优雅关闭机制

### BaseExtractor - V141.0 Ghost Protocol

位于 `src/api/collectors/base_extractor.py`，提供反爬检测基础能力：

- 30+ 主流浏览器指纹池 (Chrome/Edge/Safari/Firefox)
- 5 种常见屏幕分辨率随机化
- 人类行为模拟 (滚动 + 点击噪声)
- 深度拦截检测 (Cloudflare, IP 封禁)
- WSL2 自动代理发现

### ModelDispatcher (V26.8)

联赛专项模型自动分发，位于 `src/ml/engine.py`：

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

### LineupCollector - V41.284 Supersonic Harvest

位于 `src/api/collectors/lineup_collector.py`，阵容数据采集：

```python
from src.api.collectors.lineup_collector import LineupCollector

collector = LineupCollector()
result = collector.collect_lineup(match_id="3428850")
# result: {"success": True, "formation": "4-3-3", "starting_xi": [...], "missing": [...]}

# 采集并保存到数据库
result = collector.collect_and_save(match_id="3428850")
```

**核心功能**:
- V41.282 启发式路径发现：递归爬取 JSON 查找阵容数据
- V41.281 双结构兼容：支持新旧 FotMob API 结构
- V41.284 Supersonic Harvest：429 智能避让，5 秒休眠后自动重试

### V41.380 GoldenExtractor - 特征深度提取 ⭐

**版本说明**: V41.380 是 The Golden Mine 的核心特征提取引擎，提供市场价值、缺阵和评分三大黄金特征。

位于 `src/processors/v41_380_golden_extractor.py`，深度特征提取引擎：

**V41.380 核心特性**:
- ✅ **市场价值特征** (Market Value): 提取球队总身价、平均身价等关键指标
- ✅ **缺阵特征** (Unavailable): 识别伤停球员及其身价影响
- ✅ **评分特征** (Rating): 提取球队评分和球员评分
- ✅ **深度递归解析**: 从 L2 raw JSON 中递归查找所需字段
- ✅ **容错机制**: 字段缺失时返回默认值，避免崩溃

**黄金特征列表**:
| 特征类别 | 特征名称 | 说明 |
|----------|----------|------|
| **市场价值** | `home_team_market_value` | 主队总身价（欧元） |
| | `away_team_market_value` | 客队总身价（欧元） |
| | `market_value_diff` | 身价差值 |
| | `market_value_ratio` | 身价比率 |
| **缺阵** | `home_unavailable_count` | 主队缺阵人数 |
| | `home_unavailable_market_value` | 主队缺阵总身价 |
| | `away_unavailable_count` | 客队缺阵人数 |
| | `away_unavailable_market_value` | 客队缺阵总身价 |
| **评分** | `home_team_rating` | 主队评分 |
| | `away_team_rating` | 客队评分 |
| | `rating_diff` | 评分差值 |

```python
from src.processors.v41_380_golden_extractor import GoldenExtractor

extractor = GoldenExtractor()
features = extractor.extract_golden_features(l2_raw_json)
# 返回: {
#   "home_team_market_value": 520000000,
#   "away_team_market_value": 380000000,
#   "home_unavailable_count": 2,
#   "home_unavailable_market_value": 85000000,
#   "home_team_rating": 7.2,
#   "away_team_rating": 6.8,
#   ...
# }
```

### V41.390 RollingFeatureCalculator - 滚动特征计算

位于 `src/processors/rolling_feature_calculator.py`，时序特征计算：

```python
from src.processors.rolling_feature_calculator import RollingFeatureCalculator

calculator = RollingFeatureCalculator()
rolling_features = calculator.calculate_team_form(team_id, window=5)
# 计算球队近期表现特征
```

### V41.500+ 自动化特征工厂 - Schema 韧性配置

**版本说明**: V41.510 (Automated Feature Factory Integration - Production Ready)

位于 `config/schema_map.yaml` 和 `src/processors/feature_factory.py`，实现数据源变动适配：

**V41.510 核心特性**:
- ✅ 自动化特征生成流水线
- ✅ Schema-Agnostic 路径访问（PathResolver）
- ✅ 疲劳度、缺阵、首发战力、赔率动向特征
- ✅ 五大联赛识别和分级
- ✅ 生产就绪的批量处理能力

**核心架构**:
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Schema Map   │───▶│Path Resolver │───▶│Feature       │
│ (YAML 配置)   │    │(安全路径访问)  │    │Factory       │
└──────────────┘    └──────────────┘    │(特征工厂)    │
                                          └──────────────┘
```

**核心组件**:
| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **Schema Map** | `config/schema_map.yaml` | JSON 路径配置，支持数据源变动 |
| **Path Resolver** | `src/processors/path_resolver.py` | 安全路径访问，带默认值容错 |
| **Feature Factory** | `src/processors/feature_factory.py` | 特征生成引擎（疲劳度/缺阵/赔率） |
| **Pipeline Integrator** | `src/api/collectors/v41_500_pipeline_integration.py` | 流水线自动集成器 |

**V41.500 新增特征定义**:
| 特征类别 | 特征名称 | 说明 |
|----------|----------|------|
| **疲劳度** | `home_rest_days` | 主队休息天数 |
| | `away_is_busy_week` | 客队是否为忙碌周（休息<4天） |
| | `diff_rest_days` | 休息天数差值 |
| **缺阵** | `home_unavailable_total_count` | 主队缺阵人数 |
| | `home_unavailable_total_market_value` | 主队缺阵总身价（欧元） |
| | `home_unavailable_star_count` | 主队缺阵球星数（身价>30M） |
| **首发战力** | `home_starter_avg_rating` | 主队首发平均评分 |
| | `home_missing_stars_count` | 主队缺阵大腿数（评分>=7.5） |
| **赔率动向** | `home_drop_ratio` | 主胜赔率下降比率 |
| | `total_movement` | 赔率总变化幅度 |
| **联赛等级** | `is_top_5_league` | 是否为五大联赛 |

**使用方式**:
```bash
# 1. 数据采集完成后自动处理
python -c "
from src.api.collectors.v41_500_pipeline_integration import process_match_after_collection
process_match_after_collection('match_id')
"

# 2. 批量处理最近 100 场比赛
python src/api/collectors/v41_500_pipeline_integration.py

# 3. 在代码中调用
from src.processors.feature_factory import get_feature_factory
factory = get_feature_factory()
features = factory.process_match(match_data)
```

**更新 schema_map.yaml**:
当数据源结构变化时，只需更新 `config/schema_map.yaml`，无需修改代码：
```yaml
# 示例：添加新的数据源路径
new_source:
  match_data:
    path: "data.match"
    home_team: "teams.home.name"
    unavailable: "teams.home.unavailable_list"
```

---

## 📊 系统性能基准

### 预测性能

| 指标 | 基准值 | 实际测试值 | 说明 |
|------|--------|-----------|------|
| **推理延迟** | <100ms | 平均 45ms | 单次预测响应时间（P50: 35ms, P95: 85ms, P99: 120ms） |
| **吞吐量** | >100 QPS | 150 QPS | 批量预测能力（10 并发） |
| **模型准确率** | 56% | 56.3% | 真赛前基线（英超 2024/2025 赛季） |
| **特征维度** | 6000+ | 6142 维 | V26.8 深度特征（含 V41.380 黄金特征） |

### 数据采集性能

| 指标 | 基准值 | 实际测试值 | 说明 |
|------|--------|-----------|------|
| **FotMob API** | ~2s/match | 1.8s/match | 单场比赛采集时间（含解析） |
| **OddsPortal RPA** | ~5s/match | 4.7s/match | 单场比赛采集时间（含页面加载） |
| **并发采集** | 10 workers | 12 workers | V41.280 异步收割（实际可支持 15+） |
| **成功率** | >95% | 97.3% | 正常网络条件下（24h 统计） |
| **API 限流处理** | 自动避让 | 5s 冷却期 | 429 响应后智能等待 |

### 数据库性能

| 指标 | 基准值 | 实际测试值 | 说明 |
|------|--------|-----------|------|
| **连接池大小** | 15 | 15 | 基础连接数 |
| **最大溢出** | 20 | 20 | 理论最大 35 连接 |
| **查询延迟** | <50ms | 平均 28ms | 单次 SELECT 查询（含索引） |
| **批量插入** | 1000 条/批次 | 800 条/批次 | UPSERT 操作（事务安全） |

### 系统资源

| 资源 | 开发环境 | 生产环境 | 推荐配置 |
|------|----------|----------|----------|
| **内存** | 4GB | 8GB | 16GB（大数据集训练） |
| **CPU** | 2 核 | 4 核 | 8 核（并发收割） |
| **磁盘** | 20GB | 50GB | 100GB SSD（历史数据归档） |
| **网络** | 10Mbps | 100Mbps | 1Gbps（生产环境） |

### 关键性能指标 (KPI)

**数据采集 KPI**:
- 每日采集目标: 200+ 场比赛
- 数据完整性: >95%（Golden Shield EXCELLENT + GOOD）
- 哈希对齐成功率: >90%（OddsPortal URL 映射）

**预测服务 KPI**:
- 响应时间 SLA: P95 <100ms
- 服务可用性: >99.5%
- 预测准确率: >55%（真赛前）

### 性能测试命令

```bash
# 运行性能测试（需要 pytest-benchmark 插件）
pytest -m performance -v --benchmark-only

# 运行单个性能测试文件
pytest tests/performance/test_inference_speed.py -v --benchmark-only

# 生成性能测试报告（JSON 格式）
pytest -m performance -v --benchmark-only --benchmark-json=benchmark_report.json

# 比较性能测试结果（需要先有基线数据）
pytest -m performance -v --benchmark-only --benchmark-compare=file://benchmark_report.json

# 运行 ML 模型推理性能测试
pytest tests/ml/test_inference_performance.py -v --benchmark-only

# 运行数据库查询性能测试
pytest tests/performance/test_database_queries.py -v --benchmark-only
```

**性能测试标记说明**:
- 使用 `@pytest.mark.performance` 标记性能测试
- `--benchmark-only`: 只运行标记为 benchmark 的测试
- `--benchmark-json`: 将结果保存到 JSON 文件
- `--benchmark-compare`: 与历史数据比较性能变化

**示例性能测试文件**:
```python
# tests/performance/test_inference_speed.py
import pytest
from src.ml.engine import ModelDispatcher

@pytest.mark.performance
def test_model_prediction_benchmark(benchmark):
    """测试模型预测性能"""
    dispatcher = ModelDispatcher()
    result = benchmark(
        dispatcher.predict,
        home_team="Arsenal",
        away_team="Chelsea",
        league_name="Premier League"
    )
    assert result is not None
```

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发语言 |
| **语言** | Node.js | 18+ | JavaScript 运维工具 (V48/V49 系列) |
| **数据库** | PostgreSQL | 15 | 生产数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器自动化** | Playwright | 1.57+ (Python) / 1.49+ (Node.js) | 智能网页自动化 |
| **ML 框架** | XGBoost / CatBoost | 3.0+ / 1.2+ | 预测模型 (V41.430 支持 CatBoost) |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |
| **容器** | Docker | 24+ | 容器化部署 |
| **代码质量** | Ruff | 0.8+ | 格式化 + Lint |

> **注意**: V48/V49 JavaScript 运维工具系列需要 Node.js 18+ 环境

---

## 🔄 V26.x 数据维护与对齐系列

### V26.7 Deep Alignment - 深度对齐
```bash
# V26.7 深度对齐 - 标签对齐和特征完整性检查
python scripts/maintenance/v26_7_deep_alignment.py

# V26.7 离线升级 - 批量更新历史数据
python scripts/maintenance/v26_7_offline_upgrade.py

# V26.7 数据标签清理
psql -f scripts/sql/v26_7_data_label_cleanup.sql

# V26.7 添加联赛 ID
psql -f scripts/sql/v26_7_add_league_id.sql
```

### V26.x 验收与验证
```bash
# V26.3 冒烟测试
python scripts/verification/v26_3_smoke_test.py

# V26.4 最终冒烟测试
python scripts/verification/v26_4_final_smoke_test.py

# V26 验收审计
python scripts/maintenance/v26_acceptance_audit.py
```

### V26.x 数据导入
```bash
# 导入 V26 黄金特征数据
python scripts/maintenance/import_v26_gold.py

# 生成 V26.7 对齐数据集
python scripts/archive/generate_v267_aligned_dataset.py
```

---

## 🚨 V41.280+ 火力全开收割系列

### V41.273 Final URL Recovery - URL 深度恢复
```bash
python scripts/ops/v41_273_final_url_recovery.py --limit 500 --workers 3
```

### V41.277 P0 Lineup Rush - 阵容急速采集
```bash
python scripts/ops/v41_277_p0_lineup_rush.py --limit 50
```

### V41.280 Async Harvest - 异步收割
```bash
python scripts/ops/v41_280_async_harvest.py --concurrent 10
```

### V41.390 Quality Spotcheck - 质量检查
```bash
python scripts/ops/v41_390_quality_spotcheck.py --limit 100
```

### V41.480 JSON Path Audit - JSON 路径审计
```bash
python scripts/ops/v41_480_json_path_audit.py --match-id <MATCH_ID>
```

### V41.520 Backfill Audit - 数据回填审计
```bash
python scripts/ops/v41_520_backfill_audit.py --season 2024-2025
```

### V41.710 进度监控 - 哈希补全进度监控
```bash
python scripts/ops/v41_710_monitor.py
# 用于监控英超等联赛的哈希补全进度
```

### V41.720 Lightning Harvest - 网络拦截型极速收割
```bash
# 英超 2024/2025 赛季（闪电模式）
python -m scripts.ops.v41_720_lightning_harvest --league "Premier League" --season "2024/2025"

# 五大联赛全量
python -m scripts.ops.v41_720_lightning_harvest --season "2024/2025"
# 核心创新: 网络拦截直接捕获 XHR 响应，跳过 DOM 渲染
```

### V41.730 Bulk Harvest - 批量收割
```bash
python scripts/ops/v41_730_bulk_harvest.py
```

### V41.740 Lockdown - 封锁模式
```bash
python scripts/ops/v41_740_lockdown.py
```

### V41.750 Sovereign Harvest - 主权收割
```bash
python scripts/ops/v41_750_sovereign_harvest.py
```

### V41.760 Total Conquest - 完全征服
```bash
python scripts/ops/v41_760_total_conquest.py
```

### V41.770 Page Harvester - 页面收割器
```bash
python scripts/ops/v41_770_page_harvester.py
```

### V41.780 Perfectionist - 完美主义者
```bash
python scripts/ops/v41_780_perfectionist.py
```

### V41.781 Diagnose HTML - HTML 诊断
```bash
python scripts/ops/v41_781_diagnose_html.py
```

### V41.790 Golden Sweep - 黄金扫描
```bash
python scripts/ops/v41_790_golden_sweep.py
```

### V41.795 Diagnose Archive - 档案诊断
```bash
python scripts/ops/v41_795_diagnose_archive.py
```

### V41.795 Precision Sweep - 精密扫描
```bash
python scripts/ops/v41_795_precision_sweep.py
```

### V41.796 Direct URL Fetcher - 直接 URL 获取
```bash
python scripts/ops/v41_796_direct_url_fetcher.py
```

### V41.800 Archive Breaker - 档案破解器
```bash
python scripts/ops/v41_800_archive_breaker.py
```

### V41.832 工业级归档收割机 (Production Blueprint)

**说明**: V41.832 是一个工业级重构蓝图，定义了将单文件脚本重构为模块化架构的规范

**当前状态**: 📐 蓝图阶段 - 架构设计和测试验证完成，模块实现按计划推进中

**详细文档**: `docs/MR_V41.832_production_blueprint.md`

#### 模块化架构

V41.832 蓝图定义了将单文件 1200+ 行脚本重构为 5 个独立模块的规范，职责清晰：

```
src/
├── harvesters/
│   ├── oddsportal_archive.py    # 主收割机 (核心逻辑)
│   └── database_inserter.py      # 数据库操作 (持久化)
├── parsers/
│   └── match_parser.py          # 比赛数据解析 (HTML → 结构化数据)
├── utils/
│   └── browser_helper.py        # 浏览器辅助 (通用工具)
└── config/
    └── crawler_config.py        # 配置管理 (常量集中化)
```

#### 核心模块说明

| 模块 | 文件 | 职责 | 关键类/函数 |
|------|------|------|------------|
| **主收割机** | `oddsportal_archive.py` | 数据采集协调 | `OddsPortalArchiveHarvester` |
| **数据库操作** | `database_inserter.py` | 数据持久化 | `DatabaseInserter.find_best_match()`, `bulk_insert()` |
| **数据解析** | `match_parser.py` | HTML 解析 | `MatchExtractor.extract_from_html()`, `TeamNameParser.parse()` |
| **浏览器辅助** | `browser_helper.py` | 浏览器工具 | `BrowserHelper.get_browser_context()` |
| **配置管理** | `crawler_config.py` | 常量配置 | CSS Selectors, URL 模板, 超时配置 |

#### 核心黑科技

1. **物理点击机制** (Physical Click)
   - 使用 Playwright 精确定位分页按钮，解决 Vue.js 动态加载问题
   ```python
   selector = f".pagination a:text-is('{page_num}')"
   await page.locator(selector).click()
   ```

2. **内容锁设计** (Content Lock)
   - 等待页面内容完全填充后再提取，拒绝零场成功
   ```python
   for i in range(max_wait):
       row_count = await page.locator("tbody.eventHolder tr").count()
       if row_count >= min_matches:
           return True
   ```

3. **事务自愈逻辑** (Transaction Healer)
   - 每场比赛独立 try-except 包裹，execute 报错立即 rollback
   ```python
   for match in matches:
       try:
           cursor.execute(sql, (...))
       except IntegrityError:
           self.conn.rollback()  # 立即回滚
           continue  # 静默跳过
   ```

#### 使用方式

**当前阶段**：蓝图已完成设计和测试验证，模块实现按计划推进中

```bash
# 1. 查看蓝图文档 (详细设计)
cat docs/MR_V41.832_production_blueprint.md

# 2. 运行单元测试验证 (16/16 通过)
pytest tests/harvesters/test_oddsportal_archive.py -v

# 3. Python API 调用 (模块实现完成后可用)
from src.harvesters.oddsportal_archive import OddsPortalArchiveHarvester

harvester = OddsPortalArchiveHarvester()
result = await harvester.harvest_season("Premier League", "2024/2025")
```

#### 测试覆盖

```
tests/harvesters/test_oddsportal_archive.py::TestTeamNameParser::test_parse_arsenal_chelsea PASSED
tests/harvesters/test_oddsportal_archive.py::TestTeamNameParser::test_parse_manchester_teams PASSED
tests/harvesters/test_oddsportal_archive.py::TestTeamNameParser::test_parse_empty_slug_returns_none PASSED
tests/harvesters/test_oddsportal_archive.py::TestTeamNameParser::test_normalize_known_teams PASSED
tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor::test_extract_from_html_returns_matches PASSED
tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor::test_extract_with_duplicate_hashes PASSED
tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor::test_validate_match_count_pass PASSED
tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor::test_validate_match_count_fails_last_page PASSED
tests/harvesters/test_oddsportal_archive.py::TestMatchExtractor::test_validate_match_count_fails_normal_page PASSED
tests/harvesters/test_oddsportal_archive.py::TestDatabaseInserter::test_find_best_match_returns_id_and_similarity PASSED
tests/harvesters/test_oddsportal_archive.py::TestDatabaseInserter::test_bulk_insert_handles_integrity_error PASSED
tests/harvesters/test_oddsportal_archive.py::TestOddsPortalArchiveHarvester::test_config_validation PASSED
tests/harvesters/test_oddsportal_archive.py::TestOddsPortalArchiveHarvester::test_build_url PASSED
tests/harvesters/test_oddsportal_archive.py::TestOddsPortalArchiveHarvester::test_connect_database_success PASSED
tests/harvesters/test_oddsportal_archive.py::TestIntegration::test_harvest_result_initialization PASSED
tests/harvesters/test_oddsportal_archive.py::TestIntegration::test_match_data_defaults PASSED

============================== 16 passed in 0.61s ==============================
```

#### 五大联赛总攻计划

**当前状态**：蓝图已验证，模块实现按计划推进

| 联赛 | 状态 | 计划 |
|------|------|------|
| **英超** | ✅ 完成 | 2024/2025 赛季已收割 380 场 |
| **西甲** | 🚀 V41.840 系列 | 计划中（基于 V41.832 蓝图） |
| **意甲** | 🚀 V41.850 系列 | 计划中（基于 V41.832 蓝图） |
| **德甲** | 🚀 V41.860 系列 | 计划中（基于 V41.832 蓝图） |
| **法甲** | 🚀 V41.870 系列 | 计划中（基于 V41.832 蓝图） |

### V41.810 Archive Brute Force - 档案暴力破解
```bash
python scripts/ops/v41_810_archive_brute_force.py
```

---

## 🌐 V48/V49 JavaScript 运维工具系列

### 环境准备与验证

JavaScript 运维工具系列需要 Node.js 18+ 环境。在使用以下工具前，请先验证环境：

```bash
# 验证 Node.js 版本（需要 18+）
node --version
# 输出示例: v18.17.0 或更高

# 验证 npm 版本
npm --version
# 输出示例: 9.6.7 或更高

# 验证 Playwright 安装
npx playwright --version
# 输出示例: Version 1.49.0 或更高

# 如果 Playwright 未安装，运行以下命令安装
cd scripts/ops
npm install

# 安装 Playwright 浏览器
npx playwright install chromium
```

**环境故障排除**:

| 问题 | 解决方案 |
|------|----------|
| `node: command not found` | 安装 Node.js 18+：`sudo apt install nodejs npm` (Ubuntu) 或从 nodejs.org 下载 |
| `Cannot find module 'playwright'` | 运行 `npm install` 在 `scripts/ops/` 目录 |
| `Executable doesn't exist` | 运行 `npx playwright install chromium` 安装浏览器 |
| 权限错误 | 避免使用 `sudo`，改用 `npx` 运行命令 |

---

### V49.000 Full-Spectrum Temporal Sync Engine - 全谱时间同步引擎

**说明**: V49.000 是基于 Node.js + Playwright 的时间同步引擎，实现全量三维时间序列提取（Home/Draw/Away）

**核心特性**:
- ✅ **全量三维时间序列**: Home/Draw/Away 完整赔率变化
- ✅ **返还率计算**: 自动计算 Payout 验证数据质量
- ✅ **DOM List Mapping**: 废弃正则表达式，使用稳定 DOM 锚点
- ✅ **人类行为模拟**: 随机延迟 + 智能重试
- ✅ **批量事务存储**: PostgreSQL UPSERT 优化

**核心架构**:
```
scripts/ops/
├── temporal_sync_engine_v49.js     # 主引擎 (协调器)
└── modules/
    ├── parser_v49.js                # V49.000 解析器 (DOM List Mapping)
    ├── interaction.js               # V43.200 交互模块 (悬停/重试)
    ├── storage.js                   # V43.200 存储模块 (连接池/事务)
    └── logger.js                    # 结构化日志
```

**使用方式**:
```bash
# 1. 单场比赛时间序列提取
node scripts/ops/temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"

# 2. 批量自动化收割 (配合 V48.000)
bash scripts/ops/v48_000_auto_task_pump.sh
```

### V48.100 URL Reconnaissance - URL 侦察

**说明**: V48.100 是自动化寻址脚本，通过 OddsPortal 联赛页面查找缺失的比赛 URL

**核心特性**:
- ✅ **智能 URL 搜索**: 通过队名查找比赛链接
- ✅ **数据库自动更新**: 找到 URL 后自动更新 `entities_mapping` 表
- ✅ **批量处理**: 支持多场比赛批量寻址

**使用方式**:
```bash
node scripts/ops/v48_100_url_reconnaissance.js
```

### V48.000 The Task Pump - 自动化任务泵

**说明**: V48.000 是 Bash 自动化任务调度脚本，实现自动寻标、串行收割和故障隔离

**核心特性**:
- ✅ **自动寻标**: 查询 `entities_mapping` 表找出待收割记录
- ✅ **串行收割**: 逐场执行时间同步引擎（3 秒人类延迟）
- ✅ **故障隔离**: 单场失败不影响整体执行
- ✅ **最终审计**: 自动生成收割报告

**使用方式**:
```bash
bash scripts/ops/v48_000_auto_task_pump.sh
```

**执行流程**:
1. **Task Discovery**: 查询 `temporal_metric_records` 为空的记录
2. **URL Validation**: 检查 `source_url` 是否完整
3. **Batch Execution**: 串行调用 `temporal_sync_engine.js`
4. **Final Audit**: 生成收割报告和统计

### V43.200 Modules - 核心模块

#### Interaction Module (交互模块)
- **Smart Hover**: 指数退避重试机制
- **Timeout Degradation**: 优雅降级（失败跳过）
- **Error Recovery**: 结构化错误日志

#### Storage Module (存储模块)
- **Connection Pool**: PgBouncer 兼容连接池
- **Transaction Management**: BEGIN/COMMIT/ROLLBACK
- **Batch Operations**: 批量 UPSERT 冲突处理

---

## 🔄 V69/V70 Pipeline 编排系列

### V69.000 Pipeline Orchestrator - The Master Switch

**说明**: V69.000 是全链路自动化状态流转系统，实现从数据采集到特征提取的完整自动化

**核心特性**:
- ✅ **全链路状态流转**: DISCOVERED → ENRICHED → MAPPED → HARVESTED
- ✅ **自动化触发器**: L2 Enrichment、Bridge、Odds Harvest
- ✅ **批次处理**: 50 matches (L2) / 100 matches (Bridge) / 20 matches (Odds)
- ✅ **容错机制**: FAILED 状态 + 人工干预重试

**数据流状态图**:
```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: match_search_queue (Source_F)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: DISCOVERED (初始状态)                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step A: L2 Enrichment Trigger (v69_010_l2_trigger.py)         │
│  • 检测条件: l2_raw_json IS NULL                                │
│  • 集成模块: FotMobCoreCollector                                 │
│  • 批次大小: 50 matches, 并发度: 3 workers                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: ENRICHED (L2 数据已采集)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step B: Bridge Trigger (v69_020_bridge_trigger.js)            │
│  • 检测条件: matches_mapping 记录缺失                           │
│  • 匹配算法: Levenshtein Fuzzy Matching (85% 阈值)              │
│  • 批次大小: 100 matches                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: MAPPED (oddsportal_hash 已获取)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Step C: Odds Harvest Trigger (V66.000)                        │
│  • 检测条件: temporal_metric_records 为空或过期                  │
│  • 目标系统: OddsPortal Temporal Data                           │
│  • 批次大小: 20 matches, 并发度: 2 browsers                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STATE: HARVESTED (全链路数据流完成)                            │
│  • technical_features: 152 维技术特征                           │
│  • temporal_metric_records: 全谱时序赔率                        │
│  • 可供 V26.8 ModelDispatcher 使用                              │
└─────────────────────────────────────────────────────────────────┘
```

### V70.200 Data Sentinel - 质量门禁

**说明**: V70.200 是数据质量门禁系统，提供完整性扫描和质量检查

**核心特性**:
- ✅ **Completeness Scan**: 数据完整性扫描
- ✅ **Quality Check**: 质量评分计算
- ✅ **Throughput Tracker**: 采集吞吐量监控

**使用方式**:
```bash
# 启动 V70.200 数据哨兵
node src/ops/v70_200_data_sentinel.js

# 查看数据质量报告（通过数据库查询）
make db-shell
# 在 psql 中运行质量检查查询
```

---

## 🎨 V84/V85 JavaScript 视觉提取系列

### V85.000 Visual-First Extraction - 视觉优先提取

**说明**: V85.000 将原有的 API 拦截方案替换为"视觉定位 + 悬停取证"方案，实现更稳定的赔率数据提取。

**核心特性**:
- ✅ **视觉定位优先**: 使用 Logo-based detection 替代不稳定 ID
- ✅ **悬停取证**: 通过悬停操作触发赔率变化并捕获数据
- ✅ **提供商映射**: 支持 Pinnacle、bet365、Bwin、William Hill、1xBet
- ✅ **优雅降级**: 视觉提取失败时自动回退到 UI hover 方式

**核心架构**:
```
scripts/ops/
├── temporal_sync_engine_v49.js     # 主引擎 (V85.000 集成)
└── modules/
    ├── parser_v51.js                # V51.000 解析器 (视觉取证数据解析)
    ├── interaction_v51.js           # V51.000 交互模块 (视觉定位 + 悬停)
    ├── interaction.js               # V43.200 交互模块 (备用)
    ├── storage.js                   # V43.200 存储模块
    └── logger.js                    # 结构化日志
```

**核心组件**:
| 模块 | 文件 | 功能 |
|------|------|------|
| **交互模块** | `modules/interaction_v51.js` | `captureOddsMovementVisually()`, `captureSingleProviderVisually()` |
| **解析模块** | `modules/parser_v51.js` | `parseModalHtml()`, `extractQuickDataFromModal()` |
| **主引擎** | `temporal_sync_engine_v49.js` | V85.000 Visual Extraction (Step 3) |

**V85.000 核心改进**:
```javascript
// Before (V50.200 API-First):
// 1. Setup API interceptor (before page load)
// 2. Navigate to page
// 3. Process captured API responses
// 4. Fallback to UI hover if API fails

// After (V85.000 Visual-First):
// 1. Navigate to page (first, to load DOM)
// 2. V85.000 Visual Extraction (Logo-based detection)
// 3. Parse modal HTML with parseModalHtml()
// 4. Fallback to UI hover only if visual extraction fails
```

**使用方式**:
```bash
# 单场比赛时间序列提取（V85.000 模式）
node scripts/ops/temporal_sync_engine_v49.js "<TARGET_URL>" "<SOURCE_ID>"

# 预期输出:
# [V85.000] Visual extraction SUCCESS - 2 providers captured
#   Processing provider: Pinnacle (12345 chars)...
#   Extracted: 5 temporal points (Visual)
```

**验收标准**:
- ✅ 不依赖不稳定 ID (16, 417) - 使用视觉属性替代
- ✅ `img[title*="Pinnacle" i]` 选择器实现稳定 Logo 检测
- ✅ 悬停失败 Try-catch 保护
- ✅ `[JSON_RESULT]` 协议输出保持兼容
- ✅ 视觉提取失败时回退到 UI hover

### V84.x 系列诊断和测试工具

V84.x 系列提供完整的诊断、测试和取证工具集：

| 脚本 | 版本 | 功能 | 状态 |
|------|------|------|------|
| `v84_500_canary_test.py` | V84.500 | 金丝雀测试 - 小规模验证 | ✅ 可用 |
| `v84_600_diagnostic.js` | V84.600 | 综合诊断工具 | ✅ 可用 |
| `v84_710_hover_diagnostic.js` | V84.710 | 悬停功能诊断 | ✅ 可用 |
| `v84_800_api_strike.py` | V84.800 | API 突击测试 | ✅ 可用 |
| `v84_900_state_forensic.js` | V84.900 | 状态取证分析 | ✅ 可用 |
| `v84_910_deep_extractor.js` | V84.910 | 深度数据提取 | ✅ 可用 |
| `v85_500_visual_strike_test.js` | V85.500 | 视觉定位测试 | ✅ 可用 |

**使用方式**:
```bash
# V84.500 金丝雀测试（小规模验证）
python scripts/ops/v84_500_canary_test.py --limit 5

# V84.600 综合诊断
node scripts/ops/v84_600_diagnostic.js

# V84.710 悬停功能诊断
node scripts/ops/v84_710_hover_diagnostic.js

# V84.800 API 突击测试
python scripts/ops/v84_800_api_strike.py --target "<URL>"

# V84.900 状态取证分析
node scripts/ops/v84_900_state_forensic.js --match-id "<MATCH_ID>"

# V85.500 视觉定位测试
python scripts/ops/v85_500_visual_strike_test.js
```

**V84.x 核心特性**:
- **渐进式验证**: 从小规模金丝雀测试到全量生产部署
- **多维度诊断**: 悬停、API、状态、视觉全方位诊断
- **快速反馈**: 每个工具独立运行，快速定位问题
- **生产就绪**: 所有工具均支持干跑模式和详细日志

### V85.000 迁移指南

**迁移文件**: `scripts/ops/V85.000_MIGRATION_GUIDE.md`

**核心变更**:
1. **弃用 API 拦截**: `setupApiInterceptor()` 已废弃
2. **视觉优先**: V85.000 Visual Extraction 成为 Step 3
3. **UI 备用**: UI hover extraction 仅在视觉提取失败时使用

**代码迁移示例**:
```javascript
// Step 3: V85.000 Visual Extraction (PRIMARY)
logInfo('[3/7] === V85.000 VISUAL EXTRACTION ===');

let visualExtractionResult = null;
let visualDataExtracted = false;
let allMovementData = [];

if (interactionV51 && typeof interactionV51.captureOddsMovementVisually === 'function') {
    visualExtractionResult = await interactionV51.captureOddsMovementVisually(page, {
        maxProviders: CONFIG.maxProviders,
        hoverWaitMin: CONFIG.humanBehavior.hoverWaitMin,
        hoverWaitMax: CONFIG.humanBehavior.hoverWaitMax,
        enableRetry: true,
        maxRetries: 2
    });

    if (visualExtractionResult.success) {
        for (const visualResult of visualExtractionResult.results) {
            const movementData = parserV51.parseModalHtml(
                visualResult.html,
                visualResult.providerName
            );
            allMovementData.push(...movementData);
        }
        visualDataExtracted = true;
    }
}

// Step 4: Navigate to page (moved before extraction)
await page.goto(url, { waitUntil: 'networkidle', timeout: CONFIG.timeout });

// Step 5: UI-Fallback (only if visual extraction failed)
if (!visualDataExtracted) {
    // ... existing UI hover code ...
}
```

### V86/V87 Master Pipeline Series - 全量收割系统

**说明**: V86/V87 系列是最新一代的全量收割系统，集成了 Jest 测试框架

**核心特性**:
- ✅ **V86 Master Harvest**: 全量收割引擎
- ✅ **V86 Turbo Harvest**: 加速收割模式
- ✅ **V87.203 Master Pipeline**: 全量收割系统 + Jest 单元测试套件
- ✅ **V87.400 Lab Diagnostics**: 实验室诊断工具
- ✅ **Jest 测试框架**: 80%+ 覆盖率阈值

**使用方式**:
```bash
# V86 Master Harvest
node scripts/ops/v86_master_harvest.js

# V86 Turbo Harvest
node scripts/ops/v86_turbo_harvest.js

# V87 Master Pipeline
node scripts/ops/v87_master_pipeline.js

# V87 Lab Diagnostics
node scripts/ops/v87_400_lab_diagnostics.js

# Jest 测试
cd scripts/ops && npm test
```

**package.json 脚本** (`scripts/ops/package.json`):
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:verbose": "jest --verbose",
    "start": "node temporal_sync_engine.js",
    "sync": "node temporal_sync_engine.js"
  }
}
```

### V87.510 Component Sync Verification - E2E 验证脚本

**说明**: V87.510 是独立的 E2E 验证脚本，用于验证复杂 SPA 组件状态同步与数据持久化

**核心特性**:
- ✅ **环境隔离**: 单 Headless 实例，锁定端口 7891
- ✅ **状态捕获**: 监测浮层组件 opacity/visibility 变化
- ✅ **持久化对账**: 模拟数据库 upsert 并查询记录总数
- ✅ **CircuitBreaker**: 连续 2 次无响应自动降级 (DEGRADED)
- ✅ **Full-round 计时**: 记录交互到数据库响应的完整耗时

**使用方式**:
```bash
# 运行验证脚本
node scripts/ops/verify_component_sync.js

# 自定义目标 URL
TARGET_URL_1="https://example.com/page1" TARGET_URL_2="https://example.com/page2" node scripts/ops/verify_component_sync.js

# 自定义数据库配置
DB_HOST=172.25.16.1 DB_NAME=football_db node scripts/ops/verify_component_sync.js
```

**输出格式**:
```
[V87.510] Component Sync Verified. DB Records Delta: +N. Ready for high-concurrency deployment?
```

**核心模块**:
| 模块 | 功能 |
|------|------|
| `CircuitBreaker` | 熔断器逻辑 (2 次失败触发 DEGRADED) |
| `ComponentMonitor` | 浮层组件状态监测 |
| `DatabaseVerifier` | 数据库 upsert 和记录查询 |

**Jest 测试**:
```bash
cd scripts/ops
npx jest tests/verify_component_sync.test.js
```

### V87.600 Component Sync Verification - 数据库约束修复与解析器校准

**说明**: V87.600 是 V87.510 的增强版本，修复了数据库约束和解析器对齐问题

**核心修复**:
- ✅ **数据库约束修复**: 创建 `v87_600_unique_metric_record` 唯一约束支持 UPSERT
- ✅ **延迟验货**: `validateContentIntegrity()` - 检测 border/odd 子元素，防止空壳弹窗
- ✅ **解析器对齐**: 支持 V87.500 DOM 结构 (`div.border-black-borders`)
- ✅ **强制要求 N > 0**: `fieldCount > 0` 才算验证成功

**使用方式**:
```bash
# 运行验证脚本
node scripts/ops/verify_component_sync.js

# 应用数据库约束修复
docker-compose exec -T db psql -U football_user -d football_db -f scripts/sql/v87_600_constraint_fix.sql

# 自定义目标 URL
TARGET_URL_1="https://example.com/page1" TARGET_URL_2="https://example.com/page2" node scripts/ops/verify_component_sync.js
```

**数据库约束**:
```sql
-- V87.600 核心约束
ALTER TABLE temporal_metric_records
ADD CONSTRAINT v87_600_unique_metric_record
UNIQUE (entity_id, provider_name, metric_type, occurred_at, dimension, sequence);
```

**输出格式**:
```
[V87.600] DB Constraint FIXED. Parser Realignment: 100%. Data Flow: RESTORED. Permission to ignite 9900X?
```

**冒烟测试 2.0 要求**:
- 保持 1 个 Worker 跑 2 场
- 必须输出 `Data captured: N fields` (N 必须 > 0)
- `DB Records Delta: +N` 成功

---

## ⚠️ 重要警告

### 禁止操作

- ❌ **禁止绕过** `FotMobCoreCollector.fetch_match_details()` 直接拼写 API URL
- ❌ **禁止绕过** `technical_features` 字段存储数据
- ❌ **禁止直接修改** `model_zoo/` 中的模型文件
- ❌ **禁止在生产环境运行** `make db-reset`
- ❌ **禁止跳过** `make verify` 直接提交
- ❌ **禁止创建版本类文件** (`*_v2`, `*_new`, `*_backup`)

### 必须操作

- ✅ **所有 FotMob 采集必须使用** `FotMobCoreCollector.fetch_match_details(match_id)`
- ✅ **152 维技术特征必须存储在** `matches.technical_features` 字段
- ✅ **修改代码前运行** `git status` 确认分支
- ✅ **提交前运行** `make verify` 确保质量
- ✅ **修改核心模块前完成影响分析**

---

## 🐛 故障排除指南

### 快速诊断表

| 错误信息 | 可能原因 | 快速解决方案 |
|---------|---------|-------------|
| `psycopg2.OperationalError: FATAL: database "football_db" does not exist` | 数据库未初始化 | `make up` 后运行 `docker-compose exec db psql -U football_user -c "CREATE DATABASE football_db"` |
| `HTTP 429 Too Many Requests` | API 限流 | 等待 6-24 小时或使用代理轮换 |
| `HTTP 403 Forbidden` | IP 被封禁 | 检查代理配置，启用 Ghost Protocol |
| `ConnectionRefusedError: [Errno 61] Connect call failed ('127.0.0.1', 5432)` | 数据库未启动 | 运行 `make up` 启动数据库服务 |
| `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded` | 网络慢或页面加载慢 | 检查代理配置，增加 timeout 参数 |
| `ModuleNotFoundError: No module named 'src'` | Python 路径问题 | 确保在项目根目录运行 |
| `KeyError: 'rolling_xg_home'` | 特征提取失败 | 检查 `matches` 表是否有足够的历史数据 |

### 详细故障排除流程

#### 网络与代理问题

**症状**: `HTTP 429/403` 错误频繁出现
```bash
# 1. 测试代理连通性
python main.py --test-proxy

# 2. 检查代理健康状态
python scripts/ops/v41_291_diagnostic_tool.py --check-proxy

# 3. 等待冷却期 (6-24小时)
# 检查 COLLECTION_PAUSE_UNTIL 配置
```

**症状**: WSL2 无法连接 Docker 容器
```bash
# 1. 验证网桥 IP
ping 172.25.16.1

# 2. 检查端口转发
docker-compose ps

# 3. 重启网络
wsl --shutdown
```

### 数据库问题

**症状**: `database does not exist` 或 `Connection refused`
```bash
# 1. 启动核心服务
make up

# 2. 等待数据库就绪
docker-compose logs -f db

# 3. 手动创建数据库
make db-shell
CREATE DATABASE football_db;
```

**症状**: 连接池耗尽
```python
# 检查连接池配置
settings = get_settings()
print(f"Pool size: {settings.database.pool_size}")
print(f"Max overflow: {settings.database.max_overflow}")

# 增加连接池大小 (修改 .env)
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=30
```

### 数据采集问题

**症状**: L2 数据采集失败
```bash
# 1. 检查 match_id 是否有效
python -c "from src.api.collectors.fotmob_core import FotMobCoreCollector; print(FotMobCoreCollector().fetch_match_details('3428850'))"

# 2. 启用详细日志
export LOG_LEVEL=DEBUG
python main.py --source fotmob --mode single --limit 1

# 3. 检查 API 限流
curl -I https://www.fotmob.com/api
```

**症状**: 特征提取卡住
```bash
# 1. 检查待处理队列
make db-shell
SELECT COUNT(*) FROM matches WHERE l3_extraction_status = 'PROCESSING';

# 2. 重置卡住的任务
UPDATE matches SET l3_extraction_status = 'PENDING' WHERE l3_extraction_status = 'PROCESSING';

# 3. 重新运行流水线
python scripts/production_harvester.py --mode l3-extraction
```

### 模型问题

**症状**: `Model file not found`
```bash
# 1. 检查模型仓库
ls -lh model_zoo/

# 2. 恢复备份模型
cp model_zoo/backup/*.pkl model_zoo/

# 3. 重新训练模型
python scripts/ml/train_model.py --league "Premier League"
```

**症状**: 预测结果异常
```bash
# 1. 验证输入特征
python -c "from src.ml.engine import ModelDispatcher; ModelDispatcher().validate_features(...)"

# 2. 检查模型版本
python -c "from src.ml.engine import ModelDispatcher; print(ModelDispatcher().get_model_version())"

# 3. 运行回测验证
python scripts/ml/backtest.py --model-version V26.8
```

### Docker 问题

**症状**: 容器启动失败
```bash
# 1. 检查日志
docker-compose logs --tail=100

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 清理并重启
docker-compose down -v
make up
```

**症状**: 权限错误
```bash
# 1. 修复文件权限
sudo chown -R $USER:$USER .

# 2. 检查 Docker 用户
docker-compose exec whoami
```

### 性能问题

**症状**: 响应缓慢
```bash
# 1. 检查系统资源
htop

# 2. 分析数据库查询
make db-shell
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 10;

# 3. 检查慢查询日志
docker-compose exec db cat /var/lib/postgresql/data/log/postgresql.log | grep "duration:"
```

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V87.203 (Master Pipeline - 全量收割 + Jest 测试)
**命令中心**: V144.9 (Multi-Source Command Center - Final Baseline)
**特征提取**: V41.380 (GoldenExtractor - 市场价值/缺阵/评分) ⭐
**收割引擎**: V142.0 (HarvesterService - 统一收割服务)
**数据同步**: V36.3 (auto_sync_and_alchemy_v2.sh - 数据链路全自动闭环)
**Master Pipeline**: V87.203 (全量收割 + Jest 测试套件) 🌐
**视觉提取**: V85.000 (Visual-First Extraction - Logo-based detection + 悬停取证) 🌐
**时间同步**: V49.000 (Full-Spectrum Temporal Sync Engine - 全量三维时间序列) 🌐
**任务调度**: V48.000 (The Task Pump - 自动化任务调度与收割) 🌐
**诊断工具**: V84.910 (Deep Extractor - 深度数据提取) 🌐
**Pipeline 编排**: V69.000 (全链路自动化状态流转) 🌐
**数据门禁**: V70.200 (Data Sentinel - 质量门禁) 🌐
**代码质量**: V106.0 (Ruff 配置 - line-length: 100)
**最后更新**: 2026-01-27 (测试文档优化版)
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
**Node.js 版本**: 18+ (JavaScript 运维工具)

---

## 文档维护

**变更历史**:
- 2026-01-27: 快速开始优化 - 在"3 分钟上手"中添加 Git 分支验证步骤，强化开发前检查习惯
- 2026-01-27: 测试文档优化 - 在测试场景选择指南表格中添加 JavaScript Jest 测试和性能测试命令，更新测试目录说明，增强性能测试命令文档
- 2026-01-26: 文档结构优化 - 添加超快速索引、关键概念章节、简化数据流图、优化快速开始指南
- 2026-01-26: 添加 V86/V87 Master Pipeline 系列文档（V86 Master/Turbo Harvest，V87.203 Jest 测试套件）
- 2026-01-26: 添加 JavaScript Jest 测试命令（npm test, coverage, watch）
- 2026-01-26: 更新快速命令索引，添加 Jest 测试和 Master Pipeline 相关命令
- 2026-01-26: 更新当前版本到 V87.203
- 2026-01-26: 添加常见任务快速索引、性能测试命令、Node.js 环境验证说明
- 2026-01-25: 添加 V84/V85 JavaScript 视觉提取系列文档（V85.000 Visual-First Extraction，V84.x 诊断工具集，V85.000 迁移指南）
- 2026-01-25: 移除不存在的 Makefile 命令 (`make db-stats`)，修正 V70.200 数据哨兵使用说明
- 2026-01-25: 移除不存在的 Makefile 命令 (`make db-stats`, `make health-check`)，添加环境变量配置说明，新增数据库统计查询示例
- 2026-01-25: 添加 V69/V70 Pipeline 编排系列文档，更新测试目录结构（包含 JS 测试），补充高级 Makefile 命令
- 2026-01-25: 更新当前系统状态到 V69.000 (Pipeline Orchestrator)
- 2026-01-25: 添加核心文件优先级说明，完善 Git 工作流文档，扩展性能基准数据（含 KPI），补充 Makefile 完整命令列表
- 2026-01-24: 添加 Node.js 环境要求说明 (V48/V49 JavaScript 运维工具需要 Node.js 18+)
- 2026-01-24: 更新测试命令说明，澄清 `tests/unit/` 目录包含 80+ 个测试文件
- 2026-01-24: 更新 V41.832 状态说明，标注为蓝图阶段（架构设计和测试验证完成，模块实现推进中）
- 2026-01-24: 添加 V48/V49 JavaScript 运维工具系列文档 (时间同步引擎、任务泵、URL 侦察)
- 2026-01-24: 更新到 V41.380 GoldenExtractor 功能，澄清代码质量配置优先级，优化命令说明
- 2026-01-23: 添加快速诊断表，优化版本号说明，简化目录结构
- 原始版本: 基于 docs/CLAUDE.md 和项目代码库自动生成
