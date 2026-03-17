# FootballPrediction - AI 助手指令上下文

> **系统版本**: V6.0.0-PRODUCTION | **最后更新**: 2026-03-17
>
> 本文档为 AI 助手提供项目背景、架构理解和操作指南，用于快速上手和高效协作。

---

## 1. 项目概述

### 1.1 项目定位

**FootballPrediction** (V4.51.2-TOTAL-WAR / V6.0.0-PRODUCTION) 是一个工业级足球预测平台，采用双语言（Node.js + Python）四层架构，通过多源数据采集、C++ 模糊匹配和 XGBoost 多模型共识，实现高精度的比赛预测。

### 1.2 核心能力

| 模块 | 技术实现 | 说明 |
|------|----------|------|
| **L1 Discovery** | FotMob API | 自动发现未来 7 天比赛 |
| **L2 Harvest** | FotMob Details + OddsPortal + 22 节点代理池 | 赔率数据采集（开盘/收盘/1X2/亚洲盘） |
| **L3 Smelt** | FeatureSmelter V5.0-TURBO | 11维纯净战斗特征向量 |
| **ML Prediction** | XGBoost TITAN 模型 | 65.31% 准确率，<100ms 响应 |
| **OddsFluxDetector** | V5.0 赔率背离算法 | 实时监测赔率异常波动 |
| **Swarm Harvest** | Hyper Swarm 引擎 | 多 Worker 并发收割，吞吐量提升 3.75x |
| **V6.0 Backfill** | OddsPortal 回填系统 | 历史数据回填，22端口代理轮询 |
| **Stealth Navigator** | Playwright Stealth 强化 | 反检测页面导航 |
| **Session Warmer** | 智能会话预热 | 自动保持会话活性 |
| **Sentinel** | 哨兵监控系统 | 自动停机与熔断保护 |
| **TITAN Cruise Control** | 全自动巡航控制器 | 无人值守定时任务调度 |

### 1.3 质量认证

- **零模拟数据**：所有数据来自真实 API
- **幂等收割**：支持重复执行，自动跳过已完成
- **架构纯净**：无冗余模块，无废弃代码
- **黄金准则**：80% 测试覆盖率熔断 + 0 Error 静态质量
- **工业级部署**：Docker 全容器化，支持生产级监控
- **V6.0 加固**：P0级架构加固，断点续传，限流控制

---

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **运行时** | Node.js 20+ / Python 3.11+ | 双语言架构 |
| **数据库** | PostgreSQL 15 | 数据存储 |
| **缓存** | Redis | 分布式锁/缓存 |
| **容器化** | Docker / docker-compose | 环境隔离 |
| **浏览器** | Playwright 1.57+ + Stealth | 页面自动化与反检测 |
| **模糊匹配** | RapidFuzz (C++) | 队名匹配 |
| **ML** | XGBoost 2.0+ / scikit-learn | 预测模型 |
| **代理** | NetworkShield / ProxyRotator | 22 节点熔断保护 + 轮询 |
| **监控** | Prometheus + Grafana | 指标采集与可视化 |
| **日志** | Winston + Daily Rotate | 结构化日志与轮转 |
| **代码质量** | ESLint + Prettier + Ruff | 静态检查与格式化 |

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

### 3.2 V6.0 回填流水线架构

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

### 3.3 数据层级

| 层级 | 数据源 | 存储表 | 说明 |
|------|--------|--------|------|
| **L1** | FotMob API | `matches` | 比赛发现、基础信息 |
| **L2** | FotMob Details + OddsPortal | `raw_match_data`, `l2_match_data` | 赔率数据（开盘/收盘/1X2/亚洲盘） |
| **L3** | 特征工程 | `l3_features` | 11维纯净特征向量 + market_sentiment |
| **ELO** | 历史比赛结果 | `team_elo_ratings` | 球队动态实力评分 |
| **预测** | XGBoost 模型 | `predictions` | 预测结果 + EV 计算 |
| **回填** | OddsPortal | `backfill_progress` | V6.0 回填进度跟踪 |

### 3.4 核心资产地图

| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/FixtureSeeder.js` | `npm run seed` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` | `npm start` |
| **Swarm Harvest** | `src/infrastructure/harvesters/SwarmHarvester.js` | `npm run harvest:swarm` |
| **V6.0 Backfill** | `scripts/ops/gold_pilot_50.js` | `node scripts/ops/gold_pilot_50.js` |
| **OddsPortal Harvester** | `src/infrastructure/harvesters/OddsPortalHarvester.js` | - |
| **OddsPortal Parser** | `src/infrastructure/harvesters/OddsPortalParser.js` | - |
| **ProxyRotator** | `src/infrastructure/network/ProxyRotator.js` | - |
| **StealthNavigator** | `src/infrastructure/harvesters/StealthNavigator.js` | - |
| **SessionWarmer** | `src/infrastructure/harvesters/SessionWarmer.js` | - |
| **Checkpointer** | `src/infrastructure/persistence/Checkpointer.js` | - |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `npm run smelt` |
| **Sentinel** | `src/infrastructure/monitoring/Sentinel.js` | `npm run titan:watch` |
| **OddsFluxDetector** | `src/analysis/OddsFluxDetector.js` | V5.0 算法模块 |
| **TITAN Cruise** | `scripts/ops/titan_cruise_control.py` | 全自动巡航 |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **TITAN 模型** | `src/ml/inference/predictor.py` | `npm run predict` |
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
│   └── leagues.json             # 联赛配置
├── scripts/
│   ├── ops/                     # 运维脚本
│   │   ├── run_production.js    # 生产收割主入口
│   │   ├── seed_fixtures.js     # L1 赛程种子
│   │   ├── smelt_all.js         # L3 特征熔炼
│   │   ├── smelt_v5_turbo.js    # V5 Turbo 熔炼
│   │   ├── smelt_v5_worker.js   # V5 Worker 熔炼
│   │   ├── smelt_v5_reburn.js   # V5 重熔模式
│   │   ├── swarm_test.js        # Swarm 蜂群收割
│   │   ├── hyper_swarm.js       # 超 Swarm 引擎
│   │   ├── gold_pilot_50.js     # V6.0 黄金批次执行器
│   │   ├── golden_pilot_5.js    # V6.0 5场黄金测试
│   │   ├── titan_golden_harvest_50.js # TITAN 50场收割
│   │   ├── pilot_3_quick.js     # 3场快速测试
│   │   ├── pilot_3_v3_quick.js  # 3场V3快速测试
│   │   ├── pilot_5_deep_gold.js # 5场深度黄金测试
│   │   ├── pilot_20.js          # 20场批次测试
│   │   ├── pilot_20_precision_lock.js # 20场精准锁定
│   │   ├── first_gold_single.js # 单场黄金测试
│   │   ├── first_gold_10.js     # 10场首次黄金测试
│   │   ├── backfill_executor.js # V6.0 回填执行器核心
│   │   ├── bulk_import_matches.js # 批量导入比赛
│   │   ├── auto_harvest_v6.js   # V6.0 自动收割
│   │   ├── sniffer_harvest_v6.js # V6.0 嗅探收割
│   │   ├── assisted_harvest.js  # 辅助收割
│   │   ├── steady_harvester.js  # 稳定收割器
│   │   ├── host_force_harvest.js # 主机强制收割
│   │   ├── host_force_harvest_demo.js # 主机强制演示
│   │   ├── precision_strike.js  # 精准打击
│   │   ├── precision_strike_v6.js # V6.0 精准打击
│   │   ├── real_fusion_fire.js  # 真实融合火力
│   │   ├── titan_main_harvester.js # TITAN 主收割器
│   │   ├── titan_api_decrypt_harvester.js # API解密收割
│   │   ├── offline_backfill_v6.js # V6.0 离线回填
│   │   ├── bet365_ultimate_redo.js # Bet365 重做
│   │   ├── sentinel_watch.js    # 哨兵监控
│   │   ├── check_health.js      # 健康检查
│   │   ├── db_heartbeat.js      # 数据库心跳
│   │   ├── metrics_server.js    # 指标服务器
│   │   ├── stress_test_50.js    # 50场压力测试
│   │   ├── stress_test_1000.js  # 1000场压力测试
│   │   ├── omni_live_audit.js   # 全量实时审计
│   │   ├── api_payload_audit.js # API负载审计
│   │   ├── raw_api_dumper.js    # 原始API转储
│   │   ├── audit_dataset.js     # 数据集审计
│   │   ├── capture_auth.js      # 认证捕获
│   │   ├── inject_golden_cookies.js # 注入黄金Cookie
│   │   ├── cleanup_mock_data.js # 清理模拟数据
│   │   ├── recon_fixtures.js    # 赛程侦察
│   │   ├── recon_module.js      # 侦察模块
│   │   ├── stealth_probe_diagnostic.js # 隐身探针诊断
│   │   ├── demo_odds_timeline.js # 赔率时间线演示
│   │   ├── demo_sniffer_mapping.js # 嗅探映射演示
│   │   ├── demo_v6_data_convergence.py # V6数据汇聚演示
│   │   ├── titan_cruise_control.py  # 全自动巡航控制器
│   │   ├── titan_pipeline_demo.js # TITAN管道演示
│   │   ├── train_model.py       # 模型训练
│   │   ├── train_model_production.py # 生产模型训练
│   │   ├── train_model_real_test.py # 真实测试训练
│   │   ├── predict_pipeline.py  # 预测管道
│   │   ├── v6_audit_demo.py     # V6审计演示
│   │   ├── backfill_capability_report.py # 回填能力报告
│   │   ├── generate_weekend_harvest.py # 周末收割生成
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
│   │   │   └── MarketSentimentExtractor.js  # 市场情绪提取器
│   │   └── smelter/             # 特征熔炼器
│   ├── analysis/                # V5.0+ 分析算法（OddsFluxDetector）
│   ├── strategy/                # 策略模块（Kelly准则、Tuner）
│   ├── infrastructure/          # 基础设施
│   │   ├── harvesters/          # 收割引擎（ProductionHarvester, SwarmHarvester, OddsPortalHarvester）
│   │   ├── network/             # 网络与代理（NetworkShield, ProxyRotator）
│   │   ├── monitoring/          # 监控与哨兵
│   │   ├── persistence/         # 持久化（Checkpointer）
│   │   └── browser/             # 浏览器自动化
│   ├── ml/                      # 机器学习
│   │   ├── inference/           # 模型推理
│   │   ├── feature_engine/      # Python 特征工程
│   │   │   └── h2h_estimator.py # H2H 智能补位引擎
│   │   └── models/              # 模型定义
│   ├── database/                # 数据库模型（唯一真理源）
│   │   └── repositories/        # 数据仓储层
│   ├── schemas/                 # Pydantic Schema
│   ├── services/                # 业务服务层
│   ├── config/                  # 配置模块
│   ├── constants/               # 常量定义
│   │   └── model_config.py      # 模型配置常量唯一源
│   ├── api/                     # API 接口
│   ├── utils/                   # 工具函数
│   │   └── StructuredLogger.js  # V4.0 结构化日志器
│   └── data/                    # 数据层
├── tests/                       # 测试文件
│   ├── unit/                    # 单元测试（50+ 测试用例）
│   │   ├── JSON_Integrity.test.js
│   │   ├── BackfillFortification.test.js
│   │   ├── BackfillResilience.test.js
│   │   ├── OddsPortalHarvester_V55.test.js
│   │   └── ...
│   ├── integration/             # 集成测试
│   ├── integrity/               # 完整性测试
│   └── fixtures/                # 测试数据
├── models/                      # 生产模型文件
│   ├── TITAN_CORE_V5_PROD.joblib
│   ├── TITAN_CORE_V5_PROD_scaler.joblib
│   ├── TITAN_CORE_V5_PROD_metadata.json
│   └── archive/                 # 归档模型
├── docs/                        # 文档中心
│   └── ops/                     # 运维文档
│       └── backfill_v6_manual.md    # V6.0 回填操作手册
├── .claude/                     # Claude Skills 约束体系
│   ├── skills/                  # 专用技能
│   ├── minimal_change.skill.md
│   ├── architecture_boundary.skill.md
│   ├── test_guard.skill.md
│   ├── context_lock.skill.md
│   └── change_impact.skill.md
├── Makefile                     # V51.0 指挥塔
├── CLAUDE.md                    # AI 助手详细操作指南
├── COMMAND_CENTER.md            # 数字化指挥中心
└── AGENTS.md                    # 本文件
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
| `npm run smelt:turbo` | V5 Turbo 熔炼 |
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

### 5.3 V6.0 回填命令

```bash
# 运行 Gold Pilot 50 回填
node scripts/ops/gold_pilot_50.js

# 运行压力测试（1000场）
node scripts/ops/stress_test_1000.js

# 批量导入比赛
node scripts/ops/bulk_import_matches.js

# 查看回填进度
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "SELECT * FROM backfill_progress;"
```

---

## 6. 工程铁律

### 6.1 五大核心规则

1. **沟通协议**：所有回复、注释、日志必须使用**中文**
2. **容器化优先**：**禁止**在宿主机直接运行 Node/Python，所有操作在 Docker 容器内执行
3. **分支管理**：严禁在 `main` 分支开发，分支命名：`feat/<功能>` / `lab/<实验>` / `fix/<修复>` / `refactor/<重构>`
4. **数据完整性**：**零模拟原则**，严禁使用 `Math.random()` 伪造数据
5. **幂等性**：所有收割任务支持重复执行，已存在的完整数据应跳过

### 6.2 V6.0 架构规范

- **配置唯一源**: `src/config_unified.py` / `config/factory_config.js` / `config/registry.js`
- **数学能力**: `src/core/math/` (finance, evaluator)
- **动态能力**: `src/core/` (Math, Database, Types)
- **预测大脑**: `src/ml/`
- **分析算法**: `src/analysis/` (V5.0+ 新增)
- **策略模块**: `src/strategy/` (Kelly准则等)
- **基础设施**: `src/infrastructure/`
- **回填系统**: `scripts/ops/gold_pilot_50.js` + `src/infrastructure/harvesters/OddsPortalHarvester.js`
- **代理轮询**: `src/infrastructure/network/ProxyRotator.js` (22端口)
- **断点续传**: `src/infrastructure/persistence/Checkpointer.js`
- **唯一数据**: `src/database/`
- **日志系统**: `src/utils/StructuredLogger.js` (V4.0 模块化)

### 6.3 黄金准则（V6.0+）

- **测试覆盖率**: 80% 熔断阈值
- **静态质量**: 0 Error 容忍
- **文档规范**: JSDoc 完整注释
- **模块化**: 单一职责，高内聚低耦合
- **V6.0 加固**: P0级架构，断点续传，限流控制，健康检查

---

## 7. 常用开发命令

### 7.1 开发环境管理（Makefile）

```bash
# 启动开发环境
make dev-up

# 进入开发容器 Shell
make dev-shell

# 停止开发环境
make dev-down

# 查看开发容器日志
make dev-logs

# 在容器中运行生产收割
make dev-harvest
```

### 7.2 核心收割流程

```bash
# L1: 赛程种子
docker-compose -f docker-compose.dev.yml exec dev npm run seed

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

### 7.3 代码质量

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

### 7.4 测试

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
pytest tests/ml/ -v
```

### 7.5 数据库操作

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

### 7.6 监控与运维

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

### 7.7 模型操作

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

### 7.8 ELO 评分操作

```bash
# 重新计算 ELO（完整）
npm run elo:recalc

# 试运行模式
npm run elo:recalc:dry

# 增量更新
npm run elo:incremental
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
| **核心模型** | XGBoost 分类器 |
| **特征维度** | 11维纯净特征（Elo + 身价 + H2H）+ market_sentiment |
| **准确率** | 65.31%（测试集）/ 67.94%（5折交叉验证） |
| **F1 Score** | 0.6371 |
| **Log Loss** | 0.9834 |

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

**使用示例**:
```javascript
const { OddsFluxDetector } = require('./src/analysis/OddsFluxDetector');

const detector = new OddsFluxDetector({
  deviationThreshold: 0.15,  // 偏差阈值 15%
  minOdds: 1.5,
  maxOdds: 10.0
});

const result = detector.analyze({
  modelProbability: 0.65,
  marketOdds: 2.1,
  homeTeam: '曼城',
  awayTeam: '利物浦'
});
```

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

---

## 13. V6.0 回填系统

### 13.1 架构概述

V6.0 回填系统是针对历史数据补全的专用流水线，采用 P0级架构加固：

**核心组件**:
- **Gold Pilot 50**: 批次调度执行器
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

### 13.3 运行方式

```bash
# 标准回填（50场批次）
node scripts/ops/gold_pilot_50.js

# TITAN 黄金收割（50场）
node scripts/ops/titan_golden_harvest_50.js

# 小规模测试
node scripts/ops/golden_pilot_5.js      # 5场
node scripts/ops/pilot_3_quick.js       # 3场快速
node scripts/ops/pilot_3_v3_quick.js    # 3场V3快速
node scripts/ops/first_gold_single.js   # 单场
node scripts/ops/first_gold_10.js       # 10场

# 中等规模测试
node scripts/ops/pilot_20.js            # 20场
node scripts/ops/pilot_20_precision_lock.js  # 20场精准锁定
node scripts/ops/pilot_5_deep_gold.js   # 5场深度黄金

# 压力测试
node scripts/ops/stress_test_50.js      # 50场
node scripts/ops/stress_test_1000.js    # 1000场

# 批量导入
node scripts/ops/bulk_import_matches.js

# 自动收割
node scripts/ops/auto_harvest_v6.js
node scripts/ops/sniffer_harvest_v6.js
node scripts/ops/assisted_harvest.js
node scripts/ops/steady_harvester.js

# 主机强制收割（开发测试）
node scripts/ops/host_force_harvest.js
node scripts/ops/host_force_harvest_demo.js

# 精准打击
node scripts/ops/precision_strike.js
node scripts/ops/precision_strike_v6.js
node scripts/ops/real_fusion_fire.js

# 离线/特殊模式
node scripts/ops/offline_backfill_v6.js
node scripts/ops/bet365_ultimate_redo.js
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
| `tests/unit/` | 单元测试 | 55+ 测试用例 |
| `tests/integration/` | 集成测试 | - |
| `tests/integrity/` | 完整性测试 | - |
| `tests/fixtures/` | 测试数据 | - |

### 14.2 核心测试文件

- `StructuredLogger.test.js` - 结构化日志器测试（V4.0 模块化）
- `Smelter_Audit.test.js` - Smelter 审计测试
- `FeatureSmelter.test.js` - 特征熔炼器测试
- `ProductionHarvester.test.js` - 生产收割器测试
- `ProductionHarvester_Deep.test.js` - 生产收割器深度测试
- `SentinelWatch.test.js` - 哨兵监控测试
- `JSON_Integrity.test.js` - JSON 完整性测试（V6.0）
- `BackfillFortification.test.js` - 回填加固测试（V6.0）
- `BackfillResilience.test.js` - 回填韧性测试（V6.0）
- `OddsPortalHarvester_V55.test.js` - OddsPortal 收割器测试（V6.0）
- `Golden_Injection_Verify.test.js` - 黄金注入验证测试（V6.0）
- `Local_Rendering_Integrity.test.js` - 本地渲染完整性测试（V6.0）
- `Real_Data_Extraction.test.js` - 真实数据提取测试（V6.0）
- `Residential_Stealth.test.js` - 住宅隐身测试（V6.0）
- `Zero_Placeholder_Diversity.test.js` - 零占位符多样性测试（V6.0）
- `parser_regression.test.js` - 解析器回归测试（V6.0）
- `purity_filter.test.js` - 纯净过滤器测试（V6.0）
- `recovery_injection.test.js` - 恢复注入测试（V6.0）
- `schema_design_validator.test.js` - Schema设计验证器测试（V6.0）
- `sniffer_interceptor.test.js` - 嗅探拦截器测试（V6.0）
- `stealth_hardening.test.js` - 隐身加固测试（V6.0）
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
- `AuditDataset.test.js` - 数据集审计测试
- `AbstractHarvester.test.js` - 抽象收割器测试
- `Extractors_V4.test.js` - V4提取器测试
- `SmelterComponents_V4.test.js` - V4 Smelter组件测试
- `StrategyParser.test.js` - 策略解析器测试
- `TitanFullRegistry.test.js` - TITAN完整注册表测试
- `Parsing_Core.test.js` - 解析核心测试
- `Body_Stamina.test.js` - 身体耐力测试
- `Error_Nerves.test.js` - 错误神经测试

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

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南（工程铁律、配置系统、关键规则） |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 数字化指挥中心（完整命令、作战常规） |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 系统架构详述 |
| [docs/OPERATIONS_MANUAL.md](./docs/OPERATIONS_MANUAL.md) | 运维手册 |
| [docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md) | 测试指南 |
| [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) | 故障排查 |
| [docs/xgboost_optimization_guide.md](./docs/xgboost_optimization_guide.md) | XGBoost 优化指南 |
| [docs/MODEL_V4_ANATOMY.md](./docs/MODEL_V4_ANATOMY.md) | V4 模型解剖学报告（11维特征详解） |
| [docs/SMELTER_REFACTOR_PLAN.md](./docs/SMELTER_REFACTOR_PLAN.md) | Smelter V4.0 重构计划 |
| [docs/ops/backfill_v6_manual.md](./docs/ops/backfill_v6_manual.md) | V6.0 回填系统操作手册 |
| [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md) | V3.1-STABLE 穿透审计报告 |

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

### 16.4 Skills 约束体系

项目已配置 5 个核心 RED 约束 Skills 和多个专用技能，详见 `.claude/README.md`。核心约束：

| 约束等级 | Skill | 用途 |
|----------|-------|------|
| 🔴 RED | `minimal_change` | 最小修改策略 |
| 🔴 RED | `architecture_boundary` | 架构边界保护 |
| 🔴 RED | `test_guard` | 测试质量保护 |
| 🔴 RED | `context_lock` | 核心模块冻结 |
| 🔴 RED | `change_impact` | 变更影响分析 |

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

## 18. 近期更新（V6.0）

### 18.1 V6.0 回填系统（2026-03-15）

**核心交付**: P0级架构加固的历史数据回填系统

**新组件**:
- ✅ `gold_pilot_50.js` - 批次调度执行器
- ✅ `ProxyRotator.js` - 22端口代理轮询
- ✅ `OddsPortalHarvester.js` - Playwright 真实抓取
- ✅ `Checkpointer.js` - 断点续传机制
- ✅ `backfill_progress` 表 - 回填状态跟踪
- ✅ `MarketSentimentExtractor.js` - 市场情绪提取

**能力增强**:
- 22端口代理池轮询（7890-7911）
- 断点续传，中断自动恢复
- 限流控制，自适应延时
- 熔断机制，代理健康保护
- 实时存盘，状态持久化

### 18.2 Smelter V5.0-TURBO（2026-03-11）

**优化**:
- `smelt_v5_turbo.js` - Turbo 模式熔炼
- `smelt_v5_worker.js` - Worker 池化熔炼
- `smelt_v5_reburn.js` - 重熔模式

### 18.3 测试体系扩展

**新增测试（55+）**:
- ✅ `JSON_Integrity.test.js` - JSON完整性验证
- ✅ `BackfillFortification.test.js` - 回填加固测试
- ✅ `BackfillResilience.test.js` - 回填韧性测试
- ✅ `OddsPortalHarvester_V55.test.js` - OddsPortal收割器测试
- ✅ `Golden_Injection_Verify.test.js` - 黄金注入验证
- ✅ `Local_Rendering_Integrity.test.js` - 本地渲染完整性
- ✅ `Real_Data_Extraction.test.js` - 真实数据提取
- ✅ `Residential_Stealth.test.js` - 住宅隐身测试
- ✅ `Zero_Placeholder_Diversity.test.js` - 零占位符多样性
- ✅ `parser_regression.test.js` - 解析器回归测试
- ✅ `purity_filter.test.js` - 纯净过滤器测试
- ✅ `recovery_injection.test.js` - 恢复注入测试
- ✅ `schema_design_validator.test.js` - Schema设计验证器
- ✅ `sniffer_interceptor.test.js` - 嗅探拦截器测试
- ✅ `stealth_hardening.test.js` - 隐身加固测试
- ✅ 多个 Extractor 专项测试

### 18.4 Worker 池化架构（V4.46.4+）

**性能提升**:
- 浏览器启动次数减少 99%
- Worker 初始化减少 99%
- 单场平均耗时减少 65%
- 吞吐量提升 3.75x

### 18.5 V6.0 实战化演进（2026-03-15 至 2026-03-17）

**新增组件**:
- ✅ `StealthNavigator.js` - 隐身导航器，反检测强化
- ✅ `SessionWarmer.js` - 会话预热器，保持会话活性
- ✅ `OddsPortalParser.js` - 专用解析器，深度数据提取

**新增运维脚本**:
- ✅ `golden_pilot_5.js` - 5场黄金测试
- ✅ `pilot_3_quick.js` / `pilot_3_v3_quick.js` - 快速测试
- ✅ `pilot_20.js` / `pilot_20_precision_lock.js` - 20场批次
- ✅ `first_gold_single.js` / `first_gold_10.js` - 首次黄金测试
- ✅ `auto_harvest_v6.js` / `sniffer_harvest_v6.js` - 自动收割
- ✅ `precision_strike.js` / `precision_strike_v6.js` - 精准打击
- ✅ `real_fusion_fire.js` - 真实融合火力
- ✅ `titan_main_harvester.js` / `titan_api_decrypt_harvester.js`
- ✅ `steady_harvester.js` / `assisted_harvest.js` - 稳定收割
- ✅ `host_force_harvest.js` - 主机强制收割（开发测试）
- ✅ `omni_live_audit.js` / `api_payload_audit.js` - 审计工具
- ✅ `db_heartbeat.js` - 数据库心跳监控

**诊断与演示**:
- ✅ `stealth_probe_diagnostic.js` - 隐身探针诊断
- ✅ `demo_odds_timeline.js` - 赔率时间线演示
- ✅ `demo_sniffer_mapping.js` - 嗅探映射演示
- ✅ `titan_pipeline_demo.js` - TITAN管道演示

---

## 19. V6.0 作战报告档案

以下报告记录了 V6.0 开发过程中的关键里程碑和实战成果：

| 报告文件 | 描述 | 日期 |
|----------|------|------|
| `V6_ZERO_MOCK_REPORT.md` | 零模拟数据认证报告 | 2026-03 |
| `V6_FIRST_GOLD_REPORT.md` | 首次黄金数据获取报告 | 2026-03 |
| `V6_GOLD_INJECTION_REPORT.md` | 黄金数据注入报告 | 2026-03 |
| `V6_20_MATCH_PILOT_REPORT.md` | 20场比赛先导测试报告 | 2026-03 |
| `V6_REAL_FUSION_FIRE_REPORT.md` | 真实融合火力测试报告 | 2026-03 |
| `V6_RESIDENTIAL_BREACH_REPORT.md` | 住宅代理突破报告 | 2026-03 |
| `V6_PRECISION_STRIKE_REPORT.md` | 精准打击测试报告 | 2026-03 |
| `V6_PRECISION_LOCK_REPORT.md` | 精准锁定测试报告 | 2026-03 |
| `V6_STEALTH_OVERDRIVE_REPORT.md` | 隐身超频报告 | 2026-03 |
| `V6_STEALTH_SIEGE_REPORT.md` | 隐身围攻报告 | 2026-03 |
| `V6_SIGHT_RESTORE_REPORT.md` | 视觉恢复报告 | 2026-03 |
| `V6_API_EXCAVATOR_REPORT.md` | API挖掘报告 | 2026-03 |
| `V6_DEEP_PARSE_AUDIT_REPORT.md` | 深度解析审计报告 | 2026-03 |
| `V6_TDD_VALIDATION_REPORT.md` | TDD验证报告 | 2026-03 |
| `V6_LOCAL_OVERRIDE_REPORT.md` | 本地覆盖报告 | 2026-03 |
| `V6_HOST_FORCE_UP_REPORT.md` | 主机强制上线报告 | 2026-03 |
| `V6_ULTIMATE_FOCUS_REPORT.md` | 终极聚焦报告 | 2026-03 |
| `V6_FINAL_PILOT_REPORT.md` | 最终先导测试报告 | 2026-03 |

> 💡 **说明**: 这些报告是 V6.0 开发过程中的实战记录，包含详细的测试数据、性能指标和架构演进历程。

---

**维护者**: V174 Engineering Team  
**许可证**: MIT License  
**最后更新**: 2026-03-17