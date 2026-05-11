# FotMob Single-Target Adapter Scaffold

Phase: 4.97F
Status: scaffold-only, no-network preflight
Starting HEAD: `ea9fa12cb7c8b6f2ec05dd89d6d89e3f7b8cdf01`

## 1. Executive Summary

Phase 4.97F adds a FotMob trusted single-target adapter scaffold.

This is not a network dry-run. It does not access FotMob, collect data, write DB rows, or
write staging artifacts. It only provides parameter validation, dependency injection
shape, no-network preflight, and stdout-only JSON summary behavior.

The scaffold keeps FotMob legacy runtime blocked and proves the first future adapter path
can remain no-side-effect by default.

## 2. Implemented Files

- `scripts/ops/fotmob_single_target_adapter_scaffold.js`: FotMob single-target adapter
  scaffold CLI and exported testable functions.
- `tests/unit/fotmob_single_target_adapter_scaffold.test.js`: no-side-effect unit tests
  covering validation, blocked commit behavior, disabled dependencies, and safety flags.
- `Makefile`: adds `data-fotmob-single-target-adapter-preflight` and blocked
  `data-fotmob-single-target-adapter-commit`.
- `AGENTS.md`: records Phase 4.97F FotMob scaffold rules.
- `docs/_reports/FOTMOB_SINGLE_TARGET_ADAPTER_SCAFFOLD_PHASE4_97F.md`: this report.

## 3. Adapter Behavior

- single-target only
- supports `match_id` and `league_season_date` target scope types
- `max_targets=1`
- no bulk scope
- no network access
- no browser runtime
- no proxy runtime
- no staging write
- no source manifest write
- no packet write
- no DB read or write dependency
- stdout-only JSON preflight
- `--commit` is blocked and exits non-zero
- all `yes` CLI authorization flags remain no-op and do not authorize execution

## 4. Dependency Injection

The scaffold exposes `createFotMobSingleTargetAdapter({ networkClient, parser, clock, logger })`.

- The network client is injected.
- The default network client is disabled and throws if `fetch()` is called.
- The parser is a stubbed no-op preview parser.
- The logger is a no-op console-safe dependency by default.
- The adapter does not import FotMob legacy runtime.
- The adapter does not import browser, proxy, Redis, or DB clients.

`dryRunFetchSingleTarget()` remains disabled in Phase 4.97F. A future phase must implement
and authorize any real network behavior separately.

## 5. Guardrails

The preflight summary keeps these flags false:

- `would_access_network=false`
- `would_launch_browser=false`
- `would_use_proxy=false`
- `would_execute_legacy_runtime=false`
- `would_execute_engine=false`
- `would_write_staging=false`
- `would_create_staging_directory=false`
- `would_write_source_manifest=false`
- `would_write_packet_file=false`
- `would_write_db=false`
- `would_train=false`
- `would_predict=false`
- `would_spawn_child_process=false`

The commit gate remains `blocked`.

## 6. Validation

Required validation for this phase:

- new unit tests
- `npm test`
- `npm run test:coverage`
- `npm run test:integration`
- ESLint
- Prettier
- `git diff --check`
- DB row counts unchanged
- `l1-config-*` residue absent
- `docs/_staging_preview` absent

The expected DB counts remain:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 7. Recommended Next Phase

Recommended next phase: Phase 4.98F, FotMob adapter preflight hardening.

Phase 4.98F should:

- not access the network
- not write DB
- not write staging
- add source manifest candidate preview
- add parser confidence stub
- add stricter policy validation
- continue to avoid any network dry-run execution

## 8. Explicit Non-Execution

Phase 4.97F did not execute:

- external FotMob access
- external football data access
- external odds data access
- curl / wget
- browser automation
- proxy runtime
- scraping
- harvest
- ingest
- batch backfill
- network dry-run
- staging write
- source manifest write
- packet write
- DB writes
- pg_dump / pg_restore
- training
- prediction
- file deletion
- legacy FotMob runtime execution
