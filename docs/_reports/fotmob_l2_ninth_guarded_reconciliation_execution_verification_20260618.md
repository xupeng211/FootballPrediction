# FotMob L2 Ninth Guarded Reconciliation — Execution Verification

**Date:** 2026-06-18
**Branch:** `data/fotmob-l2-ninth-guarded-reconciliation-execution`
**Base:** `23b0fb53c6b352473092075cc8bdc1eb4a3b09b1` (origin/main)

## Nature

This is an **execution verification** report for the ninth guarded FotMob L2 reconciliation batch. The user explicitly authorized `--allow-write` for exactly 10 planned match_ids. The execution was performed and verified.

## Authorization

- User explicitly authorized real DB write for exactly these 10 match_ids
- No other matches were touched
- No raw_match_data writes were performed

## Execution command

```
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js \
  --limit 10 \
  --expected-count 10 \
  --allow-write \
  --json
```

## Pre-execution dry-run

| Metric | Value |
|--------|-------|
| `candidate_total` | 13 |
| `selected_count` | 10 |
| `would_update_count` | 10 |
| `actual_update_executed` | false |
| Candidates match planned 10 | ✅ |

## Execution result

| Metric | Value |
|--------|-------|
| `mode` | write_executed |
| `updated_count` | 10 |
| `actual_update_executed` | true |
| `selected_count` | 10 |

## Post-execution dry-run

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| `candidate_total` | 13 | 3 | -10 ✅ |
| `pending_external_scope_total` | 15 | 5 | -10 ✅ |
| `selected_count` | 10 | 3 | -7 |
| `excluded_no_raw_count` | 2 | 2 | 0 (unchanged) |
| `actual_update_executed` | false | false | ✅ |

## Ninth batch — 10 match_ids: pending → harvested

All 10 confirmed `harvested` via read-only DB query:

| # | match_id | external_id | home_team | away_team | pipeline_status |
|---|----------|-------------|-----------|-----------|-----------------|
| 1 | `53_20252026_4830510` | 4830510 | Strasbourg | Marseille | harvested |
| 2 | `53_20252026_4830505` | 4830505 | Lorient | Monaco | harvested |
| 3 | `53_20252026_4830511` | 4830511 | Toulouse | Nantes | harvested |
| 4 | `53_20252026_4830508` | 4830508 | Paris Saint-Germain | Auxerre | harvested |
| 5 | `53_20252026_4830507` | 4830507 | Nice | Paris FC | harvested |
| 6 | `53_20252026_4830746` | 4830746 | Angers | Strasbourg | harvested |
| 7 | `53_20252026_4830747` | 4830747 | Auxerre | Nice | harvested |
| 8 | `53_20252026_4830748` | 4830748 | Le Havre | Marseille | harvested |
| 9 | `53_20252026_4830750` | 4830750 | Metz | Lorient | harvested |
| 10 | `53_20252026_4830751` | 4830751 | Monaco | Lille | harvested |

## Integrity checks

| Check | Result |
|-------|--------|
| 10/10 harvested | ✅ |
| `raw_match_data_total = 76` | ✅ unchanged |
| No `raw_match_data` writes/deletes | ✅ |
| No extra updates outside the 10 | ✅ |
| harvested_ligue1 = 55 (was 45) | ✅ +10 exactly |
| pending_ligue1 = 3 (was 13) | ✅ -10 exactly |
| No FotMob live fetch | ✅ |
| No raw payload output | ✅ |
| No tenth batch execution | ✅ |
| No tenth batch planning | ✅ |
| No next task started | ✅ |

## Remaining pending (3 candidates — NOT part of this batch)

| match_id | external_id | home_team | away_team |
|----------|-------------|-----------|-----------|
| `53_20252026_4830752` | 4830752 | Paris Saint-Germain | Brest |
| `53_20252026_4830753` | 4830753 | Rennes | Paris FC |
| `53_20252026_4830754` | 4830754 | Toulouse | Lyon |

⚠️ The above 3 are surfaced by the post-execution dry-run. They are NOT part of this batch and are NOT a tenth batch plan.

## Conclusion

- ✅ User explicitly authorized --allow-write for exactly 10 planned match_ids
- ✅ updated_count = 10, all 10 pending → harvested
- ✅ candidate_total: 13 → 3
- ✅ raw_match_data_total = 76 unchanged
- ✅ No extra updates, no raw_match_data writes/deletes
- ✅ No FotMob live fetch, no raw payload output
- ✅ No tenth batch execution, no tenth batch planning

**Next step:** User must confirm for ninth batch post-execution read-only audit. Do not start without explicit user authorization.
