# FotMob Stdout Network Dry-Run Authorization Packet

Phase: 4.99F
Status: template-only, local validation only
Starting HEAD: `e1db303d3b18ee9220cd6bcad2d2c75b8b51fb80`

## 1. Executive Summary

Phase 4.99F creates a FotMob stdout-only network dry-run authorization packet
template.

This phase does not access FotMob, collect data, write DB rows, or write staging
artifacts. The authorization packet itself is not execution and does not authorize a
network dry-run.

## 2. Implemented Files

- `docs/runbooks/FOTMOB_STDOUT_ONLY_NETWORK_DRY_RUN_AUTHORIZATION_PACKET_TEMPLATE.md`
- `scripts/ops/fotmob_stdout_network_dry_run_authorization_packet.js`
- `tests/unit/fotmob_stdout_network_dry_run_authorization_packet.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/FOTMOB_STDOUT_NETWORK_DRY_RUN_AUTHORIZATION_PACKET_PHASE4_99F.md`

## 3. Packet Sections

The packet template includes these machine-readable sections:

- `target`
- `source_terms`
- `network_policy`
- `output_policy`
- `data_safety_policy`
- `authorization_decision`
- `included_artifacts`
- `authorization_blocking_reasons`
- `codex_constraints`
- `safety`
- `next_phase_requirements`

## 4. Authorization Boundary

- The packet is not an authorization result.
- The packet is not execution.
- `target_count=0` by default.
- `network_dry_run_authorized=false` by default.
- `network_dry_run_execution_allowed=false` by default.
- A future execution phase is required.
- The user must supply the real target, source terms, allowed-use approval, and
  network authorization.

## 5. Validation

Required validation for this phase:

- `node --test tests/unit/fotmob_stdout_network_dry_run_authorization_packet.test.js`
- valid packet preview
- blocked commit gate
- `npm test`
- `npm run test:coverage`
- `npm run test:integration` skipped locally if it would require browser automation
- ESLint
- Prettier
- `git diff --check`
- DB row counts unchanged
- `l1-config-*` residue absent
- `docs/_staging_preview` absent

Expected DB counts remain:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 6. Recommended Next Phase

Recommended next phase: Phase 5.00F, FotMob stdout-only network dry-run execution
plan.

Phase 5.00F should:

- still not directly access the network
- first convert a user-filled authorization packet into an execution plan
- still not write DB
- default to no staging write
- require explicit user authorization again before any network access

## 7. Explicit Non-Execution

Phase 4.99F did not execute:

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
- packet runtime write
- DB writes
- pg_dump / pg_restore
- training
- prediction
- file deletion
- legacy FotMob runtime execution
