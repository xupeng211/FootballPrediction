# Football-Data Packet File Preflight - Phase 4.70C

## 1. Current HEAD / branch

- Starting HEAD: `da30a4a7ff86907861b3f29cd20c16c98cc1ae1a`
- Branch: `feat/football-data-packet-file-preflight-phase470c`
- Base: Phase 4.69C merged on remote `main`

## 2. Why one larger themed PR is reasonable

Phase 4.70C adds one coherent safety layer: a preflight gate for future packet file generation. The script, Makefile targets, unit tests, AGENTS rules, and this report all describe the same non-write contract around future packet path and metadata preview, so keeping them in one PR keeps the behavior auditable end to end.

## 3. Added / changed files

- `scripts/ops/football_data_packet_file_preflight.js`
- `tests/unit/football_data_packet_file_preflight.test.js`
- `Makefile`
- `AGENTS.md`
- `docs/_reports/FOOTBALL_DATA_PACKET_FILE_PREFLIGHT_PHASE4_70C.md`

## 4. Packet file preflight design

The new preflight script accepts:

```bash
node scripts/ops/football_data_packet_file_preflight.js \
  --source-manifest <path> \
  --local-csv <path> \
  --approval-form docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md \
  --runbook-template docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md
```

It reads only local files, reuses the Phase 4.69C packet preview, preserves SELECT-only DB inspection through the reused gate path, validates that the packet sections are complete, and previews only the future packet directory, future packet filename, future packet manifest filename, and future metadata.

The script does not create directories, does not write packet files, does not write DB state, does not execute `pg_dump`, does not execute `pg_restore`, does not spawn child processes, and does not import the legacy downloader runtime.

## 5. Future packet directory / filename / manifest preview

The preflight outputs these preview strings:

```text
future_packet_directory_preview=docs/_packets/football_data/small_write/<timestamp>_<source_slug>/
future_packet_file_preview=football_data_small_write_packet_<source_slug>_<hash8>.json
future_packet_manifest_preview=football_data_small_write_packet_manifest_<source_slug>_<hash8>.json
```

These are preview-only strings. The script does not create `docs/_packets`, does not create the preview directory, and does not create either JSON file.

## 6. Why no packet file is created

Phase 4.70C is still a preview-only gate. A real packet file would become a durable review artifact and therefore requires a separately authorized later phase. The preflight reports:

- `packet_file_generation_allowed=false`
- `packet_write_allowed=false`
- `would_write_packet_file=false`
- `would_write_packet_manifest=false`

## 7. Why no directory is created

The future directory path is previewed only so reviewers can verify where a real packet file would belong. Directory creation would be an actual filesystem mutation and is therefore out of scope for this phase. The preflight reports:

- `would_create_packet_directory=false`
- `no_packet_directory_create`

## 8. Why no DB write is performed

This phase only previews future packet file generation prerequisites. DB access remains SELECT-only through the reused packet preview chain. The preflight reports:

- `select_only_db_reads=true`
- `would_write_db=false`
- `would_insert_matches=false`
- `would_insert_odds=false`

## 9. Why no pg_dump is executed

This phase only previews the future packet metadata and keeps backup activity blocked. A real `pg_dump` remains a separate authorization step before any future DB write. The preflight reports:

- `would_execute_pg_dump=false`
- `would_execute_pg_restore=false`
- `no_pg_dump_execution`
- `no_pg_restore_execution`

## 10. Commit gate result

Both packet file commit gate checks remained blocked:

- `make data-football-data-packet-file-commit || true`
- `make data-football-data-packet-file-commit ... CONFIRM_FOOTBALL_DATA_PACKET_FILE=1 || true`

Observed blocked message:

```text
BLOCKED: football-data packet file generation is not wired in Phase 4.70C.
```

## 11. Existing gates revalidated

All reused Football-Data gates passed:

- `make data-football-data-small-write-packet-preview`: passed
- `make data-football-data-csv-dry-run`: passed
- `make data-football-data-db-write-preflight`: passed
- `make data-football-data-duplicate-precheck`: passed
- `make data-football-data-insert-policy-precheck`: passed
- `make data-football-data-small-write-auth-preview`: passed
- `make data-football-data-small-write-runbook-validate`: passed

No DB writes, no `pg_dump`, no directory creation, and no packet file writes occurred.

## 12. Unit tests

All requested unit tests passed:

- `tests/unit/football_data_packet_file_preflight.test.js`
- `tests/unit/football_data_small_write_packet_assembly.test.js`
- `tests/unit/football_data_small_write_runbook_validate.test.js`
- `tests/unit/football_data_small_write_auth_preview.test.js`
- `tests/unit/football_data_insert_policy_precheck.test.js`
- `tests/unit/football_data_duplicate_precheck.test.js`
- `tests/unit/football_data_db_write_preflight.test.js`
- `tests/unit/football_data_adapter_dry_run.test.js`
- `tests/unit/football_data_local_csv_parser.test.js`
- `tests/unit/acquisition_engine_gate.test.js`

The new packet file preflight test covers missing arguments, successful mock preview, future packet directory / filename / manifest preview, approval defaults, blocked commit, sha256 / row_count mismatch without DB reads, invalid approval form, no legacy import, no network, no file writes, no directory creation, no packet file write, no `pg_dump`, no `pg_restore`, no child process spawn, and SELECT-only SQL guard behavior.

## 13. npm test / coverage

- `docker compose -f docker-compose.dev.yml exec -T dev npm test`: passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`: passed
- Coverage thresholds were not modified.

Final coverage:

```text
lines=88.44
branches=80.00
functions=80.88
```

## 14. DB before / after statistics

Expected before counts:

```text
matches=2
bookmaker_odds_history=2
raw_match_data=2
l3_features=2
match_features_training=2
predictions=2
```

Observed after counts:

```text
matches=2
bookmaker_odds_history=2
raw_match_data=2
l3_features=2
match_features_training=2
predictions=2
```

DB row counts were unchanged.

## 15. Next steps

- Phase 4.71C: real packet file creation authorization form, still no DB write and no `pg_dump`; whether to create a real packet file requires separate user authorization.
- Or Phase 4.56A: prepare runbook work only after the user provides complete real network dry-run parameters.

## 16. Explicitly not executed

- DB writes
- non-SELECT DB SQL
- `pg_dump`
- `pg_restore`
- backup file writes
- packet file writes
- packet directory creation
- file writes from packet runtime
- changing `approval_status` to `approved_for_db_write`
- changing `final_human_confirmation` to `true`
- external download
- `curl` / `wget` / `git clone`
- external football data source access
- external odds source access
- scraping / browser automation
- harvest / ingest
- batch backfill
- network dry-run execution
- bulk harvest
- adapted CSV / staging data writes
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
