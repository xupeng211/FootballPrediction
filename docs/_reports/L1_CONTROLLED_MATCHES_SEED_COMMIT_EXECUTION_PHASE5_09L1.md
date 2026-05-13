# L1 Controlled Matches Seed Commit Execution - Phase 5.09L1

## 1. Executive summary

Phase 5.09L1 是 controlled matches seed commit execution 阶段。

本阶段在用户最终确认后允许写 `matches`，但范围只限 exact 8 个 `2026-05-10` FotMob Ligue 1 candidates。

本阶段只写 `matches`，不写 `raw_match_data`，不训练，不预测。

## 2. Background

Phase 5.05L1 发现了 8 个 controlled candidates。

Phase 5.08L1 execution preflight 显示：

- `would_insert=8`
- `would_update=0`
- `would_skip=0`

`raw_match_data.match_id` 依赖 `matches(match_id)` 外键，所以后续 raw JSON 入库前需要先完成 matches seed。

## 3. Implemented files

- `scripts/ops/l1_matches_seed_commit_execute.js`
- `tests/unit/l1_matches_seed_commit_execute.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION_PHASE5_09L1.md`

## 4. Execution boundary

- exact scope only
- rows `<= 10`
- only `matches` table
- no `raw_match_data`
- no features / predictions
- no `titan_discovery`
- no `FixtureRepository.persist`

## 5. Validation before actual DB write

本阶段在真实 DB write 前需要完成：

- unit tests
- `npm test`
- `npm run test:coverage`
- `git diff --check`
- `eslint / prettier`
- DB baseline read-only check
- exact candidate recapture
- affected `SELECT`

## 6. Actual DB write result

本节用于记录合并后、main CI 绿灯后的受控执行结果：

- matches row count before / after
- inserted_count
- updated_count
- skipped_count
- affected match_ids
- contains `4830746`
- raw_match_data unchanged
- features unchanged
- predictions unchanged
- transaction committed

## 7. Recommended next phase

推荐进入 Phase 5.10L2：controlled raw JSON acquisition planning。

要求：

- 使用 newly seeded matches
- 只抓 match detail raw JSON
- 规划 `raw_match_data` ingest
- 不训练
- 不预测

## 8. Explicit non-execution

本阶段明确不执行：

- `titan_discovery` execution
- `DiscoveryService.discover` execution
- `FixtureRepository.persist`
- `raw_match_data` writes
- feature writes
- prediction writes
- harvest / ingest beyond controlled matches write
- training / prediction
- file deletion
