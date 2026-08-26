# Project Status

- lifecycle: current-state
- owner: project governance

Last updated: 2026-08-25

## Current State

本节是当前状态摘要；下方的 M3、VALUE_MVP-1、SC-002 和 FotMob 长篇段落是
supporting history / completed evidence，保留用于追溯，不再把旧阶段标题当作
当前战线。当前主线事实已按 `origin/main` 与 canonical code/config 独立核对。
`docs/PROJECT_VISION.md` 只描述最终 target system；本文件只报告当前事实、evidence、blockers
和 supporting history，不把 vision gap 当成已实现能力。
表中的 `Last knowledge audit base` 是 documented business snapshot 的审计基线，
不是实时 main HEAD。实时 `CURRENT_GIT_HEAD`、`CURRENT_ORIGIN_MAIN` 和 `GITHUB_MAIN`
必须从 Git/GitHub 获取。

| Field | Current truth |
|---|---|
| Last knowledge audit base | `b0995c36fcd2f84cc6f1034450881d6f15103e68`（只表示 documented audit snapshot，不是实时 main HEAD） |
| Current system stage | `CANONICAL_OFFLINE_MODEL_EVALUATION_COMPLETE`；pre-production research evidence |
| Completed canonical pipeline | GD-A01 → GD-A02 → GD-A03 → Canonical Prematch Feature Frame → Training Candidate Production → Offline Evaluation |
| Current model asset | `canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41`; `xgboost_multiclass_1x2`; `canonical_prematch/vnext-v1`; 9 accepted-for-training features |
| Population / split | 888 accounted; 545 eligible; 343 ineligible; 436 training; 109 reserved evaluation |
| Predictive evidence | log loss `0.97834` vs prior `1.05654`; Brier `0.58456` vs prior `0.63590`; accuracy `55.96%` vs majority `48.62%`; `MODEL_OFFLINE_QUALITY_STATUS=PROMISING` |
| Holdout | `CONSUMED_FOR_OFFLINE_EVALUATION`（109 outcomes，不再是 untouched/unopened） |
| Market / odds evidence | historical odds staging + provider-defined closing semantics；VALUE_MVP-1 = `MARKET_BETTER_THAN_MODEL`（另一历史研究路径） |
| Hard blockers | strict decision-time odds timeline；canonical value engine；canonical betting backtest；bankroll/staking；CLV；fresh independent future holdout；production activation |
| Non-capabilities | `MODEL_QUALITY_PROVEN=NO`; `PROFITABILITY_PROVEN=NO`; `PRODUCTION_READY=NO`; `MODEL_ACTIVATED=NO`; `BACKTEST=NOT_ESTABLISHED` |
| Next Owner decision | 明确授权下一项证据任务：优先 fresh independent future holdout，或另行设计 strict decision-time market evidence；不自动开始、不混合 VALUE_MVP-1 与 canonical candidate |

当前模型与市场证据的细节见 `docs/CAPABILITY_INDEX.md`、
`docs/ACTIVE_MILESTONE.md`、`docs/CANONICAL_OFFLINE_MODEL_EVALUATION.md`、
`docs/MODEL_ARTIFACTS.md` 和 `docs/data/FOTMOB_CURRENT_STATE.md`。代码合同与
GitHub/Actions 状态仍以机器事实为准；本摘要不授权训练、预测、回测、写入或激活。

### Security / maintenance current state — `claude_reader` ACL retirement

本节是 security / maintenance current-state，不加入上表的业务 Hard blockers，也不改变
`docs/ACTIVE_MILESTONE.md` 中的 value-betting 业务战线或下一项业务证据决策。

| Field | Current truth |
|---|---|
| Direct-login retirement | `LOGIN_RETIREMENT_STATE=DONE`；existing live PostgreSQL role `claude_reader` 的 last-audited 状态为 `NOLOGIN`；本次没有重新连接或查询 live DB |
| ACL retirement review | `COMPLETE`；decision-support evidence 见 [`docs/SC002_CLAUDE_READER_ACL_RETIREMENT_REVIEW.md`](SC002_CLAUDE_READER_ACL_RETIREMENT_REVIEW.md)，该 audit artifact 的 authority 仍为 `NONE` |
| Future provisioning retirement | `FUTURE_PROVISIONING_RETIREMENT_STATE=DONE`；`CURRENT_FUTURE_PROVISIONING_STATE=RETIRED`；repository fresh bootstrap 不再创建 `claude_reader` 或授予其 direct/default ACL；fresh-only entrypoint guard 会在 official initdb 前拒绝解析为该退休身份的旧 `DB_USER`；`FRESH_PROVISIONING_RECREATES_ROLE_ACL_DEFAULT_ACL=NO`；`PROVISIONING_BLOCKER_REMAINS=NO` |
| Login identity distinction | `REPLACEMENT_POSTGRES_LOGIN_IDENTITY_CREATED=NO`；pre-existing dev-only `football_reader` LOGIN POC role 仍由 `init_db.sql` provision，早于本次 retirement，未被本次创建、重命名或指定为 replacement；`CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT` |
| Consumer visibility | `PROCESS_ENV_COVERAGE_COMPLETE=NO`；`KNOWN_PROCESS_CONSUMER_STATE=UNKNOWN_INCOMPLETE_ENVIRONMENT_VISIBILITY`；`LOCAL_DEVELOPMENT_HOST_CONSUMER_STATE=UNKNOWN_DUE_TO_INCOMPLETE_PROCESS_ENVIRONMENT_VISIBILITY`；`HOST_COVERAGE_COMPLETE=NO` |
| External consumer boundary | `EXTERNAL_HOST_CONSUMER_STATE=UNKNOWN`；`EXTERNAL_CONSUMER_BLOCKER_CLEARED=NO`；没有把 incomplete host/process visibility 升级为 absence |
| Existing live DB ACL | `LIVE_DATABASE_ACL_RETIREMENT_STATE=BLOCKED`；last-audited 54 direct privileges、3 default ACL privileges、40 dependencies 保持未动 |
| Role drop | `ROLE_DROP_STATE=BLOCKED`；`CLAUDE_READER_FULL_RETIREMENT=NOT_DONE` |
| Accepted Layer-2 risk | `UNKNOWN_STALE_FRESH_BOOTSTRAP_COMPATIBILITY_RISK`；未知外部环境若在未来 fresh bootstrap 仍依赖旧 repository provisioning，可能出现兼容性失败；这不是 live DB mutation risk |
| Owner decision gate | Layer 2 已获 Owner 授权并落实到 repository contract；任何 live ACL/default ACL retirement 或 role drop 都必须另行举证并单独授权 |
| Prohibited automatic actions | 不得自动 `REVOKE`、`ALTER DEFAULT PRIVILEGES`、`DROP ROLE`、恢复 `LOGIN`、创建替代 login identity 或 credential |

上述结论是当前安全维护边界。Future provisioning retirement 不会自动改变 existing live
database，也不代表 retained ACL 是 active direct-login vulnerability 或 full role retirement
已完成。详细 catalog ledger、证据标签和 future plan 只保留在
linked audit evidence 中；本 current-state backflow 不复制其完整审计账本。

## Historical evidence / completed history

以下长篇段落保留历史证据、完成记录和 supporting history。它们不能覆盖上面的
Current State，也不能作为新的 workflow authority。

## M3 Historical Odds Staging — D4E controlled persistent write complete

- **M3-D4B** — historical odds staging persistence contract on the M3 identity baseline.
  - M3 deterministic Football-Data match identity is complete (#1797); the frozen business contract remains
    **38,616 accepted / 216 quarantined** observations.
  - Added the additive `V26.8__create_odds_historical_staging_contract.sql` schema contract and explicit
    dependency-injected persistence port for import run, source-file lineage, accepted observations, and quarantine.
  - `V26.8` was executed only in a task-specific PostgreSQL 15 tmpfs container and was destroyed with that container;
    no long-lived database was connected or migrated. D4C added additive `V26.9` so canonical business fingerprints are
    retained for duplicate comparison; it too was executed only in that disposable database.
  - Default behavior is fail-closed/no-write; a future adapter must pass the existing DB write guard and explicit
    authorization. Candidate IDs are retained as unverified references: no `matches` FK is claimed until DB inventory.
  - D4C used 3 synthetic accepted observations and 1 synthetic quarantine record to verify schema mapping, atomic
    rollback, database uniqueness/check constraints, idempotent rerun, and quarantine separation. No real historical
    odds were read or written. Candidate ID compatibility with `matches.match_id` remains **not proven**, so no FK was added.
  - `#1799` is merged. **M3-D4C** is complete only for the disposable PostgreSQL 15 tmpfs verification;
    no long-lived database was connected or migrated.
  - **M3-D4D-B1** readiness decision: **`READY_FOR_D4E_AUTHORIZATION`**. The named
    non-production persistent target, canonical V26.8→V26.9 migration runner, verified
    backup/restore, zero-row inventory, rollback-only writer persistence, reader/writer role
    boundaries, PUBLIC/default ACL audit, failed-migration rollback/resume, checksum-drift
    fail-closed, and same-session PostgreSQL advisory-lock concurrency are closed.
    PR #1801 is merged. Policy implementation head
    `e7171da6ac049b0368ed1f5c2171e76a9e447819` passed Production Gate run `30066372663`.
    The reviewed sandbox-only SQL classification is static only and does not authorize execution.
  - M3 milestones #1794–#1801 are merged: offline staging pipeline, CSV recovery, deterministic
    candidate export and identity, D4B persistence contract, D4C ephemeral verification, D4D
    readiness review and D4D-B1 persistent sandbox.
  - **M3-D4E COMPLETE — deterministic synthetic controlled persistent write verified.** M3-D4E is
    implemented and audited through PR #1802; the authoritative PR merge state is recorded in
    GitHub and Issue #1793. Its D4E technical/evidence head
    `b2ba7e44b7dd643ac89bd0cb2704005dbbbfbf41` passed Production Gate `30102747400`.
    First write: 6 accepted / 3 quarantine / 0 duplicates. Stable replay under a newer executor:
    0 accepted / 0 quarantine / 9 duplicates with zero table delta. Accepted and quarantine
    conflicts had actual adapter scopes `accepted` and `quarantine`, respectively, and both fully
    rolled back with zero delta. Final state: 1 import run / 1 source file / 6 accepted / 3 quarantine.
  - `canonical_match_id` remains NULL for all six accepted rows; candidate identity is unverified,
    no matches FK exists, and canonical integration/training remain blocked. Real historical odds
    were not used, and no development, staging or production database was targeted.
  - Post-merge review of #1802 identified three operator/governance P1 hardening requirements:
    dependency-complete operator runtime, exact effective PostgreSQL connection identity, and a
    hash-bound lifecycle declaration for the immutable JSONL fixture. The D4E business proof and
    retained 1 / 1 / 6 / 3 sandbox evidence remain valid; the dedicated hotfix does not connect to
    or modify that sandbox.

**M3-D4F design-review baseline — superseded by
`READY_FOR_CANONICAL_INVENTORY_WRITER_IMPLEMENTATION_REVIEW` below.**
The 2026-07-28 offline cross-source audit retained the prior D4F-A database
fact (`football_prediction_db_dev` / `football_db` has zero relevant Premier
League/E0 `matches` rows) but recovered the existing PR #1796 repository-
external FotMob candidate artifacts instead of using that empty database
inventory as the comparison side. Current exporter validation reconfirmed two
ordinary, non-symlink candidate artifacts at 1,140 candidates each (380 / 380
/ 380), unique FotMob IDs and business hash
`eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f`.
No FotMob/provider request was needed.

The existing `football-data-csv@1.2.0`, `buildSemanticMatchIdentity` and
`matchLinker` contracts recomputed 1,180 raw CSV rows, 38,832 odds
observations and 892 unique source candidates (380 / 380 / 132; source
business hash `07e579ed21224c354c6dbcf9d44913521d94ce6e48ce24c17cbbd9bfd6b98b8b`).
Two independent runs produced the identical cross-source result hash
`fee4d02ae93d2370ba9a282ef546cafa097c8f350a402f19afab39dc2f2040fb`:
888 `exact_unique_match`, 4 isolated `kickoff_conflict` (3 × 15 minutes and
1 × 30 minutes), and zero unmatched, ambiguous, team, competition/season,
incomplete or invalid-source terminals. The 888 exact candidates map to 888
distinct FotMob IDs. Of the 252 FotMob candidates without an exact link, four
are the kickoff conflicts inside this 892-source population and the remaining
248 are outside it; none is multiply used.

The cross-source audit was design-review readiness only. The four kickoff
conflicts remain isolated and cannot be guessed, linked or written. No business
database was read or written by that audit; no schema, canonical linkage, raw
payload, provider/browser request, persistent sandbox, import, migration,
training, backtest or prediction changed. Original upstream
provenance/import semantics remain unverified and Issue #1793 remains Open.

The normal documentation commit hook did perform the separately authorized
Gatekeeper `gatekeeper_cold_start_*` temporary database create/probe/rollback/
drop blueprint. It did not inspect `matches`, modify a business schema or row,
or access the persistent M3 sandbox.

M3-D4F local evidence-backed inventory conclusion:
**`FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED`**.

The repository-approved official Architecture Decision Gate direction is
**`redo source inventory strategy`**. The user-selected implementation approach
for that direction is **`RECOVER_EXISTING_ACQUISITION_ARCHITECTURE`**; the
current evidence-backed technical outcome is
**`FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED`**. This means confirming and
recovering existing providers, retained assets and reusable components—not
redesigning every source from zero.

The user explicitly authorized one local Docker, non-production, read-only
inventory. The only runtime target was the already-running repository-owned
`football_prediction_db_dev` PostgreSQL 15 container and `football_db`.
Connection used the container Unix socket as `claude_reader`, without a
password or TCP; the role has no inherited roles, no superuser/create role/create
database capability, no `public` schema CREATE privilege, and listed project
table grants are SELECT-only. Every query used `BEGIN READ ONLY` with
`transaction_read_only=on`, 10-second statement timeout and bounded output.

The local evidence is substantive but narrow:

- `matches=60`, all with `external_id`; 58 are strong, harvested
  `fotmob_live_fetch` records;
- `raw_match_data=76`, all FK-linked to `matches`, with 60 distinct match IDs,
  zero raw orphans and zero duplicate `(match_id, data_version)` groups;
  `fotmob_live_v1=58`;
- `fotmob_raw_match_payloads=32` retained full raw-payload records. V26.5
  requires complete, unparsed `__NEXT_DATA__` JSON in non-null
  `next_data_json`, with raw-file locators, SHA-256 values, byte sizes, capture
  and ingestion metadata; complete `page_props_json` is retained when present
  but is nullable. Their `match_id` values overlap retained `matches` and
  `raw_match_data` at match level, but do not prove a one-to-one or
  record-level payload-to-raw association, 32/32 parser validation or 32/32
  pageProps presence;
- `bookmaker_odds_history=2`, but both rows link to a synthetic match and a
  `test_sample.html` basename, so football-data.co.uk has no retained real-data
  proof here;
- `odds=0` and `matches_oddsportal_mapping=0`, so OddsPortal has no retained
  execution proof here;
- the four M3 historical staging tables are absent from this development DB.
  The named D4E persistent-sandbox volume remains untouched and has no running
  database container.

The current `fotmob_live_v1=58` count is a retained-row inventory, not a
58/58 parser or full-audit claim. The historical controlled audit established
4/4 parseable, SHA-valid and inner-`matchId`-valid rows only; exact writer/run
provenance for all 58 retained rows is not uniquely attributable. The legacy
`n3_live_fotmob_raw_retain.js` N=3 network/UPSERT path is historical evidence
only, not a canonical writer, recovery contract or future dependency. A future
FotMob writer remains `NOT_YET_ESTABLISHED` and must be created through a
controlled `data-*` milestone with separate network/write authorization.

No network acquisition, browser/proxy runtime, database write, migration, real
historical-odds import, training, backtest or prediction occurred.

```text
target_state_delta:
- total_targets: 50
- moved_to_clean_candidate: 32
- moved_to_rejected_mapping: 0
- moved_to_superseded_mapping: 0
- moved_to_eligible_for_re_acceptance_review: 0
- moved_to_needs_new_evidence: 10
- remain_suspended: 8
- still_blocked_pending_review: 0
- abandon_current_batch_candidate: 0
- no_progress_count: 0
```

This delta counts 50 concrete historical FotMob mapping targets, not database
asset packages or database rows. Exact-ID chronology reconciliation found 32
later ADG59A/ADG59B accepted/resolved clean candidates, ten L2V3BC targets that
still need evidence, and eight L2V3AT mappings/baselines that remain suspended.
The terminal arithmetic is `32 + 10 + 8 = 50`; the retained database assets do
not enter this calculation.

`no_progress_count = 0` is supported by 32 same-identity, source-controlled
target state changes after L2V3BC—not by the local database row count, FK or
hash inventory. The 32 clean candidates are not raw-write authorization and do
not prove M3 compatibility. All 50 are FotMob mapping-governance targets, not
M3 Football-Data candidates; the 18 non-clean targets remain excluded from
future FotMob mapping reuse until separately authorized evidence changes their
state. The formal strategy does not select abandon current batch, rebuild
canonical identity pipeline, switch/compare a provider or redesign FotMob
identity mapping. It does not permit an unbounded legacy pipeline restart or
any write/network exception.

The remaining blockers are the ten exact FotMob targets needing new evidence,
the eight still-suspended mappings/baselines, the four isolated M3 kickoff
conflicts, approved real historical-odds provenance/hash/location, real
football-data and OddsPortal evidence, M3 staging target availability, and
training quality/leakage controls. The zero-row development database remains a
fact but no longer prevents the verified offline candidate-to-candidate audit.
FotMob payload hashes establish integrity only for retained FotMob match-detail
assets. The D4F-A preflight separately reverified repository historical input
objects and SHA-256 values, but neither set of hashes proves original upstream
capture/provider/license semantics or authorizes an import.

Do not start automatically. The bounded canonical-inventory write design review
is complete. Recommended next task only after separate user confirmation is a
canonical inventory writer implementation review: a status-complete v2 input
schema, fail-closed insert-only writer and disposable PostgreSQL proof, while
preserving the 888 exact / 4 kickoff-conflict linkage partition. The 32/10/8
Ligue 1 FotMob mapping states remain independent governance evidence; no
network, database write, migration, canonical-linkage persistence, training or
legacy-writer execution is authorized.

## M3-R1 — Historical odds current-main reproducibility (reproducible rebuild entrypoint)

- **M3-R1 COMPLETE（PR #1829 squash-merged `eb924b59e`，post-merge push Gate `31320043403` success；
  M3_R1_STATUS=COMPLETE；M3_R1_CLOSEOUT_COMPLETE=YES）** —
  current-main historical odds reconstruction made deterministic and reproducible with a committed
  entrypoint `npm run odds:staging:rebuild`（`scripts/ops/odds_staging/historical_odds_rebuild.js` +
  sibling `historical_odds_rebuild_canonical.js`，lifecycle: permanent）。
- **Canonical self-recovering mode（GAP-01）**：`--canonical-history` 不要求任何预准备的 CSV bundle —
  直接从本仓库不可变 Git 对象恢复三个固定来源（CANONICAL_SOURCES 的 commit+path → blob SHA →
  核验 SHA-256/字节数/行数 → 物化到 repo 外确定性 staging 目录 → 构造 manifest → 复用
  runOfflineStaging）。只经有界只读 git 子进程（仅 rev-parse / cat-file blob / show -s；
  shell=false；限时/限量；剥离 GIT_* 环境；GIT_NO_LAZY_FETCH=1 + GIT_ALLOW_PROTOCOL=none；
  绝不接受用户命令）。candidates artifact 绑定到冻结基线（1140 + eff8817284…，fail closed，
  声明数量与数组实际数量必须一致）。
- Reproduces the entire frozen mandate baseline from current main: **38,832 observations total /
  38,616 accepted / 216 quarantined** (144×15m + 72×30m); per-source 13,680/13,572/108,
  12,546/12,510/36, 12,606/12,534/72; **892 unique source candidates** (380/380/132, all
  canonical_match_identity, zero synthetic IDs); linkage **888 exact / 3×15m + 1×30m kickoff
  conflicts / 0 unmatched / 0 ambiguous**; 888 distinct FotMob IDs. Two independent canonical
  rebuilds (BUILD_A / BUILD_B, real data) are **byte-identical**; receipt schema
  m3-historical-odds-rebuild-receipt/v2 records actuals only (no hard-coded baseline constants).
- **Source population business hash（M3-R1 canonical composition）: `40b02195cd5828d43b2be9778aa32b4bb896cf32da4e132386a8e18c8a0d2e06`** —
  sha256 over the documented sorted projection; locale-invariant sort; stable across all refactors.
  The legacy D4F hash `07e579ed…` remains **NOT reproducible** (its composition was never retained in the repo);
  count-level reproducibility is fully verified, hash-level composition is not verifiable from current main.
- **Temporal evaluation readiness: NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION** — every observation is
  snapshot_type `unknown` (38,832/38,832), source_observed_at null, captured_at null, capture_time_status
  `unknown`; plain ≠ opening, C ≠ closing; no opening/current/closing claim anywhere in extraction,
  observation, quarantine or receipt. Coverage audit: 2024/2025 has only 4 of 6 bookmaker families
  (no Interwetten, no VC Bet); 2023/2024 Interwetten sparse (840 observations). Provenance: git blob
  verified per source; acquisition mode declared (`historical_git_recovery`); upstream provider provenance,
  license and capture time unverified/unknown.
- **Machine-readable temporal contract（GAP-03，receipt v2）**：receipt 携带
  `evaluation_readiness { temporal_value_evaluation, reasons, observation_facts }`（facts 从实际发射
  observations 计算：真实数据 38,832 unknown / 0 known）与 `temporal_semantics`（snapshot_type /
  source_observed_at / capture_time 全部 unknown；plain_series_opening_status / c_series_closing_status
  均 not_proven）；`rebuild_status { source_rebuild: SUCCESS, linkage_rebuild: EXECUTED|NOT_EXECUTED }`。
  fail-closed classifier：只有 facts 与语义全部 proven 才可能 READY；手改 READY / 语义 / facts /
  reasons 全部被 --validate 拒绝。
- **Output-aware self-verification（GAP-02，--validate）**：从发射目录重算每个事实 — per-source
  计数、emitted_digest（accepted/quarantine/summary/manifest 四文件字节摘要）、source population
  业务哈希 / identity_mode / per_season、linkage 分类 / distinct ids / conflict samples（code-unit
  排序）、manifest 派生字段（raw_sha256 / raw_size_bytes / repository_provenance）、quarantine
  reasons、temporal semantics 与 readiness（含 reasons）；canonical 模式下还交叉核对 pinned 身份
  （commit/path/blob/SHA-256/字节/行数）并对每个声明对象重新 git 验证。任何手改收据 / 发射文件 /
  变更哈希都会被拒绝（确定性一致性，非密码学真实性）。真实数据验收：BUILD_A/B 字节一致、
  VERIFY_BUILD_A/B PASS、篡改探针（计数 +1 与发射行内容修改）REJECTED —— 证据见
  `acceptance-remediation-20260809T113656Z/`。
- Local validation: 68 regression tests（odds_staging_rebuild.test.js + odds_staging_rebuild_canonical.test.js）；
  Codex focused review 2 rounds（cap）—— round 1：2 P0 + 6 P1 + 3 P2 + 3 P3 全部修复；
  round 2（verification）：2 P1 + 6 P2 全部修复并各自附带回归测试；round-2 修复经
  10 个定向新测试 + 全套 286 回归 + 真实数据验收验证。eslint 8.57.1 `complexity: ["error", 15]`
  全绿（含 positive control）；`git diff --check` clean；本地 gatekeeper commit-mode 门禁通过。
- 未改变：M3_D4F 冻结合同计数不变、no-write 默认不变、无 DB/网络/训练/回测执行、无 migration。
- historical odds → production import integration remains **NOT_ESTABLISHED**（独立授权 + 独立 Gate，见下）。

## M3-R2 — Official provider temporal contract reconciliation (Issue #1793)

- **M3-R2 COMPLETE（PR #1830 squash merge `2532a7b95fb9e52e065619b904a2865dc56649c2`，
  post-merge push Production Gate `31327367581` success（event=push，exact merge commit）；
  M3_R2_STATUS=COMPLETE；M3_R2_CLOSEOUT_COMPLETE=YES）** —
  Football-Data.co.uk 官方 provider 时序语义合同对账（mandate M3-R2，evidence 目录
  `footballprediction-m3-r2-provider-temporal-contract-20260809T162422Z/`）。
- **官方证据（Level A primary provider documentation，2026-08-09 核验，无网络运行时）**：
  downloadm.php / data.php / matches.php / notes.txt —— C 系列 = closing odds（provider 定义的
  closing，非精确收盘 tick）；第一组 = market opening 之后按 fixtures 页时间采集的第一组，
  **provider 从未称其为 opening odds** → 语义 = `first_collection_after_market_open`，
  snapshot_type 保持 unknown（现有 schema 无法准确表达，mandate §22）；无任何 per-row 观察/采集
  时间戳字段 → source_observed_at / captured_at 保持 null，provider 时刻表只是 rule 不是 timestamp。
- **Per-source provenance（3 个来源分别判定，无全局 C 后缀推断）**：raw_odds_2223 / raw_odds_2324 /
  real_odds_raw 全部适用官方合同（applicable_sources 从实际发射的 normalized manifest 重算，非
  硬编码）；真实构建分布 closing 19,395 / first_collection 19,437 / unknown 0（per-source
  6,840/6,840、6,258/6,288、6,297/6,309）。
- **机器可读合同模块**：`src/infrastructure/odds_staging/footballDataProviderContract.js`（lifecycle:
  permanent）冻结 `FOOTBALL_DATA_PROVIDER_CONTRACT`（contract_id
  `football-data-provider-contract/v1`；effective_from_season 2019/20；closing /
  first_collection_after_market_open 双阶段；pinnacle_warning 2025-07-23 起不适用于 canonical
  seasons）。**fail closed**：非官方 contract_id / provider_id、applicable=false、pre-contract
  season、紧凑 '2223' 格式均不 overlay。
- **适配器 1.2.0 → 1.3.0**（football-data-csv）：C 系列 → snapshot_type=closing +
  provider_collection_phase=closing；普通系列 → snapshot_type=unknown +
  provider_collection_phase=first_collection_after_market_open；overlay 仅当 manifest 声明
  applicable:true 且 contract_id/provider_id 与 committed 合同精确匹配且 season ≥ 2019/20。
  idempotency 键分离 provider_collection_phase（Codex F-03）。
- **收据 v2 → v3**（`m3-historical-odds-rebuild-receipt/v3`）：新增
  `provider_semantic_contract`（applicable_sources 来自实际 manifests + 5 个 provenance 字段全部
  pin 到 committed 合同）、`series_semantics_distribution`（纯 facts 投影，重算比对）、7 维
  `evaluation_readiness`。
- **Population 不变量全部保持不变（POPULATION_DRIFT→STOP 未触发）**：observation 38,832 /
  accepted 38,616 / quarantine 216；unique candidates 892（380/380/132）；linkage 888 exact /
  3×15m + 1×30m conflicts / 0 unmatched / 0 ambiguous；candidates artifact 1,140 +
  eff8817284…；业务哈希 **未变**（40b02195cd…；组合只覆盖 match identities，不含时序语义 ——
  HASH_CHANGED=NO 附说明）。
- **Readiness（mandate §24 预期全部命中）**：CLOSING_ODDS_SEMANTICS_READY=YES、
  FIRST_COLLECTION_SEMANTICS_READY=YES、EXACT_OBSERVATION_TIMESTAMP_READY=NO、
  EXACT_CAPTURE_TIMESTAMP_READY=NO、STRICT_DECISION_TIME_VALUE_EVALUATION_READY=NO、
  CLOSING_MARKET_BENCHMARK_SEMANTICS_READY=YES；composite
  NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION（恰好 3 个 reasons：observed_at 缺失、captured_at
  缺失、plain opening 未 proven）。
- **验证**：真实数据 BUILD_A/BUILD_B 字节一致 + 最终代码 `verifyRebuildReceiptAgainstOutput`
  valid=true ×2；6 个 tamper 探针（closing→unknown、first_collection→opening、contract_id、
  readiness 维度、plain opening proven、distribution）全部 REJECTED；收据一致降级（closing
  not_proven + readiness NO）与 provenance 字段手改均 REJECTED（Codex R2 F-01/F-02）。eslint 0
  errors；canonical 单元套件 8,436/8,436 pass（含 M3-R2 新增 18+ 测试）；runtime 无网络回归通过。
  Local Codex review 2 rounds（cap）：round 1 P3×4、round 2 P2×1 + P3×2，全部修复并附回归测试，
  最终 P0/P1/P2=0（P3 记录）。
- **legacy 脚本未改动**：`fetch_and_adapt_euro_leagues.js` 等保持原状；M3-R2 仅在新 canonical
  语义链上叠加合同。
- 未改变：no-write 默认、无 DB/网络/训练/回测执行、无 migration、SC-002 状态不变。

## VALUE_MVP-1 — Offline probability benchmark: prematch baseline vs closing 1X2 market

- **VALUE_MVP_1_STATUS=IMPLEMENTED_AWAITING_OWNER_ACCEPTANCE（Draft PR #1831 已建立待 Owner 验收；
  M3_R2_STATUS=COMPLETE；不得自动 Mark Ready / Merge / 开始下一步）** — 回答业务问题：
  "Does a simple football-only prematch model contain predictive information competitive
  with the provider-defined closing 1X2 market?"（mandate VALUE_MVP-1，evidence 目录
  `footballprediction-value-mvp1-baseline-vs-closing-20260809T190028Z/`）。
  这是 **offline probability benchmark evaluation**，**不是** executable betting backtest /
  ROI / profitability / CLV 声明（README Backtest 行保持 Not yet established）。
- **实验纪律**：zero DB / zero network / zero new data；odds 不做模型 feature（13 个
  football-only feature：elo + 近 5 场滚动统计）；无 random split（walk-forward by season：
  fold1 train 2022/23 → test 2023/24；fold2 train 2022/23+2023/24 → test 2024/25）；
  protocol 在 OOS 前冻结（`config/value_mvp_1_evaluation_protocol.json`，
  PROTOCOL_SHA256=`c6716e911aa5fb32daab748a84ebd61313ae08acfb4e65a34994092d4b8732e8`）；
  imputer/scaler 仅 fit training 行；primary metric = multiclass log loss；INCONCLUSIVE
  为合法结果。
- **市场基准**：provider 定义 closing（消费 M3-R2 合同收据
  `m3-historical-odds-rebuild-receipt/v3`，CLOSING_MARKET_BENCHMARK_SEMANTICS_READY=YES；
  exact timestamps 未 proven → STRICT_DECISION_TIME_VALUE_EVALUATION_READY=NO，
  不发表任何 decision-time 声明）；每场至少 2 家 bookmaker，no-vig = 各家概率
  归一后取均值（MEAN_OF_BOOKMAKER_NO_VIG_PROBABILITIES）。
- **Phase 0（probe，888 场全部 7 项 gate PASS）**：closing log loss 0.9497299286 <
  first_collection 0.9548984998，closing mean overround 1.0510876522，无 §68 市场异常。
- **真实 OOS（protocol 冻结后，RUN_A/RUN_B 11 个业务输出文件字节一致）**：
  pooled OOS n=511 — model log loss 1.0691605748 vs closing market 0.9423141889，
  class-frequency 1.0729885322，delta log loss 0.1268463858
  （95% CI [0.0846640358, 0.1691520672]）；delta Brier 0.071739634
  （CI [0.0481335828, 0.0958094571]）；fold1（n=379）model 1.04464815 /
  market 0.9028403071 / delta 0.141807843；fold2（n=132）model 1.1395409458 /
  market 1.055652077 / delta 0.0838888688；**FINAL CLASSIFICATION =
  MARKET_BETTER_THAN_MODEL**（合法结果，任务技术成功 ≠ model wins；
  不自行加 feature / 换模型 / 调参 / 引入赔率 / 扩数据）。
- **验证**：validator 17 项检查全 PASS（含 bootstrap Brier CI 重算、calibration 重算、
  环境指纹与收敛记录交叉核验）；3 个 tamper 探针（receipt pooled 块翻转、summary.md
  摘要篡改、coordinated CI 伪造）REJECTED；Codex Round 1（§69，pre-execution）
  P0=P1=P2=0、Round 2（§70，post-OOS）P0=P1=P2=0；84 个 value_mvp 单元测试 +
  全套 2700 收集通过；ruff/格式干净。最终代码（1c53a00b7；经 cc96af12e 收据
  拆分、1c53a00b7 门禁 mypy type-clean 两轮修复，业务输出与 7f21c4f5 逐位一致）
  重跑真实 OOS 与 Round-1 证据数值逐位一致（protocol 未变，无 §90 语义变更）；run-receipt v2
  记录环境指纹（python 3.11.15 / sklearn 1.8.0 / numpy 2.3.5 / scipy 1.16.3）
  与 lbfgs 收敛状态（fold1 31/2000、fold2 21/2000，converged=True）。
- **入口**：`scripts/model_training/value_mvp_baseline_vs_closing.py`（internal research
  evaluation 入口，未登记 README canonical 表；实现 `src/ml/value_mvp/`，lifecycle:
  permanent）。
- 未改变：no-write 默认、无 DB/网络/训练/回测执行、无 migration、M3 core
  （`src/infrastructure/odds_staging/*`）未修改；README Backtest 行未升级为 established。
- **门禁状态（2026-08-10 更新）**：最终代码修订 `1c53a00b7a9c8533470af0fa1b26d1a2b33ecb78`
  （经 `cc96af12e` 收据拆分、`1c53a00b7` 门禁 mypy type-clean 两轮修复，业务输出逐位一致）。
  三次自然 exact-head Production Gate：31333103854（Gatekeeper >800 行）、31333795940
  （static-quality mypy 19 NEW）、31334605515（AI Workflow Gate PR body 6 项模板错误）。
  PR #1831 body 已按仓库模板对齐（11 个必需 section + `| Task type | source-code |`），
  本地 ai_workflow_gate.py --block-matrix 预验证 PASS；待下一次自然 pull_request
  synchronize gate 验证 exact head 通过后置
  `VALUE_MVP_1_STATUS=IMPLEMENTATION_VALIDATED / EXACT_HEAD_PRODUCTION_GATE=GREEN`，
  仍为 Draft、不 Merge、不 Mark Ready（等待 Owner + ChatGPT 独立验收）。

## M1 Test Foundation — Accepted (browser profile residue closed)

- **M1 可信测试地基 (Test Foundation)** — canonical test infrastructure milestone.
  - Status: **Accepted — browser profile residue closed**
  - Audit date: 2026-07-14
  - Final acceptance SHA: `e9114ce34d1885c70fdebd4b7be3c167458a5456`
  - FINAL_AUDIT_SHA: `14461ff0ad7559cf5541fbf4dd11d26e0348734c`
  - Runner flaky root cause (R2): `process.stdout.write` internal buffering under pipe
    backpressure; fix (#1785) replaces with `fs.writeSync` for deterministic fd-level output.
    Runner flaky is **closed**.
  - Runner self-test stress: 88 consecutive full-suite runs all exit 0, failed=0.
  - Failure propagation: verified (intentional failure → non-zero exit, no false green).
  - All 14 M1 PRs (#1768–#1781) + runner fix (#1785) merged, test/CI scope only.
  - **Browser profile residue closed** (#1788): root cause was Docker bind mount
    `docker-compose.dev.yml:58 ./data/browser_profile:/app/data/browser_profile`.
    Docker daemon created the host directory with `root:root` when it did not exist
    at container start. Fix: pre-create `data/browser_profile/` before Docker start
    in CI workflow and Makefile `dev-up` target. No production Dockerfile changes.
  - Final re-audit evidence:
    - Neutral host clone: `data/browser_profile` does not exist; root-owned 0
    - BrowserFactory target tests 20/20 pass, failed=0, no residue
    - Combined tests 5/5 pass, failed=0, no residue
    - CI (PR Gate + post-merge main Gate): success
    - Workspace: clean; artifact count unchanged; no untracked files
  - Old tag `m1-test-foundation-accepted` (→ `faaaff6b`) was created prematurely;
    retained for history but **superseded**.
  - `m1-test-foundation-accepted-v2` tag (→ `3d0aee6b`) is superseded by v3 —
    v2 carried the known browser_profile root-owned residue boundary now closed.
  - Official M1 acceptance tag: **`m1-test-foundation-accepted-v3`**
  - M1 boundaries: historical Python non-canonical debt, integration/e2e, real DB/network,
    model training, odds import are NOT in M1 scope and remain unchanged.
  - M2 (Governance growth freeze) is **unblocked** — v3 acceptance complete.
  - Next task: M2 read-only audit per Issue #1783. Do not start automatically.

## github_actions_workflow_permissions_hardening in progress

- **github_actions_workflow_permissions_hardening** — add least-privilege
  `permissions:` block to `production-gate.yml`.
  - Branch: `chore/github-actions-workflow-permissions-hardening`
  - **This is a CI token permissions hardening task.**
  - **No workflow behavior changed. No triggers, jobs, or steps modified.**
  - **No new write permissions added.**
  - **No DB. No SQL. No scraper/browser. No training. No data expansion.**
  - **Did not continue staging DB deployment.**
  - Added `permissions: {contents: read, actions: write, pull-requests: read}`.
  - New static tests: `tests/unit/test_github_actions_workflow_permissions_hardening.py`
  - SC-002 enforcement infrastructure complete.
  - Training / data expansion / real DB write remain blocked.
  - Next task: PR + CI validation. Do not start automatically.

## github_actions_workflow_inventory_phase1 completed

- **github_actions_workflow_inventory_phase1** — static inventory/audit of all
  `.github/workflows/` workflow files.
  - Branch: `chore/github-actions-workflow-inventory-phase1` (merged)
  - Inventory doc: `docs/GITHUB_ACTIONS_WORKFLOW_INVENTORY_PHASE1.md` (1 workflow inventoried)
  - Static tests: `tests/unit/test_github_actions_workflow_inventory_phase1.py` (33 tests)
  - SC-002 enforcement infrastructure complete.
  - Training / data expansion / real DB write remain blocked.

## agent_workflow_hardening_phase1 completed

- **agent_workflow_hardening_phase1** — standardize AI agent PR lifecycle CI evidence and governance.
  - Branch: `chore/agent-workflow-hardening-phase1` (merged)
  - Hardening doc: `docs/AI_AGENT_WORKFLOW_HARDENING.md`
  - CLAUDE.md updated: Final Report Rule, Main Gate Evidence Rule, Branch Safety Rule,
    Scope Drift Rule, Completion Definition Rule added. SC-002 status corrected.
  - Makefile enhanced: CI monitoring section with hardening doc reference.
  - Tests: `test_agent_workflow_hardening.py`, `test_agent_workflow_hardening_phase1_ci_rules.py`.
  - SC-002 enforcement infrastructure complete.
  - Training / data expansion / real DB write remain blocked.

## sc002_staging_db_role_deployment_plan completed

- **sc002_staging_db_role_deployment_plan** — staging DB role separation deployment plan.
  - Branch: `chore/sc002-staging-db-role-deployment-plan`
  - **Planning/documentation only. No DB, no SQL, no deployment, no real changes.**
  - New plan doc: `docs/SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md`
  - Contains: target 6-role model, prerequisites, deployment step drafts, rollback plan,
    validation matrix (6 roles × 14 ops), go/no-go checklist.
  - SC-002 enforcement infrastructure complete.
  - Training / data expansion / real DB write remain blocked.
  - Next task: `sc002_staging_db_role_deployment`. Do not start automatically.

## sc002_final_closure_check completed

- **sc002_final_closure_check** — final per-criterion SC-002 closure verification.
  - Branch: `chore/sc002-final-closure-check`
  - **This is a verification/documentation task. No DB, no SQL, no write.**
  - New closure check doc: `docs/SC002_FINAL_CLOSURE_CHECK.md`
  - All 10 criteria verified against concrete evidence from the codebase.
  - 9 criteria fully satisfied. 1 criterion substantially met (staging role deploy pending).
  - 0 criteria not met or unsatisfied.
  - **SC-002 status: enforcement complete** (was: partial mitigation only).
  - Training / data expansion / real DB write remain blocked (require separate authorization).
  - Next task: `sc002_staging_db_role_deployment`. Do not start automatically.

## deploy_docker_init_sql_guard completed

- **deploy_docker_init_sql_guard** — SC-002 Gate B: dev-only execution guard added to
  `deploy/docker/init_db.sql` to prevent accidental non-dev execution.
  - Branch: `chore/deploy-docker-init-sql-guard`
  - **This is a static guard implementation. No DB, no SQL, no psql, no docker compose run.**
  - Guard details:
    - `SET sc002.init_sql_context = 'development'` at the very top of init_db.sql
    - DO block verifies via `current_setting()`, RAISE EXCEPTION on mismatch
    - Guard explicitly forbids staging, production, and non-dev execution
    - No env-var bypass — operator must modify the guard itself to bypass
  - `docker-compose.dev.yml`: `command: [postgres, -c, sc002.init_sql_context=development]`
  - `.env.example`: Guard documentation added
  - Tests: 15 new static tests (`TestInitSqlGuardGateB`), 54 total dev POC tests
  - Gate B: init_db.sql guard implemented.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Next task: `sc002_final_closure_check`. Do not start automatically.

## changed_files_negative_case_enforcement_test completed

- **changed_files_negative_case_enforcement_test** — static negative-case enforcement tests
  proving that unguarded DB write paths are rejected by CI changed-files enforcement (Criterion #2).
  - Branch: `chore/changed-files-negative-case-enforcement-test`
  - **This is a static test task. No DB, no SQL, no write, no scraper/browser.**
  - New test file: `tests/unit/test_changed_files_negative_case_enforcement.py` (29 tests)
  - Negative cases proven: unguarded INSERT, UPDATE, CREATE, DELETE → rejected by Python scanner.
    Destructive SQL DROP → rejected by SQL scanner.
  - Positive cases proven: allowlisted files pass, no-DB files pass, non-SQL ignored.
  - Conservative detection: guarded-but-unallowlisted files flagged; DB-importing files flagged.
  - All tests use temp fixture files inside REPO_ROOT — never modify real code.
  - Criterion #2: Substantially met.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Next task: `deploy_docker_init_sql_guard`. Do not start automatically.

## browser_fotmob_pageprops_playwright_deep_audit completed

- **browser_fotmob_pageprops_playwright_deep_audit** — deep per-script static verification
  of all 43 skipped_complex JS scripts (Browser/FotMob/pageProps/Playwright paths).
  - Branch: `chore/browser-fotmob-pageprops-playwright-deep-audit`
  - **This is a static audit/verification task. No browser, no Playwright, no DB, no SQL.**
  - New audit doc: `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md`
  - Key findings:
    - All 43 skipped_complex scripts individually verified per-script.
    - **13 false_positive_select_only:** All confirmed non-write with active SQL guard wrappers.
    - **3 design_mapped shared modules:** All active write-capable consumers verified guarded.
    - **12 read_only:** All confirmed no DB client, no SQL execution.
    - **3 false_positive_read_only_transaction:** Confirmed with DB-level READ ONLY tx.
    - **0 hidden write paths discovered. 0 unknown_needs_followup.**
    - **1 classification correction:** `fotmob_ligue1_adg60_raw_payload_source_inventory.js`
      (scraper_or_browser_only → read_only — static file classifier, no browser/network/DB).
  - Criterion #1: Substantially met — deep per-script verification complete.
  - Criterion #3: Substantially met — deep verification complete.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Next task: `changed_files_negative_case_enforcement_test`. Do not start automatically.

## runtime_db_role_permission_dev_poc completed

- **runtime_db_role_permission_dev_poc** — dev-only POC of 6-role DB permission model.
  - Branch: `chore/runtime-db-role-permission-dev-poc`
  - **Dev-only. Not applied to staging or production.**
  - Files modified:
    - `deploy/docker/init_db.sql` — 6 PostgreSQL roles with least-privilege GRANTs
    - `docker-compose.dev.yml` — role-specific env vars for dev container
    - `.env.example` — role-specific connection config templates
    - `tests/unit/test_runtime_db_role_permission_dev_poc.py` — static validation tests
  - Roles created (dev-only passwords, all `*_dev_poc`):
    - `football_owner` — DDL/migration owner (full DDL + DML)
    - `football_app` — runtime DML (SELECT, INSERT, UPDATE; no DDL)
    - `football_ingestion` — write-limited (INSERT, UPDATE on matches/raw_match_data/odds)
    - `football_training` — training tables (INSERT, UPDATE on match_features_training/predictions)
    - `football_reader` — SELECT only on all tables
    - `football_gatekeeper` — SELECT only (CI/test temporary probes)
  - **No DB connection. No SQL execution. No real permission changes.**
  - **No real secrets. No production config modifications.**
  - SC-002 was partial mitigation only at that task's completion.
  - Criterion #6: Reviewed + Dev POC. Remains unmet for staging/production.
  - Training / data expansion / real DB write remain blocked.

## runtime_db_role_permission_review_phase1 completed

- **runtime_db_role_permission_review_phase1** — static review of DB role/permission model.
  - Branch: `chore/runtime-db-role-permission-review-phase1`
  - New review doc: `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md`
  - **This is a static audit/documentation task. No DB connection, no permission changes.**
  - Key findings:
    - **Single universal user:** `football_user` used for ALL roles (app, migration, ingestion,
      training, maintenance, CI) — full DDL + DML on all tables.
    - **One read-only user exists:** `claude_reader` for MCP only (good practice, limited scope).
    - **No privilege separation:** Migration (DDL) and runtime (DML) use the same user.
    - **No least privilege:** Ingestion, training, and maintenance each have full DB access.
    - **Hardcoded dev credentials** in `docker-compose.dev.yml` and `init_claude_reader.sql`
      (acceptable for dev, not for production).
    - **Application-layer only protection:** All write safety relies on env-var gates;
      no DB-layer role restrictions as defense-in-depth.
  - Recommended target model: 6 specialized roles (owner, app, ingestion, training, reader,
    gatekeeper) with least-privilege grants.
  - Next step: Apply role model in Docker dev environment as proof-of-concept.
  - SC-002 was partial mitigation only at that task's completion. Criterion #6 now reviewed (remains unmet for implementation).
  - Training / data expansion / real DB write remain blocked.

## sc002_overall_closure_assessment completed

- **sc002_overall_closure_assessment** — per-criterion gap analysis of SC-002 closure.
  - Branch: `chore/sc002-overall-closure-assessment`
  - New assessment doc: `docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md`
  - **This is a documentation/assessment task, NOT runtime implementation.**
  - This task did NOT run DB, SQL, migration, scraper, browser, training, or data expansion.
  - Assessment results (10 criteria):
    - Met or in good standing: 6 (criteria #5 Python/SQL/migration, #7 no production override,
      #8 training blocked, #9 PROJECT_STATUS aligned, #10 CI green, #4 shared module boundary)
    - Partial: 2 (criterion #1 entrypoints guarded, criterion #3 browser/FotMob audit)
    - Not met: 2 (criterion #2 negative-case testing, criterion #6 DB role/permission review)
  - Key gaps identified:
    - 43 skipped_complex JS scripts classified but not individually verified non-write
    - No deliberate negative-case CI testing
    - DB role/permission model not reviewed
    - `deploy/docker/init_db.sql` needs guard (Gate B)
  - Next recommended task: `runtime_db_role_permission_review_phase1` (low effort, documentation only)
  - SC-002 was partial mitigation only at that task's completion. Cannot be closed.
  - Training / data expansion / real DB write remain blocked.

## sc002_alembic_migration_runtime_guard completed

- **sc002_alembic_migration_runtime_guard_implementation** — runtime guard added to
  `src/database/migrations/env.py` for the last remaining unguarded Python write path.
  - Branch: `chore/sc002-alembic-migration-runtime-guard`
  - **Guard implemented in `run_migrations_online()` before any DB engine/connection/migration.**
  - Guard details:
    - Function: `_check_alembic_migration_guard()`
    - Reuses existing `scripts/ops/helpers/python_db_write_guard.py` (`assert_db_write_allowed`)
    - Operation: `CREATE` (triggers schema-level `ALLOW_SCHEMA_WRITE` gate)
    - `ALEMBIC_CTX` env var: `ci`/`dev`/`docker_init` auto-allow with `ALLOW_SCHEMA_WRITE=yes`
    - Production-like host **hard block** (no override)
    - `run_migrations_offline()` (`--sql` mode) NOT guarded
  - Allows list updated: env.py → `alembic_migration_runtime_guarded`
  - **Python write paths guarded: 18/20 (was 17/20).**
  - **All 20 Python write paths now classified and resolved. 0 unreviewed. 0 pending.**
  - This task did NOT run Alembic, migration, SQL, DB connection, or real DB write.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Next task: None from Python track — all 20 Python write paths resolved.
    SC-002 overall closure criteria assessment when remaining non-Python criteria are met.
    Do not start automatically.

## sc002_alembic_migration_guard_design completed

- **sc002_alembic_migration_guard_design** — design, classification, and implementation
  plan for the last remaining SC-002 Python write path: `src/database/migrations/env.py`
  (Alembic migration environment).
  - Branch: `chore/sc002-alembic-migration-guard-design`
  - New design doc: `docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md`
  - **This is a design/classification task, NOT runtime guard implementation.**
  - **0 runtime guards added. No code changed in env.py.**
  - This task did NOT run Alembic, migration, SQL, DB connection, scraper, or training.
  - Classification result: `alembic_migration_needs_specialized_runtime_guard`
    - env.py IS a real schema write path (orchestrates arbitrary DDL/DML via migration scripts)
    - env.py is NOT a false positive or read-only candidate
    - env.py requires specialized guard approach (framework orchestrator, not standalone script)
    - Standard `assert_db_write_allowed()` pattern doesn't directly fit (would break CI/dev)
  - Guard strategy designed:
    - Guard location: top of `run_migrations_online()` before any DB connection
    - Env vars: `ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`, `ALLOW_SCHEMA_WRITE`, `DRY_RUN`
    - Production-like host hard block (matching JS/Python guard pattern)
    - `ALEMBIC_CTX` env var for CI/dev context auto-allow
    - Offline mode (`--sql`) NOT guarded
  - Implementation plan documented with pseudocode, integration points, and CI/dev workflow
    compatibility analysis.
  - Allowlist updated: env.py reclassified from `pending_runtime_guard` to
    `alembic_migration_needs_specialized_runtime_guard` with full evidence and design doc reference.
  - **Python write paths guarded count: still 17/20** (unchanged — no guard added).
  - **1 path now has precise classification with implementation plan** (was generic
    `pending_runtime_guard`).
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Next task: `sc002_alembic_migration_runtime_guard_implementation`.
    Do not start automatically.

## python_manual_review_guard_phase2e completed

- **python_manual_review_guard_phase2e** — runtime DB write guard implementation
  completed for the 2 manual review write paths confirmed in Phase2D.
  - Branch: `chore/python-manual-review-guard-phase2e`
  - **2 of 2 files now have runtime guard (`assert_db_write_allowed`) before real DB write.**
  - Guard details:
    | # | File | Guard Location | Operation | Table |
    |---|---|---|---|---|
    | 1 | `scripts/maintenance/reprocess_from_local.py` | `backfill_features()` before UPDATE | UPDATE | `matches` |
    | 2 | `src/api/monitoring/prometheus_metrics.py` | `_persist_to_database()` before INSERT | INSERT | `failed_market_data` |
  - Uses existing `helpers/python_db_write_guard.py` pattern — no new mechanism.
  - All guards placed before real DB write operations.
  - Allowlist updated: 2 entries reclassified from `manual_confirmed_write_needs_guard` to `manual_confirmed_write_path_runtime_guarded`.
  - Updated `_runtime_guard_status`: **17/20** Python write paths now runtime guarded.
  - Docs updated: `SC002_MANUAL_REVIEW_PHASE2D.md`, `SC002_CLOSURE_PLAN.md`, `PROJECT_STATUS.md`.
  - **This task did NOT run any target script, DB connection, SQL/migration, scraper, training, or real DB write.**
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.

## python_manual_review_phase2d completed

- **python_manual_review_phase2d** — static manual review completed for all 5
  remaining `historical_python_needs_manual_review` entries.
  - New design doc: `docs/SC002_MANUAL_REVIEW_PHASE2D.md`
  - Allowlist updated: 5 entries reclassified with full evidence
  - **This is a static review/classification task, NOT runtime guard implementation.**
  - **0 runtime guards added. 0 files marked safe or runtime_guarded.**
  - This task did NOT run DB / migration / scraper / training.
  - Classification results:
    - **2 manual_confirmed_write_needs_guard** — reprocess_from_local.py (UPDATE matches,
      same pattern as reprocess_failed_matches.py), prometheus_metrics.py (INSERT
      failed_market_data via DeadLetterQueue._persist_to_database)
    - **1 manual_read_only_candidate** — monitoring.py (all SELECT/fetchrow via asyncpg,
      health checks/metrics only)
    - **2 manual_false_positive_candidate** — fotmob_historical_backfill.py (DEPRECATED,
      core deps = None, cannot execute), diagnose_diagnostic.py (syntactically broken,
      cannot parse/execute)
    - **0 manual_confirmed_write_already_guarded**, **0 manual_needs_design**,
      **0 manual_unknown_needs_followup**
  - **0 manual review candidates remain** — all 5 have been classified.
  - Guard implementation for 2 write_needs_guard paths deferred to `python_manual_review_guard_phase2e`.
  - Python write paths guarded count: **still 15/20** (unchanged).
  - **2 next guard candidates** identified (reprocess_from_local.py, prometheus_metrics.py).
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.

## python_indirect_write_path_guard_phase2 completed

- **python_indirect_write_path_guard_phase2** — runtime DB write guard implementation
  completed for all 6 `indirect_write_needs_guard` paths classified in design phase1.
  - Branch: `chore/python-indirect-write-path-guard-phase2`
  - **6 of 6 files now have runtime guard (`assert_db_write_allowed`) before real DB write.**
  - Guard details:
    | # | File | Guard Location | Operation | Table |
    |---|---|---|---|---|
    | 1 | `src/services/match_aligner.py` | `save_alignment()` before INSERT | INSERT | `matches_mapping` |
    | 2 | `src/services/match_linker.py` | `store_odds_intelligence()` + `batch_store_odds_intelligence()` before CREATE TABLE + INSERT | CREATE, INSERT | `match_odds_intelligence` |
    | 3 | `src/api/collectors/odds_api_client_v38.py` | `save_odds_to_db()` before INSERT | INSERT | `match_odds` |
    | 4 | `scripts/maintenance/reprocess_failed_matches.py` | `reprocess_match()` before UPDATE | UPDATE | `matches` |
    | 5 | `scripts/maintenance/clean_corrupt_l2.py` | `clean_corrupt_records()` before UPDATE (integrated with `dry_run` param) | UPDATE | `matches` |
    | 6 | `scripts/maintenance/fix_zombie_matches.py` | `fix_zombie_matches()` before `_batch_update_matches()` (integrated with `self.dry_run`) | UPDATE | `matches` |
  - Uses existing `helpers/python_db_write_guard.py` pattern — no new mechanism invented.
  - All guards placed before real DB write operations, not after.
  - 3 scripts with existing `--dry-run` flags have `dry_run` parameter integrated into guard call.
  - Allowlist updated: 6 entries reclassified from `indirect_write_needs_guard` to `indirect_write_path_runtime_guarded`.
  - Updated `_runtime_guard_status` in allowlist: **15 of 20 Python write paths now runtime guarded** (9 confirmed + 6 indirect).
  - Docs updated: `SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md`, `SC002_CLOSURE_PLAN.md`, `PROJECT_STATUS.md`.
  - **This task did NOT run any target script, DB connection, SQL/migration, scraper, training, or real DB write.**
  - **5 manual review candidates NOT processed.** SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.

## python_indirect_write_path_design_phase1 completed

- **python_indirect_write_path_design_phase1** — static design classification completed
  for all 8 `historical_python_indirect_write_path_pending_runtime_guard` entries.
  - New design doc: `docs/SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md`
  - New tests: `tests/unit/test_indirect_write_path_design_phase1.py` (17 tests)
  - Allowlist updated: 8 entries reclassified with full evidence
  - **This is a design/classification task, NOT runtime guard implementation.**
  - **0 runtime guards added. 0 files marked safe or runtime_guarded.**
  - This task did NOT run DB / migration / scraper / training.
  - Classification results:
    - **6 indirect_write_needs_guard** — all actually DIRECT write paths (use OWN psycopg2
      connection with explicit INSERT/UPDATE + commit, NOT via repository layer as
      original design assumed): match_aligner.py (INSERT matches_mapping), match_linker.py
      (INSERT+CREATE match_odds_intelligence), odds_api_client_v38.py (INSERT match_odds),
      reprocess_failed_matches.py (UPDATE matches, default=dry_run=false), clean_corrupt_l2.py
      (UPDATE matches nullification, default=dry_run=false), fix_zombie_matches.py (UPDATE
      matches, default=dry_run=false)
    - **1 indirect_read_only_candidate** — league_router.py (SELECT DISTINCT only, URL routing)
    - **1 indirect_false_positive_candidate** — match_data_service.py (skeleton class, zero
      write methods, misleading aliases)
    - **0 indirect_write_already_guarded**, **0 indirect_write_needs_design**,
      **0 indirect_unknown_needs_manual_review**
  - Key finding: 6 of 8 "indirect" paths are actually DIRECT — original design doc was
    imprecise. All 6 lack any guard. 3 of 6 have --dry-run flags but default is write-enabled
    (unsafe default).
  - Guard implementation for 6 needs_guard paths deferred to `python_indirect_write_path_guard_phase2`.
  - Confirmed Python write paths guarded count: **still 9/14** (unchanged).
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - 5 manual review candidates NOT processed.

## consumer_level_guard_audit_db_pool_sync_sql_store completed

- **consumer_level_guard_audit_db_pool_sync_sql_store** — consumer-level static audit completed
  for 3 infrastructure-only confirmed Python write paths.
  - New audit doc: `docs/SC002_CONSUMER_LEVEL_GUARD_AUDIT_DB_POOL_SYNC_SQL_STORE.md`
  - New tests: `tests/unit/test_consumer_level_guard_audit_db_pool_sync_sql_store.py` (41 tests)
  - Allowlist updated: 3 infrastructure entries now have consumer audit references
  - **This is a consumer-level audit / design task, NOT runtime guard implementation.**
  - Confirmed Python write paths guarded count: **still 9/14**.
  - This task did NOT add any runtime guard.
  - This task did NOT run DB / migration / scraper / training.
  - Consumer audit findings:
    - **2 write consumers already guarded** (collector_repository.py, streaming_db_writer.py in batch3)
    - **6 read-only consumers** (main.py, health.py, monitoring.py, dataset_generator.py, async_dependencies.py, performance_monitor.py)
    - **3 no_active_consumers** (SQLStore, SyncDatabasePool utils aliases, test mocks)
    - **0 unguarded write consumers** (category A) — all write consumers already guarded
    - **0 dynamic/unknown consumers** (categories D, E)
  - Next guard implementation candidates: none from this audit — all write consumers already guarded.
    Remaining 5 confirmed Python write paths in Phase2C batch4 still need guard implementation.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.
  - Indirect write paths (8) NOT processed.
  - Manual review candidates (5) NOT processed.

## ci_local_parity_preflight_phase1 completed

- **ci_local_parity_preflight_phase1** — local PR Gate preflight added.
  - New script: `scripts/ops/local_pr_gate_preflight.py`
  - New tests: `tests/unit/test_local_pr_gate_preflight.py` (23 tests)
  - New Makefile target: `make pr-gate-local PR_BODY=<file>`
  - New npm script: `npm run pr-gate-local`
  - Goal: improve remote CI first-pass rate by catching failures locally.
  - This is workflow / CI parity hardening, NOT SC-002 closure.
  - Does NOT change 6/14 runtime guarded state.
  - Does NOT change remaining 8 confirmed write paths.
  - Does NOT change 8 indirect write paths.
  - Does NOT change 5 manual review candidates.
  - Does NOT unlock training / data expansion / real DB write.
  - SC-002 was partial mitigation only at that task's completion.
  - Training / data expansion / real DB write remain blocked.

## Current baseline

> 以下历史 baseline 段落保留用于追溯，不再定义当前 agent workflow。当前操作权威是
> `AGENTS.md`，详细说明是 `docs/AGENT_WORKFLOW.md`；GitHub ruleset、Actions 和 Git
> 状态是机器事实。

- `main` includes PR #1463 (P0 AI Workflow Gate CI enforcement).
- `main` includes PR #16XX (`agent_workflow_rules_hardening_phase1`) — three-layer agent
  workflow discipline codified into the repo:
  1. **Resident rules**: `CLAUDE.md` now contains comprehensive non-negotiable agent
     workflow hardening rules (branch, scope, safety, SC-002, PR, task-type, post-merge
     discipline). Agents no longer need repeated long-form prompts for basic discipline.
  2. **PR template**: `.github/pull_request_template.md` now includes `## SC-002 status`,
     `## Remaining risks`, and a 16-item Agent Workflow Hardening Checklist.
  3. **CI / AI Workflow Gate**: `scripts/ops/ai_workflow_gate.py` enforces:
     - New required sections: `## SC-002 status`, `## Remaining risks`
     - Forbidden rewrite file patterns (`*_v2.py`, `*_final.js`, etc.) for new files
     - Forbidden safety claims (prematurely declaring SC-002 resolved or training/DB write unblocked)
     - Large risky change detection (deletion/rename/scanner-count thresholds)
     - Existing gates preserved (Phase2A Python, Phase2B SQL, Phase2 JS DB write)
  - SC-002 was partial mitigation only at that task's completion.
  - training / data expansion / real DB write remain blocked.
- `main` includes PR #1464 (local CI gatekeeper entrypoint).
- `main` includes PR #1567 (authoritative workflow enforcement dry-run).
- `main` includes PR #1569 (p0_db_write_safety_gate_fix_phase1 — unified guard + 8 scripts).
- `p0_db_write_guard_hardening_production_host_block` hardens the guard: production-like
  DB hosts are now blocked by default (previously warning-only). No production override exists.
- `p0_db_write_safety_gate_fix_phase2` adds guard to 8 more P0 scripts/ops entrypoints.
  Phase1 + Phase2 + Phase3 + Phase4 + Phase5 + Phase7 = 43 scripts now protected. SC-002 was partial mitigation only at that task's completion.
- Remote GitHub Actions `production-gate.yml` is the final CI authority.
- Local `make ci-local-pr` is a pre-push helper, not a full replacement for remote CI.
- The current workflow boundary is described by `AGENTS.md` and
  `docs/AGENT_WORKFLOW.md`. The following are implementation/helpers or
  historical records, not additional workflow authorities:
  - `scripts/ops/ai_workflow_gate.py` (CI-enforced workflow and documentation checks)
  - `scripts/devops/gatekeeper.sh` (CI-enforced, multi-phase)
  - `scripts/ops/documentation_governance_check.py` (standalone checker)
  - `.github/pull_request_template.md` (mandatory PR structure)
  - `docs/DOCUMENTATION_GOVERNANCE.md` (doc lifecycle rules)

## Current SC-002 status (DB write safety gate)

- SC-002 two-layer state: `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
  `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`. See
  `docs/SC002_FINAL_CLOSURE_CHECK.md`. Training / data expansion / real DB write
  remain blocked (require separate authorization).
- A unified guard helper (`scripts/ops/helpers/db_write_guard.js`) has been added.
- Production-like DB host (RDS, Cloud SQL, Supabase, etc.) is hard blocked by default.
  No production override exists. No `ALLOW_PRODUCTION_DB_WRITE` bypass variable exists.
- `p0_db_write_safety_gate_fix_phase1` (#1569): 8 scripts integrated.
- `p0_db_write_guard_hardening_production_host_block` (#1570): production host hard block.
- `p0_db_write_safety_gate_fix_phase2` (#1571): 8 more scripts integrated.
- `db_write_guard_static_enforcement_dry_run` (#1572): static scanner deployed.
- `p0_db_write_safety_gate_fix_phase3` (#1573): 8 more scripts integrated.
- `db_write_guard_static_enforcement_fix_phase1` (#1575): advisory warning in
  ai_workflow_gate.py for new/modified unguarded scripts/ops JS files.
- `p0_db_write_safety_gate_fix_phase4` (#1576): 6 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase5` (#1579): 7 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase6` (#1580): 5 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase7` (#1582): 1 script integrated.
- **Phase1 + Phase2 + Phase3 + Phase4 + Phase5 + Phase6 + Phase7 = 43 of 66 P0 scripts now guarded.**
- **db_write_guard_static_enforcement_fix_phase2** (#1583): changed-files enforcement
  upgraded from advisory to hard fail in ai_workflow_gate.py. New/modified unguarded
  scripts/ops JS files now cause CI failure. Historical full-scan candidates are
  explicitly categorized (NOT fixed) and exempt from hard fail.
- **sc002_closure_plan_phase0** (#1584): SC-002 closure plan documented in
  `docs/SC002_CLOSURE_PLAN.md`. At the time this record was written that doc
  was the authoritative SC-002 status reference (current authoritative status:
  `docs/data/FOTMOB_CURRENT_STATE.md`).
  SC-002 was partial mitigation only at that task's completion. 43/66 guarded. 22 categorized, not fixed.
  21 additional browser/Playwright scripts identified as skipped_complex (total 43).
  Training, data expansion, and real DB write remain blocked.
- **specialized_browser_fotmob_pageprops_audit_phase1** (#1585): Static audit of all
  43 skipped_complex scripts completed. See `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md`.
  Key findings: 20 confirmed DB write paths, 14 read-only/no-DB, 4 need manual review,
  3 shared modules, 1 scraper/browser only, 1 possible indirect write.
  The gap is now precisely characterized: 28 scripts need guard/exclusion action.
  SC-002 was partial mitigation only at that task's completion.
- **confirmed_write_path_guard_phase1_high_risk_browser_db** (#1586): Guard integration
  complete for the 2 highest-risk browser+DB skipped_complex scripts:
  `odds_sniper.js` and `fixture_harvester_l1.js`. Both now call `assertDbWriteAllowed()`
  before DB write operations. These are NOT part of the original 66 P0 — they are
  skipped_complex write paths now guarded.
- **confirmed_write_path_guard_phase2_batch1** (this PR): Guard integration for 3
  controlled-write scripts with INSERT INTO raw_match_data:
  `pageprops_v2_single_target_controlled_write.js`,
  `remaining_seeded_pageprops_v2_controlled_write.js`,
  `single_league_pageprops_v2_controlled_write_execute.js`.
  Remaining confirmed_write_path_needs_guard: 15 of 20.
  SC-002 was partial mitigation only at that task's completion.
- **confirmed_write_path_guard_phase2_batch2** (this PR): Guard integration for 1
  FotMob raw JSON DB storage script with INSERT INTO fotmob_raw_match_payloads:
  `fotmob_adg60_raw_json_db_storage_no_feature_parse.js`.
  Now calls `assertDbWriteAllowed()` before INSERT query.
  6 confirmed write paths guarded. Remaining: 14 of 20.
  Deep static analysis revealed that 10+ of the remaining
  "confirmed_write_path_needs_guard" scripts are false positives (SELECT-only with
  active SQL enforcement wrappers, or no DB connection at all).
  SC-002 was partial mitigation only at that task's completion.
- **sc002_allowlist_cleanup_phase1** (this PR): Formal reclassification of 15 scripts
  from `confirmed_write_path_needs_guard` to verified false positive categories:
  - 11 false_positive_select_only_with_active_wrapper (SELECT-only + queryReadOnly/safeSelect)
  - 2 false_positive_read_only_transaction (BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql)
  - 1 false_positive_no_db_connection_static_scan (no pg import, fs/child_process only)
  - 1 false_positive_policy_or_regex_keyword_only (INSERT only in conflict_policy string)
  All 20 original confirmed_write_path classifications are now resolved (6 guarded, 14
  reclassified). **0 still_needs_guard remain.**
  4 needs_manual_review remain unchanged. 3 shared_module unchanged. 1
  possible_indirect_write unchanged. SC-002 was partial mitigation only at that task's completion.
  Training, data expansion, and real DB write remain blocked.
- **shared_module_db_write_boundary_implementation_phase1** (#1592): HIGH priority
  guard implemented for `odds_harvest_pipeline.js` — the unguarded consumer discovered
  by the design phase. `assertDbWriteAllowed()` added in `upsertMappingAndOdds()` before
  BEGIN transaction, guarding INSERT/UPSERT on `matches_oddsportal_mapping` and `odds`
  tables. Same pattern as `odds_sniper.js` (Phase 1). Gatekeeper.js / gatekeeper.sh
  still pending. 8 needs_manual_review consumers still pending. No target script
  executed. No DB connection. No Playwright/browser run. SC-002 was partial
  mitigation only at that task's completion. Training, data expansion, real DB
  write remain blocked.
- **gatekeeper_boundary_implementation** (this PR): MEDIUM priority guard implemented
  for `gatekeeper.js` and `gatekeeper.sh` — the CI infrastructure consumers of
  `dbBlueprint.js`. Both entrypoints now call `assertDbWriteAllowed()` before
  `runColdStartBlueprintCheck` (which triggers CREATE DATABASE, DROP DATABASE, and
  INSERT write probe on `matches`, `raw_match_data`, `matches_oddsportal_mapping`).
  Guard at consumer entrypoint, not module level. Guard pattern: `assertDbWriteAllowed({
  script: 'gatekeeper.js', tables: ['matches', 'raw_match_data',
  'matches_oddsportal_mapping'], operations: ['CREATE', 'DROP', 'INSERT'] })` (same
  pattern for gatekeeper.sh with script 'gatekeeper.sh'). dbBlueprint.js unchanged.
  No target script executed. No DB connection. No real DB write. No scraper/browser run.
  No training. No data expansion. No schema migration. 9 needs_manual_review consumers
  still pending (corrected count — PR body typo said 8). SC-002 was partial
  mitigation only at that task's completion. Training, data expansion,
  real DB write remain blocked.
- **manual_review_phase1** (this PR): Static review and reclassification of all 14
  remaining `needs_manual_review` / `possible_indirect_write` scripts from both the
  shared-module design doc (9 dbBlueprint consumers) and the broader skipped_complex
  audit (4 pageProps + 1 possible_indirect_write). Full per-script evidence in
  `docs/SC002_MANUAL_REVIEW_PHASE1.md`. Results:
  - **7 already_guarded** (had guard from Phase1-7; design doc classification was stale):
    cleanup_csv_bulk_loader_import.js, purge_ghost_data.js, purge_orphans.js,
    raw_match_data_completeness_fidelity_audit.js, renewed_pageprops_v2_raw_write_execute.js
    (transitive via base), reset_database.js, seed_fotmob_sample.js
  - **3 false_positive_no_db_write_evidence** (SELECT-only or zero DB connection):
    fetch_and_adapt_euro_leagues.js, master_inventory.js, pageprops_v2_identity_contract_
    regression_execute.js, pageprops_v2_suspended_target_review_execute.js
  - **2 false_positive_select_only_with_active_wrapper**: all_seeded_pageprops_v2_
    canonical_read_verification.js, pageprops_v2_post_write_canonical_read_verification.js
  - **1 false_positive_read_only_transaction**: training_pipeline_smoke_dry_run.js
  - **0 confirmed_write_path_needs_guard**, **0 remaining needs_manual_review**
  - Count mismatch resolved: previous PR said "8" (typo), actual design-doc count is 9;
    combined with audit-doc 5 = 14 total reviewed
  - No guard implemented (all already guarded). No target script executed. No DB
    connection. No real DB write. No scraper/browser. SC-002 was partial
    mitigation only at that task's completion. Training, data expansion, real DB
    write remain blocked.
- **shared_module_db_write_boundary_design_phase1** (#1591): Static design of shared
  module DB write boundary completed. 3 shared modules mapped with full consumer
  entrypoint inventory:
  - `dbBlueprint.js` (24 consumers, 3 write-capable, 18 read-only, 3 needs_manual_review)
  - `restoreMappingsWorkflow.js` (0 active consumers, dependency-injected write path)
  - `odds_harvest_pipeline.shared.js` (2 consumers: 1 guarded, 1 UNGUARDED gap found —
    `odds_harvest_pipeline.js`)
  Key findings: `odds_harvest_pipeline.js` is an unguarded CLI entrypoint consuming
  write SQL from the shared module (not in any prior audit or guard phase).
  `gatekeeper.js`/`gatekeeper.sh` use `runColdStartBlueprintCheck` (DB write path) with
  no guard. Consumer entrypoint map recommends guard at consumer level, not module level.
  No runtime behavior changed. SC-002 was partial mitigation only at that task's completion.
  Training, data expansion, and real DB write remain blocked.
- Remaining 22 complex candidates categorized into:
  - `pageprops_pipeline` (9): pageProps/FotMob pipeline scripts
  - `fotmob_pipeline` (2): FotMob ingestion scripts
  - `shared_module` (3): shared helper modules consumed by entrypoints
  - `dry_run_or_audit` (8): dry-run, audit, preflight scripts
  - Plus 21 browser/Playwright scripts previously classified as `skipped_complex`
- Each remaining candidate has: explicit category, reason, reviewed_at, future_action.
  These are NOT counted as "guarded". SC-002 two-layer state:
  `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
  `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`.
- DB write safety: changed-file hard-fail enforcement active; phase1-7 guards
  added (43/66 scripts/ops JS entrypoints); staging/production role deployment
  pending.
- Guard remains opt-in per script for historical files. New scripts touching
  `scripts/ops/` with DB write risk MUST integrate the guard or be explicitly
  allowlisted — enforced via CI hard fail on changed-files.
- Training and data expansion remain blocked.
- No real DB write is authorized.
- Changed-files hard fail scope: **scripts/ops/\*\*/\*.js only** for the JS
  scanner; Python and SQL/migration enforcement runs via the separate
  PYTHON-DB-WRITE and SQL-MIGRATION gate outputs
  (`python_db_write_enforcement_check.py`, `sql_migration_policy_enforcement_check.py`,
  invoked by `scripts/ops/ai_workflow_gate.py`).

## Current operating rules

- One task / one branch / one PR.
- Do not work directly on `main`.
- Do not mix governance changes with runtime business code (CI-enforced).
- Do not start automatically. Recommended next task only after user confirmation (CI-enforced).
- PR body must include the canonical sections: Summary, Scope, Tests, Risk, Rollback.
- `Scope` must state task type, changed paths, and runtime behavior impact; `Tests` must
  list actual commands and exit codes; `Risk` must state side effects and any required
  high-risk authorization.
- Source changes invalidate old review/CI evidence; exact full SHA is required for
  freshness and merge completion.
- If a PR adds or modifies `docs/_reports/*.md`, it must update an
  authoritative doc or give a concrete source-of-truth no-update reason in the
  PR body.

## Current allowed work

- Small docs-only source-of-truth updates (like this file).
- Read-only audits.
- Small, scoped CI/governance fixes that do not touch runtime code.
- SC-002 closure planning, governance, and documentation tasks.
- Future FotMob/data work only after explicit user confirmation and under
  read-only/no-write constraints.

## Current blocked work

- DB write and schema migration.
- Raw data write (`raw_match_data`).
- Real scraper and browser automation.
- Large archive moves (delete/move/rename of historical files).
- Automatic next-task execution.
- Mixed governance + business-code PRs.
- Implementation PRs that substitute reports/manifests/tests for runtime behavior change.
- Consecutive governance-only PRs without explicit human confirmation.
- Formal model training.
- Data expansion / large-scale raw acquisition.

## Current source-of-truth docs

| Doc | Status |
|---|---|
| `docs/PROJECT_STATUS.md` | active (this file) |
| `docs/DATA_SOURCE_STRATEGY.md` | active (created alongside this file) |
| `AGENTS.md` | active —唯一 operational workflow authority |
| `docs/DOCUMENTATION_GOVERNANCE.md` | active |
| `docs/data/FOTMOB_CURRENT_STATE.md` | active — read for FotMob state |
| `docs/AGENT_WORKFLOW.md` | active |
| `docs/SC002_CLOSURE_PLAN.md` | active — SC-002 closure criteria / release gates / next tasks (current SC-002 two-layer status: `docs/data/FOTMOB_CURRENT_STATE.md`) |
| `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md` | active — static audit of all 43 skipped_complex scripts |
| `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md` | active — deep per-script verification of all 43 skipped_complex scripts |
| `docs/SC002_FINAL_CLOSURE_CHECK.md` | active — final per-criterion SC-002 closure verification |
| `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md` | active — shared module DB write boundary design |
| `docs/SC002_MANUAL_REVIEW_PHASE1.md` | active — manual review and reclassification of all needs_manual_review scripts |
| `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md` | active — Python/SQL/migration enforcement design |
| `docs/TESTING_GUIDE.md` | active — needs provenance review |
| `docs/GITHUB_ACTIONS_AUDIT_REPORT.md` | historical/superseded — current CI is `production-gate.yml` plus the GitHub ruleset/API |

## Current technical debt posture

- `docs/_reports/` contains 434 historical report files as of the
  authoritative workflow enforcement dry-run.
- `docs/_manifests/` contains 171 historical manifest files.
- These are archived evidence; they should not be read as current truth.
- Bulk archive moves are planned but not yet executed.
- `GITHUB_ACTIONS_AUDIT_REPORT.md` is now explicitly marked historical and
  superseded; it must not be used as current CI evidence.
- `TESTING_GUIDE.md` remains a separate provenance-review candidate and is not
  a workflow authority.
- Technical debt remains high enough to block data expansion and formal
  training. Current P0 debt includes DB write safety, cutoff strategy, training
  eligibility, and schema/init alignment.

## Current training and expansion posture

- Minimal training loop: connected for smoke-level validation only.
- Formal training: blocked.
- Formal cohort candidates / smoke-level candidates: 58.
- Formal candidates with odds: 0.
- Formal training must not start until eligibility, odds, cutoff-time policy,
  and DB write safety blockers are resolved.
- Data expansion: blocked by P0 technical debt and raw/write governance.
- DB write safety: blocked / partial phase1+phase2+phase3+phase4+phase5+phase6 guards added. The P0 DB
  write safety dry-run found 122 production DB-write risk files, including 66 P0
  files and 110 files with no safety gate. Phase1+Phase2+Phase3+Phase4+Phase5+Phase7 = 43 scripts/ops
  now guarded (Phase1+Phase2+Phase3+Phase4+Phase5+Phase7 = 43/66). A static enforcement dry-run scanner
  has been added to audit remaining coverage. SC-002 two-layer state:
  `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
  `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`. Remaining scripts need
  Phase8+ or static enforcement.
- Authoritative document backflow: fix phase1 starts enforcement through the PR
  template, AI Workflow Gate, Documentation Governance, Codex Workflow, and this
  current-state update.

## Recent dry-run conclusions now reflected here

| Dry-run | Current conclusion |
|---|---|
| `formal_training_cohort_inventory_dry_run` | Formal training remains blocked; only 58 smoke-level candidates were found and formal candidates with odds = 0. |
| `technical_debt_workflow_audit_dry_run` | P0 technical debt blocks data expansion and formal training; priority debt is DB write safety, cutoff strategy, training eligibility, and schema/init alignment. |
| `p0_db_write_safety_gate_dry_run` | DB write safety remains blocked; 122 production DB-write risk files were found, P0 = 66, 110 lack gates. SC-002 was unfixed at dry-run time (two-layer state now: `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`; `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`). |
| `authoritative_workflow_enforcement_dry_run` | The project already has authoritative docs, but `_reports` has overgrown and AI agents were not forced to maintain current-state docs. |

## Current FotMob status

- The frozen 888 replay packaging bridge is implemented in PR #1888: it
  reuses verified packages, wraps legitimate historical-reuse loose pairs, and
  emits the contract-valid staging source index offline. Technical Stage A
  evidence is complete, while PR CI, independent STRICT review, and merge
  closure remain pending.
- Production FotMob acquisition is `Not yet established`; see
  `docs/data/FOTMOB_CURRENT_STATE.md` for the authoritative state.
- The current read-only inventory records 58 retained `fotmob_live_v1` rows and
  76 total `raw_match_data` rows, all FK-linked to `matches`; it is not a 58/58
  full-audit assertion.
- The historical #1487 milestone audited four rows only: 4/4 parseable,
  SHA-valid and inner-`matchId` valid, with zero errors and warnings.
- Exact writer/run provenance for all 58 rows is not proven. Legacy acquisition
  scripts are historical evidence only and must not become canonical writers or
  new dependencies.
- No NEW network acquisition beyond the frozen 888 population, database write,
  browser automation, parser implementation, migration, training or prediction
  is authorized.
- **PR #1816 (bounded auditable FotMob detail capture pipeline) and PR #1817
  (offline detail staging converter/validator) are MERGED**: PR #1816 squash
  merge commit `b6f9f385124eab7476157777517fcd5bf01a93ab` (2026-08-04); PR #1817
  squash merge commit `fd60117d283a2af9e103990f733e436fda53b100` (2026-08-06),
  post-merge main Production Gate run 31075669344 success. Current main =
  `d65ec1b318309ddafc5a91bc1475f3e5a286d49c`. The chain available on main is
  PLAN → PREFLIGHT → bounded CAPTURE → REPLAY → verified archive/receipt →
  offline staging conversion → append-only retention → full validator.
  **GDI1C FotMob 888 raw acquisition = COMPLETE (2026-08-10/11)**: 14 formal
  batches / 812 unique targets / 888 frozen population (snapshot
  `206c1f04…`; see `docs/data/FOTMOB_CURRENT_STATE.md` closeout block);
  ACQUISITION_NETWORK_PHASE=CLOSED. No business database write, migration,
  canonical linkage write, training, backtest or prediction has occurred.
  The former single-match real FotMob detail trial recommendation is
  **superseded by the completed 888 acquisition**; the next recommended phase
  is GOLDEN_DATASET_CANONICAL_MULTI_SOURCE_ASSEMBLY (offline readiness/design
  only, not started; do not start automatically).
- The completed M3 offline cross-source audit derived its bounded population
  from actual offline Football-Data candidates under the Premier League
  2022/2023–2024/2025 identity contract, not the independent Ligue 1 FotMob
  mapping-target chronology. Its 888 exact matches and four isolated kickoff
  conflicts support the completed canonical-inventory write design review and
  only a separately authorized writer implementation review next; no legacy
  writer restart or raw-write expansion is recommended.
- **FotMob detail staging (offline) implemented and tested**: the offline
  converter/validator (`make data-fotmob-detail-staging-{help,receipt,build,validate}`
  over `scripts/ops/fotmob_detail_staging.js` +
  `src/infrastructure/fotmob/FotMobDetailStaging{Contract,Converter,Retention}.js`
  + `FotMobDetailStagingSourceVerification.js`)
  stages archived capture payload+manifest pairs into immutable
  `fotmob-detail-staging-artifact/v1` snapshots with an append-only file store
  (no database, no migration). Current test baseline: 340 staging
  unit tests green (122 retention fault-injection/tamper [incl. 3 R18-P2-1
  short-write injections (a/b/c) + 1 R19-P2-1 lockCreated regression + 2
  R20-P1-1 stale-lock fail-closed regressions + 3 R20-P2-1 final-artifact
  gate regressions; the former P1-4 stale auto-recovery test was reworked
  into the R20-P1-1 fail-closed regressions] + 82 source verification [75 + 4 R17-P2-1
  PAX size-override (a/b/c/d) + 3 R17-P2-1 PAX merge-semantics (e/f/g)] +
  89 contract [54 declared + 16 loop-generated per-field
  conflict tests + 3 R6-P1-2 identity-semantics + 3 R7-P3-2 id-length + 1
  R8-P2-1 strict array plainness + 3 R12-P3-1 cycle/depth guards + 3
  R13-P2-3 validator depth gate + 1 R13-P3-2 proxy array refusal + 1
  R14-P3-1 symbol own key refusal + 4 R15-P2-1 __proto__ own-key
  regressions (a/b/c/d)] + 17
  converter + 30 CLI (25 + 4 R20-P2-2 --limits-file regressions + 1
  R21-P3-2 frozen-cap regression in the dedicated
  fotmob_detail_staging_cli_limits.test.js);
  runtime counts = node --test
  # pass), incl. direct reuse of the pipeline capture hashing, determinism,
  idempotency, optional-section re-signed acceptance, atomicity, path safety,
  CLI/Make; 395 affected legacy tests green; ESLint/`git diff --check` clean;
  16 archived matches staged twice + validated twice with byte-identical
  artifacts and null canonical_match_id (derived outputs removed). Marker
  events (parser-injected AddedTime/Half minute markers, no id by design)
  recorded as a legal variant. Zero network, zero database, zero capture:
  no new real FotMob request and no real payload/manifest/artifact committed.
  Per-round Codex remediation timeline (R13–R21, counts 297→340) with
  per-finding mappings, regression evidence and Production Gate rows:
  docs/data/FOTMOB_CURRENT_STATE.md (authoritative current-state document;
  this paragraph's remediation narrative is a historical baseline).

- **FotMob detail staging (offline) PR #1817 blocker remediation (PR #1817
  MERGED 2026-08-06, squash merge commit
  `fd60117d283a2af9e103990f733e436fda53b100`; post-merge main Production Gate
  run 31075669344 success; the narrative below is the pre-merge remediation
  record)**: all 8 independent
  review findings fixed offline — F1 logical commit-marker atomic
  commit/rollback (marker written last, bound to file list + sha256 chain,
  rollback removes only this attempt's files, residue scan fail-closed);
  F2 REPEAT_EQUIVALENT rebuilds the artifact with recomputed hashes (old
  artifacts byte-untouched); F3 verified package receipts (real archive
  SHA-256 + safe pure-Node tar reader, every entry bound to one package);
  F4 symlink-ancestor + input/output non-overlap checks on all input types;
  F5 full A–E validator (38 checks, unconditional, 13 tamper tests);
  F6 LAYER_A observation_id/generated_at recomputation + LAYER_B
  artifact_integrity_sha256 (7 tamper tests); F7 SC-002 status correction
  (ENFORCEMENT_INFRASTRUCTURE=COMPLETE / STAGING_PRODUCTION_ROLE_DEPLOYMENT=
  PENDING / PR1817_CHANGES_SC002=NO); F8 Claude post-remediation self-review
  P0/P1/P2 = 0 with EXTERNAL_IMPLEMENTATION_ACCEPTANCE=PENDING and
  READY_TO_MERGE=NO. Codex closed-loop round (independent review 4863122944,
  13 findings): P0-1 live archive↔receipt re-verification with inventory
  hash; P0-2 REPEAT_EQUIVALENT final-classification write-back + three-way
  validator cross-checks; P1-1 two-level tar member-name validation; P1-2
  ACTUAL 16-field double-binding matrix; P1-3 receipt path through the
  unified input gate; P1-4 TOCTOU mitigation (no-follow fd reads, controlled
  private dirs, exclusive store lock, honest threat model); P1-5 anchored
  validation modes; P2-1 strict tar parsing (global PAX rejected); P2-2
  required three-source file hashes; P2-3 RFC 4122 UUIDv5 + byte-exact
  timestamps; P2-4 structured garbage fail-closed; P2-5 container-first make
  targets; P3-1 docs/PR-body rewrite. 297 staging tests (111 retention
  fault-injection/tamper + 65 source verification + 77 contract [54 declared
  + 16 loop-generated per-field conflict tests + 3 R6-P1-2 identity-semantics
  + 3 R7-P3-2 id-length + 1 R8-P2-1 strict array plainness] + 17 converter
  + 24 CLI; Codex round-8 (head 7bbbd7658) findings R8-P2-1 (non-plain arrays
  rejected — own toJSON/holes/symbols/extra keys/non-finite numbers, on both
  the direct accepted and REPEAT_EQUIVALENT rebuild paths) and R8-P2-2
  (unretainable LINKED_*/unknown terminal states refused in the pre-loop with
  ok-vs-classification consistency and pre-write summary self-validation)
  both remediated with zero-write regressions; Codex round-9 (head 8b1fc9034)
  findings R9-P2-1 (raw result contract gate before classification: boolean
  `ok`, ok:true declares ACCEPTED_NEW, ok:false cannot claim accepted — 3 new
  zero-write regressions + legal control) and R9-P3-1 (doc field-name
  accuracy: generated_at derives from manifest `response_received_at`, recorded
  as artifact `source_response_received_at`) both remediated); Codex round-10
  (head 4c1609945) findings R10-P2-1 (injection surface: quarantine_reason
  derived from the validated error_code — caller error text never persisted;
  rejected envelopes require a registry E### code; strict-ISO builtAt; every
  write-plan document isPlainJsonData; D-group recorded_at ISO + agreement —
  5 tests + legal control), R10-P2-2 (validator observations array/null-entry
  hardening → LEDGER_INVALID, no crash — 2 mutation tests), R10-P3-1
  (CAPABILITY_INDEX.md:70 + PR body field-name closure, counts 279),
  R10-P3-2 (tar dangling GNU L / PAX x at EOF → SAFETY_ERROR — 2 EOF tests)
  all remediated); Codex round-11 (head d9a47e1, 18 commits) findings
  R11-P2-1 (result-envelope injection closure for direct commitObservations
  callers — descriptor scan + scalar snapshot before any read (accessor/proxy
  → INPUT_ERROR), ok:true must not carry error_code, runId must be a plain
  identifier — 4 regressions + legal control, zero writes), R11-P2-2
  (validateStagingArtifact runs the prohibited raw content scan E013 on the
  whole artifact — 1 tamper regression), R11-P3-1 (D-group quarantine_reason
  must derive from the registry error_code whitelist AND agree with the
  ledger — 1 regression), R11-P3-2 (marker-tamper regression rehashes the
  marker after tampering — test-helper fix), R11-P3-3 (tar PAX multibyte
  UTF-8 path support — 1 regression); counts synced to 286, all remediated);
  Codex round-12 (head 1350ef4de) findings R12-P2-1 (artifact deep
  snapshot — descriptor-driven copy, util.types.isProxy refusal, no
  toJSON/JSON.stringify on the caller's object, cycles/depth → structured
  INPUT_ERROR — 2 regressions + legal control), R12-P2-2 (bounded archive
  inspection — pre-read compressed-size fstat, gunzipSync maxOutputLength,
  tar member/size/total caps, fail-closed SAFETY_ERROR — 4 regressions +
  legal control), R12-P3-1 (isPlainJsonData + content-scan cycle/depth/
  proxy guards — 3 regressions); counts synced to 297, all remediated);
  runtime counts = node --test # pass, the only gap vs static test()
  declarations is the loop-generated pair) + 347 legacy FotMob + 769 unit
  tests green; ESLint clean. 16-match offline revalidation on the fixed
  archives: RUN_1 16
  ACCEPTED_NEW, RUN_2 16 REPEAT_EXACT byte-identical, RUN_3 synthetic
  REPEAT_EQUIVALENT (SYNTHETIC_DERIVED_TEST=YES / REAL_NEW_OBSERVATION_CLAIM=NO);
  all stores validate PASS with zero residue. Zero network, zero database,
  zero capture, no migration; at submission time PR #1817 stayed Draft and
  unmerged, pending external implementation acceptance (merged 2026-08-06:
  squash commit `fd60117d2…`; post-merge main Production Gate 31075669344
  success).
- **FotMob 888 raw historical acquisition COMPLETE（2026-08-10/11，GDI1C）**：
  888/888 frozen canonical matches 的 FotMob raw payload 全部捕获并 durable 保留
  （formal batches B01–B14 共 812 场 + 历史 reuse 76 场）；MISSING=0 · EXTRA=0 ·
  AUTHORITATIVE_DUPLICATES=0 · FULL_RAW_RETENTION=YES · XG_FAMILY_RAW_VALIDITY=888/888。
  Frozen ledger accounting：UNIQUE_NETWORK_TARGETS=812 · SUCCESSFUL_HTTP_200=812 ·
  INITIAL_TIMEOUT_FAILURES=2 · RETRIES=2 · TOTAL_PHYSICAL_HTTP_ATTEMPTS=814。
  Asset snapshot（repo-external）：`FOTMOB_RAW_ASSET_SNAPSHOT_ID=206c1f04…`、
  `TARGET_POPULATION_HASH=133ff028…`、`ASSET_MANIFEST_SHA256=67bbb64f…`（JSONL），
  详见 `docs/data/FOTMOB_CURRENT_STATE.md` "FotMob 888 raw acquisition closeout"。
  **FOTMOB_RAW_ACQUISITION_STATUS=COMPLETE；GOLDEN_DATASET_COMPLETE=NO。**
  本轮未执行：live FotMob network / DB 读写 / 训练 / backtest / commit raw data。
  Redundant backup = PENDING_EXTERNAL_STORAGE（本机无独立存储；backup-ready
  snapshot 已生成，待 Owner 指定独立目标后复制验证）。

## Next recommended sequence

1. SC-002 closure plan phase0 completed. See `docs/data/FOTMOB_CURRENT_STATE.md`
   for the authoritative current SC-002 two-layer status; `docs/SC002_CLOSURE_PLAN.md`
   documents the closure criteria, release gates, and recommended next tasks.
2. Phase1-7 = 43 scripts/ops entrypoints now guarded (~65% of P0).
3. Static enforcement dry-run scanner deployed for coverage auditing.
4. Changed-files hard fail enabled for new/modified unguarded scripts/ops JS files.
5. **All JS-level guard work is now complete.**
6. **python_sql_migration_enforcement_design_phase1** — Python/SQL/migration enforcement
   design completed. See `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`.
7. **Python Phase2A static scanner + Phase2B SQL scanner completed.**
8. **Python Phase2C batch1 runtime guard completed (3 of 14 confirmed Python write paths).**
9. **Python Phase2C batch2 runtime guard completed (3 more of 14 confirmed Python write paths; 6 total guarded).**
10. **Python Phase2C batch3 runtime guard completed (3 more of 14 confirmed Python write paths; 9 total guarded).**
    - Batch3 guarded paths: odds_injector.py, collector_repository.py, streaming_db_writer.py
    - 5 later_needs_design identified (odds_integrity_guard.py, integrity_guard.py,
      sql_store.py, sync_db_pool.py, db_pool.py — unclear write boundaries)
    - 5 confirmed write paths remain pending. 8 indirect still pending. 5 manual review still pending.
11. **Python Confirmed Write Paths Design Phase2C Batch4 completed (this PR)** — static
    design analysis of all 5 remaining confirmed Python write paths. No runtime guard
    added (design/classification task only). Key outcomes:
    - **2 read_only_candidate:** odds_integrity_guard.py (SELECT-only, DELETE is print diagnostic),
      integrity_guard.py (SELECT COUNT/LEFT JOIN only, fix commands are shell)
    - **3 infrastructure_only_needs_caller_guard:** sql_store.py (SQL string constants, no execution),
      sync_db_pool.py (generic execute+commit, guard at callers), db_pool.py (generic async execute,
      guard at callers; 2 write callers already guarded in batch3)
    - See `docs/SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md` for full analysis.
    - **0 new runtime guards added. 0 files marked safe.**
    - **SC-002 two-layer state: `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
      `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`. Training / data
      expansion / real DB write remain blocked.**
12. **python_indirect_write_path_design_phase1 completed** — static design classification
   of all 8 indirect Python write paths. Key finding: 6 of 8 are actually DIRECT write paths
   (use OWN psycopg2, NOT via repository). 6 need guard, 2 are false positive or read-only.
   No runtime guards added. See `docs/SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md`.
   SC-002 two-layer state: `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
   `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`.
13. **runtime_db_role_permission_dev_poc completed** — 6-role dev-only POC in Docker environment.
14. SC-002 two-layer state: `SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE`;
    `SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING`.
15. Next recommended tasks (in priority order):
    - `python_indirect_write_path_guard_phase2` — implement runtime guard for 6 newly confirmed direct write paths
    - `python_manual_review_phase2D` — review 5 manual review candidates
    - `runtime_db_role_permission_review_phase1` — review DB-level role/permission model
    - `sc002_release_gate_checklist_phase1` — create detailed per-gate verification checklists
15. Keep formal training and data expansion blocked until DB write safety resolved
    and release gate criteria met.
16. Do not start model training, data expansion, raw-write work, scraper/browser
    automation automatically.
17. Do not start automatically. Recommended next task only after user confirmation.
# M3-D4D-B1 current state

Local-only persistent sandbox `fp_m3_persistent_sandbox` has sandbox-only V26.8/V26.9
migration-ledger and retained D4E synthetic evidence (1 run / 1 source / 6 accepted / 3 quarantine).
It is not dev/staging/production. D4E is complete; D4F-A read-only database
inventory and the later D4F offline cross-source audit are complete, while all
canonical/real-data writes remain blocked. See
`docs/M3_ODDS_STAGING_PERSISTENT_SANDBOX_RUNBOOK.md`.

REV2B closed the fresh disposable PostgreSQL 15 restore and complete role/grant permission
evidence. REV3 closed rollback/resume, checksum drift and advisory-lock concurrency. REV5 added
the exact reviewed sandbox-only SQL policy entries and negative escape-hatch tests; implementation
head `e7171da6ac049b0368ed1f5c2171e76a9e447819` passed Production Gate run `30066372663`.
**D4D is READY_FOR_D4E_AUTHORIZATION only:** it did not authorize persistent business writes,
D4E, or D4F.

## M3-D4E current implementation status

**M3-D4E COMPLETE — deterministic synthetic controlled write verified.** The fixed local-only
writer created exactly one completed run/source with 6 accepted and 3 quarantine records; stable
replay returned 0/0/9 with zero delta. Adapter-origin accepted and quarantine conflict scopes were
both verified as `PERSISTENCE_CONFLICT` with full rollback and zero delta. `canonical_match_id`
remains NULL for all six accepted records; no matches, canonical odds or training write occurred.
M3-D4E is implemented and audited through PR #1802; the authoritative PR merge state is recorded
in GitHub and Issue #1793. D4F-A database inventory and the offline
Football-Data-to-FotMob candidate audit are complete; real historical odds,
canonical integration and training remain unstarted and blocked.

## M3 canonical inventory write design review — 2026-07-29

**Design decision: READY_FOR_CANONICAL_INVENTORY_WRITER_IMPLEMENTATION_REVIEW.**
This is design readiness only, not database-write authorization.

- Canonical inventory and Football-Data linkage are separate objects and must
  remain separate transactions, roles, executors and future authorizations.
- The recommended future canonical population is 1,140 FotMob Premier League
  candidates (380 / 380 / 380), not 888 exact Football-Data links. Of the 252
  candidates without an exact link, four 15/30-minute conflicts are
  canonical-eligible but linkage-quarantine; the other 248 are
  canonical-only/unlinked.
- Later linkage is exactly 888 unique matches. The four remain no-link; no
  alias, fuzzy matching, home/away swap, timezone policy or tolerance change.
- Read-only PostgreSQL 15.17 evidence on the running development service
  confirmed football_db / claude_reader / BEGIN READ ONLY; role SELECT only,
  zero business schema/row change and zero target EPL rows.
- Current matches is not write-ready: only match_id is unique, external_id is
  not provider-scoped, business identity/import lineage are absent, and the
  generic writer updates on match_id conflict. New fail-closed writer and
  isolated schema/lineage migration plan are required; neither was implemented.
- Recovered FotMob v1 is reproducible identity evidence (business hash
  eff881…bc9d3f) but has no status field in 1,140 candidates. It must fail
  preflight rather than receive a guessed status; versioned status-complete
  hash-bound input is a separate precondition.
- The D4E sandbox remains 1 run / 1 source / 6 accepted / 3 quarantine and is
  not a canonical target. No canonical/linkage/staging write, migration,
  network/raw-payload action, training, backtest or prediction occurred.

## M3 canonical inventory writer implementation — 2026-07-29

**Implementation decision: READY_FOR_CANONICAL_INVENTORY_PROVENANCE_REVIEW.**
`REAL_WRITE_BLOCKED_PROVENANCE_POLICY` remains in force.

- A dedicated status-complete `candidate-match-identity/v2` contract retains
  the provider status separately, requires the exact versioned
  `fotmob-status-to-matches-status/v1` mapping and persists both it and the
  derived application status in immutable lineage; unknown semantic fields and
  unmapped provider statuses fail closed. Its v1 identity-projection binding,
  fresh hash-bound Ed25519 runtime authorization
  from a trusted authority and provenance receipt validator are implemented.
  The persisted receipt hash covers the complete signed receipt. Direct CLI
  execution is disabled; only the fixed synthetic disposable proof can write,
  through `make data-m3-canonical-inventory-disposable-proof`. The wrapper and
  launcher independently require separate exact schema and proof
  authorizations, and V26.10 runs only through the disposable-only
  `data-schema-m3-canonical-inventory-disposable-*` gate; the launcher also
  requires a clean checked-out code revision before Compose can start. Real
  inputs fail closed when provenance is absent.
- Additive V26.10 implements provider-scoped FotMob identity, fixture conflict
  protection, immutable artifact/import-run/lineage tables, a target-local
  service-identity plus PostgreSQL database-OID and owner-provisioned instance
  nonce binding, and the restricted canonical lock function. The signed runtime
  receipt must match the binding read back from the target database; restore
  rebinding rotates the nonce so a similarly named/schema-compatible clone
  fails closed. It was executed only on a task-specific PostgreSQL 15 tmpfs
  database, never on development, persistent M3 sandbox, staging or production.
- The independent insert-only writer and default-no-write operator proved a
  synthetic 1,140-candidate master (380 / 380 / 380), exact replay zero delta,
  a staged 1-row then overlapping 10-row canary under one parent master before
  the full-master lineage transition, conflict rollback, serializable lock
  contention, least-privilege denial and backup/restore.
  Before any transaction, the writer verifies the V26.10 checksum baseline,
  exact required lock-function ACLs, no writer role inheritance, no schema
  CREATE/TEMP and no UPDATE/DELETE/TRUNCATE table privilege. It also verifies
  every inventory CHECK constraint as an exact normalized expression set
  (artifact kind/parent, competition, status-mapping versions, binding key,
  hash formats, byte size and candidate count) and proves the instance-nonce
  uniqueness structurally (a real UNIQUE constraint backed by a valid, ready,
  non-partial unique index); weakened, widened, narrowed, dropped or duplicated
  definitions fail closed. The schema carries no UUID-generating defaults, so
  the writer role has no hidden function EXECUTE dependency. A full master also
  verifies that the in-scope canonical target is exactly its authorized
  1,140-candidate population before commit; an extra pre-existing in-scope row
  rolls back. The labelled proof containers, network and volume were cleaned up.
- The final proof ran at head `26c8ecf76878ec4442411c0c54c236d1db09104b` with
  the hardened baseline: migration lifecycle, 1,140 master, exact replay,
  same-parent canary rollout, conflict and committed schema-drift rollbacks,
  concurrency, exclusive-writer boundary and fresh-instance restore all passed;
  disposable containers, networks and volumes were verified removed.
- No real v2 artifact, FotMob request, canonical persistent write, linkage,
  odds staging/import, raw payload activity, training, backtest or prediction
  occurred. The 888 exact links, four kickoff quarantines and 248
  canonical-only candidates remain separate future stages.

The next separately authorized task is a provenance review for a real
status-complete FotMob artifact. It does not authorize provider acquisition or
any persistent canonical, linkage or odds write.
