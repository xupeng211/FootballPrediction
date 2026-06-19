# Matches Labeling Post-Backfill Audit

- lifecycle: phase-artifact
- generated: 2026-06-19
- branch: docs/matches-labeling-post-backfill-audit
- previous: #1551 feat(data): execute matches labeling backfill write

## Nature

Read-only post-backfill audit. Confirms matches governance labels written by
#1551 are stable and correct. No migration, no schema change, no DB write, no
backfill, no live fetch, no raw payload output.

## Audit Command

```bash
docker compose -f docker-compose.dev.yml exec -T db \
  psql -U football_user -d football_db -c "SELECT ..."
```

All queries are SELECT-only against the local dev database.

## Row Counts

| Table | Count | Status |
|-------|-------|--------|
| matches | 60 | unchanged |
| raw_match_data | 76 | unchanged |

## Governance Fields

| Metric | Count |
|--------|-------|
| governance populated | 60 |
| governance still NULL | 0 |
| candidate_total | 0 |
| no_raw_excluded | 2 |

## Pipeline Status

| Status | Count | Status |
|--------|-------|--------|
| harvested | 58 | unchanged |
| pending | 2 | unchanged |

## Source Type Distribution

| Source Type | Count |
|-------------|-------|
| fotmob_live_fetch | 58 |
| synthetic | 2 |

## Evidence Level Distribution

| Evidence Level | Count |
|----------------|-------|
| strong | 58 |
| synthetic_invalid | 2 |

## Production / Reconciliation / Training Scope

| Field | true | false |
|-------|------|-------|
| is_production_scope | 58 | 2 |
| is_reconciliation_eligible | 58 | 2 |
| is_training_eligible | 0 | 60 |

## Pipeline Status Reason

| Reason | Count |
|--------|-------|
| NULL | 58 |
| awaiting_match_completion | 1 |
| synthetic_raw_not_valid | 1 |

## Ligue 1 2025/2026 (58/58)

All 58 matches: status=finished, pipeline_status=harvested,
source_type=fotmob_live_fetch, evidence_level=strong,
is_production_scope=true, is_reconciliation_eligible=true,
is_training_eligible=false, pipeline_status_reason=NULL.

## No-Raw Excluded (2 rows)

- **140_20252026_4837496**: Segunda División / 2025/2026 / scheduled / pending,
  source_type=synthetic, evidence_level=synthetic_invalid,
  is_production_scope=false, is_reconciliation_eligible=false,
  is_training_eligible=false, pipeline_status_reason=awaiting_match_completion

- **47_20242025_900002**: Segunda / 2024/2025 / finished / pending,
  source_type=synthetic, evidence_level=synthetic_invalid,
  is_production_scope=false, is_reconciliation_eligible=false,
  is_training_eligible=false, pipeline_status_reason=synthetic_raw_not_valid

## Consistency with #1551 Write Results

✅ All metrics match the #1551 post-write verification exactly. No drift detected.

## Safety

- No migration
- No schema change
- No DB write
- No backfill
- No live fetch
- No raw payload output
- No parser/training/prediction changes

## Risk

Zero. All 60 rows have correct governance labels. No orphan or inconsistent rows.

## Next Step

Do not start automatically. Recommended next task only after user confirmation.
