# L1 Controlled Matches Seed Commit Planning - Phase 5.06L1

## 1. Executive summary

Phase 5.06L1 是 matches seed commit planning 阶段。

本阶段不写 DB，不写 `matches`，不写 `raw_match_data`。目标是为后续受控 matches seed commit 定义 candidate -> matches mapping、upsert、backup 和 rollback policy。

## 2. Background

Phase 5.05L1 已通过受控 FotMob L1 external network candidates preview 找到 8 个 Ligue 1 candidates。

结果包含 `Angers vs Strasbourg`，external id / match id candidate 为 `4830746`。

`raw_match_data.match_id` FK 到 `matches(match_id)`，所以后续 raw JSON 入库前需要先有对应 `matches` seed。

## 3. Implemented files

- `scripts/ops/l1_matches_seed_commit_plan.js`
- `tests/unit/l1_matches_seed_commit_plan.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/L1_CONTROLLED_MATCHES_SEED_COMMIT_PLANNING_PHASE5_06L1.md`

## 4. Mapping policy

Candidate source fields:

- `match_id`
- `external_id`
- `league_name`
- `season`
- `home_team`
- `away_team`
- `match_date`
- `status`
- `is_finished`
- `data_source`

Target `matches` fields:

- `match_id`
- `external_id`
- `league_name`
- `season`
- `home_team`
- `away_team`
- `match_date`
- `status`
- `is_finished`
- `data_source`

Forbidden writes:

- `raw_match_data`
- `bookmaker_odds_history`
- `l3_features`
- `match_features_training`
- `predictions`
- feature / prediction fields
- raw JSON payloads

## 5. Upsert policy

- Use `matches.match_id` as the identity key.
- If `match_id` exists: no delete; planning only marks `would_update`; manual critical fields must not be overwritten unless a future phase explicitly authorizes it.
- If `match_id` does not exist: planning only marks `would_insert`.
- Future commit must run in a transaction.
- Future commit must limit rows to `MAX_SEED_ROWS<=10`.
- Future commit must process only the exact user-confirmed candidate set.
- No `raw_match_data` write is allowed in the matches seed phase.

## 6. Backup / rollback policy

This phase only plans backup and rollback. It does not execute either.

Backup planning:

- Before a future commit, SELECT the exact affected `match_id` rows.
- Affected rows must be output to stdout or to a future user-authorized backup artifact.
- Backup file creation requires future user authorization.
- `pg_dump` is not allowed in this phase.
- Backup file writes are not allowed in this phase.

Rollback planning:

- Future commit must run in a transaction.
- On failure, use `ROLLBACK`.
- If a committed seed is later found wrong, use saved affected rows to prepare reviewed compensation SQL in a future authorized phase.
- Runtime rollback file generation is not allowed in this phase.
- DELETE execution is not allowed in this phase.

## 7. Why this lowers risk

This stage does not jump from candidates directly to writes. It first makes the write rules, affected rows, allowed fields, and rollback path explicit.

The next phase can then authorize only a narrow `matches` seed write. `raw_match_data` stays separate, and training / prediction remain isolated.

## 8. Validation

Executed local validation:

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l1_matches_seed_commit_plan.test.js` passed.
- `make data-l1-matches-seed-commit-plan SOURCE=fotmob SCOPE=league_season_date LEAGUE_ID=53 SEASON=2025/2026 DATE=2026-05-10 CANDIDATE_COUNT=8 CONTAINS_TARGET_MATCH_ID=4830746 CONTAINS_TARGET_LABEL="Angers vs Strasbourg" MAX_SEED_ROWS=10 COMMIT=no` passed and emitted planning-only JSON.
- `make data-l1-matches-seed-commit ... CONFIRM_L1_MATCHES_SEED_COMMIT=1` remained blocked.
- `docker compose -f docker-compose.dev.yml exec -T dev npm test` passed.
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage` passed.
- `git diff --check` passed.
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint scripts/ops/l1_matches_seed_commit_plan.js tests/unit/l1_matches_seed_commit_plan.test.js --no-cache` passed.
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile scripts/ops/l1_matches_seed_commit_plan.js tests/unit/l1_matches_seed_commit_plan.test.js docs/_reports/L1_CONTROLLED_MATCHES_SEED_COMMIT_PLANNING_PHASE5_06L1.md` passed.
- DB row counts were read-only checked after validation: `matches=2`, `bookmaker_odds_history=2`, `raw_match_data=2`, `l3_features=2`, `match_features_training=2`, `predictions=2`.
- `tests/fixtures/l1-config-*` had no filesystem or tracked-file residue.
- `docs/_staging_preview` was absent.

## 9. Recommended next phase

Phase 5.07L1: controlled matches seed commit authorization.

Requirements:

- user explicit authorization
- only process 2026-05-10 Ligue 1 candidates
- rows <= 10
- only write `matches`
- do not write `raw_match_data`
- do not train
- do not predict
- before commit, confirm DB baseline, affected rows, and rollback plan again

## 10. Explicit non-execution

- no external FotMob access
- no network dry-run
- no titan_discovery execution
- no DiscoveryService.discover execution
- no FixtureRepository.persist
- no DB writes
- no matches writes
- no raw_match_data writes
- no feature writes
- no prediction writes
- no harvest / ingest
- no training / prediction
- no file deletion
