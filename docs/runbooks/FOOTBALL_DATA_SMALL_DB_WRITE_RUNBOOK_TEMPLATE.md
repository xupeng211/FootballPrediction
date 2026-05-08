# Football-Data Small DB Write Runbook Template

> PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.
>
> This template records the human runbook required before any future real small
> DB write. It is not an execution authorization.

## 1. Scope

- Phase:
- Operator:
- Reviewer:
- Date:
- Target environment:
- Source manifest:
- Local CSV:
- Max rows:
- Target tables:
- Allowed operation:
- Explicitly forbidden operations:

## 2. Required preconditions

- Source manifest exists
- Source manifest approval_status=approved_for_db_write
- Human approval note present
- Local CSV exists
- sha256 matches
- row_count matches
- CSV dry-run passed
- DB write preflight passed
- duplicate precheck passed
- insert policy precheck passed
- small write auth preview passed
- exact existing matches excluded
- manual review candidates excluded
- invalid candidates excluded
- deterministic match_id strategy accepted
- max insert rows explicitly approved
- target inserted match_ids listed
- downstream training/prediction remains blocked

## 3. Pre-write commands preview

PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.

```bash
make data-football-data-csv-dry-run \
  SOURCE_MANIFEST=<local source manifest> \
  LOCAL_CSV=<local csv>
```

PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.

```bash
make data-football-data-db-write-preflight \
  SOURCE_MANIFEST=<local source manifest> \
  LOCAL_CSV=<local csv>
```

PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.

```bash
make data-football-data-duplicate-precheck \
  SOURCE_MANIFEST=<local source manifest> \
  LOCAL_CSV=<local csv>
```

PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.

```bash
make data-football-data-insert-policy-precheck \
  SOURCE_MANIFEST=<local source manifest> \
  LOCAL_CSV=<local csv>
```

PREVIEW ONLY / DO NOT RUN IN PHASE 4.68C.

```bash
make data-football-data-small-write-auth-preview \
  SOURCE_MANIFEST=<local source manifest> \
  LOCAL_CSV=<local csv>
```

## 4. pg_dump backup command preview

DO NOT RUN IN PHASE 4.68C.

```bash
docker compose -f docker-compose.dev.yml exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > data/backups/<timestamp>_pre_football_data_small_write.dump
```

## 5. Candidate insert list

| row_number | proposed_match_id | home_team | away_team | match_date | insert_policy | approved_to_insert |
| ---------- | ----------------- | --------- | --------- | ---------- | ------------- | ------------------ |
|            |                   |           |           |            |               |                    |

## 6. Forbidden candidate list

| row_number | reason | duplicate_risk | required_action |
| ---------- | ------ | -------------- | --------------- |
|            |        |                |                 |

## 7. Future write command placeholder

The future write command remains blocked / not wired in Phase 4.68C.

```bash
make data-football-data-small-write-runbook-commit \
  APPROVAL_FORM=<completed approval form> \
  CONFIRM_FOOTBALL_DATA_SMALL_WRITE_RUNBOOK=1
```

## 8. Post-write validation checklist

- before/after row counts
- inserted match_ids only
- no odds insert unless separately authorized
- no raw/l3/training/prediction writes
- rerun dataset status
- rerun duplicate precheck
- record backup path
- record commit hash
- record report path

## 9. Rollback / restore preview

- restore not automatic
- restore requires separate human authorization
- restore command preview only
- backup file must be reviewed before restore

```bash
docker compose -f docker-compose.dev.yml exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists <backup_path>
```

## 10. Final sign-off

- Operator signature:
- Reviewer signature:
- Timestamp:
- Approval scope:
- Explicit exclusions:
