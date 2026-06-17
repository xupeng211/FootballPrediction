# FotMob L2 Eighth Guarded Reconciliation — Execution Plan

**Date:** 2026-06-17
**Branch:** `docs/fotmob-l2-eighth-guarded-reconciliation-plan`
**Base commit:** `deb3344ca6df04e881226f7dc6b92940c58b79bd`
**Status:** PLAN ONLY — execution NOT performed

## Purpose

This is the **eighth batch plan**, not execution. A dry-run was performed to verify candidate state and produce the list of 10 match_ids to reconcile in the next execution batch.

## Dry-run command

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js --limit 10 --json
```

## Key metrics

| Metric | Value | Check |
|--------|-------|-------|
| batch_size | 10 | ✅ |
| candidate_total | 23 | ✅ |
| selected_count | 10 | ✅ |
| would_update_count | 10 | ✅ |
| actual_update_executed | false | ✅ |
| safety.max_batch_size | 10 | ✅ |
| hold_duplicate_raw_count | 0 | ✅ |
| hold_non_finished_count | 0 | ✅ |
| hold_missing_hash_or_payload_count | 0 | ✅ |
| hold_external_id_mismatch_count | 0 | ✅ |
| excluded_no_raw_count | 2 | — |

## Planned eighth batch — 10 match_ids

All 10 are confirmed: pipeline_status = `pending`, status = `finished`, raw_match_data exists, data_version = `fotmob_live_v1`, raw_row_count = 1, no duplicate raw, no external_id mismatch.

| # | match_id | Home | Away | Date |
|---|----------|------|------|------|
| 1 | 53_20252026_4830492 | Rennes | Lyon | 2025-09-14 |
| 2 | 53_20252026_4830498 | Lyon | Angers | 2025-09-19 |
| 3 | 53_20252026_4830501 | Nantes | Rennes | 2025-09-20 |
| 4 | 53_20252026_4830495 | Brest | Nice | 2025-09-20 |
| 5 | 53_20252026_4830497 | Lens | Lille | 2025-09-20 |
| 6 | 53_20252026_4830502 | Paris FC | Strasbourg | 2025-09-21 |
| 7 | 53_20252026_4830494 | Auxerre | Toulouse | 2025-09-21 |
| 8 | 53_20252026_4830496 | Le Havre | Lorient | 2025-09-21 |
| 9 | 53_20252026_4830500 | Monaco | Metz | 2025-09-21 |
| 10 | 53_20252026_4830499 | Marseille | Paris Saint-Germain | 2025-09-22 |

## Safety confirmation

| Check | Result |
|-------|--------|
| `--allow-write` used? | ❌ No |
| Real DB write? | ❌ No |
| Eighth batch executed? | ❌ No |
| FotMob live fetch? | ❌ No |
| Raw payload output? | ❌ No |
| Scripts modified? | ❌ No |
| Tests modified? | ❌ No |
| Schema modified? | ❌ No |
| Migration modified? | ❌ No |
| Next task started? | ❌ No |

## Next step

**User confirmation required before executing the eighth batch.** These 10 match_ids must only be harvested with `--allow-write` after explicit user authorization. Do not execute automatically.
