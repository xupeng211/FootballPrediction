# Training Eligibility Dry-Run Report

- lifecycle: phase-artifact
- generated: 2026-06-19
- branch: data/training-eligibility-dry-run
- script: scripts/ops/training_eligibility_dry_run.js
- test: tests/unit/training_eligibility_dry_run.test.js
- policy: docs/_reports/training_eligibility_policy_design_20260619.md

## Nature

Read-only dry-run for future `is_training_eligible` backfill. Evaluates all 60
matches against the 6-rule training eligibility policy. No DB write.

## Execution Command

```bash
docker compose -f docker-compose.dev.yml exec -T dev \
  node scripts/ops/training_eligibility_dry_run.js --json
```

## Current State

| Metric | Count |
|--------|-------|
| total matches | 60 |
| is_training_eligible=true | 0 |
| is_training_eligible=false | 60 |

## Dry-Run Summary

| Metric | Count |
|--------|-------|
| would_set_true_count | **0** |
| would_keep_false_count | **60** |

## by_reason

| Reason | Count | Description |
|--------|-------|-------------|
| no_valid_scores: home_score or away_score is null | **58** | Ligue 1 2025/2026 matches have no scores |
| forbidden_evidence: synthetic_invalid | **2** | Synthetic data permanently excluded |

## 58 Ligue 1 2025/2026 Analysis

All 58 matches pass most training eligibility gates:
- ✅ source_type=fotmob_live_fetch (valid)
- ✅ evidence_level=strong
- ✅ status=finished
- ✅ is_production_scope=true
- ✅ is_reconciliation_eligible=true
- ✅ pipeline_status=harvested
- ✅ pipeline_status_reason=NULL

**Blocker**: All 58 matches have `home_score=NULL` and `away_score=NULL`.
Training requires known outcomes (labels). Scores must be backfilled before
these matches can be `is_training_eligible=true`.

Additional conditional blocker: Feature leakage policy and prediction cutoff
time are not yet defined. Even after scores are backfilled, training eligibility
remains conditional on these policies.

## 2 No-Raw Excluded Analysis

| match_id | Reason |
|----------|--------|
| 140_20252026_4837496 | forbidden_evidence: synthetic_invalid |
| 47_20242025_900002 | forbidden_evidence: synthetic_invalid |

Both matches are permanently excluded from training.

## Risk Flags

1. All would_set_true rows are conditional on feature leakage policy and cutoff
   time definition
2. WARNING: feature leakage policy and prediction cutoff time are NOT yet
   defined — training eligibility remains conditional
3. 58 Ligue 1 matches lack scores — score backfill is a prerequisite

## Safety

- No migration
- No schema change
- No DB write
- No backfill
- No live fetch
- No raw payload output
- No parser/training/prediction changes

## Next Step

Do not start automatically.
Two prerequisites before training eligibility can be set to true:
1. Score backfill for the 58 Ligue 1 matches
2. Feature leakage policy and cutoff time definition
Recommended next task only after user confirmation.
