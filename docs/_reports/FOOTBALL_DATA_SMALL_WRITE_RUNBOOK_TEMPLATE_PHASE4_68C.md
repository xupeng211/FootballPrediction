# Football-Data Small Write Runbook Template Phase 4.68C

## 1. Current HEAD / branch

- Branch: `docs/football-data-small-write-runbook-phase468c`
- Start HEAD: `72e1db0976d7c9b14b42201a9bce95e9a51a5eff`
- Start commit: `72e1db0 feat(data): add football-data small write auth preview`

## 2. Why a slightly larger PR is reasonable

Phase 4.68C fixes the human-facing control surface before any real small DB write.
The runbook template, approval form, validator, Makefile gates, tests, AGENTS rules,
and report are tightly coupled: each one defines or verifies the same approval
boundary. Splitting them would leave a template without enforcement, or a gate
without the documented approval contract.

## 3. New / changed files

- `docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_RUNBOOK_TEMPLATE.md`
- `docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md`
- `scripts/ops/football_data_small_write_runbook_validate.js`
- `tests/unit/football_data_small_write_runbook_validate.test.js`
- `docs/_reports/FOOTBALL_DATA_SMALL_WRITE_RUNBOOK_TEMPLATE_PHASE4_68C.md`
- `Makefile`
- `AGENTS.md`

## 4. Runbook template summary

The runbook template records the future real small DB write procedure. It includes
scope, required preconditions, pre-write command previews, `pg_dump` preview,
candidate insert and forbidden candidate tables, a blocked future write placeholder,
post-write validation, rollback / restore preview, and final sign-off.

Every command preview is marked as preview-only for Phase 4.68C. The template is
not an execution authorization.

## 5. Approval form template summary

The approval form template contains a machine-readable YAML block with:

- `approval_status: not_approved`
- explicit source / license / terms / operator / reviewer fields
- `target_tables: [matches]`
- all write expansion flags set to `false`
- `allow_training: false`
- `allow_prediction: false`
- `require_pg_dump: true`
- before / after count placeholders
- `rollback_plan_reviewed: false`
- `post_write_validation_required: true`
- `final_human_confirmation: false`

## 6. Why the form defaults to not approved

Phase 4.68C prepares templates only. It does not approve real writes, does not
prove a real source license, does not validate a real backup file, and does not
grant final human confirmation. Keeping `approval_status=not_approved` prevents
the template from being mistaken for a completed approval record.

## 7. Validator design

`scripts/ops/football_data_small_write_runbook_validate.js` reads a local markdown
approval form, extracts the YAML fenced block, parses the supported local template
shape, and validates required safety fields.

The validator confirms:

- required fields exist
- template approval status remains `not_approved`
- `target_tables` contains only `matches`
- odds/raw/L3/training/prediction write flags remain `false`
- training and prediction remain disabled
- `require_pg_dump=true`
- `final_human_confirmation=false`

The validator does not access the network, read DB, write DB, write files, execute
`pg_dump`, execute `pg_restore`, or spawn child processes.

## 8. Makefile entries

- `make data-football-data-small-write-runbook-validate APPROVAL_FORM=<path>`
- `make data-football-data-small-write-runbook-commit APPROVAL_FORM=<path> CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1`

The commit target remains blocked in Phase 4.68C, even with confirmation.

## 9. Commit gate blocked result

Validated commands:

- `make data-football-data-small-write-runbook-validate || true`
    - Result: failed with `ERROR: provide APPROVAL_FORM=<path>`
- `make data-football-data-small-write-runbook-validate APPROVAL_FORM=docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md`
    - Result: passed
- `make data-football-data-small-write-runbook-commit || true`
    - Result: blocked
- `make data-football-data-small-write-runbook-commit APPROVAL_FORM=docs/runbooks/FOOTBALL_DATA_SMALL_DB_WRITE_APPROVAL_FORM_TEMPLATE.md CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1 || true`
    - Result: blocked

## 10. Existing gates recheck

All existing Football-Data gates passed with the local fixture manifest and CSV:

- `make data-football-data-csv-dry-run`
- `make data-football-data-db-write-preflight`
- `make data-football-data-duplicate-precheck`
- `make data-football-data-insert-policy-precheck`
- `make data-football-data-small-write-auth-preview`

No DB writes, `pg_dump`, or `pg_restore` were executed by these gates.

## 11. Unit tests

Passed:

- `node --test tests/unit/football_data_small_write_runbook_validate.test.js`
    - 31 tests passed
- `node --test tests/unit/football_data_small_write_auth_preview.test.js`
    - 23 tests passed
- `node --test tests/unit/football_data_insert_policy_precheck.test.js`
    - 23 tests passed
- `node --test tests/unit/football_data_duplicate_precheck.test.js`
    - 20 tests passed
- `node --test tests/unit/football_data_db_write_preflight.test.js`
    - 11 tests passed
- `node --test tests/unit/football_data_adapter_dry_run.test.js`
    - 11 tests passed
- `node --test tests/unit/football_data_local_csv_parser.test.js`
    - 10 tests passed
- `node --test tests/unit/acquisition_engine_gate.test.js`
    - 8 tests passed

## 12. npm test / coverage

- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
    - Result: passed
- First `npm run test:coverage`
    - Result: failed only on coverage threshold
    - Cause: `branches=79.97 < 80`
    - Action: added validator branch coverage tests; coverage threshold was not changed
- Final `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`
    - Result: passed
    - Coverage summary:
        - lines: `88.19`
        - functions: `80.74`
        - branches: `80.07`

## 13. DB row counts

Before changes:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

After validation:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

## 14. Next steps

- Phase 4.69C: prepare real small write dry-run packet assembly, still no DB writes
  and no `pg_dump` execution.
- Or Phase 4.56A: only after the user provides complete real network dry-run
  parameters should a network-source runbook be prepared.

## 15. Explicitly not executed

- DB writes
- non-SELECT DB SQL
- `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `ALTER` / `DROP` / `TRUNCATE` / `COPY`
- DB reads from the new validator
- `pg_dump`
- `pg_restore`
- backup file writes
- file writes from validator runtime
- approval status changes to `approved_for_db_write`
- `final_human_confirmation=true`
- external downloads
- external football data source access
- external odds data source access
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
