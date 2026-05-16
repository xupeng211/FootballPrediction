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
9. 数据收割、ETL、Recon、Backfill、Odds、L3/ELO 相关入口默认必须走 `make data-*` 安全门禁。
10. DB schema migration 默认必须走 `make data-schema-*` 安全门禁，禁止直接执行 migration apply。

### 2.2 默认工作方式

- 代码、脚本、测试默认在 `dev` 容器内执行。
- 数据库操作默认通过容器内 `psql` 执行。
- 开始修改前先确认当前 Git 分支；如果是 `main`，先切出工作分支。
- 如果命令已经封装为 `npm script`，优先使用脚本入口。
- 如果 `npm script` 指向缺失文件，先修正文档或脚本，再继续依赖该入口。
- 不直接运行 `scripts/ops/titan_discovery.js`。L1 discovery 默认只能通过 `make data-l1-discovery-preview` / `make data-l1-discovery-candidates-preview` 的 safe preview 路径进入；显式授权的 L1 外网候选预览只能通过 `make data-l1-discovery-candidates-network-preview`。
- L1 matches seed commit 不能由 AI / Codex 直接走旧 commit 大入口执行；Phase 5.06L1 仅允许 `make data-l1-matches-seed-commit-plan` 输出 stdout planning；Phase 5.07L1 仅允许 `make data-l1-matches-seed-commit-authorization` 输出 stdout authorization summary；Phase 5.08L1 仅允许 `make data-l1-matches-seed-commit-execution-preflight` 输出 stdout preflight summary 和 SELECT-only affected rows preview；Phase 5.09L1 仅允许 `make data-l1-matches-seed-commit-execute` 在最终确认后、按 exact scope 事务写入 `matches`。
- legacy L1 / data entrypoints 对 agents 视为 deprecated：admin / 人工兼容入口可以保留，但 AI / Codex 不得直接运行 `titan_discovery.js`、`run_production.js`、`batch_historical_backfill.js`、`total_war_pipeline.js`、生产 harvest 入口或 raw ingest commit 入口；L1 discovery 与 matches seed 操作必须走 `data-l1-*` safe targets。
- L2 raw JSON acquisition 当前仍未授权执行。AI / Codex 不得运行 legacy raw backfill、production harvest、`raw_match_data` commit 或任何会抓取 FotMob match detail / 写 `raw_match_data` 的入口；后续必须先走 Phase 5.10L2+ controlled planning / preview / authorization / preflight，且 `raw_match_data` 写入必须与训练、预测分离并单独授权。
- Phase 5.11L2 raw detail preview 仅允许 preview-only：除非未来用户扩大授权，只能目标 `53_20252026_4830746` / `external_id=4830746`；不得写 `raw_match_data` 或任何 DB，不得打印或保存完整 body，不得启 browser/proxy，不得调用 `ProductionHarvester` 或 legacy raw backfill；`raw_match_data` 写入必须等待后续 planning / authorization / preflight。
- Phase 5.11L2 direct `matchDetails` endpoint 已返回 403。AI / Codex 不得擅自 retry、增加 headers、改走 browser/proxy 或尝试 alternate route；继续请求 raw detail 前必须先完成现有 L2 fetch path reconciliation 并取得明确授权，`raw_match_data` 写入仍未授权。
- Phase 5.12L2B 新增 safe FotMob detail route selector，默认顺序为 `html_hydration` -> `api_match_details`，`alternate_route` 仅 plan-only；live external raw detail preview 仍默认 blocked，未经未来单独授权不得 retry Phase 5.11L2 direct API 403、不得加 headers/browser/proxy 绕过，`raw_match_data` 写入仍未授权。
- Phase 5.13L2 raw_match_data ingest planning 仅允许 planning-only；`raw_match_data` 写入仍未授权。raw_data 应存 canonical transformed detail payload 而不是完整 HTML body；data_hash 应为 canonical raw_data JSON 的 SHA-256，而不是 HTML body hash；raw_match_data ingest 不得更新 `matches`、features、training 或 predictions，未来写入必须另行 authorization + preflight。
- Phase 5.14L2 raw_match_data ingest authorization 仅允许 authorization-only：它只记录未来 `raw_match_data` 写入授权范围，本阶段不得写 DB、不得写 `raw_match_data`、不得 live preview / network request；后续写入仍必须先完成 Phase 5.15L2 preflight，并在最终执行阶段再次确认。raw_match_data ingest 必须保持 raw-only，不得更新 `matches`、features、training 或 predictions。
- Phase 5.15L2 raw_match_data ingest preflight 允许通过 safe route selector 重新 recapture exact raw payload；它必须保持 SELECT-only，不得写 DB，不得写 `raw_match_data`，不得写 `matches`、features、training 或 predictions；它必须输出 `would_insert` / `would_update` / `would_skip`，`data_hash` 必须来自 canonical raw_data JSON，不得存完整 HTML body；真正 controlled write 仅能留到 Phase 5.16L2 且必须有最终 DB-write confirmation。
- Phase 5.16L2 controlled raw_match_data write 是目标 `4830746` 唯一允许的 raw 写入路径；它必须要求最终 DB-write confirmation，在写入前把 recapture 得到的 `raw_data_hash` 与 Phase 5.15L2 baseline 比对，一致时才允许事务写入；它只能写 `raw_match_data`，不得更新 `matches`、features、training 或 predictions，不得训练/预测，不得保存或打印完整 body。
- Phase 5.17L2 起，L2 当前策略改为 raw-first / parse-later / train-driven parsing：在训练目标与数据泄漏策略明确前，agents 不得把 `raw_match_data` 解析成 features，不得进入 parser implementation；剩余 seeded matches 的 raw acquisition 只能继续走 authorization / preflight / controlled write，且这些 phase 不得做 parser/features/training/prediction。
- Phase 5.18L2 授权剩余 7 场 seeded matches（4830747-4830754）进入 future controlled raw_match_data acquisition；本阶段是 authorization-only，不触网、不写 DB、不写 raw_match_data；parser/features/training/prediction 仍 deferred；剩余 raw acquisition 必须先完成 preflight 才能进入 controlled write。
- Phase 5.19L2 允许对剩余 7 场执行 controlled live preflight，通过 safe html_hydration route recapture exact payload；必须输出 would_insert/would_update/would_skip per target；不得写 DB 或 raw_match_data；parser/features/training/prediction 仍 deferred；controlled write 必须留到 Phase 5.20L2。
- Phase 5.20L2C 是剩余 7 场 seeded matches（4830747-4830754）唯一允许的 `raw_match_data` 写入路径；它必须使用 `FotMobRawDetailFetcher` 逐场 recapture，并在写入前把每个 `raw_data_hash` 与 Phase 5.20L2B baseline 对比，任何 hash drift 都必须停止且不得写 DB；它只能单事务写入 `raw_match_data` 7 行，不得写 `matches`、features、training 或 predictions，不得保存或打印完整 body/raw_data。
- Phase 5.20L2D 起，FotMob raw detail `data_hash` / `raw_data_hash` 必须使用 `stable_raw_payload_v1`：hash gate 只能比较稳定 payload hash，`_meta.fetched_at`、`_meta.fetch_body_sha256`、request/final URL、HTTP metadata 和其他 volatile fetch metadata 不得参与 `data_hash`；`raw_data` 可以保留 `_meta`，但 write 在 baseline `hash_strategy` 缺失或不匹配时必须停止并等待新的 stable preflight baseline。
- Phase 5.20L2F 是使用 stable baseline 写入剩余 7 条 `raw_match_data` 的唯一批准路径：必须走 `make data-l2-remaining-raw-match-data-write`，必须传入 `HASH_STRATEGY=stable_raw_payload_v1`，必须使用 `FotMobRawDetailFetcher` 逐场 recapture，并把每个 `data_hash` / `raw_data_hash` 与 Phase 5.20L2E baseline 精确比对；只允许单事务写 `raw_match_data`，不得写 `matches`、features、training、predictions，不得 parser/features/training/prediction，不得保存或打印完整 body/raw_data。
- Phase 5.21L2A 起，Phase 5.20L2F 后不得直接跳到 training design；必须先做 `raw_match_data` completeness/source fidelity audit。Agents 不得假设 transformed `raw_data` 就是完整原始 JSON；`raw_match_data` 可包含 mixed provenance / heterogeneous schema，parser/features/training 后续必须按 data_version/source 分层。synthetic/legacy rows 不得用于判断 FotMob source fidelity；parser/features/training 继续 deferred，直到 raw storage completeness 被确认。任何 live source fidelity compare 都必须单独授权且 no-write。
- Phase 5.21L2B 仅允许在明确授权后执行 single-target source fidelity live compare：必须 no-write，不得保存或打印完整 HTML body / full JSON，不得 browser/proxy，不得 parser/features/training/prediction；若确认 stored `raw_data` 是 transformed/lossy，必须先解决 raw storage strategy，再进入 parser/training。
- Phase 5.21L2C 起，当前 FotMob v1 `raw_data` 明确视为 transformed hydration payload；未来 canonical FotMob raw 默认应优先 `fotmob_pageprops_v2`，即存 `__NEXT_DATA__.props.pageProps` 并使用 stable pageProps hash。transformed payload 只能作为 derived/helper，不得作为唯一 raw source；parser/features/training 必须按 data_version/source/provenance 分支。低级别/冷门联赛扩展前必须先做 raw completeness profile；未经明确授权不得 rewrite 现有 raw rows，也不得默认存 full `__NEXT_DATA__`。
- Phase 5.21L2D 仅允许明确授权后的 single-target pageProps v2 no-write preview：`fotmob_pageprops_v2` candidate 必须只留在内存中；在 schema/version coexistence 完成规划前不得写 v2 rows，且需先复核当前 `raw_match_data` `unique(match_id)` 是否阻止同一 match 多版本共存；parser/features/training 继续 deferred。
- Phase 5.21L2E 起，pageProps v2 write 在完成 `raw_match_data` version coexistence 规划前不得推进；当前 `unique(match_id)` 必须视为潜在 blocker。不得覆盖或 rewrite `fotmob_html_hyd_v1`，优先规划 versioned coexistence；parser/features/training 必须显式选择 `data_version`。schema migration 必须另行明确授权，pageProps v2 写入也必须先完成独立 preflight 并取得 DB-write authorization。
- Phase 5.21L2F 仅允许 `raw_match_data` versioned schema migration planning/preflight：可以规划 `UNIQUE(match_id)` 到 `UNIQUE(match_id, data_version)` 的 exact forward/rollback SQL，但不得执行 `ALTER TABLE`、drop/add constraint、CREATE/DROP INDEX、migration 或任何 DB write。Phase 5.21L2G 之前只能输出 plan；后续 schema migration execution 必须单独明确授权，且仍不得写 raw rows。
- Phase 5.21L2G 是 controlled schema-only migration：只有明确授权后才可把 `raw_match_data` 唯一约束从 `UNIQUE(match_id)` 改为 `UNIQUE(match_id, data_version)`；不得写 raw data rows、不得写 `fotmob_pageprops_v2` row、不得触 FotMob、不得 parser/features/training。迁移后 writers 必须使用 version-aware conflict target，legacy `ON CONFLICT(match_id)` 路径视为 deprecated/risky；readers/parser/training 必须 filter `data_version` 或使用 canonical selector。pageProps v2 write 仍需单独 preflight 和授权。
- Phase 5.21L2H 起，`raw_match_data` 已按 `(match_id, data_version)` 版本化；controlled writers 必须按 `match_id + data_version` lookup/conflict，agents 禁止 match_id-only raw writes。Readers 必须显式 filter `data_version` 或使用 `RawMatchDataVersionSelector`；canonical selection 默认优先 `fotmob_pageprops_v2`，回退 `fotmob_html_hyd_v1`，并默认排除 `PHASE4.43_SYNTHETIC`、`PHASE4.23` 与 unknown。legacy/admin `ON CONFLICT(match_id)` 路径在升级前继续视为 deprecated/agent-blocked；pageProps v2 write 仍需单独 preflight 和授权。
- Phase 5.21L2I 是 pageProps v2 single-target write preflight：仅可在明确授权下对 `4830747` 执行一次 HTML hydration live request，不启 browser/proxy、不 retry；必须用 `match_id + data_version` SELECT existing versions，输出 would_insert/would_update/would_skip；不得写 `raw_match_data`、不得保存/打印完整 body 或完整 JSON，真正 pageProps v2 write 仍需后续 final DB-write confirmation。
- Phase 5.21L2J 仅允许在明确最终 DB-write confirmation 后，为 `4830747` 插入 exactly one `fotmob_pageprops_v2` `raw_match_data` row；必须使用 `(match_id, data_version)` 唯一性和 Phase 5.21L2I baseline hash gate，写入前 recapture hash 必须完全一致。v2 `raw_data` 必须包含 `_meta`、top-level `matchId` 和 `pageProps`；不得写其他 matches，不得 rewrite v1，不得 parser/features/training。写入后下一步是 canonical read verification，不是 bulk v2 acquisition。
- Phase 5.21L2K 是 pageProps v2 post-write canonical read verification：只能 SELECT-only、不触 FotMob、不写 DB；首个 v2 写入后 `RawMatchDataVersionSelector` 必须为 `4830747` 选择 `fotmob_pageprops_v2`，无 v2 的 seeded matches 必须 fallback `fotmob_html_hyd_v1`，`PHASE4.43_SYNTHETIC` / `PHASE4.23` / unknown 仍默认排除。不得在 planning/preflight 前 bulk 写剩余 v2，parser/features/training 继续 deferred。
- Phase 5.21L2L 仅允许 remaining seeded pageProps v2 no-write preflight：可对 7 个 remaining seeded targets（4830746、4830748、4830750、4830751、4830752、4830753、4830754）执行授权的串行 HTML hydration live request，必须输出 `stable_pageprops_payload_v1` baselines；不得写 `raw_match_data`、不得 bulk write、不得 parser/features/training/prediction。后续 remaining write 必须另行 final DB-write confirmation，并以本阶段 hash-gated preflight 为基线。
- 以下 engine core 不是 deprecated，也不得误删：`DiscoveryService`、`DiscoveryParser`、`DiscoveryAttributeMapper`、`DiscoveryDataValidator`、`L1ConfigManager`、`HttpClient`、`FotMobExtractor`、`BrowserProvider`、`FixtureRepository`。
- 未完成 migration inventory 且未经用户批准前，不删除 legacy entrypoints。

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

## 5. 当前可用关键入口

以下入口基于当前仓库实际文件与 `package.json` 整理，只保留可验证的主路径。

### 5.1 L1 / L2 / L3

| 能力           | 推荐入口                                                                                    | 实际目标                               |
| -------------- | ------------------------------------------------------------------------------------------- | -------------------------------------- |
| L1 种子        | `<compose> -f docker-compose.dev.yml exec dev npm run seed`                                 | `scripts/ops/seed_fixtures.js`         |
| L1 发现        | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/titan_discovery.js`          | `scripts/ops/titan_discovery.js`       |
| L2 生产收割    | `<compose> -f docker-compose.dev.yml exec dev npm start`                                    | `scripts/ops/run_production.js`        |
| 全自动总攻编排 | `<compose> -f docker-compose.dev.yml exec dev npm run titan:total-war -- --season <season>` | `scripts/ops/total_war_pipeline.js`    |
| 专项赔率收割   | `<compose> -f docker-compose.dev.yml exec dev npm run odds:harvest -- --season <season>`    | `scripts/ops/odds_harvest_pipeline.js` |
| 定向 L3 缝合   | `<compose> -f docker-compose.dev.yml exec dev npm run l3:stitch`                            | `scripts/ops/l3_stitch_pipeline.js`    |
| L3 熔炼        | `<compose> -f docker-compose.dev.yml exec dev npm run smelt`                                | `scripts/ops/smelt_all.js`             |

补充说明：

- 对 AI / agents 而言，上表中的 `titan_discovery`、`run_production`、`total_war_pipeline`、`odds_harvest_pipeline` 属于 legacy/admin-only 入口清单，不是默认推荐路径。
- L1 默认推荐路径是 5.4 节的 `data-l1-*` safe workflow。

### 5.2 Recon / Backfill / Monitor

| 能力                   | 推荐入口                                                                                                             | 实际目标                        |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| Recon 扫描（唯一入口） | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/recon_scanner.js --season <season> --league <league>` | `scripts/ops/recon_scanner.js`  |
| 回填                   | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/gold_pilot_50.js`                                     | `scripts/ops/gold_pilot_50.js`  |
| 长时运行               | `<compose> -f docker-compose.dev.yml exec dev node scripts/ops/titan_marathon.js`                                    | `scripts/ops/titan_marathon.js` |
| 监控检查               | `<compose> -f docker-compose.dev.yml exec dev npm run titan:check`                                                   | `scripts/ops/check_health.js`   |
| 哨兵监控               | `<compose> -f docker-compose.dev.yml exec dev npm run titan:watch`                                                   | `scripts/ops/sentinel_watch.js` |

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

| 能力     | 推荐入口                                                          | 实际目标                                                   |
| -------- | ----------------------------------------------------------------- | ---------------------------------------------------------- |
| 训练模型 | `npm run train`                                                   | 宿主机调用后进入容器执行 `scripts/ops/train_model.py`      |
| 生成预测 | `npm run predict`                                                 | 宿主机调用后进入容器执行 `scripts/ops/predict_pipeline.py` |
| ELO 重算 | `<compose> -f docker-compose.dev.yml exec dev npm run elo:recalc` | `scripts/maintenance/recalculate_elo.js`                   |

### 5.4 数据入口安全门禁

数据收割治理以 `make data-*` 为统一入口。详细规范见：

- `docs/DATA_HARVESTING_GUIDE.md`
- `docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE4_2.md`

AI / Codex 默认只能执行：

- legacy L1/data entrypoints 对 agents 视为 deprecated：admin / 人工兼容可以继续保留，但默认不得直接运行；L1 discovery 和 matches seed 默认必须走 `data-l1-*` safe workflow。
- L2 raw JSON acquisition 仍处于 planning 阶段，默认不得触网、不得抓取 FotMob match detail、不得写 `raw_match_data`；后续必须走 controlled preview / authorization / preflight。
- Phase 5.11L2 仅允许用户明确授权的 `make data-l2-raw-detail-preview SOURCE=fotmob MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg NETWORK_AUTHORIZATION=yes ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no CONCURRENCY=1 RETRY=0 PRINT_BODY=no SAVE_BODY=no`；只输出 stdout metadata/hash/markers，不写 DB，不写 `raw_match_data`，不保存或打印完整 body。
- Phase 5.14L2 仅允许用户明确授权的 `make data-l2-raw-match-data-ingest-authorization SOURCE=fotmob ROUTE=html_hydration MATCH_ID=53_20252026_4830746 EXTERNAL_ID=4830746 HOME_TEAM=Angers AWAY_TEAM=Strasbourg DATA_VERSION=fotmob_html_hyd_v1 PREVIEW_BODY_SHA256=<sha256> HYDRATION_PARSE_OK=yes LOOKS_LIKE_VALID_MATCH_DETAIL=yes USER_AUTHORIZED_RAW_MATCH_DATA_INGEST=yes ALLOW_RAW_MATCH_DATA_WRITE_NEXT_PHASE=yes ALLOW_DB_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE_NOW=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes`；只输出 stdout authorization JSON，不触网、不写 DB、不写 `raw_match_data`。
- Phase 5.17L2 仅允许用户明确授权的 `make data-l2-remaining-raw-match-data-acquisition-plan SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 EXPECTED_SEEDED_COUNT=8 EXPECTED_EXISTING_RAW_COUNT=1 EXPECTED_MISSING_RAW_COUNT=7 ALLOW_NETWORK=no ALLOW_DB_WRITE=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_MATCHES_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no`；它只做 remaining seeded matches raw coverage planning，不触网、不写 DB、不写 `raw_match_data`，并明确 parser deferred / raw-first 策略。
- Phase 5.18L2 仅允许用户明确授权的 `make data-l2-remaining-raw-match-data-acquisition-authorization SOURCE=fotmob LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 ROUTE=html_hydration EXPECTED_SEEDED_COUNT=8 EXPECTED_EXISTING_RAW_COUNT=1 EXPECTED_MISSING_RAW_COUNT=7 REMAINING_EXTERNAL_IDS=4830747,4830748,4830750,4830751,4830752,4830753,4830754 USER_AUTHORIZED_REMAINING_RAW_ACQUISITION=yes ALLOW_NETWORK_NEXT_PHASE=yes ALLOW_RAW_MATCH_DATA_WRITE_FUTURE_PHASE=yes ALLOW_NETWORK_THIS_PHASE=no ALLOW_DB_WRITE_THIS_PHASE=no ALLOW_RAW_MATCH_DATA_WRITE_THIS_PHASE=no ALLOW_MATCHES_WRITE=no ALLOW_PARSER_FEATURES=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes`；它只做 authorization，不触网、不写 DB、不写 `raw_match_data`，并授权 7 场 remaining targets 进入 future preflight。
- `make data-help`
- `make data-check`
- `make data-l1-discovery-preview SOURCE=fotmob SCOPE=<config_only_preview|league_season_date|league_season_window_preview> ...`
- `make data-l1-discovery-candidates-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> NETWORK_AUTHORIZATION=no ...`
- 用户明确授权、仅做 candidates stdout summary、不写 DB/不启动 browser/proxy 的 `make data-l1-discovery-candidates-network-preview SOURCE=fotmob SCOPE=controlled_candidates_preview LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CONCURRENCY=1 MAX_TARGETS<=10 NETWORK_AUTHORIZATION=yes ALLOW_BROWSER_RUNTIME=no ALLOW_PROXY_RUNTIME=no ALLOW_DB_WRITE=no`
- 仅做 matches seed commit planning、不触网、不写 DB、不写 matches/raw_match_data 的 `make data-l1-matches-seed-commit-plan SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 COMMIT=no`
- 用户明确授权、只记录 stdout authorization summary、不触网、不写 DB、不写 matches/raw_match_data 的 `make data-l1-matches-seed-commit-authorization SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 USER_AUTHORIZED_MATCHES_SEED_COMMIT=yes ALLOW_MATCHES_WRITE_NEXT_PHASE=yes ALLOW_DB_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no FINAL_HUMAN_CONFIRMATION=yes`
- 用户明确授权、仅做 execution preflight、允许 safe exact candidates + SELECT-only affected matches、不写 DB、不写 matches/raw_match_data 的 `make data-l1-matches-seed-commit-execution-preflight SOURCE=fotmob SCOPE=<league_season_date|controlled_candidates_preview> LEAGUE_ID=<id> SEASON=<season> DATE=<yyyy-mm-dd> CANDIDATE_COUNT=<n> MAX_SEED_ROWS<=10 FINAL_DB_WRITE_CONFIRMATION=no ALLOW_DB_WRITE_NOW=no ALLOW_MATCHES_WRITE_NOW=no ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no`
- 用户明确授权、Phase 5.09L1 exact scope 下唯一允许的 matches 写入入口：`make data-l1-matches-seed-commit-execute SOURCE=fotmob SCOPE=league_season_date LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CANDIDATE_COUNT=8 CONTAINS_TARGET_MATCH_ID=4830746 CONTAINS_TARGET_LABEL="Angers vs Strasbourg" MAX_SEED_ROWS=10 FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_DB_WRITE_NOW=yes ALLOW_MATCHES_WRITE_NOW=yes ALLOW_RAW_MATCH_DATA_WRITE=no ALLOW_TRAINING=no ALLOW_PREDICTION=no`；仅允许事务写 `matches`，不得写 `raw_match_data`
- 用户明确授权的 `make data-local-dry-run`
- 用户明确授权且仅使用本地 fixture 的 `make data-l3-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`
- 用户明确授权且仅使用本地 fixture 的 `make data-l3-write-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`
- 用户明确授权且仅使用本地 fixture 的 `make data-raw-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`
- 安全占位且不训练、不预测、不写 DB 的 `make data-training-dry-run`
- 安全占位且不训练、不预测、不写 DB 的 `make data-prediction-dry-run`
- 用户明确授权且只读 DB 的 `make data-training-feature-dry-run MATCH_ID=<id>`
- 用户明确授权且只读 DB 的 `make data-prediction-write-dry-run MATCH_ID=<id>`
- 只读 DB 且不训练、不预测、不导出、不加载模型 artifact 的 `make data-dataset-status`
- 只读 DB 且不训练、不预测、不导出、不加载模型 artifact 的 `make data-training-dataset-dry-run`
- 不访问外网、不写 DB 的 `make data-acquisition-engines`
- 不访问外网、不写 DB 的 `make data-acquisition-engine-audit`
- 用户明确授权且只读本地 source manifest、不写 DB、不训练、不预测的 `make data-real-source-audit SOURCE_MANIFEST=<local json>`
- 用户明确授权且只读本地 source manifest + 本地 CSV、不写 DB、不训练、不预测的 `make data-real-finished-csv-dry-run SOURCE_MANIFEST=<local json> SAMPLE_CSV=<local csv>`
- 用户明确授权且只读本地 Football-Data source manifest + 本地 CSV、不写 DB、不训练、不预测、不写 staging 的 `make data-football-data-csv-dry-run SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>`
- 用户明确授权且只读本地 Football-Data source manifest + 本地 CSV、不写 DB、不执行 pg_dump、不训练、不预测的 `make data-football-data-db-write-preflight SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>`
- 用户明确授权且只读本地 Football-Data source manifest + 本地 CSV，并只执行 SELECT-only DB 查重、不写 DB、不训练、不预测的 `make data-football-data-duplicate-precheck SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>`
- 用户明确授权且只读本地 Football-Data source manifest + 本地 CSV，并只执行 SELECT-only DB schema / duplicate 查询、不写 DB、不训练、不预测的 `make data-football-data-insert-policy-precheck SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>`
- 不触网、不启动 browser、不执行 proxy runtime、不写 staging、不写 manifest、不写 DB、不运行 titan_discovery legacy runtime 的 scaffold-only 参数校验和 plan preview：`make data-single-target-acquisition-runtime-scaffold TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> ...`（Phase 4.79D scaffold-only）
- 不触网、不写文件、只读本地 schema 和 sample fixture 的 staging artifact / manifest candidate schema 校验：`make data-single-target-acquisition-staging-schema-validate ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ARTIFACT=<path> MANIFEST=<path>`（Phase 4.80D local-only）
- 不触网、不写文件、不创建目录、只做路径预览和授权预检的 staging writer preflight：`make data-single-target-acquisition-staging-writer-preflight ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ... OUTPUT_ROOT=<path> ...`（Phase 4.81D preflight-only）
- 不触网、不写文件、不创建目录、汇总 4.79D+4.80D+4.81D 安全门禁的 staging packet preview：`make data-single-target-acquisition-staging-packet-preview ARTIFACT_SCHEMA=<path> ... OUTPUT_ROOT=<path> ...`（Phase 4.82D preview-only）
- 不触网、不写文件、不创建目录、只验证 pre-network runbook draft 和 packet preview 前置条件的本地 validator：`make data-single-target-acquisition-pre-network-runbook-validate RUNBOOK=<path> ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ARTIFACT=<path> MANIFEST=<path> OUTPUT_ROOT=<path> ...`（Phase 4.83D draft-only）
- 不触网、不写文件、不创建目录、只验证 network dry-run authorization form template 和 pre-network runbook template 的本地 validator：`make data-single-target-acquisition-network-auth-form-validate AUTH_FORM=<path> RUNBOOK=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.84D template-only）
- 不触网、不写文件、不创建目录、只验证 final readiness checklist template + pre-network runbook template + network auth form template 的本地 validator：`make data-single-target-acquisition-network-readiness-checklist-validate CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.85D template-only）
- 不触网、不写文件、不创建目录、只验证 execution plan draft + final readiness checklist + runbook + auth form template 的本地 validator：`make data-single-target-acquisition-network-execution-plan-validate EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.86D draft-only）
- 不触网、不写文件、不创建目录、只预览 human approval packet + execution plan + final readiness checklist + runbook + auth form template 的本地 validator：`make data-single-target-acquisition-network-approval-packet-preview APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.87D preview-only）
- 不触网、不写文件、不创建目录、只预览 user input requirements closure + human approval packet + execution plan + final readiness checklist + runbook + auth form template 的本地 validator：`make data-single-target-acquisition-network-user-input-closure-preview INPUT_CLOSURE=<path> APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.88D closure-preview-only）
- 不触网、不写文件、不创建目录、只预览 blocked final preflight summary + user input closure + human approval packet + execution plan + final readiness checklist + runbook + auth form template 的本地 validator：`make data-single-target-acquisition-network-blocked-final-preflight-summary BLOCKED_SUMMARY=<path> INPUT_CLOSURE=<path> APPROVAL_PACKET=<path> EXECUTION_PLAN=<path> CHECKLIST=<path> RUNBOOK=<path> AUTH_FORM=<path> TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> TARGET_MATCH_ID=<id> ...`（Phase 4.89D blocked-preview-only）
- 不触网、不写文件、不创建目录、不写 DB、只预览 real-parameter intake validation closure template + real-parameter intake template + blocked preflight summary template 的本地 validator：`make data-single-target-acquisition-network-real-parameter-validation-closure-preview VALIDATION_CLOSURE=<path> INTAKE=<path> BLOCKED_SUMMARY=<path>`（Phase 4.91D template-only）
- 不触网、不写文件、不创建目录、不写 DB、只预览 filled-intake review plan template + real-parameter intake template + validation closure template + blocked preflight summary template 的本地 validator：`make data-single-target-acquisition-network-filled-intake-review-plan-preview REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>`（Phase 4.92D template-only）
- 不触网、不写文件、不创建目录、不写 DB、只预览 filled-intake review result template + review plan template + real-parameter intake template + validation closure template + blocked preflight summary template 的本地 validator：`make data-single-target-acquisition-network-filled-intake-review-result-preview REVIEW_RESULT=<path> REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>`（Phase 4.93D template-only）
- 不触网、不写文件、不创建目录、不写 DB、只预览 authorization handoff checklist template + review result + review plan + intake + validation closure + blocked summary 的本地 validator：`make data-single-target-acquisition-network-authorization-handoff-checklist-preview HANDOFF_CHECKLIST=<path> REVIEW_RESULT=<path> REVIEW_PLAN=<path> INTAKE=<path> VALIDATION_CLOSURE=<path> BLOCKED_SUMMARY=<path>`（Phase 4.94D template-only）
- 只读本地 approval form 模板、不读 DB、不写 DB、不执行 `pg_dump` / `pg_restore` 的 `make data-football-data-small-write-runbook-validate APPROVAL_FORM=<local md>`
- 只读本地 packet file creation authorization 模板、不读 DB、不写 DB、不创建目录、不写 packet 文件、不执行 `pg_dump` / `pg_restore` 的 `make data-football-data-packet-file-auth-validate AUTH_FORM=<local md>`
- 用户明确授权且只读本地 CSV、不写 DB、不训练、不预测的 `make data-finished-csv-dry-run SAMPLE_CSV=<local csv>`
- 用户明确授权、只读 DB 且只读本地 fixture 的 `make data-finished-backfill-dry-run MATCH_ID=<id>`
- 用户明确授权、只读 DB 且只读本地 JSON 的 `make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<local json>`

AI / Codex 不能直接执行：

- `make dev-harvest`
- `npm start`
- `node scripts/ops/run_production.js`
- `node scripts/ops/titan_discovery.js`
- `npm run titan:total-war`
- `npm run odds:harvest`
- `node scripts/ops/recon_scanner.js --season ...`
- `node scripts/ops/batch_historical_backfill.js`
- `npm run smelt`
- `npm run l3:stitch`
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run model:train`
- `npm run model:predict`
- `scripts/ops/smelt_all.js`
- `scripts/ops/l3_stitch_pipeline.js`
- `scripts/ops/l3_stitch_worker.js`
- `npm run elo:recalc`
- 任何写 `match_features_training` 的命令
- 任何写 `predictions` 的命令
- 任何加载或生成模型 artifact 的训练命令
- `make data-training-commit`
- `make data-training-commit CONFIRM_TRAINING=1`
- `make data-prediction-commit`
- `make data-prediction-commit CONFIRM_PREDICTION=1`
- `make data-training-feature-commit`
- `make data-training-feature-commit CONFIRM_TRAINING_FEATURE=1`
- `node scripts/ops/match_features_training_local_write_gate.js --commit`
- `make data-prediction-write-commit`
- `make data-prediction-write-commit CONFIRM_PREDICTION_WRITE=1`
- `node scripts/ops/prediction_local_write_gate.js --commit`
- `make data-training-dataset-export`
- `make data-training-dataset-export CONFIRM_DATASET_EXPORT=1`
- `make data-real-finished-csv-commit`
- `make data-real-finished-csv-commit CONFIRM_REAL_CSV_COMMIT=1`
- `node scripts/ops/real_finished_csv_staging_dry_run.js --commit`
- `make data-football-data-csv-commit`
- `make data-football-data-csv-commit CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1`
- `make data-football-data-db-write-commit`
- `make data-football-data-db-write-commit CONFIRM_FOOTBALL_DATA_DB_WRITE=1`
- `make data-football-data-duplicate-precheck-commit`
- `make data-football-data-duplicate-precheck-commit CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1`
- `make data-football-data-insert-policy-commit`
- `make data-football-data-insert-policy-commit CONFIRM_FOOTBALL_DATA_INSERT_POLICY=1`
- `make data-football-data-small-write-runbook-commit`
- `make data-football-data-small-write-runbook-commit CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1`
- `make data-football-data-packet-file-auth-commit`
- `make data-football-data-packet-file-auth-commit CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1`
- `make data-single-target-network-commit`
- `make data-single-target-network-commit CONFIRM_SINGLE_TARGET_NETWORK=1`
- `make data-single-target-acquisition-network-filled-intake-review-plan-preview`（未经授权不得运行）
- `make data-single-target-acquisition-network-filled-intake-review-plan-commit`
- `make data-single-target-acquisition-network-filled-intake-review-plan-commit CONFIRM_SINGLE_TARGET_ACQUISITION_NETWORK_FILLED_INTAKE_REVIEW_PLAN=1`
- `make data-single-target-acquisition-runtime-commit`
- `make data-single-target-acquisition-runtime-commit CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1`
- `make data-single-target-acquisition-staging-schema-commit`
- `make data-single-target-acquisition-staging-schema-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA=1`
- `make data-single-target-acquisition-staging-writer-commit`
- `make data-single-target-acquisition-staging-writer-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_WRITE=1`
- `make data-single-target-acquisition-staging-packet-commit`
- `make data-single-target-acquisition-staging-packet-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_PACKET=1`
- `node scripts/ops/acquisition_engine_gate.js --commit`
- `make data-finished-csv-commit`
- `make data-finished-csv-commit CONFIRM_FINISHED_CSV_COMMIT=1`
- `node scripts/ops/finished_csv_local_dry_run.js --commit`
- `make data-finished-backfill-commit`
- `make data-finished-backfill-commit CONFIRM_FINISHED_BACKFILL=1`
- `node scripts/ops/finished_match_backfill_preflight.js --commit`
- `make data-raw-fixture-commit`
- `make data-raw-fixture-commit CONFIRM_RAW_FIXTURE_COMMIT=1`
- `node scripts/ops/raw_fixture_adapter_dry_run.js --commit`
- `csv_bulk_loader --commit`
- 任何 finished CSV 直接写 DB 的命令
- `make data-l3-write-commit`
- `make data-l3-write-commit CONFIRM_L3_WRITE=1`
- `node scripts/ops/l3_features_local_write_gate.js --commit`
- `make data-l3-commit`
- `make data-l3-commit CONFIRM_L3_COMMIT=1`
- `make data-raw-commit`
- `node scripts/ops/raw_match_data_local_ingest.js --commit`
- 任何 `--commit` 命令
- 任何外网收割命令
- 任何写 DB 命令

Phase 5.03L1 补充约定：

- `make data-l1-discovery-preview` 仅允许 config / plan preview。
- 不得访问外部网络。
- 不得写 `matches`。
- 不得写 `raw_match_data`。
- 不得调用 `FixtureRepository.persist()`。
- 不得调用 `DiscoveryService.discover()`，除非未来阶段补齐 safe injection 或抽出 `discoverCandidates()`。
- 不得启用 browser / proxy runtime。
- `make data-l1-discovery-commit` 在 Phase 5.03L1 固定 blocked。
- 未来受控 L1 network preview 必须用户显式授权。

Phase 5.04L1 补充约定：

- L1 candidate preview 必须走 `discoverCandidates()` / safe preview path。
- `make data-l1-discovery-candidates-preview` 仅允许 `controlled_candidates_preview`。
- 默认不得访问外部网络；即使 `NETWORK_AUTHORIZATION=yes`，本阶段 CLI 仍必须 blocked / plan-only。
- 不得写 `matches`。
- 不得写 `raw_match_data`。
- 不得调用 `FixtureRepository.persist()`。
- 不得调用 `DiscoveryService.discover()`。
- 不得启动 browser / proxy runtime。
- 真实 L1 network preview 必须后续阶段另行授权。
- matches seed commit 必须后续阶段另行授权。

Phase 5.05L1 补充约定：

- L1 external network candidate preview 只能走 `make data-l1-discovery-candidates-network-preview`。
- 该入口必须调用 `discoverCandidates()`，不得运行 `titan_discovery.js`。
- 不得调用 `DiscoveryService.discover()`。
- 不得调用 `FixtureRepository.persist()`。
- 不得写 `matches`、`raw_match_data` 或任何 DB 表。
- 不得启动 browser / proxy runtime，除非未来单独阶段另行授权。
- 参数必须显式包含 source / scope / league / season / date / concurrency / maxTargets。
- 仅允许 `SOURCE=fotmob`、`SCOPE=controlled_candidates_preview`、`CONCURRENCY=1`、`MAX_TARGETS<=10`。
- 网络错误、403、429、captcha 或 block 信号必须立即停止。
- 不得自动 retry，不得降级到 browser/proxy，不得降级到 `titan_discovery.js`。

Phase 5.06L1 补充约定：

- L1 matches seed commit planning 只能走 `make data-l1-matches-seed-commit-plan`。
- `data-l1-matches-seed-commit-plan` 只允许输出 stdout planning，不得触网，不得写 DB，不得写 `matches` / `raw_match_data`。
- `make data-l1-matches-seed-commit` 固定 blocked，即使传入 `CONFIRM_L1_MATCHES_SEED_COMMIT=1`。
- matches seed commit 必须等待未来单独用户明确授权阶段。
- raw_match_data ingest 必须与 matches seed commit 分离，不得合并执行。
- matches seed 阶段不得训练、不得预测、不得加载或生成模型 artifact。
- 任何 DB write 前必须先复核 candidate mapping、upsert policy、backup policy、rollback policy。

Phase 5.07L1 补充约定：

- L1 matches seed commit authorization 只能走 `make data-l1-matches-seed-commit-authorization`。
- `data-l1-matches-seed-commit-authorization` 只允许记录 stdout authorization summary，不得触网，不得写 DB，不得写 `matches`，不得写 `raw_match_data`。
- `make data-l1-matches-seed-commit` 继续 blocked，直到 Phase 5.08L1 或后续单独执行阶段再次确认。
- matches seed commit execution 必须与 raw_match_data ingest 分离，不得合并执行。
- matches seed 各阶段不得训练、不得预测、不得加载或生成模型 artifact。

Phase 5.08L1 补充约定：

- L1 matches seed commit execution preflight 只能走 `make data-l1-matches-seed-commit-execution-preflight`。
- `data-l1-matches-seed-commit-execution-preflight` 允许 safe exact candidates preview 和 `matches` 的 SELECT-only affected rows 预览；不得写 DB，不得写 `matches`，不得写 `raw_match_data`，不得调用 `FixtureRepository.persist()`。
- `make data-l1-matches-seed-commit` 继续 blocked，直到后续单独 execution phase。
- preflight 结束后仍必须要求最终 DB-write confirmation。
- raw_match_data ingest 必须与 matches seed commit 分离，不得合并执行。
- matches seed 各阶段不得训练、不得预测、不得加载或生成模型 artifact。

Phase 5.09L1 补充约定：

- controlled matches seed commit execution 只能走 `make data-l1-matches-seed-commit-execute`。
- 该入口只允许 exact `source=fotmob`、`league_id=53`、`season=2025/2026`、`date=2026-05-10`、`candidate_count=8`、`contains_target_match_id=4830746`、`contains_target_label=Angers vs Strasbourg`。
- 必须要求 `FINAL_DB_WRITE_CONFIRMATION=yes`、`ALLOW_DB_WRITE_NOW=yes`、`ALLOW_MATCHES_WRITE_NOW=yes`。
- 只允许事务写 `matches`；不得写 `raw_match_data`、bookmaker odds、features、training、predictions。
- 不得调用 `FixtureRepository.persist()`。
- 不得运行 `titan_discovery.js`，不得调用 `DiscoveryService.discover()`。
- 不得训练，不得预测。
- L2 raw JSON acquisition 仍属于后续独立阶段。

执行 `make data-l3-dry-run` 的前提：

- 用户明确授权
- fixture 是本地文件
- 不写 DB
- 不访问外网

L3 本地 dry-run 预检背景见：`docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`

执行 `make data-training-dry-run` 或 `make data-prediction-dry-run` 的前提：

- 入口只是安全占位 / runbook preview
- 不调用 `npm run train` 或 `npm run predict`
- 不训练模型
- 不执行预测
- 不加载或生成模型 artifact
- 不写 `match_features_training`
- 不写 `predictions`
- 不写 DB
- 不访问外网

Phase 4.29 中 `make data-training-commit` 和 `make data-prediction-commit` 仍是 blocked / not wired，即使提供 `CONFIRM_TRAINING=1` 或 `CONFIRM_PREDICTION=1` 也不得执行训练、预测或写库。相关背景见：`docs/_reports/L3_FEATURES_SINGLE_INSERT_PHASE4_28.md`、`docs/_reports/L3_FEATURES_LOCAL_WRITE_GATE_PHASE4_26.md` 和 `docs/_reports/L3_FEATURES_WRITE_GATE_PREFLIGHT_PHASE4_24.md`

执行 `make data-training-feature-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 只读查询本地 DB
- 不训练模型
- 不执行预测
- 不加载或生成模型 artifact
- 不写 `match_features_training`
- 不写 `predictions`
- 不写 DB
- 不访问外网

Phase 4.30 中 `make data-training-feature-commit`、`make data-training-feature-commit CONFIRM_TRAINING_FEATURE=1` 和 `node scripts/ops/match_features_training_local_write_gate.js --commit` 仍是 blocked / not wired。禁止直接或间接执行 `npm run train`、`npm run predict`、`npm run model:train`、`npm run model:predict` 或任何写 `match_features_training` / `predictions` 的命令来替代该门禁。相关背景见：`docs/_reports/TRAINING_PREDICTION_PREFLIGHT_PHASE4_29.md` 和 `docs/_reports/L3_FEATURES_SINGLE_INSERT_PHASE4_28.md`

执行 `make data-prediction-write-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 只读查询本地 DB
- 不训练模型
- 不执行预测
- 不加载未经授权模型 artifact
- 不写 `predictions`
- 不写 DB
- 不访问外网

Phase 4.32 中 `make data-prediction-write-commit`、`make data-prediction-write-commit CONFIRM_PREDICTION_WRITE=1` 和 `node scripts/ops/prediction_local_write_gate.js --commit` 仍是 blocked / not wired。禁止直接或间接执行 `npm run predict`、`npm run predict:dry`、`npm run model:predict`、`npm run train`、`npm run model:train`、任何加载未经授权模型 artifact 的命令或任何写 `predictions` 的命令来替代该门禁。相关背景见：`docs/_reports/MATCH_FEATURES_TRAINING_SINGLE_INSERT_PHASE4_31.md` 和 `docs/_reports/TRAINING_PREDICTION_PREFLIGHT_PHASE4_29.md`

执行 `make data-dataset-status` 或 `make data-training-dataset-dry-run` 的前提：

- 入口只做 SELECT-only DB 审计
- 不训练模型
- 不执行预测
- 不加载或生成模型 artifact
- 不导出数据集或大文件
- 不写 DB
- 不访问外网

Phase 4.36 中 `make data-training-dataset-export` 和 `make data-training-dataset-export CONFIRM_DATASET_EXPORT=1` 仍是 blocked / not wired。真实训练前必须先通过 dataset readiness report；单条 local sample 不能作为真实训练集；scheduled match 不能作为训练 label；`P4_LOCAL_BASELINE` manual / baseline prediction 不是模型输出；`predictions` 表不能反哺训练。相关背景见：`docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md` 和 `docs/_reports/PREDICTION_SINGLE_INSERT_PHASE4_34B.md`

执行 `make data-finished-csv-dry-run SAMPLE_CSV=<local csv>` 的前提：

- 用户明确授权
- CSV 是本地文件
- 入口只做 dry-run 解析和可选 SELECT-only DB 查重
- 不写 DB
- 不训练模型
- 不执行预测
- 不访问外网
- 不导出数据集或大文件

Phase 4.38 中 `make data-finished-csv-commit`、`make data-finished-csv-commit CONFIRM_FINISHED_CSV_COMMIT=1` 和 `node scripts/ops/finished_csv_local_dry_run.js --commit` 仍是 blocked / not wired。finished CSV import 必须先 dry-run；label mapping 必须在报告中确认；scheduled / unlabeled rows 不可作为训练样本；外部 CSV 下载仍禁止，公开数据源也必须先人工确认许可和用途。相关背景见：`docs/_reports/FINISHED_MATCH_SOURCE_AUDIT_PHASE4_37.md`、`docs/_reports/DATASET_STATUS_AUDIT_GATE_PHASE4_36.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

执行 `make data-real-source-audit SOURCE_MANIFEST=<local json>` 的前提：

- 用户明确授权
- source manifest 是本地文件
- 入口只做 manifest 完整性和 provenance 只读检查
- 不写 DB
- 不训练模型
- 不执行预测
- 不访问外部足球数据源
- 不导出数据

执行 `make data-real-finished-csv-dry-run SOURCE_MANIFEST=<local json> SAMPLE_CSV=<local csv>` 的前提：

- 用户明确授权
- source manifest 和 CSV 都是本地文件
- 入口只做 manifest + CSV 只读解析
- DB duplicate check 仅允许 SELECT-only
- 不写 DB
- 不训练模型
- 不执行预测
- 不加载 model artifact
- 不下载外部数据
- 不访问外部足球数据源
- finished score / `actual_result` 只能做 label
- post-match stats 不得作为赛前 feature
- synthetic rows 不得混入真实训练
- `predictions` 表不得反哺训练

Phase 4.52 中 `make data-real-finished-csv-commit`、`make data-real-finished-csv-commit CONFIRM_REAL_CSV_COMMIT=1` 和 `node scripts/ops/real_finished_csv_staging_dry_run.js --commit` 仍是 blocked / not wired。没有完整 source manifest，不得 dry-run；没有 license / provenance，不得 commit；真实写库前必须 `pg_dump` + 小批量授权。相关背景见：`docs/_reports/REAL_FINISHED_CSV_STAGING_DRY_RUN_PHASE4_52.md`、`docs/_reports/REAL_DATA_SOURCE_STRATEGY_PHASE4_51.md`、`docs/_reports/SYNTHETIC_CHAIN_CLOSURE_PHASE4_50.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

真实 finished match 数据源接入前置规则：

AI / Codex 默认禁止：

- 直接下载外部足球数据
- 对外部数据源执行 `curl` / `wget` / `git clone`
- scraping / browser automation / harvest
- 导入无 license / provenance 的数据
- 写入真实数据
- 把 synthetic 数据用于真实训练
- 把 post-match stats 当作赛前 features
- 把 `predictions` 反哺训练

AI / Codex 允许：

- 本地只读审计
- 用户已提供本地文件的 dry-run
- source manifest 完整性检查
- schema mapping preview
- duplicate / label readiness preview

真实数据写入必须满足：

- 用户单独授权
- source manifest 完整
- license / terms 已人工确认
- dry-run 报告通过
- `pg_dump` 备份
- 小批量优先
- commit gate 显式授权
- 不训练、不预测，除非另行授权

没有 license / terms 结论前，不得导入；没有 provenance metadata，不得导入；外部下载必须单独授权；写库必须单独授权并完成备份。Phase 4.51 后应停止继续堆 synthetic 数据，下一步转向真实 finished match source / license / provenance / schema mapping 和 local staging dry-run。相关背景见：`docs/_reports/REAL_DATA_SOURCE_STRATEGY_PHASE4_51.md`、`docs/_reports/SYNTHETIC_CHAIN_CLOSURE_PHASE4_50.md`、`docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`、`docs/_reports/FINISHED_MATCH_SOURCE_AUDIT_PHASE4_37.md` 和 `docs/_reports/FINISHED_CSV_DRY_RUN_GATE_PHASE4_38.md`

真实数据 acquisition engine 前置规则：

AI / Codex 默认禁止：

- `node scripts/ops/run_production.js`
- `node scripts/ops/titan_discovery.js`
- `node scripts/ops/recon_scanner.js --season ...`
- `node scripts/ops/batch_historical_backfill.js`
- `node scripts/ops/fetch_and_adapt_euro_leagues.js`
- `node scripts/ops/local_dom_ingestor.js --commit`
- `node scripts/ops/csv_bulk_loader.js --commit`
- `npm start`
- `make dev-harvest`
- `make data-harvest`
- `make data-network-dry-run`
- odds harvest / total war / marathon / bulk harvest 入口
- 任何会访问外部足球数据源的命令
- 任何会写 DB 的 acquisition / ingest command
- 任何会批量抓取的命令
- 任何没有 source manifest 的真实数据接入

AI / Codex 允许：

- 只读扫描源码、文档、Makefile 和 package scripts
- 已有 local staging CSV dry-run
- source manifest audit
- 不访问外网的 preflight gate

未来 network dry-run 必须满足：

- 用户单独授权
- 目标 source 明确
- 目标范围极小，例如单场 match_id 或 very small date window
- source manifest draft 存在
- 不写 DB
- 不批量
- 不训练
- 不预测
- 不绕过 ToS / login / paywall / anti-bot
- 输出 local staging 文件、hash、timestamp、source_url、engine_version 和 provenance
- 后续入库必须另行授权并完成 `pg_dump`

Phase 4.53A 后，项目真实数据应先进入 `target source -> acquisition network dry-run -> local staging -> source manifest -> dry-run gate` 链路，不得走 `target source -> bulk harvest -> DB commit -> training` 直通链路。相关背景见：`docs/_reports/ACQUISITION_ENGINE_READINESS_PHASE4_53A.md`、`docs/_reports/REAL_DATA_SOURCE_STRATEGY_PHASE4_51.md`、`docs/_reports/REAL_FINISHED_CSV_STAGING_DRY_RUN_PHASE4_52.md` 和 `docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE4_2.md`

Phase 4.54 acquisition registry / scaffold-only gate 规则：

AI / Codex 默认允许：

- `make data-acquisition-engines`
- `make data-acquisition-engine-audit`

AI / Codex 只能在用户明确授权下运行：

- `make data-single-target-network-dry-run ENGINE=<engine> TARGET_MATCH_ID=<id> SOURCE_MANIFEST=<path>`

但在 Phase 4.54 中，上述命令仍然只是 scaffold-only，不访问外网，不执行真实 acquisition engine。

AI / Codex 默认禁止：

- `make data-single-target-network-commit`
- `make data-single-target-network-commit CONFIRM_SINGLE_TARGET_NETWORK=1`
- `make data-single-target-acquisition-runtime-commit`
- `make data-single-target-acquisition-runtime-commit CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1`
- `make data-single-target-acquisition-staging-schema-commit`
- `make data-single-target-acquisition-staging-schema-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA=1`
- `make data-single-target-acquisition-staging-writer-commit`
- `make data-single-target-acquisition-staging-writer-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_WRITE=1`
- `node scripts/ops/acquisition_engine_gate.js --commit`
- `node scripts/ops/run_production.js`
- `node scripts/ops/titan_discovery.js`
- `node scripts/ops/recon_scanner.js --season ...`
- `node scripts/ops/batch_historical_backfill.js`
- `node scripts/ops/fetch_and_adapt_euro_leagues.js`
- `node scripts/ops/odds_harvest_pipeline.js`
- `node scripts/ops/total_war_pipeline.js`
- `node scripts/ops/titan_marathon.js`
- `npm start`
- `make dev-harvest`
- `make data-harvest`
- `make data-network-dry-run`

补充约束：

- Phase 4.54 只做 registry + scaffold-only gate
- 不允许真正访问外网
- 不允许保存 staging
- 不允许写 DB
- 不允许训练
- 不允许预测
- 未来真正 network dry-run 必须在单独阶段、获得单独授权

### Phase 4.79D: single-target acquisition runtime scaffold

`data-single-target-acquisition-runtime-scaffold` 只允许参数校验和 runtime plan preview：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得写 staging
- 它不得写 manifest
- 它不得写 DB
- 它不得运行 titan_discovery legacy runtime
- 它不得执行任何 acquisition engine
- 它不得 spawn child process

`data-single-target-acquisition-runtime-commit` 当前 blocked。即使用户提供 yes 字段，Phase 4.79D 也只是 scaffold-only，不等于授权真实 network dry-run。

真实 network dry-run 必须后续单独阶段、明确 source / target / terms / network authorization / staging policy。

在 Phase 4.79D 中允许：

- `make data-single-target-acquisition-runtime-scaffold TARGET_SOURCE=<src> TARGET_ENGINE_FAMILY=titan_discovery TARGET_SCOPE_TYPE=<type> ...`
- `node scripts/ops/single_target_acquisition_runtime_scaffold.js --target-source=... --target-engine-family=titan_discovery --target-scope-type=... ...`

在 Phase 4.79D 中严格禁止：

- `make data-single-target-acquisition-runtime-commit`
- `make data-single-target-acquisition-runtime-commit CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1`
- `node scripts/ops/single_target_acquisition_runtime_scaffold.js --commit`
- 以及上述所有禁止的 legacy / high-risk 命令

### Phase 4.80D: single-target acquisition staging schema validator

`data-single-target-acquisition-staging-schema-validate` 只允许本地 schema / sample fixture 校验：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 DB
- sample fixture 不等于真实 staging artifact
- schema validator 不等于 staging write authorization
- source manifest candidate 不等于 DB write authorization

`data-single-target-acquisition-staging-schema-commit` 当前 blocked。

真实 staging write 必须后续单独阶段、用户明确授权。

在 Phase 4.80D 中允许：

- `make data-single-target-acquisition-staging-schema-validate ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ARTIFACT=<path> MANIFEST=<path>`
- `node scripts/ops/single_target_acquisition_staging_schema_validator.js --artifact-schema=... --artifact=...`

在 Phase 4.80D 中严格禁止：

- `make data-single-target-acquisition-staging-schema-commit`
- `make data-single-target-acquisition-staging-schema-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA=1`
- `node scripts/ops/single_target_acquisition_staging_schema_validator.js --commit`

### Phase 4.81D: single-target acquisition staging writer preflight

`data-single-target-acquisition-staging-writer-preflight` 只允许 staging writer preflight：

- 它不得创建 staging 目录
- 它不得写 staging artifact
- 它不得写 source manifest
- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 DB
- staging writer preflight 不等于 staging write authorization
- 即使 `STAGING_WRITE_AUTHORIZATION=yes` 和 `FINAL_HUMAN_CONFIRMATION=yes`，Phase 4.81D 也不写文件

`data-single-target-acquisition-staging-writer-commit` 当前 blocked。

真实 staging write 必须后续单独阶段、用户明确授权、路径明确、schema validation 通过。

在 Phase 4.81D 中允许：

- `make data-single-target-acquisition-staging-writer-preflight ARTIFACT_SCHEMA=<path> MANIFEST_SCHEMA=<path> ...`
- `node scripts/ops/single_target_acquisition_staging_writer_preflight.js --artifact-schema=... ...`

在 Phase 4.81D 中严格禁止：

- `make data-single-target-acquisition-staging-writer-commit`
- `make data-single-target-acquisition-staging-writer-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_WRITE=1`
- `node scripts/ops/single_target_acquisition_staging_writer_preflight.js --commit`

### Phase 4.82D: single-target acquisition staging packet preview

`data-single-target-acquisition-staging-packet-preview` 汇总 4.79D scaffold + 4.80D schema + 4.81D preflight 为一个 packet preview：

- 它不得创建 staging 目录
- 它不得写 staging artifact
- 它不得写 source manifest
- 它不得写 packet file
- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 DB
- staging packet preview 不等于 staging write authorization
- staging packet preview 不等于 network dry-run authorization
- 即使所有授权字段为 yes，Phase 4.82D 也不写文件、不触网、不写 DB

`data-single-target-acquisition-staging-packet-commit` 当前 blocked。

在 Phase 4.82D 中严格禁止：

- `make data-single-target-acquisition-staging-packet-commit`
- `make data-single-target-acquisition-staging-packet-commit CONFIRM_SINGLE_TARGET_ACQUISITION_STAGING_PACKET=1`
- `node scripts/ops/single_target_acquisition_staging_packet_preview.js --commit`

相关背景见：`docs/_reports/ACQUISITION_ENGINE_READINESS_PHASE4_53A.md`、`docs/_reports/REAL_DATA_SOURCE_STRATEGY_PHASE4_51.md` 和 `docs/_reports/REAL_FINISHED_CSV_STAGING_DRY_RUN_PHASE4_52.md`

### Phase 4.83D: single-target acquisition pre-network runbook draft

`data-single-target-acquisition-pre-network-runbook-validate` 只允许验证 pre-network runbook draft：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 DB
- pre-network runbook draft 不等于 network dry-run authorization
- 即使 CLI 传入 yes，Phase 4.83D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-pre-network-runbook-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确授权、参数齐全、terms approval 齐全、runbook 审核通过。

### Phase 4.84D: single-target acquisition network dry-run authorization form

`data-single-target-acquisition-network-auth-form-validate` 只允许验证 network dry-run authorization form template：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 DB
- authorization form template 不等于真实 network dry-run authorization
- 即使 CLI 传入 yes，Phase 4.84D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-auth-form-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确授权、参数齐全、terms approval 齐全、runbook 审核通过。

### Phase 4.85D: single-target acquisition network dry-run final readiness checklist

`data-single-target-acquisition-network-readiness-checklist-validate` 只允许验证 final readiness checklist template：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 DB
- final readiness checklist template 不等于真实 network dry-run authorization
- 即使 CLI 传入 yes，Phase 4.85D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-readiness-checklist-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确授权、参数齐全、terms approval 齐全、runbook / auth form / readiness checklist 全部审核通过。

### Phase 4.86D: single-target acquisition network dry-run execution plan draft

`data-single-target-acquisition-network-execution-plan-validate` 只允许验证 execution plan draft：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 DB
- execution plan draft 不等于真实 network dry-run authorization
- 即使 CLI 传入 yes，Phase 4.86D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-execution-plan-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确授权、参数齐全、terms approval 齐全、runbook / auth form / readiness checklist / execution plan 全部审核通过。

### Phase 4.87D: single-target acquisition network dry-run human approval packet preview

`data-single-target-acquisition-network-approval-packet-preview` 只允许预览 human approval packet：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 DB
- human approval packet preview 不等于真实 network dry-run authorization
- 即使 CLI 传入 yes，Phase 4.87D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-approval-packet-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确授权、参数齐全、terms approval 齐全、runbook / auth form / readiness checklist / execution plan / human approval packet 全部审核通过。

### Phase 4.88D: single-target acquisition network dry-run user input requirements closure

`data-single-target-acquisition-network-user-input-closure-preview` 只允许预览 user input requirements closure：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 user input closure file
- 它不得写 DB
- user input requirements closure 不等于真实 network dry-run authorization
- Codex 不得自行填写真实 source / target / terms / authorization
- 即使 CLI 传入 yes，Phase 4.88D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-user-input-closure-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、terms approval、network authorization、runbook / auth form / readiness checklist / execution plan / approval packet 全部审核通过。

### Phase 4.89D: single-target acquisition network dry-run blocked final preflight summary

`data-single-target-acquisition-network-blocked-final-preflight-summary` 只允许预览 blocked final preflight summary：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 user input closure file
- 它不得写 blocked summary file
- 它不得写 DB
- blocked final preflight summary 不等于真实 network dry-run authorization
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 blocked 改成 ready
- 即使 CLI 传入 yes，Phase 4.89D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-blocked-final-preflight-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、terms approval、network authorization、runbook / auth form / readiness checklist / execution plan / approval packet / input closure 全部审核通过。

### Phase 4.90D: single-target acquisition network dry-run real-parameter intake template

`data-single-target-acquisition-network-real-parameter-intake-preview` 只允许预览 real-parameter intake template：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 blocked summary file
- 它不得写 real parameter intake file
- 它不得写 DB
- real-parameter intake template 不等于真实 network dry-run authorization
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 provided 改成 true
- 即使 CLI 传入确认参数，Phase 4.90D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-real-parameter-intake-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、terms approval、network authorization、runbook / auth form / readiness checklist / execution plan / approval packet / input closure / blocked preflight 全部审核通过。

### Phase 4.91D: single-target acquisition network dry-run real-parameter intake validation closure

`data-single-target-acquisition-network-real-parameter-validation-closure-preview` 只允许预览 real-parameter intake validation closure：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 blocked summary file
- 它不得写 real parameter intake file
- 它不得写 validation closure file
- 它不得写 DB
- real-parameter validation closure 不等于真实 network dry-run authorization
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 validation_passed 改成 true
- Codex 不得自行把 real_parameter_intake_validated 改成 true
- 即使 CLI 传入确认参数，Phase 4.91D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-real-parameter-validation-closure-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、再经过独立 validation / terms / authorization review。validation closure 只定义校验规则，不授权任何执行。

### Phase 4.92D: single-target acquisition network dry-run filled-intake review plan

`data-single-target-acquisition-network-filled-intake-review-plan-preview` 只允许预览 filled-intake review plan：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 blocked summary file
- 它不得写 real parameter intake file
- 它不得写 validation closure file
- 它不得写 filled-intake review file
- 它不得写 DB
- filled-intake review plan 不等于真实 intake review 结果
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 review_passed 改成 true
- Codex 不得自行 accept filled intake
- 即使 CLI 传入确认参数，Phase 4.92D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-filled-intake-review-plan-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、再经过独立 filled-intake review / terms / authorization review。review plan 只定义审阅流程，不授权任何执行。

### Phase 4.93D: single-target acquisition network dry-run filled-intake review result

`data-single-target-acquisition-network-filled-intake-review-result-preview` 只允许预览 filled-intake review result template：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 titan_discovery legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 blocked summary file
- 它不得写 real parameter intake file
- 它不得写 validation closure file
- 它不得写 filled-intake review plan file
- 它不得写 filled-intake review result file
- 它不得写 DB
- filled-intake review result template 不等于真实 review result
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 reviewed / passed / accepted 改成 true
- Codex 不得自行 authorize network dry-run
- 即使 CLI 传入确认参数，Phase 4.93D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-filled-intake-review-result-commit` 当前 blocked。

真实 network dry-run 必须后续单独阶段、用户明确给齐真实参数、再经过独立 filled-intake review result / terms / authorization review。review result template 只定义记录格式，不授权任何执行。

### Phase 4.94D: single-target acquisition network dry-run authorization handoff checklist

`data-single-target-acquisition-network-authorization-handoff-checklist-preview` 只允许预览 authorization handoff checklist template：

- 它不得触网/启动 browser/执行 proxy runtime/运行 legacy runtime
- 它不得写 staging/source manifest/packet/approval/closure/runtime 文件
- 它不得写 DB
- authorization handoff checklist 不等于真实 authorization
- Codex 不得自行把 checked/passed/completed/ready 改成 true
- Codex 不得自行 authorize network dry-run
- 即使 CLI 传入确认参数，Phase 4.94D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-authorization-handoff-checklist-commit` 当前 blocked。

真实 network dry-run 必须后续单独 authorization 阶段。

### Phase 4.95D: single-target acquisition network dry-run authorization decision

`data-single-target-acquisition-network-authorization-decision-preview` 只允许预览 network authorization decision template：

- 它不得触网
- 它不得启动 browser
- 它不得执行 proxy runtime
- 它不得运行 `titan_discovery` legacy runtime
- 它不得写 staging
- 它不得写 source manifest
- 它不得写 packet file
- 它不得写 approval packet file
- 它不得写 blocked summary file
- 它不得写 real parameter intake file
- 它不得写 validation closure file
- 它不得写 filled-intake review plan file
- 它不得写 filled-intake review result file
- 它不得写 authorization handoff checklist file
- 它不得写 network authorization decision file
- 它不得写 DB
- network authorization decision template 不等于真实 authorization
- network authorization decision 也不等于 network dry-run execution
- Codex 不得自行填写真实 source / target / terms / authorization
- Codex 不得自行把 `authorization_decision` 改成 authorized
- Codex 不得自行把 `network_dry_run_authorized` 改成 true
- Codex 不得自行把 `network_dry_run_execution_allowed` 改成 true
- 即使 CLI 传入确认参数，Phase 4.95D 也不触网、不写文件、不写 DB

`data-single-target-acquisition-network-authorization-decision-commit` 当前 blocked。

真实 network dry-run 必须后续单独 execution preparation / final confirmation 阶段。

Phase 4.55C acquisition architecture rules：

- Codex 不应直接运行 legacy / high-risk acquisition engines，尤其是 `run_production`、`titan_discovery`、`recon_scanner`、`batch_historical_backfill`、`fetch_and_adapt_euro_leagues`、`odds_harvest_pipeline`、`total_war_pipeline`、`titan_marathon`。
- acquisition canonical path 应为 `source -> staging -> manifest -> dry-run -> approval -> pg_dump -> small DB write`，而不是 `bulk harvest -> DB commit -> training`。
- Codex 应优先通过 `registry / gate / manifest / dry-run` 路线操作，不应绕过 `make data-*` 门禁直接调用引擎脚本。
- bulk pipeline 只有在真实数据链路、manifest、staging、small write 和回滚策略成熟后才考虑恢复；在此之前保持 gate-only / quarantine。
- 任何新 acquisition engine 必须先登记到 registry，再决定是否允许进入 `allowed_read_only` 或未来 network dry-run。
- 任何 engine 进入 `allowed_read_only` 前，必须先具备 no-network / no-db tests。
- 任何 network dry-run 都必须单独授权；任何 DB write 都必须单独授权并先完成 `pg_dump`。

Phase 4.56C registry governance rules：

- acquisition registry 是治理总表，不只是风险清单。
- 任何新增 acquisition engine 必须注册到 registry，并包含 `owner`、`status`、`intended_layer`、`replacement_plan`、`deprecation_status`、`canonical_entrypoint`、`allowed_next_phase`、`test_coverage`。
- 只有 `canonical` engine 才能作为推荐主干入口。
- `gate_only` engine 只能通过 gate 使用；`quarantine` / `legacy_blocked` engine 禁止 Codex 直接执行。
- `adapter_candidate` 只能作为未来重写参考，不得直接运行旧 pipeline。
- `allowed_next_phase` 决定 Codex 是否可进入下一阶段；任何从 `blocked` 升级到可用状态都必须先补测试和报告。
- network dry-run 仍需单独授权；DB write 仍需单独授权并完成 `pg_dump`。

Phase 4.77D acquisition runtime / ingestion order rules：

- 真实 acquisition 主路线必须先经过 `source -> engine -> proxy/browser/network runtime -> staging -> manifest -> dry-run audit -> ordered DB write` 审计。
- 本地 CSV dry-run、packet preview 和 packet closure 只是 safety harness / 入库前审计工具，不是最终 acquisition 主路线，也不能替代真实 acquisition engine 设计。
- high-risk legacy engines 仍默认 blocked，包括 `run_production`、`titan_discovery`、`recon_scanner`、`batch_historical_backfill`、`fetch_and_adapt_euro_leagues`、`odds_harvest_pipeline`、`total_war_pipeline`、`titan_marathon`。
- 代理、浏览器、Redis、DB write 和本地文件写入耦合未拆清前，AI / Codex 不得直接运行这些 engine，也不得把它们的 `--dry-run` 当作安全采集 dry-run。
- 真实 network dry-run 必须 single-target、用户单独授权、目标 source 和 terms 明确、只落 staging、不写 DB、不训练、不预测，并且后续 DB write 必须另行授权和先完成 `pg_dump`。
- DB 入库顺序必须先确定 `matches.match_id`，再分别进入赔率 / raw data 写入，之后才允许 L3、training features 和 predictions 的单独 gate；`predictions` 不得反哺 training。

Phase 4.78D single-target acquisition runtime design rules：

- Phase 4.78D 只允许 single-target acquisition runtime design，不允许执行真实 network dry-run、采集、browser automation、staging write、DB write、训练或预测。
- `titan_discovery` 能力族可以作为未来 first single-target discovery adapter 的候选，但 `scripts/ops/titan_discovery.js` legacy runtime 仍 blocked，不能直接运行，也不能把其 `--dry-run` 当作安全采集 dry-run。
- proxy / browser / network preflight 只是配置与授权前置检查，不等于采集授权；browser launch 和 proxy health check 也不等于允许访问外部 source。
- staging artifact schema 只是设计产物，不等于 staging write authorization；source manifest candidate 也不等于 DB write authorization。
- 未来 network dry-run 必须 single-target、用户明确授权、source / terms 明确、最多只落 staging、不写 DB、不训练、不预测，且后续 DB write 必须另行授权并先完成 `pg_dump`。

Phase 4.96F FotMob single-target dry-run readiness rules：

- FotMob legacy runtime must not be executed directly by agents.
- `scripts/ops/titan_discovery.js` is not a trusted single-target dry-run adapter.
- `run_production` / `ProductionHarvester` / `FotMobStrategy` must not be used for the first safe FotMob dry-run.
- `FixtureRepository.persist` and `Persistence.dualSave` are DB/file write paths and must remain blocked unless separately authorized.
- FotMob browser / proxy / session helpers must not be launched without explicit user authorization.
- A future FotMob dry-run must first use a trusted single-target adapter scaffold.
- The first FotMob network dry-run should be stdout-only, no DB, no staging, and no browser/proxy by default.

Phase 4.97F FotMob trusted single-target adapter scaffold rules：

- FotMob trusted single-target adapter scaffold is allowed only for no-network preflight.
- `make data-fotmob-single-target-adapter-preflight` must not access external FotMob or any external football / odds data source.
- `make data-fotmob-single-target-adapter-preflight` must not launch browser or proxy runtime.
- `make data-fotmob-single-target-adapter-preflight` must not write staging, source manifest, packet, or DB.
- `make data-fotmob-single-target-adapter-commit` is blocked.
- CLI `yes` flags must not override Phase 4.97F blocked behavior.
- Future FotMob network dry-run requires explicit user target, terms, allowed-use, and network authorization in a separate phase.

Phase 4.98F FotMob adapter preflight hardening rules：

- FotMob adapter preflight may generate source manifest candidate preview only to stdout.
- It must not write source manifest files.
- Parser confidence in Phase 4.98F is stub-only and must not parse real network responses.
- Response schema preview in Phase 4.98F is stub-only and must not validate real remote payloads.
- All `yes` flags remain blocked until an explicit future authorization phase.
- Network dry-run remains prohibited in Phase 4.98F.

Phase 4.99F FotMob stdout-only network dry-run authorization packet rules：

- FotMob stdout-only network dry-run authorization packet is template-only in Phase 4.99F.
- It must not access external FotMob or execute a network dry-run.
- It must not write runtime packet files, staging, source manifest, packet, or DB.
- Codex must not self-fill a real FotMob target, source terms, license, or allowed-use approval.
- Codex must not self-authorize network access or convert the authorization packet into execution.
- Future FotMob stdout-only network dry-run requires an explicit user-filled authorization packet and a separate execution phase.

Phase 5.00F FotMob stdout-only network dry-run execution plan rules：

- FotMob stdout-only network dry-run execution plan is template-only in Phase 5.00F.
- It must not access external FotMob or execute a network dry-run.
- It must not write runtime execution plan files, staging, source manifest, packet, or DB.
- Codex must not self-fill a real FotMob target, source terms, license, or allowed-use approval.
- Codex must not self-authorize network access or convert the execution plan into execution.
- Phase 5.00F is intended to stop template expansion and wait for user real input.
- Next action after Phase 5.00F should be user-provided real FotMob target, terms, allowed-use, and authorization, not automatic Phase 5.01F.

Phase 4.57C football-data adapter rules：

- `fetch_and_adapt_euro_leagues` 属于 `adapter_candidate`，不是 Codex 可直接执行入口。
- Codex 不得直接运行 `node scripts/ops/fetch_and_adapt_euro_leagues.js`。
- 未来如要使用 Football-Data 类 CSV 来源，必须先有本地 `source manifest`，再人工确认 license / terms，再做 local staging / dry-run。
- 任何 football-data network dry-run 都必须单独授权；不得把 legacy downloader 直接接到 DB / training。
- 当前只允许通过 acquisition registry / gate 检查 `fetch_and_adapt_euro_leagues` 的 readiness，不允许直接复用其 legacy downloader runtime。
- Phase 4.61C 后，`fetch_and_adapt_euro_leagues` 只能作为 pure parser / local CSV adapter 的抽取参考；parser 必须 no-network / no-db / no-file-write。
- Phase 4.62C 的 `scripts/lib/football_data_local_csv_parser.js` 是 pure parser，只能处理调用方提供的本地 CSV text / rows 或本地 fixture。
- 在用户明确授权下，Codex 可以运行 `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_local_csv_parser.test.js`。
- `football_data_local_csv_parser` 不得访问外网、不得读 / 写 DB、不得写文件、不得 import `scripts/ops/fetch_and_adapt_euro_leagues.js` legacy runtime。
- `FTHG` / `FTAG` / `FTR` 只能用于 finished label 映射，不得作为赛前 feature；`B365H/B365D/B365A`、`PSH/PSD/PSA` 等 odds columns 只能 preview，不得写 `odds` 或 `bookmaker_odds_history`。
- Phase 4.63C 的 `make data-football-data-csv-dry-run SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>` 是本地 source manifest + CSV dry-run gate；仅在用户提供本地路径并明确授权时运行。
- `data-football-data-csv-dry-run` 只能读取本地 manifest / CSV，校验 sha256、row_count 和 approval_status，然后调用 pure parser；不得触网、不得读 / 写 DB、不得写 adapted CSV / staging 文件、不得 import `fetch_and_adapt_euro_leagues` legacy runtime。
- `make data-football-data-csv-commit` 和 `make data-football-data-csv-commit CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1` 当前仍 blocked / not wired。
- Phase 4.64C 的 `make data-football-data-db-write-preflight SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>` 是 DB write 前置 runbook preview，不是真写库；只能读取本地 manifest / CSV 并复用 dry-run 结果。
- `data-football-data-db-write-preflight` 不得触网、不得读 / 写 DB、不得执行 `pg_dump`、不得写文件、不得 import legacy downloader runtime；`make data-football-data-db-write-commit` 当前 blocked / not wired。
- Phase 4.65C 的 `make data-football-data-duplicate-precheck SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>` 是入库前 SELECT-only duplicate / existing match precheck；只能读取本地 manifest / CSV 并对 DB 执行 `BEGIN READ ONLY` + `SELECT` + `ROLLBACK`。
- `data-football-data-duplicate-precheck` 不得写 DB、不得执行 `pg_dump`、不得写文件、不得触网、不得 import legacy downloader runtime；`make data-football-data-duplicate-precheck-commit` 当前 blocked / not wired。
- Phase 4.67C 的 `make data-football-data-small-write-auth-preview SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>` 是 small DB write 授权预览；只能读取本地 manifest / CSV，复用 dry-run / preflight / duplicate / insert policy 结果，并执行 SELECT-only DB row count / schema inspection。
- `data-football-data-small-write-auth-preview` 不得写 DB、不得执行 `pg_dump`、不得执行 `pg_restore`、不得写 backup 文件、不得触网、不得 import legacy downloader runtime；`make data-football-data-small-write-commit` 当前 blocked / not wired。
- Phase 4.68C 的 `docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md` 是未来真实写库 runbook 模板，不是执行授权。
- Phase 4.68C 的 `docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md` 默认 `approval_status=not_approved`，Codex 不得把模板当作真实 approval，不得自行改成 `approved_for_db_write`，不得自行填写 `final_human_confirmation=true`。
- `make data-football-data-small-write-runbook-validate APPROVAL_FORM=<local md>` 只验证本地模板；不得读 DB、写 DB、执行 `pg_dump` / `pg_restore`、写 backup、触网、训练或预测。
- `make data-football-data-small-write-runbook-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1` 也不得执行真实写库。
- 真实 small DB write 必须在单独阶段进行，且必须有用户明确授权、真实 `pg_dump`、非空备份验证、小批量 transaction 和 post-write validation。
- Phase 4.69C 的 `make data-football-data-small-write-packet-preview SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只组装 stdout dry-run packet preview，不创建 packet 文件。
- `data-football-data-small-write-packet-preview` 不得写 DB、不得执行 `pg_dump` / `pg_restore`、不得把 approval form 变成真实授权、不得把 `approval_status` 改成 `approved_for_db_write`、不得把 `final_human_confirmation` 改成 `true`。
- `make data-football-data-small-write-packet-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_SMALL_WRITE_PACKET=1` 也不得执行真实 packet 写入或 DB write。
- 真实 packet 文件创建、真实 `pg_dump` 和真实 small DB write 必须在单独阶段进行，并需要用户明确授权。
- Phase 4.70C 的 `make data-football-data-packet-file-preflight SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只预览未来 packet 文件路径和 metadata，不创建目录，也不写 packet 文件。
- `data-football-data-packet-file-preflight` 不得创建目录、不得写 packet 文件、不得写 DB、不得执行 `pg_dump` / `pg_restore`、不得把 approval form 变成真实授权、不得把 `approval_status` 改成 `approved_for_db_write`、不得把 `final_human_confirmation` 改成 `true`。
- `make data-football-data-packet-file-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE=1` 也不得创建真实 packet 文件、执行真实 `pg_dump` 或执行真实 DB write。
- Phase 4.71C 的 `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_FORM_TEMPLATE.md` 是未来 packet 文件创建授权模板，不是真实授权。
- Phase 4.71C 的 packet file creation auth form 默认 `authorization_status=not_authorized`、默认 `final_packet_creation_confirmation=false`；Codex 不得自行改成 `authorized_for_packet_file_creation` 或 `true`。
- `make data-football-data-packet-file-auth-validate AUTH_FORM=<local md>` 只验证本地 packet file creation authorization 模板；不得读 DB、写 DB、创建目录、写 packet 文件、执行 `pg_dump` / `pg_restore`、训练或预测。
- `make data-football-data-packet-file-auth-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH=1` 也不得创建真实 packet 文件、创建 packet 目录、写 packet manifest、执行真实 `pg_dump` 或执行真实 DB write。
- Phase 4.72C 的 `make data-football-data-packet-file-auth-review AUTH_FORM=<local md> SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只做 dry-run authorization review；不得创建目录、不得写 packet 文件、不得写 DB、不得执行 `pg_dump` / `pg_restore`。
- `data-football-data-packet-file-auth-review` 不得把 `authorization_status` 改成 `authorized_for_packet_file_creation`，也不得把 `final_packet_creation_confirmation` 改成 `true`；真实 packet file creation authorization 与 DB write / `pg_dump` / training / prediction 权限分离。
- `make data-football-data-packet-file-auth-review-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW=1` 也不得创建真实 packet 文件、创建 packet 目录、执行真实 `pg_dump` / `pg_restore` 或执行真实 DB write。
- Phase 4.73C 的 `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_READINESS_CHECKLIST_TEMPLATE.md` 是未来 packet 文件创建之前的 readiness 汇总模板，不是授权表。
- Phase 4.73C 的 readiness checklist 默认 `readiness_status=not_ready`、默认 `packet_file_creation_ready=false`、默认 `packet_file_creation_authorized=false`；Codex 不得自行改成 `ready` 或 `true`。
- `make data-football-data-packet-file-readiness-review READINESS_CHECKLIST=<local md> AUTH_FORM=<local md> SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只做 readiness checklist consolidation；不得创建目录、不得写 packet 文件、不得写 DB、不得执行 `pg_dump` / `pg_restore`。
- `data-football-data-packet-file-readiness-review` 不得把 `readiness_status` 改成 `ready`、不得把 `authorization_status` 改成 `authorized_for_packet_file_creation`、不得把 `final_packet_creation_confirmation` 改成 `true`。
- `make data-football-data-packet-file-readiness-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_READINESS=1` 也不得创建目录、不写 packet 文件、不写 packet manifest、不执行 `pg_dump` / `pg_restore`、不写 DB、不触网。
- readiness checklist 不等于 packet file creation authorization；packet file creation authorization 不等于 DB write authorization。
- 真实 packet 文件创建必须单独阶段、用户明确授权、真实 auth form、显式路径。
- Phase 4.74C 的 `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_PACKET_DRAFT_TEMPLATE.md` 是未来提交给人类审核的 packet file creation authorization packet 草案模板，不是授权，不是 packet 文件。
- Phase 4.74C 的 draft template 默认 `draft_status=draft_only`、默认 `ready_for_packet_file_creation=false`、默认 `authorized_for_packet_file_creation=false`；Codex 不得自行改成 `approved` 或 `true`。
- `make data-football-data-packet-file-auth-packet-draft DRAFT_TEMPLATE=<local md> READINESS_CHECKLIST=<local md> AUTH_FORM=<local md> SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只生成 authorization packet draft review；不得创建目录、不得写 packet 文件、不得写 DB、不得执行 `pg_dump` / `pg_restore`。
- `data-football-data-packet-file-auth-packet-draft` 不得把 `draft_status` 改成 `approved`、不得把 `readiness_status` 改成 `ready`、不得把 `authorization_status` 改成 `authorized_for_packet_file_creation`、不得把 `final_packet_creation_confirmation` 改成 `true`。
- `make data-football-data-packet-file-auth-packet-draft-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_PACKET_DRAFT=1` 也不得创建目录、不写 packet 文件、不写 DB、不执行 `pg_dump` / `pg_restore`。
- authorization packet draft 不等于 packet file creation authorization；packet file creation authorization 不等于 DB write authorization。
- Phase 4.75C 的 `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_CREATION_AUTH_REVIEW_CONSOLIDATION_TEMPLATE.md` 是对 Phase 4.74C auth packet draft 的 review consolidation 模板，不是授权，不是 packet 文件。
- Phase 4.75C 的 consolidation template 默认 `consolidation_status=draft_review_only`、默认 `draft_status=draft_only`、默认 `ready_for_packet_file_creation=false`；Codex 不得自行改成 `approved` 或 `true`。
- `make data-football-data-packet-file-auth-review-consolidation CONSOLIDATION_TEMPLATE=<local md> DRAFT_TEMPLATE=<local md> READINESS_CHECKLIST=<local md> AUTH_FORM=<local md> SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只生成 authorization packet review consolidation；不得创建目录、不得写 packet 文件、不得写 DB、不得执行 `pg_dump` / `pg_restore`。
- `data-football-data-packet-file-auth-review-consolidation` 不得把 `consolidation_status` 改成 `approved`、不得把 `draft_status` 改成 `approved`、不得把 `readiness_status` 改成 `ready`、不得把 `authorization_status` 改成 `authorized_for_packet_file_creation`、不得把 `final_packet_creation_confirmation` 改成 `true`。
- `make data-football-data-packet-file-auth-review-consolidation-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_AUTH_REVIEW_CONSOLIDATION=1` 也不得创建目录、不写 packet 文件、不写 DB、不执行 `pg_dump` / `pg_restore`。
- Phase 4.76C 的 `docs/runbooks/FOOTBALL_DATA_PACKET_FILE_PREAUTHORIZATION_CLOSURE_TEMPLATE.md` 是 packet file creation pre-authorization closure 模板，不是授权，不是 packet 文件，不是 packet manifest。
- `make data-football-data-packet-file-preauth-closure CLOSURE_TEMPLATE=<local md> CONSOLIDATION_TEMPLATE=<local md> DRAFT_TEMPLATE=<local md> READINESS_CHECKLIST=<local md> AUTH_FORM=<local md> SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv> APPROVAL_FORM=<local md> RUNBOOK_TEMPLATE=<local md>` 只生成 pre-authorization closure review；不得创建目录、不得写 packet 文件、不得写 packet manifest、不得写 DB、不得执行 `pg_dump` / `pg_restore`。
- `data-football-data-packet-file-preauth-closure` 不得把 `closure_status` 改成 `approved`、不得把 `consolidation_status` 改成 `approved`、不得把 `draft_status` 改成 `approved`、不得把 `readiness_status` 改成 `ready`、不得把 `authorization_status` 改成 `authorized_for_packet_file_creation`、不得把 `final_packet_creation_confirmation` 改成 `true`。
- `make data-football-data-packet-file-preauth-closure-commit` 当前 blocked / not wired，即使带 `CONFIRM_FOOTBALL_DATA_PACKET_FILE_PREAUTH_CLOSURE=1` 也不得创建目录、不写 packet 文件、不写 packet manifest、不写 DB、不执行 `pg_dump` / `pg_restore`。
- pre-authorization closure 不等于 packet file creation authorization；packet file creation authorization 不等于 DB write authorization。
- 真实 packet 文件创建必须单独阶段、用户明确授权、真实 auth form、显式 packet output directory、显式 packet file path 和显式 packet manifest path。
- 真实 packet 文件创建、真实 `pg_dump` 和真实 DB write 必须分别在单独阶段进行，并需要用户明确授权。
- Phase 4.66C 的 `make data-football-data-insert-policy-precheck SOURCE_MANIFEST=<local json> LOCAL_CSV=<local csv>` 是 deterministic match_id + insert candidate policy preview；只能读取本地 manifest / CSV，并对 DB 执行 SELECT-only schema / duplicate 查询。
- `data-football-data-insert-policy-precheck` 不得写 DB、不得执行 `pg_dump`、不得写文件、不得触网、不得 import legacy downloader runtime；`make data-football-data-insert-policy-commit` 当前 blocked / not wired。
- future real DB write 必须单独阶段、单独授权、真实 `pg_dump`、非空备份验证、small batch transaction、post-write validation；restore 也必须单独授权，不得自动执行；DB write 前后 training / prediction 仍必须走单独 gate。
- 未来 football-data network dry-run 仍需单独授权；未来任何 DB write 仍需单独授权并先完成 `pg_dump`。
- 未来 local CSV adapter 必须由 source manifest + 本地 CSV 驱动，不得下载 Football-Data CSV，不得写 staging / DB，不得训练或预测。
- 任何 DB write 必须另行授权并先完成 `pg_dump`；不得把 legacy downloader 直接接到 training / prediction。

Phase 4.58C titan discovery rules：

- `titan_discovery` 属于 `adapter_candidate`，不是 Codex 可直接执行入口。
- Codex 不得直接运行 `node scripts/ops/titan_discovery.js`，也不得运行 `node scripts/ops/titan_discovery.js --dry-run`。
- 当前 `titan_discovery` dry-run trust 不足，不能被当作安全 dry-run 使用。
- 未来如要使用 titan discovery 能力，必须先抽取成 Layer 2 discovery-only adapter，并先具备本地 `source manifest`、单场或极小 date window 限制、以及人工确认的 license / terms。
- 任何 titan discovery network dry-run 都必须单独授权；不得把 legacy discovery runtime 直接接到 DB / staging / training。
- 当前只允许通过 acquisition registry / gate 检查 `titan_discovery` 的 readiness，不允许直接复用其 legacy runtime。

Phase 4.59C odds harvest rules：

- `odds_harvest_pipeline` 属于 `adapter_candidate`，不是 Codex 可直接执行入口。
- Codex 不得直接运行 `node scripts/ops/odds_harvest_pipeline.js`、`npm run odds:harvest` 或任何 odds harvest / bulk odds pipeline。
- 当前 `odds_harvest_pipeline` dry-run trust 不足，不能被当作安全 dry-run 使用。
- 未来如要使用 odds harvest 能力，必须先抽取成 single-target odds acquisition adapter，并先具备本地 `source manifest`、单场或极小 date window、以及人工确认的 license / terms / ToS。
- 任何 odds network dry-run 都必须单独授权；不得绕过 login / paywall / anti-bot / rate limit；不得把 legacy odds runtime 直接接到 DB / training。
- 赔率必须带 `captured_at`、`bookmaker`、`market`、`source_url` 和 provenance；closing odds / post-match odds 不能冒充赛前赔率。
- 当前只允许通过 acquisition registry / gate 检查 `odds_harvest_pipeline` 的 readiness，不允许直接复用其 legacy runtime。

执行 `make data-finished-backfill-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 入口只做 SELECT-only DB 审计和本地 fixture 只读检查
- 不写 DB
- 不执行 raw ingest
- 不写 `l3_features`
- 不写 `match_features_training`
- 不写 `predictions`
- 不训练模型
- 不执行预测
- 不加载模型 artifact
- 不访问外网
- 不导出数据集或大文件

Phase 4.40 中 `make data-finished-backfill-commit`、`make data-finished-backfill-commit CONFIRM_FINISHED_BACKFILL=1` 和 `node scripts/ops/finished_match_backfill_preflight.js --commit` 仍是 blocked / not wired。finished match backfill 必须按 `raw_match_data -> l3_features -> match_features_training -> predictions` 顺序推进；没有匹配 raw fixture 时不得伪造 `raw_match_data`；不得把相似 fixture 冒充目标比赛；scheduled / baseline sample 不可混入真实训练；任何真实 write 前必须单独授权并完成 pg_dump。相关背景见：`docs/_reports/FINISHED_CSV_SINGLE_MATCH_INSERT_PHASE4_39.md`、`docs/_reports/FINISHED_CSV_DRY_RUN_GATE_PHASE4_38.md` 和 `docs/_reports/DATASET_STATUS_AUDIT_GATE_PHASE4_36.md`

执行 `make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<local json>` 的前提：

- 用户明确授权
- 入口只做 SELECT-only DB 审计和本地 JSON 只读检查
- 不写 DB
- 不创建 fixture 文件
- 不执行 raw ingest
- 不写 `l3_features`
- 不写 `match_features_training`
- 不写 `predictions`
- 不训练模型
- 不执行预测
- 不加载模型 artifact
- 不访问外网

Phase 4.41 中 `make data-raw-fixture-commit`、`make data-raw-fixture-commit CONFIRM_RAW_FIXTURE_COMMIT=1`、`node scripts/ops/raw_fixture_adapter_dry_run.js --commit` 和 `node scripts/ops/raw_match_data_local_ingest.js --commit` 仍是 blocked / not wired。raw fixture 必须与目标 `match_id`、teams、score、status 匹配；不匹配 fixture 不能冒充目标 match；synthetic fixture 只能用于 engineering test，不能用于真实训练；synthetic raw_data 不能标记为真实 external / FotMob data；任何 `raw_match_data` 写入前必须单独授权并完成 pg_dump。相关背景见：`docs/_reports/FINISHED_MATCH_BACKFILL_PREFLIGHT_PHASE4_40.md`、`docs/_reports/FINISHED_CSV_SINGLE_MATCH_INSERT_PHASE4_39.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

AI / Codex 仅在用户明确授权时允许创建 synthetic raw fixture，且必须满足：

- fixture 路径位于 `tests/fixtures/synthetic/`
- 明确标记 `synthetic=true`
- 明确标记 `engineering_test_only=true`
- 明确标记 `not_real_external_data=true`
- 明确标记 `not_for_training=true`
- 明确标记 `not_for_production=true`
- 只用于工程链路测试
- 不写 DB
- 不用于真实训练

AI / Codex 禁止：

- 把 synthetic fixture 标记为真实 external / FotMob / OddsPortal 数据
- 用 synthetic fixture 训练模型
- 用 synthetic fixture 写 production data
- 在未授权时写 `raw_match_data`
- 用不匹配 fixture 冒充目标比赛

执行 `make data-synthetic-l3-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 入口只做 SELECT-only DB 审计
- 输入 `raw_match_data` 必须明确标记 `synthetic=true`
- 输入 `raw_match_data` 必须明确标记 `engineering_test_only=true`
- 不写 DB
- 不写 `l3_features`
- 不写 `match_features_training`
- 不写 `predictions`
- 不调用 `smelt`
- 不调用 `l3:stitch`
- 不触发 ELO 重算
- 不训练模型
- 不执行预测
- 不加载模型 artifact
- 不访问外网

AI / Codex 禁止执行：

- `make data-synthetic-l3-commit`
- `make data-synthetic-l3-commit CONFIRM_SYNTHETIC_L3=1`
- `node scripts/ops/synthetic_l3_preflight.js --commit`
- `npm run smelt`
- `npm run l3:stitch`
- `node scripts/ops/l3_features_local_write_gate.js --commit`

synthetic raw 生成的 L3 preview 只能用于工程验证，不可用于真实训练，不可进入 production，也不能被当作真实特征。任何真实 `l3_features` 写入前必须有单独授权、pg_dump 备份和写入前后统计。相关背景见：`docs/_reports/SYNTHETIC_RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_43.md`、`docs/_reports/SYNTHETIC_RAW_FIXTURE_PHASE4_42.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

执行 `make data-synthetic-training-feature-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 入口只做 SELECT-only DB 审计
- 输入 `l3_features` 必须明确标记 `synthetic=true`
- 输入 `l3_features` 必须明确标记 `engineering_test_only=true`
- 输入 `l3_features` 必须明确标记 `not_for_training=true`
- 不写 DB
- 不写 `match_features_training`
- 不写 `predictions`
- 不训练模型
- 不执行预测
- 不加载模型 artifact
- 不访问外网

AI / Codex 禁止执行：

- `make data-synthetic-training-feature-commit`
- `make data-synthetic-training-feature-commit CONFIRM_SYNTHETIC_TRAINING_FEATURE=1`
- `node scripts/ops/synthetic_training_feature_preflight.js --commit`
- `node scripts/ops/match_features_training_local_write_gate.js --commit`
- `npm run train`
- `npm run predict`

synthetic training feature preview 只能用于工程验证，不可用于真实训练，不可进入 production，也不能被当作真实训练数据。任何真实 `match_features_training` 写入前必须有单独授权、pg_dump 备份和写入前后统计。相关背景见：`docs/_reports/SYNTHETIC_L3_FEATURES_SINGLE_INSERT_PHASE4_45.md`、`docs/_reports/SYNTHETIC_L3_PREFLIGHT_PHASE4_44.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

执行 `make data-synthetic-prediction-dry-run MATCH_ID=<id>` 的前提：

- 用户明确授权
- 只读 DB
- 输入 `match_features_training` 必须明确标记 `synthetic=true`、`engineering_test_only=true`、`not_for_training=true`
- 不写 DB
- 不写 `predictions`
- 不训练模型
- 不执行真实预测
- 不加载 model artifact
- 不访问外网

AI / Codex 禁止执行：

- `make data-synthetic-prediction-commit`
- `make data-synthetic-prediction-commit CONFIRM_SYNTHETIC_PREDICTION=1`
- `node scripts/ops/synthetic_prediction_preflight.js --commit`
- `node scripts/ops/prediction_local_write_gate.js --commit`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- `npm run train`

synthetic prediction preview 只能用于工程验证，不是真实模型输出，不可进入 production，也不能被当作真实预测。真实 `predictions` 写入前必须有单独授权、pg_dump 备份和写入前后统计。相关背景见：`docs/_reports/SYNTHETIC_TRAINING_FEATURE_SINGLE_INSERT_PHASE4_47.md`、`docs/_reports/SYNTHETIC_TRAINING_FEATURE_PREFLIGHT_PHASE4_46.md` 和 `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

执行 `make data-l3-write-dry-run` 的前提：

- 用户明确授权
- fixture 是本地文件
- 不写 DB
- 不访问外网

Phase 4.26 中 `make data-l3-write-commit` 和 `node scripts/ops/l3_features_local_write_gate.js --commit` 仍是 blocked / not wired。禁止直接或间接执行 `npm run smelt`、`npm run l3:stitch`、`scripts/ops/smelt_all.js`、`scripts/ops/l3_stitch_pipeline.js`、`scripts/ops/l3_stitch_worker.js`、`npm run elo:recalc` 来替代该门禁。相关背景见：`docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`、`docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`、`docs/_reports/RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_23.md` 和 `docs/_reports/L3_FEATURES_WRITE_GATE_PREFLIGHT_PHASE4_24.md`

Phase 4.24 中 `make data-l3-commit` 仍是 blocked / not wired。禁止直接或间接执行 `npm run smelt`、`npm run l3:stitch`、`scripts/ops/smelt_all.js`、`scripts/ops/l3_stitch_pipeline.js`、`scripts/ops/l3_stitch_worker.js`、`npm run elo:recalc` 来替代该门禁。相关背景见：`docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`、`docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md` 和 `docs/_reports/RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_23.md`

执行 `make data-raw-dry-run` 的前提：

- 用户明确授权
- fixture 是本地文件
- 不写 DB
- 不访问外网

Phase 4.21 中 `make data-raw-commit` 和 `node scripts/ops/raw_match_data_local_ingest.js --commit` 仍是 blocked / not wired。相关背景见：`docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md` 和 `docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`

`NETWORK_DRY_RUN` 不是安全 dry-run，必须由用户显式授权，并给出 `LIMIT`、`SCOPE`、代理和限速说明。

`DB_WRITE_SMALL` 必须由用户显式授权，命令必须支持并显式使用 `--commit`，同时提供 `LIMIT`、`SCOPE` 和执行前后 DB 统计。

`BULK_HARVEST` 必须有 runbook、备份、监控和停止条件。没有 runbook 时，AI / Codex 不得执行。

### 5.5 DB Schema Migration 安全门禁

DB schema migration 治理以 `make data-schema-*` 为统一入口。执行规范见：

- `docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md`

AI / Codex 默认只能执行：

- `make data-schema-help`
- `make data-schema-status`
- `make data-schema-plan`

AI / Codex 不能执行：

- `make data-schema-migrate`
- any migration apply / migrate up / schema sync
- `ensureBlueprintOnCurrentDatabase`
- cold-start blueprint check
- `alembic upgrade`
- 任何 `CREATE` / `ALTER` / `INSERT` / `UPDATE` / `DELETE` / `DROP` / `TRUNCATE`

Schema migration 必须有人类明确授权。执行前必须有 runbook、DB 备份、应用文件清单、post-apply verification plan 和回滚方案。

Phase 4.9 中 `make data-schema-migrate` 即使提供确认变量也只到安全门禁，不接真实 migration 执行。

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
