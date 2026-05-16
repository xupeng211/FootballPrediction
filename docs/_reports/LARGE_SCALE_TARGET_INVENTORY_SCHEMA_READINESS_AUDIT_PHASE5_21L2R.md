# Large-Scale Target Inventory Schema-Readiness Audit - Phase 5.21L2R

## 1. Executive summary

Phase 5.21L2Q 已经规划了 large-scale `fotmob_pageprops_v2` acquisition strategy。

本阶段继续保持 planning / audit only，重点不是采集，而是审计 future acquisition
candidate inventory 应如何表达，以及当前 `matches` / `raw_match_data` schema 是否已准备好支撑这件事。

本阶段明确不执行：

- 不采集
- 不触网
- 不写库
- 不做 schema migration
- 不实现 parser / features / training

目标是回答 future acquisition candidate 应如何表达，而不是现在就创建表或跑 preflight。

## 2. Current DB/schema baseline

只读确认当前 DB baseline：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Protected tables with existing rows:

- `bookmaker_odds_history=2`
- `predictions=2`

Current `raw_match_data` data_version distribution:

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |
| `fotmob_pageprops_v2` |    8 |

`matches` schema summary:

- primary key: `match_id`
- canonical identity fields present:
    - `match_id`
    - `external_id`
    - `league_name`
    - `season`
    - `home_team`
    - `away_team`
    - `match_date`
    - `status`
- workflow-ish field already exists:
    - `pipeline_status`
- notable limitations:
    - no dedicated `league_id`
    - no acquisition `batch_id`
    - no preflight / baseline-hash / write-status contract

`raw_match_data` schema summary:

- primary key: `id`
- unique key: `UNIQUE(match_id, data_version)`
- foreign key:
    - `match_id -> matches(match_id)`
- versioned raw fields present:
    - `match_id`
    - `external_id`
    - `raw_data`
    - `collected_at`
    - `data_version`
    - `data_hash`

Current version coexistence state:

- 8 seeded Ligue 1 matches each have:
    - `fotmob_html_hyd_v1`
    - `fotmob_pageprops_v2`
- 2 non-canonical legacy rows remain:
    - `PHASE4.23`
    - `PHASE4.43_SYNTHETIC`

## 3. Schema-readiness findings

Core judgment:

- `matches` 表适合 canonical match identity。
- `matches` 表不适合 acquisition workflow queue。
- `raw_match_data` 适合 versioned raw store。
- future acquisition workflow state 应独立表达。
- acquisition workflow flags 不应直接混入 `raw_match_data`。

Why `matches` is suitable for canonical identity:

- `match_id` 主键稳定
- `external_id` 已存在
- `league_name` / `season` / `home_team` / `away_team` / `match_date` / `status`
  足以表达当前 canonical match identity baseline

Why `matches` is not suitable as workflow queue:

- 缺少 `batch_id`
- 缺少 `target_status`
- 缺少 `preflight_status`
- 缺少 `baseline_hash`
- 缺少 `write_status`
- 缺少 `failure_reason`
- 缺少 `expected_coverage_tier`
- 如果直接把这些 state 混进 `matches`，会把 canonical identity 和 workflow queue 搅在一起

Why `raw_match_data` should stay separate:

- 它的职责是 versioned raw storage
- 它不应承担 acquisition candidate lifecycle
- `baseline_hash` / `preflight_status` 不应在真正写入 raw 前混入 `raw_match_data`

Schema gaps and severities:

| gap                                            | severity                             | finding                                                                                    |
| ---------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------ |
| `kickoff_time / match_date` precision contract | `medium`                             | 当前只有 `match_date`，future inventory 需要显式定义 kickoff semantics                     |
| `league_id vs league_name`                     | `high`                               | 当前 `matches` 只有 `league_name`，没有 source-native `league_id`                          |
| source external_id mapping                     | `medium`                             | `external_id` 存在，但缺少更明确的 source/route-aware mapping contract                     |
| season normalization                           | `low`                                | 当前已有 season format check，但 future manifest 仍需显式沿用标准                          |
| status normalization                           | `medium`                             | 当前有 lowercase check，但未表达 cancelled/postponed/abandoned 的 workflow policy          |
| team identity normalization                    | `medium`                             | 现有 team name 足够显示，不足以表达 future cross-source normalized team identity           |
| `batch_id`                                     | `acceptable_for_short_term_manifest` | 短期可放 manifest，不适合现在混入 canonical table                                          |
| `target_status`                                | `acceptable_for_short_term_manifest` | 当前表中不存在，短期应在 manifest 中表达                                                   |
| `preflight_status`                             | `acceptable_for_short_term_manifest` | 当前表中不存在，短期应在 manifest 中表达                                                   |
| baseline hash storage                          | `high`                               | preflight baseline 不应 ad hoc 混入现有表，需 manifest 或 future acquisition-target schema |
| odds alignment metadata                        | `medium`                             | future odds join 需要 readiness metadata，但当前无独立字段表达                             |

## 4. Target inventory representation options

### A. Reuse matches only

- Pros:
    - 复用现有 canonical identity 表
    - 无需立刻引入新表
- Cons:
    - 把 workflow queue state 混入 canonical identity
    - 缺少 `batch_id` / `preflight_status` / `baseline_hash` / `write_status`
- Risk:
    - 高
- Migration need:
    - 大概率需要
- Recommended usage:
    - 只适合 identity lookup，不适合作为 acquisition workflow store

### B. Docs-only manifest

- Pros:
    - 不需要 migration
    - PR review 友好
    - 适合小批 planning
- Cons:
    - 状态机不强
    - 人工维护成本高
    - 不适合持续扩大规模
- Risk:
    - 中低，适合短期
- Migration need:
    - 无
- Recommended usage:
    - short-term planning / exact-scope batch proposal

### C. Source-controlled JSON/YAML manifest

- Pros:
    - 不需要 migration
    - 比 docs-only 更结构化
    - 更适合 deterministic batch generation
- Cons:
    - 状态更新会造成 manifest churn
    - 大规模长期运维会显得笨重
- Risk:
    - 中等
- Migration need:
    - 无
- Recommended usage:
    - short-term 和 early medium-term controlled batches

### D. Dedicated acquisition_targets / acquisition_batches table

- Pros:
    - canonical identity 与 workflow state 清晰分离
    - 支持显式 state machine / dedupe / audit
    - 长期最干净
- Cons:
    - 需要独立 schema planning 和 migration preflight
    - 本阶段不允许执行
- Risk:
    - 设计成本高，但长期 workflow 风险最低
- Migration need:
    - 有
- Recommended usage:
    - medium-term，等 target contract 稳定后再做

## 5. Recommended representation strategy

明确推荐：

- short term：
    - 使用 docs/source-controlled manifest 或 generated report 来表达 exact batch scope
- medium term：
    - 在独立 migration planning / preflight 后，引入 `acquisition_batches` +
      `acquisition_targets` schema

Boundary rules:

- `matches` remains canonical identity
- `raw_match_data` remains versioned raw store
- workflow flags do not belong in `raw_match_data`
- 本阶段不执行 migration
- 本阶段不创建 `acquisition_targets`

## 6. Proposed target inventory fields

未来 target inventory 建议字段：

- `target_id`
- `batch_id`
- `source`
- `route`
- `raw_data_version`
- `hash_strategy`
- `match_id`
- `external_id`
- `league_id / league_name`
- `season`
- `home_team`
- `away_team`
- `kickoff_time / match_date`
- `status`
- `target_status`
- `priority`
- `expected_coverage_tier`
- `existing_versions`
- `preflight_status`
- `baseline_hash`
- `last_preflight_at`
- `write_status`
- `write_attempt_count`
- `failure_reason`
- `source_fidelity_notes`
- `odds_alignment_ready`
- `created_at`
- `updated_at`

## 7. Target state machine

Recommended states:

- `planned`
- `inventory_validated`
- `existing_version_checked`
- `preflight_ready`
- `preflight_passed`
- `preflight_failed`
- `hash_baseline_ready`
- `write_authorized`
- `write_completed`
- `write_failed`
- `skipped`
- `blocked`

Hard gates:

- no write without `preflight_passed + hash_baseline_ready + explicit authorization`
- hash drift returns target to `preflight_failed` or `blocked`
- duplicate existing v2 moves to `skipped` / already-exists review
- `403/captcha` moves to `blocked`
- invalid hydration moves to `preflight_failed`
- cancelled/postponed handling depends on status policy and kickoff stability

## 8. Example manifest

```json
{
    "batch_id": "fotmob-pageprops-v2-ligue1-2025-2026-profile-001",
    "source": "fotmob",
    "route": "html_hydration",
    "raw_data_version": "fotmob_pageprops_v2",
    "hash_strategy": "stable_pageprops_payload_v1",
    "targets": [
        {
            "match_id": "53_20252026_4830746",
            "external_id": "4830746",
            "league_name": "Ligue 1",
            "season": "2025/2026",
            "home_team": "Angers",
            "away_team": "Strasbourg",
            "kickoff_time": "2026-05-10T19:00:00Z",
            "status": "finished",
            "target_status": "planned",
            "priority": 1,
            "expected_coverage_tier": "unknown_until_profiled"
        }
    ]
}
```

## 9. Readiness gates

Future real acquisition 前必须满足：

- inventory reviewed
- duplicate detection passed
- match identity stable
- kickoff_time present
- external_id valid
- no existing target version
- source route fixed
- raw_data_version fixed
- no-write preflight passed
- baseline hashes captured
- explicit write authorization

## 10. Odds alignment readiness

本阶段不做 odds ingestion。

但 target inventory 必须保留 future odds join 所需 identity metadata：

- `match_id`
- `kickoff_time`
- `external_id`
- `league_id / league_name`
- `season`
- `home_team`
- `away_team`

Boundary:

- odds raw 不进入 `raw_match_data`
- target inventory 不存赔率值
- `odds_alignment_ready` 只是 metadata readiness flag，不是 odds payload

## 11. Verification results

本阶段验证项：

- new schema-readiness test:
    - `tests/unit/large_scale_target_inventory_schema_readiness_audit.test.js`
- large-scale acquisition strategy tests:
    - `tests/unit/large_scale_pageprops_v2_acquisition_strategy_plan.test.js`
- parser boundary planning tests:
    - `tests/unit/pageprops_v2_parser_boundary_leakage_plan.test.js`
- raw completeness tests:
    - `tests/unit/pageprops_v2_raw_completeness_audit.test.js`
- canonical read tests:
    - `tests/unit/all_seeded_pageprops_v2_canonical_read_verification.test.js`
    - `tests/unit/RawMatchDataVersionSelector.test.js`
- Makefile audit target:
    - `make data-large-scale-target-inventory-schema-readiness-audit ...`
- full test gates:
    - `npm test`
    - `npm run test:coverage`
- quality:
    - `eslint`
    - `prettier --check`
    - `git diff --check`
- safety:
    - DB row counts unchanged
    - `tests/fixtures/l1-config-*` residue absent
    - `docs/_staging_preview` absent
    - PR CI green before merge
    - main push CI green after merge

## 12. Recommended next phases

### Phase 5.21L2S

`single-league small-batch target manifest planning`

要求：

- no DB write
- no network
- no raw acquisition
- choose one league/season profile batch
- generate docs-only target manifest proposal
- still no FotMob access

### Phase 5.21L2T

`single-league small-batch no-write preflight`

要求：

- only after explicit network authorization
- no DB write
- limited 20-50 targets
- capture baseline hashes

### Phase 5.22L2A

`odds raw schema / source / leakage policy planning and existing module audit`

要求：

- no odds access
- no DB write
- inspect existing odds modules only

## 13. Explicit non-execution

本阶段明确未执行：

- no DB writes
- no `raw_match_data` writes
- no `bookmaker_odds_history` writes
- no network / FotMob access
- no odds access
- no raw acquisition
- no schema migration
- no `matches` writes
- no parser implementation
- no feature extraction
- no `l3_features` write
- no `match_features_training` write
- no training / prediction
- no browser / proxy
- no full raw_data print / save
- no full pageProps print / save
- no file deletion
