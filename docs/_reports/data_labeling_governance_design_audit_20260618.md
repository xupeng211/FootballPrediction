# Data Labeling Governance Design Audit - 2026-06-18
- lifecycle: phase-artifact
- scope: read-only design audit only

## Nature / 边界
这是只读设计审计，不是 schema 变更。
- 没有 `--allow-write`
- 没有真实写 DB / migration / schema 变更
- 没有改业务代码 / 采集器 / parser / 训练 / 预测
- 没有 live fetch / browser / raw payload output
- 没有写 `raw_match_data`
- 没有处理 2 条 no-raw excluded
- 没有开始下一任务

## Evidence / 依据
- 迁移：`database/migrations/V12.2__add_matches_pipeline_status.sql`、`V12.3__expand_matches_pipeline_status_for_recon.sql`、`V6.6__hardened_l2_raw_storage.sql`
- 代码：`scripts/ops/l2_reconciliation_preview.js`、`scripts/ops/l2_guarded_reconciliation_write.js`、`src/infrastructure/services/FixtureRepository.js`、`src/infrastructure/harvesters/components/Persistence.js`、`src/infrastructure/services/RawMatchDataVersionSelector.js`
- SELECT-only：`matches` / `raw_match_data` 列、约束、分布、两条 excluded 明细

## Current State / 现状
- 当前 FotMob Ligue 1 2025/2026 guarded reconciliation 已完成：`58/58 harvested`
- 当前 `candidate_total = 0`
- 当前 `excluded_no_raw_count = 2`
- `matches.pipeline_status` 分布：`harvested=58`、`pending=2`
- `raw_match_data.data_version` 分布：`fotmob_live_v1=58`、`fotmob_html_hyd_v1=8`、`fotmob_pageprops_v2=8`、`PHASE4.23=1`、`PHASE4.43_SYNTHETIC=1`

## 审计回答
1. `matches` 里能表达流程状态的字段是 `pipeline_status`；`status/is_finished` 只表达比赛业务态，`updated_at` 只表达更新时间，`data_source/data_version` 只提供部分来源线索。
2. `pipeline_status` 当前允许值只有：`pending`、`processing`、`harvested`、`failed`、`skipped`、`RECON_LINKED`、`RECON_MISMATCH`。
3. 当前没有 `reason/error_reason/status_reason/metadata/notes` 专用列；状态能落，原因不能结构化落。
4. `raw_match_data` 当前通过 `data_version`、`collected_at`、`data_hash`、`external_id` 记录证据；没有独立 `data_source/source_type/evidence_level` 列。
5. `matches.data_source` 当前库内实际值：`fotmob` x50、`FotMob` x8、`manual_html_seed` x1、`local_finished_csv` x1；已经存在大小写与语义漂移。
6. `matches.data_version` 当前值：`V25.1` x58、`PHASE4.13` x1、`PHASE4.39` x1。`raw_match_data.data_version` 当前值：`fotmob_live_v1` x58、`fotmob_html_hyd_v1` x8、`fotmob_pageprops_v2` x8、`PHASE4.23` x1、`PHASE4.43_SYNTHETIC` x1。
7. synthetic / manual seed / local csv / real FotMob fetch 现在能“部分区分”，但靠组合解释，不是统一标签模型：`manual_html_seed + PHASE4.13 + PHASE4.23`、`local_finished_csv + PHASE4.39 + PHASE4.43_SYNTHETIC`、`fotmob/FotMob + fotmob_live_v1`。
8. 自动写状态方面：`pending` 由 DB 默认值写入；`harvested` 会被 `l2_guarded_reconciliation_write.js`、legacy `MarathonService`、`backfill_historical_raw_match_data.js`、`Persistence._syncMatchPipelineState()` 写入；`failed` 会被 recon/canonical janitor 路径写入；未看到当前主线对 `matches.pipeline_status='processing'` 或 `'skipped'` 的实际写入。
9. 当前代码不能自动持久化判断 `production_scope`、`training_eligible`、`reconciliation_eligible`；只有 ad hoc eligibility 规则。guarded reconciliation 当前靠查询时临时判断：`pipeline_status='pending'`、`status='finished'`、`raw_match_data.data_version='fotmob_live_v1'`、`raw_row_count=1`、`has_raw_data=true`、`has_data_hash=true`、`external_id` 不冲突。
10. 现有 guarded reconciliation 只认 `fotmob_live_v1`，因为 `l2_reconciliation_preview.js` 与 `l2_guarded_reconciliation_write.js` 都把 `DATA_VERSION` 硬编码为 `fotmob_live_v1`，SQL 也显式 `WHERE r.data_version = 'fotmob_live_v1'`。它是当前 retained live FotMob raw workflow 的单版本规则，不是通用证据模型。
11. 要避免 `pending` 变垃圾桶，最小原则是：`pending` 只留“仍可被当前授权主线消费”的目标；不可消费但仍等待证据的目标用 `needs_new_evidence` 或至少 `pending + reason`；明知不应进入当前主线的目标用 `skipped` 或 eligibility=false；`pending` 必须配结构化原因。

## Minimal Design / 最小变更建议
A. 流程状态标签：保留 `pending / processing / harvested / failed / skipped`；`needs_new_evidence` 当前不支持直接使用，因为现有 `matches_pipeline_status_valid` 不包含它，相关代码也未按它实现；若要启用，必须先做 schema + code 设计决策。

B. 数据身份证明：未来只在 `matches` 侧补最小治理标签，不改本次任何数据。建议新增 `source_type`、`evidence_level`、`is_production_scope`、`is_reconciliation_eligible`、`is_training_eligible`、`pipeline_status_reason` 或 `status_reason`。现有可继续复用的字段是 `league_name`、`season`、`data_source`、`data_version`；`league_id` 当前可由 `match_id` 前缀还原，但长期更适合显式列。

C. 入库自动打标规则：real FotMob fetch -> `source_type=fotmob_live_fetch` + `evidence_level=strong`；synthetic -> `source_type=synthetic` + `is_reconciliation_eligible=false`；manual seed -> `source_type=manual_seed` + `evidence_level=weak`；local csv -> `source_type=local_csv` + `evidence_level=weak/medium`；no raw -> `is_reconciliation_eligible=false`；non-target league -> `is_production_scope=false` by default。

D. 两条 no-raw excluded 的建议：`140_20252026_4837496` 保持 `pending`，原因应是 `scheduled + no fotmob_live_v1 raw`；`47_20242025_900002` 建议未来改成 `needs_new_evidence` 或 `skipped`，但本任务不执行。

## Design Judgment / 设计判断
- 当前最小缺口不是 `raw_match_data` 结构；它已经有 `data_version/collected_at/data_hash`
- 当前最小缺口是 `matches` 缺统一治理标签与结构化原因
- 因此最小变更应优先是“补标签设计”，不是重做 raw 表

## Next Step / 下一步
下一步需要用户确认后，才能进入 schema / migration / backfill 设计或执行。
