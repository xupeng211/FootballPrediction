# DB Write Guard Static Enforcement — Dry-Run Report

**Date:** 2026-06-21
**Phase:** DB_WRITE_GUARD_STATIC_ENFORCEMENT_DRY_RUN
**Branch:** chore/db-write-guard-static-enforcement-dry-run
**Type:** DRY-RUN — no CI hard fail, no DB connection, no script execution

---

## 1. Current JS ops write-guard coverage

| Metric | Count |
|---|---|
| JS ops files scanned | 305 |
| JS ops with write risk | 89 |
| **Guarded** | **16** (12 strict + 4 needs-review) |
| Unguarded P0 candidates | 44 |
| Skipped (complex) | 26 |
| Non-JS advisory (Python/SQL) | 11 |
| Read-only / false positive | 205 |
| Test files | 0 |
| Self-referential | 3 |

## 2. Phase1 + Phase2: all 16 detected

| Phase | Scripts | Detected as guarded |
|---|---|---|
| Phase1 (#1569) | 8 | YES (6 guarded + 2 needs-review) |
| Phase2 (#1571) | 8 | YES (6 guarded + 2 needs-review) |
| **Total** | **16** | **YES, all 16 detected** |

The 4 "needs-review" scripts have guards correctly placed but the scanner's
position heuristic flags them due to guard-in-separate-function pattern. Manual
review confirms all 4 are correctly guarded.

## 3. Remaining unguarded JS ops scripts

44 files flagged as `unguarded_p0_candidate`. Many are likely false positives:

- **Dry-run / audit / preflight scripts** (15+): scripts with "dry_run", "audit",
  "preview", "preflight", "plan" in filename — contain SQL patterns in analysis
  code but do not execute DB writes. Examples:
  `authoritative_workflow_enforcement_dry_run.js`,
  `dataset_status_audit.js`, `training_dataset_leakage_dry_run.js`

- **Write gate scripts** (5+): `l3_features_local_write_gate.js`,
  `match_features_training_local_write_gate.js`,
  `prediction_local_write_gate.js` — already have their own gate systems
  using CONFIRM_* env vars. Should be reviewed for unified guard migration.

- **Schema migration scripts** (2): `raw_match_data_versioned_schema_migration_*.js`
  — have their own authorization systems.

- **Real write entrypoints** (8-12): `gold_pilot_50.js`, `local_dom_ingestor.js`,
  `reset_database.js`, `purge_ghost_data.js`, `l3_stitch_worker.js`,
  `odds_harvest_pipeline.shared.js`, `raw_match_data_local_ingest.js`, etc.
  These are the best candidates for Phase3.

- **dbBlueprint helper**: Located in helpers/ — not a user-facing entrypoint but
  used by many scripts. Guarding it would provide broad coverage but requires
  careful interface design.

## 4. Best candidates for Phase3

Top P0 unguarded candidates (after filtering likely false positives):

1. `reset_database.js` — TRUNCATE raw_match_data/matches/odds/predictions
2. `purge_ghost_data.js` — DELETE matches/odds/training data
3. `gold_pilot_50.js` — INSERT/UPDATE matches, l3_features
4. `local_dom_ingestor.js` — INSERT/UPDATE matches, bookmaker_odds_history
5. `l3_stitch_worker.js` — INSERT/UPDATE raw_match_data/matches/l3_features
6. `raw_match_data_local_ingest.js` — raw_match_data operations
7. `odds_harvest_pipeline.shared.js` — INSERT/UPDATE matches/odds
8. `l3_features_local_write_gate.js` — has own CONFIRM_* gate, needs unified guard migration
9. `match_features_training_local_write_gate.js` — same pattern
10. `prediction_local_write_gate.js` — same pattern

## 5. False positive analysis

The scanner is a naive text-pattern matcher. It flags SQL keywords wherever
they appear, including:

- **Regex/string patterns for analysis** — scripts that search for DB write
  patterns in other files (e.g., `p0_db_write_safety_gate_dry_run.js`)
- **Report generation** — scripts that print SQL or DB status
- **Test fixtures** — scripts that happen to be in scripts/ops but serve as
  test/audit infrastructure

These need a manual review step before enforcement. A future scanner version
could check for actual `pool.query()` or `client.query()` calls with
non-SELECT SQL to reduce false positives.

## 6. Python / SQL / migration enforcement

Should be designed separately:

- **Python scripts** — need a Python equivalent of `db_write_guard.js` using
  `os.environ` checks before SQLAlchemy/psycopg2 write calls
- **SQL migration files** — already governed by migration governance;
  `make data-schema-*` gate
- **dbBlueprint helper** — special case; used by many scripts as an
  infrastructure layer

## 7. Recommended next step

**`p0_db_write_safety_gate_fix_phase3`** — continue script-level guard
integration for the top 8-12 real write entrypoints identified above.

After Phase3, consider **`db_write_guard_static_enforcement_fix_phase1`** —
implement CI check that warns (not fails) on new or modified
`scripts/ops/*.js` with DB write risk but no guard.

## 8. Recommended enforcement strategy

| Phase | What | When |
|---|---|---|
| **Now** (this PR) | Advisory dry-run scanner | Manual use |
| **Phase 3** | More script-level guard integrations | 8-12 more scripts |
| **Enforcement Phase 1** | CI warning on new unguarded JS ops | After Phase 3 |
| **Enforcement Phase 2** | CI fail on new unguarded JS ops | After warning period |
| **Enforcement Phase 3** | CI fail on all unguarded JS ops | After historical debt cleared |
| **Python/SQL** | Separate Python guard + migration governance | Future |

Do NOT fail on all historical debt immediately. Historical unguarded scripts
should remain advisory until each is individually reviewed or fixed.

## 9. CI integration recommendation

The scanner should be added to:
- **ai_workflow_gate.py** — as an additional check (warning mode initially)
- **gatekeeper.sh** — as a pre-commit advisory check

The check should:
- Only examine `scripts/ops/**/*.js` files
- Only flag files that are NEW or MODIFIED in the current diff
- For modified files: check if DB write risk exists AND no guard
- For new files: check if DB write risk exists AND no guard
- Output advisory warning; do NOT fail the gate in initial deployment

## 10. SC-002 status

**SC-002 is NOT fully fixed.** This is partial mitigation only.
Phase1 + Phase2 = 16 of 66 P0 scripts guarded. ~44 candidates remain
(many false positives). Guard is opt-in per script. Training and data
expansion remain blocked.

## Validation

- Scanner runs successfully on 305 files
- Produces valid JSON output via `--json`
- All 16 Phase1+Phase2 scripts detected as guarded
- 68 tests pass (39 guard + 10 phase2 static + 19 scanner)
- No DB connection, no script execution, no real writes
