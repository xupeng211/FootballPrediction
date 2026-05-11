# FotMob Stdout-Only Network Dry-Run Execution Plan - Phase 5.00F

## 1. Executive summary

Phase 5.00F creates a FotMob stdout-only network dry-run execution plan template.
It does not access FotMob, collect real data, write DB rows, or write staging.

The execution plan is not execution and is not final authorization. Phase 5.00F
should stop further template expansion and wait for user-provided real input.

## 2. Implemented files

- `docs/runbooks/FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_EXECUTION_PLAN_TEMPLATE.md`
- `scripts/ops/fotmob_stdout_network_dry_run_execution_plan.js`
- `tests/unit/fotmob_stdout_network_dry_run_execution_plan.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/FOTMOB_STDOUT_NETWORK_DRY_RUN_EXECUTION_PLAN_PHASE5_00F.md`

## 3. Execution plan sections

- `authorization_packet`: requires a future user-filled authorization packet.
- `target`: keeps FotMob scope empty, single-target, and max one target.
- `runtime_policy`: keeps stdout-only intent and blocks network, browser, proxy,
  legacy runtime, and acquisition engine execution in this phase.
- `output_policy`: blocks stdout preview execution, staging writes, source
  manifest writes, and packet writes in this phase.
- `data_safety_policy`: blocks DB writes, training, prediction, and model artifact
  loading.
- `pre_execution_checks`: lists required checks, all unchecked and unpassed.
- `abort_conditions`: lists conditions that must stop future execution.
- `stdout_preview_expected_shape`: defines bounded future stdout summary shape.
- `post_run_review`: documents required review after a future execution.
- `codex_constraints`: blocks self-filled target, terms, authorization, execution,
  and runtime file writes.
- `safety`: confirms all `would_*` actions remain false.
- `execution_blocking_reasons`: records why Phase 5.00F remains blocked.
- `next_step_after_phase_5_00f`: stops template phases and requires user input.

## 4. Execution boundary

- The execution plan is not execution.
- `target_count=0` by default.
- `external_network_allowed=false` by default.
- `execution_allowed=false` by default.
- `stdout_preview_allowed=false` by default.
- `staging_write_allowed=false` by default.
- DB write remains false by default.
- Future user input is required before any execution.
- Future explicit execution confirmation is required after user input.

## 5. Validation

Local validation completed for this phase:

- Unit tests passed for missing parameters, invalid YAML, unsafe field changes,
  valid execution plan preview, blocked commit gate, Makefile targets, and
  no-side-effect guards.
- Valid execution plan preview through Makefile passed.
- Blocked commit target through Makefile returned blocked as expected.
- `npm test` passed.
- `npm run test:coverage` passed.
- `npm run test:integration` was skipped locally because the integration suite
  includes Playwright / Chromium browser automation paths, which are outside
  Phase 5.00F no-browser/no-network constraints.
- `git diff --check` passed.
- ESLint and Prettier checks passed.
- DB row-count review remained unchanged.
- `l1-config-*` residue remained absent.
- `docs/_staging_preview` remained absent.

## 6. Recommended next action

Do not continue to Phase 5.01F automatically.
Do not continue adding empty templates.

The next action should be user-provided real FotMob dry-run parameters:

- real FotMob target
- target type: `match_id` or `league_season_date`
- target URL, if any
- source homepage URL
- terms URL
- license URL, if any
- allowed-use summary
- explicit stdout-only network authorization
- browser policy
- proxy policy
- staging policy
- no DB write confirmation
- no training confirmation
- no prediction confirmation
- final human confirmation

Only after those real parameters and authorization are provided should the project
enter a final pre-execution confirmation for the first stdout-only single-target
network dry-run.

## 7. Explicit non-execution

Phase 5.00F did not execute:

- external FotMob access
- external football data access
- external odds data access
- `curl` / `wget`
- browser automation
- proxy runtime
- scraping
- harvest
- ingest
- batch backfill
- network dry-run
- staging write
- source manifest write
- packet runtime write
- execution plan runtime write
- DB writes
- `pg_dump` / `pg_restore`
- training
- prediction
- file deletion
- legacy FotMob runtime execution
