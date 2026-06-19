# Matches Labeling Schema Design Proposal - 2026-06-19
- lifecycle: phase-artifact
- scope: schema/migration design only

## Nature / 边界
这是 schema/migration 设计方案，不是实现。
- 没有新增 migration
- 没有改 schema
- 没有真实写 DB
- 没有 backfill
- 没有处理 no-raw excluded
- 没有 live fetch
- 没有 raw payload output

## Current State / 当前状态
- 当前 FotMob Ligue 1 2025/2026 guarded reconciliation 已完成：`58/58 harvested`
- 当前 `candidate_total = 0`
- 当前 `excluded_no_raw_count = 2`
- `matches.pipeline_status` 当前合法值：`pending / processing / harvested / failed / skipped / RECON_LINKED / RECON_MISMATCH`
- `matches.data_source` 当前已漂移：`fotmob` x50、`FotMob` x8、`manual_html_seed` x1、`local_finished_csv` x1
- `raw_match_data.data_version` 当前分布：`fotmob_live_v1` x58、`fotmob_html_hyd_v1` x8、`fotmob_pageprops_v2` x8、`PHASE4.23` x1、`PHASE4.43_SYNTHETIC` x1

## Evidence / 依据
- migration: `database/migrations/V6.5__hardened_matches_schema.sql`, `V12.2__add_matches_pipeline_status.sql`, `V12.3__expand_matches_pipeline_status_for_recon.sql`, `V6.6__hardened_l2_raw_storage.sql`
- code: `scripts/ops/l2_reconciliation_preview.js`, `scripts/ops/l2_guarded_reconciliation_write.js`, `scripts/ops/controlled_matches_identity_seed_execute.js`, `src/infrastructure/services/FixtureRepository.js`, `src/infrastructure/services/RawMatchDataVersionSelector.js`, `src/infrastructure/harvesters/components/Persistence.js`
- prior reports: `docs/_reports/data_labeling_governance_design_audit_20260618.md`, `docs/_reports/fotmob_l2_no_raw_excluded_investigation_20260618.md`

## Minimal Field Proposal / 最小字段方案

| field | purpose | type | target steady-state | phase-1 safe migration | check |
|---|---|---|---|---|---|
| `source_type` | 记录 `matches` 当前 authoritative provenance class，不追求全量历史，只表达“这条 row 现在主要依据什么来源成立” | `VARCHAR(32)` | `NOT NULL DEFAULT 'unknown'` | 先 `NULLABLE`、先不设 default | `NULL OR IN ('fotmob_live_fetch','fotmob_html_hydration','fotmob_pageprops','manual_seed','local_csv','synthetic','unknown')` |
| `evidence_level` | 记录当前证据强度，区分真实 FotMob、弱人工、synthetic、缺失 | `VARCHAR(24)` | `NOT NULL DEFAULT 'missing'` | 先 `NULLABLE`、先不设 default | `NULL OR IN ('strong','medium','weak','synthetic_invalid','missing')` |
| `is_production_scope` | 明确是否属于当前生产范围，避免仅靠 league/season/脚本隐式判断 | `BOOLEAN` | `NOT NULL DEFAULT false` | 先 `NULLABLE`、先不设 default | 不需要额外 CHECK |
| `is_reconciliation_eligible` | 明确是否允许进入当前 reconciliation，而不是只靠 ad hoc SQL 规则 | `BOOLEAN` | `NOT NULL DEFAULT false` | 先 `NULLABLE`、先不设 default | 不需要额外 CHECK |
| `is_training_eligible` | 明确是否允许进入训练；在 cutoff/policy 未确认前默认 false | `BOOLEAN` | `NOT NULL DEFAULT false` | 先 `NULLABLE`、先不设 default | 不需要额外 CHECK |
| `pipeline_status_reason` | 为 `pending/skipped/failed` 等当前状态提供结构化原因；不替代 `pipeline_status` | `VARCHAR(64)` | `NULL DEFAULT NULL` | 直接 `NULLABLE` | 建议只做 `snake_case` 格式 CHECK，不做 closed enum，避免每加新 reason 都迁移 |

## Recommended Values / 建议值
- `source_type`: `fotmob_live_fetch`, `fotmob_html_hydration`, `fotmob_pageprops`, `manual_seed`, `local_csv`, `synthetic`, `unknown`
- `evidence_level`: `strong`, `medium`, `weak`, `synthetic_invalid`, `missing`
- `pipeline_status_reason` examples: `awaiting_match_completion`, `pending_without_fotmob_live_v1_raw`, `synthetic_raw_not_valid`, `non_production_league`, `external_id_unverified`, `no_fotmob_evidence`, `parser_failed`, `needs_new_evidence`

## Direct Answers / 必答项
1. 每个新增字段用途见上表；核心原则是把 provenance、evidence、scope、eligibility、reason 从 `pipeline_status` 里解耦。
2. 类型建议：`source_type/evidence_level/pipeline_status_reason` 用 `VARCHAR`，3 个 eligibility/scope 用 `BOOLEAN`。
3. `source_type/evidence_level/is_production_scope/is_reconciliation_eligible/is_training_eligible` 最终应 `NOT NULL`；`pipeline_status_reason` 应保持 `NULLABLE`。
4. 最终 default 建议：`unknown / missing / false / false / false / NULL`；但 phase-1 safe migration 不建议立刻加 default。
5. `source_type`、`evidence_level` 建议有限值 CHECK；`pipeline_status_reason` 只建议 `snake_case` 格式 CHECK；布尔字段无需 CHECK。
6. 应先 `NULLABLE` 再 backfill，再切 `NOT NULL`。原因：当前存在多条 `matches` writer，直接强约束会扩大改动面。
7. 这些字段不应改变现有 `pipeline_status` 主状态机；`pipeline_status` 继续表达流程位置，新字段表达治理标签与原因。
8. **不建议在第一版最小方案里新增 `pipeline_status='needs_new_evidence'`。**
9. 如果未来一定要新增 `needs_new_evidence`，至少要改：DB constraint；`scripts/ops/controlled_matches_identity_seed_execute.js` 与 `large_scale_target_inventory_schema_readiness_audit.js` 的 allowed-values 解析；`scripts/ops/l2_reconciliation_preview.js`、`l2_guarded_reconciliation_write.js`、`l2_pending_target_selection_dry_run.js`、`src/infrastructure/harvesters/ProductionHarvester.js` 的 pending 选择逻辑；`src/infrastructure/services/FixtureRepository.js`、`src/infrastructure/recon/services/ReconTaskPlannerImpl.js`、`src/infrastructure/services/recon/MatchIdentityResolver.js` 的状态消费逻辑；相关 tests。
10. 若暂时不加 `needs_new_evidence`，用 `pipeline_status + pipeline_status_reason + eligibility booleans` 表达：例如 `pending + needs_new_evidence + recon=false + training=false`，或 `skipped + synthetic_raw_not_valid + recon=false + training=false`。
11. **先只加 `matches`，不先加 `raw_match_data`。** 原因：`raw_match_data` 已有 `data_version/data_hash/collected_at`，而生产范围、recon/training eligibility、pending 原因都是 match-level 决策；先在 raw 表加同类标签会制造双真相源。
12. 最小安全 migration 方案：未来单独 migration PR 只做 additive `ALTER TABLE matches ADD COLUMN ...`；6 列全部先 `NULLABLE`；只加宽松 CHECK 与 column comments；不在同一 PR 做 backfill、不改 reader、不做 NOT NULL；后续再单独做 runtime writer PR 和 hardening PR。
13. 后续 backfill 分阶段：`Phase A` 先补 writer；`Phase B` 做 SELECT-only backfill dry-run 生成分类清单；`Phase C` 经授权后按显式规则批量回填；`Phase D` 回填完成后再上 default/NOT NULL/更严格约束，并把查询逐步切到新标签。

## Minimal Backfill Rules / 最小回填规则
- `fotmob_live_v1` real raw -> `source_type=fotmob_live_fetch`, `evidence_level=strong`
- only `fotmob_pageprops_v2` / `fotmob_html_hyd_v1` -> `source_type=fotmob_pageprops` / `fotmob_html_hydration`, `evidence_level=medium`
- `PHASE4.43_SYNTHETIC` -> `source_type=synthetic`, `evidence_level=synthetic_invalid`, `is_reconciliation_eligible=false`, `is_training_eligible=false`
- `manual_html_seed` / `local_finished_csv` without production-grade FotMob raw -> `evidence_level=weak`, `is_reconciliation_eligible=false`
- 非当前生产 league/season -> `is_production_scope=false`

## Future Guidance For The 2 No-Raw Excluded Rows / 未来建议
- `140_20252026_4837496`: 建议未来保持 `pending + pipeline_status_reason=awaiting_match_completion` 或 `pending_without_fotmob_live_v1_raw`；原因：`scheduled` + 无 `fotmob_live_v1` raw + 非当前 production league。
- `47_20242025_900002`: 建议未来改成 `skipped` 或 `pending + pipeline_status_reason=needs_new_evidence / synthetic_raw_not_valid`；原因：`finished` 但只有 `PHASE4.43_SYNTHETIC`，不是真实 FotMob 证据。

## Recommendation / 结论
- 最小 schema 重点应放在 `matches` 标签层，而不是继续扩张 `pipeline_status` 或先复制标签到 `raw_match_data`
- 第一版先不引入 `needs_new_evidence` 状态值；先用 `pipeline_status_reason + eligibility booleans` 落治理语义
- 下一步需要用户确认后，才能进入真正 migration PR
