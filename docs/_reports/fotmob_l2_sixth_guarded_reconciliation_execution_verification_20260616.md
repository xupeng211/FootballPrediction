# FotMob L2 Sixth Guarded Reconciliation Execution Verification

**Date:** 2026-06-16
**Branch:** data/fotmob-l2-sixth-guarded-reconciliation-execution
**Base:** main @ eee35fd8456f890e2273bbeaf68077cf43cf4599

## Status: SIXTH BATCH EXECUTED — VERIFIED

User explicitly authorized `--allow-write` execution for exactly these 10 planned match IDs. Execution completed successfully.

## Pre-Execution Dry-Run Verification

| Metric | Value |
|--------|-------|
| candidate_total (before) | 43 |
| selected_count | 10 |
| would_update_count | 10 |
| actual_update_executed | false |
| safety.max_batch_size | 10 |
| Selected match_ids match planned 10 | ✅ |

## Execution Summary

| Metric | Value |
|--------|-------|
| mode | write_executed |
| updated_count | **10** |
| actual_update_executed | **true** |
| --allow-write used | Yes (user authorized) |
| db_write_allowed | true |
| pipeline_status_update_allowed | true |
| live_fetch_allowed | false |
| raw_match_data_write_allowed | false |
| raw_payload_output_allowed | false |

## Executed 10 Match IDs — All pending → harvested

| # | match_id | Home | Away | Old | New | Decision |
|---|----------|------|------|-----|-----|----------|
| 1 | 53_20252026_4830474 | Strasbourg | Nantes | pending | harvested | updated |
| 2 | 53_20252026_4830475 | Toulouse | Brest | pending | harvested | updated |
| 3 | 53_20252026_4830468 | Lille | Monaco | pending | harvested | updated |
| 4 | 53_20252026_4830478 | Lens | Brest | pending | harvested | updated |
| 5 | 53_20252026_4830479 | Lorient | Lille | pending | harvested | updated |
| 6 | 53_20252026_4830482 | Nantes | Auxerre | pending | harvested | updated |
| 7 | 53_20252026_4830484 | Toulouse | Paris Saint-Germain | pending | harvested | updated |
| 8 | 53_20252026_4830476 | Angers | Rennes | pending | harvested | updated |
| 9 | 53_20252026_4830477 | Le Havre | Nice | pending | harvested | updated |
| 10 | 53_20252026_4830481 | Monaco | Strasbourg | pending | harvested | updated |

All 10 are Ligue 1 2025/2026, status `finished`.

## Post-Execution Dry-Run Verification

| Metric | Value |
|--------|-------|
| candidate_total (after) | **33** |
| actual_update_executed | false (dry-run) |
| candidate_total delta | 43 → 33 (−10) |
| Sixth batch absent from new candidates | ✅ |

## Guard Verification

- [x] candidate_total before: 43
- [x] candidate_total after: 33
- [x] updated_count: 10
- [x] All 10: pending → harvested
- [x] All 10 after_rows decision: "updated"
- [x] raw_match_data_total unchanged (raw_match_data_write_allowed: false)
- [x] No raw_match_data writes or deletes
- [x] No extra updates beyond the 10
- [x] No FotMob live fetch (live_fetch_allowed: false)
- [x] No raw payload output (raw_payload_output_allowed: false)
- [x] No seventh batch execution
- [x] No seventh batch planning
- [x] No next task started
- [x] No script changes
- [x] No test changes
- [x] No schema changes
- [x] No migration changes

## Next Step

Next recommended action is a **read-only audit** of the sixth batch execution. Do not start automatically. Recommended next task only after user confirmation. The remaining 33 pending candidates must not be processed without separate explicit authorization.
