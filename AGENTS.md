# FootballPrediction - AI 助手指令上下文

> **系统版本**: V4.51.2-TOTAL-WAR | **最后更新**: 2026-03-22
>
> 本文档为 AI 助手提供项目背景、架构理解和操作指南，用于快速上手和高效协作。

---

## 1. 项目概述

### 1.1 项目定位

**FootballPrediction** (V4.51.2-TOTAL-WAR) 是一个工业级足球预测平台，采用双语言（Node.js + Python）四层架构，通过多源数据采集、C++ 模糊匹配和 XGBoost 多模型共识，实现高精度的比赛预测。

### 1.2 核心能力

| 模块 | 技术实现 | 说明 |
|------|----------|------|
| **L1 Discovery** | FotMob API + 断路器 (Project Hound V6.7) | 自动发现未来 7 天比赛，100% 测试覆盖 |
| **L2 Harvest** | FotMob Details + OddsPortal + 22 节点代理池 | 赔率数据采集（开盘/收盘/1X2/亚洲盘） |
| **L3 Smelt** | FeatureSmelter V5.0-TURBO | 11维纯净战斗特征向量 |
| **ML Prediction** | XGBoost TITAN 模型 | 65.31% 准确率，<100ms 响应 |
| **OddsFluxDetector** | V5.0 赔率背离算法 | 实时监测赔率异常波动 |
| **Swarm Harvest** | Hyper Swarm 引擎 | Worker 池化架构，吞吐量提升 3.75x |
| **V6.0 Backfill** | OddsPortal 回填系统 | 历史数据回填，22端口代理轮询 |
| **Stealth Navigator** | Playwright Stealth 强化 | 反检测页面导航 |
| **Session Warmer** | 智能会话预热 | 自动保持会话活性 |
| **Sentinel** | 哨兵监控系统 | 自动停机与熔断保护 |
| **TITAN Cruise Control** | 全自动巡航控制器 | 无人值守定时任务调度 |
| **TITAN Discovery** | V6.7 L1 发现引擎 | 工业级赛程发现与标准化 |
| **TITAN Marathon** | 长时运行支持 | 大规模批次处理能力 |

### 1.3 质量认证

- **零模拟数据**：所有数据来自真实 API
- **幂等收割**：支持重复执行，自动跳过已完成
- **架构纯净**：无冗余模块，无废弃代码
- **黄金准则**：80% 测试覆盖率熔断 + 0 Error 静态质量
- **工业级部署**：Docker 全容器化，支持生产级监控
- **V6.7 加固**：L1/L2 双引擎工业化，ADR 架构决策记录

---

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **运行时** | Node.js 20+ / Python 3.11+ | 双语言架构 |
| **数据库** | PostgreSQL 15 | 数据存储 |
| **缓存** | Redis 7 | 分布式锁/缓存 |
| **容器化** | Docker / docker-compose | 环境隔离 |
| **浏览器** | Playwright 1.57+ + Stealth | 页面自动化与反检测 |
| **模糊匹配** | RapidFuzz (C++) | 队名匹配 |
| **ML** | XGBoost 3.1+ / scikit-learn 1.8+ | 预测模型 |
| **代理** | NetworkShield / ProxyRotator | 22 节点熔断保护 + 轮询 |
| **监控** | Prometheus + Grafana | 指标采集与可视化 |
| **日志** | Winston + Daily Rotate | 结构化日志与轮转 |
| **代码质量** | ESLint + Prettier + Ruff | 静态检查与格式化 |
| **API 框架** | FastAPI 0.124+ | 异步 API 服务 |

---

## 3. 系统架构

### 3.1 五阶段自动化流水线

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  L1         │    │  L2         │    │  L3         │    │  ELO        │    │  PREDICT    │
│  Discovery  │───▶│  Harvest    │───▶│  Smelt      │───▶│  Rating     │───▶│  Output     │
│  (赛程发现) │    │  (数据收割) │    │  (特征熔炼) │    │  (动态评分) │    │  (预测报告) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     FotMob           FotMob Details     11维特征          K-Factor           EV 排序
     API              + OddsPortal       (Elo+身价+H2H)    递归更新           TITAN 模型
     + OddsPortal     + 22代理节点        Worker 池化                          3-Model 共识
     回填系统
```

### 3.2 V6.7 L1 发现引擎架构 (Project Hound)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TITAN V6.7 L1 发现引擎                               │
│                         (Project Hound 工业级重构)                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
   │   Discovery  │────▶│  Circuit Breaker │────▶│  L1 Normalizer   │
   │   Service    │     │                  │     │                  │
   │ - FotMob API │     │ - 故障检测       │     │ - 数据标准化     │
   │ - 多源聚合   │     │ - 自动恢复       │     │ - 去重验证       │
   │ - 实时调度   │     │ - 优雅降级       │     │ - 约束 enforcement│
   └──────────────┘     └──────────────────┘     └──────────────────┘
          │                                              │
          │              ┌──────────────────┐           │
          └─────────────▶│  ADR-001/002     │◀──────────┘
                         │  架构决策记录     │
                         │ - 源级数据加固    │
                         │ - L2原始存储加固  │
                         └──────────────────┘
```

### 3.3 V6.0 回填流水线架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TITAN V6.0 回填流水线                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Executor   │────▶│  ProxyRotator    │────▶│  OddsPortal      │
│  (gold_pilot)│     │  (22端口轮询)     │     │  Harvester       │
│ - 批次调度   │     │                  │     │                  │
│ - 限流控制   │     │ - RoundRobin     │     │ - Playwright     │
│ - 状态监控   │     │ - 健康检查       │     │ - 真实抓取       │
└──────┬───────┘     └──────────────────┘     └──────────────────┘
       │
       │              ┌──────────────────┐
       └─────────────▶│   Checkpointer   │
                      │                  │
                      │ - 断点续传       │
                      │ - 实时存盘       │
                      │ - 重试计数       │
                      └────────┬─────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │  backfill_progress│
                      │  (PostgreSQL)     │
                      └──────────────────┘
```

### 3.4 数据层级

| 层级 | 数据源 | 存储表 | 说明 |
|------|--------|--------|------|
| **L1** | FotMob API | `matches` | 比赛发现、基础信息 |
| **L2** | FotMob Details + OddsPortal | `raw_match_data`, `l2_match_data` | 赔率数据（开盘/收盘/1X2/亚洲盘） |
| **L3** | 特征工程 | `l3_features` | 11维纯净特征向量 + market_sentiment |
| **ELO** | 历史比赛结果 | `team_elo_ratings` | 球队动态实力评分 |
| **预测** | XGBoost 模型 | `predictions` | 预测结果 + EV 计算 |
| **回填** | OddsPortal | `backfill_progress` | V6.0 回填进度跟踪 |

### 3.5 核心资产地图

| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/FixtureSeeder.js` | `npm run seed` |
| **L1 V6.7** | `scripts/ops/titan_discovery.js` | `node scripts/ops/titan_discovery.js` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` | `npm start` |
| **Swarm Harvest** | `src/infrastructure/harvesters/SwarmHarvester.js` | `npm run harvest:swarm` |
| **V6.0 Backfill** | `scripts/ops/gold_pilot_50.js` | `node scripts/ops/gold_pilot_50.js` |
| **TITAN Marathon** | `scripts/ops/titan_marathon.js` | `node scripts/ops/titan_marathon.js` |
| **TITAN Monitor** | `scripts/ops/titan_monitor.js` | `node scripts/ops/titan_monitor.js` |
| **TITAN Seeder** | `scripts/ops/titan_seeder.js` | `node scripts/ops/titan_seeder.js` |
| **L2 Recon** | `scripts/ops/recon_scanner.js` | `node scripts/ops/recon_scanner.js` |
| **OddsPortal Harvester** | `src/infrastructure/harvesters/OddsPortalHarvester.js` | - |
| **OddsPortal Parser** | `src/infrastructure/harvesters/OddsPortalParser.js` | - |
| **TitanSlimHarvester** | `src/infrastructure/harvesters/TitanSlimHarvester.js` | - |
| **ProxyRotator** | `src/infrastructure/harvesters/ProxyRotator.js` | - |
| **StealthNavigator** | `src/infrastructure/harvesters/StealthNavigator.js` | - |
| **SessionWarmer** | `src/infrastructure/harvesters/SessionWarmer.js` | - |
| **Checkpointer** | `src/infrastructure/harvesters/Checkpointer.js` | - |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `npm run smelt` |
| **Sentinel** | `src/infrastructure/monitoring/Sentinel.js` | `npm run titan:watch` |
| **OddsFluxDetector** | `src/analysis/OddsFluxDetector.js` | V5.0 算法模块 |
| **TITAN Cruise** | `scripts/ops/titan_cruise_control.py` | 全自动巡航 |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **TITAN 模型** | `src/ml/inference/predictor.py` | `npm run predict` |
| **H2H Estimator** | `src/ml/feature_engine/h2h_estimator.py` | H2H 智能补位 |
| **统一配置** | `src/config_unified.py` / `config/factory_config.js` | - |
| **StructuredLogger** | `src/utils/StructuredLogger.js` | V4.0 模块化日志 |

---

## 4. 项目结构

```
FootballPrediction/
├── config/                      # 配置中心
│   ├── factory_config.js        # 工厂级配置（所有魔术数字归口）
│   ├── constants.js             # 业务常量
│   ├── database.js              # 数据库配置
│   ├── registry.js              # 代理注册表（22端口配置）
│   ├── shared_constants.js      # 共享常量定义
│   ├── season_windows.json      # 赛季窗口配置
│   └── leagues.json             # 联赛配置
├── scripts/
│   ├── ops/                     # 运维脚本
│   │   ├── run_production.js    # 生产收割主入口
│   │   ├── seed_fixtures.js     # L1 赛程种子
│   │   ├── titan_discovery.js   # V6.7 L1 发现引擎
│   │   ├── titan_marathon.js    # TITAN 长时运行支持
│   │   ├── titan_monitor.js     # TITAN 监控器
│   │   ├── titan_seeder.js      # TITAN 种子器
│   │   ├── recon_scanner.js     # L2 侦察扫描器
│   │   ├── smelt_all.js         # L3 特征熔炼
│   │   ├── smelt_v5_turbo.js    # V5 Turbo 熔炼
│   │   ├── swarm_test.js        # Swarm 蜂群收割
│   │   ├── hyper_swarm.js       # 超 Swarm 引擎
│   │   ├── gold_pilot_50.js     # V6.0 黄金批次执行器
│   │   ├── titan_grand_backfill.js # TITAN 大回填
│   │   ├── p2p_harvest_v38.js   # P2P 收割 v38
│   │   ├── sentinel_watch.js    # 哨兵监控
│   │   ├── check_health.js      # 健康检查
│   │   ├── titan_cruise_control.py  # 全自动巡航控制器
│   │   ├── train_model.py       # 模型训练
│   │   ├── predict_pipeline.py  # 预测管道
│   │   └── titan_daily_ops.sh   # 一键运维脚本
│   ├── maintenance/             # 维护工具
│   │   ├── integrity_guard.py   # 数据完整性守护
│   │   ├── recalculate_elo.js   # ELO 重新计算
│   │   ├── check_system_health.py
│   │   └── show_today_summary.py # 终端作战简报
│   └── tools/                   # 工具脚本
├── src/
│   ├── core/                    # 核心基础设施
│   │   ├── browser/             # 浏览器自动化
│   │   ├── database/            # 数据库核心
│   │   ├── harvesters/          # 收割引擎核心
│   │   ├── math/                # 数学工具
│   │   └── network/             # 网络核心
│   ├── parsers/                 # 数据解析器
│   ├── feature_engine/          # 特征引擎
│   │   ├── elo/                 # ELO 评分系统
│   │   ├── extractors/          # 特征提取器
│   │   │   └── MarketSentimentExtractor.js
│   │   └── smelter/             # 特征熔炼器
│   ├── analysis/                # V5.0+ 分析算法
│   ├── strategy/                # 策略模块（Kelly准则）
│   ├── infrastructure/          # 基础设施
│   │   ├── harvesters/          # 收割引擎
│   │   │   ├── base/            # 基础类
│   │   │   ├── components/      # 组件
│   │   │   ├── strategies/      # 策略
│   │   │   ├── workers/         # Worker 池
│   │   │   ├── ProductionHarvester.js
│   │   │   ├── SwarmHarvester.js
│   │   │   ├── TitanSlimHarvester.js
│   │   │   ├── OddsPortalHarvester.js
│   │   │   ├── OddsPortalParser.js
│   │   │   ├── ProxyRotator.js
│   │   │   ├── StealthNavigator.js
│   │   │   ├── SessionWarmer.js
│   │   │   └── Checkpointer.js
│   │   ├── network/             # 网络与代理
│   │   ├── monitoring/          # 监控与哨兵
│   │   ├── database/            # 数据库操作
│   │   ├── browser/             # 浏览器自动化
│   │   └── auth/                # 认证管理
│   ├── ml/                      # 机器学习
│   │   ├── inference/           # 模型推理
│   │   │   └── titan_loader.py  # TITAN 模型加载器
│   │   ├── feature_engine/      # Python 特征工程
│   │   │   └── h2h_estimator.py # H2H 智能补位引擎
│   │   └── models/              # 模型定义
│   ├── database/                # 数据库模型
│   │   └── repositories/        # 数据仓储层
│   ├── schemas/                 # Pydantic Schema
│   ├── services/                # 业务服务层
│   ├── config/                  # 配置模块
│   ├── constants/               # 常量定义
│   │   └── model_config.py      # 模型配置常量唯一源
│   ├── api/                     # API 接口
│   ├── utils/                   # 工具函数
│   │   └── StructuredLogger.js  # V4.0 结构化日志器
│   ├── data/                    # 数据层
│   └── config_unified.py        # 统一配置入口
├── tests/                       # 测试文件
│   ├── unit/                    # 单元测试（70+ 测试用例）
│   ├── integration/             # 集成测试
│   ├── integrity/               # 完整性测试
│   └── fixtures/                # 测试数据
├── models/                      # 生产模型文件
│   ├── TITAN_CORE_V5_PROD.joblib
│   ├── TITAN_CORE_V5_PROD_scaler.joblib
│   ├── TITAN_CORE_V5_PROD_metadata.json
│   └── archive/                 # 归档模型
├── docs/                        # 文档中心
│   ├── ops/                     # 运维文档
│   ├── architecture/            # 架构文档
│   ├── adr/                     # 架构决策记录 (ADR)
│   │   ├── ADR-001-Source-Level-Data-Hardening.md
│   │   └── ADR-002-L2-Raw-Storage-Hardening.md
│   └── harvesters/              # 收割器文档
├── .claude/                     # Claude Skills 约束体系
│   ├── skills/                  # 专用技能（12个）
│   ├── minimal_change.skill.md
│   ├── architecture_boundary.skill.md
│   ├── test_guard.skill.md
│   ├── context_lock.skill.md
│   └── change_impact.skill.md
├── Makefile                     # V51.0 指挥塔
├── CLAUDE.md                    # AI 助手详细操作指南
├── COMMAND_CENTER.md            # 数字化指挥中心
├── AGENTS.md                    # 本文件
└── VERSION                      # 版本锚点
```

---

## 5. 开发环境搭建

### 5.1 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 DB_PASSWORD

# 3. 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 4. 进入容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 5. 运行生产收割
npm start
```

### 5.2 核心命令

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器（L2/L3） |
| `npm run seed` | L1 赛程种子 |
| `npm run seed:all` | L1 全量赛程种子 |
| `npm run smelt` | L3 特征熔炼 |
| `npm run harvest` | Hyper Swarm 收割 |
| `npm run harvest:swarm` | Swarm 蜂群收割（Worker 池化） |
| `npm run titan:start` | TITAN 完整工作流 |
| `npm run titan:sync` | 同步历史数据 |
| `npm run titan:watch` | 启动哨兵监控 |
| `npm run titan:check` | 健康检查 |
| `npm run titan:audit` | 数据集审计 |
| `npm run titan:clean` | 归档历史文件 |
| `npm run predict` | 生成预测报告 |
| `npm run predict:dry` | 试运行模式（不写入数据库） |
| `npm run predict:json` | JSON 格式输出 |
| `npm run train` | 训练 TITAN 模型 |
| `npm run train:fast` | 快速训练（参数减少） |
| `npm run train:deep` | 深度训练（参数增加） |
| `npm test` | 运行单元测试 |
| `npm run qa` | 全量检查（lint + test） |
| `npm run elo:recalc` | 重新计算 ELO |
| `npm run elo:incremental` | 增量更新 ELO |

### 5.3 V6.7 L1 发现引擎命令

```bash
# V6.7 L1 发现引擎（Project Hound）
node scripts/ops/titan_discovery.js

# TITAN Marathon 长时运行
node scripts/ops/titan_marathon.js

# TITAN 监控器
node scripts/ops/titan_monitor.js

# TITAN 种子器
node scripts/ops/titan_seeder.js
```

### 5.4 V6.0 回填命令

```bash
# 运行 Gold Pilot 50 回填
node scripts/ops/gold_pilot_50.js

# 运行 TITAN 大回填
node scripts/ops/titan_grand_backfill.js

# P2P 收割（v38）
node scripts/ops/p2p_harvest_v38.js

# 批量导入比赛
node scripts/ops/bulk_import_matches.js

# 查看回填进度
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "SELECT * FROM backfill_progress;"
```

### 5.5 Makefile 快捷命令

```bash
# 开发环境管理
make dev-up          # 启动开发容器
make dev-down        # 停止开发容器
make dev-shell       # 进入开发容器 Shell
make dev-logs        # 查看开发容器日志
make dev-harvest     # 在容器中运行生产收割

# 数据库操作
make db-shell        # 进入 PostgreSQL Shell
make db-backup       # 备份数据库

# 质量检查
make lint            # 运行 Lint 检查
make format          # 格式化代码
make test            # 运行测试
make verify          # 运行完整验证
make security        # 运行安全扫描

# 监控
make health          # 检查服务健康状态
make dashboard       # 启动战神仪表盘
```

---

## 6. 工程铁律

### 6.1 五大核心规则

1. **沟通协议**：所有回复、注释、日志必须使用**中文**
2. **容器化优先**：**禁止**在宿主机直接运行 Node/Python，所有操作在 Docker 容器内执行
3. **分支管理**：严禁在 `main` 分支开发，分支命名：`feat/<功能>` / `lab/<实验>` / `fix/<修复>` / `refactor/<重构>` / `chore/<杂务>`
4. **数据完整性**：**零模拟原则**，严禁使用 `Math.random()` 伪造数据
5. **幂等性**：所有收割任务支持重复执行，已存在的完整数据应跳过

### 6.2 V4.51 架构规范

- **配置唯一源**: `src/config_unified.py` / `config/factory_config.js` / `config/registry.js`
- **数学能力**: `src/core/math/` (finance, evaluator)
- **动态能力**: `src/core/` (Math, Database, Types)
- **预测大脑**: `src/ml/`
- **分析算法**: `src/analysis/`
- **策略模块**: `src/strategy/`
- **基础设施**: `src/infrastructure/`
- **回填系统**: `scripts/ops/gold_pilot_50.js` + `src/infrastructure/harvesters/OddsPortalHarvester.js`
- **代理轮询**: `src/infrastructure/harvesters/ProxyRotator.js` (22端口)
- **断点续传**: `src/infrastructure/harvesters/Checkpointer.js`
- **唯一数据**: `src/database/`
- **日志系统**: `src/utils/StructuredLogger.js`
- **架构决策**: `docs/adr/` (ADR-001, ADR-002)

### 6.3 黄金准则（V4.51+）

- **测试覆盖率**: 80% 熔断阈值
- **静态质量**: 0 Error 容忍
- **文档规范**: JSDoc 完整注释 + ADR 架构决策记录
- **模块化**: 单一职责，高内聚低耦合
- **V6.7 加固**: L1/L2 双引擎工业化，断路器保护，100% 测试覆盖

### 6.4 Skills 约束体系

项目已配置 5 个核心 RED 约束 Skills：

| 约束等级 | Skill | 用途 |
|----------|-------|------|
| 🔴 RED | `minimal_change` | 最小修改策略 |
| 🔴 RED | `architecture_boundary` | 架构边界保护 |
| 🔴 RED | `test_guard` | 测试质量保护 |
| 🔴 RED | `context_lock` | 核心模块冻结 |
| 🔴 RED | `change_impact` | 变更影响分析 |

详细说明见 `.claude/README.md`

---

## 7. 常用开发命令

### 7.1 核心收割流程

```bash
# L1: 赛程种子 (V6.7 Project Hound)
docker-compose -f docker-compose.dev.yml exec dev npm run seed

# L1: V6.7 发现引擎
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/titan_discovery.js

# L2: 数据收割
docker-compose -f docker-compose.dev.yml exec dev npm start

# Swarm 蜂群收割（推荐，多 Worker 并发）
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:swarm

# L3: 特征熔炼
docker-compose -f docker-compose.dev.yml exec dev npm run smelt

# V6.0: 历史回填
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/gold_pilot_50.js

# TITAN 完整工作流（高阶）
npm run titan:start
```

### 7.2 代码质量

```bash
# ESLint 检查
npm run lint

# ESLint 自动修复
npm run lint:fix

# Prettier 格式化
npm run format

# Python Ruff 检查
npm run lint:python

# Python 格式化
npm run format:python

# Markdown 检查
npm run lint:md

# 全量检查
npm run qa
make verify
```

### 7.3 测试

```bash
# Node.js 单元测试
npm test
npm run test:unit

# 指定测试文件
npm run test:l1

# 集成测试
npm run test:integration

# 覆盖率测试
npm run test:coverage

# Python 测试
pytest tests/ -v
```

### 7.4 数据库操作

```bash
# 进入 PostgreSQL Shell
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db
make db-shell

# 数据库备份
make db-backup

# 查看数据层级状态
npm run status:db

# 查看回填进度
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "SELECT match_id, status, retry_count FROM backfill_progress ORDER BY updated_at DESC LIMIT 10;"
```

### 7.5 监控与运维

```bash
# 启动监控栈（Prometheus + Grafana）
npm run monitor:up

# 停止监控
npm run monitor:down

# 启动哨兵监控
npm run titan:watch

# 健康检查
npm run titan:check
npm run status:health
make health

# 启动战神仪表盘
make dashboard
```

### 7.6 模型操作

```bash
# 训练模型
npm run train

# 快速训练（参数减少）
npm run train:fast

# 深度训练（参数增加）
npm run train:deep

# 生成预测
npm run predict

# 试运行模式（不写入数据库）
npm run predict:dry

# JSON 格式输出
npm run predict:json
```

---

## 8. 关键配置

### 8.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_PASSWORD` | 数据库密码（**必填**） | - |
| `DB_HOST` | 数据库主机 | `host.docker.internal` |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_NAME` | 数据库名称 | `football_db` |
| `DB_USER` | 数据库用户 | `football_user` |
| `REDIS_HOST` | Redis 主机 | `host.docker.internal` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `MAX_WORKERS` | Worker 数量 | `1` |
| `MIN_DELAY_MS` | 最小延时（ms） | `10000` |
| `MAX_DELAY_MS` | 最大延时（ms） | `15000` |
| `PROXY_HOST` | 代理服务器地址 | `172.25.16.1` |
| `LOG_LEVEL` | 日志级别 | `info` |
| `SWARM_CONCURRENCY` | Swarm 并发数 | `3` |

### 8.2 22端口代理池配置（V6.0）

代理端口范围: 7890 - 7911 (共22个端口)
策略: Round-Robin (轮询)
健康检查: 每100场自动检查
冷却机制: 403错误自动冷却5分钟

```javascript
// config/registry.js
const PROXIES = {
  getAllPorts: () => [
    7890, 7891, 7892, 7893, 7894,
    7895, 7896, 7897, 7898, 7899,
    7900, 7901, 7902, 7903, 7904,
    7905, 7906, 7907, 7908, 7909,
    7910, 7911
  ]
};
```

### 8.3 配置系统

所有配置集中在 `src/config_unified.py` / `config/factory_config.js` / `config/registry.js`，**严禁在业务代码中硬编码参数**。

```javascript
// Node.js 使用示例
const FactoryConfig = require('../../../config/factory_config');
const delay = FactoryConfig.getRandomDelay([FactoryConfig.TIMING.minDelayMs, FactoryConfig.TIMING.maxDelayMs]);
```

```python
# Python 使用示例
from src.config_unified import settings
from src.config_unified import DatabaseConfig
```

---

## 9. 故障排查

| 问题 | 诊断命令 | 解决方案 |
|------|---------|----------|
| **代理熔断** | `curl -x http://172.25.16.1:7890 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |
| **Redis 连接** | `docker-compose exec redis redis-cli ping` | `docker-compose restart redis` |
| **Swarm 挂起** | `npm run titan:check` | 检查 `sentinel_watch.js` 日志 |
| **回填中断** | `docker-compose exec db psql -U football_user -d football_db -c "SELECT match_id, status FROM backfill_progress WHERE status = 'failed';"` | 重新运行 `gold_pilot_50.js`，自动断点续传 |
| **代理403错误** | 检查代理健康状态 | 等待5分钟冷却或切换代理端口 |
| **L1 发现失败** | `npm run test:l1` | 检查断路器状态和 API 响应 |

---

## 10. 数据库表结构

| 表名 | 用途 | 数据层级 |
|------|------|----------|
| `matches` | 比赛基础信息 | L1 |
| `raw_match_data` | L2 原始数据（JSONB 赔率） | L2 |
| `l2_match_data` | L2 结构化数据 | L2 |
| `l3_features` | 特征向量（11维纯净特征 + market_sentiment） | L3 |
| `predictions` | 预测结果 | - |
| `team_elo_ratings` | 球队 Elo 评分 | - |
| `backfill_progress` | V6.0 回填进度跟踪 | - |

**常用查询：**

```sql
-- 查看待收割比赛
SELECT match_id, home_team, away_team, match_time
FROM matches
WHERE l2_harvested = false;

-- 查看高置信度预测
SELECT * FROM predictions
WHERE final_confidence > 0.65
ORDER BY match_time;

-- 查看数据层级统计
SELECT
    COUNT(*) FILTER (WHERE l2_harvested = false) as pending_l2,
    COUNT(*) FILTER (WHERE l2_harvested = true) as completed_l2
FROM matches
WHERE match_date >= NOW()
  AND match_date < NOW() + INTERVAL '4 days';

-- 查看回填进度（V6.0）
SELECT 
    status,
    COUNT(*) as count,
    MAX(updated_at) as last_update
FROM backfill_progress
GROUP BY status;

-- 查看市场情绪分布（V6.0）
SELECT 
    market_sentiment,
    COUNT(*) as count,
    AVG(home_elo_pre) as avg_home_elo
FROM l3_features
WHERE market_sentiment IS NOT NULL
GROUP BY market_sentiment;
```

---

## 11. TITAN 模型系统

### 11.1 模型架构

| 组件 | 描述 |
|------|------|
| **核心模型** | XGBoost 3.1+ 分类器 |
| **特征维度** | 11维纯净特征（Elo + 身价 + H2H）+ market_sentiment |
| **准确率** | 65.31%（测试集）/ 67.94%（5折交叉验证） |
| **F1 Score** | 0.6371 |
| **Log Loss** | 0.9834 |
| **模型加载器** | `src/ml/inference/titan_loader.py` |

### 11.2 11维特征组成

| 类别 | 特征 | 说明 |
|------|------|------|
| **Elo特征 (5维)** | `home_elo_pre`, `away_elo_pre`, `elo_diff`, `expected_home_win`, `expected_away_win` | 球队实力核心指标 |
| **身价特征 (3维)** | `log_home_squad_value`, `log_away_squad_value`, `home_mv_share` | 阵容价值量化 |
| **H2H特征 (3维)** | `h2h_home_win_ratio`, `h2h_draw_ratio`, `h2h_avg_goal_diff` | 历史对战优势 |
| **市场情绪 (V6.0)** | `market_sentiment` | 赔率市场 sentiment 分析 |

### 11.3 特征重要性

| 排名 | 特征 | 重要性 |
|------|------|--------|
| 1 | elo_diff | 64.66% |
| 2 | away_score | 14.27% |
| 3 | home_score | 13.72% |
| 4 | total_goals | 7.36% |

### 11.4 EV 计算算法

```
EV = P × Odds - 1

# 无赔率时的保守估算
if p > 0.70:    ev = min(0.10, theoretical_ev + 0.05)
elif p > 0.60:  ev = min(0.05, theoretical_ev + 0.02)
elif p > 0.50:  ev = min(0.03, theoretical_ev)
elif p > 0.40:  ev = max(-0.05, theoretical_ev - 0.02)
else:           ev = max(-0.10, theoretical_ev - 0.05)
```

---

## 12. V5.0+ 新功能

### 12.1 OddsFluxDetector - 赔率背离监测器

**文件**: `src/analysis/OddsFluxDetector.js`

TITAN V5.0 首个预测算法模块，用于实时监测赔率异常波动和市场背离信号。

**核心功能**:
- 赔率偏差检测（deviation detection）
- 市场信号分析（market signals）
- 凯利准则建议（Kelly criterion）
- 价值投注识别（value bets）

### 12.2 TITAN Cruise Control - 全自动巡航控制器

**文件**: `scripts/ops/titan_cruise_control.py`

实现无人值守运行，支持 cron 定时调度。

**核心功能**:
- 定时任务调度
- 熔断保护（连续 3 次失败自动熔断，1 小时后重置）
- 日志轮转
- 健康检查

### 12.3 H2H 智能补位引擎

**文件**: `src/ml/feature_engine/h2h_estimator.py`

解决 H2H 冷启动问题，基于 Elo 差值线性推演，消除 H2H 数据缺失阻塞。

### 12.4 MarketSentimentExtractor（V6.0）

**文件**: `src/feature_engine/extractors/MarketSentimentExtractor.js`

从 OddsPortal 数据中提取市场情绪特征，用于模型输入。

### 12.5 TITAN Loader（V4.47）

**文件**: `src/ml/inference/titan_loader.py`

TITAN 模型统一加载器，支持模型版本管理和元数据验证。

---

## 13. V6.0 回填系统

### 13.1 架构概述

V6.0 回填系统是针对历史数据补全的专用流水线，采用 P0级架构加固：

**核心组件**:
- **Gold Pilot 50**: 批次调度执行器
- **TITAN Grand Backfill**: 大回填执行器
- **ProxyRotator**: 22端口代理轮询
- **OddsPortalHarvester**: Playwright 真实页面抓取
- **Checkpointer**: 断点续传与状态持久化

### 13.2 关键特性

| 特性 | 说明 |
|------|------|
| **22端口代理池** | 7890-7911 轮询，自动健康检查 |
| **断点续传** | 中断后自动恢复，不重复处理 |
| **限流控制** | 防止请求过载，自适应延时 |
| **熔断机制** | 连续失败自动冷却，保护代理池 |
| **实时存盘** | 每场比赛状态实时持久化 |
| **P2P Harvest** | v38 点对点收割协议 |

### 13.3 运行方式

```bash
# 标准回填（50场批次）
node scripts/ops/gold_pilot_50.js

# TITAN 大回填
node scripts/ops/titan_grand_backfill.js

# P2P 收割（v38）
node scripts/ops/p2p_harvest_v38.js

# 查看回填进度
```

### 13.4 监控回填状态

```sql
-- 查看各状态数量
SELECT status, COUNT(*) FROM backfill_progress GROUP BY status;

-- 查看失败任务
SELECT match_id, error_message, retry_count 
FROM backfill_progress 
WHERE status = 'failed' 
ORDER BY updated_at DESC;

-- 查看最近完成的
SELECT match_id, completed_at 
FROM backfill_progress 
WHERE status = 'completed' 
ORDER BY completed_at DESC 
LIMIT 10;
```

---

## 14. 测试体系

### 14.1 测试结构

| 目录 | 用途 | 数量 |
|------|------|------|
| `tests/unit/` | 单元测试 | 70+ 测试用例 |
| `tests/integration/` | 集成测试 | - |
| `tests/integrity/` | 完整性测试 | - |
| `tests/fixtures/` | 测试数据 | - |

### 14.2 核心测试文件

- `StructuredLogger.test.js` - 结构化日志器测试
- `Smelter_Audit.test.js` - Smelter 审计测试
- `FeatureSmelter.test.js` - 特征熔炼器测试
- `ProductionHarvester.test.js` - 生产收割器测试
- `ProductionHarvester_Deep.test.js` - 生产收割器深度测试
- `SentinelWatch.test.js` - 哨兵监控测试
- `JSON_Integrity.test.js` - JSON 完整性测试
- `BackfillFortification.test.js` - 回填加固测试
- `BackfillResilience.test.js` - 回填韧性测试
- `OddsPortalHarvester_V55.test.js` - OddsPortal 收割器测试
- `Golden_Injection_Verify.test.js` - 黄金注入验证测试
- `Local_Rendering_Integrity.test.js` - 本地渲染完整性测试
- `Real_Data_Extraction.test.js` - 真实数据提取测试
- `Residential_Stealth.test.js` - 住宅隐身测试
- `Zero_Placeholder_Diversity.test.js` - 零占位符多样性测试
- `parser_regression.test.js` - 解析器回归测试
- `purity_filter.test.js` - 纯净过滤器测试
- `recovery_injection.test.js` - 恢复注入测试
- `schema_design_validator.test.js` - Schema设计验证器测试
- `sniffer_interceptor.test.js` - 嗅探拦截器测试
- `stealth_hardening.test.js` - 隐身加固测试
- `MarketSentimentExtractor.test.js` - 市场情绪提取器测试
- `DrawPropensityExtractor.test.js` - 平局倾向提取器测试
- `EfficiencyFeatureExtractor.test.js` - 效率特征提取器测试
- `TacticalMomentumExtractor.test.js` - 战术动量提取器测试
- `RollingFeatureExtractor.test.js` - 滚动特征提取器测试
- `XGExtractor.test.js` - 预期进球提取器测试
- `EV_Calculation_Engine.test.js` - EV 计算引擎测试
- `OddsFluxDetector.test.js` - 赔率背离检测器测试
- `ErrorAuditor.test.js` - 错误审计器测试
- `ErrorHandler.test.js` - 错误处理器测试
- `SessionManager.test.js` - 会话管理器测试
- `BrowserFactory.test.js` - 浏览器工厂测试
- `MatchDetailEngine.test.js` - 比赛详情引擎测试
- `AutoAuthManager.test.js` - 自动认证管理器测试
- `Dispatcher.test.js` - 调度器测试
- `Persistence.test.js` - 持久化测试
- `SafeAccess.test.js` - 安全访问测试
- `StressAndSecurity.test.js` - 压力与安全测试
- `ZombieKiller.test.js` - 僵尸进程清理测试
- `DataIntegrity.test.js` - 数据完整性测试
- `FixtureSeeder.test.js` - 赛程种子测试
- `FixtureSeederV5.test.js` - V5 赛程种子测试
- `DiscoveryService.test.js` - 发现服务测试 (V6.7)
- `AuditDataset.test.js` - 数据集审计测试
- `AbstractHarvester.test.js` - 抽象收割器测试
- `Extractors_V4.test.js` - V4提取器测试
- `SmelterComponents_V4.test.js` - V4 Smelter组件测试
- `StrategyParser.test.js` - 策略解析器测试
- `TitanFullRegistry.test.js` - TITAN完整注册表测试
- `Parsing_Core.test.js` - 解析核心测试
- `Body_Stamina.test.js` - 身体耐力测试
- `Error_Nerves.test.js` - 错误神经测试
- `MatchValidator.test.js` - 比赛验证器测试
- `TitanSlimHarvester.test.js` - TitanSlim 收割器测试
- `Normalizer.test.js` - 标准化器测试 (V6.7)
- `L2_Normalizer_Persistence.test.js` - L2 持久化测试 (V6.7)

### 14.3 测试运行

```bash
# 运行所有测试
npm test

# 运行指定测试
node --test tests/unit/StructuredLogger.test.js

# Python 测试
pytest tests/ -v
```

---

## 15. 相关文档

### 15.1 核心文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南 |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 数字化指挥中心 |
| [HANDOVER.md](./HANDOVER.md) | 项目交接文档 |
| [MIGRATION.md](./MIGRATION.md) | 迁移指南 |

### 15.2 架构文档

| 文档 | 说明 |
|------|------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 系统架构详述 |
| [docs/ENGINE_ARCHITECTURE.md](./docs/ENGINE_ARCHITECTURE.md) | 引擎架构 |
| [docs/MCP_ARCHITECTURE.md](./docs/MCP_ARCHITECTURE.md) | MCP 架构文档 |
| [docs/L1_DISCOVERY_ENGINE.md](./docs/L1_DISCOVERY_ENGINE.md) | L1 发现引擎文档 |
| [docs/L1_INDEX_LAYER_SPEC.md](./docs/L1_INDEX_LAYER_SPEC.md) | L1 索引层规格 |

### 15.3 运维文档

| 文档 | 说明 |
|------|------|
| [docs/OPERATIONS_MANUAL.md](./docs/OPERATIONS_MANUAL.md) | 运维手册 |
| [docs/OPERATIONS_RUNBOOK.md](./docs/OPERATIONS_RUNBOOK.md) | 运维运行手册 |
| [docs/OPERATIONS_SOP.md](./docs/OPERATIONS_SOP.md) | 运维标准作业程序 |
| [docs/ops/backfill_v6_manual.md](./docs/ops/backfill_v6_manual.md) | V6.0 回填系统操作手册 |
| [docs/SYSTEM_STABILITY_GUIDE.md](./docs/SYSTEM_STABILITY_GUIDE.md) | 系统稳定性指南 |

### 15.4 技术规格

| 文档 | 说明 |
|------|------|
| [docs/TITAN_V5.2_TECHNICAL_SPEC.md](./docs/TITAN_V5.2_TECHNICAL_SPEC.md) | V5.2 技术规格 |
| [docs/MODEL_V4_ANATOMY.md](./docs/MODEL_V4_ANATOMY.md) | V4 模型解剖学报告 |
| [docs/SMELTER_REFACTOR_PLAN.md](./docs/SMELTER_REFACTOR_PLAN.md) | Smelter V4.0 重构计划 |
| [docs/xgboost_optimization_guide.md](./docs/xgboost_optimization_guide.md) | XGBoost 优化指南 |

### 15.5 架构决策记录 (ADR)

| 文档 | 说明 |
|------|------|
| [docs/adr/ADR-001-Source-Level-Data-Hardening.md](./docs/adr/ADR-001-Source-Level-Data-Hardening.md) | 源级数据加固 |
| [docs/adr/ADR-002-L2-Raw-Storage-Hardening.md](./docs/adr/ADR-002-L2-Raw-Storage-Hardening.md) | L2 原始存储加固 |

### 15.6 审计与报告

| 文档 | 说明 |
|------|------|
| [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md) | V3.1-STABLE 穿透审计报告 |
| [docs/FORENSIC_AUDIT_REPORT.md](./docs/FORENSIC_AUDIT_REPORT.md) | 法医审计报告 |
| [docs/GITHUB_ACTIONS_AUDIT_REPORT.md](./docs/GITHUB_ACTIONS_AUDIT_REPORT.md) | GitHub Actions 审计 |
| [docs/FINGERPRINT_EXTRACTOR.md](./docs/FINGERPRINT_EXTRACTOR.md) | 指纹提取器文档 |

---

## 16. 助手行为准则

### 16.1 代码修改原则

1. **先读后改**：从不修改未读过的代码
2. **最小变更**：只做必要的修改，不过度重构
3. **测试验证**：修改后运行相关测试
4. **中文优先**：所有注释、日志使用中文

### 16.2 安全守则

1. **绝不引入**：XSS、SQL 注入、命令注入等安全漏洞
2. **边界校验**：只在系统边界（用户输入、外部 API）做验证
3. **信任内部**：信任内部代码和框架保证

### 16.3 禁止行为

- 不在 `main` 分支直接开发
- 不在宿主机直接运行 Node/Python
- 不使用 `Math.random()` 伪造数据
- 不创建不必要的抽象和工具函数
- 不添加未请求的功能
- 不硬编码配置参数

---

## 17. MCP 服务器权限

| MCP 服务器 | 权限 | 允许行为 |
|-----------|------|----------|
| **postgres** | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| **filesystem** | PROJECT ROOT | 读 / diff / 受控写 |
| **git** | READ-ONLY | commit history / diff / blame |
| **pytest** | RESTRICTED | 运行 pytest / 列出测试 |

> ⚠️ **MCP 不拥有生产环境控制权**，禁止任何不可逆或高风险自动化操作。

---

## 18. 近期更新（V4.51.2-TOTAL-WAR）

### 18.1 V6.7 L1 发现引擎 - Project Hound（2026-03-22）

**核心交付**: L1 工业级重构，断路器保护与 100% 测试覆盖

**新组件**:
- ✅ `titan_discovery.js` - V6.7 L1 发现引擎
- ✅ `titan_seeder.js` - TITAN 种子器
- ✅ `DiscoveryService.test.js` - 发现服务测试
- ✅ `Normalizer.test.js` - 标准化器测试
- ✅ `L2_Normalizer_Persistence.test.js` - L2 持久化测试
- ✅ 断路器模式实现
- ✅ 100% 测试覆盖率
- ✅ 自动故障恢复

### 18.2 V6.6 L2 引擎工业化加固（2026-03-20）

**核心交付**: TITAN L2 引擎工业化加固

- ✅ L2 收割引擎性能优化
- ✅ 模糊匹配逻辑强化
- ✅ 数据一致性保障

### 18.3 V6.5 L1 加固完成（2026-03-19）

**核心交付**: L1 层完整加固

- ✅ 标准化 1900+ EPL 赛程
- ✅ 数据库触发器/约束
- ✅ ADR-001/002 架构决策记录注入

### 18.4 V6.4 L2 侦察扫描器（2026-03-19）

**核心交付**: 成功将高级模糊匹配逻辑合并到 v6.4 基础设施

- ✅ `recon_scanner.js` - L2 侦察扫描器
- ✅ 模糊匹配逻辑集成
- ✅ 与现有 V6.0 回填流水线兼容

### 18.5 V6.0 回填系统（2026-03-15）

**核心交付**: P0级架构加固的历史数据回填系统

**新组件**:
- ✅ `gold_pilot_50.js` - 批次调度执行器
- ✅ `titan_grand_backfill.js` - 大回填执行器
- ✅ `ProxyRotator.js` - 22端口代理轮询
- ✅ `OddsPortalHarvester.js` - Playwright 真实抓取
- ✅ `Checkpointer.js` - 断点续传机制
- ✅ `backfill_progress` 表 - 回填状态跟踪
- ✅ `MarketSentimentExtractor.js` - 市场情绪提取

### 18.6 Worker 池化架构（V4.46.4+）

**性能提升**:
- 浏览器启动次数减少 99%
- Worker 初始化减少 99%
- 单场平均耗时减少 65%
- 吞吐量提升 3.75x

### 18.7 V5.5 EV 引擎与赔率撞表（2026-03-10）

**核心交付**: 实时估值引擎

- ✅ EV 引擎自动化
- ✅ 赔率撞表系统
- ✅ 价值投注识别

### 18.8 V5.2 主客场感知升级（2026-03-08）

**核心交付**: 主客场感知升级与特征交互

- ✅ 主客场特征增强
- ✅ 特征交互优化
- ✅ RollingFeatureExtractor

---

## 19. Claude Skills 体系

### 19.1 核心约束 Skills（5个 RED 等级）

| Skill | 用途 | 说明 |
|-------|------|------|
| `minimal_change` | 最小修改策略 | 防止过度重构 |
| `architecture_boundary` | 架构边界保护 | 维护层次结构 |
| `test_guard` | 测试质量保护 | 确保测试价值 |
| `context_lock` | 核心模块冻结 | 保护系统基石 |
| `change_impact` | 变更影响分析 | 评估修改影响 |

### 19.2 专用 Skills（12个）

位于 `.claude/skills/` 目录：

| 类别 | Skills |
|------|--------|
| **核心业务** | football-prediction, report-generation, machine-learning-engineering, data-collection |
| **运维支撑** | performance-monitoring, deployment-management, database-operations |
| **开发工具** | code-quality, api-testing, data-engineering, docker-devops, fastapi-development |

详细说明见 `.claude/README.md`

---

**维护者**: V174 Engineering Team  
**许可证**: MIT License  
**最后更新**: 2026-03-22