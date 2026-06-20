# Formal Training Dataset Design Dry-Run
- lifecycle: phase-artifact
- scope: read-only formal training dataset design; not real training
- report filename fixed by task: `20260619`
- audit executed on: `2026-06-20`
- base branch snapshot: `origin/main@dc74eebeb279cee125d9dade5983e3e94f4e02d8`

## Nature

This is **dry-run / design only**, not model training.

No DB write, no migration, no schema change, no live fetch, no raw payload output, no model artifact, no prediction change, no betting logic.

## Current State

- `matches=60`
- `raw_match_data=76`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`
- finished labeled matches in local DB: `59`
- current smoke training-eligible rows: `58`
- current real training scope: only `Ligue 1 2025/2026`
- formal full feature-chain rows suitable for a clean supervised dataset: `0`

## Why The 58 Smoke Rows Cannot Be Used For Formal Training

- They come from one competition and one season only, so league bias and season bias are uncontrolled.
- `venue` and `referee` are both `58/58` missing in the current smoke scope.
- `raw_match_data` is mixed provenance, not one clean raw contract: `fotmob_live_v1=58`, `fotmob_html_hyd_v1=8`, `fotmob_pageprops_v2=8`, plus legacy/synthetic rows.
- Downstream feature tables are not a formal corpus: `match_features_training=2`, with `1` row on a scheduled match, `1` unlabeled row, and both rows `feature_count=0`.
- Odds coverage is effectively absent for training design: `2` odds rows covering only `1` match.
- `matches` has no stable `home_team_id` / `away_team_id` / `league_id`, so historical joins are still identity-risky if they rely only on team names.
- Existing training entrypoints are not formal-dataset-safe: the current `scripts/ops/train_model.py` does random `train_test_split` and writes model/scaler artifacts.

## Recommended Formal Corpus

- Official minimum baseline: `3000` finished labeled matches.
- Pilot floor for internal experimentation only: `1500` finished labeled matches.
- Preferred stable baseline: `5000+` finished labeled matches.
- Minimum competition spread: `3` competitions.
- Preferred competition spread: `5` competitions.
- Minimum completed seasons per competition: `3`.
- Minimum competition set: `Premier League`, `La Liga`, `Ligue 1`.
- Preferred official set: `Premier League`, `La Liga`, `Serie A`, `Bundesliga`, `Ligue 1`.
- Preferred first training seasons: `2022/2023`, `2023/2024`, `2024/2025`.
- Preferred first out-of-time holdout: `2025/2026`, but only after that season is fully acquired and frozen.

## X / y Contract

- Dataset grain: one row per `match_id` per `prediction_horizon`.
- Label field `y`: `actual_result` with values `home_win`, `draw`, `away_win`.
- Label fallback: derive from final scores only for finished matches when `actual_result` is missing.
- Direct safe fields available now: `league_name`, `season`, `home_team`, `away_team`, `match_date`.
- Optional direct fields when truly available before kickoff: `venue`, `referee`.
- Metadata kept outside `X`: `match_id`, `external_id`, future canonical IDs, `kickoff_time`, `prediction_horizon`, `prediction_cutoff_time`, schema/hash metadata.

## Leakage Policy

- Forbidden from `X`: `actual_result`, `home_score`, `away_score`, `status`, `is_finished`, current-match corners/cards/reds.
- Forbidden from `X`: `collection_date`, `created_at`, `updated_at`, because they encode post-hoc pipeline timing.
- Forbidden from raw payload: `content.matchFacts`, `content.stats`, `content.playerStats`, `content.shotmap`, `content.momentum`.
- Forbidden from downstream tables: `predictions` rows, scheduled/unlabeled `match_features_training` rows, any feature family with unresolved cutoff provenance.

## Derived Feature Priorities

- `P0`: pre-match ELO strength.
- `P0`: recent form from prior finished matches only.
- `P0`: home/away split form from prior finished matches only.
- `P1`: historical H2H aggregates.
- `P1`: rest days / congestion / schedule pressure.
- `P1`: timestamp-safe standings snapshot.
- `P1`: cutoff-safe odds snapshots from a separate market source.
- `P2`: confirmed lineup / availability for late-horizon models only.

## Temporal Cutoff Rules

- Every row must persist `kickoff_time` and `prediction_cutoff_time`.
- Every feature must satisfy `feature_observed_at <= prediction_cutoff_time <= kickoff_time`.
- Historical aggregates may use only prior matches with `historical_match_time < current kickoff_time`.
- `T_MINUS_24H` cannot use closing odds or late lineup data.
- `T_MINUS_6H` can use only odds and context captured at or before `T-6h`.
- `T_MINUS_1H` can add lineup context only if `lineup_timestamp <= prediction_cutoff_time`.
- `CLOSING_OR_NEAR_KICKOFF` can use near-kickoff odds only if captured before kickoff.
- All validation/test splits must be chronological; no random time-mixing.

## Builder Design

1. Select the authorized competition/season cohort and exclude synthetic, scheduled, cancelled, or policy-ambiguous rows.
2. Normalize team/league identity with a version-aware raw reader instead of name-only joins.
3. Expand each match into explicit prediction horizons and compute `prediction_cutoff_time`.
4. Build direct schedule/context features from `matches`.
5. Build historical aggregates only from prior finished matches.
6. Join odds or lineup features only when their timestamps are at or before cutoff.
7. Freeze `X` first, then derive `y`.
8. Emit a dataset manifest with counts, missingness, class balance, feature families, schema version, and data hash.

## Missing Data Before Formal Training

- Multi-competition, multi-season historical match inventory is missing.
- Canonical pageProps-v2 identity coverage exists for only `8` matches.
- Cutoff-safe odds history is missing at scale.
- Current downstream feature tables are local closure artifacts, not a cleanroom training set.
- Formal `feature_time` / `prediction_cutoff_time` lineage is not yet stored for reusable derived features.

## Next Recommended Task

Do not start automatically.

Recommended next task only after explicit user confirmation:

- `formal_training_cohort_inventory_dry_run`
- Goal: produce a read-only inventory/gap audit for the exact official training cohort across the recommended competitions/seasons, so the future acquisition scope is explicit before any builder implementation or data expansion
