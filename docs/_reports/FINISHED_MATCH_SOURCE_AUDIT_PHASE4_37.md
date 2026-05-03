# Phase 4.37 - Finished Match Source Audit / Historical Sample Acquisition Runbook

## Current HEAD

- Base HEAD: `724f5bdf873c852504b50fd75429e018680e93cc`
- Working branch: `docs/finished-match-source-audit-phase437`

## Current DB / Dataset Status

Current dev DB remains unchanged from Phase 4.36:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

`make data-dataset-status` still reports:

- `finished_matches = 0`
- `matches_with_actual_result = 0`
- `matches_with_scores = 0`
- `trainable_label_rows = 0`
- `scheduled_or_unlabeled_rows = 1`
- `trainable = false`

Current local closure is still useful only as pipeline wiring evidence. It is not a real training dataset.

## Local File Scan Summary

Read-only local scan found:

- total files scanned: `40`
- CSV files: `2`
- JSON files: `38`

Primary directories with useful candidate samples:

- `data/mock/`
- `tests/fixtures/`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/data/fixtures/`
- `tests/mocks/`

Non-source files also appeared in the scan:

- config JSON
- package metadata JSON
- docs audit artifacts

These are not candidate ingestion sources and should be excluded from any future import gate.

## Candidate Finished-Match Samples

### High-value local CSV candidate

`data/mock/sample_history.csv`

- 4 rows total
- 3 unique `match_id`
- status distribution:
    - `scheduled = 3`
    - `finished = 1`
- rows with score columns populated: `1`

Header:

```text
match_id, external_id, league_name, season, home_team, away_team, match_date,
status, bookmaker_name, market_type, open_home, open_draw, open_away,
close_home, close_draw, close_away, home_score, away_score
```

Assessment:

- best current local candidate for Phase 4.38 dry-run
- includes match identity, date, teams, status, odds, and optional score
- already contains one finished row with `home_score=1`, `away_score=0`
- also contains scheduled rows and one malformed `match_date=not-a-date`, so the next gate must validate and isolate bad rows instead of assuming all rows are importable

### Historical evaluation CSV, not a primary source-of-truth

`docs/audit/yield_audit_data_20251223_182618.csv`

- 816 rows
- includes:
    - `match_time`
    - `home_team`
    - `away_team`
    - `result_score`
    - `predicted_result`
    - bookmaker odds columns
- does not provide the full identity / provenance expected for direct historical import into the current schema

Assessment:

- useful as evaluation / audit evidence
- not suitable as the first historical import source
- should not be treated as authoritative raw source data

## Candidate JSON / Fixture Samples

### Finished raw-style match payload

`tests/fixtures/match_success.json`

- `matchId = 55_20242025_4803413`
- `general.status = FINISHED`
- `general.score = { home: 2, away: 0 }`
- has stats, lineup, and shotmap

Assessment:

- good local finished raw payload example
- useful for schema mapping and fixture-based dry-run design
- likely useful for raw / L3 feature dry-run design
- contains post-match content, so future training feature extraction must enforce kickoff-time leakage rules

### Existing scheduled raw fixture

`tests/fixtures/l3/raw_match_data_phase419_sample.json`

- current local closure sample
- `general.finished = false`
- `header.status.finished = false`
- `scoreStr = - - -`

Assessment:

- useful only for scheduled local closure testing
- not a finished-match label source

### Legacy premium finished match sample

`tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`

- `match_id = 4813415`
- `general.finished = true`
- `header.status.finished = true`
- `scoreStr = 0 - 0`
- `feature_count = 7591`
- includes `extracted_features`

Assessment:

- strong fixture candidate for finished raw + feature mapping analysis
- useful for future adapter design
- must not be treated as a training-ready row without timing / schema / provenance review

### Legacy finished FotMob response

`tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/mock_responses/fotmob_success.json`

- `match.id = 4147463`
- `finished = true`
- `scoreStr = 2-1`
- includes stats

Assessment:

- useful as compact finished-match API-style response sample
- good for fixture-based parsing validation
- not a full training dataset on its own

### Legacy dataset fixture, not label-ready

`tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/data/fixtures/example_dataset.json`

- `matches` length: `50`
- all `matches[].status = scheduled`
- includes predictions and model metadata

Assessment:

- not a finished-match source
- not a training label source
- contains prediction/model data and should not be used to backfill labels

### Odds-only mock

`tests/mocks/fulham_api_sample.json`

- has match identity and bookmaker odds structure
- no clear result label

Assessment:

- useful for odds mapping
- not a finished label source

## Label / Feature Source Findings

### Label-ready sources found

Yes, but only at small local-fixture scale:

- `data/mock/sample_history.csv`
    - one finished row with scores
- `tests/fixtures/match_success.json`
    - finished status and explicit score
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`
    - finished status and score string
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/mock_responses/fotmob_success.json`
    - finished status and score string

### Raw / L3 / training feature candidates found

Yes:

- `tests/fixtures/match_success.json`
- `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`
- `tests/mocks/fulham_api_sample.json`

### Important limitation

No local source currently provides a ready-to-train multisample finished dataset with:

- enough sample count
- explicit label quality controls
- kickoff-time leakage controls
- stable schema mapping
- safe dry-run import gate

## Existing Ingest / Seed / Loader Risk Audit

### `make data-local-dry-run`

Current behavior:

- local HTML preview via `scripts/ops/local_dom_ingestor.js`
- local CSV preview via `scripts/ops/csv_bulk_loader.js`

Safety:

- local-only input
- default preview path
- no explicit network call in the gate itself

Limitations for finished historical samples:

- CSV path currently targets the generic bulk loader, not a finished-match-specific audit gate
- no dedicated label-readiness summary
- no `LIMIT`, `MATCH_ID`, or source classification output
- not tailored for would-insert / would-update match previews

### `scripts/ops/csv_bulk_loader.js`

Observed behavior:

- supports `--file`
- supports `--batch-size`
- supports `--error-log`
- supports `--commit`

Dry-run behavior:

- parses local CSV
- validates rows
- resolves against existing `matches` via SELECT
- prints dry-run row previews

Commit behavior:

- opens DB transaction
- can sync resolved `matches`
- can write `bookmaker_odds_history`
- can run migration-backed table ensure logic on commit path

Risk assessment:

- not safe for Phase 4.37 execution with `--commit`
- not a dedicated historical finished-match import gate
- assumes existing match alignment logic rather than a new finished-source audit policy
- no explicit `limit`, `match_id`, or source-dir support

### `scripts/ops/local_dom_ingestor.js`

Observed behavior:

- local HTML / clipboard parser
- default preview mode
- `--commit` writes `bookmaker_odds_history`
- no network by design for local file mode

Risk assessment:

- useful for local HTML odds preview
- not a finished historical CSV / JSON acquisition gate
- commit mode remains out of scope

### `scripts/ops/raw_match_data_local_ingest.js`

Observed behavior:

- fixture-based
- requires `--fixture` and `--match-id`
- SELECT-only DB checks
- `--commit` blocked / not wired

Risk assessment:

- good model for future finished JSON dry-run gate design
- currently single-fixture, single-match only
- not a multisample historical import path

### `scripts/ops/seed_fixtures.js`

Observed behavior:

- L1 discovery seed path
- not a dry-run gate
- not local finished sample import
- tied to discovery service workflow

Risk assessment:

- not suitable for Phase 4.37
- should not be used as a substitute for local finished historical sample audit

## Acquisition Source Tier Strategy

### Level 0: local samples already in repo

Examples:

- `data/mock/sample_history.csv`
- `tests/fixtures/match_success.json`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/mock_responses/fotmob_success.json`

Policy:

- highest priority
- lowest operational risk
- use first for mapping, schema audit, and dry-run gate design
- no network access required

### Level 1: public CSV sources, manually staged locally first

Examples:

- football-data.co.uk historical CSV
- other public CSV / Kaggle / openly published datasets

Policy:

- do not download in this phase
- first write acquisition runbook
- require human review of license, intended use, and data quality
- require manual placement into a local fixture directory
- only then run a future local dry-run gate

### Level 2: open event-data sources

Examples:

- StatsBomb open-data

Policy:

- do not access in this phase
- require explicit license / research-use review
- schema mismatch with current betting-odds pipeline must be documented first
- requires a dedicated adapter runbook instead of direct ingestion

### Level 3: external harvest / scrape

Examples:

- production harvesters
- scraper-driven historical backfill
- live / remote discovery and recon routes

Policy:

- still prohibited
- requires separate authorization
- requires rate-limit, robots, and terms review
- must go through Makefile safety gates
- must not be used before local source audit and dry-run gate design are complete

## External Data Source Use Principles

- Do not treat “public” as automatically permitted.
- Require human confirmation of license, redistribution limits, and training use policy.
- Prefer local fixture staging over direct online access.
- Separate schema mapping review from ingestion authorization.
- Preserve provenance:
    - original source
    - acquisition date
    - coverage window
    - license notes
    - transformation notes

## Why This Phase Does Not Harvest / Scrape

This is not the right phase for external data collection because:

- current dev DB still has zero trainable label rows
- local source audit was not yet completed before this phase
- there is not yet a dedicated finished CSV / JSON dry-run gate
- external collection without a runbook would bypass current safety sequencing
- model training remains blocked until dataset readiness is demonstrated

The correct next move is to validate local sample mapping and dry-run behavior first.

## Recommended Next Phase

Recommended next phase:

```text
Phase 4.38: local finished CSV sample import dry-run gate
```

Suggested scope:

- use `data/mock/sample_history.csv` as initial local fixture
- read-only dry-run only
- detect finished vs scheduled rows
- validate `match_date`
- derive `would_insert_matches` / `would_update_matches` preview only
- report label-ready rows and reject malformed rows
- no DB writes
- no training
- no prediction
- no external access

## Explicit Non-Execution

This phase did not execute:

- `INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE`
- `COPY / \copy`
- DB writes
- external download
- `curl`
- `wget`
- `git clone`
- model training
- real prediction execution
- model artifact loading
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- dataset export
- Docker volume cleanup
