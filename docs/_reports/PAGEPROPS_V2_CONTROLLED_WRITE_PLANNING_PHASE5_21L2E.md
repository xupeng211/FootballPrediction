# Phase 5.21L2E: pageProps v2 controlled write planning

## 1. Executive summary

Phase 5.21L2D 已完成 single-target pageProps v2 no-write preview，目标
`53_20252026_4830747` / `4830747` / Auxerre vs Nice 的
`fotmob_pageprops_v2` candidate 有效，并确认它比现有
`fotmob_html_hyd_v1` transformed payload 更完整：

- `stable_pageprops_hash`: `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc`
- v1 JSON bytes: `234856`
- v2 candidate JSON bytes: `321681`
- size ratio: `1.369695`
- v1 paths: `7220`
- v2 paths: `9678`
- v1 content paths: `6922`
- v2 content paths: `6922`
- v2-only paths: `2482`
- v1-only paths: `24`
- content diff paths: `0`

本阶段只规划 future controlled write。关键阻塞是 `raw_match_data`
当前 schema 的 identity / unique constraint 是否允许同一 `match_id`
保存多个 `data_version`。本阶段未触网、未写库、未执行 migration、未写
`raw_match_data`。

## 2. Current DB baseline

只读 baseline：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   10 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

当前 data_version 分布：

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |

目标 `external_id=4830747` 当前只有 1 条 raw row：

- `match_id`: `53_20252026_4830747`
- `data_version`: `fotmob_html_hyd_v1`
- `data_hash`: `8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25`

## 3. Schema findings

`raw_match_data` 当前 columns：

| column         | type / default                          | notes                                          |
| -------------- | --------------------------------------- | ---------------------------------------------- |
| `id`           | `bigint`                                | primary key                                    |
| `match_id`     | `varchar(50)`                           | not null, FK to `matches(match_id)`            |
| `external_id`  | `varchar(100)`                          | nullable                                       |
| `raw_data`     | `jsonb`                                 | not null                                       |
| `collected_at` | `timestamptz default CURRENT_TIMESTAMP` | not null by check                              |
| `data_version` | `varchar(20) default 'V26.1'`           | version marker                                 |
| `data_hash`    | `varchar(64)`                           | stable payload hash for current FotMob v1 rows |

Constraints：

- `raw_match_data_pkey`: `PRIMARY KEY (id)`
- `raw_match_data_match_id_key`: `UNIQUE (match_id)`
- `raw_match_data_match_id_fkey`: `FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE`
- `collected_at_not_null`: `CHECK (collected_at IS NOT NULL)`
- `match_id_format`: `CHECK ((match_id)::text ~ '^[0-9][0-9A-Za-z_/-]*$')`
- `raw_data_has_match_id`: `CHECK (raw_data ? 'matchId')`
- `raw_data_not_empty`: `CHECK (raw_data <> '{}'::jsonb)`

Indexes：

- `raw_match_data_pkey`: unique btree on `id`
- `raw_match_data_match_id_key`: unique btree on `match_id`
- `idx_raw_data_match_id`: btree on `match_id`
- `idx_raw_data_external_id`: btree on `external_id`
- `idx_raw_data_collected_at`: btree on `collected_at`
- `idx_raw_data_version_collected`: btree on `(data_version, collected_at DESC)`
- `idx_raw_data_gin`: GIN on `raw_data`

Schema conclusion：

- 当前存在 `UNIQUE(match_id)`。
- 当前不允许同一 `match_id` 保存多个 `data_version`。
- 当前没有 duplicate `match_id`。
- 当前 `4830747` 只有 `fotmob_html_hyd_v1` row。
- 若直接写入 `fotmob_pageprops_v2` additional row，当前 schema 会被
  `raw_match_data_match_id_key` 阻止。

## 4. Code impact findings

受影响的 write / ingest 路径：

- `scripts/ops/l2_raw_match_data_write.js`
    - controlled v1 writer 使用 plain `INSERT INTO raw_match_data`。
    - existing-row lookup 按 `match_id OR external_id` 查询，没有
      `data_version` filter。
- `scripts/ops/l2_remaining_raw_match_data_write.js`
    - remaining v1 writer 使用 plain `INSERT INTO raw_match_data`。
    - existing-row lookup 按 match/external ids 查询，没有 `data_version`
      filter。
- `scripts/ops/l2_raw_match_data_ingest_preflight.js`
    - existing raw row check 按 `match_id OR external_id` 查询，没有
      `data_version` filter。
- legacy/admin 路径仍有 `ON CONFLICT (match_id)`：
    - `src/infrastructure/harvesters/components/Persistence.js`
    - `src/infrastructure/harvesters/TitanSlimHarvester.js`
    - `src/infrastructure/services/MarathonService.js`
    - `scripts/ops/backfill_historical_raw_match_data.js`
    - `scripts/ops/seed_fotmob_sample.js`
    - `scripts/ops/bulk_import_matches.js`

可能假设一场比赛只有一条 raw row 的 read paths：

- `src/feature_engine/smelter/components/DataFetcher.js`
    - joins `raw_match_data r ON m.match_id = r.match_id` without
      `data_version` filter。
- `src/infrastructure/services/FixtureRepository.js`
    - reads `raw_match_data` by match-id patterns for league/team catalog
      context。
- `src/services/inference_service.py`
    - treats `raw_match_data` as match-level raw input source。
- `src/ml/dataset/dataset_generator.py`
    - reads `raw_match_data` without versioned raw selection semantics。
- 多个 ops/report scripts 使用 no-version `LEFT JOIN raw_match_data`，future
  reader audit 需要补 `data_version` filter 或 canonical selector。

Future compatibility impact：

- future v2 writer conflict target 应为 `(match_id, data_version)`。
- future preflight must query target version explicitly。
- parser/features/training 不得隐式读取任意 raw row，必须选择
  `data_version`。
- 建议新增 canonical/latest selector helper 或 view，例如默认优先
  `fotmob_pageprops_v2`，回退 `fotmob_html_hyd_v1`，并默认排除
  synthetic / unknown provenance。

## 5. Strategy comparison

### Option A: `UNIQUE(match_id, data_version)`

Pros：

- 最小 schema 改动。
- `raw_match_data` 继续作为 raw warehouse 主表。
- 同一 match 可保存 `fotmob_html_hyd_v1` 与 `fotmob_pageprops_v2`。
- 与当前 table / index / raw audit 语义最接近。

Cons：

- 需要 migration，不能在本阶段执行。
- 当前假设 `match_id` 唯一的 writers/readers 必须审计。
- Future upsert / lookup / report joins 需要使用 `data_version` 或 canonical
  selector。

Migration requirements：

- drop or replace current `raw_match_data_match_id_key` unique constraint。
- create versioned unique identity on `(match_id, data_version)`。
- verify existing rows have non-null / bounded `data_version`。
- verify no duplicate `(match_id, data_version)` before migration。

Rollback considerations：

- migration 前需要 backup/rollback plan。
- rollback 前必须确认没有任何 match 同时拥有多个 version，否则无法恢复
  `UNIQUE(match_id)`。

### Option B: new `raw_match_data_versions` table

Pros：

- 不立即改变 `raw_match_data` 当前 one-row-per-match 语义。
- version history 更显式。
- 可保留 `raw_match_data` 作为 current/canonical pointer。

Cons：

- schema 和 query routing 更复杂。
- writer、preflight、parser、reports 要同时理解两张表。
- future canonical/latest selector 更早成为必须。

Migration requirements：

- 新建版本表、FK、indexes、copy/backfill policy、write routing policy。
- 明确 `raw_match_data` 是否继续存 v1、latest pointer 或被只读冻结。

Rollback considerations：

- rollback 需删除/停用新表路径并处理已经写入的 v2 rows。
- 不适合在没有 versioned reader abstraction 前快速推进。

### Option C: `raw_match_data_v2` table

Pros：

- v2 isolation 清晰。
- 不修改 v1 table 的 unique constraint。

Cons：

- 长期复制 raw table 语义。
- parser/readers 需要在表层做 branching。
- 后续 v3/v4 会继续扩表，演进成本高。

### Option D: overwrite v1

明确不推荐：

- 会丢失已验证的 `fotmob_html_hyd_v1` provenance。
- 破坏 source-fidelity audit trail。
- 回滚依赖 backup，不符合当前安全演进方式。

## 6. Recommended strategy

推荐 Option A：将 `raw_match_data` 的版本共存身份规划为
`UNIQUE(match_id, data_version)`。

Recommended policy：

- 保留所有现有 `fotmob_html_hyd_v1` rows。
- `fotmob_pageprops_v2` 作为 additional version 写入，不覆盖 v1。
- Future v2 writer 使用 `data_version=fotmob_pageprops_v2`。
- Future v2 writer 使用 `data_hash=stable_pageprops_payload_v1`。
- Future upsert / conflict target 使用 `(match_id, data_version)`。
- Readers/parser/features/training 必须显式 filter `data_version` 或使用
  canonical selector/helper。
- Synthetic / unknown rows 默认不参与 FotMob v2 fidelity 判断。

这个方案比新版本表更适合当前阶段：它保持 raw warehouse 单表语义，schema
surface 最小，同时满足 v1/v2 coexistence。新版本表可以作为 fallback，但当前
没有足够证据说明需要承担额外 routing complexity。

## 7. Controlled write policy for future v2

Future v2 write must：

- 使用 pageProps candidate，不使用 transformed payload 作为 canonical raw。
- `data_version=fotmob_pageprops_v2`。
- `data_hash=stable_pageprops_payload_v1`。
- 不 rewrite / overwrite `fotmob_html_hyd_v1`。
- 首次写入只允许 single target `4830747`。
- write 前先做 no-write preflight，重新 recapture pageProps 并与 L2D preview
  hash baseline 对比。
- controlled write 必须单独授权、事务执行、写后验证 row count 和 target
  version coexistence。

## 8. Migration / rollback planning

本阶段不执行 migration。

下一阶段需要：

- 准备 exact constraint/index migration plan。
- 验证当前 `raw_match_data` row counts 和 `(match_id, data_version)` duplicate
  risk。
- 审查所有 `ON CONFLICT (match_id)` 和 no-version reader joins。
- 明确 backup/rollback plan。
- 规划 rollback 的 blocker：一旦写入 v2 additional rows，恢复
  `UNIQUE(match_id)` 前必须先处理 multi-version rows。
- 规划 compatibility helper / selector，避免 parser/training 隐式读错版本。

## 9. Recommended next phases

推荐下一步：

1. Phase 5.21L2F: `raw_match_data` versioned schema migration
   planning/preflight
    - no DB write
    - no migration execution
    - prepare exact ALTER plan
    - verify constraint/index/code impact
    - prepare backup/rollback plan

2. Phase 5.21L2G: controlled schema migration execution
    - only after explicit authorization
    - changes constraint/index only
    - no raw data writes

3. Phase 5.21L2H: pageProps v2 single-target write preflight
    - no DB write
    - recapture target `4830747`
    - compare stable hash with L2D preview baseline

4. Phase 5.21L2I: pageProps v2 single-target controlled write
    - only after explicit DB-write authorization
    - insert v2 row as additional version
    - v1 remains preserved

## 10. Explicit non-execution

本阶段确认未执行：

- no external FotMob access
- no live match detail request
- no DB writes
- no schema migration
- no raw_match_data writes
- no matches writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full raw_data print/save
- no file deletion
