# Matches Labeling Backfill Write Verification

- lifecycle: phase-artifact
- generated: 2026-06-19
- branch: data/matches-labeling-backfill-write
- script: scripts/ops/matches_labeling_backfill_dry_run.js
- previous: docs/_reports/matches_labeling_backfill_dry_run_20260619.md

## Authorization

User explicitly authorized real DB write for matches governance labeling backfill.
Write scope: exactly 6 governance columns on existing matches rows only.

## Nature

Guarded backfill write — single transaction UPDATE of source_type, evidence_level,
is_production_scope, is_reconciliation_eligible, is_training_eligible, and
pipeline_status_reason on all 60 existing matches rows. Values computed by the
existing MatchLabelingGovernance module (V26.7-writer-support-v1).

## Execution Command

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/matches_labeling_backfill_dry_run.js --allow-write --json
```

## Pre-Write Dry-Run Confirmation

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| total_matches_scanned | 60 | 60 | ✅ |
| would_update_count | 60 | 60 | ✅ |
| already_labeled_count | 0 | 0 | ✅ |
| candidate_total | 58 | 58 | ✅ |
| excluded_no_raw_count | 2 | 2 | ✅ |

## Write Result

- updated_count: 60
- transaction: single_transaction_committed
- Write gate: preflight PASS → allowed write

## Post-Write Verification

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| matches row count | 60 | 60 | ✅ unchanged |
| raw_match_data row count | 76 | 76 | ✅ unchanged |
| pipeline_status: harvested | 58 | 58 | ✅ unchanged |
| pipeline_status: pending | 2 | 2 | ✅ unchanged |
| governance fields populated | 0 | 60 | ✅ all written |

## Ligue 1 2025/2026 Label Results (58 rows)

| Field | Value | Count |
|-------|-------|-------|
| source_type | fotmob_live_fetch | 58 |
| evidence_level | strong | 58 |
| is_production_scope | true | 58 |
| is_reconciliation_eligible | true | 58 |
| is_training_eligible | false | 58 |
| pipeline_status_reason | NULL | 58 |

## No-Raw Excluded Label Results (2 rows)

### 140_20252026_4837496

| Field | Value |
|-------|-------|
| source_type | synthetic |
| evidence_level | synthetic_invalid |
| is_production_scope | false |
| is_reconciliation_eligible | false |
| is_training_eligible | false |
| pipeline_status_reason | awaiting_match_completion |

### 47_20242025_900002

| Field | Value |
|-------|-------|
| source_type | synthetic |
| evidence_level | synthetic_invalid |
| is_production_scope | false |
| is_reconciliation_eligible | false |
| is_training_eligible | false |
| pipeline_status_reason | synthetic_raw_not_valid |

## Safety Confirmation

- No migration
- No schema change
- No raw_match_data modification
- No pipeline_status change
- No live fetch / network request
- No raw payload output
- No parser / training / prediction changes
- Only 6 governance columns updated
- Single transaction with ROLLBACK on error

## Next Step

Do not start automatically. Recommended next task only after user confirmation.
