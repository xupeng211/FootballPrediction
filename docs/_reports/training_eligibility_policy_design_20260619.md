# Training Eligibility Policy Design

- lifecycle: phase-artifact
- generated: 2026-06-19
- branch: docs/training-eligibility-policy-design
- type: design proposal, not execution
- previous: #1551 feat(data): execute matches labeling backfill write

## Nature

This is a **design report**, not an execution. It proposes the policy for future
`is_training_eligible` backfill and usage. No code changes, no DB writes, no
backfill. All analysis is based on SELECT-only audit of the current 60 matches.

## Current State (Post-#1551)

| Metric | Count |
|--------|-------|
| total matches | 60 |
| fotmob_live_fetch (strong) | 58 |
| synthetic (synthetic_invalid) | 2 |
| is_production_scope=true | 58 |
| is_reconciliation_eligible=true | 58 |
| is_training_eligible=true | **0** |
| is_training_eligible=false | 60 |

All 60 matches currently have `is_training_eligible=false` — the conservative
default from MatchLabelingGovernance V26.7.

### Ligue 1 2025/2026 (58 matches)

| Field | Value |
|-------|-------|
| status | finished |
| pipeline_status | harvested |
| source_type | fotmob_live_fetch |
| evidence_level | strong |
| is_production_scope | true |
| is_reconciliation_eligible | true |
| is_training_eligible | false |
| pipeline_status_reason | NULL |

### No-Raw Excluded (2 matches)

| match_id | source_type | evidence_level | status |
|----------|-------------|----------------|--------|
| 140_20252026_4837496 | synthetic | synthetic_invalid | scheduled |
| 47_20242025_900002 | synthetic | synthetic_invalid | finished |

## Proposed Training Eligibility Rules

### Rule 1: Evidence Quality Gate

A match may be training-eligible only if:
- `source_type` IN (`fotmob_live_fetch`, `fotmob_html_hydration`, `fotmob_pageprops`)
- `evidence_level` IN (`strong`, `medium`)
- `source_type` NOT IN (`synthetic`, `manual_seed`, `local_csv`, `unknown`)

**Rationale**: Training on synthetic/manual/CSV data would produce a model that
learns from fabricated patterns, not real football outcomes. Synthetic data is
permanently excluded from training.

### Rule 2: Match Completion Gate

A match may be training-eligible only if:
- `status` = `finished`
- `actual_result` (home_score / away_score) is present and valid
- No `scheduled` or `in_progress` matches

**Rationale**: Training requires known outcomes (labels). Matches that haven't
finished have no ground truth.

### Rule 3: Feature Leakage Prevention Gate

A match may be training-eligible only if:
- `match_date` (kickoff time) is before `prediction_cutoff_time`
- Features are computed from data available BEFORE kickoff only
- Post-match statistics (corners, cards, possession, shots) are NOT used as
  pre-match features

**Rationale**: Data leakage is the most common ML failure mode in sports
prediction. Using post-match data to predict the same match inflates accuracy
and produces a useless model.

### Rule 4: Production Scope Alignment

A match should be training-eligible only if:
- `is_production_scope` = true
- League and season match the current production target

**Rationale**: Training should focus on the league/season the model will predict.
Mixing non-production leagues dilutes signal. However, this rule may be relaxed
in the future when multi-league strategy is defined.

### Rule 5: Pipeline Completion

A match may be training-eligible only if:
- `pipeline_status` IN (`harvested`, `RECON_LINKED`)
- `pipeline_status_reason` IS NULL (no blockers)
- Raw data is stored and parseable

**Rationale**: Matches with active blockers (failed, skipped, awaiting completion)
should not enter training until the pipeline issue is resolved.

### Rule 6: Reconciliation Gate (Conditional)

`is_reconciliation_eligible=true` is a **prerequisite** for training but
NOT sufficient. Reconciliation eligibility means the match has strong FotMob
evidence and is in production scope. Training additionally requires:
- Known outcome (finished + scores)
- Leakage-safe features
- Pipeline health

A match can be reconciliation-eligible but not training-eligible (e.g., if
features aren't computed yet). Conversely, training eligibility should never
exceed reconciliation eligibility.

## Data Types: Training Eligibility Summary

| source_type | evidence_level | Eligible? | Reason |
|-------------|----------------|-----------|--------|
| fotmob_live_fetch | strong | **Yes** (if all rules pass) | Real FotMob data, strong evidence |
| fotmob_html_hydration | medium | **Conditional** | May be eligible with additional validation |
| fotmob_pageprops | medium | **Conditional** | Same as above |
| manual_seed | weak | **No** | Not real data source |
| local_csv | weak | **No** | Provenance uncertain |
| synthetic | synthetic_invalid | **Never** | Fabricated data, zero training value |
| unknown | missing | **Never** | No evidence at all |

## 58 Ligue 1 Matches: Recommendation

**Recommended**: Allow `is_training_eligible=true` for all 58 Ligue 1 2025/2026
matches AFTER the following conditions are verified:

1. All 58 matches have `status=finished` with valid scores ✅ (confirmed)
2. All 58 have `is_production_scope=true` ✅ (confirmed)
3. All 58 have `is_reconciliation_eligible=true` ✅ (confirmed)
4. All 58 have `pipeline_status_reason=NULL` ✅ (confirmed)
5. Features can be computed without leakage (requires feature engineering audit)
6. Prediction cutoff time policy is defined (requires separate planning)
7. Training dataset readiness audit is completed (requires separate planning)

**Immediate blocker**: Feature leakage policy and cutoff time are not yet
defined. Training eligibility cannot be set to true until these are resolved.

## 2 No-Raw Excluded Matches: Recommendation

**Recommended**: Keep `is_training_eligible=false` **permanently**.

| match_id | Reason |
|----------|--------|
| 140_20252026_4837496 | synthetic data, scheduled (no outcome), non-production league |
| 47_20242025_900002 | synthetic data, non-production league, synthetic_raw_not_valid |

These matches have zero training value. Synthetic data contaminates training
sets and produces unreliable models. They must never be training-eligible.

## Key Design Questions Answered

### Q1: Can 58 Ligue 1 matches enter training?

**Yes, in principle.** They meet all governance prerequisites. But training
eligibility must wait for feature leakage policy and cutoff time definition.

### Q2: Why can't the 2 no-raw matches enter training?

Synthetic data (`PHASE4.43_SYNTHETIC` / `PHASE4.23`) is fabricated. It has no
relationship to real match outcomes. Training on synthetic data would teach the
model patterns that don't exist in reality.

### Q3: Is synthetic_invalid permanently excluded?

**Yes.** `evidence_level=synthetic_invalid` means the data is provably not real.
It must never enter training, regardless of any future policy changes.

### Q4: Is reconciliation_eligible equal to training_eligible?

**No.** Reconciliation eligibility means the match has strong, verified FotMob
evidence and is in production scope — it's ready for identity reconciliation.
Training eligibility additionally requires:
- Finished match with known scores (label availability)
- Leakage-safe feature computation
- Pipeline completion with no blockers
- Defined prediction cutoff time

Current data: 58 reconciliation-eligible, 0 training-eligible. The gap is by
design — training requires additional gates beyond reconciliation.

### Q5: What else is needed beyond strong evidence?

1. Feature leakage audit and prevention policy
2. Prediction cutoff time definition
3. Training dataset readiness (label balance, temporal split, no look-ahead)
4. Feature computation pipeline that respects cutoff time
5. Model evaluation framework that validates no leakage

### Q6: What dry-run checks are needed before backfill?

Before any `is_training_eligible` backfill write:
1. SELECT-only audit of all candidate matches
2. Verify all candidates have `status=finished`
3. Verify all candidates have valid `actual_result`
4. Verify feature leakage policy is documented and approved
5. Compute `would_set_true` / `would_keep_false` counts
6. Flag any candidate with unresolved pipeline blockers
7. User must explicitly authorize the write after reviewing dry-run results

## Phased Implementation Plan

### Phase A: Policy Design (this PR) ✅

Deliverable: this design report. No code, no DB write.

### Phase B: Training Eligibility Dry-Run

- Add `computeTrainingEligibility` logic to MatchLabelingGovernance
- Run dry-run showing `would_set_true` / `would_keep_false` per match
- Report per-match reasons for false
- No DB write

### Phase C: Authorized Backfill Write

- User explicitly authorizes write after reviewing Phase B results
- Single-transaction UPDATE of `is_training_eligible` only
- Preflight gate confirms expected counts
- Post-write verification

### Phase D: Training Pipeline Integration

- Feature engineering reads `is_training_eligible` to filter training set
- Training dataset builder excludes `is_training_eligible=false`
- Model evaluation validates no leakage

## Risk Flags

- **No cutoff time policy**: Training without cutoff risks data leakage
- **Feature leakage**: Post-match stats must not be pre-match features
- **Single league risk**: Training on Ligue 1 only may overfit to one league
- **58 samples is small**: May need additional leagues/seasons for robust model
- **Synthetic data proximity**: 2 synthetic rows exist in the same table; must
  ensure they're never accidentally included in training sets

## Safety

- No migration
- No schema change
- No code change
- No DB write
- No backfill
- No live fetch
- No raw payload output
- No parser/training/prediction changes

## Next Step

Do not start automatically. User must explicitly confirm this design before
proceeding to Phase B (training eligibility dry-run). Recommended next task
only after user confirmation.
