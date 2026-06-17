# FotMob L2 Tenth Guarded Reconciliation — Execution Plan

**Date:** 2026-06-18
**Branch:** `docs/fotmob-l2-tenth-guarded-reconciliation-plan`
**Base:** `6a1cd8bab66540e383e4abe764ae308fdcafc6cb` (origin/main)

## Nature

This is a **tenth batch execution plan only** — not an execution. It describes the next 3 pending Ligue 1 match_ids that are candidates for the guarded `pending -> harvested` transition via `l2_guarded_reconciliation_write.js --limit 10 --allow-write`. No `--allow-write` was passed, no real DB writes occurred, and no tenth batch execution took place.

## Safety gates

| Gate | Status |
|------|--------|
| No `--allow-write` | ✅ Confirmed — dry-run mode only |
| No real DB write | ✅ Confirmed |
| No FotMob live fetch | ✅ Confirmed |
| No raw payload output | ✅ Confirmed |
| No tenth batch execution | ✅ Confirmed |
| No next task started | ✅ Confirmed |

## Dry-run summary

Run command: `node scripts/ops/l2_guarded_reconciliation_write.js --limit 10 --json` (no `--allow-write`)

| Metric | Value | Expected | Match |
|--------|-------|----------|-------|
| `candidate_total` | 3 | 3 | ✅ |
| `selected_count` | 3 | 3 | ✅ |
| `would_update_count` | 3 | 3 | ✅ |
| `hold_duplicate_raw_count` | 0 | 0 | ✅ |
| `hold_non_finished_count` | 0 | 0 | ✅ |
| `hold_missing_hash_or_payload_count` | 0 | 0 | ✅ |
| `hold_external_id_mismatch_count` | 0 | 0 | ✅ |
| `excluded_no_raw_count` | 2 | — | — |
| `actual_update_executed` | false | false | ✅ |
| `pending_external_scope_total` | 5 | — | — |
| `batch_size` | 3 | — | — |

## Planned tenth batch — 3 match_ids

All 3 candidates confirmed via read-only DB query as `pipeline_status = 'pending'` and `status = 'finished'` with `fotmob_live_v1` raw data:

| # | match_id | external_id | home_team | away_team | match_date | pipeline_status | status | raw_data_version | raw_row_count |
|---|----------|-------------|-----------|-----------|------------|-----------------|--------|-----------------|---------------|
| 1 | `53_20252026_4830752` | 4830752 | Paris Saint-Germain | Brest | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 2 | `53_20252026_4830753` | 4830753 | Rennes | Paris FC | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 3 | `53_20252026_4830754` | 4830754 | Toulouse | Lyon | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |

## `raw_match_data` integrity

| Metric | Value |
|--------|-------|
| `raw_match_data_total` | 76 |
| `raw_match_data_total` changed | No ✅ |
| Duplicate `fotmob_live_v1` raw for candidates | 0 ✅ |
| `external_id` mismatch (matches vs raw) | 0 ✅ |

## Excluded matches

2 pending matches excluded due to `excluded_no_raw_count = 2`. These are Ligue 1 2025/2026 pending matches with no `fotmob_live_v1` raw data and are not candidates for this batch.

## Delimitation

- This is the **tenth batch** (batch 10), the final batch for Ligue 1 2025/2026 pending reconciliation.
- After this batch executes, `pending_external_scope_total` would become 0 for Ligue 1 2025/2026 (5 pending → 2 excluded no-raw + 3 harvested = all accounted for).
- The 2 excluded (no-raw) pending matches require separate handling outside the guarded reconciliation pipeline.

## Authorization required

⚠️ **This plan does NOT authorize execution.** The following explicit user confirmation is required before any tenth batch execution:

1. User must explicitly authorize `--allow-write` execution
2. Expected command: `docker compose -f docker-compose.dev.yml exec dev node scripts/ops/l2_guarded_reconciliation_write.js --limit 10 --allow-write`
3. Expected outcome: 3 match_ids transition from `pending` to `harvested`
4. Post-execution audit PR must follow separately

## Conclusion

- ✅ Tenth batch = 3 match_ids planned (4830752, 4830753, 4830754)
- ✅ All 3 confirmed `pending` + `finished` with single `fotmob_live_v1` raw data
- ✅ `raw_match_data_total` = 76, unchanged
- ✅ No duplicates, no external_id mismatches
- ✅ No `--allow-write`, no real DB write, no tenth batch execution
- ✅ No FotMob live fetch, no raw payload output
- ✅ No next task started

**Next step:** User must explicitly authorize tenth batch execution before proceeding.
