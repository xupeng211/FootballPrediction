# FotMob L2 Ninth Guarded Reconciliation — Execution Plan

**Date:** 2026-06-18
**Branch:** `docs/fotmob-l2-ninth-guarded-reconciliation-plan`
**Base:** `2c61d157851c53e1c627a8440d59d36f25ee09f4` (origin/main)

## Nature

This is a **planning-only** document for the ninth guarded FotMob L2 reconciliation batch. It records the dry-run results and the 10 planned match_ids. **No execution has been performed.**

## Safety gates confirmed

| Gate | Status |
|------|--------|
| No `--allow-write` | ✅ Confirmed — dry-run mode only |
| No real DB write | ✅ Confirmed — `actual_update_executed: false` |
| No FotMob live fetch | ✅ Confirmed — `live_fetch_allowed: false` |
| No raw payload output | ✅ Confirmed — `raw_payload_output_allowed: false` |
| No ninth batch execution | ✅ Confirmed — this is planning only |
| No next task started | ✅ Confirmed |

## Dry-run summary

Run command: `node scripts/ops/l2_guarded_reconciliation_write.js --limit 10 --json` (no `--allow-write`)

| Metric | Value | Expected | Match |
|--------|-------|----------|-------|
| `pending_external_scope_total` | 15 | — | — |
| `candidate_total` | 13 | 13 | ✅ |
| `selected_count` | 10 | 10 | ✅ |
| `would_update_count` | 10 | 10 | ✅ |
| `hold_duplicate_raw_count` | 0 | 0 | ✅ |
| `hold_non_finished_count` | 0 | 0 | ✅ |
| `hold_missing_hash_or_payload_count` | 0 | 0 | ✅ |
| `hold_external_id_mismatch_count` | 0 | 0 | ✅ |
| `excluded_no_raw_count` | 2 | — | — |
| `actual_update_executed` | false | false | ✅ |
| `safety.max_batch_size` | 10 | 10 | ✅ |

## Planned ninth batch — 10 match_ids

All 10 were verified via read-only DB query: `pipeline_status = pending`, `status = finished`, `raw_match_data` (fotmob_live_v1) exists, `raw_row_count = 1`, no duplicate raw, no external_id mismatch.

| # | match_id | external_id | home_team | away_team | match_date | pipeline_status | status | raw data_version | raw_row_count |
|---|----------|-------------|-----------|-----------|------------|-----------------|--------|-----------------|---------------|
| 1 | `53_20252026_4830510` | 4830510 | Strasbourg | Marseille | 2025-09-26 | pending | finished | fotmob_live_v1 | 1 |
| 2 | `53_20252026_4830505` | 4830505 | Lorient | Monaco | 2025-09-27 | pending | finished | fotmob_live_v1 | 1 |
| 3 | `53_20252026_4830511` | 4830511 | Toulouse | Nantes | 2025-09-27 | pending | finished | fotmob_live_v1 | 1 |
| 4 | `53_20252026_4830508` | 4830508 | Paris Saint-Germain | Auxerre | 2025-09-27 | pending | finished | fotmob_live_v1 | 1 |
| 5 | `53_20252026_4830507` | 4830507 | Nice | Paris FC | 2025-09-28 | pending | finished | fotmob_live_v1 | 1 |
| 6 | `53_20252026_4830746` | 4830746 | Angers | Strasbourg | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 7 | `53_20252026_4830747` | 4830747 | Auxerre | Nice | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 8 | `53_20252026_4830748` | 4830748 | Le Havre | Marseille | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 9 | `53_20252026_4830750` | 4830750 | Metz | Lorient | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |
| 10 | `53_20252026_4830751` | 4830751 | Monaco | Lille | 2026-05-10 | pending | finished | fotmob_live_v1 | 1 |

## DB verification details

- All 10 `pipeline_status = pending` ✅
- All 10 `status = finished`, `is_finished = true` ✅
- All 10 have `fotmob_live_v1` raw_match_data ✅
- `raw_row_count = 1` for fotmob_live_v1 per match ✅
- No duplicate raw within fotmob_live_v1 ✅
- No external_id mismatch (matches ↔ raw_match_data) ✅
- `raw_match_data_total = 76` unchanged ✅
- 5 of the 10 also have `fotmob_pageprops_v2` and `fotmob_html_hyd_v1` rows (normal, different data versions, not duplicates)

## Remaining pending candidates after this batch

After this batch executes, there will be 3 remaining pending candidates with fotmob_live_v1 raw, plus 2 pending without raw (`excluded_no_raw_count = 2`). These are for future batches — not part of this planning.

## Transition

The guarded reconciliation will transition these 10 matches: `pending → harvested`.

## Execution command (for reference only — DO NOT run yet)

```
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js --limit 10 --json --allow-write
```

## Conclusion

- ✅ candidate_total = 13, selected_count = 10, would_update_count = 10
- ✅ actual_update_executed = false (planning only)
- ✅ All 10 planned match_ids verified as pending + finished + raw exists
- ✅ No duplicate raw, no external_id mismatch
- ✅ No FotMob live fetch, no raw payload output
- ✅ No ninth batch execution, no next task started

**Next step:** User must explicitly confirm and authorize before ninth batch execution. Do not execute without explicit user authorization.
