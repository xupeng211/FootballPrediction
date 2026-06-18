# FotMob L2 No-Raw Excluded Matches — Read-Only Investigation

**Date:** 2026-06-18
**Branch:** `docs/fotmob-l2-no-raw-excluded-investigation`
**Base:** `6eeb7f3357b35e76b65aeb7da5614b27291f4ce9` (origin/main)

## Nature

This is a **read-only investigation**, not a fix. No `--allow-write`, no real DB write, no FotMob live fetch, no raw payload output, no raw_match_data write/delete, no eleventh batch planning, no eleventh batch execution.

## Investigation scope

Only the 2 `no-raw excluded` pending matches identified by the tenth guarded reconciliation dry-run:

| # | match_id | external_id |
|---|----------|-------------|
| 1 | `140_20252026_4837496` | 4837496 |
| 2 | `47_20242025_900002` | 900002 |

## Dry-run confirmation

```json
{
  "candidate_total": 0,
  "selected_count": 0,
  "would_update_count": 0,
  "actual_update_executed": false,
  "excluded_no_raw_count": 2
}
```

`candidate_total = 0` confirms Ligue 1 2025/2026 guarded reconciliation is complete. No further `fotmob_live_v1` pending candidates exist.

## Match 1: `140_20252026_4837496`

| Field | Value |
|-------|-------|
| match_id | `140_20252026_4837496` |
| external_id | `4837496` |
| league_name | **Segunda División** (not Ligue 1) |
| season | 2025/2026 |
| home_team | Cultural Leonesa |
| away_team | Burgos CF |
| match_date | 2026-05-24 17:00:00+00 |
| status | **scheduled** |
| is_finished | **false** |
| pipeline_status | pending |
| data_source | manual_html_seed |
| data_version | PHASE4.13 |
| fotmob_live_v1 raw | **No** |
| other raw version | PHASE4.23 (1 row, collected_at 2026-05-03) |

### Why excluded_no_raw

- Has exactly 1 raw_match_data row, but `data_version = PHASE4.23` (not `fotmob_live_v1`).
- The guarded reconciliation query only JOINs `raw_match_data WHERE data_version = 'fotmob_live_v1'`. This match's `raw_row_count` is therefore 0 in that join.
- `classifyPendingRowState({rawRowCount: 0})` → `excluded_no_raw`, reason: `pending_without_fotmob_live_v1_raw`.
- Additionally, status is `scheduled` (not `finished`), so even if it had fotmob_live_v1 raw data, it would be held as `hold_non_finished`.

### Risk / judgment

- **Not a Ligue 1 2025/2026 match.** League prefix `140` = Segunda División (Spanish second division).
- **Not eligible for guarded reconciliation** in its current form: it's both `scheduled` AND lacks `fotmob_live_v1` raw data.
- The existing PHASE4.23 raw data is legacy/synthetic; its provenance, fidelity, and completeness are unknown relative to the current `fotmob_live_v1` pipeline.
- This match is a completely separate league and data pipeline concern.

### Recommendation

- Should remain **pending** for now.
- If Segunda División raw data collection is desired in the future, it must go through a separate authorization / preflight / controlled write pipeline distinct from the Ligue 1 `fotmob_live_v1` workflow.
- The `scheduled` status is a blocker for any `pending → harvested` transition. Would need the match to finish and have a valid finished score first.

## Match 2: `47_20242025_900002`

| Field | Value |
|-------|-------|
| match_id | `47_20242025_900002` |
| external_id | `900002` |
| league_name | **Segunda** (not Ligue 1) |
| season | 2024/2025 |
| home_team | Burgos |
| away_team | Oviedo |
| match_date | 2024-08-17 17:30:00+00 |
| status | **finished** |
| home_score | 1 |
| away_score | 0 |
| is_finished | **true** |
| pipeline_status | pending |
| data_source | local_finished_csv |
| data_version | PHASE4.39 |
| fotmob_live_v1 raw | **No** |
| other raw version | PHASE4.43_SYNTHETIC (1 row, collected_at 2026-05-03) |

### Why excluded_no_raw

- Has exactly 1 raw_match_data row, but `data_version = PHASE4.43_SYNTHETIC` (not `fotmob_live_v1`).
- As with match 1, the reconciliation query only counts `fotmob_live_v1` rows, so `raw_row_count = 0`.
- `classifyPendingRowState({rawRowCount: 0})` → `excluded_no_raw`, reason: `pending_without_fotmob_live_v1_raw`.

### Risk / judgment

- **Not a Ligue 1 2025/2026 match.** League prefix `47` = Segunda (Spanish second division). Season is 2024/2025.
- Match IS finished (1-0, Burgos vs Oviedo, Aug 2024), so the `hold_non_finished` guard would not block it IF it had `fotmob_live_v1` raw data.
- The existing PHASE4.43_SYNTHETIC raw data was synthesized (not from real FotMob fetch). It cannot be used for guarded reconciliation.
- Guessed `external_id = 900002` — it's unclear whether this is a real FotMob match ID or was assigned synthetically. No FotMob evidence (no live fetch, no 404 check, no browser probe) has been conducted for this external_id.
- If this external_id is incorrect or FotMob returns 404, the match would need `needs_new_evidence` status.
- The `PHASE4.43_SYNTHETIC` raw data is explicitly synthetic — it has zero FotMob source fidelity and must not be used as evidence for any reconciliation transition.

### Recommendation

- Status should be **skipped** or **needs_new_evidence** rather than `pending`. The synthetic PHASE4.43_SYNTHETIC raw data does NOT constitute valid evidence for FotMob L2 reconciliation.
- Any future attempt to collect real FotMob raw data for this match must first verify that `external_id = 900002` is a valid FotMob match ID via authorized source inventory discovery.
- If FotMob returns 404 or the match never existed in FotMob's system, this match should be marked `failed` or `skipped` with reason `no_fotmob_evidence`.
- This is a Segunda 2024/2025 match — a separate league and season from the Ligue 1 2025/2026 pipeline.

## Summary

| Question | Answer |
|----------|--------|
| Are these Ligue 1 2025/2026 matches? | **No.** Both are Spanish Segunda / Segunda División (league prefixes 140 and 47). |
| Are these eligible for fotmob_live_v1 guarded reconciliation? | **No.** Both lack `fotmob_live_v1` raw data. Match 1 is also `scheduled`. Match 2 has only synthetic raw data. |
| Is Ligue 1 2025/2026 reconciliation complete? | **Yes.** 58/58 Ligue 1 matches are `harvested`. `candidate_total = 0`. |
| Should these remain pending? | Match 1: `pending` is OK for now (match is scheduled, not yet played). Match 2: should be `skipped` or `needs_new_evidence` — synthetic raw data is not valid FotMob evidence. |
| Should they be processed in a future batch? | No automated batch. Each requires explicit user authorization and a separate pipeline for non-Ligue-1 / non-fotmob_live_v1 data. |
| Was FotMob live-fetched? | **No.** |
| Was raw payload saved or printed? | **No.** |
| Was DB written? | **No.** |
| Was `--allow-write` used? | **No.** |
| Was an eleventh batch planned or executed? | **No.** |
| Was a next task started? | **No.** |

## Conclusion

The 2 no-raw excluded pending matches are confirmed as non-Ligue-1 leagues with no `fotmob_live_v1` raw data. They are a separate concern from the completed Ligue 1 2025/2026 guarded reconciliation (58/58 harvested). No automated action should be taken on them. Each requires explicit user authorization with a league-appropriate pipeline.

**Next step:** User must explicitly authorize any further action on these 2 matches. Do not process, do not plan an eleventh batch, do not start a new task without explicit authorization.
