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
15. report / manifest 必须最小化；
    大型治理 artifact、完整历史状态复制和无限 phase snapshot 不得默认提交到 `main`。
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
- Phase 5.21L2M 仅允许在明确最终 DB-write confirmation 后，为 remaining 7 个 seeded targets（4830746、4830748、4830750、4830751、4830752、4830753、4830754）插入 exactly seven `fotmob_pageprops_v2` `raw_match_data` rows；必须逐场串行 recapture 并用 Phase 5.21L2L `stable_pageprops_payload_v1` baseline 精确 hash gate，任何 hash drift / fetch failure / v2 already exists / guard failure 都阻断 whole write。不得 partial write，除非未来另行授权 reduced target set；不得 rewrite `4830747`、不得 rewrite v1、不得 parser/features/training。写后下一步是 all-seeded canonical read verification。
- Phase 5.21L2N 是 all-seeded pageProps v2 canonical read verification：只能 SELECT-only、不触 FotMob、不写 DB；Phase 5.21L2M 后 8 个 seeded matches（4830746、4830747、4830748、4830750、4830751、4830752、4830753、4830754）都应通过 `RawMatchDataVersionSelector` canonical 选择 `fotmob_pageprops_v2`，且 selected hash 必须与授权 baseline 一致。`PHASE4.43_SYNTHETIC`、`PHASE4.23` 与 unknown 仍默认排除，不得 accidental canonical select。不得直接进入 parser/features/training；下一步应先做本地 pageProps v2 raw inventory / completeness audit。
- Phase 5.21L2O 是 pageProps v2 raw inventory / completeness audit：只能 SELECT-only，只读本地 `raw_match_data` 中 8 条 seeded `fotmob_pageprops_v2`，不得触 FotMob/network、不得写 DB、不得保存或打印完整 `raw_data`/完整 `pageProps`。本阶段只允许做路径盘点、模块覆盖、可疑载荷和完整性 assessment；不得实现 parser/features/training。下一步应是 parser planning，不是 parser implementation。
- Phase 5.21L2P 是 pageProps v2 parser boundary / leakage-safe planning：只能 planning-only，不得实现 parser、不得抽 features、不得写 `l3_features` / `match_features_training` / `predictions`、不得训练/预测、不得触 FotMob/network、不得写 DB。当前 8 条 seeded `fotmob_pageprops_v2` 仅是 raw pipeline / 结构 / parser design sampling，不构成训练数据集。
- Phase 5.21L2P 起，parser implementation 必须等待 parser boundary / leakage policy review；features/training 必须等待 large-scale raw acquisition plan 和 `prediction_cutoff_time` policy 明确。odds raw 必须视为独立 market-pricing source，允许尽早做 raw history planning，但 odds features 在 cutoff-time policy 明确前保持 blocked；未经未来明确授权，不得运行 `odds_harvest_pipeline` 或任何 odds write path。
- Phase 5.21L2Q 是 large-scale pageProps v2 acquisition strategy planning-only：它只能规划 future target inventory / preflight / controlled write / canonical verification / completeness audit 生命周期，不得触 FotMob/network、不得执行 raw acquisition、不得写 DB、不得实现 parser/features/training/prediction。低级别/冷门联赛必须先做 coverage profile，不能把 seeded Ligue 1 高覆盖样本泛化到所有联赛；future odds alignment 应保留稳定 `match_id` / `kickoff_time`，但 odds ingestion 仍保持独立路线。
- Phase 5.21L2R 是 large-scale acquisition target inventory / schema-readiness planning-only：只能审计 `matches` / `raw_match_data` schema 是否足以支撑 future acquisition inventory，规划 future candidate manifest / dedicated acquisition_targets 表示方式；不得执行 schema migration、不得创建 `acquisition_targets` 表、不得写 DB、不得触 FotMob/network、不得执行 raw acquisition、不得实现 parser/features/training/prediction。future acquisition 不得把 `matches` 当作 uncontrolled workflow queue；target state 应先保存在 docs/source-controlled manifest，后续如需落库必须先完成独立 migration planning/preflight。odds alignment readiness 仅表示保留 `match_id` / `kickoff_time` / identity metadata，不表示存储任何赔率值。
- Phase 5.21L2S 是 single-league small-batch docs/source-controlled manifest planning-only：不得触 FotMob/network、不得执行 raw acquisition、不得写 DB、不得执行 schema migration、不得创建 `acquisition_targets` 表、不得 invent FotMob `external_id` / `match_id` / teams / kickoff_time。若本地 DB 不足 20-50 个真实 candidates，manifest 必须标记 `blocked_pending_authorized_target_discovery`；已完成 v2 seeded targets 必须从新 acquisition batch 中排除。future target discovery 必须单独明确 network authorization；parser/features/training 继续 blocked。
- Phase 5.21L2T0 仅允许在明确授权后对 FotMob Ligue 1 2025/2026 执行 controlled source inventory network discovery：只可发现/验证真实 candidate `external_id` 并更新 `docs/_manifests` proposal；不得抓 match detail pageProps、不得写 DB / `raw_match_data` / `matches`、不得 browser/proxy/captcha bypass、不得 retry、不得 invent target IDs。任何 raw write 前必须先进入 Phase 5.21L2T no-write pageProps v2 preflight；parser/features/training 继续 blocked。
- Phase 5.21L2T0B 是 existing L1 schedule discovery capability audit / consolidation：只能做本地代码考古、报告和 fake-fetch/unit-test adapter 整合；不得触 FotMob/network、不得 retry T0 失败请求、不得写 DB/raw/matches，不得启动 browser/proxy。若继续 source inventory，必须优先复用 `DiscoveryParser`、`L1ConfigManager`、`SeasonStrategyFactory` 等既有 L1 能力或薄 adapter，不得重复从零开发 endpoint/parser。
- Phase 5.21L2T 仅允许在明确授权后，对 manifest 中 50 个 Ligue 1 candidate targets 执行 controlled match detail pageProps v2 no-write preflight：可串行触 FotMob match detail 以计算 `stable_pageprops_payload_v1` baseline hash 并更新 source-controlled manifest/report；不得写 DB、不得写 `raw_match_data`、不得 controlled write、不得 schema migration、不得 parser/features/training、不得 browser/proxy/captcha bypass、不得保存或打印完整 body/pageProps。manifest baseline hashes 是后续 controlled write authorization 的前置条件。
- Phase 5.21L2U 是 controlled pageProps v2 write authorization / planning-only：只能读取 manifest baseline hashes 并做 SELECT-only write eligibility audit，不得执行 DB write、不得写 `raw_match_data`、不得触 FotMob/network、不得抓 match detail、不得 controlled write、不得 schema migration、不得 parser/features/training。它只准备 Phase 5.21L2V；L2V 必须单独取得 final DB-write authorization，并用 manifest `baseline_hash` 做 hash gate。
- Phase 5.21L2V 是 controlled `raw_match_data` pageProps v2 write execution：必须要求 `FINAL_DB_WRITE_CONFIRMATION=yes`，并在任何 network/write 前先通过 schema、existing-row 和 FK/matches existence gate；若 candidate `match_id` 缺少 `matches` row，必须在触网/写库前停止。L2V 只能在所有 manifest baseline hash 与 live recapture `stable_pageprops_payload_v1` 精确匹配后写 `raw_match_data`，不得写 `matches`、odds、features、training、predictions，不得 parser/features/training，不得 browser/proxy/captcha bypass，不得保存或打印完整 body/pageProps。
- Phase 5.21L2V0 是 matches identity prerequisite planning-only：只能 SELECT-only 审计 manifest 中 50 个 candidate 是否足以未来 seed `matches`，不得执行 DB write、不得写 `matches`、不得写 `raw_match_data`、不得触 FotMob/network、不得 parser/features/training。它只准备 L2V1；L2V1 需要单独 final DB-write authorization。pageProps raw write retry 必须先有 `matches` rows，并再次取得独立授权。
- Phase 5.21L2V1 是 controlled matches identity seed execution：必须要求 `FINAL_DB_WRITE_CONFIRMATION=yes`，且只允许写 `matches`；不得写 `raw_match_data`、odds、features、training、predictions，不得触 FotMob/network，不得 parser/features/training。写后必须验证 `matches` 10 -> 60 且 `raw_match_data` 仍为 18；后续 raw write retry 仍需单独 renewed authorization。
- Phase 5.21L2V2 是 post-seed matches identity verification / raw write retry readiness audit：只能 SELECT-only 验证 50 条 `matches` row、FK prerequisite、无现存 candidate v2 raw row 和 manifest baseline readiness；不得写 DB、不得触 FotMob/network、不得 retry raw write、不得 parser/features/training。若 audit ready，Phase 5.21L2V3 raw write retry 仍需单独 renewed final DB-write authorization。
- Phase 5.21L2V3 是 renewed controlled pageProps v2 raw write execution：只有明确 renewed final DB-write authorization 后才可串行 recapture manifest 中 50 个候选并在 `stable_pageprops_payload_v1` hash 全部匹配时单事务写 `raw_match_data` 50 行；不得写 `matches`、odds、features、training、predictions，不得 schema migration，不得 parser/features/training，不得 browser/proxy/captcha bypass，不得保存或打印完整 body/pageProps。成功后应验证 `raw_match_data` 18 -> 68 且非 raw 表不变，下一步是 post-write canonical/read completeness audit。
- Phase 5.21L2V3C 是 renewed baseline regeneration planning / no-write manifest proposal：只能做只读检查、no-write recapture sample、hash drift 分类和 proposal/report/manifest planning metadata；不得写 DB、不得插入 `raw_match_data`、不得把新 hash 标记为 accepted baseline、不得让 raw write 自动使用 proposal hash，后续仍需单独 baseline acceptance 与 renewed final DB-write authorization。
- 以下 engine core 不是 deprecated，也不得误删：`DiscoveryService`、`DiscoveryParser`、`DiscoveryAttributeMapper`、`DiscoveryDataValidator`、`L1ConfigManager`、`HttpClient`、`FotMobExtractor`、`BrowserProvider`、`FixtureRepository`。
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
- `docs/_reports` 与 `docs/_manifests` 只记录必要 delta 和当前有效状态；不得替代 runtime 实现。
- PR reviewer 必须能从模板中直接判断：PR type、runtime code paths、artifact 体积、business progress、blocker 变化和安全边界。
- Data ingestion PR 必须满足 `docs/INGESTION_CONVERGENCE_GATE.md` 的 outcome gate：
  声明 blocker transition、`target_state_delta`、bounded review 范围和 no-progress stop 条件。

### 2.5 Repository Hygiene / Technical Debt Guardrails

每个新增文件必须声明 lifecycle：`permanent` / `current-state` / `phase-artifact` / `temporary` / `one-shot-helper` / `test-fixture` / `archive-candidate` / `delete-after-use`。无 lifecycle 声明的新文件不得合并。

Phase artifact limits：report <= 120 行（除非明确说明原因）；manifest 只保留机器需要的最小字段；不得复制完整历史；不得保存 full HTML / pageProps / raw_data / source body。

每个新增 helper/script 必须说明是否长期保留、是否被 Makefile/npm script/CI 引用、cleanup 条件。若 helper 只服务一次，默认成为 cleanup candidate。

测试必须优先验证 runtime behavior。只验证 report wording / manifest metadata 的测试不得替代 behavior coverage。

应维护 current-state 入口；历史 ADG report 不能替代 current truth。

每 3-5 个 data/ingestion PR 后必须考虑是否需要 hygiene PR。

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

### 5.1 七个领域摘要

| Domain | Canonical status | Primary entrypoint |
|---|---|---|
| Data collection | Controlled surface | `data-l1-*` / `data-l2-*` Makefile targets |
| Odds | Primary canonical | `npm run odds:harvest` |
| FotMob | Not yet established | Controlled preview/gated `data-*` workflows only |
| Feature build | Primary canonical | `npm run l3:stitch` |
| Training | Primary canonical | `npm run train` |
| Prediction | Primary canonical | `npm run predict` |
| Backtest | Not yet established | None — future business milestone |

### 5.2 分类规则

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
