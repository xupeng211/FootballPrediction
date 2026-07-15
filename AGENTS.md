# FootballPrediction - AI 助手执行手册

> 系统版本: `V4.51.2-TOTAL-WAR`
>
> 最后整理: `2026-04-03`
>
> 目标: 让 AI 助手先遵守约束，再高效落地，不把 `AGENTS.md` 继续膨胀成总手册。
>
> Claude Code 用户也必须阅读 `CLAUDE.md`，它指向与本文件相同的权威工作流来源。

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
9. 数据收割、ETL、Recon、Backfill、Odds、L3/ELO 相关入口默认必须走 `make data-*` 安全门禁。
10. DB schema migration 默认必须走 `make data-schema-*` 安全门禁，禁止直接执行 migration apply。
11. implementation phase 必须包含实际 runtime code behavior change；
    不得只用 `docs/_reports`、`docs/_manifests`、tests 或 proposal metadata 替代实现。
12. 如果无法安全完成 runtime code change，必须 No-Go 并说明 blocker；
    不得用继续新增 report / manifest phase snapshot 伪装业务推进。
13. PR 必须声明 PR type、runtime behavior 是否变化、business progress、剩余 blocker，
    以及 no-live-fetch / no-DB-write / no-raw-write 状态。
14. 连续 governance-only PR 超过 1 个，或 implementation PR 没有 runtime behavior change，
    必须先人工确认后再继续。
15. 新 report、manifest、Phase/ADG 脚本默认禁止创建。只有当前 Issue 明确授权、PR 正文准确声明，并通过 M2 增长冻结门禁后，才允许最小必要治理资产。历史治理资产不得作为新任务默认产物。
16. 测试必须优先验证系统行为；
    文档字段断言只能作为辅助，不得替代 runtime behavior coverage。
17. Data ingestion phase 必须声明 blocker transition 目标和 `target_state_delta`；
    PR 必须回答解除哪个 blocker、哪些 target 状态发生实质变化、是否有 target 进入
    `clean_candidate` / `rejected_mapping` / `superseded_mapping` /
    `eligible_for_re_acceptance_review` / `needs_new_evidence`。
18. 如果 ingestion PR 没有解除 blocker、没有 target 状态实质变化，必须说明为什么仍值得合并；
    连续 2 个 ingestion governance / review / planning / execution PR 无实质进展时，
    必须停止进入 Ingestion Architecture Decision Gate，不得自动开启下一轮 planning / review。
19. expanded review planning / execution 必须 bounded；
    bounded review 后仍没有 clean / reject / supersede / re-acceptance candidate 时，
    必须输出架构决策，不得继续 phase 化。
20. Ingestion Architecture Decision Gate 的可选方向包括：
    abandon current batch、rebuild canonical identity pipeline、redo source inventory strategy、
    switch data source / compare alternative source、redesign FotMob identity mapping strategy。
21. raw write 仍需 fresh authorization；
    review / planning / execution 结果不得自动放行 DB write、`raw_match_data` write 或 re-acceptance。

### 2.2 默认工作方式

- 代码、脚本、测试默认在 `dev` 容器内执行。
- 数据库操作默认通过容器内 `psql` 执行。
- 开始修改前先确认当前 Git 分支；如果是 `main`，先切出工作分支。
- 如果命令已经封装为 `npm script`，优先使用脚本入口。
- 如果 `npm script` 指向缺失文件，先修正文档或脚本，再继续依赖该入口。
- 不直接运行 `scripts/ops/titan_discovery.js`。L1 discovery 默认只能通过 `make data-l1-discovery-preview` / `make data-l1-discovery-candidates-preview` 的 safe preview 路径进入；显式授权的 L1 外网候选预览只能通过 `make data-l1-discovery-candidates-network-preview`。
- L1 matches seed 操作必须走 `data-l1-*` safe preview/plan/authorize/preflight/execute 阶段，不得直接运行 legacy 入口。
- Legacy L1 / data entrypoints 对 agents 视为 deprecated：`titan_discovery.js`、`run_production.js`、`batch_historical_backfill.js`、`total_war_pipeline.js` 和生产 harvest/raw ingest 入口不得直接运行。
- L2 raw JSON acquisition 必须通过 controlled planning/preview/authorization/preflight 阶段，并按 README canonical surface 和 `docs/data/FOTMOB_CURRENT_STATE.md` 的当前状态执行。直接写 `raw_match_data`、训练、预测或 parser 均未授权且保持 blocked。
- 不得保存或打印完整 HTML body、raw_data、pageProps；不得绕过 browser/proxy/captcha 限制；hash gate 必须使用 stable payload hash（不含 volatile fetch metadata）。
- 以下 engine core 不是 deprecated：`DiscoveryService`、`DiscoveryParser`、`DiscoveryAttributeMapper`、`DiscoveryDataValidator`、`L1ConfigManager`、`HttpClient`、`FotMobExtractor`、`BrowserProvider`、`FixtureRepository`。
- 未完成 migration inventory 且未经用户批准前，不删除 legacy entrypoints。

### 2.3 禁止行为

- 不在宿主机直接运行 `node ...`、`python ...` 处理业务逻辑。
- 不在 `main` 分支提交开发修改。
- 不编造数据、测试结果、运行结果。
- 不硬编码应进入配置系统的参数。
- 不添加未被请求的功能。
- 不因为“顺手”移动核心模块边界。
- 不把 implementation phase 降级成 docs-only / report-only / manifest-only / test-only PR。
- 不默认提交大型 phase snapshot、完整历史 manifest 复制或无限增长的治理 artifact。

### 2.4 Agent workflow hardening

详细规则见 `docs/AGENT_WORKFLOW.md`。默认执行原则：

- 代码解决问题，测试证明问题，文档解释问题。
- live fetch、detail fetch、network request、DB write、`raw_match_data` write、re-acceptance、rollback、schema migration 仍必须逐项单独授权。
- `docs/_reports` 与 `docs/_manifests` 属于历史治理资产分类。新任务默认不得创建；只有 Issue 明确授权且通过 M2 增长冻结门禁时，才允许最小必要记录。现存历史资产不得替代 runtime 实现。
- PR reviewer 必须能从模板中直接判断：PR type、runtime code paths、artifact 体积、business progress、blocker 变化和安全边界。
- Data ingestion PR 必须满足 `docs/INGESTION_CONVERGENCE_GATE.md` 的 outcome gate：
  声明 blocker transition、`target_state_delta`、bounded review 范围和 no-progress stop 条件。

### 2.5 Repository Hygiene / Technical Debt Guardrails

每个新增文件必须声明 lifecycle：`permanent` / `current-state` / `temporary` / `one-shot-helper` / `test-fixture` / `delete-after-use`。无 lifecycle 声明的新文件不得合并。

`phase-artifact` 和 `archive-candidate` 仅用于识别现存历史债务的分类标记，不是新文件的推荐生命周期。新任务不得通过新增 Phase artifact、report、清单或阶段快照代替 runtime 实现或真实业务进展。

每个新增 helper/script 必须说明是否长期保留、是否被 Makefile/npm script/CI 引用、cleanup 条件。若 helper 只服务一次，默认成为 cleanup candidate。

测试必须优先验证 runtime behavior。只验证 report wording / manifest metadata 的测试不得替代 behavior coverage。

应维护 current-state 入口；历史 ADG report 不能替代 current truth。

Data/ingestion PR 的仓库卫生状态应在 PR 自身的 Debt Impact 中说明。不得在没有 explicit Issue 授权的情况下创建独立的 hygiene / cleanup PR。

PR 最终回复必须包含 Debt Impact：new files added、permanent files、phase-only files、temporary helpers、files superseded、files deleted/archived、cleanup needed later、repository noise increased? yes/no、next cleanup trigger。

详见 `docs/AGENT_WORKFLOW.md` Repository Hygiene Gate 章节。

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


### 4.1 前置检查

- 当前终端必须能正常执行 `docker compose` 或 `docker-compose`。
- 本文后续统一写作 `<compose>`，表示优先使用 `docker compose`；若本机只提供旧版命令，再替换为 `docker-compose`。
- 如果 `docker` / Compose 当前不可用，先修复 Docker Desktop / WSL 集成，再继续执行仓库命令。
- 标准开发入口优先使用 `make dev-*`，其底层固定为 `docker compose -f docker-compose.dev.yml`。
- 运行时服务名以 `docker-compose.dev.yml` 为准：开发容器 `dev`、数据库 `db`、缓存 `redis`。
- 默认 `docker-compose.yml` 只覆盖基础服务，不是完整开发栈；不要裸用 `docker compose up` 作为开发入口。
- 不要使用 `docker compose down -v`，除非明确要清空本地数据 volume。

### 4.2 进入方式

优先使用 Makefile 标准入口：

```bash
make dev-config
make dev-up
make dev-ps
make dev-shell
```

等价底层命令：

```bash
<compose> -f docker-compose.dev.yml config
<compose> -f docker-compose.dev.yml up -d --build --remove-orphans
<compose> -f docker-compose.dev.yml ps
<compose> -f docker-compose.dev.yml exec dev bash
```

如果修改了 `.devcontainer/Dockerfile`、`requirements.txt` 或 `package.json`，应改用：

```bash
make dev-up
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

---
## 5. 当前可用关键入口

业务命令的唯一权威入口清单在 **README "Canonical Business Entrypoints"** 章节中维护。
AGENTS.md 和 CLAUDE.md 只引用该章节，不重复维护完整入口表。

### 5.1 分类规则

- **Canonical** — 新的人类操作和 agent 工作默认使用的入口。
- **Specialized / Internal** — 有效但非领域默认入口。示例：`npm run seed`、`npm run odds:sniper`、`npm run smelt`、`predict:dry`、`train:fast`。
- **Legacy / Admin-only** — 保留但不得成为新代码依赖：`scripts/ops/run_production.js`、`scripts/ops/titan_discovery.js`、`scripts/ops/total_war_pipeline.js`、以及 Phase/ADG 编号脚本作为整体类别。

### 5.3 数据入口安全门禁

数据收割治理以 `make data-*` 为统一入口，通过 preview / plan / authorization / preflight / execute 多阶段门禁确保安全。详细规范见 `docs/DATA_HARVESTING_GUIDE.md`。

AI / Codex 默认只能执行 `make data-help` 和 `make data-check` 以及明确授权且标记为 no-write / SELECT-only 的 safe preview 阶段。所有 commit / execute / write 阶段以及含网络或 DB 写入的命令必须逐项单独授权。

以下入口对 agents 视为 deprecated / blocked：
- `titan_discovery.js`、`run_production.js`、`batch_historical_backfill.js`、`total_war_pipeline.js`
- `npm start`、`npm run titan:total-war`、`npm run odds:harvest`（未经授权）
- `npm run train`、`npm run predict`（未经训练/预测授权）
- 任何 `--commit` 命令、任何外网收割命令、任何写 DB 命令

### 5.4 原则

1. 新代码必须使用 README 中的 canonical 入口或 surface。
2. Specialized/internal 脚本不是默认入口。
3. Legacy/admin-only 脚本不得成为新依赖。
4. "Not yet established" 表示对应业务里程碑必须创建并测试未来入口。
5. **Canonical 不等于自动授权执行。** 含副作用的命令（DB 写入、网络、浏览器、训练、赔率采集）仍需逐项明确授权。

---

## 6. 核心文件地图

### 6.1 业务入口

| 模块     | 关键文件                                               |
| -------- | ------------------------------------------------------ |
| L1 种子  | `src/infrastructure/services/DiscoveryService.js`      |
| L1 配置  | `src/infrastructure/services/L1ConfigManager.js`       |
| L1 发现  | `scripts/ops/titan_discovery.js`                       |
| L2 收割  | `src/infrastructure/harvesters/ProductionHarvester.js` |
| Swarm    | `src/infrastructure/harvesters/SwarmHarvester.js`      |
| Backfill | `src/infrastructure/harvesters/OddsPortalHarvester.js` |
| Recon    | `src/infrastructure/recon/`                            |
| L3 熔炼  | `src/feature_engine/smelter/FeatureSmelter.js`         |
| 预测     | `src/ml/inference/predictor.py`                        |
| H2H 补位 | `src/ml/feature_engine/h2h_estimator.py`               |
| 哨兵     | `src/infrastructure/monitoring/`                       |

### 6.2 配置唯一源

配置优先看以下位置：

- `src/config/__init__.py`
- `src/config/settings.py`
- `src/config/proxy_settings.py`
- `config/factory_config.js`
- `config/registry.js`
- `config/active_registry.json`
- `config/odds_harvest_routes.json`
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
make dev-ps
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

| 表名                | 用途             |
| ------------------- | ---------------- |
| `matches`           | L1 比赛基础信息  |
| `raw_match_data`    | L2 原始数据      |
| `l2_match_data`     | L2 结构化数据    |
| `l3_features`       | L3 特征数据      |
| `predictions`       | 预测结果         |
| `team_elo_ratings`  | Elo 评分         |
| `backfill_progress` | 回填进度         |
| `recon_standings`   | Recon 标准化结果 |

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
- `docs/DATA_HARVESTING_GUIDE.md`
- `docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE4_2.md`
- `docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md`
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
