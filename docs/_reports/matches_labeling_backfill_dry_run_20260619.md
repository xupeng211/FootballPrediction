# Matches Labeling Backfill Dry-Run Report

- lifecycle: phase-artifact
- generated: 2026-06-19
- branch: data/matches-labeling-backfill-dry-run
- script: scripts/ops/matches_labeling_backfill_dry_run.js
- test: tests/unit/matches_labeling_backfill_dry_run.test.js
- governance: src/infrastructure/services/MatchLabelingGovernance.js (V26.7-writer-support-v1)

## Nature

This is a **guarded backfill dry-run**, NOT a real backfill. It computes proposed
governance labels for historical matches rows without writing any data to the
database.

## Safety Confirmation

- No migration
- No schema change
- No DB write
- No UPDATE / INSERT / DELETE
- No no-raw excluded processing
- No live fetch / network request
- No raw payload output
- No parser / training / prediction changes

## Dry-Run Command

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/matches_labeling_backfill_dry_run.js --json
```

## Dry-Run Summary

| Metric | Value |
|--------|-------|
| total_matches_scanned | 60 |
| would_update_count | 60 |
| already_labeled_count | 0 |
| unlabeled_count | 60 |
| candidate_total | 58 |
| excluded_no_raw_count | 2 |

## by_source_type

| Source Type | Count |
|-------------|-------|
| fotmob_live_fetch | 58 |
| synthetic | 2 |

## by_evidence_level

| Evidence Level | Count |
|----------------|-------|
| strong | 58 |
| synthetic_invalid | 2 |

## by_production_scope

| Scope | Count |
|-------|-------|
| true (Ligue 1 / 2025/2026) | 58 |
| false | 2 |

## by_reconciliation_eligible

| Eligible | Count |
|----------|-------|
| true | 58 |
| false | 2 |

## by_training_eligible

| Eligible | Count |
|----------|-------|
| false (conservative) | 60 |

## by_pipeline_status_reason

| Reason | Count |
|--------|-------|
| NULL | 58 |
| synthetic_raw_not_valid | 1 |
| awaiting_match_completion | 1 |

## Ligue 1 2025/2026 58/58 harvested

Status unchanged. All 58 Ligue 1 2025/2026 matches are harvested with
fotmob_live_v1 raw evidence. Proposed labels: source_type=fotmob_live_fetch,
evidence_level=strong, is_production_scope=true, is_reconciliation_eligible=true,
is_training_eligible=false, pipeline_status_reason=NULL.

## 2 No-Raw Excluded Proposed Labels

### 140_20252026_4837496

- league: Segunda División / 2025/2026
- status: scheduled
- proposed: source_type=synthetic, evidence_level=synthetic_invalid,
  is_production_scope=false, is_reconciliation_eligible=false,
  is_training_eligible=false, pipeline_status_reason=awaiting_match_completion

### 47_20242025_900002

- league: Segunda / 2024/2025
- status: finished
- proposed: source_type=synthetic, evidence_level=synthetic_invalid,
  is_production_scope=false, is_reconciliation_eligible=false,
  is_training_eligible=false, pipeline_status_reason=synthetic_raw_not_valid

## Risk Flags

- synthetic_source_detected: 2 unlabeled rows have source_type=synthetic

## Next Step

Do not start automatically. Real guarded backfill write requires explicit user
confirmation. Recommended next task only after user confirmation.
