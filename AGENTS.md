# FootballPrediction - AI 助手执行手册

> 系统版本: `V4.51.2-TOTAL-WAR`
>
> 最后整理: `2026-03-26`
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
3. 不在 `main` 分支直接开发。
4. 零模拟原则。禁止用 `Math.random()` 或伪造数据补真实链路。
5. 变更必须尽量幂等。重复执行任务时，应优先跳过已完成数据。
6. 先读后改。没有读过的文件，不直接修改。
7. 最小修改。除非明确要求，不做顺手重构和无关清理。
8. 修改后要做与改动范围相匹配的验证。

### 2.2 默认工作方式

- 代码、脚本、测试默认在 `dev` 容器内执行。
- 数据库操作默认通过容器内 `psql` 执行。
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

### 4.1 进入方式

```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml exec dev bash
```

### 4.2 命令约定

优先使用以下两类方式：

```bash
docker-compose -f docker-compose.dev.yml exec dev npm <script>
docker-compose -f docker-compose.dev.yml exec dev node <script>
```

Python 脚本同理：

```bash
docker-compose -f docker-compose.dev.yml exec -T dev python <script>
```

### 4.3 例外说明

仓库中有少量 `npm script` 内部已经封装了 `docker-compose exec ...`。这类脚本可以在宿主机调用 `npm run <script>`，但本质仍然是进入容器执行，不视为违反“容器化优先”。

---

## 5. 当前可用关键入口

以下入口基于当前仓库实际文件与 `package.json` 整理，只保留可验证的主路径。

### 5.1 L1 / L2 / L3

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| L1 种子 | `docker-compose -f docker-compose.dev.yml exec dev npm run seed` | `scripts/ops/seed_fixtures.js` |
| L1 发现 | `docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/titan_discovery.js` | `scripts/ops/titan_discovery.js` |
| L2 生产收割 | `docker-compose -f docker-compose.dev.yml exec dev npm start` | `scripts/ops/run_production.js` |
| L3 熔炼 | `docker-compose -f docker-compose.dev.yml exec dev npm run smelt` | `scripts/ops/smelt_all.js` |

### 5.2 Recon / Backfill / Monitor

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| Recon 扫描 | `docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/recon_scanner.js --season 2024-2025 --league EPL` | `scripts/ops/recon_scanner.js` |
| 回填 | `docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/gold_pilot_50.js` | `scripts/ops/gold_pilot_50.js` |
| 长时运行 | `docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/titan_marathon.js` | `scripts/ops/titan_marathon.js` |
| 监控检查 | `docker-compose -f docker-compose.dev.yml exec dev npm run titan:check` | `scripts/ops/check_health.js` |
| 哨兵监控 | `docker-compose -f docker-compose.dev.yml exec dev npm run titan:watch` | `scripts/ops/sentinel_watch.js` |

### 5.3 ML / ELO

| 能力 | 推荐入口 | 实际目标 |
|------|----------|----------|
| 训练模型 | `npm run train` | 宿主机调用后进入容器执行 `scripts/ops/train_model.py` |
| 生成预测 | `npm run predict` | 宿主机调用后进入容器执行 `scripts/ops/predict_pipeline.py` |
| ELO 重算 | `docker-compose -f docker-compose.dev.yml exec dev npm run elo:recalc` | `scripts/maintenance/recalculate_elo.js` |

### 5.4 不应作为稳定入口的脚本

当前 `package.json` 中以下脚本指向缺失文件，不能在文档中当作可靠入口：

- `harvest`
- `harvest:swarm`
- `titan:sync`
- `titan:clean`
- `metrics`
- `elo:incremental`

如需恢复，先补齐目标文件，再回写文档。

---

## 6. 核心文件地图

### 6.1 业务入口

| 模块 | 关键文件 |
|------|----------|
| L1 种子 | `src/infrastructure/FixtureSeeder.js` |
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

- `src/config_unified.py`
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
docker-compose -f docker-compose.dev.yml exec dev npm run lint
docker-compose -f docker-compose.dev.yml exec dev npm run format:check
docker-compose -f docker-compose.dev.yml exec dev npm run test:unit
docker-compose -f docker-compose.dev.yml exec dev npm run test:l1
docker-compose -f docker-compose.dev.yml exec dev npm run test:integration
```

### 7.2 Python

`npm run lint:python` 和 `npm run format:python` 当前只检查 `src/`。如果修改了 `scripts/ops/*.py` 或 `tests/**/*.py`，需要额外显式验证对应文件。

示例：

```bash
docker-compose -f docker-compose.dev.yml exec -T dev python -m pytest tests/ -v
docker-compose -f docker-compose.dev.yml exec -T dev ruff check src/ scripts/ tests/
```

### 7.3 数据库与健康状态

```bash
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "SELECT 'L1' as layer, COUNT(*) FROM matches UNION ALL SELECT 'L2', COUNT(*) FROM raw_match_data UNION ALL SELECT 'L3', COUNT(*) FROM l3_features;"
docker-compose -f docker-compose.dev.yml exec dev npm run titan:check
docker-compose -f docker-compose.dev.yml ps
```

### 7.4 变更后的最低验证要求

- 改 JavaScript 逻辑：至少运行相关单测或目标脚本的最小验证。
- 改 Python 逻辑：至少运行相关 `pytest` 或入口脚本校验。
- 改配置：至少验证能被目标入口成功加载。
- 改文档：至少做一次链接、命令、路径的实际存在性检查。

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
