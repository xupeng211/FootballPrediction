# FootballPrediction - AI 助手执行手册

> 系统版本: `V4.51.2-TOTAL-WAR`
>
> 最后整理: `2026-04-03`
>
> 目标: 让 AI 助手先遵守约束，再高效落地，不把 `AGENTS.md` 继续膨胀成总手册。

---

## 1. 文档定位

本文件只回答 4 个问题：

1. 在这个仓库里，助手必须遵守什么规则
2. 助手应该如何进入容器并执行工作
3. 当前可用的关键入口、核心文件、验证命令是什么
4. 更详细的架构、运维、模型说明应该去哪里找

不在本文件长期维护以下内容：

- 宣传性描述
- 高频变动的性能数字
- 大段发布日志
- 重复的架构大图
- 与实际文件不一致的命令清单

---

## 2. 核心规则

### 2.1 必须遵守

1. 所有回复、注释、日志优先使用中文。
2. 容器化优先。禁止直接在宿主机运行 Node.js 或 Python 业务命令。
3. 不在 `main` 分支直接开发。若当前位于 `main`，先创建或切换到工作分支，再进行任何写操作；若无法切分支，先停止并说明原因。
4. 零模拟原则。禁止用 `Math.random()` 或伪造数据补真实链路。
5. 变更必须尽量幂等。重复执行任务时，应优先跳过已完成数据。
6. 先读后改。没有读过的文件，不直接修改。
7. 最小修改。除非明确要求，不做顺手重构和无关清理。
8. 修改后要做与改动范围相匹配的验证。

### 2.2 默认工作方式

- 代码、脚本、测试默认在 `dev` 容器内执行。
- 数据库操作默认通过容器内 `psql` 执行。
- 开始修改前先确认当前 Git 分支；如果是 `main`，先切出工作分支。
- 如果命令已经封装为 `npm script`，优先使用脚本入口。
- 如果 `npm script` 指向缺失文件，先修正文档或脚本，再继续依赖该入口。

### 2.3 禁止行为

- 不在宿主机直接运行 `node ...`、`python ...` 处理业务逻辑。
- 不在 `main` 分支提交开发修改。
- 不编造数据、测试结果、运行结果。
- 不硬编码应进入配置系统的参数。
- 不添加未被请求的功能。
- 不因为“顺手”移动核心模块边界。

---

## 3. 仓库现状速览

### 3.1 项目结构

本项目是 Node.js + Python 双语言仓库，核心链路分为：

- `L1 Discovery`: 赛程发现
- `L2 Harvest`: 原始与结构化数据收割
- `L3 Smelt`: 特征熔炼
- `ELO`: 实力评分
- `Predict`: 模型推理与输出
- `Recon`: 侦察与标准化
- `Backfill`: 历史数据回填

### 3.2 关键目录

- `scripts/ops/`: 生产与运维脚本入口
- `src/infrastructure/`: 抓取、网络、侦察、监控等基础设施
- `src/ml/`: 训练、特征、推理
- `src/feature_engine/`: Node 侧特征工程
- `config/`: 配置唯一源
- `tests/`: 单元、集成、夹具
- `docs/`: 架构与运维细节

---

## 4. 容器工作流

### 4.1 前置检查

- 当前终端必须能正常执行 `docker compose` 或 `docker-compose`。
- 本文后续统一写作 `<compose>`，表示优先使用 `docker compose`；若本机只提供旧版命令，再替换为 `docker-compose`。
- 如果 `docker` / Compose 当前不可用，先修复 Docker Desktop / WSL 集成，再继续执行仓库命令。
- 运行时服务名以 `docker-compose.dev.yml` 为准：开发容器 `dev`、数据库 `db`、缓存 `redis`。

### 4.2 进入方式

```bash
<compose> -f docker-compose.dev.yml up -d
<compose> -f docker-compose.dev.yml exec dev bash
```

如果修改了 `.devcontainer/Dockerfile`、`requirements.txt` 或 `package.json`，应改用：

```bash
<compose> -f docker-compose.dev.yml up -d --build
```

如果当前机器需要代理，显式设置 `DEV_HTTP_PROXY`、`DEV_HTTPS_PROXY`、`DEV_CONTAINER_PROXY`，
不要依赖宿主机全局 `HTTP_PROXY` / `HTTPS_PROXY` 自动透传。

### 4.3 命令约定

优先使用以下两类方式：

```bash
<compose> -f docker-compose.dev.yml exec dev npm run <script>
<compose> -f docker-compose.dev.yml exec dev node <script>
```

Python 脚本同理：

```bash
<compose> -f docker-compose.dev.yml exec -T dev python <script>
```

### 4.4 例外说明

仓库中有少量 `npm script` 内部已经封装了 `docker-compose exec ...`。这类脚本可以在宿主机调用 `npm run <script>`，但本质仍然是进入容器执行，不视为违反“容器化优先”。

---

## 5. 当前可用关键入口

以下入口基于当前仓库实际文件与 `package.json` 整理，只保留可验证的主路径。

### 5.1 L1 / L2 / L3

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| L1 种子 | `<compose> -f docker-compose.dev.yml exec dev npm run seed` | `scripts/ops/seed_fixtures.js` |
| L1 发现 | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/titan_discovery.js` | `scripts/ops/titan_discovery.js` |
| L2 生产收割 | `<compose> -f docker-compose.dev.yml exec dev npm start` | `scripts/ops/run_production.js` |
| 全自动总攻编排 | `<compose> -f docker-compose.dev.yml exec dev npm run titan:total-war -- --season <season>` | `scripts/ops/total_war_pipeline.js` |
| L3 熔炼 | `<compose> -f docker-compose.dev.yml exec dev npm run smelt` | `scripts/ops/smelt_all.js` |

### 5.2 Recon / Backfill / Monitor

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| Recon 扫描（唯一入口） | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/recon_scanner.js --season <season> --league <league>` | `scripts/ops/recon_scanner.js` |
| 回填 | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/gold_pilot_50.js` | `scripts/ops/gold_pilot_50.js` |
| 长时运行 | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/titan_marathon.js` | `scripts/ops/titan_marathon.js` |
| 监控检查 | `<compose> -f docker-compose.dev.yml exec dev npm run titan:check` | `scripts/ops/check_health.js` |
| 哨兵监控 | `<compose> -f docker-compose.dev.yml exec dev npm run titan:watch` | `scripts/ops/sentinel_watch.js` |

Recon 运行补充约定：

- Recon 缝合唯一入口是 `scripts/ops/recon_scanner.js`，禁止在主干保留并行实验缝合脚本（如 `recon_index_surgical_stitch.js`、`recon_proxy_smoke.js`）。
- `recon_scanner.js` 默认直连运行，只有显式传入 `--use-proxy` 才启用代理。
- L2 主状态机含义：
  `pending` 表示等待 Detail Harvester；
  `harvested` 表示 `raw_match_data` 已落库、等待 Recon；
  `RECON_LINKED` 表示映射已建立且主表状态已同步；
  `RECON_MISMATCH` 表示当前批次未达到对齐阈值。
- V11.0 Recon 服务边界：
  `ReconNavigator` 只做浏览器流程调度；
  `ReconEngine` 只做业务编排；
  选择器、滚动参数、匹配阈值、协议超时必须进入 `config/recon_config.json`。
- Recon 审计红线：
  不允许把 `RECON_MISMATCH` 无条件回写到非 `harvested` 记录；
  不允许在已有 mapping 的同赛季比赛上继续覆盖 `RECON_MISMATCH`；
  `ReconHealthServer` 若启用，必须注册数据库 readiness；
  `ReconEngine` 批量持久化日志必须带 `recon_run_id`、`batch_type`、`batch_index`、`total_batches`。

### 5.3 ML / ELO

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| 训练模型 | `npm run train` | 宿主机调用后进入容器执行 `scripts/ops/train_model.py` |
| 生成预测 | `npm run predict` | 宿主机调用后进入容器执行 `scripts/ops/predict_pipeline.py` |
| ELO 重算 | `<compose> -f docker-compose.dev.yml exec dev npm run elo:recalc` | `scripts/maintenance/recalculate_elo.js` |

## 6. 核心文件地图

### 6.1 业务入口

| 模块 | 关键文件 |
|------|----------|
| L1 种子 | `src/infrastructure/services/DiscoveryService.js` |
| L1 配置 | `src/infrastructure/services/L1ConfigManager.js` |
| L1 发现 | `scripts/ops/titan_discovery.js` |
| L2 收割 | `src/infrastructure/harvesters/ProductionHarvester.js` |
| Swarm | `src/infrastructure/harvesters/SwarmHarvester.js` |
| Backfill | `src/infrastructure/harvesters/OddsPortalHarvester.js` |
| Recon | `src/infrastructure/recon/` |
| L3 熔炼 | `src/feature_engine/smelter/FeatureSmelter.js` |
| 预测 | `src/ml/inference/predictor.py` |
| H2H 补位 | `src/ml/feature_engine/h2h_estimator.py` |
| 哨兵 | `src/infrastructure/monitoring/` |

### 6.2 配置唯一源

配置优先看以下位置：

- `src/config/__init__.py`
- `src/config/settings.py`
- `src/config/proxy_settings.py`
- `config/factory_config.js`
- `config/registry.js`
- `config/recon_config.json`
- `config/leagues.json`
- `config/season_windows.json`

禁止在业务代码中散落硬编码参数替代这些配置源。

---

## 7. 常用验证命令

### 7.1 JavaScript / Markdown

```bash
<compose> -f docker-compose.dev.yml exec dev npm run lint
<compose> -f docker-compose.dev.yml exec dev npm run format:check
<compose> -f docker-compose.dev.yml exec dev npm run test:unit
<compose> -f docker-compose.dev.yml exec dev npm run test:l1
<compose> -f docker-compose.dev.yml exec dev npm run test:integration
```

### 7.2 Python

`npm run lint:python` 和 `npm run format:python` 当前只检查 `src/`。如果修改了 `scripts/ops/*.py` 或 `tests/**/*.py`，需要额外显式验证对应文件。

示例：

```bash
<compose> -f docker-compose.dev.yml exec -T dev python -m pytest tests/ -v
<compose> -f docker-compose.dev.yml exec -T dev ruff check src/ scripts/ tests/
```

### 7.3 数据库与健康状态

```bash
<compose> -f docker-compose.dev.yml exec db \
  psql -U football_user -d football_db \
  -c "SELECT 'L1' as layer, COUNT(*) FROM matches \
UNION ALL SELECT 'L2', COUNT(*) FROM raw_match_data \
UNION ALL SELECT 'L3', COUNT(*) FROM l3_features;"
<compose> -f docker-compose.dev.yml exec dev npm run titan:check
<compose> -f docker-compose.dev.yml ps
```

### 7.4 变更后的最低验证要求

- 改 JavaScript 逻辑：至少运行相关单测或目标脚本的最小验证。
- 改 Python 逻辑：至少运行相关 `pytest` 或入口脚本校验。
- 改配置：至少验证能被目标入口成功加载。
- 改文档：至少做一次链接、命令、路径的实际存在性检查。
- 改 Recon 核心链路：
  至少运行相关单测；
  如果触碰生命周期、并发控制或批量持久化，默认补跑 `<compose> -f docker-compose.dev.yml exec dev npm run test:unit` 全量。

---

## 8. 数据与数据库约束

### 8.1 主要数据表

| 表名 | 用途 |
|------|------|
| `matches` | L1 比赛基础信息 |
| `raw_match_data` | L2 原始数据 |
| `l2_match_data` | L2 结构化数据 |
| `l3_features` | L3 特征数据 |
| `predictions` | 预测结果 |
| `team_elo_ratings` | Elo 评分 |
| `backfill_progress` | 回填进度 |
| `recon_standings` | Recon 标准化结果 |

### 8.2 数据侧工作原则

- 不伪造比赛、赔率、特征、预测结果。
- 不破坏幂等写入逻辑。
- 涉及采集与回填时，优先保留跳过已完成数据的能力。
- 任何批量数据修复都要先确认影响范围。

---

## 9. 助手执行规范

### 9.1 修改前

- 先确认当前 Git 分支；如果在 `main`，先切到工作分支再继续。
- 先确认目标文件和依赖文件。
- 先确认入口命令是否真实存在。
- 先确认改动是否触碰配置唯一源、数据库边界或核心基础设施。

### 9.2 修改时

- 只改完成任务所必需的部分。
- 保持现有架构边界，不擅自跨层搬运职责。
- 新增注释只写必要解释，不写废话。
- 新增命令、文件、入口时，必须同步更新对应文档或脚本引用。

### 9.3 修改后

- 运行最小但足够的验证。
- 明确说明未验证的部分。
- 如果发现仓库已有坏链路，单独指出，不把它伪装成已解决。

### 9.4 Recon ELITE PASS 条件

以下条件同时满足时，Recon / Total War 变更才可宣称达到 `ELITE PASS`：

- `<compose> -f docker-compose.dev.yml exec dev npm run test:unit` 全绿
- 浏览器、Guardian、DB Pool 的退出路径闭环
- `RECON_MISMATCH` 更新具备条件保护，不会覆盖已建 mapping 的比赛
- 关键运行参数全部来自 `config/recon_config.json`
- 文档已同步到真实模块边界，而不是停留在旧的巨石结构描述

---

## 10. 文档索引

更深层信息不要继续堆在本文件，按主题去对应文档。

### 10.1 核心说明

- `CLAUDE.md`: AI 协作细则
- `COMMAND_CENTER.md`: 指挥中心总览
- `HANDOVER.md`: 交接信息
- `CHANGELOG.md`: 版本演进
- `MIGRATION.md`: 迁移说明

### 10.2 架构文档

- `docs/ARCHITECTURE.md`
- `docs/ENGINE_ARCHITECTURE.md`
- `docs/MCP_ARCHITECTURE.md`
- `docs/L1_DISCOVERY_ENGINE.md`
- `docs/L1_INDEX_LAYER_SPEC.md`
- `docs/adr/ADR-001-Source-Level-Data-Hardening.md`
- `docs/adr/ADR-002-L2-Raw-Storage-Hardening.md`

### 10.3 运维与专项文档

- `docs/OPERATIONS_MANUAL.md`
- `archive_vault_2026/docs_legacy/OPERATIONS_RUNBOOK.md`
- `docs/OPERATIONS_SOP.md`
- `docs/ops/backfill_v6_manual.md`
- `docs/SYSTEM_STABILITY_GUIDE.md`
- `archive_vault_2026/docs_legacy/TITAN_V5.2_TECHNICAL_SPEC.md`
- `archive_vault_2026/docs_legacy/MODEL_V4_ANATOMY.md`
- `archive_vault_2026/docs_legacy/SMELTER_REFACTOR_PLAN.md`
- `docs/xgboost_optimization_guide.md`
- `P2P_HARVEST_REPORT_V38.md`

### 10.4 Claude Skills

技能说明见：

- `.claude/README.md`
- `.claude/skills/`

---

## 11. 维护要求

当以下内容发生变化时，必须回写本文件：

- 关键入口脚本迁移
- `package.json` 主命令变化
- 容器工作流变化
- 核心约束变化
- 配置唯一源变化

不应因为版本升级而自动往这里追加大段发布日志。发布内容请进入 `CHANGELOG.md` 或专项文档。

---

## 12. 一句话准则

先确认真实入口，再在容器内最小修改，最后用实际验证收口。
