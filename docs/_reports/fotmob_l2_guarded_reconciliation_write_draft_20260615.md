# FotMob L2 Guarded Reconciliation Write Draft - 2026-06-15

- lifecycle: phase-artifact
- scope: no-op-by-default guarded write script draft
- source script: `scripts/ops/l2_guarded_reconciliation_write.js`
- related design: `docs/architecture/FOTMOB_L2_GUARDED_RECONCILIATION_WRITE_DESIGN.md`
- related preview: `docs/_reports/fotmob_l2_reconciliation_preview_20260615.md`

## 1. Purpose / 目的

本 PR 只提供 guarded reconciliation write 脚本草稿，默认不写库。

## 2. Safety Boundary / 安全边界

- no FotMob live fetch
- no scraper
- no browser
- no raw_match_data write
- no raw payload output
- default no DB write
- default no matches update
- default no pipeline_status update
- no parser/model/feature/schema change
- `--allow-write` path implemented but not executed in this PR

## 3. Guarded Write Contract / 写入契约

- default no-op
- `--allow-write` required
- batch size max `3`
- `expected-count` optional
- only `pending -> harvested`
- requires `raw_match_data` `fotmob_live_v1`
- requires `finished` status
- requires `raw_row_count = 1`
- requires `raw_data` / `data_hash`
- no quiet mode
- no raw payload output

## 4. Commands / 执行命令

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node --test tests/unit/scripts/ops/l2_guarded_reconciliation_write.test.js
```

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js --limit 3 --json
```

No `--allow-write` command was executed.

## 5. Dry-run Result / dry-run 结果

Dry-run 执行成功。

- candidate_total: `58`
- selected_count: `3`
- would_update_count: `3`
- actual_update_executed: `false`
- pending_external_scope_total: `60`
- excluded_no_raw_count: `2`
- hold_duplicate_raw_count: `0`
- hold_non_finished_count: `0`
- hold_missing_hash_or_payload_count: `0`
- hold_external_id_mismatch_count: `0`
- by_league: `Ligue 1 = 58`
- by_season: `2025/2026 = 58`
- by_match_status: `finished = 58`

selected sample:

| match_id | external_id | league_name | season | home_team | away_team | match_date | old_pipeline_status | new_pipeline_status_preview | raw_data_version | raw_row_count | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `53_20252026_4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |
| `53_20252026_4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |
| `53_20252026_4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |

## 6. Validation / 验证

- unit/static tests: passed
- `git diff --check`: clean
- no unexpected files: yes
- no live fetch: yes
- no DB writes executed: yes

## 7. Interpretation / 结果解读

- 脚本已经具备默认 no-op、preview-first、batch cap 和 `--allow-write` 门控草稿。
- 当前仍没有写库，`actual_update_executed=false`。
- 如果未来要执行真实小批量，仍然需要用户明确确认。
- 首次真实执行最多 `3` 条。
- 执行后必须再做 read-only verification report。

## 8. Next Recommended Task / 下一步建议

- 下一 PR 可以做 first guarded reconciliation execution plan，仍不立即执行，先列出首批 `3` 条 `match_id`、预期 before/after 状态、rollback plan 和 verification report plan。
- 或者只有在用户明确授权后，才允许执行首批 `<=3` 条。
- Do not start automatically
- Recommended next task only after user confirmation
