# Controlled Small-Batch Smelt Readiness Plan

Status: plan-only / no-write

## Purpose

Define the readiness criteria and execution guardrails for a future controlled small-batch smelt from `raw_match_data` into `l3_features`.

This document does not authorize a write.

## Current protected state

- Prematch-safe contract document exists (`docs/data/l3_prematch_safe_feature_contract.md`).
- Machine-readable L3 contract exists (`config/features/l3_prematch_safe_contract.v0.json`).
- Training entrypoints are protected by contract filter (`scripts/ops/train_model.py`, `scripts/model_training/train_baseline_v1.py`).
- Prediction path is protected by contract filter (`src/database/repositories/prediction_repo.py`).
- `dataset_generator.py` is marked legacy / non-production (`src/ml/dataset/dataset_generator.py`, `docs/data/dataset_generation_legacy_status.md`).

## Absolute blocked actions in this plan

- No DB write.
- No smelt.
- No batch smelt.
- No controlled smelt.
- No training.
- No prediction run.
- No backtest.
- No FotMob network.
- No scraper / collector / browser.

## Readiness checks before any future write

A future controlled smelt may only be considered after all are true:

1. Worktree clean.
2. Main CI green.
3. Current branch is main or explicitly authorized smelt branch.
4. `l3_prematch_contract` exists and tests pass.
5. Training entrypoints use the contract filter.
6. Prediction path uses the contract filter.
7. `dataset_generator.py` is marked legacy / non-production.
8. SELECT-only DB baseline captured immediately before write.
9. Target match list is explicit and small.
10. `--preview --no-write` has been run successfully for the exact target.
11. Expected delta is documented before write.
12. Rollback SQL is documented before write.
13. User explicitly authorizes the write task.

## Recommended batch size

Start with:

- 1 match if re-validating write mechanics;
- 5 matches for first small-batch expansion;
- never jump directly to all pending matches.

## Preferred target selection

Prefer:

- `data_version = 'fotmob_live_v1'`
- `matches.external_id IS NOT NULL`
- no existing `l3_features` row
- recent enough for parser compatibility
- no synthetic data versions
- no legacy PHASE synthetic rows

Avoid:

- `PHASE4.43_SYNTHETIC`
- `PHASE4.23`
- unknown or synthetic data versions
- rows without `external_id`
- rows already present in `l3_features`

## Required pre-write baseline

Capture:

```sql
SELECT COUNT(*) FROM raw_match_data;
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM l3_features;
SELECT data_version, COUNT(*) FROM raw_match_data GROUP BY data_version;
```

Also capture explicit target match IDs.

## Required preview

Before any future write:

```bash
node scripts/ops/smelt_all.js --preview --no-write --limit <N>
```

Preview must show:

- target match IDs;
- `data_version`;
- expected feature group counts;
- `actual_db_write=false`;
- raw/matches/l3 counts unchanged.

## Required future write envelope

Future write must be a separate task and must include explicit user authorization.

The write entrypoint is `scripts/ops/smelt_all.js`. Write mode is active when **none** of `--dry-run`, `--no-write`, or `--preview` is passed.

FeatureSmelter reads from `raw_match_data` (JOIN `matches` on `match_id`, LEFT JOIN `l3_features` on `match_id`), generates features via extractors, and writes only to `l3_features` table (INSERT/UPDATE operations only). It does **not** write to `raw_match_data` or `matches`.

Expected environment:

- Dev container with DB access.
- `l3_features` table exists (created by migration `V26.4__create_l3_features_table.sql`).
- No additional environment variables required beyond standard DB connection config.

The future write must be limited:

```bash
node scripts/ops/smelt_all.js --limit <N>
```

Only after required environment confirmations.

## Required post-write verification

After future write, verify:

```sql
SELECT COUNT(*) FROM raw_match_data;
SELECT COUNT(*) FROM matches;
SELECT COUNT(*) FROM l3_features;
```

Expected:

- `raw_match_data` delta = 0
- `matches` delta = 0
- `l3_features` delta = N
- every inserted row has non-empty prematch-safe groups after contract filtering
- no training/prediction/backtest automatically follows

## Rollback plan

For a controlled write, rollback must be explicit and limited to the inserted match IDs:

```sql
DELETE FROM l3_features
WHERE match_id IN ('...');
```

Rollback must not be executed unless user explicitly authorizes it.

## Training dry-run policy

Training dry-run remains blocked after smelt unless:

1. smelt target rows are verified;
2. contract-filtered training feature matrix is inspected;
3. no tactical/rating/postmatch leakage appears;
4. user explicitly authorizes training dry-run as a separate task.

## Next task after this plan

Possible next task:

GOLD-AUDIT-2L: Controlled small-batch smelt preview only

or

GOLD-AUDIT-2L: Controlled small-batch smelt write for 1–5 explicitly listed matches

No task should start automatically.
