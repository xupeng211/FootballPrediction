# Phase 4.80D: Single-Target Acquisition Staging Schema Validator

**Date**: 2026-05-10
**Status**: Complete (validator-only)
**Previous phase**: Phase 4.79D — Single-Target Acquisition Runtime Scaffold
**Next recommended phase**: Phase 4.81D or Phase 4.56A

---

## 1. Executive Summary

Phase 4.80D is a **schema validator** phase. It defines the JSON schemas for future
single-target acquisition staging artifacts and source manifest candidates, and provides
a local-only validator to verify sample fixtures against those schemas.

The validator:

- Reads schema files and data files from the local filesystem
- Validates JSON structure, required fields, type constraints, enum/const values
- Outputs a JSON summary to stdout
- Does NOT access network, launch browser, use proxy, write files, write DB,
  execute engines, or spawn child processes

Sample fixtures are test assets only — they are NOT real staging artifacts.

---

## 2. Implemented Files

### Schemas

```
schemas/acquisition/single_target_staging_artifact.schema.json
schemas/acquisition/source_manifest_candidate.schema.json
```

### Validator

```
scripts/ops/single_target_acquisition_staging_schema_validator.js
```

### Test Fixtures (sample only, not real staging data)

```
tests/fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json
tests/fixtures/acquisition/sample_source_manifest_candidate_phase480d.json
```

### Tests

```
tests/unit/single_target_acquisition_staging_schema_validator.test.js
```

### Makefile Targets

```
make data-single-target-acquisition-staging-schema-validate    (local-only, Phase 4.80D)
make data-single-target-acquisition-staging-schema-commit      (blocked, Phase 4.80D)
```

### Documentation

```
AGENTS.md (updated)
docs/_reports/SINGLE_TARGET_ACQUISITION_STAGING_SCHEMA_VALIDATOR_PHASE4_80D.md
```

---

## 3. Staging Artifact Schema

The staging artifact schema defines the structure for future single-target acquisition
network dry-run output.

### Required top-level fields

| Field              | Type   | Description                                    |
| ------------------ | ------ | ---------------------------------------------- |
| `artifact_version` | string | Schema version                                 |
| `phase`            | string | Acquisition phase                              |
| `source`           | object | Source metadata (name, source_url required)    |
| `target_scope`     | object | Target scope (scope_type required)             |
| `engine`           | object | Engine family (must be `titan_discovery`)      |
| `runtime`          | object | Browser/proxy/network config                   |
| `capture`          | object | Capture metadata (raw_payload_sha256 required) |
| `provenance`       | object | Provenance (captured_at required)              |
| `safety`           | object | Safety flags (all must be false)               |
| `outputs`          | object | Output paths                                   |

### Key constraints

- `source.name` required
- `source.source_url` required
- `target_scope.scope_type` must be `match_id` or `league_season_date`
- `engine.family` must be `titan_discovery`
- `safety.would_write_db` must be `false`
- `safety.would_train` must be `false`
- `safety.would_predict` must be `false`
- `safety.bulk_scope` must be `false`
- If `scope_type=match_id`, `match_id` is required
- If `scope_type=league_season_date`, `league`, `season`, `date` are required
- No additional properties allowed on core objects

---

## 4. Source Manifest Candidate Schema

The source manifest candidate schema defines the structure for a manifest derived
from a staging artifact. It documents data provenance and licensing.

### Key constraints

- `manifest_status` must be `candidate_not_approved`
- `approval_status` must be `not_approved`
- `engine_family` must be `titan_discovery`
- `safety.approved_for_db_write` must be `false`
- `safety.approved_for_training` must be `false`
- `safety.approved_for_prediction` must be `false`

**Critical**: A manifest candidate does NOT authorize DB writes, training, or
prediction. Human review and separate authorization are required for any status change.

---

## 5. Validator Behavior

- **local-only**: reads schema and data files from the filesystem
- **read-only**: does not write any files, create directories, or modify state
- **no network**: does not import http/https/net, does not make network requests
- **no DB**: does not import pg, does not connect to any database
- **no child process**: does not spawn subprocesses
- **commit gate blocked**: `--commit` exits non-zero unconditionally

### CLI examples

```bash
# Full validation (artifact + manifest)
node scripts/ops/single_target_acquisition_staging_schema_validator.js \
  --artifact-schema=schemas/acquisition/single_target_staging_artifact.schema.json \
  --manifest-schema=schemas/acquisition/source_manifest_candidate.schema.json \
  --artifact=tests/fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json \
  --manifest=tests/fixtures/acquisition/sample_source_manifest_candidate_phase480d.json

# Artifact-only
node scripts/ops/single_target_acquisition_staging_schema_validator.js \
  --artifact-schema=schemas/acquisition/single_target_staging_artifact.schema.json \
  --artifact=tests/fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json

# Via Makefile
make data-single-target-acquisition-staging-schema-validate \
  ARTIFACT_SCHEMA=schemas/acquisition/single_target_staging_artifact.schema.json \
  MANIFEST_SCHEMA=schemas/acquisition/source_manifest_candidate.schema.json \
  ARTIFACT=tests/fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json \
  MANIFEST=tests/fixtures/acquisition/sample_source_manifest_candidate_phase480d.json
```

---

## 6. Test Coverage

Tests: `tests/unit/single_target_acquisition_staging_schema_validator.test.js`

Coverage includes:

- Missing schema paths → failure
- Invalid JSON schema/data → failure
- Valid artifact → success
- Valid manifest → success
- Artifact + manifest combined → success
- Missing required fields (source.name, target_scope, etc.) → failure
- Forbidden scope_type (bulk) → failure
- Scope-dependent field requirements → failure
- Non-titan_discovery engine → failure
- Safety flags set to true → failure
- Manifest status/approval violations → failure
- `--commit` blocked → failure
- Source code audit: no forbidden imports
- Integration tests: subprocess CLI validation
- All `would_*` output fields verified false

---

## 7. Relationship to Phase 4.79D

| Phase | Purpose                                                                    | Status   |
| ----- | -------------------------------------------------------------------------- | -------- |
| 4.79D | Parameter scaffold — validates input parameters for future runtime         | Complete |
| 4.80D | Schema validator — validates output structure for future staging artifacts | Complete |

Both phases are **non-executing**:

- Neither accesses network
- Neither writes DB
- Neither writes staging
- Neither equals real network dry-run authorization
- Neither equals staging write authorization

---

## 8. Recommended Next Phase

**Phase 4.81D**: Single-target acquisition staging artifact writer preflight.

Goal: Define the preflight checks that would run before any real staging write,
while still not creating directories, not writing files, not accessing network,
and not writing DB.

Alternatively:

**Phase 4.56A**: User provides explicit real source, engine, target, manifest,
terms approval, and network authorization before executing a real network
dry-run runbook.

---

## 9. Explicit Non-Execution Confirmation

The following were **not** performed during Phase 4.80D:

- DB writes (INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/TRUNCATE/COPY)
- Non-SELECT DB SQL
- External downloads (curl/wget/git clone)
- External football data access
- External odds data access
- Scraping
- Browser automation
- Proxy runtime execution
- Harvest / ingest
- Batch backfill
- Network dry-run execution
- Bulk harvest
- Runtime staging artifact write
- Runtime source manifest write
- Packet file write
- `pg_dump` / `pg_restore`
- Model training
- Real prediction execution
- Model artifact loading
- Docker volume cleanup (`docker system prune`, `docker volume prune`)
- Force push
- `git fetch --all`
- `git pull`
- `rm -rf`
- File deletion
- Coverage threshold modification
- Test skipping
- Test deletion
- Gatekeeper bypass
