# Matches Labeling Writer Support — Verification Report

**Date:** 2026-06-19
**Branch:** `feat/matches-labeling-writer-support`
**PR Type:** Writer Support (Not Migration)
**Lifecycle:** permanent

---

## 1. Nature of This Change

This is **writer support**, not a migration. It does NOT:
- Add new database migrations
- Modify the matches schema (columns already exist from V26.7)
- Backfill historical data
- Update existing matches rows
- Process no-raw excluded matches
- Perform live fetch
- Output raw payload
- Change parser, training, or prediction code

It ONLY modifies writer/persistence code paths so that **future** writes and status updates will populate the 6 governance label columns introduced by V26.7.

---

## 2. Schema Confirmation

V26.7 migration (`database/migrations/V26.7__add_matches_labeling_governance_columns.sql`) already added:

| Column | Type | Nullable | Default |
|---|---|---|---|
| `source_type` | VARCHAR(32) | YES | NULL |
| `evidence_level` | VARCHAR(24) | YES | NULL |
| `is_production_scope` | BOOLEAN | YES | NULL |
| `is_reconciliation_eligible` | BOOLEAN | YES | NULL |
| `is_training_eligible` | BOOLEAN | YES | NULL |
| `pipeline_status_reason` | VARCHAR(64) | YES | NULL |

With CHECK constraints validating allowed values.

**No new migration added. No schema changed.**

---

## 3. New Module: MatchLabelingGovernance

**Path:** `src/infrastructure/services/MatchLabelingGovernance.js`

A pure-function module that centralizes label derivation logic. Exports:

| Function | Purpose |
|---|---|
| `computeSourceType(context)` | Derive source_type from data_version or data_source |
| `computeEvidenceLevel(sourceType)` | Map source_type → evidence_level |
| `computeProductionScope(context)` | Check if league/season is in production scope |
| `computeReconciliationEligibility(context)` | Check if match can enter reconciliation |
| `computeTrainingEligibility()` | Conservative: always returns `false` |
| `computePipelineStatusReason(context)` | Compute structured reason for pipeline_status |
| `computeGovernanceLabels(context)` | Main entry: returns all 6 fields at once |

### Label Derivation Rules (V26.7-writer-support-v1)

**source_type mapping:**

| Evidence | source_type |
|---|---|
| `fotmob_live_v1` raw | `fotmob_live_fetch` |
| `fotmob_html_hyd_v1` raw | `fotmob_html_hydration` |
| `fotmob_pageprops_v2` raw | `fotmob_pageprops` |
| `manual_*seed` data_source | `manual_seed` |
| `*csv*` data_source | `local_csv` |
| `PHASE*` / `synthetic*` version | `synthetic` |
| Cannot determine | `unknown` |

**evidence_level mapping:**

| source_type | evidence_level |
|---|---|
| `fotmob_live_fetch` | `strong` |
| `fotmob_html_hydration` | `medium` |
| `fotmob_pageprops` | `medium` |
| `manual_seed` | `weak` |
| `local_csv` | `weak` |
| `synthetic` | `synthetic_invalid` |
| `unknown` | `missing` |

**is_production_scope:** `true` only for Ligue 1 / 2025/2026.

**is_reconciliation_eligible:** `true` only when ALL of:
- status = `finished`
- has `fotmob_live_v1` raw
- evidence_level = `strong`
- is_production_scope = `true`

**is_training_eligible:** Conservatively `false` for all matches.

**pipeline_status_reason** (first applicable):
1. Not finished → `awaiting_match_completion`
2. Synthetic data → `synthetic_raw_not_valid`
3. Non-production league → `non_production_league`
4. No fotmob_live_v1 raw → `pending_without_fotmob_live_v1_raw`
5. No external_id → `external_id_unverified`
6. All conditions met → `NULL`

---

## 4. Modified Writer Paths

### 4.1 FixtureRepository._persistBatch (`src/infrastructure/services/FixtureRepository.js`)

The main new-match INSERT path. Now includes 6 governance columns in the INSERT VALUES. On conflict, the DO UPDATE SET clause does NOT touch governance fields — preserving existing values for already-inserted matches.

**Impact:** Future matches created via `FixtureRepository.persist()` will have initial governance labels computed from their `data_source`, `league_name`, `season`, `status`, and `external_id`.

### 4.2 Persistence._syncMatchPipelineState (`src/infrastructure/harvesters/components/Persistence.js`)

The harvest-time pipeline_status update path (sets `pipeline_status = 'harvested'` after raw data write). Now:
- Fetches match context (league_name, season, status, external_id, data_source)
- Checks for `fotmob_live_v1` raw existence
- Computes full governance labels and sets all 6 fields in the same UPDATE

**Impact:** Future harvests that go through V26.1 Persistence will populate governance fields when transitioning to `harvested`.

### 4.3 MarathonService._saveToDatabase (`src/infrastructure/services/MarathonService.js`)

The Marathon L2 batch harvest update path. Now:
- Fetches match context before UPDATE
- Checks for `fotmob_live_v1` raw existence
- Computes governance labels
- Sets `source_type`, `evidence_level`, `is_production_scope`, `is_reconciliation_eligible`, `is_training_eligible` in the same UPDATE
- Sets `pipeline_status_reason` in a separate UPDATE if applicable

**Impact:** Future Marathon harvests will populate governance fields.

### 4.4 l2_guarded_reconciliation_write.js (`scripts/ops/l2_guarded_reconciliation_write.js`)

Updated `GUARDED_UPDATE_SQL` to include governance fields using COALESCE (preserve existing, set defaults for new):
- `source_type = COALESCE(matches.source_type, 'fotmob_live_fetch')`
- `evidence_level = COALESCE(matches.evidence_level, 'strong')`
- `is_production_scope = COALESCE(matches.is_production_scope, true)`
- `is_reconciliation_eligible = COALESCE(matches.is_reconciliation_eligible, true)`
- `is_training_eligible = COALESCE(matches.is_training_eligible, false)`
- `pipeline_status_reason = NULL`

**Impact:** Future guarded reconciliation writes (pending → harvested with `fotmob_live_v1` raw) will populate governance fields alongside the status transition.

**Note:** This script was NOT executed as part of this PR.

---

## 5. Files Changed

```
src/infrastructure/services/MatchLabelingGovernance.js          (NEW — 346 lines)
tests/unit/MatchLabelingGovernance.test.js                      (NEW — 359 lines)
docs/_reports/matches_labeling_writer_support_verification_20260619.md  (NEW — this file)
src/infrastructure/services/FixtureRepository.js                (MODIFIED — +31 lines)
src/infrastructure/harvesters/components/Persistence.js         (MODIFIED — +69 lines)
src/infrastructure/services/MarathonService.js                  (MODIFIED — +50 lines)
scripts/ops/l2_guarded_reconciliation_write.js                  (MODIFIED — +8 lines)
```

---

## 6. Tests

### 6.1 New Tests: MatchLabelingGovernance.test.js

**53 tests, all passing.** Coverage includes:

1. `fotmob_live_v1` → `source_type=fotmob_live_fetch`, `evidence_level=strong`
2. `fotmob_html_hyd_v1` → `source_type=fotmob_html_hydration`, `evidence_level=medium`
3. `fotmob_pageprops_v2` → `source_type=fotmob_pageprops`, `evidence_level=medium`
4. `manual_html_seed` → `source_type=manual_seed`, `evidence_level=weak`
5. `local_finished_csv` → `source_type=local_csv`, `evidence_level=weak`
6. `PHASE4.43_SYNTHETIC` → `source_type=synthetic`, `evidence_level=synthetic_invalid`
7. Unknown → `source_type=unknown`, `evidence_level=missing`
8. `scheduled` → `pipeline_status_reason=awaiting_match_completion`, reconciliation=false
9. Finished + no fotmob_live_v1 raw → `pending_without_fotmob_live_v1_raw`
10. Finished + fotmob_live_v1 + production → reconciliation=true
11. Non-production league → production_scope=false
12. Training eligible always false across all scenarios

### 6.2 Existing Tests — All Passing

| Test File | Tests | Status |
|---|---|---|
| `Persistence.test.js` | 17 | ✓ Pass |
| `Persistence.StateSync.test.js` | 4 | ✓ Pass |
| `FixtureRepository.test.js` | 28 | ✓ Pass |

---

## 7. Current Production State (Unchanged)

Verified by read-only query against the production database:

| Metric | Value |
|---|---|
| Total matches | 60 |
| Ligue 1 2025/2026 harvested | 58 |
| Pipeline status = harvested | 58 |
| Pipeline status = pending | 2 |
| `candidate_total` (fotmob_live_v1 raw candidates) | 0 |
| `excluded_no_raw_count` | 2 |
| Governance columns populated on existing rows | 0 (NULL) |

**No historical data was modified. No backfill was performed.**

---

## 8. Safety Confirmation

- [x] No new migration added
- [x] No schema change
- [x] No historical data updated (no backfill)
- [x] No real writes to matches table
- [x] No no-raw excluded matches processed
- [x] No live fetch
- [x] No raw payload output
- [x] No parser/training/prediction changes
- [x] No pipeline_status constraint change
- [x] No `needs_new_evidence` status added
- [x] `is_training_eligible` defaults to false (conservative)
- [x] All related tests pass

---

## 9. Next Steps

1. Production Gate: Review and approve this PR
2. After merge, run `l2_guarded_reconciliation_write.js --dry-run --league "Ligue 1" --season "2025/2026"` to confirm state unchanged
3. Only after explicit user authorization: execute guarded backfill dry-run
4. Only after explicit user authorization: execute guarded backfill write
5. Do not expand training eligibility without confirmed training strategy
